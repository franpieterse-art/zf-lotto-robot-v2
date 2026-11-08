import os, csv, io, json, threading, secrets, re, time
from datetime import date, datetime
from flask import Flask, request, jsonify, send_from_directory
from engine import predict, compare, walkforward
import requests
from bs4 import BeautifulSoup

app = Flask(__name__, static_folder='.', static_url_path='')
LOCK = threading.RLock()
DRAWS = []
SESSIONS = {}
LAST_SYNC = 0
SYNC_ERROR = None
SOURCE = 'https://www.lottery.co.za/lotto/results/'
DATA_FILE = os.environ.get('LOTTO_DATA_FILE', 'draws.csv')
# This archive contains the 6/52 era; earlier years used other matrices.
EARLIEST = date(2026, 6, 1)

def parse_csv(raw):
    if isinstance(raw, bytes): raw = raw.decode('utf-8-sig')
    reader = csv.DictReader(io.StringIO(raw))
    if not reader.fieldnames or not {'date','n1','n2','n3','n4','n5','n6'}.issubset(reader.fieldnames):
        raise ValueError('CSV requires date,n1,n2,n3,n4,n5,n6')
    results = {}
    for row in reader:
        day = row['date'].strip()
        date.fromisoformat(day)
        nums = sorted(int(row[f'n{i}']) for i in range(1,7))
        if len(set(nums)) != 6 or not all(1 <= n <= 52 for n in nums):
            raise ValueError('Invalid 6/52 draw: ' + day)
        if day in results and results[day] != nums:
            raise ValueError('Conflicting draw: ' + day)
        results[day] = nums
    return [{'date': d, 'numbers': n} for d,n in sorted(results.items())]

def merge(new):
    global DRAWS
    with LOCK:
        all_draws = {d['date']: d['numbers'] for d in DRAWS}
        for d in new:
            day = d['date']; nums = d['numbers']
            if day in all_draws and all_draws[day] != nums:
                raise ValueError('Source conflict for ' + day + '; refusing to overwrite')
            all_draws[day] = nums
        DRAWS = [{'date': d, 'numbers': n} for d,n in sorted(all_draws.items())]
        return len(DRAWS)

def scrape_year(year):
    url = SOURCE + str(year)
    response = requests.get(url, timeout=20, headers={'User-Agent':'Mozilla/5.0 (compatible; ZFLottoResearch/6.1)'})
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    found = {}
    for tr in soup.select('tr'):
        cells = tr.find_all(['td','th'], recursive=False)
        if len(cells) < 3: continue
        raw_date = cells[0].get_text(' ', strip=True)
        # Dates on this source are English: Saturday, 7 November 2026.
        match = re.search(r'\b(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})\b', raw_date, re.I)
        if not match: continue
        draw_date = datetime.strptime(' '.join(match.groups()), '%d %B %Y').date()
        if draw_date < EARLIEST or draw_date > date.today() or draw_date.year != year: continue
        # Third cell contains the seven lottery balls (six main + bonus).
        results_text = cells[2].get_text(' ', strip=True)
        balls = [int(x) for x in re.findall(r'(?<!\d)\d{1,2}(?!\d)', results_text)]
        if len(balls) != 7: continue
        main = sorted(balls[:6])
        if len(set(main)) != 6 or not all(1 <= n <= 52 for n in main): continue
        found[draw_date.isoformat()] = main
    if not found:
        raise ValueError(f'No usable 6/52 rows parsed from {url}; website structure may have changed')
    return [{'date': d, 'numbers': n} for d,n in sorted(found.items())]

def sync(force=False):
    global LAST_SYNC, SYNC_ERROR
    with LOCK:
        if not force and DRAWS and time.time()-LAST_SYNC < 21600: return len(DRAWS)
        # Reserve the refresh window to avoid simultaneous requests.
        LAST_SYNC = time.time()
    try:
        combined = []
        errors = []
        for year in range(EARLIEST.year, date.today().year+1):
            try: combined.extend(scrape_year(year))
            except Exception as e: errors.append(str(e))
        if not combined:
            raise ValueError('; '.join(errors) or 'No results found')
        count = merge(combined)
        SYNC_ERROR = '; '.join(errors) if errors else None
        return count
    except Exception as e:
        SYNC_ERROR = str(e)
        raise

