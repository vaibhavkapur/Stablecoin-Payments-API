from __future__ import annotations
from typing import Optional
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class PaymentAccount(Base):
    __tablename__ = "payment_accounts"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    customer_id: Mapped[Optional[str]] = mapped_column(
        String(50), ForeignKey("customers.id")
    )
    type: Mapped[str] = mapped_column(String(100), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="USDC")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    customer = relationship("Customer", back_populates="accounts")
    entries = relationship("LedgerEntry", back_populates="account", lazy="selectin")
