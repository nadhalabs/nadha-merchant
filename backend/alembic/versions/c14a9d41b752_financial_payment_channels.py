"""financial payment channels and one closing per business day

Revision ID: c14a9d41b752
Revises: fe6f793fd07e
"""
from alembic import op
import sqlalchemy as sa

revision="c14a9d41b752"
down_revision="fe6f793fd07e"
branch_labels=None
depends_on=None

def upgrade():
    with op.batch_alter_table("ledger_entries") as batch:
        batch.add_column(sa.Column("payment_method",sa.Enum("cash","upi","credit","mixed","bank","other",name="paymentmethod"),nullable=True))
        batch.add_column(sa.Column("idempotency_key",sa.String(100),nullable=True))
        batch.create_index("ix_ledger_entries_idempotency_key",["idempotency_key"],unique=False)
        batch.create_unique_constraint("uq_ledger_shop_idempotency",["shop_id","idempotency_key"])
    with op.batch_alter_table("day_closings") as batch:
        batch.create_unique_constraint("uq_day_closing_shop_date",["shop_id","date"])

def downgrade():
    with op.batch_alter_table("day_closings") as batch:batch.drop_constraint("uq_day_closing_shop_date",type_="unique")
    with op.batch_alter_table("ledger_entries") as batch:
        batch.drop_constraint("uq_ledger_shop_idempotency",type_="unique")
        batch.drop_index("ix_ledger_entries_idempotency_key")
        batch.drop_column("idempotency_key");batch.drop_column("payment_method")
