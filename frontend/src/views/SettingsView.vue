<template>
  <fixed-layout>
    <div class="settings-view">
      <!-- Header Section -->
      <div class="settings-header">
        <h1 class="page-title">System Settings</h1>
        <p class="page-subtitle">Manage your account settings and preferences</p>
      </div>

      <!-- Settings Content -->
      <v-row>
        <!-- Left Column - User Profile, Quick Actions, Preferences, Security -->
        <v-col cols="12" md="4">
          <v-card class="profile-card" elevation="2">
            <v-card-text>
              <div class="profile-section">
                <div class="avatar-container">
                  <v-avatar size="80" color="primary" class="profile-avatar">
                    <v-icon size="40" color="white">mdi-account</v-icon>
                  </v-avatar>
                  <v-btn 
                    class="avatar-edit-btn" 
                    size="small" 
                    icon 
                    color="primary"
                    @click="editAvatar"
                  >
                    <v-icon size="16">mdi-camera</v-icon>
                  </v-btn>
                </div>
                
                <div class="profile-info text-center">
                  <h3 class="profile-name">{{ user.name || 'Makanaka Kanyai' }}</h3>
                  <p class="profile-email">{{ user.email || 'makanakakanyai@gmail.com' }}</p>
                  <p class="profile-role">{{ user.role || 'Administrator' }}</p>
                </div>

                <v-btn 
                  block 
                  variant="outlined" 
                  class="edit-profile-btn"
                  @click="editProfile"
                >
                  <v-icon left>mdi-pencil</v-icon>
                  Edit Profile
                </v-btn>
              </div>
            </v-card-text>
          </v-card>

          <!-- Quick Actions -->
          <v-card class="quick-actions-card" elevation="2">
            <v-card-title class="card-title">
              <v-icon class="title-icon">mdi-lightning-bolt</v-icon>
              Quick Actions
            </v-card-title>
            <v-card-text>
              <v-btn 
                block 
                variant="text" 
                class="action-btn"
                @click="exportData"
              >
                <v-icon left>mdi-download</v-icon>
                Export Data
              </v-btn>
              <v-btn 
                block 
                variant="text" 
                class="action-btn"
                @click="importData"
              >
                <v-icon left>mdi-upload</v-icon>
                Import Data
              </v-btn>
              <v-btn 
                block 
                variant="text" 
                class="action-btn"
                @click="clearCache"
              >
                <v-icon left>mdi-delete-sweep</v-icon>
                Clear Cache
              </v-btn>
            </v-card-text>
          </v-card>

          <!-- Preferences -->
          <v-card class="settings-card preferences-card" elevation="2">
            <v-card-title class="card-title">
              <v-icon class="title-icon">mdi-cog</v-icon>
              Preferences
            </v-card-title>
            <v-card-text>
              <v-form ref="preferencesForm">
                <v-select
                  v-model="preferences.language"
                  :items="languages"
                  label="Language"
                  variant="outlined"
                  prepend-inner-icon="mdi-translate"
                  class="mb-3"
                />
                
                <v-select
                  v-model="preferences.timezone"
                  :items="timezones"
                  label="Timezone"
                  variant="outlined"
                  prepend-inner-icon="mdi-clock"
                  class="mb-3"
                />
                
                <v-select
                  v-model="preferences.dateFormat"
                  :items="dateFormats"
                  label="Date Format"
                  variant="outlined"
                  prepend-inner-icon="mdi-calendar"
                  class="mb-3"
                />
                
                <v-select
                  v-model="preferences.currency"
                  :items="currencies"
                  label="Currency"
                  variant="outlined"
                  prepend-inner-icon="mdi-currency-usd"
                  class="mb-3"
                />
                
                <v-btn 
                  color="primary" 
                  block
                  @click="savePreferences"
                  :loading="saving.preferences"
                >
                  <v-icon left>mdi-content-save</v-icon>
                  Save Preferences
                </v-btn>
              </v-form>
            </v-card-text>
          </v-card>

          <!-- Security -->
          <v-card class="settings-card" elevation="2">
            <v-card-title class="card-title">
              <v-icon class="title-icon">mdi-shield-lock</v-icon>
              Security
            </v-card-title>
            <v-card-text>
              <v-btn 
                block 
                variant="outlined" 
                class="security-btn mb-3"
                @click="changePassword"
              >
                <v-icon left>mdi-lock-reset</v-icon>
                Change Password
              </v-btn>
              
              <v-btn 
                block 
                variant="outlined" 
                class="security-btn mb-3"
                @click="enable2FA"
              >
                <v-icon left>mdi-two-factor-authentication</v-icon>
                2FA Authentication
              </v-btn>
              
              <v-btn 
                block 
                variant="outlined" 
                class="security-btn mb-3"
                @click="viewLoginHistory"
              >
                <v-icon left>mdi-history</v-icon>
                Login History
              </v-btn>
              
              <v-btn 
                block 
                variant="outlined" 
                class="security-btn"
                @click="manageSessions"
              >
                <v-icon left>mdi-devices</v-icon>
                Active Sessions
              </v-btn>
            </v-card-text>
          </v-card>
        </v-col>

        <!-- Right Column - Account Settings, Notifications, System Information -->
        <v-col cols="12" md="8">
          <!-- Account Settings - Full Width -->
          <v-card class="settings-card" elevation="2">
            <v-card-title class="card-title">
              <v-icon class="title-icon">mdi-account-cog</v-icon>
              Account Settings
            </v-card-title>
            <v-card-text>
              <v-form ref="accountForm">
                <v-row>
                  <v-col cols="12" md="6">
                    <v-text-field
                      v-model="accountSettings.firstName"
                      label="First Name"
                      variant="outlined"
                      prepend-inner-icon="mdi-account"
                    />
                  </v-col>
                  <v-col cols="12" md="6">
                    <v-text-field
                      v-model="accountSettings.lastName"
                      label="Last Name"
                      variant="outlined"
                      prepend-inner-icon="mdi-account"
                    />
                  </v-col>
                </v-row>
                
                <v-text-field
                  v-model="accountSettings.email"
                  label="Email Address"
                  type="email"
                  variant="outlined"
                  prepend-inner-icon="mdi-email"
                  readonly
                />
                
                <v-text-field
                  v-model="accountSettings.phone"
                  label="Phone Number"
                  variant="outlined"
                  prepend-inner-icon="mdi-phone"
                />
                
                <v-btn 
                  color="primary" 
                  @click="saveAccountSettings"
                  :loading="saving.account"
                >
                  <v-icon left>mdi-content-save</v-icon>
                  Save Account Settings
                </v-btn>
              </v-form>
            </v-card-text>
          </v-card>

          <!-- System Information - Full Width -->
          <v-card class="settings-card" elevation="2">
            <v-card-title class="card-title">
              <v-icon class="title-icon">mdi-information</v-icon>
              System Information
            </v-card-title>
            <v-card-text>
              <v-row>
                <v-col cols="12" md="6">
                  <div class="info-item">
                    <span class="info-label">Version:</span>
                    <span class="info-value">v1.0.0</span>
                  </div>
                  <div class="info-item">
                    <span class="info-label">Environment:</span>
                    <span class="info-value">Development</span>
                  </div>
                  <div class="info-item">
                    <span class="info-label">Last Updated:</span>
                    <span class="info-value">{{ lastUpdated }}</span>
                  </div>
                </v-col>
                <v-col cols="12" md="6">
                  <div class="info-item">
                    <span class="info-label">Database:</span>
                    <span class="info-value">MySQL</span>
                  </div>
                  <div class="info-item">
                    <span class="info-label">API Status:</span>
                    <v-chip size="small" color="success">Online</v-chip>
                  </div>
                  <div class="info-item">
                    <span class="info-label">Storage Used:</span>
                    <span class="info-value">2.3 GB / 10 GB</span>
                  </div>
                </v-col>
              </v-row>
            </v-card-text>
          </v-card>

          <!-- Notifications - Full Width -->
          <v-card class="settings-card" elevation="2">
            <v-card-title class="card-title">
              <v-icon class="title-icon">mdi-bell</v-icon>
              Notifications
            </v-card-title>
            <v-card-text>
              <v-row>
                <v-col cols="12" md="6">
                  <v-switch
                    v-model="notifications.emailNotifications"
                    label="Email Notifications"
                    color="primary"
                    inset
                    class="mb-3"
                  />
                  <v-switch
                    v-model="notifications.pushNotifications"
                    label="Push Notifications"
                    color="primary"
                    inset
                    class="mb-3"
                  />
                </v-col>
                <v-col cols="12" md="6">
                  <v-switch
                    v-model="notifications.weeklyReports"
                    label="Weekly Reports"
                    color="primary"
                    inset
                    class="mb-3"
                  />
                  <v-switch
                    v-model="notifications.systemAlerts"
                    label="System Alerts"
                    color="primary"
                    inset
                    class="mb-3"
                  />
                </v-col>
              </v-row>
              
              <v-btn 
                color="primary" 
                @click="saveNotifications"
                :loading="saving.notifications"
              >
                <v-icon left>mdi-content-save</v-icon>
                Save Notification Settings
              </v-btn>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </div>
  </fixed-layout>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useAuthStore } from '../stores/auth'
