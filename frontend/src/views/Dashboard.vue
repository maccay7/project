<template>
  <div class="dashboard">
    <!-- Fixed Top Navbar -->
    <div class="top-navbar">
      <div class="logo-area">
        <div class="logo-placeholder">
          <img src="/DataStudio-logo.jpeg" alt="DataStudio Logo" class="navbar-logo" @error="e => e.target.style.display = 'none'"/>
        </div>
      </div>
      <div class="nav-actions">
        <button class="nav-icon-btn" @click="goToSettings"><v-icon>mdi-cog</v-icon></button>
        <button class="nav-icon-btn" @click="handleLogout"><v-icon>mdi-logout</v-icon></button>
      </div>
    </div>

    <div class="dashboard-title">
      <h1>Dashboard</h1>
      <!-- Refresh button removed as requested -->
    </div>

    <!-- Two-column: Recent Sessions + Create Session -->
    <div class="session-management-row">
      <div class="recent-sessions-card">
        <v-card class="session-card">
          <v-card-title class="card-title">
            <div class="title-left"><v-icon>mdi-clock-time-eight-outline</v-icon> Recent Sessions</div>
            <div class="title-right"><span class="session-count">{{ filteredSessions.length }} Total</span></div>
          </v-card-title>
          <v-card-text class="card-text-flex">
            <div class="search-bar">
              <v-icon class="search-icon" size="16">mdi-magnify</v-icon>
              <input type="text" v-model="searchQuery" placeholder="Search sessions..." class="search-input"/>
              <button v-if="searchQuery" class="clear-search" @click="searchQuery = ''"><v-icon size="14">mdi-close</v-icon></button>
            </div>
            <div class="sessions-list-container">
              <div class="sessions-list">
                <div v-if="filteredSessions.length === 0" class="empty-sessions-list">
                  <v-icon size="36" color="#ccc">mdi-folder-open</v-icon>
                  <p>No sessions yet</p>
                  <p class="empty-hint">Create a session using the form on the right</p>
                </div>
                <div v-for="session in filteredSessions" :key="session.id" class="session-row-item" :class="{ 'active-session-row': activeSession && activeSession.id === session.id }">
                  <div class="session-row-icon" :style="{ background: '#0B2044' }" @click="loadExistingSession(session.id)">
                    <v-icon size="14" color="white">mdi-folder-text-outline</v-icon>
                  </div>
                  <div class="session-row-info" @click="loadExistingSession(session.id)">
                    <div class="session-row-name">{{ session.name }}</div>
                    <div class="session-row-meta">{{ formatDate(session.date) }}</div>
                  </div>
                  <div class="session-row-stats" @click.stop="openInstrumentModal(session.id)" style="cursor: pointer;">
                    <span>{{ getInstrumentCount(session) }}/3 instruments</span>
                  </div>
                  <div class="session-row-status" :class="session.status">{{ session.status === 'completed' ? '✓' : '⟳' }}</div>
                  <button class="version-btn" @click.stop="openVersionModal(session.id)">
                    <v-icon size="12">mdi-history</v-icon>
                    <span class="version-count">{{ session.version_count || 0 }}</span>
                  </button>
                  <button class="row-rename-btn" @click.stop="openRename(session)" title="Rename"><v-icon size="12">mdi-pencil</v-icon></button>
                  <button class="row-delete-btn" @click.stop="deleteSession(session.id)"><v-icon size="12">mdi-close</v-icon></button>
                </div>
              </div>
            </div>
          </v-card-text>
        </v-card>
      </div>

      <div class="create-session-card">
        <v-card class="session-card">
          <v-card-title class="card-title"><v-icon>mdi-folder-plus-outline</v-icon> Create New Session</v-card-title>
          <v-card-text class="create-session-content">
            <div class="create-session-input">
              <input v-model="newSessionName" placeholder="Enter session name" class="session-input" @keyup.enter="createNewSession"/>
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
                  <button v-if="!renamingActive" class="btn-rename-sm" @click="startRenameActive">Rename</button>
                  <button v-else class="btn-rename-sm" @click="saveRename">Save</button>
                  <span class="session-status-badge" :class="activeSession.status">{{ activeSession.status === 'completed' ? 'Completed' : 'In Progress' }}</span>
                </div>
                <div class="session-details">
                  <span>Created: {{ formatDate(activeSession.date) }}</span>
                  <span>Instruments: {{ activeInstrumentCount }}/3</span>
                  <span>Versions: {{ activeSession.version_count || 0 }}</span>
                </div>
              </div>
              <div v-else class="no-session-warning">
                <v-icon color="warning" size="16">mdi-alert-circle-outline</v-icon>
                <span>No active session selected</span>
              </div>
            </div>

            <div class="flex-spacer"></div>
            <div class="session-stats-summary">
              <div class="stats-header"><v-icon size="16">mdi-chart-box</v-icon><span>Session Summary</span></div>
              <div class="stats-grid">
                <div class="stat-item"><div class="stat-number">{{ totalSessions }}</div><div class="stat-label">Total Sessions</div></div>
                <div class="stat-item"><div class="stat-number">{{ completedSessions }}</div><div class="stat-label">Completed</div></div>
                <div class="stat-item"><div class="stat-number">{{ inProgressSessions }}</div><div class="stat-label">In Progress</div></div>
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
        <div class="kpi-icon" :style="{ background: stat.gradient }"><v-icon size="28" color="white">{{ stat.icon }}</v-icon></div>
        <div class="kpi-info"><div class="kpi-value">{{ stat.value }}</div><div class="kpi-title">{{ stat.title }}</div></div>
      </div>
    </div>

    <!-- Instruments -->
    <div class="section-header"><v-icon color="#0B2044" size="20">mdi-filter-outline</v-icon><h2>Select Financial Instrument</h2></div>
    <div class="instruments-row">
      <div v-for="instrument in instruments" :key="instrument.id" class="instrument-card" :class="{ 'disabled-card': !activeSession }" @click="activeSession && goToInstrument(instrument.id)">
        <div class="instrument-icon" :style="{ background: instrument.gradient }"><v-icon size="28" color="white">{{ instrument.icon }}</v-icon></div>
        <div class="instrument-info"><h3>{{ instrument.name }}</h3><p>{{ instrument.description }}</p></div>
        <div v-if="!activeSession" class="lock-overlay"><v-icon>mdi-lock</v-icon></div>
      </div>
    </div>

    <!-- Version History Modal -->
    <v-dialog v-model="versionDialogVisible" max-width="650px" persistent>
      <v-card>
        <v-card-title class="version-dialog-title">
          Change History – {{ selectedSessionForVersions?.name || 'Session' }}
          <span v-if="currentUserFullName"> ({{ currentUserFullName }})</span>
          <v-spacer></v-spacer>
          <button class="btn-close-dialog" @click="versionDialogVisible = false">✕</button>
        </v-card-title>
        <v-card-text class="version-dialog-body">
          <div class="version-search-bar">
            <v-icon size="16" class="search-icon">mdi-magnify</v-icon>
            <input type="text" v-model="versionSearchQuery" placeholder="Search versions..." class="version-search-input"/>
            <button v-if="versionSearchQuery" class="clear-search" @click="versionSearchQuery = ''"><v-icon size="14">mdi-close</v-icon></button>
          </div>
          <div class="version-list-container">
            <div v-if="!filteredVersions.length" class="empty-versions">
              <v-icon size="36" color="#ccc">mdi-file-document-outline</v-icon>
              <p>{{ selectedSessionForVersions?.versions?.length ? 'No versions match your search.' : 'No changes recorded yet.' }}</p>
            </div>
            <div v-else class="version-list">
              <div v-for="(ver, idx) in filteredVersions" :key="idx" class="version-entry" :class="{ 'latest': idx === 0 }">
                <div class="version-entry-header">
                  <div class="version-entry-time">
                    <span v-if="ver.versionNumber" class="version-number">v{{ ver.versionNumber }}</span>
                    {{ formatVersionTime(ver.timestamp) }}
                  </div>
                  <div class="version-entry-badge" :class="ver.changeTypeClass">{{ ver.changeType || 'Saved' }}</div>
                </div>
                <div class="version-entry-details">
                  <!-- 🔥 Display Instrument and Change separately -->
                  <div class="version-entry-row" style="margin-bottom: 4px;">
                    <span class="label">Instrument</span>
                    <span class="value" style="font-weight:600; color:#0B2044;">{{ ver.instrumentType || '—' }}</span>
                  </div>
                  <div class="version-entry-row">
                    <span class="label">Change</span>
                    <span class="value" style="font-weight:600; color:#0B2044;">{{ ver.changeSummary || 'No description' }}</span>
                  </div>
                  <!-- Additional info if available -->
                  <div class="version-entry-row" v-if="ver.modifiedInstruments && ver.modifiedInstruments.length">
                    <span class="label">Modified</span>
                    <span class="value fields-tags">
                      <span v-for="(inst, ii) in ver.modifiedInstruments" :key="ii" class="field-tag">{{ inst }}</span>
                    </span>
                  </div>
                  <div class="version-entry-row" v-if="ver.fieldsChanged && ver.fieldsChanged.length">
                    <span class="label">Changed Fields</span>
                    <span class="value fields-tags">
                      <span v-for="(field, fi) in ver.fieldsChanged" :key="fi" class="field-tag">{{ field }}</span>
                    </span>
                  </div>
                </div>
                <div class="version-entry-actions">
                  <button class="btn-restore" @click="restoreVersion(selectedSessionForVersions.id, idx)">Restore</button>
                </div>
              </div>
            </div>
          </div>
        </v-card-text>
        <v-card-actions class="version-dialog-actions">
          <v-spacer></v-spacer>
          <button class="btn-secondary" @click="versionDialogVisible = false">Close</button>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Session Instruments Modal -->
    <v-dialog v-model="instrumentDialogVisible" max-width="600px" persistent>
      <v-card>
        <v-card-title class="version-dialog-title">
          Session Instruments – {{ selectedSessionForInstruments?.name || 'Session' }}
          <v-spacer></v-spacer>
          <button class="btn-close-dialog" @click="instrumentDialogVisible = false">✕</button>
        </v-card-title>
        <v-card-text class="version-dialog-body">
          <div v-if="!sessionInstruments.length" class="empty-versions">
            <v-icon size="36" color="#ccc">mdi-chart-line</v-icon>
            <p>No instruments saved yet.</p>
          </div>
          <div v-else class="version-list">
            <div v-for="(inst, idx) in sessionInstruments" :key="idx" class="version-entry">
              <div class="version-entry-header">
                <div class="version-entry-time">{{ inst.instrument_type || 'Instrument' }}</div>
                <div class="version-entry-badge">{{ inst.status || 'Saved' }}</div>
              </div>
              <div class="version-entry-details">
                <div class="version-entry-row">
                  <span class="label">Name</span>
                  <span class="value" style="font-weight:600; color:#0B2044;">{{ inst.instrument_name || '—' }}</span>
                </div>
                <div class="version-entry-row">
                  <span class="label">Saved At</span>
                  <span class="value">{{ formatVersionTime(inst.saved_at) }}</span>
                </div>
                <div class="version-entry-row">
                  <span class="label">Versions</span>
                  <span class="value">{{ inst.version_count || 0 }}</span>
                </div>
              </div>
            </div>
          </div>
        </v-card-text>
        <v-card-actions class="version-dialog-actions">
          <v-spacer></v-spacer>
          <button class="btn-secondary" @click="instrumentDialogVisible = false">Close</button>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup>
