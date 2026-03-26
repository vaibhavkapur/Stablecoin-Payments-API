from __future__ import annotations

import pytest


async def _funded_customer(client, email: str, amount: str = "100.00"):
    """Create a customer with a wallet and funded USDC balance."""
    cus = await client.post("/v1/customers", json={"email": email})
    cid = cus.json()["id"]
    wal = await client.post("/v1/wallets", json={"customer_id": cid})
    wid = wal.json()["id"]
    dep = await client.post("/v1/deposits", json={"customer_id": cid, "amount_usd": amount})
    await client.post(f"/v1/deposits/{dep.json()['id']}/confirm")
    return cid, wid


@pytest.mark.asyncio
async def test_create_transfer(client):
    _, wid = await _funded_customer(client, "tr1@example.com")
    resp = await client.post("/v1/transfers", json={
        "wallet_id": wid,
        "recipient_address": "0xabc123",
        "amount_usdc": "20.00",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "submitted"
    assert data["tx_hash"].startswith("0x")


@pytest.mark.asyncio
async def test_transfer_insufficient_balance(client):
    _, wid = await _funded_customer(client, "tr2@example.com", "10.00")
    resp = await client.post("/v1/transfers", json={
        "wallet_id": wid,
        "recipient_address": "0xabc123",
        "amount_usdc": "50.00",
    })
    assert resp.status_code == 400
    assert "Insufficient" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_confirm_transfer(client):
    cid, wid = await _funded_customer(client, "tr3@example.com")
    tr = await client.post("/v1/transfers", json={
        "wallet_id": wid,
        "recipient_address": "0xabc123",
        "amount_usdc": "20.00",
    })
    tr_id = tr.json()["id"]

    resp = await client.post(f"/v1/transfers/{tr_id}/confirm")
    assert resp.status_code == 200
    assert resp.json()["status"] == "confirmed"

    # Check balance: 100 - 20 = 80
    bal = await client.get(f"/v1/balances/{cid}")
    usdc = next(b for b in bal.json()["balances"] if b["account_type"] == "customer_usdc_available")
    assert usdc["balance"] == 80.0


@pytest.mark.asyncio
async def test_fail_transfer_releases_funds(client):
    cid, wid = await _funded_customer(client, "tr4@example.com")
    tr = await client.post("/v1/transfers", json={
        "wallet_id": wid,
        "recipient_address": "0xabc123",
        "amount_usdc": "30.00",
    })
    tr_id = tr.json()["id"]

    resp = await client.post(f"/v1/transfers/{tr_id}/fail")
    assert resp.status_code == 200
    assert resp.json()["status"] == "failed"

    # Balance should be restored: 100 (funds released back)
    bal = await client.get(f"/v1/balances/{cid}")
    usdc = next(b for b in bal.json()["balances"] if b["account_type"] == "customer_usdc_available")
    assert usdc["balance"] == 100.0
