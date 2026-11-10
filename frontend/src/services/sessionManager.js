// services/sessionManager.js
import api from './api.js'

function getStorageKeys() {
  let userId = 'anonymous'
  try {
    const user = JSON.parse(localStorage.getItem('user') || 'null')
    if (user?.id != null) userId = String(user.id)
  } catch {
    localStorage.removeItem('user')
  }
  return {
    sessions: `dura_sessions_${userId}`,
    activeSession: `dura_active_session_id_${userId}`
  }
}

class SessionManager {
  constructor() {
    this.sessions = []
    this.activeSessionId = null
    this.cacheOwnerKey = null
    this.loadCache()
  }

  // ─────────────────────────────────────────────────────────────
  // CACHE (localStorage)
  // FIX #1: instrumentWorkflow and versions are now persisted and
  // restored. Previously they were stripped by saveCache and reset
  // to null on load, which caused silent data loss on reload
  // (saving one instrument's workflow wiped the others).
  // ─────────────────────────────────────────────────────────────
  loadCache() {
    const { sessions, activeSession } = getStorageKeys()
    this.cacheOwnerKey = sessions
    try {
      const stored = localStorage.getItem(sessions)
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
        instrumentWorkflow: m.instrumentWorkflow || {},
        versions: m.versions || [],
        worksheets: m.worksheets || {},
        workbookName: m.workbookName || null
      }))
    } catch {
      this.sessions = []
    }
    const active = localStorage.getItem(activeSession)
    this.activeSessionId = active || null
  }

  syncCacheOwner() {
    if (getStorageKeys().sessions !== this.cacheOwnerKey) this.loadCache()
  }

  saveCache() {
    const { sessions: storageKey, activeSession } = getStorageKeys()
    const metadata = this.sessions.map(s => ({
      id: s.id,
      name: s.name,
      status: s.status,
      date: s.date,
      created_at: s.created_at || s.date,
      instrument_count: s.instrument_count || 0,
      version_count: s.version_count || 0,
      total_value: s.total_value || 0,
      worksheets: s.worksheets || {},
      workbookName: s.workbookName || null,
      instrumentWorkflow: s.instrumentWorkflow || {},
      versions: s.versions || []
    }))
    // Disabled to prevent LocalStorage quota errors
    // try {
    //   localStorage.setItem(storageKey, JSON.stringify(metadata))
    // } catch (e) {
    //   console.error('LocalStorage quota exceeded, clearing old sessions:', e)
    //   const recent = metadata.slice(0, 20)
    //   localStorage.setItem(storageKey, JSON.stringify(recent))
    // }
    // if (this.activeSessionId) {
    //   localStorage.setItem(activeSession, this.activeSessionId)
    // } else {
    //   localStorage.removeItem(activeSession)
    // }
  }

  // ─────────────────────────────────────────────────────────────
  // READ
  // ─────────────────────────────────────────────────────────────
  async getAllSessions() {
    this.syncCacheOwner()
    const cached = Array.isArray(this.sessions) ? [...this.sessions] : []
    try {
      const response = await api.sessionsAPI.list()
      if (!response?.success) {
        throw new Error(response?.message || 'Session list was not loaded from the server')
      }
      const raw = Array.isArray(response.data) ? response.data
        : Array.isArray(response.sessions) ? response.sessions : []
      const backendSessions = raw.map(bs => ({
        ...bs,
        id: String(bs.id || bs.session_id || ''),
        name: bs.name,
        status: bs.status || 'in-progress',
        date: bs.date || bs.created_at,
        created_at: bs.created_at || bs.date,
        instrument_count: bs.instrument_count || 0,
        version_count: bs.version_count || 0,
        total_value: bs.total_value || 0
      })).filter(s => s.id)

      // The backend list is authoritative: sessions absent from it (e.g.
      // deleted server-side) must not be resurrected from the local cache.
      // List failures are handled by the catch fallback below.
      this.sessions = backendSessions
      this.saveCache()
      return this.sessions
    } catch (err) {
      console.error('Failed to fetch sessions from backend:', err)
      // Do not wipe the dashboard: fall back to the local cache.
      this.sessions = cached
      return this.sessions
    }
  }

  async getSession(id) {
    this.syncCacheOwner()
    try {
      const response = await api.sessionsAPI.get(id)
      if (!response?.success) {
        throw new Error(response?.message || 'Session was not loaded from the server')
      }
      const data = response.data || response.session || null
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
          instrumentWorkflow: data.instrument_workflows || data.instrument_workflow || {},
          versions: data.versions || [],
          worksheets: data.worksheets || {},
          workbookName: data.workbookName || null
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
      this.sessions = this.sessions.filter(session => session.id !== id)
      this.saveCache()
      return null
    } catch (err) {
      console.error('Failed to fetch session from backend:', err)
      throw err
    }
  }

  // ─────────────────────────────────────────────────────────────
  // ACTIVE SESSION
  // ─────────────────────────────────────────────────────────────
  setActiveSession(session) {
    this.syncCacheOwner()
    if (!session) {
      this.activeSessionId = null
      localStorage.removeItem(getStorageKeys().activeSession)
      return
    }
    this.activeSessionId = session.id
    localStorage.setItem(getStorageKeys().activeSession, session.id)
  }

  getActiveSession() {
    this.syncCacheOwner()
    if (!this.activeSessionId) return null
    return this.sessions.find(s => s.id === this.activeSessionId) || null
  }

  getActiveSessionId() {
    this.syncCacheOwner()
    return this.activeSessionId
  }

  // ─────────────────────────────────────────────────────────────
  // CREATE / UPDATE
  // ─────────────────────────────────────────────────────────────
  async createSession(nameOverride = '') {
    this.syncCacheOwner()
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
      worksheets: {},
      workbookName: null
    }
    try {
      const response = await api.sessionsAPI.save({
        id: newSession.id,
        session_id: newSession.id,
        name: newSession.name,
        status: newSession.status,
        payload: newSession,
        instrument_workflows: {},
        versions: [],
        worksheets: {},
        workbookName: null
      })
      if (!response?.success) {
        throw new Error(response?.message || 'Session save was not confirmed by the server')
      }
    } catch (err) {
      throw new Error(`Failed to create session: ${err.message || 'Database save failed'}`)
    }
    this.sessions.unshift(newSession)
    this.saveCache()
    this.setActiveSession(newSession)
    return newSession
  }

  async updateSession(id, updates) {
    this.syncCacheOwner()
    let idx = this.sessions.findIndex(s => s.id === id)
    const current = idx === -1 ? await this.getSession(id, true) : this.sessions[idx]
    if (!current) throw new Error('Cannot update session: session was not found')
    idx = this.sessions.findIndex(s => s.id === id)
    const updatedSession = {
      ...current,
      ...updates,
      timestamp: Date.now(),
      versions: updates.versions || current.versions || [],
      instrumentWorkflow: updates.instrumentWorkflow || current.instrumentWorkflow || {},
      worksheets: updates.worksheets || current.worksheets || {},
      workbookName: updates.workbookName || current.workbookName || null
    }

    try {
      const response = await api.sessionsAPI.save({
        id: updatedSession.id,
        session_id: updatedSession.id,
        name: updatedSession.name,
        status: updatedSession.status,
        payload: updatedSession,
        instrument_workflows: updatedSession.instrumentWorkflow,
        versions: updatedSession.versions,
        instrument_count: updatedSession.instrument_count || 0,
        version_count: updatedSession.version_count || 0,
        total_value: updatedSession.total_value || 0,
        worksheets: updatedSession.worksheets,
        workbookName: updatedSession.workbookName
      })
      if (!response?.success) {
        throw new Error(response?.message || 'Session update was not confirmed by the server')
      }
    } catch (err) {
      throw new Error(`Failed to save session: ${err.message || 'Database update failed'}`)
    }
    this.sessions[idx] = updatedSession
    this.saveCache()
    return updatedSession
  }

  async renameSession(id, newName) {
    return this.updateSession(id, { name: newName.trim() })
  }

  async deleteSession(id) {
    this.syncCacheOwner()
    try {
      const response = await api.sessionsAPI.delete(id)
      if (!response?.success) {
        throw new Error(response?.message || 'Session deletion was not confirmed by the server')
      }
    } catch (err) {
      throw new Error(`Failed to delete session: ${err.message || 'Database deletion failed'}`)
    }
    this.sessions = this.sessions.filter(s => s.id !== id)
    this.saveCache()
    // saveCache() does not write to localStorage, so purge the deleted id from
    // the stored array explicitly — otherwise loadCache() resurrects it.
    try {
      const { sessions: storageKey } = getStorageKeys()
      const stored = JSON.parse(localStorage.getItem(storageKey) || '[]')
      localStorage.setItem(
        storageKey,
        JSON.stringify(stored.filter(s => String(s?.id) !== String(id)))
      )
    } catch { /* ignore */ }
    if (this.activeSessionId === id) {
      this.activeSessionId = null
      localStorage.removeItem(getStorageKeys().activeSession)
    }
  }

  // ─────────────────────────────────────────────────────────────
  // INSTRUMENT WORKFLOW
  // FIX #2: removed the redundant second api.sessionsAPI.save call.
  // updateSession already performs the backend save with the correct
  // merged payload; the second call was both redundant and used a
  // stale pre-update session snapshot.
  // ─────────────────────────────────────────────────────────────
  async saveInstrumentWorkflow(sessionId, instrumentKey, workflow) {
    const session = await this.getSession(sessionId)
    if (!session) throw new Error('Cannot save workflow: session was not found')

    const iw = { ...(session.instrumentWorkflow || {}), [instrumentKey]: workflow }
    const instrumentCount = this.countSessionInstrumentsFromWorkflows(iw)

    await this.updateSession(sessionId, {
      instrumentWorkflow: iw,
      instrument_count: instrumentCount
    })

  }

  // ─────────────────────────────────────────────────────────────
  // WORKSHEETS
  // ─────────────────────────────────────────────────────────────
  async saveWorksheetData(sessionId, worksheetName, worksheetData) {
    const session = await this.getSession(sessionId)
    if (!session) throw new Error('Cannot save worksheet: session was not found')

    const worksheets = session.worksheets || {}
    worksheets[worksheetName] = {
      ...worksheetData,
      timestamp: Date.now(),
      status: 'saved'
    }

    await this.updateSession(sessionId, {
      worksheets,
      workbookName: worksheetData.workbookName || session.workbookName || 'Workbook'
    })

    console.log('Saved worksheet data:', worksheetName, 'to session:', sessionId)
  }

  async getWorksheetData(sessionId, worksheetName) {
    const session = await this.getSession(sessionId)
    if (!session || !session.worksheets) return null
    return session.worksheets[worksheetName] || null
  }

  async getAllWorksheets(sessionId) {
    const session = await this.getSession(sessionId)
    if (!session || !session.worksheets) return {}
    return session.worksheets
  }

  async getWorksheetStatus(sessionId, worksheetName) {
    const data = await this.getWorksheetData(sessionId, worksheetName)
    return data ? data.status : null
  }

  async getInstrumentWorkflow(sessionId, instrumentKey) {
    const session = await this.getSession(sessionId)
    return session?.instrumentWorkflow?.[instrumentKey] || null
  }

  // ─────────────────────────────────────────────────────────────
  // VERSIONS
  // ─────────────────────────────────────────────────────────────
  async addVersion(sessionId, version) {
    const session = await this.getSession(sessionId)
    if (!session) return null

    const versions = session.versions || []
    const versionNumber = versions.length + 1
    const record = {
      versionNumber,
      timestamp: Date.now(),
      ...version
    }
    const savedVersion = await api.versionAPI.create(
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
    if (!savedVersion?.success) {
      throw new Error(savedVersion?.message || 'Version save was not confirmed by the server')
    }
    record.versionNumber = savedVersion.version_number
    versions.unshift(record)
    await this.updateSession(sessionId, {
      versions,
      version_count: versions.length
    })
    return record
  }

  // ─────────────────────────────────────────────────────────────
  // COUNTS
  // FIX #3: derive instrument count from workflows first; fall back
  // to the stored counter only if workflows have no data. Previously
  // instrument_count (always defined, defaults to 0) short-circuited
  // the workflow scan, so the derived count was never used.
  // ─────────────────────────────────────────────────────────────
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
        (wf.instrumentSummary && wf.instrumentSummary.rows && wf.instrumentSummary.rows.length > 0)
      )) {
        count++
      }
    }
    return Math.min(count, 3)
  }

  countSessionInstruments(sessionId) {
    const session = this.sessions.find(s => s.id === sessionId)
    if (!session) return 0
    const derived = this.countSessionInstrumentsFromWorkflows(session.instrumentWorkflow || {})
    if (derived > 0) return derived
    return session.instrument_count || 0
  }

  // ─────────────────────────────────────────────────────────────
  // MISC
  // ─────────────────────────────────────────────────────────────
  clearAllSessions() {
    this.sessions = []
    localStorage.setItem(getStorageKeys().sessions, JSON.stringify([]))
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