---
title: Home
layout: default
nav_order: 1
---

# Stablecoin Payments API
{: .fs-9 }

A production-grade, Stripe-like REST API for stablecoin payments — enabling businesses to manage customers, wallets, USDC deposits, transfers, and merchant checkout flows on Base Sepolia.
{: .fs-6 .fw-300 }

---

## Overview

The Stablecoin Payments API is a complete backend system for accepting, holding, and transferring USDC stablecoins. Built with FastAPI and Python, it provides a familiar Stripe-style interface for managing the full lifecycle of stablecoin transactions — from customer onboarding and fiat-to-USDC deposits to on-chain transfers and merchant payment intents.

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

## Tech Stack

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
