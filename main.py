import asyncio
import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request, Depends, Response, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

# Importar Configuración y Base de Datos
from database import init_db, get_session, async_session_maker
# Importar Modelos para que SQLModel los registre antes de crear tablas
from modules.clients.models import Client
from modules.routers.models import Router
from modules.billing.models import Payment
from modules.settings.models import Settings
from modules.auth.models import User  # Auth model

# Importar Routers y Servicios
from modules.clients.router import router as clients_router
from modules.billing.router import router as billing_router
from modules.monitor.router import router as monitor_router
from modules.settings.router import router as settings_router
from modules.routers.router import router as routers_router
from modules.auth.router import router as users_custom_router
from modules.billing.service import check_suspensions
from modules.monitor.router_cache import router_status_worker

# Importar Auth
from modules.auth.config import fastapi_users, auth_backend, current_active_user
from modules.auth.schemas import UserRead, UserCreate, UserUpdate
from modules.auth.dependencies import get_current_admin_user
from modules.auth.manager import get_user_manager
from modules.auth.database import get_user_db

# --- LIFESPAN EVENT HANDLER ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    asyncio.create_task(check_suspensions())
    asyncio.create_task(router_status_worker(check_interval=30))  # Check routers every 30s
    yield
    # Shutdown (add cleanup code here if needed)

# --- APP FASTAPI ---
app = FastAPI(title="SimpleISP", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# --- HELPER: Check if users exist ---
async def has_users() -> bool:
    """Check if any users exist in the database"""
    async with async_session_maker() as session:
        result = await session.execute(select(func.count(User.id)))
        count = result.scalar()
        return count > 0


# --- SETUP ROUTES (Initial Configuration) ---
class SetupAdminCreate(BaseModel):
    email: EmailStr
    password: str


@app.get("/setup", response_class=HTMLResponse)
async def setup_page(request: Request):
    """Setup page - only accessible when no users exist"""
    if await has_users():
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse("setup.html", {"request": request})


@app.post("/api/setup/create-admin")
async def create_initial_admin(data: SetupAdminCreate):
    """Create the initial admin user - only works when no users exist"""
    if await has_users():
        raise HTTPException(status_code=400, detail="Ya existe un usuario. Usa el login.")
    
    async with async_session_maker() as session:
        async for user_db in get_user_db(session):
            async for user_manager in get_user_manager(user_db):
                user_data = UserCreate(
                    email=data.email,
                    password=data.password,
                    is_superuser=True,
                    is_verified=True
                )
                try:
                    user = await user_manager.create(user_data)
                    return {"detail": "Administrador creado exitosamente", "email": user.email}
                except Exception as e:
                    raise HTTPException(status_code=400, detail=str(e))


# --- AUTH ROUTES ---
# Auth routes
app.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)

# Custom user routes (List users)
app.include_router(
    users_custom_router,
    prefix="/api/users",
    tags=["users"],
)

# User management routes (only for admins)
app.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/api/users",
    tags=["users"],
    dependencies=[Depends(get_current_admin_user)],
)

# Logout endpoint
@app.post("/auth/logout")
async def logout(response: Response, user: User = Depends(current_active_user)):
    """Logout endpoint - clears the auth cookie"""
    response.delete_cookie("simpleisp_auth")
    return {"detail": "Logout exitoso"}

# --- APP ROUTES ---
app.include_router(clients_router)
app.include_router(billing_router)
app.include_router(monitor_router)
app.include_router(settings_router)
app.include_router(routers_router)

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Login page - redirects to setup if no users exist"""
    if not await has_users():
        return RedirectResponse(url="/setup", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, user: User = Depends(current_active_user)):
    """Dashboard - requires authentication"""
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user
    })


# --- ENTRY POINT ---
if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8006"))
    uvicorn.run("main:app", host=host, port=port, reload=True)