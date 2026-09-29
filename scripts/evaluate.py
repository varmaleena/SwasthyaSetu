"""Untouched final 28 days, independent seeds, same demand/supply across policies."""
import hashlib,json,time
from pathlib import Path
import numpy as np
from scipy.stats import nbinom
from data.generate import generate
from forecasting.model import ARTIFACT,predict,baseline,adjusted
from allocation.solver import solve

def main():
    started=time.perf_counter(); model=json.loads(ARTIFACT.read_text()); results=[]; policy_results={}
    for seed in [20260928,20260929]:
        rows,truth=generate(seed); lookup={(r['state'],r['facility'],r['medicine'],r['day']):r['latent'] for r in truth}
        groups={}
        for r in rows: groups.setdefault((r['state'],r['facility'],r['medicine']),[]).append(r)
        for key,group in groups.items():
            hist=[r for r in group if r['day']<180]; test=[r for r in group if r['day']>=180]
            actual=np.array([lookup[(*key,r['day'])] for r in test]); advanced=predict(model,test)
            base=np.array([baseline(hist,r['weekday']) for r in test]); adj=np.full(28,adjusted(hist))
            for name,pred in [('weekday_median',base),('adjusted_consumption',adj),('experimental_nb',advanced)]:
                dispersion=model['dispersion'] if name=='experimental_nb' else 12
                low=nbinom.ppf(.1,dispersion,dispersion/(dispersion+pred)); high=nbinom.ppf(.9,dispersion,dispersion/(dispersion+pred))
                results.append({'seed':seed,'state':key[0],'facility':key[1],'medicine':key[2],'method':name,
                    'mae':float(np.mean(abs(pred-actual))),'coverage_p10_p90':float(np.mean((actual>=low)&(actual<=high)))})
        # Small matched three-facility replay. Latent demand is evaluator-only.
        for method in ['fixed_threshold','nearest_feasible','donor_protected']:
            stocks={'A':40,'B':120,'C':150}; unmet=days=donor_unmet=transport=0
            for day in range(180,208):
                # Identical replenishment for every policy, no hidden advantage.
                if (day-180)%7==0:
                    for f in stocks: stocks[f]+=30
                    estimates={f:adjusted(groups[('A',f,'MED-001')][:180])*7 for f in stocks}
                    need=max(0,int(estimates['A']-stocks['A']))
                    if method=='fixed_threshold': need=60 if stocks['A']<70 else 0
                    for donor,cost in [('B',1),('C',2)]:
                        protect=int(estimates[donor])+20 if method=='donor_protected' else (20 if method=='nearest_feasible' else 0)
                        q=min(need,max(0,stocks[donor]-protect))//10*10
                        stocks[donor]-=q; stocks['A']+=q; need-=q; transport+=q*cost
                for f in stocks:
                    demand=lookup[('A',f,'MED-001',day)]; missing=max(0,demand-stocks[f]); stocks[f]=max(0,stocks[f]-demand)
                    unmet+=missing; days+=int(missing>0); donor_unmet+=missing if f!='A' else 0
            policy_results.setdefault(method,[]).append({'seed':seed,'unmet_units':unmet,'stockout_facility_days':days,'donor_unmet_units':donor_unmet,'transport_cost_proxy':transport,'expiry_waste':0})
    summaries={}
    for name in ['weekday_median','adjusted_consumption','experimental_nb']:
        selected=[r for r in results if r['method']==name]
        summaries[name]={k:float(np.mean([r[k] for r in selected])) for k in ['mae','coverage_p10_p90']}
    output={'status':'measured','source':'synthetic evaluator-only truth','script_version':'evaluate-v1','model_version':model['version'],
        'model_hash':hashlib.sha256(ARTIFACT.read_bytes()).hexdigest(),'data_hash':hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest(),'evaluation_seeds':[20260928,20260929],
        'test_days':[180,207],'training_cutoff':119,'forecast_metrics':summaries,'policy_replay':policy_results,
        'stratified':results,'elapsed_seconds':round(time.perf_counter()-started,3),
        'limitations':['Synthetic outcomes do not establish clinical benefit','Replay assumes immediate transfer and no expiry during 28 days; not full transport simulation',
            'Policies share identical initial stock, replenishment and demand','No global superiority claim','Lead-time and correlated-shock sensitivity benchmark still pending']}
    folder=Path('data/evaluation');folder.mkdir(exist_ok=True);(folder/'results.json').write_text(json.dumps(output,indent=2))
    print(json.dumps({k:v for k,v in output.items() if k!='stratified'},indent=2))
if __name__=='__main__': main()
