# TPRD-2026-02-18-public-status-page

## 1. DOCUMENT METADATA

```
Document ID:    TPRD-2026-02-18-public-status-page
Version:        1.0
Status:         Draft
Feature Name:   Public Status Page
Parent TPRD:    TPRD-2026-02-18-platform-foundation
```

## 2. EXECUTIVE SUMMARY

- **Business Objective**: Provide a public-facing, unauthenticated status page that displays the operational health of products and services, active incidents, and their current resolution status — enabling internal and external stakeholders to quickly assess system availability.
- **Technical Scope**: A dedicated backend API endpoint (no auth) serving status data, plus a standalone frontend page (server-rendered or static) that displays product/service operational status, active incidents, and historical uptime. Can be served on a separate subdomain (e.g., `status.holman.com`).
- **Success Criteria**: Page loads in < 1 second. No authentication required. Shows accurate real-time operational status. Active incidents appear within 30 seconds of creation.
- **Complexity Estimate**: S — Small surface area: one API endpoint, one frontend page, data already exists.

## 3. SCOPE DEFINITION

### 3.1 In Scope
- Public (unauthenticated) REST endpoint for status data
- Status page displaying:
  - Overall system status banner (operational / degraded / outage)
  - Active incidents with timeline (public subset)
  - Product list with per-service operational status
  - Expandable product → service hierarchy
- Status indicator colors: green (operational), yellow (degraded), orange (partial outage), red (major outage)
- Static HTML page served by backend (no SPA required)
- Redis caching of status data (30-second TTL)
- Embeddable status badge (SVG/PNG)

### 3.2 Out of Scope
- Historical uptime chart (90-day)
- Scheduled maintenance windows
- Email subscription for status updates
- Custom branding per tenant
- Status page for individual components/resources (only products → services)

### 3.3 Assumptions
- Status page shows data from one tenant (configured via environment variable or default tenant)
- Incident timeline entries are filtered — only `status_change` type entries are shown publicly (not internal notes)
- Products and services with `status == "inactive"` are excluded from the status page

### 3.4 Dependencies
- TPRD-2026-02-18-core-data-models (products, services, incidents)
- TPRD-2026-02-18-incident-management (active incidents data)

## 4. TECHNICAL SPECIFICATIONS

### 4.1 Technology Stack Declaration
Per `.github/technology-stack.yml`. The status page is a server-rendered HTML page using Jinja2 templates served by FastAPI. No Vue.js SPA required for the public page.

Additional:
- **Jinja2**: Template rendering for public status page
- Justification: Minimal JS footprint, fast load time, SEO-friendly, no auth needed

### 4.2 Architecture

```
Public Request → /status (FastAPI)
  → StatusService.get_public_status()
    → Redis cache (30s TTL)
      → PostgreSQL (on cache miss)
  → Jinja2 template rendering
  → HTML response

Public API → /api/v1/status (FastAPI, no auth)
  → StatusService.get_public_status()
  → JSON response
```

### 4.3 API Specifications

#### Public Status Data Endpoint (No Auth)

**GET /api/v1/status**
```json
Response 200:
{
  "overall_status": "degraded",
  "updated_at": "2026-02-18T12:00:00Z",
  "products": [
    {
      "id": "uuid",
      "name": "Customer Portal",
      "operational_status": "degraded",
      "services": [
        {
          "id": "uuid",
          "name": "Customer API",
          "type": "api",
          "operational_status": "degraded"
        },
        {
          "id": "uuid",
          "name": "Customer Frontend",
          "type": "web_application",
          "operational_status": "operational"
        }
      ]
    },
    {
      "id": "uuid",
      "name": "Internal Tools",
      "operational_status": "operational",
      "services": [
        {
          "id": "uuid",
          "name": "Admin Dashboard",
          "type": "web_application",
          "operational_status": "operational"
        }
      ]
    }
  ],
  "active_incidents": [
    {
      "id": "uuid",
      "title": "Elevated API Latency",
      "severity": "major",
      "status": "investigating",
      "impact_type": "performance",
      "started_at": "2026-02-18T10:30:00Z",
      "affected_services": ["Customer API"],
      "timeline": [
        {
          "type": "status_change",
          "content": "Incident created with status: investigating",
          "created_at": "2026-02-18T10:30:00Z"
        },
        {
          "type": "status_change",
          "content": "Status changed to identified. Root cause: database connection pool saturation",
          "created_at": "2026-02-18T10:45:00Z"
        }
      ]
    }
  ]
}
```

