import { ref, computed } from 'vue'
import { fredAPI } from '@/services/api'

/** FRED market filters: country, currency, maturity. */
export function useFredMarket(defaultMaturity = '1Y') {
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

  const maturityItems = computed(() => {
    const c = filterOptions.value.countries?.find(
      x => x.code === fredFilters.value.country
    )
    return c?.maturities || []
  })

  const currencyItems = computed(() => filterOptions.value.currencies || [])

  const countryItems = computed(() => filterOptions.value.countries || [])

  async function loadFilterOptions() {
    try {
      const res = await fredAPI.getFilters()
      if (res?.success && res.data) {
        filterOptions.value = res.data
        applyCountryDefaults()
      }
    } catch (e) {
      console.error('FRED filters', e)
    }
  }

  function applyCountryDefaults() {
    const c = filterOptions.value.countries?.find(
      x => x.code === fredFilters.value.country
    )
    if (!c) return
    fredFilters.value.currency = c.currency
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
      return res?.series_id || 'DGS1'
    } catch {
      return 'DGS1'
    }
  }

  async function fetchBenchmark(instrumentType) {
    const res = await fredAPI.getBenchmark(
      instrumentType,
      fredFilters.value.maturity,
      fredFilters.value.country,
      fredFilters.value.currency
    )
    if (res?.success) return res.data
    if (res?.data) return res.data
    return null
  }

  function onCountryChange() {
    applyCountryDefaults()
  }

  return {
    fredFilters,
    filterOptions,
    countryItems,
    currencyItems,
    maturityItems,
    loadFilterOptions,
    applyCountryDefaults,
    onCountryChange,
    seriesIdForMaturity,
    fetchBenchmark
  }
}
