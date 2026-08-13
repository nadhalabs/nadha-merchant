import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..audit.service import record
from ..dependencies import current_user,get_db, shop_access
from ..ledgers.service import balance
from ..models import LedgerEntry, LedgerKind, Supplier,User
from ..schemas import LedgerEntryOut, LedgerPayment, SupplierCreate, SupplierOut
from ..diary.service import add_event
router=APIRouter(prefix="/shops/{shop_id}/suppliers",tags=["suppliers"])
def get_one(db,shop_id,id):
    obj=db.scalar(select(Supplier).where(Supplier.id==id,Supplier.shop_id==shop_id))
    if not obj: raise HTTPException(404,"Supplier not found")
    return obj
@router.post("",response_model=SupplierOut,status_code=201)
def create(body:SupplierCreate,shop_id=Depends(shop_access),user:User=Depends(current_user),db:Session=Depends(get_db)):
    obj=Supplier(shop_id=shop_id,**body.model_dump());db.add(obj);db.flush();add_event(db,shop_id,"supplier.created","supplier",obj.id,obj.created_at,user.id,metadata={"name":obj.name});db.commit();return obj
@router.get("")
def listing(shop_id=Depends(shop_access),db:Session=Depends(get_db)):
    return [{**SupplierOut.model_validate(x).model_dump(),"balance":balance(db,shop_id,supplier_id=x.id)} for x in db.scalars(select(Supplier).where(Supplier.shop_id==shop_id).order_by(Supplier.name)).all()]
@router.put("/{supplier_id}",response_model=SupplierOut)
def edit_supplier(supplier_id:uuid.UUID,body:SupplierCreate,shop_id=Depends(shop_access),user:User=Depends(current_user),db:Session=Depends(get_db)):
    obj=get_one(db,shop_id,supplier_id)
    for key,value in body.model_dump().items():setattr(obj,key,value)
    add_event(db,shop_id,"supplier.edited","supplier",uuid.uuid4(),obj.created_at,user.id,metadata={"supplier_id":str(obj.id),"name":obj.name});db.commit();return obj
@router.get("/{supplier_id}")
def detail(supplier_id:uuid.UUID,shop_id=Depends(shop_access),db:Session=Depends(get_db)):
    s=get_one(db,shop_id,supplier_id);entries=db.scalars(select(LedgerEntry).where(LedgerEntry.shop_id==shop_id,LedgerEntry.supplier_id==s.id).order_by(LedgerEntry.occurred_at)).all();running=0;rows=[]
    for e in entries: running += e.amount if e.kind==LedgerKind.supplier_due else -e.amount;rows.append({**LedgerEntryOut.model_validate(e).model_dump(),"running_balance":running})
    return {"supplier":SupplierOut.model_validate(s),"balance":running,"entries":rows}
@router.post("/{supplier_id}/payments",status_code=201)
def payment(supplier_id:uuid.UUID,body:LedgerPayment,shop_id=Depends(shop_access),user:User=Depends(current_user),db:Session=Depends(get_db)):
    supplier=db.scalar(select(Supplier).where(Supplier.id==supplier_id,Supplier.shop_id==shop_id).with_for_update())
    if not supplier:raise HTTPException(404,"Supplier not found")
    if body.idempotency_key:
        old=db.scalar(select(LedgerEntry).where(LedgerEntry.shop_id==shop_id,LedgerEntry.supplier_id==supplier_id,LedgerEntry.idempotency_key==body.idempotency_key))
        if old:return old
    if body.payment_method.value in ("credit","mixed"):raise HTTPException(400,"Choose Cash, UPI, Bank, or Other for money paid")
    if body.idempotency_key:
        old=db.scalar(select(LedgerEntry).where(LedgerEntry.shop_id==shop_id,LedgerEntry.supplier_id==supplier_id,LedgerEntry.idempotency_key==body.idempotency_key))
        if old:
            if old.amount!=body.amount or old.payment_method!=body.payment_method:raise HTTPException(409,"Idempotency key was already used for a different payment")
            return old
    due=balance(db,shop_id,supplier_id=supplier_id)
    if body.amount>due:raise HTTPException(400,f"You only owe ₹{due:.2f} to this supplier")
    e=LedgerEntry(shop_id=shop_id,supplier_id=supplier_id,kind=LedgerKind.supplier_payment,**body.model_dump());db.add(e);db.flush();record(db,shop_id,user.id,"create","supplier_payment",e.id,after=e);add_event(db,shop_id,"supplier_payment.created","supplier_payment",e.id,e.occurred_at,user.id,e.amount,e.payment_method,{"supplier_name":supplier.name,"remaining":str(due-body.amount),"note":e.note});db.commit();return e
