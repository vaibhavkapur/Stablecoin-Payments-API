from __future__ import annotations
import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.id_gen import generate_prefixed_id
from app.models.webhook_event import WebhookEvent


async def emit_event(
    db: AsyncSession, event_type: str, data: dict
) -> WebhookEvent:
    payload = json.dumps(
        {
            "type": event_type,
            "created": datetime.now(timezone.utc).isoformat(),
            "data": {"object": data},
        }
    )
    event = WebhookEvent(
        id=generate_prefixed_id("evt"),
        event_type=event_type,
        payload=payload,
        delivery_status="pending",
    )
    db.add(event)
    await db.flush()
    return event


async def mark_delivered(db: AsyncSession, event_id: str) -> WebhookEvent:
    result = await db.execute(
        select(WebhookEvent).where(WebhookEvent.id == event_id)
    )
    event = result.scalar_one_or_none()
    if not event:
        raise ValueError(f"WebhookEvent {event_id} not found")
    event.delivery_status = "delivered"
    event.last_attempt_at = datetime.now(timezone.utc)
    await db.flush()
    return event


async def mark_failed(db: AsyncSession, event_id: str) -> WebhookEvent:
    result = await db.execute(
        select(WebhookEvent).where(WebhookEvent.id == event_id)
    )
    event = result.scalar_one_or_none()
    if not event:
        raise ValueError(f"WebhookEvent {event_id} not found")
    event.delivery_status = "failed"
    event.retry_count += 1
    event.last_attempt_at = datetime.now(timezone.utc)
    await db.flush()
    return event


async def get_pending_events(db: AsyncSession) -> list[WebhookEvent]:
    result = await db.execute(
        select(WebhookEvent)
        .where(WebhookEvent.delivery_status.in_(["pending", "failed"]))
        .where(WebhookEvent.retry_count < 5)
    )
    return list(result.scalars().all())


async def list_events(
    db: AsyncSession, limit: int = 50
) -> list[WebhookEvent]:
    result = await db.execute(
        select(WebhookEvent).order_by(WebhookEvent.created_at.desc()).limit(limit)
    )
    return list(result.scalars().all())
