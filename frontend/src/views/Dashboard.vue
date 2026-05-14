<template>
  <div class="dashboard">
    <!-- Fixed Navigation Bar -->
    <div class="top-navbar">
      <div class="logo-area">
        <div class="logo-placeholder">
          <v-icon size="28" color="#0B2044">mdi-chart-line</v-icon>
          <span class="logo-text">DuraCapital</span>
        </div>
      </div>
      <div class="nav-actions">
        <button class="nav-icon-btn" @click="goToSettings">
          <v-icon>mdi-cog</v-icon>
        </button>
        <button class="nav-icon-btn" @click="logout">
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
        <v-card-title>
          <v-icon>mdi-folder</v-icon>
          Session Management
          <span class="required-badge">Required</span>
        </v-card-title>
        <v-card-text>
          <div class="session-controls">
            <div class="session-selector">
              <label>Select or Create Session:</label>
              <div class="session-input-group">
                <select v-model="selectedSessionId" @change="loadSelectedSession" class="session-select">
                  <option value="">-- Create New Session --</option>
                  <option v-for="session in sessions" :key="session.id" :value="session.id">
                    {{ session.name }} ({{ session.date }}) - {{ session.status === 'completed' ? '✓' : '⟳' }}
                  </option>
                </select>
                <input 
                  v-if="selectedSessionId === ''" 
                  v-model="newSessionName" 
                  placeholder="Enter session name (e.g., Bank ABC, Client XYZ)" 
                  class="session-input"
                />
              </div>
            </div>
            <div class="session-actions">
              <button class="btn-primary" @click="createOrLoadSession" :disabled="!canCreateSession">
                {{ selectedSessionId ? 'Load Session' : 'Create Session' }}
              </button>
              <button class="btn-secondary" @click="clearSessionSelection">Clear</button>
            </div>
          </div>
          
          <!-- Active Session Display -->
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

    <!-- KPI Cards Row -->
    <div class="kpis-row">
      <div v-for="stat in kpiStats" :key="stat.title" class="kpi-card-wrapper">
        <div class="kpi-card">
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
    </div>

    <!-- Select Financial Instrument Section -->
    <div class="section-header">
      <v-icon color="#0B2044" size="20">mdi-filter-outline</v-icon>
      <h2>Select Financial Instrument</h2>
    </div>

    <div class="instruments-row">
      <div 
        v-for="instrument in instruments" 
        :key="instrument.id"
        class="instrument-card"
        :class="{ 'disabled-card': !activeSession, 'completed-card': activeSession && getInstrumentSessionStatus(instrument.id) }"
        @click="activeSession && goToInstrument(instrument.id)"
      >
        <div class="instrument-top-bar"></div>
        <div class="instrument-icon" :style="{ background: instrument.gradient }">
          <v-icon size="32" color="white">{{ instrument.icon }}</v-icon>
        </div>
        <div class="instrument-info">
          <h3>{{ instrument.name }}</h3>
          <p>{{ instrument.description }}</p>
          <div class="instrument-stats">
            <span class="stat-badge">
              <v-icon size="12">mdi-folder</v-icon>
              {{ instrument.count }} Sessions
            </span>
            <span v-if="activeSession && getInstrumentSessionStatus(instrument.id)" class="stat-badge success">
              <v-icon size="12">mdi-check</v-icon>
              Completed
            </span>
            <span v-if="!activeSession" class="stat-badge locked">
              <v-icon size="12">mdi-lock</v-icon>
              Select Session First
            </span>
          </div>
        </div>
        <div v-if="!activeSession" class="lock-overlay">
          <v-icon>mdi-lock</v-icon>
        </div>
        <div v-else-if="getInstrumentSessionStatus(instrument.id)" class="check-overlay">
          <v-icon color="#4CAF50">mdi-check-circle</v-icon>
        </div>
      </div>
    </div>

    <!-- Recent Sessions -->
    <div class="section-header">
      <v-icon color="#0B2044" size="20">mdi-history</v-icon>
      <h2>Recent Sessions</h2>
      <span class="session-count">{{ sessions.length }} Total</span>
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
        <div class="session-icon" :style="{ background: session.color || '#0B2044' }">
          <v-icon size="20" color="white">{{ session.icon || 'mdi-folder' }}</v-icon>
        </div>
        <div class="session-info">
          <div class="session-name">{{ session.name }}</div>
          <div class="session-meta">{{ session.date }}</div>
          <div class="session-rows">{{ session.instrumentCount || 0 }} instruments</div>
        </div>
        <div class="session-status" :class="session.status">
          {{ session.status === 'completed' ? '✓ Complete' : '⟳ Progress' }}
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
  { 
    id: 'money-market', 
    name: 'Money Market', 
    description: 'Short-term debt instruments',
    icon: 'mdi-chart-line', 
    gradient: 'linear-gradient(135deg, #1E88E5, #0B2044)',
    count: 0
  },
  { 
    id: 'bonds', 
    name: 'Bonds', 
    description: 'Fixed income securities',
    icon: 'mdi-chart-timeline', 
    gradient: 'linear-gradient(135deg, #4CAF50, #2E7D32)',
    count: 0
  },
  { 
    id: 'tbills', 
    name: 'T-Bills', 
    description: 'Treasury bills',
    icon: 'mdi-finance', 
    gradient: 'linear-gradient(135deg, #FFC107, #FF9800)',
    count: 0
  }
]

