import json,uuid
from datetime import date
from decimal import Decimal
from fastapi import APIRouter, Depends,HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from ..audit.service import record
from ..dependencies import current_user,get_db, shop_access
from ..models import DayClosing,Shop,User
from ..schemas import ClosingIn
from .service import daily_totals,total_owed
router=APIRouter(prefix="/shops/{shop_id}",tags=["dashboard","closings"])
def serial(data): return {k:str(v) if isinstance(v,Decimal) else v for k,v in data.items()}
@router.get("/dashboard")
def dashboard(day:date|None=None,shop_id=Depends(shop_access),db:Session=Depends(get_db)):
    from datetime import datetime
    from zoneinfo import ZoneInfo
    local_day=day or datetime.now(ZoneInfo(db.get(Shop,shop_id).timezone)).date();totals=daily_totals(db,shop_id,local_day); totals["customers_owe_me"]=total_owed(db,shop_id,True);totals["i_owe_suppliers"]=total_owed(db,shop_id,False);return totals
@router.get("/today-register")
def today_register(day:date|None=None,shop_id=Depends(shop_access),db:Session=Depends(get_db)):
    return dashboard(day,shop_id,db)
@router.post("/closings",status_code=201)
def close(body:ClosingIn,shop_id=Depends(shop_access),user:User=Depends(current_user),db:Session=Depends(get_db)):
    if body.idempotency_key:
        by_key=db.scalar(select(DayClosing).where(DayClosing.shop_id==shop_id,DayClosing.idempotency_key==body.idempotency_key))
        if by_key:
            if by_key.date!=body.date or by_key.actual_cash!=body.actual_cash:raise HTTPException(409,"Idempotency key was already used for a different closing")
            return by_key
    existing=db.scalar(select(DayClosing).where(DayClosing.shop_id==shop_id,DayClosing.date==body.date))
    if existing:return existing
    totals=daily_totals(db,shop_id,body.date);totals["customers_owe_me"]=total_owed(db,shop_id,True);totals["i_owe_suppliers"]=total_owed(db,shop_id,False); obj=DayClosing(shop_id=shop_id,date=body.date,expected_cash=totals["expected_cash"],actual_cash=body.actual_cash,difference=body.actual_cash-totals["expected_cash"],upi_total=totals["upi_received"],notes=body.notes,snapshot=json.dumps(serial(totals)),idempotency_key=body.idempotency_key);db.add(obj)
    try:
        db.flush();record(db,shop_id,user.id,"create","day_closing",obj.id,after=obj)
        from ..diary.service import add_event
        add_event(db,shop_id,"day_closing.created","day_closing",obj.id,obj.created_at,user.id,metadata={"date":str(obj.date),"difference":str(obj.difference)});db.commit();return obj
    except IntegrityError:
        db.rollback();existing=db.scalar(select(DayClosing).where(DayClosing.shop_id==shop_id,DayClosing.date==body.date))
        if existing:return existing
        raise HTTPException(409,"This day was closed by another request")
@router.put("/closings/{closing_id}")
def edit_closing(closing_id:uuid.UUID,body:ClosingIn,shop_id=Depends(shop_access),user:User=Depends(current_user),db:Session=Depends(get_db)):
    obj=db.scalar(select(DayClosing).where(DayClosing.id==closing_id,DayClosing.shop_id==shop_id))
    if not obj:raise HTTPException(404,"Closing not found")
    before={c.name:getattr(obj,c.name) for c in obj.__table__.columns};totals=daily_totals(db,shop_id,body.date);obj.date=body.date;obj.expected_cash=totals["expected_cash"];obj.actual_cash=body.actual_cash;obj.difference=body.actual_cash-totals["expected_cash"];obj.upi_total=totals["upi_received"];obj.notes=body.notes;obj.snapshot=json.dumps(serial(totals));record(db,shop_id,user.id,"edit","day_closing",obj.id,before=before,after=obj);db.commit();return obj
@router.get("/closings")
def closings(shop_id=Depends(shop_access),db:Session=Depends(get_db)):
    rows=db.scalars(select(DayClosing).where(DayClosing.shop_id==shop_id).order_by(DayClosing.date.desc(),DayClosing.created_at.desc())).all();return [{"id":x.id,"date":x.date,"actual_cash":x.actual_cash,"notes":x.notes,"created_at":x.created_at,"snapshot":json.loads(x.snapshot),"expected_cash":x.expected_cash,"difference":x.difference} for x in rows]
@router.get("/closings/{closing_id}")
def closing_detail(closing_id:uuid.UUID,shop_id=Depends(shop_access),db:Session=Depends(get_db)):
    x=db.scalar(select(DayClosing).where(DayClosing.id==closing_id,DayClosing.shop_id==shop_id))
    if not x:raise HTTPException(404,"Day Book entry not found")
    return {"id":x.id,"date":x.date,"actual_cash":x.actual_cash,"notes":x.notes,"created_at":x.created_at,"snapshot":json.loads(x.snapshot),"expected_cash":x.expected_cash,"difference":x.difference}
