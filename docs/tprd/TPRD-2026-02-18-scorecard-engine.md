# TPRD-2026-02-18-scorecard-engine

## 1. DOCUMENT METADATA

```
Document ID:    TPRD-2026-02-18-scorecard-engine
Version:        1.0
Status:         Draft
Feature Name:   Scorecard Engine
Parent TPRD:    TPRD-2026-02-18-platform-foundation
```

## 2. EXECUTIVE SUMMARY

- **Business Objective**: Enforce organizational standards and best practices by evaluating entities against configurable scorecards. Scorecards provide visibility into compliance gaps and guide teams toward improving service maturity, documentation, and operational readiness.
- **Technical Scope**: Scorecard definition CRUD, criteria types, a server-side evaluation engine that scores entities on-read, grading (A–F), and frontend scorecard views with detailed evaluation breakdowns.
- **Success Criteria**: All 10 check types from the POC are supported. Evaluation results computed in < 50ms per entity. Scorecards applicable to multiple entity types simultaneously.
- **Complexity Estimate**: L — Complex evaluation engine with 10+ criterion types, weighted scoring, and polymorphic entity evaluation.

## 3. SCOPE DEFINITION

### 3.1 In Scope
- Scorecard CRUD (create, read, update, delete)
- Criteria definition with configurable check types and weights
- Entity type targeting (a scorecard applies to one or more entity types)
- Server-side evaluation engine (compute on-read, no stored results)
- Grading scale: A (90–100), B (80–89), C (70–79), D (60–69), F (0–59)
- Color coding: A=green, B=blue, C=yellow, D=orange, F=red
- Scorecard list view: all scorecards with aggregate pass/fail stats
- Scorecard detail view: per-entity evaluation results
- Entity detail integration: show scorecard results in entity detail view
- 10 criterion check types (from POC)

### 3.2 Out of Scope
- Historical score tracking / trend analysis
- Automated remediation
- Custom scripted checks (only built-in check types)
- Notification on score degradation (TPRD-011 will handle)

### 3.3 Assumptions
- Evaluation is computed on every read (not stored). This is acceptable given expected data volumes (< 10,000 entities).
- Weights are relative — they are normalized during scoring.
- Scorecards are defined by Admins and Editors; results are visible to all authenticated users.

### 3.4 Dependencies
- TPRD-2026-02-18-core-data-models (scorecards, scorecard_criteria tables)
- TPRD-2026-02-18-rest-api-catalog (entity data for evaluation)

## 4. TECHNICAL SPECIFICATIONS

### 4.1 Technology Stack Declaration
Per `.github/technology-stack.yml`. No additions.

### 4.2 Criterion Check Types

| Check Type | Description | Config Fields | Evaluation Logic |
|-----------|-------------|---------------|-----------------|
| `hasField` | Entity has a non-empty value for a specified field | `field: string` | `entity[field]` is not null/empty |
| `hasItems` | Entity has at least one item in a relationship list | `relationship: string` | `len(entity.relationship) > 0` |
| `minItems` | Entity has at least N items in a relationship list | `relationship: string, min: int` | `len(entity.relationship) >= min` |
| `fieldEquals` | Entity field equals a specific value | `field: string, value: any` | `entity[field] == value` |
| `fieldNotEquals` | Entity field does not equal a specific value | `field: string, value: any` | `entity[field] != value` |
| `hasAssignment` | Entity has at least one person assigned with a specific role | `role: string` | Any assignment with matching role |
| `minAssignments` | Entity has at least N total assignments | `min: int` | `len(entity.assignments) >= min` |
| `noActiveIncidents` | Entity has no active (unresolved) incidents | _(none)_ | No rows in incident_affected_entities for active incidents |
| `hasTag` | Entity has a specific key in its `attributes` JSON | `key: string` | `key in entity.attributes` |
| `attributeEquals` | A specific attribute key equals a specific value | `key: string, value: any` | `entity.attributes[key] == value` |

### 4.3 Data Models (Supplement to TPRD-002)

Already defined in TPRD-002. Key fields:

