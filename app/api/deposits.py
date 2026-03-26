from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import require_api_key
from app.schemas.deposit import DepositCreate, DepositResponse
from app.services import deposit_service

router = APIRouter(prefix="/v1/deposits", tags=["deposits"])


@router.post("", response_model=DepositResponse, status_code=201)
async def create_deposit(
    body: DepositCreate,
    db: AsyncSession = Depends(get_db),
    _api_key: str = Depends(require_api_key),
):
    deposit = await deposit_service.create_deposit(
        db, body.customer_id, body.amount_usd, body.idempotency_key
    )
    await db.commit()
    await db.refresh(deposit)
    return deposit


@router.post("/{deposit_id}/confirm", response_model=DepositResponse)
async def confirm_deposit(
    deposit_id: str,
    db: AsyncSession = Depends(get_db),
    _api_key: str = Depends(require_api_key),
):
    try:
        deposit = await deposit_service.confirm_deposit(db, deposit_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await db.commit()
    await db.refresh(deposit)
    return deposit


@router.get("/{deposit_id}", response_model=DepositResponse)
async def get_deposit(
    deposit_id: str,
    db: AsyncSession = Depends(get_db),
    _api_key: str = Depends(require_api_key),
):
    deposit = await deposit_service.get_deposit(db, deposit_id)
    if not deposit:
        raise HTTPException(status_code=404, detail="Deposit not found")
    return deposit
