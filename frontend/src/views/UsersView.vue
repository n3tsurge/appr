<script setup lang="ts">
import { ref, onMounted } from 'vue'
import AppLayout from '@/components/AppLayout.vue'
import DataTable from '@/components/DataTable.vue'
import Pagination from '@/components/Pagination.vue'
import { apiGet } from '@/api/client'
import { capitalize, formatDate } from '@/utils/format'
import { useAuthStore } from '@/stores/auth'
import type { User, PaginatedResponse } from '@/types'

const authStore = useAuthStore()

const rows = ref<User[]>([])
const loading = ref(false)
const page = ref(1)
const totalPages = ref(0)
const total = ref(0)
const perPage = 20

const columns = [
  { key: 'email', label: 'Email' },
  { key: 'display_name', label: 'Display Name' },
  { key: 'role', label: 'Role' },
  { key: 'is_active', label: 'Active' },
  { key: 'last_login_at', label: 'Last Login' },
]

async function fetchData(p: number) {
  if (!authStore.isAdmin) return
  loading.value = true
  try {
    const res = await apiGet<PaginatedResponse<User>>(`/users?page=${p}&per_page=${perPage}`)
    rows.value = res.data
    total.value = res.meta.total
    totalPages.value = res.meta.total_pages
    page.value = p
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  if (authStore.isAdmin) fetchData(1)
})
</script>

<template>
  <AppLayout>
    <template #header-title>
      <h1 class="text-xl font-semibold text-gray-800">Users</h1>
    </template>

    <div>
      <!-- Access denied -->
      <div v-if="!authStore.isAdmin" class="flex flex-col items-center justify-center py-20">
        <div class="w-16 h-16 rounded-full bg-red-100 flex items-center justify-center mb-4">
          <svg class="w-8 h-8 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
          </svg>
        </div>
        <h2 class="text-xl font-semibold text-gray-800 mb-2">Access Denied</h2>
        <p class="text-sm text-gray-500 text-center max-w-sm">
          You do not have permission to view this page. This section is restricted to administrators only.
        </p>
      </div>

      <!-- Admin view -->
      <template v-else>
        <div class="mb-6">
          <h2 class="text-2xl font-bold text-gray-900">Users</h2>
          <p class="mt-1 text-sm text-gray-500">{{ total }} total users</p>
        </div>

        <DataTable
          :columns="columns"
          :rows="(rows as unknown as Record<string, unknown>[])"
          :loading="loading"
        >
          <template #email="{ value }">
            <span class="font-medium text-gray-900">{{ value }}</span>
          </template>
          <template #role="{ value }">
            <span :class="[
              'inline-flex items-center px-2 py-0.5 rounded text-xs font-medium capitalize',
              (value as string) === 'admin' ? 'bg-purple-100 text-purple-700' : 'bg-gray-100 text-gray-600'
            ]">
              {{ capitalize(value as string) }}
            </span>
          </template>
          <template #is_active="{ value }">
            <span :class="[
              'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium',
              value ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
            ]">
              {{ value ? 'Active' : 'Inactive' }}
            </span>
          </template>
          <template #last_login_at="{ value }">
            <span class="text-gray-500 text-sm">{{ value ? formatDate(value as string) : 'Never' }}</span>
          </template>
        </DataTable>

        <Pagination
          v-if="totalPages > 1"
          :page="page"
          :total-pages="totalPages"
          :total="total"
          @change="fetchData"
        />
      </template>
    </div>
  </AppLayout>
</template>
