<script setup lang="ts">
import { ref, onMounted } from 'vue'
import AppLayout from '@/components/AppLayout.vue'
import { apiGet } from '@/api/client'
import type { PaginatedResponse, Service, Component, Product, Incident } from '@/types'

interface StatCard {
  label: string
  count: number
  route: string
  icon: string
  color: string
  bgColor: string
}

const cards = ref<StatCard[]>([
  { label: 'Services', count: 0, route: '/services', icon: '⚙', color: 'text-brand-600', bgColor: 'bg-brand-50' },
  { label: 'Components', count: 0, route: '/components', icon: '◈', color: 'text-purple-600', bgColor: 'bg-purple-50' },
  { label: 'Products', count: 0, route: '/products', icon: '◻', color: 'text-green-600', bgColor: 'bg-green-50' },
  { label: 'Incidents', count: 0, route: '/incidents', icon: '⚠', color: 'text-red-600', bgColor: 'bg-red-50' },
])

const loading = ref(true)

async function fetchCounts() {
  loading.value = true
  try {
    const [services, components, products, incidents] = await Promise.allSettled([
      apiGet<PaginatedResponse<Service>>('/services?page=1&per_page=1'),
      apiGet<PaginatedResponse<Component>>('/components?page=1&per_page=1'),
      apiGet<PaginatedResponse<Product>>('/products?page=1&per_page=1'),
      apiGet<PaginatedResponse<Incident>>('/incidents?page=1&per_page=1'),
    ])

    if (services.status === 'fulfilled') cards.value[0].count = services.value.meta?.total ?? 0
    if (components.status === 'fulfilled') cards.value[1].count = components.value.meta?.total ?? 0
    if (products.status === 'fulfilled') cards.value[2].count = products.value.meta?.total ?? 0
    if (incidents.status === 'fulfilled') cards.value[3].count = incidents.value.meta?.total ?? 0
  } finally {
    loading.value = false
  }
}

onMounted(fetchCounts)
</script>

<template>
  <AppLayout>
    <template #header-title>
      <h1 class="text-xl font-semibold text-gray-800">Dashboard</h1>
    </template>

    <div>
      <div class="mb-6">
        <h2 class="text-2xl font-bold text-gray-900">Overview</h2>
        <p class="mt-1 text-sm text-gray-500">Your application inventory at a glance</p>
      </div>

      <!-- Stat cards -->
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 mb-8">
        <RouterLink
          v-for="card in cards"
          :key="card.label"
          :to="card.route"
          class="bg-white rounded-xl border border-gray-200 shadow-sm p-6 hover:shadow-md hover:border-brand-200 transition-all group"
        >
          <div class="flex items-center justify-between mb-4">
            <span
              :class="[card.bgColor, card.color, 'w-10 h-10 rounded-lg flex items-center justify-center text-xl']"
            >
              {{ card.icon }}
            </span>
            <svg class="w-5 h-5 text-gray-300 group-hover:text-brand-400 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
            </svg>
          </div>
          <div>
            <div v-if="loading" class="h-8 w-16 bg-gray-100 animate-pulse rounded" />
            <p v-else class="text-3xl font-bold text-gray-900">{{ card.count.toLocaleString() }}</p>
            <p class="text-sm font-medium text-gray-500 mt-1">{{ card.label }}</p>
          </div>
        </RouterLink>
      </div>

      <!-- Quick links -->
      <div class="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
        <h3 class="text-base font-semibold text-gray-800 mb-4">Quick Access</h3>
        <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
          <RouterLink
            v-for="item in [
              { to: '/teams', label: 'Teams', icon: '◯' },
              { to: '/people', label: 'People', icon: '◎' },
              { to: '/repositories', label: 'Repositories', icon: '⊡' },
              { to: '/resources', label: 'Resources', icon: '◆' },
              { to: '/scorecards', label: 'Scorecards', icon: '◈' },
            ]"
            :key="item.to"
            :to="item.to"
            class="flex flex-col items-center gap-2 px-4 py-4 rounded-lg bg-gray-50 hover:bg-brand-50 hover:text-brand-700 text-gray-600 transition-colors border border-gray-100 hover:border-brand-200"
          >
            <span class="text-2xl">{{ item.icon }}</span>
            <span class="text-xs font-medium">{{ item.label }}</span>
          </RouterLink>
        </div>
      </div>
    </div>
  </AppLayout>
</template>
