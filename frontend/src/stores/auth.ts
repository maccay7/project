// stores/auth.ts
import { ref, computed } from 'vue'
import { defineStore } from 'pinia'

const TOKEN_KEY = 'auth_token'
const USER_KEY = 'user'

// FIX #1: normalize away historically-bad localStorage values.
// A previous bug in login/register could have written the literal
// string "undefined" or "null" as the token, which is truthy and
// permanently breaks auth. This scrubs it on boot.
function readTokenFromStorage(): string | null {
  const raw = localStorage.getItem(TOKEN_KEY)
  if (!raw || raw === 'undefined' || raw === 'null') {
    localStorage.removeItem(TOKEN_KEY)
    return null
  }
  return raw
}

export const useAuthStore = defineStore('auth', () => {
  const user = ref<any>(null)
  const token = ref<string | null>(readTokenFromStorage())

  const isAuthenticated = computed(() => !!token.value)

  // FIX #2: crash-proof JSON.parse. A corrupt "user" entry in
  // localStorage would previously throw and take down store init
  // (white-screen the whole app). Now it silently clears and starts
  // fresh, so the login screen is reachable.
  const loadUser = () => {
    try {
      const storedUser = localStorage.getItem(USER_KEY)
      if (!storedUser) return
      user.value = JSON.parse(storedUser)
    } catch (err) {
      console.warn('Corrupt user in localStorage, clearing:', err)
      user.value = null
      localStorage.removeItem(USER_KEY)
    }
  }

  // Centralized state clear (avoids drift between logout, 401 handlers, etc.)
  const clearAuthState = () => {
    token.value = null
    user.value = null
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
  }

  const persistAuth = (newToken: string, newUser: any) => {
    token.value = newToken
    user.value = newUser
    localStorage.setItem(TOKEN_KEY, newToken)
    localStorage.setItem(USER_KEY, JSON.stringify(newUser))
  }

  // FIX #3: validate that `token` is a real non-empty string before
  // accepting a "successful" login. Previously `data.token === undefined`
  // would write the string "undefined" to localStorage and permanently
  // fake-authenticate the user.
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

      if (
        data &&
        data.success === true &&
        typeof data.token === 'string' &&
        data.token.length > 0 &&
        data.user
      ) {
        persistAuth(data.token, data.user)
        return true
      }

      console.warn('Login response missing token or user — rejecting')
      clearAuthState()
      return false
    } catch (error) {
      console.error('❌ Login error:', error)
      return false
    }
  }

  const logout = async () => {
    try {
      const apiUrl = import.meta.env.VITE_API_BASE_URL || window.location.origin
      const headers: Record<string, string> = { 'Content-Type': 'application/json' }
      if (token.value) headers['Authorization'] = `Bearer ${token.value}`

      await fetch(`${apiUrl}/api/logout`, {
        method: 'POST',
        headers
      })
    } catch (error) {
      console.error('Logout error:', error)
    } finally {
      clearAuthState()
    }
  }

  // FIX #4: same token validation as login.
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

      if (
        data &&
        data.success === true &&
        typeof data.token === 'string' &&
        data.token.length > 0 &&
        data.user
      ) {
        persistAuth(data.token, data.user)
        return true
      }

      console.warn('Register response missing token or user — rejecting')
      clearAuthState()
      return false
    } catch (error) {
      console.error('Register error:', error)
      return false
    }
  }

  // FIX #5: 
  //   - explicit 401 → clear token (was leaving stale token in place)
  //   - refresh token if backend rotates it in the response
  //   - network errors leave token alone (don't log the user out on a blip)
  //   - early-return if no token, avoids a pointless round-trip
  const checkSession = async () => {
    if (!token.value) return false

    try {
      const apiUrl = import.meta.env.VITE_API_BASE_URL || window.location.origin
      const response = await fetch(`${apiUrl}/api/session`, {
        method: 'GET',
        headers: { 'Authorization': `Bearer ${token.value}` }
      })

      if (response.status === 401) {
        // Token explicitly rejected by backend → really logged out.
        clearAuthState()
        return false
      }

      if (!response.ok) {
        // Network hiccup / 5xx / 429 — do NOT clear token.
        return false
      }

      const data = await response.json()
      if (data && data.authenticated === true) {
        if (data.user) {
          user.value = data.user
          localStorage.setItem(USER_KEY, JSON.stringify(data.user))
        }
        // Accept a rotated token if backend sent a fresh one.
        if (typeof data.token === 'string' && data.token.length > 0) {
          token.value = data.token
          localStorage.setItem(TOKEN_KEY, data.token)
        }
        return true
      }

      // 200 but not authenticated → treat as expired.
      clearAuthState()
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
      return data?.success === true
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
      return data?.success === true
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
      return data?.success === true
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