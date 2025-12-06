import routeros_api
import threading
from typing import Dict, Tuple
from modules.routers.models import Router

class RouterConnectionManager:
    _instance = None
    _lock = threading.Lock()
    # Store tuple (connection_pool, api_instance)
    _connections: Dict[int, Tuple[routeros_api.RouterOsApiPool, routeros_api.api.RouterOsApi]] = {} 

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RouterConnectionManager, cls).__new__(cls)
        return cls._instance

    def get_connection(self, router_db: Router) -> routeros_api.api.RouterOsApi:
        """Devuelve una conexión existente o crea una nueva si se cayó"""
        with self._lock:
            if router_db.id in self._connections:
                # Could add logic to verify connection here
                pool, api = self._connections[router_db.id]
                return api
            
            # Crear nueva conexión persistente
            connection = routeros_api.RouterOsApiPool(
                router_db.ip_address,
                username=router_db.username,
                password=router_db.password,
                port=router_db.port,
                plaintext_login=True
            )
            api = connection.get_api()
            self._connections[router_db.id] = (connection, api)
            return api

    def disconnect(self, router_id: int):
        """Cierra y elimina la conexión de un router específico."""
        with self._lock:
            if router_id in self._connections:
                try:
                    pool, _ = self._connections[router_id]
                    pool.disconnect()
                except Exception:
                    pass
                del self._connections[router_id]

    def disconnect_all(self):
        with self._lock:
            for pool, _ in self._connections.values():
                try:
                    pool.disconnect()
                except:
                    pass
            self._connections.clear()

# Instancia global
manager = RouterConnectionManager()
