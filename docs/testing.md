---
title: Testing
layout: default
nav_order: 20
---

# Testing

[Documentation home](index.md)

## Run the automated suite

From the repository root, in an activated Python virtual environment:

```bash
pip install -r requirements.txt
pip install aiosqlite pytest 'pytest-asyncio==0.25.0'
pytest tests/ -v
```

The async fixtures use an in-memory SQLite database and an HTTPX ASGI client. The extra SQLite and test packages are required because they are not included in `requirements.txt`.

The committed tests cover customers, wallets, deposits, transfers, payment intents, webhook signing, and ledger behavior. They exercise the local implementation, not a live bank or blockchain settlement service.

## Manual API flow

Follow [Getting Started](getting-started.md), create an API key, then create a customer and wallet, confirm a simulated deposit, and submit a transfer. Replace each example identifier with the value returned by the preceding request. Inspect the customer balance and ledger using [API Reference](api-reference.md).

For delivery and background processing, use the dedicated [Webhooks](webhooks.md) and [Workers](workers.md) guides.
