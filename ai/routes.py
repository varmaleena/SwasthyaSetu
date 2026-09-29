import hashlib, os, time
from fastapi import Request, UploadFile, File
from fastapi.responses import Response
from services.api.contracts import ExtractInput, Actor
from services.api.models import Record, Budget
from services.api.db import transaction
from services.api.domain import record, uid, role, get, serial, budget, fail, iso_now, DomainError
from ai.provider import validate_media, extract
from ai.storage import store, load

def register(app,read,mutate,auth):
    @app.post('/api/v1/evidence')
    async def evidence(request:Request,file:UploadFile=File(...)):
        # Bound the read; do not trust Content-Type or file extension.
        data=await file.read(2*1024*1024+1); mime=validate_media(data)
        class Upload(Actor):
            hash: str
        body=Upload(role='custodian',hash=hashlib.sha256(data).hexdigest())
        def run(db,st,sid,s):
            budget(db,'uploads:'+sid,8)
            db.get(Budget,'ai-guard',with_for_update=True)
            storage_budget=db.get(Budget,'evidence-bytes',with_for_update=True)
            if storage_budget is None:
                storage_budget=Budget(id='evidence-bytes',count=0);db.add(storage_budget);db.flush()
            if storage_budget.count+len(data)>45*1024*1024:
                fail('STORAGE_QUOTA','State evidence budget reached. Owner cleanup is required; manual entry still works.',429)
            storage_budget.count+=len(data)
            eid=uid(); stored=store(st,sid,eid,data,mime)
            r=record(db,st,sid,'evidence',{'storage':stored,'mime':mime,'hash':body.hash,'captured_at':iso_now(),'source':'synthetic user upload'},eid)
            return {'id':r.id,'mime':mime,'hash':body.hash,'source':'synthetic'}
        return mutate(request,body,'evidence',run)

    @app.get('/api/v1/evidence/{id}')
    def download(id:str,request:Request):
        def run(db,st,sid,s):
            r=get(db,Record,st,sid,id)
            if r.kind!='evidence': fail('NOT_FOUND','Evidence not found',404)
            return Response(load(st,r.payload['storage']),media_type=r.payload['mime'],headers={'Content-Disposition':'attachment; filename="synthetic-evidence"'})
        return read(request,run)

    @app.post('/api/v1/extract')
    def extraction(body:ExtractInput,request:Request):
        def run(db,st,sid,s):
            role(body,['custodian']); r=get(db,Record,st,sid,body.evidence_id)
            if r.kind!='evidence': fail('NOT_FOUND','Evidence not found',404)
            if not os.getenv('GEMINI_API_KEY') or os.getenv('GEMINI_FREE_TIER_VERIFIED')!='true' or not os.getenv('GEMINI_MODEL_ID'):
                fail('AI_NOT_CONFIGURED','Configure server-side Gemini free-tier credentials; manual reporting works now.',503)
            budget(db,'ai-session:'+sid,6)
            def global_quota(qdb):
                qdb.get(Budget,'ai-guard',with_for_update=True)
                budget(qdb,'ai-global:'+time.strftime('%Y-%m-%d',time.gmtime()),min(100,int(os.getenv('AI_GLOBAL_DAILY_LIMIT','0'))))
            if st=='A': global_quota(db)
            else:
                with transaction(app.state.engines['A']) as qdb: global_quota(qdb)
            started=time.perf_counter()
            try:
                draft,meta=extract(load(st,r.payload['storage']),r.payload['mime'])
                payload={**draft,'metadata':{**meta,'request_time':iso_now(),'latency_seconds':round(time.perf_counter()-started,3)},'source_id':r.id,'confirmed':False}
                return serial(record(db,st,sid,'extraction',payload))
            except Exception as e:
                # Commit the consumed quota and a truthful failure. No stock write, no synthetic response.
                payload={'status':'failed','message':'Provider or media retrieval failed. Use manual entry; no stock changed.',
                    'error_type':type(e).__name__,'requested_at':iso_now(),'live_success':False,'source_id':r.id}
                return serial(record(db,st,sid,'extraction_failure',payload))
        return mutate(request,body,'extract',run)
