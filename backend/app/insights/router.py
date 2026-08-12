import json,uuid
from datetime import date,datetime,time,timedelta,timezone
from decimal import Decimal
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import delete,func,select
from sqlalchemy.orm import Session
from ..dependencies import get_db,shop_access
from ..health.router import cash_review
from ..models import Insight,InventoryMovement,LostSale,Product,Transaction,TransactionType
router=APIRouter(prefix="/shops/{shop_id}/insights",tags=["insights"]);Z=Decimal("0")
def add(db,shop_id,type,title,explanation,start,end,refs):db.add(Insight(shop_id=shop_id,type=type,title=title,explanation=explanation,date_from=start,date_to=end,references_json=json.dumps(refs,default=str)))
@router.post("/generate")
def generate(shop_id=Depends(shop_access),db:Session=Depends(get_db)):
    today=date.today();start=today-timedelta(days=6);prev=start-timedelta(days=7);db.execute(delete(Insight).where(Insight.shop_id==shop_id,Insight.dismissed==False))
    review=cash_review(db,shop_id,start,today);mismatches=[x for x in review["dates"] if x["status"]=="review"]
    if mismatches:add(db,shop_id,"cash_difference",f"Cash closing differed on {len(mismatches)} day(s)","Cash did not match recorded activity. Check entries for the listed dates.",start,today,[{"closing_date":x["date"],"href":x["transaction_href"]} for x in mismatches])
    def expense(a,b):return Decimal(db.scalar(select(func.coalesce(func.sum(Transaction.amount),0)).where(Transaction.shop_id==shop_id,Transaction.type==TransactionType.expense,Transaction.occurred_at>=datetime.combine(a,time.min,tzinfo=timezone.utc),Transaction.occurred_at<=datetime.combine(b,time.max,tzinfo=timezone.utc))))
    current,previous=expense(start,today),expense(prev,start-timedelta(days=1))
    if current>previous*Decimal("1.25") and current>0:add(db,shop_id,"expense_increase","Expenses are unusually high this week",f"Recorded expenses are ₹{current:,.2f}, compared with ₹{previous:,.2f} in the previous 7 days.",start,today,[{"href":"/history?type=expense"}])
    month=today.replace(day=1);requests=db.execute(select(func.lower(LostSale.requested_product),func.count(LostSale.id),func.min(LostSale.requested_product)).where(LostSale.shop_id==shop_id,LostSale.occurred_at>=datetime.combine(month,time.min,tzinfo=timezone.utc)).group_by(func.lower(LostSale.requested_product)).having(func.count(LostSale.id)>=2)).all()
    for _,count,name in requests:add(db,shop_id,"lost_sale",f"{name} was requested {count} times",f"Customers requested this item {count} times this month while it was unavailable.",month,today,[{"href":"/lost-sales","requested_product":name}])
    cutoff=datetime.now(timezone.utc)-timedelta(days=30)
    for p in db.scalars(select(Product).where(Product.shop_id==shop_id,Product.active==True,Product.inventory_enabled==True)).all():
        recent=db.scalar(select(func.count(InventoryMovement.id)).where(InventoryMovement.shop_id==shop_id,InventoryMovement.product_id==p.id,InventoryMovement.occurred_at>=cutoff))
        if not recent:add(db,shop_id,"slow_stock",f"{p.name} has not moved for 30 days","No inventory movement was recorded for this product in the last 30 days.",today-timedelta(days=30),today,[{"product_id":str(p.id),"href":"/products"}])
    db.commit();return list_insights(shop_id,db)
@router.get("")
def list_insights(shop_id=Depends(shop_access),db:Session=Depends(get_db)):return db.scalars(select(Insight).where(Insight.shop_id==shop_id,Insight.dismissed==False).order_by(Insight.created_at.desc())).all()
@router.post("/{insight_id}/dismiss",status_code=204)
def dismiss(insight_id:uuid.UUID,shop_id=Depends(shop_access),db:Session=Depends(get_db)):
    obj=db.scalar(select(Insight).where(Insight.id==insight_id,Insight.shop_id==shop_id));
    if not obj:raise HTTPException(404,"Insight not found")
    obj.dismissed=True;db.commit();return None
