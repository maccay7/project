<template>
  <div class="login-container">
    <div class="login-form">
      <!-- Logo – no pill -->
      <div class="logo-section">
        <img 
          src="/Untitled - July 02, 2026 at 13.19.30.png" 
          alt="Logo" 
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
        </div>
        <div class="forgot-password-wrapper">
          <a href="#" class="forgot-password-link" @click.prevent="openForgotModal">Forgot Password?</a>
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
    </div>

    <!-- Forgot Password Modal -->
    <div v-if="showForgotModal" class="modal-overlay" @click.self="closeForgotModal">
      <div class="modal-content">
        <div class="modal-header">
          <h3>Reset Password</h3>
          <button class="modal-close" @click="closeForgotModal">✕</button>
        </div>
        <p class="modal-instruction">Enter your email address and we'll send you a reset link.</p>
        <div class="form-group">
          <div class="input-wrapper">
            <span class="input-icon">📧</span>
            <input 
              v-model="resetEmail" 
              type="email" 
              class="form-input" 
              placeholder="Email"
              @keyup.enter="sendResetLink"
            />
          </div>
        </div>
        <button 
          class="reset-button" 
          @click="sendResetLink"
          :disabled="resetLoading"
        >
          {{ resetLoading ? 'Sending...' : 'Send Reset Link' }}
        </button>
        <div v-if="resetError" class="error-message">{{ resetError }}</div>
        <div v-if="resetSuccess" class="success-message">{{ resetSuccess }}</div>
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
const successMessage = ref('')

const showForgotModal = ref(false)
const resetEmail = ref('')
const resetLoading = ref(false)
const resetError = ref('')
const resetSuccess = ref('')

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
      setTimeout(() => router.push('/dashboard'), 1200)
    } else {
      error.value = 'Invalid email or password'
    }
  } catch (e) {
    error.value = 'Login failed. Try again.'
  } finally {
    loading.value = false
  }
}

const openForgotModal = () => {
  resetEmail.value = ''
  resetError.value = ''
  resetSuccess.value = ''
  showForgotModal.value = true
}
const closeForgotModal = () => { showForgotModal.value = false }

