

from fastapi import APIRouter, Depends, Body, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
import secrets

from database import get_session
from modules.auth.config import current_active_user
from modules.auth.models import User
from modules.settings.service import set_setting, get_system_settings

router = APIRouter(prefix="/api/settings", tags=["settings"])


class TelegramSaveRequest(BaseModel):
    token: str
    bot_name: str = ""


class ChatIdRequest(BaseModel):
    chat_id: str


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


# ============ TELEGRAM ENDPOINTS ============

@router.post("/telegram/save")
async def save_telegram_settings(
    data: TelegramSaveRequest,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user)
):
    """Save Telegram bot token and name to settings."""
    await set_setting(session, "telegram_bot_token", data.token)
    await set_setting(session, "telegram_bot_name", data.bot_name)
    return {"message": "Token de Telegram guardado"}


@router.post("/telegram/restart-bot")
async def restart_telegram_bot(
    user: User = Depends(current_active_user)
):
    """Restart the Telegram bot with the current token from settings."""
    from modules.bot.service import restart_bot
    
    success = await restart_bot()
    
    if success:
        return {"message": "Bot reiniciado correctamente", "status": "connected"}
    else:
        return {"message": "No se pudo iniciar el bot. Verifica el token.", "status": "disconnected"}


@router.get("/telegram/status")
async def get_telegram_status(
    user: User = Depends(current_active_user)
):
    """Get the current status of the Telegram bot."""
    from modules.bot.service import is_bot_running
    
    return {
        "status": "connected" if is_bot_running() else "disconnected"
    }


# ============ NOTIFICATION ENDPOINTS ============

@router.post("/notifications/generate-token")
async def generate_link_token(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user)
):
    """Generate a temporary token for linking Telegram account."""
    # Generate an 8-character alphanumeric token
    token = secrets.token_hex(4).upper()
    
    # Save to user
    user.telegram_link_token = token
    session.add(user)
    await session.commit()
    
    return {
        "token": token,
        "message": "Envía /link " + token + " al bot de Telegram"
    }


@router.post("/notifications/save-chat-id")
async def save_chat_id(
    data: ChatIdRequest,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user)
):
    """Manually save a Telegram chat ID for the current user."""
    if not data.chat_id.lstrip('-').isdigit():
        raise HTTPException(status_code=400, detail="Chat ID debe ser un número")
    
    user.telegram_chat_id = data.chat_id
    user.telegram_link_token = None  # Clear any pending link token
    session.add(user)
    await session.commit()
    
    return {"message": "Chat ID guardado correctamente"}


@router.post("/notifications/test-alert")
async def send_test_alert(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user)
):
    """Send a test message to the user's linked Telegram account."""
    from modules.bot.service import send_test_message, is_bot_running
    from modules.settings.service import get_setting
    
    if not is_bot_running():
        raise HTTPException(status_code=400, detail="El bot no está activo. Configura el token primero.")
    
    if not user.telegram_chat_id:
        raise HTTPException(status_code=400, detail="No tienes una cuenta de Telegram vinculada")
    
    bot_name = await get_setting(session, "telegram_bot_name", "SimpleISP")
    success = await send_test_message(user.telegram_chat_id, bot_name)
    
    if success:
        return {"message": "Mensaje de prueba enviado"}
    else:
        raise HTTPException(status_code=500, detail="Error al enviar mensaje. Verifica tu Chat ID.")


@router.get("/notifications/my-status")
async def get_my_notification_status(
    user: User = Depends(current_active_user)
):
    """Get the current user's notification settings."""
    return {
        "telegram_linked": user.telegram_chat_id is not None,
        "telegram_chat_id": user.telegram_chat_id,
        "receive_alerts": user.receive_alerts
    }


@router.post("/notifications/toggle-alerts")
async def toggle_alerts(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user)
):
    """Toggle whether the user receives alerts."""
    user.receive_alerts = not user.receive_alerts
    session.add(user)
    await session.commit()
    
    status = "activadas" if user.receive_alerts else "desactivadas"
    return {"message": f"Alertas {status}", "receive_alerts": user.receive_alerts}
