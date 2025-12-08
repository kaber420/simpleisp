from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from database import get_session
from modules.auth.config import current_active_user
from modules.auth.models import User
from modules.clients.models import Client
from modules.clients.schemas import ClientWithStats
from modules.clients.service import (
    get_all_clients_with_stats,
    create_new_client,
    update_existing_client,
    delete_existing_client
)

router = APIRouter(prefix="/api/clients", tags=["clients"])


@router.get("", response_model=List[ClientWithStats])
async def get_clients(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user)
):
    return await get_all_clients_with_stats(session)


@router.post("")
async def create_client(
    client: Client,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user)
):
    return await create_new_client(session, client)


@router.put("/{client_id}")
async def update_client(
    client_id: int,
    client_data: Client,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user)
):
    return await update_existing_client(session, client_id, client_data)


@router.delete("/{client_id}")
async def delete_client(
    client_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user)
):
    return await delete_existing_client(session, client_id)