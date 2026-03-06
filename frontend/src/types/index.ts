export interface User {
  id: string
  email: string
  display_name: string
  role: string
  is_active?: boolean
  last_login_at?: string | null
  created_at?: string
  updated_at?: string
}

export interface Service {
  id: string
  name: string
  slug: string
  description?: string
  service_type: string
  status: string
  operational_status: string
  owner_team_id?: string
  owner_team?: Team
  tier?: number
  lifecycle_status?: string
  docs_url?: string
  repo_url?: string
  tags?: string[]
  created_at?: string
  updated_at?: string
}

export interface Component {
  id: string
  name: string
  slug: string
  description?: string
  component_type: string
  status: string
  owner_team_id?: string
  owner_team?: Team
  language?: string
  framework?: string
  tags?: string[]
  created_at?: string
  updated_at?: string
}

export interface Product {
  id: string
  name: string
  slug: string
  description?: string
  status: string
  owner_team_id?: string
  owner_team?: Team
  tags?: string[]
  created_at?: string
  updated_at?: string
}

export interface Team {
  id: string
  name: string
  slug: string
  description?: string
  email?: string
  slack_channel?: string
  member_count?: number
  created_at?: string
  updated_at?: string
}

export interface Person {
  id: string
  email: string
  display_name: string
  title?: string
  department?: string
  location?: string
  team_id?: string
  team?: Team
  manager_id?: string
  created_at?: string
  updated_at?: string
}

export interface Repository {
  id: string
  name: string
  url: string
  provider: string
  organization?: string
  description?: string
  language?: string
  is_private?: boolean
  default_branch?: string
  created_at?: string
  updated_at?: string
}

export interface Resource {
  id: string
  name: string
  resource_type: string
  cloud_provider?: string
  region?: string
  account_id?: string
  status: string
  tags?: Record<string, string>
  metadata?: Record<string, unknown>
  created_at?: string
  updated_at?: string
}

export interface Incident {
  id: string
  title: string
  description?: string
  severity: string
  status: string
  detected_at: string
  resolved_at?: string | null
  service_id?: string
  service?: Service
  assignee_id?: string
  created_at?: string
  updated_at?: string
}

export interface Scorecard {
  id: string
  name: string
  description?: string
  scorecard_type: string
  score?: number
  target_score?: number
  entity_type?: string
  entity_id?: string
  checks?: ScorecardCheck[]
  created_at?: string
  updated_at?: string
}

export interface ScorecardCheck {
  id: string
  name: string
  passed: boolean
  score?: number
  message?: string
}

export interface PaginatedResponse<T> {
  data: T[]
  meta: {
    total: number
    page: number
    per_page: number
    total_pages: number
  }
}

export interface ApiResponse<T> {
  data: T
  message?: string
}

export interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
  user: User
}
