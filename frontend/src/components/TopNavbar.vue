<template>
  <div class="top-navbar">
    <div class="logo-area">
      <div class="logo-placeholder">
        <img 
          src="/DataStudio-logo.jpeg" 
          alt="DataStudio Logo" 
          class="navbar-logo"
          @error="e => e.target.style.display = 'none'"
        />
      </div>
    </div>
    <div class="nav-actions">
      <button class="nav-icon-btn" @click="goToSettings">
        <v-icon>mdi-cog</v-icon>
      </button>
      <button class="nav-icon-btn" @click="handleLogout">
        <v-icon>mdi-logout</v-icon>
      </button>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()

function goToSettings() {
  router.push('/settings')
}

// FIXED: Force redirect to login page
function handleLogout() {
  // Clear all storage
  localStorage.clear()
  sessionStorage.clear()
  // Force hard navigation to login page
  window.location.href = '/login'
}
</script>

<style scoped>
.top-navbar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 60px;
  background: white;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 30px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
  z-index: 1000;
}

.logo-area {
  display: flex;
  align-items: center;
}

.logo-placeholder {
  display: flex;
  align-items: center;
}

.navbar-logo {
  width: 180px;
  max-height: 48px;
  height: auto;
  object-fit: contain;
  border-radius: 8px;
}

.nav-actions {
  display: flex;
  gap: 15px;
  align-items: center;
}

.nav-icon-btn {
  background: transparent;
  border: none;
  cursor: pointer;
  padding: 8px;
  border-radius: 8px;
  transition: all 0.2s;
  color: #666;
  display: flex;
  align-items: center;
  justify-content: center;
}

.nav-icon-btn:hover {
  background: #f0f0f0;
  color: #0B2044;
}

@media (max-width: 768px) {
  .top-navbar {
    padding: 0 16px;
  }
}
</style>