const sendResetLink = async () => {
  if (!resetEmail.value) {
    resetError.value = 'Please enter your email'
    return
  }
  resetError.value = ''
  resetSuccess.value = ''
  resetLoading.value = true
  try {
    const apiUrl = import.meta.env.VITE_API_BASE_URL || window.location.origin
    const response = await fetch(`${apiUrl}/api/forgot-password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: resetEmail.value })
    })
    const data = await response.json()
    if (data.success) {
      resetSuccess.value = 'Reset link sent to your email!'
      setTimeout(() => closeForgotModal(), 2000)
    } else {
      resetError.value = data.message || 'Failed to send reset link'
    }
  } catch (err) {
    resetError.value = 'Network error. Please try again.'
  } finally {
    resetLoading.value = false
  }
}

const goToRegister = () => {
  router.push('/signup')
}
</script>

<style scoped>
/* ===== BRIGHTENED GLASS – no pill ===== */
.login-container {
  min-height: 100vh;
  background: url('/login1.jpg') center/cover no-repeat;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}
.login-form {
  background: rgba(18, 22, 30, 0.15);
  border-radius: 28px;
  padding: 4px 34px 20px 34px;
  width: 100%;
  max-width: 400px;
  box-shadow: 0 30px 80px rgba(0, 0, 0, 0.7), inset 0 1px 0 rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(22px) saturate(160%);
  position: relative;
  z-index: 2;
}

.logo-section {
  text-align: center;
  margin-bottom: 4px;
  padding: 0;
}
.login-logo {
  width: 200px;
  height: auto;
  display: block;
  margin: 0 auto;
  background: transparent !important;
  padding: 0 !important;
  border: none !important;
  filter: drop-shadow(0 0 30px rgba(255, 255, 255, 0.2)) 
          drop-shadow(0 10px 20px rgba(0, 0, 0, 0.3));
}

/* ---- Even spacing ---- */
.form-group { margin-bottom: 12px; }
.form-group:last-of-type { margin-bottom: 12px; }
.input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}
.input-icon {
  position: absolute;
  left: 14px;
  font-size: 16px;
  z-index: 2;
  opacity: 0.7;
}
.form-input {
  width: 100%;
  padding: 10px 12px 10px 40px;
  border: 1px solid #ccc;
  border-radius: 14px;
  font-size: 14px;
  background: #fff;
  color: #222;
  transition: all 0.3s ease;
  outline: none;
}
.form-input::placeholder { color: #888; font-weight: 400; }
.form-input:focus {
  border-color: #4a90e2;
  box-shadow: 0 0 0 3px rgba(74, 144, 226, 0.2);
}
.password-toggle {
  position: absolute;
  right: 14px;
  background: none;
  border: none;
  font-size: 16px;
  cursor: pointer;
  color: #666;
  transition: color 0.3s ease;
  z-index: 2;
  padding: 0;
}
.password-toggle:hover { color: #222; }

.forgot-password-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 2px;
}
.forgot-password-link {
  color: #8ab4f8;
  font-size: 12px;
  font-weight: 500;
  text-decoration: none;
  transition: color 0.3s ease;
  letter-spacing: 0.3px;
}
.forgot-password-link:hover {
  color: #b0d0ff;
  text-decoration: underline;
}

.form-options {
  display: flex;
  align-items: center;
  margin-bottom: 12px;
}
.checkbox-wrapper {
  display: flex;
  align-items: center;
  cursor: pointer;
  font-size: 13px;
  color: rgba(255,255,255,0.8);
  font-weight: 300;
}
.checkbox-wrapper input[type="checkbox"] { display: none; }
.checkmark {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255,255,255,0.4);
  border-radius: 4px;
  margin-right: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s ease;
  background: rgba(255,255,255,0.1);
}
.checkbox-wrapper input[type="checkbox"]:checked + .checkmark {
  background: #4a90e2;
  border-color: #4a90e2;
}
.checkbox-wrapper input[type="checkbox"]:checked + .checkmark::after {
  content: '✓';
  color: white;
  font-size: 11px;
  font-weight: bold;
}
.checkbox-label { user-select: none; }

.login-button {
  width: 100%;
  padding: 11px;
  background: linear-gradient(135deg, #1f5a9e, #12315f);
  color: white;
  border: none;
  border-radius: 14px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  text-transform: uppercase;
  letter-spacing: 1.2px;
  margin-bottom: 12px;
  box-shadow: 0 8px 30px rgba(0, 20, 60, 0.4);
}
.login-button:hover:not(:disabled) {
  background: linear-gradient(135deg, #2a6fb8, #1a3f7a);
  transform: translateY(-2px);
  box-shadow: 0 12px 35px rgba(30, 80, 160, 0.35);
}
.login-button:disabled { opacity: 0.6; cursor: not-allowed; transform: none; }

.register-link {
  text-align: center;
  font-size: 12px;
  color: rgba(255,255,255,0.5);
  font-weight: 300;
}
.register-link a { color: #8ab4f8; text-decoration: none; font-weight: 500; }
.register-link a:hover { color: #b0d0ff; text-decoration: underline; }

.error-message {
  background: rgba(244, 67, 54, 0.15);
  color: #ff8a80;
  padding: 8px;
  border-radius: 8px;
  font-size: 12px;
  text-align: center;
  margin-top: 10px;
  border: 1px solid rgba(244, 67, 54, 0.15);
}

.success-toast {
  position: fixed;
  top: 24px;
  right: 24px;
  z-index: 9999;
  background: rgba(18, 22, 30, 0.92);
  border-radius: 12px;
  padding: 12px 20px;
  display: flex;
  align-items: center;
  gap: 12px;
  color: #eee;
  box-shadow: 0 8px 32px rgba(0,0,0,0.6);
  border: 1px solid rgba(255,255,255,0.06);
  animation: slideIn 0.4s ease;
  backdrop-filter: blur(10px);
}
@keyframes slideIn {
  from { opacity: 0; transform: translateY(-20px); }
  to { opacity: 1; transform: translateY(0); }
}
.toast-icon { font-size: 20px; }
.toast-text { font-size: 14px; font-weight: 500; }

.modal-overlay {
  position: fixed;
  top: 0; left: 0; width: 100%; height: 100%;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(6px);
  display: flex;
  align-items: center; justify-content: center;
  z-index: 9998;
  animation: fadeIn 0.3s ease;
}
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
.modal-content {
  background: rgba(18, 22, 30, 0.85);
  backdrop-filter: blur(22px) saturate(160%);
  border-radius: 28px;
  padding: 24px 28px;
  width: 100%; max-width: 400px;
  box-shadow: 0 30px 80px rgba(0, 0, 0, 0.8);
  border: 1px solid rgba(255, 255, 255, 0.08);
  animation: slideUp 0.3s ease;
}
@keyframes slideUp { from { transform: translateY(30px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
.modal-header {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 8px;
}
.modal-header h3 { color: #fff; font-size: 18px; font-weight: 600; margin: 0; }
.modal-close {
  background: none; border: none; color: rgba(255,255,255,0.6); font-size: 22px;
  cursor: pointer; transition: color 0.3s; padding: 0 4px;
}
.modal-close:hover { color: #fff; }
.modal-instruction {
  color: rgba(255,255,255,0.7); font-size: 13px; margin-bottom: 16px;
  font-weight: 300; line-height: 1.5;
}
.reset-button {
  width: 100%; padding: 11px;
  background: linear-gradient(135deg, #1f5a9e, #12315f);
  color: white; border: none; border-radius: 14px;
  font-size: 14px; font-weight: 600; cursor: pointer;
  transition: all 0.3s ease;
  text-transform: uppercase; letter-spacing: 1.2px;
  margin-top: 4px;
  box-shadow: 0 8px 30px rgba(0, 20, 60, 0.4);
}
.reset-button:hover:not(:disabled) {
  background: linear-gradient(135deg, #2a6fb8, #1a3f7a);
  transform: translateY(-2px);
}
.reset-button:disabled { opacity: 0.6; cursor: not-allowed; transform: none; }
.success-message {
  background: rgba(76, 175, 80, 0.15);
  color: #81c784;
  padding: 8px;
  border-radius: 8px;
  font-size: 12px;
  text-align: center;
  margin-top: 10px;
  border: 1px solid rgba(76, 175, 80, 0.2);
}
@media (max-width: 480px) {
  .login-form, .modal-content { margin: 16px; padding: 4px 20px 16px; max-width: 320px; }
  .login-logo { width: 150px; }
  .success-toast { top: 16px; right: 16px; left: 16px; }
}
</style>