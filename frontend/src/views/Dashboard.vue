<template>
  <div class="dashboard">
    <!-- Fixed Top Navbar -->
    <div class="top-navbar">
      <div class="logo-area">
        <div class="logo-placeholder">
          <img 
            src="/DataStudio-logo.jpeg" 
            alt="DataStudio Logo" 
            class="navbar-logo"
            @error="e => e.target.style.display = 'none'"
          />
        </div>
      </div>
      <div class="nav-actions">
        <button class="nav-icon-btn" @click="goToSettings">
          <v-icon>mdi-cog</v-icon>
        </button>
        <button class="nav-icon-btn" @click="handleLogout">
          <v-icon>mdi-logout</v-icon>
        </button>
      </div>
    </div>

    <!-- Dashboard Title -->
    <div class="dashboard-title">
      <h1>Dashboard</h1>
    </div>

    <!-- Session Management - Side by Side Layout -->
    <div class="session-management-row">
      <!-- Recent Sessions Card -->
      <div class="recent-sessions-card">
        <v-card class="session-card">
          <v-card-title class="card-title">
            <div class="title-left">
              <v-icon>mdi-history</v-icon>
              Recent Sessions
            </div>
            <div class="title-right">
              <span class="session-count">{{ sessions.length }} Total</span>
            </div>
          </v-card-title>
          <v-card-text>
            <!-- Search Bar -->
            <div class="search-bar">
              <v-icon class="search-icon" size="16">mdi-magnify</v-icon>
              <input 
                type="text" 
                v-model="searchQuery" 
                placeholder="Search sessions..." 
                class="search-input"
              />
              <button v-if="searchQuery" class="clear-search" @click="searchQuery = ''">
                <v-icon size="14">mdi-close</v-icon>
              </button>
            </div>

            <div class="sessions-list-container">
              <div class="sessions-list">
                <div v-if="filteredSessions.length === 0" class="empty-sessions-list">
                  <v-icon size="36" color="#ccc">mdi-folder-open</v-icon>
                  <p>No sessions yet</p>
                  <p class="empty-hint">Create a session using the form on the right</p>
                </div>
                <div 
                  v-for="session in filteredSessions" 
                  :key="session.id" 
                  class="session-row-item"
                  @click="loadExistingSession(session.id)"
                >
                  <div class="session-row-icon" :style="{ background: '#0B2044' }">
                    <v-icon size="14" color="white">mdi-folder</v-icon>
                  </div>
                  <div class="session-row-info">
                    <div class="session-row-name">{{ session.name }}</div>
                    <div class="session-row-meta">{{ session.date }}</div>
                  </div>
                  <div class="session-row-stats">
                    <span>{{ session.instrumentCount || 0 }} instruments</span>
                    <span class="session-row-value">${{ (session.totalValue || 0).toLocaleString() }}</span>
                  </div>
                  <div class="session-row-status" :class="session.status">
                    {{ session.status === 'completed' ? '✓' : '⟳' }}
                  </div>
                  <button class="row-rename-btn" @click.stop="openRename(session)" title="Rename">
                    <v-icon size="12">mdi-pencil</v-icon>
                  </button>
                  <button class="row-delete-btn" @click.stop="deleteSession(session.id)">
                    <v-icon size="12">mdi-close</v-icon>
                  </button>
                </div>
              </div>
            </div>
          </v-card-text>
        </v-card>
      </div>

      <!-- Create New Session Card -->
      <div class="create-session-card">
        <v-card class="session-card">
          <v-card-title class="card-title">
            <v-icon>mdi-folder-plus</v-icon>
            Create New Session
          </v-card-title>
          <v-card-text class="create-session-content">
            <div class="create-session-input">
              <input 
                v-model="newSessionName" 
                placeholder="Enter session name " 
                class="session-input"
                @keyup.enter="createNewSession"
              />
            </div>
            <div class="create-session-action">
              <button class="btn-primary full-width" @click="createNewSession" :disabled="!newSessionName.trim()">
                <v-icon>mdi-plus</v-icon> Create Session
              </button>
            </div>
            
            <div class="active-session-container">
              <div v-if="activeSession" class="active-session-info">
                <div class="session-header">
                  <v-icon color="#4CAF50" size="16">mdi-check-circle</v-icon>
                  <span v-if="!renamingActive" class="session-name-display">Active: {{ activeSession.name }}</span>
                  <input v-else v-model="renameInput" class="session-rename-input" @keyup.enter="saveRename" @keyup.esc="renamingActive = false" />
                  <button v-if="!renamingActive" class="btn-rename-sm" type="button" @click="startRenameActive">Rename</button>
                  <button v-else class="btn-rename-sm" type="button" @click="saveRename">Save</button>
                  <span class="session-status-badge" :class="activeSession.status">
                    {{ activeSession.status === 'completed' ? 'Completed' : 'In Progress' }}
                  </span>
                </div>
                <div class="session-details">
                  <span>Created: {{ activeSession.date }}</span>
                  <span>Instruments: {{ activeSession.instrumentCount || 0 }}/3</span>
                </div>
              </div>
              <div v-else class="no-session-warning">
                <v-icon color="warning" size="16">mdi-alert</v-icon>
                <span>No active session selected</span>
              </div>
            </div>

            <div class="flex-spacer"></div>

            <div class="session-stats-summary">
              <div class="stats-header">
                <v-icon size="16">mdi-chart-box</v-icon>
                <span>Session Summary</span>
              </div>
              <div class="stats-grid">
                <div class="stat-item">
                  <div class="stat-number">{{ totalSessions }}</div>
                  <div class="stat-label">Total Sessions</div>
                </div>
                <div class="stat-item">
                  <div class="stat-number">{{ completedSessions }}</div>
                  <div class="stat-label">Completed</div>
                </div>
                <div class="stat-item">
                  <div class="stat-number">{{ inProgressSessions }}</div>
                  <div class="stat-label">In Progress</div>
                </div>
              </div>
            </div>
          </v-card-text>
        </v-card>
      </div>
    </div>

    <!-- KPI Cards -->
    <div class="kpis-row">
      <div v-for="stat in kpiStats" :key="stat.title" class="kpi-card">
        <div class="kpi-top-bar"></div>
        <div class="kpi-icon" :style="{ background: stat.gradient }">
          <v-icon size="28" color="white">{{ stat.icon }}</v-icon>
        </div>
        <div class="kpi-info">
          <div class="kpi-value">{{ stat.value }}</div>
          <div class="kpi-title">{{ stat.title }}</div>
        </div>
      </div>
    </div>

    <!-- Instruments -->
    <div class="section-header">
      <v-icon color="#0B2044" size="20">mdi-filter-outline</v-icon>
      <h2>Select Financial Instrument</h2>
    </div>

    <div class="instruments-row">
      <div 
        v-for="instrument in instruments" 
        :key="instrument.id"
        class="instrument-card"
        :class="{ 'disabled-card': !activeSession }"
        @click="activeSession && goToInstrument(instrument.id)"
      >
        <div class="instrument-icon" :style="{ background: instrument.gradient }">
          <v-icon size="28" color="white">{{ instrument.icon }}</v-icon>
        </div>
        <div class="instrument-info">
          <h3>{{ instrument.name }}</h3>
          <p>{{ instrument.description }}</p>
        </div>
        <div v-if="!activeSession" class="lock-overlay">
          <v-icon>mdi-lock</v-icon>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import sessionManager from '@/services/sessionManager.js'
