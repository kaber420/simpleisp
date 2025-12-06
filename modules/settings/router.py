

from fastapi import APIRouter, Depends, Body
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_session
from modules.auth.config import current_active_user
from modules.auth.models import User
from modules.settings.service import set_setting, get_system_settings

router = APIRouter(prefix="/api/settings", tags=["settings"])

@router.get("/")
async def get_all_settings(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user)
):
    return await get_system_settings(session)

@router.post("/")
async def save_settings(
    data: dict = Body(...), 
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user)
):
    for key, value in data.items():
        await set_setting(session, key, str(value))
    return {"message": "Configuración guardada"}
