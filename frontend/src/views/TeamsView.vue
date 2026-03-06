<script setup lang="ts">
import { ref, onMounted } from 'vue'
import AppLayout from '@/components/AppLayout.vue'
import DataTable from '@/components/DataTable.vue'
import Pagination from '@/components/Pagination.vue'
import { apiGet } from '@/api/client'
import type { Team, PaginatedResponse } from '@/types'

const rows = ref<Team[]>([])
const loading = ref(false)
const page = ref(1)
const totalPages = ref(0)
const total = ref(0)
const perPage = 20

const columns = [
  { key: 'name', label: 'Name' },
  { key: 'slug', label: 'Slug' },
  { key: 'email', label: 'Email' },
  { key: 'member_count', label: 'Members' },
]

async function fetchData(p: number) {
  loading.value = true
  try {
    const res = await apiGet<PaginatedResponse<Team>>(`/teams?page=${p}&per_page=${perPage}`)
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
      <h1 class="text-xl font-semibold text-gray-800">Teams</h1>
    </template>

    <div>
      <div class="mb-6">
        <h2 class="text-2xl font-bold text-gray-900">Teams</h2>
        <p class="mt-1 text-sm text-gray-500">{{ total }} total teams</p>
      </div>

      <DataTable
        :columns="columns"
        :rows="(rows as unknown as Record<string, unknown>[])"
        :loading="loading"
      >
        <template #slug="{ value }">
          <span class="font-mono text-xs text-gray-500">{{ value }}</span>
        </template>
        <template #email="{ value }">
          <a v-if="value" :href="`mailto:${value}`" class="text-brand-600 hover:underline text-xs">
            {{ value }}
          </a>
          <span v-else class="text-gray-400">-</span>
        </template>
        <template #member_count="{ value }">
          <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-700">
            {{ value ?? 0 }}
          </span>
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
