<template>
  <div class="verify-code-container">
    <div class="verify-code-form">
      <div class="logo-section">
        <img 
          src="/Untitled - July 02, 2026 at 13.19.30.png" 
          alt="Logo" 
          class="verify-logo"
          @error="(e: Event) => { const target = e.target as HTMLImageElement; if (target) target.style.display = 'none' }"
        />
      </div>
      
      <h2 class="form-title">Enter Verification Code</h2>
      <p class="form-instruction">Enter the 6-digit code sent to your email</p>
      
      <div class="form-group">
        <div class="input-wrapper">
          <span class="input-icon">🔢</span>
          <input 
            v-model="verificationCode" 
            type="text" 
            class="form-input" 
            placeholder="123456"
            maxlength="6"
            @input="formatCode"
          />
        </div>
      </div>
      
      <div v-if="error" class="error-message">{{ error }}</div>
      <div v-if="success" class="success-message">{{ success }}</div>
      
      <button 
        @click="verifyCode" 
        class="submit-btn"
        :disabled="loading || !verificationCode"
      >
        <span v-if="loading">Verifying...</span>
        <span v-else>Verify Code</span>
      </button>
      
      <div class="form-footer">
        <button @click="resendCode" class="resend-link" :disabled="resending">
          <span v-if="resending">Sending...</span>
          <span v-else>Resend Code</span>
        </button>
        <button @click="goBack" class="back-link">Back to Login</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()

const verificationCode = ref('')
const error = ref('')
const success = ref('')
const loading = ref(false)
const resending = ref(false)
const email = ref('')

onMounted(() => {
  email.value = (route.query.email as string) || ''
  if (!email.value) {
    router.push('/login')
  }
})

function formatCode() {
  verificationCode.value = verificationCode.value.replace(/\D/g, '').slice(0, 6)
}

async function verifyCode() {
  if (verificationCode.value.length !== 6) {
    error.value = 'Please enter a valid 6-digit code'
    return
  }
  
  loading.value = true
  error.value = ''
  success.value = ''
  
  try {
    const apiUrl = import.meta.env.VITE_API_BASE_URL || window.location.origin
    const response = await fetch(`${apiUrl}/api/verify-reset-code`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        email: email.value,
        code: verificationCode.value 
      })
    })
    const data = await response.json()
    
    if (data.success) {
      success.value = 'Code verified! Redirecting to reset password...'
      setTimeout(() => {
        router.push({ 
          path: '/reset-password', 
          query: { code: verificationCode.value, email: email.value } 
        })
      }, 1000)
    } else {
      error.value = data.message || 'Invalid verification code'
    }
  } catch (err) {
    error.value = 'Network error. Please try again.'
  } finally {
    loading.value = false
  }
}

async function resendCode() {
  resending.value = true
  error.value = ''
  success.value = ''
  
  try {
    const apiUrl = import.meta.env.VITE_API_BASE_URL || window.location.origin
    const response = await fetch(`${apiUrl}/api/forgot-password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: email.value })
    })
    const data = await response.json()
    
    if (data.success) {
      success.value = 'New code sent to your email'
      if (data.verification_code) {
        success.value += ` (Development: ${data.verification_code})`
      }
    } else {
      error.value = data.message || 'Failed to resend code'
    }
  } catch (err) {
    error.value = 'Network error. Please try again.'
  } finally {
    resending.value = false
  }
}

function goBack() {
  router.push('/login')
}
</script>

<style scoped>
.verify-code-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #0B2044 0%, #1E3A5F 100%);
  padding: 20px;
}

.verify-code-form {
  background: white;
  border-radius: 12px;
  padding: 40px;
  width: 100%;
  max-width: 400px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
}

.logo-section {
  display: flex;
  justify-content: center;
  margin-bottom: 24px;
}

.verify-logo {
  max-height: 60px;
  object-fit: contain;
}

.form-title {
  font-size: 24px;
  font-weight: 600;
  color: #0B2044;
  text-align: center;
  margin-bottom: 8px;
}

.form-instruction {
  font-size: 14px;
  color: #666;
  text-align: center;
  margin-bottom: 24px;
}

.form-group {
  margin-bottom: 20px;
}

.input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.input-icon {
  position: absolute;
  left: 12px;
  font-size: 18px;
}

.form-input {
  width: 100%;
  padding: 12px 12px 12px 40px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 16px;
  letter-spacing: 4px;
  text-align: center;
  font-weight: 600;
}

.form-input:focus {
  outline: none;
  border-color: #0B2044;
}

.error-message {
  color: #dc3545;
  font-size: 14px;
  margin-bottom: 16px;
  text-align: center;
}

.success-message {
  color: #28a745;
  font-size: 14px;
  margin-bottom: 16px;
  text-align: center;
}

.submit-btn {
  width: 100%;
  padding: 14px;
  background: #0B2044;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}

.submit-btn:hover:not(:disabled) {
  background: #1a3a6e;
}

.submit-btn:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.form-footer {
  display: flex;
  justify-content: space-between;
  margin-top: 20px;
  gap: 12px;
}

.resend-link, .back-link {
  flex: 1;
  padding: 10px;
  background: transparent;
  border: 1px solid #0B2044;
  color: #0B2044;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.resend-link:hover:not(:disabled), .back-link:hover {
  background: #0B2044;
  color: white;
}

.resend-link:disabled {
  border-color: #ccc;
  color: #ccc;
  cursor: not-allowed;
}
</style>
