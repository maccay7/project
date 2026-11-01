// Visualization and yield curve logic extracted from InstrumentView
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useFredMarket } from './useFredMarket'
import Chart from 'chart.js/auto'
import 'chartjs-adapter-date-fns'

export function useVisualizationYieldCurve(instrumentType, config) {
  const yieldCurveLoading = ref(false)
  const yieldCurveError = ref('')
  const yieldCurveChart = ref(null)
  const chartInstanceRef = { current: null }
  const yieldCurveData = ref([])
  const chartSeriesLabel = ref('')
  const chartImageData = ref('')
  
  const maturityMode = ref('maturity')
  const yieldCurveStartDate = ref('')
  const yieldCurveEndDate = ref('')
  
  const selectedMaturityOption = ref('')
  const selectedCountryOption = ref('')
  const selectedCurrencyOption = ref('')
  const customCountryInput = ref('')
  const customCurrencyInput = ref('')
  const customMaturityInput = ref('')
  
  const CACHE_TTL = 5 * 60 * 1000 // 5 minutes
  const yieldCurveCache = new Map()

  const { fredFilters, loadFilterOptions, fetchBenchmark } = useFredMarket(() => config.value.defaultMaturity)

  const effectiveCountry = computed(() => {
    if (selectedCountryOption.value === '__custom__') return customCountryInput.value || 'US'
    return selectedCountryOption.value || 'US'
  })

  const effectiveCurrency = computed(() => {
    if (selectedCurrencyOption.value === '__custom__') return customCurrencyInput.value || 'USD'
    return selectedCurrencyOption.value || 'USD'
  })

  const effectiveMaturity = computed(() => {
    if (selectedMaturityOption.value === '__custom__') return customMaturityInput.value || config.value.defaultMaturity
    return selectedMaturityOption.value
  })

  async function fetchYieldCurve() {
    const country = effectiveCountry.value
    const maturity = effectiveMaturity.value
    const currency = effectiveCurrency.value
    const from_date = yieldCurveStartDate.value || null
    const to_date = yieldCurveEndDate.value || null
    
    yieldCurveLoading.value = true
    yieldCurveError.value = ''
    
    try {
      const payload = {
        instrument_type: instrumentType.value,
        country: country,
        currency,
        maturity: maturityMode.value === 'dateRange' ? (maturity || '10Y') : maturity
      }
      
      if (maturityMode.value === 'dateRange') {
        payload.from_date = from_date
        payload.to_date = to_date
      }
      
      const response = await api.fredAPI.getYieldCurve(payload)
      
      if (response?.success && response.data) {
        const curveData = response.data
        yieldCurveData.value = curveData.datasets?.[0]?.data || []
        chartSeriesLabel.value = curveData.datasets?.[0]?.label || 'Yield Curve'
        yieldCurveError.value = ''
        
        await renderYieldCurveChart()
      } else {
        yieldCurveError.value = response?.data?.note || response?.message || 'Failed to fetch yield curve'
        yieldCurveData.value = []
      }
    } catch (error) {
      yieldCurveError.value = 'Error fetching yield curve'
      console.error('Yield curve error:', error)
    } finally {
      yieldCurveLoading.value = false
    }
  }

  async function renderYieldCurveChart() {
    if (!yieldCurveData.value.length) return

    if (chartInstanceRef.current) {
      chartInstanceRef.current.destroy()
    }

    const ctx = yieldCurveChart.value?.getContext('2d')
    if (!ctx) return

    const isDateMode = maturityMode.value === 'dateRange'
    
    chartInstanceRef.current = new Chart(ctx, {
      type: isDateMode ? 'line' : 'bar',
      data: {
        labels: yieldCurveData.value.map(p => p.date || p.maturityLabel),
        datasets: [{
          label: chartSeriesLabel.value,
          data: yieldCurveData.value.map(p => p.y),
          borderColor: '#0B2044',
          backgroundColor: 'rgba(11, 32, 68, 0.1)',
          tension: 0.1
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: {
            title: {
              display: true,
              text: isDateMode ? 'Date' : 'Maturity'
            }
          },
          y: {
            title: {
              display: true,
              text: 'Yield (%)'
            }
          }
        }
      }
    })
  }

  function switchToMaturityMode(mode) {
    maturityMode.value = mode
    if (mode === 'dateRange') {
      const today = new Date()
      const oneYearAgo = new Date(today)
      oneYearAgo.setFullYear(today.getFullYear() - 1)
      yieldCurveEndDate.value = today.toISOString().split('T')[0]
      yieldCurveStartDate.value = oneYearAgo.toISOString().split('T')[0]
      if (yieldCurveStartDate.value && yieldCurveEndDate.value) {
        fetchYieldCurve()
      }
    } else {
      fetchYieldCurve()
    }
  }

  function onDateRangeChange() {
    if (yieldCurveStartDate.value && yieldCurveEndDate.value) {
      fetchYieldCurve()
    }
  }

  function destroyChart() {
    if (chartInstanceRef.current) {
      chartInstanceRef.current.destroy()
      chartInstanceRef.current = null
    }
  }

  onMounted(() => {
    loadFilterOptions()
  })

  onBeforeUnmount(() => {
    destroyChart()
  })

  return {
    yieldCurveLoading,
    yieldCurveError,
    yieldCurveChart,
    yieldCurveData,
    chartSeriesLabel,
    chartImageData,
    maturityMode,
    yieldCurveStartDate,
    yieldCurveEndDate,
    selectedMaturityOption,
    selectedCountryOption,
    selectedCurrencyOption,
    customCountryInput,
    customCurrencyInput,
    customMaturityInput,
    effectiveCountry,
    effectiveCurrency,
    effectiveMaturity,
    fredFilters,
    fetchBenchmark,
    fetchYieldCurve,
    renderYieldCurveChart,
    switchToMaturityMode,
    onDateRangeChange,
    destroyChart
  }
}