import { useRouter } from 'vue-router'

const router = useRouter()

const SESSIONS_STORAGE_KEY = 'dura_sessions'
const ACTIVE_SESSION_ID_KEY = 'dura_active_session_id'

const sessions = ref([])
const searchQuery = ref('')
const newSessionName = ref('')
const activeSession = ref(null)
const renamingActive = ref(false)
const renameInput = ref('')

const instruments = [
  { id: 'money-market', name: 'Money Market', description: 'Short-term debt instruments', icon: 'mdi-chart-line', gradient: 'linear-gradient(135deg, #1E88E5, #0B2044)' },
  { id: 'bonds', name: 'Bonds', description: 'Fixed income securities', icon: 'mdi-chart-timeline', gradient: 'linear-gradient(135deg, #4CAF50, #2E7D32)' },
  { id: 'tbills', name: 'T-Bills', description: 'Treasury bills', icon: 'mdi-finance', gradient: 'linear-gradient(135deg, #FFC107, #FF9800)' }
]

const filteredSessions = computed(() => {
  if (!searchQuery.value) return sessions.value
  const query = searchQuery.value.toLowerCase()
  return sessions.value.filter(session => 
    session.name.toLowerCase().includes(query)
  )
})

const totalSessions = computed(() => sessions.value.length)
const completedSessions = computed(() => sessions.value.filter(s => s.status === 'completed').length)
const inProgressSessions = computed(() => sessions.value.filter(s => s.status === 'in-progress').length)

