from tests.test_workflow import sandbox,post

def test_exact_catalogue_units_and_explicit_pack_conversion(client):
    h=sandbox(client)
    text='batch,quantity,unit,pack_size,mode,observed_at\nA-MED-002,5,packs,10,snapshot,2026-09-27T09:00:00+00:00\n'
    d=post(client,h,'imports/preview',{'role':'custodian','csv':text})
    row=d['payload']['rows'][0];assert not row['errors'] and row['observation']['quantity']==50
    post(client,h,'imports/confirm',{'role':'custodian','draft_id':d['id'],'observations':[row['observation']]})
    bad=post(client,h,'imports/preview',{'role':'custodian','csv':text.replace('packs,10','packs,12')})
    assert bad['payload']['rows'][0]['errors']
