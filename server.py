import csv, io, os, re, time, secrets, threading
from datetime import date, datetime
from flask import Flask, request, jsonify, send_from_directory
import requests
import storage
from engine import predict, compare, walkforward, v29_scores, prediction_diagnostics, _learned_weights, feedback_repredict

app = Flask(__name__, static_folder='.', static_url_path='')
LOCK = threading.RLock()
DRAWS = {}
PLUS_DRAWS = {"plus1": {}, "plus2": {}}
MAX_DRAWS = {}
BONUS = {"lotto":{},"plus1":{},"plus2":{},"max5":{}}
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
    for fmt in ('%Y-%m-%d','%Y/%m/%d','%d/%m/%Y','%d-%m-%Y','%d %b %Y','%d %B %Y'):
        try: return datetime.strptime(s if '%b' in fmt or '%B' in fmt else s[:10],fmt).date().isoformat()
        except ValueError: pass
    raise ValueError('Unrecognized draw date: '+s[:30])

def parse_numbers(record):
    if isinstance(record,dict):
        for key in ('numbers','winning_numbers','winningNumbers','main_numbers','mainNumbers','balls','results','winningNumbersMain'):
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
        for key in ('data','draws','results','items','history'):
            if key in payload:
                val=payload[key]
                if isinstance(val,list): return val
                if isinstance(val,dict): return extract_records(val)
    raise ValueError('Unknown BetTip archive response shape')

def game_kind(record):
    value=str(record.get('game',record.get('gameName',record.get('game_name',record.get('lottery','lotto'))))).lower()
    value=re.sub(r'[^a-z0-9]+',' ',value).strip()
    if 'daily' in value or 'powerball' in value or '5 max' in value:return None
    if re.search(r'(?:plus|pl)\s*2\b',value):return 'plus2'
    if re.search(r'(?:plus|pl)\s*1\b',value):return 'plus1'
    if value in ('lotto','sa lotto','south african lotto','national lotto','national lottery lotto'):return 'lotto'
    return None

def validate_record(record,expected_game='lotto',allow_unlabelled=False):
    if not isinstance(record,dict): raise ValueError('Draw is not an object')
    kind=game_kind(record)
    if allow_unlabelled and kind=='lotto' and not any(k in record for k in ('game','game_name','lottery')):
        kind=expected_game
    if kind!=expected_game:return None
    day=normalized_date(record.get('date',record.get('draw_date',record.get('drawDate'))))
    # Accept the uploaded historical Main LOTTO archive across historical number ranges.
    nums=sorted(parse_numbers(record))
    if len(nums)!=6 or len(set(nums))!=6 or not all(1<=n<=58 for n in nums):
        raise ValueError('Invalid six-number draw for '+day)
    return day,nums

def parse_archive(raw,content_type='',expected_game='lotto',allow_unlabelled=False):
    text=raw.decode('utf-8-sig') if isinstance(raw,bytes) else raw
    if 'csv' in content_type or (text.lstrip().lower().startswith('date,')):
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
    path=os.getenv('LOTTO_DATA_FILE','za_lotto.csv')
    if not os.path.isfile(path): return
    with open(path,'rb') as f: rows,_=parse_archive(f.read(),'text/csv')
    with LOCK:
        DRAWS.update(rows)
        try: storage.save('lotto',rows,'local CSV')
        except ValueError: pass  # bundled CSV is authoritative if old SQLite differs
        global SOURCE
        SOURCE='Local verified CSV (user supplied)'

def load_plus_local():
    for kind,filename in [('plus1','draws_plus1.csv'),('plus2','draws_plus2.csv')]:
        if not os.path.isfile(filename):continue
        try:
            with open(filename,'rb') as f:
                rows,_=parse_archive(f.read(),'text/csv',kind,True)
            with LOCK:
                PLUS_DRAWS[kind].update(rows)
                try: storage.save(kind,rows,'local CSV')
                except ValueError: pass  # preserve user-supplied archive in memory
        except Exception as exc: PLUS_ERRORS[kind]='Local archive: '+str(exc)

def load_max_local():
    filename='draws_5max.csv'
    if not os.path.isfile(filename): return
    with open(filename,'rb') as f: rows,_=parse_archive(f.read(),'text/csv','lotto')
    with LOCK: MAX_DRAWS.update(rows)

