// router/index.js

import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
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
    path: '/forgot-password',
    name: 'forgot-password',
    component: () => import('@/views/resetpassword.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/dashboard',
    name: 'dashboard',
    component: () => import('@/views/Dashboard.vue'),
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
  // REMOVED: /calculations route – calculations are handled inside InstrumentView.vue tab
  // {
  //   path: '/calculations',
  //   name: 'calculations',
  //   component: () => import('@/views/CalculationsView.vue'),
  //   meta: { requiresAuth: true }
  // },
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
  },
  {
    // SINGLE UNIFIED INSTRUMENT PAGE – handles all three instruments
    path: '/instrument/:type',
    name: 'instrument',
    component: () => import('@/views/InstrumentView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/summary',
    name: 'summary',
    component: () => import('@/views/Summary.vue'),
    meta: { requiresAuth: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// ─── Navigation Guard ────────────────────────────────
router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()
  
  // If route requires authentication and user is not logged in, redirect to login
  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next('/login')
  } 
  // If user is logged in and tries to go to login page, redirect to dashboard
  else if (to.path === '/login' && authStore.isAuthenticated) {
    next('/dashboard')
  } 
  // Otherwise, allow navigation
  else {
    next()
  }
})

export default router