// ================================================================
// ✅ FULL IMPLEMENTATION – ALL FIXES APPLIED
// Fixed: version fetching, change summary display, instrument count.
// ================================================================

import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import sessionManager from '@/services/sessionManager.js'
import { useRouter } from 'vue-router'
import api from '@/services/api.js'

const router = useRouter()

const STORAGE_KEY = 'dura_sessions'
const ACTIVE_KEY = 'dura_active_session_id'

// ---- Reactive state ----
const sessions = ref([])
const searchQuery = ref('')
const newSessionName = ref('')
const activeSession = ref(null)
const renamingActive = ref(false)
const renameInput = ref('')
const versionDialogVisible = ref(false)
const selectedSessionForVersions = ref(null)
const versionSearchQuery = ref('')
const currentUserFullName = ref('')
const instrumentDialogVisible = ref(false)
const selectedSessionForInstruments = ref(null)
const sessionInstruments = ref([])

// ---- Instruments data ----
const instruments = [
  { id: 'money-market', name: 'Money Market', description: 'Short-term debt instruments', icon: 'mdi-chart-line', gradient: 'linear-gradient(135deg, #1E88E5, #0B2044)' },
  { id: 'bonds', name: 'Bonds', description: 'Fixed income securities', icon: 'mdi-chart-timeline', gradient: 'linear-gradient(135deg, #4CAF50, #2E7D32)' },
  { id: 'tbills', name: 'T-Bills', description: 'Treasury bills', icon: 'mdi-finance', gradient: 'linear-gradient(135deg, #FFC107, #FF9800)' }
]