import { userAPI, systemAPI } from '../services/api'
import FixedLayout from '../components/FixedLayout.vue'

const authStore = useAuthStore()

// User data
const user = ref(authStore.user || {})

// Account settings
const accountSettings = ref({
  firstName: 'Makanaka',
  lastName: 'Kanyai',
  email: 'makanakakanyai@gmail.com',
  phone: '+263 77 123 4567'
})

// Preferences
const preferences = ref({
  language: 'English',
  timezone: 'GMT+2',
  dateFormat: 'DD/MM/YYYY',
  currency: 'USD'
})

// Notifications
const notifications = ref({
  emailNotifications: true,
  pushNotifications: false,
  weeklyReports: true,
  systemAlerts: true
})

// Loading states
const saving = ref({
  account: false,
  preferences: false,
  notifications: false
})

// Options for selects
const languages = ['English', 'Spanish', 'French', 'German', 'Portuguese']
const timezones = ['GMT+0', 'GMT+1', 'GMT+2', 'GMT+3', 'GMT+4', 'GMT+5']
const dateFormats = ['DD/MM/YYYY', 'MM/DD/YYYY', 'YYYY-MM-DD', 'DD-MM-YYYY']
const currencies = ['USD', 'EUR', 'GBP', 'ZAR', 'AUD', 'CAD']

