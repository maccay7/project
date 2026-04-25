<template>
  <v-container class="login-container" fluid>
    <v-row justify="center" align="center" class="fill-height">

      <!-- Left Panel - Branding -->
      <v-col cols="12" md="6" class="brand-panel d-none d-md-flex">
        <div class="brand-content">
          <div class="brand-logo">
            <div class="logo-d">D</div>
            <div class="logo-text">
              <span class="dura">Dura</span>
              <span class="capital">Capital</span>
            </div>
          </div>
          <h1 class="brand-title">Financial Intelligence Platform</h1>
          <p class="brand-subtitle">Advanced treasury bill calculations and yield curve analysis for modern finance</p>
          
          <div class="features">
            <div class="feature-item">
              <v-icon color="white" class="feature-icon">mdi-chart-line</v-icon>
              <span>Real-time Calculations</span>
            </div>
            <div class="feature-item">
              <v-icon color="white" class="feature-icon">mdi-shield-check</v-icon>
              <span>Secure & Reliable</span>
            </div>
            <div class="feature-item">
              <v-icon color="white" class="feature-icon">mdi-lightning-bolt</v-icon>
              <span>Lightning Fast</span>
            </div>
          </div>
        </div>
      </v-col>

      <!-- Right Panel - Login Form -->
      <v-col cols="12" md="6" class="form-panel">
        <div class="form-wrapper">
          <v-card class="login-card" elevation="0">

            <v-card-text class="pa-8">

              <!-- Mobile Logo -->
              <div class="text-center mb-8 d-md-none">
                <div class="logo-container">
                  <div class="logo-d">D</div>
                  <div class="logo-text">
                    <span class="dura">Dura</span>
                    <span class="capital">Capital</span>
                  </div>
                </div>
                <div class="tagline">mathematics matters</div>
              </div>

              <!-- Welcome Text -->
              <div class="welcome-section mb-6">
                <h2 class="welcome-title">Welcome Back</h2>
                <p class="welcome-subtitle">Sign in to your account to continue</p>
              </div>

              <!-- FORM -->
              <v-form ref="loginForm" @submit.prevent="handleLogin">

                <v-text-field
                  v-model="email"
                  label="Email Address"
                  type="email"
                  variant="outlined"
                  prepend-inner-icon="mdi-email"
                  :rules="emailRules"
                  class="mb-4"
                  bg-color="grey-lighten-5"
                  required
                />

                <v-text-field
                  v-model="password"
                  :type="showPassword ? 'text' : 'password'"
                  label="Password"
                  variant="outlined"
                  prepend-inner-icon="mdi-lock"
                  :append-inner-icon="showPassword ? 'mdi-eye' : 'mdi-eye-off'"
                  @click:append-inner="showPassword = !showPassword"
                  :rules="passwordRules"
                  class="mb-4"
                  bg-color="grey-lighten-5"
                  required
                />

                <!-- OPTIONS ROW -->
                <div class="login-options mb-6">

                  <v-checkbox
                    v-model="rememberMe"
                    label="Remember me"
                    density="compact"
                    color="primary"
                  />

                  <v-btn variant="text" size="small" @click="forgotPassword" class="forgot-link">
                    Forgot password?
                  </v-btn>

                </div>

                <!-- LOGIN BUTTON -->
                <v-btn
                  type="submit"
                  block
                  size="large"
                  color="primary"
                  class="login-btn mb-4"
                  :loading="loading"
                >
                  <v-icon left>mdi-login</v-icon>
                  Sign In
                </v-btn>

                <!-- Divider -->
                <div class="divider-section mb-4">
                  <v-divider></v-divider>
                  <span class="divider-text">or</span>
                  <v-divider></v-divider>
                </div>

                <!-- DEMO LOGIN -->
                <v-btn
                  block
                  variant="outlined"
                  class="demo-btn"
                  @click="demoLogin"
                >
                  <v-icon left>mdi-account-circle</v-icon>
                  Use Demo Account
                </v-btn>

              </v-form>

              <!-- ERROR -->
              <v-alert
                v-if="error"
                type="error"
                class="mt-4"
                variant="tonal"
              >
                {{ error }}
              </v-alert>

              <!-- Sign Up Link -->
              <div class="signup-link mt-6 text-center">
                <span class="text-grey-darken-1">Don't have an account?</span>
                <v-btn variant="text" color="primary" class="px-2">Contact Sales</v-btn>
              </div>

            </v-card-text>
          </v-card>
        </div>
      </v-col>

    </v-row>
  </v-container>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const email = ref('')
const password = ref('')
const rememberMe = ref(false)
const showPassword = ref(false)

const loading = ref(false)
const error = ref('')
const loginForm = ref()

const emailRules = [
  (v: string) => !!v || 'Email is required',
  (v: string) => /.+@.+\..+/.test(v) || 'Invalid email'
]

const passwordRules = [
  (v: string) => !!v || 'Password is required'
]

