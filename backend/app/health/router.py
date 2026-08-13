from datetime import date,datetime,time,timedelta,timezone
from decimal import Decimal
from fastapi import APIRouter,Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..closings.service import daily_totals,total_owed,day_bounds,paid_amount
from ..dependencies import get_db,shop_access
from ..models import DayClosing,LedgerEntry,LedgerKind,Shop,Transaction,TransactionType
from ..profit.router import profit_data
router=APIRouter(prefix="/shops/{shop_id}",tags=["shop-health"]);Z=Decimal("0")
def bounds(period,day):
    d=day or date.today()
    start=d if period=="today" else (d-timedelta(days=6) if period=="7d" else d.replace(day=1))
    return start,d
def cash_review(db,shop_id,start,end):
    closings=db.scalars(select(DayClosing).where(DayClosing.shop_id==shop_id,DayClosing.date>=start,DayClosing.date<=end).order_by(DayClosing.date)).all();rows=[]
    for c in closings:
        current=daily_totals(db,shop_id,c.date);difference=c.actual_cash-current["expected_cash"];changed=current["expected_cash"]!=c.expected_cash
        rows.append({"date":c.date,"expected_cash":current["expected_cash"],"closed_expected_cash":c.expected_cash,"actual_cash":c.actual_cash,"difference":difference,"changed_after_closing":changed,"status":"changed" if changed else "matched" if difference==0 else "review","message":"Day changed after closing; review and close again" if changed else "Cash matched recorded activity" if difference==0 else "Difference requires review","transaction_href":f"/history?date={c.date}"})
    total=sum((abs(x["difference"]) for x in rows),Z)
    return {"difference_requiring_review":total,"message":f"₹{total:,.2f} difference requires review" if total else "Recorded cash matches actual cash","dates":rows}
@router.get("/shop-health")
def health(period:str="today",day:date|None=None,shop_id=Depends(shop_access),db:Session=Depends(get_db)):
    from zoneinfo import ZoneInfo
    local_day=day or datetime.now(ZoneInfo(db.get(Shop,shop_id).timezone)).date();start,end=bounds(period,local_day);start_dt,_=day_bounds(db,shop_id,start);_,end_dt=day_bounds(db,shop_id,end);txs=db.scalars(select(Transaction).where(Transaction.shop_id==shop_id,Transaction.occurred_at>=start_dt,Transaction.occurred_at<=end_dt)).all();entries=db.scalars(select(LedgerEntry).where(LedgerEntry.shop_id==shop_id,LedgerEntry.occurred_at>=start_dt,LedgerEntry.occurred_at<=end_dt)).all()
    sales=sum((x.amount for x in txs if x.type==TransactionType.sale),Z);received=sum((paid_amount(x) for x in txs if x.type==TransactionType.sale),Z)+sum((x.amount for x in entries if x.kind==LedgerKind.customer_payment),Z)
    expenses=sum((x.amount for x in txs if x.type==TransactionType.expense),Z);profit=profit_data(db,shop_id,start_dt,end_dt)
    return {"period":period,"date_from":start,"date_to":end,"sales":sales,"money_received":received,"customers_owe":total_owed(db,shop_id,True),"suppliers_owed":total_owed(db,shop_id,False),"expenses":expenses,"profit":profit,"cash_review":cash_review(db,shop_id,start,end)}
@router.get("/cash-review")
def missing_money(period:str="7d",day:date|None=None,shop_id=Depends(shop_access),db:Session=Depends(get_db)):
    start,end=bounds(period,day);return cash_review(db,shop_id,start,end)