const kpiStats = computed(() => [
  { title: 'Active Session', value: activeSession.value?.name || 'No Session', icon: 'mdi-folder', gradient: 'linear-gradient(135deg, #0B2044, #1a3a6e)' },
  { title: 'Instruments Used', value: activeSession.value?.instrumentCount || '0', icon: 'mdi-chart-line', gradient: 'linear-gradient(135deg, #1E88E5, #0B2044)' },
  { title: 'Completion', value: `${Math.round((activeSession.value?.instrumentCount || 0) / 3 * 100)}%`, icon: 'mdi-database', gradient: 'linear-gradient(135deg, #4CAF50, #2E7D32)' }
])

// ========== PERSISTENCE HELPERS ==========
function saveSessionsToLocalStorage() {
  localStorage.setItem(SESSIONS_STORAGE_KEY, JSON.stringify(sessions.value))
}

function loadSessionsFromLocalStorage() {
  const stored = localStorage.getItem(SESSIONS_STORAGE_KEY)
  if (stored) {
    try {
      sessions.value = JSON.parse(stored)
    } catch(e) { console.error('Failed to parse sessions', e) }
  } else {
    sessions.value = []
  }
}

function saveActiveSessionId(id) {
  if (id) {
    localStorage.setItem(ACTIVE_SESSION_ID_KEY, id)
  } else {
    localStorage.removeItem(ACTIVE_SESSION_ID_KEY)
  }
}

function loadActiveSessionId() {
  return localStorage.getItem(ACTIVE_SESSION_ID_KEY)
}

// Sync a single session (after updates from instrument pages) – can be called from elsewhere
function syncSessionFromManager(sessionId) {
  const managerSession = sessionManager.getSession(sessionId)
  if (managerSession) {
    const index = sessions.value.findIndex(s => s.id === sessionId)
    if (index !== -1) {
      sessions.value[index] = { ...managerSession }
      saveSessionsToLocalStorage()
      if (activeSession.value && activeSession.value.id === sessionId) {
        activeSession.value = sessions.value[index]
      }
    }
  }
}

// ========== SESSION ACTIONS ==========
function createNewSession() {
  if (!newSessionName.value.trim()) return
  const created = sessionManager.createSession(newSessionName.value.trim())
  // Ensure the created session has the required fields
  const newSession = {
    id: created.id,
    name: created.name,
    date: created.date || new Date().toLocaleString(),
    status: created.status || 'in-progress',
    instrumentCount: created.instrumentCount || 0,
    totalValue: created.totalValue || 0
  }
  sessions.value.unshift(newSession)
  saveSessionsToLocalStorage()
  activeSession.value = newSession
  sessionManager.setActiveSession(activeSession.value)
  saveActiveSessionId(activeSession.value.id)
  newSessionName.value = ''
}

function loadExistingSession(sessionId) {
  // First try to get from our local array
  let session = sessions.value.find(s => s.id === sessionId)
  if (!session) {
    // Try to load from sessionManager
    const full = sessionManager.getSession(sessionId)
    if (full) session = full
  }
  if (!session) return
  
  // Load full data from sessionManager (workflows, etc.)
  sessionManager.loadSessionFromDb(sessionId).then(() => {
    // Refresh session from manager after load
    const refreshed = sessionManager.getSession(sessionId)
    if (refreshed) {
      const index = sessions.value.findIndex(s => s.id === sessionId)
      if (index !== -1) {
        sessions.value[index] = { ...refreshed }
        saveSessionsToLocalStorage()
        session = sessions.value[index]
      }
    }
    activeSession.value = session
    sessionManager.setActiveSession(activeSession.value)
    saveActiveSessionId(activeSession.value.id)
  }).catch(() => {
    // Even if load fails, still set active session with basic info
    activeSession.value = session
    sessionManager.setActiveSession(activeSession.value)
    saveActiveSessionId(activeSession.value.id)
  })
}

function openRename(session) {
  const name = prompt('Rename session:', session.name)
  if (name && name.trim()) {
    sessionManager.renameSession(session.id, name.trim())
    // Update local session array
    const index = sessions.value.findIndex(s => s.id === session.id)
    if (index !== -1) {
      sessions.value[index].name = name.trim()
      saveSessionsToLocalStorage()
    }
    if (activeSession.value?.id === session.id) {
      activeSession.value = sessions.value[index]
    }
  }
}

