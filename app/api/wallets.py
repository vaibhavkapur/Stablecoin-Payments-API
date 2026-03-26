from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import require_api_key
from app.models.customer import Customer
from app.schemas.wallet import WalletCreate, WalletResponse
from app.services import wallet_service

router = APIRouter(prefix="/v1/wallets", tags=["wallets"])


@router.post("", response_model=WalletResponse, status_code=201)
async def create_wallet(
    body: WalletCreate,
    db: AsyncSession = Depends(get_db),
    _api_key: str = Depends(require_api_key),
):
    # Verify customer exists
    result = await db.execute(
        select(Customer).where(Customer.id == body.customer_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Customer not found")

    wallet = await wallet_service.create_wallet(db, body.customer_id, body.chain)
    await db.commit()
    await db.refresh(wallet)
    return wallet


@router.get("/{wallet_id}", response_model=WalletResponse)
async def get_wallet(
    wallet_id: str,
    db: AsyncSession = Depends(get_db),
    _api_key: str = Depends(require_api_key),
):
    wallet = await wallet_service.get_wallet(db, wallet_id)
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")
    return wallet


@router.get("", response_model=list[WalletResponse])
async def list_wallets_by_customer(
    customer_id: str,
    db: AsyncSession = Depends(get_db),
    _api_key: str = Depends(require_api_key),
):
    return await wallet_service.get_wallets_by_customer(db, customer_id)
