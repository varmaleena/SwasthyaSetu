"""Run as a separate state process. Only this node reads its own state observations."""
import json,sys
import numpy as np
from forecasting.model import train,predict,valid,fit_local_effects

def step(rows):
    # Fixed training/validation partition; bounded sample, no evaluator truth.
    training=[r for r in rows if r['day']<120][:1800]
    validation=valid([r for r in rows if 150<=r['day']<180 and not r['stock_exhausted']])[:600]
    model=train(training,maxiter=30)
    model['local_effects']=fit_local_effects(model,training)
    mae=float(np.mean(abs(predict(model,validation)-np.array([r['dispensed'] for r in validation]))))
    return model,validation,mae

def main():
    import os
    from sqlalchemy import select
    from services.api.db import make_engine,transaction
    from services.api.models import History
    state=os.environ['NODE_STATE']
    engine=make_engine(os.environ[f'STATE_{state}_DATABASE_URL'])
    with transaction(engine) as db: rows=[r.payload for r in db.scalars(select(History).where(History.state_id==state).order_by(History.facility,History.medicine,History.day)).all()]
    model,validation,mae=step(rows)
    message={'state':state,'schema':model['schema'],'coefficients':model['coefficients'],'sample_count':model['training_rows'],'validation_mae':mae}
    print(json.dumps(message),flush=True)
    candidate=json.loads(sys.stdin.readline())
    candidate['local_effects']=model['local_effects']
    candidate_mae=float(np.mean(abs(predict(candidate,validation)-np.array([r['dispensed'] for r in validation]))))
    print(json.dumps({'state':state,'local_mae':mae,'candidate_mae':candidate_mae,'accepted':candidate_mae<=mae}),flush=True)
if __name__=='__main__': main()
