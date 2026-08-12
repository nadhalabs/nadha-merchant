from decimal import Decimal
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session
from ..models import LedgerEntry, LedgerKind
def balance(db: Session, shop_id, *, customer_id=None, supplier_id=None):
    positive=(LedgerKind.customer_credit,LedgerKind.supplier_due)
    q=select(func.coalesce(func.sum(case((LedgerEntry.kind.in_(positive),LedgerEntry.amount),else_=-LedgerEntry.amount)),0)).where(LedgerEntry.shop_id==shop_id)
    q=q.where(LedgerEntry.customer_id==customer_id) if customer_id else q.where(LedgerEntry.supplier_id==supplier_id)
    return Decimal(db.scalar(q))

