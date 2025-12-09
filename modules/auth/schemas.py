from typing import Optional
from fastapi_users import schemas


class UserRead(schemas.BaseUser[int]):
    """Schema para leer datos de usuario (sin password)"""
    telegram_chat_id: Optional[str] = None
    receive_alerts: bool = True


class UserCreate(schemas.BaseUserCreate):
    """Schema para crear nuevo usuario"""
    pass


class UserUpdate(schemas.BaseUserUpdate):
    """Schema para actualizar usuario"""
    telegram_chat_id: Optional[str] = None
    receive_alerts: Optional[bool] = None
