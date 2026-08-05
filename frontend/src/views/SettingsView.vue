<template>
  <fixed-layout>
    <div class="settings-view">
      <!-- Header Section -->
      <div class="settings-header">
        <h1 class="page-title">System Settings</h1>
        <p class="page-subtitle">Manage your account settings and security</p>
      </div>

      <!-- Settings Content -->
      <v-row class="settings-row" align="stretch">
        <!-- Profile Card - Top with spacing -->
        <v-col cols="12" class="settings-col profile-col">
          <v-card class="settings-card profile-card">
            <div class="card-accent"></div>
            <v-card-text class="profile-card-text">
              <div class="profile-section">
                <div class="avatar-container">
                  <v-avatar size="80" color="primary" class="profile-avatar">
                    <v-img v-if="user.avatar" :src="user.avatar" />
                    <v-icon v-else size="40" color="white">mdi-account</v-icon>
                  </v-avatar>
                </div>
                
                <div class="profile-info text-center">
                  <h3 class="profile-name">{{ user.fullName || 'User' }}</h3>
                  <p class="profile-email">{{ user.email || 'user@example.com' }}</p>
                  <p class="profile-role">{{ user.role || 'Administrator' }}</p>
                </div>

                <v-btn 
                  block 
                  size="small"
                  variant="outlined" 
                  class="edit-profile-btn"
                  @click="editProfile"
                >
                  <v-icon left size="14">mdi-pencil</v-icon>
                  Edit Profile
                </v-btn>
              </div>
            </v-card-text>
          </v-card>
        </v-col>

        <!-- System Information Card - Left Half -->
        <v-col cols="12" md="6" class="settings-col">
          <v-card class="settings-card info-card">
            <div class="card-accent"></div>
            <v-card-title class="card-title">
              <v-icon class="title-icon">mdi-information</v-icon>
              System Information
            </v-card-title>
            <v-card-text>
              <div class="info-item">
                <span class="info-label">Administrator</span>
                <span class="info-value">{{ user.email || 'Not logged in' }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">Database Status</span>
                <v-chip size="small" color="success" class="status-chip">
                  Connected
                </v-chip>
              </div>
              <div class="info-item">
                <span class="info-label">API Status</span>
                <v-chip size="small" color="success" class="status-chip">
                  Online
                </v-chip>
              </div>
              <div class="info-item">
                <span class="info-label">Version</span>
                <span class="info-value">1.0.0</span>
              </div>
            </v-card-text>
          </v-card>
        </v-col>

        <!-- Security Card - Right Half -->
        <v-col cols="12" md="6" class="settings-col">
          <!-- Security Card -->
          <v-card class="settings-card security-card">
            <div class="card-accent"></div>
            <v-card-title class="card-title">
              <v-icon class="title-icon">mdi-shield-lock</v-icon>
              Security
            </v-card-title>
            <v-card-text>
              <v-btn 
                block 
                variant="outlined" 
                class="security-btn"
                @click="showChangePassword = true"
              >
                <v-icon left size="16">mdi-lock-reset</v-icon>
                Change Password
              </v-btn>
              
              <v-btn 
                block 
                variant="outlined" 
                class="security-btn"
                @click="showLoginHistory = true"
              >
                <v-icon left size="16">mdi-history</v-icon>
                Login History
              </v-btn>
              
              <v-btn 
                block 
                variant="outlined" 
                class="security-btn"
                @click="loadActiveSessions"
              >
                <v-icon left size="16">mdi-devices</v-icon>
                Active Sessions
              </v-btn>
            </v-card-text>
          </v-card>

        </v-col>
      </v-row>
    </div>

    <!-- ========== DIALOGS / MODALS ========== -->

    <!-- Change Password Dialog -->
    <v-dialog v-model="showChangePassword" max-width="450px" persistent>
      <v-card>
        <v-card-title class="dialog-title">
          <v-icon>mdi-lock-reset</v-icon> Change Password
          <v-spacer></v-spacer>
          <button class="btn-close-dialog" @click="showChangePassword = false">✕</button>
        </v-card-title>
        <v-card-text class="dialog-body">
          <v-form ref="passwordForm">
            <v-text-field
              v-model="passwordData.currentPassword"
              label="Current Password"
              type="password"
              variant="outlined"
              prepend-inner-icon="mdi-lock"
              class="mb-3"
            />
            <v-text-field
              v-model="passwordData.newPassword"
              label="New Password"
              type="password"
              variant="outlined"
              prepend-inner-icon="mdi-lock"
              class="mb-3"
              :rules="[v => v.length >= 8 || 'Password must be at least 8 characters']"
            />
            <v-text-field
              v-model="passwordData.confirmPassword"
              label="Confirm Password"
              type="password"
              variant="outlined"
              prepend-inner-icon="mdi-lock"
              class="mb-3"
              :rules="[v => v === passwordData.newPassword || 'Passwords do not match']"
            />
          </v-form>
        </v-card-text>
        <v-card-actions class="dialog-actions">
          <v-spacer></v-spacer>
          <button class="btn-secondary" @click="showChangePassword = false">Cancel</button>
          <button class="btn-primary" @click="changePassword" :loading="saving.password">Save</button>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Edit Profile Dialog – includes avatar upload -->
    <v-dialog v-model="profileDialog" max-width="450px" persistent>
      <v-card>
        <v-card-title class="dialog-title">
          <v-icon>mdi-account-edit</v-icon> Edit Profile
          <v-spacer></v-spacer>
          <button class="btn-close-dialog" @click="profileDialog = false">✕</button>
        </v-card-title>
        <v-card-text class="dialog-body">
          <div class="dialog-avatar-section">
            <v-avatar size="64" color="primary" class="dialog-avatar">
              <v-img v-if="profileData.avatarPreview" :src="profileData.avatarPreview" />
              <v-icon v-else size="32" color="white">mdi-account</v-icon>
            </v-avatar>
            <div class="dialog-avatar-actions">
              <v-btn size="small" color="primary" variant="tonal" @click="uploadAvatarFromDialog">
                <v-icon left size="16">mdi-upload</v-icon>
                Upload Photo
              </v-btn>
              <v-btn size="small" color="error" variant="tonal" @click="removeAvatar" v-if="profileData.avatarPreview">
                <v-icon left size="16">mdi-close</v-icon>
                Remove
              </v-btn>
              <input type="file" ref="avatarFileInput" accept="image/*" style="display:none" @change="handleAvatarFileSelect" />
            </div>
          </div>

          <v-divider class="my-3" />

          <v-text-field
            v-model="profileData.fullName"
            label="Full Name"
            variant="outlined"
            prepend-inner-icon="mdi-account"
            class="mb-3"
          />
          <v-text-field
            v-model="profileData.email"
            label="Email"
            type="email"
            variant="outlined"
            prepend-inner-icon="mdi-email"
            class="mb-3"
            readonly
          />
          <v-text-field
            v-model="profileData.phone"
            label="Phone Number"
            variant="outlined"
            prepend-inner-icon="mdi-phone"
            class="mb-3"
          />
        </v-card-text>
        <v-card-actions class="dialog-actions">
          <v-spacer></v-spacer>
          <button class="btn-secondary" @click="profileDialog = false">Cancel</button>
          <button class="btn-primary" @click="saveProfile" :loading="saving.profile">Save</button>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Login History Dialog -->
    <v-dialog v-model="showLoginHistory" max-width="700" persistent>
      <v-card>
        <v-card-title class="dialog-title">
          <v-icon>mdi-history</v-icon> Login History
          <v-spacer></v-spacer>
          <button class="btn-close-dialog" @click="showLoginHistory = false">✕</button>
        </v-card-title>
        <v-card-text class="dialog-body">
          <div v-if="loadingHistory" class="text-center py-8">
            <v-progress-circular indeterminate color="primary"></v-progress-circular>
            <p class="mt-4">Loading login history...</p>
          </div>
          <div v-else-if="loginHistory.length === 0" class="empty-state">
            <v-icon size="48" color="#ccc">mdi-history</v-icon>
            <p>No login history available</p>
          </div>
          <div v-else class="history-table-container">
            <table class="history-table">
              <thead>
                <tr>
                  <th>Email</th>
                  <th>Login Time</th>
                  <th>Status</th>
                  <th>Expires</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(entry, index) in loginHistory" :key="index" :class="{ 'active-row': entry.status === 'Active' }">
                  <td class="email-cell">{{ entry.email || '—' }}</td>
                  <td class="time-cell">{{ formatDateTime(entry.login_time) }}</td>
                  <td class="status-cell">
                    <v-chip size="small" :color="entry.status === 'Active' ? 'success' : 'grey'" class="status-chip">
                      <v-icon start size="14">{{ entry.status === 'Active' ? 'mdi-check-circle' : 'mdi-clock-outline' }}</v-icon>
                      {{ entry.status }}
                    </v-chip>
                  </td>
                  <td class="time-cell">{{ formatDateTime(entry.expires_at) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </v-card-text>
        <v-card-actions class="dialog-actions">
          <v-spacer></v-spacer>
          <button class="btn-secondary" @click="showLoginHistory = false">Close</button>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Active Sessions Dialog -->
    <v-dialog v-model="showActiveSessions" max-width="600" persistent>
      <v-card>
        <v-card-title class="dialog-title">
          <v-icon>mdi-devices</v-icon> Active Sessions
          <v-spacer></v-spacer>
          <button class="btn-close-dialog" @click="showActiveSessions = false">✕</button>
        </v-card-title>
        <v-card-text class="dialog-body">
          <div v-if="loadingHistory" class="text-center py-8">
            <v-progress-circular indeterminate color="primary"></v-progress-circular>
            <p class="mt-4">Loading active sessions...</p>
          </div>
          <div v-else-if="activeSessions.length === 0" class="empty-state">
            <v-icon size="48" color="#ccc">mdi-devices</v-icon>
            <p>No active sessions</p>
          </div>
          <div v-else class="sessions-list">
            <div v-for="(session, idx) in activeSessions" :key="idx" class="session-item">
              <div class="session-info">
                <div class="session-email">{{ session.email }}</div>
                <div class="session-details">
                  <span class="session-detail"><v-icon size="14">mdi-laptop</v-icon> {{ session.device }}</span>
                  <span class="session-detail"><v-icon size="14">mdi-map-marker</v-icon> {{ session.location }}</span>
                </div>
                <div class="session-time">Logged in: {{ formatDateTime(session.login_time) }}</div>
              </div>
              <button class="btn-terminate" @click="terminateSession(idx)">Terminate</button>
            </div>
          </div>
        </v-card-text>
        <v-card-actions class="dialog-actions">
          <v-spacer></v-spacer>
          <button class="btn-secondary" @click="showActiveSessions = false">Close</button>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </fixed-layout>
</template>

<script setup lang="ts">
import { ref, onMounted, reactive } from 'vue'
import { useAuthStore } from '../stores/auth'
import { userAPI, systemAPI } from '../services/api'
import FixedLayout from '../components/FixedLayout.vue'
import { API_BASE_URL } from '../config.js'

const authStore = useAuthStore()

// ========== State ==========
const user = ref({
  name: '',
  fullName: '',
  email: '',
  role: '',
  avatar: '',
  phone: ''
})

const systemInfo = ref({
  database: 'MySQL',
  apiStatus: 'Online'
})

const saving = ref({
  password: false,
  profile: false
})

const profileDialog = ref(false)
const showChangePassword = ref(false)
const showLoginHistory = ref(false)
const showActiveSessions = ref(false)
const loginHistory = ref<any[]>([])
const activeSessions = ref<any[]>([])
const loadingHistory = ref(false)

const passwordData = reactive({
  currentPassword: '',
  newPassword: '',
  confirmPassword: ''
})

const profileData = ref({
  fullName: '',
  email: '',
  phone: '',
  avatarPreview: ''
})

const avatarFileInput = ref<HTMLInputElement | null>(null)

// ========== LOAD DATA FROM BACKEND ==========
const loadSettingsData = async () => {
  try {
    const userId = authStore.user?.id || 1
    
    // 1. Profile
    const profileRes = await userAPI.getProfile(userId)
    if (profileRes?.success) {
      const data = profileRes.data
      user.value.name = data.name || ''
      user.value.fullName = data.name || ''
      user.value.email = data.email || ''
      user.value.role = data.role || 'Administrator'
      const savedAvatar = localStorage.getItem('user-avatar')
      if (savedAvatar) user.value.avatar = savedAvatar
      user.value.phone = data.phone || ''
      profileData.value = {
        fullName: user.value.fullName,
        email: user.value.email,
        phone: user.value.phone,
        avatarPreview: user.value.avatar
      }
    }

    // 2. System info
    const sysRes = await systemAPI.getInfo()
    if (sysRes?.success) {
      const s = sysRes.data
      systemInfo.value.apiStatus = s.apiStatus || 'Online'
      systemInfo.value.database = s.database || 'MySQL'
    }
  } catch (error) {
    console.error('Error loading settings:', error)
    const avatar = localStorage.getItem('user-avatar')
    if (avatar) {
      user.value.avatar = avatar
      profileData.value.avatarPreview = avatar
    }
  }
}

const changePassword = async () => {
  if (!passwordData.currentPassword || !passwordData.newPassword || !passwordData.confirmPassword) {
    alert('Please fill in all password fields')
    return
  }
  if (passwordData.newPassword !== passwordData.confirmPassword) {
    alert('New passwords do not match')
    return
  }
  if (passwordData.newPassword.length < 8) {
    alert('Password must be at least 8 characters')
    return
  }

  saving.value.password = true
  try {
    const success = await authStore.changePassword(passwordData.currentPassword, passwordData.newPassword)
    if (success) {
      alert('Password changed successfully!')
      showChangePassword.value = false
      passwordData.currentPassword = ''
      passwordData.newPassword = ''
      passwordData.confirmPassword = ''
    } else {
      alert('Failed to change password. Please check your current password.')
    }
  } catch (error) {
    alert('Error changing password. Please try again.')
  } finally {
    saving.value.password = false
  }
}

const saveProfile = async () => {
  saving.value.profile = true
  try {
    const userId = authStore.user?.id || 1
    const nameParts = profileData.value.fullName.split(' ', 2)
    const payload = {
      user_id: userId,
      first_name: nameParts[0] || '',
      last_name: nameParts[1] || '',
      email: profileData.value.email
    }
    const response = await fetch(`${API_BASE_URL}/api/user/profile?user_id=${userId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    const result = await response.json()
    if (result?.success) {
      user.value.fullName = profileData.value.fullName
      user.value.name = profileData.value.fullName
      user.value.email = profileData.value.email
      if (profileData.value.avatarPreview && profileData.value.avatarPreview !== user.value.avatar) {
        user.value.avatar = profileData.value.avatarPreview
        localStorage.setItem('user-avatar', profileData.value.avatarPreview)
      }
      alert('Profile updated successfully!')
      profileDialog.value = false
      await loadSettingsData()
    } else {
      alert('Failed to update profile.')
    }
  } catch {
    alert('Error updating profile.')
  } finally {
    saving.value.profile = false
  }
}

// ========== AVATAR UPLOAD ==========
const uploadAvatarFromDialog = () => {
  avatarFileInput.value?.click()
}

const handleAvatarFileSelect = (event: Event) => {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  if (file.size > 2 * 1024 * 1024) {
    alert('Image size must be less than 2MB.')
    input.value = ''
    return
  }
  const reader = new FileReader()
  reader.onload = (e: any) => {
    profileData.value.avatarPreview = e.target.result
    input.value = ''
  }
  reader.readAsDataURL(file)
}

const removeAvatar = () => {
  profileData.value.avatarPreview = ''
}

const loadActiveSessions = async () => {
  loadingHistory.value = true
  try {
    const token = localStorage.getItem('auth_token')
    const apiUrl = import.meta.env.VITE_API_BASE_URL || window.location.origin
    const response = await fetch(`${apiUrl}/api/active-sessions`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    const data = await response.json()
    if (data.success) {
      activeSessions.value = data.sessions || []
    }
  } catch (error) {
    console.error('Failed to load active sessions:', error)
  } finally {
    loadingHistory.value = false
  }
  showActiveSessions.value = true
}

const terminateSession = (index: number) => {
  activeSessions.value.splice(index, 1)
  alert('Session terminated.')
}

const editProfile = () => {
  profileData.value = {
    fullName: user.value.fullName || user.value.name || '',
    email: user.value.email || '',
    phone: user.value.phone || '',
    avatarPreview: user.value.avatar || ''
  }
  profileDialog.value = true
}

function formatDateTime(dateStr: string | null) {
  if (!dateStr) return 'N/A'
  return new Date(dateStr).toLocaleString()
}

async function loadLoginHistory() {
  loadingHistory.value = true
  try {
    const token = localStorage.getItem('auth_token')
    const apiUrl = import.meta.env.VITE_API_BASE_URL || window.location.origin
    const response = await fetch(`${apiUrl}/api/login-history`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    const data = await response.json()
    if (data.success) {
      loginHistory.value = data.history || []
    }
  } catch (error) {
    console.error('Failed to load login history:', error)
  } finally {
    loadingHistory.value = false
  }
}

// Watch for login history dialog to load data
import { watch } from 'vue'
watch(showLoginHistory, (newVal) => {
  if (newVal) {
    loadLoginHistory()
  }
})
watch(showActiveSessions, (newVal) => {
  if (newVal) {
    loadActiveSessions()
  }
})

onMounted(() => {
  loadSettingsData()
  if (authStore.user) {
    user.value = { ...user.value, ...authStore.user }
  }
})
</script>

<style scoped>
.settings-view {
  padding: 20px 30px;
  max-width: 1400px;
  margin: 0 auto;
}
.settings-header {
  margin-bottom: 28px;
}
.page-title {
  font-size: 28px;
  font-weight: 700;
  color: #0B2044;
  margin-bottom: 6px;
}
.page-subtitle {
  font-size: 14px;
  color: #666;
  margin: 0;
}
.settings-row {
  margin: 0 -12px !important;
  display: flex;
  align-items: stretch;
}
.settings-col {
  padding: 0 12px !important;
  display: flex;
  flex-direction: column;
}
.settings-card {
  border-radius: 16px;
  overflow: hidden;
  background: white;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
  transition: transform 0.2s, box-shadow 0.2s;
  position: relative;
  margin-bottom: 24px;
  flex: 1;
  display: flex;
  flex-direction: column;
}
.settings-card:last-child {
  margin-bottom: 0;
}
.settings-card:hover {
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.10);
  transform: translateY(-2px);
}
.settings-card .v-card-text {
  padding: 16px !important;
  flex: 1;
}
.settings-card .v-card-title {
  padding: 12px 16px 0 16px !important;
}
.card-title {
  font-size: 16px;
  font-weight: 600;
  color: #0B2044;
  display: flex;
  align-items: center;
  padding-bottom: 8px;
}
.title-icon {
  margin-right: 10px;
  color: #1E88E5;
  font-size: 22px;
}
.profile-card-text {
  padding-bottom: 12px !important;
}
.profile-col {
  margin-bottom: 20px;
  display: flex;
  justify-content: center;
  align-items: center;
}
.profile-card {
  max-width: 480px;
  width: 100%;
  border-radius: 16px;
  overflow: hidden;
  background: white;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
  transition: transform 0.2s, box-shadow 0.2s;
}
.profile-card:hover {
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.10);
  transform: translateY(-2px);
}
.profile-section {
  text-align: center;
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 0;
}
.avatar-container {
  display: inline-block;
  margin-bottom: 8px;
}
.profile-avatar {
  border: 2px solid #e8ecf1;
  background: #0B2044;
}
.profile-info {
  margin-bottom: 8px;
}
.profile-name {
  font-size: 18px;
  font-weight: 700;
  color: #0B2044;
  margin-bottom: 2px;
}
.profile-email {
  font-size: 12px;
  color: #666;
  margin-bottom: 2px;
}
.profile-role {
  font-size: 11px;
  color: #1E88E5;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 0;
}
.edit-profile-btn {
  border-radius: 6px;
  border-color: #0B2044;
  color: #0B2044;
  transition: all 0.2s;
  min-height: 28px;
  font-size: 11px;
  padding: 4px 10px;
  margin-top: 8px;
}
.edit-profile-btn:hover {
  background: #0B2044;
  color: white;
}
.info-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 0;
  border-bottom: 1px solid #f0f0f0;
}
.info-item:last-child {
  border-bottom: none;
}
.info-label {
  font-size: 12px;
  color: #666;
  font-weight: 500;
}
.info-value {
  font-size: 12px;
  color: #0B2044;
  font-weight: 600;
}
.status-chip {
  background: #E8F5E9 !important;
  color: #2E7D32 !important;
  font-weight: 600;
}
.security-btn {
  margin-bottom: 12px;
  border-radius: 8px;
  border-color: #0B2044;
  color: #0B2044;
  transition: all 0.2s;
  min-height: 40px;
  font-size: 14px;
}
.security-btn:hover {
  background: #0B2044;
  color: white;
}
.security-btn:last-child {
  margin-bottom: 0;
}
.dialog-title {
  display: flex;
  align-items: center;
  font-size: 16px;
  font-weight: 600;
  color: #0B2044;
  padding: 12px 16px;
}
.dialog-title .v-icon {
  margin-right: 8px;
  color: #1E88E5;
  font-size: 20px;
}
.btn-close-dialog {
  background: none;
  border: none;
  font-size: 18px;
  color: #999;
  cursor: pointer;
  padding: 2px 6px;
  transition: color 0.2s;
}
.btn-close-dialog:hover {
  color: #333;
}
.dialog-body {
  padding: 16px;
}
.dialog-actions {
  padding: 10px 16px;
  border-top: 1px solid #e0e0e0;
  display: flex;
  gap: 8px;
}
.btn-primary {
  background: #0B2044;
  color: white;
  border: none;
  border-radius: 6px;
  padding: 6px 16px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
}
.btn-primary:hover {
  background: #1a3a6e;
}
.btn-secondary {
  background: white;
  color: #0B2044;
  border: 1px solid #0B2044;
  border-radius: 6px;
  padding: 6px 16px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}
.btn-secondary:hover {
  background: #f5f5f5;
}
.empty-state {
  text-align: center;
  padding: 32px 16px;
  color: #999;
}
.empty-state p {
  margin-top: 8px;
  font-size: 13px;
}
.history-table-container {
  overflow-x: auto;
}
.history-table {
  width: 100%;
  border-collapse: collapse;
}
.history-table th {
  text-align: left;
  padding: 12px;
  background: #f5f5f5;
  font-size: 13px;
  font-weight: 600;
  color: #0B2044;
  border-bottom: 2px solid #e0e0e0;
}
.history-table td {
  padding: 12px;
  border-bottom: 1px solid #e0e0e0;
  font-size: 13px;
  color: #333;
}
.history-table tr.active-row {
  background: #E8F5E9;
}
.email-cell {
  font-weight: 500;
  color: #0B2044;
}
.time-cell {
  color: #666;
  font-size: 12px;
}
.status-cell {
  padding: 8px;
}
.sessions-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.session-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  background: #f9fafc;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
}
.session-info {
  flex: 1;
}
.session-email {
  font-weight: 600;
  color: #0B2044;
  margin-bottom: 8px;
  font-size: 14px;
}
.session-details {
  display: flex;
  gap: 16px;
  margin-bottom: 8px;
}
.session-detail {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #666;
}
.session-time {
  font-size: 12px;
  color: #999;
}
.btn-terminate {
  background: #ffebee;
  color: #c62828;
  border: none;
  border-radius: 6px;
  padding: 6px 12px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
}
.btn-terminate:hover {
  background: #ffcdd2;
}
</style>