---
title: Services
layout: default
nav_order: 9
---

# Services

[Documentation home](index.md)

Business logic layer orchestrating deposits, transfers, payments, wallets, and webhooks.

---

## Overview

The services layer encapsulates all business logic, sitting between the API routes and the data layer. Each service module owns a single domain and coordinates with the ledger service for any financial operations.

## Deposit Service

**File**: `app/services/deposit_service.py`

Handles the lifecycle of fiat-to-USDC deposits.

### `create_deposit(db, customer_id, amount_usd, idempotency_key)`

Creates a new deposit in `pending` status. If an `idempotency_key` is provided and matches an existing deposit, returns the existing one.

### `confirm_deposit(db, deposit_id)`

Confirms a pending deposit and creates two balanced ledger journals:

1. **Fiat deposit journal**:
   - `bank_clearing_usd` (debit) → `customer_usd` (credit)
2. **USD→USDC conversion journal**:
   - `customer_usd` (debit) → `customer_usdc_available` (credit)

Sets status to `completed` and records `completed_at` timestamp.

> Confirming an already-completed deposit raises a `ValueError`.

## Transfer Service

**File**: `app/services/transfer_service.py`

Manages the full transfer lifecycle from creation through blockchain confirmation or failure.

### `create_transfer(db, wallet_id, recipient_address, amount_usdc, idempotency_key)`

1. Looks up the wallet and its owner's `customer_usdc_available` account
2. Validates sufficient balance
3. Creates a reservation journal: available → reserved
4. Simulates blockchain submission (generates `tx_hash`)
5. Returns transfer with status `submitted`

### `confirm_transfer(db, transfer_id)`

Consumes reserved funds on successful on-chain confirmation:
- Journal: `customer_usdc_reserved` (debit) → `treasury_usdc` (credit)
- Emits `transfer.confirmed` webhook event

### `fail_transfer(db, transfer_id, reason)`

Releases reserved funds back to available on failure:
- Journal: `customer_usdc_reserved` (debit) → `customer_usdc_available` (credit)
- Records `failure_reason`
- Emits `transfer.failed` webhook event

## Payment Service

**File**: `app/services/payment_service.py`

Implements the Stripe-like merchant checkout flow with automatic platform fee deduction.

### `create_payment_intent(db, merchant_id, amount, currency, customer_id, metadata, idempotency_key)`

Creates a payment intent with:
- Status: `requires_payment_method`
- A generated `client_secret` for frontend integration
- Optional metadata stored as JSON

### `confirm_payment_intent(db, payment_intent_id, customer_id)`

1. Validates the payment intent is in `requires_payment_method` status
2. Checks the customer's available USDC balance
3. Calculates the platform fee (default: 2% / 200 basis points)
4. Creates two ledger journals:
   - **Merchant payment**: customer → merchant (amount minus fee)
   - **Platform fee**: customer → platform_fee account
5. Sets status to `succeeded`

**Fee calculation**:

```python
fee = amount * PLATFORM_FEE_BPS / 10000  # 200 BPS = 2%
merchant_amount = amount - fee
```

## Wallet Service

**File**: `app/services/wallet_service.py`

Provisions wallets and initializes ledger accounts for new customers.

### `create_wallet(db, customer_id, chain)`

1. Generates a simulated blockchain address (`0x{random_hex}`)
2. Creates the wallet record
3. Initializes customer ledger accounts:
   - `customer_usdc_available` (USDC)
   - `customer_usdc_reserved` (USDC)

## Webhook Service

**File**: `app/services/webhook_service.py`

Creates webhook events that are picked up by the webhook retry worker for delivery.

### `create_event(db, event_type, payload)`

Creates a `WebhookEvent` with:
- `delivery_status`: `pending`
- `retry_count`: 0
- Serialized JSON payload

Events are not delivered inline — the webhook retry worker handles asynchronous delivery with retries.

## Ledger Service

**File**: `app/services/ledger_service.py`

The financial core — see the [Ledger System](ledger.md) page for full documentation.

### Key Functions

| Function | Description |
|:---------|:------------|
| `create_account()` | Create a new ledger account |
| `get_or_create_account()` | Idempotent account creation |
| `get_system_account()` | Get/create system-level account (no customer) |
| `get_balance()` | Compute balance from ledger entries |
| `get_customer_balances()` | All balances for a customer |
| `post_journal()` | Post a balanced journal with entries |

## Reconciliation Service

**File**: `app/services/reconciliation_service.py`

Validates ledger integrity and generates summary reports.

### `check_reconciliation(db)`

Scans all customer accounts for negative balances and returns a list of anomalies.

### `get_ledger_summary(db)`

Returns aggregate balances for all accounts in the system, grouped by account type.