// ---- Computed ----
const filteredSessions = computed(() => {
  const q = searchQuery.value.toLowerCase()
  return q ? sessions.value.filter(s => s.name.toLowerCase().includes(q)) : sessions.value
})

const totalSessions = computed(() => sessions.value.length)
const completedSessions = computed(() => sessions.value.filter(s => s.status === 'completed').length)
const inProgressSessions = computed(() => sessions.value.filter(s => s.status === 'in-progress').length)

const backendKpiData = ref(null)
const kpiStats = computed(() => {
  if (backendKpiData.value) {
    return [
      { title: 'Active Sessions', value: backendKpiData.value.active_sessions || totalSessions.value, icon: 'mdi-folder-multiple', gradient: 'linear-gradient(135deg, #0B2044, #1a3a6e)' },
      { title: 'Worked Instruments', value: backendKpiData.value.total_instruments || 0, icon: 'mdi-chart-line', gradient: 'linear-gradient(135deg, #4CAF50, #2E7D32)' },
      { title: 'Portfolio Total', value: formatCurrency(backendKpiData.value.portfolio_total || 0), icon: 'mdi-cash', gradient: 'linear-gradient(135deg, #FFC107, #FF9800)' }
    ]
  }
  const totalInstruments = sessions.value.reduce((sum, s) => sum + (s.instrument_count || 0), 0)
  const portfolioTotal = sessions.value.reduce((sum, s) => sum + (s.total_value || 0), 0)
  return [
    { title: 'Active Sessions', value: totalSessions.value, icon: 'mdi-folder-multiple', gradient: 'linear-gradient(135deg, #0B2044, #1a3a6e)' },
    { title: 'Worked Instruments', value: totalInstruments, icon: 'mdi-chart-line', gradient: 'linear-gradient(135deg, #4CAF50, #2E7D32)' },
    { title: 'Portfolio Total', value: formatCurrency(portfolioTotal), icon: 'mdi-cash', gradient: 'linear-gradient(135deg, #FFC107, #FF9800)' }
  ]
})

const activeInstrumentCount = computed(() => {
  if (!activeSession.value) return 0
  return activeSession.value.instrument_count || 0
})

// ---- 🔥 FIX: filteredVersions uses actual versions from API ----
const filteredVersions = computed(() => {
  const versions = selectedSessionForVersions.value?.versions || []
  const q = versionSearchQuery.value.toLowerCase()
  if (!q) return versions
  return versions.filter(v =>
    (v.instrumentType || '').toLowerCase().includes(q) ||
    (v.changeSummary || '').toLowerCase().includes(q) ||
    (v.changeType || '').toLowerCase().includes(q)
  )
})

// ---- Helper functions ----
const formatDate = d => d ? new Date(d).toLocaleString() : ''
const formatVersionTime = t => new Date(t).toLocaleString()
const formatCurrency = (val) => {
  if (!val) return '$0'
  return '$' + Number(val).toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })
}

function getInstrumentCount(session) {
  return session?.instrument_count || 0
}

// ---- Refresh Dashboard from backend ----
async function refreshDashboard() {
  try {
    const backendSessions = await sessionManager.getAllSessions()
    sessions.value = backendSessions.map(s => ({
      ...s,
      version_count: s.version_count || 0,
      instrument_count: Math.min(s.instrument_count || 0, 3)
    }))
    if (activeSession.value) {
      const updated = sessions.value.find(s => s.id === activeSession.value.id)
      if (updated) {
        activeSession.value = updated
      } else {
        activeSession.value = null
        localStorage.removeItem(ACTIVE_KEY)
      }
    }
  } catch (error) {
    console.error('Failed to refresh dashboard:', error)
  }
}

