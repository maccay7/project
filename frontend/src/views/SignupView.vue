<template>
  <div class="login-container">
    <div class="login-form">
      <div class="logo-section">
        <img 
          src="/DuraCapital logo.png" 
          alt="DuraCapital Logo" 
          class="login-logo"
          @error="e => e.target.style.display = 'none'"
        />
      </div>
      
      <div class="form-group">
        <div class="input-wrapper">
          <span class="input-icon">👤</span>
          <input 
            v-model="fullName" 
            type="text" 
            class="form-input" 
            placeholder="Full Name"
            @keyup.enter="handleRegister"
          />
        </div>
      </div>

      <div class="form-group">
        <div class="input-wrapper">
          <span class="input-icon">📧</span>
          <input 
            v-model="email" 
            type="email" 
            class="form-input" 
            placeholder="Email"
            @keyup.enter="handleRegister"
          />
        </div>
      </div>

      <div class="form-group">
        <div class="input-wrapper">
          <span class="input-icon">🔒</span>
          <input 
            v-model="password" 
            :type="showPassword ? 'text' : 'password'" 
            class="form-input" 
            placeholder="Password"
            @keyup.enter="handleRegister"
          />
          <button 
            type="button" 
            class="password-toggle" 
            @click="showPassword = !showPassword"
          >
            {{ showPassword ? '👁️' : '👁️‍🗨️' }}
          </button>
        </div>
      </div>

      <div class="form-group">
        <div class="input-wrapper">
          <span class="input-icon">🔒</span>
          <input 
            v-model="confirmPassword" 
            :type="showConfirmPassword ? 'text' : 'password'" 
            class="form-input" 
            placeholder="Confirm Password"
            @keyup.enter="handleRegister"
          />
          <button 
            type="button" 
            class="password-toggle" 
            @click="showConfirmPassword = !showConfirmPassword"
          >
            {{ showConfirmPassword ? '👁️' : '👁️‍🗨️' }}
          </button>
        </div>
      </div>

      <button 
        type="button" 
        class="login-button" 
        @click="handleRegister"
        :disabled="loading"
      >
        {{ loading ? 'Creating account...' : 'Sign Up' }}
      </button>

      <div class="register-link">
        Already have an account? <a href="#" @click.prevent="goToLogin">Login</a>
      </div>

      <div v-if="error" class="error-message">
        {{ error }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const fullName = ref('')
const email = ref('')
const password = ref('')
const confirmPassword = ref('')
const showPassword = ref(false)
const showConfirmPassword = ref(false)
const loading = ref(false)
const error = ref('')

const handleRegister = async () => {
  error.value = ''
  
  if (!fullName.value.trim()) {
    error.value = 'Please enter your full name'
    return
  }
  if (!email.value.trim()) {
    error.value = 'Please enter your email'
    return
  }
  if (!password.value) {
    error.value = 'Please enter a password'
    return
  }
  if (password.value !== confirmPassword.value) {
    error.value = 'Passwords do not match'
    return
  }
  if (password.value.length < 6) {
    error.value = 'Password must be at least 6 characters'
    return
  }

  loading.value = true

  try {
    const success = await authStore.register(
      email.value.trim(),
      password.value,
      fullName.value.trim()
    )
    if (success) {
      router.push('/dashboard')
    } else {
      error.value = 'Registration failed. Try again.'
    }
  } catch (err) {
    error.value = 'Network error. Please check your connection.'
  } finally {
    loading.value = false
  }
}

const goToLogin = () => {
  router.push('/login')
}
</script>

<style scoped>
/* Use the same styles as your Login.vue – copy from your original */
.login-container {
  min-height: 100vh;
  background: url('https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=1600&h=900&fit=crop') center/cover no-repeat;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
}
.login-container::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.3);
  backdrop-filter: blur(2px);
}
.login-form {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-radius: 20px;
  padding: 25px 30px;
  width: 100%;
  max-width: 360px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  position: relative;
  z-index: 1;
}
.logo-section {
  text-align: center;
  margin-bottom: 20px;
}
.login-logo {
  width: 200px;
  height: 60px;
  object-fit: contain;
  display: block;
  margin: 0 auto;
}
.form-group {
  margin-bottom: 14px;
}
.input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}
.input-icon {
  position: absolute;
  left: 12px;
  font-size: 15px;
  z-index: 2;
}
.form-input {
  width: 100%;
  padding: 11px 11px 11px 36px;
  border: 1.5px solid #e0e0e0;
  border-radius: 10px;
  font-size: 14px;
  background: rgba(255, 255, 255, 0.9);
  transition: all 0.3s ease;
  outline: none;
}
.form-input:focus {
  border-color: #4a90e2;
  background: white;
  box-shadow: 0 0 0 2px rgba(74, 144, 226, 0.1);
}
.password-toggle {
  position: absolute;
  right: 12px;
  background: none;
  border: none;
  font-size: 15px;
  cursor: pointer;
  color: #666;
  z-index: 2;
}
.password-toggle:hover {
  color: #4a90e2;
}
.login-button {
  width: 100%;
  padding: 11px;
  background: linear-gradient(135deg, #4a90e2, #357abd);
  color: white;
  border: none;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-bottom: 14px;
}
.login-button:hover:not(:disabled) {
  background: linear-gradient(135deg, #357abd, #2968a3);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(74, 144, 226, 0.3);
}
.login-button:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}
.register-link {
  text-align: center;
  font-size: 12px;
  color: #666;
}
.register-link a {
  color: #4a90e2;
  text-decoration: none;
  font-weight: 600;
}
.register-link a:hover {
  text-decoration: underline;
}
.error-message {
  background: rgba(244, 67, 54, 0.1);
  color: #f44336;
  padding: 8px;
  border-radius: 6px;
  font-size: 11px;
  text-align: center;
  margin-top: 12px;
  border: 1px solid rgba(244, 67, 54, 0.2);
}
@media (max-width: 480px) {
  .login-form {
    margin: 20px;
    padding: 20px;
    max-width: 320px;
  }
  .login-logo {
    width: 100px;
    height: 100px;
  }
}
</style>