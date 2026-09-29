"""No browser role may directly access operational tables."""
from alembic import op
from sqlalchemy import text
from services.api.models import Base
revision='0002'
down_revision='0001'
def upgrade():
    bind=op.get_bind()
    if bind.dialect.name!='postgresql': return
    for table in Base.metadata.tables:
        bind.execute(text(f'REVOKE ALL ON TABLE "{table}" FROM PUBLIC'))
        for role in ['anon','authenticated']:
            if bind.execute(text('SELECT 1 FROM pg_roles WHERE rolname=:role'),{'role':role}).scalar():
                bind.execute(text(f'REVOKE ALL ON TABLE "{table}" FROM "{role}"'))
def downgrade(): raise RuntimeError('Unsafe permission rollback disabled')