const canCreateSession = computed(() => {
  if (selectedSessionId.value) return true
  return newSessionName.value.trim() !== ''
})

const kpiStats = computed(() => [
  { 
    title: 'Active Session', 
    value: activeSession.value?.name || 'No Session', 
    icon: 'mdi-folder', 
    gradient: 'linear-gradient(135deg, #0B2044, #1a3a6e)'
  },
  { 
    title: 'Instruments Used', 
    value: activeSession.value?.instrumentCount || '0', 
    icon: 'mdi-chart-line', 
    gradient: 'linear-gradient(135deg, #1E88E5, #0B2044)'
  },
  { 
    title: 'Completion', 
    value: `${Math.round((activeSession.value?.instrumentCount || 0) / 3 * 100)}%`, 
    icon: 'mdi-database', 
    gradient: 'linear-gradient(135deg, #4CAF50, #2E7D32)'
  }
])

function getInstrumentSessionStatus(instrumentId) {
  if (!activeSession.value) return false
  return activeSession.value.completedInstruments?.[instrumentId] || false
}

function loadExistingSession(sessionId) {
  const session = sessions.value.find(s => s.id === sessionId)
  if (session) {
    activeSession.value = session
    selectedSessionId.value = session.id
    localStorage.setItem('active_session', JSON.stringify(session))
    updateInstrumentCounts()
  }
}

function loadSelectedSession() {
  if (selectedSessionId.value) {
    const session = sessions.value.find(s => s.id === selectedSessionId.value)
    if (session) {
      activeSession.value = session
      localStorage.setItem('active_session', JSON.stringify(session))
      updateInstrumentCounts()
    }
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
      updateInstrumentCounts()
    }
  } else if (newSessionName.value.trim()) {
    const newSession = {
      id: Date.now().toString(),
      name: newSessionName.value.trim(),
      date: new Date().toLocaleString(),
      status: 'in-progress',
      instrumentCount: 0,
      totalValue: 0,
      completedInstruments: {},
      instrumentData: {}
    }
    sessions.value.push(newSession)
    activeSession.value = newSession
    selectedSessionId.value = newSession.id
    localStorage.setItem('sessions_list', JSON.stringify(sessions.value))
    localStorage.setItem('active_session', JSON.stringify(newSession))
    newSessionName.value = ''
    updateInstrumentCounts()
  }
}

function clearSessionSelection() {
  selectedSessionId.value = ''
  newSessionName.value = ''
  activeSession.value = null
  localStorage.removeItem('active_session')
}

function updateInstrumentCounts() {
  if (!activeSession.value) return
  
  let instrumentCount = 0
  
  instruments.forEach(inst => {
    const sessionData = activeSession.value.instrumentData?.[inst.id]
    if (sessionData && sessionData.totalValue > 0) {
      inst.count = 1
      instrumentCount++
    } else {
      inst.count = 0
    }
  })
  
  activeSession.value.instrumentCount = instrumentCount
  
  const completedCount = Object.values(activeSession.value.completedInstruments || {}).filter(v => v === true).length
  if (completedCount === 3 && instrumentCount === 3) {
    activeSession.value.status = 'completed'
  } else {
    activeSession.value.status = 'in-progress'
  }
  
  const index = sessions.value.findIndex(s => s.id === activeSession.value.id)
  if (index !== -1) {
    sessions.value[index] = activeSession.value
    localStorage.setItem('sessions_list', JSON.stringify(sessions.value))
    localStorage.setItem('active_session', JSON.stringify(activeSession.value))
  }
}

function goToInstrument(instrumentId) {
  if (!activeSession.value) return
  router.push(`/instrument/${instrumentId}?sessionId=${activeSession.value.id}`)
}

function goToSettings() { router.push('/settings') }
function logout() { localStorage.clear(); router.push('/login') }

function loadSessions() {
  const saved = localStorage.getItem('sessions_list')
  if (saved) {
    sessions.value = JSON.parse(saved)
  }
  
  const active = localStorage.getItem('active_session')
  if (active) {
    activeSession.value = JSON.parse(active)
    selectedSessionId.value = activeSession.value.id
    updateInstrumentCounts()
  }
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
  box-shadow: 0 2px 10px rgba(0,0,0,0.05);
  z-index: 1000;
}

.logo-placeholder {
  display: flex;
  align-items: center;
  gap: 10px;
}

.logo-text {
  font-size: 18px;
  font-weight: 600;
  color: #0B2044;
}

.nav-actions {
  display: flex;
  gap: 15px;
}

