# TPRD-2026-02-18-authentication-authorization

## 1. DOCUMENT METADATA

```
Document ID:    TPRD-2026-02-18-authentication-authorization
Version:        1.0
Status:         Draft
Feature Name:   Authentication & Authorization
Parent TPRD:    TPRD-2026-02-18-platform-foundation
```

## 2. EXECUTIVE SUMMARY

- **Business Objective**: Provide secure, standards-based authentication and role-based access control that supports enterprise SSO via Okta (SAML/OAuth 2.0) with a local authentication fallback, ensuring only authorized users can access and modify inventory data.
- **Technical Scope**: OAuth 2.0 / SAML integration with Okta, local username/password authentication, JWT token lifecycle (access + refresh), RBAC enforcement middleware, and tenant-scoped authorization.
- **Success Criteria**: Users can log in via Okta SSO or local credentials. All API endpoints enforce RBAC. JWT tokens expire correctly. Unauthorized access returns 401/403 per RFC 7807.
- **Complexity Estimate**: L — SSO integration, JWT lifecycle, RBAC middleware, and multi-tenant context.

## 3. SCOPE DEFINITION

### 3.1 In Scope
- OAuth 2.0 Authorization Code flow with PKCE (Okta)
- SAML 2.0 SP-initiated SSO (Okta)
- Local authentication (email + password with bcrypt)
- JWT access tokens (15-minute expiry)
- JWT refresh tokens (7-day expiry, stored in database)
- Token refresh endpoint
- Logout (token revocation)
- RBAC middleware with 4 roles: Admin, Editor, Viewer, Incident Commander
- Tenant context resolution from JWT claims
- Password reset flow (local auth only)
- User session management

### 3.2 Out of Scope
- User self-registration (admin-only user creation initially)
- MFA (handled by Okta)
- API key authentication for service-to-service (future TPRD)
- Fine-grained permissions beyond role-based (e.g., field-level, entity-level)

### 3.3 Assumptions
- Okta is the primary IdP and the customer has an Okta org (impact if wrong: make IdP configurable)
- A single JWT signing key (RS256) is sufficient (impact if wrong: implement JWK rotation)
- Refresh tokens stored in database (impact if wrong: consider Redis for better performance)

### 3.4 Dependencies
- TPRD-2026-02-18-platform-foundation (FastAPI app, database)
- TPRD-2026-02-18-core-data-models (users table, tenants table)

## 4. TECHNICAL SPECIFICATIONS

### 4.1 Technology Stack Declaration
Per `.github/technology-stack.yml`. Additional packages:
- `python-jose[cryptography]` — JWT encoding/decoding
- `passlib[bcrypt]` — Password hashing
- `python3-saml` — SAML 2.0 SP implementation
- `authlib` — OAuth 2.0 client

### 4.2 Architecture & Design Patterns

```
┌──────────────┐     ┌──────────────┐
│  Browser     │────▶│  Frontend    │
│  (Vue SPA)   │     │  /login      │
└──────┬───────┘     └──────┬───────┘
       │                     │
       │  1. Redirect        │ 2. Auth Code
       ▼  to Okta           ▼  + PKCE
┌──────────────┐     ┌──────────────┐
│  Okta IdP    │────▶│  Backend     │
│  (OAuth/SAML)│     │  /api/v1/auth│
└──────────────┘     │  /callback   │
                     └──────┬───────┘
                            │ 3. Issue JWT
                            ▼
                     ┌──────────────┐
                     │  JWT Token   │
                     │  (access +   │
                     │   refresh)   │
                     └──────────────┘
```

**Design Patterns:**
- **Strategy Pattern**: `AuthProvider` interface with `LocalAuthProvider` and `OktaAuthProvider` implementations
- **Middleware Pattern**: Auth middleware extracts JWT, resolves user + tenant, injects into request state
- **Dependency Injection**: `get_current_user()`, `require_role()` as FastAPI `Depends()`

### 4.3 Data Models

**Table `refresh_tokens`:**

| Column | Type | Constraints | Index |
|--------|------|-------------|-------|
| id | UUID | PK | — |
| user_id | UUID | FK(users.id), NOT NULL | yes |
| token_hash | VARCHAR(255) | NOT NULL, UNIQUE | yes |
| expires_at | TIMESTAMPTZ | NOT NULL | yes |
| revoked_at | TIMESTAMPTZ | NULLABLE | — |
| created_at | TIMESTAMPTZ | NOT NULL | — |
| user_agent | VARCHAR(500) | NULLABLE | — |
| ip_address | VARCHAR(45) | NULLABLE | — |

### 4.4 API Specifications

