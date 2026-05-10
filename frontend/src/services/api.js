// API Service for DuraCapital Frontend
const API_BASE_URL = 'http://localhost:5000'

async function callAPI(endpoint, method = 'GET', body = null, isFileUpload = false) {
  const url = API_BASE_URL + endpoint
  console.log('Calling:', url, method)
  
  const options = { method }
  
  if (isFileUpload) {
    options.body = body  // FormData - browser sets Content-Type
  } else if (body) {
    options.headers = { 'Content-Type': 'application/json' }
    options.body = JSON.stringify(body)
  }
  
  const response = await fetch(url, options)
  const data = await response.json()
  
  if (!response.ok) throw new Error(data.message || 'Something went wrong')
  return data
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
  execute: (type, data = [], params = {}) => callAPI('/api/calculations/execute', 'POST', {
    instrument_type: type, data, params
  }),
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

export default { authAPI, dashboardAPI, calculationsAPI, userAPI, systemAPI, dataAPI }