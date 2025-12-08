from typing import Optional, List, TYPE_CHECKING
from sqlmodel import Field, SQLModel, Relationship

if TYPE_CHECKING:
    from modules.clients.models import Client

class Router(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    ip_address: str
    username: str
    password: str
    port: int = 8728
    is_active: bool = Field(default=True)
    wan_interface: Optional[str] = Field(default=None)

    clients: List["Client"] = Relationship(back_populates="router")
