import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from services.api.db import make_engine, transaction
from services.api.models import Base, DemoSession, Balance, Facility
from data.generate import seed_session

def test_compound_scope_and_stock_constraints(tmp_path):
    e=make_engine(f'sqlite:///{tmp_path}/scope.db'); Base.metadata.create_all(e)
    with transaction(e) as db:
        db.add(DemoSession(state_id='A',id='one',expires=9999999999,scenario='GOLDEN')); db.flush()
        seed_session(db,'A','one','GOLDEN')
    with pytest.raises(IntegrityError), transaction(e) as db:
        db.add(Balance(state_id='A',session_id='one',id='bad',facility_id='foreign',medicine_code='MED-001',lot='x',expiry='2027-01-01',on_hand=10,observed_at='x'))
    with pytest.raises(IntegrityError), transaction(e) as db:
        b=db.get(Balance,('A','one','A-MED-001')); b.reserved=41
    with transaction(e) as db:
        assert len(db.scalars(select(Facility)).all())==8
        assert len(db.scalars(select(Balance)).all())==64
