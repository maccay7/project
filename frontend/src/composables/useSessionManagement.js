// Session management logic extracted from InstrumentView
import { ref } from 'vue'
import sessionManager from '@/services/sessionManager.js'

export function useSessionManagement(instrumentType) {
  const activeSession = ref(null)
  const sessionSavedAt = ref(null)
  const isSaving = ref(false)
  const skipAutoSave = ref(false)
  let isSavingVersion = false
  let lastInstrument = ''
  let lastSessionId = ''
  let lastSaveTime = 0
  const SAVE_DEBOUNCE_MS = 2000

  async function loadActiveSession() {
    try {
      const session = await sessionManager.getActiveSession()
      if (session) {
        activeSession.value = session
        loadSavedData(session)
      }
    } catch (error) {
      console.error('Error loading session:', error)
    }
  }

  async function saveToSession() {
    if (!activeSession.value || isSaving.value) return

    isSaving.value = true
    try {
      const sessionData = await sessionManager.saveSessionData(activeSession.value.id, {
        instrument_type: instrumentType.value,
        saved_at: new Date().toISOString()
      })
      sessionSavedAt.value = new Date().toISOString()
      return sessionData
    } catch (error) {
      console.error('Error saving session:', error)
      throw error
    } finally {
      isSaving.value = false
    }
  }

  async function loadSavedData(session) {
    if (!session || !session.data) return

    try {
      const savedData = session.data
      if (savedData.cleanedData) {
        // Restore cleaned data - this would be passed from component
      }
      if (savedData.calculations) {
        // Restore calculations - this would be passed from component
      }
      sessionSavedAt.value = session.saved_at
    } catch (error) {
      console.error('Error loading saved data:', error)
    }
  }

  function clearSession() {
    activeSession.value = null
    sessionSavedAt.value = null
  }

  return {
    activeSession,
    sessionSavedAt,
    isSaving,
    skipAutoSave,
    loadActiveSession,
    saveToSession,
    loadSavedData,
    clearSession
  }
}