function startRenameActive() {
  if (!activeSession.value) return
  renameInput.value = activeSession.value.name
  renamingActive.value = true
}

function saveRename() {
  if (!activeSession.value || !renameInput.value.trim()) return
  sessionManager.renameSession(activeSession.value.id, renameInput.value.trim())
  const index = sessions.value.findIndex(s => s.id === activeSession.value.id)
  if (index !== -1) {
    sessions.value[index].name = renameInput.value.trim()
    saveSessionsToLocalStorage()
    activeSession.value = sessions.value[index]
  }
  renamingActive.value = false
}

function deleteSession(sessionId) {
  if (confirm('Are you sure you want to delete this session? This action cannot be undone.')) {
    sessionManager.deleteSession(sessionId)
    sessions.value = sessions.value.filter(s => s.id !== sessionId)
    saveSessionsToLocalStorage()
    if (activeSession.value && activeSession.value.id === sessionId) {
      activeSession.value = null
      saveActiveSessionId(null)
    }
  }
}

function goToInstrument(instrumentId) {
  if (!activeSession.value) {
    alert('Please create or select a session first')
    return
  }
  sessionManager.setActiveSession(activeSession.value)
  router.push({ path: `/instrument/${instrumentId}`, query: { session: activeSession.value.id } })
}

function goToSettings() {
  router.push('/settings')
}

function handleLogout() {
  localStorage.removeItem('auth_token')
  localStorage.removeItem('user')
  sessionStorage.clear()
  window.location.href = '/login'
}

// Initialize sessions on mount
onMounted(async () => {
  loadSessionsFromLocalStorage()
  
  // Also try to load from sessionManager in case there are newer sessions there (e.g., from other tabs)
  const managerSessions = sessionManager.getAllSessions()
  if (managerSessions.length > 0) {
    // Merge: manager sessions may have more up-to-date data (like instrument counts)
    const merged = [...sessions.value]
    for (const ms of managerSessions) {
      const existingIndex = merged.findIndex(s => s.id === ms.id)
      if (existingIndex !== -1) {
        merged[existingIndex] = { ...merged[existingIndex], ...ms }
      } else {
        merged.push(ms)
      }
    }
    sessions.value = merged
    saveSessionsToLocalStorage()
  }
  
  const activeId = loadActiveSessionId()
  if (activeId) {
    const session = sessions.value.find(s => s.id === activeId)
    if (session) {
      activeSession.value = session
      sessionManager.setActiveSession(activeSession.value)
      // Optionally load full data in background
      sessionManager.loadSessionFromDb(activeId).catch(() => {})
    } else {
      // Try to load from manager directly
      const managerSession = sessionManager.getSession(activeId)
      if (managerSession) {
        activeSession.value = managerSession
        sessionManager.setActiveSession(activeSession.value)
        sessions.value.unshift(managerSession)
        saveSessionsToLocalStorage()
      } else {
        saveActiveSessionId(null)
      }
    }
  } else if (sessions.value.length > 0 && !activeSession.value) {
    // Auto-select the most recent session
    activeSession.value = sessions.value[0]
    sessionManager.setActiveSession(activeSession.value)
    saveActiveSessionId(activeSession.value.id)
  }
})
</script>

<style scoped>
/* ========== ALL STYLES REMAIN EXACTLY AS IN YOUR ORIGINAL ========== */
.dashboard {
  min-height: 100vh;
  background: linear-gradient(135deg, #f5f7fa 0%, #e8ecf1 100%);
  padding: 20px 40px;
}

.top-navbar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 60px;
  background: white;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 30px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
  z-index: 1000;
}

.logo-placeholder {
  display: flex;
  align-items: center;
}

.navbar-logo {
  width: 180px;
  max-height: 48px;
  height: auto;
  object-fit: contain;
  border-radius: 8px;
}

.nav-actions {
  display: flex;
  gap: 15px;
  align-items: center;
}

.nav-icon-btn {
  background: transparent;
  border: none;
  cursor: pointer;
  padding: 8px;
  border-radius: 8px;
  transition: all 0.2s;
  color: #666;
  display: flex;
  align-items: center;
  justify-content: center;
}

.nav-icon-btn:hover {
  background: #f0f0f0;
  color: #0B2044;
}

.dashboard-title {
  margin-top: 80px;
  margin-bottom: 25px;
}

