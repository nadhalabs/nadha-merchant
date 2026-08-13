from datetime import datetime,timedelta,timezone
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import func,select
from sqlalchemy.orm import Session
from ..closings.service import total_owed
from ..dependencies import get_db,shop_access
from ..models import AIUsage,Customer,DiaryEvent,LedgerEntry,LedgerKind,Shop,Supplier
from ..schemas import AIQuestion
from .service import provider
router=APIRouter(prefix="/shops/{shop_id}/ai",tags=["nadha-ai"])
def context(db,shop_id):
    customers=db.execute(select(Customer.name,func.coalesce(func.sum(LedgerEntry.amount),0)).join(LedgerEntry,LedgerEntry.customer_id==Customer.id).where(Customer.shop_id==shop_id).group_by(Customer.id).limit(20)).all()
    events=db.scalars(select(DiaryEvent).where(DiaryEvent.shop_id==shop_id).order_by(DiaryEvent.occurred_at.desc()).limit(50)).all()
    return {"exact":{"customers_owe":str(total_owed(db,shop_id,True)),"suppliers_due":str(total_owed(db,shop_id,False))},"recent_events":[{"code":x.event_code,"amount":str(x.amount) if x.amount is not None else None,"data":x.metadata_json,"occurred_at":x.occurred_at.isoformat()} for x in events]}
@router.post("/ask")
def ask(body:AIQuestion,shop_id=Depends(shop_access),db:Session=Depends(get_db)):
    shop=db.get(Shop,shop_id)
    if not shop.ai_enabled:raise HTTPException(403,"Nadha AI isn't enabled for this account yet.")
    recent=db.scalar(select(func.count(AIUsage.id)).where(AIUsage.shop_id==shop_id,AIUsage.created_at>=datetime.now(timezone.utc)-timedelta(hours=1)))
    if recent>=30:raise HTTPException(429,"Nadha AI request limit reached. Try again later.")
    ctx=context(db,shop_id);result=provider().generate_business_answer(ctx,body.question,body.language);db.add(AIUsage(shop_id=shop_id,provider="unconfigured",success=result.get("available",False)));db.commit()
    return {"enabled":True,**result,"context_preview":ctx}
