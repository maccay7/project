// services/api.js
import { API_BASE_URL, RATE_LIMIT_MESSAGE } from '../config.js'

async function callAPI(endpoint, method = 'GET', body = null, isFileUpload = false, fetchOptions = {}) {
  const url = API_BASE_URL + endpoint
  console.log('=== API CALL ===')
  console.log('URL:', url)
  console.log('Method:', method)
  console.log('Body:', body ? (isFileUpload ? '[FormData]' : JSON.stringify(body).substring(0, 200)) : 'null')
  
  const options = { method, ...fetchOptions }
  const token = localStorage.getItem('auth_token')
  
  if (token) {
    options.headers = { ...(options.headers || {}), 'Authorization': `Bearer ${token}` }
  }
  
  if (isFileUpload) {
    options.body = body
  } else if (body) {
    options.headers = { ...(options.headers || {}), 'Content-Type': 'application/json' }
    options.body = JSON.stringify(body)
  }
  
  try {
    const response = await fetch(url, options)
    const data = await response.json()
    
    if (!response.ok) {
      if (response.status === 429) throw new Error(RATE_LIMIT_MESSAGE)
      if (response.status === 401) {
        localStorage.removeItem('auth_token')
        localStorage.removeItem('user')
        window.location.href = '/login'
        throw new Error('Session expired. Please login again.')
      }
      throw new Error(data.message || data.error || 'Request failed')
    }
    console.log('✅ API Response success')
    return data
  } catch (error) {
    console.error('❌ API Error:', error)
    throw error
  }
}

// ===== AUTH API =====
export const authAPI = {
  login: (email, password) => callAPI('/api/login', 'POST', { email, password }),
  logout: () => callAPI('/api/logout', 'POST'),
  register: (userData) => callAPI('/api/register', 'POST', userData)
}

// ===== DASHBOARD API =====
export const dashboardAPI = {
  getKPI: () => callAPI('/api/dashboard/kpi'),
  getRecentActivity: () => callAPI('/api/dashboard/recent-activity'),
  getYieldCurve: (type = 'all') => callAPI(`/api/fred-yield-curve?instrument_type=${type}`),
  getCharts: () => callAPI('/api/dashboard/charts')
}

// ===== CALCULATIONS API =====
export const calculationsAPI = {
  execute: (type, data = [], params = {}, datasetId = null, sessionId = null) =>
    callAPI('/api/calculate', 'POST', { instrument_type: type, data, params, dataset_id: datasetId, session_id: sessionId }),
  executeByType: (type, data = [], params = {}, datasetId = null, sessionId = null) =>
    callAPI(`/api/calculate/${encodeURIComponent(type)}`, 'POST', { data, dataset_id: datasetId, session_id: sessionId, ...params }),
  getHistory: () => callAPI('/api/calculations/history'),
  getLatest: (datasetId) => callAPI(`/api/calculations/latest?dataset_id=${encodeURIComponent(datasetId)}`),
  getBySession: (sessionId) => callAPI(`/api/calculations/session/${encodeURIComponent(sessionId)}`),
  getInstrumentSummary: (sessionId, instrumentType = null) =>
    callAPI('/api/calculations/instrument-summary', 'POST', { session_id: sessionId, instrument_type: instrumentType }),
  getPortfolioSummary: (sessionId) =>
    callAPI('/api/calculations/portfolio-summary', 'POST', { session_id: sessionId })
}

// ===== USER API =====
export const userAPI = {
  getProfile: (userId = 1) => callAPI(`/api/user/profile?user_id=${userId}`),
  updateProfile: (profile) => callAPI('/api/user/profile', 'PUT', profile),
  getPreferences: (userId = 1) => callAPI(`/api/user/preferences?user_id=${userId}`),
  updatePreferences: (prefs) => callAPI('/api/user/preferences', 'PUT', prefs),
  getNotificationSettings: (userId = 1) => callAPI(`/api/user/notifications/settings?user_id=${userId}`),
  updateNotificationSettings: (settings) => callAPI('/api/user/notifications/settings', 'PUT', settings)
}

// ===== SYSTEM API =====
export const systemAPI = {
  getInfo: () => callAPI('/api/system/info'),
  getHealth: () => callAPI('/api/health')
}

// ===== DATA API =====
export const dataAPI = {
  upload: async (file, type) => {
    console.log('Uploading:', file.name)
    const formData = new FormData()
    formData.append('file', file)
    formData.append('instrument_type', type)
    return await callAPI('/api/upload', 'POST', formData, true)
  },
  clean: (data, options) => callAPI('/api/clean', 'POST', { data, options }),
  calculate: (data, type, params, datasetId = null) => callAPI('/api/calculate', 'POST', { data, instrument_type: type, params, dataset_id: datasetId }),
  deleteDataset: (id) => callAPI('/api/delete-dataset', 'POST', { upload_id: id }),
  parseExcel: (formData) => callAPI('/api/data/parse-excel', 'POST', formData, true)
}

