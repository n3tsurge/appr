# TPRD-2026-02-18-frontend-application

## 1. DOCUMENT METADATA

```
Document ID:    TPRD-2026-02-18-frontend-application
Version:        1.0
Status:         Draft
Feature Name:   Frontend Application — Vue 3 SPA
Parent TPRD:    TPRD-2026-02-18-platform-foundation
```

## 2. EXECUTIVE SUMMARY

- **Business Objective**: Convert the single-file POC HTML application into a production-grade Vue 3 SPA with TypeScript, component-based architecture, proper state management, and a professional UI using Tailwind CSS.
- **Technical Scope**: Vite-based Vue 3 project with TypeScript strict mode, Vue Router 4, Pinia stores, Axios API client, Tailwind CSS styling, and all views from the POC (Dashboard, Entity Lists, Detail Views, Dependency Graph, Incidents, Scorecards, Status Page).
- **Success Criteria**: All POC functionality replicated. Lighthouse performance score > 90. Full TypeScript coverage. E2E tests for critical flows.
- **Complexity Estimate**: XL — 15+ views, 30+ components, 8+ stores, complete API integration layer.

## 3. SCOPE DEFINITION

### 3.1 In Scope
- Vite project scaffolding with TypeScript strict mode
- Vue Router with route guards (auth, role-based)
- Pinia stores for all entity types + auth + UI state
- Axios HTTP client with JWT interceptors (access token, refresh token rotation)
- Tailwind CSS with Holman brand color palette
- Responsive layout: sidebar navigation, header, content area
- Dashboard view with summary statistics and charts
- Entity list views (Products, Services, Components, Resources, Repositories, Teams, People)
- Entity detail views with relationship panels
- Entity create/edit modals
- Dependency Graph view (D3.js) — detailed in TPRD-010
- Incident Management views — detailed in TPRD-007
- Scorecard views — detailed in TPRD-008
- Status Page view (internal, authenticated) — status page public variant in TPRD-009
- Import/Export functionality
- Toast notifications for success/error feedback
- Loading states, error states, empty states for all views
- Dark mode support (Tailwind dark variant)

### 3.2 Out of Scope
- Mobile-native app
- Offline mode / PWA
- i18n / localization (English only)
- Real-time WebSocket updates (future)

### 3.3 Assumptions
- Users have modern browsers (Chrome/Edge/Firefox latest 2 versions)
- All data access goes through the REST API (no direct DB access)
- GraphQL used only for dependency graph and relationship queries

### 3.4 Dependencies
- TPRD-2026-02-18-rest-api-catalog (API endpoints)
- TPRD-2026-02-18-graphql-api (graph queries)
- TPRD-2026-02-18-authentication-authorization (auth flow)

## 4. TECHNICAL SPECIFICATIONS

### 4.1 Technology Stack Declaration
Per `.github/technology-stack.yml`:
- Vue 3.4+ with Composition API (`<script setup lang="ts">`)
- TypeScript 5.x strict mode
- Vite 5.x
- Vue Router 4
- Pinia 2.x
- Tailwind CSS 3.x
- Axios 1.x
- D3.js 7.x (for graph visualizations)
- Vitest + Vue Test Utils (unit tests)
- Playwright (E2E tests)

### 4.2 Architecture & Design Patterns

