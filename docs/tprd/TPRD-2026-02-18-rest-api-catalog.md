# TPRD-2026-02-18-rest-api-catalog

## 1. DOCUMENT METADATA

```
Document ID:    TPRD-2026-02-18-rest-api-catalog
Version:        1.0
Status:         Draft
Feature Name:   REST API — Catalog Entities
Parent TPRD:    TPRD-2026-02-18-platform-foundation
```

## 2. EXECUTIVE SUMMARY

- **Business Objective**: Provide a complete RESTful API for all catalog entity CRUD operations, enabling the frontend and future integrations to manage Products, Services, Components, Resources, Repositories, Teams, People, and their relationships.
- **Technical Scope**: FastAPI route handlers for 8 entity types, each with list (paginated + filtered), detail, create, update, and delete endpoints. Standard response envelope. RFC 7807 error responses.
- **Success Criteria**: All CRUD operations from the POC are replicated via REST API. 100% of POC data can be represented. All endpoints enforce RBAC. Response time < 100ms for list queries with pagination.
- **Complexity Estimate**: XL — 8 entity types × 5 endpoints each = 40+ endpoint definitions, plus relationship management, filtering, sorting, and search.

## 3. SCOPE DEFINITION

### 3.1 In Scope
- CRUD endpoints for: Teams, People, Products, Services, Components, Resources, Repositories
- Relationship management (add/remove services to products, components to services, etc.)
- Pagination (cursor-based with fallback to offset-based)
- Filtering by common fields (status, type, team_id, operational_status)
- Sorting by name, created_at, updated_at
- Search by name (ILIKE)
- Bulk import endpoint (JSON file upload)
- Export endpoint (JSON download)
- Operational status change endpoints for Services, Components, Resources
- Redis caching for frequently accessed list queries

### 3.2 Out of Scope
- Incidents (TPRD-007)
- Scorecards (TPRD-008)
- GraphQL (TPRD-005)
- Notifications (TPRD-011)
- Webhook endpoints (future)

### 3.3 Assumptions
- Cursor-based pagination uses `created_at` + `id` for stable ordering
- Search uses PostgreSQL `ILIKE` (not full-text search) for initial implementation
- Bulk import is limited to 1,000 entities per request

### 3.4 Dependencies
- TPRD-2026-02-18-platform-foundation
- TPRD-2026-02-18-core-data-models
- TPRD-2026-02-18-authentication-authorization

## 4. TECHNICAL SPECIFICATIONS

### 4.1 Technology Stack Declaration
Per `.github/technology-stack.yml`. No additions.

### 4.2 Architecture & Design Patterns

**Layered Architecture per Entity:**
```
Route Handler (api/v1/products.py)
  ↓ validates input via Pydantic
Service Layer (services/product_service.py)
  ↓ business logic, authorization checks
Repository Layer (repositories/product_repository.py)
  ↓ SQLAlchemy queries, tenant scoping
Database (PostgreSQL)
```

**Common Patterns:**
- `GenericRepository[T]` base class for standard CRUD operations
- `GenericService[T]` base class handling audit logging and cache invalidation
- Pagination helper: `paginate(query, params) -> PaginatedResponse`

### 4.3 API Specifications — Endpoint Summary

All endpoints are prefixed with `/api/v1/`.

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| GET | /teams | ✅ | Any | List teams |
| POST | /teams | ✅ | Editor+ | Create team |
| GET | /teams/{id} | ✅ | Any | Get team detail |
| PUT | /teams/{id} | ✅ | Editor+ | Update team |
| DELETE | /teams/{id} | ✅ | Admin | Soft delete team |
| GET | /people | ✅ | Any | List people |
| POST | /people | ✅ | Editor+ | Create person |
| GET | /people/{id} | ✅ | Any | Get person detail |
| PUT | /people/{id} | ✅ | Editor+ | Update person |
| DELETE | /people/{id} | ✅ | Admin | Soft delete person |
| GET | /products | ✅ | Any | List products |
| POST | /products | ✅ | Editor+ | Create product |
| GET | /products/{id} | ✅ | Any | Get product detail (with services, assignments, scorecards) |
| PUT | /products/{id} | ✅ | Editor+ | Update product |
| DELETE | /products/{id} | ✅ | Admin | Soft delete product |
| GET | /services | ✅ | Any | List services |
| POST | /services | ✅ | Editor+ | Create service |
| GET | /services/{id} | ✅ | Any | Get service detail (with components, resources, deps, assignments) |
| PUT | /services/{id} | ✅ | Editor+ | Update service |
| DELETE | /services/{id} | ✅ | Admin | Soft delete service |
| PATCH | /services/{id}/operational-status | ✅ | Editor+/IC | Change operational status |
| GET | /components | ✅ | Any | List components |
| POST | /components | ✅ | Editor+ | Create component |
| GET | /components/{id} | ✅ | Any | Get component detail |
| PUT | /components/{id} | ✅ | Editor+ | Update component |
| DELETE | /components/{id} | ✅ | Admin | Soft delete component |
| PATCH | /components/{id}/operational-status | ✅ | Editor+/IC | Change operational status |
| GET | /resources | ✅ | Any | List resources |
| POST | /resources | ✅ | Editor+ | Create resource |
| GET | /resources/{id} | ✅ | Any | Get resource detail |
| PUT | /resources/{id} | ✅ | Editor+ | Update resource |
| DELETE | /resources/{id} | ✅ | Admin | Soft delete resource |
| PATCH | /resources/{id}/operational-status | ✅ | Editor+/IC | Change operational status |
| GET | /repositories | ✅ | Any | List repositories |
| POST | /repositories | ✅ | Editor+ | Create repository |
| GET | /repositories/{id} | ✅ | Any | Get repository detail |
| PUT | /repositories/{id} | ✅ | Editor+ | Update repository |
| DELETE | /repositories/{id} | ✅ | Admin | Soft delete repository |
| POST | /import | ✅ | Admin | Bulk import from JSON |
| GET | /export | ✅ | Admin | Export all data as JSON |

