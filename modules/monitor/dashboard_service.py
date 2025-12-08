"""
Dashboard service for aggregated statistics.
"""
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, func

from modules.clients.models import Client
from modules.routers.models import Router
from modules.routers.connection_manager import manager
from utils.logging import logger


def check_router_online(router_obj) -> dict:
    """
    Checks if a router is reachable by attempting a quick API call.
    Returns router info with online status.
    """
    try:
        with manager.get_locked_connection(router_obj) as api:
            # Quick identity check
            api.get_resource('/system/identity').get()
            return {
                "id": router_obj.id,
                "name": router_obj.name,
                "ip_address": router_obj.ip_address,
                "online": True
            }
    except Exception as e:
        logger.warning(f"Router {router_obj.name} offline: {e}")
        return {
            "id": router_obj.id,
            "name": router_obj.name,
            "ip_address": router_obj.ip_address,
            "online": False,
            "error": str(e)
        }


async def get_dashboard_summary(session: AsyncSession) -> dict:
    """
    Returns aggregated dashboard statistics:
    - Routers: online count, offline count, list of offline routers
    - Clients: active count, suspended count
    """
    # Get client counts by status
    clients_result = await session.execute(
        select(Client.status, func.count(Client.id)).group_by(Client.status)
    )
    client_counts = dict(clients_result.all())
    clients_active = client_counts.get("active", 0)
    clients_suspended = client_counts.get("suspended", 0)
    
    # Get all routers
    routers_result = await session.execute(select(Router).where(Router.is_active == True))
    routers = routers_result.scalars().all()
    
    # Check each router's connectivity (run in thread pool)
    router_statuses = []
    for router_obj in routers:
        status = await asyncio.to_thread(check_router_online, router_obj)
        router_statuses.append(status)
    
    # Aggregate router stats
    online_routers = [r for r in router_statuses if r["online"]]
    offline_routers = [r for r in router_statuses if not r["online"]]
    
    return {
        "routers": {
            "total": len(router_statuses),
            "online": len(online_routers),
            "offline": len(offline_routers),
            "offline_list": offline_routers
        },
        "clients": {
            "total": clients_active + clients_suspended,
            "active": clients_active,
            "suspended": clients_suspended
        }
    }