#### POST /api/v1/auth/login (Local Auth)
```
Request:
{
  "email": "user@holman.com",
  "password": "secret123"
}

Response 200:
{
  "data": {
    "access_token": "eyJ...",
    "refresh_token": "eyJ...",
    "token_type": "bearer",
    "expires_in": 900,
    "user": {
      "id": "uuid",
      "email": "user@holman.com",
      "display_name": "John Doe",
      "role": "editor",
      "tenant_id": "uuid"
    }
  }
}

Response 401 (RFC 7807):
{
  "type": "https://api.appinventory.holman.com/errors/invalid-credentials",
  "title": "Invalid Credentials",
  "status": 401,
  "detail": "The email or password provided is incorrect."
}
```

#### GET /api/v1/auth/okta/authorize
Redirects to Okta OAuth 2.0 authorization endpoint with PKCE challenge.
```
Response 302: Redirect to https://{okta-domain}/oauth2/default/v1/authorize?...
```

#### GET /api/v1/auth/okta/callback
Handles OAuth 2.0 callback, exchanges code for tokens, creates/updates user, issues JWT.
```
Query Params: code, state
Response 200: Same shape as /login response
```

#### POST /api/v1/auth/saml/acs
SAML Assertion Consumer Service endpoint.
```
Request: SAMLResponse (form POST)
Response 200: Same shape as /login response
```

#### GET /api/v1/auth/saml/metadata
Returns SAML SP metadata XML.
```
Response 200: application/xml
```

#### POST /api/v1/auth/refresh
```
Request:
{
  "refresh_token": "eyJ..."
}

Response 200:
{
  "data": {
    "access_token": "eyJ...(new)",
    "refresh_token": "eyJ...(new, rotated)",
    "token_type": "bearer",
    "expires_in": 900
  }
}

Response 401: Refresh token expired or revoked
```

#### POST /api/v1/auth/logout
```
Request:
{
  "refresh_token": "eyJ..."
}

Response 204: No Content (token revoked)
```

#### GET /api/v1/auth/me
```
Response 200:
{
  "data": {
    "id": "uuid",
    "email": "user@holman.com",
    "display_name": "John Doe",
    "role": "admin",
    "tenant_id": "uuid",
    "auth_provider": "okta",
    "person_id": "uuid|null"
  }
}
```

### 4.5 Frontend Specifications

**Login Page (`/login`):**
- Display email/password form for local auth
- "Sign in with Okta" button that redirects to OAuth flow
- Remember last auth method in localStorage
- Show validation errors inline

**Auth Store (Pinia):**
```typescript
interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

// Actions
login(email: string, password: string): Promise<void>
loginWithOkta(): void  // redirect
handleOktaCallback(code: string, state: string): Promise<void>
refreshAccessToken(): Promise<void>
logout(): Promise<void>
fetchCurrentUser(): Promise<void>
```

**Axios Interceptor:**
- Attach `Authorization: Bearer {access_token}` to all API requests
- On 401 response, attempt token refresh; if refresh fails, redirect to `/login`
- Queue requests during token refresh to avoid duplicate refresh calls

**Route Guards:**
- `requireAuth`: Redirect to `/login` if not authenticated
- `requireRole(roles)`: Show 403 page if user role is insufficient

### 4.6 Business Logic

**JWT Claims:**
```json
{
  "sub": "user-uuid",
  "tenant_id": "tenant-uuid",
  "role": "editor",
  "email": "user@holman.com",
  "display_name": "John Doe",
  "iat": 1708243200,
  "exp": 1708244100
}
```

**RBAC Permission Matrix:**

| Resource | Admin | Editor | Viewer | Incident Commander |
|----------|-------|--------|--------|--------------------|
| Users (CRUD) | ✅ | ❌ | ❌ | ❌ |
| Teams (CRUD) | ✅ | ✅ | ❌ | ❌ |
| People (CRUD) | ✅ | ✅ | ❌ | ❌ |
| Products (CRUD) | ✅ | ✅ | ❌ | ❌ |
| Services (CRUD) | ✅ | ✅ | ❌ | ❌ |
| Components (CRUD) | ✅ | ✅ | ❌ | ❌ |
| Resources (CRUD) | ✅ | ✅ | ❌ | ❌ |
| Repositories (CRUD) | ✅ | ✅ | ❌ | ❌ |
| Incidents (Create/Update) | ✅ | ❌ | ❌ | ✅ |
| Incidents (Resolve) | ✅ | ❌ | ❌ | ✅ |
| Scorecards (CRUD) | ✅ | ✅ | ❌ | ❌ |
| All entities (Read) | ✅ | ✅ | ✅ | ✅ |
| Operational status change | ✅ | ✅ | ❌ | ✅ |
| Import/Export data | ✅ | ❌ | ❌ | ❌ |
| Audit log (Read) | ✅ | ❌ | ❌ | ❌ |

**Okta User Provisioning:**
- On first SSO login, auto-create user with `role: viewer`
- Map Okta groups to roles (configurable via tenant settings)
- If user already exists (matched by email), update `auth_provider` and `external_id`
- Link to existing `people` record if email matches

**Refresh Token Rotation:**
- On each refresh, issue a NEW refresh token and revoke the old one
- If a revoked refresh token is used, revoke ALL refresh tokens for that user (compromise detection)

