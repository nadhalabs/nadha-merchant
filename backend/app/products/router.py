import uuid
from fastapi import APIRouter,Depends,HTTPException,Query
from sqlalchemy import func,select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from ..dependencies import get_db,shop_access
from ..models import InventoryMovement,Product,ProductCategory,Transaction,TransactionItem
from ..schemas import CategoryIn,ItemIn,ItemOut,ProductIn,ProductOut
from .service import replace_items
router=APIRouter(prefix="/shops/{shop_id}",tags=["products"])
def product_or_404(db,shop_id,id):
    obj=db.scalar(select(Product).where(Product.id==id,Product.shop_id==shop_id))
    if not obj:raise HTTPException(404,"Product not found")
    return obj
@router.post("/product-categories",status_code=201)
def category(body:CategoryIn,shop_id=Depends(shop_access),db:Session=Depends(get_db)):
    obj=ProductCategory(shop_id=shop_id,name=body.name.strip());db.add(obj)
    try:db.commit()
    except IntegrityError:db.rollback();raise HTTPException(409,"Category already exists")
    return obj
@router.get("/product-categories")
def categories(shop_id=Depends(shop_access),db:Session=Depends(get_db)):return db.scalars(select(ProductCategory).where(ProductCategory.shop_id==shop_id).order_by(ProductCategory.name)).all()
@router.post("/products",response_model=ProductOut,status_code=201)
def create(body:ProductIn,shop_id=Depends(shop_access),db:Session=Depends(get_db)):
    if body.category_id and not db.scalar(select(ProductCategory).where(ProductCategory.id==body.category_id,ProductCategory.shop_id==shop_id)):raise HTTPException(400,"Category does not belong to shop")
    obj=Product(shop_id=shop_id,**body.model_dump());obj.name=obj.name.strip();db.add(obj)
    try:db.commit()
    except IntegrityError:db.rollback();raise HTTPException(409,"A product with this name already exists")
    return obj
@router.get("/products")
def products(search:str|None=None,active:str|None="true",shop_id=Depends(shop_access),db:Session=Depends(get_db)):
    q=select(Product).where(Product.shop_id==shop_id)
    if active in ("true","false"):q=q.where(Product.active==(active=="true"))
    if search:q=q.where(func.lower(Product.name).contains(search.lower()))
    rows=db.scalars(q.order_by(Product.name)).all()
    return [{**ProductOut.model_validate(x).model_dump(),"stock":db.scalar(select(func.coalesce(func.sum(InventoryMovement.quantity_delta),0)).where(InventoryMovement.product_id==x.id))} for x in rows]
@router.put("/products/{product_id}",response_model=ProductOut)
def edit(product_id:uuid.UUID,body:ProductIn,shop_id=Depends(shop_access),db:Session=Depends(get_db)):
    obj=product_or_404(db,shop_id,product_id)
    for k,v in body.model_dump().items():setattr(obj,k,v)
    try:db.commit()
    except IntegrityError:db.rollback();raise HTTPException(409,"A product with this name already exists")
    return obj
@router.get("/transactions/{transaction_id}/items")
def items(transaction_id:uuid.UUID,shop_id=Depends(shop_access),db:Session=Depends(get_db)):
    tx=db.scalar(select(Transaction).where(Transaction.id==transaction_id,Transaction.shop_id==shop_id))
    if not tx:raise HTTPException(404,"Transaction not found")
    rows=db.scalars(select(TransactionItem).where(TransactionItem.transaction_id==tx.id)).all();total=sum((x.line_total for x in rows),0)
    return {"transaction_amount":tx.amount,"itemized_total":total,"difference":tx.amount-total,"complete":total==tx.amount,"items":[ItemOut.model_validate(x) for x in rows]}
@router.put("/transactions/{transaction_id}/items")
def attach(transaction_id:uuid.UUID,body:list[ItemIn],shop_id=Depends(shop_access),db:Session=Depends(get_db)):
    tx=db.scalar(select(Transaction).where(Transaction.id==transaction_id,Transaction.shop_id==shop_id))
    if not tx:raise HTTPException(404,"Transaction not found")
    if tx.idempotency_key:raise HTTPException(409,"Items for finalized financial entries cannot be changed separately")
    try:rows=replace_items(db,shop_id,tx,body);db.commit()
    except ValueError as e:db.rollback();raise HTTPException(400,str(e))
    total=sum((x.line_total for x in rows),0);return {"transaction_amount":tx.amount,"itemized_total":total,"difference":tx.amount-total,"complete":total==tx.amount,"items":[ItemOut.model_validate(x) for x in rows]}
