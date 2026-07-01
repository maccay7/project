import { API_BASE_URL, RATE_LIMIT_MESSAGE } from '../config.js'

async function callAPI(endpoint, method = 'GET', body = null, isFileUpload = false) {
  const url = API_BASE_URL + endpoint
  console.log('Calling:', url, method)
  
  const options = { method }
  const token = localStorage.getItem('auth_token')
  
  if (token) {
    options.headers = { 'Authorization': `Bearer ${token}` }
  }
  
  if (isFileUpload) {
    options.body = body
  } else if (body) {
    options.headers = { ...options.headers, 'Content-Type': 'application/json' }
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
    return data
  } catch (error) {
    console.error('API Error:', error)
    throw error
  }
}

export const authAPI = {
  login: (email, password) => callAPI('/api/login', 'POST', { email, password }),
  logout: () => callAPI('/api/logout', 'POST'),
  register: (userData) => callAPI('/api/register', 'POST', userData)
}

export const dashboardAPI = {
  getKPI: () => callAPI('/api/dashboard/kpi'),
  getRecentActivity: () => callAPI('/api/dashboard/recent-activity'),
  getYieldCurve: (type = 'all') => callAPI(`/api/fred-yield-curve?instrument_type=${type}`),
  getCharts: () => callAPI('/api/dashboard/charts')
}

export const calculationsAPI = {
  execute: (type, data = [], params = {}, datasetId = null) =>
    callAPI('/api/calculate', 'POST', { instrument_type: type, data, params, dataset_id: datasetId }),
  getHistory: () => callAPI('/api/calculations/history'),
  getLatest: (datasetId) => callAPI(`/api/calculations/latest?dataset_id=${encodeURIComponent(datasetId)}`)
}

export const userAPI = {
  getProfile: () => callAPI('/api/user/profile'),
  updateProfile: (profile) => callAPI('/api/user/profile', 'PUT', profile),
  getPreferences: () => callAPI('/api/user/preferences'),
  updatePreferences: (prefs) => callAPI('/api/user/preferences', 'PUT', prefs),
  getNotificationSettings: () => callAPI('/api/user/notifications/settings'),
  updateNotificationSettings: (settings) => callAPI('/api/user/notifications/settings', 'PUT', settings)
}

export const systemAPI = {
  getInfo: () => callAPI('/api/system/info'),
  getHealth: () => callAPI('/api/health')
}

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

export const datasetAPI = {
  save: (name, file_base64, sheet_names, upload_id, data = null, headers = null, instrument_type = null) =>
    callAPI('/api/save-dataset', 'POST', { name, file_base64, sheet_names, upload_id, data, headers, instrument_type }),
  getAll: () => callAPI('/api/get-datasets'),
  load: (id) => callAPI('/api/load-dataset', 'POST', { dataset_id: id }),
  delete: (id) => callAPI('/api/delete-dataset', 'POST', { dataset_id: id }),
  markDone: (id) => callAPI('/api/dataset/done', 'POST', { dataset_id: id, done: true })
}

export const fredAPI = {
  getSeries: (seriesId, limit = 365, sortOrder = 'desc') =>
    callAPI(`/api/fred/series/${seriesId}?limit=${limit}&sort_order=${sortOrder}`),
  getCategories: () => callAPI('/api/fred/categories'),
  getYieldCurve: (instrumentType = 'all', country = 'US', currency = 'USD') =>
    callAPI(
      `/api/fred-yield-curve?instrument_type=${encodeURIComponent(instrumentType)}&country=${country}&currency=${currency}`
    ),
  getFilters: () => callAPI('/api/fred/filters'),
  getBenchmark: (instrumentType, maturity = '1Y', country = 'US', currency = 'USD') =>
    callAPI(
      `/api/fred/benchmark?instrument_type=${encodeURIComponent(instrumentType)}&maturity=${maturity}&country=${country}&currency=${currency}`
    ),
  getSeriesByMaturity: (maturity, country = 'US') =>
    callAPI(`/api/fred/series-by-maturity?maturity=${maturity}&country=${country}`)
}

export const instrumentConfigAPI = {
  getAll: () => callAPI('/api/instrument-config'),
  get: (instrumentType) => callAPI(`/api/instrument-config/${encodeURIComponent(instrumentType)}`)
}

export const sessionsAPI = {
  save: (session) => callAPI('/api/sessions/save', 'POST', session),
  get: async (session_id) => {
    try {
      return await callAPI('/api/sessions/get', 'POST', { session_id })
    } catch (e) {
      if (e.message === 'Not found' || e.message?.includes('not found')) {
        return { success: true, data: null }
      }
      throw e
    }
  },
  list: () => callAPI('/api/sessions/list', 'GET'),
  delete: (session_id) => callAPI('/api/sessions/delete', 'POST', { session_id })
}

// ========== NEW: Visualization API ==========
export const visualizationAPI = {
  // Get yield curve data (aggregated) – this is the one we use now
  getYieldCurve: (payload) => callAPI('/api/visualization/yield-curve', 'POST', payload),
  getChartData: (data, instrumentType) => 
    callAPI('/api/visualization/chart-data', 'POST', { data, instrument_type: instrumentType }),
  clearCache: () => callAPI('/api/visualization/cache/clear', 'DELETE')
}

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
  visualizationAPI  
}