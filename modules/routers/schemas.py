from typing import Optional
from pydantic import BaseModel

class RouterBase(BaseModel):
    name: str
    ip_address: str
    username: str
    port: int = 8728
    is_active: bool = True
    wan_interface: Optional[str] = None
    use_ssl: bool = False

class RouterCreate(RouterBase):
    password: str

class RouterUpdate(BaseModel):
    name: Optional[str] = None
    ip_address: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    port: Optional[int] = None
    is_active: Optional[bool] = None
    wan_interface: Optional[str] = None
    use_ssl: Optional[bool] = None

class RouterRead(RouterBase):
    id: int

    class Config:
        from_attributes = True
