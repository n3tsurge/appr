# AppInventory — Technical Product Requirements Documents

## Document Index

This directory contains the complete set of TPRDs for converting the AppInventory POC into an enterprise-grade application.

### Foundation

| ID | Document | Status | Complexity |
|----|----------|--------|------------|
| TPRD-001 | [Platform Foundation](TPRD-2026-02-18-platform-foundation.md) | Draft | L |
| TPRD-002 | [Core Data Models](TPRD-2026-02-18-core-data-models.md) | Draft | XL |
| TPRD-003 | [Authentication & Authorization](TPRD-2026-02-18-authentication-authorization.md) | Draft | L |

### APIs

| ID | Document | Status | Complexity |
|----|----------|--------|------------|
| TPRD-004 | [REST API — Catalog Entities](TPRD-2026-02-18-rest-api-catalog.md) | Draft | XL |
| TPRD-005 | [GraphQL API](TPRD-2026-02-18-graphql-api.md) | Draft | M |

### Frontend

| ID | Document | Status | Complexity |
|----|----------|--------|------------|
| TPRD-006 | [Frontend Application](TPRD-2026-02-18-frontend-application.md) | Draft | XL |

### Features

| ID | Document | Status | Complexity |
|----|----------|--------|------------|
| TPRD-007 | [Incident Management](TPRD-2026-02-18-incident-management.md) | Draft | L |
| TPRD-008 | [Scorecard Engine](TPRD-2026-02-18-scorecard-engine.md) | Draft | M |
| TPRD-009 | [Public Status Page](TPRD-2026-02-18-public-status-page.md) | Draft | S |
| TPRD-010 | [Dependency Graph Visualization](TPRD-2026-02-18-dependency-graph.md) | Draft | M |
| TPRD-011 | [Notifications](TPRD-2026-02-18-notifications.md) | Draft | M |

### Operations

| ID | Document | Status | Complexity |
|----|----------|--------|------------|
| TPRD-012 | [Observability & Audit](TPRD-2026-02-18-observability-audit.md) | Draft | M |

## Implementation Order

```
Phase 1 — Foundation (Weeks 1-3)
  ├── TPRD-001: Platform Foundation
  ├── TPRD-002: Core Data Models
  └── TPRD-003: Authentication & Authorization

Phase 2 — APIs (Weeks 4-6)
  ├── TPRD-004: REST API
  └── TPRD-005: GraphQL API

Phase 3 — Frontend (Weeks 5-9)
  └── TPRD-006: Frontend Application

Phase 4 — Features (Weeks 7-11)
  ├── TPRD-007: Incident Management
  ├── TPRD-008: Scorecard Engine
  ├── TPRD-009: Public Status Page
  └── TPRD-010: Dependency Graph

Phase 5 — Integration (Weeks 10-12)
  ├── TPRD-011: Notifications
  └── TPRD-012: Observability & Audit
```

## Cross-Cutting Concerns

All TPRDs inherit these requirements:

- **Multi-tenancy**: All database tables include `tenant_id`. Queries are scoped by tenant via middleware.
- **Audit**: All mutations are logged to the `audit_log` table.
- **Soft Deletes**: All entities use `deleted_at` instead of hard deletes.
- **UUID Primary Keys**: All entities use UUID v4.
- **Timestamps**: All tables include `created_at`, `updated_at`, `created_by`, `updated_by`.
- **ISO 27001 Compliance**: All features must be designed with ISO 27001 controls in mind.
