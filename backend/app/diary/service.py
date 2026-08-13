import json
from sqlalchemy.orm import Session
from ..models import DiaryEvent
def add_event(db:Session,shop_id,event_code,entity,entity_id,occurred_at,actor_id=None,amount=None,payment_method=None,metadata=None):
    data=metadata or {};search=json.dumps(data,default=str,ensure_ascii=False)
    obj=DiaryEvent(shop_id=shop_id,actor_id=actor_id,event_code=event_code,related_entity_type=entity,related_entity_id=entity_id,amount=amount,payment_method=payment_method,metadata_json=json.dumps(data,default=str),search_text=search,occurred_at=occurred_at);db.add(obj);return obj
