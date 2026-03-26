from __future__ import annotations
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.id_gen import generate_prefixed_id
from app.core.security import generate_idempotency_key
from app.models.deposit import Deposit
from app.services import ledger_service, webhook_service


async def create_deposit(
    db: AsyncSession,
    customer_id: str,
    amount_usd: str,
    idempotency_key: str | None = None,
) -> Deposit:
    idem_key = idempotency_key or generate_idempotency_key()

    # Check idempotency
    existing = await db.execute(
        select(Deposit).where(Deposit.idempotency_key == idem_key)
    )
    if found := existing.scalar_one_or_none():
        return found

    deposit = Deposit(
        id=generate_prefixed_id("dep"),
        customer_id=customer_id,
        amount_usd=Decimal(amount_usd),
        status="pending",
        idempotency_key=idem_key,
    )
    db.add(deposit)
    await db.flush()

    await webhook_service.emit_event(
        db, "deposit.pending", {"id": deposit.id, "amount_usd": amount_usd, "status": "pending"}
    )

    return deposit


async def confirm_deposit(db: AsyncSession, deposit_id: str) -> Deposit:
    result = await db.execute(
        select(Deposit).where(Deposit.id == deposit_id)
    )
    deposit = result.scalar_one_or_none()
    if not deposit:
        raise ValueError(f"Deposit {deposit_id} not found")
    if deposit.status != "pending":
        raise ValueError(f"Deposit {deposit_id} is not pending (status={deposit.status})")

    amount = Decimal(str(deposit.amount_usd))

    # Journal A: fiat deposit received
    bank_clearing = await ledger_service.get_system_account(db, "bank_clearing_usd", "USD")
    customer_usd = await ledger_service.get_or_create_account(
        db, deposit.customer_id, "customer_usd", "USD"
    )
    await ledger_service.post_journal(
        db,
        reference_type="deposit",
        reference_id=deposit.id,
        idempotency_key=f"dep_fiat_{deposit.id}",
        description=f"Fiat deposit received: ${amount}",
        entries=[
            {"account_id": bank_clearing.id, "direction": "debit", "amount": amount, "currency": "USD"},
            {"account_id": customer_usd.id, "direction": "credit", "amount": amount, "currency": "USD"},
        ],
    )

    # Journal B: USD → USDC conversion (1:1)
    customer_usdc = await ledger_service.get_or_create_account(
        db, deposit.customer_id, "customer_usdc_available", "USDC"
    )
    await ledger_service.post_journal(
        db,
        reference_type="deposit",
        reference_id=deposit.id,
        idempotency_key=f"dep_conv_{deposit.id}",
        description=f"USD to USDC conversion: {amount}",
        entries=[
            {"account_id": customer_usd.id, "direction": "debit", "amount": amount, "currency": "USD"},
            {"account_id": customer_usdc.id, "direction": "credit", "amount": amount, "currency": "USDC"},
        ],
    )

    deposit.status = "completed"
    deposit.completed_at = datetime.now(timezone.utc)
    await db.flush()

    await webhook_service.emit_event(
        db, "deposit.completed", {"id": deposit.id, "amount_usd": str(amount), "status": "completed"}
    )

    return deposit


async def get_deposit(db: AsyncSession, deposit_id: str) -> Deposit | None:
    result = await db.execute(
        select(Deposit).where(Deposit.id == deposit_id)
    )
    return result.scalar_one_or_none()
