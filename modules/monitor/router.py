import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from utils.logging import logger
from modules.routers.connection_manager import manager
from modules.routers.models import Router
from database import async_session_maker, get_session
from sqlmodel import select
from modules.auth.config import current_active_user
from modules.monitor.dashboard_service import get_dashboard_summary

router = APIRouter(tags=["monitor"])

@router.websocket("/ws/traffic")
async def websocket_traffic(websocket: WebSocket):
    await websocket.accept()
    
    # Fetch default router (or make this dynamic via query param later)
    async with async_session_maker() as session:
        res = await session.execute(select(Router))
        router_db = res.scalars().first()

    if not router_db:
        logger.error("No router found for monitor.")
        await websocket.close()
        return

    # Función para obtener datos en un hilo separado para no bloquear
    def fetch_mikrotik_data(router_obj):
        try:
            # Usar conexión con bloqueo thread-safe
            with manager.get_locked_connection(router_obj) as api:
                # 1. Obtener Tráfico de Colas
                queues = api.get_resource('/queue/simple').get()
                traffic_map = {}
                
                for q in queues:
                    rx_bytes = 0
                    tx_bytes = 0
                    if 'bytes' in q:
                        parts = q['bytes'].split('/')
                        if len(parts) == 2:
                            tx_bytes = int(parts[0]) 
                            rx_bytes = int(parts[1])
                    
                    target_ip = q.get('target', '').split('/')[0]
                    traffic_map[target_ip] = {
                        "upload": tx_bytes,
                        "download": rx_bytes
                    }

                # 2. Obtener Recursos
                resource = api.get_resource('/system/resource').get()
                system_stats = {}
                if resource:
                    res = resource[0]
                    total_mem = int(res.get('total-memory', 1))
                    free_mem = int(res.get('free-memory', 0))
                    used_mem_perc = ((total_mem - free_mem) / total_mem) * 100
                    
                    system_stats = {
                        "cpu_load": res.get('cpu-load', '0'),
                        "uptime": res.get('uptime', ''),
                        "version": res.get('version', ''),
                        "board": res.get('board-name', ''),
                        "ram_usage": round(used_mem_perc, 1)
                    }

            return {
                "queues": traffic_map,
                "system": system_stats
            }

        except Exception as e:
            logger.error(f"Error leyendo Mikrotik: {e}")
            # Invalidate the broken connection so the next attempt creates a fresh one
            manager.disconnect(router_obj.id)
            return {"queues": {}, "system": {}}

    try:
        while True:
            data = await asyncio.to_thread(fetch_mikrotik_data, router_db)
            await websocket.send_json(data)
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        logger.info("Cliente WebSocket desconectado") 
    except Exception as e:
        logger.error(f"WS Error: {e}")


@router.get("/api/dashboard/summary", dependencies=[Depends(current_active_user)])
async def dashboard_summary(session: AsyncSession = Depends(get_session)):
    """
    Returns aggregated dashboard statistics:
    - Routers: online/offline counts and list of offline routers
    - Clients: active/suspended counts
    """
    return await get_dashboard_summary(session)