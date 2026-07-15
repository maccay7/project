// composables/useFredMarket.js
import { ref, computed, watch } from 'vue'
import { fredAPI } from '@/services/api'

export function useFredMarket(defaultMaturity = '1Y') {
  // ===== STATE =====
  const fredFilters = ref({
    country: 'US',
    currency: 'USD',
    maturity: defaultMaturity
  })

  const filterOptions = ref({
    countries: [],
    currencies: [],
    note: ''
  })

  const isLoading = ref(false)
  const lastError = ref(null)

  // Cache for yield curve data (only successful API responses)
  const yieldCurveCache = new Map()
  const CACHE_TTL = 15 * 60 * 1000 // 15 minutes

  // ===== COMPUTED =====
  const maturityItems = computed(() => {
    const c = filterOptions.value.countries?.find(
      x => x.code === fredFilters.value.country
    )
    const maturities = c?.maturities || []
    return [...maturities, { code: 'custom', name: 'Custom' }]
  })

  const currencyItems = computed(() => {
    const currencies = filterOptions.value.currencies || []
    return [...currencies, { code: 'custom', name: 'Custom' }]
  })

  const countryItems = computed(() => {
    const countries = filterOptions.value.countries || []
    return [...countries, { code: 'custom', name: 'Custom' }]
  })

  // ===== METHODS =====

  async function loadFilterOptions() {
    isLoading.value = true
    lastError.value = null
    try {
      const res = await fredAPI.getFilters()
      if (res?.success && res.data && res.data.countries && res.data.countries.length) {
        filterOptions.value = res.data
        applyCountryDefaults()
        return
      } else {
        throw new Error(res?.message || 'No filter data received')
      }
    } catch (e) {
      console.error('FRED filters error:', e)
      lastError.value = e.message
      throw e
    } finally {
      isLoading.value = false
    }
  }

  function applyCountryDefaults() {
    const c = filterOptions.value.countries?.find(
      x => x.code === fredFilters.value.country
    )
    if (!c) {
      const first = filterOptions.value.countries?.[0]
      if (first) {
        fredFilters.value.country = first.code
        fredFilters.value.currency = first.currency || 'USD'
      }
      return
    }
    if (!fredFilters.value.currency || fredFilters.value.currency === '') {
      fredFilters.value.currency = c.currency || 'USD'
    }
    const mats = c.maturities || []
    if (mats.length && !mats.some(m => m.code === fredFilters.value.maturity)) {
      fredFilters.value.maturity = mats[0].code
    }
  }

  async function seriesIdForMaturity() {
    try {
      const res = await fredAPI.getSeriesByMaturity(
        fredFilters.value.maturity,
        fredFilters.value.country
      )
      return res?.series_id || null
    } catch (error) {
      console.error('Failed to get series ID:', error)
      throw error
    }
  }

  // ===== fetchBenchmark – no fallback =====
  async function fetchBenchmark(instrumentType) {
    isLoading.value = true
    lastError.value = null
    try {
      console.log(`Fetching FRED benchmark for ${instrumentType} ${fredFilters.value.maturity} ${fredFilters.value.country}`)
      const res = await fredAPI.getBenchmark(
        instrumentType,
        fredFilters.value.maturity,
        fredFilters.value.country,
        fredFilters.value.currency
      )
      if (res?.success && res.data && res.data.benchmark_rate !== undefined) {
        console.log('FRED benchmark received:', res.data)
        return res.data
      }
      if (res?.data && res.data.benchmark_rate !== undefined) {
        console.log('FRED benchmark received (data only):', res.data)
        return res.data
      }
      throw new Error(res?.message || 'No benchmark data received')
    } catch (e) {
      console.error('FRED benchmark error:', e)
      lastError.value = e.message
      throw e
    } finally {
      isLoading.value = false
    }
  }

  // ===== fetchYieldCurve – no fallback =====
  async function fetchYieldCurve(instrumentType = 'money_market') {
    const cacheKey = `${instrumentType}_${fredFilters.value.country}_${fredFilters.value.currency}`
    
    // Check cache
    const cached = yieldCurveCache.get(cacheKey)
    if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
      console.log('Using cached yield curve data')
      return cached.data
    }

    isLoading.value = true
    lastError.value = null
    try {
      console.log(`Fetching FRED yield curve for ${instrumentType} ${fredFilters.value.country} ${fredFilters.value.currency}`)
      const res = await fredAPI.getYieldCurve(
        instrumentType,
        fredFilters.value.country,
        fredFilters.value.currency
      )
      if (res?.success && res.data && res.data.maturities && res.data.maturities.length) {
        // Transform to points format
        const points = res.data.maturities.map((m, idx) => ({
          maturity: parseFloat(m),
          maturityLabel: res.data.labels?.[idx] || m,
          rate: res.data.rates?.[idx] || 0
        }))
        // Cache the result
        yieldCurveCache.set(cacheKey, { data: points, timestamp: Date.now() })
        console.log('FRED yield curve received, points:', points.length)
        return points
      }
      throw new Error(res?.message || 'No yield curve data received')
    } catch (e) {
      console.error('FRED yield curve error:', e)
      lastError.value = e.message
      throw e
    } finally {
      isLoading.value = false
    }
  }

  function onCountryChange() {
    applyCountryDefaults()
  }

  // Watch for country changes to update currency automatically
  watch(() => fredFilters.value.country, () => {
    applyCountryDefaults()
  })

  // ===== EXPOSE =====
  return {
    fredFilters,
    filterOptions,
    countryItems,
    currencyItems,
    maturityItems,
    isLoading,
    lastError,
    loadFilterOptions,
    applyCountryDefaults,
    onCountryChange,
    seriesIdForMaturity,
    fetchBenchmark,
    fetchYieldCurve
  }
}