#### Project Structure
```
frontend/
  index.html
  vite.config.ts
  tsconfig.json
  tailwind.config.js
  postcss.config.js
  package.json
  .env.development
  .env.production
  src/
    main.ts                    # App entry, plugin registration
    App.vue                    # Root component with layout
    router/
      index.ts                 # Route definitions
      guards.ts                # Auth and role guards
    stores/
      auth.ts                  # Authentication state
      ui.ts                    # Sidebar, theme, toasts
      teams.ts                 # Teams CRUD state
      people.ts                # People CRUD state
      products.ts              # Products CRUD state
      services.ts              # Services CRUD state
      components.ts            # Components CRUD state
      resources.ts             # Resources CRUD state
      repositories.ts          # Repositories CRUD state
      incidents.ts             # Incidents state
      scorecards.ts            # Scorecards state
      graph.ts                 # Dependency graph state
    api/
      client.ts                # Axios instance with interceptors
      auth.ts                  # Auth API calls
      teams.ts                 # Teams API calls
      people.ts                # People API calls
      products.ts              # Products API calls
      services.ts              # Services API calls
      components.ts            # Components API calls
      resources.ts             # Resources API calls
      repositories.ts          # Repositories API calls
      incidents.ts             # Incidents API calls
      scorecards.ts            # Scorecards API calls
      graphql.ts               # GraphQL client
      import-export.ts         # Import/Export API calls
    types/
      index.ts                 # Re-exports
      common.ts                # ApiResponse, PaginatedResponse, etc.
      auth.ts                  # User, LoginRequest, TokenResponse
      team.ts                  # Team, TeamCreate, TeamUpdate
      person.ts                # Person, PersonCreate, PersonUpdate
      product.ts               # Product, ProductCreate, ProductUpdate
      service.ts               # ServiceType enums + interfaces
      component.ts             # ComponentType enums + interfaces
      resource.ts              # ResourceType enums + interfaces
      repository.ts            # Repository, RepositoryCreate
      incident.ts              # Incident, IncidentTimeline, etc.
      scorecard.ts             # Scorecard, Criteria, EvaluationResult
      graph.ts                 # GraphNode, GraphEdge, DependencyGraph
    components/
      layout/
        AppSidebar.vue         # Sidebar navigation
        AppHeader.vue          # Top bar with user menu, search
        AppFooter.vue          # Footer
        ToastContainer.vue     # Toast notification stack
      common/
        DataTable.vue          # Reusable table with sort/filter/pagination
        SearchInput.vue        # Debounced search input
        FilterBar.vue          # Entity-specific filter dropdowns
        Pagination.vue         # Pagination controls
        StatusBadge.vue        # Operational status indicator
        EntityTypeBadge.vue    # Type badge (api, library, etc.)
        ConfirmDialog.vue      # Confirmation modal
        EmptyState.vue         # No data placeholder
        LoadingSpinner.vue     # Loading indicator
        ErrorAlert.vue         # Error state display
        BreadcrumbNav.vue      # Breadcrumb trail
      forms/
        TeamForm.vue           # Team create/edit form
        PersonForm.vue
        ProductForm.vue
        ServiceForm.vue
        ComponentForm.vue
        ResourceForm.vue
        RepositoryForm.vue
      cards/
        StatCard.vue           # Dashboard stat card
        EntityCard.vue         # Entity summary card for grid view
      graph/                   # D3.js components (TPRD-010)
        DependencyGraph.vue
        GraphControls.vue
        GraphLegend.vue
      incidents/               # Incident components (TPRD-007)
        IncidentTimeline.vue
        IncidentStatusBadge.vue
      scorecards/              # Scorecard components (TPRD-008)
        ScorecardEvaluation.vue
        CriteriaChecklist.vue
    views/
      DashboardView.vue
      LoginView.vue
      ProductListView.vue
      ProductDetailView.vue
      ServiceListView.vue
      ServiceDetailView.vue
      ComponentListView.vue
      ComponentDetailView.vue
      ResourceListView.vue
      ResourceDetailView.vue
      RepositoryListView.vue
      RepositoryDetailView.vue
      TeamListView.vue
      TeamDetailView.vue
      PeopleListView.vue
      PersonDetailView.vue
      IncidentListView.vue
      IncidentDetailView.vue
      ScorecardListView.vue
      ScorecardDetailView.vue
      DependencyGraphView.vue
      StatusPageView.vue       # Internal status view
      ImportExportView.vue
      NotFoundView.vue
    composables/
      useAuth.ts               # Auth helper (login, logout, token refresh)
      usePagination.ts         # Pagination state and navigation
      useSearch.ts             # Debounced search composable
      useToast.ts              # Toast notification helper
      useEntityCrud.ts         # Generic CRUD composable
      useTheme.ts              # Dark mode toggle
    assets/
      logo.svg                 # Holman Enterprises logo
  tests/
    unit/
      stores/
      components/
      composables/
    e2e/
      auth.spec.ts
      dashboard.spec.ts
      services.spec.ts
      incidents.spec.ts
```

