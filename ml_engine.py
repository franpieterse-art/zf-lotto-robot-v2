"""Dependency-free chronological learning models for 6/52 research (not proven predictive)."""
import math
from collections import Counter
from functools import lru_cache
WINDOWS=(10,25,50,100,250,500)

def feature_rows(history):
    # Each feature vector depends exclusively on earlier draws.
    n=len(history); counts={w:Counter(x for d in history[-w:] for x in d['numbers']) for w in WINDOWS}
    last={x:next((i for i,d in enumerate(reversed(history)) if x in d['numbers']),n) for x in range(1,53)}
    return {x:[1.0]+[counts[w][x]/max(1,min(n,w))*52/6 for w in WINDOWS]+[min(last[x],52)/52] for x in range(1,53)}

def train_examples(history, upto, cap=220):
    # Only completed historical draws strictly before `upto` are labels.
    start=max(40,upto-cap)
    for j in range(start,upto):
        xs=feature_rows(history[:j]); winners=set(history[j]['numbers'])
        for num in range(1,53):yield xs[num],int(num in winners)

def sigmoid(v):return 1/(1+math.exp(-max(-25,min(25,v))))

def logistic_scores(history,cap=60):
    weights=[-2.0]+[0.0]*7
    # Online SGD, balanced class prior is handled by intercept.
    for x,y in train_examples(history,len(history),cap):
        p=sigmoid(sum(a*b for a,b in zip(weights,x))); err=y-p
        for k in range(len(weights)):
            weights[k]+=0.015*(err*x[k]-(0.002*weights[k] if k else 0))
    return {num:sigmoid(sum(a*b for a,b in zip(weights,x))) for num,x in feature_rows(history).items()}

def boosted_scores(history,cap=60):
    # Small gradient-boosted ensemble of one-dimensional decision stumps.
    examples=list(train_examples(history,len(history),cap))
    base=6/52
    if not examples:return {x:base for x in range(1,53)}
    pred=[base]*len(examples); stumps=[]; rate=0.30
    for _ in range(6):
        best=None
        for feature in range(1,8):
            for threshold in (0.25,0.6,1.0,1.5):
                a=[i for i,(x,y) in enumerate(examples) if x[feature]<=threshold]
                if not a or len(a)==len(examples):continue
                left=set(a); right_count=len(examples)-len(a)
                l=sum(examples[i][1]-pred[i] for i in a)/len(a)
                r=sum(examples[i][1]-pred[i] for i in range(len(examples)) if i not in left)/right_count
                gain=len(a)*l*l+right_count*r*r
                if best is None or gain>best[0]:best=(gain,feature,threshold,l,r)
        if best is None:break
        _,feature,threshold,l,r=best
        stumps.append((feature,threshold,l,r))
        for i,(x,y) in enumerate(examples):pred[i]+=rate*(l if x[feature]<=threshold else r)
    return {num:max(.001,min(.999,base+sum(rate*(l if x[f]<=t else r) for f,t,l,r in stumps))) for num,x in feature_rows(history).items()}

def window_scores(history):
    x=feature_rows(history)
    # Equal-weight multi-window evidence; window selection tested independently.
    return {num:sum(x[num][1:7])/6 for num in range(1,53)}
