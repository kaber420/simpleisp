from typing import Optional
from datetime import datetime
from sqlmodel import Field, SQLModel

class Payment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    client_id: int = Field(foreign_key="client.id")
    amount: float
    month_paid: str
    date_paid: datetime = Field(default_factory=datetime.utcnow)
