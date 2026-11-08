import os, json, urllib.request, urllib.error, datetime, random, hashlib
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse,parse_qs
from functools import lru_cache
BASE='https://resultsza.co.za/api/get_lotto_results'
KEY=os.environ.get('RESULTSZA_API_KEY','')
START=datetime.date(2015,1,3)
def fetch(date):
    if not KEY: raise RuntimeError('RESULTSZA_API_KEY is not configured on Render')
    url=BASE+'?api_key='+__import__('urllib.parse',fromlist=['quote']).quote(KEY)+'&date='+date.isoformat()
    try:
        with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'ZF-Lotto-Historical-Research/1.0'}),timeout=12) as resp:
            obj=json.load(resp)
    except urllib.error.HTTPError as e:
        if e.code==404:return None
        raise RuntimeError('Results provider HTTP '+str(e.code))
    rows=obj.get('results') or []
    if not rows:return None
    r=rows[0]; nums=r.get('winning_numbers')
    if not isinstance(nums,list) or len(nums)!=6:raise RuntimeError('Unexpected provider response')
    nums=[int(n) for n in nums]
    if len(set(nums))!=6 or min(nums)<1 or max(nums)>58:raise RuntimeError('Invalid provider numbers')
    return {'date':date.isoformat(),'numbers':sorted(nums),'bonus':r.get('bonus_ball'),'source':'ResultsZA API'}
@lru_cache(maxsize=12000)
def cached(date):return fetch(date)
def prior_dates(d,count=80):
    # Wednesday=2, Saturday=5; draw days in modern era.
    result=[];cur=d-datetime.timedelta(days=1)
    while len(result)<count and cur>=START:
        if cur.weekday() in (2,5):result.append(cur)
        cur-=datetime.timedelta(days=1)
    return result
class Handler(SimpleHTTPRequestHandler):
    def reply(self,status,data):
        payload=json.dumps(data).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(payload)));self.end_headers();self.wfile.write(payload)
    def do_GET(self):
        u=urlparse(self.path)
        if u.path not in ('/api/predict','/api/reveal'):return super().do_GET()
        try:
            s=parse_qs(u.query).get('date',[''])[0];d=datetime.date.fromisoformat(s)
            if d>=datetime.date.today() or d<START:raise ValueError('Choose a past date on or after 2015-01-03')
            if d.weekday() not in (2,5):raise ValueError('Choose a Wednesday or Saturday draw date')
            if u.path=='/api/reveal':
                row=cached(d)
                return self.reply(200,{'result':row,'message':None if row else 'No result available for this date'})
            history=[];errors=0
            for pd in prior_dates(d):
                try:
                    r=cached(pd)
                    if r:history.append(r)
                except Exception:errors+=1
            if len(history)<20:raise RuntimeError('Only '+str(len(history))+' prior draws available; at least 20 required. Check provider/API key.')
            # Use only historical data before selected date. Weighted recency + frequency heuristic.
            counts={i:0.0 for i in range(1,53 if d>=datetime.date(2026,6,1) else 59)}
            for age,r in enumerate(history):
                for n in r['numbers']:
                    if n in counts:counts[n]+=1.0+0.4/(1+age/15)
            ranking=sorted(counts,key=lambda n:(-counts[n],hashlib.sha256((s+':'+str(n)).encode()).hexdigest()))
            nums=sorted(ranking[:6]);token=hashlib.sha256((s+':'+','.join(map(str,nums))).encode()).hexdigest()[:16]
            return self.reply(200,{'date':s,'numbers':nums,'training_draws':len(history),'latest_training_date':history[0]['date'],'prediction_id':token,'method':'Frequency and recency heuristic; not proven to outperform random selection'})
        except ValueError as e:self.reply(400,{'error':str(e)})
        except Exception as e:self.reply(503,{'error':str(e)})
if __name__=='__main__':
    port=int(os.environ.get('PORT','10000'));ThreadingHTTPServer(('0.0.0.0',port),Handler).serve_forever()
