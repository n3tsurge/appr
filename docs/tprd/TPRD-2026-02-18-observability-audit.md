# TPRD-2026-02-18-observability-audit

## 1. DOCUMENT METADATA

```
Document ID:    TPRD-2026-02-18-observability-audit
Version:        1.0
Status:         Draft
Feature Name:   Observability & Audit Logging
Parent TPRD:    TPRD-2026-02-18-platform-foundation
```

## 2. EXECUTIVE SUMMARY

- **Business Objective**: Provide comprehensive observability (logging, metrics, traces) and a tamper-resistant audit trail for all data mutations, supporting operational troubleshooting, performance monitoring, ISO 27001 compliance, and security investigations.
- **Technical Scope**: Structured JSON logging via structlog, distributed tracing via OpenTelemetry (exported to New Relic), application metrics, and an audit log service that records every create/update/delete operation with before/after snapshots.
- **Success Criteria**: All API requests emit structured logs with correlation IDs. Every mutation is recorded in the audit log. Traces are visible in New Relic within 5 seconds. Audit log entries are immutable.
- **Complexity Estimate**: M — Cross-cutting concern touching all API endpoints, middleware, and services.

## 3. SCOPE DEFINITION

### 3.1 In Scope
- Structured JSON logging (structlog)
- Request/response logging middleware (method, path, status, duration, user_id, tenant_id)
- OpenTelemetry instrumentation:
  - Automatic HTTP span creation (FastAPI)
  - Database query spans (SQLAlchemy)
  - Redis operation spans
  - Celery task spans
  - Custom spans for business logic
- Metrics:
  - Request count by endpoint, method, status
  - Request duration histogram (p50, p95, p99)
  - Active database connections
  - Cache hit/miss ratio
  - Celery task queue depth
  - Celery task duration
- New Relic export via OTLP
- Audit log service:
  - Records all create, update, delete operations
  - Captures actor (user_id), tenant_id, entity_type, entity_id, action, timestamp
  - Captures `before` and `after` snapshots (JSONB diff)
  - Immutable — no UPDATE or DELETE on audit_log table
- Audit log API endpoint (Admin read-only)
- Health check endpoints with dependency status

### 3.2 Out of Scope
- Log aggregation infrastructure (ELK/Splunk — uses New Relic)
- Alerting rules configuration (configured in New Relic UI)
- Real-time dashboards (New Relic dashboards)
- Frontend error tracking (Sentry — future)
- SIEM integration

### 3.3 Assumptions
- New Relic OTLP endpoint and license key are available
- Log volume is manageable at < 10,000 requests/day initially
- Audit log retention: 2 years (ISO 27001 requirement)

### 3.4 Dependencies
- TPRD-2026-02-18-platform-foundation (app structure, middleware stack)
- TPRD-2026-02-18-core-data-models (audit_logs table)

## 4. TECHNICAL SPECIFICATIONS

### 4.1 Technology Stack Declaration
Per `.github/technology-stack.yml`:
- **structlog** for structured JSON logging
- **OpenTelemetry SDK** for Python:
  - `opentelemetry-api`
  - `opentelemetry-sdk`
  - `opentelemetry-instrumentation-fastapi`
  - `opentelemetry-instrumentation-sqlalchemy`
  - `opentelemetry-instrumentation-redis`
  - `opentelemetry-instrumentation-celery`
  - `opentelemetry-exporter-otlp`
- **New Relic** as the observability backend (via OTLP)

### 4.2 Structured Logging Configuration

```python
# backend/app/core/logging.py
import structlog
import logging
import sys

def configure_logging(log_level: str = "INFO", json_output: bool = True):
    """Configure structlog for structured JSON logging."""

    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    if json_output:
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[*shared_processors, renderer],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, log_level.upper()))
```

**Log output sample:**
```json
{
  "timestamp": "2026-02-18T12:00:00.123Z",
  "level": "info",
  "logger": "app.api.v1.services",
  "event": "service_created",
  "request_id": "abc-123-def",
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "tenant_id": "660e8400-e29b-41d4-a716-446655440000",
  "entity_type": "service",
  "entity_id": "770e8400-e29b-41d4-a716-446655440000",
  "entity_name": "Customer API",
  "duration_ms": 45
}
```

### 4.3 Request Logging Middleware

```python
# backend/app/middleware/logging_middleware.py
import time
import uuid
import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger()

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        start_time = time.perf_counter()

        # Bind context for all log entries in this request
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else None,
        )

        try:
            response = await call_next(request)
            duration_ms = (time.perf_counter() - start_time) * 1000

            logger.info(
                "request_completed",
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2),
            )

            response.headers["X-Request-ID"] = request_id
            return response

        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                "request_failed",
                error=str(exc),
                duration_ms=round(duration_ms, 2),
            )
            raise
```

### 4.4 OpenTelemetry Configuration

