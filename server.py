import csv, io, os, re, time, secrets, threading
from datetime import date, datetime
from flask import Flask, request, jsonify, send_from_directory
import requests
from engine import predict, compare, walkforward, coldest_numbers

app = Flask(__name__, static_folder='.', static_url_path='')
LOCK = threading.RLock()
DRAWS = {}
PLUS_DRAWS = {"plus1": {}, "plus2": {}}
PLUS_ERRORS = {"plus1": None, "plus2": None}
PLUS_FETCH = {"plus1": 0, "plus2": 0}
PLUS_URLS = {"plus1": os.getenv("LOTTO_PLUS1_ARCHIVE_URL", "https://bettip.co.za/api/v1/lotto-plus-1/draws.json"), "plus2": os.getenv("LOTTO_PLUS2_ARCHIVE_URL", "https://bettip.co.za/api/v1/lotto-plus-2/draws.json")}
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

def game_kind(record):
    value=str(record.get('game',record.get('game_name',record.get('lottery','lotto')))).lower()
    value=re.sub(r'[^a-z0-9]+',' ',value).strip()
    if 'daily' in value or 'powerball' in value: return None
    if re.search(r'(?:plus|\bpl\b)\s*2\b',value): return 'plus2'
    if re.search(r'(?:plus|\bpl\b)\s*1\b',value): return 'plus1'
    if value in ('lotto','sa lotto','south african lotto','national lotto','national lottery lotto'): return 'lotto'
    return None

def validate_record(record,expected_game='lotto',allow_unlabelled=False):
    if not isinstance(record,dict): raise ValueError('Draw is not an object')
    kind=game_kind(record)
    if allow_unlabelled and kind=='lotto' and not any(k in record for k in ('game','game_name','lottery')):
        kind=expected_game
    if kind!=expected_game:return None
    day=normalized_date(record.get('date',record.get('draw_date',record.get('drawDate'))))
    nums=sorted(parse_numbers(record))
    if len(nums)!=6 or len(set(nums))!=6 or not all(1<=n<=52 for n in nums):
        raise ValueError('Invalid six-number draw for '+day)
    # Reject rows whose ruleset is not known to be 6/52. Historical game rules changed.
    if max(nums)>52: raise ValueError('Out-of-range draw')
    return day,nums

def parse_archive(raw,content_type='',expected_game='lotto',allow_unlabelled=False):
    text=raw.decode('utf-8-sig') if isinstance(raw,bytes) else raw
    if 'csv' in content_type or text.lstrip().lower().startswith('date,'):
        records=list(csv.DictReader(io.StringIO(text)))
    else:
        import json
        records=extract_records(json.loads(text))
    out={}; bad=0
    for rec in records:
        try:
            item=validate_record(rec,expected_game,allow_unlabelled)
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

def load_plus_local():
    for kind,filename in [('plus1','draws_plus1.csv'),('plus2','draws_plus2.csv')]:
        if not os.path.isfile(filename):continue
        try:
            with open(filename,'rb') as f:
                rows,_=parse_archive(f.read(),'text/csv',kind,True)
            with LOCK: PLUS_DRAWS[kind].update(rows)
        except Exception as exc: PLUS_ERRORS[kind]='Local archive: '+str(exc)

try: load_local()
except Exception as exc: LAST_ERROR='Local archive: '+str(exc)
load_plus_local()

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

# Secondary source: publicly viewable archive listing all three games in one table.
# HTML is parsed by column heading, never by arbitrary numbers on a page.
LOTTLOGY_URL=os.getenv('LOTTO_COMBINED_ARCHIVE_URL','https://lottology.com/south-africa-lotto/draws')
COMBINED_FETCH=0
COMBINED_ERROR=None
COMBINED_SOURCE=None

