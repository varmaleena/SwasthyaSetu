import io,wave
import pytest
from ai.provider import validate_media,Extraction
from services.api.domain import DomainError
from federation.coordinator import aggregate
from tests.test_workflow import sandbox,post,stock_total

def test_no_fake_ai_or_unconfirmed_stock(client):
    h=sandbox(client)
    post(client,h,'extract',{'role':'custodian','evidence_id':'not-in-sandbox'},status=404)
    assert stock_total(client,h)==310

def test_scoped_evidence_and_disabled_provider(client,monkeypatch):
    from PIL import Image
    monkeypatch.delenv('GEMINI_API_KEY',raising=False)
    monkeypatch.setenv('APP_ENV','local')
    h=sandbox(client); other=sandbox(client)
    data=io.BytesIO();Image.new('RGB',(20,20),'white').save(data,format='PNG')
    r=client.post('/api/v1/evidence',headers={**h,'Idempotency-Key':'upload-test'},files={'file':('fictional.png',data.getvalue(),'image/png')})
    assert r.status_code==200,r.text
    eid=r.json()['id']
    assert client.get('/api/v1/evidence/'+eid,headers=other).status_code==404
    post(client,h,'extract',{'role':'custodian','evidence_id':eid},status=503)
    assert stock_total(client,h)==310

def test_media_validated_by_bytes_and_duration():
    with pytest.raises(DomainError): validate_media(b'<script>bad</script>')
    for seconds in [2,21]:
        data=io.BytesIO()
        with wave.open(data,'wb') as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000); w.writeframes(b'\0\0'*16000*seconds)
        if seconds==2: assert validate_media(data.getvalue())=='audio/wav'
        else:
            with pytest.raises(DomainError): validate_media(data.getvalue())

def test_coordinator_rejects_raw_rows_nonfinite_and_bad_shape():
    good={'state':'A','schema':'count-v1:intercept,weekend,log-footfall','coefficients':[2.,0.,1.],'sample_count':100,'validation_mae':2.}
    other={**good,'state':'B'}
    assert aggregate([good,other])['coefficients']==[2,0,1]
    for bad in [{**good,'raw_rows':[]},{**good,'coefficients':[float('nan'),0,1]},{**good,'coefficients':[1,2]},{**good,'sample_count':5001}]:
        with pytest.raises(ValueError): aggregate([bad,other])
