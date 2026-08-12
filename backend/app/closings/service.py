from datetime import date, datetime, time, timezone
from decimal import Decimal
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session
from ..models import LedgerEntry, LedgerKind, PaymentMethod, PaymentState, Transaction, TransactionType
Z=Decimal("0.00")
def daily_totals(db:Session,shop_id,day:date):
    start=datetime.combine(day,time.min,tzinfo=timezone.utc);end=datetime.combine(day,time.max,tzinfo=timezone.utc)
    txs=db.scalars(select(Transaction).where(Transaction.shop_id==shop_id,Transaction.occurred_at>=start,Transaction.occurred_at<=end)).all()
    sales=sum((x.amount for x in txs if x.type==TransactionType.sale),Z);purchases=sum((x.amount for x in txs if x.type==TransactionType.purchase),Z);expenses=sum((x.amount for x in txs if x.type==TransactionType.expense),Z)
    cash_received=sum(((x.amount if x.payment_method==PaymentMethod.cash else (x.cash_amount or Z)) for x in txs if x.type==TransactionType.sale),Z)
    upi=sum(((x.amount if x.payment_method==PaymentMethod.upi else (x.upi_amount or Z)) for x in txs if x.type==TransactionType.sale),Z)
    credit_sales=sum((x.amount-(x.paid_amount or Z) for x in txs if x.type==TransactionType.sale and x.payment_method==PaymentMethod.credit),Z)
    cash_out=sum(((x.paid_amount if x.payment_state==PaymentState.partial else x.amount) for x in txs if x.type==TransactionType.purchase and x.payment_method==PaymentMethod.cash),Z)+sum((x.amount for x in txs if x.type==TransactionType.expense and x.payment_method==PaymentMethod.cash),Z)
    entries=db.scalars(select(LedgerEntry).where(LedgerEntry.shop_id==shop_id,LedgerEntry.occurred_at>=start,LedgerEntry.occurred_at<=end)).all()
    collected=sum((e.amount for e in entries if e.kind==LedgerKind.customer_payment),Z);supplier_paid=sum((e.amount for e in entries if e.kind==LedgerKind.supplier_payment),Z)
    return {"sales":sales,"purchases":purchases,"expenses":expenses,"credit_given":sum((e.amount for e in entries if e.kind==LedgerKind.customer_credit),Z),"credit_collected":collected,"cash_received":cash_received,"upi_received":upi,"credit_sales":credit_sales,"expected_cash":cash_received+collected-cash_out-supplier_paid}
def total_owed(db,shop_id,customer=True):
    positive=(LedgerKind.customer_credit,LedgerKind.supplier_due);col=LedgerEntry.customer_id if customer else LedgerEntry.supplier_id;kinds=(LedgerKind.customer_credit,LedgerKind.customer_payment) if customer else (LedgerKind.supplier_due,LedgerKind.supplier_payment)
    return Decimal(db.scalar(select(func.coalesce(func.sum(case((LedgerEntry.kind.in_(positive),LedgerEntry.amount),else_=-LedgerEntry.amount)),0)).where(LedgerEntry.shop_id==shop_id,LedgerEntry.kind.in_(kinds))))

