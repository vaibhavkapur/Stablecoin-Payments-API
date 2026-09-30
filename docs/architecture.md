---
title: Architecture
layout: default
nav_order: 3
---

# Architecture

[Documentation home](index.md)

A four-layer design separating API routing, business logic, ledger accounting, and external integrations.

---

## System Design

The Stablecoin Payments API follows a **layered architecture** with a synchronous API server handling client requests and asynchronous background workers managing blockchain confirmations, webhook delivery, and reconciliation. Both share PostgreSQL and Redis infrastructure.

```
┌──────────────────────────────────────────────────────────┐
│                     API Server (port 8000)                │
│                                                          │
│   ┌─────────┐    ┌────────────┐    ┌──────────────────┐ │
│   │  Routes  │───▶│  Services  │───▶│  Ledger Service  │ │
│   │  (API)   │    │  (Logic)   │    │  (Double-Entry)  │ │
│   └─────────┘    └────────────┘    └──────────────────┘ │
│        │                │                    │           │
│   ┌────┴────────────────┴────────────────────┴────────┐ │
│   │           SQLAlchemy Async ORM                     │ │
│   └────────────────────────┬──────────────────────────┘ │
└────────────────────────────┼────────────────────────────┘
                             │
              ┌──────────────┴──────────────┐
              │     PostgreSQL / SQLite      │
              └──────────────┬──────────────┘
                             │
┌────────────────────────────┼────────────────────────────┐
│                  Background Workers                      │
│   ┌──────────────┐ ┌────────────┐ ┌───────────────────┐│
│   │ Transfer      │ │  Webhook   │ │  Reconciliation   ││
│   │ Status Poller │ │  Retrier   │ │  Checker          ││
│   │ (15s cycle)   │ │ (30s cycle)│ │  (5min cycle)     ││
│   └──────────────┘ └────────────┘ └───────────────────┘│
└─────────────────────────────────────────────────────────┘
```

## Four-Layer Architecture

### Layer 1: API Layer (`app/api/`)

Route handlers define REST endpoints and manage HTTP concerns — request validation, status codes, and error responses. Routes delegate all business logic to the services layer.

```python
@router.post("", response_model=TransferResponse, status_code=201)
async def create_transfer(
    body: TransferCreate,
    db: AsyncSession = Depends(get_db),
    _api_key: str = Depends(require_api_key),
):
    transfer = await transfer_service.create_transfer(
        db, body.wallet_id, body.recipient_address,
        body.amount_usdc, body.idempotency_key
    )
    await db.commit()
    return transfer
```

### Layer 2: Services Layer (`app/services/`)

Business logic is encapsulated in service modules. Each service orchestrates one domain — deposits, transfers, payments, or webhooks — and calls the ledger service for any balance movement.

| Service | Responsibility |
|:--------|:---------------|
| `deposit_service` | Deposit creation, fiat settlement, USD→USDC conversion |
| `transfer_service` | Transfer lifecycle, fund reservation, blockchain simulation |
| `payment_service` | Payment intent creation, merchant checkout, platform fee calculation |
| `wallet_service` | Wallet provisioning, address generation, account initialization |
| `webhook_service` | Event emission, payload signing, delivery tracking |
| `ledger_service` | Account management, journal posting, balance computation |
| `reconciliation_service` | Balance validation, account summaries |

### Layer 3: Ledger Layer (`app/services/ledger_service.py`)

The ledger enforces **double-entry bookkeeping** — every journal must have balanced debits and credits. This guarantees that no funds appear or disappear without a corresponding counter-entry.

```python
async def post_journal(db, reference_type, reference_id,
                       idempotency_key, description, entries):
    # Validate: total debits == total credits
    total_debits = sum(e["amount"] for e in entries if e["direction"] == "debit")
    total_credits = sum(e["amount"] for e in entries if e["direction"] == "credit")
    if total_debits != total_credits:
        raise ValueError("Journal does not balance")

    # Post journal with entries
    journal = Journal(id=generate_prefixed_id("jrn"), ...)
    for entry in entries:
        LedgerEntry(id=generate_prefixed_id("le"), ...)
```

### Layer 4: Data Layer

SQLAlchemy async ORM with explicit session management. All database access goes through `AsyncSession` with commit/flush control at the API layer.

## Key Design Patterns

### Idempotency

All creation endpoints accept an optional `idempotency_key`. If a record with the same key already exists, the original is returned instead of creating a duplicate. This prevents double-charges from network retries.

```python
# Check idempotency before creating
existing = await db.execute(
    select(Journal).where(Journal.idempotency_key == idempotency_key)
)
if found := existing.scalar_one_or_none():
    return found  # Return existing record
```

### Status State Machines

Each transaction type follows a defined state machine:

**Deposit:**
```
pending ──▶ completed
```

**Transfer:**
```
created ──▶ submitted ──▶ confirmed
                     └──▶ failed
```

**Payment Intent:**
```
requires_payment_method ──▶ processing ──▶ succeeded
                                     └──▶ failed
```

### Prefixed IDs

Every entity uses a prefixed ID for instant type identification:

| Entity | Prefix | Example |
|:-------|:-------|:--------|
| Customer | `cus_` | `cus_a1b2c3d4` |
| Wallet | `wal_` | `wal_e5f6g7h8` |
| Deposit | `dep_` | `dep_i9j0k1l2` |
| Transfer | `tr_` | `tr_m3n4o5p6` |
| Payment Intent | `pi_` | `pi_q7r8s9t0` |
| Account | `acct_` | `acct_u1v2w3` |
| Journal | `jrn_` | `jrn_x4y5z6` |
| Ledger Entry | `le_` | `le_a7b8c9` |
| Webhook Event | `evt_` | `evt_d0e1f2` |

### Dependency Injection

FastAPI's dependency system provides database sessions and API key validation to route handlers. Test fixtures override these dependencies for isolated testing.

```python
# Production
db: AsyncSession = Depends(get_db)
_api_key: str = Depends(require_api_key)

# Tests
app.dependency_overrides[get_db] = override_get_db
```

## Security Model

### API Key Authentication

- Keys are generated via `POST /v1/admin/api_keys` with the format `sk_test_{random_hex}`
- Passed in the `X-API-Key` header on all protected endpoints
- In development mode (no keys created), all requests are allowed
- In production, keys should be stored hashed in the database

### Webhook Signing

Outbound webhooks are signed with HMAC-SHA256:

```
X-Webhook-Signature: t=1711468800,v1=5257a869e7ecebeda32affa62cdca3fa51cad7e77a0e56ff536d0ce8e108d8bd
```

The signature covers `{timestamp}.{payload}`, preventing replay attacks while allowing merchants to verify authenticity.
