---
title: API Reference
layout: default
nav_order: 4
---

# API Reference
{: .fs-9 }

Complete reference for all REST endpoints — authentication, request/response schemas, and example payloads.
{: .fs-6 .fw-300 }

---

## Base URL

```
http://localhost:8000
```

Interactive Swagger documentation is available at `/docs` and ReDoc at `/redoc`.

## Authentication

All `/v1/*` endpoints require the `X-API-Key` header. Generate a key via the admin endpoint first.

```bash
curl -X POST http://localhost:8000/v1/admin/api_keys
```

{: .note }
> In development mode (no keys created), all requests are allowed without authentication.

---

## Customers

### Create Customer

`POST /v1/customers`

| Field | Type | Required | Description |
|:------|:-----|:---------|:------------|
| `email` | string | Yes | Valid email address (unique) |
| `external_ref` | string | No | External reference ID |

```bash
curl -X POST http://localhost:8000/v1/customers \
  -H "X-API-Key: sk_test_..." \
  -H "Content-Type: application/json" \
  -d '{"email": "alice@example.com", "external_ref": "user_123"}'
```

**Response** `201 Created`

```json
{
  "id": "cus_a1b2c3d4e5f6",
  "email": "alice@example.com",
  "external_ref": "user_123",
  "created_at": "2026-03-26T10:00:00Z"
}
```

### Get Customer

`GET /v1/customers/{customer_id}`

```bash
curl http://localhost:8000/v1/customers/cus_a1b2c3d4e5f6 \
  -H "X-API-Key: sk_test_..."
```

### List Customers

`GET /v1/customers`

Returns all customers ordered by creation date.

---

## Wallets

### Create Wallet

`POST /v1/wallets`

| Field | Type | Required | Description |
|:------|:-----|:---------|:------------|
| `customer_id` | string | Yes | Customer ID (`cus_` prefix) |
| `chain` | string | No | Blockchain network (default: `base-sepolia`) |

```bash
curl -X POST http://localhost:8000/v1/wallets \
  -H "X-API-Key: sk_test_..." \
  -H "Content-Type: application/json" \
  -d '{"customer_id": "cus_a1b2c3d4e5f6"}'
```

**Response** `201 Created`

```json
{
  "id": "wal_g7h8i9j0k1l2",
  "customer_id": "cus_a1b2c3d4e5f6",
  "address": "0x1a2b3c4d5e6f7890abcdef1234567890abcdef12",
  "chain": "base-sepolia",
  "provider": "local",
  "created_at": "2026-03-26T10:00:01Z"
}
```

Creating a wallet also initializes ledger accounts for the customer:
- `customer_usdc_available` — spendable USDC balance
- `customer_usdc_reserved` — funds reserved for pending transfers

### Get Wallet

`GET /v1/wallets/{wallet_id}`

### List Wallets

`GET /v1/wallets?customer_id={customer_id}`

---

## Deposits

Deposits represent fiat USD flowing into the system and converting to USDC.

### Create Deposit

`POST /v1/deposits`

| Field | Type | Required | Description |
|:------|:-----|:---------|:------------|
| `customer_id` | string | Yes | Customer ID |
| `amount_usd` | string | Yes | USD amount (e.g., `"500.00"`) |
| `idempotency_key` | string | No | Unique key to prevent duplicates |

```bash
curl -X POST http://localhost:8000/v1/deposits \
  -H "X-API-Key: sk_test_..." \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "cus_a1b2c3d4e5f6",
    "amount_usd": "500.00",
    "idempotency_key": "dep_unique_001"
  }'
```

**Response** `201 Created`

```json
{
  "id": "dep_m3n4o5p6q7r8",
  "customer_id": "cus_a1b2c3d4e5f6",
  "amount_usd": 500.0,
  "status": "pending",
  "reference": null,
  "created_at": "2026-03-26T10:00:02Z",
  "completed_at": null
}
```

### Confirm Deposit

`POST /v1/deposits/{deposit_id}/confirm`

Simulates bank settlement. On confirmation, two ledger journals are created:

1. **Fiat deposit**: `bank_clearing_usd` (debit) → `customer_usd` (credit)
2. **USD→USDC conversion**: `customer_usd` (debit) → `customer_usdc_available` (credit)

