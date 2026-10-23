// [MODIFIED] workflowProgress.js
/** State-driven workflow step completion – steps marked completed only after successful completion,
    preserved when navigating backwards, synchronized across pages, advances only after success,
    reverts only on explicit reset or new session. */

const WORKFLOW_PROGRESS_KEY = 'dura_workflow_progress'

import sessionManager from '@/services/sessionManager.js'

// FIX: sessionManager.getSession() is async and returns a Promise, not a
// session object. The original code did `const s = sessionManager.getSession(id);
// if (s && s.workflow_progress) return s.workflow_progress` — s was always a
// Promise, so the branch never fired and session-backed progress was silently
// lost. Now we read the synchronous in-memory cache (`sessionManager.sessions`)
// which is populated on boot from localStorage.
function getSessionProgressSync(sessionId) {
  if (!sessionId) return null
  try {
    const cached = sessionManager.sessions?.find(s => s.id === sessionId)
    if (cached && cached.workflow_progress) return cached.workflow_progress
  } catch {
    // ignore
  }
  return null
}

function getWorkflowProgress(sessionId) {
  if (!sessionId) return {}
  try {
    const sessionProgress = getSessionProgressSync(sessionId)
    if (sessionProgress) return sessionProgress

    const stored = localStorage.getItem(WORKFLOW_PROGRESS_KEY)
    const all = stored ? JSON.parse(stored) : {}
    return all[sessionId] || {}
  } catch {
    return {}
  }
}

function saveWorkflowProgress(sessionId, progress) {
  if (!sessionId) return

  // Local write first (synchronous, always succeeds or logs)
  try {
    const stored = localStorage.getItem(WORKFLOW_PROGRESS_KEY)
    const all = stored ? JSON.parse(stored) : {}
    all[sessionId] = progress
    localStorage.setItem(WORKFLOW_PROGRESS_KEY, JSON.stringify(all))
  } catch (e) {
    console.error('Failed to save workflow progress (local):', e)
  }

  // Fire-and-forget backend sync
  try {
    const serverProgress = getSessionProgressSync(sessionId) || {}
    const merged = { ...serverProgress, ...progress }
    sessionManager.updateSession(sessionId, { workflow_progress: merged })
      .catch(err => console.warn('Workflow backend sync failed:', err))
  } catch (e) {
    // ignore
  }
}

function clearWorkflowProgress(sessionId) {
  if (!sessionId) return

  try {
    const stored = localStorage.getItem(WORKFLOW_PROGRESS_KEY)
    const all = stored ? JSON.parse(stored) : {}
    delete all[sessionId]
    localStorage.setItem(WORKFLOW_PROGRESS_KEY, JSON.stringify(all))
  } catch (e) {
    console.error('Failed to clear workflow progress (local):', e)
  }

  try {
    sessionManager.updateSession(sessionId, { workflow_progress: {} })
      .catch(err => console.warn('Workflow backend clear failed:', err))
  } catch (e) {
    // ignore
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