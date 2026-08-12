from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..dependencies import current_user, get_db
from ..models import User
from ..schemas import Login, Register, Token, UserOut
from .service import create_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])
@router.post("/register", response_model=Token, status_code=201)
def register(body: Register, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.email == body.email.lower())): raise HTTPException(409, "Email already registered")
    user = User(email=body.email.lower(), name=body.name.strip(), password_hash=hash_password(body.password)); db.add(user); db.commit()
    return Token(access_token=create_token(user.id))
@router.post("/login", response_model=Token)
def login(body: Login, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if not user or not verify_password(body.password, user.password_hash): raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    return Token(access_token=create_token(user.id))
@router.post("/logout", status_code=204)
def logout(user: User = Depends(current_user)): return None
@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)): return user

