# Stablecoin Payments API

A Stripe-like REST API for stablecoin payments. Supports customer management, wallet creation, simulated fiat-to-USDC deposits, USDC transfers, merchant checkout flows, webhook delivery, and double-entry ledger reconciliation.

## Getting Started

```bash
# Local (no Docker)
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Or with Docker Compose (starts API + Postgres + Redis)
docker compose up --build
```

The API auto-creates tables on startup. Visit http://localhost:8000/docs for Swagger UI.

## Quick Example

```bash
# 1. Get an API key
curl -X POST http://localhost:8000/v1/admin/api_keys

# 2. Create a customer
curl -X POST http://localhost:8000/v1/customers \
  -H "X-API-Key: sk_test_..." \
  -H "Content-Type: application/json" \
  -d '{"email": "alice@example.com"}'

# 3. Create a wallet
curl -X POST http://localhost:8000/v1/wallets \
  -H "X-API-Key: sk_test_..." \
  -H "Content-Type: application/json" \
  -d '{"customer_id": "cus_...", "chain": "base-sepolia"}'

# 4. Deposit 100 USD and confirm
curl -X POST http://localhost:8000/v1/deposits \
  -H "X-API-Key: sk_test_..." \
  -H "Content-Type: application/json" \
  -d '{"customer_id": "cus_...", "amount_usd": "100.00"}'

curl -X POST http://localhost:8000/v1/deposits/dep_.../confirm \
  -H "X-API-Key: sk_test_..."

# 5. Transfer 20 USDC
curl -X POST http://localhost:8000/v1/transfers \
  -H "X-API-Key: sk_test_..." \
  -H "Content-Type: application/json" \
  -d '{"wallet_id": "wal_...", "recipient_address": "0x...", "amount_usdc": "20.00"}'

# 6. Check balance
curl http://localhost:8000/v1/balances/cus_... \
  -H "X-API-Key: sk_test_..."
```
