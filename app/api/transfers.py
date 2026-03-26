from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import require_api_key
from app.schemas.transfer import TransferCreate, TransferResponse
from app.services import transfer_service

router = APIRouter(prefix="/v1/transfers", tags=["transfers"])


@router.post("", response_model=TransferResponse, status_code=201)
async def create_transfer(
    body: TransferCreate,
    db: AsyncSession = Depends(get_db),
    _api_key: str = Depends(require_api_key),
):
    try:
        transfer = await transfer_service.create_transfer(
            db, body.wallet_id, body.recipient_address, body.amount_usdc, body.idempotency_key
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await db.commit()
    await db.refresh(transfer)
    return transfer


@router.post("/{transfer_id}/confirm", response_model=TransferResponse)
async def confirm_transfer(
    transfer_id: str,
    db: AsyncSession = Depends(get_db),
    _api_key: str = Depends(require_api_key),
):
    """Manually confirm a transfer (simulates on-chain confirmation)."""
    try:
        transfer = await transfer_service.confirm_transfer(db, transfer_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await db.commit()
    await db.refresh(transfer)
    return transfer


@router.post("/{transfer_id}/fail", response_model=TransferResponse)
async def fail_transfer(
    transfer_id: str,
    db: AsyncSession = Depends(get_db),
    _api_key: str = Depends(require_api_key),
):
    """Manually fail a transfer and release reserved funds."""
    try:
        transfer = await transfer_service.fail_transfer(
            db, transfer_id, "Manually marked as failed"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await db.commit()
    await db.refresh(transfer)
    return transfer


@router.get("/{transfer_id}", response_model=TransferResponse)
async def get_transfer(
    transfer_id: str,
    db: AsyncSession = Depends(get_db),
    _api_key: str = Depends(require_api_key),
):
    transfer = await transfer_service.get_transfer(db, transfer_id)
    if not transfer:
        raise HTTPException(status_code=404, detail="Transfer not found")
    return transfer
