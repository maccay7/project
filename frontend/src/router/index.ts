// router/index.ts – main app routes (instrument workflow + dashboard)

import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  { path: '/', redirect: '/login' },
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
    path: '/verify-code',
    name: 'verify-code',
    component: () => import('@/views/VerifyCodeView.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/reset-password',
    name: 'reset-password',
    component: () => import('@/views/ResetPasswordView.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/dashboard',
    name: 'dashboard',
    component: () => import('@/views/Dashboard.vue'),
    meta: { requiresAuth: true }
  },
  {
    // Money Market, Bonds, T-Bills – unified workflow page
    path: '/instrument/:type',
    name: 'instrument',
    component: () => import('@/views/InstrumentView.vue'),
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
    path: '/summary',
    name: 'summary',
    component: () => import('@/views/Summary.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/settings',
    name: 'settings',
    component: () => import('@/views/SettingsView.vue'),
    meta: { requiresAuth: true }
  }
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes
})

router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()
  
  // For routes requiring authentication
  if (to.meta.requiresAuth) {
    if (!authStore.isAuthenticated) {
      next('/login')
      return
    }
    
    // Validate session with backend for protected routes
    const isValid = await authStore.checkSession()
    if (!isValid) {
      authStore.logout()
      next('/login')
      return
    }
  }
  
  // Redirect authenticated users away from login/signup
  if ((to.path === '/login' || to.path === '/signup') && authStore.isAuthenticated) {
    next('/dashboard')
    return
  }
  
  next()
})

export default router
