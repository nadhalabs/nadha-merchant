import uuid
from datetime import date,datetime,time,timedelta,timezone
from decimal import Decimal
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import func,select
from sqlalchemy.orm import Session
from ..dependencies import get_db,shop_access
from ..ledgers.service import balance
from ..models import Customer,LedgerEntry,LedgerKind,Supplier,Transaction,TransactionItem,TransactionType
router=APIRouter(prefix="/shops/{shop_id}",tags=["recovery","supplier-memory"]);Z=Decimal("0")
@router.get("/collect-today")
def collect(shop_id=Depends(shop_access),db:Session=Depends(get_db)):
    now=datetime.now(timezone.utc);rows=[]
    for c in db.scalars(select(Customer).where(Customer.shop_id==shop_id)).all():
        owed=balance(db,shop_id,customer_id=c.id)
        if owed<=0:continue
        credits=db.scalars(select(LedgerEntry).where(LedgerEntry.shop_id==shop_id,LedgerEntry.customer_id==c.id,LedgerEntry.kind==LedgerKind.customer_credit).order_by(LedgerEntry.occurred_at)).all();payments=db.scalars(select(LedgerEntry).where(LedgerEntry.shop_id==shop_id,LedgerEntry.customer_id==c.id,LedgerEntry.kind==LedgerKind.customer_payment).order_by(LedgerEntry.occurred_at.desc())).all();oldest=credits[0].occurred_at if credits else now;age=max(0,(now-oldest.replace(tzinfo=oldest.tzinfo or timezone.utc)).days);score=float(owed)+age*10-(min(len(payments),5)*20);reasons=[f"₹{owed:,.2f} outstanding",f"oldest credit is {age} days old"]
        if payments:reasons.append(f"{len(payments)} repayment(s) recorded")
        rows.append({"customer_id":c.id,"name":c.name,"outstanding":owed,"oldest_unpaid_date":oldest,"age_days":age,"priority_score":score,"why_prioritized":reasons,"last_payment":payments[0].occurred_at if payments else None})
    rows.sort(key=lambda x:x["priority_score"],reverse=True);recent=db.execute(select(Customer.id,Customer.name,LedgerEntry.amount,LedgerEntry.occurred_at).join(LedgerEntry,LedgerEntry.customer_id==Customer.id).where(Customer.shop_id==shop_id,LedgerEntry.kind==LedgerKind.customer_payment,LedgerEntry.occurred_at>=now-timedelta(days=30)).order_by(LedgerEntry.occurred_at.desc())).all()
    return {"priorities":rows,"recently_paid":[{"customer_id":x.id,"name":x.name,"amount":x.amount,"occurred_at":x.occurred_at} for x in recent],"collection_history":[{"customer_id":x.id,"name":x.name,"amount":x.amount,"occurred_at":x.occurred_at} for x in recent]}
@router.get("/suppliers/{supplier_id}/footprint")
def footprint(supplier_id:uuid.UUID,shop_id=Depends(shop_access),db:Session=Depends(get_db)):
    supplier=db.scalar(select(Supplier).where(Supplier.id==supplier_id,Supplier.shop_id==shop_id))
    if not supplier:raise HTTPException(404,"Supplier not found")
    purchases=db.scalars(select(Transaction).where(Transaction.shop_id==shop_id,Transaction.supplier_id==supplier.id,Transaction.type==TransactionType.purchase).order_by(Transaction.occurred_at)).all();ids=[x.id for x in purchases];items=db.scalars(select(TransactionItem).where(TransactionItem.transaction_id.in_(ids)).order_by(TransactionItem.created_at)).all() if ids else [];by_product={}
    for item in items:by_product.setdefault(str(item.product_id),{"product_id":item.product_id,"product_name":item.product_name_snapshot,"prices":[]})["prices"].append({"price":item.unit_price,"quantity":item.quantity,"occurred_at":item.created_at,"supplier_name_snapshot":item.supplier_name_snapshot})
    histories=[]
    for value in by_product.values():
        prices=value["prices"];histories.append({**value,"previous_price":prices[-2]["price"] if len(prices)>1 else None,"latest_price":prices[-1]["price"],"change":prices[-1]["price"]-prices[-2]["price"] if len(prices)>1 else None})
    return {"supplier":{"id":supplier.id,"name":supplier.name,"contact_person":supplier.contact_person,"phone":supplier.phone,"payment_terms":supplier.payment_terms},"current_owed":balance(db,shop_id,supplier_id=supplier.id),"purchase_frequency":len(purchases),"average_purchase_value":sum((x.amount for x in purchases),Z)/len(purchases) if purchases else Z,"latest_purchase":purchases[-1].occurred_at if purchases else None,"products":histories}
@router.get("/products/{product_id}/supplier-prices")
def prices(product_id:uuid.UUID,shop_id=Depends(shop_access),db:Session=Depends(get_db)):
    rows=db.execute(select(TransactionItem,Transaction,Supplier).join(Transaction,Transaction.id==TransactionItem.transaction_id).join(Supplier,Supplier.id==Transaction.supplier_id).where(Transaction.shop_id==shop_id,Transaction.type==TransactionType.purchase,TransactionItem.product_id==product_id).order_by(Transaction.occurred_at)).all();return [{"supplier_id":s.id,"supplier_name":s.name,"supplier_name_snapshot":i.supplier_name_snapshot,"product_name_snapshot":i.product_name_snapshot,"unit_price":i.unit_price,"quantity":i.quantity,"occurred_at":t.occurred_at} for i,t,s in rows]
