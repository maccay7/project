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

    <div class="dashboard-title"><h1>Dashboard</h1></div>

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
                  <div class="session-row-stats"><span>{{ session.instrumentCount || 0 }} instruments</span></div>
                  <div class="session-row-status" :class="session.status">{{ session.status === 'completed' ? '✓' : '⟳' }}</div>
                  <button class="version-btn" @click.stop="openVersionModal(session.id)">
                    <v-icon size="12">mdi-history</v-icon>
                    <span class="version-count">History ({{ session.versions?.length || 0 }})</span>
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
                  <span>Instruments: {{ activeSession.instrumentCount || 0 }}/3</span>
                </div>
                <!-- Save to Session button removed -->
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
                  <div class="version-entry-badge" :class="ver.changeTypeClass">{{ ver.changeType }}</div>
                </div>
                <div class="version-entry-details">
                  <div class="version-entry-row">
                    <span class="label">Instrument</span>
                    <span class="value" style="font-weight:600; color:#0B2044;">{{ ver.instrument || '—' }}</span>
                  </div>
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
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import sessionManager from '@/services/sessionManager.js'
import { useRouter } from 'vue-router'

const router = useRouter()

// Constants & Storage Keys
const STORAGE_KEY = 'dura_sessions'
const ACTIVE_KEY = 'dura_active_session_id'

// Reactive State
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

// Instruments Data
const instruments = [
  { id: 'money-market', name: 'Money Market', description: 'Short-term debt instruments', icon: 'mdi-chart-line', gradient: 'linear-gradient(135deg, #1E88E5, #0B2044)' },
  { id: 'bonds', name: 'Bonds', description: 'Fixed income securities', icon: 'mdi-chart-timeline', gradient: 'linear-gradient(135deg, #4CAF50, #2E7D32)' },
  { id: 'tbills', name: 'T-Bills', description: 'Treasury bills', icon: 'mdi-finance', gradient: 'linear-gradient(135deg, #FFC107, #FF9800)' }
]

// Computed
const validSessions = computed(() => {
  const valid = sessions.value.filter(s => s.name?.trim())
  valid.forEach(s => {
    if (s.versions) {
      s.versions.forEach(v => {
        if (v.name?.includes('Auto-save')) {
          v.name = v.name.replace(/Auto-save\s*/g, '').trim()
        }
        if (!v.displayName) v.displayName = v.name
      })
    }
  })
  return valid
})

const filteredSessions = computed(() => {
  const q = searchQuery.value.toLowerCase()
  return q ? validSessions.value.filter(s => s.name.toLowerCase().includes(q)) : validSessions.value
})

const filteredVersions = computed(() => {
  const versions = selectedSessionForVersions.value?.versions || []
  const q = versionSearchQuery.value.toLowerCase()
  if (!q) return versions
  return versions.filter(v =>
    [v.instrument, v.changeType, v.shortDescription, v.description, v.name, ...(v.fieldsChanged || [])]
      .some(f => f?.toLowerCase().includes(q))
  )
})

const totalSessions = computed(() => validSessions.value.length)
const completedSessions = computed(() => validSessions.value.filter(s => s.status === 'completed').length)
const inProgressSessions = computed(() => validSessions.value.filter(s => s.status === 'in-progress').length)

const kpiStats = computed(() => [
  { title: 'Active Session', value: activeSession.value?.name || 'No Session', icon: 'mdi-folder', gradient: 'linear-gradient(135deg, #0B2044, #1a3a6e)' },
  { title: 'Instruments Used', value: activeSession.value?.instrumentCount || '0', icon: 'mdi-chart-line', gradient: 'linear-gradient(135deg, #1E88E5, #0B2044)' },
  { title: 'Completion', value: `${Math.round((activeSession.value?.instrumentCount || 0) / 3 * 100)}%`, icon: 'mdi-database', gradient: 'linear-gradient(135deg, #4CAF50, #2E7D32)' }
])

// Helpers
const formatDate = d => d ? new Date(d).toLocaleString() : ''
const formatVersionTime = t => new Date(t).toLocaleString()

const stripEmojis = (text) => {
  if (!text) return text
  return text.replace(/[\u{1F000}-\u{1FFFF}]|[\u{2600}-\u{27BF}]|[\u{FE00}-\u{FEFF}]|[\u{1F600}-\u{1F64F}]|[\u{1F300}-\u{1F5FF}]|[\u{1F680}-\u{1F6FF}]|[\u{1F700}-\u{1F77F}]|[\u{1F780}-\u{1F7FF}]|[\u{1F800}-\u{1F8FF}]|[\u{1F900}-\u{1F9FF}]|[\u{1FA00}-\u{1FA6F}]|[\u{1FA70}-\u{1FAFF}]|[\u{1FB00}-\u{1FBFF}]|[\u{1FC00}-\u{1FCFF}]|[\u{1FD00}-\u{1FDFF}]|[\u{1FE00}-\u{1FEFF}]|[\u{1FF00}-\u{1FFFF}]/gu, '').trim()
}

