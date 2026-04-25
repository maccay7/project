import { ref, computed } from 'vue'
import { defineStore } from 'pinia'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<any>(null)
  const token = ref<string | null>(localStorage.getItem('token'))

  const isAuthenticated = computed(() => !!token.value)

  const login = async (email: string, password: string) => {
    // Mock authentication - replace with actual API call
    if (email === 'makanakakanyai@gmail.com' && password === 'Business7mogul') {
      token.value = 'mock-token-' + Date.now()
      localStorage.setItem('token', token.value)
      user.value = {
        email: email,
        name: 'Makanaka Kanyai',
        role: 'admin'
      }
      return true
    }
    return false
  }

  const logout = () => {
    token.value = null
    user.value = null
    localStorage.removeItem('token')
  }

  return {
    user,
    token,
    isAuthenticated,
    login,
    logout
  }
})
