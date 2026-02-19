# TPRD-2026-02-18-incident-management

## 1. DOCUMENT METADATA

```
Document ID:    TPRD-2026-02-18-incident-management
Version:        1.0
Status:         Draft
Feature Name:   Incident Management
Parent TPRD:    TPRD-2026-02-18-platform-foundation
```

## 2. EXECUTIVE SUMMARY

- **Business Objective**: Provide a structured incident lifecycle that tracks disruptions, cascades operational status to affected entities, supports investigation/resolution workflows, and maintains a full timeline of actions for post-incident review.
- **Technical Scope**: Backend incident CRUD with lifecycle state machine, timeline entries, status cascading to affected entities, operational status recalculation on resolution. Frontend incident list, detail view with timeline, and entity impact panel.
- **Success Criteria**: Incident lifecycle matches the POC flow (investigating → identified → monitoring → resolved). Status cascading propagates within 1 second. Timeline provides complete audit trail for post-mortems.
- **Complexity Estimate**: L — State machine with cascading side effects, polymorphic affected entity relationships, timeline management.

## 3. SCOPE DEFINITION

### 3.1 In Scope
- Incident CRUD (create, read, update, delete)
- Incident lifecycle state machine: `investigating` → `identified` → `monitoring` → `resolved`
- Incident reopening: `resolved` → `investigating`
- Timeline entries: automated (status changes) + manual (user notes)
- Affected entity management: link services, components, resources to an incident
- Operational status cascading: when an incident is created/updated, affected entities' `operational_status` changes based on incident severity
- Operational status recalculation: when incident resolves, recalculate each affected entity's status based on remaining open incidents
- Incident severity levels: `minor`, `major`, `critical`
- Impact types: `performance`, `availability`, `data_integrity`, `security`
- Incident Commander role: authorized to advance incident status, update affected entities
- REST API endpoints for all incident operations
- Frontend: Incident list view, incident detail view with timeline, create/edit modals

### 3.2 Out of Scope
- Automated incident detection (PagerDuty/Datadog integration — future)
- SLA tracking and breach calculations
- Post-mortem templates
- Incident analytics / MTTR dashboards
- External notification (covered by TPRD-011)

### 3.3 Assumptions
- Only one operational_status per entity (not per-incident). Worst-case status wins.
- An entity can be affected by multiple concurrent incidents.
- Incident Commander is a dedicated RBAC role (not just an assignment).

### 3.4 Dependencies
- TPRD-2026-02-18-core-data-models (incidents, incident_timeline_entries, incident_affected_entities tables)
- TPRD-2026-02-18-rest-api-catalog (entity APIs for status updates)
- TPRD-2026-02-18-authentication-authorization (RBAC — Incident Commander role)

## 4. TECHNICAL SPECIFICATIONS

### 4.1 Technology Stack Declaration
Per `.github/technology-stack.yml`. No additions.

### 4.2 Incident Lifecycle State Machine

```
                    ┌─────────────────┐
                    │   investigating  │ ← create / reopen
                    └───────┬─────────┘
                            │ advance
                    ┌───────▼─────────┐
                    │   identified     │
                    └───────┬─────────┘
                            │ advance
                    ┌───────▼─────────┐
                    │   monitoring     │
                    └───────┬─────────┘
                            │ resolve
                    ┌───────▼─────────┐
                    │    resolved      │
                    └───────┬─────────┘
                            │ reopen
                    ┌───────▼─────────┐
                    │   investigating  │
                    └─────────────────┘
```

**Legal Transitions:**
| Current State | Allowed Next States |
|---------------|-------------------|
| investigating | identified, monitoring, resolved |
| identified | monitoring, resolved |
| monitoring | resolved |
| resolved | investigating (reopen) |

### 4.3 API Specifications

#### Incident CRUD

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| GET | /api/v1/incidents | ✅ | Any | List incidents (filterable by status, severity) |
| POST | /api/v1/incidents | ✅ | Editor+/IC | Create incident |
| GET | /api/v1/incidents/{id} | ✅ | Any | Get incident detail with timeline and affected entities |
| PUT | /api/v1/incidents/{id} | ✅ | Editor+/IC | Update incident metadata |
| DELETE | /api/v1/incidents/{id} | ✅ | Admin | Soft delete incident |

#### Incident Lifecycle Actions

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| POST | /api/v1/incidents/{id}/advance | ✅ | IC+/Admin | Advance status to next state |
| POST | /api/v1/incidents/{id}/resolve | ✅ | IC+/Admin | Resolve incident |
| POST | /api/v1/incidents/{id}/reopen | ✅ | IC+/Admin | Reopen resolved incident |

#### Timeline

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| GET | /api/v1/incidents/{id}/timeline | ✅ | Any | Get timeline entries |
| POST | /api/v1/incidents/{id}/timeline | ✅ | Editor+/IC | Add manual note to timeline |