#### Status Page HTML Endpoint (No Auth)

**GET /status**
- Returns server-rendered HTML page
- Content-Type: text/html
- Uses Jinja2 template with Tailwind CSS (inline or CDN)

#### Status Badge Endpoint (No Auth)

**GET /api/v1/status/badge**
- Returns SVG badge showing overall status
- Query param: `format=svg` (default) or `format=json`
- Example SVG: green shield "operational" or red shield "outage"
- Cache-Control: public, max-age=60

### 4.4 Business Logic

#### Overall Status Calculation
```python
def calculate_overall_status(products: list[Product]) -> str:
    """Determine the worst operational status across all products and services."""
    worst = "operational"
    ranking = {"operational": 0, "degraded": 1, "partial_outage": 2, "major_outage": 3}

    for product in products:
        for service in product.services:
            if ranking.get(service.operational_status, 0) > ranking.get(worst, 0):
                worst = service.operational_status
    return worst
```

#### Product Operational Status
A product's operational status is the worst status of any of its services:
```python
def calculate_product_status(services: list[Service]) -> str:
    ranking = {"operational": 0, "degraded": 1, "partial_outage": 2, "major_outage": 3}
    worst = "operational"
    for svc in services:
        if ranking.get(svc.operational_status, 0) > ranking.get(worst, 0):
            worst = svc.operational_status
    return worst
```

#### Timeline Filtering for Public Display
- Only entries with `type == "status_change"` are shown
- Manual notes (which may contain internal details) are excluded
- User names are NOT shown on the public page — only timestamps and content

### 4.5 Frontend Specifications (Status HTML Page)

**Layout:**
```
┌─────────────────────────────────────────────────┐
│  🏢 Holman Enterprises - System Status          │
├─────────────────────────────────────────────────┤
│  ┌───────────────────────────────────────────┐  │
│  │ ✅ All Systems Operational                │  │  ← Overall status banner
│  │    (or ⚠️ Some Systems Experiencing       │  │    Color: green/yellow/red
│  │     Degraded Performance)                 │  │
│  └───────────────────────────────────────────┘  │
│                                                 │
│  🚨 Active Incidents                            │
│  ┌───────────────────────────────────────────┐  │
│  │ 🟡 MAJOR - Elevated API Latency          │  │
│  │ Started: Feb 18, 2026 10:30 AM            │  │
│  │ Status: Investigating                     │  │
│  │ Affected: Customer API                    │  │
│  │                                           │  │
│  │ Timeline:                                 │  │
│  │ • 10:45 AM - Root cause identified        │  │
│  │ • 10:30 AM - Incident created             │  │
│  └───────────────────────────────────────────┘  │
│                                                 │
│  📦 Products                                    │
│  ┌───────────────────────────────────────────┐  │
│  │ ▸ Customer Portal           ⚠️ Degraded   │  │  ← Expandable
│  │   ├── Customer API          ⚠️ Degraded   │  │
│  │   ├── Customer Frontend     ✅ Operational │  │
│  │   └── Customer Database     ✅ Operational │  │
│  │                                           │  │
│  │ ▸ Internal Tools            ✅ Operational │  │
│  │   └── Admin Dashboard       ✅ Operational │  │
│  └───────────────────────────────────────────┘  │
│                                                 │
│  Last updated: Feb 18, 2026 12:00 PM            │
└─────────────────────────────────────────────────┘
```

