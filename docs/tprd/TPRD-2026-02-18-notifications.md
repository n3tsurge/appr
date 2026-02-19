# TPRD-2026-02-18-notifications

## 1. DOCUMENT METADATA

```
Document ID:    TPRD-2026-02-18-notifications
Version:        1.0
Status:         Draft
Feature Name:   Notifications — Email & Microsoft Teams
Parent TPRD:    TPRD-2026-02-18-platform-foundation
```

## 2. EXECUTIVE SUMMARY

- **Business Objective**: Keep stakeholders informed of critical events (incident creation/resolution, status changes, scorecard degradation) via email and Microsoft Teams, reducing response times and improving awareness.
- **Technical Scope**: Celery-based async notification system that dispatches Email (SMTP) and Microsoft Teams (webhook) notifications for configurable events. Notification preferences per user, templated message content, and delivery tracking.
- **Success Criteria**: Notifications delivered within 30 seconds of triggering event. Zero blocking impact on API response times (fully async). Delivery failures logged and retryable.
- **Complexity Estimate**: M — Celery infrastructure, two delivery channels, template rendering, preference management.

## 3. SCOPE DEFINITION

### 3.1 In Scope
- Notification triggers:
  - Incident created (with severity, affected entities)
  - Incident status changed (advanced, resolved, reopened)
  - Entity operational status changed (degraded, outage, restored)
  - Scorecard grade dropped below threshold (optional, per scorecard)
- Delivery channels:
  - Email via SMTP (HTML templates)
  - Microsoft Teams via incoming webhook (Adaptive Cards)
- User notification preferences (opt-in/out per event type per channel)
- Teams channel configuration (per-tenant webhook URL)
- Celery async task execution (Redis broker)
- Retry with exponential backoff (3 retries, 30s/60s/120s)
- Delivery logging (success/failure tracking)

### 3.2 Out of Scope
- Slack integration
- SMS / push notifications
- In-app notification center (bell icon with unread count — future)
- Digest / summary emails
- PagerDuty / OpsGenie integration
- User self-service preferences UI (Admin manages for initial release)

### 3.3 Assumptions
- SMTP server is available (configured via environment variables)
- Microsoft Teams incoming webhooks are pre-configured per channel
- Celery workers are running alongside the API server
- One Teams webhook per tenant (sends to a shared channel)

### 3.4 Dependencies
- TPRD-2026-02-18-platform-foundation (Celery + Redis infrastructure)
- TPRD-2026-02-18-incident-management (incident events)
- TPRD-2026-02-18-scorecard-engine (scorecard evaluation)

## 4. TECHNICAL SPECIFICATIONS

### 4.1 Technology Stack Declaration
Per `.github/technology-stack.yml`:
- **Celery 5.x** for async task execution
- **Redis** as Celery broker and result backend
- **Jinja2** for email HTML templates
- **httpx** for Teams webhook HTTP calls
- **Python `smtplib`** wrapped in async (via Celery task)

### 4.2 Architecture

```
API Endpoint (e.g., create incident)
  → IncidentService.create()
    → After commit: dispatch_notification.delay(event_type, payload)

Celery Worker:
  dispatch_notification(event_type, payload)
    → Load notification preferences for tenant
    → For each enabled channel:
        → send_email.delay(recipients, subject, body)
        → send_teams_message.delay(webhook_url, card)

  send_email(recipients, subject, body)
    → Render Jinja2 template
    → Send via SMTP
    → Log result to notification_log table

  send_teams_message(webhook_url, card)
    → Build Adaptive Card JSON
    → POST to webhook URL
    → Log result to notification_log table
```

### 4.3 Data Models

**notification_preferences table:**
```sql
CREATE TABLE notification_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    user_id UUID REFERENCES users(id),           -- NULL = tenant-wide default
    event_type VARCHAR(50) NOT NULL,              -- incident_created, incident_resolved, etc.
    channel VARCHAR(20) NOT NULL,                 -- email, teams
    enabled BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(tenant_id, user_id, event_type, channel)
);
```

