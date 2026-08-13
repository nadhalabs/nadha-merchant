import uuid
from decimal import Decimal
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import func,select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from ..audit.service import record
from ..dependencies import current_user,get_db,shop_access
from ..models import InventoryMovement,InventoryMovementType,Product,User
from ..schemas import ManualMovementIn,SetActualStockIn
router=APIRouter(prefix="/shops/{shop_id}/inventory",tags=["inventory"])
@router.get("")
def inventory(shop_id=Depends(shop_access),db:Session=Depends(get_db)):
    rows=db.scalars(select(Product).where(Product.shop_id==shop_id,Product.inventory_enabled==True,Product.active==True).order_by(Product.name)).all()
    return [{"product_id":p.id,"name":p.name,"unit":p.unit,"stock":db.scalar(select(func.coalesce(func.sum(InventoryMovement.quantity_delta),0)).where(InventoryMovement.product_id==p.id)),"buy_price":p.buy_price} for p in rows]
@router.get("/{product_id}/movements")
def movements(product_id:uuid.UUID,shop_id=Depends(shop_access),db:Session=Depends(get_db)):
    if not db.scalar(select(Product).where(Product.id==product_id,Product.shop_id==shop_id)):raise HTTPException(404,"Product not found")
    return db.scalars(select(InventoryMovement).where(InventoryMovement.shop_id==shop_id,InventoryMovement.product_id==product_id).order_by(InventoryMovement.occurred_at.desc())).all()
@router.post("/{product_id}/adjustments",status_code=201)
def adjustment(product_id:uuid.UUID,body:ManualMovementIn,shop_id=Depends(shop_access),user:User=Depends(current_user),db:Session=Depends(get_db)):
    old=db.scalar(select(InventoryMovement).where(InventoryMovement.shop_id==shop_id,InventoryMovement.idempotency_key==body.idempotency_key))
    if old:
        if old.product_id!=product_id or old.quantity_delta!=body.quantity_difference:raise HTTPException(409,"Idempotency key was already used for a different stock change")
        return old
    product=db.scalar(select(Product).where(Product.id==product_id,Product.shop_id==shop_id,Product.inventory_enabled==True).with_for_update())
    if not product:raise HTTPException(404,"Inventory-enabled product not found")
    old=db.scalar(select(InventoryMovement).where(InventoryMovement.shop_id==shop_id,InventoryMovement.idempotency_key==body.idempotency_key))
    if old:return old
    if body.quantity_difference==0:raise HTTPException(400,"Quantity difference cannot be zero")
    current=db.scalar(select(func.coalesce(func.sum(InventoryMovement.quantity_delta),0)).where(InventoryMovement.product_id==product_id))
    if current+body.quantity_difference<0:raise HTTPException(400,f"Only {current} {product.unit.value} are in stock")
    kind=InventoryMovementType.manual_increase if body.quantity_difference>0 else InventoryMovementType.manual_decrease
    obj=InventoryMovement(shop_id=shop_id,product_id=product_id,type=kind,quantity_delta=body.quantity_difference,reason=body.reason,occurred_at=body.occurred_at,idempotency_key=body.idempotency_key);db.add(obj)
    try:db.flush();record(db,shop_id,user.id,"create","inventory_adjustment",obj.id,after=obj);db.commit();return obj
    except IntegrityError:
        db.rollback();return db.scalar(select(InventoryMovement).where(InventoryMovement.shop_id==shop_id,InventoryMovement.idempotency_key==body.idempotency_key))
@router.post("/{product_id}/set-actual",status_code=201)
def set_actual(product_id:uuid.UUID,body:SetActualStockIn,shop_id=Depends(shop_access),user:User=Depends(current_user),db:Session=Depends(get_db)):
    old=db.scalar(select(InventoryMovement).where(InventoryMovement.shop_id==shop_id,InventoryMovement.idempotency_key==body.idempotency_key))
    if old:
        if old.product_id!=product_id:raise HTTPException(409,"Idempotency key was already used for a different stock change")
        return old
    product=db.scalar(select(Product).where(Product.id==product_id,Product.shop_id==shop_id,Product.inventory_enabled==True).with_for_update())
    if not product:raise HTTPException(404,"Inventory-enabled product not found")
    old=db.scalar(select(InventoryMovement).where(InventoryMovement.shop_id==shop_id,InventoryMovement.idempotency_key==body.idempotency_key))
    if old:return old
    current=db.scalar(select(func.coalesce(func.sum(InventoryMovement.quantity_delta),0)).where(InventoryMovement.product_id==product_id));delta=body.actual_quantity-current
    if delta==0:raise HTTPException(400,"Stock already matches the counted quantity")
    obj=InventoryMovement(shop_id=shop_id,product_id=product_id,type=InventoryMovementType.correction,quantity_delta=delta,reason=body.reason,occurred_at=body.occurred_at,idempotency_key=body.idempotency_key);db.add(obj);db.flush();record(db,shop_id,user.id,"create","inventory_correction",obj.id,after=obj);db.commit();return obj
