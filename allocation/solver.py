"""Bounded integer packs; explicit exclusions and an independent arithmetic verifier."""
from datetime import datetime,timedelta
import math
from ortools.sat.python import cp_model

POLICY={'version':'demo-v1','donor_protection':.95,'stock_stale_hours':24,'plan_hours':2,'reservation_minutes':30,'solver_seconds':2,
    'objective':'unmet units, then synthetic transport cost (single-recipient v1)'}

def solve(batches, recipient, product, demand, clock, scenario='GOLDEN', pack=10):
    stock=sum(b['on_hand']-b['reserved']-b['quarantined'] for b in batches if b['facility_id']==recipient and b['medicine_code']==product and usable(b,clock))
    need=max(0,math.ceil(demand.get(recipient,0)-stock))
    model=cp_model.CpModel(); candidates=[]; rejected=[]
    # Aggregate protection per facility, not per batch (prevents double-spending donor reserves).
    donors={b['facility_id'] for b in batches if b['facility_id']!=recipient and b['medicine_code']==product}
    for f in sorted(donors):
        rows=[b for b in batches if b['facility_id']==f and b['medicine_code']==product]
        reserve=20 if f=='B' else 30
        protected=math.ceil(demand.get(f,0))+reserve
        valid=[b for b in rows if usable(b,clock) and (datetime.fromisoformat(clock)-datetime.fromisoformat(b['observed_at'])).total_seconds()<=86400]
        available=sum(b['on_hand']-b['reserved']-b['quarantined'] for b in valid)
        surplus=max(0,available-protected)
        # Bundled synthetic authorised routes to A only. Other routes intentionally disabled.
        travel=1 if f=='B' else 2
        if scenario=='S06': travel=8
        valid=[b for b in valid if b['expiry']>(datetime.fromisoformat(clock)+timedelta(days=travel)).date().isoformat()]
        available=sum(b['on_hand']-b['reserved']-b['quarantined'] for b in valid)
        surplus=max(0,available-protected)
        deadline=7*stock/max(1,demand.get(recipient,1))
        why=None
        if recipient!='A' or f not in ['B','C']: why='UNAUTHORISED_ROUTE'
        elif not valid: why='EXPIRED_OR_STALE_OR_UNSUITABLE'
        elif surplus<pack: why='DONOR_DEMAND_AND_RESERVE'
        elif travel>deadline: why='ARRIVES_AFTER_DEPLETION'
        if why:
            rejected.append({'facility':f,'reason':why,'protected':protected,'free_stock':available}); continue
        variables=[]
        for b in valid:
            upper=min(surplus,b['on_hand']-b['reserved']-b['quarantined'])//pack
            x=model.new_int_var(0,upper,f"packs_{b['id']}"); variables.append(x)
            candidates.append((x,b,protected,travel,surplus))
        model.add(sum(variables)*pack<=surplus)
    total=sum(x*pack for x,*_ in candidates)
    model.add(total<=need)
    # One extra delivered pack must dominate every possible travel-cost difference.
    model.maximize(total*100000-sum(x*travel for x,b,p,travel,s in candidates))
    solver=cp_model.CpSolver(); solver.parameters.max_time_in_seconds=2; solver.parameters.num_search_workers=1
    status=solver.solve(model)
    lines=[]
    if status in [cp_model.OPTIMAL,cp_model.FEASIBLE]:
        for x,b,protected,travel,surplus in candidates:
            q=solver.value(x)*pack
            if q: lines.append({'batch':b['id'],'source':b['facility_id'],'destination':recipient,'quantity':q,'protected':protected,'travel_days':travel})
    result={'lines':lines,'unresolved':need-sum(l['quantity'] for l in lines),'need':need,'rejected':rejected,
        'status':solver.status_name(status),'policy':POLICY,'source':'synthetic computation','demand':demand}
    verify(result,batches,recipient,product,demand,clock,pack)
    result['verified']=True
    return result

def usable(b,clock): return b['expiry']>clock[:10] and b['quality']=='usable' and b['storage']=='suitable'

def verify(result,batches,recipient,product,demand,clock,pack):
    by_id={b['id']:b for b in batches}; seen=set(); by_donor={}
    for line in result['lines']:
        b=by_id[line['batch']]; q=line['quantity']
        if b['id'] in seen or q<=0 or q%pack or b['medicine_code']!=product or b['facility_id']==recipient: raise ValueError('Invalid product/quantity/duplicate')
        if not usable(b,clock) or q>b['on_hand']-b['reserved']-b['quarantined']: raise ValueError('Unusable or insufficient batch')
        if (datetime.fromisoformat(clock)-datetime.fromisoformat(b['observed_at'])).total_seconds()>86400: raise ValueError('Stale batch')
        if b['facility_id'] not in ['B','C'] or recipient!='A': raise ValueError('Route forbidden')
        stock=sum(x['on_hand']-x['reserved']-x['quarantined'] for x in batches if x['facility_id']==recipient and x['medicine_code']==product and usable(x,clock))
        if line['travel_days']>7*stock/max(1,demand.get(recipient,1)): raise ValueError('Late delivery')
        if b['expiry']<=(datetime.fromisoformat(clock)+timedelta(days=line['travel_days'])).date().isoformat(): raise ValueError('Expires before arrival')
        seen.add(b['id']); by_donor[b['facility_id']]=by_donor.get(b['facility_id'],0)+q
    for f,q in by_donor.items():
        stock=sum(b['on_hand']-b['reserved']-b['quarantined'] for b in batches if b['facility_id']==f and b['medicine_code']==product and usable(b,clock) and (datetime.fromisoformat(clock)-datetime.fromisoformat(b['observed_at'])).total_seconds()<=86400)
        if stock-q<math.ceil(demand.get(f,0))+(20 if f=='B' else 30): raise ValueError('Donor reserve violated')
    if sum(l['quantity'] for l in result['lines'])>result['need'] or result['unresolved']<0: raise ValueError('Over-allocation')
