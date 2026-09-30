---
title: Database Schema
layout: default
nav_order: 7
---

# Database Schema

[Documentation home](index.md)

PostgreSQL schema with eight core tables, managed by Alembic migrations and accessed through SQLAlchemy async ORM.

---

## Overview

The database stores all transactional state — customers, wallets, deposits, transfers, payment intents, ledger accounts, journals, and webhook events. SQLAlchemy async ORM provides the data access layer, with Alembic managing schema migrations.

- **Production**: PostgreSQL 16
- **Development**: SQLite (via aiosqlite)

## Entity Relationships

```
┌──────────┐     ┌──────────┐     ┌──────────────┐
│ Customer │────▶│  Wallet  │     │   Deposit    │
│          │     └──────────┘     └──────────────┘
│          │                            │
│          │────▶┌──────────────┐       │
│          │     │  Payment     │       │
└──────────┘     │  Account     │◀──────┘ (via ledger)
      │          └──────┬───────┘
      │                 │
      │          ┌──────┴───────┐
      │          │   Journal    │
      │          │   ┌─────────┐│
      │          │   │ Ledger  ││
      │          │   │ Entry   ││
      │          │   └─────────┘│
      │          └──────────────┘
      │
      ├────▶┌──────────────┐
      │     │   Transfer   │
      │     └──────────────┘
      │
      ├────▶┌──────────────┐
      │     │  Payment     │
      │     │  Intent      │
      │     └──────────────┘
      │
      └────▶┌──────────────┐
            │  Webhook     │
            │  Event       │
            └──────────────┘
```

## Tables

### customers

| Column | Type | Constraints | Description |
|:-------|:-----|:------------|:------------|
| `id` | VARCHAR | PK | Prefixed `cus_` |
| `email` | VARCHAR | UNIQUE, NOT NULL | Customer email |
| `external_ref` | VARCHAR | NULLABLE | External system reference |
| `created_at` | TIMESTAMP | NOT NULL, DEFAULT now() | Creation timestamp |

### wallets

| Column | Type | Constraints | Description |
|:-------|:-----|:------------|:------------|
| `id` | VARCHAR | PK | Prefixed `wal_` |
| `customer_id` | VARCHAR | FK → customers.id | Owner customer |
| `address` | VARCHAR | UNIQUE, NOT NULL | Blockchain address (0x...) |
| `provider` | VARCHAR | NOT NULL, DEFAULT 'local' | Wallet provider |
| `chain` | VARCHAR | NOT NULL, DEFAULT 'base-sepolia' | Blockchain network |
| `wallet_provider_id` | VARCHAR | NULLABLE | External provider reference |
| `created_at` | TIMESTAMP | NOT NULL, DEFAULT now() | Creation timestamp |

### deposits

| Column | Type | Constraints | Description |
|:-------|:-----|:------------|:------------|
| `id` | VARCHAR | PK | Prefixed `dep_` |
| `customer_id` | VARCHAR | FK → customers.id | Depositing customer |
| `amount_usd` | NUMERIC | NOT NULL | USD deposit amount |
| `status` | VARCHAR | NOT NULL, DEFAULT 'pending' | `pending` or `completed` |
| `idempotency_key` | VARCHAR | UNIQUE, NULLABLE | Deduplication key |
| `created_at` | TIMESTAMP | NOT NULL, DEFAULT now() | Creation timestamp |
| `completed_at` | TIMESTAMP | NULLABLE | Confirmation timestamp |

### transfers

| Column | Type | Constraints | Description |
|:-------|:-----|:------------|:------------|
| `id` | VARCHAR | PK | Prefixed `tr_` |
| `sender_wallet_id` | VARCHAR | FK → wallets.id | Source wallet |
| `recipient_address` | VARCHAR | NOT NULL | Destination address |
| `amount_usdc` | NUMERIC | NOT NULL | USDC transfer amount |
| `status` | VARCHAR | NOT NULL | `created`, `submitted`, `confirmed`, `failed` |
| `chain` | VARCHAR | NOT NULL | Blockchain network |
| `tx_hash` | VARCHAR | NULLABLE | Blockchain transaction hash |
| `block_number` | INTEGER | NULLABLE | Confirmation block number |
| `confirmations` | INTEGER | NULLABLE | Number of block confirmations |
| `gas_used` | NUMERIC | NULLABLE | Gas consumed |
| `effective_fee` | NUMERIC | NULLABLE | Actual transaction fee |
| `failure_reason` | VARCHAR | NULLABLE | Error description on failure |
| `idempotency_key` | VARCHAR | UNIQUE, NULLABLE | Deduplication key |
| `created_at` | TIMESTAMP | NOT NULL, DEFAULT now() | Creation timestamp |
| `submitted_at` | TIMESTAMP | NULLABLE | Blockchain submission time |
| `confirmed_at` | TIMESTAMP | NULLABLE | On-chain confirmation time |

