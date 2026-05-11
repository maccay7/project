<template>
  <div class="signup-container">
    <div class="signup-form">
      <h1 class="signup-title">SIGN UP</h1>
      
      <div class="form-group">
        <div class="input-wrapper">
          <span class="input-icon">👤</span>
          <input 
            v-model="fullName" 
            type="text" 
            class="form-input" 
            placeholder="Full Name"
            @keyup.enter="handleSignup"
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
            @keyup.enter="handleSignup"
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
            @keyup.enter="handleSignup"
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
            @keyup.enter="handleSignup"
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
        @click="handleSignup"
        :disabled="loading"
      >
        {{ loading ? 'Creating account...' : 'Sign Up' }}
      </button>

      <div class="login-link">
        Already have an Account? <router-link to="/login">Login</router-link>
      </div>

      <div v-if="error" class="error-message">
        {{ error }}
      </div>

      <div v-if="success" class="success-message">
        Account created successfully! Redirecting to login...
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
const success = ref(false)

const handleSignup = async () => {
  error.value = ''
  success.value = false

  // Validation
  if (!fullName.value || !email.value || !password.value || !confirmPassword.value) {
    error.value = 'Please fill in all fields'
    return
  }

  if (password.value.length < 6) {
    error.value = 'Password must be at least 6 characters'
    return
  }

  if (password.value !== confirmPassword.value) {
    error.value = 'Passwords do not match'
    return
  }

  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  if (!emailRegex.test(email.value)) {
    error.value = 'Invalid email format'
    return
  }

  loading.value = true

  try {
    const success = await authStore.register(email.value, password.value, fullName.value)
    
    if (success) {
      success.value = true
      setTimeout(() => {
        router.push('/dashboard')
      }, 2000)
    } else {
      error.value = 'Registration failed. Email may already be in use.'
    }
  } catch (e) {
    error.value = 'Registration failed. Try again.'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.signup-container {
  min-height: 100vh;
  background: url('https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=1600&h=900&fit=crop') center/cover no-repeat;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}

.signup-container::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.3);
  backdrop-filter: blur(2px);
}

.signup-form {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-radius: 20px;
  padding: 40px;
  width: 100%;
  max-width: 400px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  position: relative;
  z-index: 1;
}

.signup-title {
  font-size: 32px;
  font-weight: 700;
  text-align: center;
  margin-bottom: 30px;
  color: #333;
  letter-spacing: 2px;
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
  left: 15px;
  font-size: 18px;
  z-index: 2;
}

.form-input {
  width: 100%;
  padding: 15px 15px 15px 45px;
  border: 2px solid #e0e0e0;
  border-radius: 10px;
  font-size: 16px;
  background: rgba(255, 255, 255, 0.8);
  transition: all 0.3s ease;
  outline: none;
}

.form-input:focus {
  border-color: #4a90e2;
  background: white;
  box-shadow: 0 0 0 3px rgba(74, 144, 226, 0.1);
}

.form-input::placeholder {
  color: #999;
}

.password-toggle {
  position: absolute;
  right: 15px;
  background: none;
  border: none;
  font-size: 18px;
  cursor: pointer;
  color: #666;
  transition: color 0.3s ease;
  z-index: 2;
}

.password-toggle:hover {
  color: #4a90e2;
}

.signup-button {
  width: 100%;
  padding: 15px;
  background: linear-gradient(135deg, #4a90e2, #357abd);
  color: white;
  border: none;
  border-radius: 10px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  text-transform: uppercase;
  letter-spacing: 1px;
  margin-bottom: 20px;
}

.signup-button:hover:not(:disabled) {
  background: linear-gradient(135deg, #357abd, #2968a3);
  transform: translateY(-2px);
  box-shadow: 0 5px 15px rgba(74, 144, 226, 0.3);
}

.signup-button:disabled {
  opacity: 0.7;
  cursor: not-allowed;
  transform: none;
}

.login-link {
  text-align: center;
  font-size: 14px;
  color: #666;
}

.login-link a {
  color: #4a90e2;
  text-decoration: none;
  font-weight: 600;
  transition: color 0.3s ease;
}

.login-link a:hover {
  color: #357abd;
  text-decoration: underline;
}

.error-message {
  background: rgba(244, 67, 54, 0.1);
  color: #f44336;
  padding: 12px;
  border-radius: 8px;
  font-size: 14px;
  text-align: center;
  margin-top: 15px;
  border: 1px solid rgba(244, 67, 54, 0.2);
}

.success-message {
  background: rgba(76, 175, 80, 0.1);
  color: #4caf50;
  padding: 12px;
  border-radius: 8px;
  font-size: 14px;
  text-align: center;
  margin-top: 15px;
  border: 1px solid rgba(76, 175, 80, 0.2);
}

/* Responsive Design */
@media (max-width: 480px) {
  .signup-form {
    margin: 20px;
    padding: 30px 20px;
  }
  
  .signup-title {
    font-size: 28px;
  }
  
  .form-input {
    padding: 12px 12px 12px 40px;
  }
  
  .password-toggle {
    right: 12px;
  }
}
</style>
