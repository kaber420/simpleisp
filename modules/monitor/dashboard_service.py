"""
Dashboard service for aggregated statistics.
Now uses cached router status for instant response.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, func

from modules.clients.models import Client
from modules.routers.models import Router
from modules.monitor.router_cache import router_cache


async def get_dashboard_summary(session: AsyncSession) -> dict:
    """
    Returns aggregated dashboard statistics INSTANTLY:
    - Clients: active/suspended counts (from DB - fast)
    - Routers: online/offline counts (from cache - instant)
    
    No network calls are made here. Router status comes from
    the background worker that updates the cache periodically.
    """
    # Get client counts by status (fast DB query)
    clients_result = await session.execute(
        select(Client.status, func.count(Client.id)).group_by(Client.status)
    )
    client_counts = dict(clients_result.all())
    clients_active = client_counts.get("active", 0)
    clients_suspended = client_counts.get("suspended", 0)
    
    # Get router count from DB (for total, in case cache is not yet populated)
    routers_result = await session.execute(
        select(func.count(Router.id)).where(Router.is_active == True)
    )
    total_routers = routers_result.scalar() or 0
    
    # Get router status from cache (INSTANT - no network calls)
    cache_summary = router_cache.get_summary()
    
    # If cache is not yet initialized, show DB count with "checking" status
    if not cache_summary["initialized"]:
        return {
            "routers": {
                "total": total_routers,
                "online": 0,
                "offline": 0,
                "offline_list": [],
                "checking": True  # Frontend can show "Verificando..."
            },
            "clients": {
                "total": clients_active + clients_suspended,
                "active": clients_active,
                "suspended": clients_suspended
            }
        }
    
    return {
        "routers": {
            "total": cache_summary["total"],
            "online": cache_summary["online"],
            "offline": cache_summary["offline"],
            "offline_list": cache_summary["offline_list"],
            "checking": False
        },
        "clients": {
            "total": clients_active + clients_suspended,
            "active": clients_active,
            "suspended": clients_suspended
        }
    }
