from sqlalchemy import select
from data.generate import generate
from services.api.db import transaction
from services.api.models import History
from tests.test_workflow import sandbox,post

def test_forecast_s02_s03_s08_and_resumable_round(client):
    rows,_=generate()
    for state,engine in client.app.state.engines.items():
        with transaction(engine) as db:
            db.add_all([History(state_id=state,facility=r['facility'],medicine=r['medicine'],day=r['day'],payload=r)
                for r in rows if r['state']==state and r['day']<180])
    for scenario in ['S02','S03','S08']:
        h=sandbox(client,scenario=scenario)
        f=post(client,h,'forecast')
        assert f['payload']['items']['A']['sample_count']==100
        assert all(a<=b<=c for a,b,c in zip(f['payload']['items']['A']['p10'],f['payload']['items']['A']['p50'],f['payload']['items']['A']['p90']))
        p=post(client,h,'plans',{'forecast_id':f['id']})
        assert p['payload']['verified'] and p['payload']['unresolved']>=0
        assert all(l['source']!='B' for l in p['payload']['lines'])
        if scenario=='S08': assert not p['payload']['lines'] and p['payload']['unresolved']>0
    j=post(client,h,'model-rounds')
    for checkpoint in range(3):
        # Round state is reloaded through the API before each next step.
        saved=client.get('/api/v1/jobs/'+j['id'],headers=h).json()
        assert saved['payload']['checkpoint']==checkpoint
        j=post(client,h,'jobs/'+j['id']+'/advance',{'expected_version':saved['version']})
    assert j['payload']['status']=='completed' and len(j['payload']['decisions'])==2
