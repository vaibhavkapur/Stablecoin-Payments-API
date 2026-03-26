from __future__ import annotations
import asyncio
import logging

from app.core.database import async_session
from app.services import reconciliation_service

logger = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS = 300  # every 5 minutes


async def run_reconciliation():
    """Periodically check all account balances for mismatches."""
    while True:
        try:
            async with async_session() as db:
                issues = await reconciliation_service.check_all_balances(db)
                if issues:
                    logger.warning(f"Reconciliation found {len(issues)} issue(s):")
                    for issue in issues:
                        logger.warning(f"  {issue}")
                else:
                    logger.info("Reconciliation check passed — no issues")
        except Exception:
            logger.exception("Error in reconciliation worker")
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
