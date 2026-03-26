from __future__ import annotations

import pytest

from app.core.security import sign_webhook_payload, verify_webhook_signature


def test_webhook_signing_roundtrip():
    payload = b'{"type": "test.ping", "data": {}}'
    secret = "whsec_test"
    sig = sign_webhook_payload(payload, secret)
    assert sig.startswith("t=")
    assert ",v1=" in sig
    assert verify_webhook_signature(payload, sig, secret)


def test_webhook_invalid_signature():
    payload = b'{"type": "test.ping"}'
    sig = sign_webhook_payload(payload, "correct_secret")
    assert not verify_webhook_signature(payload, sig, "wrong_secret")


def test_webhook_tampered_payload():
    payload = b'{"type": "test.ping"}'
    sig = sign_webhook_payload(payload, "secret")
    tampered = b'{"type": "test.tampered"}'
    assert not verify_webhook_signature(tampered, sig, "secret")


@pytest.mark.asyncio
async def test_webhook_events_listed(client):
    # Create a customer + wallet + deposit to generate events
    cus = await client.post("/v1/customers", json={"email": "webhooktest@example.com"})
    cid = cus.json()["id"]
    await client.post("/v1/wallets", json={"customer_id": cid})
    dep = await client.post("/v1/deposits", json={"customer_id": cid, "amount_usd": "10.00"})
    await client.post(f"/v1/deposits/{dep.json()['id']}/confirm")

    resp = await client.get("/v1/webhooks/events")
    assert resp.status_code == 200
    events = resp.json()
    event_types = [e["event_type"] for e in events]
    assert "deposit.pending" in event_types
    assert "deposit.completed" in event_types
