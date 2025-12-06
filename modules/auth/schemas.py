from fastapi_users import schemas


class UserRead(schemas.BaseUser[int]):
    """Schema para leer datos de usuario (sin password)"""
    pass


class UserCreate(schemas.BaseUserCreate):
    """Schema para crear nuevo usuario"""
    pass


class UserUpdate(schemas.BaseUserUpdate):
    """Schema para actualizar usuario"""
    pass
