from typing import Optional, TYPE_CHECKING
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship

if TYPE_CHECKING:
    from modules.routers.models import Router

class Client(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    ip_address: str = Field(unique=True, index=True)
    limit_max_upload: str = "5M"
    limit_max_download: str = "10M"
    billing_day: int = 1
    status: str = "active"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    router_id: Optional[int] = Field(default=None, foreign_key="router.id")
    router: Optional["Router"] = Relationship(back_populates="clients")