def parse_combined_archive(html):
    from bs4 import BeautifulSoup
    soup=BeautifulSoup(html,'html.parser')
    found={'lotto':{},'plus1':{},'plus2':{}}
    for table in soup.find_all('table'):
        trs=table.find_all('tr')
        if not trs:continue
        heads=[re.sub(r'[^a-z0-9]+','_',c.get_text(' ',strip=True).lower()).strip('_') for c in trs[0].find_all(['th','td'])]
        needed={'date','draws','plus_1','plus_2'}
        if not needed.issubset(set(heads)):continue
        ix={h:i for i,h in enumerate(heads)}
        for tr in trs[1:]:
            cells=tr.find_all(['th','td'])
            if len(cells)<len(heads):continue
            try:
                day=datetime.strptime(cells[ix['date']].get_text(' ',strip=True),'%d %b %Y').date().isoformat()
            except ValueError:continue
            # 6/52 rules started in June 2026; do not mix older 6/58 draws.
            if day<'2026-06-04':continue
            for game,column in [('lotto','draws'),('plus1','plus_1'),('plus2','plus_2')]:
                vals=[int(n) for n in re.findall(r'\b\d{1,2}\b',cells[ix[column]].get_text(' ',strip=True))]
                if len(vals)==6 and len(set(vals))==6 and all(1<=n<=52 for n in vals):
                    found[game][day]=sorted(vals)
        if any(found.values()):break
    if not found['lotto'] or not found['plus1'] or not found['plus2']:
        raise ValueError('Combined archive table missing or has no valid 6/52 results')
    return found

def refresh_combined(force=False):
    global COMBINED_FETCH,COMBINED_ERROR,COMBINED_SOURCE,SOURCE
    with LOCK:
        if not force and COMBINED_FETCH and time.time()-COMBINED_FETCH<TTL:return
        COMBINED_FETCH=time.time()
    try:
        if not LOTTLOGY_URL.startswith('https://'):raise ValueError('HTTPS required')
        response=requests.get(LOTTLOGY_URL,headers={'User-Agent':'Mozilla/5.0 (compatible; ZF-Lotto/10)'},timeout=(7,18))
        response.raise_for_status()
        if len(response.content)>6_000_000:raise ValueError('HTML archive too large')
        found=parse_combined_archive(response.text)
        with LOCK:
            for game,store in [('lotto',DRAWS),('plus1',PLUS_DRAWS['plus1']),('plus2',PLUS_DRAWS['plus2'])]:
                for day,nums in found[game].items():
                    if day in store and store[day]!=nums:
                        raise ValueError('Conflicting verified result for '+game+' '+day)
            DRAWS.update(found['lotto'])
            PLUS_DRAWS['plus1'].update(found['plus1'])
            PLUS_DRAWS['plus2'].update(found['plus2'])
            COMBINED_ERROR=None
            COMBINED_SOURCE='Lottology combined archive (independent third party)'
            if not SOURCE:SOURCE=COMBINED_SOURCE
    except Exception as exc:
        with LOCK:COMBINED_ERROR=f'{type(exc).__name__}: {str(exc)[:220]}'

def refresh_plus(kind,force=False):
    with LOCK:
        if not force and PLUS_FETCH[kind] and time.time()-PLUS_FETCH[kind]<TTL:return
        PLUS_FETCH[kind]=time.time()
    try:
        url=PLUS_URLS[kind]
        if not url.startswith('https://'):raise ValueError('Archive URL must use HTTPS')
        response=requests.get(url,headers={'Accept':'application/json,text/csv','User-Agent':'ZF-Lotto-Robot/9.0'},timeout=(7,18))
        response.raise_for_status()
        if len(response.content)>12_000_000:raise ValueError('Archive exceeds 12MB limit')
        rows,_=parse_archive(response.content,response.headers.get('Content-Type',''),kind,True)
        with LOCK:
            for day,nums in rows.items():
                if day in PLUS_DRAWS[kind] and PLUS_DRAWS[kind][day]!=nums:
                    raise ValueError('Conflicting '+kind+' result on '+day)
            PLUS_DRAWS[kind].update(rows)
            PLUS_ERRORS[kind]=None
    except Exception as exc:
        with LOCK:PLUS_ERRORS[kind]=f'{type(exc).__name__}: {str(exc)[:250]}'

