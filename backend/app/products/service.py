from decimal import Decimal
from sqlalchemy import delete, select
from sqlalchemy.orm import Session
from ..models import InventoryMovement, InventoryMovementType, Product, Supplier, Transaction, TransactionItem, TransactionType
from ..schemas import ItemIn

def replace_items(db:Session,shop_id,transaction:Transaction,items:list[ItemIn]):
    old_ids=select(TransactionItem.id).where(TransactionItem.transaction_id==transaction.id)
    db.execute(delete(InventoryMovement).where(InventoryMovement.transaction_item_id.in_(old_ids)))
    db.execute(delete(TransactionItem).where(TransactionItem.transaction_id==transaction.id));db.flush()
    created=[]
    for data in items:
        product=db.scalar(select(Product).where(Product.id==data.product_id,Product.shop_id==shop_id))
        if not product: raise ValueError("Product does not belong to shop")
        price=data.unit_price if data.unit_price is not None else (product.sell_price if transaction.type==TransactionType.sale else product.buy_price)
        if price is None: raise ValueError("Unit price is required")
        cost=data.cost_price if data.cost_price is not None else product.buy_price
        supplier=db.get(Supplier,transaction.supplier_id) if transaction.supplier_id else None
        item=TransactionItem(transaction_id=transaction.id,product_id=product.id,product_name_snapshot=product.name,supplier_name_snapshot=supplier.name if supplier else None,quantity=data.quantity,unit_price=price,cost_price=cost,line_total=(data.quantity*price).quantize(Decimal("0.01")))
        db.add(item);db.flush();created.append(item)
        if product.inventory_enabled and transaction.type in (TransactionType.sale,TransactionType.purchase):
            delta=data.quantity if transaction.type==TransactionType.purchase else -data.quantity
            db.add(InventoryMovement(shop_id=shop_id,product_id=product.id,transaction_item_id=item.id,type=InventoryMovementType.purchase if delta>0 else InventoryMovementType.sale,quantity_delta=delta,reason=f"{transaction.type.value.title()} transaction",occurred_at=transaction.occurred_at))
    return created
