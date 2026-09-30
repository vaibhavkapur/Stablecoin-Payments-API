---
title: Home
layout: default
nav_order: 1
---

# Stablecoin Payments API

A Stripe-style REST API demonstration for customers, wallets, deposits, USDC transfers, merchant checkout, webhooks, and double-entry ledger reconciliation.

[Get Started](getting-started.md) · [API Reference](api-reference.md) · [Repository README](https://github.com/vaibhavkapur/Stablecoin-Payments-API/blob/main/README.md)

## Documentation

- [Getting Started](getting-started.md)
- [Architecture](architecture.md)
- [API Reference](api-reference.md)
- [Configuration](configuration.md)
- [Database Schema](database.md)
- [Testing](testing.md)
- [Deployment](deployment.md)
- [Ledger System](ledger.md)
- [Webhooks](webhooks.md)
- [Workers](workers.md)
- [Services](services.md)

## Overview

The API demonstrates stablecoin payment workflows through a Stripe-style interface, from customer onboarding and simulated fiat deposits to transfers and merchant payment intents. The local services model wallet creation and blockchain settlement.

Every balance movement is tracked through a **double-entry ledger**, ensuring full auditability and reconciliation at all times.

## Key Features

- **Customer & Wallet Management** — Create customers and provision wallets on Base Sepolia
- **Fiat-to-USDC Deposits** — Accept USD deposits and convert to USDC with ledger tracking
- **On-Chain Transfers** — Send USDC with fund reservation, blockchain simulation, and confirmation
- **Merchant Checkout** — Stripe-like Payment Intents with client secrets and platform fees
- **Double-Entry Ledger** — Every transaction is balanced with debit/credit journal entries
- **Idempotent Operations** — All creation endpoints support idempotency keys to prevent duplicates
- **Webhook System** — Real-time event notifications with HMAC-SHA256 signing and retry logic
- **Background Workers** — Async transfer confirmation, webhook delivery, and reconciliation
- **API Key Authentication** — Secure endpoints with generated API keys
- **Admin & Reconciliation** — Ledger summaries and automated balance integrity checks

## Architecture at a Glance

```
┌─────────────┐     ┌───────────────────────────────────────────────┐
│   Client     │     │              FastAPI Server                   │
│  (cURL /     │────▶│                                               │
│   Frontend)  │     │  ┌──────────┐  ┌───────────┐  ┌───────────┐ │
└─────────────┘     │  │ API Layer │─▶│  Services  │─▶│  Ledger   │ │
                     │  │ (Routes)  │  │ (Business  │  │ (Double-  │ │
                     │  └──────────┘  │  Logic)    │  │  Entry)   │ │
                     │                └───────────┘  └───────────┘ │
                     │                       │                      │
                     │                ┌──────┴──────┐               │
                     │                │  SQLAlchemy  │               │
                     │                │  (Async ORM) │               │
                     │                └──────┬──────┘               │
                     └───────────────────────┼───────────────────────┘
                                             │
                     ┌───────────────────────┼───────────────────────┐
                     │       PostgreSQL / SQLite       Redis         │
                     └──────────────────────────────────────────────┘
                                             │
                     ┌───────────────────────┼───────────────────────┐
                     │            Background Workers                 │
                     │  ┌────────────┐ ┌──────────┐ ┌─────────────┐│
                     │  │  Transfer   │ │ Webhook  │ │Reconciliation││
                     │  │  Confirmer  │ │ Retrier  │ │   Checker   ││
                     │  └────────────┘ └──────────┘ └─────────────┘│
                     └──────────────────────────────────────────────┘
```

## Tech Stack and Scope

Python / FastAPI / SQLAlchemy, with SQLite or PostgreSQL and Redis. Wallet provisioning, fiat deposits, and blockchain transfers use local simulation; the API does not move real funds.

| Component | Technology |
|:----------|:-----------|
| Framework | FastAPI 0.111 |
| Language | Python 3.12 |
| ORM | SQLAlchemy 2.0 (async) |
| Migrations | Alembic 1.13 |
| Database | PostgreSQL 16 / SQLite (dev) |
| Cache & Queue | Redis 7 |
| Auth | API Keys + HMAC-SHA256 webhooks |
| HTTP Client | httpx (async) |
| Containerization | Docker & Docker Compose |
| Testing | pytest + pytest-asyncio |

## Project Structure

```
stablecoin-payments-api/
├── app/
│   ├── main.py                  # FastAPI app init & router setup
│   ├── core/
│   │   ├── config.py            # Settings & environment config
│   │   ├── database.py          # Async SQLAlchemy engine & sessions
│   │   ├── id_gen.py            # Prefixed ID generation (cus_, wal_, tr_)
│   │   └── security.py          # API key auth, webhook signing
│   ├── models/                  # SQLAlchemy ORM models
│   ├── schemas/                 # Pydantic request/response schemas
│   ├── api/                     # Route handlers
│   ├── services/                # Business logic layer
│   ├── workers/                 # Background async workers
│   └── static/                  # Dashboard & checkout HTML
├── migrations/                  # Alembic database migrations
├── tests/                       # Async test suite
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## Related projects

These are independent companion repositories. The links describe related work, not implemented runtime integrations:

- [Agent Authorization Wallet + Merchant Trust Gateway](https://github.com/vaibhavkapur/Agent-Authorization-Wallet-Merchant-Trust-Gateway): purchase authorization, merchant verification, and execution evidence.
- [Agent Services Marketplace](https://github.com/vaibhavkapur/Agent-Services-Marketplace): service discovery, quotes, and agent purchase workflows.
- [Agentic Commerce Protocol Test Lab](https://github.com/vaibhavkapur/Agentic-Commerce-Protocol-Test-Lab): protocol fixtures, scenarios, and conformance checks.
- [Autonomous Price Watch Buyer](https://github.com/vaibhavkapur/Autonomous-Price-Watch-Buyer): price monitoring and bounded purchase decisions.
- [Cross-Merchant Procurement Agent](https://github.com/vaibhavkapur/Cross-Merchant-Procurement-Agent): merchant comparison and procurement planning.
