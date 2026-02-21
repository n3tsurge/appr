<script setup lang="ts">
import { ref, onMounted } from 'vue'
import AppLayout from '@/components/AppLayout.vue'
import DataTable from '@/components/DataTable.vue'
import Pagination from '@/components/Pagination.vue'
import { apiGet } from '@/api/client'
import { capitalize } from '@/utils/format'
import type { Scorecard, PaginatedResponse } from '@/types'

const rows = ref<Scorecard[]>([])
const loading = ref(false)
const page = ref(1)
const totalPages = ref(0)
const total = ref(0)
const perPage = 20

const columns = [
  { key: 'name', label: 'Name' },
  { key: 'scorecard_type', label: 'Type' },
  { key: 'score', label: 'Score' },
  { key: 'entity_type', label: 'Target Entity' },
]

async function fetchData(p: number) {
  loading.value = true
  try {
    const res = await apiGet<PaginatedResponse<Scorecard>>(`/scorecards?page=${p}&per_page=${perPage}`)
    rows.value = res.data
    total.value = res.meta.total
    totalPages.value = res.meta.total_pages
    page.value = p
  } finally {
    loading.value = false
  }
}

function scoreColor(score: number): string {
  if (score >= 80) return 'bg-green-500'
  if (score >= 60) return 'bg-yellow-500'
  if (score >= 40) return 'bg-orange-500'
  return 'bg-red-500'
}

onMounted(() => fetchData(1))
</script>

<template>
  <AppLayout>
    <template #header-title>
      <h1 class="text-xl font-semibold text-gray-800">Scorecards</h1>
    </template>

    <div>
      <div class="mb-6">
        <h2 class="text-2xl font-bold text-gray-900">Scorecards</h2>
        <p class="mt-1 text-sm text-gray-500">{{ total }} total scorecards</p>
      </div>

      <DataTable
        :columns="columns"
        :rows="(rows as unknown as Record<string, unknown>[])"
        :loading="loading"
      >
        <template #scorecard_type="{ value }">
          <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-teal-50 text-teal-700">
            {{ capitalize(value as string) }}
          </span>
        </template>
        <template #score="{ value }">
          <div v-if="value !== null && value !== undefined" class="flex items-center gap-2 min-w-32">
            <div class="flex-1 bg-gray-100 rounded-full h-2 overflow-hidden">
              <div
                :class="['h-2 rounded-full transition-all', scoreColor(Number(value))]"
                :style="{ width: `${Math.min(100, Number(value))}%` }"
              />
            </div>
            <span class="text-sm font-semibold text-gray-700 w-8 text-right">{{ Math.round(Number(value)) }}</span>
          </div>
          <span v-else class="text-gray-400 text-sm">N/A</span>
        </template>
        <template #entity_type="{ value }">
          <span class="text-gray-600 text-sm">{{ capitalize((value as string) ?? '-') }}</span>
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
