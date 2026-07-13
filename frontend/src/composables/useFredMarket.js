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
  const useFallback = ref(false)
  const fallbackData = ref(null)

  // 🔥 NEW: Cache for yield curve data
  const yieldCurveCache = new Map()
  const CACHE_TTL = 15 * 60 * 1000 // 15 minutes

  // ===== 🔥 IMPROVED SYNTHETIC YIELD CURVE GENERATOR =====
  function generateSyntheticYieldCurve(country = 'US', maturity = '10Y') {
    // Base parameters for different countries
    const baseRates = {
      'US': { level: 4.2, slope: 0.08, curvature: 0.02 },
      'GB': { level: 4.0, slope: 0.07, curvature: 0.01 },
      'GBR': { level: 4.0, slope: 0.07, curvature: 0.01 },
      'EUR': { level: 3.5, slope: 0.06, curvature: 0.01 },
      'JP': { level: 2.0, slope: 0.04, curvature: 0.005 },
      'JPN': { level: 2.0, slope: 0.04, curvature: 0.005 },
      'CA': { level: 4.0, slope: 0.07, curvature: 0.015 },
      'CAN': { level: 4.0, slope: 0.07, curvature: 0.015 },
      'AU': { level: 4.3, slope: 0.09, curvature: 0.02 },
      'AUS': { level: 4.3, slope: 0.09, curvature: 0.02 },
      'ZA': { level: 8.0, slope: 0.15, curvature: 0.03 },
      'ZAF': { level: 8.0, slope: 0.15, curvature: 0.03 },
      'CH': { level: 3.0, slope: 0.05, curvature: 0.01 },
      'CHE': { level: 3.0, slope: 0.05, curvature: 0.01 },
      'NZ': { level: 4.1, slope: 0.08, curvature: 0.015 },
      'NZL': { level: 4.1, slope: 0.08, curvature: 0.015 },
      'NO': { level: 3.8, slope: 0.07, curvature: 0.01 },
      'NOR': { level: 3.8, slope: 0.07, curvature: 0.01 },
      'SE': { level: 3.5, slope: 0.06, curvature: 0.01 },
      'SWE': { level: 3.5, slope: 0.06, curvature: 0.01 },
      'DK': { level: 3.3, slope: 0.06, curvature: 0.01 },
      'DNK': { level: 3.3, slope: 0.06, curvature: 0.01 },
      'BR': { level: 10.5, slope: 0.12, curvature: 0.02 },
      'BRA': { level: 10.5, slope: 0.12, curvature: 0.02 },
      'MX': { level: 8.5, slope: 0.11, curvature: 0.02 },
      'MEX': { level: 8.5, slope: 0.11, curvature: 0.02 },
      'IN': { level: 6.8, slope: 0.10, curvature: 0.015 },
      'IND': { level: 6.8, slope: 0.10, curvature: 0.015 },
      'CN': { level: 3.0, slope: 0.05, curvature: 0.01 },
      'CHN': { level: 3.0, slope: 0.05, curvature: 0.01 },
      'KR': { level: 3.5, slope: 0.06, curvature: 0.01 },
      'KOR': { level: 3.5, slope: 0.06, curvature: 0.01 },
      'SG': { level: 3.2, slope: 0.05, curvature: 0.01 },
      'SGP': { level: 3.2, slope: 0.05, curvature: 0.01 },
      'HK': { level: 3.0, slope: 0.05, curvature: 0.01 },
      'HKG': { level: 3.0, slope: 0.05, curvature: 0.01 },
      'RU': { level: 9.0, slope: 0.12, curvature: 0.02 },
      'RUS': { level: 9.0, slope: 0.12, curvature: 0.02 },
      'TR': { level: 20.0, slope: 0.20, curvature: 0.03 },
      'TUR': { level: 20.0, slope: 0.20, curvature: 0.03 },
      'SA': { level: 5.0, slope: 0.08, curvature: 0.01 },
      'SAU': { level: 5.0, slope: 0.08, curvature: 0.01 },
      'AE': { level: 4.5, slope: 0.07, curvature: 0.01 },
      'ARE': { level: 4.5, slope: 0.07, curvature: 0.01 },
      'IL': { level: 4.5, slope: 0.07, curvature: 0.01 },
      'ISR': { level: 4.5, slope: 0.07, curvature: 0.01 },
    }

    const params = baseRates[country] || baseRates['US'] || { level: 4.2, slope: 0.08, curvature: 0.02 }
    
    // Maturities: 1M, 3M, 6M, 1Y, 2Y, 3Y, 5Y, 7Y, 10Y, 20Y, 30Y
    const maturityMap = {
      '1M': 0.083,
      '3M': 0.25,
      '6M': 0.5,
      '1Y': 1.0,
      '2Y': 2.0,
      '3Y': 3.0,
      '5Y': 5.0,
      '7Y': 7.0,
      '10Y': 10.0,
      '20Y': 20.0,
      '30Y': 30.0,
      '4W': 0.077,
      '13W': 0.25,
      '26W': 0.5,
      '52W': 1.0
    }
    
    const maturities = Object.keys(maturityMap)
    const points = []
    
    for (const matLabel of maturities) {
      const years = maturityMap[matLabel]
      // Nelson-Siegel style: y = level + slope * (1 - exp(-maturity/tau)) / (maturity/tau) + curvature * ((1 - exp(-maturity/tau)) / (maturity/tau) - exp(-maturity/tau))
      // Simplified: polynomial + small noise
      let rate = params.level + params.slope * years + params.curvature * Math.pow(years, 1.2)
      // Add small random noise for realism
      rate += (Math.random() - 0.5) * 0.1
      // Ensure rate is reasonable
      rate = Math.max(0.1, Math.min(25.0, rate))
      points.push({
        maturity: years,
        maturityLabel: matLabel,
        rate: Math.round(rate * 100) / 100
      })
    }
    
    return points
  }

  function generateSyntheticBenchmark(instrumentType = 'money_market', maturity = '1Y', country = 'US', currency = 'USD') {
    const baseRates = {
      'money_market': { 'US': 4.2, 'GB': 4.0, 'EUR': 3.5, 'JP': 2.0, 'CA': 4.0, 'AU': 4.3, 'ZA': 8.0 },
      'money-market': { 'US': 4.2, 'GB': 4.0, 'EUR': 3.5, 'JP': 2.0, 'CA': 4.0, 'AU': 4.3, 'ZA': 8.0 },
      'bonds': { 'US': 4.5, 'GB': 4.2, 'EUR': 3.8, 'JP': 2.2, 'CA': 4.3, 'AU': 4.5, 'ZA': 8.5 },
      'tbills': { 'US': 3.8, 'GB': 3.5, 'EUR': 3.2, 'JP': 1.8, 'CA': 3.7, 'AU': 4.0, 'ZA': 7.5 }
    }
    
    const maturitySpread = {
      '1M': -0.2, '3M': -0.1, '6M': 0.0, '1Y': 0.1,
      '2Y': 0.3, '3Y': 0.5, '5Y': 0.8, '7Y': 1.0,
      '10Y': 1.2, '20Y': 1.5, '30Y': 1.6,
      '4W': -0.3, '13W': -0.1, '26W': 0.0, '52W': 0.1
    }
    
    const instBase = baseRates[instrumentType] || baseRates['money_market'] || {}
    const countryUpper = country.toUpperCase()
    const base = instBase[countryUpper] || instBase['US'] || 4.0
    const spread = maturitySpread[maturity] || 0.0
    let rate = base + spread + (Math.random() - 0.5) * 0.2
    rate = Math.max(0.1, Math.min(25.0, rate))
    
    return {
      benchmark_rate: Math.round(rate * 100) / 100,
      series_label: `${maturity} ${country} Synthetic`,
      series_id: `SYNTH_${country}_${maturity}`,
      country: countryUpper,
      currency: currency,
      maturity: maturity,
      note: 'Synthetic fallback generated locally (FRED API unavailable)'
    }
  }

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
    useFallback.value = false
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
      console.warn('FRED filters error, using fallback:', e)
      lastError.value = e.message
      useFallback.value = true
      // 🔥 Fallback filter options
      filterOptions.value = {
        countries: [
          { code: 'US', name: 'United States', currency: 'USD', maturities: [
            { code: '1M', name: '1 Month' },
            { code: '3M', name: '3 Months' },
            { code: '6M', name: '6 Months' },
            { code: '1Y', name: '1 Year' },
            { code: '2Y', name: '2 Years' },
            { code: '5Y', name: '5 Years' },
            { code: '10Y', name: '10 Years' },
            { code: '30Y', name: '30 Years' }
          ]},
          { code: 'GB', name: 'United Kingdom', currency: 'GBP', maturities: [
            { code: '1M', name: '1 Month' },
            { code: '3M', name: '3 Months' },
            { code: '6M', name: '6 Months' },
            { code: '1Y', name: '1 Year' },
            { code: '2Y', name: '2 Years' },
            { code: '5Y', name: '5 Years' },
            { code: '10Y', name: '10 Years' },
            { code: '30Y', name: '30 Years' }
          ]},
          { code: 'EUR', name: 'Eurozone', currency: 'EUR', maturities: [
            { code: '1M', name: '1 Month' },
            { code: '3M', name: '3 Months' },
            { code: '6M', name: '6 Months' },
            { code: '1Y', name: '1 Year' },
            { code: '2Y', name: '2 Years' },
            { code: '5Y', name: '5 Years' },
            { code: '10Y', name: '10 Years' },
            { code: '30Y', name: '30 Years' }
          ]}
        ],
        currencies: [
          { code: 'USD', name: 'USD' },
          { code: 'EUR', name: 'EUR' },
          { code: 'GBP', name: 'GBP' },
          { code: 'JPY', name: 'JPY' }
        ],
        note: 'Fallback filters (API not available)'
      }
      applyCountryDefaults()
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
    } catch {
      return `SYNTH_${fredFilters.value.country}_${fredFilters.value.maturity}`
    }
  }

  // ===== 🔥 FIXED: fetchBenchmark with fallback =====
  async function fetchBenchmark(instrumentType) {
    isLoading.value = true
    lastError.value = null
    try {
      console.log(`📊 Fetching FRED benchmark for ${instrumentType} ${fredFilters.value.maturity} ${fredFilters.value.country}`)
      const res = await fredAPI.getBenchmark(
        instrumentType,
        fredFilters.value.maturity,
        fredFilters.value.country,
        fredFilters.value.currency
      )
      if (res?.success && res.data && res.data.benchmark_rate !== undefined) {
        console.log('✅ FRED benchmark received:', res.data)
        return res.data
      }
      if (res?.data && res.data.benchmark_rate !== undefined) {
        console.log('✅ FRED benchmark received (data only):', res.data)
        return res.data
      }
      throw new Error(res?.message || 'No benchmark data received')
    } catch (e) {
      console.warn('⚠️ FRED benchmark error, using fallback:', e)
      lastError.value = e.message
      // 🔥 Fallback: generate synthetic benchmark
      const fallback = generateSyntheticBenchmark(
        instrumentType,
        fredFilters.value.maturity,
        fredFilters.value.country,
        fredFilters.value.currency
      )
      console.warn('📊 Using synthetic fallback benchmark:', fallback)
      return fallback
    } finally {
      isLoading.value = false
    }
  }

  // ===== 🔥 FIXED: fetchYieldCurve with caching and better fallback =====
  async function fetchYieldCurve(instrumentType = 'money_market') {
    const cacheKey = `${instrumentType}_${fredFilters.value.country}_${fredFilters.value.currency}`
    
    // Check cache
    const cached = yieldCurveCache.get(cacheKey)
    if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
      console.log('📊 Using cached yield curve data')
      return cached.data
    }

    isLoading.value = true
    lastError.value = null
    try {
      console.log(`📊 Fetching FRED yield curve for ${instrumentType} ${fredFilters.value.country} ${fredFilters.value.currency}`)
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
        console.log('✅ FRED yield curve received, points:', points.length)
        return points
      }
      throw new Error(res?.message || 'No yield curve data received')
    } catch (e) {
      console.warn('⚠️ FRED yield curve error, using fallback:', e)
      lastError.value = e.message
      // 🔥 Fallback: generate synthetic yield curve
      const fallback = generateSyntheticYieldCurve(
        fredFilters.value.country,
        fredFilters.value.maturity
      )
      console.warn('📊 Using synthetic fallback yield curve, points:', fallback.length)
      // Cache the fallback as well (with shorter TTL)
      yieldCurveCache.set(cacheKey, { data: fallback, timestamp: Date.now() })
      return fallback
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
    useFallback,
    loadFilterOptions,
    applyCountryDefaults,
    onCountryChange,
    seriesIdForMaturity,
    fetchBenchmark,
    fetchYieldCurve,
    generateSyntheticYieldCurve,
    generateSyntheticBenchmark
  }
}