### 4.4 API Specifications — Detail

#### Standard Query Parameters (all list endpoints)

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| page | int | 1 | Page number (offset pagination) |
| per_page | int | 25 | Items per page (max 100) |
| cursor | string | null | Cursor for cursor-based pagination |
| sort | string | "name" | Sort field |
| order | string | "asc" | Sort direction (asc, desc) |
| search | string | null | Search by name (ILIKE) |

#### Entity-Specific Filters

**Services:** `?type=api&status=active&operational_status=operational&team_id=uuid`
**Components:** `?type=library&status=active&operational_status=operational&team_id=uuid`
**Resources:** `?type=kubernetes&environment=production&operational_status=operational&team_id=uuid`
**Repositories:** `?provider=github&language=Python&team_id=uuid`
**Products:** `?status=active&team_id=uuid`
**People:** `?team_id=uuid`

#### Standard List Response Shape
```json
{
  "data": [
    { "id": "...", "name": "...", ... }
  ],
  "meta": {
    "total": 42,
    "page": 1,
    "per_page": 25,
    "total_pages": 2,
    "next_cursor": "eyJ...",
    "prev_cursor": null
  }
}
```

#### Standard Detail Response Shape (Example: Service)
```json
{
  "data": {
    "id": "uuid",
    "name": "Customer API",
    "type": "api",
    "description": "RESTful API serving the customer portal",
    "team_id": "uuid",
    "team": { "id": "uuid", "name": "Platform Engineering" },
    "status": "active",
    "operational_status": "operational",
    "attributes": {
      "endpoint": "https://api.holman.com/v2",
      "protocol": "REST",
      "auth_method": "OAuth2",
      "rate_limit": 1000,
      "sla": "99.9",
      "version": "v2"
    },
    "components": [
      { "id": "uuid", "name": "Auth Middleware", "type": "library", "operational_status": "operational" }
    ],
    "resources": [
      { "id": "uuid", "name": "prod-api-aks", "type": "kubernetes", "operational_status": "operational" }
    ],
    "depends_on": [
      { "id": "uuid", "name": "Core Database", "type": "database", "operational_status": "degraded" }
    ],
    "dependents": [
      { "id": "uuid", "name": "Customer Frontend", "type": "web_application" }
    ],
    "products": [
      { "id": "uuid", "name": "Customer Portal" }
    ],
    "repositories": [
      { "id": "uuid", "name": "HolmanEnterprises/customer-portal", "provider": "azure_devops" }
    ],
    "assignments": [
      { "person_id": "uuid", "person_name": "Alice Chen", "role": "Lead" },
      { "person_id": "uuid", "person_name": "Bob Martinez", "role": "On-Call" }
    ],
    "active_incidents": [
      { "id": "uuid", "title": "Core DB Degradation", "severity": "major", "status": "investigating" }
    ],
    "created_at": "2026-02-18T00:00:00Z",
    "updated_at": "2026-02-18T00:00:00Z"
  }
}
```

#### Standard Error Response (RFC 7807)
```json
{
  "type": "https://api.appinventory.holman.com/errors/not-found",
  "title": "Not Found",
  "status": 404,
  "detail": "Service with id '550e8400-e29b-41d4-a716-446655440000' was not found.",
  "instance": "/api/v1/services/550e8400-e29b-41d4-a716-446655440000"
}
```

#### PATCH /api/v1/services/{id}/operational-status
```json
Request:
{ "operational_status": "degraded" }

Response 200:
{
  "data": {
    "id": "uuid",
    "name": "Customer API",
    "operational_status": "degraded",
    "previous_status": "operational",
    "changed_at": "2026-02-18T12:00:00Z",
    "changed_by": "uuid"
  }
}
```

#### POST /api/v1/import
```
Content-Type: multipart/form-data
Body: file (JSON, same shape as sample-data.json)

Response 200:
{
  "data": {
    "imported": {
      "teams": 3,
      "people": 3,
      "products": 2,
      "services": 4,
      "components": 5,
      "resources": 4,
      "repositories": 6,
      "incidents": 1,
      "scorecards": 3
    },
    "errors": []
  }
}
```

