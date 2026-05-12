<template>
  <FixedLayout>
    <div class="dashboard">

      <!-- Welcome Section -->
      <div class="welcome-section">
        <h1>Dashboard</h1>
        <p>Welcome to DuraCapital Financial System</p>
      </div>

      <!-- Stats Cards -->
      <v-row>
        <v-col cols="12" sm="6" md="3" v-for="stat in stats" :key="stat.title">
          <v-card class="stat-card">
            <v-card-text>
              <div class="stat-content">
                <div class="stat-icon" :style="{ backgroundColor: stat.bgColor }">
                  <v-icon :color="stat.iconColor">{{ stat.icon }}</v-icon>
                </div>
                <div class="stat-info">
                  <div class="stat-value">{{ stat.value }}</div>
                  <div class="stat-title">{{ stat.title }}</div>
                </div>
              </div>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <!-- Quick Actions & Recent Activity -->
      <v-row class="mt-4">
        <v-col cols="12" md="8">
          <v-card>
            <v-card-title>
              <v-icon>mdi-lightning-bolt</v-icon> Quick Actions
            </v-card-title>
            <v-card-text>
              <v-row>
                <v-col cols="12" sm="4" v-for="action in actions" :key="action.title">
                  <v-card class="action-btn" @click="goTo(action.route)">
                    <v-card-text class="text-center">
                      <v-icon :color="action.color" size="32">{{ action.icon }}</v-icon>
                      <div class="action-title">{{ action.title }}</div>
                      <div class="action-desc">{{ action.desc }}</div>
                    </v-card-text>
                  </v-card>
                </v-col>
              </v-row>
            </v-card-text>
          </v-card>
        </v-col>

        <v-col cols="12" md="4">
          <v-card>
            <v-card-title>
              <v-icon>mdi-history</v-icon> Recent Activity
            </v-card-title>
            <v-card-text>
              <div v-for="activity in activities" :key="activity.id" class="activity-item">
                <div class="activity-dot" :style="{ background: activity.color }"></div>
                <div>
                  <div class="activity-text">{{ activity.text }}</div>
                  <div class="activity-time">{{ activity.time }}</div>
                </div>
              </div>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

    </div>
  </FixedLayout>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import FixedLayout from '../components/FixedLayout.vue'
import { dashboardAPI } from '../services/api'

const router = useRouter()

// Data
const activities = ref([])
const yieldData = ref(null)

// Stats (will update from localStorage)
const stats = ref([
  { title: 'Total Datasets', value: '0', icon: 'mdi-database', bgColor: 'rgba(11,42,68,0.1)', iconColor: '#0B2A44' },
  { title: 'Calculations', value: '0', icon: 'mdi-calculator', bgColor: 'rgba(30,136,229,0.1)', iconColor: '#1E88E5' },
  { title: 'Reports', value: '0', icon: 'mdi-file-document', bgColor: 'rgba(76,175,80,0.1)', iconColor: '#4CAF50' },
  { title: 'Instrument', value: 'N/A', icon: 'mdi-chart-line', bgColor: 'rgba(255,193,7,0.1)', iconColor: '#FFC107' }
])

// Quick actions
const actions = [
  { title: 'Upload', desc: 'Upload files', icon: 'mdi-upload', color: '#0B2A44', route: '/upload' },
  { title: 'Calculate', desc: 'Run calculations', icon: 'mdi-calculator', color: '#1E88E5', route: '/calculations' },
  { title: 'Reports', desc: 'Generate reports', icon: 'mdi-file-document', color: '#4CAF50', route: '/reports' },
  { title: 'Charts', desc: 'View analytics', icon: 'mdi-chart-line', color: '#FFC107', route: '/visualizations' },
  { title: 'Clean', desc: 'Clean data', icon: 'mdi-broom', color: '#9C27B0', route: '/cleaning' },
  { title: 'Settings', desc: 'Configure', icon: 'mdi-cog', color: '#F44336', route: '/settings' }
]

// Load all data
async function loadData() {
  try {
    // Load from localStorage (saved datasets)
    const saved = localStorage.getItem('saved-datasets')
    if (saved) {
      const datasets = JSON.parse(saved)
      stats.value[0].value = datasets.length.toString()
      
      // Add activity for each dataset
      datasets.forEach(ds => {
        activities.value.unshift({
          id: ds.id || Date.now(),
          text: `Dataset "${ds.name}" saved`,
          time: new Date(ds.timestamp || Date.now()).toLocaleString(),
          color: '#0B2A44'
        })
      })
    }
    
    // Load calculations data
    const calcData = localStorage.getItem('calculations')
    if (calcData) {
      const calculations = JSON.parse(calcData)
      const calcs = calculations.calculations || []
      stats.value[1].value = calcs.length.toString()
      stats.value[2].value = calcs.length.toString()
      
      // Get instrument type - fixed
      if (calculations.instrumentType) {
        let instrumentName = calculations.instrumentType.replace(/_/g, ' ')
        instrumentName = instrumentName.charAt(0).toUpperCase() + instrumentName.slice(1)
        stats.value[3].value = instrumentName
      }
    }
    
    // Load yield curve from backend
    const yieldResp = await dashboardAPI.getYieldCurve('all')
    if (yieldResp.success && yieldResp.data) {
      yieldData.value = yieldResp.data
    }
    
  } catch (err) {
    console.error('Error loading data:', err)
  }
}

// Navigate
function goTo(route) {
  router.push(route)
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.dashboard { max-width: 1400px; margin: 0 auto; padding: 20px; }

.welcome-section { margin-bottom: 30px; }
.welcome-section h1 { color: #0B2A44; font-size: 32px; margin-bottom: 8px; }
.welcome-section p { color: #666; font-size: 16px; }

.stat-card { height: 120px; border-radius: 12px; transition: 0.2s; }
.stat-card:hover { transform: translateY(-2px); }
.stat-content { display: flex; align-items: center; height: 100%; }
.stat-icon { width: 56px; height: 56px; border-radius: 12px; display: flex; align-items: center; justify-content: center; margin-right: 12px; }
.stat-value { font-size: 24px; font-weight: 700; color: #0B2A44; }
.stat-title { font-size: 12px; color: #666; }

.action-btn { cursor: pointer; transition: 0.2s; border-radius: 8px; }
.action-btn:hover { transform: translateY(-3px); box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
.action-title { font-weight: 600; color: #0B2A44; margin-top: 8px; }
.action-desc { font-size: 12px; color: #666; }

.activity-item { display: flex; gap: 12px; margin-bottom: 16px; }
.activity-dot { width: 8px; height: 8px; border-radius: 50%; margin-top: 6px; }
.activity-text { font-size: 14px; color: #333; }
.activity-time { font-size: 12px; color: #999; margin-top: 2px; }

.v-card { border-radius: 12px; border: 1px solid rgba(11,42,68,0.08); }
.v-card-title { display: flex; align-items: center; gap: 8px; color: #0B2A44; font-weight: 600; }

@media (max-width: 600px) {
  .dashboard { padding: 0 16px; }
  .stat-card { height: 100px; }
  .stat-value { font-size: 20px; }
}
</style>