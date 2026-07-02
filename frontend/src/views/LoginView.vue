<template>
  <div class="login-container">
    <div class="login-form">
      <!-- Logo Section -->
      <div class="logo-section">
        <img 
          src="/DuraCapital logo.png" 
          alt="Dura Capital Logo" 
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

    <!-- Success Toast -->
    <div v-if="successMessage" class="success-toast">
      <span class="toast-icon">✅</span>
      <span class="toast-text">{{ successMessage }}</span>
      <button class="toast-close" @click="successMessage = ''">✕</button>
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
const successMessage = ref('')

const handleLogin = async () => {
  if (!email.value || !password.value) {
    error.value = 'Please enter both email and password'
    return
  }

  loading.value = true
  error.value = ''
  successMessage.value = ''

  try {
    const success = await authStore.login(email.value, password.value)
    
    if (success) {
      if (rememberMe.value) {
        localStorage.setItem('rememberMe', 'true')
        localStorage.setItem('email', email.value)
      }
      successMessage.value = 'Login successful'
      setTimeout(() => {
        router.push('/dashboard')
      }, 1200)
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
    const apiUrl = import.meta.env.VITE_API_BASE_URL || window.location.origin
    const response = await fetch(`${apiUrl}/api/forgot-password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: userEmail })
    })
    const data = await response.json()
    
    if (data.success) {
      if (data.reset_token) {
        const frontendUrl = window.location.origin
        alert(`Reset token (development only): ${data.reset_token}\n\nUse this link to reset your password:\n${frontendUrl}/reset-password?token=${data.reset_token}`)
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
/* ===== ORIGINAL STYLES – UNCHANGED ===== */
.login-container {
  min-height: 100vh;
  background: url('/login1.jpg') center/cover no-repeat;
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
  background: rgba(5, 17, 34, 0.35);
  backdrop-filter: blur(8px);
}

.login-form {
  background: rgba(255,255,255,0.14);
  border-radius: 24px;
  padding: 28px 30px;
  width: 100%;
  max-width: 400px;
  box-shadow: 0 24px 65px rgba(0, 0, 0, 0.28);
  border: 1px solid rgba(255, 255, 255, 0.18);
  backdrop-filter: blur(22px) saturate(160%);
  position: relative;
  z-index: 2;
}

.logo-section {
  text-align: center;
  margin-bottom: 20px;
}

.login-logo {
  width: 160px;
  height: auto;
  object-fit: contain;
  display: block;
  margin: 0 auto 18px;
  background: rgba(255, 255, 255, 0.08);
  padding: 10px;
  border-radius: 18px;
  mix-blend-mode: normal;
  filter: drop-shadow(0 20px 40px rgba(0,0,0,0.25));
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
  border: 1.5px solid rgba(255,255,255,0.34);
  border-radius: 14px;
  font-size: 14px;
  background: rgba(255,255,255,0.86);
  transition: all 0.3s ease;
  outline: none;
}

.form-input:focus {
  border-color: rgba(74, 144, 226, 0.85);
  background: rgba(255,255,255,0.96);
  box-shadow: 0 0 0 3px rgba(74, 144, 226, 0.12);
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
  padding: 12px;
  background: linear-gradient(135deg, #3b7fd1, #1f497f);
  color: white;
  border: none;
  border-radius: 14px;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.3s ease;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-bottom: 14px;
  box-shadow: 0 10px 24px rgba(15, 60, 110, 0.2);
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

/* ===== SUCCESS TOAST ===== */
.success-toast {
  position: fixed;
  top: 24px;
  right: 24px;
  z-index: 9999;
  background: rgba(255,255,255,0.95);
  border-radius: 10px;
  padding: 10px 16px;
  display: flex;
  align-items: center;
  gap: 10px;
  color: #222;
  box-shadow: 0 8px 32px rgba(6,24,64,0.25);
  border: 1px solid rgba(255,255,255,0.06);
  animation: slideIn 0.4s ease;
}

@keyframes slideIn {
  from { opacity: 0; transform: translateY(-20px); }
  to { opacity: 1; transform: translateY(0); }
}

.toast-icon {
  font-size: 20px;
}

.toast-text {
  font-size: 14px;
  font-weight: 500;
}

.toast-close {
  background: none;
  border: none;
  color: #999;
  cursor: pointer;
  font-size: 16px;
  padding: 0 4px;
  transition: color 0.2s;
}

.toast-close:hover {
  color: #333;
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
  .success-toast {
    top: 16px;
    right: 16px;
    left: 16px;
  }
}
</style>