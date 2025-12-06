from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from database import get_session
from modules.auth.models import User
from modules.auth.schemas import UserRead
from modules.auth.dependencies import get_current_admin_user

router = APIRouter()

@router.get("/", response_model=List[UserRead])
async def get_all_users(
    user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    """List all users (Admin only)"""
    stmt = select(User)
    result = await session.execute(stmt)
    users = result.scalars().all()
    return users

@router.get("", response_model=List[UserRead], include_in_schema=False)
async def get_all_users_no_slash(
    user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    return await get_all_users(user, session)
