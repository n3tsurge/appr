# TPRD-2026-02-18-core-data-models

## 1. DOCUMENT METADATA

```
Document ID:    TPRD-2026-02-18-core-data-models
Version:        1.0
Status:         Draft
Feature Name:   Core Data Models
Parent TPRD:    TPRD-2026-02-18-platform-foundation
```

## 2. EXECUTIVE SUMMARY

- **Business Objective**: Define the complete relational data model for all entities in the AppInventory system, enabling persistent storage, referential integrity, and efficient querying of the enterprise application catalog.
- **Technical Scope**: SQLAlchemy 2.0 async models, Alembic migrations, Pydantic v2 schemas, and database indexes for all 12 core entity types: Tenants, Users, Teams, People, Products, Services, Components, Resources, Repositories, Incidents, Scorecards, and AuditLogs.
- **Success Criteria**: All entities from the POC `sample-data.json` can be represented and queried via the ORM. Full referential integrity. All migrations reversible.
- **Complexity Estimate**: XL — 12+ entity types with many-to-many relationships, polymorphic attributes, and a flexible scorecard evaluation system.

## 3. SCOPE DEFINITION

### 3.1 In Scope
- SQLAlchemy 2.0 model definitions for all entities
- Pydantic v2 request/response schemas for all entities
- Alembic migration files for initial schema
- Database indexes for common query patterns
- Many-to-many relationship tables (assignments, service-component links, etc.)
- JSONB columns for flexible entity attributes
- Soft delete support via `deleted_at`
- Multi-tenant column (`tenant_id`) on all tables
- Audit log table definition

### 3.2 Out of Scope
- API endpoint implementation (TPRD-004, TPRD-005)
- Business logic and service layer (covered per-feature TPRD)
- Data seeding / import from JSON (future task)
- Full-text search indexes (evaluated if needed)

### 3.3 Assumptions
- PostgreSQL 16 with `uuid-ossp` and `pg_trgm` extensions enabled
- JSONB columns are acceptable for type-specific `attributes` fields
- Assignment roles are free-text strings (not a separate table) per POC design
- Impact if wrong: would need to create a `roles` lookup table

### 3.4 Dependencies
- TPRD-2026-02-18-platform-foundation (database engine, base model mixin)

## 4. TECHNICAL SPECIFICATIONS

### 4.1 Technology Stack Declaration
Per `.github/technology-stack.yml`. No additions.

### 4.2 Architecture & Design Patterns
- **Declarative Mapping**: SQLAlchemy 2.0 `DeclarativeBase` with `MappedAsDataclass` mixin
- **Base Mixin**: All models inherit `BaseModel` providing `id`, `tenant_id`, `created_at`, `updated_at`, `created_by`, `updated_by`, `deleted_at`
- **Association Tables**: Many-to-many relationships use explicit association tables with extra columns (e.g., role in assignments)
- **Polymorphic Attributes**: Type-specific fields stored as JSONB in `attributes` column

### 4.3 Data Models

#### 4.3.1 Entity Relationship Diagram (Textual)

```
Tenant 1──* User
Tenant 1──* Team
Tenant 1──* Person (Owner)
Tenant 1──* Product
Tenant 1──* Service
Tenant 1──* Component
Tenant 1──* Resource
Tenant 1──* Repository
Tenant 1──* Incident
Tenant 1──* Scorecard
Tenant 1──* AuditLog

Team 1──* Person
Team 1──* Product
Team 1──* Service
Team 1──* Component
Team 1──* Resource
Team 1──* Repository

Product *──* Service          (via product_services)
Service *──* Component        (via service_components)
Service *──* Resource         (via service_resources)
Service *──* Service          (via service_dependencies, self-referential)
Component *──* Component      (via component_dependencies, self-referential)
Component *──* Service        (via component_service_dependencies)
Service *──* Repository       (via service_repositories)
Component *──* Repository     (via component_repositories)

Product *──* EntityAssignment
Service *──* EntityAssignment
Component *──* EntityAssignment
Resource *──* EntityAssignment
Repository *──* EntityAssignment

Incident *──* (Service|Component|Resource) (via incident_affected_entities)

Scorecard 1──* ScorecardCriterion
```

#### 4.3.2 Table: `tenants`

