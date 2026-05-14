<template>
  <div class="fixed-layout">
    <!-- Sidebar -->
    <aside class="sidebar">
      <div class="logo">
        <v-icon color="white" size="28">mdi-chart-line</v-icon>
        <h2>DuraCapital</h2>
      </div>
      
      <!-- Main Navigation -->
      <div class="nav-section">
        <div class="nav-title">MAIN</div>
        <div 
          v-for="item in mainNav" 
          :key="item.path"
          class="nav-item"
          :class="{ active: isActive(item.path) }"
          @click="navigateTo(item.path)"
        >
          <v-icon>{{ item.icon }}</v-icon>
          <span>{{ item.name }}</span>
        </div>
      </div>

      <!-- Report Section -->
      <div class="nav-section">
        <div class="nav-title">REPORTS</div>
        <div class="nav-item" @click="openReportDialog">
          <v-icon>mdi-file-pdf</v-icon>
          <span>Generate Report</span>
        </div>
      </div>

      <!-- Instrument Tools -->
      <div v-if="isOnInstrumentPage" class="nav-section">
        <div class="nav-title">INSTRUMENT TOOLS</div>
        <div 
          v-for="item in instrumentNav" 
          :key="item.tab"
          class="nav-item"
          :class="{ active: currentTab === item.tab }"
          @click="changeInstrumentTab(item.tab)"
        >
          <v-icon>{{ item.icon }}</v-icon>
          <span>{{ item.name }}</span>
          <span v-if="getTabStatus(item.tab)" class="status-badge">✓</span>
        </div>
      </div>

      <!-- Bottom Section -->
      <div class="nav-section bottom-nav">
        <div class="nav-item" @click="goToSettings">
          <v-icon>mdi-cog</v-icon>
          <span>Settings</span>
        </div>
        <div class="nav-item" @click="logout">
          <v-icon>mdi-logout</v-icon>
          <span>Logout</span>
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

const isOnInstrumentPage = computed(() => route.path.includes('/instrument/'))
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

function goToSettings() {
  router.push('/settings')
}

function logout() {
  localStorage.clear()
  router.push('/login')
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

.sidebar {
  width: 280px;
  background: linear-gradient(180deg, #0B2044 0%, #0a1a38 100%);
  color: white;
  position: fixed;
  height: 100vh;
  left: 0;
  top: 0;
  overflow-y: auto;
  box-shadow: 2px 0 20px rgba(0, 0, 0, 0.1);
  z-index: 1000;
  display: flex;
  flex-direction: column;
}

.logo {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 24px 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  margin-bottom: 20px;
}

.logo h2 {
  font-size: 1.3rem;
  font-weight: 600;
  margin: 0;
}

.nav-section {
  margin-bottom: 25px;
}

.nav-title {
  font-size: 11px;
  letter-spacing: 1px;
  color: rgba(255, 255, 255, 0.4);
  padding: 8px 20px;
  margin-top: 10px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 20px;
  margin: 4px 12px;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s;
  color: rgba(255, 255, 255, 0.7);
  position: relative;
}

.nav-item:hover {
  background: rgba(255, 255, 255, 0.1);
  color: white;
  transform: translateX(5px);
}

.nav-item.active {
  background: #1E88E5;
  color: white;
  box-shadow: 0 2px 8px rgba(30, 136, 229, 0.3);
}

.status-badge {
  position: absolute;
  right: 20px;
  background: #4CAF50;
  color: white;
  border-radius: 50%;
  width: 18px;
  height: 18px;
  font-size: 11px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.bottom-nav {
  margin-top: auto;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  padding-top: 10px;
}

.main-content {
  margin-left: 280px;
  flex: 1;
  background: #f5f7fa;
  min-height: 100vh;
}

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
  .sidebar { width: 80px; }
  .logo h2, .nav-item span, .nav-title { display: none; }
  .logo { justify-content: center; }
  .nav-item { justify-content: center; }
  .main-content { margin-left: 80px; }
}
</style>