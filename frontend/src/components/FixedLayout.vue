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

      <v-btn icon>
        <v-icon>mdi-bell</v-icon>
      </v-btn>

      <v-btn icon>
        <v-icon>mdi-account-circle</v-icon>
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
import { useRoute } from 'vue-router'

const route = useRoute()
const drawer = ref(true)

const menu = [
  { title: 'Dashboard', icon: 'mdi-view-dashboard', route: '/dashboard' },
  { title: 'Upload', icon: 'mdi-upload', route: '/upload' },
  { title: 'Cleaning', icon: 'mdi-broom', route: '/cleaning' },
  { title: 'Calculations', icon: 'mdi-calculator', route: '/calculations' },
  { title: 'Reports', icon: 'mdi-file-document', route: '/reports' },
  { title: 'Visualizations', icon: 'mdi-chart-line', route: '/visualizations' }
]
</script>

<style scoped>
.v-navigation-drawer {
  position: fixed !important;
  height: 100vh !important;
}

.v-list-item--active {
  background-color: rgba(255, 255, 255, 0.1) !important;
  color: white !important;
}

.v-list-item--active .v-icon {
  color: white !important;
}
</style>
