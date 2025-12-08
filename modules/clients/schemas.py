from typing import Optional
from pydantic import BaseModel
from datetime import datetime

class ClientWithStats(BaseModel):
    """Client model with queue statistics from MikroTik."""
    id: int
    name: str
    ip_address: str
    limit_max_upload: str
    limit_max_download: str
    billing_day: int
    status: str
    created_at: datetime
    router_id: Optional[int] = None
    # Additional stats
    router_name: Optional[str] = None
    total_upload: str = "0 B"
    total_download: str = "0 B"
    current_upload_speed: str = "0 bps"
    current_download_speed: str = "0 bps"

    class Config:
        from_attributes = True