```bash
curl -X POST http://localhost:8000/v1/deposits/dep_m3n4o5p6q7r8/confirm \
  -H "X-API-Key: sk_test_..."
```

**Response** `200 OK`

```json
{
  "id": "dep_m3n4o5p6q7r8",
  "customer_id": "cus_a1b2c3d4e5f6",
  "amount_usd": 500.0,
  "status": "completed",
  "reference": null,
  "created_at": "2026-03-26T10:00:02Z",
  "completed_at": "2026-03-26T10:00:10Z"
}
```

### Get Deposit

`GET /v1/deposits/{deposit_id}`

---

## Transfers

Transfers send USDC from a customer's wallet to an external address on Base Sepolia.

### Create Transfer

`POST /v1/transfers`

| Field | Type | Required | Description |
|:------|:-----|:---------|:------------|
| `wallet_id` | string | Yes | Source wallet ID |
| `recipient_address` | string | Yes | Destination blockchain address |
| `amount_usdc` | string | Yes | USDC amount (e.g., `"100.00"`) |
| `idempotency_key` | string | No | Unique key to prevent duplicates |

On creation, the system:
1. Validates the customer has sufficient available balance
2. Reserves funds: `customer_usdc_available` → `customer_usdc_reserved`
3. Simulates blockchain submission (generates `tx_hash`)
4. Sets status to `submitted`

```bash
curl -X POST http://localhost:8000/v1/transfers \
  -H "X-API-Key: sk_test_..." \
  -H "Content-Type: application/json" \
  -d '{
    "wallet_id": "wal_g7h8i9j0k1l2",
    "recipient_address": "0x9876543210abcdef9876543210abcdef98765432",
    "amount_usdc": "100.00"
  }'
```

**Response** `201 Created`

```json
{
  "id": "tr_s9t0u1v2w3x4",
  "sender_wallet_id": "wal_g7h8i9j0k1l2",
  "recipient_address": "0x9876543210abcdef9876543210abcdef98765432",
  "amount_usdc": 100.0,
  "status": "submitted",
  "chain": "base-sepolia",
  "tx_hash": "0xabc123def456...",
  "failure_reason": null,
  "created_at": "2026-03-26T10:00:15Z",
  "submitted_at": "2026-03-26T10:00:15Z",
  "confirmed_at": null
}
```

### Confirm Transfer

`POST /v1/transfers/{transfer_id}/confirm`

Manually confirms a transfer (simulates on-chain confirmation). The background worker also auto-confirms after ~15 seconds.

**Ledger**: `customer_usdc_reserved` (debit) → `treasury_usdc` (credit)

### Fail Transfer

`POST /v1/transfers/{transfer_id}/fail`

Marks a transfer as failed and releases reserved funds back to available.

**Ledger**: `customer_usdc_reserved` (debit) → `customer_usdc_available` (credit)

### Get Transfer

`GET /v1/transfers/{transfer_id}`

---

## Payment Intents

Stripe-like merchant checkout flow. A merchant creates a payment intent, and a customer confirms it to transfer USDC with an automatic platform fee deduction.

### Create Payment Intent

`POST /v1/payment_intents`

| Field | Type | Required | Description |
|:------|:-----|:---------|:------------|
| `merchant_id` | string | Yes | Merchant's customer ID |
| `customer_id` | string | No | Paying customer's ID (can be set at confirmation) |
| `amount` | string | Yes | USDC amount |
| `currency` | string | No | Currency code (default: `USDC`) |
| `metadata` | object | No | Arbitrary key-value metadata |
| `idempotency_key` | string | No | Unique key to prevent duplicates |

```bash
curl -X POST http://localhost:8000/v1/payment_intents \
  -H "X-API-Key: sk_test_..." \
  -H "Content-Type: application/json" \
  -d '{
    "merchant_id": "cus_merchant_001",
    "amount": "50.00",
    "metadata": {"order_id": "order_789"}
  }'
```

**Response** `201 Created`

```json
{
  "id": "pi_y5z6a7b8c9d0",
  "merchant_id": "cus_merchant_001",
  "customer_id": null,
  "amount": 50.0,
  "currency": "USDC",
  "status": "requires_payment_method",
  "client_secret": "pi_y5z6a7b8c9d0_secret_e1f2g3h4",
  "created_at": "2026-03-26T10:00:20Z",
  "confirmed_at": null
}
```

