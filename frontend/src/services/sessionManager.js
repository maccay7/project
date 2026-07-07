// src/services/sessionManager.js
// Full integration with MySQL via sessionsAPI and versionAPI

import api from './api.js'

const STORAGE_KEY = 'dura_sessions'
const ACTIVE_KEY = 'dura_active_session_id'

class SessionManager {
  constructor() {
    this.sessions = []
    this.activeSessionId = null
    this.loadCache()
  }

  // ---- Local cache ----
  loadCache() {
    try {
      const stored = localStorage.getItem(STORAGE_KEY)
      this.sessions = stored ? JSON.parse(stored) : []
    } catch {
      this.sessions = []
    }
    const active = localStorage.getItem(ACTIVE_KEY)
    this.activeSessionId = active || null
  }

  saveCache() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(this.sessions))
    if (this.activeSessionId) {
      localStorage.setItem(ACTIVE_KEY, this.activeSessionId)
    } else {
      localStorage.removeItem(ACTIVE_KEY)
    }
  }

  // ---- API calls ----

  // Fetch all sessions from backend, merge with cache
  async getAllSessions() {
    try {
      const data = await api.sessionsAPI.list()
      // data is the array of sessions from backend
      const backendSessions = Array.isArray(data) ? data : []
      // Merge: override local with backend data (preserve any extra fields)
      const merged = [...this.sessions]
      for (const bs of backendSessions) {
        const idx = merged.findIndex(s => s.id === bs.id || s.session_id === bs.id)
        if (idx !== -1) {
          merged[idx] = { ...merged[idx], ...bs }
        } else {
          merged.push(bs)
        }
      }
      this.sessions = merged
      this.saveCache()
      return this.sessions
    } catch (err) {
      console.error('Failed to fetch sessions from backend:', err)
      return this.sessions
    }
  }

  // Get a single session – from cache or fetch from backend
  async getSession(id) {
    // Check cache first
    let session = this.sessions.find(s => s.id === id)
    if (session) return session

    // Fetch from backend
    try {
      const data = await api.sessionsAPI.get(id)
      if (data) {
        const mapped = {
          id: data.id || data.session_id,
          name: data.name,
          status: data.status || 'in-progress',
          date: data.created_at || data.date,
          created_at: data.created_at || data.date,
          instrument_count: data.instrument_count || 0,
          version_count: data.version_count || 0,
          total_value: data.total_value || 0,
          instrumentWorkflow: data.instrument_workflows || {},
          versions: data.versions || [],
        }
        const idx = this.sessions.findIndex(s => s.id === mapped.id)
        if (idx !== -1) {
          this.sessions[idx] = { ...this.sessions[idx], ...mapped }
        } else {
          this.sessions.push(mapped)
        }
        this.saveCache()
        return mapped
      }
    } catch (err) {
      console.error('Failed to fetch session from backend:', err)
    }
    return null
  }

  // ---- Active session ----
  setActiveSession(session) {
    if (!session) {
      this.activeSessionId = null
      localStorage.removeItem(ACTIVE_KEY)
      return
    }
    this.activeSessionId = session.id
    localStorage.setItem(ACTIVE_KEY, session.id)
  }

  getActiveSession() {
    if (!this.activeSessionId) return null
    return this.sessions.find(s => s.id === this.activeSessionId) || null
  }

  getActiveSessionId() {
    return this.activeSessionId
  }

  // ---- CRUD operations ----

  // Create a new session – persists to backend immediately
  async createSession(nameOverride = '') {
    const newSession = {
      id: Date.now().toString(),
      name: nameOverride || `Session ${new Date().toLocaleDateString()}`,
      date: new Date().toISOString(),
      status: 'in-progress',
      instrument_count: 0,
      version_count: 0,
      total_value: 0,
      instrumentWorkflow: {},
      versions: [],
    }
    // Add to cache
    this.sessions.unshift(newSession)
    this.saveCache()
    this.setActiveSession(newSession)

    // Persist to backend
    try {
      await api.sessionsAPI.save({
        id: newSession.id,
        session_id: newSession.id,
        name: newSession.name,
        status: newSession.status,
        payload: newSession,
        instrument_workflows: {},
        versions: [],
      })
    } catch (err) {
      console.error('Failed to create session on backend:', err)
    }
    return newSession
  }

  // Update session – persist to backend
  async updateSession(id, updates) {
    const idx = this.sessions.findIndex(s => s.id === id)
    if (idx === -1) return null

    // Preserve versions if not overwritten
    const existingVersions = this.sessions[idx].versions || []
    this.sessions[idx] = { ...this.sessions[idx], ...updates, timestamp: Date.now() }
    if (!updates.versions) {
      this.sessions[idx].versions = existingVersions
    }
    this.saveCache()

    // Persist to backend
    try {
      await api.sessionsAPI.save({
        id: this.sessions[idx].id,
        session_id: this.sessions[idx].id,
        name: this.sessions[idx].name,
        status: this.sessions[idx].status,
        payload: this.sessions[idx],
        instrument_workflows: this.sessions[idx].instrumentWorkflow || {},
        versions: this.sessions[idx].versions || [],
      })
    } catch (err) {
      console.error('Failed to update session on backend:', err)
    }
    return this.sessions[idx]
  }

  // Rename session
  async renameSession(id, newName) {
    return this.updateSession(id, { name: newName.trim() })
  }

  // Delete session – from cache and backend
  async deleteSession(id) {
    this.sessions = this.sessions.filter(s => s.id !== id)
    this.saveCache()
    if (this.activeSessionId === id) {
      this.activeSessionId = null
      localStorage.removeItem(ACTIVE_KEY)
    }
    try {
      await api.sessionsAPI.delete(id)
    } catch (err) {
      console.error('Failed to delete session from backend:', err)
    }
  }

  // ---- Workflow management (stored inside session payload) ----

  // Save instrument workflow – updates session and persists
  async saveInstrumentWorkflow(sessionId, instrumentKey, workflow) {
    const session = await this.getSession(sessionId)
    if (!session) return
    const iw = { ...(session.instrumentWorkflow || {}), [instrumentKey]: workflow }
    await this.updateSession(sessionId, { instrumentWorkflow: iw })
  }

  // Get instrument workflow – from session cache
  async getInstrumentWorkflow(sessionId, instrumentKey) {
    const session = await this.getSession(sessionId)
    return session?.instrumentWorkflow?.[instrumentKey] || null
  }

  // ---- Version management ----

  // Add a version record – calls versionAPI.create and refreshes session
  async addVersion(sessionId, version) {
    const session = await this.getSession(sessionId)
    if (!session) return null

    // Local update
    const versions = session.versions || []
    const versionNumber = versions.length + 1
    const record = {
      versionNumber,
      timestamp: Date.now(),
      ...version,
    }
    versions.unshift(record)
    await this.updateSession(sessionId, { versions })

    // Call backend version API to create a dedicated version record
    try {
      await api.versionAPI.create(
        sessionId,
        version.instrument || 'General',
        version.shortDescription || version.changeType || 'Saved',
        version.datasetSnapshot || null,
        version.mappingSnapshot || null,
        version.calculationSnapshot || null,
        version.portfolioSnapshot || null,
        version.reportSnapshot || null,
        null // userId
      )
      // Refresh the session to get updated version_count from backend
      await this.getSession(sessionId)
    } catch (err) {
      console.error('Failed to save version to backend:', err)
    }
    return record
  }

  // ---- Helpers ----

  // Count distinct instruments (max 3) – uses instrument_count from backend if available
  countSessionInstruments(sessionId) {
    const session = this.sessions.find(s => s.id === sessionId)
    if (!session) return 0
    if (session.instrument_count !== undefined) return session.instrument_count
    // Fallback: count from instrumentWorkflow
    const keys = ['money-market', 'bonds', 'tbills']
    let count = 0
    for (const key of keys) {
      const wf = session.instrumentWorkflow?.[key]
      const hasData = wf && (
        (wf.cleanedData?.length > 0) ||
        (wf.data?.length > 0) ||
        (wf.calculations && parseFloat(wf.calculations.totalValue) > 0)
      )
      if (hasData) count++
    }
    return Math.min(count, 3)
  }

  // Clear all sessions (local only)
  clearAllSessions() {
    this.sessions = []
    localStorage.setItem(STORAGE_KEY, JSON.stringify([]))
    localStorage.removeItem(ACTIVE_KEY)
    this.activeSessionId = null
  }

  // Get instrument name from key
  getInstrumentName(type) {
    const names = {
      treasury_bills: 'Treasury Bills',
      tbills: 'T-Bills',
      bonds: 'Bonds',
      money_market: 'Money Market',
      'money-market': 'Money Market'
    }
    return names[type] || type
  }
}

// Export a singleton instance
export default new SessionManager()