```python
# backend/app/core/telemetry.py
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.celery import CeleryInstrumentor

def configure_telemetry(app, engine, service_name: str = "app-inventory"):
    """Configure OpenTelemetry with New Relic OTLP exporter."""

    resource = Resource.create({
        "service.name": service_name,
        "service.version": "1.0.0",
        "deployment.environment": settings.ENVIRONMENT,
    })

    provider = TracerProvider(resource=resource)

    # Export to New Relic via OTLP
    otlp_exporter = OTLPSpanExporter(
        endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
        headers={"api-key": settings.NEW_RELIC_LICENSE_KEY},
    )
    provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

    trace.set_tracer_provider(provider)

    # Instrument frameworks
    FastAPIInstrumentor.instrument_app(app)
    SQLAlchemyInstrumentor().instrument(engine=engine)
    RedisInstrumentor().instrument()
    CeleryInstrumentor().instrument()
```

### 4.5 Audit Log Service

```python
# backend/app/services/audit_service.py
import structlog
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit import AuditLog

logger = structlog.get_logger()

class AuditService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def log(
        self,
        action: str,           # "create" | "update" | "delete"
        entity_type: str,      # "service" | "component" | etc.
        entity_id: UUID,
        actor_id: UUID,
        tenant_id: UUID,
        before: dict | None = None,  # Previous state (for update/delete)
        after: dict | None = None,   # New state (for create/update)
        metadata: dict | None = None,
    ) -> AuditLog:
        """Record an audit log entry. This is append-only — never update or delete."""

        # Compute diff for updates
        changes = None
        if action == "update" and before and after:
            changes = {
                k: {"old": before.get(k), "new": after[k]}
                for k in after
                if before.get(k) != after[k]
            }

        entry = AuditLog(
            tenant_id=tenant_id,
            actor_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            before_state=before,
            after_state=after,
            changes=changes,
            metadata=metadata,
            created_at=datetime.now(timezone.utc),
        )

        self.session.add(entry)
        # Flush to get ID but don't commit (caller's transaction)
        await self.session.flush()

        logger.info(
            "audit_logged",
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id),
            actor_id=str(actor_id),
        )

        return entry
```

### 4.6 Audit Log Data Model (supplement to TPRD-002)

The `audit_logs` table is defined in TPRD-002. Key fields:
- `id` UUID PK
- `tenant_id` UUID NOT NULL
- `actor_id` UUID NOT NULL (FK to users)
- `action` VARCHAR(20) NOT NULL (create, update, delete)
- `entity_type` VARCHAR(50) NOT NULL
- `entity_id` UUID NOT NULL
- `before_state` JSONB (nullable — null for create)
- `after_state` JSONB (nullable — null for delete)
- `changes` JSONB (nullable — computed diff for updates)
- `metadata` JSONB (nullable — extra context like IP, request_id)
- `created_at` TIMESTAMPTZ NOT NULL

**CRITICAL**: This table MUST have a database-level trigger or policy that prevents UPDATE and DELETE operations:
```sql
CREATE RULE audit_logs_no_update AS ON UPDATE TO audit_logs DO INSTEAD NOTHING;
CREATE RULE audit_logs_no_delete AS ON DELETE TO audit_logs DO INSTEAD NOTHING;
```

### 4.7 API Specifications

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| GET | /api/v1/audit-logs | ✅ | Admin | List audit log entries (paginated, filterable) |
| GET | /api/v1/audit-logs/{id} | ✅ | Admin | Get audit log entry detail |

**Query Parameters for audit log list:**
- `entity_type`: Filter by entity type
- `entity_id`: Filter by specific entity
- `action`: Filter by action (create, update, delete)
- `actor_id`: Filter by user
- `from_date`: Start date filter (ISO 8601)
- `to_date`: End date filter (ISO 8601)
- `page`, `per_page`: Pagination

**Response:**
```json
{
  "data": [
    {
      "id": "uuid",
      "action": "update",
      "entity_type": "service",
      "entity_id": "uuid",
      "actor_id": "uuid",
      "actor_name": "Alice Chen",
      "changes": {
        "operational_status": {
          "old": "operational",
          "new": "degraded"
        }
      },
      "metadata": {
        "request_id": "abc-123",
        "ip_address": "10.0.1.100"
      },
      "created_at": "2026-02-18T12:00:00Z"
    }
  ],
  "meta": { "total": 1250, "page": 1, "per_page": 25, "total_pages": 50 }
}
```

### 4.8 Integration Points

Every service layer write operation MUST call `AuditService.log()`:

```python
# Example: ServiceService.update()
async def update(self, id: UUID, data: ServiceUpdate, actor: User) -> Service:
    service = await self.repository.get(id)
    before = service.to_dict()  # Snapshot before

    # Apply updates
    for field, value in data.dict(exclude_unset=True).items():
        setattr(service, field, value)

    await self.session.flush()
    after = service.to_dict()  # Snapshot after

    # Audit log
    await self.audit.log(
        action="update",
        entity_type="service",
        entity_id=id,
        actor_id=actor.id,
        tenant_id=actor.tenant_id,
        before=before,
        after=after,
        metadata={"request_id": get_request_id()},
    )

    return service
```

