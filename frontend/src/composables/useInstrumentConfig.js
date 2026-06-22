import { ref, shallowRef } from 'vue'
import api from '@/services/api.js'

const configCache = shallowRef({})
const loading = ref(false)

export function useInstrumentConfig(instrumentType) {
  const requiredColumns = ref([])
  const columnVariations = ref({})
  const workflowSteps = ref([])

  async function loadConfig(type = instrumentType) {
    if (!type) return
    if (configCache.value[type]) {
      applyConfig(configCache.value[type])
      return
    }
    loading.value = true
    try {
      const res = await api.instrumentConfigAPI.get(type)
      if (res?.success && res.data) {
        configCache.value[type] = res.data
        applyConfig(res.data)
      }
    } catch (e) {
      console.error('Failed to load instrument config:', e)
    } finally {
      loading.value = false
    }
  }

  function applyConfig(cfg) {
    requiredColumns.value = cfg.required_columns || []
    columnVariations.value = cfg.column_variations || {}
    workflowSteps.value = (cfg.workflow_steps || []).sort((a, b) => a.order - b.order)
  }

  return {
    requiredColumns,
    columnVariations,
    workflowSteps,
    loading,
    loadConfig
  }
}