**Styling**: Tailwind CSS via CDN for the public page. Matches Holman brand colors.

**Interactivity**: Minimal JavaScript:
- Product expand/collapse (toggle)
- Auto-refresh every 60 seconds via `<meta http-equiv="refresh">` or minimal JS fetch

### 4.6 Internal Status View (Authenticated SPA)

The authenticated frontend (TPRD-006) includes a Status Page view at `/status` that:
- Shows the same data as the public page
- Additionally shows component and resource status
- Links entity names to their detail views
- Shows incident links

## 5. SECURITY REQUIREMENTS

- `/api/v1/status` and `/status` endpoints MUST NOT require authentication
- These endpoints MUST NOT expose:
  - Internal entity IDs in the HTML (IDs can be in JSON API)
  - Internal notes from incident timelines
  - User names or email addresses
  - Component or resource details (only products → services)
  - Tenant-specific configuration
- Rate limiting: 60 requests/minute per IP (prevent scraping)
- CORS: Allow all origins for the badge endpoint
- Redis cache prevents database overload from public traffic

## 6. TESTING REQUIREMENTS

### 6.1 Unit Tests
- Overall status calculation: test all combinations
- Product status calculation: test with mixed service statuses
- Timeline filtering: verify manual notes excluded
- Badge generation: verify SVG output for each status

### 6.2 Integration Tests
- `/api/v1/status` returns correct JSON shape
- `/status` returns valid HTML with correct status information
- Create an incident, verify it appears on status page
- Resolve incident, verify status page updates
- Verify caching: first request hits DB, second within 30s hits cache
- Verify inactive products/services excluded

### 6.3 Security Tests
- Verify no auth required for status endpoints
- Verify internal notes not exposed
- Verify rate limiting enforced

## 7. NON-FUNCTIONAL REQUIREMENTS

- **Performance**: Status page HTML loads in < 500ms (including server rendering)
- **Availability**: Cache gracefully serves stale data if PostgreSQL is temporarily unavailable
- **Scalability**: Redis cache prevents DB load from public traffic spikes
- **Observability**: Log cache hit/miss ratio for status endpoint

## 8. MIGRATION & DEPLOYMENT

- No additional migrations
- Status page can be served on a separate subdomain via nginx configuration:
  ```
  server {
    server_name status.holman.com;
    location / { proxy_pass http://backend:8000/status; }
    location /api/v1/status { proxy_pass http://backend:8000/api/v1/status; }
  }
  ```
- Feature flag: N/A

## 9. IMPLEMENTATION GUIDANCE FOR CODING AGENTS

### Implementation Order
1. Create status service (data aggregation + caching)
2. Create public API endpoint (`/api/v1/status`)
3. Create Jinja2 template for status page
4. Create HTML endpoint (`/status`)
5. Create badge endpoint (`/api/v1/status/badge`)
6. Create internal status view component for authenticated SPA
7. Write tests

### File Creation Plan

**Backend:**
```
backend/app/services/status_service.py
backend/app/api/v1/status.py
backend/app/templates/
  status.html                  # Jinja2 template
backend/app/static/
  status.css                   # Minimal custom styles (if Tailwind CDN insufficient)
```

**Frontend (authenticated view):**
```
frontend/src/views/StatusPageView.vue
```

### Do NOT
- Do NOT require authentication for public status endpoints
- Do NOT expose internal notes, user names, or entity IDs in the HTML page
- Do NOT query the database on every public page request — always use Redis cache
- Do NOT include component or resource level details on the public page

### Verify
- [ ] `/api/v1/status` returns correct JSON without authentication
- [ ] `/status` returns valid, styled HTML page
- [ ] Overall status reflects worst service status
- [ ] Active incidents appear with filtered timeline
- [ ] Internal notes are NOT visible on public page
- [ ] Redis cache is used (verify with cache metrics)
- [ ] Badge endpoint returns valid SVG
- [ ] Auto-refresh works (page updates every 60 seconds)

## 10. OPEN QUESTIONS

None.
