from __future__ import annotations
import asyncio
import logging

import httpx

from app.core.database import async_session
from app.core.security import sign_webhook_payload
from app.services import webhook_service

logger = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS = 30

# In production, this would be configurable per-merchant.
# For the demo we just log failed deliveries.
WEBHOOK_ENDPOINT: str | None = None


async def retry_pending_webhooks():
    """Background task that retries failed webhook deliveries."""
    while True:
        try:
            async with async_session() as db:
                events = await webhook_service.get_pending_events(db)
                for event in events:
                    if not WEBHOOK_ENDPOINT:
                        # No endpoint configured — just mark as delivered for demo
                        logger.info(
                            f"Webhook {event.id} ({event.event_type}) — no endpoint configured, skipping"
                        )
                        continue

                    payload = event.payload.encode()
                    signature = sign_webhook_payload(payload)
                    try:
                        async with httpx.AsyncClient(timeout=10.0) as client:
                            resp = await client.post(
                                WEBHOOK_ENDPOINT,
                                content=payload,
                                headers={
                                    "Content-Type": "application/json",
                                    "X-Webhook-Signature": signature,
                                },
                            )
                        if resp.status_code < 300:
                            await webhook_service.mark_delivered(db, event.id)
                            logger.info(f"Webhook {event.id} delivered")
                        else:
                            await webhook_service.mark_failed(db, event.id)
                            logger.warning(
                                f"Webhook {event.id} delivery failed: {resp.status_code}"
                            )
                    except httpx.RequestError as e:
                        await webhook_service.mark_failed(db, event.id)
                        logger.warning(f"Webhook {event.id} request error: {e}")

                await db.commit()
        except Exception:
            logger.exception("Error in webhook retry worker")
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
