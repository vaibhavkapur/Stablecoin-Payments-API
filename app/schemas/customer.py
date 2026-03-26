from __future__ import annotations
from typing import Optional
from datetime import datetime

from pydantic import BaseModel, EmailStr


class CustomerCreate(BaseModel):
    email: EmailStr
    external_ref: Optional[str] = None


class CustomerResponse(BaseModel):
    id: str
    email: str
    external_ref: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}
