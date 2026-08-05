import { ref, computed } from 'vue'
import { defineStore } from 'pinia'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<any>(null)
  const token = ref<string | null>(localStorage.getItem('auth_token'))

  const isAuthenticated = computed(() => !!token.value)

  const loadUser = () => {
    const storedUser = localStorage.getItem('user')
    if (storedUser) {
      user.value = JSON.parse(storedUser)
    }
  }

  const login = async (email: string, password: string) => {
    try {
      const apiUrl = import.meta.env.VITE_API_BASE_URL || window.location.origin
      console.log('🔍 Login request to:', `${apiUrl}/api/login`)
      
      const response = await fetch(`${apiUrl}/api/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      })

      const data = await response.json()
      console.log('📦 Login response:', data)

      if (data.success) {
        token.value = data.token
        user.value = data.user
        localStorage.setItem('auth_token', data.token)
        localStorage.setItem('user', JSON.stringify(data.user))
        return true
      }

      return false
    } catch (error) {
      console.error('❌ Login error:', error)
      return false
    }
  }

  const logout = async () => {
    try {
      const apiUrl = import.meta.env.VITE_API_BASE_URL || window.location.origin
      await fetch(`${apiUrl}/api/logout`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token.value}`
        }
      })
    } catch (error) {
      console.error('Logout error:', error)
    } finally {
      token.value = null
      user.value = null
      localStorage.removeItem('auth_token')
      localStorage.removeItem('user')
    }
  }

  const register = async (email: string, password: string, fullName: string) => {
    try {
      const apiUrl = import.meta.env.VITE_API_BASE_URL || window.location.origin
      const response = await fetch(`${apiUrl}/api/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password, full_name: fullName })
      })

      const data = await response.json()
      console.log('Register response:', data)

      if (data.success) {
        token.value = data.token
        user.value = data.user
        localStorage.setItem('auth_token', data.token)
        localStorage.setItem('user', JSON.stringify(data.user))
        return true
      }

      return false
    } catch (error) {
      console.error('Register error:', error)
      return false
    }
  }

  const checkSession = async () => {
    try {
      const apiUrl = import.meta.env.VITE_API_BASE_URL || window.location.origin
      const response = await fetch(`${apiUrl}/api/session`, {
        method: 'GET',
        headers: { 
          'Authorization': `Bearer ${token.value}`
        }
      })

      const data = await response.json()
      if (data.authenticated) {
        user.value = data.user
        localStorage.setItem('user', JSON.stringify(data.user))
        return true
      }

      return false
    } catch (error) {
      console.error('Session check error:', error)
      return false
    }
  }

  const forgotPassword = async (email: string) => {
    try {
      const apiUrl = import.meta.env.VITE_API_BASE_URL || window.location.origin
      const response = await fetch(`${apiUrl}/api/forgot-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email })
      })

      const data = await response.json()
      return data.success
    } catch (error) {
      console.error('Forgot password error:', error)
      return false
    }
  }

  const resetPassword = async (token: string, newPassword: string) => {
    try {
      const apiUrl = import.meta.env.VITE_API_BASE_URL || window.location.origin
      const response = await fetch(`${apiUrl}/api/reset-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, new_password: newPassword })
      })

      const data = await response.json()
      return data.success
    } catch (error) {
      console.error('Reset password error:', error)
      return false
    }
  }

  const changePassword = async (oldPassword: string, newPassword: string) => {
    try {
      const apiUrl = import.meta.env.VITE_API_BASE_URL || window.location.origin
      const response = await fetch(`${apiUrl}/api/change-password`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token.value}`
        },
        body: JSON.stringify({ old_password: oldPassword, new_password: newPassword })
      })

      const data = await response.json()
      return data.success
    } catch (error) {
      console.error('Change password error:', error)
      return false
    }
  }

  loadUser()

  return {
    user,
    token,
    isAuthenticated,
    login,
    logout,
    register,
    checkSession,
    forgotPassword,
    resetPassword,
    changePassword
  }
})