.nav-icon-btn {
  background: transparent;
  border: none;
  cursor: pointer;
  padding: 8px;
  border-radius: 8px;
  transition: all 0.2s;
  color: #666;
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

.session-section {
  margin-bottom: 30px;
}

.session-card {
  border-radius: 16px;
  background: white;
  border: 1px solid rgba(11,32,68,0.1);
}

.required-badge {
  background: #FF9800;
  color: white;
  font-size: 10px;
  padding: 2px 8px;
  border-radius: 20px;
  margin-left: 10px;
}

.session-controls {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  align-items: flex-end;
}

.session-selector {
  flex: 2;
  min-width: 300px;
}

.session-selector label {
  display: block;
  font-size: 12px;
  color: #666;
  margin-bottom: 5px;
  font-weight: 600;
}

.session-input-group {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.session-select, .session-input {
  width: 100%;
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 14px;
}

.session-actions {
  display: flex;
  gap: 10px;
}

.active-session-info {
  margin-top: 15px;
  padding: 15px;
  background: linear-gradient(135deg, #e8f5e9, #c8e6c9);
  border-radius: 12px;
}

.session-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
  flex-wrap: wrap;
}

.session-name-display {
  font-size: 16px;
  font-weight: 700;
  color: #0B2044;
}

.session-status-badge {
  padding: 2px 10px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 600;
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
  flex-wrap: wrap;
}

.no-session-warning {
  margin-top: 15px;
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
  transition: all 0.3s ease;
  box-shadow: 0 4px 12px rgba(0,0,0,0.05);
  position: relative;
  overflow: hidden;
}

.kpi-top-bar {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(90deg, #0B2044, #1E88E5, #4CAF50);
  transform: scaleX(0);
  transition: transform 0.3s ease;
  transform-origin: left;
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
  flex-shrink: 0;
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
  margin-top: 10px;
}

.section-header h2 {
  color: #0B2044;
  font-size: 18px;
  font-weight: 600;
  margin: 0;
}

.session-count {
  background: #e8ecf1;
  padding: 4px 10px;
  border-radius: 20px;
  font-size: 12px;
  color: #0B2044;
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
  transition: all 0.3s ease;
  box-shadow: 0 4px 12px rgba(0,0,0,0.05);
  position: relative;
  border: 2px solid transparent;
  overflow: hidden;
}

.instrument-card.disabled-card {
  cursor: not-allowed;
  opacity: 0.7;
}

.instrument-card.completed-card {
  border-color: #4CAF50;
  background: linear-gradient(135deg, #fff, #f8fff8);
}

.instrument-top-bar {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(90deg, #0B2044, #1E88E5, #4CAF50);
  transform: scaleX(0);
  transition: transform 0.3s ease;
  transform-origin: left;
}

.instrument-card:not(.disabled-card):hover .instrument-top-bar {
  transform: scaleX(1);
}

.instrument-card:not(.disabled-card):hover {
  transform: translateY(-5px);
  box-shadow: 0 12px 28px rgba(0,0,0,0.15);
  border-color: rgba(11,32,68,0.2);
}

.instrument-icon {
  width: 60px;
  height: 60px;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.instrument-info {
  flex: 1;
}

.instrument-info h3 {
  color: #0B2044;
  font-size: 17px;
  font-weight: 700;
  margin-bottom: 6px;
}

.instrument-info p {
  color: #888;
  font-size: 12px;
  margin-bottom: 10px;
}

.instrument-stats {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.stat-badge {
  background: #f5f5f5;
  padding: 4px 10px;
  border-radius: 20px;
  font-size: 11px;
  color: #666;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.stat-badge.success {
  background: #E8F5E9;
  color: #4CAF50;
}

.stat-badge.locked {
  background: #f5f5f5;
  color: #999;
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

.check-overlay {
  position: absolute;
  top: 10px;
  right: 10px;
}

.sessions-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
  margin-top: 5px;
}

.session-card {
  background: white;
  border-radius: 16px;
  padding: 16px;
  display: flex;
  align-items: center;
  gap: 14px;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 2px 8px rgba(0,0,0,0.05);
}

.session-card:hover {
  transform: translateX(5px);
  box-shadow: 0 8px 20px rgba(0,0,0,0.12);
  background: linear-gradient(135deg, #ffffff, #f8f9ff);
}

.session-icon {
  width: 48px;
  height: 48px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.session-info {
  flex: 1;
}

.session-name {
  font-weight: 700;
  color: #0B2044;
  font-size: 14px;
  margin-bottom: 4px;
}

.session-meta {
  font-size: 11px;
  color: #999;
  margin-bottom: 2px;
}

.session-rows {
  font-size: 10px;
  color: #0B2044;
  font-weight: 600;
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
  padding: 10px 24px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 15px rgba(11,32,68,0.3);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  background: white;
  color: #0B2044;
  border: 2px solid #0B2044;
  padding: 10px 24px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
}

.btn-secondary:hover {
  background: #0B2044;
  color: white;
  transform: translateY(-2px);
}

@media (max-width: 1000px) {
  .dashboard { padding: 20px; }
  .kpis-row, .instruments-row, .sessions-row {
    grid-template-columns: 1fr;
    gap: 16px;
  }
  .empty-sessions { grid-column: span 1; }
  .session-controls { flex-direction: column; align-items: stretch; }
}
</style>