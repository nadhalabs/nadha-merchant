from fastapi import APIRouter,Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..dependencies import get_db,shop_access
from ..models import AuditLog
router=APIRouter(prefix="/shops/{shop_id}/audit",tags=["audit"])
@router.get("")
def audit(shop_id=Depends(shop_access),db:Session=Depends(get_db)):return db.scalars(select(AuditLog).where(AuditLog.shop_id==shop_id).order_by(AuditLog.created_at.desc()).limit(200)).all()
