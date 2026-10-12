import os
import sys

# Ensure backend folder is on python path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from database import init_db
from seed_data import seed_database

# Import routers
from routes.dashboard import router as dashboard_router
from routes.orders import router as orders_router
from routes.invoices import router as invoices_router
from routes.customers import router as customers_router
from routes.drivers import router as drivers_router
from routes.expenses import router as expenses_router
from routes.whatsapp import router as whatsapp_router
from routes.products import router as products_router
from routes.sync import router as sync_router
from routes.employees import router as employees_router
from routes.auth import router as auth_router
from routes.purchases import router as purchases_router
from routes.creative_tasks import router as creative_tasks_router

app = FastAPI(title="نظام نبت لإدارة محلات الورد | Nabt Flowers ERP", version="1.0.0")

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize and seed database if not already (including weekly off and leave logic)
init_db()
seed_database()

# Static and Templates
static_dir = os.path.join(parent_dir, "static")
templates_dir = os.path.join(parent_dir, "templates")

app.mount("/static", StaticFiles(directory=static_dir), name="static")
templates = Jinja2Templates(directory=templates_dir)

# Register API Routers
app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(orders_router)
app.include_router(invoices_router)
app.include_router(customers_router)
app.include_router(drivers_router)
app.include_router(expenses_router)
app.include_router(purchases_router)
app.include_router(whatsapp_router)
app.include_router(products_router)
app.include_router(sync_router)
app.include_router(employees_router)
app.include_router(creative_tasks_router)

@app.api_route("/", methods=["GET", "HEAD"])
def serve_home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.api_route("/login", methods=["GET", "HEAD"])
def serve_login(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.api_route("/api/health", methods=["GET", "HEAD"])
def health_check():
    return {"status": "ok", "app": "Nabt Flowers ERP", "version": "1.0.2"}
