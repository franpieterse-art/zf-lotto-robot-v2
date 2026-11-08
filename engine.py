import math, random, hashlib
from collections import Counter
from datetime import date
N=52

def seed_for(draw_date, strategy, salt=''):
    return int(hashlib.sha256(f'{draw_date}|{strategy}|{salt}'.encode()).hexdigest()[:16],16)

def features(history, ball_max=N):
    windows=[10,30,80,200]
    feats={}
    for n in range(1,ball_max+1):
        gap=next((i for i,d in enumerate(reversed(history)) if n in d['numbers']),len(history))
        freqs=[sum(n in d['numbers'] for d in history[-w:])/max(1,min(w,len(history))) for w in windows]
        feats[n]=[1.,*freqs,min(gap,100)/100]
    return feats

def ml_scores(history, ball_max=N):
    # Online logistic model: training examples are constructed only from preceding draws.
    # Every training target is the next observed draw, never the selected test draw.
    if len(history)<25: return {n:0. for n in range(1,ball_max+1)}
    weights=[-2.1,0,0,0,0,0]
    start=max(12,len(history)-80)
    for epoch in range(1):
        for i in range(start,len(history)):
            f=features(history[:i],ball_max); actual=set(history[i]['numbers'])
            for n in range(1,ball_max+1):
                x=f[n]; z=max(-20,min(20,sum(a*b for a,b in zip(weights,x))))
                p=1/(1+math.exp(-z)); error=(int(n in actual)-p)
                for j in range(len(weights)):weights[j]+=0.009*(error*x[j]-0.001*weights[j])
    f=features(history,ball_max)
    return {n:sum(a*b for a,b in zip(weights,f[n])) for n in f}

def score_sets(history, ball_max=N):
    fs=features(history,ball_max); total=len(history)
    counts=Counter(n for d in history for n in d['numbers'])
    pair=Counter()
    for d in history[-150:]:
        a=d['numbers']
        for i in range(6):
            for j in range(i+1,6):pair[(a[i],a[j])]+=1
    frequency={n:2*fs[n][1]+fs[n][2]+0.5*fs[n][3] for n in fs}
    gap={n:fs[n][1]+fs[n][2]+0.35*fs[n][5] for n in fs}
    pair_score={n:sum(c for (a,b),c in pair.items() if a==n or b==n)/max(1,total) for n in fs}
    ml=ml_scores(history,ball_max)
    def standard(s):
        vals=list(s.values()); mean=sum(vals)/len(vals); sd=(sum((v-mean)**2 for v in vals)/len(vals))**0.5 or 1
        return {n:(v-mean)/sd for n,v in s.items()}
    normalized=[standard(x) for x in (frequency,gap,pair_score,ml)]
    ensemble={n:sum(s[n] for s in normalized)/4 for n in fs}
    return [frequency,gap,pair_score,ml,ensemble],pair

def hottest_numbers(history, count=5, ball_max=N):
    """Highest historical frequency, ties: most recently seen, then lowest number.

    Only pass verified Main Lotto draws strictly earlier than prediction date.
    """
    if not history:
        raise ValueError('No earlier historical draws to calculate hot numbers.')
    counts=Counter(n for d in history for n in d['numbers'])
    gaps={n:next((i for i,d in enumerate(reversed(history)) if n in d['numbers']),len(history))
          for n in range(1,ball_max+1)}
    return sorted(range(1,ball_max+1), key=lambda n:(-counts[n],gaps[n],n))[:count]


def adaptive_window_scores(history, ball_max=N):
    """Select lookback by walk-forward validation strictly before target."""
    windows=(10,25,50,100,200)
    nvalid=min(24,max(0,len(history)-12))
    scores={}
    for window in windows:
        hits=0
        for i in range(len(history)-nvalid,len(history)):
            past=history[:i]
            counts=Counter(n for d in past[-window:] for n in d['numbers'])
            ranked=sorted((n for n in range(1,ball_max+1)),key=lambda n:(-counts[n],n))[:6]
            hits+=len(set(ranked)&set(history[i]['numbers']))
        scores[window]=hits/max(1,nvalid)
    best=max(windows,key=lambda w:(scores[w],w))
    counts=Counter(n for d in history[-best:] for n in d['numbers'])
    return {n:counts[n]/max(1,min(best,len(history))) for n in range(1,ball_max+1)},best,scores

