<template>
  <div class="reset-container">
    <div class="reset-form">
      <div class="logo-section">
        <img 
          src="/DuraCapital logo.png" 
          alt="Dura Capital Logo" 
          class="reset-logo"
          @error="e => e.target.style.display = 'none'"
        />
      </div>

      <p class="instruction-text">Enter your new password below.</p>

      <div class="form-group">
        <div class="input-wrapper">
          <span class="input-icon">🔒</span>
          <input 
            v-model="newPassword" 
            :type="showNewPassword ? 'text' : 'password'" 
            class="form-input" 
            placeholder="New password"
            @keyup.enter="resetPassword"
          />
          <button 
            type="button" 
            class="password-toggle" 
            @click="showNewPassword = !showNewPassword"
          >
            {{ showNewPassword ? '👁️' : '👁️‍🗨️' }}
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
            placeholder="Confirm new password"
            @keyup.enter="resetPassword"
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
        @click="resetPassword"
        :disabled="loading"
      >
        {{ loading ? 'Resetting...' : 'Reset Password' }}
      </button>

      <div class="login-link">
        <a href="#" @click.prevent="goToLogin">Back to Login</a>
      </div>

      <div v-if="message" :class="messageClass" class="message">
        {{ message }}
      </div>
    </div>

    <div v-if="successMessage" class="success-toast">
      <span class="toast-icon">✅</span>
      <span class="toast-text">{{ successMessage }}</span>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const newPassword = ref('')
const confirmPassword = ref('')
const showNewPassword = ref(false)
const showConfirmPassword = ref(false)
const loading = ref(false)
const message = ref('')
const messageClass = ref('')
const successMessage = ref('')

const resetPassword = async () => {
  message.value = ''
  successMessage.value = ''
  if (!newPassword.value || !confirmPassword.value) {
    message.value = 'Please fill in both fields'
    messageClass.value = 'error'
    return
  }
  if (newPassword.value !== confirmPassword.value) {
    message.value = 'Passwords do not match'
    messageClass.value = 'error'
    return
  }
  if (newPassword.value.length < 8) {
    message.value = 'Password must be at least 8 characters'
    messageClass.value = 'error'
    return
  }
  const token = route.query.token
  if (!token) {
    message.value = 'No reset token provided'
    messageClass.value = 'error'
    return
  }
  loading.value = true
  try {
    const apiUrl = import.meta.env.VITE_API_BASE_URL || window.location.origin
    const response = await fetch(`${apiUrl}/api/reset-password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token, new_password: newPassword.value })
    })
    const data = await response.json()
    if (data.success) {
      successMessage.value = 'Password reset successfully! Redirecting...'
      setTimeout(() => router.push('/login'), 2000)
    } else {
      message.value = data.message || 'Failed to reset password'
      messageClass.value = 'error'
    }
  } catch (err) {
    message.value = 'Network error. Please try again.'
    messageClass.value = 'error'
  } finally {
    loading.value = false
  }
}

const goToLogin = () => {
  router.push('/login')
}
</script>

<style scoped>
/* ===== FULL GLASS STYLING (matching Login) ===== */
.reset-container {
  min-height: 100vh;
  background: url('/login1.jpg') center/cover no-repeat;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}
.reset-form {
  background: rgba(18, 22, 30, 0.45);
  border-radius: 28px;
  padding: 32px 34px;
  width: 100%;
  max-width: 400px;
  box-shadow: 0 30px 80px rgba(0, 0, 0, 0.7), inset 0 1px 0 rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(22px) saturate(160%);
  position: relative;
  z-index: 2;
}
.logo-section { text-align: center; margin-bottom: 24px; }
.reset-logo {
  width: 160px;
  height: auto;
  object-fit: contain;
  display: block;
  margin: 0 auto 18px;
  background: transparent !important;
  padding: 0 !important;
  border: none !important;
  filter: drop-shadow(0 0 30px rgba(255, 255, 255, 0.12)) drop-shadow(0 10px 20px rgba(0, 0, 0, 0.3));
}
.instruction-text {
  color: rgba(255,255,255,0.7);
  font-size: 14px;
  text-align: center;
  margin-bottom: 24px;
  font-weight: 300;
  line-height: 1.5;
}
.form-group { margin-bottom: 16px; }
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
  opacity: 0.6;
}
.form-input {
  width: 100%;
  padding: 12px 12px 12px 40px;
  border: 1px solid rgba(255,255,255,0.12);
  border-radius: 16px;
  font-size: 14px;
  background: rgba(255,255,255,0.07);
  color: #fff;
  transition: all 0.3s ease;
  outline: none;
  backdrop-filter: blur(4px);
}
.form-input::placeholder { color: rgba(255,255,255,0.4); font-weight: 300; }
.form-input:focus {
  border-color: rgba(74, 144, 226, 0.5);
  background: rgba(255,255,255,0.12);
  box-shadow: 0 0 0 4px rgba(74, 144, 226, 0.06);
}
.password-toggle {
  position: absolute;
  right: 14px;
  background: none;
  border: none;
  font-size: 16px;
  cursor: pointer;
  color: rgba(255,255,255,0.4);
  transition: color 0.3s ease;
  z-index: 2;
  padding: 0;
}
.password-toggle:hover { color: #fff; }
.reset-button {
  width: 100%;
  padding: 13px;
  background: linear-gradient(135deg, #1f5a9e, #12315f);
  color: white;
  border: none;
  border-radius: 16px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  text-transform: uppercase;
  letter-spacing: 1.2px;
  margin-bottom: 16px;
  box-shadow: 0 8px 30px rgba(0, 20, 60, 0.4);
}
.reset-button:hover:not(:disabled) {
  background: linear-gradient(135deg, #2a6fb8, #1a3f7a);
  transform: translateY(-2px);
  box-shadow: 0 12px 35px rgba(30, 80, 160, 0.35);
}
.reset-button:disabled { opacity: 0.6; cursor: not-allowed; transform: none; }
.login-link {
  text-align: center;
  font-size: 13px;
  color: rgba(255,255,255,0.5);
  font-weight: 300;
}
.login-link a { color: #8ab4f8; text-decoration: none; font-weight: 500; }
.login-link a:hover { color: #b0d0ff; text-decoration: underline; }
.message {
  margin-top: 14px;
  padding: 10px;
  border-radius: 10px;
  font-size: 12px;
  text-align: center;
}
.message.success {
  background: rgba(76, 175, 80, 0.15);
  color: #81c784;
  border: 1px solid rgba(76, 175, 80, 0.2);
}
.message.error {
  background: rgba(244, 67, 54, 0.12);
  color: #ff8a80;
  border: 1px solid rgba(244, 67, 54, 0.1);
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
  .reset-form { margin: 20px; padding: 24px 20px; max-width: 320px; }
  .reset-logo { width: 120px; }
  .success-toast { top: 16px; right: 16px; left: 16px; }
}
</style>