from fastapi import Depends, HTTPException, status
from modules.auth.models import User
from modules.auth.config import current_active_user


async def get_current_admin_user(
    user: User = Depends(current_active_user)
) -> User:
    """
    Dependency para verificar que el usuario actual es un superuser/admin.
    
    Uso:
        @app.get("/admin-only-route")
        async def admin_route(user: User = Depends(get_current_admin_user)):
            ...
    """
    if not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos de administrador"
        )
    return user
