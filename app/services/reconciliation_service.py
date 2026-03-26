from __future__ import annotations
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import PaymentAccount
from app.services import ledger_service


async def check_all_balances(db: AsyncSession) -> list[dict]:
    """Verify all account balances are non-negative where expected.

    Returns a list of mismatches/warnings.
    """
    result = await db.execute(select(PaymentAccount))
    accounts = result.scalars().all()

    issues = []
    for acct in accounts:
        balance = await ledger_service.get_balance(db, acct.id)
        # Customer available and reserved should never go negative
        if acct.type in ("customer_usdc_available", "customer_usdc_reserved") and balance < 0:
            issues.append(
                {
                    "account_id": acct.id,
                    "account_type": acct.type,
                    "customer_id": acct.customer_id,
                    "balance": float(balance),
                    "issue": "negative_balance",
                }
            )

    return issues


async def get_ledger_summary(db: AsyncSession) -> list[dict]:
    """Get balance summary for all accounts."""
    result = await db.execute(select(PaymentAccount))
    accounts = result.scalars().all()

    summary = []
    for acct in accounts:
        balance = await ledger_service.get_balance(db, acct.id)
        summary.append(
            {
                "account_id": acct.id,
                "account_type": acct.type,
                "customer_id": acct.customer_id,
                "currency": acct.currency,
                "balance": float(balance),
            }
        )
    return summary