def load_bonuses():
    for kind,filename in [('lotto','za_lotto.csv'),('plus1','draws_plus1.csv'),('max5','draws_5max.csv')]:
        if not os.path.isfile(filename): continue
        with open(filename,encoding='utf-8-sig',newline='') as f:
            for row in csv.DictReader(f):
                try:
                    day=normalized_date(row['date'])
                    if kind=='lotto' and day not in DRAWS: continue
                    if kind=='plus1' and day not in PLUS_DRAWS['plus1']: continue
                    if kind=='max5' and day not in MAX_DRAWS: continue
                    BONUS[kind][day]=int(row['bonus'])
                except (ValueError,KeyError,TypeError): pass

# Load cached results before making any external network requests.
try:
    cached=storage.load()
    DRAWS.update(cached['lotto'])
    for kind in PLUS_DRAWS: PLUS_DRAWS[kind].update(cached[kind])
    if any(cached.values()): SOURCE='SQLite historical cache'
except Exception as exc: LAST_ERROR='Database: '+str(exc)

try: load_local()
except Exception as exc: LAST_ERROR='Local archive: '+str(exc)
load_plus_local()
try: load_max_local(); load_bonuses()
except Exception as exc: LAST_ERROR="Local 5 MAX / bonus: "+str(exc)

def refresh(force=False):
    """Load BetTip's documented mixed South African lottery archive once.

    The API wraps draws under `data`; each row has a `game` slug.
    Only Lotto/Plus 1/Plus 2 six-number records are accepted.
    """
    global LAST_FETCH,LAST_ERROR,SOURCE
    with LOCK:
        if not force and LAST_FETCH and time.time()-LAST_FETCH<TTL:return
        LAST_FETCH=time.time()
    try:
        if not BETTIP_URL.startswith('https://'):raise ValueError('Archive URL must be HTTPS')
        response=requests.get(BETTIP_URL,headers={'Accept':'application/json','User-Agent':'ZF-Lotto-Robot/19 (+https://bettip.co.za/)'},timeout=(8,30))
        response.raise_for_status()
        if len(response.content)>20_000_000:raise ValueError('Archive exceeds 20MB safety limit')
        import json
        records=extract_records(response.json())
        found={'lotto':{},'plus1':{},'plus2':{}}
        for record in records:
            if not isinstance(record,dict):continue
            kind=game_kind(record)
            if kind not in found:continue
            try:item=validate_record(record,kind)
            except (ValueError,TypeError,KeyError):continue
            if not item:continue
            day,nums=item
            if day in found[kind] and found[kind][day]!=nums:
                raise ValueError('BetTip conflicting '+kind+' draw on '+day)
            found[kind][day]=nums
        if not any(found.values()):raise ValueError('BetTip returned no valid Lotto/Plus draws; inspect archive schema')
        with LOCK:
            for kind,rows in found.items():
                store=DRAWS if kind=='lotto' else PLUS_DRAWS[kind]
                for day,nums in rows.items():
                    if day in store and store[day]!=nums:
                        raise ValueError('Source conflict for '+kind+' '+day+'; existing record preserved')
            for kind,rows in found.items():
                if not rows:continue
                storage.save(kind,rows,'BetTip API')
                (DRAWS if kind=='lotto' else PLUS_DRAWS[kind]).update(rows)
                if kind!='lotto':PLUS_ERRORS[kind]=None
            LAST_ERROR=None
            SOURCE='BetTip SA Lotto historical API (third-party)'
    except Exception as exc:
        with LOCK:LAST_ERROR=f'{type(exc).__name__}: {str(exc)[:250]}'

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
                day=normalized_date(cells[ix['date']].get_text(' ',strip=True))
            except ValueError:continue
            # 6/52 rules started in June 2026; do not mix older 6/58 draws.
            if day<'2026-06-04':continue
            for game,column in [('lotto','draws'),('plus1','plus_1'),('plus2','plus_2')]:
                vals=[int(n) for n in re.findall(r'\b\d{1,2}\b',cells[ix[column]].get_text(' ',strip=True))]
                if len(vals)==6 and len(set(vals))==6 and all(1<=n<=52 for n in vals):
                    found[game][day]=sorted(vals)
        if any(found.values()):break
    if not any(found.values()):
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
            for game,rows in found.items():storage.save(game,rows,'Lottology')
            DRAWS.update(found['lotto'])
            PLUS_DRAWS['plus1'].update(found['plus1'])
            PLUS_DRAWS['plus2'].update(found['plus2'])
            COMBINED_ERROR=None
            COMBINED_SOURCE='Lottology combined archive (independent third party)'
            if not SOURCE:SOURCE=COMBINED_SOURCE
    except Exception as exc:
        with LOCK:COMBINED_ERROR=f'{type(exc).__name__}: {str(exc)[:220]}'