**notification_channels table:**
```sql
CREATE TABLE notification_channels (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    channel_type VARCHAR(20) NOT NULL,            -- email, teams
    name VARCHAR(100) NOT NULL,                   -- "Incidents Channel", "Ops Email"
    config JSONB NOT NULL,                        -- {"webhook_url": "..."} or {"smtp_from": "..."}
    enabled BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

**notification_log table:**
```sql
CREATE TABLE notification_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    channel VARCHAR(20) NOT NULL,
    recipient VARCHAR(255),                       -- email address or channel name
    subject VARCHAR(255),
    status VARCHAR(20) NOT NULL,                  -- sent, failed, retrying
    error_message TEXT,
    payload JSONB,                                -- The notification content for debugging
    attempted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    delivered_at TIMESTAMPTZ
);
```

### 4.4 Event Types

| Event Type | Triggered By | Default Channels | Priority |
|-----------|-------------|-----------------|----------|
| `incident_created` | Incident creation | Email + Teams | High |
| `incident_status_changed` | Incident advance/resolve/reopen | Teams | Medium |
| `incident_resolved` | Incident resolution | Email + Teams | High |
| `entity_status_degraded` | Operational status → degraded/outage | Teams | High |
| `entity_status_restored` | Operational status → operational | Teams | Low |
| `scorecard_grade_dropped` | Scorecard evaluation grade drops | Email | Low |

### 4.5 Email Templates

**Incident Created:**
```
Subject: [{{ severity | upper }}] New Incident: {{ title }}

Body (HTML):
┌─────────────────────────────────────────┐
│ 🚨 New Incident Created                 │
│                                         │
│ Title: {{ title }}                       │
│ Severity: {{ severity }}                 │
│ Status: Investigating                   │
│ Impact: {{ impact_type }}               │
│                                         │
│ Affected:                               │
│ {% for e in affected_entities %}         │
│ • {{ e.name }} ({{ e.type }})           │
│ {% endfor %}                            │
│                                         │
│ [View Incident →]                       │
│                                         │
│ — AppInventory by Holman Enterprises    │
└─────────────────────────────────────────┘
```

**Incident Resolved:**
```
Subject: [RESOLVED] {{ title }} ({{ duration_formatted }})

Body (HTML):
┌─────────────────────────────────────────┐
│ ✅ Incident Resolved                     │
│                                         │
│ Title: {{ title }}                       │
│ Duration: {{ duration_formatted }}       │
│ Resolution:                             │
│ {{ resolution_note }}                    │
│                                         │
│ Affected Services Restored:             │
│ {% for e in entities_restored %}         │
│ • {{ e.name }} → Operational            │
│ {% endfor %}                            │
│                                         │
│ [View Incident →]                       │
└─────────────────────────────────────────┘
```

### 4.6 Microsoft Teams Adaptive Card

**Incident Created Card:**
```json
{
  "type": "message",
  "attachments": [{
    "contentType": "application/vnd.microsoft.card.adaptive",
    "content": {
      "type": "AdaptiveCard",
      "version": "1.4",
      "body": [
        {
          "type": "TextBlock",
          "text": "🚨 New Incident",
          "weight": "bolder",
          "size": "large",
          "color": "attention"
        },
        {
          "type": "FactSet",
          "facts": [
            { "title": "Title", "value": "{{ title }}" },
            { "title": "Severity", "value": "{{ severity }}" },
            { "title": "Impact", "value": "{{ impact_type }}" },
            { "title": "Affected", "value": "{{ affected_names }}" }
          ]
        }
      ],
      "actions": [
        {
          "type": "Action.OpenUrl",
          "title": "View Incident",
          "url": "{{ incident_url }}"
        }
      ]
    }
  }]
}
```

### 4.7 Celery Task Definitions

```python
# backend/app/tasks/notifications.py
from celery import shared_task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)

@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    retry_backoff=True,
    retry_backoff_max=120,
    acks_late=True,
)
def dispatch_notification(self, event_type: str, payload: dict, tenant_id: str):
    """Dispatch notification to all configured channels for this event type."""
    # 1. Load notification preferences for tenant
    # 2. For each enabled channel, dispatch channel-specific task
    pass


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    retry_backoff=True,
)
def send_email(self, tenant_id: str, recipients: list[str], subject: str,
               template_name: str, context: dict):
    """Render email template and send via SMTP."""
    try:
        # 1. Render Jinja2 template
        # 2. Send via smtplib
        # 3. Log success to notification_log
        pass
    except Exception as exc:
        # Log failure to notification_log
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    retry_backoff=True,
)
def send_teams_message(self, tenant_id: str, webhook_url: str, card: dict):
    """Send Adaptive Card to Microsoft Teams webhook."""
    try:
        # 1. POST card to webhook_url
        # 2. Verify 200 response
        # 3. Log success to notification_log
        pass
    except Exception as exc:
        # Log failure to notification_log
        raise self.retry(exc=exc)
