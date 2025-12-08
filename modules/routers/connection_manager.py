import routeros_api
import threading
from typing import Dict, Tuple
from contextlib import contextmanager
from modules.routers.models import Router

class RouterConnectionManager:
    _instance = None
    _init_lock = threading.Lock()
    # Store tuple (connection_pool, api_instance, per_router_lock)
    _connections: Dict[int, Tuple[routeros_api.RouterOsApiPool, routeros_api.api.RouterOsApi, threading.RLock]] = {} 

    def __new__(cls):
        if cls._instance is None:
            with cls._init_lock:
                if cls._instance is None:
                    cls._instance = super(RouterConnectionManager, cls).__new__(cls)
        return cls._instance

    def get_connection(self, router_db: Router) -> routeros_api.api.RouterOsApi:
        """Devuelve una conexión existente o crea una nueva si no existe.
        NOTA: Para operaciones thread-safe, use get_locked_connection() en su lugar.
        """
        with self._init_lock:
            if router_db.id in self._connections:
                pool, api, lock = self._connections[router_db.id]
                return api
            
            # Crear nueva conexión persistente
            connection = routeros_api.RouterOsApiPool(
                router_db.ip_address,
                username=router_db.username,
                password=router_db.password,
                port=router_db.port,
                use_ssl=router_db.use_ssl,
                ssl_verify=False,
                plaintext_login=True
            )
            api = connection.get_api()
            lock = threading.RLock()
            self._connections[router_db.id] = (connection, api, lock)
            return api

    @contextmanager
    def get_locked_connection(self, router_db: Router):
        """Context manager que devuelve una conexión API con bloqueo thread-safe.
        
        Uso:
            with manager.get_locked_connection(router) as api:
                api.get_resource('/queue/simple').get()
        """
        # Primero asegurarse de que la conexión existe
        with self._init_lock:
            if router_db.id not in self._connections:
                connection = routeros_api.RouterOsApiPool(
                    router_db.ip_address,
                    username=router_db.username,
                    password=router_db.password,
                    port=router_db.port,
                    use_ssl=router_db.use_ssl,
                    ssl_verify=False,
                    plaintext_login=True
                )
                api = connection.get_api()
                lock = threading.RLock()
                self._connections[router_db.id] = (connection, api, lock)
        
        pool, api, lock = self._connections[router_db.id]
        
        # Adquirir el lock específico del router
        lock.acquire()
        try:
            yield api
        finally:
            lock.release()

    def disconnect(self, router_id: int):
        """Cierra y elimina la conexión de un router específico."""
        with self._init_lock:
            if router_id in self._connections:
                try:
                    pool, _, lock = self._connections[router_id]
                    # Intentar adquirir el lock antes de desconectar
                    with lock:
                        pool.disconnect()
                except Exception:
                    pass
                del self._connections[router_id]

    def disconnect_all(self):
        with self._init_lock:
            for pool, _, lock in self._connections.values():
                try:
                    with lock:
                        pool.disconnect()
                except:
                    pass
            self._connections.clear()

# Instancia global
manager = RouterConnectionManager()
