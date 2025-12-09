"""
Telegram Bot Service - Handles bot lifecycle, commands, and alert broadcasting.
"""
import asyncio
from typing import Optional
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandStart, Filter
from aiogram.types import Message

from utils.logging import logger

# Global bot instance
_bot: Optional[Bot] = None
_dispatcher: Optional[Dispatcher] = None
_bot_task: Optional[asyncio.Task] = None
_current_token: Optional[str] = None


async def get_bot_token() -> Optional[str]:
    """Fetch bot token from database Settings table."""
    from database import async_session_maker
    from modules.settings.service import get_setting
    
    try:
        async with async_session_maker() as session:
            token = await get_setting(session, "telegram_bot_token", "")
            return token if token else None
    except Exception as e:
        logger.error(f"Error fetching bot token: {e}")
        return None


async def get_users_with_telegram() -> list:
    """Get all users who have linked their Telegram account and want alerts."""
    from database import async_session_maker
    from sqlmodel import select
    from modules.auth.models import User
    
    try:
        async with async_session_maker() as session:
            result = await session.execute(
                select(User).where(
                    User.telegram_chat_id.isnot(None),
                    User.receive_alerts == True
                )
            )
            return result.scalars().all()
    except Exception as e:
        logger.error(f"Error fetching users with telegram: {e}")
        return []


async def link_user_by_token(link_token: str, chat_id: str) -> Optional[str]:
    """
    Link a Telegram chat ID to a user using their link token.
    Returns the user's email if successful, None otherwise.
    """
    from database import async_session_maker
    from sqlmodel import select
    from modules.auth.models import User
    
    try:
        async with async_session_maker() as session:
            result = await session.execute(
                select(User).where(User.telegram_link_token == link_token)
            )
            user = result.scalars().first()
            
            if user:
                user.telegram_chat_id = chat_id
                user.telegram_link_token = None  # Clear the token after use
                await session.commit()
                return user.email
            return None
    except Exception as e:
        logger.error(f"Error linking user: {e}")
        return None


async def is_telegram_user_allowed(chat_id: str) -> bool:
    """Check if the user is allowed to interact with the bot."""
    from database import async_session_maker
    from sqlmodel import select
    from modules.auth.models import User
    
    try:
        async with async_session_maker() as session:
            result = await session.execute(
                select(User).where(User.telegram_chat_id == chat_id)
            )
            user = result.scalars().first()
            return user is not None
    except Exception as e:
        logger.error(f"Error checking telegram user allowance: {e}")
        return False


async def get_router_summary() -> dict:
    """Get summary of router statuses."""
    from modules.monitor.router_cache import router_cache
    return router_cache.get_summary()


