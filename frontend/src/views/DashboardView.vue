<template>
  <FixedLayout>
    <div class="dashboard">
      <!-- Welcome Section -->
      <div class="welcome-section">
        <h1>Dashboard</h1>
        <p>Welcome to DuraCapital Financial System</p>
      </div>

      <!-- Stats Cards - Show numbers at a glance -->
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

      <!-- Quick Actions - Main buttons user can click -->
      <v-row class="mt-4">
        <v-col cols="12" md="8">
          <v-card>
            <v-card-title>
              <v-icon>mdi-lightning-bolt</v-icon>
              Quick Actions
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

        <!-- Recent Activity - What happened lately -->
        <v-col cols="12" md="4">
          <v-card>
            <v-card-title>
              <v-icon>mdi-history</v-icon>
              Recent Activity
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

      <!-- Charts - Visual data -->
      <v-row class="mt-4">
        <v-col cols="12" md="8">
          <v-card>
            <v-card-title>
              <v-icon>mdi-chart-line</v-icon>
              Monthly Activity
            </v-card-title>
            <v-card-text>
              <canvas ref="monthlyChartRef" class="chart-canvas"></canvas>
            </v-card-text>
          </v-card>
        </v-col>
        <v-col cols="12" md="4">
          <v-card>
            <v-card-title>
              <v-icon>mdi-chart-pie</v-icon>
              Distribution
            </v-card-title>
            <v-card-text>
              <canvas ref="pieChartRef" class="chart-canvas"></canvas>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <!-- Yield Curve Chart -->
      <v-row class="mt-4">
        <v-col cols="12">
          <v-card>
            <v-card-title>
              <v-icon>mdi-trending-up</v-icon>
              Yield Rate Trends
            </v-card-title>
            <v-card-text>
              <canvas ref="yieldChartRef" class="chart-canvas-large"></canvas>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </div>
  </FixedLayout>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import FixedLayout from '../components/FixedLayout.vue'
import { dashboardAPI } from '../services/api'
import { useDataset } from '../composables/useDataset'

const router = useRouter()

// Use dataset composable for global state
const { datasetInfo, hasDataset, loadDataset } = useDataset()

// Chart references
const monthlyChartRef = ref<any>(null)
const pieChartRef = ref<any>(null)
const yieldChartRef = ref<any>(null)

// Store chart instances
let monthlyChart: any = null
let pieChart: any = null
let yieldChart: any = null

// Data from backend
const activities = ref<any[]>([])
const monthlyData = ref<any>(null)
const pieData = ref<any>(null)
const yieldData = ref<any>(null)

// Stats to display
const stats = ref([
  { title: 'Total Datasets', value: '0', icon: 'mdi-database', bgColor: 'rgba(11,42,68,0.1)', iconColor: '#0B2A44' },
  { title: 'Calculations', value: '0', icon: 'mdi-calculator', bgColor: 'rgba(30,136,229,0.1)', iconColor: '#1E88E5' },
  { title: 'Reports', value: '0', icon: 'mdi-file-document', bgColor: 'rgba(76,175,80,0.1)', iconColor: '#4CAF50' },
  { title: 'Instrument Type', value: 'N/A', icon: 'mdi-chart-line', bgColor: 'rgba(255,193,7,0.1)', iconColor: '#FFC107' }
])

// Quick action buttons
const actions = [
  { title: 'Upload', desc: 'Upload files', icon: 'mdi-upload', color: '#0B2A44', route: '/upload' },
  { title: 'Calculate', desc: 'Run calculations', icon: 'mdi-calculator', color: '#1E88E5', route: '/calculations' },
  { title: 'Reports', desc: 'Generate reports', icon: 'mdi-file-document', color: '#4CAF50', route: '/reports' },
  { title: 'Charts', desc: 'View analytics', icon: 'mdi-chart-line', color: '#FFC107', route: '/visualizations' },
  { title: 'Clean', desc: 'Clean data', icon: 'mdi-broom', color: '#9C27B0', route: '/cleaning' },
  { title: 'Settings', desc: 'Configure', icon: 'mdi-cog', color: '#F44336', route: '/settings' }
]

