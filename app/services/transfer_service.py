from __future__ import annotations
import secrets
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.id_gen import generate_prefixed_id
from app.core.security import generate_idempotency_key
from app.models.transfer import Transfer
from app.services import ledger_service, webhook_service


async def create_transfer(
    db: AsyncSession,
    wallet_id: str,
    recipient_address: str,
    amount_usdc: str,
    idempotency_key: str | None = None,
) -> Transfer:
    from app.services.wallet_service import get_wallet

    idem_key = idempotency_key or generate_idempotency_key()

    # Check idempotency
    existing = await db.execute(
        select(Transfer).where(Transfer.idempotency_key == idem_key)
    )
    if found := existing.scalar_one_or_none():
        return found

    wallet = await get_wallet(db, wallet_id)
    if not wallet:
        raise ValueError(f"Wallet {wallet_id} not found")

    amount = Decimal(amount_usdc)

    # Check available balance
    customer_usdc = await ledger_service.get_or_create_account(
        db, wallet.customer_id, "customer_usdc_available", "USDC"
    )
    balance = await ledger_service.get_balance(db, customer_usdc.id)
    if balance < amount:
        raise ValueError(
            f"Insufficient balance: available={balance}, requested={amount}"
        )

    # Reserve funds
    customer_reserved = await ledger_service.get_or_create_account(
        db, wallet.customer_id, "customer_usdc_reserved", "USDC"
    )

    transfer = Transfer(
        id=generate_prefixed_id("tr"),
        sender_wallet_id=wallet_id,
        recipient_address=recipient_address,
        amount_usdc=amount,
        status="created",
        chain=wallet.chain,
        idempotency_key=idem_key,
    )
    db.add(transfer)
    await db.flush()

    # Reserve: debit available, credit reserved
    await ledger_service.post_journal(
        db,
        reference_type="transfer",
        reference_id=transfer.id,
        idempotency_key=f"tr_reserve_{transfer.id}",
        description=f"Reserve {amount} USDC for transfer",
        entries=[
            {"account_id": customer_usdc.id, "direction": "debit", "amount": amount, "currency": "USDC"},
            {"account_id": customer_reserved.id, "direction": "credit", "amount": amount, "currency": "USDC"},
        ],
    )

    # Simulate chain submission
    transfer.tx_hash = "0x" + secrets.token_hex(32)
    transfer.status = "submitted"
    transfer.submitted_at = datetime.now(timezone.utc)
    await db.flush()

    await webhook_service.emit_event(
        db,
        "transfer.submitted",
        {
            "id": transfer.id,
            "amount_usdc": amount_usdc,
            "tx_hash": transfer.tx_hash,
            "status": "submitted",
        },
    )

    return transfer


async def confirm_transfer(db: AsyncSession, transfer_id: str) -> Transfer:
    """Called by the background worker when a tx is confirmed on-chain."""
    result = await db.execute(
        select(Transfer).where(Transfer.id == transfer_id)
    )
    transfer = result.scalar_one_or_none()
    if not transfer:
        raise ValueError(f"Transfer {transfer_id} not found")

    from app.services.wallet_service import get_wallet

    wallet = await get_wallet(db, transfer.sender_wallet_id)
    amount = Decimal(str(transfer.amount_usdc))

    # Consume reserved funds
    customer_reserved = await ledger_service.get_or_create_account(
        db, wallet.customer_id, "customer_usdc_reserved", "USDC"
    )
    treasury = await ledger_service.get_system_account(db, "treasury_usdc", "USDC")

    await ledger_service.post_journal(
        db,
        reference_type="transfer",
        reference_id=transfer.id,
        idempotency_key=f"tr_confirm_{transfer.id}",
        description=f"Transfer confirmed: {amount} USDC",
        entries=[
            {"account_id": customer_reserved.id, "direction": "debit", "amount": amount, "currency": "USDC"},
            {"account_id": treasury.id, "direction": "credit", "amount": amount, "currency": "USDC"},
        ],
    )

    transfer.status = "confirmed"
    transfer.confirmed_at = datetime.now(timezone.utc)
    transfer.confirmations = 1
    await db.flush()

    await webhook_service.emit_event(
        db,
        "transfer.confirmed",
        {"id": transfer.id, "tx_hash": transfer.tx_hash, "status": "confirmed"},
    )

    return transfer


async def fail_transfer(
    db: AsyncSession, transfer_id: str, reason: str
) -> Transfer:
    """Mark transfer as failed and release reserved funds."""
    result = await db.execute(
        select(Transfer).where(Transfer.id == transfer_id)
    )
    transfer = result.scalar_one_or_none()
    if not transfer:
        raise ValueError(f"Transfer {transfer_id} not found")

    from app.services.wallet_service import get_wallet

    wallet = await get_wallet(db, transfer.sender_wallet_id)
    amount = Decimal(str(transfer.amount_usdc))

    # Release reserved funds back to available
    customer_usdc = await ledger_service.get_or_create_account(
        db, wallet.customer_id, "customer_usdc_available", "USDC"
    )
    customer_reserved = await ledger_service.get_or_create_account(
        db, wallet.customer_id, "customer_usdc_reserved", "USDC"
    )

    await ledger_service.post_journal(
        db,
        reference_type="transfer",
        reference_id=transfer.id,
        idempotency_key=f"tr_fail_{transfer.id}",
        description=f"Transfer failed, releasing {amount} USDC",
        entries=[
            {"account_id": customer_reserved.id, "direction": "debit", "amount": amount, "currency": "USDC"},
            {"account_id": customer_usdc.id, "direction": "credit", "amount": amount, "currency": "USDC"},
        ],
    )

    transfer.status = "failed"
    transfer.failure_reason = reason
    await db.flush()

    await webhook_service.emit_event(
        db,
        "transfer.failed",
        {"id": transfer.id, "reason": reason, "status": "failed"},
    )

    return transfer


async def get_transfer(db: AsyncSession, transfer_id: str) -> Transfer | None:
    result = await db.execute(
        select(Transfer).where(Transfer.id == transfer_id)
    )
    return result.scalar_one_or_none()


async def get_pending_transfers(db: AsyncSession) -> list[Transfer]:
    result = await db.execute(
        select(Transfer).where(
            Transfer.status.in_(["created", "submitted", "pending_confirmation"])
        )
    )
    return list(result.scalars().all())