def setup_handlers(dp: Dispatcher):
    """Set up bot command handlers."""
    
    class IsUnknownUser(Filter):
        """Filter to check if user is NOT known/allowed."""
        async def __call__(self, message: Message) -> bool:
            return not await is_telegram_user_allowed(str(message.chat.id))

    @dp.message(Command("link"))
    async def cmd_link(message: Message):
        """Handle /link command to link Telegram account."""
        args = message.text.split()
        
        if len(args) < 2:
            await message.answer(
                "❌ *Uso incorrecto*\n\n"
                "Debes proporcionar el código de vinculación:\n"
                "`/link TU_CODIGO`\n\n"
                "Genera el código en el panel web → Notificaciones",
                parse_mode="Markdown"
            )
            return
        
        link_token = args[1].upper()
        chat_id = str(message.chat.id)
        
        email = await link_user_by_token(link_token, chat_id)
        
        if email:
            await message.answer(
                f"✅ *¡Cuenta vinculada exitosamente!*\n\n"
                f"Tu cuenta `{email}` ahora recibirá alertas de routers.\n\n"
                f"Usa /resumen para ver el estado actual de la red.",
                parse_mode="Markdown"
            )
        else:
            await message.answer(
                "❌ *Código inválido o expirado*\n\n"
                "Genera un nuevo código en el panel web → Notificaciones",
                parse_mode="Markdown"
            )

    @dp.message(IsUnknownUser())
    async def reject_unauthorized(message: Message):
        """Reject unauthorized users."""
        chat_id = message.chat.id
        await message.answer(
            "⛔ *Acceso Denegado*\n\n"
            "Este bot es privado y solo responde a usuarios registrados.\n\n"
            f"🆔 Tu Chat ID: `{chat_id}`\n\n"
            "Por favor, comparte este ID con el administrador para solicitar acceso\n"
            "o usa el comando `/link CODIGO` si tienes un código de vinculación.",
            parse_mode="Markdown"
        )

    @dp.message(CommandStart())
    async def cmd_start(message: Message):
        """Handle /start command."""
        await message.answer(
            "🌐 *¡Bienvenido a SimpleISP Bot!*\n\n"
            "Este bot te enviará alertas cuando un router se caiga o se recupere.\n\n"
            "*Comandos disponibles:*\n"
            "• /link CODIGO - Vincular tu cuenta\n"
            "• /resumen - Ver estado de la red\n"
            "• /caidos - Ver routers offline\n\n"
            "Para vincular tu cuenta, genera un código en el panel web y envía:\n"
            "`/link TU_CODIGO`",
            parse_mode="Markdown"
        )

    @dp.message(Command("resumen"))
    async def cmd_resumen(message: Message):
        """Handle /resumen command to show network summary."""
        summary = await get_router_summary()
        
        if not summary.get("initialized"):
            await message.answer(
                "⏳ *El sistema está iniciando...*\n\n"
                "El caché de routers aún no está disponible.\n"
                "Intenta de nuevo en unos segundos.",
                parse_mode="Markdown"
            )
            return
        
        total = summary["total"]
        online = summary["online"]
        offline = summary["offline"]
        
        if total == 0:
            await message.answer(
                "ℹ️ *No hay routers configurados*\n\n"
                "Agrega routers en el panel web para empezar a monitorear.",
                parse_mode="Markdown"
            )
            return
        
        percentage = (online / total * 100) if total > 0 else 0
        status_emoji = "🟢" if offline == 0 else "🟡" if percentage >= 80 else "🔴"
        
        await message.answer(
            f"{status_emoji} *Resumen de Red*\n\n"
            f"📊 Total de routers: *{total}*\n"
            f"🟢 Online: *{online}*\n"
            f"🔴 Offline: *{offline}*\n"
            f"📈 Disponibilidad: *{percentage:.1f}%*",
            parse_mode="Markdown"
        )
    
    @dp.message(Command("caidos"))
    async def cmd_caidos(message: Message):
        """Handle /caidos command to show offline routers."""
        summary = await get_router_summary()
        
        if not summary.get("initialized"):
            await message.answer(
                "⏳ *El sistema está iniciando...*\n\n"
                "El caché de routers aún no está disponible.",
                parse_mode="Markdown"
            )
            return
        
        offline_list = summary.get("offline_list", [])
        
        if not offline_list:
            await message.answer(
                "✅ *¡Todos los routers están activos!*\n\n"
                "No hay routers caídos en este momento.",
                parse_mode="Markdown"
            )
            return
        
        router_lines = []
        for r in offline_list:
            error_msg = f" - {r['error'][:30]}..." if r.get('error') else ""
            router_lines.append(f"• *{r['name']}* ({r['ip_address']}){error_msg}")
        
        routers_text = "\n".join(router_lines)
        
        await message.answer(
            f"🔴 *Routers Caídos ({len(offline_list)})*\n\n"
            f"{routers_text}",
            parse_mode="Markdown"
        )