**scorecards table:**
- `id`, `tenant_id`, `name`, `description`, `entity_types` (ARRAY of strings — e.g., `["service", "component"]`), `status` (active/draft), standard audit fields

**scorecard_criteria table:**
- `id`, `scorecard_id` (FK), `name`, `description`, `check_type` (enum), `config` (JSONB), `weight` (integer, 1–100), `order` (integer for display)

### 4.4 API Specifications

#### Scorecard CRUD

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| GET | /api/v1/scorecards | ✅ | Any | List scorecards with aggregate stats |
| POST | /api/v1/scorecards | ✅ | Editor+ | Create scorecard |
| GET | /api/v1/scorecards/{id} | ✅ | Any | Get scorecard detail with criteria |
| PUT | /api/v1/scorecards/{id} | ✅ | Editor+ | Update scorecard |
| DELETE | /api/v1/scorecards/{id} | ✅ | Admin | Soft delete scorecard |

#### Evaluation Endpoints

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| GET | /api/v1/scorecards/{id}/evaluate | ✅ | Any | Evaluate all applicable entities against this scorecard |
| GET | /api/v1/scorecards/{id}/evaluate/{entity_type}/{entity_id} | ✅ | Any | Evaluate a single entity against this scorecard |
| GET | /api/v1/entities/{entity_type}/{entity_id}/scorecards | ✅ | Any | Get all scorecard results for an entity |

#### Request/Response Schemas

**POST /api/v1/scorecards** (Create)
```json
Request:
{
  "name": "Service Readiness",
  "description": "Evaluates whether a service meets production readiness standards",
  "entity_types": ["service"],
  "criteria": [
    {
      "name": "Has Description",
      "description": "Service must have a description",
      "check_type": "hasField",
      "config": { "field": "description" },
      "weight": 10
    },
    {
      "name": "Has Components",
      "description": "Service must have at least one component",
      "check_type": "hasItems",
      "config": { "relationship": "components" },
      "weight": 20
    },
    {
      "name": "Has On-Call",
      "description": "Service must have on-call assignment",
      "check_type": "hasAssignment",
      "config": { "role": "On-Call" },
      "weight": 30
    },
    {
      "name": "Is Operational",
      "description": "Service must not have active incidents",
      "check_type": "noActiveIncidents",
      "config": {},
      "weight": 25
    },
    {
      "name": "Has Repository",
      "description": "Service must be linked to at least one repository",
      "check_type": "hasItems",
      "config": { "relationship": "repositories" },
      "weight": 15
    }
  ]
}
```

**GET /api/v1/scorecards/{id}/evaluate**
```json
Response 200:
{
  "data": {
    "scorecard": {
      "id": "uuid",
      "name": "Service Readiness",
      "entity_types": ["service"]
    },
    "summary": {
      "total_entities": 10,
      "average_score": 76.5,
      "average_grade": "C",
      "grade_distribution": { "A": 3, "B": 2, "C": 2, "D": 1, "F": 2 }
    },
    "results": [
      {
        "entity_id": "uuid",
        "entity_type": "service",
        "entity_name": "Customer API",
        "score": 92.0,
        "grade": "A",
        "criteria_results": [
          { "criterion_id": "uuid", "name": "Has Description", "passed": true, "weight": 10 },
          { "criterion_id": "uuid", "name": "Has Components", "passed": true, "weight": 20 },
          { "criterion_id": "uuid", "name": "Has On-Call", "passed": true, "weight": 30 },
          { "criterion_id": "uuid", "name": "Is Operational", "passed": true, "weight": 25 },
          { "criterion_id": "uuid", "name": "Has Repository", "passed": false, "weight": 15 }
        ]
      }
    ]
  }
}
```

### 4.5 Evaluation Engine Logic