def experimental_scores(history, ball_max=N):
    """Seven past-only, exploratory statistical models (not calibrated probabilities)."""
    pool=range(1,ball_max+1)
    past=[set(n for n in d['numbers'] if n<=ball_max) for d in history]
    total=len(past)
    windows=(10,30,100,200)
    counts={w:Counter(n for d in past[-w:] for n in d) for w in windows}
    # 1. Markov-style transition associations, with smoothing.
    previous=past[-1]
    transition=Counter(); occurrences=Counter()
    for a,b in zip(past[:-1],past[1:]):
        for n in a: occurrences[n]+=1
        for n in b:
            transition[n]+=sum(1/max(1,occurrences[x]) for x in a if x in previous)
    markov={n:transition[n]/max(1,total) for n in pool}
    # 2. Beta-Binomial posterior mean, with uniform lottery prior.
    overall=Counter(n for d in past for n in d)
    bayes={n:(overall[n]+6)/(total+ball_max) for n in pool}
    # 3. Momentum of recent versus medium-term frequency.
    momentum={n:counts[10][n]/max(1,min(10,total))-counts[100][n]/max(1,min(100,total)) for n in pool}
    # 4. Rank stability across different windows.
    rankings={w:{n:i for i,n in enumerate(sorted(pool,key=lambda n:(-counts[w][n],n)))} for w in windows}
    stability={n:-sum(rankings[w][n] for w in windows)/len(windows) for n in pool}
    # 5. Triplet association support from earlier draws.
    triples=Counter()
    from itertools import combinations
    for d in past[-150:]:
        for tri in combinations(sorted(d),3):triples[tri]+=1
    triplet={n:sum(c for tri,c in triples.items() if n in tri)/max(1,min(total,150)) for n in pool}
    # 6. Monte Carlo: smoothed frequency distribution, sampled reproducibly.
    rng=random.Random(seed_for(history[-1]['date'] if history else '', 'monte-carlo'))
    weights=[overall[n]+6 for n in pool]
    simulated=Counter()
    for _ in range(250):
        choices=list(pool); w=weights[:]
        for _ in range(min(6,len(choices))):
            picked=rng.choices(range(len(choices)),weights=w,k=1)[0]
            simulated[choices.pop(picked)]+=1;w.pop(picked)
    monte={n:simulated[n]/250 for n in pool}
    # 7. Adaptive rolling-window frequency model (validated separately).
    adaptive,window,_=adaptive_window_scores(history,ball_max)
    return [markov,bayes,momentum,stability,triplet,monte,adaptive],window


def normalized(scores):
    values=list(scores.values());mean=sum(values)/len(values)
    sd=(sum((v-mean)**2 for v in values)/len(values))**.5 or 1
    return {n:(v-mean)/sd for n,v in scores.items()}


def selected_model_scores(history, ball_max=N):
    """Select the five best past-validated methods, with no target leakage."""
    scores,window=experimental_scores(history,ball_max)
    # Validation strictly within history; train each model on draws preceding its validation draw.
    # Limit validation to 8 completed draws to keep Render response time bounded.
    validation=Counter()
    if len(history)>=30:
        for i in range(max(20,len(history)-8),len(history)):
            prior=history[:i]
            # Score first six inexpensive methods on their past-only history.
            candidate,_=experimental_scores(prior,ball_max)
            actual=set(history[i]['numbers'])
            for j,sc in enumerate(candidate):
                top=sorted(sc,key=lambda n:(-sc[n],n))[:6]
                validation[j]+=len(actual.intersection(top))
    # Choose top five, with stable deterministic tie-breaking.
    selected=sorted(range(7),key=lambda j:(-validation[j],j))[:5]
    return [scores[j] for j in selected],selected,dict(validation),window


# V30: fast, six-factor experimental score. All eligible numbers remain in the pool.
# No score is a calibrated winning probability.
V29_WEIGHTS={'long_frequency':.20,'recent_frequency':.20,'momentum':.15,'gap':.10,'pairing':.15,'stability':.20}

# V32: smoothed multi-horizon ensemble. Scores are NOT winning probabilities.
V32_WEIGHTS={'long':.25,'recent':.25,'momentum':.15,'gap':.05,'pair':.15,'stability':.15}

