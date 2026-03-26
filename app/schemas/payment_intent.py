from __future__ import annotations
from typing import Optional
from datetime import datetime

from pydantic import BaseModel


class PaymentIntentCreate(BaseModel):
    merchant_id: str
    customer_id: Optional[str] = None
    amount: str
    currency: str = "USDC"
    metadata: Optional[dict] = None
    idempotency_key: Optional[str] = None


class PaymentIntentConfirm(BaseModel):
    customer_id: str


class PaymentIntentResponse(BaseModel):
    id: str
    merchant_id: str
    customer_id: Optional[str] = None
    amount: float
    currency: str
    status: str
    client_secret: str
    created_at: datetime
    confirmed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
