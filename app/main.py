from __future__ import annotations
import asyncio
import logging
import pathlib
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import admin, balances, customers, deposits, payment_intents, transfers, wallets, webhooks
from app.core.database import Base, engine
from app.workers.transfer_status_worker import poll_pending_transfers
from app.workers.webhook_retry_worker import retry_pending_webhooks
from app.workers.reconciliation_worker import run_reconciliation

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup (dev convenience — use Alembic in production)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created")

    # Start background workers
    worker_tasks = [
        asyncio.create_task(poll_pending_transfers()),
        asyncio.create_task(retry_pending_webhooks()),
        asyncio.create_task(run_reconciliation()),
    ]
    logger.info("Background workers started")

    yield

    # Shutdown workers
    for task in worker_tasks:
        task.cancel()
    logger.info("Background workers stopped")


app = FastAPI(
    title="Stablecoin Payments API",
    description="A Stripe-like API for stablecoin payments on Base Sepolia",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(customers.router)
app.include_router(wallets.router)
app.include_router(deposits.router)
app.include_router(transfers.router)
app.include_router(payment_intents.router)
app.include_router(balances.router)
app.include_router(webhooks.router)
app.include_router(admin.router)


STATIC_DIR = pathlib.Path(__file__).parent / "static"


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/dashboard")
async def dashboard():
    return FileResponse(STATIC_DIR / "dashboard.html")


@app.get("/checkout")
async def checkout():
    return FileResponse(STATIC_DIR / "checkout.html")
