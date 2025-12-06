from typing import Optional
from sqlmodel import Field, SQLModel
from fastapi_users.db import SQLAlchemyBaseUserTable


class User(SQLModel, SQLAlchemyBaseUserTable[int], table=True):
    """
    Modelo de Usuario compatible con FastAPI Users y SQLModel.
    
    Campos:
    - id: Primary key
    - email: Email único para login
    - hashed_password: Password hasheado con bcrypt
    - is_active: Usuario activo o inactivo
    - is_superuser: Admin con permisos completos
    - is_verified: Email verificado (para futuras expansiones)
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True, max_length=255)
    hashed_password: str
    is_active: bool = True
    is_superuser: bool = False
    is_verified: bool = False
