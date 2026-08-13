"""backfill diary events from existing financial history

Revision ID: f7a82c149d31
Revises: e6c91a73d440
"""
import json,uuid
from alembic import op
import sqlalchemy as sa
revision="f7a82c149d31";down_revision="e6c91a73d440";branch_labels=None;depends_on=None
def upgrade():
    db=op.get_bind();existing={(str(x.shop_id),x.event_code,str(x.related_entity_id)) for x in db.execute(sa.text("SELECT shop_id,event_code,related_entity_id FROM diary_events"))}
    def add(shop,code,kind,entity,amount,method,data,occurred,created):
        key=(str(shop),code,str(entity))
        if key in existing:return
        db.execute(sa.text("INSERT INTO diary_events (id,shop_id,actor_id,event_code,related_entity_type,related_entity_id,amount,payment_method,metadata_json,search_text,occurred_at,created_at) VALUES (:id,:shop,NULL,:code,:kind,:entity,:amount,:method,:metadata,:search,:occurred,:created)"),{"id":str(uuid.uuid4()),"shop":str(shop),"code":code,"kind":kind,"entity":str(entity),"amount":amount,"method":method,"metadata":json.dumps(data,default=str),"search":json.dumps(data,default=str,ensure_ascii=False),"occurred":occurred,"created":created});existing.add(key)
    for x in db.execute(sa.text("SELECT id,shop_id,type,amount,payment_method,note,occurred_at,created_at FROM transactions")):
        add(x.shop_id,f"{x.type}.created",x.type,x.id,x.amount,x.payment_method,{"note":x.note,"historical":True},x.occurred_at,x.created_at)
    for x in db.execute(sa.text("SELECT id,shop_id,kind,amount,payment_method,note,occurred_at,created_at FROM ledger_entries WHERE kind IN ('customer_payment','supplier_payment')")):
        add(x.shop_id,f"{x.kind}.created",x.kind,x.id,x.amount,x.payment_method,{"note":x.note,"historical":True},x.occurred_at,x.created_at)
    for x in db.execute(sa.text("SELECT id,shop_id,date,difference,notes,created_at FROM day_closings")):
        add(x.shop_id,"day_closing.created","day_closing",x.id,None,None,{"date":str(x.date),"difference":str(x.difference),"note":x.notes,"historical":True},x.created_at,x.created_at)
def downgrade():
    # Historical events are legitimate records once created; do not delete them on downgrade.
    pass
