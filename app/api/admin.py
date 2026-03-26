from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import generate_api_key, require_api_key
from app.services import reconciliation_service

router = APIRouter(prefix="/v1/admin", tags=["admin"])


@router.post("/api_keys")
async def create_api_key():
    """Generate a new API key (dev convenience endpoint)."""
    key = generate_api_key()
    return {"api_key": key}


@router.get("/reconciliation")
async def run_reconciliation(
    db: AsyncSession = Depends(get_db),
    _api_key: str = Depends(require_api_key),
):
    issues = await reconciliation_service.check_all_balances(db)
    return {"issues": issues, "status": "clean" if not issues else "mismatches_found"}


@router.get("/ledger_summary")
async def get_ledger_summary(
    db: AsyncSession = Depends(get_db),
    _api_key: str = Depends(require_api_key),
):
    summary = await reconciliation_service.get_ledger_summary(db)
    return {"accounts": summary}
