import os,uuid
import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from services.api.db import make_engine

@pytest.mark.skipif(not os.getenv('TEST_POSTGRES_URL'),reason='Requires explicit local PostgreSQL test URL')
def test_unprivileged_role_cannot_read_operational_data():
    e=make_engine(os.environ['TEST_POSTGRES_URL']); suffix=uuid.uuid4().hex
    role='test_guest_'+suffix; schema='test_permission_'+suffix
    with e.begin() as c:
        c.execute(text(f'CREATE ROLE {role} NOLOGIN'))
        c.execute(text(f'CREATE SCHEMA {schema}'))
        c.execute(text(f'CREATE TABLE {schema}.private_stock (quantity integer)'))
        c.execute(text(f'GRANT USAGE ON SCHEMA {schema} TO {role}'))
    try:
        with pytest.raises(DBAPIError),e.begin() as c:
            c.execute(text(f'SET LOCAL ROLE {role}'))
            c.execute(text(f'SELECT * FROM {schema}.private_stock'))
    finally:
        with e.begin() as c:
            c.execute(text(f'DROP SCHEMA {schema} CASCADE'));c.execute(text(f'DROP ROLE {role}'))
        e.dispose()
