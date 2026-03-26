from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_create_customer(client):
    resp = await client.post("/v1/customers", json={"email": "test@example.com"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["id"].startswith("cus_")
    assert data["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_create_customer_duplicate_email(client):
    await client.post("/v1/customers", json={"email": "dup@example.com"})
    resp = await client.post("/v1/customers", json={"email": "dup@example.com"})
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_get_customer(client):
    create = await client.post("/v1/customers", json={"email": "get@example.com"})
    cid = create.json()["id"]
    resp = await client.get(f"/v1/customers/{cid}")
    assert resp.status_code == 200
    assert resp.json()["id"] == cid


@pytest.mark.asyncio
async def test_get_customer_not_found(client):
    resp = await client.get("/v1/customers/cus_nonexistent")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_customers(client):
    await client.post("/v1/customers", json={"email": "list1@example.com"})
    await client.post("/v1/customers", json={"email": "list2@example.com"})
    resp = await client.get("/v1/customers")
    assert resp.status_code == 200
    assert len(resp.json()) >= 2
