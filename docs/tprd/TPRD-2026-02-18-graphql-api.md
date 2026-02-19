# TPRD-2026-02-18-graphql-api

## 1. DOCUMENT METADATA

```
Document ID:    TPRD-2026-02-18-graphql-api
Version:        1.0
Status:         Draft
Feature Name:   GraphQL API — Relationship Queries
Parent TPRD:    TPRD-2026-02-18-platform-foundation
```

## 2. EXECUTIVE SUMMARY

- **Business Objective**: Provide a flexible query language for exploring complex entity relationships—dependency chains, impact analysis, and graph traversal—that are cumbersome with fixed REST endpoints.
- **Technical Scope**: Strawberry GraphQL schema exposing all catalog entities with full relationship traversal, plus specialized queries for dependency graph data, impact analysis (upstream/downstream), and scorecard evaluation results.
- **Success Criteria**: Frontend dependency graph can be populated with a single GraphQL query. Nested relationship queries resolve within 200ms for up to 3 levels of depth. N+1 query problem eliminated via DataLoaders.
- **Complexity Estimate**: L — The schema mirrors existing data models but requires careful DataLoader design, depth limiting, and complexity analysis.

## 3. SCOPE DEFINITION

### 3.1 In Scope
- Strawberry GraphQL schema for all entity types
- Relationship traversal up to configurable depth (default: 3 levels)
- `dependencyGraph` query: returns all nodes and edges for D3.js visualization
- `impactAnalysis` query: given an entity, return all upstream and downstream dependencies
- `serviceHealth` query: aggregate operational status across a product's services
- DataLoaders for all relationships to prevent N+1 queries
- Query complexity analysis and depth limiting
- Authentication via JWT (same as REST)
- Tenant scoping on all resolvers

### 3.2 Out of Scope
- GraphQL mutations (all writes go through REST API, per tech stack decision)
- Subscriptions (future consideration)
- Federation (single service, not needed yet)
- File uploads via GraphQL

### 3.3 Assumptions
- GraphQL is read-only. All mutations happen via REST endpoints.
- Maximum query depth of 5 levels prevents abuse.
- Maximum query complexity score of 1000 prevents expensive queries.

### 3.4 Dependencies
- TPRD-2026-02-18-core-data-models (all entity models)
- TPRD-2026-02-18-authentication-authorization (JWT validation)

## 4. TECHNICAL SPECIFICATIONS

### 4.1 Technology Stack Declaration
Per `.github/technology-stack.yml`:
- **Strawberry** for GraphQL schema definition
- **strawberry-sqlalchemy** integration for model mapping
- Served via FastAPI's Strawberry integration at `/graphql`

### 4.2 Architecture & Design Patterns

**Schema Structure:**
```
backend/app/graphql/
  schema.py              # Root schema combining all types
  types/
    __init__.py
    team.py              # TeamType
    person.py            # PersonType
    product.py           # ProductType
    service.py           # ServiceType
    component.py         # ComponentType
    resource.py          # ResourceType
    repository.py        # RepositoryType
    incident.py          # IncidentType (read-only summary)
    scorecard.py         # ScorecardType + evaluation result
    enums.py             # All enum types
    common.py            # PageInfo, Connection, Edge
  queries/
    __init__.py
    catalog.py           # Entity list/detail queries
    graph.py             # dependencyGraph, impactAnalysis
    health.py            # serviceHealth
  dataloaders/
    __init__.py
    entity_loaders.py    # DataLoaders for each entity type
    relationship_loaders.py  # DataLoaders for M:M relationships
  middleware/
    complexity.py        # Query complexity analysis
    depth_limit.py       # Max depth enforcement
```

**DataLoader Pattern:**
Every relationship resolver uses a DataLoader to batch and cache database queries within a single request. DataLoaders are created per-request via Strawberry context.

### 4.3 GraphQL Schema Definition

#### Entity Types