const handleLogin = async () => {
  const { valid } = await loginForm.value.validate()
  if (!valid) return

  loading.value = true
  error.value = ''

  try {
    const success = await authStore.login(email.value, password.value)

    if (success) {
      if (rememberMe.value) {
        localStorage.setItem('rememberMe', 'true')
      }

      router.push('/dashboard')
    } else {
      error.value = 'Invalid credentials'
    }

  } catch (e) {
    error.value = 'Login failed. Try again.'
  } finally {
    loading.value = false
  }
}

const forgotPassword = () => {
  alert('Password reset feature coming soon')
}

const demoLogin = async () => {
  email.value = 'demo@duracapital.com'
  password.value = 'demo123'

  await handleLogin()
}
</script>

<style scoped>
.login-container {
  min-height: 100vh;
  padding: 0;
}

/* Left Panel - Branding */
.brand-panel {
  background: linear-gradient(135deg, #0B2A44 0%, #1E88E5 100%);
  position: relative;
  overflow: hidden;
}

.brand-panel::before {
  content: '';
  position: absolute;
  top: -50%;
  right: -50%;
  width: 200%;
  height: 200%;
  background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
  animation: float 20s ease-in-out infinite;
}

@keyframes float {
  0%, 100% { transform: translate(0, 0) rotate(0deg); }
  50% { transform: translate(-20px, -20px) rotate(180deg); }
}

.brand-content {
  position: relative;
  z-index: 1;
  padding: 60px;
  color: white;
  height: 100vh;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.brand-logo {
  display: flex;
  align-items: center;
  margin-bottom: 40px;
}

.brand-logo .logo-d {
  font-size: 48px;
  font-weight: bold;
  color: white;
  margin-right: 12px;
  position: relative;
}

.brand-logo .logo-d::after {
  content: '';
  position: absolute;
  right: -4px;
  top: 50%;
  width: 12px;
  height: 30px;
  background: #4CAF50;
  border-radius: 6px;
  transform: translateY(-50%);
}

.brand-logo .dura, .brand-logo .capital {
  font-size: 24px;
  font-weight: bold;
}

.brand-logo .dura { color: white; }
.brand-logo .capital { color: #4CAF50; }

.brand-title {
  font-size: 36px;
  font-weight: 700;
  margin-bottom: 20px;
  line-height: 1.2;
}

.brand-subtitle {
  font-size: 18px;
  opacity: 0.9;
  margin-bottom: 40px;
  line-height: 1.5;
}

.features {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.feature-item {
  display: flex;
  align-items: center;
  font-size: 16px;
}

.feature-icon {
  margin-right: 12px;
}

/* Right Panel - Form */
.form-panel {
  background: #f8f9fa;
  display: flex;
  align-items: center;
}

.form-wrapper {
  width: 100%;
  max-width: 480px;
  margin: 0 auto;
  padding: 40px;
}

.login-card {
  background: white;
  border-radius: 20px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.08);
  border: 1px solid rgba(0, 0, 0, 0.06);
}

/* Mobile Logo */
.logo-container {
  display: flex;
  justify-content: center;
  align-items: center;
}

.logo-d {
  font-size: 40px;
  font-weight: bold;
  color: #0B2A44;
  margin-right: 8px;
  position: relative;
}

.logo-d::after {
  content: '';
  position: absolute;
  right: -4px;
  top: 50%;
  width: 10px;
  height: 24px;
  background: #1E88E5;
  border-radius: 5px;
  transform: translateY(-50%);
}

.dura, .capital {
  font-size: 20px;
  font-weight: bold;
}

.dura { color: #0B2A44; }
.capital { color: #1E88E5; }

.tagline {
  font-size: 11px;
  color: #1E88E5;
  margin-top: 4px;
  text-transform: lowercase;
}

/* Welcome Section */
.welcome-title {
  font-size: 28px;
  font-weight: 700;
  color: #0B2A44;
  margin-bottom: 8px;
}

.welcome-subtitle {
  font-size: 16px;
  color: #666;
  margin: 0;
}

/* Form Styles */
.login-options {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.forgot-link {
  color: #1E88E5 !important;
  font-weight: 500;
}

.login-btn {
  height: 56px;
  font-weight: 600;
  font-size: 16px;
  text-transform: none;
  letter-spacing: 0.5px;
}

.divider-section {
  display: flex;
  align-items: center;
  gap: 16px;
}

.divider-text {
  color: #666;
  font-size: 14px;
  font-weight: 500;
}

.demo-btn {
  height: 56px;
  font-weight: 600;
  text-transform: none;
  letter-spacing: 0.5px;
  border-color: #1E88E5;
  color: #1E88E5;
}

.demo-btn:hover {
  background: rgba(30, 136, 229, 0.08);
}

.signup-link {
  font-size: 14px;
}

/* Responsive Design */
@media (max-width: 960px) {
  .form-wrapper {
    padding: 20px;
  }
  
  .brand-content {
    padding: 40px;
  }
  
  .brand-title {
    font-size: 28px;
  }
  
  .brand-subtitle {
    font-size: 16px;
  }
}

@media (max-width: 600px) {
  .form-wrapper {
    padding: 16px;
  }
  
  .welcome-title {
    font-size: 24px;
  }
  
  .login-card {
    border-radius: 16px;
  }
}
</style>