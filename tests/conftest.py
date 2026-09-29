import pytest,os,uuid
from sqlalchemy import text
from fastapi.testclient import TestClient
from services.api.db import make_engine, transaction
from services.api.models import Base, Budget, Medicine
from services.api.main import create_app
from data.generate import CATALOGUE

@pytest.fixture
def client(tmp_path):
    pg=os.getenv('TEST_POSTGRES_URL')
    schemas={s:'test_'+s.lower()+'_'+uuid.uuid4().hex for s in ['A','B']}
    admin=make_engine(pg) if pg else None
    if admin:
        with admin.begin() as conn:
            for schema in schemas.values(): conn.execute(text(f'CREATE SCHEMA {schema}'))
        from sqlalchemy.engine import make_url
        engines={s:make_engine(make_url(pg).update_query_dict({'options':f'-csearch_path={schema}'}).render_as_string(hide_password=False)) for s,schema in schemas.items()}
    else:
        engines={s:make_engine(f'sqlite:///{tmp_path}/{s}.db') for s in ['A','B']}
    for e in engines.values():
        Base.metadata.create_all(e)
        with transaction(e) as db:
            db.add_all([Budget(id='session-guard',count=0),Budget(id='ai-guard',count=0)])
            for c in CATALOGUE: db.add(Medicine(code=c[0],name=c[1],strength=c[2],formulation=c[3],unit=c[4],pack_size=c[5]))
    yield TestClient(create_app(engines,b'test-only-secret-at-least-32-bytes-long'))
    for e in engines.values(): e.dispose()
    if admin:
        with admin.begin() as conn:
            for schema in schemas.values(): conn.execute(text(f'DROP SCHEMA {schema} CASCADE'))
        admin.dispose()
