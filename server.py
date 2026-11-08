import csv, io, os, re, time, secrets, threading
from datetime import date, datetime
from flask import Flask, request, jsonify, send_from_directory
import requests
from engine import predict, compare, walkforward, coldest_numbers

app = Flask(__name__, static_folder='.', static_url_path='')
LOCK = threading.RLock()
DRAWS = {}
SESSIONS = {}
LAST_FETCH = 0
LAST_ERROR = None
SOURCE = None
TTL = int(os.getenv('LOTTO_CACHE_SECONDS', '21600'))
BETTIP_URL = os.getenv('LOTTO_ARCHIVE_URL', 'https://bettip.co.za/api/v1/lotto/draws.json')
# BetTip endpoint was advertised but could not be independently verified at build time.

def normalized_date(raw):
    s = str(raw or '').strip()
    for fmt in ('%Y-%m-%d','%Y/%m/%d','%d/%m/%Y','%d-%m-%Y'):
        try: return datetime.strptime(s[:10],fmt).date().isoformat()
        except ValueError: pass
    raise ValueError('Unrecognized draw date: '+s[:30])

def parse_numbers(record):
    if isinstance(record,dict):
        for key in ('numbers','winning_numbers','winningNumbers','main_numbers','mainNumbers','balls','results'):
            if key in record:
                val=record[key]
                if isinstance(val,dict): val=val.get('main',val.get('numbers',[]))
                if isinstance(val,str): val=re.findall(r'\d+',val)
                if isinstance(val,list):
                    val=[(x.get('number') if isinstance(x,dict) else x) for x in val]
                    return [int(x) for x in val]
        for prefix in ('n','number','ball'):
            if all(f'{prefix}{i}' in record for i in range(1,7)):
                return [int(record[f'{prefix}{i}']) for i in range(1,7)]
    raise ValueError('Unrecognized number format')

def extract_records(payload):
    if isinstance(payload,list): return payload
    if isinstance(payload,dict):
        for key in ('draws','results','data','lotto','items'):
            if key in payload:
                val=payload[key]
                if isinstance(val,list): return val
                if isinstance(val,dict): return extract_records(val)
    raise ValueError('Unknown BetTip archive response shape')

def validate_record(record):
    if not isinstance(record,dict): raise ValueError('Draw is not an object')
    # Reject explicitly non-Lotto games, including Lotto Plus and Daily Lotto.
    game=str(record.get('game',record.get('game_name',record.get('lottery','lotto')))).lower().replace('_',' ').strip()
    if game not in ('lotto','sa lotto','south african lotto','national lotto','national lottery lotto'):
        return None
    day=normalized_date(record.get('date',record.get('draw_date',record.get('drawDate'))))
    nums=sorted(parse_numbers(record))
    if len(nums)!=6 or len(set(nums))!=6 or not all(1<=n<=52 for n in nums):
        raise ValueError('Invalid six-number draw for '+day)
    # Reject rows whose ruleset is not known to be 6/52. Historical game rules changed.
    if max(nums)>52: raise ValueError('Out-of-range draw')
    return day,nums

def parse_archive(raw,content_type=''):
    text=raw.decode('utf-8-sig') if isinstance(raw,bytes) else raw
    if 'csv' in content_type or text.lstrip().lower().startswith('date,'):
        records=list(csv.DictReader(io.StringIO(text)))
    else:
        import json
        records=extract_records(json.loads(text))
    out={}; bad=0
    for rec in records:
        try:
            item=validate_record(rec)
            if not item: continue
            day,nums=item
            if day in out and out[day]!=nums: raise ValueError('Conflicting results on '+day)
            out[day]=nums
        except Exception: bad+=1
    if not out: raise ValueError('No valid 6/52 Lotto draws found; check the API response format')
    return out,bad

def load_local():
    path=os.getenv('LOTTO_DATA_FILE','draws.csv')
    if not os.path.isfile(path): return
    with open(path,'rb') as f: rows,_=parse_archive(f.read(),'text/csv')
    with LOCK:
        DRAWS.update(rows)
        global SOURCE
        SOURCE='Local verified CSV (user supplied)'

try: load_local()
except Exception as exc: LAST_ERROR='Local archive: '+str(exc)

