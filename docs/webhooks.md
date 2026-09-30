---
title: Webhooks
layout: default
nav_order: 6
---

# Webhooks

[Documentation home](index.md)

Real-time event notifications with HMAC-SHA256 signatures, automatic retries, and delivery tracking.

---

## Overview

The webhook system delivers real-time HTTPS POST notifications when key events occur in the payment lifecycle. Every outbound webhook is signed with HMAC-SHA256 so recipients can verify authenticity.

## Event Types

| Event | Trigger |
|:------|:--------|
| `deposit.pending` | Deposit created, awaiting confirmation |
| `deposit.completed` | Deposit confirmed, funds available |
| `transfer.submitted` | Transfer submitted to blockchain |
| `transfer.confirmed` | Transfer confirmed on-chain |
| `transfer.failed` | Transfer failed, funds released |
| `payment_intent.created` | Payment intent created |
| `payment_intent.succeeded` | Payment confirmed, merchant paid |
| `payment_intent.failed` | Payment failed |
| `test.ping` | Test webhook event |

## Webhook Payload

```json
{
  "id": "evt_x1y2z3a4b5c6",
  "event_type": "transfer.confirmed",
  "payload": {
    "transfer_id": "tr_s9t0u1v2w3x4",
    "sender_wallet_id": "wal_g7h8i9j0k1l2",
    "recipient_address": "0x9876543210abcdef...",
    "amount_usdc": 100.0,
    "status": "confirmed",
    "chain": "base-sepolia",
    "tx_hash": "0xabc123def456..."
  },
  "created_at": "2026-03-26T10:00:30Z"
}
```

## Signature Verification

Every webhook includes a signature header:

```
X-Webhook-Signature: t=1711468800,v1=5257a869e7ecebeda32affa62cdca3fa51cad7e77a0e56ff536d0ce8e108d8bd
```

The signature is computed as `HMAC-SHA256(secret, "{timestamp}.{payload}")`.

### Python Verification Example

```python
import hmac
import hashlib

def verify_webhook(payload: bytes, signature_header: str, secret: str) -> bool:
    parts = dict(p.split("=", 1) for p in signature_header.split(","))
    timestamp = parts["t"]
    expected_sig = parts["v1"]

    signed_content = f"{timestamp}.{payload.decode()}"
    computed = hmac.new(
        secret.encode(), signed_content.encode(), hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(computed, expected_sig)
```

### Node.js Verification Example

```javascript
const crypto = require('crypto');

function verifyWebhook(payload, signatureHeader, secret) {
  const parts = Object.fromEntries(
    signatureHeader.split(',').map(p => p.split('=', 2))
  );
  const timestamp = parts.t;
  const expectedSig = parts.v1;

  const signedContent = `${timestamp}.${payload}`;
  const computed = crypto
    .createHmac('sha256', secret)
    .update(signedContent)
    .digest('hex');

  return crypto.timingSafeEqual(
    Buffer.from(computed),
    Buffer.from(expectedSig)
  );
}
```

## Delivery Specifications

| Property | Value |
|:---------|:------|
| Method | `HTTPS POST` |
| Content-Type | `application/json` |
| Max retries | 5 attempts |
| Retry interval | 30 seconds |
| Signature header | `X-Webhook-Signature` |

## Delivery States

```
pending ──▶ delivered
       └──▶ failed (after 5 attempts)
```

| Status | Description |
|:-------|:------------|
| `pending` | Awaiting delivery or retry |
| `delivered` | Successfully delivered (2xx response) |
| `failed` | All retry attempts exhausted |

## Webhook Event Schema

```python
WebhookEvent:
  id: str                  # Prefixed "evt_"
  event_type: str           # e.g., "transfer.confirmed"
  payload: str              # JSON string of event data
  delivery_status: str      # "pending", "delivered", "failed"
  retry_count: int          # Number of delivery attempts
  last_attempt_at: datetime # Timestamp of last attempt
  created_at: datetime
```

## Testing Webhooks

Send a test event to any URL:

```bash
curl -X POST http://localhost:8000/v1/webhooks/test \
  -H "X-API-Key: sk_test_..." \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://webhook.site/your-unique-id",
    "event_type": "test.ping"
  }'
```

The test endpoint sends a signed webhook immediately, bypassing the retry queue.

## Configuration

| Variable | Default | Description |
|:---------|:--------|:------------|
| `WEBHOOK_SECRET` | `whsec_test_secret` | HMAC-SHA256 signing secret |

> Use a strong, unique `WEBHOOK_SECRET` in production. The default value is for development only.
