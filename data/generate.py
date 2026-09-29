"""Reproducible fictional observations; latent demand is NEVER stored in serving DBs."""
import json
from pathlib import Path
import numpy as np
from sqlalchemy import select
from services.api.models import Medicine, History, Facility, Balance, Record, Budget,StockEvent
import uuid
from services.api.db import engines_from_env, transaction

CATALOGUE = [
    ('MED-001','Paracetamol','500 mg','tablet','tablet',10),
    ('MED-002','Amoxicillin','250 mg','capsule','capsule',10),
    ('MED-003','ORS','20.5 g','sachet','sachet',1),
    ('MED-004','Zinc','20 mg','tablet','tablet',10),
    ('MED-005','Metformin','500 mg','tablet','tablet',10),
    ('MED-006','Amlodipine','5 mg','tablet','tablet',10),
    ('MED-007','Cetirizine','10 mg','tablet','tablet',10),
    ('MED-008','Salbutamol','100 mcg','inhaler','inhaler',1),
]
FACILITIES = ['A','B','C','D','E','F','G','H']
FACILITY_PROFILES = {
 'A':('Madhavapur Primary Health Centre','Anitha Rao',58,12,8,4,3),
 'B':('Sevanagar Primary Health Centre','Ravi Kumar',64,18,14,11,4),
 'C':('Anandapur Community Health Centre','Farah Begum',46,24,18,9,6),
 'D':('Riverbend District Medicine Store','Suresh Das',0,0,0,0,0),
 'E':('Padmapur Primary Health Centre','Meena Devi',37,10,8,3,2),
 'F':('Neemgaon Primary Health Centre','Arun Das',42,12,10,7,3),
 'G':('Mallipur Primary Health Centre','Lakshmi Sen',29,8,6,2,2),
 'H':('Hillview District Medicine Store','Joseph Paul',0,0,0,0,0),
}
SCENARIOS = {'S01':'Normal replenishment','S02':'Hidden demand during stock-out','S03':'Nearest donor protected',
 'S04':'District surge','S05':'Stale donor','S06':'Late transport','S07':'Expired batch','S08':'No safe supply',
 'S09':'Duplicate/offline/concurrent actions','S10':'State model drift','GOLDEN':'Deterministic arithmetic fixture'}

def generate(seed=20260927):
    rng = np.random.default_rng(seed)
    observations, truth = [], []
    for state in ['A','B']:
        shocks = rng.lognormal(-0.02, .15, (2,208))
        for fi, facility in enumerate(FACILITIES):
            for mi, med in enumerate(CATALOGUE):
                for day in range(208):
                    closed = day % 53 == 0
                    missing = rng.random() < .025
                    footfall = int(rng.poisson(45 + 12*(day%7<5)))
                    mu = (8 + mi + fi%3*2) * (footfall+10)/60 * shocks[fi//4,day] * (1.18 if state=='B' else 1)
                    latent = 0 if closed else int(rng.negative_binomial(12, 12/(12+mu)))
                    supply = max(0, int(latent * rng.uniform(.05,.5))) if 100<=day%140<=120 else latent + 10
                    dispensed = min(supply, latent)
                    censored = not closed and supply < latent
                    row = dict(state=state,facility=facility,medicine=med[0],day=day,weekday=day%7,footfall=footfall,
                        dispensed=None if missing else dispensed, unfilled_requests=None if missing else max(0,latent-dispensed),
                        availability_fraction=None if missing else (supply/max(1,latent) if censored else 1.),
                        stock_exhausted=censored,hours_open=0 if closed else 8,source='synthetic')
                    observations.append(row)
                    truth.append(dict(state=state,facility=facility,medicine=med[0],day=day,latent=latent,source='synthetic evaluator-only'))
    return observations, truth

def seed_history():
    rows, _ = generate()
    for state, engine in engines_from_env().items():
        with transaction(engine) as db:
            for key in ['session-guard','ai-guard']:
                if not db.get(Budget,key): db.add(Budget(id=key,count=0))
            for c in CATALOGUE:
                if not db.get(Medicine,c[0]): db.add(Medicine(code=c[0],name=c[1],strength=c[2],formulation=c[3],unit=c[4],pack_size=c[5]))
            if not db.scalar(select(History).limit(1)):
                db.add_all([History(state_id=state,facility=r['facility'],medicine=r['medicine'],day=r['day'],payload=r)
                    for r in rows if r['state']==state and r['day']<180])
        print(f'State {state}: immutable synthetic history seeded (180 days, 8 facilities, 8 products)')

def seed_session(db, state, sid, scenario):
    clock = '2026-09-27T09:00:00+00:00'
    if scenario=='S01':
        db.add(Record(state_id=state,session_id=sid,id=str(uuid.uuid4()),kind='replenishment',version=1,payload={'batch':'A-MED-001','facility_id':'A','product':'MED-001','quantity':80,'eta_min':'2026-09-28T09:00:00+00:00','eta_max':'2026-09-29T09:00:00+00:00','status':'scheduled','source':'synthetic incoming supply'}))
    for i, f in enumerate(FACILITIES):
        profile=FACILITY_PROFILES[f]
        db.add(Facility(state_id=state,session_id=sid,id=f,code=f'{state}-{f}',district='D1' if f in ['A','B','D','E'] else 'D2',
            name=profile[0],payload={'source':'synthetic','fictional':True,'pharmacist':profile[1],'district_name':'Riverbend' if f in ['A','B','D','E'] else 'Hillview','timezone':'Asia/Kolkata','capabilities':['ambient storage']}))
    db.flush()
    for i, f in enumerate(FACILITIES):
        for med in CATALOGUE:
            stock = [40,120,150,0,0,0,0,0][i] if med[0]=='MED-001' else (12+i*7+int(med[0][-1])*9)*med[5]
            if f=='C' and med[0]=='MED-001' and scenario=='S08': stock=70
            db.add(Balance(state_id=state,session_id=sid,id=f'{f}-{med[0]}',facility_id=f,medicine_code=med[0],lot='SYN-01',
                expiry='2026-09-26' if f=='C' and scenario=='S07' else '2027-09-27',on_hand=stock,
                quality='usable',storage='suitable',reserved=0,quarantined=0,version=1,
                observed_at='2026-09-25T09:00:00+00:00' if f=='C' and scenario=='S05' else clock))
            db.flush()
            db.add(StockEvent(state_id=state,session_id=sid,id=str(uuid.uuid4()),batch=f'{f}-{med[0]}',delta=stock,event_type='synthetic_opening_balance',observed_at=clock,reason='Deterministic fictional fixture; not a physical receipt'))
        profile=FACILITY_PROFILES[f]
        db.add(Record(state_id=state,session_id=sid,id=f'capacity-{f}',kind='capacity',version=1,payload={
            'facility_id':f,'physical_beds':profile[3],'operational_beds':profile[4],'occupied_beds':profile[5],'staff_by_role':{'nurse':profile[6],'pharmacist':2 if f in ['C','D','H'] else 1},
            'footfall':87 if scenario=='S10' and state=='B' else profile[2],'observed_at':clock,'source':'synthetic'}))

if __name__ == '__main__': seed_history()
