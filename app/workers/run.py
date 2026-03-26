from __future__ import annotations
"""Entry point for running background workers standalone."""

import asyncio
import logging

from app.workers.transfer_status_worker import poll_pending_transfers
from app.workers.webhook_retry_worker import retry_pending_webhooks
from app.workers.reconciliation_worker import run_reconciliation

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    logger.info("Starting background workers...")
    await asyncio.gather(
        poll_pending_transfers(),
        retry_pending_webhooks(),
        run_reconciliation(),
    )


if __name__ == "__main__":
    asyncio.run(main())