```python
# backend/app/services/scorecard_engine.py

from typing import Any

def evaluate_criterion(
    entity: dict,
    check_type: str,
    config: dict,
    relationships: dict,  # pre-loaded relationships
    active_incident_count: int,
) -> bool:
    """Evaluate a single criterion against an entity."""

    match check_type:
        case "hasField":
            field = config["field"]
            value = entity.get(field) or entity.get("attributes", {}).get(field)
            return value is not None and value != "" and value != []

        case "hasItems":
            rel = config["relationship"]
            items = relationships.get(rel, [])
            return len(items) > 0

        case "minItems":
            rel = config["relationship"]
            min_count = config["min"]
            items = relationships.get(rel, [])
            return len(items) >= min_count

        case "fieldEquals":
            field = config["field"]
            expected = config["value"]
            actual = entity.get(field)
            return actual == expected

        case "fieldNotEquals":
            field = config["field"]
            unexpected = config["value"]
            actual = entity.get(field)
            return actual != unexpected

        case "hasAssignment":
            role = config["role"]
            assignments = relationships.get("assignments", [])
            return any(a["role"] == role for a in assignments)

        case "minAssignments":
            min_count = config["min"]
            assignments = relationships.get("assignments", [])
            return len(assignments) >= min_count

        case "noActiveIncidents":
            return active_incident_count == 0

        case "hasTag":
            key = config["key"]
            attrs = entity.get("attributes") or {}
            return key in attrs

        case "attributeEquals":
            key = config["key"]
            expected = config["value"]
            attrs = entity.get("attributes") or {}
            return attrs.get(key) == expected

        case _:
            return False


def calculate_score(criteria_results: list[dict]) -> tuple[float, str]:
    """Calculate weighted score and grade from criteria results.

    Args:
        criteria_results: List of {"passed": bool, "weight": int}

    Returns:
        (score: float 0-100, grade: str A-F)
    """
    total_weight = sum(c["weight"] for c in criteria_results)
    if total_weight == 0:
        return 0.0, "F"

    earned_weight = sum(c["weight"] for c in criteria_results if c["passed"])
    score = (earned_weight / total_weight) * 100

    grade = (
        "A" if score >= 90 else
        "B" if score >= 80 else
        "C" if score >= 70 else
        "D" if score >= 60 else
        "F"
    )

    return round(score, 1), grade
```

### 4.6 Evaluation Data Loading Strategy

To evaluate a scorecard against all applicable entities efficiently:

1. Load all entities of the target types in a single query (with `tenant_id` scoping)
2. Batch-load relationships for all entities:
   - Components for services: single query with `IN` clause
   - Resources for services: single query with `IN` clause
   - Assignments for all entities: single query grouped by entity_type + entity_id
   - Active incident counts: single query grouped by entity_type + entity_id
3. For each entity, build a relationship dict and evaluate all criteria
4. Calculate weighted score and grade per entity
5. Calculate aggregate stats (average, distribution)

This approach uses O(1) queries per relationship type, not O(N) per entity.

### 4.7 Frontend Specifications

#### Scorecard List View
- Table columns: Name, Entity Types (badges), Total Entities, Average Score (progress bar), Average Grade (colored badge)
- Filter: Entity type dropdown
- Sort: By name or average score
- "Create Scorecard" button (Editor+ role)

#### Scorecard Detail View
- **Header**: Scorecard name, description, entity type badges, Edit/Delete buttons
- **Summary Panel**: Total entities, average score, grade distribution as horizontal bar chart (colored segments A-F)
- **Criteria Panel**: List of criteria with name, check type badge, weight, description
- **Results Table**: Entity name, entity type, individual criteria pass/fail icons, total score, grade badge
  - Sortable by score (ascending or descending)
  - Searchable by entity name
  - Click entity name → navigate to entity detail view
- **Grade Legend**: A=green, B=blue, C=yellow, D=orange, F=red

#### Entity Detail → Scorecards Tab
- Show all scorecards that apply to this entity's type
- For each: scorecard name, score, grade, expandable criteria checklist (pass/fail per criterion)

#### Scorecard Create/Edit Modal
- Name (required)
- Description
- Entity types multi-select (service, component, resource, product, repository)
- Criteria list (dynamic add/remove):
  - Name (required)
  - Check type dropdown
  - Config fields (dynamic based on check type)
  - Weight (1–100 number input)
