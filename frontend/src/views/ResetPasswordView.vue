<template>
  <div class="reset-password-container">
    <div class="reset-password-form">
      <div class="logo-section">
        <img 
          src="/Untitled - July 02, 2026 at 13.19.30.png" 
          alt="Logo" 
          class="reset-logo"
          @error="(e: Event) => { const target = e.target as HTMLImageElement; if (target) target.style.display = 'none' }"
        />
      </div>
      
      <h2 class="form-title">Reset Password</h2>
      <p class="form-instruction">Enter your new password below.</p>
      
      <div class="form-group">
        <div class="input-wrapper">
          <span class="input-icon">🔒</span>
          <input 
            v-model="newPassword" 
            :type="showPassword ? 'text' : 'password'" 
            class="form-input" 
            placeholder="New Password"
            @keyup.enter="handleReset"
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
            placeholder="Confirm New Password"
            @keyup.enter="handleReset"
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
        class="reset-button" 
        @click="handleReset"
        :disabled="loading"
      >
        {{ loading ? 'Resetting...' : 'Reset Password' }}
      </button>

      <div class="back-to-login">
        <a href="#" @click.prevent="goToLogin">Back to Login</a>
      </div>

      <div v-if="error" class="error-message">
        {{ error }}
      </div>
      <div v-if="successMessage" class="success-message">
        {{ successMessage }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()

const newPassword = ref('')
const confirmPassword = ref('')
const code = ref('')
const email = ref('')
const showPassword = ref(false)
const showConfirmPassword = ref(false)
const error = ref('')
const successMessage = ref('')
const loading = ref(false)

onMounted(() => {
  code.value = (route.query.code as string) || ''
  email.value = (route.query.email as string) || ''
  if (!code.value || !email.value) {
    error.value = 'Invalid reset link'
  }
})

const handleReset = async () => {
  error.value = ''
  successMessage.value = ''
  
  if (!newPassword.value) {
    error.value = 'Please enter a new password'
    return
  }
  if (newPassword.value.length < 6) {
    error.value = 'Password must be at least 6 characters'
    return
  }
  if (newPassword.value !== confirmPassword.value) {
    error.value = 'Passwords do not match'
    return
  }
  if (!code.value || !email.value) {
    error.value = 'Invalid reset link'
    return
  }

  loading.value = true

  try {
    const apiUrl = import.meta.env.VITE_API_BASE_URL || window.location.origin
    const response = await fetch(`${apiUrl}/api/reset-password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        code: code.value,
        email: email.value,
        new_password: newPassword.value 
      })
    })
    const data = await response.json()
    if (data.success) {
      successMessage.value = 'Password reset successfully! Redirecting to login...'
      setTimeout(() => router.push('/login'), 2000)
    } else {
      error.value = data.message || 'Failed to reset password. The code may be invalid or expired.'
    }
  } catch (err) {
    error.value = 'Network error. Please try again.'
  } finally {
    loading.value = false
  }
}

const goToLogin = () => {
  router.push('/login')
}
</script>

<style scoped>
.reset-password-container {
  min-height: 100vh;
  background: url('/login1.jpg') center/cover no-repeat;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}

.reset-password-form {
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

.reset-logo {
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

.form-title {
  color: #fff;
  font-size: 20px;
  font-weight: 600;
  text-align: center;
  margin: 0 0 8px 0;
}

.form-instruction {
  color: rgba(255, 255, 255, 0.7);
  font-size: 13px;
  text-align: center;
  margin-bottom: 20px;
  font-weight: 300;
  line-height: 1.5;
}

.form-group {
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

.reset-button {
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

.reset-button:hover:not(:disabled) {
  background: linear-gradient(135deg, #2a6fb8, #1a3f7a);
  transform: translateY(-2px);
  box-shadow: 0 12px 35px rgba(30, 80, 160, 0.35);
}

.reset-button:disabled { opacity: 0.6; cursor: not-allowed; transform: none; }

.back-to-login {
  text-align: center;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.5);
  font-weight: 300;
}

.back-to-login a { color: #8ab4f8; text-decoration: none; font-weight: 500; }
.back-to-login a:hover { color: #b0d0ff; text-decoration: underline; }

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
  .reset-password-form { margin: 16px; padding: 8px 20px 16px; max-width: 320px; }
  .reset-logo { width: 150px; }
}
</style>
