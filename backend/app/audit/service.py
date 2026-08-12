import json
from datetime import date,datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID
from ..models import AuditLog
def encode(value):
    if value is None:return None
    if hasattr(value,"__table__"):value={c.name:getattr(value,c.name) for c in value.__table__.columns}
    return json.dumps(value,default=lambda x:str(x.value if isinstance(x,Enum) else x))
def record(db,shop_id,actor_id,action,entity,entity_id,before=None,after=None):
    db.add(AuditLog(shop_id=shop_id,actor_id=actor_id,action=action,entity=entity,entity_id=entity_id,before_json=encode(before),after_json=encode(after)))

