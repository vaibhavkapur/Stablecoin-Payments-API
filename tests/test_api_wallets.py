from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_create_wallet(client):
    cus = await client.post("/v1/customers", json={"email": "waltest@example.com"})
    cid = cus.json()["id"]

    resp = await client.post("/v1/wallets", json={"customer_id": cid, "chain": "base-sepolia"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["id"].startswith("wal_")
    assert data["address"].startswith("0x")
    assert data["chain"] == "base-sepolia"


@pytest.mark.asyncio
async def test_create_wallet_customer_not_found(client):
    resp = await client.post("/v1/wallets", json={"customer_id": "cus_fake", "chain": "base-sepolia"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_wallet(client):
    cus = await client.post("/v1/customers", json={"email": "walget@example.com"})
    cid = cus.json()["id"]
    wal = await client.post("/v1/wallets", json={"customer_id": cid})
    wid = wal.json()["id"]

    resp = await client.get(f"/v1/wallets/{wid}")
    assert resp.status_code == 200
    assert resp.json()["id"] == wid
