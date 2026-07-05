<template>
  <fixed-layout>
    <div class="settings-view">
      <!-- Header Section -->
      <div class="settings-header">
        <h1 class="page-title">System Settings</h1>
        <p class="page-subtitle">Manage your account settings and security</p>
      </div>

      <!-- Settings Content – equal height columns -->
      <v-row class="settings-row" align="stretch">
        <!-- Left Column -->
        <v-col cols="12" md="4" class="settings-col">
          <!-- Profile Card -->
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

          <!-- System Information Card -->
          <v-card class="settings-card info-card">
            <div class="card-accent"></div>
            <v-card-title class="card-title">
              <v-icon class="title-icon">mdi-information</v-icon>
              System Information
            </v-card-title>
            <v-card-text>
              <div class="info-item">
                <span class="info-label">Last Updated</span>
                <span class="info-value">{{ systemInfo.lastUpdated || 'Loading...' }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">Database</span>
                <span class="info-value">{{ systemInfo.database || 'MySQL' }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">API Status</span>
                <v-chip size="small" color="success" class="status-chip">
                  {{ systemInfo.apiStatus || 'Online' }}
                </v-chip>
              </div>
            </v-card-text>
          </v-card>
        </v-col>

        <!-- Right Column -->
        <v-col cols="12" md="8" class="settings-col">
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
                @click="loadLoginHistory"
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

          <!-- Notifications Card -->
          <v-card class="settings-card notifications-card">
            <div class="card-accent"></div>
            <v-card-title class="card-title">
              <v-icon class="title-icon">mdi-bell</v-icon>
              Notifications
            </v-card-title>
            <v-card-text>
              <div class="notification-toggle-wrapper">
                <div class="toggle-content">
                  <div class="toggle-icon">
                    <v-icon size="28" :color="notifications.enabled ? '#1E88E5' : '#999'">
                      {{ notifications.enabled ? 'mdi-bell-ring' : 'mdi-bell-off' }}
                    </v-icon>
                  </div>
                  <div class="toggle-info">
                    <div class="toggle-title">Enable Notifications</div>
                  </div>
                  <div class="toggle-switch">
                    <v-switch
                      v-model="notifications.enabled"
                      color="primary"
                      inset
                      hide-details
                      class="master-switch"
                      @update:model-value="saveNotifications"
                    />
                  </div>
                </div>
              </div>
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

    <!-- Login History Dialog -->
    <v-dialog v-model="showLoginHistory" max-width="650px" persistent>
      <v-card>
        <v-card-title class="dialog-title">
          <v-icon>mdi-history</v-icon> Login History
          <v-spacer></v-spacer>
          <button class="btn-close-dialog" @click="showLoginHistory = false">✕</button>
        </v-card-title>
        <v-card-text class="dialog-body">
          <div class="history-list-container">
            <div v-if="loginHistory.length === 0" class="empty-history">
              <v-icon size="36" color="#ccc">mdi-file-document-outline</v-icon>
              <p>No login history found.</p>
            </div>
            <div v-else class="history-list">
              <div v-for="(entry, idx) in loginHistory" :key="idx" class="history-entry">
                <div class="history-entry-header">
                  <div class="history-entry-time">{{ formatDate(entry.timestamp) }}</div>
                  <div class="history-entry-badge" :class="entry.status === 'Success' ? 'badge-success' : 'badge-failed'">
                    {{ entry.status }}
                  </div>
                </div>
                <div class="history-entry-details">
                  <div class="history-entry-row">
                    <span class="label">IP Address</span>
                    <span class="value">{{ entry.ip }}</span>
                  </div>
                  <div class="history-entry-row">
                    <span class="label">Location</span>
                    <span class="value">{{ entry.location || '—' }}</span>
                  </div>
                  <div class="history-entry-row">
                    <span class="label">Device</span>
                    <span class="value">{{ entry.device || '—' }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </v-card-text>
        <v-card-actions class="dialog-actions">
          <v-spacer></v-spacer>
          <button class="btn-secondary" @click="showLoginHistory = false">Close</button>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Active Sessions Dialog -->
    <v-dialog v-model="showActiveSessions" max-width="650px" persistent>
      <v-card>
        <v-card-title class="dialog-title">
          <v-icon>mdi-devices</v-icon> Active Sessions
          <v-spacer></v-spacer>
          <button class="btn-close-dialog" @click="showActiveSessions = false">✕</button>
        </v-card-title>
        <v-card-text class="dialog-body">
          <div class="history-list-container">
            <div v-if="activeSessions.length === 0" class="empty-history">
              <v-icon size="36" color="#ccc">mdi-device-off</v-icon>
              <p>No active sessions found.</p>
            </div>
            <div v-else class="history-list">
              <div v-for="(session, idx) in activeSessions" :key="idx" class="history-entry">
                <div class="history-entry-header">
                  <div class="history-entry-time">{{ formatDate(session.lastActive) }}</div>
                  <div class="history-entry-badge badge-active">Active</div>
                </div>
                <div class="history-entry-details">
                  <div class="history-entry-row">
                    <span class="label">Device</span>
                    <span class="value">{{ session.device }}</span>
                  </div>
                  <div class="history-entry-row">
                    <span class="label">Location</span>
                    <span class="value">{{ session.location }}</span>
                  </div>
                  <div class="history-entry-row">
                    <span class="label">IP Address</span>
                    <span class="value">{{ session.ip }}</span>
                  </div>
                </div>
                <div class="history-entry-actions">
                  <button class="btn-terminate" @click="terminateSession(idx)">Terminate</button>
                </div>
              </div>
            </div>
          </div>
        </v-card-text>
        <v-card-actions class="dialog-actions">
          <v-spacer></v-spacer>
          <button class="btn-secondary" @click="showActiveSessions = false">Close</button>
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

const notifications = ref({
  enabled: true
})

const systemInfo = ref({
  lastUpdated: '',
  database: 'MySQL',
  apiStatus: 'Online'
})

const saving = ref({
  notifications: false,
  password: false,
  profile: false
})

const profileDialog = ref(false)
const showChangePassword = ref(false)
const showLoginHistory = ref(false)
const showActiveSessions = ref(false)

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

const loginHistory = ref<any[]>([])
const activeSessions = ref<any[]>([])

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

    // 2. Notification settings
    const notifRes = await userAPI.getNotificationSettings(userId)
    if (notifRes?.success) {
      const n = notifRes.data
      notifications.value.enabled = n.emailNotifications ?? true
    }

    // 3. System info
    const sysRes = await systemAPI.getInfo()
    if (sysRes?.success) {
      const s = sysRes.data
      systemInfo.value.lastUpdated = s.last_updated || '—'
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

// ========== SAVE FUNCTIONS ==========
const saveNotifications = async () => {
  saving.value.notifications = true
  try {
    const userId = authStore.user?.id || 1
    const payload = {
      user_id: userId,
      emailNotifications: notifications.value.enabled,
      pushNotifications: false,
      weeklyReports: true,
      systemAlerts: true
    }
    const response = await fetch(`${API_BASE_URL}/api/user/preferences?user_id=${userId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    const result = await response.json()
    if (!result?.success) {
      notifications.value.enabled = !notifications.value.enabled
      alert('Failed to save notification settings.')
    }
  } catch {
    notifications.value.enabled = !notifications.value.enabled
    alert('Error saving notification settings.')
  } finally {
    saving.value.notifications = false
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
    const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/api/user/profile?user_id=${userId}`, {
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

// ========== SECURITY ==========
const changePassword = async () => {
  if (passwordData.newPassword !== passwordData.confirmPassword) {
    alert('Passwords do not match.')
    return
  }
  if (passwordData.newPassword.length < 8) {
    alert('Password must be at least 8 characters.')
    return
  }
  saving.value.password = true
  try {
    const response = await userAPI.changePassword({
      currentPassword: passwordData.currentPassword,
      newPassword: passwordData.newPassword
    })
    if (response?.success) {
      alert('Password changed successfully!')
      showChangePassword.value = false
      passwordData.currentPassword = ''
      passwordData.newPassword = ''
      passwordData.confirmPassword = ''
    } else {
      alert(response?.message || 'Failed to change password.')
    }
  } catch {
    alert('Error changing password.')
  } finally {
    saving.value.password = false
  }
}

// ===== Mock data for login history & active sessions (backend not implemented yet) =====
const loadLoginHistory = () => {
  loginHistory.value = [
    { timestamp: new Date().toISOString(), ip: '192.168.1.1', location: 'Harare, Zimbabwe', device: 'Chrome on Windows', status: 'Success' },
    { timestamp: new Date(Date.now() - 86400000).toISOString(), ip: '192.168.1.1', location: 'Harare, Zimbabwe', device: 'Firefox on Windows', status: 'Success' }
  ]
  showLoginHistory.value = true
}

const loadActiveSessions = () => {
  activeSessions.value = [
    { device: 'Chrome on Windows', location: 'Harare, Zimbabwe', ip: '192.168.1.1', lastActive: new Date().toISOString() }
  ]
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

const formatDate = (timestamp: string) => {
  if (!timestamp) return ''
  try { return new Date(timestamp).toLocaleString() } catch { return timestamp }
}

onMounted(() => {
  loadSettingsData()
  if (authStore.user) {
    user.value = { ...user.value, ...authStore.user }
  }
})
</script>

<style scoped>
/* ===== LAYOUT ===== */
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

/* ===== ROW & COLUMN – EQUAL HEIGHT ===== */
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

/* ===== CARDS ===== */
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

.card-accent {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(90deg, #0B2044, #1E88E5);
  border-radius: 16px 16px 0 0;
}

.settings-card .v-card-text {
  padding: 20px !important;
  flex: 1;
}

.settings-card .v-card-title {
  padding: 16px 20px 4px 20px !important;
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

/* ===== PROFILE CARD ===== */
.profile-card-text {
  padding-bottom: 20px !important;
}

.profile-section {
  text-align: center;
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 4px 0;
}

.avatar-container {
  display: inline-block;
  margin-bottom: 12px;
}

.profile-avatar {
  border: 3px solid #e8ecf1;
  background: #0B2044;
}

.profile-info {
  margin-bottom: 10px;
}

.profile-name {
  font-size: 20px;
  font-weight: 700;
  color: #0B2044;
  margin-bottom: 2px;
}

.profile-email {
  font-size: 13px;
  color: #666;
  margin-bottom: 2px;
}

.profile-role {
  font-size: 12px;
  color: #1E88E5;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 0;
}

/* ===== SMALLER EDIT PROFILE BUTTON ===== */
.edit-profile-btn {
  border-radius: 8px;
  border-color: #0B2044;
  color: #0B2044;
  transition: all 0.2s;
  min-height: 30px;
  font-size: 12px;
  padding: 4px 12px;
  margin-top: 4px;
}

.edit-profile-btn:hover {
  background: #0B2044;
  color: white;
}

/* ===== SYSTEM INFO ===== */
.info-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid #f0f0f0;
}

.info-item:last-child {
  border-bottom: none;
}

.info-label {
  font-size: 13px;
  color: #666;
  font-weight: 500;
}

.info-value {
  font-size: 13px;
  color: #0B2044;
  font-weight: 600;
}

.status-chip {
  background: #E8F5E9 !important;
  color: #2E7D32 !important;
  font-weight: 600;
}

/* ===== SECURITY CARD ===== */
.security-card .v-card-text {
  padding-top: 4px !important;
}

.security-btn {
  justify-content: flex-start;
  border-radius: 10px;
  border-color: #e0e0e0;
  margin-bottom: 10px;
  padding: 10px 16px;
  min-height: 44px;
  font-size: 14px;
  transition: all 0.2s;
}

.security-btn:last-child {
  margin-bottom: 0;
}

.security-btn:hover {
  border-color: #0B2044;
  background: rgba(11, 32, 68, 0.04);
}

/* ===== NOTIFICATIONS ===== */
.notification-toggle-wrapper {
  background: #f8f9ff;
  border-radius: 12px;
  padding: 16px 20px;
  border: 1px solid #e8ecf1;
}

.toggle-content {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.toggle-icon {
  flex-shrink: 0;
}

.toggle-info {
  flex: 1;
  min-width: 120px;
}

.toggle-title {
  font-size: 15px;
  font-weight: 600;
  color: #0B2044;
}

.toggle-switch {
  flex-shrink: 0;
}

.master-switch {
  margin: 0;
}

/* ===== DIALOGS ===== */
.dialog-title {
  background: #0B2044;
  color: white;
  padding: 14px 20px;
  display: flex;
  align-items: center;
  font-size: 18px;
}

.btn-close-dialog {
  background: transparent;
  border: none;
  color: white;
  cursor: pointer;
  padding: 6px;
  border-radius: 50%;
  transition: background 0.2s;
  font-size: 18px;
}

.btn-close-dialog:hover {
  background: rgba(255,255,255,0.1);
}

.dialog-body {
  padding: 20px;
  max-height: 70vh;
  overflow-y: auto;
}

.dialog-body::-webkit-scrollbar {
  width: 6px;
}

.dialog-body::-webkit-scrollbar-track {
  background: #f0f0f0;
  border-radius: 4px;
}

.dialog-body::-webkit-scrollbar-thumb {
  background: #0B2044;
  border-radius: 4px;
}

.dialog-actions {
  padding: 8px 16px 12px;
  border-top: 1px solid #e8ecf1;
}

.btn-secondary {
  background: white;
  color: #0B2044;
  border: 2px solid #0B2044;
  padding: 6px 20px;
  border-radius: 30px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-secondary:hover {
  background: #0B2044;
  color: white;
}

.btn-primary {
  background: linear-gradient(135deg, #0B2044, #1E88E5);
  color: white;
  border: none;
  padding: 6px 20px;
  border-radius: 30px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(11, 32, 68, 0.3);
}

/* ===== DIALOG AVATAR ===== */
.dialog-avatar-section {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 4px 0;
}

.dialog-avatar {
  border: 3px solid #e8ecf1;
  background: #0B2044;
}

.dialog-avatar-actions {
  display: flex;
  gap: 8px;
}

.dialog-avatar-actions .v-btn {
  font-size: 12px;
  padding: 4px 12px;
  min-height: 30px;
  border-radius: 6px;
}

/* ===== HISTORY LISTS ===== */
.history-list-container {
  max-height: 400px;
  overflow-y: auto;
}

.history-list-container::-webkit-scrollbar {
  width: 6px;
}

.history-list-container::-webkit-scrollbar-track {
  background: #f0f0f0;
  border-radius: 4px;
}

.history-list-container::-webkit-scrollbar-thumb {
  background: #0B2044;
  border-radius: 4px;
}

.empty-history {
  text-align: center;
  padding: 40px 0;
  color: #999;
}

.empty-history p {
  margin-top: 8px;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.history-entry {
  background: #f8f9ff;
  border-radius: 8px;
  padding: 10px 14px;
  border: 1px solid #e8ecf1;
  transition: all 0.2s;
}

.history-entry:hover {
  border-color: #0B2044;
}

.history-entry-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.history-entry-time {
  font-size: 12px;
  font-weight: 600;
  color: #0B2044;
}

.history-entry-badge {
  padding: 2px 12px;
  border-radius: 30px;
  font-size: 10px;
  font-weight: 600;
  color: white;
  text-transform: uppercase;
}

.badge-success {
  background: #4CAF50;
}

.badge-failed {
  background: #f44336;
}

.badge-active {
  background: #1E88E5;
}

.history-entry-details {
  font-size: 12px;
  color: #555;
}

.history-entry-row {
  display: flex;
  align-items: baseline;
  margin-bottom: 2px;
}

.history-entry-row .label {
  width: 72px;
  font-weight: 600;
  color: #0B2044;
  font-size: 11px;
  flex-shrink: 0;
}

.history-entry-row .value {
  color: #333;
}

.history-entry-actions {
  margin-top: 6px;
  display: flex;
  justify-content: flex-end;
}

.btn-terminate {
  background: #f44336;
  color: white;
  border: none;
  padding: 2px 14px;
  border-radius: 30px;
  font-size: 10px;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-terminate:hover {
  background: #d32f2f;
}

/* ===== RESPONSIVE ===== */
@media (max-width: 960px) {
  .settings-view {
    padding: 16px;
  }
  .settings-col {
    padding: 0 8px !important;
  }
  .settings-card {
    margin-bottom: 16px;
  }
}

@media (max-width: 600px) {
  .settings-view {
    padding: 12px;
  }
  .settings-card {
    border-radius: 12px;
  }
  .page-title {
    font-size: 24px;
  }
  .settings-col {
    padding: 0 4px !important;
  }
  .settings-card .v-card-text {
    padding: 16px !important;
  }
  .info-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 2px;
  }
  .dialog-title {
    font-size: 16px;
    padding: 10px 14px;
  }
  .dialog-body {
    padding: 14px;
  }
  .toggle-content {
    flex-wrap: wrap;
    justify-content: center;
    text-align: center;
  }
  .toggle-info {
    min-width: 100%;
    text-align: center;
  }
}
</style>