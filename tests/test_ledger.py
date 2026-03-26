from __future__ import annotations

from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.services import ledger_service


@pytest.mark.asyncio
async def test_create_account(db_session: AsyncSession):
    acct = await ledger_service.create_account(db_session, "cus_test", "customer_usdc_available", "USDC")
    await db_session.flush()
    assert acct.id.startswith("acct_")
    assert acct.customer_id == "cus_test"
    assert acct.type == "customer_usdc_available"


@pytest.mark.asyncio
async def test_get_or_create_account_idempotent(db_session: AsyncSession):
    a1 = await ledger_service.get_or_create_account(db_session, "cus_x", "customer_usdc_available", "USDC")
    await db_session.flush()
    a2 = await ledger_service.get_or_create_account(db_session, "cus_x", "customer_usdc_available", "USDC")
    assert a1.id == a2.id


@pytest.mark.asyncio
async def test_post_journal_balanced(db_session: AsyncSession):
    a1 = await ledger_service.create_account(db_session, None, "bank_clearing_usd", "USD")
    a2 = await ledger_service.create_account(db_session, "cus_j", "customer_usd", "USD")
    await db_session.flush()

    journal = await ledger_service.post_journal(
        db_session,
        reference_type="deposit",
        reference_id="dep_test",
        idempotency_key="test_key_1",
        description="Test deposit",
        entries=[
            {"account_id": a1.id, "direction": "debit", "amount": Decimal("100"), "currency": "USD"},
            {"account_id": a2.id, "direction": "credit", "amount": Decimal("100"), "currency": "USD"},
        ],
    )
    assert journal.id.startswith("jrn_")


@pytest.mark.asyncio
async def test_post_journal_unbalanced_raises(db_session: AsyncSession):
    a1 = await ledger_service.create_account(db_session, None, "test_debit", "USD")
    a2 = await ledger_service.create_account(db_session, None, "test_credit", "USD")
    await db_session.flush()

    with pytest.raises(ValueError, match="does not balance"):
        await ledger_service.post_journal(
            db_session,
            reference_type="test",
            reference_id="t1",
            idempotency_key="unbalanced_1",
            description="Bad journal",
            entries=[
                {"account_id": a1.id, "direction": "debit", "amount": Decimal("50"), "currency": "USD"},
                {"account_id": a2.id, "direction": "credit", "amount": Decimal("30"), "currency": "USD"},
            ],
        )


@pytest.mark.asyncio
async def test_post_journal_idempotent(db_session: AsyncSession):
    a1 = await ledger_service.create_account(db_session, None, "idem_d", "USD")
    a2 = await ledger_service.create_account(db_session, None, "idem_c", "USD")
    await db_session.flush()

    entries = [
        {"account_id": a1.id, "direction": "debit", "amount": Decimal("10"), "currency": "USD"},
        {"account_id": a2.id, "direction": "credit", "amount": Decimal("10"), "currency": "USD"},
    ]
    j1 = await ledger_service.post_journal(
        db_session, "test", "t2", "idem_key_dup", "First", entries
    )
    j2 = await ledger_service.post_journal(
        db_session, "test", "t2", "idem_key_dup", "Second", entries
    )
    assert j1.id == j2.id


@pytest.mark.asyncio
async def test_balance_computation(db_session: AsyncSession):
    acct = await ledger_service.create_account(db_session, "cus_bal", "customer_usdc_available", "USDC")
    other = await ledger_service.create_account(db_session, None, "source", "USDC")
    await db_session.flush()

    # Credit 100
    await ledger_service.post_journal(
        db_session, "test", "t3", "bal_credit", "Credit",
        [
            {"account_id": other.id, "direction": "debit", "amount": Decimal("100"), "currency": "USDC"},
            {"account_id": acct.id, "direction": "credit", "amount": Decimal("100"), "currency": "USDC"},
        ],
    )
    # Debit 30
    await ledger_service.post_journal(
        db_session, "test", "t4", "bal_debit", "Debit",
        [
            {"account_id": acct.id, "direction": "debit", "amount": Decimal("30"), "currency": "USDC"},
            {"account_id": other.id, "direction": "credit", "amount": Decimal("30"), "currency": "USDC"},
        ],
    )

    balance = await ledger_service.get_balance(db_session, acct.id)
    assert balance == Decimal("70")
