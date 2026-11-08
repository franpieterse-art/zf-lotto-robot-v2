"""ZF Lotto V3 prediction research engine. Python 3.10+, standard library only.
Input: list of {'date':'YYYY-MM-DD','numbers':[six distinct integers 1..52]}.
No future draws are used for a target date. Not a guarantee of predictive skill.
"""
from __future__ import annotations
from collections import Counter
from datetime import date
from itertools import combinations
from math import comb
import hashlib, random

N=52

def validate(draws):
    clean=[]; seen=set()
    for d in draws:
        dt=date.fromisoformat(str(d['date'])[:10]); ns=tuple(sorted(map(int,d['numbers'])))
        if len(ns)!=6 or len(set(ns))!=6 or min(ns)<1 or max(ns)>N: raise ValueError('Invalid 6/52 draw: '+str(d))
        if dt in seen: raise ValueError('Duplicate draw date: '+str(dt))
        seen.add(dt); clean.append({'date':dt.isoformat(),'numbers':ns})
    return sorted(clean,key=lambda x:x['date'])

def seed_for(target,tag):
    return int.from_bytes(hashlib.sha256(f'{target}|{tag}'.encode()).digest()[:8],'big')

def score_numbers(history, method):
    if not history: return [1.0]*N
    counts=Counter(n for d in history for n in d['numbers'])
    recent=history[-min(30,len(history)):]
    rcounts=Counter(n for d in recent for n in d['numbers'])
    last={n:len(history) for n in range(1,N+1)}
    for i,d in enumerate(reversed(history)):
        for n in d['numbers']:
            if last[n]==len(history): last[n]=i
    if method=='frequency': raw=[counts[n] for n in range(1,N+1)]
    elif method=='recent': raw=[rcounts[n] for n in range(1,N+1)]
    elif method=='cold': raw=[-counts[n] for n in range(1,N+1)]
    elif method=='overdue': raw=[last[n] for n in range(1,N+1)]
    elif method=='blend':
        raw=[.5*counts[n]/len(history)+.5*rcounts[n]/len(recent) for n in range(1,N+1)]
    else: return [1.0]*N
    lo,hi=min(raw),max(raw)
    if hi==lo:return [1.0]*N
    return [0.4+1.2*(x-lo)/(hi-lo) for x in raw]

def weighted_sample(weights,rng):
    available=list(range(1,N+1)); w=list(weights); result=[]
    for _ in range(6):
        chosen=rng.choices(range(len(available)),weights=w,k=1)[0]
        result.append(available.pop(chosen));w.pop(chosen)
    return tuple(sorted(result))

def predict(history,target,rows=5,method='blend'):
    """Deterministic, reproducible prediction. All history must precede target."""
    if not 1<=rows<=100:raise ValueError('rows must be 1..100')
    if any(d['date']>=target for d in history):raise ValueError('Future-data leakage detected')
    rng=random.Random(seed_for(target,method)); weights=score_numbers(history,method)
    output=[]; used=set()
    for _ in range(rows):
        best=None;best_score=-1e9
        for _ in range(120):
            ticket=weighted_sample(weights,rng)
            if ticket in used:continue
            # Diversify rows without claiming better per-ticket odds.
            overlap=sum(len(set(ticket)&set(prev))**2 for prev in output)
            value=-overlap+rng.random()*.001
            if value>best_score:best,best_score=ticket,value
        if best is None:raise RuntimeError('Could not generate unique rows')
        output.append(best);used.add(best)
    return output

def matches(rows,actual):
    s=set(actual)
    return [len(set(row)&s) for row in rows]

def backtest(draws,start=None,end=None,minimum_history=20,methods=('random','frequency','recent','cold','overdue','blend'),rows=5):
    """Walk-forward evaluation: each test date only sees earlier draws."""
    data=validate(draws)
    results={m:{'tested':0,'total_matches':0,'best_match_histogram':{i:0 for i in range(7)},'rows_3plus':0,'rows_4plus':0} for m in methods}
    for i,d in enumerate(data):
        if i<minimum_history or (start and d['date']<start) or (end and d['date']>end):continue
        history=data[:i]
        for method in methods:
            predicted=predict(history,d['date'],rows,method)
            hits=matches(predicted,d['numbers']); r=results[method]
            r['tested']+=1;r['total_matches']+=sum(hits)
            r['best_match_histogram'][max(hits)]+=1
            r['rows_3plus']+=sum(h>=3 for h in hits)
            r['rows_4plus']+=sum(h>=4 for h in hits)
    for r in results.values():
        r['average_matches_per_row']=round(r['total_matches']/(r['tested']*rows),4) if r['tested'] else None
    return results

def choose_method(draws,target,minimum_history=20,validation_draws=100):
    """Select on a validation period strictly before target; do not select on target outcome."""
    history=[d for d in validate(draws) if d['date']<target]
    if len(history)<minimum_history+10:return 'random',{}
    window=history[-validation_draws:]
    start=window[0]['date']
    results=backtest(history,start=start,minimum_history=minimum_history)
    # Conservative selection: only choose nonrandom if it exceeds random on held-out dates.
    base=results['random']['average_matches_per_row'] or 0
    winner=max(results,key=lambda m:(results[m]['average_matches_per_row'] or -1))
    if winner!='random' and (results[winner]['average_matches_per_row'] or 0)<=base+0.05:
        winner='random'
    return winner,results

def prediction_for_date(draws,target,rows=5):
    history=[d for d in validate(draws) if d['date']<target]
    if len(history)<20:raise ValueError(f'Only {len(history)} prior draws available; at least 20 required')
    method,validation=choose_method(history,target)
    return {'date':target,'method':method,'training_draws':len(history),'predictions':[list(x) for x in predict(history,target,rows,method)],'validation':validation,'actual_numbers':None}

if __name__=='__main__':
    print('ZF Lotto V3 module ready. Import prediction_for_date(draws, target).')
    print('Jackpot probability per unique row: 1 in',comb(52,6))