async function refreshSession(sessionId) {
  try {
    const session = await sessionManager.getSession(sessionId)
    if (session) {
      // Fetch versions from API
      let versions = []
      try {
        const res = await api.versionAPI.getVersions(sessionId)
        if (res && res.success && res.data) {
          versions = res.data.map(v => ({
            id: v.id,
            versionNumber: v.versionNumber,
            timestamp: v.timestamp || v.created_at,
            changeSummary: v.changeSummary || v.change_summary || 'No description',
            instrumentType: v.instrumentType || v.instrument_type || 'General',
            changeType: v.changeType || 'Saved',
            changeTypeClass: v.changeTypeClass || 'badge-saved',
            modifiedInstruments: v.modifiedInstruments || [],
            fieldsChanged: v.fieldsChanged || []
          }))
        }
      } catch (e) {
        console.warn('Failed to fetch versions for session:', sessionId, e)
      }
      const enriched = {
        ...session,
        versions: versions,
        version_count: versions.length || session.version_count || 0,
        instrument_count: Math.min(session.instrument_count || 0, 3)
      }
      const idx = sessions.value.findIndex(s => s.id === sessionId)
      if (idx !== -1) {
        sessions.value[idx] = enriched
      }
      if (activeSession.value?.id === sessionId) {
        activeSession.value = enriched
      }
    }
  } catch (error) {
    console.error('Failed to refresh session:', error)
  }
}

// ---- Session CRUD (using sessionManager) ----
async function createNewSession() {
  if (!newSessionName.value.trim()) return
  try {
    const created = await sessionManager.createSession(newSessionName.value.trim())
    await refreshDashboard()
    const fresh = sessions.value.find(s => s.id === created.id)
    if (fresh) {
      activeSession.value = fresh
      sessionManager.setActiveSession(fresh)
      localStorage.setItem(ACTIVE_KEY, fresh.id)
    }
    newSessionName.value = ''
  } catch (err) {
    alert('Failed to create session: ' + err.message)
  }
}

async function loadExistingSession(sessionId) {
  try {
    const session = await sessionManager.getSession(sessionId)
    if (session) {
      // Fetch versions
      let versions = []
      try {
        const res = await api.versionAPI.getVersions(sessionId)
        if (res && res.success && res.data) {
          versions = res.data.map(v => ({
            id: v.id,
            versionNumber: v.versionNumber,
            timestamp: v.timestamp || v.created_at,
            changeSummary: v.changeSummary || v.change_summary || 'No description',
            instrumentType: v.instrumentType || v.instrument_type || 'General',
            changeType: v.changeType || 'Saved',
            changeTypeClass: v.changeTypeClass || 'badge-saved',
            modifiedInstruments: v.modifiedInstruments || [],
            fieldsChanged: v.fieldsChanged || []
          }))
        }
      } catch (e) {}
      session.versions = versions
      session.version_count = versions.length
      activeSession.value = session
      sessionManager.setActiveSession(session)
      localStorage.setItem(ACTIVE_KEY, session.id)
      await refreshDashboard()
    }
  } catch (err) {
    alert('Error loading session: ' + err.message)
  }
}

async function openRename(session) {
  const name = prompt('Rename session:', session.name)
  if (name?.trim()) {
    try {
      await sessionManager.renameSession(session.id, name.trim())
      await refreshDashboard()
      if (activeSession.value?.id === session.id) {
        const updated = sessions.value.find(s => s.id === session.id)
        if (updated) activeSession.value = updated
      }
    } catch (err) {
      alert('Rename failed: ' + err.message)
    }
  }
}

async function deleteSession(sessionId) {
  if (!confirm('Delete this session permanently?')) return
  try {
    await sessionManager.deleteSession(sessionId)
    await refreshDashboard()
    if (activeSession.value?.id === sessionId) {
      activeSession.value = null
      localStorage.removeItem(ACTIVE_KEY)
    }
  } catch (err) {
    alert('Delete failed: ' + err.message)
  }
}

// ---- Version history modal ----
async function openVersionModal(sessionId) {
  try {
    const session = await sessionManager.getSession(sessionId)
    if (session) {
      // Fetch versions from API
      let versions = []
      try {
        const res = await api.versionAPI.getVersions(sessionId)
        console.log('Versions API response:', res)
        if (res && res.success && res.data) {
          versions = res.data.map(v => ({
            id: v.id,
            versionNumber: v.versionNumber,
            timestamp: v.timestamp || v.created_at,
            changeSummary: v.changeSummary || v.change_summary || 'No description',
            instrumentType: v.instrumentType || v.instrument_type || 'General',
            changeType: v.changeType || 'Saved',
            changeTypeClass: v.changeTypeClass || 'badge-saved',
            modifiedInstruments: v.modifiedInstruments || [],
            fieldsChanged: v.fieldsChanged || []
          }))
          console.log('Mapped versions:', versions)
          // Update session versions
          session.versions = versions
          session.version_count = versions.length
          await sessionManager.updateSession(sessionId, { versions, version_count: versions.length })
        }
      } catch (e) {
        console.warn('Failed to fetch versions:', e)
        // Fallback to existing
        versions = session.versions || []
      }
      console.log('Setting selectedSessionForVersions with versions:', versions.length)
      selectedSessionForVersions.value = {
        ...session,
        versions: versions
      }
      versionSearchQuery.value = ''
      versionDialogVisible.value = true
    }
  } catch (err) {
    alert('Error loading versions: ' + err.message)
  }
}

