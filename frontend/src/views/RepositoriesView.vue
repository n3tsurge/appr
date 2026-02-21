<script setup lang="ts">
import { ref, onMounted } from 'vue'
import AppLayout from '@/components/AppLayout.vue'
import DataTable from '@/components/DataTable.vue'
import Pagination from '@/components/Pagination.vue'
import { apiGet } from '@/api/client'
import { capitalize } from '@/utils/format'
import type { Repository, PaginatedResponse } from '@/types'

const rows = ref<Repository[]>([])
const loading = ref(false)
const page = ref(1)
const totalPages = ref(0)
const total = ref(0)
const perPage = 20

const columns = [
  { key: 'name', label: 'Name' },
  { key: 'provider', label: 'Provider' },
  { key: 'organization', label: 'Organization' },
  { key: 'url', label: 'URL' },
]

async function fetchData(p: number) {
  loading.value = true
  try {
    const res = await apiGet<PaginatedResponse<Repository>>(`/repositories?page=${p}&per_page=${perPage}`)
    rows.value = res.data
    total.value = res.meta.total
    totalPages.value = res.meta.total_pages
    page.value = p
  } finally {
    loading.value = false
  }
}

onMounted(() => fetchData(1))
</script>

<template>
  <AppLayout>
    <template #header-title>
      <h1 class="text-xl font-semibold text-gray-800">Repositories</h1>
    </template>

    <div>
      <div class="mb-6">
        <h2 class="text-2xl font-bold text-gray-900">Repositories</h2>
        <p class="mt-1 text-sm text-gray-500">{{ total }} total repositories</p>
      </div>

      <DataTable
        :columns="columns"
        :rows="(rows as unknown as Record<string, unknown>[])"
        :loading="loading"
      >
        <template #name="{ value, row }">
          <span class="font-medium text-gray-900">{{ value }}</span>
          <span v-if="(row as unknown as Repository).is_private" class="ml-2 inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-600">
            Private
          </span>
        </template>
        <template #provider="{ value }">
          <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-indigo-50 text-indigo-700">
            {{ capitalize(value as string) }}
          </span>
        </template>
        <template #url="{ value }">
          <a v-if="value" :href="value as string" target="_blank" class="text-brand-600 hover:underline text-sm truncate max-w-xs inline-block">
            {{ value }}
          </a>
          <span v-else class="text-gray-400">-</span>
        </template>
      </DataTable>

      <Pagination
        v-if="totalPages > 1"
        :page="page"
        :total-pages="totalPages"
        :total="total"
        @change="fetchData"
      />
    </div>
  </AppLayout>
</template>
