from typing import Optional
from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    """
    Modelo de Usuario compatible con FastAPI Users y SQLModel.
    
    Campos:
    - id: Primary key
    - email: Email único para login
    - hashed_password: Password hasheado con bcrypt
    - is_active: Usuario activo o inactivo
    - is_superuser: Admin con permisos completos
    - is_verified: Email verificado (para futuras expansiones)
    
    Telegram Integration:
    - telegram_chat_id: ID del chat de Telegram para notificaciones
    - telegram_link_token: Token temporal para vincular cuenta via /link
    - receive_alerts: Si el usuario desea recibir alertas de routers
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True, max_length=320)
    hashed_password: str = Field(max_length=1024)
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)
    is_verified: bool = Field(default=False)
    
    # Telegram Integration
    telegram_chat_id: Optional[str] = Field(default=None, index=True)
    telegram_link_token: Optional[str] = Field(default=None, index=True)
    receive_alerts: bool = Field(default=True)

