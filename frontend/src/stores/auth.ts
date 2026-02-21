import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { apiPost, apiGet } from '@/api/client'
import type { User, ApiResponse, LoginResponse } from '@/types'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const accessToken = ref<string | null>(localStorage.getItem('access_token'))
  const refreshToken = ref<string | null>(localStorage.getItem('refresh_token'))
  const loading = ref(false)

  const isAuthenticated = computed(() => !!accessToken.value)
  const isAdmin = computed(() => user.value?.role === 'admin')

  function setTokens(access: string, refresh: string) {
    accessToken.value = access
    refreshToken.value = refresh
    localStorage.setItem('access_token', access)
    localStorage.setItem('refresh_token', refresh)
  }

  function clearTokens() {
    accessToken.value = null
    refreshToken.value = null
    user.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  }

  async function login(email: string, password: string) {
    loading.value = true
    try {
      const response = await apiPost<ApiResponse<LoginResponse>>('/auth/login', { email, password })
      const { access_token, refresh_token, user: userData } = response.data
      setTokens(access_token, refresh_token)
      user.value = userData
    } finally {
      loading.value = false
    }
  }

  async function logout() {
    loading.value = true
    try {
      if (refreshToken.value) {
        await apiPost('/auth/logout', { refresh_token: refreshToken.value })
      }
    } catch {
      // Ignore logout errors
    } finally {
      clearTokens()
      loading.value = false
    }
  }

  async function refreshAuth() {
    const storedRefresh = refreshToken.value || localStorage.getItem('refresh_token')
    if (!storedRefresh) {
      clearTokens()
      return false
    }
    try {
      const response = await apiPost<ApiResponse<LoginResponse>>('/auth/refresh', {
        refresh_token: storedRefresh,
      })
      const { access_token, refresh_token } = response.data
      setTokens(access_token, refresh_token)
      return true
    } catch {
      clearTokens()
      return false
    }
  }

  async function fetchMe() {
    if (!accessToken.value) return
    try {
      const response = await apiGet<ApiResponse<User>>('/auth/me')
      user.value = response.data
    } catch {
      // If fetching user fails, don't clear tokens - let the interceptor handle it
    }
  }

  return {
    user,
    accessToken,
    refreshToken,
    loading,
    isAuthenticated,
    isAdmin,
    login,
    logout,
    refreshAuth,
    fetchMe,
  }
})