| Column | Type | Constraints | Index | Notes |
|--------|------|-------------|-------|-------|
| id | UUID | PK, default uuid4 | — | |
| name | VARCHAR(255) | NOT NULL, UNIQUE | yes | |
| slug | VARCHAR(100) | NOT NULL, UNIQUE | yes | URL-safe identifier |
| is_active | BOOLEAN | NOT NULL, default true | — | |
| settings | JSONB | default '{}' | — | Tenant-specific config |
| created_at | TIMESTAMPTZ | NOT NULL, server default | — | |
| updated_at | TIMESTAMPTZ | NOT NULL, auto-update | — | |

#### 4.3.3 Table: `users`

| Column | Type | Constraints | Index | Notes |
|--------|------|-------------|-------|-------|
| id | UUID | PK | — | |
| tenant_id | UUID | FK(tenants.id), NOT NULL | yes | |
| email | VARCHAR(320) | NOT NULL | unique(tenant_id, email) | |
| display_name | VARCHAR(255) | NOT NULL | — | |
| password_hash | VARCHAR(255) | NULLABLE | — | NULL for SSO-only users |
| role | VARCHAR(50) | NOT NULL, default 'viewer' | — | admin, editor, viewer, incident_commander |
| auth_provider | VARCHAR(50) | NOT NULL, default 'local' | — | local, okta, saml |
| external_id | VARCHAR(255) | NULLABLE | — | SSO subject ID |
| is_active | BOOLEAN | NOT NULL, default true | — | |
| last_login_at | TIMESTAMPTZ | NULLABLE | — | |
| person_id | UUID | FK(people.id), NULLABLE | — | Link to catalog person record |
| created_at | TIMESTAMPTZ | NOT NULL | — | |
| updated_at | TIMESTAMPTZ | NOT NULL | — | |
| deleted_at | TIMESTAMPTZ | NULLABLE | — | |

#### 4.3.4 Table: `teams`

| Column | Type | Constraints | Index | Notes |
|--------|------|-------------|-------|-------|
| id | UUID | PK | — | |
| tenant_id | UUID | FK(tenants.id), NOT NULL | yes | |
| name | VARCHAR(255) | NOT NULL | unique(tenant_id, name) | |
| description | TEXT | NULLABLE | — | |
| slack_channel | VARCHAR(100) | NULLABLE | — | |
| contact_email | VARCHAR(320) | NULLABLE | — | |
| created_at | TIMESTAMPTZ | NOT NULL | — | |
| updated_at | TIMESTAMPTZ | NOT NULL | — | |
| created_by | UUID | NULLABLE | — | |
| updated_by | UUID | NULLABLE | — | |
| deleted_at | TIMESTAMPTZ | NULLABLE | — | |

#### 4.3.5 Table: `people`

| Column | Type | Constraints | Index | Notes |
|--------|------|-------------|-------|-------|
| id | UUID | PK | — | |
| tenant_id | UUID | FK(tenants.id), NOT NULL | yes | |
| name | VARCHAR(255) | NOT NULL | — | |
| email | VARCHAR(320) | NOT NULL | unique(tenant_id, email) | |
| team_id | UUID | FK(teams.id), NULLABLE | yes | |
| role_title | VARCHAR(100) | NULLABLE | — | e.g., "Senior Engineer" |
| slack_handle | VARCHAR(100) | NULLABLE | — | |
| created_at | TIMESTAMPTZ | NOT NULL | — | |
| updated_at | TIMESTAMPTZ | NOT NULL | — | |
| created_by | UUID | NULLABLE | — | |
| updated_by | UUID | NULLABLE | — | |
| deleted_at | TIMESTAMPTZ | NULLABLE | — | |

#### 4.3.6 Table: `products`

