from datetime import date, datetime, time, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session
from ..models import LedgerEntry, LedgerKind, PaymentMethod, PaymentState, Shop, Transaction, TransactionType
Z=Decimal("0.00")
def day_bounds(db:Session,shop_id,day:date):
    zone=ZoneInfo(db.scalar(select(Shop.timezone).where(Shop.id==shop_id)) or "Asia/Kolkata")
    return datetime.combine(day,time.min,zone).astimezone(timezone.utc),datetime.combine(day,time.max,zone).astimezone(timezone.utc)
def paid_amount(tx:Transaction):
    if tx.type==TransactionType.expense:return tx.amount
    if tx.payment_method==PaymentMethod.credit:return Z
    if tx.payment_method==PaymentMethod.mixed:return (tx.cash_amount or Z)+(tx.upi_amount or Z)+(tx.bank_amount or Z)+(tx.other_amount or Z)
    if tx.type==TransactionType.purchase:return tx.amount if tx.payment_state==PaymentState.paid else (tx.paid_amount or Z)
    return tx.amount
def daily_totals(db:Session,shop_id,day:date):
    start,end=day_bounds(db,shop_id,day)
    txs=db.scalars(select(Transaction).where(Transaction.shop_id==shop_id,Transaction.occurred_at>=start,Transaction.occurred_at<=end)).all()
    sales=sum((x.amount for x in txs if x.type==TransactionType.sale),Z);purchases=sum((x.amount for x in txs if x.type==TransactionType.purchase),Z);expenses=sum((x.amount for x in txs if x.type==TransactionType.expense),Z)
    cash_sales=sum((paid_amount(x) if x.payment_method==PaymentMethod.cash else (x.cash_amount or Z) if x.payment_method==PaymentMethod.mixed else Z for x in txs if x.type==TransactionType.sale),Z)
    upi_sales=sum((paid_amount(x) if x.payment_method==PaymentMethod.upi else (x.upi_amount or Z) if x.payment_method==PaymentMethod.mixed else Z for x in txs if x.type==TransactionType.sale),Z)
    bank_sales=sum((paid_amount(x) if x.payment_method==PaymentMethod.bank else (x.bank_amount or Z) if x.payment_method==PaymentMethod.mixed else Z for x in txs if x.type==TransactionType.sale),Z);other_sales=sum((paid_amount(x) if x.payment_method==PaymentMethod.other else (x.other_amount or Z) if x.payment_method==PaymentMethod.mixed else Z for x in txs if x.type==TransactionType.sale),Z)
    credit_sales=sum((x.amount-paid_amount(x) for x in txs if x.type==TransactionType.sale),Z)
    entries=db.scalars(select(LedgerEntry).where(LedgerEntry.shop_id==shop_id,LedgerEntry.occurred_at>=start,LedgerEntry.occurred_at<=end)).all()
    customer_payments=[e for e in entries if e.kind==LedgerKind.customer_payment];supplier_payments=[e for e in entries if e.kind==LedgerKind.supplier_payment]
    collected=sum((e.amount for e in customer_payments),Z);supplier_paid=sum((e.amount for e in supplier_payments),Z)
    by=lambda rows,method:sum((e.amount for e in rows if e.payment_method==method),Z)
    cash_received=cash_sales+by(customer_payments,PaymentMethod.cash);upi=upi_sales+by(customer_payments,PaymentMethod.upi);bank_received=bank_sales+by(customer_payments,PaymentMethod.bank);other_received=other_sales+by(customer_payments,PaymentMethod.other)
    purchase_paid=sum((paid_amount(x) for x in txs if x.type==TransactionType.purchase),Z);purchase_due=purchases-purchase_paid
    cash_paid=sum((paid_amount(x) for x in txs if x.type in (TransactionType.purchase,TransactionType.expense) and x.payment_method==PaymentMethod.cash),Z)+by(supplier_payments,PaymentMethod.cash)
    upi_paid=sum((paid_amount(x) for x in txs if x.type in (TransactionType.purchase,TransactionType.expense) and x.payment_method==PaymentMethod.upi),Z)+by(supplier_payments,PaymentMethod.upi)
    bank_paid=sum((paid_amount(x) for x in txs if x.type in (TransactionType.purchase,TransactionType.expense) and x.payment_method==PaymentMethod.bank),Z)+by(supplier_payments,PaymentMethod.bank)
    other_paid=sum((paid_amount(x) for x in txs if x.type in (TransactionType.purchase,TransactionType.expense) and x.payment_method==PaymentMethod.other),Z)+by(supplier_payments,PaymentMethod.other)
    money_received=cash_received+upi+bank_received+other_received;money_paid=cash_paid+upi_paid+bank_paid+other_paid
    return {"sales":sales,"sales_total":sales,"purchases":purchases,"purchase_total":purchases,"purchase_paid":purchase_paid,"purchase_on_credit":purchase_due,"expenses":expenses,"expenses_paid":expenses,"credit_given":sum((e.amount for e in entries if e.kind==LedgerKind.customer_credit),Z),"credit_collected":collected,"cash_sales":cash_sales,"upi_sales":upi_sales,"other_paid_sales":bank_sales+other_sales,"cash_received":cash_received,"upi_received":upi,"bank_received":bank_received,"other_received":other_received,"money_received":money_received,"supplier_payments":supplier_paid,"cash_paid":cash_paid,"upi_paid":upi_paid,"bank_paid":bank_paid,"other_paid":other_paid,"money_paid":money_paid,"credit_sales":credit_sales,"expected_cash":cash_received-cash_paid}
def total_owed(db,shop_id,customer=True):
    positive=(LedgerKind.customer_credit,LedgerKind.supplier_due);col=LedgerEntry.customer_id if customer else LedgerEntry.supplier_id;kinds=(LedgerKind.customer_credit,LedgerKind.customer_payment) if customer else (LedgerKind.supplier_due,LedgerKind.supplier_payment)
    return Decimal(db.scalar(select(func.coalesce(func.sum(case((LedgerEntry.kind.in_(positive),LedgerEntry.amount),else_=-LedgerEntry.amount)),0)).where(LedgerEntry.shop_id==shop_id,LedgerEntry.kind.in_(kinds))))
