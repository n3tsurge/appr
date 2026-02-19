# TPRD-2026-02-18-platform-foundation

## 1. DOCUMENT METADATA

```
Document ID:    TPRD-2026-02-18-platform-foundation
Version:        1.0
Status:         Draft
Feature Name:   Platform Foundation
Parent TPRD:    None
```

## 2. EXECUTIVE SUMMARY

- **Business Objective**: Establish the foundational infrastructure, project structure, containerization, CI/CD pipeline, and database setup required before any feature development begins. This converts the single-file HTML POC into a properly architected enterprise application.
- **Technical Scope**: Python/FastAPI backend scaffolding, Vue 3/TypeScript frontend scaffolding, PostgreSQL + Redis infrastructure, Docker composition, GitHub Actions CI/CD, and development environment tooling.
- **Success Criteria**: A developer can clone the repo, run `docker compose up`, and have a fully operational local environment with hot-reload on both backend and frontend within 5 minutes.
- **Complexity Estimate**: L — Multiple moving parts across backend, frontend, database, and CI/CD.

## 3. SCOPE DEFINITION

### 3.1 In Scope
- Backend project scaffolding (FastAPI application factory)
- Frontend project scaffolding (Vite + Vue 3 + TypeScript)
- PostgreSQL 16 database setup with initial schema
- Redis 7 setup for caching and Celery broker
- Alembic migration framework initialization
- Docker and Docker Compose for local development
- Production-ready Dockerfile (multi-stage builds)
- GitHub Actions CI/CD pipeline (lint, test, build, push)
- Environment-based configuration (`.env` files, pydantic-settings)
- Health check endpoints (`/health`, `/ready`)
- CORS middleware configuration
- Request ID middleware for tracing
- Structured logging setup (structlog)

### 3.2 Out of Scope
- Application feature logic (covered by TPRD-004 through TPRD-011)
- Authentication (covered by TPRD-003)
- Kubernetes manifests for production (future TPRD)
- Terraform/IaC for cloud provisioning (future TPRD)
- SSL/TLS certificate management (infrastructure concern)

### 3.3 Assumptions
- Developers have Docker Desktop installed (impact if wrong: must provide alternative setup instructions)
- GitHub is the sole source control provider (impact if wrong: must adapt CI/CD)
- PostgreSQL 16 is available as a Docker image (impact if wrong: use closest available version)
- Python 3.12 is the minimum Python version (impact if wrong: adjust type hints and dependencies)

### 3.4 Dependencies
- None — this is the root TPRD

## 4. TECHNICAL SPECIFICATIONS

### 4.1 Technology Stack Declaration
Per `.github/technology-stack.yml`. No feature-specific additions.

### 4.2 Architecture & Design Patterns

**System Architecture:**
```
┌─────────────────────────────────────────────────────┐
│                    Reverse Proxy                     │
│               (nginx / traefik / etc.)               │
├──────────────────────┬──────────────────────────────┤
│   Frontend (Vue 3)   │      Backend (FastAPI)        │
│   Vite Dev Server    │   ┌───────────────────────┐  │
│   Port: 5173         │   │  REST API /api/v1/    │  │
│                      │   │  GraphQL /graphql     │  │
│                      │   │  Health /health       │  │
│                      │   │  Status /status/*     │  │
│                      │   └──────────┬────────────┘  │
│                      │              │                │
│                      │   ┌──────────▼────────────┐  │
│                      │   │    Service Layer       │  │
│                      │   └──────────┬────────────┘  │
│                      │              │                │
│                      │   ┌──────────▼────────────┐  │
│                      │   │  SQLAlchemy 2 Async    │  │
│                      │   └──────────┬────────────┘  │
├──────────────────────┴──────────────┼────────────────┤
│  PostgreSQL 16   │   Redis 7   │   Celery Workers   │
└──────────────────┴─────────────┴────────────────────┘
```

**Design Patterns:**
- **Application Factory Pattern**: `create_app()` function for FastAPI app instantiation
- **Repository Pattern**: Thin data access layer wrapping SQLAlchemy queries
- **Service Layer**: Business logic sits between API handlers and repositories
- **Dependency Injection**: FastAPI `Depends()` for database sessions, auth, and services

**Directory Structure:**
```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                  # Application factory
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py              # Shared dependencies
│   │   └── v1/
│   │       ├── __init__.py
│   │       └── router.py        # V1 API router aggregator
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py            # Pydantic Settings
│   │   ├── database.py          # Async engine + session factory
│   │   ├── redis.py             # Redis client factory
│   │   ├── security.py          # JWT, password hashing
│   │   └── logging.py           # structlog configuration
│   ├── middleware/
│   │   ├── __init__.py
│   │   ├── cors.py
│   │   ├── request_id.py
│   │   └── tenant.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── base.py              # Declarative base, mixins
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── common.py            # Shared envelope, pagination
│   │   └── health.py
│   ├── services/
│   │   └── __init__.py
│   ├── graphql/
│   │   └── __init__.py
│   └── tasks/
│       ├── __init__.py
│       └── celery_app.py        # Celery configuration
├── migrations/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
├── tests/
│   ├── conftest.py
│   ├── test_health.py
│   └── factories/
├── alembic.ini
├── pyproject.toml
├── Dockerfile
└── .env.example

frontend/
├── src/
│   ├── App.vue
│   ├── main.ts
│   ├── api/
│   │   ├── client.ts            # Axios instance
│   │   └── index.ts
│   ├── assets/
│   │   └── main.css             # Tailwind imports
│   ├── components/
│   │   └── common/
│   ├── composables/
│   ├── router/
│   │   └── index.ts
│   ├── stores/
│   │   └── index.ts
│   ├── types/
│   │   └── index.ts
│   └── views/
├── tests/
├── index.html
├── package.json
├── tailwind.config.ts
├── tsconfig.json
├── vite.config.ts
├── vitest.config.ts
└── Dockerfile

docker-compose.yml
docker-compose.override.yml      # Dev overrides
.env.example
.github/
  workflows/
    ci.yml
    deploy.yml
```

