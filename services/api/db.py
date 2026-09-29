"""Separate state engines. SQLite is explicitly limited to local development/tests."""
import os
from contextlib import contextmanager
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session

SCHEMA_VERSION = "0002"

def engines_from_env():
    urls = {s: os.getenv(f"STATE_{s}_DATABASE_URL", f"sqlite:///state_{s.lower()}.db") for s in ("A", "B")}
    if urls['A'] == urls['B']:
        raise RuntimeError("State databases must be separate")
    if os.getenv('APP_ENV', 'local') != 'local' and any(not u.startswith('postgresql') for u in urls.values()):
        raise RuntimeError('Hosted mode requires two persistent PostgreSQL databases')
    return {s: make_engine(url) for s, url in urls.items()}

def make_engine(url):
    sqlite = url.startswith('sqlite')
    engine = create_engine(url, pool_pre_ping=True, **({'connect_args': {'check_same_thread': False, 'timeout': 30}} if sqlite else {'pool_size': 2, 'max_overflow': 0}))
    if sqlite:
        @event.listens_for(engine, 'connect')
        def constraints(conn, _):
            conn.execute('PRAGMA foreign_keys=ON')
    return engine

@contextmanager
def transaction(engine):
    with Session(engine, expire_on_commit=False) as db:
        if engine.dialect.name == 'sqlite':
            db.execute(text('BEGIN IMMEDIATE'))
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise

def check_schema(engine):
    with engine.connect() as conn:
        return conn.execute(text('SELECT version_num FROM alembic_version')).scalar() == SCHEMA_VERSION
