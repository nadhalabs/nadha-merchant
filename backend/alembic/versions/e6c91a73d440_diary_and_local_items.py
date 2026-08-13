"""diary and transaction-local items

Revision ID: e6c91a73d440
Revises: d5b4f7c82011
"""
from alembic import op
import sqlalchemy as sa
revision="e6c91a73d440";down_revision="d5b4f7c82011";branch_labels=None;depends_on=None
def upgrade():
    op.add_column("shops",sa.Column("ai_enabled",sa.Boolean(),nullable=False,server_default=sa.false()))
    with op.batch_alter_table("transaction_items") as b:b.alter_column("product_id",existing_type=sa.Uuid(),nullable=True)
    op.create_table("diary_events",sa.Column("id",sa.Uuid(),primary_key=True),sa.Column("shop_id",sa.Uuid(),sa.ForeignKey("shops.id",ondelete="CASCADE"),nullable=False),sa.Column("actor_id",sa.Uuid(),sa.ForeignKey("users.id",ondelete="SET NULL")),sa.Column("event_code",sa.String(80),nullable=False),sa.Column("related_entity_type",sa.String(80),nullable=False),sa.Column("related_entity_id",sa.Uuid(),nullable=False),sa.Column("amount",sa.Numeric(14,2)),sa.Column("payment_method",sa.Enum("cash","upi","credit","mixed","bank","other",name="paymentmethod")),sa.Column("metadata_json",sa.Text(),nullable=False),sa.Column("search_text",sa.Text(),nullable=False),sa.Column("occurred_at",sa.DateTime(timezone=True),nullable=False),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False),sa.UniqueConstraint("shop_id","event_code","related_entity_id",name="uq_diary_business_event"));op.create_index("ix_diary_shop_occurred","diary_events",["shop_id","occurred_at"]);op.create_index("ix_diary_events_shop_id","diary_events",["shop_id"]);op.create_index("ix_diary_events_event_code","diary_events",["event_code"]);op.create_index("ix_diary_events_occurred_at","diary_events",["occurred_at"]);op.create_index("ix_diary_events_related_entity_id","diary_events",["related_entity_id"])
    op.create_table("ai_usage",sa.Column("id",sa.Uuid(),primary_key=True),sa.Column("shop_id",sa.Uuid(),sa.ForeignKey("shops.id",ondelete="CASCADE"),nullable=False),sa.Column("provider",sa.String(80),nullable=False),sa.Column("model",sa.String(120)),sa.Column("success",sa.Boolean(),nullable=False),sa.Column("input_units",sa.Integer()),sa.Column("output_units",sa.Integer()),sa.Column("created_at",sa.DateTime(timezone=True),nullable=False));op.create_index("ix_ai_usage_shop_id","ai_usage",["shop_id"]);op.create_index("ix_ai_usage_created_at","ai_usage",["created_at"])
def downgrade():
    op.drop_table("ai_usage");op.drop_table("diary_events")
    with op.batch_alter_table("transaction_items") as b:b.alter_column("product_id",existing_type=sa.Uuid(),nullable=False)
    op.drop_column("shops","ai_enabled")
