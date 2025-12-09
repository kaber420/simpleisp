"""
Router Status Cache - Background service for router connectivity monitoring.
"""
import asyncio
import threading
from datetime import datetime
from typing import Dict, Optional
from dataclasses import dataclass, field

from utils.logging import logger
from modules.routers.connection_manager import manager


@dataclass
class RouterStatus:
    """Status information for a single router."""
    router_id: int
    name: str
    ip_address: str
    online: bool
    last_check: datetime
    error: Optional[str] = None


class RouterStatusCache:
    """
    In-memory cache for router connectivity status.
    Updated by background worker, read instantly by dashboard.
    """
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._statuses: Dict[int, RouterStatus] = {}
                    cls._instance._initialized = False
        return cls._instance
    
    def update_status(self, router_id: int, name: str, ip_address: str, online: bool, error: Optional[str] = None):
        """Update the cached status for a router."""
        with self._lock:
            self._statuses[router_id] = RouterStatus(
                router_id=router_id,
                name=name,
                ip_address=ip_address,
                online=online,
                last_check=datetime.now(),
                error=error
            )
            self._initialized = True
    
    def get_status(self, router_id: int) -> Optional[RouterStatus]:
        """Get cached status for a specific router."""
        with self._lock:
            return self._statuses.get(router_id)
    
    def get_all_statuses(self) -> Dict[int, RouterStatus]:
        """Get all cached router statuses."""
        with self._lock:
            return dict(self._statuses)
    
    def remove_router(self, router_id: int):
        """Remove a router from cache (when deleted)."""
        with self._lock:
            self._statuses.pop(router_id, None)
    
    def is_initialized(self) -> bool:
        """Check if cache has been populated at least once."""
        with self._lock:
            return self._initialized
    
    def get_summary(self) -> dict:
        """Get aggregated summary of router statuses."""
        with self._lock:
            statuses = list(self._statuses.values())
            online = [s for s in statuses if s.online]
            offline = [s for s in statuses if not s.online]
            
            return {
                "total": len(statuses),
                "online": len(online),
                "offline": len(offline),
                "offline_list": [
                    {
                        "id": s.router_id,
                        "name": s.name,
                        "ip_address": s.ip_address,
                        "online": False,
                        "error": s.error
                    }
                    for s in offline
                ],
                "initialized": self._initialized
            }


def check_router_connectivity(router_obj) -> dict:
    """
    Check if a router is reachable. Returns status dict.
    This runs in a thread pool.
    """
    try:
        with manager.get_locked_connection(router_obj) as api:
            api.get_resource('/system/identity').get()
            return {
                "router_id": router_obj.id,
                "name": router_obj.name,
                "ip_address": router_obj.ip_address,
                "online": True,
                "error": None
            }
    except Exception as e:
        logger.debug(f"Router {router_obj.name} offline: {e}")
        manager.disconnect(router_obj.id)
        return {
            "router_id": router_obj.id,
            "name": router_obj.name,
            "ip_address": router_obj.ip_address,
            "online": False,
            "error": str(e)
        }


async def router_status_worker(check_interval: int = 30):
    """
    Background worker that periodically checks router connectivity
    and updates the cache. Runs independently of user requests.
    """
    from database import async_session_maker
    from sqlmodel import select
    from modules.routers.models import Router
    
    cache = RouterStatusCache()
    
    logger.info(f"Router status worker started (interval: {check_interval}s)")
    
    while True:
        try:
            # Fetch all active routers from DB
            async with async_session_maker() as session:
                result = await session.execute(select(Router).where(Router.is_active == True))
                routers = result.scalars().all()
            
            if routers:
                # Check all routers in parallel
                tasks = [asyncio.to_thread(check_router_connectivity, r) for r in routers]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Update cache with results
                for result in results:
                    if isinstance(result, Exception):
                        logger.error(f"Error checking router: {result}")
                        continue
                    
                    cache.update_status(
                        router_id=result["router_id"],
                        name=result["name"],
                        ip_address=result["ip_address"],
                        online=result["online"],
                        error=result["error"]
                    )
                
                online_count = sum(1 for r in results if isinstance(r, dict) and r.get("online"))
                logger.debug(f"Router status check: {online_count}/{len(routers)} online")
            
            # Wait before next check
            await asyncio.sleep(check_interval)
            
        except Exception as e:
            logger.error(f"Router status worker error: {e}")
            await asyncio.sleep(10)  # Short retry on error


# Global cache instance
router_cache = RouterStatusCache()
