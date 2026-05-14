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
          <div class="nav-link" @click="openReportDialog">
            <v-icon class="nav-icon">mdi-file-pdf</v-icon>
            <span class="nav-label">Generate Report</span>
          </div>
        </div>

        <div v-if="isOnInstrumentPage" class="nav-group">
          <div class="nav-group-title">INSTRUMENT TOOLS</div>
          <div 
            v-for="item in instrumentNav" 
            :key="item.tab"
            class="nav-link"
            :class="{ active: currentTab === item.tab }"
            @click="changeInstrumentTab(item.tab)"
          >
            <v-icon class="nav-icon">{{ item.icon }}</v-icon>
            <span class="nav-label">{{ item.name }}</span>
            <span v-if="getTabStatus(item.tab)" class="check-badge">✓</span>
          </div>
        </div>
      </div>
    </aside>

    <main class="main-content">
      <slot />
    </main>

    <!-- Report Dialog -->
    <v-dialog v-model="showReportDialog" max-width="500px">
      <v-card>
        <v-card-title>Generate Report</v-card-title>
        <v-card-text>
          <div class="report-type-selector">
            <label>Select Report Type:</label>
            <select v-model="reportType" class="report-select">
              <option value="current">Current Instrument Report</option>
              <option value="session">Full Session Report</option>
            </select>
          </div>
        </v-card-text>
        <v-card-actions>
          <button class="btn-secondary" @click="showReportDialog = false">Cancel</button>
          <button class="btn-primary" @click="generateAndNavigate">Generate</button>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import TopNavbar from '@/components/TopNavbar.vue'

const router = useRouter()
const route = useRoute()

const showReportDialog = ref(false)
const reportType = ref('current')

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

const isOnInstrumentPage = computed(() => route.path.includes('/instrument/') || route.path.includes('/summary'))
const currentTab = computed(() => route.query.tab || 'upload')

function isActive(path) {
  return route.path === path
}

function navigateTo(path) {
  router.push(path)
}

function changeInstrumentTab(tab) {
  router.push({ path: route.path, query: { tab } })
}

function getTabStatus(tab) {
  const instrument = route.path.split('/').pop()
  const statuses = JSON.parse(localStorage.getItem(`instrument_${instrument}_status`) || '{}')
  return statuses[tab] || false
}

function openReportDialog() {
  showReportDialog.value = true
}

function generateAndNavigate() {
  const session = JSON.parse(localStorage.getItem('active_session') || '{}')
  localStorage.setItem('report_type', reportType.value)
  localStorage.setItem('report_session_id', session.id || '')
  showReportDialog.value = false
  router.push('/reports')
}
</script>

<style scoped>
.fixed-layout {
  display: flex;
  min-height: 100vh;
}

/* Sidebar */
.sidebar {
  width: 260px;
  background: linear-gradient(180deg, #0B2044 0%, #0e2a54 100%);
  color: white;
  position: fixed;
  height: calc(100vh - 65px);
  top: 65px;
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

.check-badge {
  background: #4CAF50;
  color: white;
  border-radius: 50%;
  width: 18px;
  height: 18px;
  font-size: 10px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
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
  padding-top: 65px;
}

/* Report Dialog */
.report-type-selector {
  padding: 10px 0;
}

.report-type-selector label {
  display: block;
  font-size: 14px;
  font-weight: 600;
  color: #0B2044;
  margin-bottom: 10px;
}

.report-select {
  width: 100%;
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 14px;
}

.btn-primary {
  background: linear-gradient(135deg, #0B2044, #1E88E5);
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 8px;
  cursor: pointer;
}

.btn-secondary {
  background: white;
  color: #0B2044;
  border: 1px solid #ddd;
  padding: 10px 20px;
  border-radius: 8px;
  cursor: pointer;
  margin-right: 10px;
}

@media (max-width: 768px) {
  .sidebar {
    width: 70px;
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
    margin-left: 70px;
    width: calc(100% - 70px);
  }
}
</style>