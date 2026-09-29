import json, hashlib
from pathlib import Path
import numpy as np
from data.generate import generate
from forecasting.model import train, predict, baseline, ARTIFACT, fit_local_effects,valid

def main():
    rows,_=generate(); training=[r for r in rows if r['day']<120]
    model=train(training)
    model['local_effects']=fit_local_effects(model,training)
    calibration=valid([r for r in rows if 120<=r['day']<150 and not r['stock_exhausted']])
    means=predict(model,calibration); actual=np.array([r['dispensed'] for r in calibration])
    # Moment estimate of NB dispersion from calibration residuals, bounded for stability.
    model['dispersion']=float(np.clip(np.mean(means**2)/max(.01,np.mean((actual-means)**2-means)),2,100))
    validation=[r for r in rows if 150<=r['day']<180 and r['dispensed'] is not None and not r['stock_exhausted'] and r['hours_open']>0]
    y=np.array([r['dispensed'] for r in validation]); advanced=float(np.mean(abs(predict(model,validation)-y)))
    groups={}
    for r in rows:
        if r['day']<120: groups.setdefault((r['state'],r['facility'],r['medicine']),[]).append(r)
    pred=np.array([baseline(groups[(r['state'],r['facility'],r['medicine'])],r['weekday']) for r in validation])
    base=float(np.mean(abs(pred-y)))
    model.update(version='nb-v2-local-effects',training_cutoff=119,calibration_range=[120,149],validation_range=[150,179],
        selected=advanced<base,validation_mae=advanced,baseline_validation_mae=base,source='synthetic',
        data_hash=hashlib.sha256(json.dumps(training,sort_keys=True).encode()).hexdigest(),
        limitations=['Local intercepts are fitted only on uncensored training observations','NB dispersion is moment-calibrated; no guaranteed coverage','No clinical validation'])
    ARTIFACT.parent.mkdir(parents=True,exist_ok=True); ARTIFACT.write_text(json.dumps(model,indent=2))
    print(json.dumps(model,indent=2))
if __name__=='__main__': main()
