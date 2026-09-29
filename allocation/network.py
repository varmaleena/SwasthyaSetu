"""Multi-recipient allocation with lexicographic unmet, equity, transport/expiry objectives."""
from datetime import datetime,timedelta
import math
from ortools.sat.python import cp_model
from allocation.solver import usable,POLICY

DISTRICTS={'A':'D1','B':'D1','C':'D2','D':'D1','E':'D1','F':'D2','G':'D2','H':'D2'}
def solve_network(batches,product,demand,clock,pack=10):
    now=datetime.fromisoformat(clock)
    rows=[b for b in batches if b['medicine_code']==product and usable(b,clock) and (now-datetime.fromisoformat(b['observed_at'])).total_seconds()<=86400]
    stock={f:sum(b['on_hand']-b['reserved']-b['quarantined'] for b in rows if b['facility_id']==f) for f in DISTRICTS}
    needs={f:max(0,math.ceil(demand.get(f,0)-stock[f])) for f in DISTRICTS}
    protected={f:math.ceil(demand.get(f,0))+(20 if f=='B' else 30) for f in DISTRICTS}
    model=cp_model.CpModel(); variables=[]
    for b in rows:
        donor=b['facility_id']; surplus=max(0,stock[donor]-protected[donor])
        if surplus<pack:continue
        for dest,need in needs.items():
            if not need or DISTRICTS[donor]==DISTRICTS[dest]:continue
            travel=1+abs(ord(donor)-ord(dest))%3
            if travel>7*stock[dest]/max(1,demand.get(dest,1)) or b['expiry']<=(now+timedelta(days=travel)).date().isoformat():continue
            x=model.new_int_var(0,min(surplus,need,b['on_hand']-b['reserved']-b['quarantined'])//pack,f"{b['id']}->{dest}")
            variables.append((x,b,dest,travel))
    for f in DISTRICTS:
        model.add(sum(x*pack for x,b,d,t in variables if b['facility_id']==f)<=max(0,stock[f]-protected[f]))
    for b in rows:model.add(sum(x*pack for x,row,d,t in variables if row['id']==b['id'])<=b['on_hand']-b['reserved']-b['quarantined'])
    remaining={}
    for f,need in needs.items():
        r=model.new_int_var(0,need,'unmet_'+f); model.add(r==need-sum(x*pack for x,b,d,t in variables if d==f));remaining[f]=r
    burden=model.new_int_var(0,1000,'max_shortage_fraction')
    for f,need in needs.items():
        if need:model.add(remaining[f]*1000<=burden*need)
    objectives=[sum(remaining.values()),burden,sum(x*(t*100+min(99,(datetime.fromisoformat(b['expiry'])-now.replace(tzinfo=None)).days)) for x,b,d,t in variables)]
    solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=.6;solver.parameters.num_search_workers=1
    statuses=[];solution=[]
    for objective in objectives:
        model.minimize(objective);status=solver.solve(model);statuses.append(solver.status_name(status))
        if status not in [cp_model.OPTIMAL,cp_model.FEASIBLE]:break
        solution=[{'batch':b['id'],'source':b['facility_id'],'destination':d,'quantity':solver.value(x)*pack,'protected':protected[b['facility_id']],'travel_days':t} for x,b,d,t in variables if solver.value(x)>0]
        if status!=cp_model.OPTIMAL:break
        model.add(objective==int(solver.value(objective)))
    verify_network(solution,batches,product,demand,clock,pack)
    unmet={f:n-sum(l['quantity'] for l in solution if l['destination']==f) for f,n in needs.items()}
    return {'lines':solution,'need':sum(needs.values()),'unresolved':sum(unmet.values()),'unresolved_by_facility':unmet,'rejected':[],
        'status':'OPTIMAL' if len(statuses)==3 and all(s=='OPTIMAL' for s in statuses) else 'VERIFIED_FEASIBLE' if solution else 'NO_PLAN',
        'stage_statuses':statuses,'verified':True,'demand':demand,'policy':{**POLICY,'objective':'lexicographic unmet units, max relative shortage, transport/expiry','weights':'all facilities weight 1; synthetic engineering policy'},'source':'synthetic network computation'}

def verify_network(lines,batches,product,demand,clock,pack):
    now=datetime.fromisoformat(clock); by_id={b['id']:b for b in batches}; allocated={};outgoing={};incoming={};seen=set()
    valid=[b for b in batches if b['medicine_code']==product and usable(b,clock) and (now-datetime.fromisoformat(b['observed_at'])).total_seconds()<=86400]
    stock={f:sum(b['on_hand']-b['reserved']-b['quarantined'] for b in valid if b['facility_id']==f) for f in DISTRICTS}
    for line in lines:
        b=by_id[line['batch']];src,dst,q=line['source'],line['destination'],line['quantity'];pair=(b['id'],dst)
        if pair in seen or b not in valid or src!=b['facility_id'] or q<=0 or q%pack or src not in DISTRICTS or dst not in DISTRICTS or DISTRICTS[src]==DISTRICTS[dst]:raise ValueError('Invalid network line')
        if line['travel_days']!=1+abs(ord(src)-ord(dst))%3 or line['travel_days']>7*stock[dst]/max(1,demand.get(dst,1)):raise ValueError('Late/incorrect route')
        if b['expiry']<=(now+timedelta(days=line['travel_days'])).date().isoformat():raise ValueError('Expiry before arrival')
        seen.add(pair);allocated[b['id']]=allocated.get(b['id'],0)+q;outgoing[src]=outgoing.get(src,0)+q;incoming[dst]=incoming.get(dst,0)+q
    for bid,q in allocated.items():
        b=by_id[bid]
        if q>b['on_hand']-b['reserved']-b['quarantined']:raise ValueError('Batch overallocated')
    for f,q in outgoing.items():
        if stock[f]-q<math.ceil(demand.get(f,0))+(20 if f=='B' else 30):raise ValueError('Donor protection failed')
    for f,q in incoming.items():
        if q>max(0,math.ceil(demand.get(f,0)-stock[f])):raise ValueError('Recipient overallocated')
