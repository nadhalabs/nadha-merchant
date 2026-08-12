import uuid
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from .auth.service import decode_token
from .database import SessionLocal
from .models import ShopMember, User

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

def current_user(authorization: str | None = Header(None), db: Session = Depends(get_db)) -> User:
    if not authorization or not authorization.startswith("Bearer "): raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentication required")
    user_id = decode_token(authorization[7:])
    user = db.get(User, user_id)
    if not user: raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")
    return user

def shop_access(shop_id: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(get_db)) -> uuid.UUID:
    member = db.scalar(select(ShopMember).where(ShopMember.shop_id == shop_id, ShopMember.user_id == user.id))
    if not member: raise HTTPException(status.HTTP_404_NOT_FOUND, "Shop not found")
    return shop_id