| Column | Type | Constraints | Index | Notes |
|--------|------|-------------|-------|-------|
| id | UUID | PK | — | |
| tenant_id | UUID | FK(tenants.id), NOT NULL | yes | |
| name | VARCHAR(255) | NOT NULL | unique(tenant_id, name) | |
| description | TEXT | NULLABLE | — | |
| team_id | UUID | FK(teams.id), NULLABLE | yes | |
| status | VARCHAR(20) | NOT NULL, default 'active' | yes | active, planned, maintenance, deprecated |
| version | VARCHAR(50) | NULLABLE | — | |
| tags | JSONB | default '[]' | GIN index | Array of strings |
| created_at | TIMESTAMPTZ | NOT NULL | — | |
| updated_at | TIMESTAMPTZ | NOT NULL | — | |
| created_by | UUID | NULLABLE | — | |
| updated_by | UUID | NULLABLE | — | |
| deleted_at | TIMESTAMPTZ | NULLABLE | — | |

#### 4.3.7 Table: `services`

| Column | Type | Constraints | Index | Notes |
|--------|------|-------------|-------|-------|
| id | UUID | PK | — | |
| tenant_id | UUID | FK(tenants.id), NOT NULL | yes | |
| name | VARCHAR(255) | NOT NULL | unique(tenant_id, name) | |
| type | VARCHAR(30) | NOT NULL | yes | api, web_application, database, message_queue, cache, infrastructure |
| description | TEXT | NULLABLE | — | |
| team_id | UUID | FK(teams.id), NULLABLE | yes | |
| status | VARCHAR(20) | NOT NULL, default 'active' | yes | active, planned, maintenance, deprecated |
| operational_status | VARCHAR(20) | NOT NULL, default 'operational' | yes | operational, degraded, outage |
| attributes | JSONB | default '{}' | GIN index | Type-specific fields (endpoint, protocol, etc.) |
| created_at | TIMESTAMPTZ | NOT NULL | — | |
| updated_at | TIMESTAMPTZ | NOT NULL | — | |
| created_by | UUID | NULLABLE | — | |
| updated_by | UUID | NULLABLE | — | |
| deleted_at | TIMESTAMPTZ | NULLABLE | — | |

**Service Types & Their Attributes:**

| Type | Attribute Keys |
|------|---------------|
| api | endpoint, protocol, auth_method, rate_limit, sla, version |
| web_application | url, framework, hosting, cdn, authentication |
| database | db_type, version, hosting, backup_frequency, encryption |
| message_queue | broker, topics, retention_days, dlq |
| cache | cache_type, ttl, size |
| infrastructure | provider, region, redundancy, iac |

#### 4.3.8 Table: `components`

| Column | Type | Constraints | Index | Notes |
|--------|------|-------------|-------|-------|
| id | UUID | PK | — | |
| tenant_id | UUID | FK(tenants.id), NOT NULL | yes | |
| name | VARCHAR(255) | NOT NULL | unique(tenant_id, name) | |
| type | VARCHAR(30) | NOT NULL | yes | library, microservice, sdk, agent, ui_component |
| description | TEXT | NULLABLE | — | |
| team_id | UUID | FK(teams.id), NULLABLE | yes | |
| status | VARCHAR(20) | NOT NULL, default 'active' | yes | |
| operational_status | VARCHAR(20) | NOT NULL, default 'operational' | yes | |
| attributes | JSONB | default '{}' | GIN index | |
| created_at | TIMESTAMPTZ | NOT NULL | — | |
| updated_at | TIMESTAMPTZ | NOT NULL | — | |
| created_by | UUID | NULLABLE | — | |
| updated_by | UUID | NULLABLE | — | |
| deleted_at | TIMESTAMPTZ | NULLABLE | — | |

**Component Types & Their Attributes:**

| Type | Attribute Keys |
|------|---------------|
| library | language, version, repository, license |
| microservice | runtime, containerized, repository, cicd |
| sdk | vendor, version, language, documentation |
| agent | runtime, schedule, containerized, repository |
| ui_component | framework, repository, package_name |

#### 4.3.9 Table: `resources`