### 4.9 Health Check Enhancement

The `/health` and `/ready` endpoints (from TPRD-001) MUST report dependency status:

```json
GET /api/v1/health
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime_seconds": 86400,
  "checks": {
    "database": { "status": "healthy", "latency_ms": 2 },
    "redis": { "status": "healthy", "latency_ms": 1 },
    "celery": { "status": "healthy", "active_workers": 2 }
  }
}
```

## 5. SECURITY REQUIREMENTS

- Audit logs are immutable — no UPDATE or DELETE at database level
- Audit log access restricted to Admin role
- Audit logs MUST NOT contain passwords, tokens, or secrets
- `before_state` and `after_state` MUST exclude sensitive fields (password_hash, tokens)
- New Relic API key stored in environment variable, never in code
- Log output MUST NOT contain PII (email addresses are acceptable per data classification, but passwords/tokens are not)

## 6. TESTING REQUIREMENTS

### 6.1 Unit Tests
- AuditService.log(): verify entry created with correct fields
- Change diff computation: verify correct diff for various update scenarios
- Structured logging: verify JSON output format
- Health check: verify status aggregation logic

### 6.2 Integration Tests
- Create entity → verify audit log entry exists with action="create"
- Update entity → verify audit log entry with before/after diff
- Delete entity → verify audit log entry with before state
- Audit log API: verify pagination, filtering by entity_type, date range
- Verify immutability: attempt UPDATE/DELETE on audit_logs → fails
- Verify OpenTelemetry spans created for API requests

### 6.3 Security Tests
- Verify non-admin users cannot access /api/v1/audit-logs
- Verify audit log entries do not contain password_hash fields

## 7. NON-FUNCTIONAL REQUIREMENTS

- **Performance**: Audit logging adds < 5ms per write operation
- **Storage**: Audit log retention: 2 years. Partition by month for performance.
- **Reliability**: Audit log writes MUST be in the same transaction as the data mutation (atomic)
- **Observability**: OpenTelemetry traces visible in New Relic within 5 seconds. Log throughput metrics exported.

## 8. MIGRATION & DEPLOYMENT

- Alembic migration: Create audit_log immutability rules (if not in TPRD-002 migration)
- Alembic migration: Add `notification_preferences`, `notification_channels`, `notification_log` tables (if not separate TPRD-011 migration)
- Create monthly partitions for audit_logs table (PostgreSQL table partitioning):
  ```sql
  CREATE TABLE audit_logs (
    ...
  ) PARTITION BY RANGE (created_at);

  CREATE TABLE audit_logs_2026_01 PARTITION OF audit_logs
    FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');
  ```
- Cron job or Celery beat task to create future partitions
- Environment variables:
  - `OTEL_EXPORTER_OTLP_ENDPOINT`
  - `NEW_RELIC_LICENSE_KEY`
  - `LOG_LEVEL` (default: INFO)
  - `LOG_FORMAT` (json | console)

## 9. IMPLEMENTATION GUIDANCE FOR CODING AGENTS

### Implementation Order
1. Configure structlog (`core/logging.py`)
2. Create request logging middleware
3. Configure OpenTelemetry (`core/telemetry.py`)
4. Create AuditService
5. Integrate AuditService into all existing service layer write operations
6. Create audit log API endpoint
7. Create health check dependency status checks
8. Create audit_log partitioning migration
9. Write tests

### File Creation Plan

```
backend/app/core/logging.py                    # structlog configuration
backend/app/core/telemetry.py                  # OpenTelemetry configuration
backend/app/middleware/logging_middleware.py    # Request logging
backend/app/services/audit_service.py          # Audit log service
backend/app/api/v1/audit_logs.py               # Audit log API routes
backend/app/schemas/audit.py                   # Pydantic schemas for audit log
```

### Do NOT
- Do NOT allow UPDATE or DELETE on the audit_logs table
- Do NOT log passwords, tokens, or secrets in any log output
- Do NOT make audit logging async (must be in same transaction)
- Do NOT skip audit logging for any write operation — every mutation must be logged
- Do NOT use print() — always use structlog
- Do NOT store OpenTelemetry data locally — export to New Relic via OTLP

### Verify
- [ ] All API requests produce structured JSON log entries
- [ ] Request ID is propagated through all log entries in a request
- [ ] Every create/update/delete operation produces an audit log entry
- [ ] Audit log change diff is accurate for updates
- [ ] Audit logs cannot be modified or deleted (DB rules enforced)
- [ ] OpenTelemetry traces appear in New Relic
- [ ] Health check reports database, Redis, Celery status
- [ ] Audit log API supports pagination and filtering
- [ ] No sensitive data in logs or audit entries

## 10. OPEN QUESTIONS

None.
