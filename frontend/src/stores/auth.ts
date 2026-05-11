import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { authAPI } from '../services/api'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<any>(null)
  const token = ref<string | null>(localStorage.getItem('auth_token'))

  const isAuthenticated = computed(() => !!token.value)

  // Load user from localStorage on init
  const loadUser = () => {
    const storedUser = localStorage.getItem('user')
    if (storedUser) {
      user.value = JSON.parse(storedUser)
    }
  }

  const login = async (email: string, password: string) => {
    try {
      const response = await authAPI.login(email, password)
      if (response.success) {
        token.value = response.token
        localStorage.setItem('auth_token', response.token || '')
        user.value = response.user
        localStorage.setItem('user', JSON.stringify(response.user))
        return true
      }
      return false
    } catch (error) {
      console.error('Login error:', error)
      return false
    }
  }

  const register = async (email: string, password: string, full_name: string) => {
    try {
      const response = await fetch('http://localhost:5000/api/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password, full_name })
      })
      const data = await response.json()
      if (data.success) {
        token.value = data.token
        localStorage.setItem('auth_token', data.token || '')
        user.value = data.user
        localStorage.setItem('user', JSON.stringify(data.user))
        return true
      }
      return false
    } catch (error) {
      console.error('Registration error:', error)
      return false
    }
  }

  const logout = () => {
    token.value = null
    user.value = null
    localStorage.removeItem('auth_token')
    localStorage.removeItem('user')
  }

  // Initialize user from localStorage
  loadUser()

  return {
    user,
    token,
    isAuthenticated,
    login,
    register,
    logout
  }
})
