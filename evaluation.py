"""Leakage-free chronological evaluation. Each draw is learned only AFTER scoring it."""
import random, hashlib
from engine import predict_learned, learning_update

def _seed(day):
    return int(hashlib.sha256(('v40-baseline-'+day).encode()).hexdigest()[:16],16)

def _metrics(rows, actual):
    wins=set(actual)
    hits=[len(wins.intersection(row)) for row in rows]
    return {'total_matches':sum(hits),'best_row':max(hits),
            'three_plus':sum(x>=3 for x in hits),'four_plus':sum(x>=4 for x in hits),
            'unique_coverage':len(set().union(*map(set,rows)))}

def evaluate(draws, era_fn, limit=30, warmup=100):
    ordered=sorted(draws,key=lambda d:d['date'])
    if len(ordered)<warmup+1:raise ValueError('Not enough earlier draws for blind evaluation')
    limit=max(1,min(int(limit),100))
    start=max(warmup,len(ordered)-limit)
    # Seed training lessons using completed historical draws strictly before test start.
    lessons=[]
    for i in range(max(12,start-40),start):
        day=ordered[i]['date'];history=ordered[:i];n=era_fn(day)[2]
        rows,_=predict_learned(history,day,ball_max=n,lessons=lessons)
        lessons.append(learning_update(history,rows,ordered[i]['numbers'],n))
    results=[]
    for i in range(start,len(ordered)):
        d=ordered[i];day=d['date'];n=era_fn(day)[2];history=ordered[:i]
        baseline,_=predict_learned(history,day,ball_max=n,lessons=[])
        adaptive,coefficients=predict_learned(history,day,ball_max=n,lessons=lessons)
        rng=random.Random(_seed(day))
        random_rows=[]
        while len(random_rows)<10:
            row=sorted(rng.sample(range(1,n+1),6))
            if row not in random_rows:random_rows.append(row)
        metrics={'fixed':_metrics(baseline,d['numbers']),
                 'learned':_metrics(adaptive,d['numbers']),
                 'random':_metrics(random_rows,d['numbers'])}
        results.append({'date':day,'metrics':metrics,'training_draws':i,
                        'prior_lessons':len(lessons),'weights':coefficients})
        # Actual is only introduced AFTER all three models were evaluated.
        lessons.append(learning_update(history,adaptive,d['numbers'],n))
    summary={}
    for name in ('fixed','learned','random'):
        values=[r['metrics'][name] for r in results]
        summary[name]={'average_matches_per_row':round(sum(v['total_matches'] for v in values)/(len(values)*10),4),
                       'best_row_mean':round(sum(v['best_row'] for v in values)/len(values),4),
                       'three_plus':sum(v['three_plus'] for v in values),
                       'four_plus':sum(v['four_plus'] for v in values),
                       'average_unique_coverage':round(sum(v['unique_coverage'] for v in values)/len(values),2)}
    return {'tested':len(results),'first':results[0]['date'],'last':results[-1]['date'],
            'summary':summary,'results':results,
            'warning':'Historical evaluation only. Model selection, data gaps and randomness can create misleading apparent improvements. No winning advantage established.'}
