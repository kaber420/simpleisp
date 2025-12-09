"""
Utility functions for router operations.
"""
from utils.logging import logger
from modules.routers.connection_manager import manager


def format_bytes(bytes_value) -> str:
    """Convert bytes to human-readable format (KB, MB, GB, TB)."""
    if not bytes_value:
        return "0 B"
    try:
        size = float(bytes_value)
    except (ValueError, TypeError):
        return "0 B"
    
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024:
            return f"{size:.1f} {unit}" if unit != 'B' else f"{int(size)} {unit}"
        size /= 1024
    return f"{size:.1f} PB"


def fetch_router_interfaces(router_obj):
    """
    Fetches the list of interfaces from a MikroTik router.
    
    Args:
        router_obj: The Router model object with connection details.
        
    Returns:
        A list of interface dictionaries with name, comment, and type.
    """
    try:
        with manager.get_locked_connection(router_obj) as api:
            interfaces = api.get_resource('/interface').get()
            
            result = []
            for iface in interfaces:
                result.append({
                    "name": iface.get("name", ""),
                    "comment": iface.get("comment", ""),
                    "type": iface.get("type", ""),
                    "running": iface.get("running") == "true"
                })
            return result
    except Exception as e:
        logger.error(f"Error fetching interfaces for router {router_obj.name}: {e}")
        manager.disconnect(router_obj.id)
        return []


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
            # Check connection alive first with a lightweight call or just proceed
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

            stats = {
                "cpu_load": int(res.get('cpu-load', 0)),
                "ram_usage": round(used_mem_perc, 1),
                "hdd_usage": round(used_hdd_perc, 1),
                "uptime": res.get('uptime', 'N/A'),
                "version": res.get('version', 'N/A'),
                "board": res.get('board-name', 'N/A'),
                "architecture": res.get('architecture-name', 'N/A'),
                "online": True
            }
            
            # Fetch WAN interface stats if configured
            if router_obj.wan_interface:
                try:
                    interface_stats = api.get_resource('/interface').get(name=router_obj.wan_interface)
                    
                    if interface_stats:
                        inf = interface_stats[0]
                        stats["wan"] = {
                            "name": inf.get("name", ""),
                            "comment": inf.get("comment", ""),
                            "tx_bytes": format_bytes(inf.get("tx-byte", 0)),
                            "rx_bytes": format_bytes(inf.get("rx-byte", 0)),
                            "running": inf.get("running") == "true"
                        }
                except Exception as wan_error:
                    logger.warning(f"Error fetching WAN stats for {router_obj.name}: {wan_error}")
            
            return stats

    except Exception as e:
        logger.error(f"Error fetching stats for router {router_obj.name}: {e}")
        # Force disconnect to allow reconnection on next attempt
        manager.disconnect(router_obj.id)
        return {"online": False, "error": str(e)}