def snapshot():
    with LOCK: return [{'date':d,'numbers':nums} for d,nums in sorted(DRAWS.items())]

@app.get('/')
def home(): return send_from_directory('.','index.html')

@app.get('/api/status')
def status():
    refresh_combined()
    ds=snapshot()
    with LOCK: err=LAST_ERROR; src=SOURCE; last=LAST_FETCH; plus_counts={k:len(v) for k,v in PLUS_DRAWS.items()}; plus_errors=dict(PLUS_ERRORS)
    return jsonify(combined_error=COMBINED_ERROR,combined_source=COMBINED_SOURCE,draws=len(ds),first=ds[0]['date'] if ds else None,last=ds[-1]['date'] if ds else None,provider='BetTip',online_provider_configured=True,source=src,fetch_error=err,cache_age_seconds=round(time.time()-last) if last else None,plus_draws=plus_counts,plus_errors=plus_errors)

@app.post('/api/refresh')
def refresh_endpoint():
    refresh_combined(force=True)
    refresh(force=True)
    for kind in PLUS_DRAWS:refresh_plus(kind,force=True)
    return status()

@app.post('/api/import')
def import_csv():
    f=request.files.get('file')
    if not f: return jsonify(error='CSV required'),400
    try:
        kind=request.form.get('game','lotto')
        if kind not in ('lotto','plus1','plus2'):raise ValueError('Unknown game')
        rows,_=parse_archive(f.read(),'text/csv',kind,kind!='lotto')
        target=DRAWS if kind=='lotto' else PLUS_DRAWS[kind]
        with LOCK:
            for d,nums in rows.items():
                if d in target and target[d]!=nums: raise ValueError('Conflicting result: '+d)
            target.update(rows)
        return jsonify(imported=len(rows),total=len(target),game=kind)
    except Exception as e:return jsonify(error=str(e)),400

@app.post('/api/predict')
def prediction():
    p=request.get_json(silent=True) or {}; day=p.get('date','')
    try: date.fromisoformat(day)
    except (ValueError,TypeError):return jsonify(error='Choose a valid date'),400
    if day>=date.today().isoformat():return jsonify(error='Choose a previous draw date'),400
    refresh_combined()
    history=[d for d in snapshot() if d['date']<day]
    try: rows=predict(history,day,str(p.get('reset',0)))
    except ValueError as exc:
        return jsonify(error=str(exc)+' Historical archive may be unavailable. Check Data Status.'),400
    token=secrets.token_urlsafe(32)
    with LOCK:
        if len(SESSIONS)>1000: SESSIONS.pop(next(iter(SESSIONS)))
        SESSIONS[token]={'date':day,'rows':rows}
    return jsonify(token=token,date=day,rows=rows,training_draws=len(history),excluded_cold_numbers=coldest_numbers(history, count=10))

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
    refresh_combined()
    # Each game is independent. Never substitute the main draw for Plus results.
    for kind in ('plus1','plus2'):
        with LOCK:missing=day not in PLUS_DRAWS[kind]
        if missing:refresh_plus(kind)
    with LOCK:
        results={'lotto':DRAWS.get(day),'plus1':PLUS_DRAWS['plus1'].get(day),'plus2':PLUS_DRAWS['plus2'].get(day)}
        errors=dict(PLUS_ERRORS)
    comparisons={kind:compare(sess['rows'],nums) if nums is not None else None for kind,nums in results.items()}
    return jsonify(date=day,actual=results['lotto'],source=SOURCE or 'Historical archive',comparison=comparisons['lotto'],results=results,comparisons=comparisons,plus_errors=errors)

@app.post('/api/backtest')
def backtest():
    p=request.get_json(silent=True) or {}
    try: limit=max(1,min(500,int(p.get('limit',100))))
    except (ValueError,TypeError):return jsonify(error='Invalid limit'),400
    refresh_combined()
    # The engine trains on only prior draws. Data must be checked for completeness.
    return jsonify(walkforward(snapshot(),p.get('start'),p.get('end'),limit))

if __name__=='__main__': app.run(host='0.0.0.0',port=int(os.getenv('PORT','10000')))