def v32_scores(history,ball_max=N):
    from itertools import combinations
    pool=range(1,ball_max+1)
    if not history: return {n:0.0 for n in pool}
    # Historical eligibility: numbers 50+ did not exist in 6/49 draws.
    eligible=Counter()
    counts=Counter()
    for d in history:
        historical_max=49 if d['date']<'2017-01-01' else (58 if d['date']<'2026-06-01' else 52)
        eligible.update(n for n in pool if n<=historical_max)
        counts.update(n for n in d['numbers'] if n in pool)
    def rate(window):
        draws=history[-window:]
        occ=Counter(n for d in draws for n in d['numbers'] if n in pool)
        exposures=Counter()
        for d in draws:
            maximum=49 if d['date']<'2017-01-01' else (58 if d['date']<'2026-06-01' else 52)
            exposures.update(n for n in pool if n<=maximum)
        # Shrink toward uniform expectation: short samples should not dominate.
        return {n:(occ[n]+12*6/ball_max)/(exposures[n]+12) for n in pool}
    r20=rate(20);r60=rate(60);r150=rate(150)
    long={n:(counts[n]+30*6/ball_max)/(eligible[n]+30) for n in pool}
    recent={n:.50*r20[n]+.30*r60[n]+.20*r150[n] for n in pool}
    momentum={n:r20[n]-r150[n] for n in pool}
    gap={}
    for n in pool:
        # Gap is a descriptive signal, not evidence a number is 'due'.
        last=next((i for i,d in enumerate(reversed(history)) if n in d['numbers']),len(history))
        gap[n]=min(last,40)/40
    # Pair score uses smoothed support, without treating co-occurrence as causation.
    pair=Counter()
    for d in history[-100:]:
        for x,y in combinations(sorted(n for n in d['numbers'] if n in pool),2):
            pair[x]+=1;pair[y]+=1
    pairing={n:(pair[n]+5)/(min(100,len(history))+5) for n in pool}
    stability={n:-abs(r20[n]-r60[n])-abs(r60[n]-r150[n]) for n in pool}
    factors={'long':long,'recent':recent,'momentum':momentum,
             'gap':gap,'pair':pairing,'stability':stability}
    standardized={k:normalized(v) for k,v in factors.items()}
    return {n:sum(V32_WEIGHTS[k]*standardized[k][n] for k in V32_WEIGHTS) for n in pool}

# Backwards-compatible alias for other code importing v29_scores.
v29_scores=v32_scores

def predict(history,target,salt='0',ball_max=N):
    if len(history)<12:raise ValueError('At least 12 earlier Main LOTTO draws are required.')
    scores=v32_scores(history,ball_max)
    rows=[]
    for idx in range(5):
        rng=random.Random(seed_for(target,'v32-'+str(idx),salt))
        options=list(range(1,ball_max+1));chosen=[]
        temperature=(1.4,1.0,.7,.45,.25)[idx]
        for _ in range(6):
            peak=max(scores[n] for n in options)
            weights=[math.exp(max(-20,(scores[n]-peak)*temperature)) for n in options]
            pick=rng.choices(options,weights=weights,k=1)[0]
            chosen.append(pick);options.remove(pick)
        row=sorted(chosen)
        if row in rows:
            for _ in range(100):
                row=sorted(rng.sample(range(1,ball_max+1),6))
                if row not in rows:break
        rows.append(row)
    return rows

def compare(rows,actual):
    actual=set(actual)
    return [{'numbers':row,'matched':sorted(actual.intersection(row)),'count':len(actual.intersection(row)),'percentage':round(len(actual.intersection(row))*100/6,2)} for row in rows]

def walkforward(draws,start=None,end=None,limit=100,era_fn=None):
    # Most recent test draws first to keep backtesting relevant and bounded.
    targets=[d for d in draws if (not start or d['date']>=start) and (not end or d['date']<=end)]
    targets=targets[-limit:]
    results=[]
    for target in targets:
        day=target['date'];history=[d for d in draws if d['date']<day]
        if len(history)<12:continue
        ball_max=era_fn(day)[2] if era_fn else N
        rows=predict(history,day,ball_max=ball_max)
        results.append({'date':day,'actual':target['numbers'],'rows':compare(rows,target['numbers']),'training_draws':len(history),'number_range':ball_max})
    summary=[]
    for j in range(5):
        counts=[r['rows'][j]['count'] for r in results]
        summary.append({'strategy':'V32 formula row '+str(j+1),'mean_matches':round(sum(counts)/len(counts),3) if counts else None,'three_plus':sum(c>=3 for c in counts),'four_plus':sum(c>=4 for c in counts),'histogram':{str(k):counts.count(k) for k in range(7)}})
    return {'tested':len(results),'summary':summary,'results':results}