async function restoreVersion(sessionId, index) {
  try {
    const session = await sessionManager.getSession(sessionId)
    if (!session || !session.versions || !session.versions[index]) {
      alert('Version not found')
      return
    }
    
    const version = session.versions[index]
    if (!confirm(`Restore session to version ${version.versionNumber} from ${new Date(version.timestamp).toLocaleString()}?\n\nThis will replace all current data with the saved version.`)) {
      return
    }
    
    // Restore the version data
    const response = await api.versionAPI.restoreVersion(sessionId, version.id)
    if (response && response.success) {
      alert(`✅ Session restored to version ${version.versionNumber}`)
      versionDialogVisible.value = false
      await refreshSession(sessionId)
      await refreshDashboard()
    } else {
      alert('Failed to restore version: ' + (response?.message || 'Unknown error'))
    }
  } catch (err) {
    console.error('Restore error:', err)
    alert('Error restoring version: ' + err.message)
  }
}

// ---- Session instruments modal ----
async function openInstrumentModal(sessionId) {
  try {
    const session = await sessionManager.getSession(sessionId)
    if (session) {
      selectedSessionForInstruments.value = session
      const instruments = []
      const workflows = session.instrumentWorkflow || {}
      const instrumentKeys = ['money-market', 'bonds', 'tbills']
      
      // Count actual instruments with data
      let instrumentCount = 0
      for (const key of instrumentKeys) {
        const wf = workflows[key]
        if (wf && (wf.cleanedData?.length > 0 || wf.rawData?.length > 0 || wf.data?.length > 0 || wf.calculations)) {
          instrumentCount++
          let instrumentName = wf.instrumentName || key
          if (instrumentName.includes('.')) instrumentName = instrumentName.split('.')[0]
          instruments.push({
            instrument_type: key,
            instrument_name: instrumentName || 'Unnamed',
            status: 'Saved',
            saved_at: wf.sessionSavedAt || session.updated_at || Date.now(),
            version_count: session.version_count || 0,
            has_data: true
          })
        }
      }
      
      // Update session instrument count
      if (instrumentCount !== session.instrument_count) {
        sessionManager.updateSession(sessionId, { instrument_count: instrumentCount })
        session.instrument_count = instrumentCount
      }
      
      // Fallback to versions if no workflow data
      if (instruments.length === 0 && session.version_count > 0) {
        const existingVersions = session.versions || []
        const seen = new Set()
        for (const v of existingVersions) {
          if (v.instrumentType && !seen.has(v.instrumentType)) {
            seen.add(v.instrumentType)
            instruments.push({
              instrument_type: v.instrumentType,
              instrument_name: v.instrumentType,
              status: 'Saved',
              saved_at: v.timestamp,
              version_count: 1
            })
          }
        }
      }
      
      sessionInstruments.value = instruments
      instrumentDialogVisible.value = true
    }
  } catch (err) {
    console.error('Error loading instruments:', err)
    alert('Error loading instruments: ' + err.message)
  }
}

// ---- Active session rename ----
function startRenameActive() {
  if (activeSession.value) {
    renameInput.value = activeSession.value.name
    renamingActive.value = true
  }
}

async function saveRename() {
  if (!activeSession.value || !renameInput.value.trim()) return
  try {
    await sessionManager.renameSession(activeSession.value.id, renameInput.value.trim())
    await refreshDashboard()
    const updated = sessions.value.find(s => s.id === activeSession.value.id)
    if (updated) activeSession.value = updated
    renamingActive.value = false
  } catch (err) {
    alert('Rename failed: ' + err.message)
  }
}

// ---- Navigation ----
function goToInstrument(instrumentId) {
  if (!activeSession.value) {
    alert('Please select a session first')
    return
  }
  sessionManager.setActiveSession(activeSession.value)
  router.push({ path: `/instrument/${instrumentId}`, query: { session: activeSession.value.id } })
}

function goToSettings() { router.push('/settings') }

function handleLogout() {
  localStorage.removeItem('auth_token')
  localStorage.removeItem('user')
  sessionStorage.clear()
  window.location.href = '/login'
}

// ---- Functions ----
async function fetchBackendKPI() {
  try {
    const response = await api.dashboardAPI.getKPI()
    if (response?.success && response?.data) {
      backendKpiData.value = {
        active_sessions: response.data.total_users || 0,
        total_instruments: response.data.total_instruments || 0,
        portfolio_total: response.data.datasets_processed || 0
      }
    }
  } catch (err) {
    console.error('Failed to fetch backend KPI data:', err)
  }
}

// ===== 🔥 FIX: handleSessionUpdate at root scope =====
const handleSessionUpdate = async (event) => {
  const { sessionId, versionCount, instrumentCount } = event.detail || {}
  if (sessionId) {
    // Update the specific session
    await refreshSession(sessionId)
    // If we have a versionCount, update the active session immediately
    if (versionCount !== undefined && activeSession.value?.id === sessionId) {
      activeSession.value.version_count = versionCount
    }
    if (instrumentCount !== undefined && activeSession.value?.id === sessionId) {
      activeSession.value.instrument_count = instrumentCount
    }
    // Also update selectedSessionForVersions if it matches
    if (selectedSessionForVersions.value?.id === sessionId) {
      // Fetch updated versions for the dialog
      try {
        const versionsRes = await api.versionAPI.getVersions(sessionId)
        if (versionsRes && versionsRes.success && versionsRes.data) {
          const versions = versionsRes.data.map(v => ({
            id: v.id,
            versionNumber: v.versionNumber,
            timestamp: v.timestamp || v.created_at,
            changeSummary: v.changeSummary || v.change_summary || 'No description',
            instrumentType: v.instrumentType || v.instrument_type || 'General',
            changeType: v.changeType || 'Saved',
            changeTypeClass: v.changeTypeClass || 'badge-saved',
            modifiedInstruments: v.modifiedInstruments || [],
            fieldsChanged: v.fieldsChanged || []
          }))
          selectedSessionForVersions.value.versions = versions
          selectedSessionForVersions.value.version_count = versions.length
        }
      } catch (e) {
        console.warn('Failed to update versions in dialog:', e)
      }
    }
    // Refresh the dashboard to ensure everything is consistent
    await refreshDashboard()
  } else {
    await refreshDashboard()
  }
}

