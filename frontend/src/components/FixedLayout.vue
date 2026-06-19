<template>
  <div class="fixed-layout">
    <!-- Top Navbar - Shows on ALL pages -->
    <TopNavbar />

    <!-- Sidebar -->
    <aside class="sidebar">
      <div class="nav-menu">
        <div class="nav-group">
          <div class="nav-group-title">MAIN</div>
          <div 
            v-for="item in mainNav" 
            :key="item.path"
            class="nav-link"
            :class="{ active: isActive(item.path) }"
            @click="navigateTo(item.path)"
          >
            <v-icon class="nav-icon">{{ item.icon }}</v-icon>
            <span class="nav-label">{{ item.name }}</span>
          </div>
        </div>

        <div class="nav-group">
          <div class="nav-group-title">REPORTS</div>
          <div class="nav-link" @click="goToReportsPage">
            <v-icon class="nav-icon">mdi-file-pdf</v-icon>
            <span class="nav-label">Generate Report</span>
          </div>
        </div>

        <!-- Instrument Tools - ALWAYS VISIBLE -->
        <div class="nav-group">
          <div class="nav-group-title">INSTRUMENT TOOLS</div>
          <div 
            v-for="item in instrumentNav" 
            :key="item.tab"
            class="nav-link"
            :class="{ active: currentTab === item.tab && isOnInstrumentPage }"
            @click="changeInstrumentTab(item.tab)"
          >
            <v-icon class="nav-icon">{{ item.icon }}</v-icon>
            <span class="nav-label">{{ item.name }}</span>
          </div>
        </div>
      </div>
    </aside>

    <main class="main-content">
      <slot />
    </main>
  </div>
</template>

<script setup>
import { computed, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import TopNavbar from '@/components/TopNavbar.vue'
import sessionManager from '@/services/sessionManager.js'

const router = useRouter()
const route = useRoute()

const mainNav = [
  { name: 'Dashboard', path: '/dashboard', icon: 'mdi-view-dashboard' },
  { name: 'Summary', path: '/summary', icon: 'mdi-file-document-outline' }
]

const instrumentNav = [
  { tab: 'upload', name: 'Upload Data', icon: 'mdi-upload' },
  { tab: 'cleaning', name: 'Clean Data', icon: 'mdi-broom' },
  { tab: 'calculations', name: 'Calculations', icon: 'mdi-calculator' },
  { tab: 'visualizations', name: 'Visualizations', icon: 'mdi-chart-line' },
  { tab: 'summary', name: 'Instrument Summary', icon: 'mdi-file-document' }
]

const isOnInstrumentPage = computed(() => route.path.includes('/instrument/'))
const currentTab = computed(() => route.query.tab || 'upload')

function isActive(path) {
  return route.path === path
}

function navigateTo(path) {
  router.push(path)
}

function goToReportsPage() {
  const sessionId = sessionManager.getActiveSessionId()
  if (!sessionId) {
    alert('No active session – please select a session from Dashboard')
    router.push('/dashboard')
    return
  }
  let instrument = 'money-market'
  if (isOnInstrumentPage.value) {
    const pathParts = route.path.split('/')
    instrument = pathParts[pathParts.length - 1]
  }
  router.push({ path: `/instrument/${instrument}`, query: { session: sessionId, tab: 'reports' } })
}

function changeInstrumentTab(tab) {
  if (isOnInstrumentPage.value) {
    router.push({ path: route.path, query: { ...route.query, tab } })
  } else {
    const lastInstrument = localStorage.getItem('last_instrument') || '/instrument/money-market'
    router.push({ path: lastInstrument, query: { tab } })
  }
}

watch(() => route.path, (newPath) => {
  if (newPath.includes('/instrument/')) {
    localStorage.setItem('last_instrument', newPath)
  }
})
</script>

<style scoped>
/* ===== LAYOUT FIX – SIDEBAR FIXED, MAIN SCROLLS ===== */
.fixed-layout {
  display: flex;
  height: 100vh;                 /* full viewport height */
  overflow: hidden;              /* no page scroll – only main content scrolls */
  width: 100%;
}

/* Sidebar – stays fixed, never moves */
.sidebar {
  background: linear-gradient(180deg, #0a1a33 0%, #0B2044 50%, #0e2a54 100%);
  color: white;
  position: sticky;              /* keep it in place while main scrolls */
  top: 60px;                     /* below the navbar */
  height: calc(100vh - 60px);    /* full remaining height */
  flex: 0 0 auto;                /* width from content */
  padding: 20px 12px 16px;
  box-shadow: 4px 0 20px rgba(0, 0, 0, 0.25), inset -1px 0 0 rgba(255, 255, 255, 0.05), inset 0 1px 0 rgba(255, 255, 255, 0.08);
  border-right: 1px solid rgba(255, 255, 255, 0.04);
  z-index: 999;
  display: flex;
  flex-direction: column;
  overflow-y: auto;              /* sidebar scrolls if content overflows */
}

/* Inner glow for 3D depth */
.sidebar::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, transparent, rgba(79, 195, 247, 0.3), transparent);
  pointer-events: none;
}

