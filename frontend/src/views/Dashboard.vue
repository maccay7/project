<template>
  <div class="dashboard">
    <!-- Fixed Top Navbar -->
    <div class="top-navbar">
      <div class="logo-area">
        <div class="logo-placeholder">
          <img 
            src="/DuraCapital logo.png" 
            alt="DuraCapital Logo" 
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

    <!-- Session Management Section -->
    <div class="session-section">
      <v-card class="session-card">
        <v-card-title class="card-title">
          <v-icon>mdi-folder</v-icon>
          Session Management
        </v-card-title>
        <v-card-text>
          <div class="session-controls">
            <div class="session-selector">
              <label>Select or Create Session</label>
              <div class="session-input-group">
                <select v-model="selectedSessionId" @change="loadSelectedSession" class="session-select">
                  <option value="">-- Create New Session --</option>
                  <option v-for="session in sessions" :key="session.id" :value="session.id">
                    {{ session.name }} ({{ session.date }}) - {{ session.status === 'completed' ? '✓ Complete' : '⟳ Progress' }}
                  </option>
                </select>
                <input 
                  v-if="selectedSessionId === ''" 
                  v-model="newSessionName" 
                  placeholder="Enter session name" 
                  class="session-input"
                />
              </div>
            </div>
            <div class="session-actions">
              <button class="btn-primary" @click="createOrLoadSession" :disabled="!canCreateSession">
                {{ selectedSessionId ? 'Load Session' : 'Create Session' }}
              </button>
              <button class="btn-secondary" @click="clearSessionSelection">Clear</button>
              <button v-if="selectedSessionId && activeSession" class="btn-danger" @click="deleteCurrentSession">
                Delete Session
              </button>
            </div>
          </div>
          
          <div v-if="activeSession" class="active-session-info">
            <div class="session-header">
              <v-icon color="#4CAF50">mdi-check-circle</v-icon>
              <span class="session-name-display">{{ activeSession.name }}</span>
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
            <v-icon color="warning">mdi-alert</v-icon>
            <span>Please create or select a session to continue</span>
          </div>
        </v-card-text>
      </v-card>
    </div>

    <!-- KPI Cards -->
    <div class="kpis-row">
      <div v-for="stat in kpiStats" :key="stat.title" class="kpi-card">
        <div class="kpi-top-bar"></div>
        <div class="kpi-icon" :style="{ background: stat.gradient }">
          <v-icon size="32" color="white">{{ stat.icon }}</v-icon>
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
          <v-icon size="32" color="white">{{ instrument.icon }}</v-icon>
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

    <!-- Recent Sessions -->
    <div class="section-header">
      <v-icon color="#0B2044" size="20">mdi-history</v-icon>
      <h2>Recent Sessions</h2>
    </div>

    <div class="sessions-row">
      <div v-if="sessions.length === 0" class="empty-sessions">
        <v-icon size="48" color="#ccc">mdi-folder-open</v-icon>
        <p>No sessions yet. Create your first session above!</p>
      </div>
      <div 
        v-for="session in sessions.slice(0, 3)" 
        :key="session.id" 
        class="session-card"
        @click="loadExistingSession(session.id)"
      >
        <div class="session-icon" :style="{ background: '#0B2044' }">
          <v-icon size="20" color="white">mdi-folder</v-icon>
        </div>
        <div class="session-info">
          <div class="session-name">{{ session.name }}</div>
          <div class="session-meta">{{ session.date }}</div>
        </div>
        <div class="session-status" :class="session.status">
          {{ session.status === 'completed' ? '✓' : '⟳' }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const sessions = ref([])
const selectedSessionId = ref('')
const newSessionName = ref('')
const activeSession = ref(null)

const instruments = [
  { id: 'money-market', name: 'Money Market', description: 'Short-term debt instruments', icon: 'mdi-chart-line', gradient: 'linear-gradient(135deg, #1E88E5, #0B2044)' },
  { id: 'bonds', name: 'Bonds', description: 'Fixed income securities', icon: 'mdi-chart-timeline', gradient: 'linear-gradient(135deg, #4CAF50, #2E7D32)' },
  { id: 'tbills', name: 'T-Bills', description: 'Treasury bills', icon: 'mdi-finance', gradient: 'linear-gradient(135deg, #FFC107, #FF9800)' }
]

const canCreateSession = computed(() => {
  if (selectedSessionId.value) return true
  return newSessionName.value.trim() !== ''
})

const kpiStats = computed(() => [
  { title: 'Active Session', value: activeSession.value?.name || 'No Session', icon: 'mdi-folder', gradient: 'linear-gradient(135deg, #0B2044, #1a3a6e)' },
  { title: 'Instruments Used', value: activeSession.value?.instrumentCount || '0', icon: 'mdi-chart-line', gradient: 'linear-gradient(135deg, #1E88E5, #0B2044)' },
  { title: 'Completion', value: `${Math.round((activeSession.value?.instrumentCount || 0) / 3 * 100)}%`, icon: 'mdi-database', gradient: 'linear-gradient(135deg, #4CAF50, #2E7D32)' }
])

function goToSettings() {
  router.push('/settings')
}

// FIXED LOGOUT - Force redirect to login page
function handleLogout() {
  // Clear all storage
  localStorage.clear()
  sessionStorage.clear()
  // Force hard navigation to login page (bypasses any router issues)
  window.location.href = '/login'
}

function loadExistingSession(sessionId) {
  const session = sessions.value.find(s => s.id === sessionId)
  if (session) {
    activeSession.value = session
    selectedSessionId.value = session.id
    localStorage.setItem('active_session', JSON.stringify(session))
  }
}

function loadSelectedSession() {
  if (selectedSessionId.value) {
    const session = sessions.value.find(s => s.id === selectedSessionId.value)
    if (session) activeSession.value = session
  } else {
    activeSession.value = null
  }
}

function createOrLoadSession() {
  if (selectedSessionId.value) {
    const session = sessions.value.find(s => s.id === selectedSessionId.value)
    if (session) {
      activeSession.value = session
      localStorage.setItem('active_session', JSON.stringify(session))
    }
  } else if (newSessionName.value.trim()) {
    const newSession = {
      id: Date.now().toString(),
      name: newSessionName.value.trim(),
      date: new Date().toLocaleString(),
      status: 'in-progress',
      instrumentCount: 0,
      instrumentData: {}
    }
    sessions.value.push(newSession)
    activeSession.value = newSession
    selectedSessionId.value = newSession.id
    localStorage.setItem('sessions_list', JSON.stringify(sessions.value))
    localStorage.setItem('active_session', JSON.stringify(newSession))
    newSessionName.value = ''
  }
}

function clearSessionSelection() {
  selectedSessionId.value = ''
  newSessionName.value = ''
  activeSession.value = null
  localStorage.removeItem('active_session')
}

function deleteCurrentSession() {
  if (activeSession.value) {
    sessions.value = sessions.value.filter(s => s.id !== activeSession.value.id)
    localStorage.setItem('sessions_list', JSON.stringify(sessions.value))
    clearSessionSelection()
  }
}

function goToInstrument(instrumentId) {
  if (!activeSession.value) return
  router.push(`/instrument/${instrumentId}`)
}

function loadSessions() {
  const saved = localStorage.getItem('sessions_list')
  if (saved) sessions.value = JSON.parse(saved)
  const active = localStorage.getItem('active_session')
  if (active) activeSession.value = JSON.parse(active)
}

onMounted(() => {
  loadSessions()
})
</script>

<style scoped>
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
  height: 200px;
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

.session-card {
  border-radius: 16px;
  background: white;
  margin-bottom: 30px;
  overflow: hidden;
  position: relative;
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
  align-items: center;
  gap: 8px;
  color: #0B2044;
  padding: 20px 24px 0 24px;
}

.session-controls {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  padding: 20px;
}

.session-selector {
  flex: 2;
  min-width: 250px;
}

.session-selector label {
  display: block;
  font-size: 12px;
  color: #666;
  margin-bottom: 5px;
}

.session-select, .session-input {
  width: 100%;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 8px;
}

.session-actions {
  display: flex;
  gap: 10px;
  align-items: flex-end;
}

.active-session-info {
  margin: 0 20px 20px;
  padding: 15px;
  background: #e8f5e9;
  border-radius: 12px;
}

.session-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.session-name-display {
  font-weight: 700;
  color: #0B2044;
}

.session-status-badge {
  padding: 2px 10px;
  border-radius: 20px;
  font-size: 11px;
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
  gap: 20px;
  font-size: 12px;
  color: #555;
}

.no-session-warning {
  margin: 0 20px 20px;
  padding: 12px;
  background: #FFF3E0;
  border-radius: 8px;
  display: flex;
  align-items: center;
  gap: 10px;
  color: #E65100;
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
  padding: 24px;
  display: flex;
  align-items: center;
  gap: 16px;
  position: relative;
  overflow: hidden;
  cursor: pointer;
}

.kpi-top-bar {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(90deg, #0B2044, #1E88E5);
  transform: scaleX(0);
  transition: transform 0.3s;
}

.kpi-card:hover .kpi-top-bar {
  transform: scaleX(1);
}

.kpi-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 12px 28px rgba(0,0,0,0.15);
}

.kpi-icon {
  width: 64px;
  height: 64px;
  border-radius: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.kpi-info {
  flex: 1;
}

.kpi-value {
  font-size: 24px;
  font-weight: 800;
  color: #0B2044;
}

.kpi-title {
  font-size: 12px;
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
  padding: 20px;
  display: flex;
  gap: 16px;
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
  width: 60px;
  height: 60px;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.instrument-info {
  flex: 1;
}

.instrument-info h3 {
  color: #0B2044;
  margin-bottom: 5px;
}

.instrument-info p {
  color: #888;
  font-size: 12px;
}

.lock-overlay {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background: rgba(0,0,0,0.6);
  border-radius: 50%;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.sessions-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
}

.session-card {
  background: white;
  border-radius: 16px;
  padding: 16px;
  display: flex;
  align-items: center;
  gap: 14px;
  cursor: pointer;
  transition: all 0.3s;
}

.session-card:hover {
  transform: translateX(5px);
  box-shadow: 0 8px 20px rgba(0,0,0,0.12);
}

.session-icon {
  width: 48px;
  height: 48px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.session-info {
  flex: 1;
}

.session-name {
  font-weight: 700;
  color: #0B2044;
}

.session-meta {
  font-size: 11px;
  color: #999;
}

.session-status {
  padding: 4px 10px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 600;
}

.session-status.in-progress {
  background: #FFF3E0;
  color: #FF9800;
}

.session-status.completed {
  background: #E8F5E9;
  color: #4CAF50;
}

.empty-sessions {
  grid-column: span 3;
  text-align: center;
  padding: 40px;
  background: white;
  border-radius: 20px;
  color: #999;
}

.btn-primary {
  background: linear-gradient(135deg, #0B2044, #1E88E5);
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 8px;
  cursor: pointer;
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  background: white;
  color: #0B2044;
  border: 1px solid #0B2044;
  padding: 10px 20px;
  border-radius: 8px;
  cursor: pointer;
}

.btn-danger {
  background: #f44336;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 8px;
  cursor: pointer;
}

@media (max-width: 900px) {
  .dashboard { padding: 20px; }
  .kpis-row, .instruments-row, .sessions-row {
    grid-template-columns: 1fr;
  }
  .empty-sessions {
    grid-column: span 1;
  }
}
</style>