## 5. SECURITY REQUIREMENTS

- Passwords MUST be hashed with bcrypt (cost factor >= 12)
- JWT MUST use RS256 signing algorithm
- Access tokens MUST expire in 15 minutes
- Refresh tokens MUST expire in 7 days
- Refresh token MUST be rotated on each use
- Failed login attempts MUST be rate-limited (5 per minute per email)
- Audit log MUST record: login, logout, failed_login, token_refresh, password_change
- SAML assertions MUST be validated (signature, expiry, audience)
- OAuth state parameter MUST be cryptographically random and validated
- PKCE code verifier MUST be used for OAuth flows

## 6. TESTING REQUIREMENTS

### 6.1 Unit Tests
- JWT token generation and validation
- Password hashing and verification
- RBAC permission checks for each role
- Refresh token rotation logic
- Okta callback user provisioning logic

### 6.2 Integration Tests
- Full local auth flow: login → access API → refresh → logout
- Invalid credentials return 401
- Expired access token returns 401, refresh works
- Expired refresh token returns 401
- RBAC enforcement: viewer cannot POST, editor cannot manage users
- Rate limiting on login endpoint

### 6.3 Frontend Tests
- Login form submission and error display
- Axios interceptor token refresh behavior
- Route guard redirects
- Auth store state transitions

### 6.4 Security Tests
- Cross-tenant JWT: token for tenant A cannot access tenant B resources
- Revoked refresh token: using a revoked token revokes all user sessions
- SQL injection in login form
- XSS in user display name fields

## 7. NON-FUNCTIONAL REQUIREMENTS

- **Performance**: Login response < 200ms (local auth); < 2s (SSO round-trip)
- **Scalability**: Stateless JWT enables horizontal scaling without session sharing
- **Availability**: Auth endpoints must have 99.9% uptime; if Okta is down, local auth still works
- **Observability**: Log all auth events with structlog; emit OpenTelemetry spans for auth middleware

## 8. MIGRATION & DEPLOYMENT

- **Database Migration**: Add `users`, `refresh_tokens` tables (extends TPRD-002 migration)
- **Environment Variables**: `OKTA_CLIENT_ID`, `OKTA_CLIENT_SECRET`, `OKTA_DOMAIN`, `JWT_PRIVATE_KEY`, `JWT_PUBLIC_KEY`
- **Seed Data**: Create a default admin user for initial setup
- **Feature Flag**: `AUTH_SSO_ENABLED=true/false` to enable/disable SSO
- **Rollback**: Drop `refresh_tokens` table; revert user table changes

## 9. IMPLEMENTATION GUIDANCE FOR CODING AGENTS

### Implementation Order
1. Create `backend/app/core/security.py` (JWT creation/validation, password hashing)
2. Create `backend/app/models/user.py` and `backend/app/models/refresh_token.py`
3. Create `backend/app/schemas/auth.py` (login request, token response, etc.)
4. Create `backend/app/services/auth_service.py` (login, refresh, logout logic)
5. Create `backend/app/api/v1/auth.py` (route handlers)
6. Create `backend/app/middleware/auth.py` (JWT extraction + user resolution)
7. Create `backend/app/api/deps.py` — `get_current_user()`, `require_role()`
8. Create `frontend/src/stores/auth.ts`
9. Create `frontend/src/views/LoginView.vue`
10. Create `frontend/src/api/interceptors.ts`
11. Create `frontend/src/router/guards.ts`
12. Write tests

### File Creation Plan
```
backend/app/core/security.py
backend/app/models/refresh_token.py
backend/app/schemas/auth.py
backend/app/services/auth_service.py
backend/app/api/v1/auth.py
backend/app/middleware/auth.py
frontend/src/stores/auth.ts
frontend/src/views/LoginView.vue
frontend/src/api/interceptors.ts
frontend/src/router/guards.ts
```

### Do NOT
- Do NOT store JWT secret as plaintext in code — use environment variables
- Do NOT use HS256 — use RS256 for JWT signing
- Do NOT store access tokens in localStorage — use memory only (Pinia store)
- Do NOT send refresh tokens in URL parameters
- Do NOT disable PKCE for OAuth flows
- Do NOT return different error messages for "user not found" vs. "wrong password" (timing attack)

### Verify
- [ ] Local login works with correct credentials
- [ ] Local login fails with incorrect credentials (401)
- [ ] JWT contains correct claims (sub, tenant_id, role)
- [ ] Access token expires after 15 minutes
- [ ] Refresh token rotation issues new tokens and revokes old
- [ ] RBAC: viewer cannot create entities (403)
- [ ] RBAC: editor can create entities (200)
- [ ] RBAC: admin can manage users (200)
- [ ] Axios interceptor refreshes token on 401
- [ ] Rate limiting blocks after 5 failed login attempts

## 10. OPEN QUESTIONS

None.