| Column | Type | Constraints | Index | Notes |
|--------|------|-------------|-------|-------|
| id | UUID | PK | — | |
| tenant_id | UUID | FK(tenants.id), NOT NULL | yes | |
| name | VARCHAR(255) | NOT NULL | unique(tenant_id, name) | |
| type | VARCHAR(30) | NOT NULL | yes | ec2, virtual_machine, logic_app, storage_account, container_instance, kubernetes, function_app, load_balancer, api_gateway, cdn |
| description | TEXT | NULLABLE | — | |
| team_id | UUID | FK(teams.id), NULLABLE | yes | |
| operational_status | VARCHAR(20) | NOT NULL, default 'operational' | yes | |
| environment | VARCHAR(20) | NOT NULL, default 'production' | yes | production, staging, development, dr |
| attributes | JSONB | default '{}' | GIN index | |
| created_at | TIMESTAMPTZ | NOT NULL | — | |
| updated_at | TIMESTAMPTZ | NOT NULL | — | |
| created_by | UUID | NULLABLE | — | |
| updated_by | UUID | NULLABLE | — | |
| deleted_at | TIMESTAMPTZ | NULLABLE | — | |

#### 4.3.10 Table: `repositories`

| Column | Type | Constraints | Index | Notes |
|--------|------|-------------|-------|-------|
| id | UUID | PK | — | |
| tenant_id | UUID | FK(tenants.id), NOT NULL | yes | |
| name | VARCHAR(255) | NOT NULL | unique(tenant_id, name) | |
| url | VARCHAR(2048) | NULLABLE | — | |
| provider | VARCHAR(30) | NOT NULL | yes | github, gitlab, azure_devops, bitbucket |
| description | TEXT | NULLABLE | — | |
| default_branch | VARCHAR(100) | default 'main' | — | |
| language | VARCHAR(50) | NULLABLE | — | Primary language |
| team_id | UUID | FK(teams.id), NULLABLE | yes | |
| created_at | TIMESTAMPTZ | NOT NULL | — | |
| updated_at | TIMESTAMPTZ | NOT NULL | — | |
| created_by | UUID | NULLABLE | — | |
| updated_by | UUID | NULLABLE | — | |
| deleted_at | TIMESTAMPTZ | NULLABLE | — | |

#### 4.3.11 Table: `incidents`

| Column | Type | Constraints | Index | Notes |
|--------|------|-------------|-------|-------|
| id | UUID | PK | — | |
| tenant_id | UUID | FK(tenants.id), NOT NULL | yes | |
| title | VARCHAR(500) | NOT NULL | — | |
| description | TEXT | NULLABLE | — | |
| severity | VARCHAR(20) | NOT NULL | yes | critical, major, minor |
| status | VARCHAR(20) | NOT NULL, default 'investigating' | yes | investigating, identified, monitoring, resolved |
| impact_type | VARCHAR(20) | NOT NULL, default 'degraded' | yes | outage, degraded |
| created_at | TIMESTAMPTZ | NOT NULL | — | |
| updated_at | TIMESTAMPTZ | NOT NULL | — | |
| resolved_at | TIMESTAMPTZ | NULLABLE | — | |
| created_by | UUID | NULLABLE | — | |
| updated_by | UUID | NULLABLE | — | |
| deleted_at | TIMESTAMPTZ | NULLABLE | — | |

#### 4.3.12 Table: `incident_timeline_entries`

| Column | Type | Constraints | Index | Notes |
|--------|------|-------------|-------|-------|
| id | UUID | PK | — | |
| incident_id | UUID | FK(incidents.id), NOT NULL | yes | |
| timestamp | TIMESTAMPTZ | NOT NULL | yes | |
| status | VARCHAR(20) | NOT NULL | — | Status at time of entry |
| message | TEXT | NOT NULL | — | |
| created_by | UUID | NULLABLE | — | |

#### 4.3.13 Table: `scorecards`

| Column | Type | Constraints | Index | Notes |
|--------|------|-------------|-------|-------|
| id | UUID | PK | — | |
| tenant_id | UUID | FK(tenants.id), NOT NULL | yes | |
| name | VARCHAR(255) | NOT NULL | unique(tenant_id, name) | |
| description | TEXT | NULLABLE | — | |
| entity_types | JSONB | NOT NULL | GIN | Array of applicable entity types |
| created_at | TIMESTAMPTZ | NOT NULL | — | |
| updated_at | TIMESTAMPTZ | NOT NULL | — | |
| created_by | UUID | NULLABLE | — | |
| updated_by | UUID | NULLABLE | — | |
| deleted_at | TIMESTAMPTZ | NULLABLE | — | |

#### 4.3.14 Table: `scorecard_criteria`