### 4.3 Data Models

**Base Model Mixin** (all tables inherit):
```python
class BaseModel:
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
```

### 4.4 API Specifications

**Health Check:**
```
GET /health
Response 200:
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2026-02-18T12:00:00Z"
}

GET /ready
Response 200:
{
  "status": "ready",
  "checks": {
    "database": "ok",
    "redis": "ok",
    "celery": "ok"
  }
}
Response 503:
{
  "status": "not_ready",
  "checks": {
    "database": "ok",
    "redis": "error",
    "celery": "ok"
  }
}
```

### 4.5 Frontend Specifications
- Vite project scaffolded with `create-vue` (TypeScript, Vue Router, Pinia)
- Tailwind CSS configured with Holman brand colors
- Axios client with base URL from environment variable
- JWT interceptor (placeholder for TPRD-003)

### 4.6 Business Logic
N/A for this TPRD — this is infrastructure only.

## 5. SECURITY REQUIREMENTS

- Health endpoints (`/health`, `/ready`) MUST be accessible without authentication
- All other endpoints MUST require authentication (enforced globally, implemented in TPRD-003)
- Environment secrets MUST NOT be committed to source control
- Docker images MUST use non-root users
- Docker images MUST use multi-stage builds to minimize attack surface
- CORS origins MUST be configurable via environment variable
- `.env.example` MUST NOT contain real credentials

## 6. TESTING REQUIREMENTS

### 6.1 Unit Tests
- `test_health.py`: Verify `/health` returns 200 with correct shape
- `test_ready.py`: Verify `/ready` returns 200 when all dependencies are up, 503 when any is down
- `test_config.py`: Verify pydantic-settings loads correctly from environment

### 6.2 Integration Tests
- Docker Compose test: Verify all containers start and communicate
- Database connection test: Verify SQLAlchemy session creation
- Redis connection test: Verify Redis ping

### 6.3 Frontend Tests
- `App.test.ts`: Verify App component mounts
- Axios client test: Verify base URL configuration

### 6.4 Security Tests
- Verify no secrets in Docker image layers
- Verify non-root user in containers

## 7. NON-FUNCTIONAL REQUIREMENTS

- **Performance**: Health check response < 50ms
- **Scalability**: Backend and frontend are stateless containers; scale horizontally
- **Availability**: Health checks enable container orchestrator liveness/readiness probes
- **Observability**: structlog JSON output from first request; OpenTelemetry SDK initialized

## 8. MIGRATION & DEPLOYMENT

- **Database Migration**: Run `alembic upgrade head` on container startup via entrypoint script
- **Rollback**: `alembic downgrade -1` to revert last migration
- **Feature Flags**: N/A for foundation
- **Deployment Sequence**: Database → Redis → Backend → Celery Workers → Frontend

## 9. IMPLEMENTATION GUIDANCE FOR CODING AGENTS

### Implementation Order
1. Create `pyproject.toml` with all backend dependencies
2. Create `backend/app/core/config.py` (pydantic-settings)
3. Create `backend/app/core/database.py` (async engine)
4. Create `backend/app/core/redis.py` (aioredis)
5. Create `backend/app/core/logging.py` (structlog)
6. Create `backend/app/models/base.py` (declarative base + mixin)
7. Create `backend/app/main.py` (application factory)
8. Create `backend/app/middleware/` (CORS, request_id, tenant)
9. Create health check endpoints
10. Initialize Alembic
11. Create `backend/Dockerfile`
12. Scaffold frontend with Vite
13. Configure Tailwind with Holman colors
14. Create Axios client
15. Create `frontend/Dockerfile`
16. Create `docker-compose.yml`
17. Create `.github/workflows/ci.yml`
18. Write tests

### File Creation Plan
See Section 4.2 for complete directory structure.

### Do NOT
- Do NOT install packages not in `.github/technology-stack.yml` without justification
- Do NOT use synchronous SQLAlchemy — all database access MUST be async
- Do NOT hardcode configuration values — use pydantic-settings
- Do NOT use `print()` — use structlog
- Do NOT use `latest` Docker tags — pin all versions

### Verify
- [ ] `docker compose up` starts all services without errors
- [ ] `GET /health` returns 200
- [ ] `GET /ready` returns 200 with all checks passing
- [ ] Backend hot-reload works (change a file, see restart)
- [ ] Frontend hot-reload works (change a file, see update in browser)
- [ ] `pytest` passes with no errors
- [ ] `npm run test` passes with no errors
- [ ] `alembic upgrade head` runs without errors
- [ ] GitHub Actions CI workflow passes

## 10. OPEN QUESTIONS

None — this TPRD is ready for implementation.