```python
import strawberry
from uuid import UUID
from datetime import datetime
from typing import Optional

@strawberry.type
class TeamType:
    id: UUID
    name: str
    description: Optional[str]
    created_at: datetime
    updated_at: datetime

    @strawberry.field
    async def members(self, info) -> list["PersonType"]:
        loader = info.context["person_by_team_loader"]
        return await loader.load(self.id)

    @strawberry.field
    async def services(self, info) -> list["ServiceType"]:
        loader = info.context["services_by_team_loader"]
        return await loader.load(self.id)


@strawberry.type
class PersonType:
    id: UUID
    name: str
    email: Optional[str]
    role: Optional[str]
    team_id: Optional[UUID]
    created_at: datetime

    @strawberry.field
    async def team(self, info) -> Optional[TeamType]:
        if not self.team_id:
            return None
        loader = info.context["team_loader"]
        return await loader.load(self.team_id)

    @strawberry.field
    async def assignments(self, info) -> list["EntityAssignmentType"]:
        loader = info.context["assignments_by_person_loader"]
        return await loader.load(self.id)


@strawberry.type
class ProductType:
    id: UUID
    name: str
    description: Optional[str]
    status: str
    team_id: Optional[UUID]
    created_at: datetime
    updated_at: datetime

    @strawberry.field
    async def team(self, info) -> Optional[TeamType]:
        if not self.team_id:
            return None
        loader = info.context["team_loader"]
        return await loader.load(self.team_id)

    @strawberry.field
    async def services(self, info) -> list["ServiceType"]:
        loader = info.context["services_by_product_loader"]
        return await loader.load(self.id)

    @strawberry.field
    async def assignments(self, info) -> list["EntityAssignmentType"]:
        loader = info.context["assignments_by_entity_loader"]
        return await loader.load(("product", self.id))


@strawberry.type
class ServiceType:
    id: UUID
    name: str
    type: str  # ServiceTypeEnum
    description: Optional[str]
    status: str
    operational_status: str
    team_id: Optional[UUID]
    attributes: Optional[strawberry.scalars.JSON]
    created_at: datetime
    updated_at: datetime

    @strawberry.field
    async def team(self, info) -> Optional[TeamType]:
        if not self.team_id:
            return None
        return await info.context["team_loader"].load(self.team_id)

    @strawberry.field
    async def products(self, info) -> list[ProductType]:
        return await info.context["products_by_service_loader"].load(self.id)

    @strawberry.field
    async def components(self, info) -> list["ComponentType"]:
        return await info.context["components_by_service_loader"].load(self.id)

    @strawberry.field
    async def resources(self, info) -> list["ResourceType"]:
        return await info.context["resources_by_service_loader"].load(self.id)

    @strawberry.field
    async def depends_on(self, info) -> list["ServiceType"]:
        return await info.context["service_dependencies_loader"].load(self.id)

    @strawberry.field
    async def dependents(self, info) -> list["ServiceType"]:
        return await info.context["service_dependents_loader"].load(self.id)

    @strawberry.field
    async def repositories(self, info) -> list["RepositoryType"]:
        return await info.context["repositories_by_service_loader"].load(self.id)

    @strawberry.field
    async def assignments(self, info) -> list["EntityAssignmentType"]:
        return await info.context["assignments_by_entity_loader"].load(("service", self.id))

    @strawberry.field
    async def active_incidents(self, info) -> list["IncidentSummaryType"]:
        return await info.context["active_incidents_by_entity_loader"].load(("service", self.id))


@strawberry.type
class ComponentType:
    id: UUID
    name: str
    type: str  # ComponentTypeEnum
    description: Optional[str]
    status: str
    operational_status: str
    team_id: Optional[UUID]
    attributes: Optional[strawberry.scalars.JSON]
    created_at: datetime
    updated_at: datetime

    @strawberry.field
    async def team(self, info) -> Optional[TeamType]:
        if not self.team_id:
            return None
        return await info.context["team_loader"].load(self.team_id)

    @strawberry.field
    async def services(self, info) -> list[ServiceType]:
        return await info.context["services_by_component_loader"].load(self.id)

    @strawberry.field
    async def depends_on_components(self, info) -> list["ComponentType"]:
        return await info.context["component_dependencies_loader"].load(self.id)

    @strawberry.field
    async def depends_on_services(self, info) -> list[ServiceType]:
        return await info.context["component_service_dependencies_loader"].load(self.id)

    @strawberry.field
    async def repositories(self, info) -> list["RepositoryType"]:
        return await info.context["repositories_by_component_loader"].load(self.id)


@strawberry.type
class ResourceType:
    id: UUID
    name: str
    type: str  # ResourceTypeEnum
    description: Optional[str]
    status: str
    operational_status: str
    environment: Optional[str]
    team_id: Optional[UUID]
    attributes: Optional[strawberry.scalars.JSON]
    created_at: datetime
    updated_at: datetime

    @strawberry.field
    async def team(self, info) -> Optional[TeamType]:
        if not self.team_id:
            return None
        return await info.context["team_loader"].load(self.team_id)

    @strawberry.field
    async def services(self, info) -> list[ServiceType]:
        return await info.context["services_by_resource_loader"].load(self.id)


@strawberry.type
class RepositoryType:
    id: UUID
    name: str
    url: Optional[str]
    provider: str  # github | azure_devops
    default_branch: Optional[str]
    language: Optional[str]
    team_id: Optional[UUID]
    created_at: datetime

    @strawberry.field
    async def team(self, info) -> Optional[TeamType]:
        if not self.team_id:
            return None
        return await info.context["team_loader"].load(self.team_id)


@strawberry.type
class EntityAssignmentType:
    person_id: UUID
    person_name: str
    entity_type: str
    entity_id: UUID
    entity_name: str
    role: str


@strawberry.type
class IncidentSummaryType:
    id: UUID
    title: str
    severity: str
    status: str
    started_at: datetime
```

