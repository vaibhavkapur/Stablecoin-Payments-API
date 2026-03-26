from __future__ import annotations
from typing import Optional
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PaymentIntent(Base):
    __tablename__ = "payment_intents"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    merchant_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("customers.id"), nullable=False
    )
    customer_id: Mapped[Optional[str]] = mapped_column(
        String(50), ForeignKey("customers.id")
    )
    amount: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="USDC")
    status: Mapped[str] = mapped_column(
        String(30), default="requires_payment_method"
    )
    recipient_address: Mapped[Optional[str]] = mapped_column(String(255))
    metadata_json: Mapped[Optional[str]] = mapped_column(String(2000))
    client_secret: Mapped[str] = mapped_column(String(100), nullable=False)
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
