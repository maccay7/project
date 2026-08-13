import api from './api.js'

const STORAGE_KEY = 'dura_sessions'
const ACTIVE_KEY = 'dura_active_session_id'

class SessionManager {
  constructor() {
    this.sessions = []
    this.activeSessionId = null
    this.loadCache()
  }

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
        versions: null,
        worksheets: m.worksheets || {},
        workbookName: m.workbookName || null
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
      total_value: s.total_value || 0,
      worksheets: s.worksheets || {},
      workbookName: s.workbookName || null
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

  async getSession(id, forceRefresh = false) {
    if (!forceRefresh) {
      const cached = this.sessions.find(s => s.id === id)
      if (cached) return cached
    }
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
    } catch (err) {
      console.error('Failed to fetch session from backend:', err)
    }
    return null
  }

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
    const existingWorkflows = this.sessions[idx].instrumentWorkflow || {}
    const existingWorksheets = this.sessions[idx].worksheets || {}
    const existingWorkbookName = this.sessions[idx].workbookName || null
    this.sessions[idx] = { ...this.sessions[idx], ...updates, timestamp: Date.now() }
    
    if (!updates.versions) {
      this.sessions[idx].versions = existingVersions
    }
    if (!updates.instrumentWorkflow) {
      this.sessions[idx].instrumentWorkflow = existingWorkflows
    }
    if (!updates.worksheets) {
      this.sessions[idx].worksheets = existingWorksheets
    }
    if (!updates.workbookName) {
      this.sessions[idx].workbookName = existingWorkbookName
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
        instrument_count: this.sessions[idx].instrument_count || 0,
        version_count: this.sessions[idx].version_count || 0,
        worksheets: this.sessions[idx].worksheets || {},
        workbookName: this.sessions[idx].workbookName || null
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

  async saveInstrumentWorkflow(sessionId, instrumentKey, workflow) {
    const session = await this.getSession(sessionId)
    if (!session) return

    const iw = { ...(session.instrumentWorkflow || {}), [instrumentKey]: workflow }
    const instrumentCount = this.countSessionInstrumentsFromWorkflows(iw)

    await this.updateSession(sessionId, {
      instrumentWorkflow: iw,
      instrument_count: instrumentCount,
    })

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
        version_count: session.version_count || 0,
      })
    } catch (err) {
      console.error('Failed to sync workflow to backend:', err)
    }

    await this.getSession(sessionId)
  }

  // NEW: Save worksheet data to session
  async saveWorksheetData(sessionId, worksheetName, worksheetData) {
    const session = await this.getSession(sessionId)
    if (!session) return

    // Initialize worksheets structure if not exists
    const worksheets = session.worksheets || {}
    
    // Save/update worksheet data
    worksheets[worksheetName] = {
      ...worksheetData,
      timestamp: Date.now(),
      status: 'saved'
    }

    // Update session
    await this.updateSession(sessionId, {
      worksheets,
      workbookName: worksheetData.workbookName || session.workbookName || 'Workbook'
    })

    console.log('Saved worksheet data:', worksheetName, 'to session:', sessionId)
  }

  // NEW: Get worksheet data from session
  async getWorksheetData(sessionId, worksheetName) {
    const session = await this.getSession(sessionId)
    if (!session || !session.worksheets) return null
    return session.worksheets[worksheetName] || null
  }

  // NEW: Get all worksheets from session
  async getAllWorksheets(sessionId) {
    const session = await this.getSession(sessionId)
    if (!session || !session.worksheets) return {}
    return session.worksheets
  }

  // NEW: Get worksheet status
  async getWorksheetStatus(sessionId, worksheetName) {
    const data = await this.getWorksheetData(sessionId, worksheetName)
    return data ? data.status : null
  }

  async getInstrumentWorkflow(sessionId, instrumentKey) {
    const session = await this.getSession(sessionId)
    return session?.instrumentWorkflow?.[instrumentKey] || null
  }

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
    const newVersionCount = versions.length
    
    await this.updateSession(sessionId, { 
      versions, 
      version_count: newVersionCount 
    })

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
      // Force refresh to get the latest version count from backend
      await this.getSession(sessionId, true)
    } catch (err) {
      console.error('Failed to save version to backend:', err)
    }
    return record
  }

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