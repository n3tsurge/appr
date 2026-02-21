import axios, { type AxiosRequestConfig, type AxiosResponse } from 'axios'

const BASE_URL = '/api/v1'

const http = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor: attach Bearer token
http.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

let isRefreshing = false
let refreshSubscribers: Array<(token: string) => void> = []

function onRefreshed(token: string) {
  refreshSubscribers.forEach((cb) => cb(token))
  refreshSubscribers = []
}

function addRefreshSubscriber(cb: (token: string) => void) {
  refreshSubscribers.push(cb)
}

// Response interceptor: handle 401 and refresh token
http.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config as AxiosRequestConfig & { _retry?: boolean }

    if (error.response?.status === 401 && !originalRequest._retry) {
      const refreshToken = localStorage.getItem('refresh_token')

      if (!refreshToken) {
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        window.location.href = '/login'
        return Promise.reject(error)
      }

      if (isRefreshing) {
        return new Promise((resolve) => {
          addRefreshSubscriber((token: string) => {
            if (originalRequest.headers) {
              (originalRequest.headers as Record<string, string>)['Authorization'] = `Bearer ${token}`
            }
            resolve(http(originalRequest))
          })
        })
      }

      originalRequest._retry = true
      isRefreshing = true

      try {
        const response = await axios.post(`${BASE_URL}/auth/refresh`, {
          refresh_token: refreshToken,
        })

        const { access_token, refresh_token: newRefreshToken } = response.data.data
        localStorage.setItem('access_token', access_token)
        if (newRefreshToken) {
          localStorage.setItem('refresh_token', newRefreshToken)
        }

        http.defaults.headers.common['Authorization'] = `Bearer ${access_token}`
        onRefreshed(access_token)
        isRefreshing = false

        if (originalRequest.headers) {
          (originalRequest.headers as Record<string, string>)['Authorization'] = `Bearer ${access_token}`
        }
        return http(originalRequest)
      } catch {
        isRefreshing = false
        refreshSubscribers = []
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        window.location.href = '/login'
        return Promise.reject(error)
      }
    }

    return Promise.reject(error)
  }
)

export async function apiGet<T>(path: string, params?: Record<string, unknown>): Promise<T> {
  const response: AxiosResponse<T> = await http.get(path, { params })
  return response.data
}

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const response: AxiosResponse<T> = await http.post(path, body)
  return response.data
}

export async function apiPut<T>(path: string, body: unknown): Promise<T> {
  const response: AxiosResponse<T> = await http.put(path, body)
  return response.data
}

export async function apiDelete(path: string): Promise<void> {
  await http.delete(path)
}

export default http