.nav-menu {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.nav-group {
  margin-bottom: 24px;
}

.nav-group-title {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 1.2px;
  color: rgba(255, 255, 255, 0.35);
  padding: 0 8px 8px;
  text-transform: uppercase;
  position: relative;
}

.nav-group-title::after {
  content: '';
  position: absolute;
  bottom: 4px;
  left: 8px;
  width: 20px;
  height: 2px;
  background: linear-gradient(90deg, rgba(30, 136, 229, 0.4), transparent);
  border-radius: 2px;
}

.nav-link {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  margin: 2px 0;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
  color: rgba(255, 255, 255, 0.7);
  font-size: 14px;
  font-weight: 500;
  position: relative;
}

.nav-link:hover {
  background: rgba(255, 255, 255, 0.08);
  color: white;
  transform: translateX(4px) translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

.nav-link.active {
  background: rgba(30, 136, 229, 0.2);
  color: white;
  box-shadow: inset 0 0 0 1px rgba(30, 136, 229, 0.2), 0 4px 12px rgba(0, 0, 0, 0.15);
  transform: translateX(2px);
}

.nav-link.active .nav-icon {
  color: #4FC3F7;
}

.nav-icon {
  font-size: 20px;
  width: 24px;
  text-align: center;
  color: rgba(255, 255, 255, 0.6);
  transition: color 0.2s;
}

.nav-link:hover .nav-icon {
  color: rgba(255, 255, 255, 0.9);
}

.nav-label {
  flex: 1;
  white-space: nowrap;
}

/* Scrollbar for sidebar */
.sidebar::-webkit-scrollbar {
  width: 4px;
}
.sidebar::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.03);
}
.sidebar::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.15);
  border-radius: 4px;
}

/* Main content – scrolls vertically, fills remaining space */
.main-content {
  flex: 1;
  background: #f5f7fa;
  padding-top: 60px;           /* space for fixed navbar */
  overflow-y: auto;            /* only this scrolls */
  height: 100vh;               /* full viewport height */
  max-width: 100%;             /* prevent horizontal overflow */
  overflow-x: hidden;          /* if any horizontal overflow, hide it (but we have scroll for tables) */
}

/* Responsive: on small screens, sidebar collapses to icon-only */
@media (max-width: 768px) {
  .sidebar {
    padding: 12px 8px;
    min-width: 60px;
  }
  .nav-label,
  .nav-group-title {
    display: none;
  }
  .nav-link {
    justify-content: center;
    padding: 12px 8px;
  }
  .nav-icon {
    width: auto;
    margin: 0;
  }
  .nav-link:hover {
    transform: translateX(0) translateY(-1px);
  }
}
</style>