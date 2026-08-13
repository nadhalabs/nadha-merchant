import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..audit.service import record
from ..dependencies import current_user,get_db, shop_access
from ..ledgers.service import balance
from ..models import Customer, LedgerEntry, LedgerKind,User
from ..schemas import CustomerCreate, CustomerOut, LedgerEntryOut, LedgerPayment
from ..diary.service import add_event
router=APIRouter(prefix="/shops/{shop_id}/customers",tags=["customers"])
def get_one(db,shop_id,id):
    obj=db.scalar(select(Customer).where(Customer.id==id,Customer.shop_id==shop_id))
    if not obj: raise HTTPException(404,"Customer not found")
    return obj
@router.post("",response_model=CustomerOut,status_code=201)
def create(body:CustomerCreate,shop_id=Depends(shop_access),user:User=Depends(current_user),db:Session=Depends(get_db)):
    obj=Customer(shop_id=shop_id,**body.model_dump());db.add(obj);db.flush();add_event(db,shop_id,"customer.created","customer",obj.id,obj.created_at,user.id,metadata={"name":obj.name});db.commit();return obj
@router.put("/{customer_id}",response_model=CustomerOut)
def edit(customer_id:uuid.UUID,body:CustomerCreate,shop_id=Depends(shop_access),user:User=Depends(current_user),db:Session=Depends(get_db)):
    obj=get_one(db,shop_id,customer_id)
    for k,v in body.model_dump().items():setattr(obj,k,v)
    add_event(db,shop_id,"customer.edited","customer",uuid.uuid4(),obj.created_at,user.id,metadata={"customer_id":str(obj.id),"name":obj.name});db.commit();return obj
@router.get("")
def listing(shop_id=Depends(shop_access),db:Session=Depends(get_db)):
    return [{**CustomerOut.model_validate(x).model_dump(),"balance":balance(db,shop_id,customer_id=x.id)} for x in db.scalars(select(Customer).where(Customer.shop_id==shop_id).order_by(Customer.name)).all()]
@router.get("/{customer_id}")
def detail(customer_id:uuid.UUID,shop_id=Depends(shop_access),db:Session=Depends(get_db)):
    c=get_one(db,shop_id,customer_id); entries=db.scalars(select(LedgerEntry).where(LedgerEntry.shop_id==shop_id,LedgerEntry.customer_id==c.id).order_by(LedgerEntry.occurred_at)).all(); running=0; rows=[]
    for e in entries: running += e.amount if e.kind==LedgerKind.customer_credit else -e.amount; rows.append({**LedgerEntryOut.model_validate(e).model_dump(),"running_balance":running})
    return {"customer":CustomerOut.model_validate(c),"balance":running,"entries":rows}
@router.post("/{customer_id}/payments",status_code=201)
def payment(customer_id:uuid.UUID,body:LedgerPayment,shop_id=Depends(shop_access),user:User=Depends(current_user),db:Session=Depends(get_db)):
    customer=db.scalar(select(Customer).where(Customer.id==customer_id,Customer.shop_id==shop_id).with_for_update())
    if not customer:raise HTTPException(404,"Customer not found")
    if body.idempotency_key:
        old=db.scalar(select(LedgerEntry).where(LedgerEntry.shop_id==shop_id,LedgerEntry.customer_id==customer_id,LedgerEntry.idempotency_key==body.idempotency_key))
        if old:return old
    if body.payment_method.value in ("credit","mixed"):raise HTTPException(400,"Choose Cash, UPI, Bank, or Other for money received")
    if body.idempotency_key:
        old=db.scalar(select(LedgerEntry).where(LedgerEntry.shop_id==shop_id,LedgerEntry.customer_id==customer_id,LedgerEntry.idempotency_key==body.idempotency_key))
        if old:
            if old.amount!=body.amount or old.payment_method!=body.payment_method:raise HTTPException(409,"Idempotency key was already used for a different payment")
            return old
    due=balance(db,shop_id,customer_id=customer_id)
    if body.amount>due:raise HTTPException(400,f"Customer only owes ₹{due:.2f}")
    e=LedgerEntry(shop_id=shop_id,customer_id=customer_id,kind=LedgerKind.customer_payment,**body.model_dump());db.add(e);db.flush();record(db,shop_id,user.id,"create","customer_payment",e.id,after=e);remaining=due-body.amount;add_event(db,shop_id,"customer_payment.created","customer_payment",e.id,e.occurred_at,user.id,e.amount,e.payment_method,{"customer_name":customer.name,"remaining":str(remaining),"note":e.note});db.commit();return e