// ===== DATASET API =====
export const datasetAPI = {
  save: (name, file_base64, sheet_names, upload_id, data = null, headers = null, instrument_type = null) =>
    callAPI('/api/save-dataset', 'POST', { name, file_base64, sheet_names, upload_id, data, headers, instrument_type }),
  getAll: () => callAPI('/api/get-datasets'),
  load: (id) => callAPI('/api/load-dataset', 'POST', { dataset_id: id }),
  delete: (id) => callAPI('/api/delete-dataset', 'POST', { dataset_id: id }),
  markDone: (id) => callAPI('/api/dataset/done', 'POST', { dataset_id: id, done: true })
}

// ===== FRED API – NO FALLBACK FOR YIELD CURVE =====
export const fredAPI = {
  getSeries: (seriesId, limit = 365, sortOrder = 'desc') =>
    callAPI(`/api/fred/series/${seriesId}?limit=${limit}&sort_order=${sortOrder}`),
  getCategories: () => callAPI('/api/fred/categories'),
  // 🔥 Uses POST to /api/fred/yield-curve with payload – returns only real data
  getYieldCurve: (params) => callAPI('/api/fred/yield-curve', 'POST', params),
  getFilters: () => callAPI('/api/fred/filters'),
  getBenchmark: (instrumentType, maturity = '1Y', country = 'US', currency = 'USD') =>
    callAPI(`/api/fred/benchmark?instrument_type=${encodeURIComponent(instrumentType)}&maturity=${maturity}&country=${country}&currency=${currency}`),
  getSeriesByMaturity: (maturity, country = 'US') =>
    callAPI(`/api/fred/series-by-maturity?maturity=${maturity}&country=${country}`)
}

// ===== INSTRUMENT CONFIG API =====
export const instrumentConfigAPI = {
  getAll: () => callAPI('/api/instrument-config'),
  get: (instrumentType) => callAPI(`/api/instrument-config/${encodeURIComponent(instrumentType)}`)
}

// ===== SESSIONS API =====
export const sessionsAPI = {
  save: (session) => callAPI('/api/sessions/save', 'POST', session),
  get: (session_id) => callAPI('/api/sessions/get', 'POST', { session_id }),
  list: () => callAPI('/api/sessions/list', 'GET'),
  delete: (session_id) => callAPI('/api/sessions/delete', 'POST', { session_id })
  // 🔥 REMOVED: incrementVersion - version_count should only be updated by create_version
}

// ===== VERSION API =====
export const versionAPI = {
  create: (session_id, instrument_type, change_summary, dataset_snapshot = null, mapping_snapshot = null, calculation_snapshot = null, portfolio_snapshot = null, report_snapshot = null, user_id = null) =>
    callAPI('/api/version', 'POST', {
      session_id,
      instrument_type,
      change_summary,
      dataset_snapshot,
      mapping_snapshot,
      calculation_snapshot,
      portfolio_snapshot,
      report_snapshot,
      user_id
    }),
  getVersions: (session_id) => callAPI(`/api/version/session/${session_id}`, 'GET'),
  getLatest: (session_id) => callAPI(`/api/version/session/${session_id}/latest`, 'GET'),
  restore: (version_id) => callAPI(`/api/version/${version_id}/restore`, 'POST'),
  deleteVersion: (version_id) => callAPI(`/api/version/${version_id}/delete`, 'DELETE'),
  getTotalCount: () => callAPI('/api/version/count', 'GET')
}

// ===== VISUALIZATION API =====
export const visualizationAPI = {
  getYieldCurve: (payload, fetchOptions = {}) =>
    callAPI('/api/visualization/yield-curve', 'POST', payload, false, fetchOptions),
  getChartData: (data, instrumentType) =>
    callAPI('/api/visualization/chart-data', 'POST', { data, instrument_type: instrumentType }),
  clearCache: () => callAPI('/api/visualization/cache/clear', 'DELETE')
}

// ===== MAPPING TEMPLATES API =====
export const mappingTemplatesAPI = {
  getAll: () => callAPI('/api/mapping-templates', 'GET'),
  getByInstrument: (instrumentType) => callAPI(`/api/mapping-templates?instrument_type=${instrumentType}`, 'GET'),
  get: (id) => callAPI(`/api/mapping-templates/${id}`, 'GET'),
  create: (template) => callAPI('/api/mapping-templates', 'POST', template),
  update: (id, updates) => callAPI(`/api/mapping-templates/${id}`, 'PUT', updates),
  delete: (id) => callAPI(`/api/mapping-templates/${id}`, 'DELETE')
}

// ===== REPORT API =====
export const reportAPI = {
  generate: (params) => callAPI('/api/reports/generate', 'POST', params),
  getStatus: (reportId) => callAPI(`/api/reports/status/${reportId}`, 'GET'),
  download: (reportId, format = 'pdf') => callAPI(`/api/reports/download/${reportId}?format=${format}`, 'GET')
}

// ===== EXPORT =====
export default {
  authAPI,
  dashboardAPI,
  calculationsAPI,
  userAPI,
  systemAPI,
  dataAPI,
  datasetAPI,
  fredAPI,
  instrumentConfigAPI,
  sessionsAPI,
  versionAPI,
  visualizationAPI,
  mappingTemplatesAPI,
  reportAPI
}