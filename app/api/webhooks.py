from __future__ import annotations
import json

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import require_api_key, sign_webhook_payload
from app.schemas.webhook import WebhookEventResponse, WebhookTestRequest
from app.services import webhook_service

router = APIRouter(prefix="/v1/webhooks", tags=["webhooks"])


@router.post("/test", status_code=200)
async def test_webhook(
    body: WebhookTestRequest,
    db: AsyncSession = Depends(get_db),
    _api_key: str = Depends(require_api_key),
):
    """Send a test webhook to the given URL."""
    event = await webhook_service.emit_event(
        db, body.event_type, {"message": "This is a test webhook"}
    )
    await db.commit()
    await db.refresh(event)

    payload = event.payload.encode()
    signature = sign_webhook_payload(payload)

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                body.url,
                content=payload,
                headers={
                    "Content-Type": "application/json",
                    "X-Webhook-Signature": signature,
                },
            )
        if resp.status_code < 300:
            await webhook_service.mark_delivered(db, event.id)
        else:
            await webhook_service.mark_failed(db, event.id)
        await db.commit()
        return {
            "event_id": event.id,
            "status_code": resp.status_code,
            "delivery_status": event.delivery_status,
        }
    except httpx.RequestError as e:
        await webhook_service.mark_failed(db, event.id)
        await db.commit()
        return {
            "event_id": event.id,
            "error": str(e),
            "delivery_status": "failed",
        }


@router.get("/events", response_model=list[WebhookEventResponse])
async def list_webhook_events(
    db: AsyncSession = Depends(get_db),
    _api_key: str = Depends(require_api_key),
):
    return await webhook_service.list_events(db)


@router.get("/events/{event_id}", response_model=WebhookEventResponse)
async def get_webhook_event(
    event_id: str,
    db: AsyncSession = Depends(get_db),
    _api_key: str = Depends(require_api_key),
):
    from sqlalchemy import select
    from app.models.webhook_event import WebhookEvent

    result = await db.execute(
        select(WebhookEvent).where(WebhookEvent.id == event_id)
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Webhook event not found")
    return event
