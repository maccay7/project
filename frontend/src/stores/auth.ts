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

      // ✅ Check if the response indicates success
      if (data.success) {
        token.value = data.token
        user.value = data.user
        localStorage.setItem('auth_token', data.token)
        localStorage.setItem('user', JSON.stringify(data.user))
        return true
      }

      // 🔁 OPTIONAL MOCK FALLBACK – remove when backend is ready
      // If backend returns an error, but we want to test, we can hardcode:
      if (email === 'makanakakanyai@gmail.com' && password === 'Business7mogul') {
        console.warn('⚠️ Using mock login – backend not available')
        const mockUser = { id: 1, email, name: 'Makanaka' }
        token.value = 'mock-token'
        user.value = mockUser
        localStorage.setItem('auth_token', 'mock-token')
        localStorage.setItem('user', JSON.stringify(mockUser))
        return true
      }

      return false
    } catch (error) {
      console.error('❌ Login error:', error)
      
      // 🔁 Also try mock on network error
      if (email === 'makanakakanyai@gmail.com' && password === 'Business7mogul') {
        console.warn('⚠️ Network error – using mock login')
        const mockUser = { id: 1, email, name: 'Makanaka' }
        token.value = 'mock-token'
        user.value = mockUser
        localStorage.setItem('auth_token', 'mock-token')
        localStorage.setItem('user', JSON.stringify(mockUser))
        return true
      }

      return false
    }
  }

  const logout = () => {
    token.value = null
    user.value = null
    localStorage.removeItem('auth_token')
    localStorage.removeItem('user')
  }

  loadUser()

  return {
    user,
    token,
    isAuthenticated,
    login,
    logout
  }
})