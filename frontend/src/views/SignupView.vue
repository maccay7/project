<template>
  <div class="signup-container">
    <div class="signup-form">
      <div class="logo-section">
        <img 
          src="/Untitled - July 02, 2026 at 13.19.30.png" 
          alt="Logo" 
          class="signup-logo"
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
        class="signup-button" 
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

    <div v-if="successMessage" class="success-toast">
      <span class="toast-icon">✅</span>
      <span class="toast-text">{{ successMessage }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
// (Your existing script – unchanged)
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
const successMessage = ref('')

const handleRegister = async () => {
  error.value = ''
  successMessage.value = ''
  
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
      successMessage.value = 'Account created! Redirecting...'
      setTimeout(() => router.push('/dashboard'), 1200)
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
/* ===== LOGO RAISED TO THE VERY TOP ===== */
.signup-container {
  min-height: 100vh;
  background: url('/login1.jpg') center/cover no-repeat;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}
.signup-form {
  background: rgba(18, 22, 30, 0.45);
  border-radius: 28px;
  padding: 8px 34px 20px 34px;
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
.signup-logo {
  width: 200px;
  height: auto;
  object-fit: contain;
  display: block;
  margin: 0 auto 2px;
  background: transparent !important;
  padding: 0 !important;
  border: none !important;
  filter: drop-shadow(0 0 30px rgba(255, 255, 255, 0.12)) 
          drop-shadow(0 10px 20px rgba(0, 0, 0, 0.3));
}

/* ---- Even spacing ---- */
.form-group {
  margin-bottom: 12px;
}
.form-group:last-of-type {
  margin-bottom: 12px;
}
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

.signup-button {
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
.signup-button:hover:not(:disabled) {
  background: linear-gradient(135deg, #2a6fb8, #1a3f7a);
  transform: translateY(-2px);
  box-shadow: 0 12px 35px rgba(30, 80, 160, 0.35);
}
.signup-button:disabled { opacity: 0.6; cursor: not-allowed; transform: none; }

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

@media (max-width: 480px) {
  .signup-form { margin: 16px; padding: 8px 20px 16px; max-width: 320px; }
  .signup-logo { width: 150px; }
  .success-toast { top: 16px; right: 16px; left: 16px; }
}
</style>