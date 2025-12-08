
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

async def process_suspensions():
    """Lógica principal de suspensión/reactivación que puede ser llamada manual o automáticamente."""
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
            
            processed_count = 0
            
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
                
                # Check if we are past the deadline
                if today.day >= grace_deadline:
                    if not payment:
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
                    processed_count += 1

                # Cambio de estado: Suspendido -> Activo (Pagó o cambiaron fechas)
                elif not should_be_suspended and client.status == 'suspended':
                    # Double check logic: if they are suspended, and they shouldn't be (because they paid OR it's not deadline yet)
                    # If they paid, 'payment' is not None. 
                    # If it's before deadline, 'today.day < grace_deadline'.
                    client.status = 'active'
                    session.add(client)
                    await session.commit()
                    await asyncio.to_thread(sync_client_mikrotik, client, False, settings, client.router)
                    logger.info(f"Cliente {client.name} REACTIVADO (tiene pago {current_month_str} o antes del deadline)")
                    processed_count += 1

            return {"detail": "Proceso de suspensión completado", "processed": processed_count}

    except Exception as e:
        logger.error(f"Error en process_suspensions: {e}")
        return {"detail": f"Error: {str(e)}"}

async def check_suspensions():
    """Tarea de fondo: Revisa pagos y suspende/activa una vez al día a la hora configurada."""
    from datetime import datetime, timedelta
    
    while True:
        try:
            # Obtener la hora configurada desde settings
            async with async_session_maker() as session:
                settings = await get_system_settings(session)
                check_time_str = settings.get("suspension_check_time", "09:00")
            
            # Parsear la hora configurada
            check_hour, check_minute = map(int, check_time_str.split(":"))
            
            # Calcular el próximo momento de ejecución
            now = datetime.now()
            next_run = now.replace(hour=check_hour, minute=check_minute, second=0, microsecond=0)
            
            # Si ya pasó la hora de hoy, programar para mañana
            if now >= next_run:
                next_run += timedelta(days=1)
            
            # Calcular segundos hasta la próxima ejecución
            seconds_until_run = (next_run - now).total_seconds()
            logger.info(f"Próxima revisión de suspensiones programada para {next_run.strftime('%Y-%m-%d %H:%M')}")
            
            # Esperar hasta la hora programada
            await asyncio.sleep(seconds_until_run)
            
            # Ejecutar el proceso de suspensiones
            await process_suspensions()
            
        except Exception as e:
            logger.error(f"Error en check_suspensions: {e}")
            # En caso de error, esperar 1 hora antes de reintentar
            await asyncio.sleep(3600)
