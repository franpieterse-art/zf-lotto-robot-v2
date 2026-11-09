import csv, io, math, random, hashlib
from collections import Counter
from datetime import datetime
from itertools import combinations

MAX_N=52

def parse_csv(data):
    text=data.decode('utf-8-sig') if isinstance(data,bytes) else data
    rows=list(csv.reader(io.StringIO(text)))
    out=[]
    for row in rows:
        if not row: continue
        date=None
        for cell in row:
            s=cell.strip()
            for fmt in ('%Y-%m-%d','%d/%m/%Y','%Y/%m/%d','%d-%m-%Y','%m/%d/%Y'):
                try: date=datetime.strptime(s[:10],fmt).date().isoformat(); break
                except ValueError: pass
            if date: break
        if not date: continue
        nums=[]
        for cell in row:
            s=cell.strip()
            if s.isdigit() and 1<=int(s)<=MAX_N: nums.append(int(s))
        # Date columns and bonus columns are ignored after first six numbers
        nums=nums[:6]
        if len(nums)==6 and len(set(nums))==6: out.append({'date':date,'numbers':sorted(nums)})
    unique={x['date']:x for x in out}
    return sorted(unique.values(),key=lambda x:x['date'])

def features(history):
    n=len(history); counts=Counter(x for d in history for x in d['numbers']); recent=Counter(x for d in history[-20:] for x in d['numbers']); prev=Counter(x for d in history[-60:-20] for x in d['numbers']); last={x:-1 for x in range(1,53)}
    pairs=Counter(p for d in history[-100:] for p in combinations(d['numbers'],2))
    for i,d in enumerate(history):
        for x in d['numbers']:last[x]=i
    return counts,recent,prev,last,pairs

def rank_scores(history,method):
    counts,recent,prev,last,pairs=features(history); n=len(history)
    if method=='random':return {x:0 for x in range(1,53)}
    scores={}
    for x in range(1,53):
        f=counts[x]/max(1,n); m=recent[x]/max(1,min(n,20)); old=prev[x]/max(1,min(max(0,n-20),40)); gap=min(1,(n-1-last[x])/max(1,52/6*2));
        hot=f; cold=1-min(1,f*52/6); momentum=max(0,min(1,.5+(m-old)*3)); trend=min(1,m*52/6); pair=sum(v for p,v in pairs.items() if x in p)/max(1,100*5); pair=min(1,pair*2)
        if method=='weighted':score=.30*hot*52/6+.20*momentum+.15*gap+.15*trend+.10*pair+.10*cold
        elif method=='hot':score=f
        elif method=='cold':score=-f
        elif method=='overdue':score=gap
        elif method=='momentum':score=momentum
        elif method=='adaptive':score=.25*hot*52/6+.15*cold+.15*gap+.20*momentum+.15*trend+.10*pair
        else:score=f
        scores[x]=score
    return scores

def predict(history,method='weighted',seed=0,rows=5,weights=None):
    scores=rank_scores(history,method)
    if method=='adaptive' and weights:
        score_parts={m:rank_scores(history,m) for m in ('weighted','hot','cold','overdue','momentum')}
        scores={x:sum(weights.get(m,0)*score_parts[m][x] for m in score_parts) for x in scores}
    rng=random.Random(seed)
    tickets=[]; used=set()
    for r in range(rows):
        pool=list(range(1,53)); selected=[]
        while len(selected)<6:
            if method=='random':choice=rng.choice(pool)
            else:
                vals=[scores[x] for x in pool]; low=min(vals); adjusted=[math.exp(min(20,(v-low)*4))*(0.15 if x in used else 1) for x,v in zip(pool,vals)]
                choice=rng.choices(pool,weights=adjusted,k=1)[0]
            selected.append(choice);pool.remove(choice)
        ticket=sorted(selected)
        while ticket in tickets:
            selected[-1]=rng.choice([x for x in range(1,53) if x not in selected[:-1]])
            ticket=sorted(selected)
        tickets.append(ticket);used.update(ticket)
    return tickets

def seed_for(date,method):return int(hashlib.sha256((date+method).encode()).hexdigest()[:12],16)

def evaluate(tickets,actual):
    matches=[len(set(t)&set(actual)) for t in tickets]
    return {'best':max(matches),'matches':matches,'three_plus':int(max(matches)>=3),'four_plus':int(max(matches)>=4),'five_plus':int(max(matches)>=5)}

def learn(history,upto,min_train=40, cached_results=None):
    methods=('weighted','hot','cold','overdue','momentum')
    # Select weights using strictly earlier outcomes; no access to test draw.
    start=max(min_train,upto-120); totals={m:0.0 for m in methods}; tested=0
    for i in range(start,upto):
        train=history[:i]; actual=history[i]['numbers']; tested+=1
        for m in methods:
            if cached_results is not None and (i,m) in cached_results:
                value=cached_results[(i,m)]
            else:
                result=evaluate(predict(train,m,seed_for(history[i]['date'],m)),actual)
                value=result['best']+3*result['four_plus']+result['three_plus']
            totals[m]+=value
    if not tested:return {m:1/len(methods) for m in methods}
    raw={m:max(.01,totals[m]/tested) for m in methods}; z=sum(raw.values())
    return {m:v/z for m,v in raw.items()}

def backtest(history,start_date=None,end_date=None,min_train=40,limit=150):
    if len(history)<min_train+1:raise ValueError(f'Need at least {min_train+1} historical draws')
    indices=[i for i in range(min_train,len(history)) if (not start_date or history[i]['date']>=start_date) and (not end_date or history[i]['date']<=end_date)]
    indices=indices[-limit:]
    if not indices:raise ValueError('No eligible draws in selected date range')
    methods=['random','weighted','hot','cold','overdue','momentum','adaptive']; stats={m:{'draws':0,'total_best':0,'three_plus':0,'four_plus':0,'five_plus':0} for m in methods}; detail=[]
    # Precompute each prior outcome once, instead of recalculating the same
    # 120-draw training window for every backtest target.
    cached_results={}
    first=max(min_train,indices[0]-120)
    base_methods=('weighted','hot','cold','overdue','momentum')
    for j in range(first,indices[-1]):
        past=history[:j]; actual=history[j]['numbers']; date=history[j]['date']
        for m in base_methods:
            r=evaluate(predict(past,m,seed_for(date,m)),actual)
            cached_results[(j,m)]=r['best']+3*r['four_plus']+r['three_plus']
    for i in indices:
        target=history[i]; train=history[:i]; weights=learn(history,i,min_train,cached_results) if i>=min_train+5 else None
        rec={'date':target['date'],'actual':target['numbers'],'results':{}}
        for m in methods:
            tickets=predict(train,m,seed_for(target['date'],m),weights=weights)
            result=evaluate(tickets,target['numbers']); rec['results'][m]={'tickets':tickets,**result}
            s=stats[m];s['draws']+=1;s['total_best']+=result['best']
            for k in ('three_plus','four_plus','five_plus'):s[k]+=result[k]
        detail.append(rec)
    for s in stats.values():s['average_best']=round(s.pop('total_best')/s['draws'],3)
    return {'stats':stats,'draws':detail,'notice':'All predictions use earlier draws only. Historical success does not imply future advantage.'}