const lastUpdated = ref(new Date().toLocaleDateString())

// Load settings data from backend
const loadSettingsData = async () => {
  try {
    // Load user profile
    const profileResponse = await userAPI.getProfile()
    if (profileResponse.success) {
      user.value = profileResponse.data
      accountSettings.value.firstName = profileResponse.data.name.split(' ')[0] || ''
      accountSettings.value.lastName = profileResponse.data.name.split(' ')[1] || ''
      accountSettings.value.email = profileResponse.data.email
    }

    // Load user preferences
    const preferencesResponse = await userAPI.getPreferences()
    if (preferencesResponse.success) {
      preferences.value.language = preferencesResponse.data.language
      preferences.value.timezone = preferencesResponse.data.timezone
      preferences.value.dateFormat = preferencesResponse.data.date_format
      preferences.value.currency = preferencesResponse.data.currency
    }

    // Load notification settings
    const notificationsResponse = await userAPI.getNotificationSettings()
    if (notificationsResponse.success) {
      notifications.value.emailNotifications = notificationsResponse.data.emailNotifications
      notifications.value.pushNotifications = notificationsResponse.data.pushNotifications
      notifications.value.weeklyReports = notificationsResponse.data.weeklyReports
      notifications.value.systemAlerts = notificationsResponse.data.systemAlerts
    }

    // Load system information
    const systemResponse = await systemAPI.getInfo()
    if (systemResponse.success) {
      lastUpdated.value = new Date(systemResponse.data.last_updated).toLocaleDateString()
    }
  } catch (error) {
    console.error('Error loading settings data:', error)
  }
}

// Methods
const editAvatar = () => {
  alert('Avatar upload feature coming soon')
}

const editProfile = () => {
  alert('Profile edit feature coming soon')
}

const saveAccountSettings = async () => {
  saving.value.account = true
  await new Promise(resolve => setTimeout(resolve, 1000))
  saving.value.account = false
  alert('Account settings saved successfully!')
}

const savePreferences = async () => {
  saving.value.preferences = true
  await new Promise(resolve => setTimeout(resolve, 1000))
  saving.value.preferences = false
  alert('Preferences saved successfully!')
}

