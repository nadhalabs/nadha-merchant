import uuid
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator
from .models import InventoryMovementType, LedgerKind, PaymentMethod, PaymentState, ProductUnit, TransactionType

class ORM(BaseModel): model_config = ConfigDict(from_attributes=True)
class Register(BaseModel): email: EmailStr; password: str = Field(min_length=8); name: str
class Login(BaseModel): email: EmailStr; password: str
class Token(BaseModel): access_token: str; token_type: str = "bearer"
class UserOut(ORM): id: uuid.UUID; email: str; name: str
class ShopCreate(BaseModel): name: str; phone: str | None = None; business_type: str | None = None; timezone: str = "Asia/Kolkata"; currency: str = "INR"
class ShopOut(ORM): id: uuid.UUID; name: str; phone: str | None; business_type: str | None; timezone: str; currency: str; ai_enabled:bool=False
class CustomerCreate(BaseModel): name: str; phone: str | None = None; notes: str | None = None
class CustomerOut(ORM): id: uuid.UUID; shop_id: uuid.UUID; name: str; phone: str | None; notes: str | None
class SupplierCreate(BaseModel): name: str; contact_person: str | None = None; phone: str | None = None; payment_terms:str|None=None; notes: str | None = None
class SupplierOut(ORM): id: uuid.UUID; shop_id: uuid.UUID; name: str; contact_person: str | None; phone: str | None; payment_terms:str|None; notes: str | None
class TransactionIn(BaseModel):
    type: TransactionType; amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2); payment_state: PaymentState | None = None; payment_method: PaymentMethod | None = None
    paid_amount: Decimal | None = Field(default=None, ge=0); cash_amount: Decimal | None = Field(default=None, ge=0); upi_amount: Decimal | None = Field(default=None, ge=0)
    customer_id: uuid.UUID | None = None; supplier_id: uuid.UUID | None = None; category: str | None = None; note: str | None = None; occurred_at: datetime
    @model_validator(mode="after")
    def validate_type(self):
        if self.type == TransactionType.sale and self.payment_method == PaymentMethod.credit and not self.customer_id: raise ValueError("Credit sale requires a customer")
        if self.type == TransactionType.sale and self.payment_method == PaymentMethod.mixed:
            if (self.cash_amount or 0) + (self.upi_amount or 0) > self.amount: raise ValueError("Mixed components exceed total")
        if self.type == TransactionType.purchase and self.payment_state is None: raise ValueError("Purchase requires payment_state")
        if self.type == TransactionType.expense and not self.category: raise ValueError("Expense requires category")
        return self
class TransactionOut(ORM):
    id: uuid.UUID; shop_id: uuid.UUID; type: TransactionType; amount: Decimal; payment_state: PaymentState | None; payment_method: PaymentMethod | None
    paid_amount: Decimal | None; cash_amount: Decimal | None; upi_amount: Decimal | None; customer_id: uuid.UUID | None; supplier_id: uuid.UUID | None; category: str | None; note: str | None; occurred_at: datetime; created_at: datetime; updated_at: datetime
class LedgerPayment(BaseModel): amount: Decimal = Field(gt=0); payment_method: PaymentMethod = PaymentMethod.cash; occurred_at: datetime; note: str | None = None; idempotency_key: str | None = Field(default=None,max_length=100)
class LedgerEntryOut(ORM): id: uuid.UUID; kind: LedgerKind; amount: Decimal; transaction_id: uuid.UUID | None; payment_method: PaymentMethod | None; occurred_at: datetime; note: str | None
class ClosingIn(BaseModel): date: date; actual_cash: Decimal = Field(ge=0); notes: str | None = Field(default=None,max_length=2000); idempotency_key:str|None=Field(default=None,min_length=8,max_length=100)
class CategoryIn(BaseModel): name:str
class ProductIn(BaseModel):
    name:str; category_id:uuid.UUID|None=None; buy_price:Decimal|None=Field(default=None,ge=0); sell_price:Decimal|None=Field(default=None,ge=0); unit:ProductUnit=ProductUnit.piece; inventory_enabled:bool=False; active:bool=True; notes:str|None=None
class ProductOut(ORM):
    id:uuid.UUID; shop_id:uuid.UUID; name:str; category_id:uuid.UUID|None; buy_price:Decimal|None; sell_price:Decimal|None; unit:ProductUnit; inventory_enabled:bool; active:bool; notes:str|None; created_at:datetime; updated_at:datetime
class ItemIn(BaseModel): product_id:uuid.UUID|None=None; item_name:str|None=Field(default=None,max_length=160); quantity:Decimal|None=Field(default=None,gt=0); unit:str|None=Field(default=None,max_length=30); unit_price:Decimal|None=Field(default=None,ge=0); amount:Decimal|None=Field(default=None,ge=0); cost_price:Decimal|None=Field(default=None,ge=0); note:str|None=Field(default=None,max_length=500)
class FinancialTransactionIn(TransactionIn):
    idempotency_key:str=Field(min_length=8,max_length=100)
    items:list[ItemIn]=Field(default_factory=list)
    bank_amount:Decimal|None=Field(default=None,ge=0)
    other_amount:Decimal|None=Field(default=None,ge=0)
class ItemOut(ORM): id:uuid.UUID; transaction_id:uuid.UUID; product_id:uuid.UUID|None; product_name_snapshot:str; supplier_name_snapshot:str|None; quantity:Decimal; unit_price:Decimal; cost_price:Decimal|None; line_total:Decimal; created_at:datetime; updated_at:datetime
class DiaryNoteIn(BaseModel):text:str=Field(min_length=1,max_length=2000);occurred_at:datetime
class AIQuestion(BaseModel):question:str=Field(min_length=2,max_length=500);language:str=Field(default="en",pattern="^(en|ml)$")
class ManualMovementIn(BaseModel): quantity_difference:Decimal; reason:str=Field(min_length=2,max_length=500); occurred_at:datetime; idempotency_key:str=Field(min_length=8,max_length=100)
class SetActualStockIn(BaseModel): actual_quantity:Decimal=Field(ge=0); reason:str=Field(min_length=2,max_length=500); occurred_at:datetime; idempotency_key:str=Field(min_length=8,max_length=100)
class LostSaleIn(BaseModel): requested_product:str=Field(min_length=1,max_length=200);quantity:Decimal|None=Field(default=None,gt=0);customer_id:uuid.UUID|None=None;note:str|None=None;occurred_at:datetime
class LostSaleConvert(BaseModel): buy_price:Decimal|None=Field(default=None,ge=0);sell_price:Decimal|None=Field(default=None,ge=0);unit:ProductUnit=ProductUnit.piece;inventory_enabled:bool=False
