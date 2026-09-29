import uuid
from concurrent.futures import ThreadPoolExecutor

def sandbox(client,state='A',scenario='GOLDEN'):
    response=client.post('/api/v1/demo/sessions',json={'state':state,'scenario':scenario})
    assert response.status_code==200,response.text
    return {'Authorization':'Bearer '+response.json()['token']}

def post(client,h,path,body=None,key=None,status=200):
    r=client.post('/api/v1/'+path,headers={**h,'Idempotency-Key':key or str(uuid.uuid4())},json=body or {})
    assert r.status_code==status,r.text
    return r.json()

def reserve(client,h):
    p=post(client,h,'plans')
    assert p['payload']['lines'][0]['source']=='C'
    assert p['payload']['lines'][0]['quantity']==60
    return post(client,h,'transfers',{'plan_id':p['id']})

def approve_dispatch(client,h,t):
    for district in ['D1','D2']:
        t=post(client,h,f"transfers/{t['id']}/approve",{'role':'approver','district':district,'expected_version':t['version']})
    return post(client,h,f"transfers/{t['id']}/dispatch",{'role':'custodian','district':'D2','expected_version':t['version']})

def stock_total(client,h): return sum(b['on_hand'] for b in client.get('/api/v1/inventory',headers=h).json() if b['medicine_code']=='MED-001')

def test_golden_partial_duplicate_and_conservation(client):
    h=sandbox(client); assert stock_total(client,h)==310
    t=reserve(client,h)
    post(client,h,f"transfers/{t['id']}/dispatch",{'role':'custodian','district':'D2','expected_version':t['version']},status=409)
    t=approve_dispatch(client,h,t); assert stock_total(client,h)==250
    body={'role':'receiver','district':'D1','expected_version':t['version'],'quantity':20}
    t=post(client,h,f"transfers/{t['id']}/receive",body,key='receipt-1')
    duplicate=post(client,h,f"transfers/{t['id']}/receive",body,key='receipt-1')
    assert duplicate==t and t['status']=='partially_received' and stock_total(client,h)==270
    post(client,h,f"transfers/{t['id']}/receive",{**body,'quantity':21},key='receipt-1',status=409)
    t=post(client,h,f"transfers/{t['id']}/receive",{**body,'expected_version':t['version'],'quantity':40})
    assert stock_total(client,h)==310 and t['received']==60
    # Consume actual post-receipt batches; 260 units consumed leaves 50.
    inv=client.get('/api/v1/inventory',headers=h).json()
    for facility,need,dist in [('A',100,'D1'),('B',100,'D1'),('C',60,'D2')]:
        for b in [b for b in inv if b['facility_id']==facility and b['medicine_code']=='MED-001']:
            q=min(need,b['on_hand']); need-=q
            if q: post(client,h,'stock-events',{'role':'custodian','district':dist,'expected_version':b['version'],'batch':b['id'],'quantity':q,'mode':'consume','observed_at':'2026-09-27T09:00:00+00:00','reason':'Synthetic demand consumption'})
        assert need==0
    assert stock_total(client,h)==50

def test_isolation_roles_and_concurrent_reservation(client):
    h=sandbox(client); other=sandbox(client); state_b=sandbox(client,'B')
    p=post(client,h,'plans')
    post(client,other,'transfers',{'plan_id':p['id']},status=404)
    post(client,state_b,'transfers',{'plan_id':p['id']},status=404)
    post(client,h,'transfers',{'plan_id':p['id'],'role':'receiver'},status=403)
    def run(_): return client.post('/api/v1/transfers',headers={**h,'Idempotency-Key':str(uuid.uuid4())},json={'plan_id':p['id']}).status_code
    with ThreadPoolExecutor(max_workers=2) as pool: statuses=list(pool.map(run,range(2)))
    assert sorted(statuses)==[200,409]
    assert len(client.get('/api/v1/transfers',headers=other).json())==0

def test_capacity_offline_conflict_cancel_expiry(client):
    h=sandbox(client)
    post(client,h,'capacity',{'role':'custodian','facility_id':'A','physical_beds':3,'operational_beds':4},status=422)
    b={'role':'custodian','facility_id':'A','physical_beds':12,'operational_beds':10,'occupied_beds':6,'footfall':100}
    post(client,h,'capacity',b); post(client,h,'capacity',b,status=409)
    t=reserve(client,h)
    post(client,h,'demo/clock',{'hours':1})
    t=client.get('/api/v1/transfers',headers=h).json()[0]
    assert t['status']=='expired'
    assert all(b['reserved']==0 for b in client.get('/api/v1/inventory',headers=h).json())

def test_stale_snapshot_and_no_unconfirmed_write(client):
    h=sandbox(client)
    csv='batch,quantity,unit,mode,observed_at\nA-MED-001,50,tablet,snapshot,2026-09-27T09:00:00+00:00'
    d=post(client,h,'imports/preview',{'role':'custodian','csv':csv})
    assert stock_total(client,h)==310
    o=d['payload']['rows'][0]['observation']
    post(client,h,'imports/confirm',{'role':'custodian','draft_id':d['id'],'observations':[o]})
    assert stock_total(client,h)==320
    post(client,h,'stock-events',o,status=409)

def test_token_and_idempotency_required(client):
    assert client.get('/api/v1/inventory').status_code==401
    h=sandbox(client)
    assert client.post('/api/v1/plans',headers=h,json={}).status_code==422

def test_network_plan_reserves_all_lines_atomically(client):
    h=sandbox(client)
    for f,q,d in [('A',50,'D1'),('B',50,'D1'),('C',200,'D2')]:
        post(client,h,'stock-events',{'role':'custodian','district':d,'batch':f+'-MED-001','quantity':q,'mode':'snapshot','observed_at':'2026-09-27T09:00:00+00:00','reason':'Synthetic network fixture'})
    p=post(client,h,'plans',{'recipient':'*'})
    assert len(p['payload']['lines'])==2
    result=post(client,h,'plans/'+p['id']+'/reserve')
    assert len(result['transfers'])==2
    inv=client.get('/api/v1/inventory',headers=h).json()
    donor=next(b for b in inv if b['id']=='C-MED-001')
    assert donor['reserved']==100 and donor['on_hand']==200
    post(client,h,'plans/'+p['id']+'/reserve',status=409)
