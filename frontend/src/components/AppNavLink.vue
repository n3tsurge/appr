<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const props = defineProps<{
  to: string
  label: string
  icon?: string
}>()

const route = useRoute()
const isActive = computed(() => {
  if (props.to === '/dashboard') return route.path === '/dashboard'
  return route.path.startsWith(props.to)
})
</script>

<template>
  <RouterLink
    :to="to"
    :class="[
      'flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors duration-150',
      isActive
        ? 'bg-brand-700 text-white'
        : 'text-brand-100 hover:bg-brand-800 hover:text-white',
    ]"
  >
    <span v-if="icon" class="text-base w-5 text-center">{{ icon }}</span>
    <span>{{ label }}</span>
  </RouterLink>
</template>
