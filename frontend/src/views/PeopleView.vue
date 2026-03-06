<script setup lang="ts">
import { ref, onMounted } from 'vue'
import AppLayout from '@/components/AppLayout.vue'
import DataTable from '@/components/DataTable.vue'
import Pagination from '@/components/Pagination.vue'
import { apiGet } from '@/api/client'
import type { Person, PaginatedResponse } from '@/types'

const rows = ref<Person[]>([])
const loading = ref(false)
const page = ref(1)
const totalPages = ref(0)
const total = ref(0)
const perPage = 20

const columns = [
  { key: 'display_name', label: 'Name' },
  { key: 'email', label: 'Email' },
  { key: 'title', label: 'Title' },
  { key: 'location', label: 'Location' },
]

async function fetchData(p: number) {
  loading.value = true
  try {
    const res = await apiGet<PaginatedResponse<Person>>(`/people?page=${p}&per_page=${perPage}`)
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
      <h1 class="text-xl font-semibold text-gray-800">People</h1>
    </template>

    <div>
      <div class="mb-6">
        <h2 class="text-2xl font-bold text-gray-900">People</h2>
        <p class="mt-1 text-sm text-gray-500">{{ total }} total people</p>
      </div>

      <DataTable
        :columns="columns"
        :rows="(rows as unknown as Record<string, unknown>[])"
        :loading="loading"
      >
        <template #display_name="{ value, row }">
          <div class="flex items-center gap-2">
            <div class="w-7 h-7 rounded-full bg-brand-100 text-brand-700 flex items-center justify-center text-xs font-semibold flex-shrink-0">
              {{ String(value || '').charAt(0).toUpperCase() }}
            </div>
            <span class="font-medium text-gray-900">{{ value || '-' }}</span>
          </div>
        </template>
        <template #email="{ value }">
          <a v-if="value" :href="`mailto:${value}`" class="text-brand-600 hover:underline text-sm">
            {{ value }}
          </a>
          <span v-else>-</span>
        </template>
        <template #title="{ value }">
          <span class="text-gray-600">{{ value ?? '-' }}</span>
        </template>
        <template #location="{ value }">
          <span class="text-gray-600">{{ value ?? '-' }}</span>
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
