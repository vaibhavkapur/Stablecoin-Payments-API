---
title: Getting Started
layout: default
nav_order: 2
---

# Getting Started
{: .fs-9 }

Set up the Stablecoin Payments API locally and run your first payment flow in under five minutes.
{: .fs-6 .fw-300 }

---

## Prerequisites

| Requirement | Version |
|:------------|:--------|
| Python | 3.12+ |
| Docker & Docker Compose | Latest |
| Git | Any |

## Clone & Install

```bash
git clone https://github.com/vaibhavkapur22/Stablecoin-Payments-API.git
cd Stablecoin-Payments-API
pip install -r requirements.txt
```

## Infrastructure

Start PostgreSQL and Redis with Docker Compose:

```bash
docker-compose up -d postgres redis
```

This launches:
- **PostgreSQL 16** on port `5432` (user: `stablecoin`, db: `stablecoin_payments`)
- **Redis 7** on port `6379`

For local development without Docker, SQLite is used by default — no additional setup needed.

## Configuration

Copy and edit the environment file:

```bash
cp .env.example .env
```

Default `.env` settings for local development:

```bash
DATABASE_URL=sqlite+aiosqlite:///./stablecoin_payments.db
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=change-me-in-production-use-a-real-secret
API_KEY_HEADER=X-API-Key
WEBHOOK_SECRET=whsec_test_secret
```

## Database Migrations

Run Alembic migrations to set up the schema:

```bash
alembic upgrade head
```

## Start the Services

**Terminal 1** — API Server:

```bash
uvicorn app.main:app --reload --port 8000
```

**Terminal 2** — Background Workers:

```bash
python -m app.workers.run
```

The API is now available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

## Quick Start Flow

Walk through a complete payment lifecycle — create a customer, fund their account, and send USDC.

### 1. Generate an API Key

```bash
curl -X POST http://localhost:8000/v1/admin/api_keys
```

```json
{
  "api_key": "sk_test_a1b2c3d4e5f6..."
}
```

### 2. Create a Customer

```bash
curl -X POST http://localhost:8000/v1/customers \
  -H "X-API-Key: sk_test_a1b2c3d4e5f6..." \
  -H "Content-Type: application/json" \
  -d '{"email": "alice@example.com"}'
```

```json
{
  "id": "cus_abc123",
  "email": "alice@example.com",
  "external_ref": null,
  "created_at": "2026-03-26T10:00:00Z"
}
```

### 3. Create a Wallet

```bash
curl -X POST http://localhost:8000/v1/wallets \
  -H "X-API-Key: sk_test_a1b2c3d4e5f6..." \
  -H "Content-Type: application/json" \
  -d '{"customer_id": "cus_abc123"}'
```

```json
{
  "id": "wal_def456",
  "customer_id": "cus_abc123",
  "address": "0x1a2b3c4d5e6f...",
  "chain": "base-sepolia",
  "provider": "local",
  "created_at": "2026-03-26T10:00:01Z"
}
```

### 4. Deposit Funds (USD → USDC)

```bash
# Create a pending deposit
curl -X POST http://localhost:8000/v1/deposits \
  -H "X-API-Key: sk_test_a1b2c3d4e5f6..." \
  -H "Content-Type: application/json" \
  -d '{"customer_id": "cus_abc123", "amount_usd": "500.00"}'

# Confirm the deposit (simulates bank settlement)
curl -X POST http://localhost:8000/v1/deposits/dep_ghi789/confirm \
  -H "X-API-Key: sk_test_a1b2c3d4e5f6..."
```

After confirmation, the ledger records two journals:
1. **Fiat deposit**: bank_clearing (debit) → customer_usd (credit)
2. **USD→USDC conversion**: customer_usd (debit) → customer_usdc_available (credit)

### 5. Send a Transfer

```bash
curl -X POST http://localhost:8000/v1/transfers \
  -H "X-API-Key: sk_test_a1b2c3d4e5f6..." \
  -H "Content-Type: application/json" \
  -d '{
    "wallet_id": "wal_def456",
    "recipient_address": "0x9876543210abcdef...",
    "amount_usdc": "100.00"
  }'
```

```json
{
  "id": "tr_jkl012",
  "sender_wallet_id": "wal_def456",
  "recipient_address": "0x9876543210abcdef...",
  "amount_usdc": 100.0,
  "status": "submitted",
  "chain": "base-sepolia",
  "tx_hash": "0xabc123...",
  "created_at": "2026-03-26T10:00:05Z"
}
```

The transfer worker will auto-confirm it within ~15 seconds.

### 6. Check Balance

```bash
curl http://localhost:8000/v1/balances/cus_abc123 \
  -H "X-API-Key: sk_test_a1b2c3d4e5f6..."
```

```json
{
  "customer_id": "cus_abc123",
  "balances": [
    {"account_type": "customer_usdc_available", "currency": "USDC", "balance": 400.0},
    {"account_type": "customer_usdc_reserved", "currency": "USDC", "balance": 0.0}
  ]
}
```

## Docker Deployment

Run the full stack with a single command:

```bash
docker-compose up --build
```

This starts four containers:
- **api** — FastAPI on port 8000
- **postgres** — PostgreSQL 16 on port 5432
- **redis** — Redis 7 on port 6379
- **worker** — Background workers

## Running Tests

```bash
pytest tests/ -v
```

Tests use an in-memory SQLite database — no external services required.
