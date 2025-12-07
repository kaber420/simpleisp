"""
Utility functions for router operations.
"""
from utils.logging import logger
from modules.routers.connection_manager import manager


def fetch_router_stats(router_obj):
    """
    Fetches system resource stats (CPU, RAM, HDD, uptime, model) from a MikroTik router.
    
    Args:
        router_obj: The Router model object with connection details.
        
    Returns:
        A dictionary with system stats, or an error dict if connection fails.
    """
    try:
        with manager.get_locked_connection(router_obj) as api:
            resource = api.get_resource('/system/resource').get()
            
            if not resource:
                return {"error": "No resource data returned"}
            
            res = resource[0]
            total_mem = int(res.get('total-memory', 1))
            free_mem = int(res.get('free-memory', 0))
            used_mem_perc = ((total_mem - free_mem) / total_mem) * 100

            total_hdd = int(res.get('total-hdd-space', 1))
            free_hdd = int(res.get('free-hdd-space', 0))
            used_hdd_perc = ((total_hdd - free_hdd) / total_hdd) * 100 if total_hdd > 0 else 0

            return {
                "cpu_load": int(res.get('cpu-load', 0)),
                "ram_usage": round(used_mem_perc, 1),
                "hdd_usage": round(used_hdd_perc, 1),
                "uptime": res.get('uptime', 'N/A'),
                "version": res.get('version', 'N/A'),
                "board": res.get('board-name', 'N/A'),
                "architecture": res.get('architecture-name', 'N/A'),
                "online": True
            }
    except Exception as e:
        logger.error(f"Error fetching stats for router {router_obj.name}: {e}")
        return {"online": False, "error": str(e)}
