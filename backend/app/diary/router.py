import json,uuid
from datetime import datetime,timezone
from fastapi import APIRouter,Depends,Query
from sqlalchemy import or_,select
from sqlalchemy.orm import Session
from ..dependencies import current_user,get_db,shop_access
from ..models import DiaryEvent,User
from ..schemas import DiaryNoteIn
from .service import add_event
router=APIRouter(prefix="/shops/{shop_id}/diary",tags=["diary"])
@router.get("")
def listing(category:str|None=None,search:str|None=None,limit:int=Query(100,ge=1,le=200),shop_id=Depends(shop_access),db:Session=Depends(get_db)):
    q=select(DiaryEvent).where(DiaryEvent.shop_id==shop_id)
    if category:q=q.where(DiaryEvent.event_code.startswith(category))
    if search:q=q.where(DiaryEvent.search_text.ilike(f"%{search[:100]}%"))
    rows=db.scalars(q.order_by(DiaryEvent.occurred_at.desc()).limit(limit)).all();return [{"id":x.id,"event_code":x.event_code,"related_entity_type":x.related_entity_type,"related_entity_id":x.related_entity_id,"amount":x.amount,"payment_method":x.payment_method,"metadata":json.loads(x.metadata_json),"occurred_at":x.occurred_at} for x in rows]
@router.post("/notes",status_code=201)
def note(body:DiaryNoteIn,shop_id=Depends(shop_access),user:User=Depends(current_user),db:Session=Depends(get_db)):
    entity_id=uuid.uuid4();obj=add_event(db,shop_id,"note.created","diary_note",entity_id,body.occurred_at,user.id,metadata={"text":body.text});db.commit();return obj