#### Design Patterns
- **Composables**: Extract reusable logic into `useX()` functions
- **Generic CRUD Pattern**: `useEntityCrud<T>(apiModule)` provides list, detail, create, update, delete operations with loading/error management
- **API Module Pattern**: Each entity has a typed API module (e.g., `api/services.ts`) that maps to REST endpoints
- **Store Pattern**: Each entity has a Pinia store; stores call API modules, not Axios directly
- **Container/Presenter**: View components manage data flow; presentational components receive props

### 4.3 Router Configuration

```typescript
const routes: RouteRecordRaw[] = [
  { path: '/login', name: 'login', component: LoginView, meta: { public: true } },
  {
    path: '/',
    component: AppLayout,  // Layout with sidebar + header
    meta: { requiresAuth: true },
    children: [
      { path: '', name: 'dashboard', component: DashboardView },
      // Products
      { path: 'products', name: 'products', component: ProductListView },
      { path: 'products/:id', name: 'product-detail', component: ProductDetailView },
      // Services
      { path: 'services', name: 'services', component: ServiceListView },
      { path: 'services/:id', name: 'service-detail', component: ServiceDetailView },
      // Components
      { path: 'components', name: 'components', component: ComponentListView },
      { path: 'components/:id', name: 'component-detail', component: ComponentDetailView },
      // Resources
      { path: 'resources', name: 'resources', component: ResourceListView },
      { path: 'resources/:id', name: 'resource-detail', component: ResourceDetailView },
      // Repositories
      { path: 'repositories', name: 'repositories', component: RepositoryListView },
      { path: 'repositories/:id', name: 'repository-detail', component: RepositoryDetailView },
      // Teams
      { path: 'teams', name: 'teams', component: TeamListView },
      { path: 'teams/:id', name: 'team-detail', component: TeamDetailView },
      // People
      { path: 'people', name: 'people', component: PeopleListView },
      { path: 'people/:id', name: 'person-detail', component: PersonDetailView },
      // Incidents
      { path: 'incidents', name: 'incidents', component: IncidentListView },
      { path: 'incidents/:id', name: 'incident-detail', component: IncidentDetailView },
      // Scorecards
      { path: 'scorecards', name: 'scorecards', component: ScorecardListView },
      { path: 'scorecards/:id', name: 'scorecard-detail', component: ScorecardDetailView },
      // Graph
      { path: 'graph', name: 'dependency-graph', component: DependencyGraphView },
      // Status
      { path: 'status', name: 'status', component: StatusPageView },
      // Import/Export
      { path: 'import-export', name: 'import-export', component: ImportExportView, meta: { roles: ['admin'] } },
      // 404
      { path: ':pathMatch(.*)*', name: 'not-found', component: NotFoundView },
    ],
  },
];
```

### 4.4 Sidebar Navigation Structure

```
🏠 Dashboard
━━━━━━━━━━━━━━━━━━
📊 Dependency Graph
🔴 Status Page
📋 Scorecards
🚨 Incidents
━━━━━━━━━━━━━━━━━━
📦 Products
⚙️ Services
🧩 Components
🖥️ Resources
📂 Repositories
━━━━━━━━━━━━━━━━━━
👥 Teams
👤 People
━━━━━━━━━━━━━━━━━━
📥 Import / Export   (Admin only)
```

### 4.5 Pinia Store Pattern (Generic Example)

