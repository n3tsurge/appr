export interface ApiResponse<T> {
  data: T
  message?: string
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

export interface ProblemDetail {
  type: string
  title: string
  status: number
  detail?: string
  instance?: string
}

export interface PaginationParams {
  page: number
  perPage: number
  total: number
  totalPages: number
}

export type SortOrder = 'asc' | 'desc'

export interface ListParams {
  page?: number
  per_page?: number
  search?: string
  sort?: string
  order?: SortOrder
  cursor?: string
}
