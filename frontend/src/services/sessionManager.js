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
      const metadata = stored ? JSON.parse(stored) : []
      this.sessions = metadata.map(m => ({
        id: m.id,
        name: m.name,
        status: m.status || 'in-progress',
        date: m.date,
        created_at: m.created_at || m.date,
        instrument_count: m.instrument_count || 0,
        version_count: m.version_count || 0,
        total_value: m.total_value || 0,
        instrumentWorkflow: null,
        versions: null
      }))
    } catch {
      this.sessions = []
    }
    const active = localStorage.getItem(ACTIVE_KEY)
    this.activeSessionId = active || null
  }

  saveCache() {
    const metadata = this.sessions.map(s => ({
      id: s.id,
      name: s.name,
      status: s.status,
      date: s.date,
      created_at: s.created_at || s.date,
      instrument_count: s.instrument_count || 0,
      version_count: s.version_count || 0,
      total_value: s.total_value || 0
    }))
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(metadata))
    } catch (e) {
      console.error('LocalStorage quota exceeded, clearing old sessions:', e)
      const recent = metadata.slice(0, 20)
      localStorage.setItem(STORAGE_KEY, JSON.stringify(recent))
    }
    if (this.activeSessionId) {
      localStorage.setItem(ACTIVE_KEY, this.activeSessionId)
    } else {
      localStorage.removeItem(ACTIVE_KEY)
    }
  }

  // ---- API calls ----

  async getAllSessions() {
    try {
      const data = await api.sessionsAPI.list()
      const backendSessions = Array.isArray(data) ? data : []
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

  async getSession(id) {
    let session = this.sessions.find(s => s.id === id)
    if (session) return session

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
    this.sessions.unshift(newSession)
    this.saveCache()
    this.setActiveSession(newSession)

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

  async updateSession(id, updates) {
    const idx = this.sessions.findIndex(s => s.id === id)
    if (idx === -1) return null

    const existingVersions = this.sessions[idx].versions || []
    this.sessions[idx] = { ...this.sessions[idx], ...updates, timestamp: Date.now() }
    if (!updates.versions) {
      this.sessions[idx].versions = existingVersions
    }
    this.saveCache()

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

  async renameSession(id, newName) {
    return this.updateSession(id, { name: newName.trim() })
  }

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

  // ---- Workflow management ----

  async saveInstrumentWorkflow(sessionId, instrumentKey, workflow) {
    // First, ensure we have the latest session
    const session = await this.getSession(sessionId)
    if (!session) return

    // Update the workflow
    const iw = { ...(session.instrumentWorkflow || {}), [instrumentKey]: workflow }
    // Compute the instrument count from the workflows
    const instrumentCount = this.countSessionInstrumentsFromWorkflows(iw)

    // Update the session with new workflow and count
    await this.updateSession(sessionId, {
      instrumentWorkflow: iw,
      instrument_count: instrumentCount,
    })

    // Also ensure the backend gets the updated instrument_count
    try {
      await api.sessionsAPI.save({
        id: sessionId,
        session_id: sessionId,
        name: session.name,
        status: session.status,
        payload: session,
        instrument_workflows: iw,
        versions: session.versions || [],
        instrument_count: instrumentCount,
      })
    } catch (err) {
      console.error('Failed to sync workflow to backend:', err)
    }

    // After saving, refresh the session from backend to ensure consistency
    await this.getSession(sessionId)
  }

  async getInstrumentWorkflow(sessionId, instrumentKey) {
    const session = await this.getSession(sessionId)
    return session?.instrumentWorkflow?.[instrumentKey] || null
  }

  // ---- Version management ----

  async addVersion(sessionId, version) {
    const session = await this.getSession(sessionId)
    if (!session) return null

    const versions = session.versions || []
    const versionNumber = versions.length + 1
    const record = {
      versionNumber,
      timestamp: Date.now(),
      ...version,
    }
    versions.unshift(record)
    await this.updateSession(sessionId, { versions })

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
        null
      )
      await this.getSession(sessionId)
    } catch (err) {
      console.error('Failed to save version to backend:', err)
    }
    return record
  }

  // ---- Helpers ----

  countSessionInstrumentsFromWorkflows(workflows) {
    if (!workflows || typeof workflows !== 'object') return 0
    const keys = ['money-market', 'bonds', 'tbills']
    let count = 0
    for (const key of keys) {
      const wf = workflows[key]
      if (wf && (
        (wf.cleanedData && wf.cleanedData.length > 0) ||
        (wf.rawData && wf.rawData.length > 0) ||
        (wf.data && wf.data.length > 0) ||
        (wf.calculations && parseFloat(wf.calculations.totalValue) > 0) ||
        (wf.calculations && Object.keys(wf.calculations).length > 0)
      )) {
        count++
      }
    }
    return Math.min(count, 3)
  }

  countSessionInstruments(sessionId) {
    const session = this.sessions.find(s => s.id === sessionId)
    if (!session) return 0
    if (session.instrument_count !== undefined) {
      return session.instrument_count
    }
    return this.countSessionInstrumentsFromWorkflows(session.instrumentWorkflow || {})
  }

  clearAllSessions() {
    this.sessions = []
    localStorage.setItem(STORAGE_KEY, JSON.stringify([]))
    localStorage.removeItem(ACTIVE_KEY)
    this.activeSessionId = null
  }

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

export default new SessionManager()