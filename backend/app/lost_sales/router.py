import uuid
from datetime import date,datetime,time,timezone
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import func,select
from sqlalchemy.orm import Session
from ..dependencies import get_db,shop_access
from ..models import Customer,LostSale,Product
from ..schemas import LostSaleConvert,LostSaleIn,ProductOut
router=APIRouter(prefix="/shops/{shop_id}/lost-sales",tags=["lost-sales"])
@router.post("",status_code=201)
def create(body:LostSaleIn,shop_id=Depends(shop_access),db:Session=Depends(get_db)):
    if body.customer_id and not db.scalar(select(Customer).where(Customer.id==body.customer_id,Customer.shop_id==shop_id)):raise HTTPException(400,"Customer does not belong to shop")
    obj=LostSale(shop_id=shop_id,**body.model_dump());obj.requested_product=obj.requested_product.strip();db.add(obj);db.commit();return obj
@router.get("")
def list_lost(month:date|None=None,shop_id=Depends(shop_access),db:Session=Depends(get_db)):
    d=month or date.today();start=datetime(d.year,d.month,1,tzinfo=timezone.utc);end=datetime(d.year+(d.month==12),(d.month%12)+1,1,tzinfo=timezone.utc)
    rows=db.execute(select(func.lower(LostSale.requested_product),func.count(LostSale.id),func.coalesce(func.sum(LostSale.quantity),0),func.min(LostSale.requested_product)).where(LostSale.shop_id==shop_id,LostSale.occurred_at>=start,LostSale.occurred_at<end).group_by(func.lower(LostSale.requested_product)).order_by(func.count(LostSale.id).desc())).all();return [{"requested_product":x[3],"request_count":x[1],"total_quantity":x[2],"message":f"Customers asked for this {x[1]} time(s) this month"} for x in rows]
@router.post("/{lost_sale_id}/convert",response_model=ProductOut)
def convert(lost_sale_id:uuid.UUID,body:LostSaleConvert,shop_id=Depends(shop_access),db:Session=Depends(get_db)):
    lost=db.scalar(select(LostSale).where(LostSale.id==lost_sale_id,LostSale.shop_id==shop_id))
    if not lost:raise HTTPException(404,"Request not found")
    product=Product(shop_id=shop_id,name=lost.requested_product,buy_price=body.buy_price,sell_price=body.sell_price,unit=body.unit,inventory_enabled=body.inventory_enabled,active=True);db.add(product);db.flush();lost.converted_product_id=product.id;db.commit();return product

