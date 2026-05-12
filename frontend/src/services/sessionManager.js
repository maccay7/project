// utils/sessionManager.js

const STORAGE_KEY = 'duracapital_sessions'

export const sessionManager = {
  // Get all sessions
  getAllSessions() {
    try {
      const stored = localStorage.getItem(STORAGE_KEY)
      return stored ? JSON.parse(stored) : []
    } catch (err) {
      console.error('Error loading sessions:', err)
      return []
    }
  },

  // Get single session by ID
  getSession(id) {
    const sessions = this.getAllSessions()
    return sessions.find(s => s.id === id)
  },

  // Create new session
  createSession(instrumentType) {
    const sessions = this.getAllSessions()
    const newSession = {
      id: Date.now().toString(),
      instrument: instrumentType,
      name: `${this.getInstrumentName(instrumentType)} - ${new Date().toLocaleDateString()}`,
      date: new Date().toISOString(),
      data: null,
      cleanedData: null,
      calculations: null,
      rows: 0,
      status: 'upload', // upload, cleaned, calculated, completed
      timestamp: Date.now()
    }
    sessions.unshift(newSession)
    localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions))
    return newSession
  },

  // Update existing session
  updateSession(id, updates) {
    const sessions = this.getAllSessions()
    const index = sessions.findIndex(s => s.id === id)
    if (index !== -1) {
      sessions[index] = { ...sessions[index], ...updates, timestamp: Date.now() }
      localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions))
      return sessions[index]
    }
    return null
  },

  // Update session data (uploaded file)
  updateSessionData(id, dataType, data, rows = 0) {
    const updates = { [dataType]: data, rows: rows }
    if (dataType === 'data') updates.status = 'upload'
    if (dataType === 'cleanedData') updates.status = 'cleaned'
    if (dataType === 'calculations') updates.status = 'calculated'
    return this.updateSession(id, updates)
  },

  // Delete session
  deleteSession(id) {
    const sessions = this.getAllSessions().filter(s => s.id !== id)
    localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions))
  },

  // Clear all sessions
  clearAllSessions() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify([]))
  },

  // Get sessions by instrument
  getSessionsByInstrument(instrumentType) {
    return this.getAllSessions().filter(s => s.instrument === instrumentType)
  },

  // Get instrument name
  getInstrumentName(type) {
    const names = {
      treasury_bills: 'Treasury Bills',
      bonds: 'Bonds',
      money_market: 'Money Market'
    }
    return names[type] || type
  },

  // Get summary totals across all instruments
  getSummaryTotals() {
    const sessions = this.getAllSessions()
    const totals = {
      treasury_bills: { count: 0, totalPrincipal: 0, totalInterest: 0, avgYield: 0 },
      bonds: { count: 0, totalPrincipal: 0, totalInterest: 0, avgYield: 0 },
      money_market: { count: 0, totalPrincipal: 0, totalInterest: 0, avgYield: 0 },
      grandTotal: { totalPrincipal: 0, totalInterest: 0, sessionCount: 0 }
    }
    
    let yieldSum = 0
    let yieldCount = 0
    
    sessions.forEach(session => {
      if (session.calculations && session.calculations.length) {
        const calc = session.calculations[0]
        const instrument = session.instrument
        
        if (totals[instrument]) {
          totals[instrument].count++
          totals[instrument].totalPrincipal += calc.principal || 0
          totals[instrument].totalInterest += calc.interest_earned || 0
          if (calc.annual_yield || calc.yield) {
            totals[instrument].avgYield += calc.annual_yield || calc.yield || 0
          }
        }
        
        totals.grandTotal.totalPrincipal += calc.principal || 0
        totals.grandTotal.totalInterest += calc.interest_earned || 0
        totals.grandTotal.sessionCount++
        
        yieldSum += calc.annual_yield || calc.yield || 0
        yieldCount++
      }
    })
    
    // Calculate averages
    if (yieldCount > 0) {
      totals.grandTotal.avgYield = yieldSum / yieldCount
    }
    
    return totals
  }
}

export default sessionManager