from __future__ import annotations
import secrets

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.id_gen import generate_prefixed_id
from app.models.wallet import Wallet
from app.services import ledger_service


def generate_testnet_address() -> str:
    """Generate a simulated testnet wallet address."""
    return "0x" + secrets.token_hex(20)


async def create_wallet(
    db: AsyncSession, customer_id: str, chain: str = "base-sepolia"
) -> Wallet:
    address = generate_testnet_address()
    wallet = Wallet(
        id=generate_prefixed_id("wal"),
        customer_id=customer_id,
        provider="local",
        chain=chain,
        address=address,
    )
    db.add(wallet)

    # Create ledger accounts for this customer if they don't exist yet
    await ledger_service.get_or_create_account(
        db, customer_id, "customer_usdc_available", "USDC"
    )
    await ledger_service.get_or_create_account(
        db, customer_id, "customer_usdc_reserved", "USDC"
    )
    await ledger_service.get_or_create_account(
        db, customer_id, "customer_usd", "USD"
    )

    await db.flush()
    return wallet


async def get_wallet(db: AsyncSession, wallet_id: str) -> Wallet | None:
    result = await db.execute(select(Wallet).where(Wallet.id == wallet_id))
    return result.scalar_one_or_none()


async def get_wallets_by_customer(
    db: AsyncSession, customer_id: str
) -> list[Wallet]:
    result = await db.execute(
        select(Wallet).where(Wallet.customer_id == customer_id)
    )
    return list(result.scalars().all())
