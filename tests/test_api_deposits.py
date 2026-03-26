from __future__ import annotations

import pytest


async def _create_customer_with_wallet(client):
    cus = await client.post("/v1/customers", json={"email": f"dep{id(client)}@example.com"})
    cid = cus.json()["id"]
    await client.post("/v1/wallets", json={"customer_id": cid})
    return cid


@pytest.mark.asyncio
async def test_create_deposit(client):
    cid = await _create_customer_with_wallet(client)
    resp = await client.post("/v1/deposits", json={"customer_id": cid, "amount_usd": "100.00"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "pending"
    assert data["amount_usd"] == 100.0


@pytest.mark.asyncio
async def test_confirm_deposit(client):
    cid = await _create_customer_with_wallet(client)
    dep = await client.post("/v1/deposits", json={"customer_id": cid, "amount_usd": "50.00"})
    dep_id = dep.json()["id"]

    resp = await client.post(f"/v1/deposits/{dep_id}/confirm")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert data["completed_at"] is not None


@pytest.mark.asyncio
async def test_confirm_deposit_twice_fails(client):
    cid = await _create_customer_with_wallet(client)
    dep = await client.post("/v1/deposits", json={"customer_id": cid, "amount_usd": "25.00"})
    dep_id = dep.json()["id"]

    await client.post(f"/v1/deposits/{dep_id}/confirm")
    resp = await client.post(f"/v1/deposits/{dep_id}/confirm")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_deposit_credits_balance(client):
    cid = await _create_customer_with_wallet(client)
    dep = await client.post("/v1/deposits", json={"customer_id": cid, "amount_usd": "75.00"})
    await client.post(f"/v1/deposits/{dep.json()['id']}/confirm")

    resp = await client.get(f"/v1/balances/{cid}")
    assert resp.status_code == 200
    balances = resp.json()["balances"]
    usdc_available = next(b for b in balances if b["account_type"] == "customer_usdc_available")
    assert usdc_available["balance"] == 75.0
