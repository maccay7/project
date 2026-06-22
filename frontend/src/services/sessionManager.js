// Session manager: localStorage + MySQL via /api/sessions/*
import api from './api.js'

const STORAGE_KEY = 'dura_sessions'
const ACTIVE_KEY = 'dura_active_session_id'

function parsePayload(p) {
  if (!p) return null
  if (typeof p === 'string') {
    try { return JSON.parse(p) } catch { return null }
  }
  return p
}

function buildInstrumentWorkflows(session) {
  return session?.instrumentWorkflow || session?.instrument_workflows || {}
}

export const sessionManager = {
  getAllSessions() {
    try {
      const stored = localStorage.getItem(STORAGE_KEY)
      const local = stored ? JSON.parse(stored) : []
      api.sessionsAPI.list().then(res => {
        if (res?.success && Array.isArray(res.data)) {
          const mapped = res.data.map(r => ({
            id: r.id || r.session_id,
            name: r.name,
            instrument: r.instrument,
            status: r.status,
            date: r.created_at || r.date,
            created_at: r.created_at || r.date,
            versions: r.versions || [],
            instrumentCount: r.instrumentCount || 0
          }))
          const merged = [...local]
          for (const ms of mapped) {
            const idx = merged.findIndex(s => s.id === ms.id)
            if (idx !== -1) {
              merged[idx] = {
                ...merged[idx],
                ...ms,
                versions: ms.versions?.length ? ms.versions : (merged[idx].versions || [])
              }
            } else {
              merged.push(ms)
            }
          }
          localStorage.setItem(STORAGE_KEY, JSON.stringify(merged))
        }
      }).catch(() => {})
      return local
    } catch {
      return []
    }
  },

  getSession(id) {
    return this.getAllSessions().find(s => s.id === id) || null
  },

  /** Load full session from database into localStorage */
  async loadSessionFromDb(sessionId) {
    const res = await api.sessionsAPI.get(sessionId)
    if (!res?.success) return null
    const body = res.data
    if (!body) return this.getSession(sessionId)

    let full = parsePayload(body.payload) || {}
    full.id = body.session_id || sessionId
    full.name = body.name || full.name
    full.status = body.status || full.status
    full.created_at = body.created_at
    if (body.versions?.length) full.versions = body.versions
    if (body.instrument_workflows && Object.keys(body.instrument_workflows).length) {
      full.instrumentWorkflow = body.instrument_workflows
    }

    const list = this.getAllSessions().filter(s => s.id !== full.id)
    list.unshift(full)
    localStorage.setItem(STORAGE_KEY, JSON.stringify(list))
    return full
  },

  setActiveSession(session) {
    if (!session) {
      localStorage.removeItem(ACTIVE_KEY)
      return
    }
    localStorage.setItem(ACTIVE_KEY, session.id)
  },

  getActiveSessionId() {
    try {
      const a = localStorage.getItem(ACTIVE_KEY)
      if (!a) return null
      if (a.startsWith('{')) return JSON.parse(a).id
      return a
    } catch {
      return null
    }
  },

  createSession(nameOverride = '') {
    const sessions = this.getAllSessions()
    const newSession = {
      id: Date.now().toString(),
      instrument: '',
      name: nameOverride || `Session ${new Date().toLocaleDateString()}`,
      date: new Date().toISOString(),
      instrumentWorkflow: {},
      status: 'in-progress',
      instrumentCount: 0,
      totalValue: 0,
      versions: []
    }
    sessions.unshift(newSession)
    localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions))
    this.persistToDb(newSession)
    this.setActiveSession(newSession)
    return newSession
  },

  renameSession(id, newName) {
    return this.updateSession(id, { name: newName.trim() })
  },

  updateSession(id, updates) {
    const sessions = this.getAllSessions()
    const index = sessions.findIndex(s => s.id === id)
    if (index === -1) return null
    sessions[index] = { ...sessions[index], ...updates, timestamp: Date.now() }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions))
    this.persistToDb(sessions[index])
    const active = this.getActiveSessionId()
    if (active === id && updates.name) {
      this.setActiveSession(sessions[index])
    }
    return sessions[index]
  },

  /** Save workflow for one instrument inside the session */
  saveInstrumentWorkflow(sessionId, instrumentKey, workflow) {
    const s = this.getSession(sessionId)
    if (!s) return
    const iw = { ...(s.instrumentWorkflow || {}), [instrumentKey]: workflow }
    this.updateSession(sessionId, { instrumentWorkflow: iw })
  },

  getInstrumentWorkflow(sessionId, instrumentKey) {
    const s = this.getSession(sessionId)
    return s?.instrumentWorkflow?.[instrumentKey] || null
  },

  /** Append a version record and persist to DB */
  addVersion(sessionId, version) {
    const s = this.getSession(sessionId)
    if (!s) return null
    const versions = s.versions || []
    const versionNumber = versions.length + 1
    const record = {
      versionNumber,
      timestamp: Date.now(),
      ...version
    }
    versions.unshift(record)
    if (versions.length > 50) versions.pop()
    return this.updateSession(sessionId, { versions })
  },

  updateSessionData(id, dataType, data, rows = 0) {
    const updates = { [dataType]: data, rows }
    if (dataType === 'data') updates.status = 'in-progress'
    return this.updateSession(id, updates)
  },

  persistToDb(session) {
    if (!session?.id) return
    api.sessionsAPI.save({
      id: session.id,
      session_id: session.id,
      name: session.name,
      instrument: session.instrument || '',
      payload: session,
      status: session.status || 'in-progress',
      versions: session.versions || [],
      instrument_workflows: buildInstrumentWorkflows(session)
    }).catch(() => {})
  },

  deleteSession(id) {
    const sessions = this.getAllSessions().filter(s => s.id !== id)
    localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions))
    if (this.getActiveSessionId() === id) localStorage.removeItem(ACTIVE_KEY)
    api.sessionsAPI.delete(id).catch(() => {})
  },

  clearAllSessions() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify([]))
    localStorage.removeItem(ACTIVE_KEY)
  },

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

export default sessionManager
