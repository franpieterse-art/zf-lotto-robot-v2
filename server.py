from flask import Flask,request,jsonify,send_from_directory
from engine import parse_csv,predict,seed_for,evaluate,backtest,learn
import os
app=Flask(__name__)
DATA=os.environ.get('LOTTO_CSV','za_lotto.csv')
def history():
    if not os.path.exists(DATA):return []
    with open(DATA,'rb') as f:return parse_csv(f.read())
@app.get('/')
def home():return send_from_directory('.','index.html')
@app.get('/api/status')
def status():
    h=history();return jsonify(draws=len(h),first=h[0]['date'] if h else None,last=h[-1]['date'] if h else None)
@app.post('/api/upload')
def upload():
    f=request.files.get('file')
    if not f:return jsonify(error='CSV file required'),400
    raw=f.read();h=parse_csv(raw)
    if len(h)<41:return jsonify(error='Need at least 41 valid dated draws with six numbers (1–52).'),400
    with open(DATA,'wb') as dest:dest.write(raw)
    return jsonify(draws=len(h),first=h[0]['date'],last=h[-1]['date'])
@app.post('/api/predict')
def make_prediction():
    data=request.get_json() or {};date=data.get('date');method=data.get('method','adaptive');h=history()
    if method not in ('random','weighted','hot','cold','overdue','momentum','adaptive'):return jsonify(error='Invalid method'),400
    if not date:return jsonify(error='Choose a date'),400
    prior=[d for d in h if d['date']<date]
    if len(prior)<40:return jsonify(error='Need at least 40 draws before the selected date'),400
    weights=learn(h,len(prior)) if method=='adaptive' else None
    tickets=predict(prior,method,seed_for(date,method),weights=weights)
    return jsonify(date=date,method=method,tickets=tickets,training_draws=len(prior),weights=weights,has_actual=any(d['date']==date for d in h))
@app.post('/api/reveal')
def reveal():
    data=request.get_json() or {};date=data.get('date');h=history();actual=next((d['numbers'] for d in h if d['date']==date),None)
    if actual is None:return jsonify(error='No result recorded for this date'),404
    method=data.get('method','adaptive');prior=[d for d in h if d['date']<date]
    if len(prior)<40:return jsonify(error='Insufficient history'),400
    weights=learn(h,len(prior)) if method=='adaptive' else None
    tickets=predict(prior,method,seed_for(date,method),weights=weights)
    return jsonify(actual=actual,tickets=tickets,**evaluate(tickets,actual))
@app.post('/api/backtest')
def run_backtest():
    data=request.get_json() or {}
    try:return jsonify(backtest(history(),data.get('start'),data.get('end'),limit=min(300,max(1,int(data.get('limit',60))))))
    except (ValueError,TypeError) as e:return jsonify(error=str(e)),400
    except Exception:
        app.logger.exception('Backtest failed')
        return jsonify(error='Backtest failed on the server. Check Render Logs for the traceback.'),500
if __name__=='__main__':app.run(host='0.0.0.0',port=int(os.environ.get('PORT',5000)))