```typescript
// stores/services.ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Service, ServiceCreate, ServiceUpdate } from '@/types/service'
import type { PaginatedResponse, PaginationParams } from '@/types/common'
import { servicesApi } from '@/api/services'

export const useServicesStore = defineStore('services', () => {
  // State
  const items = ref<Service[]>([])
  const current = ref<Service | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const pagination = ref<PaginationParams>({
    page: 1,
    perPage: 25,
    total: 0,
    totalPages: 0,
  })
  const filters = ref({
    search: '',
    type: '',
    status: '',
    operationalStatus: '',
    teamId: '',
    sort: 'name',
    order: 'asc' as 'asc' | 'desc',
  })

  // Getters
  const hasItems = computed(() => items.value.length > 0)
  const isFiltered = computed(() =>
    filters.value.search || filters.value.type || filters.value.status
  )

  // Actions
  async function fetchList() {
    loading.value = true
    error.value = null
    try {
      const response = await servicesApi.list({
        page: pagination.value.page,
        per_page: pagination.value.perPage,
        search: filters.value.search || undefined,
        type: filters.value.type || undefined,
        status: filters.value.status || undefined,
        operational_status: filters.value.operationalStatus || undefined,
        team_id: filters.value.teamId || undefined,
        sort: filters.value.sort,
        order: filters.value.order,
      })
      items.value = response.data
      pagination.value.total = response.meta.total
      pagination.value.totalPages = response.meta.total_pages
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Failed to fetch services'
    } finally {
      loading.value = false
    }
  }

  async function fetchDetail(id: string) {
    loading.value = true
    error.value = null
    try {
      const response = await servicesApi.get(id)
      current.value = response.data
    } catch (err: any) {
      error.value = err.response?.data?.detail || 'Service not found'
    } finally {
      loading.value = false
    }
  }

  async function create(data: ServiceCreate) {
    const response = await servicesApi.create(data)
    items.value.unshift(response.data)
    return response.data
  }

  async function update(id: string, data: ServiceUpdate) {
    const response = await servicesApi.update(id, data)
    const idx = items.value.findIndex(i => i.id === id)
    if (idx >= 0) items.value[idx] = response.data
    if (current.value?.id === id) current.value = response.data
    return response.data
  }

  async function remove(id: string) {
    await servicesApi.delete(id)
    items.value = items.value.filter(i => i.id !== id)
    if (current.value?.id === id) current.value = null
  }

  function setPage(page: number) {
    pagination.value.page = page
    fetchList()
  }

  function setFilters(newFilters: Partial<typeof filters.value>) {
    Object.assign(filters.value, newFilters)
    pagination.value.page = 1 // Reset to page 1
    fetchList()
  }

  function resetFilters() {
    filters.value = { search: '', type: '', status: '', operationalStatus: '', teamId: '', sort: 'name', order: 'asc' }
    pagination.value.page = 1
    fetchList()
  }

  return {
    items, current, loading, error, pagination, filters,
    hasItems, isFiltered,
    fetchList, fetchDetail, create, update, remove,
    setPage, setFilters, resetFilters,
  }
})
```

### 4.6 API Client Pattern

```typescript
// api/client.ts
import axios from 'axios'
import { useAuthStore } from '@/stores/auth'
import router from '@/router'

const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  headers: { 'Content-Type': 'application/json' },
})

// Request interceptor: attach access token
client.interceptors.request.use((config) => {
  const auth = useAuthStore()
  if (auth.accessToken) {
    config.headers.Authorization = `Bearer ${auth.accessToken}`
  }
  return config
})

// Response interceptor: handle 401, refresh token
client.interceptors.response.use(
  (response) => response,
  async (error) => {
    const auth = useAuthStore()
    if (error.response?.status === 401 && !error.config._retry) {
      error.config._retry = true
      try {
        await auth.refreshAccessToken()
        error.config.headers.Authorization = `Bearer ${auth.accessToken}`
        return client(error.config)
      } catch {
        auth.logout()
        router.push('/login')
      }
    }
    return Promise.reject(error)
  }
)

export default client
```

```typescript
// api/services.ts
import client from './client'
import type { Service, ServiceCreate, ServiceUpdate } from '@/types/service'
import type { ApiResponse, PaginatedResponse } from '@/types/common'

interface ServiceListParams {
  page?: number
  per_page?: number
  search?: string
  type?: string
  status?: string
  operational_status?: string
  team_id?: string
  sort?: string
  order?: string
}

export const servicesApi = {
  list: (params: ServiceListParams) =>
    client.get<PaginatedResponse<Service>>('/services', { params }).then(r => r.data),

  get: (id: string) =>
    client.get<ApiResponse<Service>>(`/services/${id}`).then(r => r.data),

  create: (data: ServiceCreate) =>
    client.post<ApiResponse<Service>>('/services', data).then(r => r.data),

  update: (id: string, data: ServiceUpdate) =>
    client.put<ApiResponse<Service>>(`/services/${id}`, data).then(r => r.data),

  delete: (id: string) =>
    client.delete(`/services/${id}`),

  changeOperationalStatus: (id: string, status: string) =>
    client.patch<ApiResponse<Service>>(`/services/${id}/operational-status`, {
      operational_status: status,
    }).then(r => r.data),
}
```

