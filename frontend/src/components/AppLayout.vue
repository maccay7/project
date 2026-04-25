<template>
  <v-app>
    <v-navigation-drawer v-model="drawer" :rail="rail" permanent class="nav-drawer">
      <!-- LOGO SECTION -->
      <div class="logo-section">
        <div class="logo-container">
          <div class="logo-d">D</div>
          <div class="logo-text">
            <span class="dura">Dura</span>
            <span class="capital">Capital</span>
          </div>
        </div>
        <div class="tagline">mathematics matters</div>
      </div>

      <v-divider></v-divider>

      <v-list density="compact" nav class="nav-list">
        <v-list-item
          v-for="item in navItems"
          :key="item.title"
          :to="item.to"
          :value="item.value"
          :prepend-icon="item.icon"
          :title="item.title"
          nav
          exact
        ></v-list-item>
      </v-list>

      <template v-slot:append>
        <v-list-item @click="handleLogout" class="logout-item">
          <template v-slot:prepend>
            <v-icon color="error">mdi-logout</v-icon>
          </template>
          <v-list-item-title class="text-error">Logout</v-list-item-title>
        </v-list-item>
      </template>
    </v-navigation-drawer>

    <v-app-bar class="app-header" elevation="2">
      <v-app-bar-nav-icon @click="drawer = !drawer"></v-app-bar-nav-icon>
      
      <v-toolbar-title class="header-title">
        Financial Instrument Automation System
      </v-toolbar-title>

      <v-spacer></v-spacer>

      <v-menu>
        <template v-slot:activator="{ props }">
          <v-btn
            v-bind="props"
            variant="text"
            class="user-menu"
          >
            <v-avatar size="32" color="primary" class="mr-2">
              <v-icon>mdi-account</v-icon>
            </v-avatar>
            <span class="user-name">{{ user?.name || 'User' }}</span>
            <v-icon>mdi-chevron-down</v-icon>
          </v-btn>
        </template>

        <v-list>
          <v-list-item>
            <v-list-item-title>{{ user?.email }}</v-list-item-title>
          </v-list-item>
          <v-divider></v-divider>
          <v-list-item @click="handleLogout">
            <template v-slot:prepend>
              <v-icon color="error">mdi-logout</v-icon>
            </template>
            <v-list-item-title>Logout</v-list-item-title>
          </v-list-item>
        </v-list>
      </v-menu>
    </v-app-bar>

    <v-main class="main-content">
      <v-container fluid class="pa-6">
        <router-view />
      </v-container>
    </v-main>
  </v-app>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const drawer = ref(true)
const rail = ref(false)

const user = computed(() => authStore.user)

const navItems = [
  {
    title: 'Dashboard',
    value: 'dashboard',
    to: '/dashboard',
    icon: 'mdi-view-dashboard'
  },
  {
    title: 'Upload Data',
    value: 'upload',
    to: '/upload',
    icon: 'mdi-upload'
  },
  {
    title: 'Clean Data',
    value: 'cleaning',
    to: '/cleaning',
    icon: 'mdi-broom'
  },
  {
    title: 'Calculations',
    value: 'calculations',
    to: '/calculations',
    icon: 'mdi-calculator'
  },
  {
    title: 'Visualizations',
    value: 'visualizations',
    to: '/visualizations',
    icon: 'mdi-chart-line'
  },
  {
    title: 'Reports',
    value: 'reports',
    to: '/reports',
    icon: 'mdi-file-document'
  }
]

const handleLogout = () => {
  authStore.logout()
  router.push('/login')
}
</script>

<style scoped>
.nav-drawer {
  background: #0B2A44;
  border-right: 1px solid rgba(255, 255, 255, 0.1);
}

/* Logo Section Styles */
.logo-section {
  padding: 24px 16px !important;
  text-align: center !important;
  background: none !important;
  border: none !important;
}

.logo-container {
  display: flex !important;
  justify-content: center !important;
  align-items: center !important;
  margin-bottom: 8px !important;
}

.logo-d {
  font-size: 32px !important;
  font-weight: bold !important;
  color: white !important;
  margin-right: 8px !important;
  position: relative !important;
  line-height: 1 !important;
}

.logo-d::after {
  content: '' !important;
  position: absolute !important;
  right: -4px !important;
  top: 50% !important;
  width: 10px !important;
  height: 20px !important;
  background: #1E88E5 !important;
  border-radius: 6px !important;
  transform: translateY(-50%) !important;
}

.dura, .capital {
  font-size: 16px !important;
  font-weight: bold !important;
  line-height: 1 !important;
}

.dura { color: white !important; }
.capital { color: #1E88E5 !important; }

.tagline {
  font-size: 10px !important;
  color: #1E88E5 !important;
  text-transform: lowercase !important;
  opacity: 0.8 !important;
  margin-top: 4px !important;
}

.nav-list :deep(.v-list-item) {
  color: rgba(255, 255, 255, 0.8);
  margin: 4px 8px;
  border-radius: 8px;
}

.nav-list :deep(.v-list-item:hover) {
  background: rgba(255, 255, 255, 0.1);
  color: white;
}

.nav-list :deep(.v-list-item--active) {
  background: #1E88E5;
  color: white;
}

.logout-item {
  color: rgba(255, 255, 255, 0.8);
  margin: 8px;
}

.logout-item:hover {
  background: rgba(244, 67, 54, 0.1);
}

.app-header {
  background: white;
  border-bottom: 1px solid #e0e0e0;
}

.header-title {
  color: #0B2A44;
  font-weight: 600;
  font-size: 20px;
}

.user-menu {
  color: #0B2A44;
}

.user-name {
  font-weight: 500;
}

.main-content {
  background: #f5f7fa;
}
</style>
