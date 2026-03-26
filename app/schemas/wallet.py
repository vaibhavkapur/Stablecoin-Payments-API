from __future__ import annotations
from datetime import datetime

from pydantic import BaseModel


class WalletCreate(BaseModel):
    customer_id: str
    chain: str = "base-sepolia"


class WalletResponse(BaseModel):
    id: str
    customer_id: str
    address: str
    chain: str
    provider: str
    created_at: datetime

    model_config = {"from_attributes": True}
