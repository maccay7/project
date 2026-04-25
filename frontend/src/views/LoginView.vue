<template>
  <v-container class="login-container" fluid>
    <v-row justify="center" align="center" class="fill-height">

      <v-col cols="12" md="6" lg="4">
        <v-card class="login-card" elevation="10">

          <v-card-text class="pa-8">

            <!-- LOGO -->
            <div class="text-center mb-8">
              <div class="logo-container">
                <div class="logo-d">D</div>
                <div class="logo-text">
                  <span class="dura">Dura</span>
                  <span class="capital">Capital</span>
                </div>
              </div>
              <div class="tagline">mathematics matters</div>
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
                class="mb-3"
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
                class="mb-2"
                required
              />

              <!-- OPTIONS ROW -->
              <div class="login-options">

                <v-checkbox
                  v-model="rememberMe"
                  label="Remember me"
                  density="compact"
                />

                <v-btn variant="text" size="small" @click="forgotPassword">
                  Forgot password?
                </v-btn>

              </div>

              <!-- LOGIN BUTTON -->
              <v-btn
                type="submit"
                block
                size="large"
                color="primary"
                class="login-btn"
                :loading="loading"
              >
                Sign In
              </v-btn>

              <!-- DEMO LOGIN -->
              <v-btn
                block
                variant="outlined"
                class="mt-3"
                @click="demoLogin"
              >
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

          </v-card-text>
        </v-card>
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
  background: linear-gradient(135deg, #0B2A44, #1E88E5);
  min-height: 100vh;
}

.login-card {
  border-radius: 16px;
}

.logo-container {
  display: flex;
  justify-content: center;
  align-items: center;
}

.logo-d {
  font-size: 50px;
  font-weight: bold;
  color: #0B2A44;
  margin-right: 10px;
  position: relative;
}

.logo-d::after {
  content: '';
  position: absolute;
  right: -6px;
  top: 50%;
  width: 14px;
  height: 32px;
  background: #1E88E5;
  border-radius: 8px;
  transform: translateY(-50%);
}

.dura, .capital {
  font-size: 22px;
  font-weight: bold;
}

.dura { color: #0B2A44; }
.capital { color: #1E88E5; }

.tagline {
  font-size: 12px;
  color: #1E88E5;
  margin-top: 6px;
  text-transform: lowercase;
}

.login-btn {
  height: 48px;
  font-weight: 600;
}

.login-options {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>