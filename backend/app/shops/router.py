from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..dependencies import current_user, get_db, shop_access
from ..models import Shop, ShopMember, User
from ..schemas import ShopCreate, ShopOut
router = APIRouter(prefix="/shops", tags=["shops"])
@router.post("", response_model=ShopOut, status_code=201)
def create(body: ShopCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    shop = Shop(**body.model_dump()); db.add(shop); db.flush(); db.add(ShopMember(shop_id=shop.id, user_id=user.id)); db.commit(); return shop
@router.get("", response_model=list[ShopOut])
def list_shops(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return db.scalars(select(Shop).join(ShopMember).where(ShopMember.user_id == user.id)).all()
@router.get("/{shop_id}", response_model=ShopOut)
def get_shop(shop_id=Depends(shop_access), db: Session = Depends(get_db)): return db.get(Shop, shop_id)

