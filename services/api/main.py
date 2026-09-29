import csv, io, json, os, time, uuid
from contextlib import asynccontextmanager
from datetime import timedelta
from pathlib import Path
from fastapi import FastAPI, Request, Header, UploadFile, File
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, func, delete
from sqlalchemy.exc import SQLAlchemyError
from services.api.db import engines_from_env, transaction, check_schema
from services.api.models import *
from services.api.contracts import *
from services.api.domain import *
from services.api.security import secret, sign, verify
from data.generate import seed_session, SCENARIOS
from allocation.solver import solve
from allocation.network import solve_network
from forecasting.model import forecast

def create_app(engines=None,token_secret=None):
    @asynccontextmanager
    async def lifespan(app):
        if engines is None and not all(check_schema(e) for e in app.state.engines.values()):
            raise RuntimeError('Apply migrations to both state databases before startup')
        yield
    app=FastAPI(title='SwasthyaSetu synthetic prototype',version='0.1.0',lifespan=lifespan)
    app.state.engines=engines or engines_from_env(); app.state.key=token_secret or secret()
    app.add_middleware(CORSMiddleware,allow_origins=os.getenv('ALLOWED_ORIGINS','http://localhost:5173').split(','),
        allow_methods=['GET','POST'],allow_headers=['Authorization','Content-Type','Idempotency-Key'])

    @app.middleware('http')
    async def headers(request,call_next):
        if int(request.headers.get('content-length','0'))>3_000_000:
            return JSONResponse(status_code=413,content={'code':'TOO_LARGE','message':'Maximum request size is 3 MB','field_errors':[],'retryable':False,'trace_id':uid()})
        response=await call_next(request)
        response.headers['Cache-Control']='no-store'; response.headers['X-Content-Type-Options']='nosniff'
        return response

    def error(code,message,status,fields=None): return JSONResponse(status_code=status,content={'code':code,'message':message,'field_errors':fields or [],'retryable':status in [429,503],'trace_id':uid()})
    @app.exception_handler(DomainError)
    async def domain_error(_,e): return error(e.code,e.message,e.status)
    @app.exception_handler(RequestValidationError)
    async def validation_error(_,e): return error('VALIDATION','Review the highlighted fields',422,[{'field':str(x['loc']),'message':x['msg']} for x in e.errors()])
    @app.exception_handler(SQLAlchemyError)
    async def database_error(_,e): return error('DATABASE_UNAVAILABLE','Database operation failed; no success is implied. Retry after checking service readiness.',503)

    def auth(request):
        try:
            token=request.headers.get('authorization','').removeprefix('Bearer ')
            p=verify(token,app.state.key)
        except (ValueError,KeyError,TypeError): fail('UNAUTHORISED','Session missing or expired. Start a sandbox.',401)
        return p['state'],p['sid']

    def read(request,fn):
        state,sid=auth(request)
        with transaction(app.state.engines[state]) as db:
            s=db.get(DemoSession,(state,sid))
            if not s or s.expires<time.time(): fail('SESSION_EXPIRED','Start a new sandbox',401)
            return fn(db,state,sid,s)

    def mutate(request,body,operation,fn):
        state,sid=auth(request)
        with transaction(app.state.engines[state]) as db:
            return command(db,state,sid,request.headers.get('idempotency-key'),operation,body,lambda s:fn(db,state,sid,s))

    @app.get('/health/live')
    def live(): return {'status':'alive','build':os.getenv('BUILD_SHA','local')}
    @app.get('/health/ready')
    def ready():
        try:
            states={s:check_schema(e) for s,e in app.state.engines.items()}
            if not all(states.values()): fail('SCHEMA_MISMATCH','Run migrations for both states',503)
        except SQLAlchemyError: fail('DATABASE_UNAVAILABLE','State databases are unavailable or unmigrated',503)
        return {'status':'ready','states':states,'persistence':'local development SQLite' if any(e.dialect.name=='sqlite' for e in app.state.engines.values()) else 'separate PostgreSQL databases',
            'ai_configured':bool(os.getenv('GEMINI_API_KEY')) and os.getenv('GEMINI_FREE_TIER_VERIFIED')=='true','source':'synthetic','build':os.getenv('BUILD_SHA','local')}

    @app.get('/api/v1/scenarios')
    def scenarios(): return SCENARIOS

    @app.post('/api/v1/demo/sessions')
    def new_session(body:NewSession,request:Request):
        if body.scenario not in SCENARIOS: fail('UNKNOWN_SCENARIO','Select a supported scenario',422)
        state=body.state; sid=uid(); expiry=time.time()+86400
        with transaction(app.state.engines[state]) as db:
            # Pre-created global guard serializes quota creation across workers/processes.
            guard=db.get(Budget,'session-guard',with_for_update=True)
            if guard is None: fail('SEED_REQUIRED','Run seed before creating sessions',503)
            if db.scalar(select(func.count()).select_from(DemoSession).where(DemoSession.expires>=time.time()))>=40:
                fail('SANDBOX_CAPACITY','This free demo state has 40 active sandboxes. Try later or select the other fictional state.',429)
            budget(db,'session-day:'+time.strftime('%Y-%m-%d',time.gmtime()),200)
            ip=digest({'ip':request.client.host if request.client else 'unknown'})[:24]
            budget(db,'session-ip:'+ip+':'+str(int(time.time()//3600)),100 if os.getenv('APP_ENV','local')=='local' else 10)
            # Small expired-session cleanup chunk; no keepalive scheduler.
            expired=db.scalars(select(DemoSession).where(DemoSession.expires<time.time()).limit(5)).all()
            for old in expired:
                for table in [Command,StockEvent,Transfer,Record,Balance,Facility]:
                    db.execute(delete(table).where(table.state_id==state,table.session_id==old.id))
                db.delete(old)
                for prefix in ['commands:','bytes:','forecast:','plans:','rounds:','uploads:','ai-session:']:
                    db.execute(delete(Budget).where(Budget.id==prefix+old.id))
            db.add(DemoSession(state_id=state,id=sid,expires=expiry,scenario=body.scenario)); db.flush()
            seed_session(db,state,sid,body.scenario)
        return {'session_id':sid,'state':state,'expires':expiry,'scenario':body.scenario,'token':sign({'sid':sid,'state':state,'exp':expiry},app.state.key),'synthetic':True}

    @app.get('/api/v1/session')
    def session(request:Request):
        return read(request,lambda db,state,sid,s:{'id':sid,'state':state,'scenario':s.scenario,'scenario_clock':s.scenario_clock,'version':s.version,'expires':s.expires})

    @app.post('/api/v1/demo/reset')
    def reset(body:Actor,request:Request):
        def run(db,state,sid,s):
            check_version(s,body.expected_version)
            for table in [StockEvent,Transfer,Record,Balance,Facility]: db.execute(delete(table).where(table.state_id==state,table.session_id==sid))
            s.scenario_clock='2026-09-27T09:00:00+00:00'; s.version+=1
            seed_session(db,state,sid,s.scenario)
            return {'reset':True,'version':s.version}
        return mutate(request,body,'reset',run)

    @app.post('/api/v1/demo/clock')
    def clock(body:ClockInput,request:Request):
        def run(db,state,sid,s):
            check_version(s,body.expected_version); s.scenario_clock=(parse_time(s.scenario_clock)+timedelta(hours=body.hours)).isoformat(); s.version+=1
            expire_reservations(db,state,sid,s.scenario_clock)
            return {'scenario_clock':s.scenario_clock,'version':s.version}
        return mutate(request,body,'clock',run)

    @app.get('/api/v1/catalogue')
    def catalogue(request:Request): return read(request,lambda db,*_:[serial(x) for x in db.scalars(select(Medicine)).all()])
    @app.get('/api/v1/facilities')
    def facilities(request:Request): return read(request,lambda db,st,sid,s:[serial(x) for x in db.scalars(scoped(db,Facility,st,sid)).all()])
    @app.get('/api/v1/inventory')
    def inventory(request:Request): return read(request,lambda db,st,sid,s:[serial(x) for x in db.scalars(scoped(db,Balance,st,sid)).all()])
    @app.get('/api/v1/transfers')
    def transfers(request:Request): return read(request,lambda db,st,sid,s:[serial(x) for x in db.scalars(scoped(db,Transfer,st,sid)).all()])
    @app.get('/api/v1/readiness')
    def readiness(request:Request): return read(request,lambda db,st,sid,s:[serial(x) for x in db.scalars(scoped(db,Record,st,sid).where(Record.kind=='capacity')).all()])
    @app.get('/api/v1/audit')
    def audit(request:Request): return read(request,lambda db,st,sid,s:[serial(x) for x in db.scalars(scoped(db,Record,st,sid).where(Record.kind=='audit')).all()])
    @app.get('/api/v1/ledger')
    def ledger(request:Request): return read(request,lambda db,st,sid,s:[serial(x) for x in db.scalars(scoped(db,StockEvent,st,sid)).all()])

    @app.post('/api/v1/stock-events')
    def stock(body:StockInput,request:Request): return mutate(request,body,'stock',lambda db,st,sid,s:update_stock(db,st,sid,body,s))
    @app.post('/api/v1/capacity')
    def capacity(body:CapacityInput,request:Request):
        def run(db,st,sid,s):
            role(body,['custodian']); district(db,st,sid,body.facility_id,body)
            r=get(db,Record,st,sid,'capacity-'+body.facility_id,True); check_version(r,body.expected_version)
            r.payload={**body.model_dump(exclude={'role','district','expected_version'}),'observed_at':s.scenario_clock,'source':'synthetic'}; r.version+=1
            return serial(r)
        return mutate(request,body,'capacity',run)

    @app.post('/api/v1/forecast')
    def forecast_run(body:PlanInput,request:Request):
        def run(db,st,sid,s):
            role(body,['planner']); budget(db,'forecast:'+sid,30)
            balances=db.scalars(scoped(db,Balance,st,sid).where(Balance.medicine_code==body.product)).all()
            result={}
            context_versions={}
            for facility in sorted({b.facility_id for b in balances}):
                history=[r.payload for r in db.scalars(select(History).where(History.state_id==st,History.facility==facility,History.medicine==body.product).order_by(History.day)).all()]
                if not history: fail('HISTORY_MISSING','Run synthetic seed',503)
                cap=get(db,Record,st,sid,'capacity-'+facility)
                context_versions[cap.id]=cap.version
                ff=cap.payload['footfall']
                if s.scenario=='S04': ff=(ff or 50)*2
                deliveries=[]
                for r in db.scalars(scoped(db,Record,st,sid).where(Record.kind=='replenishment')).all():
                    p=r.payload
                    context_versions[r.id]=r.version
                    if p['facility_id']==facility and p['product']==body.product and p['status']=='scheduled' and parse_time(p['eta_max'])>=parse_time(s.scenario_clock):
                        deliveries.append({'quantity':p['quantity'],'eta_min_days':max(0,int((parse_time(p['eta_min'])-parse_time(s.scenario_clock)).total_seconds()/86400)), 'eta_max_days':max(0,int((parse_time(p['eta_max'])-parse_time(s.scenario_clock)).total_seconds()/86400))})
                result[facility]=forecast(history,sum(b.on_hand-b.reserved-b.quarantined for b in balances if b.facility_id==facility and b.quality=='usable' and b.expiry>s.scenario_clock[:10]),ff,replenishments=deliveries)
            r=record(db,st,sid,'forecast',{'items':result,'product':body.product,'computed_at':iso_now(),'scenario_clock':s.scenario_clock,
                'versions':{b.id:b.version for b in balances},'context_versions':context_versions,'source':'synthetic'})
            return serial(r)
        return mutate(request,body,'forecast',run)

    @app.post('/api/v1/plans')
    def plans(body:PlanInput,request:Request):
        def run(db,st,sid,s):
            role(body,['planner']); budget(db,'plans:'+sid,40)
            batches=[serial(b) for b in db.scalars(scoped(db,Balance,st,sid).order_by(Balance.id)).all()]
            context_versions={}
            if s.scenario=='GOLDEN': demand={'A':100,'B':100,'C':60}
            else:
                if not body.forecast_id: fail('FORECAST_REQUIRED','Run numerical analysis before planning',422)
                fr=get(db,Record,st,sid,body.forecast_id)
                if fr.kind!='forecast' or fr.payload['product']!=body.product: fail('FORECAST_MISMATCH','Forecast product differs')
                for bid,v in fr.payload['versions'].items(): check_version(get(db,Balance,st,sid,bid),v)
                context_versions=fr.payload.get('context_versions',{})
                for rid,v in context_versions.items():check_version(get(db,Record,st,sid,rid),v)
                if fr.payload['scenario_clock']!=s.scenario_clock:fail('STALE_FORECAST','Scenario time advanced; recompute analysis')
                demand={f:item['protected_7d'] for f,item in fr.payload['items'].items()}
                # Only reduce the recipient's shortage for expected inbound supply. Donor protection stays conservative.
                if body.recipient in demand:demand[body.recipient]=fr.payload['items'][body.recipient]['net_required_7d']
            medicine=db.get(Medicine,body.product)
            if not medicine: fail('CATALOGUE_MISMATCH','Unknown exact product',422)
            result=solve_network(batches,body.product,demand,s.scenario_clock,medicine.pack_size) if body.recipient=='*' else solve(batches,body.recipient,body.product,demand,s.scenario_clock,s.scenario,medicine.pack_size)
            result.update(versions={b['id']:b['version'] for b in batches},context_versions=context_versions,expires=(parse_time(s.scenario_clock)+timedelta(hours=2)).isoformat(),snapshot_hash=digest(batches))
            return serial(record(db,st,sid,'plan',result))
        return mutate(request,body,'plan',run)

    @app.post('/api/v1/transfers')
    def create_transfer(body:TransferInput,request:Request): return mutate(request,body,'reserve',lambda db,st,sid,s:reserve(db,st,sid,body,s))
    @app.post('/api/v1/plans/{id}/reserve')
    def reserve_all(id:str,body:Actor,request:Request):
        def run(db,st,sid,s):
            p=get(db,Record,st,sid,id)
            if p.kind!='plan' or not p.payload['lines']:fail('NO_SUPPLY','No feasible lines to reserve')
            output=[]
            for i,line in enumerate(p.payload['lines']):
                output.append(reserve(db,st,sid,TransferInput(**body.model_dump(),plan_id=id,line_index=i),s,verify_snapshot=i==0))
            return {'transfers':output}
        return mutate(request,body,'reserve-plan:'+id,run)

    @app.get('/api/v1/replenishments')
    def replenishments(request:Request):return read(request,lambda db,st,sid,s:[serial(r) for r in db.scalars(scoped(db,Record,st,sid).where(Record.kind=='replenishment')).all()])
    @app.post('/api/v1/replenishments')
    def schedule(body:ReplenishmentInput,request:Request):
        def run(db,st,sid,s):
            role(body,['planner']);b=get(db,Balance,st,sid,body.batch);district(db,st,sid,b.facility_id,body);check_version(b,body.expected_version)
            return serial(record(db,st,sid,'replenishment',{'batch':b.id,'facility_id':b.facility_id,'product':b.medicine_code,'quantity':body.quantity,'eta_min':(parse_time(s.scenario_clock)+timedelta(days=body.eta_min_days)).isoformat(),'eta_max':(parse_time(s.scenario_clock)+timedelta(days=body.eta_max_days)).isoformat(),'status':'scheduled','source':'synthetic incoming supply'}))
        return mutate(request,body,'replenishment',run)
    @app.post('/api/v1/replenishments/{id}/receive')
    def receive_replenishment(id:str,body:Actor,request:Request):
        def run(db,st,sid,s):
            role(body,['custodian']);r=get(db,Record,st,sid,id,True);check_version(r,body.expected_version)
            if r.kind!='replenishment' or r.payload['status']!='scheduled':fail('DELIVERY_STATE','Supply already received or unavailable')
            b=get(db,Balance,st,sid,r.payload['batch'],True);district(db,st,sid,b.facility_id,body)
            if parse_time(s.scenario_clock)<parse_time(r.payload['eta_min']):fail('NOT_ARRIVED','Advance the synthetic clock to the scheduled arrival before confirming receipt')
            valid_batch(b,s.scenario_clock) if (parse_time(s.scenario_clock)-parse_time(b.observed_at)).total_seconds()<=86400 else None
            if b.expiry<=s.scenario_clock[:10] or b.quality!='usable':fail('UNUSABLE_BATCH','Incoming lot requires an explicit quality review')
            b.on_hand+=r.payload['quantity'];b.version+=1;b.observed_at=s.scenario_clock
            event(db,st,sid,b,r.payload['quantity'],'replenishment_receipt',s.scenario_clock,r.id)
            r.payload={**r.payload,'status':'received'};r.version+=1
            return serial(r)
        return mutate(request,body,'replenishment-receive:'+id,run)
    @app.post('/api/v1/transfers/{id}/approve')
    def approve(id:str,body:Actor,request:Request): return mutate(request,body,'approve:'+id,lambda db,st,sid,s:transfer_action(db,st,sid,id,'approve',body,s))
    @app.post('/api/v1/transfers/{id}/dispatch')
    def dispatch(id:str,body:Actor,request:Request): return mutate(request,body,'dispatch:'+id,lambda db,st,sid,s:transfer_action(db,st,sid,id,'dispatch',body,s))
    @app.post('/api/v1/transfers/{id}/receive')
    def receive(id:str,body:ReceiptInput,request:Request): return mutate(request,body,'receive:'+id,lambda db,st,sid,s:transfer_action(db,st,sid,id,'receive',body,s))
    @app.post('/api/v1/transfers/{id}/cancel')
    def cancel(id:str,body:Actor,request:Request): return mutate(request,body,'cancel:'+id,lambda db,st,sid,s:transfer_action(db,st,sid,id,'cancel',body,s))

    @app.post('/api/v1/imports/preview')
    def preview(body:CSVInput,request:Request):
        def run(db,st,sid,s):
            role(body,['custodian']); rows=[]
            for i,row in enumerate(csv.DictReader(io.StringIO(body.csv))):
                if i>=100: fail('ROW_LIMIT','At most 100 CSV rows',422)
                errors=[]
                try:
                    b=get(db,Balance,st,sid,row.get('batch','')); quantity=int(row['quantity'])
                    if quantity<0: raise ValueError('Negative quantity')
                    medicine=db.get(Medicine,b.medicine_code)
                    if row.get('unit') in ['pack','packs']:
                        if int(row.get('pack_size','0'))!=medicine.pack_size:raise ValueError('Pack size must explicitly match the exact catalogue item')
                        quantity*=medicine.pack_size
                    elif row.get('unit')!=medicine.unit:raise ValueError('Unit must exactly match catalogue base unit or an explicitly confirmed pack size')
                    observation=StockInput(batch=b.id,quantity=quantity,mode=row['mode'],observed_at=row['observed_at'],reason='Confirmed synthetic CSV',role='custodian',district=body.district,expected_version=b.version).model_dump()
                except (ValueError,KeyError,DomainError) as e: errors.append(str(e)); observation=None
                rows.append({'row':i+2,'original':row,'observation':observation,'errors':errors})
            if not rows: fail('EMPTY_IMPORT','CSV requires a header and rows',422)
            return serial(record(db,st,sid,'import',{'rows':rows,'confirmed':False,'source':'synthetic CSV'}))
        return mutate(request,body,'import-preview',run)

    @app.post('/api/v1/imports/confirm')
    def confirm(body:ConfirmInput,request:Request):
        def run(db,st,sid,s):
            role(body,['custodian']); draft=get(db,Record,st,sid,body.draft_id,True); check_version(draft,body.expected_version)
            if draft.kind not in ['import','extraction'] or draft.payload.get('confirmed'): fail('DRAFT_STATE','Draft unavailable or already confirmed')
            output=[]
            for observation in body.observations:
                if observation.role!=body.role or observation.district!=body.district: fail('SCOPE_DENIED','Confirmation actor differs',403)
                output.append(update_stock(db,st,sid,observation,s))
            draft.payload={**draft.payload,'confirmed':True,'confirmed_fields':[b.model_dump() for b in body.observations]}; draft.version+=1
            return {'confirmed':True,'balances':output}
        return mutate(request,body,'confirm',run)

    @app.get('/api/v1/evaluation')
    def evaluation(request:Request):
        def result(*_):
            p=Path('data/evaluation/results.json')
            return json.loads(p.read_text()) if p.exists() else {'status':'not_run','message':'Run make evaluate. No benchmark results yet.'}
        return read(request,result)

    # AI and federation routes are registered separately to retain clear trust boundaries.
    from ai.routes import register as ai_routes
    from federation.routes import register as federation_routes
    ai_routes(app,read,mutate,auth)
    federation_routes(app,read,mutate)
    return app

app=create_app()
