from __future__ import annotations
import json
import secrets
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.id_gen import generate_prefixed_id
from app.core.security import generate_idempotency_key
from app.models.payment_intent import PaymentIntent
from app.services import ledger_service, webhook_service


async def create_payment_intent(
    db: AsyncSession,
    merchant_id: str,
    amount: str,
    currency: str = "USDC",
    customer_id: str | None = None,
    metadata: dict | None = None,
    idempotency_key: str | None = None,
) -> PaymentIntent:
    idem_key = idempotency_key or generate_idempotency_key()

    existing = await db.execute(
        select(PaymentIntent).where(PaymentIntent.idempotency_key == idem_key)
    )
    if found := existing.scalar_one_or_none():
        return found

    pi = PaymentIntent(
        id=generate_prefixed_id("pi"),
        merchant_id=merchant_id,
        customer_id=customer_id,
        amount=Decimal(amount),
        currency=currency,
        status="requires_payment_method",
        client_secret=f"pi_secret_{secrets.token_hex(16)}",
        metadata_json=json.dumps(metadata) if metadata else None,
        idempotency_key=idem_key,
    )
    db.add(pi)
    await db.flush()

    await webhook_service.emit_event(
        db,
        "payment_intent.created",
        {"id": pi.id, "amount": amount, "currency": currency, "status": pi.status},
    )

    return pi


async def confirm_payment_intent(
    db: AsyncSession, payment_intent_id: str, customer_id: str
) -> PaymentIntent:
    result = await db.execute(
        select(PaymentIntent).where(PaymentIntent.id == payment_intent_id)
    )
    pi = result.scalar_one_or_none()
    if not pi:
        raise ValueError(f"PaymentIntent {payment_intent_id} not found")
    if pi.status not in ("requires_payment_method",):
        raise ValueError(f"PaymentIntent is in invalid state: {pi.status}")

    amount = Decimal(str(pi.amount))

    # Check customer balance
    customer_usdc = await ledger_service.get_or_create_account(
        db, customer_id, "customer_usdc_available", "USDC"
    )
    balance = await ledger_service.get_balance(db, customer_usdc.id)
    if balance < amount:
        raise ValueError(
            f"Insufficient balance: available={balance}, requested={amount}"
        )

    # Calculate platform fee
    fee_bps = Decimal(str(settings.PLATFORM_FEE_BPS))
    fee = (amount * fee_bps / Decimal("10000")).quantize(Decimal("0.000001"))
    merchant_amount = amount - fee

    # Get merchant and platform fee accounts
    merchant_usdc = await ledger_service.get_or_create_account(
        db, pi.merchant_id, "merchant_usdc", "USDC"
    )
    platform_fee_acct = await ledger_service.get_system_account(
        db, "platform_fee", "USDC"
    )

    pi.status = "processing"
    pi.customer_id = customer_id
    await db.flush()

    await webhook_service.emit_event(
        db,
        "payment_intent.processing",
        {"id": pi.id, "status": "processing"},
    )

    # Post journal: debit customer, credit merchant + platform fee
    entries = [
        {"account_id": customer_usdc.id, "direction": "debit", "amount": amount, "currency": "USDC"},
        {"account_id": merchant_usdc.id, "direction": "credit", "amount": merchant_amount, "currency": "USDC"},
    ]
    if fee > 0:
        entries.append(
            {"account_id": platform_fee_acct.id, "direction": "credit", "amount": fee, "currency": "USDC"}
        )

    await ledger_service.post_journal(
        db,
        reference_type="payment_intent",
        reference_id=pi.id,
        idempotency_key=f"pi_confirm_{pi.id}",
        description=f"Payment: {amount} USDC (fee: {fee})",
        entries=entries,
    )

    pi.status = "succeeded"
    pi.confirmed_at = datetime.now(timezone.utc)
    await db.flush()

    await webhook_service.emit_event(
        db,
        "payment_intent.succeeded",
        {
            "id": pi.id,
            "amount": str(amount),
            "fee": str(fee),
            "currency": pi.currency,
            "status": "succeeded",
        },
    )

    return pi


async def get_payment_intent(
    db: AsyncSession, payment_intent_id: str
) -> PaymentIntent | None:
    result = await db.execute(
        select(PaymentIntent).where(PaymentIntent.id == payment_intent_id)
    )
    return result.scalar_one_or_none()