// Load all data from backend
async function loadData() {
  try {
    // Load dataset from localStorage
    await loadDataset()
    
    // Update stats based on uploaded dataset
    if (hasDataset.value && datasetInfo.value) {
      const savedDatasets = JSON.parse(localStorage.getItem('saved-datasets') || '[]')
      stats.value[0].value = savedDatasets.length || 0
      
      // Show instrument type from dataset
      if (datasetInfo.value.instrumentType) {
        stats.value[3].value = datasetInfo.value.instrumentType
      }
      
      // Add recent activity for dataset upload
      if (datasetInfo.value.name) {
        activities.value.unshift({
          id: Date.now(),
          text: `Dataset uploaded: ${datasetInfo.value.name}`,
          time: new Date().toLocaleString(),
          color: '#4CAF50'
        })
      }
      
      // Load data from uploaded dataset for charts
      const uploadedDataset = JSON.parse(localStorage.getItem('uploadedDataset') || '{}')
      if (uploadedDataset.data && Array.isArray(uploadedDataset.data)) {
        const data = uploadedDataset.data
        
        // Generate Monthly Activity data from dataset
        const monthlyActivity: any = {
          labels: [],
          datasets: [{
            label: 'Records per Month',
            data: [],
            borderColor: '#0B2A44',
            backgroundColor: 'rgba(11, 42, 68, 0.1)',
            fill: true,
            tension: 0.4
          }]
        }
        
        // Group data by date if available, otherwise show distribution
        const dateField = Object.keys(data[0]).find(k => k.toLowerCase().includes('date') || k.toLowerCase().includes('issue'))
        if (dateField) {
          const monthCounts: any = {}
          data.forEach((row: any) => {
            try {
              const date = new Date(row[dateField])
              if (!isNaN(date.getTime())) {
                const monthKey = date.toLocaleString('default', { month: 'short', year: 'numeric' })
                monthCounts[monthKey] = (monthCounts[monthKey] || 0) + 1
              }
            } catch (e) {
              // Skip invalid dates
            }
          })
          monthlyActivity.labels = Object.keys(monthCounts)
          monthlyActivity.datasets[0].data = Object.values(monthCounts)
        } else {
          // If no date field, show data distribution by index
          monthlyActivity.labels = ['Dataset Size']
          monthlyActivity.datasets[0].data = [data.length]
        }
        monthlyData.value = monthlyActivity
        
        // Generate Instrument Distribution data from dataset
        const classificationField = Object.keys(data[0]).find(k => k.toLowerCase().includes('classification') || k.toLowerCase().includes('instrument') || k.toLowerCase().includes('type'))
        const instrumentDistribution: any = {
          labels: [],
          datasets: [{
            data: [],
            backgroundColor: ['#0B2A44', '#1E88E5', '#4CAF50', '#FFC107', '#F44336', '#9C27B0', '#00BCD4', '#FF5722']
          }]
        }
        
        if (classificationField) {
          const typeCounts: any = {}
          data.forEach((row: any) => {
            const type = row[classificationField] || 'Unknown'
            typeCounts[type] = (typeCounts[type] || 0) + 1
          })
          instrumentDistribution.labels = Object.keys(typeCounts)
          instrumentDistribution.datasets[0].data = Object.values(typeCounts)
        } else {
          // If no classification field, show by portfolio or other field
          const portfolioField = Object.keys(data[0]).find(k => k.toLowerCase().includes('portfolio') || k.toLowerCase().includes('pfolio'))
          if (portfolioField) {
            const portfolioCounts: any = {}
            data.forEach((row: any) => {
              const portfolio = row[portfolioField] || 'Unknown'
              portfolioCounts[portfolio] = (portfolioCounts[portfolio] || 0) + 1
            })
            instrumentDistribution.labels = Object.keys(portfolioCounts)
            instrumentDistribution.datasets[0].data = Object.values(portfolioCounts)
          } else {
            // Fallback: show total records
            instrumentDistribution.labels = ['Total Records']
            instrumentDistribution.datasets[0].data = [data.length]
          }
        }
        pieData.value = instrumentDistribution
      }
    }
    
    // Get stats from backend
    const kpi = await dashboardAPI.getKPI()
    if (kpi.success && kpi.data) {
      // Only update if not already set from localStorage
      if (stats.value[0].value === '0') {
        stats.value[0].value = kpi.data.total_datasets || 0
      }
      if (stats.value[1].value === '0') {
        stats.value[1].value = kpi.data.active_calculations || 0
      }
      if (stats.value[2].value === '0') {
        stats.value[2].value = kpi.data.reports_generated || 0
      }
    }

    // Get yield curve data - use instrument type from dataset
    const instrumentType = stats.value[3].value !== 'N/A' ? stats.value[3].value : 'all'
    const yieldResp = await dashboardAPI.getYieldCurve(instrumentType.toLowerCase())
    if (yieldResp.success) {
      yieldData.value = yieldResp.data
    }

    // Draw charts
    await drawCharts()
  } catch (err) {
    console.error('Failed to load data:', err)
  }
}

