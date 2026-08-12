import enum
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Index, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Role(str, enum.Enum): owner = "owner"
class TransactionType(str, enum.Enum): sale = "sale"; purchase = "purchase"; expense = "expense"
class PaymentMethod(str, enum.Enum): cash = "cash"; upi = "upi"; credit = "credit"; mixed = "mixed"; bank = "bank"; other = "other"
class PaymentState(str, enum.Enum): paid = "paid"; partial = "partial"; due = "due"
class LedgerKind(str, enum.Enum): customer_credit = "customer_credit"; customer_payment = "customer_payment"; supplier_due = "supplier_due"; supplier_payment = "supplier_payment"; adjustment = "adjustment"
class ProductUnit(str, enum.Enum): piece="piece"; packet="packet"; box="box"; kg="kg"; gram="gram"; litre="litre"; ml="ml"; dozen="dozen"; custom="custom"
class InventoryMovementType(str, enum.Enum): purchase="purchase"; sale="sale"; manual_increase="manual_increase"; manual_decrease="manual_decrease"; correction="correction"


class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Shop(Base):
    __tablename__ = "shops"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(160)); phone: Mapped[str | None] = mapped_column(String(30))
    business_type: Mapped[str | None] = mapped_column(String(80)); timezone: Mapped[str] = mapped_column(String(60), default="Asia/Kolkata")
    currency: Mapped[str] = mapped_column(String(3), default="INR"); created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ShopMember(Base):
    __tablename__ = "shop_members"; __table_args__ = (UniqueConstraint("shop_id", "user_id"),)
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    shop_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("shops.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[Role] = mapped_column(Enum(Role), default=Role.owner)


class Customer(Base):
    __tablename__ = "customers"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4); shop_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("shops.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(160)); phone: Mapped[str | None] = mapped_column(String(30)); notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Supplier(Base):
    __tablename__ = "suppliers"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4); shop_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("shops.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(160)); contact_person: Mapped[str | None] = mapped_column(String(160)); phone: Mapped[str | None] = mapped_column(String(30)); payment_terms: Mapped[str | None] = mapped_column(String(160)); notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__=(Index("ix_transactions_shop_type_occurred","shop_id","type","occurred_at"),)
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4); shop_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("shops.id", ondelete="CASCADE"), index=True)
    type: Mapped[TransactionType] = mapped_column(Enum(TransactionType)); amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    payment_state: Mapped[PaymentState | None] = mapped_column(Enum(PaymentState)); payment_method: Mapped[PaymentMethod | None] = mapped_column(Enum(PaymentMethod))
    paid_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2)); cash_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2)); upi_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    category: Mapped[str | None] = mapped_column(String(80)); customer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("customers.id", ondelete="RESTRICT"), index=True)
    supplier_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("suppliers.id", ondelete="RESTRICT"), index=True); note: Mapped[str | None] = mapped_column(Text)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True); created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow); updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"
    __table_args__=(Index("ix_ledger_shop_customer_date","shop_id","customer_id","occurred_at"),Index("ix_ledger_shop_supplier_date","shop_id","supplier_id","occurred_at"))
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4); shop_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("shops.id", ondelete="CASCADE"), index=True)
    customer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("customers.id", ondelete="RESTRICT"), index=True); supplier_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("suppliers.id", ondelete="RESTRICT"), index=True)
    transaction_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("transactions.id", ondelete="CASCADE"), index=True)
    kind: Mapped[LedgerKind] = mapped_column(Enum(LedgerKind)); amount: Mapped[Decimal] = mapped_column(Numeric(14, 2)); note: Mapped[str | None] = mapped_column(Text)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True); created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class DayClosing(Base):
    __tablename__ = "day_closings"
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4); shop_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("shops.id", ondelete="CASCADE"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True); expected_cash: Mapped[Decimal] = mapped_column(Numeric(14,2)); actual_cash: Mapped[Decimal] = mapped_column(Numeric(14,2)); difference: Mapped[Decimal] = mapped_column(Numeric(14,2)); upi_total: Mapped[Decimal] = mapped_column(Numeric(14,2)); notes: Mapped[str | None] = mapped_column(Text)
    snapshot: Mapped[str] = mapped_column(Text, default="{}"); created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow); updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

class ProductCategory(Base):
    __tablename__="product_categories"; __table_args__=(UniqueConstraint("shop_id","name",name="uq_product_category_shop_name"),)
    id: Mapped[uuid.UUID]=mapped_column(primary_key=True,default=uuid.uuid4); shop_id: Mapped[uuid.UUID]=mapped_column(ForeignKey("shops.id",ondelete="CASCADE"),index=True)
    name: Mapped[str]=mapped_column(String(100)); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)

