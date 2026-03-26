from __future__ import annotations
from typing import Optional
from datetime import datetime

from pydantic import BaseModel


class DepositCreate(BaseModel):
    customer_id: str
    amount_usd: str
    idempotency_key: Optional[str] = None


class DepositResponse(BaseModel):
    id: str
    customer_id: str
    amount_usd: float
    status: str
    reference: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