### payment_intents

| Column | Type | Constraints | Description |
|:-------|:-----|:------------|:------------|
| `id` | VARCHAR | PK | Prefixed `pi_` |
| `merchant_id` | VARCHAR | FK → customers.id | Receiving merchant |
| `customer_id` | VARCHAR | FK → customers.id, NULLABLE | Paying customer |
| `amount` | NUMERIC | NOT NULL | Payment amount |
| `currency` | VARCHAR | NOT NULL, DEFAULT 'USDC' | Payment currency |
| `status` | VARCHAR | NOT NULL | `requires_payment_method`, `processing`, `succeeded`, `failed` |
| `client_secret` | VARCHAR | NOT NULL | Stripe-like client secret |
| `metadata_json` | TEXT | NULLABLE | JSON metadata blob |
| `idempotency_key` | VARCHAR | UNIQUE, NULLABLE | Deduplication key |
| `created_at` | TIMESTAMP | NOT NULL, DEFAULT now() | Creation timestamp |
| `confirmed_at` | TIMESTAMP | NULLABLE | Payment confirmation time |

### payment_accounts

| Column | Type | Constraints | Description |
|:-------|:-----|:------------|:------------|
| `id` | VARCHAR | PK | Prefixed `acct_` |
| `customer_id` | VARCHAR | FK → customers.id, NULLABLE | NULL for system accounts |
| `type` | VARCHAR | NOT NULL | Account type (see Ledger System) |
| `currency` | VARCHAR | NOT NULL | `USDC` or `USD` |

### journals

| Column | Type | Constraints | Description |
|:-------|:-----|:------------|:------------|
| `id` | VARCHAR | PK | Prefixed `jrn_` |
| `reference_type` | VARCHAR | NOT NULL | `deposit`, `transfer`, `payment_intent` |
| `reference_id` | VARCHAR | NOT NULL | ID of the originating transaction |
| `description` | VARCHAR | NOT NULL | Human-readable description |
| `idempotency_key` | VARCHAR | UNIQUE, NOT NULL | Deduplication key |
| `created_at` | TIMESTAMP | NOT NULL, DEFAULT now() | Creation timestamp |

### ledger_entries

| Column | Type | Constraints | Description |
|:-------|:-----|:------------|:------------|
| `id` | VARCHAR | PK | Prefixed `le_` |
| `journal_id` | VARCHAR | FK → journals.id | Parent journal |
| `account_id` | VARCHAR | FK → payment_accounts.id | Target account |
| `direction` | VARCHAR | NOT NULL | `debit` or `credit` |
| `amount` | NUMERIC | NOT NULL | Entry amount |
| `currency` | VARCHAR | NOT NULL | `USDC` or `USD` |

### webhook_events

| Column | Type | Constraints | Description |
|:-------|:-----|:------------|:------------|
| `id` | VARCHAR | PK | Prefixed `evt_` |
| `event_type` | VARCHAR | NOT NULL | Event type string |
| `payload` | TEXT | NOT NULL | JSON event payload |
| `delivery_status` | VARCHAR | NOT NULL, DEFAULT 'pending' | `pending`, `delivered`, `failed` |
| `retry_count` | INTEGER | NOT NULL, DEFAULT 0 | Delivery attempts |
| `last_attempt_at` | TIMESTAMP | NULLABLE | Last delivery attempt |
| `created_at` | TIMESTAMP | NOT NULL, DEFAULT now() | Creation timestamp |

## Migrations

Migrations are managed by Alembic:

```bash
# Apply all migrations
alembic upgrade head

# Create a new migration
alembic revision --autogenerate -m "description"

# Roll back one migration
alembic downgrade -1
```

Migration files live in `migrations/versions/`.