### Confirm Payment Intent

`POST /v1/payment_intents/{payment_intent_id}/confirm`

| Field | Type | Required | Description |
|:------|:-----|:---------|:------------|
| `customer_id` | string | Yes | Customer making the payment |

On confirmation:
1. Customer's available balance is validated
2. **Platform fee** (2%, configurable via `PLATFORM_FEE_BPS`) is calculated
3. Two ledger journals are posted:
   - Customer USDC → Merchant USDC (minus fee)
   - Customer USDC → Platform Fee account (fee amount)

```bash
curl -X POST http://localhost:8000/v1/payment_intents/pi_y5z6a7b8c9d0/confirm \
  -H "X-API-Key: sk_test_..." \
  -H "Content-Type: application/json" \
  -d '{"customer_id": "cus_a1b2c3d4e5f6"}'
```

**Response** `200 OK`

```json
{
  "id": "pi_y5z6a7b8c9d0",
  "merchant_id": "cus_merchant_001",
  "customer_id": "cus_a1b2c3d4e5f6",
  "amount": 50.0,
  "currency": "USDC",
  "status": "succeeded",
  "client_secret": "pi_y5z6a7b8c9d0_secret_e1f2g3h4",
  "created_at": "2026-03-26T10:00:20Z",
  "confirmed_at": "2026-03-26T10:00:25Z"
}
```

For a $50.00 payment with 2% fee:
- Merchant receives **$49.00 USDC**
- Platform keeps **$1.00 USDC**

### Get Payment Intent

`GET /v1/payment_intents/{payment_intent_id}`

---

## Balances

### Get Customer Balances

`GET /v1/balances/{customer_id}`

Returns the real-time ledger balance for all of a customer's accounts.

```bash
curl http://localhost:8000/v1/balances/cus_a1b2c3d4e5f6 \
  -H "X-API-Key: sk_test_..."
```

**Response** `200 OK`

```json
{
  "customer_id": "cus_a1b2c3d4e5f6",
  "balances": [
    {
      "account_type": "customer_usdc_available",
      "currency": "USDC",
      "balance": 400.0
    },
    {
      "account_type": "customer_usdc_reserved",
      "currency": "USDC",
      "balance": 0.0
    }
  ]
}
```

---

## Webhooks

### Send Test Webhook

`POST /v1/webhooks/test`

| Field | Type | Required | Description |
|:------|:-----|:---------|:------------|
| `url` | string | Yes | Destination URL for the webhook |
| `event_type` | string | No | Event type (default: `test.ping`) |

```bash
curl -X POST http://localhost:8000/v1/webhooks/test \
  -H "X-API-Key: sk_test_..." \
  -H "Content-Type: application/json" \
  -d '{"url": "https://webhook.site/your-id", "event_type": "test.ping"}'
```

### List Webhook Events

`GET /v1/webhooks/events`

### Get Webhook Event

`GET /v1/webhooks/events/{event_id}`

```json
{
  "id": "evt_x1y2z3a4b5c6",
  "event_type": "transfer.confirmed",
  "payload": "{\"transfer_id\": \"tr_s9t0u1v2w3x4\", \"status\": \"confirmed\"}",
  "delivery_status": "delivered",
  "retry_count": 1,
  "last_attempt_at": "2026-03-26T10:01:00Z",
  "created_at": "2026-03-26T10:00:30Z"
}
```

---

## Admin

### Generate API Key

`POST /v1/admin/api_keys`

No authentication required. Returns a new API key with `sk_test_` prefix.

### Reconciliation Check

`GET /v1/admin/reconciliation`

Validates all ledger accounts for balance integrity. Returns any mismatches found.

### Ledger Summary

`GET /v1/admin/ledger_summary`

Returns balances for all accounts in the system, including system-level accounts (treasury, platform fee, bank clearing).

---

## Health Check

`GET /health`

```json
{
  "status": "ok"
}
```

---

## Error Responses

All errors follow a consistent format:

```json
{
  "detail": "Insufficient available balance"
}
```

| Status Code | Meaning |
|:------------|:--------|
| `400` | Bad request — validation error or business rule violation |
| `401` | Unauthorized — missing or invalid API key |
| `404` | Not found — resource does not exist |
| `422` | Unprocessable entity — request body validation failed |
| `500` | Internal server error |
