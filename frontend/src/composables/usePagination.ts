import { ref, type Ref } from 'vue'

export interface PaginationState {
  page: Ref<number>
  perPage: Ref<number>
  total: Ref<number>
  totalPages: Ref<number>
  loading: Ref<boolean>
  goToPage: (n: number) => void
  refresh: () => void
}

export function usePagination(
  fetchFn: (page: number, perPage: number) => Promise<{ total: number; totalPages: number }>
): PaginationState {
  const page = ref(1)
  const perPage = ref(20)
  const total = ref(0)
  const totalPages = ref(0)
  const loading = ref(false)

  async function load(p: number) {
    loading.value = true
    try {
      const result = await fetchFn(p, perPage.value)
      total.value = result.total
      totalPages.value = result.totalPages
      page.value = p
    } finally {
      loading.value = false
    }
  }

  function goToPage(n: number) {
    if (n < 1 || (totalPages.value > 0 && n > totalPages.value)) return
    load(n)
  }

  function refresh() {
    load(page.value)
  }

  // Auto-load first page
  load(1)

  return {
    page,
    perPage,
    total,
    totalPages,
    loading,
    goToPage,
    refresh,
  }
}