// Local storage helpers
const saveSessions = () => localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions.value))
const loadSessions = () => {
  const stored = localStorage.getItem(STORAGE_KEY)
  if (stored) {
    try {
      sessions.value = JSON.parse(stored)
      sessions.value.forEach(s => { if (!s.versions) s.versions = [] })
    } catch (e) {}
  }
}
const saveActiveId = id => id ? localStorage.setItem(ACTIVE_KEY, id) : localStorage.removeItem(ACTIVE_KEY)
const loadActiveId = () => localStorage.getItem(ACTIVE_KEY)

// Detect instrument with data
const detectInstrument = (sessionId) => {
  const map = { 'money-market': 'Money Market', 'bonds': 'Bonds', 'tbills': 'T-Bills' }
  const found = []
  for (const [key, name] of Object.entries(map)) {
    const wf = sessionManager.getInstrumentWorkflow(sessionId, key)
    if (wf && ((wf.data?.length) || (wf.cleanedData?.length) || (wf.calculations && Object.keys(wf.calculations).length))) {
      found.push(name)
    }
  }
  const session = sessions.value.find(s => s.id === sessionId)
  if (session?.instrumentData) {
    for (const [key, name] of Object.entries(map)) {
      if (session.instrumentData[key]?.completed && !found.includes(name)) found.push(name)
    }
  }
  return found.length === 1 ? found[0] : found.length > 1 ? found.join(', ') : null
}

// Capture version
const captureVersion = (sessionId, options = {}) => {
  const session = sessions.value.find(s => s.id === sessionId)
  if (!session) return

  let { instrument, changeType = 'Updated', fieldsChanged = [], description, shortDescription, modifiedInstruments = [] } = options

  instrument = instrument || detectInstrument(sessionId) || (session.versions?.length ? session.versions[0].instrument : null) || 'Session'

  const shortDesc = shortDescription || description || changeType
  const defaultDescriptions = {
    'Uploaded': 'Uploaded data',
    'Cleaned': 'Cleaned data',
    'Calculated': 'Updated calculations',
    'Renamed': 'Renamed session',
    'Restored': 'Restored previous version',
    'Saved': 'Saved to session'
  }
  let finalShort = shortDesc === changeType ? (defaultDescriptions[changeType] || changeType) : shortDesc
  finalShort = stripEmojis(finalShort)
  if (description) description = stripEmojis(description)

  const workflows = {}
  for (const inst of ['money-market', 'bonds', 'tbills']) {
    const wf = sessionManager.getInstrumentWorkflow(sessionId, inst)
    if (wf) workflows[inst] = wf
  }

  const badgeMap = {
    'Uploaded': 'badge-uploaded', 'Cleaned': 'badge-cleaned',
    'Calculated': 'badge-calculated', 'Renamed': 'badge-renamed',
    'Updated': 'badge-updated', 'Restored': 'badge-restored',
    'Saved': 'badge-saved'
  }

  const version = {
    versionNumber: (session.versions?.length || 0) + 1,
    timestamp: Date.now(),
    instrument,
    changeType,
    changeTypeClass: badgeMap[changeType] || 'badge-updated',
    fieldsChanged: fieldsChanged || [],
    description: description || finalShort,
    shortDescription: finalShort,
    modifiedInstruments: modifiedInstruments.length ? modifiedInstruments : [instrument],
    workflows,
    name: finalShort
  }

  if (!session.versions) session.versions = []
  session.versions.unshift(version)
  if (session.versions.length > 50) session.versions.pop()

  saveSessions()
  sessionManager.updateSession(sessionId, { versions: session.versions })
}

// Version Modal
const openVersionModal = (sessionId) => {
  const session = sessions.value.find(s => s.id === sessionId)
  if (session) {
    selectedSessionForVersions.value = session
    versionSearchQuery.value = ''
    versionDialogVisible.value = true
  }
}