#### Specialized Graph Types

```python
@strawberry.type
class GraphNode:
    id: UUID
    name: str
    entity_type: str  # "service" | "component" | "resource" | "product"
    operational_status: str
    type_detail: Optional[str]  # e.g., "api", "library", "kubernetes"

@strawberry.type
class GraphEdge:
    source_id: UUID
    target_id: UUID
    relationship: str  # "depends_on" | "contains" | "uses" | "assigned_to"

@strawberry.type
class DependencyGraph:
    nodes: list[GraphNode]
    edges: list[GraphEdge]

@strawberry.type
class ImpactAnalysisResult:
    entity: GraphNode
    upstream: list[GraphNode]    # Things this entity depends on
    downstream: list[GraphNode]  # Things that depend on this entity
    graph: DependencyGraph       # Full subgraph for visualization

@strawberry.type
class ServiceHealthSummary:
    product_id: UUID
    product_name: str
    total_services: int
    operational: int
    degraded: int
    outage: int
    overall_status: str  # worst status across services
```

#### Root Queries

```python
@strawberry.type
class Query:
    # === Catalog Queries ===
    @strawberry.field
    async def teams(
        self, info,
        search: Optional[str] = None,
        limit: int = 25,
        offset: int = 0,
    ) -> list[TeamType]: ...

    @strawberry.field
    async def team(self, info, id: UUID) -> Optional[TeamType]: ...

    @strawberry.field
    async def people(
        self, info,
        team_id: Optional[UUID] = None,
        search: Optional[str] = None,
        limit: int = 25,
        offset: int = 0,
    ) -> list[PersonType]: ...

    @strawberry.field
    async def person(self, info, id: UUID) -> Optional[PersonType]: ...

    @strawberry.field
    async def products(
        self, info,
        status: Optional[str] = None,
        team_id: Optional[UUID] = None,
        search: Optional[str] = None,
        limit: int = 25,
        offset: int = 0,
    ) -> list[ProductType]: ...

    @strawberry.field
    async def product(self, info, id: UUID) -> Optional[ProductType]: ...

    @strawberry.field
    async def services(
        self, info,
        type: Optional[str] = None,
        status: Optional[str] = None,
        operational_status: Optional[str] = None,
        team_id: Optional[UUID] = None,
        search: Optional[str] = None,
        limit: int = 25,
        offset: int = 0,
    ) -> list[ServiceType]: ...

    @strawberry.field
    async def service(self, info, id: UUID) -> Optional[ServiceType]: ...

    @strawberry.field
    async def components(
        self, info,
        type: Optional[str] = None,
        operational_status: Optional[str] = None,
        team_id: Optional[UUID] = None,
        search: Optional[str] = None,
        limit: int = 25,
        offset: int = 0,
    ) -> list[ComponentType]: ...

    @strawberry.field
    async def component(self, info, id: UUID) -> Optional[ComponentType]: ...

    @strawberry.field
    async def resources(
        self, info,
        type: Optional[str] = None,
        environment: Optional[str] = None,
        operational_status: Optional[str] = None,
        team_id: Optional[UUID] = None,
        search: Optional[str] = None,
        limit: int = 25,
        offset: int = 0,
    ) -> list[ResourceType]: ...

    @strawberry.field
    async def resource(self, info, id: UUID) -> Optional[ResourceType]: ...

    @strawberry.field
    async def repositories(
        self, info,
        provider: Optional[str] = None,
        language: Optional[str] = None,
        team_id: Optional[UUID] = None,
        search: Optional[str] = None,
        limit: int = 25,
        offset: int = 0,
    ) -> list[RepositoryType]: ...

    @strawberry.field
    async def repository(self, info, id: UUID) -> Optional[RepositoryType]: ...

    # === Graph Queries ===
    @strawberry.field
    async def dependency_graph(
        self, info,
        product_id: Optional[UUID] = None,  # Scope to a product
    ) -> DependencyGraph: ...

    @strawberry.field
    async def impact_analysis(
        self, info,
        entity_type: str,   # "service" | "component" | "resource"
        entity_id: UUID,
        depth: int = 3,     # Max traversal depth
    ) -> ImpactAnalysisResult: ...

    @strawberry.field
    async def service_health(
        self, info,
        product_id: UUID,
    ) -> ServiceHealthSummary: ...
```

