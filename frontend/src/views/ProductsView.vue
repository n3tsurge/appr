<script setup lang="ts">
import { ref, onMounted } from 'vue'
import AppLayout from '@/components/AppLayout.vue'
import DataTable from '@/components/DataTable.vue'
import Pagination from '@/components/Pagination.vue'
import { apiGet } from '@/api/client'
import { statusColor, capitalize } from '@/utils/format'
import type { Product, PaginatedResponse } from '@/types'

const rows = ref<Product[]>([])
const loading = ref(false)
const page = ref(1)
const totalPages = ref(0)
const total = ref(0)
const perPage = 20

const columns = [
  { key: 'name', label: 'Name' },
  { key: 'status', label: 'Status' },
  { key: 'owner_team', label: 'Owner' },
]

async function fetchData(p: number) {
  loading.value = true
  try {
    const res = await apiGet<PaginatedResponse<Product>>(`/products?page=${p}&per_page=${perPage}`)
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
      <h1 class="text-xl font-semibold text-gray-800">Products</h1>
    </template>

    <div>
      <div class="mb-6">
        <h2 class="text-2xl font-bold text-gray-900">Products</h2>
        <p class="mt-1 text-sm text-gray-500">{{ total }} total products</p>
      </div>

      <DataTable
        :columns="columns"
        :rows="(rows as unknown as Record<string, unknown>[])"
        :loading="loading"
      >
        <template #status="{ value }">
          <span :class="['inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium', statusColor(value as string)]">
            {{ capitalize(value as string) }}
          </span>
        </template>
        <template #owner_team="{ row }">
          {{ (row as unknown as Product).owner_team?.name ?? '-' }}
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
