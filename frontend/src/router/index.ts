import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { requiresAuth: false },
    },
    {
      path: '/',
      redirect: '/dashboard',
    },
    {
      path: '/dashboard',
      name: 'dashboard',
      component: () => import('@/views/DashboardView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/services',
      name: 'services',
      component: () => import('@/views/ServicesView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/services/:id',
      name: 'service-detail',
      component: () => import('@/views/ServiceDetailView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/components',
      name: 'components',
      component: () => import('@/views/ComponentsView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/products',
      name: 'products',
      component: () => import('@/views/ProductsView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/teams',
      name: 'teams',
      component: () => import('@/views/TeamsView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/people',
      name: 'people',
      component: () => import('@/views/PeopleView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/repositories',
      name: 'repositories',
      component: () => import('@/views/RepositoriesView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/resources',
      name: 'resources',
      component: () => import('@/views/ResourcesView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/incidents',
      name: 'incidents',
      component: () => import('@/views/IncidentsView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/scorecards',
      name: 'scorecards',
      component: () => import('@/views/ScorecardsView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/users',
      name: 'users',
      component: () => import('@/views/UsersView.vue'),
      meta: { requiresAuth: true, requiresAdmin: true },
    },
  ],
})

router.beforeEach(async (to, _from, next) => {
  const authStore = useAuthStore()

  const requiresAuth = to.meta.requiresAuth !== false

  if (requiresAuth && !authStore.isAuthenticated) {
    next({ name: 'login', query: { redirect: to.fullPath } })
    return
  }

  if (authStore.isAuthenticated && !authStore.user) {
    await authStore.fetchMe()
  }

  if (to.name === 'login' && authStore.isAuthenticated) {
    next({ name: 'dashboard' })
    return
  }

  next()
})

export default router
