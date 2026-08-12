import uuid
from datetime import datetime, timedelta, timezone
import jwt
from fastapi import HTTPException, status
from pwdlib import PasswordHash
from ..config import settings

hasher = PasswordHash.recommended()
def hash_password(value: str) -> str: return hasher.hash(value)
def verify_password(value: str, hashed: str) -> bool: return hasher.verify(value, hashed)
def create_token(user_id: uuid.UUID) -> str:
    return jwt.encode({"sub": str(user_id), "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_minutes)}, settings.secret_key, algorithm="HS256")
def decode_token(token: str) -> uuid.UUID:
    try: return uuid.UUID(jwt.decode(token, settings.secret_key, algorithms=["HS256"])["sub"])
    except Exception: raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")

