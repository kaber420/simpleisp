from typing import Optional
from fastapi import Depends, Request
from fastapi_users import BaseUserManager, IntegerIDMixin
from modules.auth.models import User
import os


SECRET = os.getenv("SECRET_KEY", "CHANGE_ME_IN_PRODUCTION_USE_OPENSSL_RAND_HEX_32")


class UserManager(IntegerIDMixin, BaseUserManager[User, int]):
    """
    User Manager para manejar lógica de usuarios.
    Personalizable para eventos como registro, login, etc.
    """
    reset_password_token_secret = SECRET
    verification_token_secret = SECRET

    async def on_after_register(self, user: User, request: Optional[Request] = None):
        print(f"Usuario {user.email} se ha registrado.")

    async def on_after_forgot_password(
        self, user: User, token: str, request: Optional[Request] = None
    ):
        print(f"Usuario {user.email} olvidó su contraseña. Token: {token}")

    async def on_after_request_verify(
        self, user: User, token: str, request: Optional[Request] = None
    ):
        print(f"Verificación solicitada para {user.email}. Token: {token}")


from modules.auth.database import get_user_db

async def get_user_manager(user_db=Depends(get_user_db)):
    """Dependency para obtener UserManager"""
    yield UserManager(user_db)
