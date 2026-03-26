from __future__ import annotations
from typing import Optional
from datetime import datetime

from pydantic import BaseModel


class TransferCreate(BaseModel):
    wallet_id: str
    recipient_address: str
    amount_usdc: str
    idempotency_key: Optional[str] = None


class TransferResponse(BaseModel):
    id: str
    sender_wallet_id: str
    recipient_address: str
    amount_usdc: float
    status: str
    chain: str
    tx_hash: Optional[str] = None
    failure_reason: Optional[str] = None
    created_at: datetime
    submitted_at: Optional[datetime] = None
    confirmed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