```

### 4.8 API Specifications

#### Notification Management (Admin only)

| Method | Path | Auth | Role | Description |
|--------|------|------|------|-------------|
| GET | /api/v1/notifications/channels | ✅ | Admin | List notification channels |
| POST | /api/v1/notifications/channels | ✅ | Admin | Create notification channel |
| PUT | /api/v1/notifications/channels/{id} | ✅ | Admin | Update channel config |
| DELETE | /api/v1/notifications/channels/{id} | ✅ | Admin | Delete channel |
| GET | /api/v1/notifications/preferences | ✅ | Admin | List notification preferences |
| PUT | /api/v1/notifications/preferences | ✅ | Admin | Update preferences (bulk) |
| GET | /api/v1/notifications/log | ✅ | Admin | View notification delivery log |
| POST | /api/v1/notifications/test | ✅ | Admin | Send test notification |

## 5. SECURITY REQUIREMENTS

- Webhook URLs MUST be stored encrypted in the database (application-level encryption)
- SMTP credentials MUST come from environment variables, never from database
- Notification log MUST NOT store email body content (only metadata)
- Admin-only access for all notification management endpoints
- Rate limiting on notification dispatch: max 100 notifications per minute per tenant

## 6. TESTING REQUIREMENTS

### 6.1 Unit Tests
- Template rendering: verify email HTML output for each event type
- Adaptive Card generation: verify JSON structure for each event type
- Preference filtering: verify correct channels enabled/disabled

### 6.2 Integration Tests
- End-to-end: create incident → verify Celery task dispatched → verify notification logged
- Test with mock SMTP server: verify email sent with correct content
- Test with mock webhook endpoint: verify Adaptive Card posted correctly
- Retry behavior: simulate SMTP failure, verify 3 retries with backoff

### 6.3 Manual Testing
- Send test notification → verify email received
- Send test notification → verify Teams message appears in configured channel

## 7. NON-FUNCTIONAL REQUIREMENTS

- **Performance**: Notification dispatch adds < 5ms to API response time (async via Celery)
- **Reliability**: 3 retries with exponential backoff. Failed notifications logged for manual review.
- **Observability**: Celery task metrics (dispatched, succeeded, failed, retried) exported to OpenTelemetry
- **Scalability**: Celery workers horizontally scalable. Redis broker handles queuing.

## 8. MIGRATION & DEPLOYMENT

- Alembic migration: create `notification_preferences`, `notification_channels`, `notification_log` tables
- Celery worker must be deployed alongside API server (separate container or process)
- Environment variables:
  - `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`
  - `CELERY_BROKER_URL` (Redis)
  - `CELERY_RESULT_BACKEND` (Redis)
- Feature flag: `NOTIFICATIONS_ENABLED` (default: true). When false, `dispatch_notification` returns immediately.

## 9. IMPLEMENTATION GUIDANCE FOR CODING AGENTS

### Implementation Order
1. Set up Celery configuration and worker
2. Create notification data models and migration
3. Create email template renderer
4. Create `send_email` Celery task
5. Create Teams Adaptive Card builder
6. Create `send_teams_message` Celery task
7. Create `dispatch_notification` orchestrator task
8. Integrate notification dispatch into incident service
9. Create notification management API routes
10. Write tests with mock SMTP and webhook servers

### File Creation Plan

```
backend/app/core/celery.py                     # Celery app configuration
backend/app/tasks/
  __init__.py
  notifications.py                              # Celery tasks
backend/app/services/notification_service.py   # Preferences, channels, dispatch logic
backend/app/services/email_renderer.py         # Jinja2 template rendering
backend/app/services/teams_card_builder.py     # Adaptive Card JSON builder
backend/app/models/notification.py             # SQLAlchemy models
backend/app/schemas/notification.py            # Pydantic schemas
backend/app/api/v1/notifications.py            # Admin API routes
backend/app/templates/email/
  incident_created.html
  incident_resolved.html
  entity_status_changed.html
  scorecard_grade_dropped.html
  base.html                                     # Base email layout template
backend/migrations/versions/xxx_add_notifications.py
```

### Do NOT
- Do NOT send notifications synchronously — always use Celery tasks
- Do NOT store SMTP credentials in the database
- Do NOT store full email body in notification_log (only subject, recipient, status)
- Do NOT send notifications for soft-deleted entities
- Do NOT block on notification failures — log and continue

### Verify
- [ ] Celery worker starts and processes tasks
- [ ] Incident creation dispatches notification tasks
- [ ] Email renders correctly with Jinja2 templates
- [ ] Teams Adaptive Card posts successfully to webhook
- [ ] Retry logic works with exponential backoff
- [ ] Notification log records all attempts
- [ ] Feature flag disables notifications when set to false
- [ ] Admin API manages channels and preferences
- [ ] Test notification endpoint works for both channels

## 10. OPEN QUESTIONS

None.