def refresh(force=False):
    global LAST_FETCH,LAST_ERROR,SOURCE
    with LOCK:
        if not force and LAST_FETCH and time.time()-LAST_FETCH<TTL: return
        # Avoid repeated failing requests on every page load.
        LAST_FETCH=time.time()
    try:
        if not BETTIP_URL.startswith('https://'): raise ValueError('Archive URL must be HTTPS')
        resp=requests.get(BETTIP_URL,headers={'Accept':'application/json,text/csv','User-Agent':'ZF-Lotto-Robot/7.0'},timeout=(7,18))
        resp.raise_for_status()
        if len(resp.content)>12_000_000: raise ValueError('Archive exceeds 12MB safety limit')
        rows,bad=parse_archive(resp.content,resp.headers.get('Content-Type',''))
        with LOCK:
            for day,nums in rows.items():
                if day in DRAWS and DRAWS[day]!=nums:
                    raise ValueError('Source conflict for '+day+'; refusing to overwrite existing result')
            DRAWS.update(rows)
            LAST_ERROR=None
            SOURCE='BetTip archive (unverified third-party provider)'
    except Exception as exc:
        with LOCK: LAST_ERROR=f'{type(exc).__name__}: {str(exc)[:250]}'

def snapshot():
    with LOCK: return [{'date':d,'numbers':nums} for d,nums in sorted(DRAWS.items())]

@app.get('/')
def home(): return send_from_directory('.','index.html')

@app.get('/api/status')
def status():
    refresh()
    ds=snapshot()
    with LOCK: err=LAST_ERROR; src=SOURCE; last=LAST_FETCH
    return jsonify(draws=len(ds),first=ds[0]['date'] if ds else None,last=ds[-1]['date'] if ds else None,provider='BetTip',online_provider_configured=True,source=src,fetch_error=err,cache_age_seconds=round(time.time()-last) if last else None)

@app.post('/api/refresh')
def refresh_endpoint():
    refresh(force=True)
    return status()

@app.post('/api/import')
def import_csv():
    f=request.files.get('file')
    if not f: return jsonify(error='CSV required'),400
    try:
        rows,_=parse_archive(f.read(),'text/csv')
        with LOCK:
            for d,nums in rows.items():
                if d in DRAWS and DRAWS[d]!=nums: raise ValueError('Conflicting result: '+d)
            DRAWS.update(rows)
        return jsonify(imported=len(rows),total=len(DRAWS))
    except Exception as e:return jsonify(error=str(e)),400

@app.post('/api/predict')
def prediction():
    p=request.get_json(silent=True) or {}; day=p.get('date','')
    try: date.fromisoformat(day)
    except (ValueError,TypeError):return jsonify(error='Choose a valid date'),400
    if day>=date.today().isoformat():return jsonify(error='Choose a previous draw date'),400
    refresh()
    history=[d for d in snapshot() if d['date']<day]
    try: rows=predict(history,day,str(p.get('reset',0)))
    except ValueError as exc:
        return jsonify(error=str(exc)+' Historical archive may be unavailable. Check Data Status.'),400
    token=secrets.token_urlsafe(32)
    with LOCK:
        if len(SESSIONS)>1000: SESSIONS.pop(next(iter(SESSIONS)))
        SESSIONS[token]={'date':day,'rows':rows}
    return jsonify(token=token,date=day,rows=rows,training_draws=len(history),excluded_cold_numbers=coldest_numbers(history))

@app.post('/api/reveal')
def reveal():
    token=(request.get_json(silent=True) or {}).get('token','')
    with LOCK: sess=SESSIONS.get(token)
    if not sess:return jsonify(error='Predict first'),400
    day=sess['date']
    with LOCK: actual=DRAWS.get(day)
    if actual is None:
        refresh(force=True)
        with LOCK: actual=DRAWS.get(day)
    if actual is None:return jsonify(error='No verified winning result found for this date. It may be a non-draw date or the archive is incomplete. No result was invented.'),404
    return jsonify(date=day,actual=actual,source=SOURCE or 'Historical archive',comparison=compare(sess['rows'],actual))

@app.post('/api/backtest')
def backtest():
    p=request.get_json(silent=True) or {}
    try: limit=max(1,min(500,int(p.get('limit',100))))
    except (ValueError,TypeError):return jsonify(error='Invalid limit'),400
    refresh()
    # The engine trains on only prior draws. Data must be checked for completeness.
    return jsonify(walkforward(snapshot(),p.get('start'),p.get('end'),limit))

if __name__=='__main__': app.run(host='0.0.0.0',port=int(os.getenv('PORT','10000')))
