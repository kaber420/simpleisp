from typing import Dict, Any
from utils.logging import logger
from modules.clients.models import Client
from modules.routers.models import Router
from modules.routers.connection_manager import manager

def format_bytes(bytes_str: str) -> str:
    """Converts bytes string to human readable format."""
    try:
        bytes_val = int(bytes_str)
    except (ValueError, TypeError):
        return "0 B"
    
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_val < 1024:
            return f"{bytes_val:.1f} {unit}"
        bytes_val /= 1024
    return f"{bytes_val:.1f} PB"

def format_rate(rate_str: str) -> str:
    """Converts rate string to human readable format (bps)."""
    try:
        rate_val = int(rate_str)
    except (ValueError, TypeError):
        return "0 bps"
    
    for unit in ['bps', 'Kbps', 'Mbps', 'Gbps']:
        if rate_val < 1000:
            return f"{rate_val:.1f} {unit}"
        rate_val /= 1000
    return f"{rate_val:.1f} Tbps"

def get_router_queue_stats(router_db: Router) -> Dict[str, Dict[str, Any]]:
    """
    Fetches queue statistics from MikroTik router.
    Returns a dict mapping target IP -> stats dict.
    """
    stats = {}
    try:
        with manager.get_locked_connection(router_db) as api:
            queue_res = api.get_resource('/queue/simple')
            queues = queue_res.get()
            
            for q in queues:
                target = q.get('target', '')
                # Remove /32 suffix if present
                if target.endswith('/32'):
                    target = target[:-3]
                
                stats[target] = {
                    'total_upload': format_bytes(q.get('bytes', '0/0').split('/')[0]),
                    'total_download': format_bytes(q.get('bytes', '0/0').split('/')[-1]),
                    'current_upload_speed': format_rate(q.get('rate', '0/0').split('/')[0]),
                    'current_download_speed': format_rate(q.get('rate', '0/0').split('/')[-1]),
                }
    except Exception as e:
        logger.warning(f"Error fetching queue stats from router {router_db.name}: {e}")
        manager.disconnect(router_db.id)
    
    return stats

def sync_client_mikrotik(client: Client, suspend: bool, settings: dict, router_db: Router):
    """
    Sincroniza el estado del cliente en Mikrotik (Cola y Address List)
    según la configuración elegida.
    Incluye lógica de reintento en caso de desconexión.
    """
    # Configuraciones generales
    method = settings.get("suspension_method", "queue")
    susp_speed = settings.get("suspension_speed", "1k/1k")
    list_name = settings.get("address_list_name", "clientes_activos")

    # Definir parámetros según estado
    if suspend and method in ["queue", "both"]:
        max_limit = susp_speed
        comment = f"SUSPENDIDO - {client.name}"
    else:
        max_limit = f"{client.limit_max_upload}/{client.limit_max_download}"
        comment = f"Cliente: {client.name}"

    for attempt in range(2):
        try:
            # Usar conexión con bloqueo thread-safe
            with manager.get_locked_connection(router_db) as api:
                # --- 1. GESTIONAR COLA (SIMPLE QUEUE) ---
                queue_res = api.get_resource('/queue/simple')
                existing_queue = queue_res.get(name=client.name)
                if not existing_queue:
                    existing_queue = queue_res.get(target=f"{client.ip_address}/32")

                if existing_queue:
                    queue_res.set(id=existing_queue[0]['id'], max_limit=max_limit, target=client.ip_address, comment=comment)
                else:
                    queue_res.add(name=client.name, target=client.ip_address, max_limit=max_limit, comment=comment)

                # --- 2. GESTIONAR ADDRESS LIST ---
                if method in ["address_list", "both"]:
                    addr_list_res = api.get_resource('/ip/firewall/address-list')
                    existing_item = addr_list_res.get(address=client.ip_address, list=list_name)
                    should_disable = 'yes' if suspend else 'no'
                    
                    if existing_item:
                        if existing_item[0]['disabled'] != should_disable:
                            addr_list_res.set(id=existing_item[0]['id'], disabled=should_disable, comment=client.name)
                    else:
                        addr_list_res.add(list=list_name, address=client.ip_address, comment=client.name, disabled=should_disable)
            
            # Si llegamos aquí, todo funcionó bien
            break

        except Exception as e:
            logger.warning(f"Error sincronizando Mikrotik para {client.name} (intento {attempt+1}/2): {e}")
            # Forzamos desconexión para renovar socket en el próximo intento
            manager.disconnect(router_db.id)
            if attempt == 1:
                logger.error(f"Fallo definitivo sincronizando {client.name}: {e}")

def remove_client_mikrotik(name: str, ip_address: str, settings: dict, router_db: Router):
    """Elimina cola y entrada de address list del cliente con reintento."""
    list_name = settings.get("address_list_name", "clientes_activos")

    for attempt in range(2):
        try:
            # Usar conexión con bloqueo thread-safe
            with manager.get_locked_connection(router_db) as api:
                # 1. Borrar Cola
                q_res = api.get_resource('/queue/simple')
                q = q_res.get(name=name) or q_res.get(target=f"{ip_address}/32")
                if q:
                    q_res.remove(id=q[0]['id'])
                    logger.info(f"Cola eliminada: {name}")

                # 2. Borrar de Address List
                al_res = api.get_resource('/ip/firewall/address-list')
                al = al_res.get(address=ip_address, list=list_name)
                if al:
                    al_res.remove(id=al[0]['id'])
                    logger.info(f"Address List eliminada: {name}")
            
            break

        except Exception as e:
            logger.warning(f"Error eliminando recursos de {name} (intento {attempt+1}/2): {e}")
            manager.disconnect(router_db.id)
            if attempt == 1:
                logger.error(f"Fallo definitivo eliminando {name}: {e}")


