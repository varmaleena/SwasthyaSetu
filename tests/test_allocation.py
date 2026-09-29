from allocation.solver import solve
from allocation.network import solve_network,verify_network
import pytest

def batches():
    return [dict(id=f,facility_id=f,medicine_code='MED-001',on_hand=q,reserved=0,quarantined=0,quality='usable',storage='suitable',expiry='2027-01-01',observed_at='2026-09-27T09:00:00+00:00') for f,q in [('A',40),('B',120),('C',150)]]
def run(b,scenario='GOLDEN'): return solve(b,'A','MED-001',{'A':100,'B':100,'C':60},'2026-09-27T09:00:00+00:00',scenario)
def test_golden_and_variations():
    b=batches(); assert run(b)['lines'][0]['quantity']==60
    b[-1]['on_hand']=130
    assert run(b)['lines'][0]['quantity']==40 and run(b)['unresolved']==20
    b[-1]['expiry']='2026-09-26'; assert run(b)['unresolved']==60
    b=batches(); b[-1]['observed_at']='2026-09-25T00:00:00+00:00'; assert run(b)['unresolved']==60
    assert run(batches(),'S06')['unresolved']==60

def test_network_protects_shared_donor_across_recipients():
    b=batches();b[0]['on_hand']=50;b[1]['on_hand']=50;b[2]['on_hand']=200
    demand={'A':110,'B':110,'C':60}
    r=solve_network(b,'MED-001',demand,'2026-09-27T09:00:00+00:00')
    assert r['verified'] and sum(l['quantity'] for l in r['lines'])==110
    assert set(l['destination'] for l in r['lines'])=={'A','B'}
    assert r['unresolved']==10
    bad=[{**l,'quantity':l['quantity']+100} for l in r['lines']]
    with pytest.raises(ValueError):verify_network(bad,b,'MED-001',demand,'2026-09-27T09:00:00+00:00',10)
