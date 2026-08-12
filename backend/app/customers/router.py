import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..audit.service import record
from ..dependencies import current_user,get_db, shop_access
from ..ledgers.service import balance
from ..models import Customer, LedgerEntry, LedgerKind,User
from ..schemas import CustomerCreate, CustomerOut, LedgerEntryOut, LedgerPayment
router=APIRouter(prefix="/shops/{shop_id}/customers",tags=["customers"])
def get_one(db,shop_id,id):
    obj=db.scalar(select(Customer).where(Customer.id==id,Customer.shop_id==shop_id))
    if not obj: raise HTTPException(404,"Customer not found")
    return obj
@router.post("",response_model=CustomerOut,status_code=201)
def create(body:CustomerCreate,shop_id=Depends(shop_access),db:Session=Depends(get_db)):
    obj=Customer(shop_id=shop_id,**body.model_dump());db.add(obj);db.commit();return obj
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
    get_one(db,shop_id,customer_id); e=LedgerEntry(shop_id=shop_id,customer_id=customer_id,kind=LedgerKind.customer_payment,**body.model_dump());db.add(e);db.flush();record(db,shop_id,user.id,"create","customer_payment",e.id,after=e);db.commit();return e