### 4.4 DataLoader Specifications

| Loader Name | Key Type | Returns | Source |
|-------------|----------|---------|--------|
| team_loader | UUID | TeamType | teams table |
| person_loader | UUID | PersonType | people table |
| person_by_team_loader | UUID (team_id) | list[PersonType] | people WHERE team_id |
| services_by_team_loader | UUID (team_id) | list[ServiceType] | services WHERE team_id |
| services_by_product_loader | UUID (product_id) | list[ServiceType] | product_services join |
| services_by_component_loader | UUID (component_id) | list[ServiceType] | service_components join |
| services_by_resource_loader | UUID (resource_id) | list[ServiceType] | service_resources join |
| components_by_service_loader | UUID (service_id) | list[ComponentType] | service_components join |
| resources_by_service_loader | UUID (service_id) | list[ResourceType] | service_resources join |
| service_dependencies_loader | UUID (service_id) | list[ServiceType] | service_dependencies (source) |
| service_dependents_loader | UUID (service_id) | list[ServiceType] | service_dependencies (target) |
| component_dependencies_loader | UUID (component_id) | list[ComponentType] | component_dependencies (source) |
| component_service_dependencies_loader | UUID (component_id) | list[ServiceType] | component_service_dependencies |
| products_by_service_loader | UUID (service_id) | list[ProductType] | product_services join |
| repositories_by_service_loader | UUID (service_id) | list[RepositoryType] | service_repositories join |
| repositories_by_component_loader | UUID (component_id) | list[RepositoryType] | component_repositories join |
| assignments_by_entity_loader | (type, UUID) | list[EntityAssignmentType] | entity_assignments |
| assignments_by_person_loader | UUID (person_id) | list[EntityAssignmentType] | entity_assignments |
| active_incidents_by_entity_loader | (type, UUID) | list[IncidentSummaryType] | incident_affected_entities join |

### 4.5 Graph Query Implementation Logic

#### `dependency_graph` Query
1. If `product_id` provided, fetch only services linked to that product
2. Otherwise, fetch all active services, components, and resources for the tenant
3. For each service: fetch `depends_on` and `components` and `resources`
4. For each component: fetch `depends_on_components` and `depends_on_services`
5. Build `GraphNode` list (deduplicated by ID)
6. Build `GraphEdge` list from all relationships
7. Return `DependencyGraph`

**SQL Strategy**: Use 3 batch queries (services + deps, components + deps, resources) rather than N+1 individual queries. All queries scoped by `tenant_id` and `deleted_at IS NULL`.

#### `impact_analysis` Query
1. Start with the target entity
2. Traverse upstream (what it depends on) to `depth` levels using recursive CTE:
   ```sql
   WITH RECURSIVE upstream AS (
     SELECT target_service_id AS id, 1 AS depth
     FROM service_dependencies
     WHERE source_service_id = :entity_id
     UNION ALL
     SELECT sd.target_service_id, u.depth + 1
     FROM service_dependencies sd
     JOIN upstream u ON sd.source_service_id = u.id
     WHERE u.depth < :max_depth
   )
   SELECT DISTINCT id FROM upstream;
   ```
3. Traverse downstream (what depends on this) similarly
4. Build subgraph from all discovered entities

