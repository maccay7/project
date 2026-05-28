<template>
  <div class="login-container">
    <div class="login-form">
      <!-- Logo Section -->
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
          <span class="input-icon">📧</span>
          <input 
            v-model="email" 
            type="email" 
            class="form-input" 
            placeholder="Email"
            @keyup.enter="handleLogin"
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
            @keyup.enter="handleLogin"
          />
          <button 
            type="button" 
            class="password-toggle" 
            @click="showPassword = !showPassword"
          >
            {{ showPassword ? '👁️' : '👁️‍🗨️' }}
          </button>
          <a href="#" class="forgot-password" @click.prevent="forgotPassword">Forgot Password?</a>
        </div>
      </div>

      <div class="form-options">
        <label class="checkbox-wrapper">
          <input v-model="rememberMe" type="checkbox" />
          <span class="checkmark"></span>
          <span class="checkbox-label">Remember Me</span>
        </label>
      </div>

      <button 
        type="button" 
        class="login-button" 
        @click="handleLogin"
        :disabled="loading"
      >
        {{ loading ? 'Signing in...' : 'Login' }}
      </button>

      <div class="register-link">
        Don't have an Account? <a href="#" @click.prevent="goToRegister">Register</a>
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

const email = ref('')
const password = ref('')
const rememberMe = ref(false)
const showPassword = ref(false)
const loading = ref(false)
const error = ref('')

const handleLogin = async () => {
  if (!email.value || !password.value) {
    error.value = 'Please enter both email and password'
    return
  }

  loading.value = true
  error.value = ''

  try {
    const success = await authStore.login(email.value, password.value)
    
    if (success) {
      if (rememberMe.value) {
        localStorage.setItem('rememberMe', 'true')
        localStorage.setItem('email', email.value)
      }
      router.push('/dashboard')
    } else {
      error.value = 'Invalid email or password'
    }
  } catch (e) {
    error.value = 'Login failed. Try again.'
  } finally {
    loading.value = false
  }
}

const forgotPassword = async () => {
  const userEmail = prompt('Enter your email address to reset your password:')
  if (!userEmail) return
  
  try {
    const response = await fetch('http://localhost:5000/api/forgot-password', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: userEmail })
    })
    const data = await response.json()
    
    if (data.success) {
      if (data.reset_token) {
        // Development mode: show token and direct link
        alert(`Reset token (development only): ${data.reset_token}\n\nUse this link to reset your password:\nhttp://localhost:3000/reset-password?token=${data.reset_token}`)
      } else {
        alert(data.message || 'If the email exists, a reset link has been sent.')
      }
    } else {
      alert(data.message || 'Failed to send reset link. Please try again.')
    }
  } catch (err) {
    alert('Network error. Please try again later.')
  }
}

const goToRegister = () => {
  router.push('/signup')
}
</script>

<style scoped>
/* ========== YOUR EXACT ORIGINAL STYLES ========== */
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

.form-input::placeholder {
  color: #999;
}

.password-toggle {
  position: absolute;
  right: 12px;
  background: none;
  border: none;
  font-size: 15px;
  cursor: pointer;
  color: #666;
  transition: color 0.3s ease;
  z-index: 2;
  padding: 0;
}

.password-toggle:hover {
  color: #4a90e2;
}

.forgot-password {
  position: absolute;
  right: 42px;
  font-size: 10px;
  color: #4a90e2;
  text-decoration: none;
  font-weight: 500;
  transition: color 0.3s ease;
  z-index: 2;
}

.forgot-password:hover {
  color: #357abd;
  text-decoration: underline;
}

.form-options {
  display: flex;
  align-items: center;
  margin-bottom: 18px;
}

.checkbox-wrapper {
  display: flex;
  align-items: center;
  cursor: pointer;
  font-size: 12px;
  color: #666;
}

.checkbox-wrapper input[type="checkbox"] {
  display: none;
}

.checkmark {
  width: 15px;
  height: 15px;
  border: 2px solid #e0e0e0;
  border-radius: 3px;
  margin-right: 7px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s ease;
  background: white;
}

.checkbox-wrapper input[type="checkbox"]:checked + .checkmark {
  background: #4a90e2;
  border-color: #4a90e2;
}

.checkbox-wrapper input[type="checkbox"]:checked + .checkmark::after {
  content: '✓';
  color: white;
  font-size: 9px;
  font-weight: bold;
}

.checkbox-label {
  user-select: none;
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
  transform: none;
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
  transition: color 0.3s ease;
}

.register-link a:hover {
  color: #357abd;
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
  .forgot-password {
    right: 38px;
    font-size: 9px;
  }
}
</style>