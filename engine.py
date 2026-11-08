import math, random, hashlib
from collections import Counter
from datetime import date
N=52

def seed_for(draw_date, strategy, salt=''):
    return int(hashlib.sha256(f'{draw_date}|{strategy}|{salt}'.encode()).hexdigest()[:16],16)

def features(history):
    windows=[10,30,80,200]
    feats={}
    for n in range(1,N+1):
        gap=next((i for i,d in enumerate(reversed(history)) if n in d['numbers']),len(history))
        freqs=[sum(n in d['numbers'] for d in history[-w:])/max(1,min(w,len(history))) for w in windows]
        feats[n]=[1.,*freqs,min(gap,100)/100]
    return feats

def ml_scores(history):
    # Online logistic model: training examples are constructed only from preceding draws.
    # Every training target is the next observed draw, never the selected test draw.
    if len(history)<25: return {n:0. for n in range(1,N+1)}
    weights=[-2.1,0,0,0,0,0]
    start=max(12,len(history)-80)
    for epoch in range(1):
        for i in range(start,len(history)):
            f=features(history[:i]); actual=set(history[i]['numbers'])
            for n in range(1,N+1):
                x=f[n]; z=max(-20,min(20,sum(a*b for a,b in zip(weights,x))))
                p=1/(1+math.exp(-z)); error=(int(n in actual)-p)
                for j in range(len(weights)):weights[j]+=0.009*(error*x[j]-0.001*weights[j])
    f=features(history)
    return {n:sum(a*b for a,b in zip(weights,f[n])) for n in f}

def score_sets(history):
    fs=features(history); total=len(history)
    counts=Counter(n for d in history for n in d['numbers'])
    pair=Counter()
    for d in history[-150:]:
        a=d['numbers']
        for i in range(6):
            for j in range(i+1,6):pair[(a[i],a[j])]+=1
    frequency={n:2*fs[n][1]+fs[n][2]+0.5*fs[n][3] for n in fs}
    gap={n:fs[n][1]+fs[n][2]+0.35*fs[n][5] for n in fs}
    pair_score={n:sum(c for (a,b),c in pair.items() if a==n or b==n)/max(1,total) for n in fs}
    ml=ml_scores(history)
    def standard(s):
        vals=list(s.values()); mean=sum(vals)/len(vals); sd=(sum((v-mean)**2 for v in vals)/len(vals))**0.5 or 1
        return {n:(v-mean)/sd for n,v in s.items()}
    normalized=[standard(x) for x in (frequency,gap,pair_score,ml)]
    ensemble={n:sum(s[n] for s in normalized)/4 for n in fs}
    return [frequency,gap,pair_score,ml,ensemble],pair

def coldest_numbers(history, count=5):
    # Use ONLY draws strictly preceding the target, in the same 6/52 dataset.
    # Lowest total frequency = coldest; ties use longer absence, then number.
    if not history:
        raise ValueError('No earlier historical draws to calculate cold numbers.')
    counts=Counter(n for d in history for n in d['numbers'])
    gaps={n:next((i for i,d in enumerate(reversed(history)) if n in d['numbers']),len(history))
          for n in range(1,N+1)}
    return sorted(range(1,N+1),key=lambda n:(counts[n],-gaps[n],n))[:count]

def predict(history, target, salt='0'):
    if len(history)<25:raise ValueError('At least 25 earlier verified draws are needed to predict.')
    excluded=set(coldest_numbers(history))
    sets,pairs=score_sets(history)
    out=[]
    for idx, scores in enumerate(sets):
        rng=random.Random(seed_for(target,idx,salt)); chosen=[]
        for _ in range(6):
            options=[n for n in range(1,N+1) if n not in chosen and n not in excluded]
            vals=[]
            for n in options:
                pbonus=sum(pairs.get(tuple(sorted((n,x))),0) for x in chosen)
                vals.append(scores[n]+(pbonus*0.025 if idx==2 else 0))
            peak=max(vals); weights=[math.exp(max(-30,min(30,(v-peak)*1.3))) for v in vals]
            chosen.append(rng.choices(options,weights=weights,k=1)[0])
        out.append(sorted(chosen))
    return out

def compare(rows,actual):
    actual=set(actual)
    return [{'numbers':row,'matched':sorted(actual.intersection(row)),'count':len(actual.intersection(row)),'percentage':round(len(actual.intersection(row))*100/6,2)} for row in rows]

def walkforward(draws,start=None,end=None,limit=200):
    results=[]
    for i in range(25,len(draws)):
        target=draws[i]
        if start and target['date']<start:continue
        if end and target['date']>end:continue
        results.append({'date':target['date'],'actual':target['numbers'],'rows':compare(predict(draws[:i],target['date']),target['numbers'])})
        if len(results)>=limit:break
    summary=[]
    for j in range(5):
        counts=[r['rows'][j]['count'] for r in results]
        summary.append({'strategy':['Frequency / recency','Hot / cold + gaps','Pairs / triplets','Online machine learning','Ensemble'][j], 'mean_matches':round(sum(counts)/len(counts),3) if counts else None,'three_plus':sum(c>=3 for c in counts),'four_plus':sum(c>=4 for c in counts),'histogram':{str(k):counts.count(k) for k in range(7)}})
    return {'tested':len(results),'summary':summary,'results':results}
