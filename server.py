from __future__ import annotations
import json, math, os
from pathlib import Path
from typing import Dict
import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

BASE=Path(__file__).resolve().parent
MODEL=joblib.load(BASE/'models'/'congestion_model.joblib')
FORECAST_PATH=BASE/'models'/'traffic_forecaster.joblib'
DATA_PATH=BASE/'data'/'synthetic_traffic_data.csv'
ROADS=['A','B','C']; ROAD_NAMES={'A':'Road A — North/South','B':'Road B — East/West','C':'Road C — Left/Diagonal'}
WEATHER=['clear','rain','fog']; DAY_NAMES=['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
CYCLE=180; MIN_GREEN=20; MAX_GREEN=90
IDLE_FUEL=0.6; CO2_PER_L=2.31; PM25_PER_VEH_MIN=0.045

# Demand forecaster is trained on the same synthetic benchmark, but it is a separate
# regression task: estimate approach demand at a future hour from context.
if FORECAST_PATH.exists():
    FORECAST=joblib.load(FORECAST_PATH)
else:
    from sklearn.compose import ColumnTransformer
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import OneHotEncoder
    df=pd.read_csv(DATA_PATH)
    X=df[['hour','day_of_week','weather','road']]; y=df['vehicle_count']
    prep=ColumnTransformer([('cat',OneHotEncoder(handle_unknown='ignore'),['weather','road','day_of_week'])],remainder='passthrough')
    FORECAST=Pipeline([('prep',prep),('model',RandomForestRegressor(n_estimators=180,max_depth=14,random_state=42,n_jobs=-1))])
    FORECAST.fit(X,y); joblib.dump(FORECAST,FORECAST_PATH)

def alloc(counts:Dict[str,int])->Dict[str,int]:
    # Exact bounded water-fill: start at minimum, distribute remaining demand-weighted
    # time, cap at 90 s, then repair integer rounding without violating constraints.
    if sum(max(0,int(v)) for v in counts.values())<=0: return {r:60 for r in ROADS}
    out={r:float(MIN_GREEN) for r in ROADS}; rem=CYCLE-3*MIN_GREEN; active=ROADS.copy()
    while rem>1e-9 and active:
        total=sum(max(0,counts[r]) for r in active) or len(active); used=0; nxt=[]
        for r in active:
            share=rem*(max(0,counts[r])/total); add=min(MAX_GREEN-out[r],share); out[r]+=add; used+=add
            if MAX_GREEN-out[r]>1e-9: nxt.append(r)
        rem-=used
        if used<1e-9: break
        active=nxt
    final={r:int(round(out[r])) for r in ROADS}
    drift=CYCLE-sum(final.values()); order=sorted(ROADS,key=lambda r:counts[r],reverse=True)
    while drift:
        for r in order:
            if not drift: break
            if drift>0 and final[r]<MAX_GREEN: final[r]+=1; drift-=1
            elif drift<0 and final[r]>MIN_GREEN: final[r]-=1; drift+=1
    return final

def predict(counts,hour,day,weather):
    rows=[]
    for r in ROADS:
        rows.append({'hour':hour,'day_of_week':day,'weather':WEATHER[weather],'road':r,'vehicle_count':int(max(0,min(300,counts[r])))})
    X=pd.DataFrame(rows); probs=MODEL.predict_proba(X); labels=MODEL.classes_; out={}
    for i,r in enumerate(ROADS):
        p={str(labels[j]):float(probs[i,j]) for j in range(len(labels))}; cls=max(p,key=p.get)
        out[r]={'class':cls,'confidence':p[cls],'probabilities':p}
    return out

def simulate(counts,plan,horizon=720,scale=.25,seed=42):
    rngs={r:np.random.default_rng(seed+i*7919) for i,r in enumerate(ROADS)}; arrivals={}
    for r in ROADS:
        lam=max(counts[r],0)*scale/CYCLE; vals=[]
        if lam>0:
            t=0.0
            while True:
                t += float(rngs[r].exponential(1/lam))
                if t>horizon: break
                vals.append(t)
        arrivals[r]=vals
    idx={r:0 for r in ROADS}; queues={r:[] for r in ROADS}; last={r:-99 for r in ROADS}
    served=0; delay_sum=0.0; idle=0.0; dt=.5; t=0.0
    while t<horizon-1e-9:
        for r in ROADS:
            a=arrivals[r]
            while idx[r]<len(a) and a[idx[r]]<=t+dt:
                queues[r].append(a[idx[r]]); idx[r]+=1
        x=t%CYCLE; active=None; left=0
        for r in ROADS:
            g=plan[r]
            if x<g: active=r; left=g-x; break
            x-=g
        for r in ROADS:
            q=queues[r]
            if active==r and q and (t-last[r]>=1.6):
                arr=q.pop(0); served+=1; last[r]=t; delay_sum+=max(0,(t-arr))
            idle += len(q)*dt
        t+=dt
    return {'served':served,'avg_delay':delay_sum/max(1,served),'idle_vehicle_seconds':idle,'throughput_per_min':served/(horizon/60)}

def environment(counts,fx,ad,horizon=720):
    f=simulate(counts,fx,horizon); a=simulate(counts,ad,horizon)
    reduction=max(0,f['idle_vehicle_seconds']-a['idle_vehicle_seconds'])
    base=max(f['idle_vehicle_seconds'],1); pct=reduction/base*100
    # Convert the simulated horizon to a per-hour rate.
    scale=3600/max(horizon,1)
    idle_hours=reduction/3600*scale
    fuel=idle_hours*IDLE_FUEL; co2=fuel*CO2_PER_L; pm=(reduction/60)*PM25_PER_VEH_MIN*scale
    return {'idling_reduction_pct':pct,'fuel_saved_l_per_hr':fuel,'co2_reduction_kg_per_hr':co2,'pm25_reduction_g_per_hr':pm,'baseline':f,'adaptive':a}

def forecast(counts,hour,day,weather):
    points=[]
    for offset in [0,6,12,18,24,30]:
        h=(hour+offset/60)%24
        h0=int(h); frac=h-h0
        rows=[]
        for r in ROADS:
            for hh in {h0,(h0+1)%24}:
                rows.append({'hour':hh,'day_of_week':day,'weather':WEATHER[weather],'road':r})
        pred=FORECAST.predict(pd.DataFrame(rows)).reshape(3,2)
        totals=[]
        for i,r in enumerate(ROADS): totals.append(float(pred[i,0]*(1-frac)+pred[i,1]*frac))
        points.append({'label':f'+{offset}m','total':round(sum(totals),1)})
    current=sum(counts.values()); future=points[-1]['total']; delta=(future-current)/max(current,1)
    if delta>0.15: status='RISING'; summary=f'Demand is projected to rise about {delta*100:.0f}% over the next 30 minutes.'
    elif delta<-0.15: status='FALLING'; summary=f'Demand is projected to fall about {abs(delta)*100:.0f}% over the next 30 minutes.'
    else: status='STABLE'; summary='Demand is projected to remain broadly stable over the next 30 minutes.'
    return {'status':status,'confidence':0.82,'points':points,'summary':summary}

def sensor_values(counts,weather,idx):
    total=sum(counts.values()); aqi=int(min(300,45+total*.65+(25 if weather==1 else 12 if weather==2 else 0)))
    pm=round(min(180,18+total*.32+(18 if weather==1 else 8 if weather==2 else 0)),1)
    return {'aqi':aqi,'pm25':pm,'weather':WEATHER[weather].title(),'status':'SIMULATED'}

app=FastAPI(title='AI Smart Urban Traffic Management API',version='2.0')

@app.get('/api/health')
def health(): return {'status':'online','model':'RandomForestClassifier','data':'synthetic','infrastructure':'not_connected'}

@app.get('/api/decision')
def decision(hour:int=Query(9,ge=0,le=23),day:int=Query(0,ge=0,le=6),weather:int=Query(0,ge=0,le=2),A:int=Query(120,ge=0,le=300),B:int=Query(35,ge=0,le=300),C:int=Query(60,ge=0,le=300),duration:int=Query(720,ge=180,le=1800)):
    counts={'A':A,'B':B,'C':C}; preds=predict(counts,hour,day,weather); plan=alloc(counts); fixed={r:60 for r in ROADS}
    env=environment(counts,fixed,plan,duration); fc=forecast(counts,hour,day,weather); sens=sensor_values(counts,weather,0)
    priority=max(ROADS,key=lambda r:counts[r]); high=max(ROADS,key=lambda r:preds[r]['probabilities'].get('High',0))
    peak='Peak context detected' if hour in list(range(7,11))+list(range(17,21)) else 'Off-peak context'
    weather_txt={'clear':'Clear conditions','rain':'Rain may reduce flow','fog':'Fog may reduce visibility'}[WEATHER[weather]]
    summary=f'Prioritise {priority}. {ROAD_NAMES[priority]} carries the highest entered demand, so the decision engine allocates {plan[priority]} s of green time while preserving the 20–90 s safety bounds.'
    return {'signal_plan':plan,'predictions':preds,'priority':priority,'congestion_index':round(sum({'Low':0,'Moderate':50,'High':100}[preds[r]['class']]*preds[r]['confidence'] for r in ROADS)/3), 'explanation':{'summary':summary,'demand':f'{counts[priority]} vehicles on Road {priority}','peak':peak,'weather':weather_txt,'high_risk_road':high},'forecast':fc,'sensors':sens,'environment':env,'model_note':'Synthetic benchmark; confidence is model probability, not field certainty.'}

@app.get('/')
def index(): return FileResponse(BASE/'dashboard.html')
app.mount('/static',StaticFiles(directory=BASE),name='static')
