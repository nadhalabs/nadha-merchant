from decimal import Decimal
from sqlalchemy import delete, select
from sqlalchemy.orm import Session
from ..models import InventoryMovement, InventoryMovementType, LedgerEntry, LedgerKind, PaymentMethod, PaymentState, Product, Transaction, TransactionItem, TransactionType

ZERO = Decimal("0.00")
def rebuild_ledger(db: Session, tx: Transaction) -> None:
    db.execute(delete(LedgerEntry).where(LedgerEntry.transaction_id == tx.id))
    entry = None
    if tx.type == TransactionType.sale and tx.customer_id:
        paid = tx.paid_amount or ZERO
        if tx.payment_method == PaymentMethod.credit: paid = ZERO
        elif tx.payment_method == PaymentMethod.mixed: paid = (tx.cash_amount or ZERO) + (tx.upi_amount or ZERO)+(tx.bank_amount or ZERO)+(tx.other_amount or ZERO)
        due = tx.amount - paid
        if due > 0: entry = LedgerEntry(shop_id=tx.shop_id, customer_id=tx.customer_id, transaction_id=tx.id, kind=LedgerKind.customer_credit, amount=due, occurred_at=tx.occurred_at, note=tx.note)
    if tx.type == TransactionType.purchase and tx.supplier_id:
        paid = tx.amount if tx.payment_state == PaymentState.paid else (tx.paid_amount or ZERO)
        due = tx.amount - paid
        if due > 0: entry = LedgerEntry(shop_id=tx.shop_id, supplier_id=tx.supplier_id, transaction_id=tx.id, kind=LedgerKind.supplier_due, amount=due, occurred_at=tx.occurred_at, note=tx.note)
    if entry: db.add(entry)

def rebuild_inventory(db:Session,tx:Transaction)->None:
    items=db.scalars(select(TransactionItem).where(TransactionItem.transaction_id==tx.id)).all()
    for item in items:
        db.execute(delete(InventoryMovement).where(InventoryMovement.transaction_item_id==item.id))
        product=db.get(Product,item.product_id)
        if product and product.inventory_enabled and tx.type in (TransactionType.sale,TransactionType.purchase):
            delta=item.quantity if tx.type==TransactionType.purchase else -item.quantity
            db.add(InventoryMovement(shop_id=tx.shop_id,product_id=item.product_id,transaction_item_id=item.id,type=InventoryMovementType.purchase if delta>0 else InventoryMovementType.sale,quantity_delta=delta,reason=f"{tx.type.value.title()} transaction",occurred_at=tx.occurred_at))