#### Affected Entities

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| GET | /api/v1/incidents/{id}/affected | ✅ | Any | List affected entities |
| POST | /api/v1/incidents/{id}/affected | ✅ | Editor+/IC | Add affected entity |
| DELETE | /api/v1/incidents/{id}/affected/{entity_type}/{entity_id} | ✅ | Editor+/IC | Remove affected entity |

#### Request/Response Schemas

**POST /api/v1/incidents** (Create)
```json
Request:
{
  "title": "Core Database Degradation",
  "description": "PostgreSQL primary showing increased latency",
  "severity": "major",
  "impact_type": "performance",
  "affected_entities": [
    { "entity_type": "service", "entity_id": "uuid" },
    { "entity_type": "resource", "entity_id": "uuid" }
  ]
}

Response 201:
{
  "data": {
    "id": "uuid",
    "title": "Core Database Degradation",
    "description": "...",
    "severity": "major",
    "status": "investigating",
    "impact_type": "performance",
    "started_at": "2026-02-18T12:00:00Z",
    "resolved_at": null,
    "affected_entities": [
      { "entity_type": "service", "entity_id": "uuid", "entity_name": "Customer API" },
      { "entity_type": "resource", "entity_id": "uuid", "entity_name": "prod-pg-primary" }
    ],
    "timeline": [
      {
        "id": "uuid",
        "type": "status_change",
        "content": "Incident created with status: investigating",
        "created_at": "2026-02-18T12:00:00Z",
        "created_by": "uuid",
        "created_by_name": "Alice Chen"
      }
    ],
    "created_at": "2026-02-18T12:00:00Z",
    "created_by": "uuid"
  }
}
```

**POST /api/v1/incidents/{id}/advance**
```json
Request:
{
  "note": "Root cause identified: connection pool exhaustion on primary DB"
}

Response 200:
{
  "data": {
    "id": "uuid",
    "status": "identified",
    "previous_status": "investigating",
    "timeline_entry": {
      "id": "uuid",
      "type": "status_change",
      "content": "Status changed from investigating to identified. Root cause identified: connection pool exhaustion on primary DB",
      "created_at": "2026-02-18T12:15:00Z",
      "created_by_name": "Alice Chen"
    }
  }
}
```

**POST /api/v1/incidents/{id}/resolve**
```json
Request:
{
  "note": "Connection pool limits adjusted. Monitoring shows normal latency restored."
}

Response 200:
{
  "data": {
    "id": "uuid",
    "status": "resolved",
    "resolved_at": "2026-02-18T14:00:00Z",
    "duration_minutes": 120,
    "affected_entities_status": [
      { "entity_type": "service", "entity_id": "uuid", "entity_name": "Customer API", "new_status": "operational" },
      { "entity_type": "resource", "entity_id": "uuid", "entity_name": "prod-pg-primary", "new_status": "operational" }
    ]
  }
}
```

### 4.4 Business Logic

#### Status Cascading on Incident Creation/Update

When an incident is created or affected entities are added:

1. For each affected entity:
   a. Determine new `operational_status` based on incident severity:
      - `critical` → `major_outage`
      - `major` → `degraded`
      - `minor` → `degraded`
   b. If entity's current `operational_status` is already worse than the proposed status, keep the worse status
   c. Update entity's `operational_status`
   d. Create audit log entry

**Status Severity Ranking** (worst to best):
1. `major_outage`
2. `partial_outage`
3. `degraded`
4. `operational`

#### Status Recalculation on Incident Resolution

When an incident is resolved:

1. For each affected entity:
   a. Query all OTHER active (non-resolved) incidents that affected this entity
   b. If no other active incidents: set `operational_status` = `operational`
   c. If other active incidents: set `operational_status` = worst status from remaining incidents (using severity-to-status mapping above)
   d. Update entity's `operational_status`
   e. Create audit log entry

**Python pseudocode (from POC `recalcEntityStatus`):**
```python
async def recalculate_entity_status(
    entity_type: str,
    entity_id: UUID,
    excluding_incident_id: UUID,
    session: AsyncSession,
) -> OperationalStatus:
    """Recalculate entity's operational status based on remaining active incidents."""
    active_incidents = await session.execute(
        select(Incident)
        .join(IncidentAffectedEntity)
        .where(
            IncidentAffectedEntity.entity_type == entity_type,
            IncidentAffectedEntity.entity_id == entity_id,
            Incident.id != excluding_incident_id,
            Incident.status != IncidentStatus.RESOLVED,
            Incident.deleted_at.is_(None),
        )
    )
    incidents = active_incidents.scalars().all()

    if not incidents:
        return OperationalStatus.OPERATIONAL

    worst = OperationalStatus.OPERATIONAL
    for incident in incidents:
        status = severity_to_operational_status(incident.severity)
        if STATUS_RANKING[status] < STATUS_RANKING[worst]:
            worst = status
    return worst
```

#### Timeline Entry Auto-Generation

The system MUST automatically create timeline entries for:
- Incident creation
- Status changes (advance, resolve, reopen)
- Affected entity additions/removals
- Severity changes

Manual entries MUST be created via the `/timeline` POST endpoint.

### 4.5 Frontend Specifications

