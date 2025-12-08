import asyncio
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import select

from database import get_session
from modules.auth.config import current_active_user
from modules.auth.models import User
from modules.billing.models import Payment
from modules.clients.models import Client
# Importamos la función que SÍ existe
from modules.clients.service import sync_client_mikrotik
# Importamos get_system_settings para pasar la configuración completa
from modules.settings.service import get_system_settings
from modules.billing.service import process_suspensions

router = APIRouter(prefix="/api/payments", tags=["payments"])

@router.post("/run-suspensions")
async def run_suspensions(
    user: User = Depends(current_active_user)
):
    """Ejecuta el proceso de cortes y suspensiones manualmente."""
    return await process_suspensions()


@router.get("/{client_id}")
async def get_payments(
    client_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user)
):
    query = select(Payment).where(Payment.client_id == client_id).order_by(Payment.date_paid.desc())
    res = await session.execute(query)
    return res.scalars().all()

@router.get("/check/{client_id}/{month}")
async def check_payment(
    client_id: int,
    month: str,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user)
):
    """Verifica si ya existe un pago para el cliente en el mes especificado"""
    query = select(Payment).where(
        Payment.client_id == client_id,
        Payment.month_paid == month
    )
    res = await session.execute(query)
    existing_payment = res.scalars().first()
    return {"paid": existing_payment is not None, "payment": existing_payment}

@router.post("")
async def add_payment(
    payment: Payment,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(current_active_user)
):
    # Verificar si ya existe un pago para este cliente en este mes
    query = select(Payment).where(
        Payment.client_id == payment.client_id,
        Payment.month_paid == payment.month_paid
    )
    res = await session.execute(query)
    existing_payment = res.scalars().first()
    
    if existing_payment:
        raise HTTPException(
            status_code=400, 
            detail=f"Ya existe un pago para el mes {payment.month_paid}"
        )
    
    session.add(payment)
    await session.commit()
    
    # Cargar cliente con su router para evitar errores en la sincronización
    result = await session.execute(
        select(Client).options(selectinload(Client.router)).where(Client.id == payment.client_id)
    )
    client = result.scalars().first()
    
    if client and client.status == 'suspended':
        client.status = 'active'
        session.add(client)
        await session.commit()
        
        if client.router:
            # Obtenemos el diccionario completo de settings
            settings = await get_system_settings(session)
            
            # Llamamos a la función correcta para reactivar al cliente en Mikrotik
            await asyncio.to_thread(sync_client_mikrotik, client, False, settings, client.router)
        
    return payment
