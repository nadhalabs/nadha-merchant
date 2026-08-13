"""atomic financial commands and idempotency

Revision ID: d5b4f7c82011
Revises: c14a9d41b752
"""
from alembic import op
import sqlalchemy as sa
revision="d5b4f7c82011";down_revision="c14a9d41b752";branch_labels=None;depends_on=None
def upgrade():
    with op.batch_alter_table("ledger_entries") as b:
        b.drop_constraint("uq_ledger_shop_idempotency",type_="unique");b.create_unique_constraint("uq_ledger_shop_operation_idempotency",["shop_id","kind","idempotency_key"])
    with op.batch_alter_table("transactions") as b:
        b.add_column(sa.Column("bank_amount",sa.Numeric(14,2),nullable=True));b.add_column(sa.Column("other_amount",sa.Numeric(14,2),nullable=True));b.add_column(sa.Column("idempotency_key",sa.String(100),nullable=True));b.create_index("ix_transactions_idempotency_key",["idempotency_key"]);b.create_unique_constraint("uq_transaction_shop_idempotency",["shop_id","idempotency_key"])
    with op.batch_alter_table("inventory_movements") as b:
        b.add_column(sa.Column("idempotency_key",sa.String(100),nullable=True));b.create_unique_constraint("uq_inventory_shop_idempotency",["shop_id","idempotency_key"])
    with op.batch_alter_table("day_closings") as b:
        b.add_column(sa.Column("idempotency_key",sa.String(100),nullable=True));b.create_unique_constraint("uq_closing_shop_idempotency",["shop_id","idempotency_key"])
def downgrade():
    with op.batch_alter_table("ledger_entries") as b:b.drop_constraint("uq_ledger_shop_operation_idempotency",type_="unique");b.create_unique_constraint("uq_ledger_shop_idempotency",["shop_id","idempotency_key"])
    with op.batch_alter_table("day_closings") as b:b.drop_constraint("uq_closing_shop_idempotency",type_="unique");b.drop_column("idempotency_key")
    with op.batch_alter_table("inventory_movements") as b:b.drop_constraint("uq_inventory_shop_idempotency",type_="unique");b.drop_column("idempotency_key")
    with op.batch_alter_table("transactions") as b:b.drop_constraint("uq_transaction_shop_idempotency",type_="unique");b.drop_index("ix_transactions_idempotency_key");b.drop_column("idempotency_key");b.drop_column("other_amount");b.drop_column("bank_amount")
