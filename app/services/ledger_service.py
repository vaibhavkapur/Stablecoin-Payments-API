from __future__ import annotations
from decimal import Decimal

from sqlalchemy import select, case, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.id_gen import generate_prefixed_id
from app.models.account import PaymentAccount
from app.models.journal import Journal, LedgerEntry


async def create_account(
    db: AsyncSession,
    customer_id: str | None,
    account_type: str,
    currency: str = "USDC",
) -> PaymentAccount:
    account = PaymentAccount(
        id=generate_prefixed_id("acct"),
        customer_id=customer_id,
        type=account_type,
        currency=currency,
    )
    db.add(account)
    await db.flush()
    return account


async def get_or_create_account(
    db: AsyncSession,
    customer_id: str | None,
    account_type: str,
    currency: str = "USDC",
) -> PaymentAccount:
    stmt = select(PaymentAccount).where(
        PaymentAccount.customer_id == customer_id,
        PaymentAccount.type == account_type,
        PaymentAccount.currency == currency,
    )
    result = await db.execute(stmt)
    account = result.scalar_one_or_none()
    if account:
        return account
    return await create_account(db, customer_id, account_type, currency)


async def get_system_account(
    db: AsyncSession, account_type: str, currency: str = "USDC"
) -> PaymentAccount:
    """Get or create a system-level account (no customer)."""
    return await get_or_create_account(db, None, account_type, currency)


async def get_balance(db: AsyncSession, account_id: str) -> Decimal:
    """Compute balance from ledger entries: sum(credits) - sum(debits)."""
    stmt = select(
        func.coalesce(
            func.sum(
                case(
                    (LedgerEntry.direction == "credit", LedgerEntry.amount),
                    else_=0,
                )
            )
            - func.sum(
                case(
                    (LedgerEntry.direction == "debit", LedgerEntry.amount),
                    else_=0,
                )
            ),
            0,
        )
    ).where(LedgerEntry.account_id == account_id)
    result = await db.execute(stmt)
    return Decimal(str(result.scalar()))


async def get_customer_balances(
    db: AsyncSession, customer_id: str
) -> list[dict]:
    stmt = select(PaymentAccount).where(
        PaymentAccount.customer_id == customer_id
    )
    result = await db.execute(stmt)
    accounts = result.scalars().all()

    balances = []
    for acct in accounts:
        bal = await get_balance(db, acct.id)
        balances.append(
            {
                "account_type": acct.type,
                "currency": acct.currency,
                "balance": float(bal),
            }
        )
    return balances


async def post_journal(
    db: AsyncSession,
    reference_type: str,
    reference_id: str,
    idempotency_key: str,
    description: str,
    entries: list[dict],
) -> Journal:
    """Post a balanced journal with entries.

    Each entry dict: {"account_id": str, "direction": "debit"|"credit", "amount": Decimal, "currency": str}

    Raises ValueError if the journal doesn't balance.
    """
    # Check idempotency
    existing = await db.execute(
        select(Journal).where(Journal.idempotency_key == idempotency_key)
    )
    if found := existing.scalar_one_or_none():
        return found

    # Validate balance
    total_debits = sum(
        Decimal(str(e["amount"])) for e in entries if e["direction"] == "debit"
    )
    total_credits = sum(
        Decimal(str(e["amount"])) for e in entries if e["direction"] == "credit"
    )
    if total_debits != total_credits:
        raise ValueError(
            f"Journal does not balance: debits={total_debits} credits={total_credits}"
        )

    journal = Journal(
        id=generate_prefixed_id("jrn"),
        reference_type=reference_type,
        reference_id=reference_id,
        description=description,
        idempotency_key=idempotency_key,
    )
    db.add(journal)
    await db.flush()

    for entry in entries:
        ledger_entry = LedgerEntry(
            id=generate_prefixed_id("le"),
            journal_id=journal.id,
            account_id=entry["account_id"],
            direction=entry["direction"],
            amount=entry["amount"],
            currency=entry.get("currency", "USDC"),
        )
        db.add(ledger_entry)

    await db.flush()
    return journal