def refresh_plus(kind,force=False):
    # BetTip documents ONE mixed lotto/draws.json feed, not separate Plus URLs.
    refresh(force=force)
    with LOCK:
        if not PLUS_DRAWS[kind]:
            PLUS_ERRORS[kind]='No '+kind+' records in the BetTip archive. This API may not cover the game.'

def refresh_pages(force=False):
    """Optional page URL templates: use {page} and configure max pages explicitly.

    Supports per-game JSON or CSV archive pages. Never guesses undocumented endpoints.
    """
    global SOURCE
    errors={}; totals={}
    maxpages=max(1,min(500,int(os.getenv('LOTTO_ARCHIVE_MAX_PAGES','30'))))
    for game in ('lotto','plus1','plus2'):
        template=os.getenv('LOTTO_'+game.upper()+'_PAGED_URL','')
        if not template:continue
        if not template.startswith('https://') or '{page}' not in template:
            errors[game]='URL must be HTTPS and include {page}';continue
        total=0
        for page in range(1,maxpages+1):
            try:
                response=requests.get(template.format(page=page),timeout=(6,16),headers={'User-Agent':'ZF-Lotto-Robot/13'})
                if response.status_code in (404,410):break
                response.raise_for_status()
                if len(response.content)>12_000_000:raise ValueError('Page exceeds size limit')
                rows,_=parse_archive(response.content,response.headers.get('Content-Type',''),game,True)
                store=DRAWS if game=='lotto' else PLUS_DRAWS[game]
                with LOCK:
                    storage.save(game,rows,'Configured paged archive');store.update(rows)
                total+=len(rows)
                if len(rows)==0:break
            except Exception as exc:
                errors[game]=f'Page {page}: {str(exc)[:140]}';break
        totals[game]=total
        if total:SOURCE='SQLite cache + configured paged archive'
    return {'downloaded':totals,'errors':errors}

def training_era(day):
    # Conservative year-based splits: do not mix 6/49, 6/52, and 6/58 datasets.
    # Boundaries must be confirmed against official rules before treating backtests as definitive.
    if day < '2017-01-01': return ('2015-01-01','2017-01-01',49)
    if day < '2026-06-01': return ('2017-01-01','2026-06-01',58)
    return ('2026-06-01','9999-12-31',52)

def training_history(day):
    """Use ALL stored, verified Main LOTTO draws before the chosen date.

    Older draws with different ball ranges are retained as historical
    observations. The prediction engine scores only balls eligible for
    the selected date; never use a draw on/after the target date.
    """
    return [d for d in snapshot() if d['date'] < day]


def snapshot():
    with LOCK: return [{'date':d,'numbers':nums} for d,nums in sorted(DRAWS.items())]

@app.get('/')
def home(): return send_from_directory('.','index.html')

@app.get('/api/status')
def status():
    ds=snapshot()
    with LOCK: err=LAST_ERROR; src=SOURCE; last=LAST_FETCH; plus_counts={k:len(v) for k,v in PLUS_DRAWS.items()}; plus_errors=dict(PLUS_ERRORS)
    return jsonify(minimum_training_draws=12,bet_tip_endpoint=BETTIP_URL,bet_tip_last_attempt=LAST_FETCH or None,combined_error=COMBINED_ERROR,combined_source=COMBINED_SOURCE,draws=len(ds),first=ds[0]['date'] if ds else None,last=ds[-1]['date'] if ds else None,provider='BetTip mixed SA archive',online_provider_configured=True,source=src,fetch_error=err,cache_age_seconds=round(time.time()-last) if last else None,plus_draws=plus_counts,max5_draws=len(MAX_DRAWS),plus_errors=plus_errors,database=storage.DB,persistent_disk_configured=storage.DB.startswith('/var/data/'),historical_rules='All stored Main LOTTO draws strictly before the selected date are used. Historical ball ranges may differ; results across rule changes are not directly comparable.')