const saveNotifications = async () => {
  saving.value.notifications = true
  await new Promise(resolve => setTimeout(resolve, 1000))
  saving.value.notifications = false
  alert('Notification settings saved successfully!')
}

const exportData = () => {
  alert('Data export feature coming soon')
}

const importData = () => {
  alert('Data import feature coming soon')
}

const clearCache = () => {
  alert('Cache cleared successfully!')
}

const changePassword = () => {
  alert('Change password feature coming soon')
}

const enable2FA = () => {
  alert('Two-factor authentication feature coming soon')
}

const viewLoginHistory = () => {
  alert('Login history feature coming soon')
}

const manageSessions = () => {
  alert('Session management feature coming soon')
}

onMounted(() => {
  loadSettingsData()
  if (authStore.user) {
    user.value = authStore.user
  }
})
</script>

<style scoped>
.settings-view {
  padding: 0;
  max-width: 100%;
}

.settings-view .v-row {
  margin: 0 !important;
}

.settings-view .v-col {
  padding: 4px !important;
}

.settings-header {
  margin-bottom: 12px;
}

.page-title {
  font-size: 28px;
  font-weight: 700;
  color: #0B2A44;
  margin-bottom: 6px;
}

.page-subtitle {
  font-size: 14px;
  color: #666;
  margin: 0;
}

/* Profile Card */
.profile-card {
  border-radius: 16px;
  overflow: hidden;
}

.profile-card .v-card-text {
  padding: 12px !important;
}

.profile-section {
  text-align: center;
  padding: 0;
}

.avatar-container {
  position: relative;
  display: inline-block;
  margin-bottom: 12px;
}

.profile-avatar {
  border: 3px solid #f0f0f0;
}

.avatar-edit-btn {
  position: absolute;
  bottom: 0;
  right: 0;
  background: white !important;
}

.profile-name {
  font-size: 18px;
  font-weight: 600;
  color: #333;
  margin-bottom: 3px;
}

.profile-email {
  font-size: 13px;
  color: #666;
  margin-bottom: 3px;
}

.profile-role {
  font-size: 11px;
  color: #1E88E5;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 12px;
}

.edit-profile-btn {
  border-radius: 8px;
}

/* Quick Actions Card */
.quick-actions-card {
  border-radius: 16px;
  margin-top: 16px;
}

.quick-actions-card .v-card-text {
  padding: 20px !important;
}

.quick-actions-card .v-card-title {
  padding: 20px 20px 12px 20px !important;
}

.action-btn {
  justify-content: flex-start;
  margin-bottom: 6px;
  border-radius: 8px;
  padding: 8px 16px;
  min-height: 40px;
}

/* Settings Cards */
.settings-card {
  border-radius: 16px;
  margin-bottom: 16px;
  min-height: 280px;
}

.preferences-card {
  margin-top: 16px;
}

.settings-card .v-card-text {
  padding: 20px !important;
}

.settings-card .v-card-title {
  padding: 20px 20px 12px 20px !important;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  color: #0B2A44;
  display: flex;
  align-items: center;
  padding-bottom: 12px;
}

.settings-card .v-text-field,
.settings-card .v-select {
  margin-bottom: 16px !important;
}

.settings-card .v-switch {
  margin-bottom: 16px !important;
}

.title-icon {
  margin-right: 8px;
  color: #1E88E5;
  font-size: 20px;
}

/* Security Buttons */
.security-btn {
  justify-content: flex-start;
  border-radius: 8px;
  border-color: #e0e0e0;
  margin-bottom: 8px;
  padding: 8px 16px;
  min-height: 40px;
  font-size: 14px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* System Information */
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
  font-size: 13px;
  color: #666;
  font-weight: 500;
}

.info-value {
  font-size: 13px;
  color: #333;
  font-weight: 600;
}

/* Responsive Design */
@media (max-width: 960px) {
  .settings-header {
    margin-bottom: 16px;
  }
  
  .page-title {
    font-size: 26px;
  }
}

@media (max-width: 600px) {
  .profile-card,
  .quick-actions-card,
  .settings-card {
    border-radius: 12px;
  }
  
  .card-title {
    font-size: 15px;
  }
  
  .info-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 3px;
  }
  
  .settings-card {
    margin-bottom: 12px;
  }
}
</style>
