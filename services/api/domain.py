from datetime import datetime, timedelta, timezone
import time, uuid,json
from sqlalchemy import select
from services.api.models import DemoSession, Record, Balance, Facility, Command, StockEvent, Transfer, Budget
from services.api.security import digest

class DomainError(Exception):
    def __init__(self,code,message,status=409): self.code,self.message,self.status=code,message,status

def fail(code,message,status=409): raise DomainError(code,message,status)
def uid(): return str(uuid.uuid4())
def iso_now(): return datetime.now(timezone.utc).isoformat()
def parse_time(value):
    try:
        d=datetime.fromisoformat(value)
        if d.tzinfo is None: raise ValueError()
        return d
    except ValueError: fail('INVALID_TIME','A timezone-aware ISO timestamp is required',422)

def scoped(db,model,state,sid): return select(model).where(model.state_id==state,model.session_id==sid)
def get(db,model,state,sid,id,lock=False):
    q=scoped(db,model,state,sid).where(model.id==id)
    obj=db.scalar(q.with_for_update() if lock else q)
    if obj is None: fail('NOT_FOUND','No record in this sandbox',404)
    return obj
def record(db,state,sid,kind,payload,id=None):
    obj=Record(state_id=state,session_id=sid,id=id or uid(),kind=kind,version=1,payload=payload)
    db.add(obj); db.flush(); return obj
def serial(obj): return {c.name:getattr(obj,c.name) for c in obj.__table__.columns if c.name not in ['session_id','state_id']}
def check_version(obj,expected):
    if obj.version!=expected: fail('VERSION_CONFLICT',f'Record changed: current version {obj.version}. Review and recalculate.')
def role(body,allowed):
    if body.role not in allowed: fail('ROLE_DENIED',f'Action requires simulated role: {", ".join(allowed)}',403)
def district(db,state,sid,facility,body):
    f=get(db,Facility,state,sid,facility)
    if f.district!=body.district: fail('SCOPE_DENIED','Switch to the facility district in this synthetic sandbox',403)

def budget(db,key,limit):
    # Caller holds a database-level guard row or session lock. Always lock budgets in stable order.
    row=db.get(Budget,key,with_for_update=True)
    if row is None:
        row=Budget(id=key,count=0); db.add(row); db.flush()
    if row.count>=limit: fail('QUOTA_EXCEEDED','Demo request limit reached. Manual entry remains available.',429)
    row.count+=1

def command(db,state,sid,key,operation,body,fn):
    session=db.get(DemoSession,(state,sid),with_for_update=True)
    if session is None or session.expires<time.time(): fail('SESSION_EXPIRED','Start a new sandbox',401)
    if not key or len(key)>120: fail('IDEMPOTENCY_REQUIRED','Supply a unique Idempotency-Key (max 120 characters)',422)
    fingerprint=digest({'operation':operation,'body':body.model_dump()})
    previous=db.get(Command,(state,sid,key))
    if previous:
        if previous.digest!=fingerprint: fail('IDEMPOTENCY_CONFLICT','This key was already used with different content')
        return previous.response
    budget(db,f'commands:{sid}',500)
    storage=db.get(Budget,'bytes:'+sid)
    if storage is None:
        storage=Budget(id='bytes:'+sid,count=0);db.add(storage);db.flush()
    if storage.count>900000:fail('SANDBOX_STORAGE_LIMIT','Sandbox storage budget reached. Start a fresh session later.',429)
    output=fn(session)
    # Conservative accounting for response, stored record, audit and command duplication.
    size=len(json.dumps(output).encode())*3+1024
    if size>100000:fail('RESULT_SIZE_LIMIT','Result exceeds the bounded demo record size',422)
    storage.count+=size
    record(db,state,sid,'audit',{'action':operation,'actor_role':body.role,'district':body.district,
        'timestamp':iso_now(),'input_hash':fingerprint,'after_hash':digest(output),'source':'synthetic role simulation'})
    db.add(Command(state_id=state,session_id=sid,id=key,operation=operation,digest=fingerprint,response=output))
    return output

def event(db,state,sid,batch,delta,kind,clock,reason):
    db.add(StockEvent(state_id=state,session_id=sid,id=uid(),batch=batch.id,delta=delta,event_type=kind,observed_at=clock,reason=reason))

def update_stock(db,state,sid,body,session):
    role(body,['custodian']); batch=get(db,Balance,state,sid,body.batch,True)
    district(db,state,sid,batch.facility_id,body); check_version(batch,body.expected_version)
    observed=parse_time(body.observed_at); clock=parse_time(session.scenario_clock)
    if observed>clock or observed<parse_time(batch.observed_at): fail('RECOUNT_REQUIRED','Observation timing is ambiguous or older than the last stock movement; recount at the scenario clock')
    delta=body.quantity-batch.on_hand if body.mode=='snapshot' else body.quantity * (-1 if body.mode=='consume' else 1)
    if batch.on_hand+delta<batch.reserved+batch.quarantined: fail('INSUFFICIENT_STOCK','Adjustment would consume reserved/quarantined stock')
    batch.on_hand+=delta; batch.version+=1; batch.observed_at=body.observed_at
    event(db,state,sid,batch,delta,body.mode,body.observed_at,body.reason)
    db.flush(); return serial(batch)

def valid_batch(batch,clock):
    if batch.expiry<=clock[:10] or batch.quality!='usable' or batch.storage!='suitable': fail('UNUSABLE_BATCH','Expired, quarantined or unsuitable batch')
    if (parse_time(clock)-parse_time(batch.observed_at)).total_seconds()>86400: fail('STALE_STOCK','Verify donor stock: older than 24 scenario hours')

