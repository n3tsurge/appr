<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppLayout from '@/components/AppLayout.vue'
import { apiGet } from '@/api/client'
import { capitalize, formatDate, statusColor } from '@/utils/format'
import type { Service, ApiResponse } from '@/types'

const route = useRoute()
const router = useRouter()

const service = ref<Service | null>(null)
const loading = ref(true)
const error = ref('')

async function fetchService() {
  loading.value = true
  error.value = ''
  try {
    const res = await apiGet<ApiResponse<Service>>(`/services/${route.params.id}`)
    service.value = res.data
  } catch {
    error.value = 'Failed to load service details.'
  } finally {
    loading.value = false
  }
}

onMounted(fetchService)
</script>

<template>
  <AppLayout>
    <template #header-title>
      <h1 class="text-xl font-semibold text-gray-800">Service Detail</h1>
    </template>

    <div>
      <!-- Back button -->
      <button
        @click="router.push('/services')"
        class="flex items-center gap-1 text-sm text-gray-500 hover:text-brand-600 mb-6 transition-colors"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
        </svg>
        Back to Services
      </button>

      <!-- Loading -->
      <div v-if="loading" class="flex items-center justify-center py-20">
        <svg class="animate-spin h-8 w-8 text-brand-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
      </div>

      <!-- Error -->
      <div v-else-if="error" class="bg-red-50 border border-red-200 rounded-xl p-6 text-red-700">
        {{ error }}
      </div>

      <!-- Content -->
      <div v-else-if="service" class="space-y-6">
        <!-- Header card -->
        <div class="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
          <div class="flex items-start justify-between">
            <div>
              <h2 class="text-2xl font-bold text-gray-900">{{ service.name }}</h2>
              <p class="text-sm text-gray-500 mt-1 font-mono">{{ service.slug }}</p>
            </div>
            <div class="flex gap-2">
              <span :class="['inline-flex items-center px-3 py-1 rounded-full text-sm font-medium', statusColor(service.status)]">
                {{ capitalize(service.status) }}
              </span>
              <span :class="['inline-flex items-center px-3 py-1 rounded-full text-sm font-medium', statusColor(service.operational_status)]">
                {{ capitalize(service.operational_status) }}
              </span>
            </div>
          </div>

          <p v-if="service.description" class="mt-4 text-sm text-gray-600 leading-relaxed">
            {{ service.description }}
          </p>
        </div>

        <!-- Details grid -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div class="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
            <h3 class="text-base font-semibold text-gray-800 mb-4">Service Details</h3>
            <dl class="space-y-3">
              <div class="flex justify-between text-sm">
                <dt class="text-gray-500 font-medium">Type</dt>
                <dd class="text-gray-900">{{ capitalize(service.service_type) }}</dd>
              </div>
              <div class="flex justify-between text-sm">
                <dt class="text-gray-500 font-medium">Tier</dt>
                <dd class="text-gray-900">{{ service.tier ?? '-' }}</dd>
              </div>
              <div class="flex justify-between text-sm">
                <dt class="text-gray-500 font-medium">Lifecycle</dt>
                <dd class="text-gray-900">{{ capitalize(service.lifecycle_status ?? '-') }}</dd>
              </div>
              <div class="flex justify-between text-sm">
                <dt class="text-gray-500 font-medium">Owner Team</dt>
                <dd class="text-gray-900">{{ service.owner_team?.name ?? service.owner_team_id ?? '-' }}</dd>
              </div>
            </dl>
          </div>

          <div class="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
            <h3 class="text-base font-semibold text-gray-800 mb-4">Links & Metadata</h3>
            <dl class="space-y-3">
              <div class="flex justify-between text-sm">
                <dt class="text-gray-500 font-medium">ID</dt>
                <dd class="text-gray-900 font-mono text-xs truncate max-w-40">{{ service.id }}</dd>
              </div>
              <div v-if="service.docs_url" class="flex justify-between text-sm">
                <dt class="text-gray-500 font-medium">Docs</dt>
                <dd>
                  <a :href="service.docs_url" target="_blank" class="text-brand-600 hover:underline truncate max-w-40 inline-block">
                    {{ service.docs_url }}
                  </a>
                </dd>
              </div>
              <div v-if="service.repo_url" class="flex justify-between text-sm">
                <dt class="text-gray-500 font-medium">Repository</dt>
                <dd>
                  <a :href="service.repo_url" target="_blank" class="text-brand-600 hover:underline truncate max-w-40 inline-block">
                    {{ service.repo_url }}
                  </a>
                </dd>
              </div>
              <div class="flex justify-between text-sm">
                <dt class="text-gray-500 font-medium">Created</dt>
                <dd class="text-gray-900">{{ formatDate(service.created_at ?? '') }}</dd>
              </div>
              <div class="flex justify-between text-sm">
                <dt class="text-gray-500 font-medium">Updated</dt>
                <dd class="text-gray-900">{{ formatDate(service.updated_at ?? '') }}</dd>
              </div>
            </dl>
          </div>
        </div>

        <!-- Tags -->
        <div v-if="service.tags && service.tags.length > 0" class="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
          <h3 class="text-base font-semibold text-gray-800 mb-3">Tags</h3>
          <div class="flex flex-wrap gap-2">
            <span
              v-for="tag in service.tags"
              :key="tag"
              class="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-brand-50 text-brand-700 border border-brand-100"
            >
              {{ tag }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </AppLayout>
</template>
