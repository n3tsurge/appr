<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import AppLayout from '@/components/AppLayout.vue'
import DataTable from '@/components/DataTable.vue'
import Pagination from '@/components/Pagination.vue'
import { apiGet } from '@/api/client'
import { statusColor, capitalize } from '@/utils/format'
import type { Service, PaginatedResponse } from '@/types'

const router = useRouter()

const rows = ref<Service[]>([])
const loading = ref(false)
const page = ref(1)
const totalPages = ref(0)
const total = ref(0)
const perPage = 20

const columns = [
  { key: 'name', label: 'Name' },
  { key: 'service_type', label: 'Type' },
  { key: 'status', label: 'Status' },
  { key: 'operational_status', label: 'Operational Status' },
  { key: 'owner_team', label: 'Owner Team' },
]

async function fetchData(p: number) {
  loading.value = true
  try {
    const res = await apiGet<PaginatedResponse<Service>>(`/services?page=${p}&per_page=${perPage}`)
    rows.value = res.data
    total.value = res.meta.total
    totalPages.value = res.meta.total_pages
    page.value = p
  } finally {
    loading.value = false
  }
}

function handleRowClick(row: Record<string, unknown>) {
  router.push(`/services/${row.id}`)
}

onMounted(() => fetchData(1))
</script>

<template>
  <AppLayout>
    <template #header-title>
      <h1 class="text-xl font-semibold text-gray-800">Services</h1>
    </template>

    <div>
      <div class="flex items-center justify-between mb-6">
        <div>
          <h2 class="text-2xl font-bold text-gray-900">Services</h2>
          <p class="mt-1 text-sm text-gray-500">{{ total }} total services</p>
        </div>
      </div>

      <DataTable
        :columns="columns"
        :rows="(rows as unknown as Record<string, unknown>[])"
        :loading="loading"
        @row-click="handleRowClick"
      >
        <template #service_type="{ value }">
          <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-50 text-blue-700">
            {{ capitalize(value as string) }}
          </span>
        </template>
        <template #status="{ value }">
          <span :class="['inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium', statusColor(value as string)]">
            {{ capitalize(value as string) }}
          </span>
        </template>
        <template #operational_status="{ value }">
          <span :class="['inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium', statusColor(value as string)]">
            {{ capitalize(value as string) }}
          </span>
        </template>
        <template #owner_team="{ row }">
          {{ (row as unknown as Service).owner_team?.name ?? '-' }}
        </template>
      </DataTable>

      <Pagination
        v-if="totalPages > 1"
        :page="page"
        :total-pages="totalPages"
        :total="total"
        class="mt-0"
        @change="fetchData"
      />
    </div>
  </AppLayout>
</template>
