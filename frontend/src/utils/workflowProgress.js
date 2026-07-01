/** State-driven workflow step completion – steps marked completed only after successful completion,
    preserved when navigating backwards, synchronized across pages, advances only after success,
    reverts only on explicit reset or new session. */

const WORKFLOW_PROGRESS_KEY = 'dura_workflow_progress'

import sessionManager from '@/services/sessionManager.js'

// Get persisted workflow progress for a session
function getWorkflowProgress(sessionId) {
  if (!sessionId) return {}
  try {
    // Prefer server-backed session data when available
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

// Save workflow progress for a session
function saveWorkflowProgress(sessionId, progress) {
  if (!sessionId) return
  try {
    // Persist locally for quick reads
    const stored = localStorage.getItem(WORKFLOW_PROGRESS_KEY)
    const all = stored ? JSON.parse(stored) : {}
    all[sessionId] = progress
    localStorage.setItem(WORKFLOW_PROGRESS_KEY, JSON.stringify(all))

    // Also persist to backend via sessionManager (will call API)
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

// Clear workflow progress for a session (on reset or new session)
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

// Mark a step as completed
export function markStepCompleted(sessionId, stepTab) {
  const progress = getWorkflowProgress(sessionId)
  progress[stepTab] = { completed: true, timestamp: Date.now() }
  saveWorkflowProgress(sessionId, progress)
}

// Check if a step is marked as completed (persisted state)
export function isStepPersistedCompleted(sessionId, stepTab) {
  const progress = getWorkflowProgress(sessionId)
  return progress[stepTab]?.completed || false
}

// Check step criteria (actual state check)
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

// State-driven step completion check - combines persisted state with current criteria
export function isStepCompleted(tab, steps, state, sessionId) {
  const idx = steps.findIndex(s => s.tab === tab)
  if (idx === -1) return false
  
  // Check if step is persisted as completed
  const persistedCompleted = isStepPersistedCompleted(sessionId, tab)
  
  // Check current criteria
  const criteriaMet = checkStepCriteria(tab, state)
  
  // Step is completed if either:
  // 1. It's persisted as completed AND current criteria still met (preservation)
  // 2. Current criteria met AND all prior steps completed (advancement)
  if (persistedCompleted && criteriaMet) {
    return true
  }
  
  // Check all prior steps
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

// Farthest allowed index based on state-driven progress
export function farthestAllowedIndex(steps, state, sessionId) {
  for (let i = 0; i < steps.length; i++) {
    const tab = steps[i].tab
    const persistedCompleted = isStepPersistedCompleted(sessionId, tab)
    const criteriaMet = checkStepCriteria(tab, state)
    
    // Allow navigation if step is persisted as completed and criteria still met
    if (persistedCompleted && criteriaMet) {
      continue
    }
    
    // Stop at first incomplete step
    if (!criteriaMet) return i
  }
  return steps.length - 1
}

// Reset workflow progress (explicit reset or new session)
export function resetWorkflowProgress(sessionId) {
  clearWorkflowProgress(sessionId)
}

// Auto-mark step as completed when criteria met (call after successful operation)
export function autoMarkStepIfCompleted(tab, state, sessionId) {
  if (checkStepCriteria(tab, state) && !isStepPersistedCompleted(sessionId, tab)) {
    markStepCompleted(sessionId, tab)
  }
}