async def broadcast_alert(alert_type: str, router_name: str, router_ip: str, error: str = None):
    """
    Send alert to all users with linked Telegram accounts.
    
    Args:
        alert_type: "down" for offline, "up" for recovery
        router_name: Name of the router
        router_ip: IP address of the router
        error: Optional error message
    """
    global _bot
    
    if not _bot:
        logger.debug("Bot not initialized, skipping alert")
        return
    
    users = await get_users_with_telegram()
    
    if not users:
        logger.debug("No users to notify")
        return
    
    if alert_type == "down":
        emoji = "🔴"
        status = "OFFLINE"
        error_text = f"\n\n📝 Error: `{error[:100]}`" if error else ""
        message = (
            f"{emoji} *Router {status}*\n\n"
            f"📍 *{router_name}*\n"
            f"🌐 IP: `{router_ip}`"
            f"{error_text}"
        )
    else:  # up
        emoji = "🟢"
        status = "ONLINE"
        message = (
            f"{emoji} *Router {status}*\n\n"
            f"📍 *{router_name}*\n"
            f"🌐 IP: `{router_ip}`\n\n"
            f"✅ El router se ha recuperado"
        )
    
    for user in users:
        try:
            await _bot.send_message(
                chat_id=user.telegram_chat_id,
                text=message,
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.warning(f"Failed to send alert to {user.email}: {e}")


async def send_test_message(chat_id: str, bot_name: str = "SimpleISP") -> bool:
    """Send a test message to verify the bot is working."""
    global _bot
    
    if not _bot:
        logger.error("Bot not initialized")
        return False
    
    try:
        await _bot.send_message(
            chat_id=chat_id,
            text=(
                f"🔔 *Mensaje de Prueba*\n\n"
                f"¡Tu conexión con {bot_name} está funcionando!\n\n"
                f"Recibirás alertas cuando un router se caiga o se recupere."
            ),
            parse_mode="Markdown"
        )
        return True
    except Exception as e:
        logger.error(f"Failed to send test message: {e}")
        return False


async def stop_bot():
    """Stop the current bot instance."""
    global _bot, _dispatcher, _bot_task, _current_token
    
    if _bot_task and not _bot_task.done():
        _bot_task.cancel()
        try:
            await _bot_task
        except asyncio.CancelledError:
            pass
    
    if _dispatcher:
        await _dispatcher.stop_polling()
        _dispatcher = None
    
    if _bot:
        await _bot.session.close()
        _bot = None
    
    _current_token = None
    logger.info("Telegram bot stopped")


async def initialize_bot(token: str) -> bool:
    """Initialize bot with the given token."""
    global _bot, _dispatcher, _current_token
    
    try:
        _bot = Bot(token=token)
        _dispatcher = Dispatcher()
        setup_handlers(_dispatcher)
        _current_token = token
        
        # Verify the bot token is valid
        bot_info = await _bot.get_me()
        logger.info(f"Telegram bot initialized: @{bot_info.username}")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize Telegram bot: {e}")
        _bot = None
        _dispatcher = None
        _current_token = None
        return False


async def run_bot_polling():
    """Run the bot polling loop."""
    global _bot, _dispatcher
    
    if not _bot or not _dispatcher:
        return
    
    try:
        await _dispatcher.start_polling(_bot)
    except asyncio.CancelledError:
        logger.info("Bot polling cancelled")
    except Exception as e:
        logger.error(f"Bot polling error: {e}")


async def start_telegram_bot():
    """
    Main entry point to start the Telegram bot.
    Called from main.py lifespan.
    """
    global _bot_task
    
    # Wait a bit for database to be ready
    await asyncio.sleep(2)
    
    token = await get_bot_token()
    
    if not token:
        logger.info("No Telegram bot token configured, bot will not start")
        return
    
    if await initialize_bot(token):
        _bot_task = asyncio.create_task(run_bot_polling())
        logger.info("Telegram bot started successfully")
    else:
        logger.warning("Failed to start Telegram bot")


async def restart_bot():
    """Restart the bot with a potentially new token."""
    global _bot_task
    
    await stop_bot()
    
    token = await get_bot_token()
    
    if not token:
        logger.info("No token configured, bot stopped")
        return False
    
    if await initialize_bot(token):
        _bot_task = asyncio.create_task(run_bot_polling())
        logger.info("Telegram bot restarted successfully")
        return True
    else:
        logger.warning("Failed to restart Telegram bot")
        return False


def is_bot_running() -> bool:
    """Check if the bot is currently running."""
    return _bot is not None and _current_token is not None


def get_bot() -> Optional[Bot]:
    """Get the current bot instance."""
    return _bot
