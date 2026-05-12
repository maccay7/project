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

      <!-- Charts -->
      <v-row class="mt-4">
        <v-col cols="12" md="8">
          <v-card>
            <v-card-title>
              <v-icon>mdi-chart-line</v-icon> Monthly Activity
            </v-card-title>
            <v-card-text>
              <canvas ref="monthlyCanvas" class="chart-canvas"></canvas>
            </v-card-text>
          </v-card>
        </v-col>
        <v-col cols="12" md="4">
          <v-card>
            <v-card-title>
              <v-icon>mdi-chart-pie</v-icon> Distribution
            </v-card-title>
            <v-card-text>
              <canvas ref="pieCanvas" class="chart-canvas"></canvas>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <!-- Yield Curve Chart -->
      <v-row class="mt-4">
        <v-col cols="12">
          <v-card>
            <v-card-title>
              <v-icon>mdi-trending-up</v-icon> Yield Rate Trends
            </v-card-title>
            <v-card-text>
              <canvas ref="yieldCanvas" class="chart-canvas-large"></canvas>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

    </div>
  </FixedLayout>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import FixedLayout from '../components/FixedLayout.vue'
import { dashboardAPI } from '../services/api'

const router = useRouter()

// Chart refs
const monthlyCanvas = ref(null)
const pieCanvas = ref(null)
const yieldCanvas = ref(null)

// Chart instances
let monthlyChart = null
let pieChart = null
let yieldChart = null

// Data
const activities = ref([])
const monthlyData = ref(null)
const pieData = ref(null)
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
      
      // Get instrument type
      if (calculations.instrumentType) {
        stats.value[3].value = calculations.instrumentType.replace('_', ' ').title()
      }
    }
    
    // Load yield curve from backend
    const yieldResp = await dashboardAPI.getYieldCurve('all')
    if (yieldResp.success && yieldResp.data) {
      yieldData.value = yieldResp.data
    }
    
    // Generate sample chart data from actual dataset
    const uploaded = localStorage.getItem('uploadedDataset')
    if (uploaded) {
      const dataset = JSON.parse(uploaded)
      const dataArray = dataset.data || []
      
      if (dataArray.length) {
        // Monthly activity data
        monthlyData.value = {
          labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
          datasets: [{
            label: 'Records',
            data: [dataArray.length, dataArray.length + 2, dataArray.length + 5, dataArray.length + 3, dataArray.length + 8, dataArray.length + 10],
            borderColor: '#0B2A44',
            backgroundColor: 'rgba(11, 42, 68, 0.1)',
            fill: true
          }]
        }
        
        // Distribution data
        pieData.value = {
          labels: ['Treasury Bills', 'Bonds', 'Money Market'],
          datasets: [{
            data: [dataArray.length * 0.4, dataArray.length * 0.35, dataArray.length * 0.25],
            backgroundColor: ['#0B2A44', '#1E88E5', '#4CAF50']
          }]
        }
      }
    }
    
    // If no uploaded data, use empty data
    if (!monthlyData.value) {
      monthlyData.value = { labels: [], datasets: [] }
      pieData.value = { labels: [], datasets: [] }
    }
    
    await drawCharts()
    
  } catch (err) {
    console.error('Error loading data:', err)
  }
}

// Draw charts
async function drawCharts() {
  const chartModule = await import('chart.js/auto')
  const Chart = chartModule.default
  
  // Destroy old charts
  if (monthlyChart) monthlyChart.destroy()
  if (pieChart) pieChart.destroy()
  if (yieldChart) yieldChart.destroy()
  
  // Monthly chart
  if (monthlyCanvas.value && monthlyData.value) {
    monthlyChart = new Chart(monthlyCanvas.value.getContext('2d'), {
      type: 'line',
      data: monthlyData.value,
      options: { responsive: true, maintainAspectRatio: false }
    })
  }
  
  // Pie chart
  if (pieCanvas.value && pieData.value) {
    pieChart = new Chart(pieCanvas.value.getContext('2d'), {
      type: 'doughnut',
      data: pieData.value,
      options: { responsive: true, maintainAspectRatio: false }
    })
  }
  
  // Yield curve chart
  if (yieldCanvas.value && yieldData.value) {
    yieldChart = new Chart(yieldCanvas.value.getContext('2d'), {
      type: 'line',
      data: {
        labels: yieldData.value.labels || ['3M', '6M', '1Y', '2Y', '5Y', '10Y', '30Y'],
        datasets: yieldData.value.datasets || [{
          label: 'Yield Curve',
          data: [4.2, 4.4, 4.6, 4.8, 4.5, 4.3, 4.1],
          borderColor: '#0B2A44',
          fill: true
        }]
      },
      options: { responsive: true, maintainAspectRatio: false }
    })
  }
}

// Navigate
function goTo(route) {
  router.push(route)
}

onMounted(() => {
  loadData()
})

onUnmounted(() => {
  if (monthlyChart) monthlyChart.destroy()
  if (pieChart) pieChart.destroy()
  if (yieldChart) yieldChart.destroy()
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

.chart-canvas { height: 250px; width: 100%; }
.chart-canvas-large { height: 350px; width: 100%; }

.v-card { border-radius: 12px; border: 1px solid rgba(11,42,68,0.08); }
.v-card-title { display: flex; align-items: center; gap: 8px; color: #0B2A44; font-weight: 600; }

@media (max-width: 600px) {
  .dashboard { padding: 0 16px; }
  .stat-card { height: 100px; }
  .stat-value { font-size: 20px; }
  .chart-canvas { height: 200px; }
}
</style>