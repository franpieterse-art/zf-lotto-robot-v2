import os,csv,io,json,threading,urllib.request
from datetime import date
from flask import Flask,request,jsonify,send_from_directory
from engine import predict,compare,walkforward
app=Flask(__name__,static_folder='.',static_url_path='')
LOCK=threading.RLock(); DRAWS=[]; SESSIONS={}
DATA_FILE=os.environ.get('LOTTO_DATA_FILE','draws.csv')

def parse_csv(data):
    text=data.decode('utf-8-sig') if isinstance(data,bytes) else data
    reader=csv.DictReader(io.StringIO(text)); out={}
    if not reader.fieldnames:raise ValueError('CSV must have headers: date,n1,n2,n3,n4,n5,n6')
    for row in reader:
        day=row['date'].strip(); date.fromisoformat(day)
        nums=sorted(int(row[f'n{i}']) for i in range(1,7))
        if len(set(nums))!=6 or not all(1<=n<=52 for n in nums):raise ValueError('Invalid six-number draw on '+day)
        if day in out and out[day]!=nums:raise ValueError('Conflicting results for '+day)
        out[day]=nums
    return [{'date':k,'numbers':v} for k,v in sorted(out.items())]

def load():
    global DRAWS
    if os.path.isfile(DATA_FILE):
        with open(DATA_FILE,'rb') as f:DRAWS=parse_csv(f.read())
load()

@app.get('/')
def home():return send_from_directory('.','index.html')
@app.get('/api/status')
def status():
    with LOCK:return jsonify({'draws':len(DRAWS),'first':DRAWS[0]['date'] if DRAWS else None,'last':DRAWS[-1]['date'] if DRAWS else None,'online_provider_configured':bool(os.environ.get('LOTTO_RESULTS_URL_TEMPLATE'))})
@app.post('/api/import')
def import_draws():
    global DRAWS
    f=request.files.get('file')
    if not f:return jsonify(error='CSV file required'),400
    try:
        new=parse_csv(f.read());
        with LOCK:
            existing={d['date']:d['numbers'] for d in DRAWS}
            for d in new:
                if d['date'] in existing and existing[d['date']]!=d['numbers']:raise ValueError('Conflicting draw: '+d['date'])
                existing[d['date']]=d['numbers']
            DRAWS=[{'date':k,'numbers':v} for k,v in sorted(existing.items())]
        return jsonify(imported=len(new),total=len(DRAWS))
    except Exception as e:return jsonify(error=str(e)),400

def fetch_date(day):
    # Explicitly configured trusted provider. URL must return JSON with date and six numbers.
    template=os.environ.get('LOTTO_RESULTS_URL_TEMPLATE','')
    if not template:return None
    url=template.replace('{date}',day)
    if not url.startswith('https://'):raise ValueError('Provider URL must use HTTPS')
    req=urllib.request.Request(url,headers={'Accept':'application/json','User-Agent':'ZF-Lotto-V6/1.0'})
    with urllib.request.urlopen(req,timeout=12) as resp:
        payload=json.load(resp)
    if payload.get('date')!=day:raise ValueError('Provider returned a different draw date')
    nums=sorted(int(n) for n in payload['numbers'])
    if len(nums)!=6 or len(set(nums))!=6 or not all(1<=n<=52 for n in nums):raise ValueError('Invalid provider result')
    return nums

@app.post('/api/predict')
def prediction():
    payload=request.get_json(silent=True) or {}; day=payload.get('date','')
    try:date.fromisoformat(day)
    except ValueError:return jsonify(error='Invalid date'),400
    if day>=date.today().isoformat():return jsonify(error='Choose a past draw date'),400
    with LOCK: history=[d for d in DRAWS if d['date']<day]
    try: rows=predict(history,day,str(payload.get('reset',0)))
    except ValueError as e:return jsonify(error=str(e)+' Import historical results or configure a verified data feed.'),400
    import secrets
    token=secrets.token_urlsafe(24)
    with LOCK:
        SESSIONS[token]={'date':day,'rows':rows}
        if len(SESSIONS)>1000:SESSIONS.pop(next(iter(SESSIONS)))
    return jsonify(token=token,date=day,rows=rows,training_draws=len(history))

@app.post('/api/reveal')
def reveal():
    token=(request.get_json(silent=True) or {}).get('token','')
    with LOCK:session=SESSIONS.get(token)
    if not session:return jsonify(error='Predict first; prediction token missing'),400
    day=session['date']
    with LOCK:match=next((d['numbers'] for d in DRAWS if d['date']==day),None)
    source='Imported historical archive'
    if match is None:
        try:match=fetch_date(day);source='Configured online results provider'
        except Exception as e:return jsonify(error='Online results lookup failed: '+str(e)),502
    if match is None:return jsonify(error='Result not available for this date. Configure a verified online provider or import a historical archive. No result was invented.'),404
    return jsonify(date=day,actual=match,source=source,comparison=compare(session['rows'],match))

@app.post('/api/backtest')
def backtest():
    p=request.get_json(silent=True) or {}
    try:limit=max(1,min(500,int(p.get('limit',100))))
    except ValueError:return jsonify(error='Invalid limit'),400
    with LOCK:draws=list(DRAWS)
    return jsonify(walkforward(draws,p.get('start'),p.get('end'),limit))

if __name__=='__main__':
    app.run(host='0.0.0.0',port=int(os.environ.get('PORT','10000')))
