import uuid
from datetime import date,datetime,time,timezone
from decimal import Decimal
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import func,select
from sqlalchemy.orm import Session
from ..closings.service import daily_totals,total_owed
from ..dependencies import get_db,shop_access
from ..models import InventoryMovement,LedgerEntry,LedgerKind,Product,Transaction,TransactionItem,TransactionType
router=APIRouter(prefix="/shops/{shop_id}",tags=["profit","money-map"]);Z=Decimal("0")
def profit_data(db,shop_id,start=None,end=None,transaction_id=None):
    tq=select(Transaction).where(Transaction.shop_id==shop_id,Transaction.type==TransactionType.sale)
    if start:tq=tq.where(Transaction.occurred_at>=start)
    if end:tq=tq.where(Transaction.occurred_at<=end)
    if transaction_id:tq=tq.where(Transaction.id==transaction_id)
    txs=db.scalars(tq).all();sales=sum((x.amount for x in txs),Z);ids=[x.id for x in txs]
    items=db.scalars(select(TransactionItem).where(TransactionItem.transaction_id.in_(ids))).all() if ids else []
    eligible=[x for x in items if x.cost_price is not None];covered=sum((x.line_total for x in eligible),Z);profit=sum((x.line_total-x.quantity*x.cost_price for x in eligible),Z)
    covered_capped=min(covered,sales);coverage=(covered_capped/sales*100).quantize(Decimal("0.1")) if sales else Z;margin=(profit/covered*100).quantize(Decimal("0.1")) if covered else None
    return {"label":"Gross Profit" if sales>0 and coverage==100 else "Estimated Profit","profit":profit,"gross_margin_percent":margin,"sales":sales,"sales_value_with_cost_data":covered,"coverage_percent":coverage,"is_exact":sales>0 and coverage==100}
@router.get("/profit")
def profit(period:str="daily",day:date|None=None,shop_id=Depends(shop_access),db:Session=Depends(get_db)):
    d=day or date.today()
    if period=="monthly":start=datetime(d.year,d.month,1,tzinfo=timezone.utc);end=datetime(d.year+(d.month==12),(d.month%12)+1,1,tzinfo=timezone.utc)
    else:start=datetime.combine(d,time.min,tzinfo=timezone.utc);end=datetime.combine(d,time.max,tzinfo=timezone.utc)
    return profit_data(db,shop_id,start,end)
@router.get("/transactions/{transaction_id}/profit")
def transaction_profit(transaction_id:uuid.UUID,shop_id=Depends(shop_access),db:Session=Depends(get_db)):
    if not db.scalar(select(Transaction).where(Transaction.id==transaction_id,Transaction.shop_id==shop_id)):raise HTTPException(404,"Transaction not found")
    return profit_data(db,shop_id,transaction_id=transaction_id)
@router.get("/money-map")
def money_map(day:date|None=None,shop_id=Depends(shop_access),db:Session=Depends(get_db)):
    d=day or date.today();daily=daily_totals(db,shop_id,d);profit=profit_data(db,shop_id,datetime.combine(d,time.min,tzinfo=timezone.utc),datetime.combine(d,time.max,tzinfo=timezone.utc))
    products=db.scalars(select(Product).where(Product.shop_id==shop_id,Product.inventory_enabled==True,Product.active==True)).all();stock_value=Z
    for p in products:
        stock=Decimal(db.scalar(select(func.coalesce(func.sum(InventoryMovement.quantity_delta),0)).where(InventoryMovement.product_id==p.id)));stock_value+=max(stock,Z)*(p.buy_price or Z)
    return {"cash_received":{"value":daily["cash_received"],"href":"/history?method=cash"},"upi_received":{"value":daily["upi_received"],"href":"/history?method=upi"},"customer_outstanding":{"value":total_owed(db,shop_id,True),"href":"/credit"},"supplier_outstanding":{"value":total_owed(db,shop_id,False),"href":"/credit?tab=suppliers"},"estimated_stock_value":{"value":stock_value,"href":"/products"},"expenses":{"value":daily["expenses"],"href":"/history?type=expense"},"profit":{**profit,"href":"/profit"}}