// ---- Lifecycle ----
onMounted(async () => {
  try {
    const user = JSON.parse(localStorage.getItem('user'))
    if (user) {
      currentUserFullName.value = (user.firstName || '' + ' ' + user.lastName || '').trim()
    }
  } catch {}

  await fetchBackendKPI()
  await refreshDashboard()

  let activeId = localStorage.getItem(ACTIVE_KEY)
  if (activeId) {
    const session = sessions.value.find(s => s.id === activeId)
    if (session) {
      // Fetch versions
      let versions = []
      try {
        const res = await api.versionAPI.getVersions(activeId)
        if (res && res.success && res.data) {
          versions = res.data.map(v => ({
            id: v.id,
            versionNumber: v.versionNumber,
            timestamp: v.timestamp || v.created_at,
            changeSummary: v.changeSummary || v.change_summary || 'No description',
            instrumentType: v.instrumentType || v.instrument_type || 'General',
            changeType: v.changeType || 'Saved',
            changeTypeClass: v.changeTypeClass || 'badge-saved',
            modifiedInstruments: v.modifiedInstruments || [],
            fieldsChanged: v.fieldsChanged || []
          }))
        }
      } catch (e) {}
      session.versions = versions
      session.version_count = versions.length
      activeSession.value = session
      sessionManager.setActiveSession(session)
    } else {
      localStorage.removeItem(ACTIVE_KEY)
      activeId = null
    }
  }

  if (!activeSession.value && sessions.value.length) {
    activeSession.value = sessions.value[0]
    sessionManager.setActiveSession(activeSession.value)
    localStorage.setItem(ACTIVE_KEY, activeSession.value.id)
  }

  window.addEventListener('session-updated', handleSessionUpdate)
})

// ===== 🔥 FIX: onBeforeUnmount at root scope =====
onBeforeUnmount(() => {
  window.removeEventListener('session-updated', handleSessionUpdate)
})
</script>