| Column | Type | Constraints | Index | Notes |
|--------|------|-------------|-------|-------|
| id | UUID | PK | — | |
| scorecard_id | UUID | FK(scorecards.id), NOT NULL | yes | CASCADE delete |
| name | VARCHAR(255) | NOT NULL | — | |
| description | TEXT | NULLABLE | — | |
| weight | INTEGER | NOT NULL, default 1 | — | 1-3 scale |
| check_type | VARCHAR(30) | NOT NULL | — | has_field, has_items, field_equals, has_assignment, min_assignments, no_active_incidents, has_tag, etc. |
| check_config | JSONB | NOT NULL | — | `{"field":"teamId"}` or `{"value":"Lead"}` or `{"min":2}` |
| sort_order | INTEGER | NOT NULL, default 0 | — | Display ordering |

#### 4.3.15 Table: `audit_logs`

| Column | Type | Constraints | Index | Notes |
|--------|------|-------------|-------|-------|
| id | UUID | PK | — | |
| tenant_id | UUID | NOT NULL | yes | |
| user_id | UUID | NULLABLE | yes | NULL for system actions |
| action | VARCHAR(50) | NOT NULL | yes | create, update, delete, restore, status_change, login, etc. |
| entity_type | VARCHAR(50) | NOT NULL | yes | products, services, etc. |
| entity_id | UUID | NULLABLE | yes | |
| entity_name | VARCHAR(255) | NULLABLE | — | Denormalized for display |
| changes | JSONB | NULLABLE | — | `{"field": {"old": "x", "new": "y"}}` |
| metadata | JSONB | default '{}' | — | Request ID, IP, user agent, etc. |
| timestamp | TIMESTAMPTZ | NOT NULL, server default | yes | |

**Indexes on audit_logs:**
- `(tenant_id, timestamp DESC)` — for listing recent audit events
- `(tenant_id, entity_type, entity_id)` — for entity history

### Association Tables

#### Table: `product_services`

| Column | Type | Constraints |
|--------|------|-------------|
| product_id | UUID | FK(products.id), PK |
| service_id | UUID | FK(services.id), PK |

#### Table: `service_components`

| Column | Type | Constraints |
|--------|------|-------------|
| service_id | UUID | FK(services.id), PK |
| component_id | UUID | FK(components.id), PK |

#### Table: `service_resources`

| Column | Type | Constraints |
|--------|------|-------------|
| service_id | UUID | FK(services.id), PK |
| resource_id | UUID | FK(resources.id), PK |

#### Table: `service_dependencies`

| Column | Type | Constraints |
|--------|------|-------------|
| service_id | UUID | FK(services.id), PK |
| depends_on_service_id | UUID | FK(services.id), PK |

#### Table: `component_dependencies`

| Column | Type | Constraints |
|--------|------|-------------|
| component_id | UUID | FK(components.id), PK |
| depends_on_component_id | UUID | FK(components.id), PK |

#### Table: `component_service_dependencies`

| Column | Type | Constraints |
|--------|------|-------------|
| component_id | UUID | FK(components.id), PK |
| depends_on_service_id | UUID | FK(services.id), PK |

#### Table: `service_repositories`

| Column | Type | Constraints |
|--------|------|-------------|
| service_id | UUID | FK(services.id), PK |
| repository_id | UUID | FK(repositories.id), PK |

#### Table: `component_repositories`

| Column | Type | Constraints |
|--------|------|-------------|
| component_id | UUID | FK(components.id), PK |
| repository_id | UUID | FK(repositories.id), PK |

#### Table: `incident_affected_entities`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| incident_id | UUID | FK(incidents.id), PK | |
| entity_type | VARCHAR(20) | PK | services, components, resources |
| entity_id | UUID | PK | Not a FK — polymorphic reference |

#### Table: `entity_assignments`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | UUID | PK | |
| tenant_id | UUID | FK(tenants.id), NOT NULL | |
| entity_type | VARCHAR(30) | NOT NULL | products, services, components, resources, repositories |
| entity_id | UUID | NOT NULL | Polymorphic |
| person_id | UUID | FK(people.id), NOT NULL | |
| role | VARCHAR(50) | NOT NULL | Lead, Engineer, Architect, On-Call, Stakeholder, Product Manager |