class Product(Base):
    __tablename__="products"; __table_args__=(UniqueConstraint("shop_id","name",name="uq_product_shop_name"),)
    id: Mapped[uuid.UUID]=mapped_column(primary_key=True,default=uuid.uuid4); shop_id: Mapped[uuid.UUID]=mapped_column(ForeignKey("shops.id",ondelete="CASCADE"),index=True)
    name: Mapped[str]=mapped_column(String(160)); category_id: Mapped[uuid.UUID|None]=mapped_column(ForeignKey("product_categories.id",ondelete="SET NULL"),index=True)
    buy_price: Mapped[Decimal|None]=mapped_column(Numeric(14,2)); sell_price: Mapped[Decimal|None]=mapped_column(Numeric(14,2)); unit: Mapped[ProductUnit]=mapped_column(Enum(ProductUnit),default=ProductUnit.piece)
    inventory_enabled: Mapped[bool]=mapped_column(default=False); active: Mapped[bool]=mapped_column(default=True); notes: Mapped[str|None]=mapped_column(Text)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow); updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow,onupdate=utcnow)

class TransactionItem(Base):
    __tablename__="transaction_items"
    id: Mapped[uuid.UUID]=mapped_column(primary_key=True,default=uuid.uuid4); transaction_id: Mapped[uuid.UUID]=mapped_column(ForeignKey("transactions.id",ondelete="CASCADE"),index=True); product_id: Mapped[uuid.UUID]=mapped_column(ForeignKey("products.id",ondelete="RESTRICT"),index=True)
    product_name_snapshot: Mapped[str]=mapped_column(String(160),default=""); supplier_name_snapshot: Mapped[str|None]=mapped_column(String(160)); quantity: Mapped[Decimal]=mapped_column(Numeric(14,3)); unit_price: Mapped[Decimal]=mapped_column(Numeric(14,2)); cost_price: Mapped[Decimal|None]=mapped_column(Numeric(14,2)); line_total: Mapped[Decimal]=mapped_column(Numeric(14,2))
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow); updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow,onupdate=utcnow)

class InventoryMovement(Base):
    __tablename__="inventory_movements"
    __table_args__=(Index("ix_inventory_shop_product_date","shop_id","product_id","occurred_at"),)
    id: Mapped[uuid.UUID]=mapped_column(primary_key=True,default=uuid.uuid4); shop_id: Mapped[uuid.UUID]=mapped_column(ForeignKey("shops.id",ondelete="CASCADE"),index=True); product_id: Mapped[uuid.UUID]=mapped_column(ForeignKey("products.id",ondelete="RESTRICT"),index=True)
    transaction_item_id: Mapped[uuid.UUID|None]=mapped_column(ForeignKey("transaction_items.id",ondelete="CASCADE"),unique=True,index=True); type: Mapped[InventoryMovementType]=mapped_column(Enum(InventoryMovementType)); quantity_delta: Mapped[Decimal]=mapped_column(Numeric(14,3)); reason: Mapped[str]=mapped_column(Text); occurred_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),index=True); created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)

class LostSale(Base):
    __tablename__="lost_sales";__table_args__=(Index("ix_lost_sales_shop_requested_date","shop_id","requested_product","occurred_at"),)
    id:Mapped[uuid.UUID]=mapped_column(primary_key=True,default=uuid.uuid4);shop_id:Mapped[uuid.UUID]=mapped_column(ForeignKey("shops.id",ondelete="CASCADE"),index=True);requested_product:Mapped[str]=mapped_column(String(200));quantity:Mapped[Decimal|None]=mapped_column(Numeric(14,3));customer_id:Mapped[uuid.UUID|None]=mapped_column(ForeignKey("customers.id",ondelete="SET NULL"),index=True);note:Mapped[str|None]=mapped_column(Text);occurred_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),index=True);created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow);converted_product_id:Mapped[uuid.UUID|None]=mapped_column(ForeignKey("products.id",ondelete="SET NULL"))

class Insight(Base):
    __tablename__="insights";__table_args__=(Index("ix_insights_shop_created","shop_id","created_at"),)
    id:Mapped[uuid.UUID]=mapped_column(primary_key=True,default=uuid.uuid4);shop_id:Mapped[uuid.UUID]=mapped_column(ForeignKey("shops.id",ondelete="CASCADE"),index=True);type:Mapped[str]=mapped_column(String(80));title:Mapped[str]=mapped_column(String(240));explanation:Mapped[str]=mapped_column(Text);date_from:Mapped[date]=mapped_column(Date);date_to:Mapped[date]=mapped_column(Date);references_json:Mapped[str]=mapped_column(Text,default="[]");read:Mapped[bool]=mapped_column(Boolean,default=False);dismissed:Mapped[bool]=mapped_column(Boolean,default=False);created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow)

class AuditLog(Base):
    __tablename__="audit_logs";__table_args__=(Index("ix_audit_shop_entity_date","shop_id","entity","created_at"),)
    id:Mapped[uuid.UUID]=mapped_column(primary_key=True,default=uuid.uuid4);shop_id:Mapped[uuid.UUID]=mapped_column(ForeignKey("shops.id",ondelete="CASCADE"),index=True);actor_id:Mapped[uuid.UUID]=mapped_column(ForeignKey("users.id",ondelete="RESTRICT"),index=True);action:Mapped[str]=mapped_column(String(80));entity:Mapped[str]=mapped_column(String(80));entity_id:Mapped[uuid.UUID]=mapped_column(index=True);before_json:Mapped[str|None]=mapped_column(Text);after_json:Mapped[str|None]=mapped_column(Text);created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=utcnow,index=True)
