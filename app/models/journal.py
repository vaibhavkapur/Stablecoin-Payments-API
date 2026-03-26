from __future__ import annotations
from typing import Optional
from datetime import datetime

from sqlalchemy import DateTime, Numeric, String, func, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Journal(Base):
    __tablename__ = "journals"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    reference_type: Mapped[str] = mapped_column(String(50), nullable=False)
    reference_id: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500))
    idempotency_key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    entries = relationship("LedgerEntry", back_populates="journal", lazy="selectin")


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    journal_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("journals.id"), nullable=False
    )
    account_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("payment_accounts.id"), nullable=False
    )
    direction: Mapped[str] = mapped_column(String(10), nullable=False)  # "debit" or "credit"
    amount: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="USDC")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    journal = relationship("Journal", back_populates="entries")
    account = relationship("PaymentAccount", back_populates="entries")
