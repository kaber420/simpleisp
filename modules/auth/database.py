from fastapi import Depends
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession
from modules.auth.models import User
from database import get_session


async def get_user_db(session: AsyncSession = Depends(get_session)):
    """Database adapter para FastAPI Users"""
    yield SQLAlchemyUserDatabase(session, User)