.dashboard-title h1 {
  color: #0B2044;
  font-size: 28px;
  font-weight: 700;
}

.session-management-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
  margin-bottom: 30px;
}

.recent-sessions-card,
.create-session-card {
  width: 100%;
}

.session-card {
  border-radius: 16px;
  background: white;
  overflow: hidden;
  position: relative;
  height: 100%;
  min-height: 440px;
  display: flex;
  flex-direction: column;
}

.session-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(90deg, #0B2044, #1E88E5);
}

.card-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 18px 0 18px;
}

.title-left {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #0B2044;
  font-size: 15px;
  font-weight: 600;
}

.title-right {
  display: flex;
  align-items: center;
}

.session-count {
  background: #e8ecf1;
  padding: 2px 8px;
  border-radius: 20px;
  font-size: 11px;
  color: #0B2044;
}

.search-bar {
  display: flex;
  align-items: center;
  background: #f5f5f5;
  border-radius: 8px;
  padding: 5px 10px;
  margin: 10px 16px;
  border: 1px solid #e0e0e0;
  transition: all 0.2s;
}

.search-bar:focus-within {
  border-color: #0B2044;
  background: white;
}

.search-icon {
  color: #999;
  margin-right: 6px;
}

.search-input {
  flex: 1;
  border: none;
  background: transparent;
  outline: none;
  font-size: 12px;
}

.clear-search {
  background: none;
  border: none;
  cursor: pointer;
  color: #999;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2px;
}

.clear-search:hover {
  color: #f44336;
}

.sessions-list-container {
  margin: 0 12px;
}

.sessions-list {
  max-height: 280px;
  overflow-y: auto;
  padding: 0 8px 8px 0;
}

.sessions-list::-webkit-scrollbar {
  width: 4px;
}

.sessions-list::-webkit-scrollbar-track {
  background: #f0f0f0;
  border-radius: 4px;
}

.sessions-list::-webkit-scrollbar-thumb {
  background: #0B2044;
  border-radius: 4px;
}

.session-row-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  margin-bottom: 3px;
  background: #f8f9ff;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  position: relative;
  border: 1px solid transparent;
}

.session-row-item:hover {
  background: white;
  border-color: #e0e0e0;
  transform: translateX(3px);
}

.session-row-icon {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.session-row-info {
  flex: 2;
  min-width: 90px;
}

.session-row-name {
  font-weight: 600;
  color: #0B2044;
  font-size: 12px;
  margin-bottom: 1px;
}

.session-row-meta {
  font-size: 9px;
  color: #999;
}

.session-row-stats {
  flex: 2;
  display: flex;
  gap: 6px;
  font-size: 9px;
  color: #666;
}

.session-row-value {
  font-weight: 600;
  color: #4CAF50;
}

.session-row-status {
  width: 24px;
  text-align: center;
  padding: 2px 0;
  border-radius: 10px;
  font-size: 9px;
  font-weight: 600;
}

.session-row-status.in-progress {
  background: #FFF3E0;
  color: #FF9800;
}

.session-row-status.completed {
  background: #E8F5E9;
  color: #4CAF50;
}

.row-rename-btn {
  background: #0B2044;
  border: none;
  color: white;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  opacity: 0;
  margin-right: 4px;
}
.session-row-item:hover .row-rename-btn { opacity: 1; }
.session-rename-input {
  flex: 1;
  min-width: 120px;
  padding: 4px 8px;
  border: 1px solid #0B2044;
  border-radius: 6px;
  font-size: 13px;
}
.btn-rename-sm {
  background: #0B2044;
  color: white;
  border: none;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
  cursor: pointer;
  margin-left: 8px;
}

.row-delete-btn {
  background: #f44336;
  border: none;
  color: white;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
  opacity: 0;
  flex-shrink: 0;
}

.session-row-item:hover .row-delete-btn {
  opacity: 1;
}

.row-delete-btn:hover {
  background: #d32f2f;
  transform: scale(1.1);
}

.empty-sessions-list {
  text-align: center;
  padding: 40px 20px;
  color: #999;
}

.empty-sessions-list p {
  margin-top: 6px;
  font-size: 12px;
}

.empty-hint {
  font-size: 10px;
  color: #bbb;
  margin-top: 4px;
}

.create-session-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  height: 100%;
}

.create-session-input {
  padding: 14px 16px 6px 16px;
}

