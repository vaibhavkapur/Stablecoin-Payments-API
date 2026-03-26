from __future__ import annotations
from typing import Optional
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Wallet(Base):
    __tablename__ = "wallets"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    customer_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("customers.id"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(50), default="local")
    chain: Mapped[str] = mapped_column(String(50), default="base-sepolia")
    address: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    wallet_provider_id: Mapped[Optional[str]] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    customer = relationship("Customer", back_populates="wallets")