### 4.7 TypeScript Types

```typescript
// types/service.ts
export type ServiceTypeEnum = 'api' | 'web_application' | 'database' | 'message_queue' | 'cache'
  | 'cdn' | 'dns' | 'load_balancer' | 'monitoring' | 'logging' | 'other'

export type OperationalStatusEnum = 'operational' | 'degraded' | 'partial_outage' | 'major_outage'

export interface Service {
  id: string
  name: string
  type: ServiceTypeEnum
  description?: string
  status: string
  operational_status: OperationalStatusEnum
  team_id?: string
  team?: { id: string; name: string }
  attributes?: Record<string, unknown>
  components?: Array<{ id: string; name: string; type: string; operational_status: string }>
  resources?: Array<{ id: string; name: string; type: string; operational_status: string }>
  depends_on?: Array<{ id: string; name: string; type: string; operational_status: string }>
  dependents?: Array<{ id: string; name: string; type: string }>
  products?: Array<{ id: string; name: string }>
  repositories?: Array<{ id: string; name: string; provider: string }>
  assignments?: Array<{ person_id: string; person_name: string; role: string }>
  active_incidents?: Array<{ id: string; title: string; severity: string; status: string }>
  created_at: string
  updated_at: string
}

export interface ServiceCreate {
  name: string
  type: ServiceTypeEnum
  description?: string
  team_id?: string
  attributes?: Record<string, unknown>
}

export interface ServiceUpdate extends Partial<ServiceCreate> {}
```

```typescript
// types/common.ts
export interface ApiResponse<T> {
  data: T
}

export interface PaginationMeta {
  total: number
  page: number
  per_page: number
  total_pages: number
  next_cursor?: string | null
  prev_cursor?: string | null
}

export interface PaginatedResponse<T> {
  data: T[]
  meta: PaginationMeta
}

export interface PaginationParams {
  page: number
  perPage: number
  total: number
  totalPages: number
}

export interface ProblemDetail {
  type: string
  title: string
  status: number
  detail: string
  instance: string
}
```

### 4.8 Tailwind Configuration

```javascript
// tailwind.config.js
export default {
  content: ['./index.html', './src/**/*.{vue,ts,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Holman Enterprises brand palette
        brand: {
          50:  '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',  // Primary
          600: '#2563eb',
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a',
          950: '#172554',
        },
        status: {
          operational: '#10b981',    // Green
          degraded:    '#f59e0b',    // Amber
          partial:     '#f97316',    // Orange
          outage:      '#ef4444',    // Red
        },
        severity: {
          minor:    '#60a5fa',       // Blue
          major:    '#f59e0b',       // Amber
          critical: '#ef4444',       // Red
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/typography'),
  ],
}
```

### 4.9 Dashboard View Specification

The Dashboard MUST display:
1. **Summary Stats Row** (top): Total Products, Services, Components, Resources, Repositories, Teams — each with count and active/total ratio
2. **Operational Status Bar**: Services by status (operational / degraded / outage) — horizontal stacked bar
3. **Active Incidents Panel**: List of unresolved incidents with severity badge, title, affected entities count, duration
4. **Recent Changes**: Last 10 audit log entries showing entity type, action, user, timestamp
5. **Scorecard Health**: Average scores for each entity type, with worst-scoring entities highlighted

### 4.10 Entity List View Pattern

All entity list views follow this layout:
1. **Header**: Entity name (e.g., "Services"), count, "Add New" button (Editor+ role)
2. **Filter Bar**: Search input, type dropdown, status dropdown, team dropdown, sort controls
3. **Data Table**: Columns vary by entity; common: Name, Type, Status, Team, Updated
4. **Pagination**: Page controls at bottom
5. **Empty State**: When no results, show illustration + "No services found" + "Create your first service" CTA

### 4.11 Entity Detail View Pattern

