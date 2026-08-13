"""Admin-only direct database command for Nadha AI entitlement.

Usage from backend/: python scripts/set_ai_entitlement.py SHOP_UUID on|off
Requires DATABASE_URL. This is intentionally not exposed as an HTTP endpoint.
"""
import sys,uuid
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.database import SessionLocal
from app.models import Shop
def main():
    if len(sys.argv)!=3 or sys.argv[2] not in ("on","off"):raise SystemExit("Usage: set_ai_entitlement.py SHOP_UUID on|off")
    try:shop_id=uuid.UUID(sys.argv[1])
    except ValueError:raise SystemExit("SHOP_UUID must be a valid UUID")
    with SessionLocal() as db:
        shop=db.get(Shop,shop_id)
        if not shop:raise SystemExit("Shop not found")
        shop.ai_enabled=sys.argv[2]=="on";db.commit();print(f"Nadha AI entitlement {'enabled' if shop.ai_enabled else 'disabled'} for shop {shop.id}")
if __name__=="__main__":main()
