"""Initial scoped ledger. Apply to each state independently."""
from alembic import op
from services.api.models import Base
revision = '0001'
down_revision = None
def upgrade():
    Base.metadata.create_all(op.get_bind())
def downgrade():
    raise RuntimeError('Destructive downgrade disabled; restore an owner-managed backup')
