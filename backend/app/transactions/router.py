import uuid
from datetime import date, datetime, time, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from ..audit.service import record
from ..dependencies import current_user,get_db, shop_access
from ..models import Customer, PaymentMethod, Shop, Supplier, Transaction, TransactionType,User
from ..closings.service import day_bounds
from ..schemas import FinancialTransactionIn, TransactionIn, TransactionOut
from ..products.service import replace_items
from .service import rebuild_inventory,rebuild_ledger
router = APIRouter(prefix="/shops/{shop_id}/transactions", tags=["transactions"])
def validate_people(db, shop_id, body):
    if body.customer_id and not db.scalar(select(Customer).where(Customer.id == body.customer_id, Customer.shop_id == shop_id)): raise HTTPException(400, "Customer does not belong to shop")
    if body.supplier_id and not db.scalar(select(Supplier).where(Supplier.id == body.supplier_id, Supplier.shop_id == shop_id)): raise HTTPException(400, "Supplier does not belong to shop")
@router.post("", response_model=TransactionOut, status_code=201)
def create(body: FinancialTransactionIn, shop_id=Depends(shop_access), user:User=Depends(current_user), db: Session=Depends(get_db)):
    existing=db.scalar(select(Transaction).where(Transaction.shop_id==shop_id,Transaction.idempotency_key==body.idempotency_key))
    if existing:
        if existing.type!=body.type or existing.amount!=body.amount or existing.payment_method!=body.payment_method or existing.customer_id!=body.customer_id or existing.supplier_id!=body.supplier_id:raise HTTPException(409,"Idempotency key was already used for a different financial entry")
        return existing
    validate_people(db, shop_id, body)
    if body.type==TransactionType.expense and body.items:raise HTTPException(400,"Expenses cannot contain stock items")
    if body.type==TransactionType.purchase:
        paid=body.amount if body.payment_state.value=="paid" else (body.paid_amount or 0)
        if paid>body.amount:raise HTTPException(400,"Amount paid cannot exceed purchase total")
        if paid>0 and body.payment_method in (None,PaymentMethod.credit):raise HTTPException(400,"Choose how the paid amount was paid")
        if paid<body.amount and not body.supplier_id:raise HTTPException(400,"Select a supplier for the amount due")
    if body.type==TransactionType.expense and body.payment_method in (None,PaymentMethod.credit):raise HTTPException(400,"Choose how this expense was paid")
    values=body.model_dump(exclude={"items"});tx=Transaction(shop_id=shop_id,**values);db.add(tx)
    try:
        db.flush()
        if body.items:
            rows=replace_items(db,shop_id,tx,body.items);calculated=sum((x.line_total for x in rows),0)
            amounts_supplied=all(x.amount is not None or x.unit_price is not None for x in body.items)
            if amounts_supplied and calculated!=body.amount:raise HTTPException(400,f"Item total ₹{calculated:.2f} does not match transaction total ₹{body.amount:.2f}")
        if body.type==TransactionType.sale:
            channels=(body.cash_amount or 0)+(body.upi_amount or 0)+(body.bank_amount or 0)+(body.other_amount or 0)
            if body.payment_method==PaymentMethod.mixed:
                if channels>body.amount:raise HTTPException(400,"Paid channel amounts exceed sale total")
                tx.paid_amount=channels
            elif body.payment_method==PaymentMethod.credit:tx.paid_amount=0
            else:tx.paid_amount=body.amount
        rebuild_ledger(db,tx);record(db,shop_id,user.id,"create","transaction",tx.id,after=tx)
        from ..diary.service import add_event
        names=[x.item_name or "" for x in body.items];person=db.get(Customer,body.customer_id).name if body.customer_id else db.get(Supplier,body.supplier_id).name if body.supplier_id else None
        add_event(db,shop_id,f"{body.type.value}.created",body.type.value,tx.id,body.occurred_at,user.id,body.amount,body.payment_method,{"person_name":person,"items":names,"note":body.note,"paid_amount":str(tx.paid_amount or 0),"due_amount":str(body.amount-(tx.paid_amount or 0))});db.commit();return tx
    except IntegrityError:
        db.rollback();existing=db.scalar(select(Transaction).where(Transaction.shop_id==shop_id,Transaction.idempotency_key==body.idempotency_key))
        if existing:return existing
        raise HTTPException(409,"This submission conflicts with an existing financial entry")
    except ValueError as error:
        db.rollback();raise HTTPException(409,str(error))
    except Exception:
        db.rollback();raise
@router.get("", response_model=list[TransactionOut])
def history(shop_id=Depends(shop_access), db: Session=Depends(get_db), type: TransactionType|None=None, payment_method: PaymentMethod|None=None, customer_id: uuid.UUID|None=None, supplier_id: uuid.UUID|None=None, date_from: date|None=None, date_to: date|None=None):
    q=select(Transaction).where(Transaction.shop_id==shop_id)
    if type: q=q.where(Transaction.type==type)
    if payment_method: q=q.where(Transaction.payment_method==payment_method)
    if customer_id: q=q.where(Transaction.customer_id==customer_id)
    if supplier_id: q=q.where(Transaction.supplier_id==supplier_id)
    if date_from:q=q.where(Transaction.occurred_at>=day_bounds(db,shop_id,date_from)[0])
    if date_to:q=q.where(Transaction.occurred_at<=day_bounds(db,shop_id,date_to)[1])
    return db.scalars(q.order_by(Transaction.occurred_at.desc())).all()
@router.put("/{transaction_id}", response_model=TransactionOut)
def edit(transaction_id: uuid.UUID, body: TransactionIn, shop_id=Depends(shop_access), user:User=Depends(current_user), db: Session=Depends(get_db)):
    tx=db.scalar(select(Transaction).where(Transaction.id==transaction_id,Transaction.shop_id==shop_id))
    if not tx: raise HTTPException(404,"Transaction not found")
    validate_people(db,shop_id,body);before={c.name:getattr(tx,c.name) for c in tx.__table__.columns}
    for key,value in body.model_dump().items(): setattr(tx,key,value)
    rebuild_ledger(db,tx);rebuild_inventory(db,tx);record(db,shop_id,user.id,"edit","transaction",tx.id,before=before,after=tx); db.commit(); return tx
