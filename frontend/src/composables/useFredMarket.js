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
      if (res?.success && res.data) {
        filterOptions.value = res.data
        applyCountryDefaults()
      } else {
        throw new Error(res?.message || 'Failed to load FRED filters')
      }
    } catch (e) {
      console.error('FRED filters error:', e)
      lastError.value = e.message
      // Set fallback defaults
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
          ]}
        ],
        currencies: [
          { code: 'USD', name: 'USD' },
          { code: 'EUR', name: 'EUR' },
          { code: 'GBP', name: 'GBP' },
          { code: 'JPY', name: 'JPY' }
        ],
        note: 'Default fallback (API not available)'
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
      return null
    }
  }

  async function fetchBenchmark(instrumentType) {
    isLoading.value = true
    lastError.value = null
    try {
      const res = await fredAPI.getBenchmark(
        instrumentType,
        fredFilters.value.maturity,
        fredFilters.value.country,
        fredFilters.value.currency
      )
      if (res?.success && res.data) return res.data
      if (res?.data) return res.data
      return null
    } catch (e) {
      console.error('FRED benchmark error:', e)
      lastError.value = e.message
      return null
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
    fetchBenchmark
  }
}