All entity detail views follow this layout:
1. **Breadcrumb**: Dashboard > Services > Customer API
2. **Header**: Entity name, type badge, operational status badge, Edit/Delete buttons
3. **Tab Navigation**: Overview | Relationships | Assignments | Incidents | Scorecards
4. **Overview Tab**: Description, attributes table, team link, key metadata
5. **Relationships Tab**: Panels for each relationship type (components, resources, dependencies, etc.) with add/remove controls
6. **Assignments Tab**: People assigned with roles; add/remove assignment controls
7. **Incidents Tab**: Active and recent incidents affecting this entity
8. **Scorecards Tab**: All scorecards that apply to this entity type with evaluation results

## 5. SECURITY REQUIREMENTS

- JWT stored in memory (Pinia store) — NOT in localStorage
- Refresh token stored in httpOnly cookie (set by backend)
- All API requests include JWT via Axios interceptor
- Route guards check authentication and role before rendering views
- Admin-only views (Import/Export) hidden from sidebar for non-admin users
- No sensitive data rendered in component data attributes or console logs in production
- CSP headers configured via backend

## 6. TESTING REQUIREMENTS

### 6.1 Unit Tests (Vitest + Vue Test Utils)
- Each Pinia store: test actions, getters, state mutations
- API modules: mock Axios, verify request shapes
- Composables: test reactive behavior
- Components: mount with test data, verify rendered output
- DataTable: verify sorting, filtering, pagination interactions
- StatusBadge: verify correct color/text for each status
- Route guards: verify redirect behavior for unauthenticated/unauthorized

### 6.2 E2E Tests (Playwright)
- **Login flow**: Navigate to /login, enter credentials, verify redirect to dashboard
- **CRUD flow**: Navigate to services, create new service, edit it, delete it
- **Navigation**: Verify all sidebar links navigate correctly
- **Search & Filter**: Search for entity, apply filters, verify results
- **Dark mode**: Toggle dark mode, verify styling changes

## 7. NON-FUNCTIONAL REQUIREMENTS

- **Performance**: Lighthouse score > 90 (Performance, Accessibility, Best Practices)
- **Bundle Size**: < 500KB gzipped for initial load (code-split by route)
- **Accessibility**: WCAG 2.1 Level AA — keyboard navigation, ARIA labels, color contrast
- **Browser Support**: Chrome 90+, Edge 90+, Firefox 90+, Safari 15+
- **Responsive**: Desktop-first with usable mobile layout (sidebar becomes hamburger menu)

## 8. MIGRATION & DEPLOYMENT

- Frontend built as static assets via `vite build`
- Deployed alongside backend via Docker (nginx serving static files + reverse proxy to API)
- Environment variables via `.env.production`: `VITE_API_BASE_URL`, `VITE_OKTA_CLIENT_ID`, `VITE_OKTA_ISSUER`

## 9. IMPLEMENTATION GUIDANCE FOR CODING AGENTS

### Implementation Order
1. Scaffold Vite + Vue 3 + TypeScript project
2. Configure Tailwind CSS with brand theme
3. Create types (`types/` directory)
4. Create API client with interceptors (`api/client.ts`)
5. Create auth store and login view
6. Create layout components (Sidebar, Header, Footer)
7. Create common components (DataTable, StatusBadge, Pagination, etc.)
8. Create entity API modules
9. Create entity Pinia stores
10. Create entity list views (all follow same pattern)
11. Create entity detail views
12. Create Dashboard view
13. Create form components for create/edit
14. Integrate graph, incident, and scorecard views (from their respective TPRDs)

### Do NOT
- Do NOT use Options API — always use Composition API with `<script setup lang="ts">`
- Do NOT write custom CSS — use Tailwind utility classes exclusively
- Do NOT store JWT in localStorage — keep in memory (Pinia store)
- Do NOT use `any` type — always provide proper TypeScript types
- Do NOT import components globally — use local imports
- Do NOT use inline styles
- Do NOT skip loading/error/empty states on any data-fetching view

### Verify
- [ ] `npm run build` produces no TypeScript errors
- [ ] All routes render correctly with mock data
- [ ] Auth flow works end-to-end (login, token refresh, logout)
- [ ] RBAC route guards prevent unauthorized access
- [ ] Dark mode toggle works across all views
- [ ] Keyboard navigation works for all interactive elements
- [ ] All entity CRUD operations work through UI
- [ ] Lighthouse score > 90

## 10. OPEN QUESTIONS

None.
