from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .auth.router import router as auth
from .shops.router import router as shops
from .transactions.router import router as transactions
from .customers.router import router as customers
from .suppliers.router import router as suppliers
from .closings.router import router as closings
from .products.router import router as products
from .inventory.router import router as inventory
from .profit.router import router as profit
from .health.router import router as health
from .recovery.router import router as recovery
from .lost_sales.router import router as lost_sales
from .insights.router import router as insights
from .audit.router import router as audit
app=FastAPI(title="Nadha Shop Ledger",version="1.0.0")
app.add_middleware(CORSMiddleware,allow_origins=settings.cors_origin_list,allow_credentials=True,allow_methods=["*"],allow_headers=["*"])
for router in (auth,shops,transactions,customers,suppliers,closings,products,inventory,profit,health,recovery,lost_sales,insights,audit): app.include_router(router,prefix="/api")
@app.get("/health")
def health(): return {"status":"ok"}
