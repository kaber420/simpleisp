from fastapi import Depends
from fastapi_users import FastAPIUsers
from fastapi_users.authentication import (
    AuthenticationBackend,
    CookieTransport,
    JWTStrategy,
)
from modules.auth.models import User
from modules.auth.manager import get_user_manager
from modules.auth.database import get_user_db
import os


SECRET = os.getenv("SECRET_KEY", "CHANGE_ME_IN_PRODUCTION_USE_OPENSSL_RAND_HEX_32")


def get_jwt_strategy() -> JWTStrategy:
    """Estrategia JWT para las cookies"""
    return JWTStrategy(secret=SECRET, lifetime_seconds=86400)  # 24 horas


# Cookie transport - las cookies se usan para mantener la sesión
cookie_transport = CookieTransport(
    cookie_name="simpleisp_auth",
    cookie_max_age=86400,  # 24 horas
    cookie_httponly=True,  # Seguridad XSS
    cookie_secure=False,   # True en producción con HTTPS
)

# Authentication backend
auth_backend = AuthenticationBackend(
    name="cookie",
    transport=cookie_transport,
    get_strategy=get_jwt_strategy,
)

# FastAPI Users instance
fastapi_users = FastAPIUsers[User, int](
    get_user_manager,
    [auth_backend],
)

# Dependency para obtener usuario actual
current_active_user = fastapi_users.current_user(active=True)