- Preview button: show evaluation results for first 5 entities

## 5. SECURITY REQUIREMENTS

- Scorecard CRUD: Editor+ can create/edit; Admin can delete
- Evaluation results: visible to all authenticated users
- Scorecards MUST be scoped by tenant_id
- Scorecard definitions MUST NOT expose raw SQL or allow code injection through config fields
- Config JSONB fields MUST be validated against a schema per check type

## 6. TESTING REQUIREMENTS

### 6.1 Unit Tests
- Each of the 10 check types: test with passing entity, failing entity, edge cases (null, empty)
- Score calculation: test with all pass, all fail, mixed, unequal weights, zero total weight
- Grade assignment: test boundary values (89.9 → B, 90.0 → A, etc.)

### 6.2 Integration Tests
- Create scorecard, then evaluate against test entities
- Verify evaluation results match expected scores
- Modify an entity (add description), re-evaluate, verify score changes
- Create/resolve incident, verify `noActiveIncidents` criterion changes
- Verify multiple scorecards can target same entity type
- RBAC: Viewer can view evaluations but cannot create scorecards

### 6.3 Frontend Tests
- Scorecard list: verify rows render with correct aggregate data
- Scorecard detail: verify criteria pass/fail icons, grade colors
- Create modal: verify dynamic config fields change per check type

## 7. NON-FUNCTIONAL REQUIREMENTS

- **Performance**: Single entity evaluation < 50ms. Full scorecard evaluation (100 entities) < 500ms.
- **Scalability**: Batch relationship loading ensures O(1) query sets regardless of entity count.
- **Observability**: Log evaluation duration and entity count per scorecard evaluation.

## 8. MIGRATION & DEPLOYMENT

- No additional migrations beyond TPRD-002
- Feature flag: N/A — core functionality

## 9. IMPLEMENTATION GUIDANCE FOR CODING AGENTS

### Implementation Order
1. Create scorecard evaluation engine (`services/scorecard_engine.py`)
2. Create scorecard service (CRUD + evaluation orchestration)
3. Create scorecard API routes
4. Create frontend scorecard types and API module
5. Create frontend scorecard store
6. Create scorecard list and detail views
7. Integrate scorecards tab into entity detail views
8. Create scorecard create/edit modal with dynamic criteria form
9. Write tests

### File Creation Plan

**Backend:**
```
backend/app/services/scorecard_engine.py       # Pure evaluation logic
backend/app/services/scorecard_service.py      # CRUD + orchestration
backend/app/repositories/scorecard_repository.py
backend/app/api/v1/scorecards.py
backend/app/schemas/scorecard.py               # Pydantic schemas
```

**Frontend:**
```
frontend/src/api/scorecards.ts
frontend/src/stores/scorecards.ts
frontend/src/types/scorecard.ts
frontend/src/views/ScorecardListView.vue
frontend/src/views/ScorecardDetailView.vue
frontend/src/components/scorecards/ScorecardEvaluation.vue
frontend/src/components/scorecards/CriteriaChecklist.vue
frontend/src/components/scorecards/GradeBadge.vue
frontend/src/components/scorecards/ScorecardCreateModal.vue
frontend/src/components/scorecards/CriterionConfigForm.vue
```

### Do NOT
- Do NOT store evaluation results in the database — always compute on read
- Do NOT allow arbitrary field names in criterion configs — validate against known entity fields
- Do NOT use `eval()` or dynamic code execution for criteria evaluation
- Do NOT load relationships per-entity — use batch loading
- Do NOT allow weight values outside 1–100 range

### Verify
- [ ] All 10 check types evaluate correctly
- [ ] Weighted scoring produces correct results
- [ ] Grade boundaries are correct (A: 90–100, B: 80–89, C: 70–79, D: 60–69, F: 0–59)
- [ ] Evaluation with 100 entities completes in < 500ms
- [ ] Frontend criteria form dynamically updates based on check type
- [ ] Entity detail scorecard tab shows correct results
- [ ] Config JSONB validated against check type schema

## 10. OPEN QUESTIONS

None.
