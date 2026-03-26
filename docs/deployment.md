---
title: Deployment
layout: default
nav_order: 11
---

# Deployment
{: .fs-9 }

Run the full stack with Docker Compose, or deploy to production with PostgreSQL and Redis.
{: .fs-6 .fw-300 }

---

## Prerequisites

| Requirement | Version |
|:------------|:--------|
| PostgreSQL | 16+ |
| Redis | 7+ |
| Python | 3.12+ |
| Docker (optional) | Latest |

## Docker Compose (Recommended)

The fastest way to run the complete system:

```bash
docker-compose up --build
```

This starts four containers:

| Service | Port | Description |
|:--------|:-----|:------------|
| `api` | 8000 | FastAPI server with hot reload |
| `postgres` | 5432 | PostgreSQL 16-alpine |
| `redis` | 6379 | Redis 7-alpine |
| `worker` | — | Background workers (no exposed port) |

Health checks ensure services start in the correct order:
- PostgreSQL: `pg_isready -U stablecoin`
- Redis: `redis-cli ping`
- API and worker wait for both to be healthy before starting.

## Manual Deployment

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Set environment variables or create a `.env` file. See [Configuration](configuration) for all available settings.

```bash
export DATABASE_URL=postgresql+asyncpg://user:pass@db-host:5432/stablecoin_payments
export REDIS_URL=redis://redis-host:6379/0
export SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
export WEBHOOK_SECRET=$(python -c "import secrets; print('whsec_' + secrets.token_hex(24))")
```

### 3. Run Migrations

```bash
alembic upgrade head
```

### 4. Start Services

**API Server**:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

**Background Workers**:

```bash
python -m app.workers.run
```

## Production Architecture

```
                    ┌─────────────────┐
                    │  Load Balancer   │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
        ┌─────┴─────┐ ┌─────┴─────┐ ┌─────┴─────┐
        │  API (1)   │ │  API (2)   │ │  API (N)   │
        └─────┬─────┘ └─────┬─────┘ └─────┬─────┘
              │              │              │
              └──────────────┼──────────────┘
                             │
              ┌──────────────┼──────────────┐
              │                             │
       ┌──────┴──────┐              ┌──────┴──────┐
       │  PostgreSQL  │              │    Redis     │
       │  (Primary)   │              │  (Cluster)   │
       └─────────────┘              └─────────────┘
                             │
                      ┌──────┴──────┐
                      │   Worker    │
                      │  Instance   │
                      └─────────────┘
```

## Scaling Guidelines

### API Service

API instances are stateless and scale horizontally behind a load balancer. Each instance shares the same database and Redis.

```bash
# Run with multiple Uvicorn workers
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Background Workers

| Worker | Scaling | Notes |
|:-------|:--------|:------|
| Transfer Status | Single instance | Use distributed locks for multi-instance |
| Webhook Retry | Scalable | Idempotent delivery tracking prevents duplicates |
| Reconciliation | Single instance | Read-only, no concurrency risk |

### Database

- Use connection pooling (PgBouncer) for high-throughput scenarios
- Enable `statement_timeout` to prevent long-running queries
- Set up read replicas for balance queries and reconciliation

## Infrastructure Setup

### PostgreSQL

```bash
# Run migrations before first startup
alembic upgrade head
```

Recommended PostgreSQL configuration:
- Enable WAL archiving for point-in-time recovery
- Set `max_connections` appropriate to your connection pool size
- Enable `log_min_duration_statement` for slow query monitoring

### Redis

- Enable persistence (RDB + AOF) to prevent job loss on restart
- Configure `maxmemory-policy` as `noeviction` for task queue reliability
- Monitor memory usage — webhook events and transfer polling data accumulate

## Security Checklist

Before going live:

- [ ] Set strong `SECRET_KEY` and `WEBHOOK_SECRET` values
- [ ] Store all secrets in a secrets manager (AWS Secrets Manager, HashiCorp Vault)
- [ ] Enable TLS on all connections (database, Redis, API)
- [ ] Place admin endpoints (`/v1/admin/*`) behind a VPN
- [ ] Set `--workers` > 1 for the API server
- [ ] Configure database connection pooling
- [ ] Enable Redis persistence
- [ ] Set up monitoring and alerting

## Monitoring

### Key Metrics

| Metric | Source | Alert Threshold |
|:-------|:-------|:----------------|
| Payment success rate | API logs | < 95% |
| Transfer confirmation time | Worker logs | > 60 seconds |
| Webhook delivery rate | Webhook events table | < 90% |
| Negative account balances | Reconciliation worker | Any occurrence |
| API response latency (p95) | Load balancer | > 500ms |

### Health Check

The `/health` endpoint returns `200 OK` when the API is operational:

```bash
curl http://localhost:8000/health
# {"status": "ok"}
```

Use this for load balancer health checks and uptime monitoring.

### Recommended Tools

- **Metrics**: Datadog, Prometheus + Grafana
- **Logging**: ELK Stack, Loki
- **Alerting**: PagerDuty, OpsGenie
- **APM**: Datadog APM, New Relic

## Dockerfile

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

For production, remove `--reload` and set appropriate `--workers` count based on available CPU cores.