### 4.6 Query Complexity & Depth Limiting

**Depth Limit**: Maximum 5 levels of nested resolution. Enforced via Strawberry extension.

**Complexity Scoring**:
| Field Type | Cost |
|-----------|------|
| Scalar field | 0 |
| Single object | 1 |
| List (no limit) | 10 × child cost |
| List (with limit) | limit × child cost |

**Maximum Complexity**: 1000 per query. Exceeding returns:
```json
{
  "errors": [{
    "message": "Query complexity 1250 exceeds maximum allowed complexity of 1000",
    "extensions": { "code": "QUERY_TOO_COMPLEX" }
  }]
}
```

## 5. SECURITY REQUIREMENTS

- GraphQL endpoint MUST require JWT authentication
- All resolvers MUST scope queries by `tenant_id` from JWT
- Introspection MUST be disabled in production
- Query depth and complexity limits MUST be enforced before execution
- No mutations allowed — enforce at schema level (no `Mutation` type)
- Rate limiting: 30 requests/minute per user

## 6. TESTING REQUIREMENTS

### 6.1 Unit Tests
- Each DataLoader: verify batching (1 SQL query for N keys)
- Complexity calculator: verify scoring for sample queries
- Depth limiter: verify rejection at depth > 5
- Graph builder: verify node/edge generation from mock data

### 6.2 Integration Tests
- `dependency_graph` query: verify correct nodes and edges for sample data
- `dependency_graph` with `product_id` filter: verify scoped results
- `impact_analysis` query: verify upstream/downstream traversal
- `service_health` query: verify status aggregation
- Nested query (3 levels): product → services → components → repositories
- Verify N+1 prevention: capture SQL query count, assert bounded
- Auth: verify 401 without token, verify tenant isolation

### 6.3 Performance Tests
- `dependency_graph` with 100 services, 200 components, 500 edges: < 200ms
- Nested 3-level query with 50 entities: < 150ms

## 7. NON-FUNCTIONAL REQUIREMENTS

- **Performance**: Graph query < 200ms for typical (< 200 nodes) graphs
- **Scalability**: Complexity limits prevent abuse; DataLoaders prevent N+1
- **Availability**: GraphQL errors return partial data where possible
- **Observability**: Log query complexity score, execution time, user_id

## 8. MIGRATION & DEPLOYMENT

- No database migrations needed beyond TPRD-002
- Mount GraphQL endpoint at `/graphql` in FastAPI app
- GraphiQL playground enabled in development, disabled in production

## 9. IMPLEMENTATION GUIDANCE FOR CODING AGENTS

### Implementation Order
1. Create GraphQL type definitions (`types/`)
2. Create DataLoaders (`dataloaders/`)
3. Create catalog queries (`queries/catalog.py`)
4. Create graph queries (`queries/graph.py`)
5. Create health queries (`queries/health.py`)
6. Assemble root schema (`schema.py`)
7. Add complexity and depth middleware
8. Mount in FastAPI app
9. Write tests

### File Creation Plan
```
backend/app/graphql/
  __init__.py
  schema.py
  types/
    __init__.py
    common.py
    enums.py
    team.py
    person.py
    product.py
    service.py
    component.py
    resource.py
    repository.py
    incident.py
    scorecard.py
  queries/
    __init__.py
    catalog.py
    graph.py
    health.py
  dataloaders/
    __init__.py
    entity_loaders.py
    relationship_loaders.py
  middleware/
    __init__.py
    complexity.py
    depth_limit.py
```

### Do NOT
- Do NOT define any mutations — all writes go through REST API
- Do NOT enable introspection in production
- Do NOT resolve relationships without DataLoaders
- Do NOT allow unbounded list queries — enforce `limit` parameter (max 100)
- Do NOT return soft-deleted entities in any resolver

### Verify
- [ ] All entity types are queryable with relationship traversal
- [ ] DataLoaders batch queries (verify SQL count in tests)
- [ ] `dependency_graph` returns correct structure for D3.js consumption
- [ ] `impact_analysis` correctly traverses upstream/downstream
- [ ] Depth limit rejects queries deeper than 5 levels
- [ ] Complexity limit rejects expensive queries
- [ ] Introspection disabled in production config
- [ ] All resolvers scope by tenant_id

## 10. OPEN QUESTIONS

None.
