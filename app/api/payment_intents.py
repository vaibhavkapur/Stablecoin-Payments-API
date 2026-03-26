from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import require_api_key
from app.schemas.payment_intent import (
    PaymentIntentConfirm,
    PaymentIntentCreate,
    PaymentIntentResponse,
)
from app.services import payment_service

router = APIRouter(prefix="/v1/payment_intents", tags=["payment_intents"])


@router.post("", response_model=PaymentIntentResponse, status_code=201)
async def create_payment_intent(
    body: PaymentIntentCreate,
    db: AsyncSession = Depends(get_db),
    _api_key: str = Depends(require_api_key),
):
    pi = await payment_service.create_payment_intent(
        db,
        merchant_id=body.merchant_id,
        amount=body.amount,
        currency=body.currency,
        customer_id=body.customer_id,
        metadata=body.metadata,
        idempotency_key=body.idempotency_key,
    )
    await db.commit()
    await db.refresh(pi)
    return pi


@router.post("/{payment_intent_id}/confirm", response_model=PaymentIntentResponse)
async def confirm_payment_intent(
    payment_intent_id: str,
    body: PaymentIntentConfirm,
    db: AsyncSession = Depends(get_db),
    _api_key: str = Depends(require_api_key),
):
    try:
        pi = await payment_service.confirm_payment_intent(
            db, payment_intent_id, body.customer_id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    await db.commit()
    await db.refresh(pi)
    return pi


@router.get("/{payment_intent_id}", response_model=PaymentIntentResponse)
async def get_payment_intent(
    payment_intent_id: str,
    db: AsyncSession = Depends(get_db),
    _api_key: str = Depends(require_api_key),
):
    pi = await payment_service.get_payment_intent(db, payment_intent_id)
    if not pi:
        raise HTTPException(status_code=404, detail="PaymentIntent not found")
    return pi
