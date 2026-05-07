// API Service for DuraCapital Frontend
const API_BASE_URL = 'http://localhost:5000'

// Generic API request function
const apiRequest = async (endpoint, options = {}) => {
  try {
    const url = `${API_BASE_URL}${endpoint}`
    console.log('apiRequest called:', endpoint, options.method || 'GET')
    
    const config = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers
      },
      ...options
    }

    console.log('Making fetch request to:', url)
    const response = await fetch(url, config)
    const data = await response.json()

    console.log('API response status:', response.status)
    console.log('API response data:', data)

    if (!response.ok) {
      throw new Error(data.message || `HTTP error! status: ${response.status}`)
    }

    return data
  } catch (error) {
    console.error('API Error:', error)
    throw error
  }
}

// Authentication API
export const authAPI = {
  login: async (email, password) => {
    return await apiRequest('/api/login', {
      method: 'POST',
      body: JSON.stringify({ email, password })
    })
  }
}

// Dashboard API
export const dashboardAPI = {
  getKPI: async () => {
    return await apiRequest('/api/dashboard/kpi')
  },
  
  getRecentActivity: async () => {
    return await apiRequest('/api/dashboard/recent-activity')
  },
  
  getYieldCurve: async (instrumentType = 'all') => {
    return await apiRequest(`/api/fred-yield-curve?instrument_type=${instrumentType}`)
  },
  
  getCharts: async () => {
    return await apiRequest('/api/dashboard/charts')
  }
}

// Calculations API
export const calculationsAPI = {
  execute: async (instrumentType, data = [], params = {}) => {
    return await apiRequest('/api/calculations/execute', {
      method: 'POST',
      body: JSON.stringify({
        instrument_type: instrumentType,
        data: data,
        params: params
      })
    })
  },
  
  getHistory: async () => {
    return await apiRequest('/api/calculations/history')
  }
}

// User API
export const userAPI = {
  getProfile: async () => {
    return await apiRequest('/api/user/profile')
  },
  
  getPreferences: async () => {
    return await apiRequest('/api/user/preferences')
  },
  
  getNotificationSettings: async () => {
    return await apiRequest('/api/user/notifications/settings')
  }
}

// System API
export const systemAPI = {
  getInfo: async () => {
    return await apiRequest('/api/system/info')
  }
}

// Data Operations API
export const dataAPI = {
  upload: async (file, instrumentType) => {
    console.log('dataAPI.upload called with:', file?.name, instrumentType)
    
    const formData = new FormData()
    formData.append('file', file)
    formData.append('instrument_type', instrumentType)
    
    console.log('FormData created, making API request...')
    
    const response = await apiRequest('/api/upload', {
      method: 'POST',
      headers: {}, // Remove content-type to let browser set it for FormData
      body: formData
    })
    
    console.log('dataAPI.upload response:', response)
    return response
  },
  
  clean: async (data, options) => {
    return await apiRequest('/api/clean', {
      method: 'POST',
      body: JSON.stringify({ data, options })
    })
  },
  
  calculate: async (data, instrumentType, params) => {
    return await apiRequest('/api/calculate', {
      method: 'POST',
      body: JSON.stringify({ 
        data, 
        instrument_type: instrumentType, 
        params 
      })
    })
  },
  
  clean: async (data, options) => {
    return await apiRequest('/api/clean', {
      method: 'POST',
      body: JSON.stringify({ 
        data, 
        options 
      })
    })
  },
  
  deleteDataset: async (uploadId) => {
    return await apiRequest('/api/delete-dataset', {
      method: 'POST',
      body: JSON.stringify({ 
        upload_id: uploadId 
      })
    })
  }
}

export default {
  authAPI,
  dashboardAPI,
  calculationsAPI,
  userAPI,
  systemAPI,
  dataAPI
}
