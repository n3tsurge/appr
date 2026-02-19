# Copilot Instructions — AppInventory (AppR)

## Project Overview
AppInventory is an enterprise application inventory and management system. It tracks products, services, components, resources, repositories, teams, people, incidents, and scorecards across the organization.

## Technology Stack
Refer to `.github/technology-stack.yml` for the authoritative technology decisions.

## Code Conventions

### Backend (Python / FastAPI)
- Python 3.12, type hints on all functions
- FastAPI with async endpoints using `async def`
- SQLAlchemy 2.0 async ORM with mapped_column
- Pydantic v2 for request/response schemas
- Alembic for database migrations
- Dependency injection via FastAPI `Depends()`
- All endpoints under `/api/v1/` prefix
- Error responses follow RFC 7807 Problem Details
- Use structlog for structured JSON logging
- Celery for async background tasks

### Frontend (Vue.js 3 / TypeScript)
- Vue 3 Composition API with `<script setup lang="ts">`
- Pinia stores for state management
- Vue Router 4 for navigation
- Tailwind CSS for all styling (no custom CSS)
- Axios for HTTP requests with interceptors for auth
- TypeScript strict mode enabled
- D3.js for graph/visualization components

### API Design
- RESTful endpoints for CRUD operations
- GraphQL (Strawberry) for complex relationship queries
- Pagination: cursor-based for lists
- Filtering: query parameter based
- Sorting: `?sort=field&order=asc|desc`
- All responses wrapped in standard envelope

### Database
- PostgreSQL 16, self-hosted
- Redis for caching and Celery broker
- All tables include `tenant_id`, `created_at`, `updated_at`, `created_by`, `updated_by`
- Soft deletes via `deleted_at` column
- UUID primary keys

### Authentication & Authorization
- OAuth 2.0 / SAML via Okta (primary)
- Local auth fallback (bcrypt hashed passwords)
- JWT access tokens (15 min) + refresh tokens (7 days)
- RBAC: Admin, Editor, Viewer, Incident Commander

### Testing
- Backend: pytest + pytest-asyncio, minimum 85% coverage
- Frontend: Vitest + Vue Test Utils, Playwright for E2E
- API tests use httpx AsyncClient

### File Structure
```
backend/
  app/
    api/v1/          # Route handlers
    core/            # Config, security, dependencies
    models/          # SQLAlchemy models
    schemas/         # Pydantic schemas
    services/        # Business logic
    graphql/         # Strawberry GraphQL schema
    tasks/           # Celery tasks
    middleware/      # Custom middleware
  migrations/        # Alembic migrations
  tests/
frontend/
  src/
    components/      # Vue components
    views/           # Page-level components
    stores/          # Pinia stores
    composables/     # Reusable composition functions
    types/           # TypeScript interfaces
    router/          # Vue Router config
    api/             # Axios API client
    assets/          # Static assets
  tests/
docs/
  tprd/              # Technical Product Requirements
  security/          # Security documentation
```
