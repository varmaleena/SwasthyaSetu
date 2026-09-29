import os,uuid
import httpx

def main():
    base=os.getenv('DEMO_API_URL','http://localhost:8000')
    with httpx.Client(base_url=base,timeout=60) as c:
        c.get('/health/ready').raise_for_status()
        s=c.post('/api/v1/demo/sessions',json={'scenario':'GOLDEN','state':'A'});s.raise_for_status()
        c.headers['Authorization']='Bearer '+s.json()['token']
        def post(path,body):
            r=c.post('/api/v1/'+path,json=body,headers={'Idempotency-Key':str(uuid.uuid4())});r.raise_for_status();return r.json()
        p=post('plans',{}); t=post('transfers',{'plan_id':p['id']})
        for d in ['D1','D2']: t=post(f"transfers/{t['id']}/approve",{'role':'approver','district':d,'expected_version':t['version']})
        t=post(f"transfers/{t['id']}/dispatch",{'role':'custodian','district':'D2','expected_version':t['version']})
        t=post(f"transfers/{t['id']}/receive",{'role':'receiver','district':'D1','quantity':60,'expected_version':t['version']})
        assert t['received']==60
        print(f'Actual API workflow passed at {base}. This does not verify live AI, cold start, or browser CORS.')
if __name__=='__main__': main()