#### Incident List View
- Table columns: Severity (icon + color), Title, Status (badge), Affected Entities (count), Started, Duration
- Filters: Status (active, resolved, all), Severity (minor, major, critical)
- Default sort: Active incidents first, then by started_at descending
- Active incidents highlighted with left border color by severity

#### Incident Detail View
- **Header**: Title, severity badge, status badge, action buttons (Advance, Resolve, Reopen — based on current status and user role)
- **Info Panel**: Description, impact type, started_at, resolved_at, duration, created_by
- **Affected Entities Panel**: List of affected entities with operational status badges, remove button (IC+), add entity button (IC+)
- **Timeline Panel**: Chronological list of timeline entries
  - Status changes: icon + colored text
  - Manual notes: user avatar + text
  - Entity changes: "Added/Removed [Entity Name]"
  - Each entry shows timestamp and author
  - "Add Note" button at top of timeline
- **Add Note Modal**: Textarea for note content, submit button

#### Incident Create Modal
- Title (required)
- Description (required)
- Severity dropdown (minor, major, critical)
- Impact type dropdown (performance, availability, data_integrity, security)
- Affected entities multi-select (searchable, grouped by type)

## 5. SECURITY REQUIREMENTS

- Incident creation requires Editor or Incident Commander role
- Lifecycle actions (advance, resolve, reopen) require Incident Commander or Admin
- Timeline notes can be added by Editor, Incident Commander, or Admin
- Deleting incidents requires Admin role
- All incident mutations MUST create audit log entries
- Affected entity status changes MUST be logged

## 6. TESTING REQUIREMENTS

### 6.1 Unit Tests
- State machine: test all valid transitions succeed, all invalid transitions raise error
- Status cascading: test severity-to-status mapping for all combinations
- Status recalculation: test with 0, 1, and multiple remaining active incidents
- Timeline auto-generation: verify entries created for each action type

### 6.2 Integration Tests
- Full incident lifecycle: create → advance (×3) → resolve
- Reopen flow: resolve → reopen → advance → resolve
- Multi-incident scenario: 2 incidents on same entity; resolve one, verify status recalculation
- Adding/removing affected entities mid-incident
- RBAC: verify IC can advance, Editor cannot advance, Viewer cannot create

### 6.3 Frontend Tests
- Incident list: verify filtering by status, sorting
- Incident detail: verify timeline rendering, action buttons visibility by role
- Create modal: verify form validation, entity multi-select

## 7. NON-FUNCTIONAL REQUIREMENTS

- **Performance**: Status cascading completes within 1 second for up to 50 affected entities
- **Consistency**: Status changes are atomic — either all affected entities update or none do (database transaction)
- **Observability**: Incident creation/resolution emits structured log with severity, affected entity count, duration

## 8. MIGRATION & DEPLOYMENT

- No additional migrations beyond TPRD-002
- Feature flag: N/A — core functionality

## 9. IMPLEMENTATION GUIDANCE FOR CODING AGENTS

### Implementation Order
1. Create incident service with lifecycle state machine
2. Create status cascading service
3. Create timeline service
4. Create incident API routes
5. Create frontend incident store
6. Create frontend incident list view
7. Create frontend incident detail view with timeline
8. Create incident create/edit modals
9. Write tests

### File Creation Plan

**Backend:**
```
backend/app/services/incident_service.py       # CRUD + lifecycle + status cascading
backend/app/services/status_cascade_service.py  # Operational status cascading logic
backend/app/repositories/incident_repository.py
backend/app/api/v1/incidents.py
backend/app/schemas/incident.py                 # Pydantic schemas
```

**Frontend:**
```
frontend/src/api/incidents.ts
frontend/src/stores/incidents.ts
frontend/src/types/incident.ts
frontend/src/views/IncidentListView.vue
frontend/src/views/IncidentDetailView.vue
frontend/src/components/incidents/IncidentTimeline.vue
frontend/src/components/incidents/IncidentStatusBadge.vue
frontend/src/components/incidents/IncidentCreateModal.vue
frontend/src/components/incidents/AffectedEntitiesPanel.vue
frontend/src/components/incidents/TimelineEntry.vue
frontend/src/components/incidents/AddNoteModal.vue
```

### Do NOT
- Do NOT allow skipping states in the lifecycle (e.g., investigating → resolved is allowed, but not identified → investigating)
- Do NOT cascade status changes outside of a database transaction
- Do NOT allow status recalculation to set an entity to a BETTER status than warranted by other active incidents
- Do NOT hard-delete timeline entries — they are immutable audit records

### Verify
- [ ] All lifecycle transitions work correctly
- [ ] Invalid transitions return 422 with clear error
- [ ] Status cascading updates all affected entities' operational_status
- [ ] Resolution recalculates status correctly with multiple concurrent incidents
- [ ] Timeline entries are created automatically for all state changes
- [ ] Manual notes appear in timeline
- [ ] RBAC enforced: only IC/Admin can advance/resolve/reopen
- [ ] Frontend action buttons respect user role

## 10. OPEN QUESTIONS

None.