**Unique constraint**: `(entity_type, entity_id, person_id, role)`
**Indexes**: `(entity_type, entity_id)`, `(person_id)`

### 4.4 Pydantic Schemas (Representative Samples)

**Standard Response Envelope:**
```python
class ApiResponse[T](BaseModel):
    data: T
    meta: dict | None = None

class PaginatedResponse[T](BaseModel):
    data: list[T]
    meta: PaginationMeta

class PaginationMeta(BaseModel):
    total: int
    page: int
    per_page: int
    total_pages: int
    next_cursor: str | None = None
    prev_cursor: str | None = None
```

**Example Entity Schemas (Service):**
```python
class ServiceBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    type: ServiceType  # Enum
    description: str | None = None
    team_id: uuid.UUID | None = None
    status: EntityStatus = EntityStatus.ACTIVE
    operational_status: OperationalStatus = OperationalStatus.OPERATIONAL
    attributes: dict[str, Any] = Field(default_factory=dict)

class ServiceCreate(ServiceBase):
    component_ids: list[uuid.UUID] = Field(default_factory=list)
    resource_ids: list[uuid.UUID] = Field(default_factory=list)
    depends_on_service_ids: list[uuid.UUID] = Field(default_factory=list)
    repository_ids: list[uuid.UUID] = Field(default_factory=list)
    assignments: list[AssignmentInput] = Field(default_factory=list)

class ServiceUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    type: ServiceType | None = None
    description: str | None = None
    team_id: uuid.UUID | None = None
    status: EntityStatus | None = None
    operational_status: OperationalStatus | None = None
    attributes: dict[str, Any] | None = None
    component_ids: list[uuid.UUID] | None = None
    resource_ids: list[uuid.UUID] | None = None
    depends_on_service_ids: list[uuid.UUID] | None = None
    repository_ids: list[uuid.UUID] | None = None
    assignments: list[AssignmentInput] | None = None

class ServiceRead(ServiceBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    created_by: uuid.UUID | None = None
    updated_by: uuid.UUID | None = None

class ServiceDetail(ServiceRead):
    components: list[ComponentSummary] = []
    resources: list[ResourceSummary] = []
    depends_on: list[ServiceSummary] = []
    dependents: list[ServiceSummary] = []
    repositories: list[RepositorySummary] = []
    products: list[ProductSummary] = []
    assignments: list[AssignmentRead] = []
    incidents: list[IncidentSummary] = []
    scorecards: list[ScorecardResult] = []
```

### 4.5 Frontend Specifications
N/A — covered by TPRD-006.

### 4.6 Business Logic

**Enum Definitions:**
```python
class EntityStatus(str, Enum):
    ACTIVE = "active"
    PLANNED = "planned"
    MAINTENANCE = "maintenance"
    DEPRECATED = "deprecated"

class OperationalStatus(str, Enum):
    OPERATIONAL = "operational"
    DEGRADED = "degraded"
    OUTAGE = "outage"

class ServiceType(str, Enum):
    API = "api"
    WEB_APPLICATION = "web_application"
    DATABASE = "database"
    MESSAGE_QUEUE = "message_queue"
    CACHE = "cache"
    INFRASTRUCTURE = "infrastructure"

class ComponentType(str, Enum):
    LIBRARY = "library"
    MICROSERVICE = "microservice"
    SDK = "sdk"
    AGENT = "agent"
    UI_COMPONENT = "ui_component"

class ResourceType(str, Enum):
    EC2 = "ec2"
    VIRTUAL_MACHINE = "virtual_machine"
    LOGIC_APP = "logic_app"
    STORAGE_ACCOUNT = "storage_account"
    CONTAINER_INSTANCE = "container_instance"
    KUBERNETES = "kubernetes"
    FUNCTION_APP = "function_app"
    LOAD_BALANCER = "load_balancer"
    API_GATEWAY = "api_gateway"
    CDN = "cdn"

class RepositoryProvider(str, Enum):
    GITHUB = "github"
    GITLAB = "gitlab"
    AZURE_DEVOPS = "azure_devops"
    BITBUCKET = "bitbucket"

class IncidentSeverity(str, Enum):
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"

class IncidentStatus(str, Enum):
    INVESTIGATING = "investigating"
    IDENTIFIED = "identified"
    MONITORING = "monitoring"
    RESOLVED = "resolved"

class ImpactType(str, Enum):
    OUTAGE = "outage"
    DEGRADED = "degraded"

class UserRole(str, Enum):
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"
    INCIDENT_COMMANDER = "incident_commander"
```