const restoreVersion = (sessionId, index) => {
  const session = sessions.value.find(s => s.id === sessionId)
  if (!session?.versions?.[index]) return
  const version = session.versions[index]
  if (!version.workflows) {
    alert('This version does not contain workflow data to restore.')
    return
  }
  for (const [inst, wf] of Object.entries(version.workflows)) {
    sessionManager.saveInstrumentWorkflow(sessionId, inst, wf)
  }
  const restoredInstrument = detectInstrument(sessionId) || version.instrument || 'Session'
  captureVersion(sessionId, {
    changeType: 'Restored',
    shortDescription: `Restored version from ${formatVersionTime(version.timestamp)}`,
    instrument: restoredInstrument
  })
  alert(`Restored version from ${formatVersionTime(version.timestamp)}`)
  if (activeSession.value?.id === sessionId) loadExistingSession(sessionId)
  versionDialogVisible.value = false
}

// Event listener for external updates
const onSessionUpdated = (event) => {
  const detail = event.detail || {}
  const { sessionId, skipCapture, explicitSave, ...options } = detail
  if (!sessionId) return
  if (skipCapture) {
    const updated = sessionManager.getSession(sessionId)
    if (updated) {
      const idx = sessions.value.findIndex(s => s.id === sessionId)
      if (idx !== -1) {
        sessions.value[idx] = { ...sessions.value[idx], ...updated, versions: updated.versions || sessions.value[idx].versions }
      } else {
        sessions.value.unshift(updated)
      }
      saveSessions()
    }
    return
  }
  // Only capture version if explicitly saving to session
  if (explicitSave) {
    captureVersion(sessionId, options)
  } else {
    // Just update session data without creating a version
    const updated = sessionManager.getSession(sessionId)
    if (updated) {
      const idx = sessions.value.findIndex(s => s.id === sessionId)
      if (idx !== -1) {
        sessions.value[idx] = { ...sessions.value[idx], ...updated, versions: updated.versions || sessions.value[idx].versions }
      } else {
        sessions.value.unshift(updated)
      }
      saveSessions()
    }
  }
}

// Session Actions
const createNewSession = () => {
  if (!newSessionName.value.trim()) return
  const created = sessionManager.createSession(newSessionName.value.trim())
  const newSession = {
    id: created.id,
    name: created.name,
    date: created.date || new Date().toISOString(),
    status: created.status || 'in-progress',
    instrumentCount: 0,
    totalValue: 0,
    versions: []
  }
  sessions.value.unshift(newSession)
  saveSessions()
  activeSession.value = newSession
  sessionManager.setActiveSession(activeSession.value)
  saveActiveId(activeSession.value.id)
  newSessionName.value = ''
}

const loadExistingSession = (sessionId) => {
  let session = sessions.value.find(s => s.id === sessionId)
  if (!session) {
    const full = sessionManager.getSession(sessionId)
    if (full) session = full
  }
  if (!session) return

  sessionManager.loadSessionFromDb(sessionId)
    .then(() => {
      const refreshed = sessionManager.getSession(sessionId)
      if (refreshed) {
        const idx = sessions.value.findIndex(s => s.id === sessionId)
        if (idx !== -1) {
          sessions.value[idx] = {
            ...sessions.value[idx],
            ...refreshed,
            versions: refreshed.versions?.length ? refreshed.versions : (sessions.value[idx]?.versions || [])
          }
          saveSessions()
          session = sessions.value[idx]
        }
      }
      activeSession.value = session
      sessionManager.setActiveSession(activeSession.value)
      saveActiveId(activeSession.value.id)
    })
    .catch(() => {
      activeSession.value = session
      sessionManager.setActiveSession(activeSession.value)
      saveActiveId(activeSession.value.id)
    })
}

const openRename = (session) => {
  const name = prompt('Rename session:', session.name)
  if (name?.trim()) {
    sessionManager.renameSession(session.id, name.trim())
    const idx = sessions.value.findIndex(s => s.id === session.id)
    if (idx !== -1) {
      sessions.value[idx].name = name.trim()
      saveSessions()
      captureVersion(session.id, { changeType: 'Renamed', shortDescription: `Renamed to "${name.trim()}"` })
    }
    if (activeSession.value?.id === session.id) activeSession.value = sessions.value[idx]
  }
}

const startRenameActive = () => {
  if (activeSession.value) {
    renameInput.value = activeSession.value.name
    renamingActive.value = true
  }
}

const saveRename = () => {
  if (!activeSession.value || !renameInput.value.trim()) return
  sessionManager.renameSession(activeSession.value.id, renameInput.value.trim())
  const idx = sessions.value.findIndex(s => s.id === activeSession.value.id)
  if (idx !== -1) {
    sessions.value[idx].name = renameInput.value.trim()
    saveSessions()
    captureVersion(activeSession.value.id, { changeType: 'Renamed', shortDescription: `Renamed to "${renameInput.value.trim()}"` })
    activeSession.value = sessions.value[idx]
  }
  renamingActive.value = false
}

