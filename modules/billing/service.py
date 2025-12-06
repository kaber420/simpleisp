
import asyncio
from datetime import date
from sqlmodel import select
from sqlalchemy.orm import selectinload
from utils.logging import logger
from database import async_session_maker
from modules.clients.models import Client
from modules.billing.models import Payment
from modules.clients.service import sync_client_mikrotik
from modules.settings.service import get_system_settings

async def check_suspensions():
    """Tarea de fondo: Revisa pagos y suspende/activa."""
    while True:
        try:
            async with async_session_maker() as session:
                # Obtener la configuración completa del sistema
                settings = await get_system_settings(session)
                grace_days = int(settings.get("grace_days", "3"))
                
                # Eager load the 'router' relationship to avoid missing attributes
                result = await session.execute(select(Client).options(selectinload(Client.router)))
                clients = result.scalars().all()
                
                today = date.today()
                current_month_str = today.strftime("%Y-%m")
                
                for client in clients:
                    payment_query = select(Payment).where(
                        Payment.client_id == client.id, 
                        Payment.month_paid == current_month_str
                    )
                    payment_result = await session.execute(payment_query)
                    payment = payment_result.scalars().first()

                    should_be_suspended = False
                    # Regla: si hoy >= dia_corte + dias_de_gracia y no hay pago
                    grace_deadline = client.billing_day + grace_days
                    if not payment and today.day >= grace_deadline:
                        should_be_suspended = True
                        logger.debug(f"Cliente {client.name}: día {today.day} >= deadline {grace_deadline} (corte {client.billing_day} + {grace_days} días de gracia), sin pago de {current_month_str}")
                    
                    # Ensure client has a router assigned before attempting sync
                    if not client.router:
                         logger.warning(f"Client {client.name} has no router assigned. Skipping sync.")
                         continue

                    # Cambio de estado: Activo -> Suspendido
                    if should_be_suspended and client.status != 'suspended':
                        client.status = 'suspended'
                        session.add(client)
                        await session.commit()
                        await asyncio.to_thread(sync_client_mikrotik, client, True, settings, client.router)
                        logger.info(f"Cliente {client.name} SUSPENDIDO (día {today.day}, corte día {client.billing_day} + {grace_days} días de gracia, sin pago {current_month_str})")

                    # Cambio de estado: Suspendido -> Activo (Pagó o cambiaron fechas)
                    elif not should_be_suspended and client.status == 'suspended':
                        client.status = 'active'
                        session.add(client)
                        await session.commit()
                        await asyncio.to_thread(sync_client_mikrotik, client, False, settings, client.router)
                        logger.info(f"Cliente {client.name} REACTIVADO (tiene pago {current_month_str} o antes del deadline)")
        except Exception as e:
            logger.error(f"Error en check_suspensions: {e}")
        
        await asyncio.sleep(3600)