## 5. SECURITY REQUIREMENTS

- All queries MUST be scoped by `tenant_id` — no cross-tenant data leakage
- Soft-deleted records (`deleted_at IS NOT NULL`) MUST be excluded from all default queries
- JSONB `attributes` columns MUST be validated against known type schemas before persistence
- `audit_logs` table MUST be append-only — no update/delete operations permitted
- User `password_hash` MUST use bcrypt with cost factor >= 12

## 6. TESTING REQUIREMENTS

### 6.1 Unit Tests
- Model creation and validation for each entity type
- Pydantic schema validation (valid and invalid inputs)
- Enum serialization/deserialization

### 6.2 Integration Tests
- CRUD operations via SQLAlchemy session for each entity
- Cascade delete behavior (e.g., deleting a scorecard deletes its criteria)
- Soft delete filtering
- Multi-tenant isolation (create entities in tenant A, verify not visible in tenant B)
- Unique constraint enforcement

### 6.3 Frontend Tests
N/A for this TPRD.

### 6.4 Security Tests
- Cross-tenant query attempt returns empty results
- Deleted records excluded from standard queries

## 7. NON-FUNCTIONAL REQUIREMENTS

- **Performance**: Single entity retrieval < 20ms; List queries with pagination < 100ms
- **Scalability**: Indexes support efficient queries up to 100K entities per type per tenant
- **Observability**: All SQL queries instrumented via OpenTelemetry SQLAlchemy integration

## 8. MIGRATION & DEPLOYMENT

- **Initial Migration**: Single Alembic migration creates all tables, indexes, and constraints
- **Rollback Plan**: `alembic downgrade base` drops all tables
- **Data Backfill**: Provide a `seed_sample_data.py` script that loads `sample-data.json` into the database

## 9. IMPLEMENTATION GUIDANCE FOR CODING AGENTS

### Implementation Order
1. Create enum modules (`backend/app/models/enums.py`)
2. Create base model mixin (`backend/app/models/base.py`)
3. Create association tables (`backend/app/models/associations.py`)
4. Create entity models in order: `tenant.py`, `user.py`, `team.py`, `person.py`, `product.py`, `service.py`, `component.py`, `resource.py`, `repository.py`, `incident.py`, `scorecard.py`, `audit_log.py`
5. Create Pydantic schemas matching each model
6. Generate Alembic migration: `alembic revision --autogenerate -m "initial_schema"`
7. Write tests

### File Creation Plan
```
backend/app/models/
  enums.py
  base.py
  associations.py
  tenant.py
  user.py
  team.py
  person.py
  product.py
  service.py
  component.py
  resource.py
  repository.py
  incident.py
  scorecard.py
  audit_log.py

backend/app/schemas/
  common.py
  tenant.py
  user.py
  team.py
  person.py
  product.py
  service.py
  component.py
  resource.py
  repository.py
  incident.py
  scorecard.py
  audit_log.py
```

### Do NOT
- Do NOT use Integer primary keys — all PKs are UUID
- Do NOT use eager loading by default — use `selectinload` explicitly where needed
- Do NOT create foreign keys to `entity_assignments.entity_id` — it is polymorphic
- Do NOT store computed scorecard results — they are always calculated on read
- Do NOT create separate tables for each service/component/resource type — use JSONB attributes

### Verify
- [ ] `alembic upgrade head` creates all tables without errors
- [ ] `alembic downgrade base` drops all tables cleanly
- [ ] All entities can be created, read, updated, soft-deleted via ORM
- [ ] Multi-tenant isolation works (entities only visible within their tenant)
- [ ] Cascade deletes work for scorecard → scorecard_criteria
- [ ] Unique constraints prevent duplicate names within a tenant
- [ ] JSONB attributes can store and retrieve type-specific data
- [ ] All Pydantic schemas validate sample data correctly

## 10. OPEN QUESTIONS

None — all data modeling decisions are finalized based on the POC analysis.
