import uuid
from datetime import date, datetime, time, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..audit.service import record
from ..dependencies import current_user,get_db, shop_access
from ..models import Customer, PaymentMethod, Supplier, Transaction, TransactionType,User
from ..schemas import TransactionIn, TransactionOut
from .service import rebuild_inventory,rebuild_ledger
router = APIRouter(prefix="/shops/{shop_id}/transactions", tags=["transactions"])
def validate_people(db, shop_id, body):
    if body.customer_id and not db.scalar(select(Customer).where(Customer.id == body.customer_id, Customer.shop_id == shop_id)): raise HTTPException(400, "Customer does not belong to shop")
    if body.supplier_id and not db.scalar(select(Supplier).where(Supplier.id == body.supplier_id, Supplier.shop_id == shop_id)): raise HTTPException(400, "Supplier does not belong to shop")
@router.post("", response_model=TransactionOut, status_code=201)
def create(body: TransactionIn, shop_id=Depends(shop_access), user:User=Depends(current_user), db: Session=Depends(get_db)):
    validate_people(db, shop_id, body); tx=Transaction(shop_id=shop_id, **body.model_dump()); db.add(tx); db.flush(); rebuild_ledger(db,tx);record(db,shop_id,user.id,"create","transaction",tx.id,after=tx); db.commit(); return tx
@router.get("", response_model=list[TransactionOut])
def history(shop_id=Depends(shop_access), db: Session=Depends(get_db), type: TransactionType|None=None, payment_method: PaymentMethod|None=None, customer_id: uuid.UUID|None=None, supplier_id: uuid.UUID|None=None, date_from: date|None=None, date_to: date|None=None):
    q=select(Transaction).where(Transaction.shop_id==shop_id)
    if type: q=q.where(Transaction.type==type)
    if payment_method: q=q.where(Transaction.payment_method==payment_method)
    if customer_id: q=q.where(Transaction.customer_id==customer_id)
    if supplier_id: q=q.where(Transaction.supplier_id==supplier_id)
    if date_from: q=q.where(Transaction.occurred_at>=datetime.combine(date_from,time.min,tzinfo=timezone.utc))
    if date_to: q=q.where(Transaction.occurred_at<=datetime.combine(date_to,time.max,tzinfo=timezone.utc))
    return db.scalars(q.order_by(Transaction.occurred_at.desc())).all()
@router.put("/{transaction_id}", response_model=TransactionOut)
def edit(transaction_id: uuid.UUID, body: TransactionIn, shop_id=Depends(shop_access), user:User=Depends(current_user), db: Session=Depends(get_db)):
    tx=db.scalar(select(Transaction).where(Transaction.id==transaction_id,Transaction.shop_id==shop_id))
    if not tx: raise HTTPException(404,"Transaction not found")
    validate_people(db,shop_id,body);before={c.name:getattr(tx,c.name) for c in tx.__table__.columns}
    for key,value in body.model_dump().items(): setattr(tx,key,value)
    rebuild_ledger(db,tx);rebuild_inventory(db,tx);record(db,shop_id,user.id,"edit","transaction",tx.id,before=before,after=tx); db.commit(); return tx
