// composables/useInstrumentConfig.js
import { ref, shallowRef } from 'vue'
import api from '@/services/api.js'

// ===== STATIC FALLBACK CONFIGS =====
const STATIC_CONFIGS = {
  'money-market': {
    required_columns: [
      'Instrument', 'Amount', 'Rate', 'Principal', 'DaysToMaturity',
      'Trade Date', 'Maturity Date'
    ],
    column_variations: {
      'Instrument': ['Instrument', 'Security', 'Name', 'Description', 'Issuer', 'Bank', 'Counterparty'],
      'Amount': ['Amount', 'Principal', 'FaceValue', 'Value', 'Notional', 'Investment'],
      'Rate': ['Rate', 'InterestRate', 'Yield', 'CouponRate', 'DiscountRate'],
      'Principal': ['Principal', 'Amount', 'Value'],
      'DaysToMaturity': ['DaysToMaturity', 'Term', 'Maturity', 'Tenor', 'Period'],
      'Trade Date': ['Trade Date', 'Settlement Date', 'Date', 'Start Date'],
      'Maturity Date': ['Maturity Date', 'End Date', 'Maturity', 'Redemption Date']
    },
    workflow_steps: [
      { tab: 'upload', name: 'Upload', order: 1 },
      { tab: 'cleaning', name: 'Clean', order: 2 },
      { tab: 'calculations', name: 'Calculate', order: 3 },
      { tab: 'visualizations', name: 'Visualize', order: 4 },
      { tab: 'summary', name: 'Summary', order: 5 },
      { tab: 'reports', name: 'Report', order: 6 }
    ]
  },
  bonds: {
    required_columns: [
      'BondName', 'FaceValue', 'CouponRate', 'Yield',
      'Maturity Date', 'Issue Date', 'Coupon Frequency'
    ],
    column_variations: {
      'BondName': ['BondName', 'Bond', 'Name', 'Security', 'Description', 'Issuer', 'Counterparty'],
      'FaceValue': ['FaceValue', 'Amount', 'Principal', 'Value', 'Notional', 'Nominal', 'Par Value'],
      'CouponRate': ['CouponRate', 'Rate', 'InterestRate', 'Coupon'],
      'Yield': ['Yield', 'YTM', 'YieldToMaturity', 'Rate'],
      'Maturity Date': ['Maturity Date', 'End Date', 'Redemption Date', 'Maturity'],
      'Issue Date': ['Issue Date', 'Issuance Date', 'Settlement Date'],
      'Coupon Frequency': ['Coupon Frequency', 'Frequency', 'Coupon Period']
    },
    workflow_steps: [
      { tab: 'upload', name: 'Upload', order: 1 },
      { tab: 'cleaning', name: 'Clean', order: 2 },
      { tab: 'calculations', name: 'Calculate', order: 3 },
      { tab: 'visualizations', name: 'Visualize', order: 4 },
      { tab: 'summary', name: 'Summary', order: 5 },
      { tab: 'reports', name: 'Report', order: 6 }
    ]
  },
  tbills: {
    required_columns: [
      'TBillName', 'FaceValue', 'DiscountRate', 'DaysToMaturity',
      'Auction Date', 'Maturity Date'
    ],
    column_variations: {
      'TBillName': ['TBillName', 'T-Bill', 'Security', 'Name', 'Description', 'Issuer'],
      'FaceValue': ['FaceValue', 'Amount', 'Principal', 'Value', 'Notional', 'Nominal', 'Par Value'],
      'DiscountRate': ['DiscountRate', 'Rate', 'Discount', 'Yield'],
      'DaysToMaturity': ['DaysToMaturity', 'Term', 'Maturity', 'Tenor', 'Period'],
      'Auction Date': ['Auction Date', 'Trade Date', 'Settlement Date'],
      'Maturity Date': ['Maturity Date', 'End Date', 'Redemption Date']
    },
    workflow_steps: [
      { tab: 'upload', name: 'Upload', order: 1 },
      { tab: 'cleaning', name: 'Clean', order: 2 },
      { tab: 'calculations', name: 'Calculate', order: 3 },
      { tab: 'visualizations', name: 'Visualize', order: 4 },
      { tab: 'summary', name: 'Summary', order: 5 },
      { tab: 'reports', name: 'Report', order: 6 }
    ]
  }
}

const configCache = shallowRef({})
const loading = ref(false)

export function useInstrumentConfig(instrumentType) {
  const requiredColumns = ref([])
  const columnVariations = ref({})
  const workflowSteps = ref([])

  function applyConfig(cfg, type = instrumentType) {
    const cols = cfg.required_columns || []
    requiredColumns.value = cols.length ? cols : (STATIC_CONFIGS[type]?.required_columns || [])
    columnVariations.value = {
      ...(STATIC_CONFIGS[type]?.column_variations || {}),
      ...(cfg.column_variations || {})
    }
    workflowSteps.value = (cfg.workflow_steps || STATIC_CONFIGS[type]?.workflow_steps || []).sort((a, b) => a.order - b.order)
  }

  async function loadConfig(type = instrumentType) {
    if (!type) return
    if (configCache.value[type]) {
      applyConfig(configCache.value[type], type)
      return
    }
    loading.value = true
    try {
      const res = await api.instrumentConfigAPI.get(type)
      if (res?.success && res.data) {
        configCache.value[type] = res.data
        applyConfig(res.data, type)
      } else {
        const fallback = STATIC_CONFIGS[type]
        if (fallback) {
          configCache.value[type] = fallback
          applyConfig(fallback, type)
        } else {
          console.warn('No config found for instrument type:', type)
          requiredColumns.value = []
          columnVariations.value = {}
          workflowSteps.value = []
        }
      }
    } catch (e) {
      console.error('Failed to load instrument config, using fallback:', e)
      const fallback = STATIC_CONFIGS[type]
      if (fallback) {
        configCache.value[type] = fallback
        applyConfig(fallback, type)
      } else {
        requiredColumns.value = []
        columnVariations.value = {}
        workflowSteps.value = []
      }
    } finally {
      loading.value = false
    }
  }

  if (instrumentType) {
    loadConfig(instrumentType)
  }

  return {
    requiredColumns,
    columnVariations,
    workflowSteps,
    loading,
    loadConfig
  }
}