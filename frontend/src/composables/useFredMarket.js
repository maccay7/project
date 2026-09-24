// composables/useFredMarket.js
import { ref, computed, watch } from 'vue'
import { fredAPI } from '@/services/api'

const COUNTRY_MAP = {
  'USA': 'US', 'US': 'US',
  'GBR': 'GB', 'GB': 'GB',
  'EUR': 'EUR',
  'JPN': 'JP', 'JP': 'JP',
  'CAN': 'CA', 'CA': 'CA',
  'AUS': 'AU', 'AU': 'AU',
  'ZAF': 'ZA', 'ZA': 'ZA',
  'CHE': 'CH', 'CH': 'CH',
  'NZL': 'NZ', 'NZ': 'NZ',
  'NOR': 'NO', 'NO': 'NO',
  'SWE': 'SE', 'SE': 'SE',
  'DNK': 'DK', 'DK': 'DK',
  'BRA': 'BR', 'BR': 'BR',
  'MEX': 'MX', 'MX': 'MX',
  'IND': 'IN', 'IN': 'IN',
  'CHN': 'CN', 'CN': 'CN',
  'KOR': 'KR', 'KR': 'KR',
  'SGP': 'SG', 'SG': 'SG',
  'HKG': 'HK', 'HK': 'HK',
  'RUS': 'RU', 'RU': 'RU',
  'TUR': 'TR', 'TR': 'TR',
  'SAU': 'SA', 'SA': 'SA',
  'ARE': 'AE', 'AE': 'AE',
  'ISR': 'IL', 'IL': 'IL'
}

export function useFredMarket(defaultMaturity = '1Y') {
  const fredFilters = ref({
    country: '',
    currency: '',
    maturity: defaultMaturity || '',
    maturityMode: 'tenor',
    fromDate: '',
    toDate: ''
  })

  const filterOptions = ref({
    countries: [],
    currencies: [],
    note: ''
  })

  const isLoading = ref(false)
  const lastError = ref(null)

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

  function normalizeCountry(country) {
    if (!country) return ''
    const normalized = COUNTRY_MAP[country.toUpperCase()]
    return normalized || country.toUpperCase()
  }

  async function loadFilterOptions() {
    isLoading.value = true
    lastError.value = null
    try {
      const res = await fredAPI.getFilters()
      if (res?.success && res.data && res.data.countries && res.data.countries.length) {
        filterOptions.value = res.data
        applyCountryDefaults()
        return
      }
      throw new Error(res?.message || 'No filter data received')
    } catch (e) {
      console.error('FRED filters error:', e)
      lastError.value = e.message
      throw e
    } finally {
      isLoading.value = false
    }
  }

  function applyCountryDefaults() {
    if (!fredFilters.value.country) {
      const first = filterOptions.value.countries?.[0]
      if (first) {
        fredFilters.value.country = first.code
        if (!fredFilters.value.currency) fredFilters.value.currency = first.currency || ''
      }
      return
    }
    const c = filterOptions.value.countries?.find(
      x => x.code === fredFilters.value.country
    )
    if (!c) return
    if (!fredFilters.value.currency) {
      fredFilters.value.currency = c.currency || ''
    }
    const mats = c.maturities || []
    if (mats.length && fredFilters.value.maturityMode !== 'date' &&
        !mats.some(m => m.code === fredFilters.value.maturity)) {
      fredFilters.value.maturity = mats[0].code
    }
  }

  async function seriesIdForMaturity() {
    try {
      const res = await fredAPI.getSeriesByMaturity(
        fredFilters.value.maturity,
        normalizeCountry(fredFilters.value.country)
      )
      return res?.series_id || null
    } catch (error) {
      console.error('Failed to get series ID:', error)
      throw error
    }
  }

  async function fetchBenchmark(instrumentType) {
    isLoading.value = true
    lastError.value = null
    try {
      const country = normalizeCountry(fredFilters.value.country)
      const res = await fredAPI.getBenchmark(
        instrumentType,
        fredFilters.value.maturity,
        country,
        fredFilters.value.currency
      )
      if (res?.success && res.data && res.data.benchmark_rate !== undefined) {
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

  async function fetchYieldCurve(instrumentType = 'money_market') {
    const country = normalizeCountry(fredFilters.value.country)

    isLoading.value = true
    lastError.value = null
    try {
      const params = {
        instrument_type: instrumentType,
        country,
        currency: fredFilters.value.currency
      }
      if (fredFilters.value.maturityMode === 'date') {
        params.from_date = fredFilters.value.fromDate
        params.to_date = fredFilters.value.toDate
      } else {
        params.maturity = fredFilters.value.maturity
      }
      const res = await fredAPI.getYieldCurve(params)
      if (res?.success && res.data && res.data.maturities && res.data.maturities.length) {
        const points = res.data.maturities.map((m, idx) => ({
          maturity: parseFloat(m),
          maturityLabel: res.data.labels?.[idx] || m,
          rate: res.data.rates?.[idx] || 0
        }))
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

  watch(() => fredFilters.value.country, () => {
    applyCountryDefaults()
  })

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
    fetchYieldCurve,
    normalizeCountry
  }
}