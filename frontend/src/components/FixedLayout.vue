<template>
  <v-app>
    <!-- Fixed Sidebar -->
    <v-navigation-drawer app v-model="drawer" color="#0B2A44" dark permanent>
      <v-list>
        <v-list-item class="mb-4">
          <v-list-item-title class="text-h6 font-weight-bold">
            DuraCapital
          </v-list-item-title>
        </v-list-item>

        <v-list-item
          v-for="item in menu"
          :key="item.title"
          :to="item.route"
          router
          :class="{ 'v-list-item--active': $route.path === item.route }"
        >
          <template #prepend>
            <v-icon>{{ item.icon }}</v-icon>
          </template>
          <v-list-item-title>{{ item.title }}</v-list-item-title>
        </v-list-item>
      </v-list>
    </v-navigation-drawer>

    <!-- Top bar -->
    <v-app-bar app color="white" elevation="1">
      <v-app-bar-nav-icon @click="drawer = !drawer" />
      <v-spacer />

      <v-btn icon @click="handleNotifications">
        <v-icon>mdi-bell</v-icon>
      </v-btn>

      <v-btn icon @click="handleProfile">
        <v-icon>mdi-account-circle</v-icon>
      </v-btn>

      <v-btn icon @click="handleLogout" color="error">
        <v-icon>mdi-logout</v-icon>
      </v-btn>
    </v-app-bar>

    <!-- Page content -->
    <v-main>
      <v-container fluid class="pa-6">
        <slot />
      </v-container>
    </v-main>
  </v-app>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const drawer = ref(true)

const menu = [
  { title: 'Dashboard', icon: 'mdi-view-dashboard', route: '/dashboard' },
  { title: 'Upload', icon: 'mdi-upload', route: '/upload' },
  { title: 'Cleaning', icon: 'mdi-broom', route: '/cleaning' },
  { title: 'Calculations', icon: 'mdi-calculator', route: '/calculations' },
  { title: 'Reports', icon: 'mdi-file-document', route: '/reports' },
  { title: 'Visualizations', icon: 'mdi-chart-line', route: '/visualizations' },
  { title: 'Settings', icon: 'mdi-cog', route: '/settings' }
]

const handleNotifications = () => {
  // Navigate to notifications page or show notifications dropdown
  // For now, navigate to settings where notifications are located
  router.push('/settings')
}

const handleProfile = () => {
  // Navigate to user profile section in settings
  router.push('/settings')
}

const handleLogout = () => {
  // Use the auth store logout function to properly clear authentication state
  authStore.logout()
  
  // Clear additional stored data
  localStorage.removeItem('rememberMe')
  localStorage.removeItem('email')
  
  // Navigate to login page
  router.push('/login')
}
</script>

<style scoped>
/* Ensure sidebar is fixed and doesn't move */
.v-navigation-drawer {
  position: fixed !important;
  height: 100vh !important;
  top: 0 !important;
  left: 0 !important;
  z-index: 1000 !important;
}

/* Ensure app bar is fixed at top and spans full width */
.v-app-bar {
  position: fixed !important;
  top: 0 !important;
  left: 0 !important;
  right: 0 !important;
  width: 100vw !important;
  z-index: 1001 !important;
  margin: 0 !important;
  padding: 0 !important;
}

/* Adjust main content to account for fixed header and sidebar */
.v-main {
  padding-top: 64px !important; /* Height of app bar */
  padding-left: 256px !important; /* Width of sidebar */
}

/* Active menu item styling */
.v-list-item--active {
  background-color: rgba(255, 255, 255, 0.1) !important;
  color: white !important;
}

.v-list-item--active .v-icon {
  color: white !important;
}

/* Responsive adjustments */
@media (max-width: 960px) {
  .v-main {
    padding-left: 0 !important;
  }
}

@media (max-width: 600px) {
  .v-main {
    padding-top: 56px !important; /* Smaller app bar on mobile */
  }
}
</style>