<style scoped>
/* your existing styles – unchanged */
.dashboard { min-height: 100vh; background: linear-gradient(135deg, #f5f7fa 0%, #e8ecf1 100%); padding: 20px 40px; }
.top-navbar { position: fixed; top: 0; left: 0; right: 0; height: 60px; background: white; display: flex; justify-content: space-between; align-items: center; padding: 0 30px; box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05); z-index: 1000; }
.logo-placeholder { display: flex; align-items: center; }
.navbar-logo { width: 180px; max-height: 48px; height: auto; object-fit: contain; border-radius: 8px; }
.nav-actions { display: flex; gap: 15px; align-items: center; }
.nav-icon-btn { background: transparent; border: none; cursor: pointer; padding: 8px; border-radius: 8px; transition: all 0.2s; color: #666; display: flex; align-items: center; justify-content: center; }
.nav-icon-btn:hover { background: #f0f0f0; color: #0B2044; }
.dashboard-title { margin-top: 80px; margin-bottom: 25px; display: flex; align-items: center; justify-content: space-between; }
.dashboard-title h1 { color: #0B2044; font-size: 28px; font-weight: 700; margin: 0; }
.session-management-row { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-bottom: 30px; }
.recent-sessions-card, .create-session-card { width: 100%; }
.session-card { border-radius: 16px; background: white; overflow: hidden; position: relative; height: 100%; min-height: 440px; display: flex; flex-direction: column; }
.session-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 4px; background: linear-gradient(90deg, #0B2044, #1E88E5); }
.card-title { display: flex; justify-content: space-between; align-items: center; padding: 14px 18px 0 18px; }
.title-left { display: flex; align-items: center; gap: 8px; color: #0B2044; font-size: 15px; font-weight: 600; }
.title-right { display: flex; align-items: center; }
.session-count { background: #e8ecf1; padding: 2px 8px; border-radius: 20px; font-size: 11px; color: #0B2044; }
.card-text-flex { flex: 1; display: flex; flex-direction: column; padding: 0 16px 16px 16px; }
.search-bar { display: flex; align-items: center; background: #f5f5f5; border-radius: 8px; padding: 5px 10px; margin: 10px 0; border: 1px solid #e0e0e0; transition: all 0.2s; }
.search-bar:focus-within { border-color: #0B2044; background: white; }
.search-icon { color: #999; margin-right: 6px; }
.search-input { flex: 1; border: none; background: transparent; outline: none; font-size: 12px; }
.clear-search { background: none; border: none; cursor: pointer; color: #999; display: flex; align-items: center; justify-content: center; padding: 2px; }
.clear-search:hover { color: #f44336; }
.sessions-list-container { flex: 1; overflow-y: auto; margin: 0 0 8px 0; min-height: 0; max-height: 320px; }
.sessions-list { padding: 0 8px 8px 0; }
.sessions-list::-webkit-scrollbar { width: 4px; }
.sessions-list::-webkit-scrollbar-track { background: #f0f0f0; border-radius: 4px; }
.sessions-list::-webkit-scrollbar-thumb { background: #0B2044; border-radius: 4px; }
.session-row-item { display: flex; align-items: center; gap: 8px; padding: 6px 8px; margin-bottom: 3px; background: #f8f9ff; border-radius: 8px; transition: all 0.2s; position: relative; border: 1px solid transparent; }
.session-row-item:hover { background: white; border-color: #e0e0e0; transform: translateX(3px); }
.session-row-item.active-session-row { background: #e3f2fd !important; border-left: 3px solid #1E88E5; }
.session-row-icon { width: 28px; height: 28px; border-radius: 6px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; cursor: pointer; }
.session-row-info { flex: 2; min-width: 90px; cursor: pointer; }
.session-row-name { font-weight: 600; color: #0B2044; font-size: 12px; margin-bottom: 1px; }
.session-row-meta { font-size: 9px; color: #999; }
.session-row-stats { flex: 2; display: flex; gap: 6px; font-size: 9px; color: #666; }
.session-row-status { width: 24px; text-align: center; padding: 2px 0; border-radius: 10px; font-size: 9px; font-weight: 600; }
.session-row-status.in-progress { background: #FFF3E0; color: #FF9800; }
.session-row-status.completed { background: #E8F5E9; color: #4CAF50; }
.version-btn { background: #e8ecf1; border: none; border-radius: 20px; padding: 4px 10px; font-size: 10px; cursor: pointer; display: inline-flex; align-items: center; gap: 4px; transition: all 0.2s; color: #0B2044; white-space: nowrap; }
.version-btn:hover { background: #d0d5dd; }
.version-count { font-weight: 600; }
.row-rename-btn { background: #0B2044; border: none; color: white; width: 20px; height: 20px; border-radius: 50%; display: flex; align-items: center; justify-content: center; cursor: pointer; opacity: 0; margin-right: 4px; }
.session-row-item:hover .row-rename-btn { opacity: 1; }
.session-rename-input { flex: 1; min-width: 120px; padding: 4px 8px; border: 1px solid #0B2044; border-radius: 6px; font-size: 13px; }
.btn-rename-sm { background: #0B2044; color: white; border: none; padding: 4px 10px; border-radius: 6px; font-size: 12px; cursor: pointer; margin-left: 8px; }
.row-delete-btn { background: #f44336; border: none; color: white; width: 20px; height: 20px; border-radius: 50%; display: flex; align-items: center; justify-content: center; cursor: pointer; transition: all 0.2s; opacity: 0; flex-shrink: 0; }
.session-row-item:hover .row-delete-btn { opacity: 1; }
.row-delete-btn:hover { background: #d32f2f; transform: scale(1.1); }
.empty-sessions-list { text-align: center; padding: 40px 20px; color: #999; }
.empty-sessions-list p { margin-top: 6px; font-size: 12px; }
.empty-hint { font-size: 10px; color: #bbb; margin-top: 4px; }
.create-session-content { flex: 1; display: flex; flex-direction: column; height: 100%; padding: 16px; }
.create-session-input { padding: 0 0 6px 0; }
.session-input { width: 100%; padding: 8px 12px; border: 1px solid #e0e0e0; border-radius: 8px; font-size: 12px; transition: all 0.2s; }
.session-input:focus { outline: none; border-color: #0B2044; box-shadow: 0 0 0 2px rgba(11, 32, 68, 0.1); }
.create-session-action { padding: 0 0 12px 0; }
.full-width { width: 100%; }
.active-session-container { margin: 0; }
.active-session-info { padding: 8px 10px; background: #e8f5e9; border-radius: 8px; margin-bottom: 12px; }
.session-header { display: flex; align-items: center; gap: 6px; margin-bottom: 3px; flex-wrap: wrap; }
.session-name-display { font-weight: 600; color: #0B2044; font-size: 11px; }
.session-status-badge { padding: 1px 6px; border-radius: 10px; font-size: 8px; }
.session-status-badge.in-progress { background: #FFF3E0; color: #FF9800; }
.session-status-badge.completed { background: #E8F5E9; color: #4CAF50; }
.session-details { display: flex; gap: 10px; font-size: 9px; color: #555; }
.no-session-warning { padding: 10px 10px; background: #FFF3E0; border-radius: 8px; display: flex; align-items: center; gap: 6px; color: #E65100; font-size: 10px; margin-bottom: 12px; }
.flex-spacer { flex: 1; min-height: 10px; }
.session-stats-summary { background: #f8f9ff; margin: 0; padding: 10px 12px; border-radius: 10px; border: 1px solid rgba(11, 32, 68, 0.08); }
.stats-header { display: flex; align-items: center; gap: 6px; font-weight: 600; color: #0B2044; font-size: 11px; margin-bottom: 8px; }
.stats-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.stat-item { text-align: center; }
.stat-number { font-size: 20px; font-weight: 700; color: #0B2044; }
.stat-label { font-size: 9px; color: #888; margin-top: 2px; }
.kpis-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; margin-bottom: 40px; }
.kpi-card { background: white; border-radius: 20px; padding: 18px; display: flex; align-items: center; gap: 12px; position: relative; overflow: hidden; cursor: pointer; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05); transition: all 0.3s ease; }
.kpi-top-bar { position: absolute; top: 0; left: 0; right: 0; height: 4px; background: linear-gradient(90deg, #0B2044, #1E88E5, #4CAF50); transform: scaleX(1); }
.kpi-card:hover { transform: translateY(-5px); box-shadow: 0 12px 28px rgba(0, 0, 0, 0.15); }
.kpi-icon { width: 52px; height: 52px; border-radius: 14px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; transition: transform 0.3s ease; }
.kpi-card:hover .kpi-icon { transform: scale(1.05); }
.kpi-info { flex: 1; }
.kpi-value { font-size: 20px; font-weight: 800; color: #0B2044; }
.kpi-title { font-size: 10px; color: #888; }
.section-header { display: flex; align-items: center; gap: 10px; margin-bottom: 20px; }
.section-header h2 { color: #0B2044; font-size: 18px; margin: 0; }
.instruments-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; margin-bottom: 40px; }
.instrument-card { background: white; border-radius: 20px; padding: 18px; display: flex; gap: 14px; cursor: pointer; position: relative; transition: all 0.3s; }
.instrument-card.disabled-card { opacity: 0.6; cursor: not-allowed; }
.instrument-card:not(.disabled-card):hover { transform: translateY(-5px); box-shadow: 0 12px 28px rgba(0,0,0,0.15); }
.instrument-icon { width: 52px; height: 52px; border-radius: 14px; display: flex; align-items: center; justify-content: center; }
.instrument-info { flex: 1; }
.instrument-info h3 { color: #0B2044; font-size: 15px; margin-bottom: 4px; }
.instrument-info p { color: #888; font-size: 11px; }
.lock-overlay { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.6); border-radius: 50%; width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; color: white; }
.btn-primary { background: linear-gradient(135deg, #0B2044, #1E88E5); color: white; border: none; padding: 8px 14px; border-radius: 8px; font-size: 12px; font-weight: 600; cursor: pointer; display: inline-flex; align-items: center; justify-content: center; gap: 5px; transition: all 0.3s; }
.btn-primary:hover:not(:disabled) { transform: translateY(-2px); box-shadow: 0 6px 15px rgba(11, 32, 68, 0.3); }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.version-dialog-title { background: #0B2044; color: white; padding: 14px 20px; display: flex; align-items: center; font-size: 18px; }
.btn-close-dialog { background: transparent; border: none; color: white; cursor: pointer; padding: 6px; border-radius: 50%; transition: background 0.2s; font-size: 18px; }
.btn-close-dialog:hover { background: rgba(255,255,255,0.1); }
.version-dialog-body { padding: 12px 16px; display: flex; flex-direction: column; max-height: 70vh; }
.version-search-bar { display: flex; align-items: center; background: #f5f5f5; border-radius: 8px; padding: 5px 10px; margin-bottom: 12px; border: 1px solid #e0e0e0; transition: border-color 0.2s; flex-shrink: 0; }
.version-search-bar:focus-within { border-color: #0B2044; background: white; }
.version-search-input { flex: 1; border: none; background: transparent; outline: none; font-size: 13px; padding: 6px 0; }
.version-search-input::placeholder { color: #aaa; }
.version-list-container { flex: 1; overflow-y: auto; min-height: 0; max-height: 420px; padding-right: 4px; }
.version-list-container::-webkit-scrollbar { width: 6px; }
.version-list-container::-webkit-scrollbar-track { background: #f0f0f0; border-radius: 4px; }
.version-list-container::-webkit-scrollbar-thumb { background: #0B2044; border-radius: 4px; }
.empty-versions { text-align: center; padding: 30px 0; color: #999; }
.empty-versions p { margin-top: 8px; }
.version-list { display: flex; flex-direction: column; gap: 6px; padding: 2px 0; }
.version-entry { background: #f8f9ff; border-radius: 6px; padding: 8px 12px; border: 1px solid #e8ecf1; transition: all 0.2s; }
.version-entry.latest { border-color: #0B2044; background: #f0f4ff; }
.version-entry:hover { border-color: #0B2044; }
.version-entry-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 2px; }
.version-entry-time { font-size: 11px; font-weight: 600; color: #0B2044; }
.version-entry-badge { padding: 1px 10px; border-radius: 30px; font-size: 9px; font-weight: 600; color: white; letter-spacing: 0.2px; text-transform: uppercase; }
.badge-created { background: #2E7D32; }
.badge-uploaded { background: #0B2044; }
.badge-cleaned { background: #FF9800; }
.badge-calculated { background: #1E88E5; }
.badge-renamed { background: #607D8B; }
.badge-updated { background: #0B2044; }
.badge-restored { background: #C62828; }
.badge-saved { background: #0B2044; }
.version-entry-details { font-size: 11px; color: #555; }
.version-entry-row { display: flex; align-items: baseline; margin-bottom: 1px; }
.version-entry-row .label { width: 68px; font-weight: 600; color: #0B2044; font-size: 10px; flex-shrink: 0; }
.version-entry-row .value { color: #333; font-size: 11px; }
.description-row .description-text { font-weight: 500; color: #0B2044; }
.fields-tags { display: flex; flex-wrap: wrap; gap: 3px; }
.field-tag { background: #e8ecf1; padding: 0 8px; border-radius: 20px; font-size: 9px; color: #0B2044; line-height: 1.6; }
.version-entry-actions { margin-top: 4px; display: flex; justify-content: flex-end; }
.btn-restore { background: #0B2044; color: white; border: none; padding: 1px 12px; border-radius: 30px; font-size: 10px; cursor: pointer; transition: background 0.2s; }
.btn-restore:hover { background: #1a3a6e; }
.version-dialog-actions { padding: 6px 16px 10px; border-top: 1px solid #e8ecf1; flex-shrink: 0; }
.btn-secondary { background: white; color: #0B2044; border: 2px solid #0B2044; padding: 4px 16px; border-radius: 30px; font-size: 12px; font-weight: 600; cursor: pointer; transition: all 0.2s; }
.btn-secondary:hover { background: #0B2044; color: white; }
@media (max-width: 900px) {
  .dashboard { padding: 20px; }
  .session-management-row { grid-template-columns: 1fr; gap: 20px; }
  .kpis-row, .instruments-row { grid-template-columns: 1fr; }
  .session-row-stats { display: none; }
  .row-delete-btn { opacity: 1; }
  .version-list-container { max-height: 300px; }
}
</style>