def reserve(db,state,sid,body,session,verify_snapshot=True):
    role(body,['planner']); plan=get(db,Record,state,sid,body.plan_id)
    if plan.kind!='plan': fail('NOT_FOUND','Plan not found',404)
    check_version(plan,body.expected_version)
    if session.scenario_clock>plan.payload['expires']: fail('STALE_PLAN','Plan expired. Recalculate.')
    lines=plan.payload['lines']
    if body.line_index>=len(lines): fail('NO_SUPPLY','No feasible line to reserve')
    line=lines[body.line_index]; batch=get(db,Balance,state,sid,line['batch'],True)
    district(db,state,sid,line['destination'],body); valid_batch(batch,session.scenario_clock)
    # Revalidate the entire snapshot, including recipient changes, before reservation.
    if verify_snapshot:
        for bid,version in plan.payload['versions'].items(): check_version(get(db,Balance,state,sid,bid),version)
        for rid,version in plan.payload.get('context_versions',{}).items():check_version(get(db,Record,state,sid,rid),version)
    donor_rows=db.scalars(scoped(db,Balance,state,sid).where(Balance.facility_id==batch.facility_id,Balance.medicine_code==batch.medicine_code)).all()
    free=sum(b.on_hand-b.reserved-b.quarantined for b in donor_rows if b.quality=='usable' and b.storage=='suitable' and b.expiry>session.scenario_clock[:10] and (parse_time(session.scenario_clock)-parse_time(b.observed_at)).total_seconds()<=86400)
    if batch.on_hand-batch.reserved-batch.quarantined<line['quantity'] or free-line['quantity']<line['protected']: fail('DONOR_PROTECTION','Donor demand and reserve would be violated')
    batch.reserved+=line['quantity']; batch.version+=1
    transfer=Transfer(state_id=state,session_id=sid,id=uid(),source=batch.facility_id,destination=line['destination'],batch=batch.id,
        quantity=line['quantity'],dispatched=0,received=0,status='reserved',version=1,approvals=[],
        expires=(parse_time(session.scenario_clock)+timedelta(minutes=30)).isoformat())
    db.add(transfer); db.flush(); return serial(transfer)

def transfer_action(db,state,sid,id,action,body,session):
    t=get(db,Transfer,state,sid,id,True); check_version(t,body.expected_version)
    batch=get(db,Balance,state,sid,t.batch,True)
    if action=='approve':
        role(body,['approver'])
        required={get(db,Facility,state,sid,t.source).district,get(db,Facility,state,sid,t.destination).district}
        if body.district not in required: fail('SCOPE_DENIED','Approval district is outside the transfer',403)
        if t.status!='reserved' or session.scenario_clock>t.expires: fail('TRANSFER_STATE','Reservation is not active')
        valid_batch(batch,session.scenario_clock)
        t.approvals=sorted(set(t.approvals+[body.district]))
        if set(t.approvals)==required: t.status='approved'
    elif action=='dispatch':
        role(body,['custodian']); district(db,state,sid,t.source,body)
        if t.status!='approved' or session.scenario_clock>t.expires: fail('APPROVAL_REQUIRED','Both district approvals and a current reservation are required')
        valid_batch(batch,session.scenario_clock)
        batch.on_hand-=t.quantity; batch.reserved-=t.quantity; batch.version+=1; batch.observed_at=session.scenario_clock
        t.dispatched=t.quantity; t.status='dispatched'
        event(db,state,sid,batch,-t.quantity,'dispatch',session.scenario_clock,t.id)
    elif action=='receive':
        role(body,['receiver']); district(db,state,sid,t.destination,body)
        if t.status not in ['dispatched','partially_received']: fail('TRANSFER_STATE','Shipment is not in transit')
        if body.quantity>t.dispatched-t.received: fail('EXCESS_RECEIPT','Cannot receive more than outstanding transit')
        # Keep received lots distinct; never merge different expiry/quality into an existing lot.
        dest_id=f'{t.destination}-receipt-{t.id}'
        dest=db.get(Balance,(state,sid,dest_id))
        if not dest:
            dest=Balance(state_id=state,session_id=sid,id=dest_id,facility_id=t.destination,medicine_code=batch.medicine_code,
                lot=batch.lot,expiry=batch.expiry,quality=batch.quality,storage=batch.storage,on_hand=0,reserved=0,quarantined=0,version=1,observed_at=session.scenario_clock)
            db.add(dest); db.flush()
        dest.on_hand+=body.quantity; dest.version+=1; dest.observed_at=session.scenario_clock
        if batch.expiry<=session.scenario_clock[:10] or batch.quality!='usable':
            dest.quarantined+=body.quantity; dest.quality='quarantined'
        t.received+=body.quantity; t.status='received' if t.received==t.dispatched else 'partially_received'
        event(db,state,sid,dest,body.quantity,'receive',session.scenario_clock,t.id)
    elif action=='cancel':
        role(body,['planner'])
        district(db,state,sid,t.destination,body)
        if t.status not in ['reserved','approved']: fail('TRANSFER_STATE','Dispatched stock requires explicit reconciliation, never automatic return')
        batch.reserved-=t.quantity; batch.version+=1; t.status='cancelled'
    t.version+=1; db.flush(); return serial(t)

def expire_reservations(db,state,sid,clock):
    rows=db.scalars(scoped(db,Transfer,state,sid).where(Transfer.status.in_(['reserved','approved'])).order_by(Transfer.batch)).all()
    for t in rows:
        if t.expires<clock:
            b=get(db,Balance,state,sid,t.batch,True); b.reserved-=t.quantity; b.version+=1
            t.status='expired'; t.version+=1
            record(db,state,sid,'audit',{'action':'reservation_expired','transfer':t.id,'timestamp':iso_now()})