.session-input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  font-size: 12px;
  transition: all 0.2s;
}

.session-input:focus {
  outline: none;
  border-color: #0B2044;
  box-shadow: 0 0 0 2px rgba(11, 32, 68, 0.1);
}

.create-session-action {
  padding: 0 16px 12px 16px;
}

.full-width {
  width: 100%;
}

.active-session-container {
  margin: 0 16px;
}

.active-session-info {
  padding: 8px 10px;
  background: #e8f5e9;
  border-radius: 8px;
  margin-bottom: 12px;
}

.session-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 3px;
  flex-wrap: wrap;
}

.session-name-display {
  font-weight: 600;
  color: #0B2044;
  font-size: 11px;
}

.session-status-badge {
  padding: 1px 6px;
  border-radius: 10px;
  font-size: 8px;
}

.session-status-badge.in-progress {
  background: #FFF3E0;
  color: #FF9800;
}

.session-status-badge.completed {
  background: #E8F5E9;
  color: #4CAF50;
}

.session-details {
  display: flex;
  gap: 10px;
  font-size: 9px;
  color: #555;
}

.no-session-warning {
  padding: 10px 10px;
  background: #FFF3E0;
  border-radius: 8px;
  display: flex;
  align-items: center;
  gap: 6px;
  color: #E65100;
  font-size: 10px;
  margin-bottom: 12px;
}

.flex-spacer {
  flex: 1;
  min-height: 10px;
}

.session-stats-summary {
  background: #f8f9ff;
  margin: 0 16px 16px 16px;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid rgba(11, 32, 68, 0.08);
}

.stats-header {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  color: #0B2044;
  font-size: 11px;
  margin-bottom: 8px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.stat-item {
  text-align: center;
}

.stat-number {
  font-size: 20px;
  font-weight: 700;
  color: #0B2044;
}

.stat-label {
  font-size: 9px;
  color: #888;
  margin-top: 2px;
}

.kpis-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
  margin-bottom: 40px;
}

.kpi-card {
  background: white;
  border-radius: 20px;
  padding: 18px;
  display: flex;
  align-items: center;
  gap: 12px;
  position: relative;
  overflow: hidden;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
  transition: all 0.3s ease;
}

.kpi-top-bar {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(90deg, #0B2044, #1E88E5, #4CAF50);
  transform: scaleX(1);
}

.kpi-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 12px 28px rgba(0, 0, 0, 0.15);
}

.kpi-icon {
  width: 52px;
  height: 52px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: transform 0.3s ease;
}

.kpi-card:hover .kpi-icon {
  transform: scale(1.05);
}

.kpi-info {
  flex: 1;
}

.kpi-value {
  font-size: 20px;
  font-weight: 800;
  color: #0B2044;
}

.kpi-title {
  font-size: 10px;
  color: #888;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 20px;
}

.section-header h2 {
  color: #0B2044;
  font-size: 18px;
  margin: 0;
}

.instruments-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
  margin-bottom: 40px;
}

.instrument-card {
  background: white;
  border-radius: 20px;
  padding: 18px;
  display: flex;
  gap: 14px;
  cursor: pointer;
  position: relative;
  transition: all 0.3s;
}

.instrument-card.disabled-card {
  opacity: 0.6;
  cursor: not-allowed;
}

.instrument-card:not(.disabled-card):hover {
  transform: translateY(-5px);
  box-shadow: 0 12px 28px rgba(0,0,0,0.15);
}

.instrument-icon {
  width: 52px;
  height: 52px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.instrument-info {
  flex: 1;
}

.instrument-info h3 {
  color: #0B2044;
  font-size: 15px;
  margin-bottom: 4px;
}

.instrument-info p {
  color: #888;
  font-size: 11px;
}

.lock-overlay {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background: rgba(0,0,0,0.6);
  border-radius: 50%;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.btn-primary {
  background: linear-gradient(135deg, #0B2044, #1E88E5);
  color: white;
  border: none;
  padding: 8px 14px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  transition: all 0.3s;
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 15px rgba(11, 32, 68, 0.3);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

@media (max-width: 900px) {
  .dashboard { padding: 20px; }
  .session-management-row {
    grid-template-columns: 1fr;
    gap: 20px;
  }
  .kpis-row, .instruments-row {
    grid-template-columns: 1fr;
  }
  .session-row-stats {
    display: none;
  }
  .row-delete-btn {
    opacity: 1;
  }
}
</style>