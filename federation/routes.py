import time
import numpy as np
from fastapi import Request
from sqlalchemy import select
from services.api.models import History,Record
from services.api.contracts import Actor
from services.api.db import transaction
from services.api.domain import record,serial,get,budget,fail,role,iso_now
from federation.node import step
from federation.coordinator import aggregate
from forecasting.model import predict

def register(app,read,mutate):
    @app.post('/api/v1/model-rounds')
    def start(body:Actor,request:Request):
        def run(db,st,sid,s):
            role(body,['planner']); budget(db,'rounds:'+sid,3)
            return serial(record(db,st,sid,'job',{'status':'pending','checkpoint':0,'updates':[],'lease_until':0,'source':'synthetic, separate state databases in shared runtime','created_at':iso_now()}))
        return mutate(request,body,'round-start',run)

    @app.get('/api/v1/jobs/{id}')
    def status(id:str,request:Request): return read(request,lambda db,st,sid,s:serial(get(db,Record,st,sid,id)))

    @app.post('/api/v1/jobs/{id}/advance')
    def advance(id:str,body:Actor,request:Request):
        def run(db,st,sid,s):
            role(body,['planner']); job=get(db,Record,st,sid,id,True)
            if job.kind!='job': fail('NOT_FOUND','Job not found',404)
            if job.version!=body.expected_version: fail('VERSION_CONFLICT','Job has advanced; reload')
            p=dict(job.payload)
            if p['status']=='completed': return serial(job)
            if p['lease_until']>time.time(): fail('JOB_BUSY','Step already running')
            p['lease_until']=time.time()+45
            checkpoint=p['checkpoint']
            def rows(state):
                # Local scoped query uses existing transaction to avoid self-deadlock.
                def scenario_rows(data):
                    if s.scenario=='S10' and state=='B':
                        return [{**r,'dispensed':None if r['dispensed'] is None else int(r['dispensed']*(1.4 if r['day']>=90 else 1)),'source':'synthetic S10 state drift'} for r in data]
                    return data
                if state==st: return scenario_rows([r.payload for r in db.scalars(select(History).where(History.state_id==state).order_by(History.facility,History.medicine,History.day)).all()])
                # Read only: no transaction-level SQLite write lock on peer.
                from sqlalchemy.orm import Session
                with Session(app.state.engines[state]) as peer:
                    return scenario_rows([r.payload for r in peer.scalars(select(History).where(History.state_id==state).order_by(History.facility,History.medicine,History.day)).all()])
            if checkpoint<2:
                state=['A','B'][checkpoint]; data=rows(state)
                if not data: fail('HISTORY_MISSING','Seed both state databases first',503)
                model,validation,mae=step(data)
                p['updates']=p['updates']+[{'state':state,'schema':model['schema'],'coefficients':model['coefficients'],'sample_count':model['training_rows'],'validation_mae':mae}]
            else:
                candidate=aggregate(p['updates']); decisions=[]
                for state in ['A','B']:
                    local,validation,mae=step(rows(state))
                    shared=float(np.mean(abs(predict({**candidate,'local_effects':local['local_effects']},validation)-np.array([r['dispensed'] for r in validation]))))
                    decisions.append({'state':state,'local_mae':mae,'shared_mae':shared,'accepted':shared<=mae})
                p.update(candidate=candidate,decisions=decisions,status='completed',publication='Sandbox candidate only. Guest cannot publish global model.')
            p['checkpoint']+=1; p['lease_until']=0; job.payload=p; job.version+=1
            return serial(job)
        return mutate(request,body,'round-advance:'+id,run)
