"""Matched transport/expiry replay; evaluator latent demand never reaches the planner."""
import hashlib,json
from datetime import datetime,timedelta,timezone
from pathlib import Path
import numpy as np
from data.generate import generate
from forecasting.model import forecast,adjusted
from allocation.solver import solve

def replay(seed,shock,delay,policy):
    observations,truth=generate(seed)
    history={f:[r for r in observations if r['state']=='A' and r['facility']==f and r['medicine']=='MED-001'] for f in 'ABC'}
    actual={(r['facility'],r['day']):r['latent'] for r in truth if r['state']=='A' and r['medicine']=='MED-001'}
    start=datetime(2026,9,27,9,tzinfo=timezone.utc)
    batches=[];transit=[];unmet=stockouts=donor_units=donor_days=waste=cost=0;ledger=[]
    def add(f,q,day,expiry_day,label):
        batches.append({'id':label,'facility_id':f,'medicine_code':'MED-001','on_hand':q,'reserved':0,'quarantined':0,'quality':'usable','storage':'suitable','expiry':(start+timedelta(days=expiry_day)).date().isoformat(),'observed_at':(start+timedelta(days=day)).isoformat()})
    for f,q in [('A',40),('B',120),('C',150)]:add(f,q,0,21,'initial-'+f)
    for day in range(28):
        clock=(start+timedelta(days=day)).isoformat()
        for b in batches:
            if b['expiry']<=clock[:10]:waste+=b['on_hand'];b['on_hand']=0
            b['observed_at']=clock # Daily synthetic count, same observation policy across comparators.
        for shipment in list(transit):
            if shipment['arrival']<=day:
                if shipment['expiry']<=day:waste+=shipment['quantity']
                else:add(shipment['destination'],shipment['quantity'],day,shipment['expiry'],'transfer-'+str(len(batches)))
                transit.remove(shipment)
        if day>=delay and (day-delay)%7==0:
            for f in 'ABC':add(f,35,day,day+10,f'external-{f}-{day}')
        if day%7==0:
            stocks={f:sum(b['on_hand'] for b in batches if b['facility_id']==f) for f in 'ABC'}
            observed={f:[r for r in history[f] if r['day']<180+day] for f in 'ABC'}
            if policy=='full_solver':
                demands={f:forecast(observed[f],stocks[f],seed=seed+day)['protected_7d'] for f in 'ABC'}
                plan=solve(batches,'A','MED-001',demands,clock)
                lines=plan['lines']
            else:
                demands={f:adjusted(observed[f])*7 for f in 'ABC'};needed=max(0,int(demands['A']-stocks['A']))
                if policy=='fixed_threshold':needed=60 if stocks['A']<70 else 0
                lines=[]
                for donor,travel in [('B',1),('C',2)]:
                    protect=int(demands[donor])+(20 if donor=='B' else 30)
                    surplus=max(0,stocks[donor]-protect)
                    if travel>7*stocks['A']/max(1,demands['A']):continue
                    for b in sorted([b for b in batches if b['facility_id']==donor],key=lambda b:b['expiry']):
                        if b['expiry']<=(start+timedelta(days=day+travel)).date().isoformat():continue
                        q=min(needed,surplus,b['on_hand'])//10*10
                        if q:lines.append({'batch':b['id'],'source':donor,'destination':'A','quantity':q,'travel_days':travel});needed-=q;surplus-=q
            for line in lines:
                b=next(b for b in batches if b['id']==line['batch']);q=line['quantity'];b['on_hand']-=q;cost+=q*line['travel_days']
                expiry=(datetime.fromisoformat(b['expiry']).replace(tzinfo=timezone.utc)-start.replace(hour=0)).days
                transit.append({'quantity':q,'destination':'A','arrival':day+line['travel_days']+delay,'expiry':expiry})
        daily={}
        for f in 'ABC':
            demand=int(np.ceil(actual[(f,180+day)]*(shock if 7<=day<14 else 1)));left=demand
            for b in sorted([b for b in batches if b['facility_id']==f],key=lambda b:b['expiry']):
                q=min(left,b['on_hand']);b['on_hand']-=q;left-=q
            unmet+=left;stockouts+=int(left>0);donor_units+=left if f!='A' else 0;donor_days+=int(left>0) if f!='A' else 0
            daily[f]={'requested':demand,'unmet':left}
        ledger.append({'day':day,'facilities':daily,'on_hand':sum(b['on_hand'] for b in batches),'in_transit':sum(t['quantity'] for t in transit)})
    return {'seed':seed,'district_surge_multiplier':shock,'additional_delivery_delay_days':delay,'policy':policy,'unmet_units':unmet,'stockout_facility_days':stockouts,
        'donor_unmet_units':donor_units,'donor_stockout_days':donor_days,'expiry_waste':waste,'transport_cost_proxy':cost,'remaining_stock':sum(b['on_hand'] for b in batches),'in_transit':sum(t['quantity'] for t in transit),'ledger_hash':hashlib.sha256(json.dumps(ledger,sort_keys=True).encode()).hexdigest()}

def main():
    rows=[replay(seed,shock,delay,policy) for seed in [20261001,20261002] for shock in [1.,1.5] for delay in [0,2] for policy in ['fixed_threshold','nearest_feasible','full_solver']]
    result={'script_version':'transport-v1','status':'measured synthetic transport replay','seeds':[20261001,20261002],
        'controls':'Identical initial batches, replenishment, expiry, demand and delay per matched case. All policies protect donors; only demand estimation/allocation differs.',
        'limitations':['Synthetic data only','Lead-time shocks are stress tests, not estimated real distributions','Future latent demand is evaluator-only','No universal improvement claimed'], 'rows':rows}
    Path('data/evaluation/transport.json').write_text(json.dumps(result,indent=2))
    p=Path('data/evaluation/results.json');overview=json.loads(p.read_text());overview['transport_sensitivity']=result
    overview['limitations']=[x for x in overview['limitations'] if 'sensitivity benchmark still pending' not in x]
    p.write_text(json.dumps(overview,indent=2));print('Measured 24 matched transport/expiry/surge policy replays; saved data/evaluation/transport.json')
if __name__=='__main__':main()
