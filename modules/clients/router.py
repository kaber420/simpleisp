import asyncio
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from sqlalchemy.exc import IntegrityError

from database import get_session
from modules.auth.config import current_active_user
from modules.auth.models import User
from utils.logging import logger
from modules.clients.models import Client
from modules.routers.models import Router
from modules.clients.service import sync_client_mikrotik, remove_client_mikrotik
from modules.settings.service import get_system_settings

router = APIRouter(prefix="/api/clients", tags=["clients"])

async def get_client_router(session: AsyncSession, client: Client):
    if client.router_id:
        return await session.get(Router, client.router_id)
    res = await session.execute(select(Router))
    return res.scalars().first()

@router.get("")
async def get_clients(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user)
):
    result = await session.execute(select(Client))
    return result.scalars().all()

@router.post("")
async def create_client(
    client: Client,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user)
):
    try:
        # Assign default router if not set? Or let the UI handle it?
        # For now, if not set, we can assign the default one logic later or leave as None
        # but sync needs a router.
        
        session.add(client)
        await session.commit()
        await session.refresh(client)
        
        # Crear cola en Router
        settings = await get_system_settings(session)
        router_db = await get_client_router(session, client)
        
        if router_db:
            # If router was implicit (fallback), maybe we should save it? 
            # But let's just sync for now.
            if not client.router_id:
                 client.router_id = router_db.id
                 session.add(client)
                 await session.commit()
            
            await asyncio.to_thread(sync_client_mikrotik, client, False, settings, router_db)
        
        return client
    except IntegrityError as e:
        await session.rollback()
        if "unique" in str(e).lower() and "ip_address" in str(e).lower():
            raise HTTPException(status_code=400, detail="Error: La dirección IP ya está registrada.")
        raise HTTPException(status_code=400, detail="Error de integridad: Verifique los datos (IP duplicada o Router inválido).")
    except Exception as e:
        logger.error(f"Error creando cliente: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{client_id}")
async def delete_client(
    client_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user)
):
    client = await session.get(Client, client_id)
    if client:
        # Eliminar del Mikrotik usando la función correcta
        settings = await get_system_settings(session)
        router_db = await get_client_router(session, client)
        
        if router_db:
            await asyncio.to_thread(remove_client_mikrotik, client.name, client.ip_address, settings, router_db)
            
        await session.delete(client)
        await session.commit()
    return {"ok": True}

@router.put("/{client_id}")
async def update_client(
    client_id: int,
    client_data: Client,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user)
):
    client = await session.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    client.name = client_data.name
    client.ip_address = client_data.ip_address
    client.limit_max_upload = client_data.limit_max_upload
    client.limit_max_download = client_data.limit_max_download
    client.billing_day = client_data.billing_day
    # Update router_id if provided?
    if client_data.router_id is not None:
        client.router_id = client_data.router_id
    
    try:
        session.add(client)
        await session.commit()
        await session.refresh(client)
        
        # Actualizamos la cola en el Router inmediatamente
        settings = await get_system_settings(session)
        router_db = await get_client_router(session, client)
        
        if router_db:
            await asyncio.to_thread(sync_client_mikrotik, client, client.status == 'suspended', settings, router_db)
        
        return client
    except Exception as e:
        logger.error(f"Error actualizando cliente: {e}")
        raise HTTPException(status_code=500, detail="Error al actualizar.")