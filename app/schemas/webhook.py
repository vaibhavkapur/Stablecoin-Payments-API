from __future__ import annotations
from typing import Optional
from datetime import datetime

from pydantic import BaseModel


class WebhookEventResponse(BaseModel):
    id: str
    event_type: str
    payload: str
    delivery_status: str
    retry_count: int
    last_attempt_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class WebhookTestRequest(BaseModel):
    url: str
    event_type: str = "test.ping"
