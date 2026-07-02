<template>
  <div class="reset-container">
    <div class="reset-form">
      <h2>Reset Password</h2>
      <p>Enter your new password below.</p>
      
      <div class="form-group">
        <input 
          v-model="newPassword" 
          type="password" 
          placeholder="New password" 
          class="form-input"
        />
      </div>
      <div class="form-group">
        <input 
          v-model="confirmPassword" 
          type="password" 
          placeholder="Confirm new password" 
          class="form-input"
        />
      </div>
      
      <button @click="resetPassword" :disabled="loading" class="reset-button">
        {{ loading ? 'Resetting...' : 'Reset Password' }}
      </button>
      
      <div v-if="message" :class="messageClass" class="message">
        {{ message }}
      </div>
      
      <div class="login-link">
        <router-link to="/login">Back to Login</router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const newPassword = ref('')
const confirmPassword = ref('')
const loading = ref(false)
const message = ref('')
const messageClass = ref('')

const resetPassword = async () => {
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
      message.value = 'Password reset successfully! Redirecting to login...'
      messageClass.value = 'success'
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
</script>

<style scoped>
.reset-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #f5f7fa 0%, #e8ecf1 100%);
}
.reset-form {
  background: white;
  padding: 40px;
  border-radius: 16px;
  width: 100%;
  max-width: 400px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.1);
}
.reset-form h2 {
  color: #0B2044;
  margin-bottom: 10px;
}
.form-group {
  margin-bottom: 15px;
}
.form-input {
  width: 100%;
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 14px;
}
.reset-button {
  width: 100%;
  padding: 12px;
  background: #0B2044;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
}
.reset-button:hover:not(:disabled) {
  background: #1a3a6e;
}
.message {
  margin-top: 15px;
  padding: 10px;
  border-radius: 6px;
  font-size: 13px;
  text-align: center;
}
.message.success {
  background: #e8f5e9;
  color: #4caf50;
}
.message.error {
  background: #ffebee;
  color: #f44336;
}
.login-link {
  text-align: center;
  margin-top: 20px;
}
.login-link a {
  color: #4a90e2;
  text-decoration: none;
}
</style>