#### GET /api/v1/export
```
Response 200:
Content-Type: application/json
Content-Disposition: attachment; filename="app-inventory-2026-02-18.json"
Body: Full inventory JSON (same shape as import)
```

### 4.5 Frontend Specifications
Covered by TPRD-006. API client modules will be generated per entity type.

### 4.6 Business Logic

**Soft Delete Cascade Rules:**
- Deleting a Team: Set `team_id = NULL` on all associated entities; do NOT delete child entities
- Deleting a Product: Remove `product_services` associations; do NOT delete services
- Deleting a Service: Remove all association table entries (`service_components`, `service_resources`, `service_dependencies`, `service_repositories`); remove from `product_services`; remove from `incident_affected_entities`
- Deleting a Component: Remove all association table entries; remove from `service_components`
- Deleting a Resource: Remove from `service_resources`
- Deleting a Person: Remove from `entity_assignments`; set `person_id = NULL` on linked user
- Deleting a Repository: Remove from `service_repositories` and `component_repositories`

**Redis Cache Strategy:**
- Cache key pattern: `tenant:{tid}:{entity_type}:list:{hash_of_query_params}`
- TTL: 60 seconds
- Invalidation: On any write (create/update/delete) for that entity type within the tenant, delete all list cache keys for that type
- Detail views: NOT cached (always real-time for operational status accuracy)

## 5. SECURITY REQUIREMENTS

- All endpoints MUST require authentication (JWT)
- All queries MUST be scoped by `tenant_id` from JWT
- Write operations (POST, PUT, DELETE) MUST be authorized per RBAC matrix
- Operational status changes MUST be authorized (Editor + Incident Commander + Admin)
- Import endpoint MUST validate JSON schema before processing
- Export endpoint MUST only export current tenant's data
- All write operations MUST emit audit log entries

## 6. TESTING REQUIREMENTS

### 6.1 Unit Tests
- Service layer CRUD logic for each entity type
- Pagination logic (offset and cursor-based)
- Filter and sort query building
- Soft delete cascade logic
- Cache invalidation logic

### 6.2 Integration Tests
- Full CRUD cycle for each entity type via httpx AsyncClient
- Relationship management (add service to product, verify detail endpoint)
- Pagination: verify page navigation, cursor stability
- Filtering: verify each filter parameter
- Search: verify name ILIKE matching
- Import: upload sample-data.json, verify all entities created
- Export: verify JSON shape matches import format
- RBAC: verify 403 for unauthorized operations
- Soft delete: verify entity hidden from list but exists in DB

### 6.3 Security Tests
- Cross-tenant data access attempt returns 404 (not 403, to avoid information leakage)
- SQL injection via filter parameters
- Oversized request body rejection (>1MB)

## 7. NON-FUNCTIONAL REQUIREMENTS

- **Performance**: List queries < 100ms at p95 (with cache); Detail queries < 50ms
- **Scalability**: Pagination prevents unbounded result sets
- **Availability**: Graceful degradation if Redis is down (bypass cache, serve from DB)
- **Observability**: OpenTelemetry spans for each endpoint; log request/response summary

## 8. MIGRATION & DEPLOYMENT

- No additional migrations beyond TPRD-002
- Feature flag: N/A — API is core functionality
- Deployment: API routes registered on app startup via router inclusion

## 9. IMPLEMENTATION GUIDANCE FOR CODING AGENTS

### Implementation Order
1. Create `backend/app/repositories/base.py` (GenericRepository)
2. Create `backend/app/services/base.py` (GenericService with audit + cache)
3. Implement Teams → People → Products → Services → Components → Resources → Repositories (in order, since each depends on prior entities for relationships)
4. For each entity: repository → service → schemas → route handler → tests
5. Implement import/export endpoints last
6. Add Redis caching layer

### File Creation Plan
```
backend/app/repositories/
  base.py
  team_repository.py
  person_repository.py
  product_repository.py
  service_repository.py
  component_repository.py
  resource_repository.py
  repository_repository.py

backend/app/services/
  base.py
  team_service.py
  person_service.py
  product_service.py
  service_service.py
  component_service.py
  resource_service.py
  repository_service.py
  import_export_service.py

backend/app/api/v1/
  teams.py
  people.py
  products.py
  services.py
  components.py
  resources.py
  repositories.py
  import_export.py
```

### Do NOT
- Do NOT return `password_hash` or any sensitive user data in API responses
- Do NOT allow write operations without tenant_id validation
- Do NOT eager-load all relationships on list endpoints — only include summary data on detail
- Do NOT use `session.delete()` for any entity — always soft delete via `deleted_at`
- Do NOT return 403 for cross-tenant access — return 404

### Verify
- [ ] All 40+ endpoints return correct status codes
- [ ] Pagination works correctly with cursor and offset modes
- [ ] All filters produce correct results
- [ ] Search by name works case-insensitively
- [ ] Import successfully creates all entities from sample-data.json
- [ ] Export produces valid JSON matching import format
- [ ] RBAC prevents unauthorized writes
- [ ] Soft-deleted entities are excluded from all queries
- [ ] Audit log entries created for all write operations
- [ ] Cache hit rate > 50% on repeated list queries

## 10. OPEN QUESTIONS

None.