# --- High-Level Async Service Functions ---
import asyncio
from collections import defaultdict
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import select
from modules.clients.schemas import ClientWithStats
from modules.settings.service import get_system_settings


async def get_client_router(session: AsyncSession, client: Client):
    """Get the router for a client, or the first available router if not assigned."""
    if client.router_id:
        return await session.get(Router, client.router_id)
    res = await session.execute(select(Router))
    return res.scalars().first()


async def get_all_clients_with_stats(session: AsyncSession) -> List[ClientWithStats]:
    """
    Fetches all clients with their queue statistics from MikroTik.
    Groups clients by router and fetches stats efficiently.
    """
    result = await session.execute(
        select(Client).options(selectinload(Client.router))
    )
    clients = result.scalars().all()

    # Group clients by router_id
    clients_by_router = defaultdict(list)
    routers_map = {}

    for client in clients:
        if client.router_id:
            clients_by_router[client.router_id].append(client)
            if client.router and client.router_id not in routers_map:
                routers_map[client.router_id] = client.router

    # Fetch stats from each router
    router_stats = {}
    # Fetch stats from each router concurrently
    tasks = []
    router_ids = []
    for router_id, router_db in routers_map.items():
        tasks.append(asyncio.to_thread(get_router_queue_stats, router_db))
        router_ids.append(router_id)
    
    results = await asyncio.gather(*tasks)
    
    router_stats = {r_id: stats for r_id, stats in zip(router_ids, results)}

    # Build response with stats
    clients_with_stats = []
    for client in clients:
        stats = {}
        router_name = None

        if client.router_id and client.router_id in router_stats:
            stats = router_stats[client.router_id].get(client.ip_address, {})
            if client.router:
                router_name = client.router.name

        clients_with_stats.append(ClientWithStats(
            id=client.id,
            name=client.name,
            ip_address=client.ip_address,
            limit_max_upload=client.limit_max_upload,
            limit_max_download=client.limit_max_download,
            billing_day=client.billing_day,
            status=client.status,
            created_at=client.created_at,
            router_id=client.router_id,
            router_name=router_name,
            total_upload=stats.get('total_upload', '0 B'),
            total_download=stats.get('total_download', '0 B'),
            current_upload_speed=stats.get('current_upload_speed', '0 bps'),
            current_download_speed=stats.get('current_download_speed', '0 bps'),
        ))

    return clients_with_stats


async def create_new_client(session: AsyncSession, client_data: Client) -> Client:
    """
    Creates a new client, assigns a default router if needed, and syncs to MikroTik.
    """
    from sqlalchemy.exc import IntegrityError
    from fastapi import HTTPException

    try:
        session.add(client_data)
        await session.commit()
        await session.refresh(client_data)

        settings = await get_system_settings(session)
        router_db = await get_client_router(session, client_data)

        if router_db:
            if not client_data.router_id:
                client_data.router_id = router_db.id
                session.add(client_data)
                await session.commit()

            await asyncio.to_thread(sync_client_mikrotik, client_data, False, settings, router_db)

        return client_data
    except IntegrityError as e:
        await session.rollback()
        if "unique" in str(e).lower() and "ip_address" in str(e).lower():
            raise HTTPException(status_code=400, detail="Error: La dirección IP ya está registrada.")
        raise HTTPException(status_code=400, detail="Error de integridad: Verifique los datos (IP duplicada o Router inválido).")
    except Exception as e:
        logger.error(f"Error creando cliente: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def update_existing_client(session: AsyncSession, client_id: int, client_data: Client) -> Client:
    """
    Updates an existing client and syncs changes to MikroTik.
    """
    from fastapi import HTTPException

    client = await session.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    client.name = client_data.name
    client.ip_address = client_data.ip_address
    client.limit_max_upload = client_data.limit_max_upload
    client.limit_max_download = client_data.limit_max_download
    client.billing_day = client_data.billing_day
    if client_data.router_id is not None:
        client.router_id = client_data.router_id

    try:
        session.add(client)
        await session.commit()
        await session.refresh(client)

        settings = await get_system_settings(session)
        router_db = await get_client_router(session, client)

        if router_db:
            await asyncio.to_thread(sync_client_mikrotik, client, client.status == 'suspended', settings, router_db)

        return client
    except Exception as e:
        logger.error(f"Error actualizando cliente: {e}")
        raise HTTPException(status_code=500, detail="Error al actualizar.")


async def delete_existing_client(session: AsyncSession, client_id: int) -> dict:
    """
    Deletes a client and removes it from MikroTik.
    """
    client = await session.get(Client, client_id)
    if client:
        settings = await get_system_settings(session)
        router_db = await get_client_router(session, client)

        if router_db:
            await asyncio.to_thread(remove_client_mikrotik, client.name, client.ip_address, settings, router_db)

        await session.delete(client)
        await session.commit()
    return {"ok": True}