@app.post('/api/refresh')
def refresh_endpoint():
    refresh(force=True)
    refresh_combined(force=True)
    for kind in PLUS_DRAWS:refresh_plus(kind,force=False)
    pages=refresh_pages(force=True)
    response=status().get_json();response['paged_download']=pages;response['diagnostic']='Downloaded counts reflect only validated records; inspect fetch_error and combined_error. Plus 2 is not confirmed supported by BetTip.'
    return jsonify(response)

@app.get('/api/data-health')
def data_health():
    with LOCK:
        stores={'lotto':dict(DRAWS),'plus1':dict(PLUS_DRAWS['plus1']),'plus2':dict(PLUS_DRAWS['plus2'])}
    report={}
    for game,rows in stores.items():
        dates=sorted(rows)
        report[game]={'count':len(dates),'first':dates[0] if dates else None,'last':dates[-1] if dates else None,
                      'pre_2026_06_04':sum(d<'2026-06-04' for d in dates),
                      'note':'Coverage counts are not proof of completeness or official verification.'}
    return jsonify(games=report,source_errors={'combined':COMBINED_ERROR,'main':LAST_ERROR,**PLUS_ERRORS},database=storage.DB,persistence_note='Render free filesystem is ephemeral. Configure a persistent disk or commit exported CSV files.')

@app.get('/api/export/<game>')
def export_history(game):
    if game not in ('lotto','plus1','plus2'):return jsonify(error='Unknown game'),400
    with LOCK: rows=dict(DRAWS if game=='lotto' else PLUS_DRAWS[game])
    output=io.StringIO();writer=csv.writer(output);writer.writerow(['date','n1','n2','n3','n4','n5','n6'])
    for day,nums in sorted(rows.items()):writer.writerow([day,*nums])
    from flask import Response
    return Response(output.getvalue(),mimetype='text/csv',headers={'Content-Disposition':f'attachment; filename=zf_{game}_history.csv'})

@app.post('/api/import')
def import_csv():
    f=request.files.get('file')
    if not f: return jsonify(error='CSV required'),400
    try:
        kind=request.form.get('game','lotto')
        if kind not in ('lotto','plus1','plus2'):raise ValueError('Unknown game')
        if f.content_length and f.content_length>5_000_000: raise ValueError('CSV exceeds 5 MB')
        content=f.read(5_000_001)
        if len(content)>5_000_000: raise ValueError('CSV exceeds 5 MB')
        rows,_=parse_archive(content,'text/csv',kind,kind!='lotto')
        target=DRAWS if kind=='lotto' else PLUS_DRAWS[kind]
        with LOCK:
            for d,nums in rows.items():
                if d in target and target[d]!=nums: raise ValueError('Conflicting result: '+d)
            storage.save(kind,rows,'CSV upload'); target.update(rows)
        return jsonify(imported=len(rows),total=len(target),game=kind)
    except Exception as e:return jsonify(error=str(e)),400

@app.post('/api/predict')
def prediction():
    p=request.get_json(silent=True) or {}; day=p.get('date','')
    try: date.fromisoformat(day)
    except (ValueError,TypeError):return jsonify(error='Choose a valid date'),400
    if day>=date.today().isoformat():return jsonify(error='Choose a previous draw date'),400
    # Never block a prediction on a third-party site. Use cached/local draws.
    history=training_history(day)
    if len(history)<12:
        return jsonify(error=f'Only {len(history)} earlier Main LOTTO draws are stored for {day}; 12 are required. Import additional verified earlier results or select a later date. Data coverage is not the same as data completeness.', earlier_draws=len(history),required=12),400
    try: rows=predict(history,day,str(p.get('reset',0)),ball_max=training_era(day)[2])
    except ValueError as exc:
        return jsonify(error=str(exc)+' Historical archive may be unavailable. Check Data Status.'),400
    token=secrets.token_urlsafe(32)
    with LOCK:
        if len(SESSIONS)>1000: SESSIONS.pop(next(iter(SESSIONS)))
        SESSIONS[token]={'date':day,'rows':rows,'original_rows':rows,'training_draws':len(history),'iteration':0,'revealed':False}
    return jsonify(token=token,date=day,rows=rows,training_draws=len(history),all_numbers_allowed=True,eligible_numbers=list(range(1,training_era(day)[2]+1)),model_validation={'formula':'V37 past-only calibrated evidence weighting and ten-row diversity','learned_weights':_learned_weights(history,training_era(day)[2])},limited_history=len(history)<25)