const deleteSession = (sessionId) => {
  if (confirm('Are you sure you want to delete this session? This action cannot be undone.')) {
    sessionManager.deleteSession(sessionId)
    sessions.value = sessions.value.filter(s => s.id !== sessionId)
    saveSessions()
    if (activeSession.value?.id === sessionId) {
      activeSession.value = null
      saveActiveId(null)
    }
  }
}

// ***** FIXED NAVIGATION *****
const goToInstrument = (instrumentId) => {
  if (!activeSession.value) {
    alert('Please create or select a session first')
    return
  }
  sessionManager.setActiveSession(activeSession.value)
  router.push({ path: `/instrument/${instrumentId}`, query: { session: activeSession.value.id } })
}

const goToSettings = () => router.push('/settings')

const handleLogout = () => {
  localStorage.removeItem('auth_token')
  localStorage.removeItem('user')
  sessionStorage.clear()
  window.location.href = '/login'
}

// Cleanup sessions
const cleanupSessions = () => {
  let changed = false
  sessions.value = sessions.value.filter(s => {
    if (!s.name?.trim()) {
      changed = true
      return false
    }
    return true
  })
  sessions.value.forEach(s => {
    if (s.versions) {
      s.versions.forEach(v => {
        if (v.name?.includes('Auto-save')) {
          v.name = v.name.replace(/Auto-save\s*/g, '').trim()
          v.displayName = v.name
          changed = true
        }
        if (!v.displayName) v.displayName = v.name
      })
    }
  })
  if (changed) saveSessions()
}

// Lifecycle
onMounted(async () => {
  // Get logged-in user's full name from localStorage
  try {
    const user = JSON.parse(localStorage.getItem('user'))
    if (user) {
      const firstName = user.firstName || ''
      const lastName = user.lastName || ''
      currentUserFullName.value = (firstName + ' ' + lastName).trim()
    }
  } catch (e) {}

  loadSessions()
  cleanupSessions()

  // Merge sessions from sessionManager
  const managerSessions = sessionManager.getAllSessions()
  if (managerSessions.length) {
    const merged = [...sessions.value]
    for (const ms of managerSessions) {
      const idx = merged.findIndex(s => s.id === ms.id)
      if (idx !== -1) merged[idx] = { ...merged[idx], ...ms }
      else merged.push(ms)
    }
    sessions.value = merged
    cleanupSessions()
    saveSessions()
  }

  // Restore active session – ensure it is set
  let activeId = loadActiveId()
  if (activeId) {
    const session = sessions.value.find(s => s.id === activeId)
    if (session) {
      activeSession.value = session
      sessionManager.setActiveSession(activeSession.value)
    } else {
      const managerSession = sessionManager.getSession(activeId)
      if (managerSession) {
        activeSession.value = managerSession
        sessionManager.setActiveSession(activeSession.value)
        sessions.value.unshift(managerSession)
        cleanupSessions()
        saveSessions()
      } else {
        // If active ID is invalid, clear it and fallback to first session
        saveActiveId(null)
        activeId = null
      }
    }
  }

  // If still no active session, pick the first available session or null
  if (!activeSession.value && sessions.value.length > 0) {
    activeSession.value = sessions.value[0]
    sessionManager.setActiveSession(activeSession.value)
    saveActiveId(activeSession.value.id)
  } else if (!activeSession.value && sessions.value.length === 0) {
    // No sessions at all – keep null
  }

  window.addEventListener('session-updated', onSessionUpdated)
})

onBeforeUnmount(() => {
  window.removeEventListener('session-updated', onSessionUpdated)
})
</script>

<style scoped>
/* (All styles unchanged – keep your existing dashboard styles) */
.dashboard { min-height: 100vh; background: linear-gradient(135deg, #f5f7fa 0%, #e8ecf1 100%); padding: 20px 40px; }
.top-navbar { position: fixed; top: 0; left: 0; right: 0; height: 60px; background: white; display: flex; justify-content: space-between; align-items: center; padding: 0 30px; box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05); z-index: 1000; }
.logo-placeholder { display: flex; align-items: center; }
.navbar-logo { width: 180px; max-height: 48px; height: auto; object-fit: contain; border-radius: 8px; }
.nav-actions { display: flex; gap: 15px; align-items: center; }
.nav-icon-btn { background: transparent; border: none; cursor: pointer; padding: 8px; border-radius: 8px; transition: all 0.2s; color: #666; display: flex; align-items: center; justify-content: center; }
.nav-icon-btn:hover { background: #f0f0f0; color: #0B2044; }
.dashboard-title { margin-top: 80px; margin-bottom: 25px; }
.dashboard-title h1 { color: #0B2044; font-size: 28px; font-weight: 700; }
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