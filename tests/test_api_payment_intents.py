from __future__ import annotations

import pytest


async def _funded_customer(client, email: str, amount: str = "100.00"):
    cus = await client.post("/v1/customers", json={"email": email})
    cid = cus.json()["id"]
    wal = await client.post("/v1/wallets", json={"customer_id": cid})
    wid = wal.json()["id"]
    dep = await client.post("/v1/deposits", json={"customer_id": cid, "amount_usd": amount})
    await client.post(f"/v1/deposits/{dep.json()['id']}/confirm")
    return cid, wid


@pytest.mark.asyncio
async def test_create_payment_intent(client):
    merchant_cid, _ = await _funded_customer(client, "pimerch@example.com", "0")
    resp = await client.post("/v1/payment_intents", json={
        "merchant_id": merchant_cid,
        "amount": "25.00",
        "currency": "USDC",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "requires_payment_method"
    assert data["client_secret"].startswith("pi_secret_")


@pytest.mark.asyncio
async def test_confirm_payment_intent(client):
    alice_cid, _ = await _funded_customer(client, "pialice@example.com", "100.00")
    merchant_cid, _ = await _funded_customer(client, "pimerch2@example.com", "0")

    pi = await client.post("/v1/payment_intents", json={
        "merchant_id": merchant_cid,
        "amount": "50.00",
        "currency": "USDC",
    })
    pi_id = pi.json()["id"]

    resp = await client.post(f"/v1/payment_intents/{pi_id}/confirm", json={
        "customer_id": alice_cid,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "succeeded"

    # Alice: 100 - 50 = 50
    bal = await client.get(f"/v1/balances/{alice_cid}")
    usdc = next(b for b in bal.json()["balances"] if b["account_type"] == "customer_usdc_available")
    assert usdc["balance"] == 50.0

    # Merchant: 50 - 2% fee = 49.0
    mbal = await client.get(f"/v1/balances/{merchant_cid}")
    merchant_usdc = next(b for b in mbal.json()["balances"] if b["account_type"] == "merchant_usdc")
    assert merchant_usdc["balance"] == 49.0


@pytest.mark.asyncio
async def test_payment_intent_insufficient_balance(client):
    alice_cid, _ = await _funded_customer(client, "pipoor@example.com", "5.00")
    merchant_cid, _ = await _funded_customer(client, "pimerch3@example.com", "0")

    pi = await client.post("/v1/payment_intents", json={
        "merchant_id": merchant_cid,
        "amount": "50.00",
        "currency": "USDC",
    })
    pi_id = pi.json()["id"]

    resp = await client.post(f"/v1/payment_intents/{pi_id}/confirm", json={
        "customer_id": alice_cid,
    })
    assert resp.status_code == 400
    assert "Insufficient" in resp.json()["detail"]