@app.post('/api/reveal')
def reveal():
    token=(request.get_json(silent=True) or {}).get('token','')
    with LOCK: sess=SESSIONS.get(token)
    if not sess:return jsonify(error='Predict first'),400
    day=sess['date']
    with LOCK: sess['revealed']=True
    with LOCK: actual=DRAWS.get(day)
    if actual is None:
        with LOCK: actual=DRAWS.get(day)
    # Reveal reads cached results immediately; online sync is explicit via Retry.
    # Each game is independent. Never substitute the main draw for Plus results.
    for kind in ('plus1','plus2'):
        with LOCK:missing=day not in PLUS_DRAWS[kind]
        # Missing results remain unavailable until a separate refresh succeeds.
        pass
    with LOCK:
        results={'lotto':DRAWS.get(day),'plus1':PLUS_DRAWS['plus1'].get(day),'plus2':PLUS_DRAWS['plus2'].get(day),'max5':MAX_DRAWS.get(day)}
        errors=dict(PLUS_ERRORS)
    comparisons={kind:compare(sess['rows'],nums) if nums is not None else None for kind,nums in results.items()}
    # Display ONE third panel, preserving the true underlying game identity.
    # Do not relabel 5 MAX results as historical PLUS 2 data.
    third_key = 'plus2' if results['plus2'] is not None else ('max5' if results['max5'] is not None else 'plus2')
    diagnostics=prediction_diagnostics(training_history(day),sess['rows'],results['lotto'],training_era(day)[2]) if results['lotto'] is not None else None
    return jsonify(date=day,actual=results['lotto'],source=SOURCE or 'Historical archive',comparison=comparisons['lotto'],results=results,comparisons=comparisons,plus_errors=errors,bonuses={k:BONUS[k].get(day) for k in results},third_game=third_key,learning_diagnostics=diagnostics)



@app.post('/api/learn-repredict')
def learn_repredict():
    token=(request.get_json(silent=True) or {}).get('token','')
    with LOCK: sess=SESSIONS.get(token)
    if not sess:return jsonify(error='Predict and Reveal first'),400
    if not sess.get('revealed'):return jsonify(error='Click Reveal before learning'),400
    day=sess['date']
    with LOCK: actual=DRAWS.get(day)
    if actual is None:return jsonify(error='Verified Main LOTTO result is not stored for this date'),400
    with LOCK:
        iteration=sess.get('iteration',0)+1
        if iteration>20:return jsonify(error='Maximum 20 retrospective iterations per prediction; start a new session'),400
        earlier=sess['rows']
        updated=feedback_repredict(training_history(day),day,earlier,actual,iteration,training_era(day)[2])
        sess['rows']=updated
        sess['iteration']=iteration
    return jsonify(date=day,rows=updated,iteration=iteration,
                   comparisons=compare(updated,actual),
                   diagnostics=prediction_diagnostics(training_history(day),updated,actual,training_era(day)[2]),
                   hindsight=True,warning='These revised rows use the revealed winning numbers. They are retrospective experiments, NOT valid blind predictions or evidence of improved future accuracy.')

@app.post('/api/backtest')
def backtest():
    p=request.get_json(silent=True) or {}
    try: limit=max(1,min(500,int(p.get('limit',100))))
    except (ValueError,TypeError):return jsonify(error='Invalid limit'),400
    # No external HTTP calls in backtesting.
    # The engine trains on only prior draws. Data must be checked for completeness.
    return jsonify(walkforward(snapshot(),p.get('start'),p.get('end'),limit,training_era))

if __name__=='__main__': app.run(host='0.0.0.0',port=int(os.getenv('PORT','10000')))
