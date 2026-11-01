// Calculation orchestration logic extracted from InstrumentView
import { ref, computed } from 'vue'
import api from '@/services/api.js'

export function useCalculationOrchestration() {
  const calculations = ref({})
  const allCalculations = ref({})
  const selectedCalculations = ref({})
  const lastCalcInputData = ref([])
  const instrumentSummary = ref({ columns: [], rows: [] })
  const portfolioSummary = ref({ columns: [], rows: [] })
  const completedInstrumentSummary = ref({ columns: [], rows: [] })
  const completedPortfolioSummary = ref({ columns: [], rows: [] })
  const isCalculating = ref(false)
  const _lastCalcSignature = ref('')
  const _recalcQueued = ref(false)

  function calculateMetrics(data, instrumentType) {
    if (!data || !data.length) {
      allCalculations.value = {}
      selectedCalculations.value = {}
      calculations.value = {}
      instrumentSummary.value = { columns: [], rows: [] }
      return Promise.resolve()
    }

    if (isCalculating.value) {
      _recalcQueued.value = true
      return Promise.resolve()
    }

    isCalculating.value = true
    _recalcQueued.value = false

    const payload = {
      data: data,
      instrument_type: instrumentType
    }

    return api.calculationsAPI.executeByType(payload)
      .then(response => {
        if (response?.success) {
          allCalculations.value = response.data
          selectedCalculations.value = response.data
          calculations.value = response.data
          lastCalcInputData.value = JSON.parse(JSON.stringify(data))
          _lastCalcSignature.value = JSON.stringify(data)
          
          if (response.data.instrument_results) {
            instrumentSummary.value = {
              columns: Object.keys(response.data.instrument_results[0] || {}),
              rows: response.data.instrument_results
            }
          }
          
          if (response.data.aggregates) {
            portfolioSummary.value = {
              columns: Object.keys(response.data.aggregates),
              rows: [response.data.aggregates]
            }
          }
        }
      })
      .catch(error => {
        console.error('Calculation error:', error)
      })
      .finally(() => {
        isCalculating.value = false
        
        if (_recalcQueued.value) {
          _recalcQueued.value = false
          calculateMetrics(data, instrumentType)
        }
      })
  }

  function clearCalculations() {
    calculations.value = {}
    allCalculations.value = {}
    selectedCalculations.value = {}
    instrumentSummary.value = { columns: [], rows: [] }
    portfolioSummary.value = { columns: [], rows: [] }
    lastCalcInputData.value = []
    _lastCalcSignature.value = ''
  }

  function calculationSignatureMatches(data) {
    return _lastCalcSignature.value === JSON.stringify(data)
  }

  return {
    calculations,
    allCalculations,
    selectedCalculations,
    lastCalcInputData,
    instrumentSummary,
    portfolioSummary,
    completedInstrumentSummary,
    completedPortfolioSummary,
    isCalculating,
    calculateMetrics,
    clearCalculations,
    calculationSignatureMatches
  }
}
