import asyncio
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_session
from modules.auth.config import current_active_user
from modules.auth.dependencies import get_current_admin_user
from modules.auth.models import User
from modules.routers.schemas import RouterCreate, RouterRead, RouterUpdate
from modules.routers.service import router_service
from modules.routers.utils import fetch_router_stats

router = APIRouter(prefix="/api/routers", tags=["routers"])

@router.get("", response_model=List[RouterRead], dependencies=[Depends(current_active_user)])
async def get_routers(
    session: AsyncSession = Depends(get_session),
):
    return await router_service.get_all(session)

@router.get("/{router_id}", response_model=RouterRead, dependencies=[Depends(current_active_user)])
async def get_router(
    router_id: int,
    session: AsyncSession = Depends(get_session),
):
    router_item = await router_service.get_by_id(session, router_id)
    if not router_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Router not found")
    return router_item

@router.get("/{router_id}/stats", dependencies=[Depends(current_active_user)])
async def get_router_stats(
    router_id: int,
    session: AsyncSession = Depends(get_session),
):
    """Fetches real-time system stats (CPU, RAM, HDD, uptime) for a specific router."""
    router_item = await router_service.get_by_id(session, router_id)
    if not router_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Router not found")
    
    # Run the blocking API call in a thread pool
    stats = await asyncio.to_thread(fetch_router_stats, router_item)
    return stats

@router.post("", response_model=RouterRead, dependencies=[Depends(get_current_admin_user)])
async def create_router(
    router_in: RouterCreate,
    session: AsyncSession = Depends(get_session),
):
    return await router_service.create(session, router_in)

@router.put("/{router_id}", response_model=RouterRead, dependencies=[Depends(get_current_admin_user)])
async def update_router(
    router_id: int,
    router_in: RouterUpdate,
    session: AsyncSession = Depends(get_session),
):
    router_item = await router_service.update(session, router_id, router_in)
    if not router_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Router not found")
    return router_item

@router.delete("/{router_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(get_current_admin_user)])
async def delete_router(
    router_id: int,
    session: AsyncSession = Depends(get_session),
):
    success = await router_service.delete(session, router_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Router not found")
    return None
