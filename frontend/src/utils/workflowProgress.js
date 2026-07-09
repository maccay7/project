/** State-driven workflow step completion – steps marked completed only after successful completion,
    preserved when navigating backwards, synchronized across pages, advances only after success,
    reverts only on explicit reset or new session. */

const WORKFLOW_PROGRESS_KEY = 'dura_workflow_progress'

import sessionManager from '@/services/sessionManager.js'

function getWorkflowProgress(sessionId) {
  if (!sessionId) return {}
  try {
    try {
      const s = sessionManager.getSession(sessionId)
      if (s && s.workflow_progress) return s.workflow_progress
    } catch (e) {
      // ignore and fallback to localStorage
    }

    const stored = localStorage.getItem(WORKFLOW_PROGRESS_KEY)
    const all = stored ? JSON.parse(stored) : {}
    return all[sessionId] || {}
  } catch {
    return {}
  }
}

function saveWorkflowProgress(sessionId, progress) {
  if (!sessionId) return
  try {
    const stored = localStorage.getItem(WORKFLOW_PROGRESS_KEY)
    const all = stored ? JSON.parse(stored) : {}
    all[sessionId] = progress
    localStorage.setItem(WORKFLOW_PROGRESS_KEY, JSON.stringify(all))

    try {
      const s = sessionManager.getSession(sessionId) || {}
      const serverProgress = s.workflow_progress || {}
      const merged = { ...serverProgress, ...progress }
      sessionManager.updateSession(sessionId, { workflow_progress: merged })
    } catch (e) {
      // ignore backend failures — local copy remains
    }
  } catch (e) {
    console.error('Failed to save workflow progress:', e)
  }
}

function clearWorkflowProgress(sessionId) {
  if (!sessionId) return
  try {
    const stored = localStorage.getItem(WORKFLOW_PROGRESS_KEY)
    const all = stored ? JSON.parse(stored) : {}
    delete all[sessionId]
    localStorage.setItem(WORKFLOW_PROGRESS_KEY, JSON.stringify(all))

    try {
      sessionManager.updateSession(sessionId, { workflow_progress: {} })
    } catch (e) {
      // ignore
    }
  } catch (e) {
    console.error('Failed to clear workflow progress:', e)
  }
}

export function markStepCompleted(sessionId, stepTab) {
  const progress = getWorkflowProgress(sessionId)
  progress[stepTab] = { completed: true, timestamp: Date.now() }
  saveWorkflowProgress(sessionId, progress)
}

export function isStepPersistedCompleted(sessionId, stepTab) {
  const progress = getWorkflowProgress(sessionId)
  return progress[stepTab]?.completed || false
}

export function checkStepCriteria(tab, state) {
  const {
    rawDataLength,
    mappingApplied,
    allColumnsMapped,
    cleanedDataLength,
    calculations,
    chartData,
    reportsSaved
  } = state

  switch (tab) {
    case 'upload':
      return rawDataLength > 0 && mappingApplied && allColumnsMapped
    case 'cleaning':
      return cleanedDataLength > 0
    case 'calculations':
      return !!(calculations && calculations.totalValue)
    case 'visualizations':
      return !!(chartData?.datasets && chartData.datasets.length > 0)
    case 'summary':
      return !!(calculations && calculations.totalValue)
    case 'reports':
      return !!reportsSaved || !!(calculations && calculations.totalValue)
    default:
      return false
  }
}

export function isStepCompleted(tab, steps, state, sessionId) {
  const idx = steps.findIndex(s => s.tab === tab)
  if (idx === -1) return false
  
  const persistedCompleted = isStepPersistedCompleted(sessionId, tab)
  const criteriaMet = checkStepCriteria(tab, state)
  
  if (persistedCompleted && criteriaMet) {
    return true
  }
  
  for (let i = 0; i < idx; i++) {
    const priorTab = steps[i].tab
    const priorPersisted = isStepPersistedCompleted(sessionId, priorTab)
    const priorCriteria = checkStepCriteria(priorTab, state)
    if (!(priorPersisted && priorCriteria)) {
      return false
    }
  }
  
  return criteriaMet
}

export function farthestAllowedIndex(steps, state, sessionId) {
  for (let i = 0; i < steps.length; i++) {
    const tab = steps[i].tab
    const persistedCompleted = isStepPersistedCompleted(sessionId, tab)
    const criteriaMet = checkStepCriteria(tab, state)
    
    if (persistedCompleted && criteriaMet) {
      continue
    }
    
    if (!criteriaMet) return i
  }
  return steps.length - 1
}

export function resetWorkflowProgress(sessionId) {
  clearWorkflowProgress(sessionId)
}

export function autoMarkStepIfCompleted(tab, state, sessionId) {
  if (checkStepCriteria(tab, state) && !isStepPersistedCompleted(sessionId, tab)) {
    markStepCompleted(sessionId, tab)
  }
}