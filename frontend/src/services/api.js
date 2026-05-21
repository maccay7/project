// API Service for DuraCapital
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

// Auth
export const authAPI = {
  login: (email, password) => callAPI('/api/login', 'POST', { email, password })
}

// Dashboard
export const dashboardAPI = {
  getKPI: () => callAPI('/api/dashboard/kpi'),
  getRecentActivity: () => callAPI('/api/dashboard/recent-activity'),
  getYieldCurve: (type = 'all') => callAPI(`/api/fred-yield-curve?instrument_type=${type}`),
  getCharts: () => callAPI('/api/dashboard/charts')
}

// Calculations
export const calculationsAPI = {
  execute: (type, data = [], params = {}) => callAPI('/api/calculations/execute', 'POST', { instrument_type: type, data, params }),
  getHistory: () => callAPI('/api/calculations/history')
}

// User
export const userAPI = {
  getProfile: () => callAPI('/api/user/profile'),
  getPreferences: () => callAPI('/api/user/preferences'),
  getNotificationSettings: () => callAPI('/api/user/notifications/settings')
}

// System
export const systemAPI = {
  getInfo: () => callAPI('/api/system/info')
}

// Data Operations
export const dataAPI = {
  upload: async (file, type) => {
    console.log('Uploading:', file.name)
    const formData = new FormData()
    formData.append('file', file)
    formData.append('instrument_type', type)
    return await callAPI('/api/upload', 'POST', formData, true)
  },
  clean: (data, options) => callAPI('/api/clean', 'POST', { data, options }),
  calculate: (data, type, params) => callAPI('/api/calculate', 'POST', { data, instrument_type: type, params }),
  deleteDataset: (id) => callAPI('/api/delete-dataset', 'POST', { upload_id: id })
}

// Dataset Operations
export const datasetAPI = {
  save: (name, file_base64, sheet_names, upload_id, data = null, headers = null, instrument_type = null) =>
    callAPI('/api/save-dataset', 'POST', { name, file_base64, sheet_names, upload_id, data, headers, instrument_type }),
  getAll: () => callAPI('/api/get-datasets'),
  load: (id) => callAPI('/api/load-dataset', 'POST', { dataset_id: id }),
  delete: (id) => callAPI('/api/delete-dataset', 'POST', { dataset_id: id }),
  markDone: (id) => callAPI('/api/dataset/done', 'POST', { dataset_id: id, done: true })
}

export default { authAPI, dashboardAPI, calculationsAPI, userAPI, systemAPI, dataAPI, datasetAPI }