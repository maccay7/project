<template>
  <div class="top-navbar">
    <div class="logo-area">
      <div class="logo-glow">
        <img 
          src="/DuraCapital logo.png" 
          alt="DuraCapital Logo" 
          class="navbar-logo"
          @error="e => e.target.style.display = 'none'"
        />
      </div>
    </div>
    <div class="nav-actions">
      <button class="nav-icon-btn" @click="goToSettings">
        <v-icon>mdi-cog</v-icon>
        <span>Settings</span>
      </button>
      <button class="nav-icon-btn" @click="handleLogout">
        <v-icon>mdi-logout</v-icon>
        <span>Logout</span>
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

function handleLogout() {
  localStorage.clear()
  sessionStorage.clear()
  router.push('/login')
}
</script>

<style scoped>
.top-navbar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 65px;
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

.logo-glow {
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.navbar-logo {
  width: 180px;
  height: 200px;
  object-fit: contain;
  filter: drop-shadow(0 0 4px rgba(30, 136, 229, 0.3));
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
  padding: 8px 12px;
  border-radius: 8px;
  transition: all 0.2s;
  color: #666;
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
}

.nav-icon-btn:hover {
  background: #f0f0f0;
  color: #0B2044;
}

@media (max-width: 768px) {
  .top-navbar {
    padding: 0 16px;
  }
  .nav-icon-btn span {
    display: none;
  }
}
</style>