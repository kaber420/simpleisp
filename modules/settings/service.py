
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from modules.settings.models import Settings

async def get_setting(session: AsyncSession, key: str, default: str = "") -> str:
    """Obtiene un valor de configuración individual."""
    statement = select(Settings).where(Settings.key == key)
    result = await session.execute(statement)
    setting = result.scalars().first()
    return setting.value if setting else default

async def set_setting(session: AsyncSession, key: str, value: str):
    """Crea o actualiza una configuración."""
    statement = select(Settings).where(Settings.key == key)
    result = await session.execute(statement)
    setting = result.scalars().first()
    
    if setting:
        setting.value = value
    else:
        setting = Settings(key=key, value=value)
        session.add(setting)
    
    await session.commit()
    return setting

async def get_system_settings(session: AsyncSession) -> dict:
    """Devuelve un diccionario con todas las configuraciones clave y sus defaults."""
    # Obtenemos todo de la DB para no hacer mil consultas
    result = await session.execute(select(Settings))
    all_settings = {s.key: s.value for s in result.scalars().all()}
    
    return {
        "suspension_speed": all_settings.get("suspension_speed", "1k/1k"),
        "suspension_method": all_settings.get("suspension_method", "queue"), # queue, address_list, both
        "address_list_name": all_settings.get("address_list_name", "clientes_activos"),
        "grace_days": all_settings.get("grace_days", "3")
    }
