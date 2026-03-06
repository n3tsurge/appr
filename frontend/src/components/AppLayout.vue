<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import AppNavLink from './AppNavLink.vue'

const router = useRouter()
const authStore = useAuthStore()
const userMenuOpen = ref(false)

const navItems = [
  { to: '/dashboard', label: 'Dashboard', icon: '⊞' },
  { to: '/services', label: 'Services', icon: '⚙' },
  { to: '/components', label: 'Components', icon: '◈' },
  { to: '/products', label: 'Products', icon: '◻' },
  { to: '/teams', label: 'Teams', icon: '◯' },
  { to: '/people', label: 'People', icon: '◎' },
  { to: '/repositories', label: 'Repositories', icon: '⊡' },
  { to: '/resources', label: 'Resources', icon: '◆' },
  { to: '/incidents', label: 'Incidents', icon: '⚠' },
  { to: '/scorecards', label: 'Scorecards', icon: '◈' },
]

async function handleLogout() {
  userMenuOpen.value = false
  await authStore.logout()
  router.push('/login')
}
</script>

<template>
  <div class="flex h-screen overflow-hidden bg-gray-50">
    <!-- Sidebar -->
    <aside class="flex flex-col w-60 flex-shrink-0 bg-brand-900 text-white">
      <!-- Logo/Brand -->
      <div class="flex items-center gap-2 px-4 py-5 border-b border-brand-800">
        <span class="text-2xl font-bold tracking-tight text-white">AppR</span>
        <span class="text-xs text-brand-300 mt-1">Inventory</span>
      </div>

      <!-- Navigation -->
      <nav class="flex-1 overflow-y-auto px-3 py-4 space-y-1">
        <AppNavLink
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          :label="item.label"
          :icon="item.icon"
        />

        <!-- Admin section -->
        <template v-if="authStore.isAdmin">
          <div class="pt-4 pb-1">
            <p class="px-3 text-xs font-semibold text-brand-400 uppercase tracking-wider">Admin</p>
          </div>
          <AppNavLink to="/users" label="Users" icon="◉" />
        </template>
      </nav>

      <!-- Sidebar footer -->
      <div class="px-3 py-3 border-t border-brand-800">
        <p class="text-xs text-brand-400 text-center">Enterprise Inventory</p>
      </div>
    </aside>

    <!-- Main area -->
    <div class="flex flex-col flex-1 overflow-hidden">
      <!-- Top header -->
      <header class="flex items-center justify-between px-6 py-4 bg-white border-b border-gray-200 shadow-sm flex-shrink-0">
        <div>
          <slot name="header-title">
            <h1 class="text-xl font-semibold text-gray-800">AppR</h1>
          </slot>
        </div>

        <!-- User menu -->
        <div class="relative">
          <button
            @click="userMenuOpen = !userMenuOpen"
            class="flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium text-gray-700 hover:bg-gray-100 transition-colors"
          >
            <div class="w-8 h-8 rounded-full bg-brand-600 flex items-center justify-center text-white text-xs font-semibold">
              {{ authStore.user?.display_name?.charAt(0)?.toUpperCase() || 'U' }}
            </div>
            <span class="hidden sm:inline max-w-32 truncate">{{ authStore.user?.display_name || authStore.user?.email || 'User' }}</span>
            <svg class="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
            </svg>
          </button>

          <!-- Dropdown -->
          <div
            v-if="userMenuOpen"
            class="absolute right-0 mt-1 w-56 bg-white rounded-lg shadow-lg border border-gray-200 z-50"
          >
            <div class="px-4 py-3 border-b border-gray-100">
              <p class="text-sm font-medium text-gray-900 truncate">{{ authStore.user?.display_name }}</p>
              <p class="text-xs text-gray-500 truncate">{{ authStore.user?.email }}</p>
              <span class="inline-flex mt-1 items-center px-2 py-0.5 rounded text-xs font-medium bg-brand-100 text-brand-700 capitalize">
                {{ authStore.user?.role || 'user' }}
              </span>
            </div>
            <div class="py-1">
              <button
                @click="handleLogout"
                class="flex w-full items-center gap-2 px-4 py-2 text-sm text-red-600 hover:bg-red-50 transition-colors"
              >
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                </svg>
                Sign out
              </button>
            </div>
          </div>

          <!-- Backdrop -->
          <div
            v-if="userMenuOpen"
            class="fixed inset-0 z-40"
            @click="userMenuOpen = false"
          />
        </div>
      </header>

      <!-- Page content -->
      <main class="flex-1 overflow-y-auto p-6">
        <slot />
      </main>
    </div>
  </div>
</template>
