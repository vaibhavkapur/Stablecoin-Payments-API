from __future__ import annotations
from typing import Optional
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Transfer(Base):
    __tablename__ = "transfers"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    sender_wallet_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("wallets.id"), nullable=False
    )
    recipient_address: Mapped[str] = mapped_column(String(255), nullable=False)
    amount_usdc: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="created")
    chain: Mapped[str] = mapped_column(String(50), default="base-sepolia")
    tx_hash: Mapped[Optional[str]] = mapped_column(String(255))
    block_number: Mapped[Optional[int]] = mapped_column()
    confirmations: Mapped[Optional[int]] = mapped_column()
    gas_used: Mapped[Optional[str]] = mapped_column(String(50))
    effective_fee: Mapped[Optional[str]] = mapped_column(String(50))
    failure_reason: Mapped[Optional[str]] = mapped_column(String(500))
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
