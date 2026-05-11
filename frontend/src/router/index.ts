import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      redirect: '/login'
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { requiresAuth: false }
    },
    {
      path: '/signup',
      name: 'signup',
      component: () => import('@/views/SignupView.vue'),
      meta: { requiresAuth: false }
    },
    {
      path: '/dashboard',
      name: 'dashboard',
      component: () => import('@/views/DashboardView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/upload',
      name: 'upload',
      component: () => import('@/views/UploadView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/cleaning',
      name: 'cleaning',
      component: () => import('@/views/CleaningView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/calculations',
      name: 'calculations',
      component: () => import('@/views/CalculationsView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/visualizations',
      name: 'visualizations',
      component: () => import('@/views/VisualizationsView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/reports',
      name: 'reports',
      component: () => import('@/views/ReportsView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/settings',
      name: 'settings',
      component: () => import('@/views/SettingsView.vue'),
      meta: { requiresAuth: true }
    }
  ]
})

router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()
  
  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next('/login')
  } else if (to.path === '/login' && authStore.isAuthenticated) {
    next('/dashboard')
  } else {
    next()
  }
})

export default router
