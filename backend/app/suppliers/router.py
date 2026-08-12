import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..audit.service import record
from ..dependencies import current_user,get_db, shop_access
from ..ledgers.service import balance
from ..models import LedgerEntry, LedgerKind, Supplier,User
from ..schemas import LedgerEntryOut, LedgerPayment, SupplierCreate, SupplierOut
router=APIRouter(prefix="/shops/{shop_id}/suppliers",tags=["suppliers"])
def get_one(db,shop_id,id):
    obj=db.scalar(select(Supplier).where(Supplier.id==id,Supplier.shop_id==shop_id))
    if not obj: raise HTTPException(404,"Supplier not found")
    return obj
@router.post("",response_model=SupplierOut,status_code=201)
def create(body:SupplierCreate,shop_id=Depends(shop_access),db:Session=Depends(get_db)):
    obj=Supplier(shop_id=shop_id,**body.model_dump());db.add(obj);db.commit();return obj
@router.get("")
def listing(shop_id=Depends(shop_access),db:Session=Depends(get_db)):
    return [{**SupplierOut.model_validate(x).model_dump(),"balance":balance(db,shop_id,supplier_id=x.id)} for x in db.scalars(select(Supplier).where(Supplier.shop_id==shop_id).order_by(Supplier.name)).all()]
@router.put("/{supplier_id}",response_model=SupplierOut)
def edit_supplier(supplier_id:uuid.UUID,body:SupplierCreate,shop_id=Depends(shop_access),db:Session=Depends(get_db)):
    obj=get_one(db,shop_id,supplier_id)
    for key,value in body.model_dump().items():setattr(obj,key,value)
    db.commit();return obj
@router.get("/{supplier_id}")
def detail(supplier_id:uuid.UUID,shop_id=Depends(shop_access),db:Session=Depends(get_db)):
    s=get_one(db,shop_id,supplier_id);entries=db.scalars(select(LedgerEntry).where(LedgerEntry.shop_id==shop_id,LedgerEntry.supplier_id==s.id).order_by(LedgerEntry.occurred_at)).all();running=0;rows=[]
    for e in entries: running += e.amount if e.kind==LedgerKind.supplier_due else -e.amount;rows.append({**LedgerEntryOut.model_validate(e).model_dump(),"running_balance":running})
    return {"supplier":SupplierOut.model_validate(s),"balance":running,"entries":rows}
@router.post("/{supplier_id}/payments",status_code=201)
def payment(supplier_id:uuid.UUID,body:LedgerPayment,shop_id=Depends(shop_access),user:User=Depends(current_user),db:Session=Depends(get_db)):
    get_one(db,shop_id,supplier_id);e=LedgerEntry(shop_id=shop_id,supplier_id=supplier_id,kind=LedgerKind.supplier_payment,**body.model_dump());db.add(e);db.flush();record(db,shop_id,user.id,"create","supplier_payment",e.id,after=e);db.commit();return e
