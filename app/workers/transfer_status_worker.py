from __future__ import annotations
import asyncio
import logging

from app.core.database import async_session
from app.services import transfer_service

logger = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS = 15


async def poll_pending_transfers():
    """Background task that simulates checking on-chain tx status.

    In production, this would query a node/indexer for tx receipts.
    For the demo, submitted transfers are auto-confirmed after one poll cycle.
    """
    while True:
        try:
            async with async_session() as db:
                transfers = await transfer_service.get_pending_transfers(db)
                for t in transfers:
                    if t.status == "submitted":
                        logger.info(f"Auto-confirming transfer {t.id} (tx: {t.tx_hash})")
                        await transfer_service.confirm_transfer(db, t.id)
                await db.commit()
        except Exception:
            logger.exception("Error in transfer status worker")
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
