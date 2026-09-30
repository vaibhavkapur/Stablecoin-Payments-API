---
title: Ledger System
layout: default
nav_order: 5
---

# Ledger System

[Documentation home](index.md)

Double-entry bookkeeping that creates a complete audit trail for every balance movement in the system.

---

## Overview

The ledger system is the financial backbone of the Stablecoin Payments API. Every operation that affects a balance — deposits, transfers, payment intents — is recorded as a **journal** containing balanced **ledger entries**. No funds can appear or disappear without a corresponding counter-entry.

This design enables:
- **Full auditability** — trace any balance back to its originating transactions
- **Reconciliation** — automated checks that all accounts balance correctly
- **Idempotency** — journals are deduplicated by idempotency key

## Account Types

Each customer gets dedicated accounts when their first wallet is created. System-level accounts track platform-wide balances.

### Customer Accounts

| Account Type | Currency | Purpose |
|:-------------|:---------|:--------|
| `customer_usdc_available` | USDC | Spendable USDC balance |
| `customer_usdc_reserved` | USDC | Funds locked for pending transfers |
| `customer_usd` | USD | Intermediate USD balance during deposit |

### System Accounts

| Account Type | Currency | Purpose |
|:-------------|:---------|:--------|
| `treasury_usdc` | USDC | USDC received from confirmed transfers |
| `platform_fee` | USDC | Platform fees collected from merchant payments |
| `bank_clearing_usd` | USD | Represents incoming fiat deposits |

## Journal & Entry Schema

### Journal

```python
Journal:
  id: str              # Prefixed "jrn_"
  reference_type: str   # "deposit", "transfer", or "payment_intent"
  reference_id: str     # ID of the originating transaction
  description: str      # Human-readable description
  idempotency_key: str  # Unique key — prevents duplicate journals
  created_at: datetime
```

### Ledger Entry

```python
LedgerEntry:
  id: str              # Prefixed "le_"
  journal_id: str       # Parent journal
  account_id: str       # Target account
  direction: str        # "debit" or "credit"
  amount: Decimal       # Entry amount
  currency: str         # "USDC" or "USD"
```

## Balance Calculation

Account balances are computed from ledger entries in real time:

```
Balance = SUM(credits) - SUM(debits)
```

```python
async def get_balance(db, account_id) -> Decimal:
    stmt = select(
        func.coalesce(
            func.sum(case((LedgerEntry.direction == "credit", LedgerEntry.amount), else_=0))
            - func.sum(case((LedgerEntry.direction == "debit", LedgerEntry.amount), else_=0)),
            0
        )
    ).where(LedgerEntry.account_id == account_id)
    result = await db.execute(stmt)
    return Decimal(str(result.scalar()))
```

## Lifecycle Examples

### Successful Deposit ($500 USD → USDC)

When a deposit is confirmed, two journals are created:

**Journal 1 — Fiat Deposit**

| Account | Direction | Amount | Currency |
|:--------|:----------|:-------|:---------|
| `bank_clearing_usd` | debit | 500.00 | USD |
| `customer_usd` | credit | 500.00 | USD |

**Journal 2 — USD to USDC Conversion**

| Account | Direction | Amount | Currency |
|:--------|:----------|:-------|:---------|
| `customer_usd` | debit | 500.00 | USD |
| `customer_usdc_available` | credit | 500.00 | USDC |

**Result**: Customer has 500.00 USDC available.

### Successful Transfer ($100 USDC)

**Journal 1 — Reserve Funds (on creation)**

| Account | Direction | Amount | Currency |
|:--------|:----------|:-------|:---------|
| `customer_usdc_available` | debit | 100.00 | USDC |
| `customer_usdc_reserved` | credit | 100.00 | USDC |

**Journal 2 — Confirm Transfer (on chain confirmation)**

| Account | Direction | Amount | Currency |
|:--------|:----------|:-------|:---------|
| `customer_usdc_reserved` | debit | 100.00 | USDC |
| `treasury_usdc` | credit | 100.00 | USDC |

**Result**: Customer available balance reduced by 100.00 USDC. Treasury holds the confirmed funds.

### Failed Transfer ($100 USDC)

**Journal 1 — Reserve Funds (on creation)**

| Account | Direction | Amount | Currency |
|:--------|:----------|:-------|:---------|
| `customer_usdc_available` | debit | 100.00 | USDC |
| `customer_usdc_reserved` | credit | 100.00 | USDC |

**Journal 2 — Release Funds (on failure)**

| Account | Direction | Amount | Currency |
|:--------|:----------|:-------|:---------|
| `customer_usdc_reserved` | debit | 100.00 | USDC |
| `customer_usdc_available` | credit | 100.00 | USDC |

**Result**: Funds returned to customer's available balance. No net change.

### Merchant Payment ($50 USDC, 2% Fee)

**Journal 1 — Customer to Merchant (minus fee)**

| Account | Direction | Amount | Currency |
|:--------|:----------|:-------|:---------|
| `customer_usdc_available` | debit | 49.00 | USDC |
| `merchant_usdc` | credit | 49.00 | USDC |

**Journal 2 — Platform Fee**

| Account | Direction | Amount | Currency |
|:--------|:----------|:-------|:---------|
| `customer_usdc_available` | debit | 1.00 | USDC |
| `platform_fee` | credit | 1.00 | USDC |

**Result**: Merchant receives $49.00, platform collects $1.00 fee.

## Idempotency Guarantees

Every journal has a unique `idempotency_key`. Before creating a new journal, the ledger service checks for an existing entry with the same key:

```python
existing = await db.execute(
    select(Journal).where(Journal.idempotency_key == idempotency_key)
)
if found := existing.scalar_one_or_none():
    return found  # Return existing — no duplicate created
```

This ensures that network retries, duplicate API calls, or worker restarts never create duplicate financial records.

## Balance Validation

Every `post_journal` call validates that debits equal credits before persisting:

```python
total_debits = sum(e["amount"] for e in entries if e["direction"] == "debit")
total_credits = sum(e["amount"] for e in entries if e["direction"] == "credit")
if total_debits != total_credits:
    raise ValueError(f"Journal does not balance: debits={total_debits} credits={total_credits}")
```

The reconciliation worker periodically scans all customer accounts and flags any negative balances as anomalies.