// Draw all charts
async function drawCharts() {
  // Load Chart.js library
  const chartModule = await import('chart.js/auto')
  const Chart = chartModule.default || chartModule.Chart

  // Destroy old charts if they exist
  if (monthlyChart) monthlyChart.destroy()
  if (pieChart) pieChart.destroy()
  if (yieldChart) yieldChart.destroy()

  // Draw monthly line chart
  if (monthlyChartRef.value && monthlyData.value) {
    const ctx = monthlyChartRef.value.getContext('2d')
    monthlyChart = new Chart(ctx, {
      type: 'line',
      data: monthlyData.value,
      options: { responsive: true, maintainAspectRatio: false }
    })
  }

  // Draw pie chart
  if (pieChartRef.value && pieData.value) {
    const ctx = pieChartRef.value.getContext('2d')
    pieChart = new Chart(ctx, {
      type: 'doughnut',
      data: pieData.value,
      options: { responsive: true, maintainAspectRatio: false }
    })
  }

  // Draw yield curve
  if (yieldChartRef.value && yieldData.value) {
    const ctx = yieldChartRef.value.getContext('2d')
    yieldChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: yieldData.value.labels || [],
        datasets: yieldData.value.datasets || []
      },
      options: { responsive: true, maintainAspectRatio: false }
    })
  }
}

// Navigate to a page
function goTo(route: string) {
  router.push(route)
}

// Load data when page opens
onMounted(() => {
  loadData()
})

// Clean up charts when leaving page
onUnmounted(() => {
  if (monthlyChart) monthlyChart.destroy()
  if (pieChart) pieChart.destroy()
  if (yieldChart) yieldChart.destroy()
})
</script>

<style scoped>
.dashboard { max-width: 1400px; margin: 0 auto; padding: 20px; }

/* Welcome section */
.welcome-section { margin-bottom: 30px; }
.welcome-section h1 { color: #0B2A44; font-size: 32px; margin-bottom: 8px; }
.welcome-section p { color: #666; font-size: 16px; }

/* Stat cards */
.stat-card { height: 120px; border-radius: 12px; }
.stat-card:hover { transform: translateY(-2px); transition: 0.2s; }
.stat-content { display: flex; align-items: center; height: 100%; }
.stat-icon { width: 56px; height: 56px; border-radius: 12px; display: flex; align-items: center; justify-content: center; margin-right: 12px; }
.stat-value { font-size: 24px; font-weight: 700; color: #0B2A44; }
.stat-title { font-size: 12px; color: #666; }

/* Action buttons */
.action-btn { cursor: pointer; transition: 0.2s; border-radius: 8px; }
.action-btn:hover { transform: translateY(-3px); box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
.action-title { font-weight: 600; color: #0B2A44; margin-top: 8px; }
.action-desc { font-size: 12px; color: #666; }

/* Activity list */
.activity-item { display: flex; gap: 12px; margin-bottom: 16px; }
.activity-dot { width: 8px; height: 8px; border-radius: 50%; margin-top: 6px; }
.activity-text { font-size: 14px; color: #333; }
.activity-time { font-size: 12px; color: #999; margin-top: 2px; }

/* Charts */
.chart-canvas { height: 250px; width: 100%; }
.chart-canvas-large { height: 350px; width: 100%; }

/* Cards styling */
.v-card { border-radius: 12px; border: 1px solid rgba(11,42,68,0.08); }
.v-card-title { display: flex; align-items: center; gap: 8px; color: #0B2A44; font-weight: 600; }

/* Mobile friendly */
@media (max-width: 600px) {
  .dashboard { padding: 0 16px; }
  .stat-card { height: 100px; }
  .stat-value { font-size: 20px; }
  .chart-canvas { height: 200px; }
}
</style>