from sqlalchemy import Column, String, Integer, Float, JSON, Text, ForeignKeyConstraint, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class DemoSession(Base):
    __tablename__ = 'demo_sessions'
    state_id = Column(String, primary_key=True)
    id = Column(String, primary_key=True)
    expires = Column(Float, nullable=False)
    scenario = Column(String, nullable=False)
    scenario_clock = Column(String, nullable=False, default='2026-09-27T09:00:00+00:00')
    version = Column(Integer, nullable=False, default=1)

class Scoped:
    state_id = Column(String, primary_key=True)
    session_id = Column(String, primary_key=True)
    id = Column(String, primary_key=True)

def session_fk():
    return ForeignKeyConstraint(['state_id', 'session_id'], ['demo_sessions.state_id', 'demo_sessions.id'], ondelete='CASCADE')

class Facility(Scoped, Base):
    __tablename__ = 'facilities'
    district = Column(String, nullable=False)
    name = Column(String, nullable=False)
    code = Column(String, nullable=False)
    payload = Column(JSON, nullable=False)
    __table_args__ = (session_fk(),)

class Medicine(Base):
    __tablename__ = 'medicines'
    code = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    strength = Column(String, nullable=False)
    formulation = Column(String, nullable=False)
    unit = Column(String, nullable=False)
    pack_size = Column(Integer, nullable=False)

class Balance(Scoped, Base):
    __tablename__ = 'balances'
    facility_id = Column(String, nullable=False)
    medicine_code = Column(String, nullable=False)
    lot = Column(String, nullable=False)
    expiry = Column(String, nullable=False)
    quality = Column(String, nullable=False, default='usable')
    storage = Column(String, nullable=False, default='suitable')
    on_hand = Column(Integer, nullable=False)
    reserved = Column(Integer, nullable=False, default=0)
    quarantined = Column(Integer, nullable=False, default=0)
    version = Column(Integer, nullable=False, default=1)
    observed_at = Column(String, nullable=False)
    __table_args__ = (session_fk(), ForeignKeyConstraint(['state_id','session_id','facility_id'], ['facilities.state_id','facilities.session_id','facilities.id']),
        CheckConstraint('on_hand >= 0 AND reserved >= 0 AND quarantined >= 0 AND reserved + quarantined <= on_hand'),)

class Record(Scoped, Base):
    """Versioned ancillary entities: plans, forecasts, readiness, jobs, extraction drafts, audit."""
    __tablename__ = 'records'
    kind = Column(String, nullable=False, index=True)
    version = Column(Integer, nullable=False, default=1)
    payload = Column(JSON, nullable=False)
    __table_args__ = (session_fk(),)

class Transfer(Scoped, Base):
    __tablename__ = 'transfers'
    source = Column(String, nullable=False)
    destination = Column(String, nullable=False)
    batch = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False)
    dispatched = Column(Integer, nullable=False, default=0)
    received = Column(Integer, nullable=False, default=0)
    status = Column(String, nullable=False, default='reserved')
    approvals = Column(JSON, nullable=False, default=list)
    version = Column(Integer, nullable=False, default=1)
    expires = Column(String, nullable=False)
    __table_args__ = (session_fk(),
        ForeignKeyConstraint(['state_id','session_id','batch'], ['balances.state_id','balances.session_id','balances.id']),
        ForeignKeyConstraint(['state_id','session_id','destination'], ['facilities.state_id','facilities.session_id','facilities.id']),
        CheckConstraint('quantity > 0 AND received >= 0 AND received <= dispatched AND dispatched <= quantity'),)

class StockEvent(Scoped, Base):
    __tablename__ = 'stock_events'
    batch = Column(String, nullable=False)
    delta = Column(Integer, nullable=False)
    event_type = Column(String, nullable=False)
    observed_at = Column(String, nullable=False)
    reason = Column(String, nullable=False)
    __table_args__ = (session_fk(), ForeignKeyConstraint(['state_id','session_id','batch'], ['balances.state_id','balances.session_id','balances.id']),)

class Command(Scoped, Base):
    __tablename__ = 'commands'
    operation = Column(String, nullable=False)
    digest = Column(String, nullable=False)
    response = Column(JSON, nullable=False)
    __table_args__ = (session_fk(),)

class Budget(Base):
    __tablename__ = 'budgets'
    id = Column(String, primary_key=True)
    count = Column(Integer, nullable=False, default=0)

class History(Base):
    __tablename__ = 'daily_medicine_activity'
    state_id = Column(String, primary_key=True)
    facility = Column(String, primary_key=True)
    medicine = Column(String, primary_key=True)
    day = Column(Integer, primary_key=True)
    payload = Column(JSON, nullable=False)
