from decimal import Decimal
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session
from ..models import InventoryMovement, InventoryMovementType, Product, Supplier, Transaction, TransactionItem, TransactionType
from ..schemas import ItemIn

def replace_items(db:Session,shop_id,transaction:Transaction,items:list[ItemIn]):
    old_ids=select(TransactionItem.id).where(TransactionItem.transaction_id==transaction.id)
    db.execute(delete(InventoryMovement).where(InventoryMovement.transaction_item_id.in_(old_ids)))
    db.execute(delete(TransactionItem).where(TransactionItem.transaction_id==transaction.id));db.flush()
    created=[]
    for data in items:
        product=db.scalar(select(Product).where(Product.id==data.product_id,Product.shop_id==shop_id).with_for_update()) if data.product_id else None
        if data.product_id and not product: raise ValueError("Product does not belong to shop")
        name=(data.item_name or (product.name if product else "")).strip()
        if not name:raise ValueError("Item name is required")
        quantity=data.quantity or Decimal("1");price=data.amount if data.amount is not None else data.unit_price
        if price is None:price=Decimal("0")
        cost=data.cost_price if data.cost_price is not None else (product.buy_price if product else None)
        supplier=db.get(Supplier,transaction.supplier_id) if transaction.supplier_id else None
        line_total=(data.amount if data.amount is not None else quantity*price).quantize(Decimal("0.01"));item=TransactionItem(transaction_id=transaction.id,product_id=product.id if product else None,product_name_snapshot=name,supplier_name_snapshot=supplier.name if supplier else None,quantity=quantity,unit_price=price,cost_price=cost,line_total=line_total)
        db.add(item);db.flush();created.append(item)
        if product and product.inventory_enabled and transaction.type in (TransactionType.sale,TransactionType.purchase):
            delta=quantity if transaction.type==TransactionType.purchase else -quantity
            if delta<0:
                available=Decimal(db.scalar(select(func.coalesce(func.sum(InventoryMovement.quantity_delta),0)).where(InventoryMovement.product_id==product.id)))
                if available+delta<0:raise ValueError(f"Only {available} {product.unit.value} are in stock")
            db.add(InventoryMovement(shop_id=shop_id,product_id=product.id,transaction_item_id=item.id,type=InventoryMovementType.purchase if delta>0 else InventoryMovementType.sale,quantity_delta=delta,reason=f"{transaction.type.value.title()} transaction",occurred_at=transaction.occurred_at))
    return created
