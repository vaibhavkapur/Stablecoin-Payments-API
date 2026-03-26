from __future__ import annotations
import hashlib
import hmac
import secrets
import time

from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader

from app.core.config import settings

api_key_header = APIKeyHeader(name=settings.API_KEY_HEADER, auto_error=False)

# In production, API keys would be stored hashed in the database.
# For the demo, we use a simple in-memory set.
VALID_API_KEYS: set[str] = set()


def generate_api_key() -> str:
    key = f"sk_test_{secrets.token_hex(24)}"
    VALID_API_KEYS.add(key)
    return key


def generate_idempotency_key() -> str:
    return secrets.token_hex(16)


async def require_api_key(key: str | None = Security(api_key_header)) -> str:
    if not VALID_API_KEYS:
        # Allow all requests when no keys have been created (dev mode)
        return "dev"
    if key is None or key not in VALID_API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return key


def sign_webhook_payload(payload: bytes, secret: str | None = None) -> str:
    secret = secret or settings.WEBHOOK_SECRET
    timestamp = str(int(time.time()))
    signed_content = f"{timestamp}.{payload.decode()}"
    signature = hmac.new(
        secret.encode(), signed_content.encode(), hashlib.sha256
    ).hexdigest()
    return f"t={timestamp},v1={signature}"


def verify_webhook_signature(
    payload: bytes, signature_header: str, secret: str | None = None
) -> bool:
    secret = secret or settings.WEBHOOK_SECRET
    try:
        parts = dict(p.split("=", 1) for p in signature_header.split(","))
        timestamp = parts["t"]
        expected_sig = parts["v1"]
    except (KeyError, ValueError):
        return False

    signed_content = f"{timestamp}.{payload.decode()}"
    computed = hmac.new(
        secret.encode(), signed_content.encode(), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(computed, expected_sig)
