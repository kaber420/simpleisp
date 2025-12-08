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
