<script setup lang="ts">
const props = defineProps<{
  page: number
  totalPages: number
  total: number
}>()

const emit = defineEmits<{
  change: [page: number]
}>()

function prev() {
  if (props.page > 1) emit('change', props.page - 1)
}

function next() {
  if (props.page < props.totalPages) emit('change', props.page + 1)
}
</script>

<template>
  <div class="flex items-center justify-between px-4 py-3 border-t border-gray-200 bg-white rounded-b-xl">
    <div class="text-sm text-gray-500">
      Showing page <span class="font-medium text-gray-700">{{ page }}</span>
      of <span class="font-medium text-gray-700">{{ totalPages }}</span>
      &mdash;
      <span class="font-medium text-gray-700">{{ total }}</span> total records
    </div>

    <div class="flex items-center gap-2">
      <button
        @click="prev"
        :disabled="page <= 1"
        class="inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium rounded-lg border border-gray-300 bg-white text-gray-700 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
        </svg>
        Previous
      </button>

      <span class="px-3 py-1.5 text-sm font-semibold text-brand-600 bg-brand-50 rounded-lg border border-brand-200">
        {{ page }}
      </span>

      <button
        @click="next"
        :disabled="page >= totalPages"
        class="inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium rounded-lg border border-gray-300 bg-white text-gray-700 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
      >
        Next
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
        </svg>
      </button>
    </div>
  </div>
</template>
