---
title: Configuration
layout: default
nav_order: 10
---

# Configuration

[Documentation home](index.md)

Environment variables and settings for database, Redis, authentication, and platform behavior.

---

## Overview

Configuration is managed through environment variables, loaded by Pydantic Settings (`app/core/config.py`). Variables can be set in a `.env` file at the project root or passed directly as environment variables.

## Database

| Variable | Required | Default | Description |
|:---------|:---------|:--------|:------------|
| `DATABASE_URL` | Yes | `sqlite+aiosqlite:///./stablecoin_payments.db` | SQLAlchemy async database URL |

**PostgreSQL (production)**:
```bash
DATABASE_URL=postgresql+asyncpg://stablecoin:password@localhost:5432/stablecoin_payments
```

**SQLite (development)**:
```bash
DATABASE_URL=sqlite+aiosqlite:///./stablecoin_payments.db
```

## Redis

| Variable | Required | Default | Description |
|:---------|:---------|:--------|:------------|
| `REDIS_URL` | No | `redis://localhost:6379/0` | Redis connection URL |

Redis is used for caching and as a message broker. Required for the Docker Compose deployment but optional for local SQLite development.

## Authentication

| Variable | Required | Default | Description |
|:---------|:---------|:--------|:------------|
| `SECRET_KEY` | Yes | `change-me-in-production` | Application secret key |
| `API_KEY_HEADER` | No | `X-API-Key` | HTTP header name for API keys |

> Always set a strong, unique `SECRET_KEY` in production. Never use the default value.

## Webhooks

| Variable | Required | Default | Description |
|:---------|:---------|:--------|:------------|
| `WEBHOOK_SECRET` | Yes | `whsec_test_secret` | HMAC-SHA256 signing secret for outbound webhooks |

## Platform

| Variable | Required | Default | Description |
|:---------|:---------|:--------|:------------|
| `PLATFORM_FEE_BPS` | No | `200` | Platform fee in basis points (200 = 2%) |

The platform fee is deducted from merchant payments during Payment Intent confirmation.

## Complete `.env` Example

```bash
# Database
DATABASE_URL=sqlite+aiosqlite:///./stablecoin_payments.db

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=change-me-in-production-use-a-real-secret
API_KEY_HEADER=X-API-Key
WEBHOOK_SECRET=whsec_test_secret

# Platform
PLATFORM_FEE_BPS=200
```

## Docker Compose Environment

When running with Docker Compose, the services are configured with:

```yaml
services:
  api:
    environment:
      DATABASE_URL: postgresql+asyncpg://stablecoin:stablecoin@postgres:5432/stablecoin_payments
      REDIS_URL: redis://redis:6379/0

  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: stablecoin
      POSTGRES_PASSWORD: stablecoin
      POSTGRES_DB: stablecoin_payments
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

## Pydantic Settings

Settings are loaded through Pydantic's `BaseSettings`, which automatically reads from environment variables and `.env` files:

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./stablecoin_payments.db"
    REDIS_URL: str = "redis://localhost:6379/0"
    SECRET_KEY: str = "change-me-in-production"
    API_KEY_HEADER: str = "X-API-Key"
    WEBHOOK_SECRET: str = "whsec_test_secret"
    PLATFORM_FEE_BPS: int = 200

settings = Settings()
```

> Environment variables take precedence over `.env` file values, which take precedence over defaults.

## Security Checklist

Before deploying to production:

- [ ] Set a strong, random `SECRET_KEY` (at least 32 characters)
- [ ] Set a unique `WEBHOOK_SECRET` (at least 32 characters)
- [ ] Use PostgreSQL (not SQLite) as the database
- [ ] Store secrets in a secrets manager (AWS Secrets Manager, Vault, etc.)
- [ ] Never commit `.env` files with real credentials to version control
- [ ] Enable TLS for all database and Redis connections
- [ ] Place admin endpoints behind a VPN or internal network
