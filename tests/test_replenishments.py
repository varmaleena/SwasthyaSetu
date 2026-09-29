from tests.test_workflow import sandbox,post,stock_total
from forecasting.model import forecast
from data.generate import generate

def test_arrival_is_not_stock_until_confirmed_and_is_idempotent(client):
    h=sandbox(client,scenario='S01');rows=client.get('/api/v1/replenishments',headers=h).json();r=rows[0]
    assert stock_total(client,h)==310
    post(client,h,'replenishments/'+r['id']+'/receive',{'role':'custodian'},status=409)
    post(client,h,'demo/clock',{'hours':24})
    body={'role':'custodian','expected_version':1}
    post(client,h,'replenishments/'+r['id']+'/receive',body,key='arrival')
    post(client,h,'replenishments/'+r['id']+'/receive',body,key='arrival')
    assert stock_total(client,h)==390

def test_supply_forecast_preserves_early_shortage_risk():
    rows,_=generate();history=[r for r in rows if r['state']=='A' and r['facility']=='A' and r['medicine']=='MED-001' and r['day']<180]
    no_supply=forecast(history,0)
    late=forecast(history,0,replenishments=[{'quantity':10000,'eta_min_days':10,'eta_max_days':12}])
    assert no_supply['risk_14d']==1 and late['risk_14d']==1
