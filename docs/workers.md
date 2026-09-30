---
title: Workers
layout: default
nav_order: 8
---

# Workers

[Documentation home](index.md)

Three concurrent background processes handling transfer confirmations, webhook delivery, and ledger reconciliation.

---

## Overview

The workers service runs three independent async background processes that share the PostgreSQL database. They handle operations that cannot be completed synchronously during an API request — blockchain confirmations, webhook delivery retries, and periodic balance checks.

```bash
# Start all workers
python -m app.workers.run
```

## Transfer Status Worker

**Type**: Interval-based polling (every 15 seconds)

Monitors pending transfers and auto-confirms them, simulating on-chain finality.

### Process Flow

1. Query all transfers with `status = "submitted"`
2. For each submitted transfer:
   - Call `confirm_transfer()` on the transfer service
   - Journal: `customer_usdc_reserved` (debit) → `treasury_usdc` (credit)
   - Update status to `confirmed`
   - Emit `transfer.confirmed` webhook event
3. Commit all changes

### Production Behavior

In a production environment, this worker would:
- Query a blockchain node or indexer for transaction receipts
- Verify the required number of block confirmations
- Record actual `block_number`, `confirmations`, `gas_used`, and `effective_fee`
- Flag stuck transactions for manual review after a timeout

```python
async def _poll_transfers(self):
    async with async_session() as db:
        result = await db.execute(
            select(Transfer).where(Transfer.status == "submitted")
        )
        for transfer in result.scalars().all():
            await transfer_service.confirm_transfer(db, transfer.id)
        await db.commit()
```

## Webhook Retry Worker

**Type**: Interval-based polling (every 30 seconds)

Retries delivery of pending and failed webhook events, ensuring at-least-once delivery.

### Process Flow

1. Query webhook events where `delivery_status = "pending"` and `retry_count < 5`
2. For each event:
   - Sign the payload with HMAC-SHA256
   - Attempt HTTPS POST delivery
   - On success: set `delivery_status = "delivered"`
   - On failure: increment `retry_count`, update `last_attempt_at`
3. After 5 failed attempts: set `delivery_status = "failed"`

### Delivery Guarantees

| Property | Value |
|:---------|:------|
| Delivery model | At-least-once |
| Max attempts | 5 |
| Retry interval | 30 seconds |
| Signature | HMAC-SHA256 via `X-Webhook-Signature` header |

### Signature Format

```
X-Webhook-Signature: t=1711468800,v1=5257a869e7ecebeda32affa62cdca3fa51cad7e77a0e56ff536d0ce8e108d8bd
```

The signed content is `{timestamp}.{payload_json}`, computed with the `WEBHOOK_SECRET` environment variable.

## Reconciliation Worker

**Type**: Interval-based polling (every 5 minutes)

Validates the integrity of all ledger account balances by checking for anomalies.

### Checks Performed

1. **Negative balance detection** — Scans all customer accounts for negative balances, which indicate a ledger inconsistency
2. **Journal balance verification** — Ensures every journal's debits equal its credits
3. **Account summary generation** — Logs aggregate balances across all account types

### Alerting

When an anomaly is detected, the worker logs a warning:

```
WARNING: Account acct_xyz has negative balance: -50.00 USDC
```

In production, these warnings should be routed to an alerting system (PagerDuty, Slack, etc.) for immediate investigation.

## Worker Architecture

All workers use Python's `asyncio` for non-blocking execution:

```python
async def run_workers():
    await asyncio.gather(
        transfer_status_worker.start(),
        webhook_retry_worker.start(),
        reconciliation_worker.start(),
    )
```

### Worker Summary

| Worker | Interval | Purpose |
|:-------|:---------|:--------|
| Transfer Status | 15 seconds | Auto-confirm submitted transfers |
| Webhook Retry | 30 seconds | Retry failed webhook deliveries |
| Reconciliation | 5 minutes | Validate ledger integrity |

### Scaling Considerations

Workers are designed to run as a single instance. In a distributed deployment:

- **Transfer worker** — Use distributed locks (Redis) to prevent duplicate confirmations
- **Webhook worker** — Safe to scale with idempotent delivery tracking
- **Reconciliation worker** — Single instance only; read-only operation
