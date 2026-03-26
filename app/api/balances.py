from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import require_api_key
from app.models.customer import Customer
from app.schemas.balance import CustomerBalanceResponse
from app.services import ledger_service

router = APIRouter(prefix="/v1/balances", tags=["balances"])


@router.get("/{customer_id}", response_model=CustomerBalanceResponse)
async def get_customer_balance(
    customer_id: str,
    db: AsyncSession = Depends(get_db),
    _api_key: str = Depends(require_api_key),
):
    result = await db.execute(
        select(Customer).where(Customer.id == customer_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Customer not found")

    balances = await ledger_service.get_customer_balances(db, customer_id)
    return CustomerBalanceResponse(customer_id=customer_id, balances=balances)
