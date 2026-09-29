"""Small censored negative-binomial model, safe JSON artifacts, seeded scenario inference."""
import hashlib, json
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from scipy.stats import nbinom

SCHEMA='count-v1:intercept,weekend,log-footfall'
ARTIFACT=Path(__file__).parent/'artifacts'/'model.json'

def features(rows):
    return np.array([[1.,float(r['weekday']>=5),np.log((r['footfall']+10)/60)] for r in rows])

def valid(rows): return [r for r in rows if r['dispensed'] is not None and r['hours_open']>0]

def train(rows,initial=None,maxiter=80):
    rows=valid(rows); x=features(rows); y=np.array([r['dispensed'] for r in rows]); cens=np.array([r['stock_exhausted'] for r in rows])
    def loss(beta):
        mu=np.exp(np.clip(x@beta,-3,7)); p=12/(12+mu)
        ll=np.where(cens,nbinom.logsf(np.maximum(y-1,-1),12,p),nbinom.logpmf(y,12,p))
        return float(-np.mean(np.maximum(ll,-100))+0.001*np.sum(beta[1:]**2))
    result=minimize(loss,np.array(initial if initial is not None else [2.5,0.,1.]),method='L-BFGS-B',options={'maxiter':maxiter})
    if not np.isfinite(result.fun): raise ValueError('Training failed')
    return {'coefficients':result.x.tolist(),'schema':SCHEMA,'dispersion':12,'training_rows':len(rows),'loss':float(result.fun),'converged':bool(result.success)}

def effect_key(row): return '|'.join(str(row.get(k,'')) for k in ['state','facility','medicine'])

def fit_local_effects(model,rows):
    """Shrink facility/product intercepts towards the shared count model; fitted on training only."""
    groups={}
    for r in valid(rows):
        if not r['stock_exhausted']: groups.setdefault(effect_key(r),[]).append(r)
    effects={}
    for key,group in groups.items():
        mu=np.exp(np.clip(features(group)@np.array(model['coefficients']),-3,7))
        ratio=(sum(r['dispensed'] for r in group)+20)/(float(sum(mu))+20)
        effects[key]=float(np.clip(np.log(ratio),-1,1)*len(group)/(len(group)+10))
    return effects

def predict(model,rows):
    offsets=np.array([model.get('local_effects',{}).get(effect_key(r),0) for r in rows])
    return np.exp(np.clip(features(rows)@np.array(model['coefficients'])+offsets,-3,7))

def baseline(rows,weekday):
    good=[r['dispensed'] for r in valid(rows) if r['availability_fraction']>=.99 and r['weekday']==weekday]
    if len(good)<3: good=[r['dispensed'] for r in valid(rows) if r['availability_fraction']>=.99]
    return float(np.median(good)) if good else 0.

def adjusted(rows):
    r=valid(rows)[-28:]
    return float(np.mean([max(x['dispensed']+x['unfilled_requests'],x['dispensed']/max(.2,x['availability_fraction'])) for x in r])) if r else 0.

def forecast(rows,stock,footfall=None,seed=20260927,replenishments=None):
    model=json.loads(ARTIFACT.read_text()); history=valid(rows)[-28:]
    fallback=not model.get('selected',False)
    daily=[]
    for day in range(14):
        feature={**({k:history[-1][k] for k in ['state','facility','medicine']} if history else {}),'weekday':(180+day)%7,'footfall':footfall if footfall is not None else float(np.mean([r['footfall'] for r in history])) if history else 50}
        daily.append(baseline(history,feature['weekday']) if fallback else float(predict(model,[feature])[0]))
    # Same seed per district induces shared shocks, intentionally correlated demand scenarios.
    rng=np.random.default_rng(seed); shocks=rng.lognormal(-.01125,.15,(100,14))
    mu=np.array(daily)[None,:]*shocks
    paths=rng.negative_binomial(model['dispersion'],model['dispersion']/(model['dispersion']+mu))
    cumulative=paths.cumsum(axis=1)
    arrivals=np.zeros_like(cumulative)
    for delivery in replenishments or []:
        eta=rng.integers(max(0,delivery['eta_min_days']),max(0,delivery['eta_max_days'])+1,100)
        for i,day in enumerate(eta):
            if day<14: arrivals[i,int(day):]+=delivery['quantity']
    net=cumulative-arrivals
    return {'model_version':model['version'],'method':'weekday median fallback' if fallback else 'experimental censored negative binomial',
        'horizon':14,'sample_count':100,'p10':np.quantile(cumulative,.1,axis=0).tolist(),'p50':np.quantile(cumulative,.5,axis=0).tolist(),
        'p90':np.quantile(cumulative,.9,axis=0).tolist(),'protected_7d':float(np.quantile(cumulative[:,6],.95)),
        'net_required_7d':float(max(0,np.quantile(net[:,6],.95))), 'risk_14d':float(np.mean(np.any(net>stock,axis=1))),
        'replenishments':replenishments or [],'lead_time_source':'synthetic uniform ETA ranges',
        'quality_flags':['SYNTHETIC_HISTORY','EXPERIMENTAL_MODEL' if not fallback else 'BASELINE_SELECTED'],
        'observed_daily':[r['dispensed'] for r in rows[-28:]],'availability':[r['availability_fraction'] for r in rows[-28:]],'source':'synthetic'}
