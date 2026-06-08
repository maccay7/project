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

        <!-- Instrument Tools - ALWAYS VISIBLE (green ticks removed) -->
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
            <!-- ✓ REMOVED GREEN TICK BADGE -->
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

// Check if on an instrument page
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

// Save last instrument when on instrument page
watch(() => route.path, (newPath) => {
  if (newPath.includes('/instrument/')) {
    localStorage.setItem('last_instrument', newPath)
  }
})
</script>

<style scoped>
/* ===== YOUR EXACT ORIGINAL STYLES – NO CHANGES ===== */
.fixed-layout {
  display: flex;
  min-height: 100vh;
}

/* Sidebar - Below top navbar */
.sidebar {
  width: 260px;
  background: linear-gradient(180deg, #0B2044 0%, #0e2a54 100%);
  color: white;
  position: fixed;
  height: calc(100vh - 60px);
  top: 60px;
  left: 0;
  overflow-y: auto;
  box-shadow: 2px 0 20px rgba(0, 0, 0, 0.08);
  z-index: 999;
  display: flex;
  flex-direction: column;
}

.nav-menu {
  flex: 1;
  padding: 16px 12px;
}

.nav-group {
  margin-bottom: 24px;
}

.nav-group-title {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 1px;
  color: rgba(255, 255, 255, 0.4);
  padding: 8px 12px;
  margin-bottom: 4px;
  text-transform: uppercase;
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
  color: rgba(255, 255, 255, 0.75);
  font-size: 14px;
  font-weight: 500;
  position: relative;
}

.nav-link:hover {
  background: rgba(255, 255, 255, 0.08);
  color: white;
  transform: translateX(4px);
}

.nav-link.active {
  background: linear-gradient(135deg, #1E88E5, #0B2044);
  color: white;
  box-shadow: 0 2px 8px rgba(30, 136, 229, 0.3);
}

.nav-icon {
  font-size: 20px;
  width: 24px;
  text-align: center;
}

.nav-label {
  flex: 1;
}

.sidebar::-webkit-scrollbar {
  width: 4px;
}

.sidebar::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.05);
}

.sidebar::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.2);
  border-radius: 4px;
}

.main-content {
  margin-left: 260px;
  flex: 1;
  background: #f5f7fa;
  min-height: 100vh;
  width: calc(100% - 260px);
  padding-top: 60px;
}

@media (max-width: 768px) {
  .sidebar {
    width: 80px;
    top: 60px;
    height: calc(100vh - 60px);
  }
  .nav-label, .nav-group-title {
    display: none;
  }
  .nav-link {
    justify-content: center;
    padding: 12px;
  }
  .nav-icon {
    margin: 0;
  }
  .main-content {
    margin-left: 80px;
    width: calc(100% - 80px);
  }
}
</style>