if os.path.isfile(DATA_FILE):
    with open(DATA_FILE,'rb') as f: merge(parse_csv(f.read()))

@app.get('/')
def home(): return send_from_directory('.', 'index.html')

@app.get('/api/status')
def status():
    try: sync()
    except Exception: pass
    with LOCK:
        return jsonify(draws=len(DRAWS), first=DRAWS[0]['date'] if DRAWS else None,
                       last=DRAWS[-1]['date'] if DRAWS else None,
                       online_provider_configured=True, source=SOURCE,
                       sync_error=SYNC_ERROR)

@app.post('/api/sync')
def manual_sync():
    try: return jsonify(draws=sync(force=True), source=SOURCE, warning=SYNC_ERROR)
    except Exception as e: return jsonify(error=str(e)), 502

@app.post('/api/import')
def import_draws():
    f = request.files.get('file')
    if not f: return jsonify(error='CSV file required'),400
    try:
        rows = parse_csv(f.read())
        return jsonify(imported=len(rows), total=merge(rows))
    except Exception as e: return jsonify(error=str(e)),400

@app.post('/api/predict')
def prediction():
    p = request.get_json(silent=True) or {}
    day = p.get('date','')
    try: target = date.fromisoformat(day)
    except (ValueError,TypeError): return jsonify(error='Invalid date'),400
    if target >= date.today(): return jsonify(error='Choose a previous draw date'),400
    if target < EARLIEST: return jsonify(error='This version supports the 6/52 era from June 2026 onward; older Lotto matrices must be handled separately.'),400
    try: sync()
    except Exception as e:
        with LOCK:
            if not DRAWS: return jsonify(error='Historical download failed: '+str(e)),502
    with LOCK: history = [d for d in DRAWS if d['date'] < day]
    try: rows = predict(history, day, str(p.get('reset',0)))
    except ValueError as e: return jsonify(error=str(e)+' Available earlier draws: '+str(len(history))),400
    token = secrets.token_urlsafe(24)
    with LOCK:
        SESSIONS[token] = {'date':day,'rows':rows}
        if len(SESSIONS)>1000: SESSIONS.pop(next(iter(SESSIONS)))
    return jsonify(token=token,date=day,rows=rows,training_draws=len(history))

@app.post('/api/reveal')
def reveal():
    token = (request.get_json(silent=True) or {}).get('token','')
    with LOCK: session = SESSIONS.get(token)
    if not session: return jsonify(error='Predict first'),400
    day = session['date']
    with LOCK: actual = next((d['numbers'] for d in DRAWS if d['date']==day),None)
    if actual is None:
        try: sync(force=True)
        except Exception as e: return jsonify(error='Result lookup failed: '+str(e)),502
        with LOCK: actual = next((d['numbers'] for d in DRAWS if d['date']==day),None)
    if actual is None: return jsonify(error='No verified result available for selected date; no numbers invented.'),404
    return jsonify(date=day,actual=actual,source=SOURCE,comparison=compare(session['rows'],actual))

@app.post('/api/backtest')
def backtest():
    p = request.get_json(silent=True) or {}
    try: limit=max(1,min(500,int(p.get('limit',100))))
    except (ValueError,TypeError): return jsonify(error='Invalid limit'),400
    try: sync()
    except Exception as e:
        with LOCK:
            if not DRAWS: return jsonify(error='Historical download failed: '+str(e)),502
    with LOCK: draws=list(DRAWS)
    return jsonify(walkforward(draws,p.get('start'),p.get('end'),limit))

if __name__ == '__main__':
    app.run(host='0.0.0.0',port=int(os.environ.get('PORT','10000')))
