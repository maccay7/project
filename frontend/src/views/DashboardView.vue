<template>
  <FixedLayout>
    <div class="dashboard-view">
      <!-- Header Section -->
      <div class="dashboard-header">
        <h1 class="page-title">Dashboard</h1>
        <p class="page-subtitle">Welcome to DuraCapital Financial Instrument Automation System</p>
      </div>

      <!-- KPI Cards -->
      <v-row class="kpi-row">
        <v-col cols="12" sm="6" md="3" v-for="kpi in kpiData" :key="kpi.title">
          <v-card class="kpi-card" elevation="2">
            <v-card-text>
              <div class="kpi-content">
                <div class="kpi-icon" :style="{ backgroundColor: kpi.color }">
                  <v-icon :color="kpi.iconColor">{{ kpi.icon }}</v-icon>
                </div>
                <div class="kpi-info">
                  <div class="kpi-value">{{ kpi.value }}</div>
                  <div class="kpi-title">{{ kpi.title }}</div>
                  <div v-if="kpi.change" class="kpi-change" :class="kpi.changeClass">
                    <v-icon size="16">{{ kpi.changeIcon }}</v-icon>
                    {{ kpi.change }}
                  </div>
                </div>
              </div>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <!-- Quick Actions and Recent Activity -->
      <v-row class="content-row">
        <!-- Quick Actions -->
        <v-col cols="12" md="8">
          <v-card class="action-card" elevation="2">
            <v-card-title class="card-title">
              <v-icon class="title-icon">mdi-lightning-bolt</v-icon>
              Quick Actions
            </v-card-title>
            <v-card-text>
              <!-- Top Row - 3 Actions -->
              <v-row class="mb-4">
                <v-col cols="12" sm="4" v-for="action in quickActions.slice(0, 3)" :key="action.title">
                  <v-card 
                    class="action-item" 
                    hover 
                    @click="navigateTo(action.route)"
                    elevation="1"
                  >
                    <v-card-text class="text-center pa-4">
                      <v-icon :color="action.color" size="32" class="mb-2">{{ action.icon }}</v-icon>
                      <div class="action-title">{{ action.title }}</div>
                      <div class="action-desc">{{ action.description }}</div>
                    </v-card-text>
                  </v-card>
                </v-col>
              </v-row>
              
              <!-- Bottom Row - 3 Actions -->
              <v-row>
                <v-col cols="12" sm="4" v-for="action in quickActions.slice(3, 6)" :key="action.title">
                  <v-card 
                    class="action-item" 
                    hover 
                    @click="navigateTo(action.route)"
                    elevation="1"
                  >
                    <v-card-text class="text-center pa-4">
                      <v-icon :color="action.color" size="32" class="mb-2">{{ action.icon }}</v-icon>
                      <div class="action-title">{{ action.title }}</div>
                      <div class="action-desc">{{ action.description }}</div>
                    </v-card-text>
                  </v-card>
                </v-col>
              </v-row>
            </v-card-text>
          </v-card>
        </v-col>

        <!-- Recent Activity -->
        <v-col cols="12" md="4">
          <v-card class="activity-card" elevation="2">
            <v-card-title class="card-title">
              <v-icon class="title-icon">mdi-history</v-icon>
              Recent Activity
            </v-card-title>
            <v-card-text>
              <div class="activity-list">
                <div v-for="activity in recentActivities" :key="activity.id" class="activity-item">
                  <div class="activity-dot" :style="{ backgroundColor: activity.color }"></div>
                  <div class="activity-content">
                    <div class="activity-text">{{ activity.text }}</div>
                    <div class="activity-time">{{ activity.time }}</div>
                  </div>
                </div>
              </div>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <!-- Charts Section - Real Data -->
      <v-row class="charts-section">
        <v-col cols="12" md="8">
          <v-card class="chart-card" elevation="2">
            <v-card-title class="card-title">
              <v-icon class="title-icon">mdi-chart-line</v-icon>
              Monthly Activity Trends
            </v-card-title>
            <v-card-text>
              <div class="chart-container">
                <canvas ref="monthlyChart" width="400" height="200"></canvas>
              </div>
            </v-card-text>
          </v-card>
        </v-col>
        <v-col cols="12" md="4">
          <v-card class="chart-card" elevation="2">
            <v-card-title class="card-title">
              <v-icon class="title-icon">mdi-chart-pie</v-icon>
              Instrument Distribution
            </v-card-title>
            <v-card-text>
              <div class="chart-container">
                <canvas ref="pieChart" width="200" height="200"></canvas>
              </div>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <!-- Yield Rate Chart - Backend Data -->
      <v-row class="mb-8">
        <v-col cols="12">
          <v-card class="chart-card" elevation="2">
            <v-card-title class="card-title">
              <v-icon class="title-icon">mdi-trending-up</v-icon>
              {{ yieldCurveTitle }}
            </v-card-title>
            <v-card-text>
              <div v-if="yieldCurveData" class="chart-container">
                <canvas ref="yieldCurveChart" width="800" height="300"></canvas>
              </div>
              <div v-else class="chart-placeholder large">
                <v-icon size="80" color="#4CAF50">mdi-trending-up</v-icon>
                <p class="placeholder-text">Loading yield rate trends...</p>
                <p class="placeholder-subtitle">Fetching data from FRED API</p>
              </div>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <!-- Financial Instruments Overview -->
      <v-row class="mb-8">
        <v-col cols="12">
          <v-card class="instruments-card" elevation="2">
            <v-card-title class="card-title">
              <v-icon class="title-icon">mdi-chart-pie</v-icon>
              Supported Financial Instruments
            </v-card-title>
            <v-card-text>
              <v-row>
                <v-col cols="12" md="4" v-for="instrument in instruments" :key="instrument.name">
                  <v-card class="instrument-item" outlined>
                    <v-card-text class="text-center pa-4">
                      <v-icon :color="instrument.color" size="40" class="mb-3">{{ instrument.icon }}</v-icon>
                      <div class="instrument-name">{{ instrument.name }}</div>
                      <div class="instrument-desc">{{ instrument.description }}</div>
                    </v-card-text>
                  </v-card>
                </v-col>
              </v-row>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </div>
  </FixedLayout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { dashboardAPI, calculationsAPI } from '../services/api'
import FixedLayout from '../components/FixedLayout.vue'

// Chart.js - load dynamically to prevent rendering issues
let Chart: any = null
let monthlyChartInstance: any = null
let pieChartInstance: any = null
let yieldCurveChartInstance: any = null

const router = useRouter()

// Load saved datasets from localStorage
const savedDatasets = ref<any[]>([])
const loadSavedDatasets = () => {
  try {
    const saved = localStorage.getItem('saved-datasets')
    if (saved) {
      savedDatasets.value = JSON.parse(saved)
    }
  } catch (err) {
    console.error('Failed to load saved datasets:', err)
  }
}

const kpiData = ref([
  {
    title: 'Total Datasets',
    value: '0',
    icon: 'mdi-database',
    color: 'rgba(11, 42, 68, 0.1)',
    iconColor: '#0B2A44',
    change: '',
    changeIcon: 'mdi-minus',
    changeClass: 'neutral'
  },
  {
    title: 'Calculations',
    value: '0',
    icon: 'mdi-calculator',
    color: 'rgba(30, 136, 229, 0.1)',
    iconColor: '#1E88E5',
    change: '',
    changeIcon: 'mdi-minus',
    changeClass: 'neutral'
  },
  {
    title: 'Reports Generated',
    value: '0',
    icon: 'mdi-file-document',
    color: 'rgba(76, 175, 80, 0.1)',
    iconColor: '#4CAF50',
    change: '',
    changeIcon: 'mdi-minus',
    changeClass: 'neutral'
  },
  {
    title: 'Instrument Type',
    value: 'N/A',
    icon: 'mdi-chart-line',
    color: 'rgba(255, 193, 7, 0.1)',
    iconColor: '#FFC107',
    change: '',
    changeIcon: 'mdi-minus',
    changeClass: 'neutral'
  }
])

// Chart data will be fetched from backend when connected
// Expected data structure for backend:
// const chartData = ref({
//   monthlyData: [
//     { month: 'Jan', datasets: number, calculations: number, reports: number },
//     // ... more months
//   ],
//   instrumentDistribution: [
//     { name: 'Treasury Bills', value: number, color: '#0B2A44' },
//     { name: 'Bonds', value: number, color: '#1E88E5' },
//     { name: 'Money Market', value: number, color: '#4CAF50' }
//   ],
//   yieldRates: [
//     { date: '2024-01', rate: number },
//     // ... more dates
//   ]
// })

const quickActions = ref([
  {
    title: 'Upload Dataset',
    description: 'Upload financial data for analysis',
    icon: 'mdi-upload',
    color: '#0B2A44',
    route: '/upload'
  },
  {
    title: 'View Calculations',
    description: 'Check yields and discount rates',
    icon: 'mdi-calculator',
    color: '#1E88E5',
    route: '/calculations'
  },
  {
    title: 'Generate Reports',
    description: 'Create and download reports',
    icon: 'mdi-file-document',
    color: '#4CAF50',
    route: '/reports'
  },
  {
    title: 'View Analytics',
    description: 'Visualize financial data',
    icon: 'mdi-chart-line',
    color: '#FFC107',
    route: '/visualizations'
  },
  {
    title: 'Data Cleaning',
    description: 'Clean and prepare datasets',
    icon: 'mdi-broom',
    color: '#9C27B0',
    route: '/cleaning'
  },
  {
    title: 'System Settings',
    description: 'Configure system preferences',
    icon: 'mdi-cog',
    color: '#F44336',
    route: '/settings'
  }
])

const recentActivities = ref<any[]>([])
const yieldCurveData = ref<any>(null)
const chartData = ref<any>(null)
const monthlyChart = ref<HTMLCanvasElement | null>(null)
const pieChart = ref<HTMLCanvasElement | null>(null)
const yieldCurveChart = ref<HTMLCanvasElement | null>(null)

// Load data from backend
const loadDashboardData = async () => {
  try {
    // Load KPI data
    try {
      const kpiResponse = await dashboardAPI.getKPI()
      console.log('KPI Response:', kpiResponse)
      if (kpiResponse.success && kpiResponse.data) {
        // Update KPI data with real values
        const data = kpiResponse.data
        kpiData.value[0].value = data.total_datasets || data.datasets || 0
        kpiData.value[1].value = data.active_calculations || data.calculations || 0
        kpiData.value[2].value = data.reports_generated || data.reports || 0

        // Get instrument type from saved datasets or backend data
        let instrumentType = 'N/A'
        if (savedDatasets.value.length > 0) {
          instrumentType = savedDatasets.value[0].instrumentType || 'N/A'
        } else if (data.instrument_type) {
          instrumentType = data.instrument_type
        } else if (data.active_instrument) {
          instrumentType = data.active_instrument
        }
        kpiData.value[3].value = instrumentType

        console.log('Updated KPI values:', kpiData.value)

        // Update instrument counts
        if (data.instrument_breakdown) {
          data.instrument_breakdown.forEach((instrument: any) => {
            const instrumentIndex = instruments.value.findIndex(
              inst => inst.name.toLowerCase().replace(' ', '_') === instrument.file_type
            )
            if (instrumentIndex !== -1) {
              instruments.value[instrumentIndex].count = instrument.count
              console.log(`Updated ${instruments.value[instrumentIndex].name} count to ${instrument.count}`)
            }
          })
        } else {
          // If no instrument breakdown from backend, use saved datasets to populate counts
          const instrumentCounts: any = { 'treasury_bills': 0, 'bonds': 0, 'money_market': 0 }
          savedDatasets.value.forEach((dataset: any) => {
            const type = dataset.instrumentType?.toLowerCase().replace(' ', '_') || 'unknown'
            if (instrumentCounts[type] !== undefined) {
              instrumentCounts[type]++
            }
          })
          instruments.value[0].count = instrumentCounts.treasury_bills
          instruments.value[1].count = instrumentCounts.bonds
          instruments.value[2].count = instrumentCounts.money_market
        }
      } else {
        console.error('KPI API returned unsuccessful or no data:', kpiResponse)
      }
    } catch (error) {
      console.error('Error loading KPI data:', error)
    }

    // Load recent activity
    try {
      const activityResponse = await dashboardAPI.getRecentActivity()
      console.log('Recent Activity Response:', activityResponse)
      if (activityResponse.success && activityResponse.data) {
        recentActivities.value = activityResponse.data
        console.log('Updated recent activities:', recentActivities.value)
      } else {
        console.error('Recent Activity API returned unsuccessful or no data:', activityResponse)
      }
    } catch (error) {
      console.error('Error loading recent activity:', error)
    }

    // Load yield curve data
    try {
      // Get instrument type from saved dataset
      let instrumentType = 'all'
      if (savedDatasets.value && savedDatasets.value.length > 0) {
        instrumentType = savedDatasets.value[0].instrumentType?.toLowerCase().replace(' ', '_') || 'all'
      }

      const yieldCurveResponse = await dashboardAPI.getYieldCurve(instrumentType)
      if (yieldCurveResponse.success) {
        yieldCurveData.value = yieldCurveResponse.data
        // Render yield curve chart after data is loaded
        await nextTick()
        renderCharts()
      }
    } catch (error) {
      console.error('Error loading yield curve data:', error)
    }

    // Load chart data - only use FRED API data
    try {
      const chartsResponse = await dashboardAPI.getCharts()
      console.log('Charts Response:', chartsResponse)
      if (chartsResponse.success && chartsResponse.data) {
        chartData.value = chartsResponse.data
        console.log('Chart data set:', chartData.value)
        // Render charts after data is loaded
        await nextTick()
        renderCharts()
      } else {
        console.error('Charts API returned no data:', chartsResponse)
      }
    } catch (error) {
      console.error('Error loading charts data:', error)
    }
  } catch (error) {
    console.error('Error loading dashboard data:', error)
  }
}

// Render charts using Chart.js
const renderCharts = () => {
  try {
    // Dynamically import Chart.js to prevent rendering issues
    import('chart.js').then(chartModule => {
      const ChartClass = chartModule.default || chartModule.Chart
      const registerables = chartModule.registerables || []

      // Register Chart.js components
      ChartClass.register(...registerables)

      // Destroy existing charts
      if (monthlyChartInstance) {
        monthlyChartInstance.destroy()
      }
      if (pieChartInstance) {
        pieChartInstance.destroy()
      }
      if (yieldCurveChartInstance) {
        yieldCurveChartInstance.destroy()
      }

      // Render monthly activity chart
      if (monthlyChart.value) {
        try {
          const ctx = monthlyChart.value.getContext('2d')
          if (ctx) {
            const monthlyData = chartData.value?.monthlyActivity || {
              labels: [],
              datasets: []
            }
            monthlyChartInstance = new ChartClass(ctx, {
              type: 'line',
              data: {
                labels: monthlyData.labels || [],
                datasets: monthlyData.datasets || []
              },
              options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                  legend: {
                    position: 'top',
                  },
                  title: {
                    display: false
                  }
                },
                scales: {
                  y: {
                    beginAtZero: true
                  }
                }
              }
            })
          }
        } catch (error) {
          console.error('Error rendering monthly chart:', error)
        }
      }

      // Render instrument distribution pie chart
      if (pieChart.value) {
        try {
          const ctx = pieChart.value.getContext('2d')
          if (ctx) {
            const distributionData = chartData.value?.instrumentDistribution || {
              labels: ['No Data'],
              data: [0],
              backgroundColor: ['#E0E0E0']
            }
            pieChartInstance = new ChartClass(ctx, {
              type: 'doughnut',
              data: {
                labels: distributionData.labels || ['No Data'],
                datasets: [{
                  data: distributionData.data || [0],
                  backgroundColor: distributionData.backgroundColor || ['#E0E0E0'],
                  borderWidth: 2,
                  borderColor: '#fff'
                }]
              },
              options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                  legend: {
                    position: 'bottom',
                  },
                  title: {
                    display: false
                  }
                }
              }
            })
          }
        } catch (error) {
          console.error('Error rendering pie chart:', error)
        }
      }

      // Render yield curve chart
      if (yieldCurveChart.value) {
        try {
          const ctx = yieldCurveChart.value.getContext('2d')
          if (ctx) {
            const labels = yieldCurveData.value?.labels || []
            const datasets = yieldCurveData.value?.datasets || []

            yieldCurveChartInstance = new ChartClass(ctx, {
              type: 'line',
              data: {
                labels: labels,
                datasets: datasets
              },
              options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                  legend: {
                    position: 'top',
                  },
                  title: {
                    display: false
                  }
                },
                scales: {
                  y: {
                    beginAtZero: false,
                    title: {
                      display: true,
                      text: 'Yield Rate (%)'
                    }
                  },
                  x: {
                    title: {
                      display: true,
                      text: 'Maturity'
                    }
                  }
                }
              }
            })
          }
        } catch (error) {
          console.error('Error rendering yield curve chart:', error)
        }
      }
    }).catch(err => {
      console.error('Failed to load Chart.js:', err)
    })
  } catch (error) {
    console.error('Error rendering charts:', error)
  }
}

// Execute yield curve calculation
const executeYieldCurveCalculation = async () => {
  try {
    const response = await calculationsAPI.execute('yield_curve')
    if (response.success) {
      console.log('Yield curve calculation completed:', response.data)
      // Reload dashboard data to show updated activity
      await loadDashboardData()
    }
  } catch (error) {
    console.error('Error executing yield curve calculation:', error)
  }
}

const instruments = ref([
  {
    name: 'Treasury Bills',
    description: 'Short-term government securities with maturities of one year or less',
    icon: 'mdi-bank',
    color: '#0B2A44',
    count: 0
  },
  {
    name: 'Bonds',
    description: 'Long-term debt instruments with fixed interest payments',
    icon: 'mdi-chart-line',
    color: '#1E88E5',
    count: 0
  },
  {
    name: 'Money Market',
    description: 'Short-term borrowing and lending with maturities of one year or less',
    icon: 'mdi-cash',
    color: '#4CAF50',
    count: 0
  }
])

// Computed property for yield curve title based on uploaded dataset
const yieldCurveTitle = computed(() => {
  if (savedDatasets.value && savedDatasets.value.length > 0) {
    const instrumentType = savedDatasets.value[0].instrumentType || 'All Instruments'
    return `Yield Rate Trends - ${instrumentType}`
  }
  return 'Yield Rate Trends (2024)'
})


const navigateTo = (route: string) => {
  router.push(route)
}

// Function to refresh dashboard data - can be called from other components
const refreshDashboard = async () => {
  console.log('Refreshing dashboard data...')
  await loadDashboardData()
}

// Expose refresh function globally for other components to call
if (typeof window !== 'undefined') {
  (window as any).refreshDashboard = refreshDashboard
}

// Load data when component mounts
onMounted(() => {
  loadSavedDatasets()
  loadDashboardData()
})

// Cleanup charts on unmount
onUnmounted(() => {
  if (monthlyChartInstance) {
    monthlyChartInstance.destroy()
  }
  if (pieChartInstance) {
    pieChartInstance.destroy()
  }
  if (yieldCurveChartInstance) {
    yieldCurveChartInstance.destroy()
  }
})
</script>

<style scoped>
.dashboard-view {
  width: 100%;
  margin: 0 auto;
  padding: 20px;
  min-height: 100vh;
}

.dashboard-header {
  margin-bottom: 32px;
}

.page-title {
  color: #0B2A44;
  font-size: 32px;
  font-weight: 700;
  margin-bottom: 8px;
}

.page-subtitle {
  color: #666;
  font-size: 16px;
  margin: 0;
}

.kpi-row {
  margin-bottom: 32px;
}

/* Ensure consistent spacing for all major sections */
.content-row {
  margin-bottom: 32px;
}

.charts-section {
  margin-bottom: 32px;
}

.stats-row {
  margin-bottom: 32px;
}

/* Quick Stats Bar - Final Section */
.quick-stats-card {
  margin-bottom: 32px;
}

.kpi-card {
  height: 120px;
  border-radius: 12px;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.kpi-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
}

.kpi-content {
  display: flex;
  align-items: center;
  height: 100%;
  padding: 8px;
}

.kpi-icon {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 12px;
  flex-shrink: 0;
}

.kpi-icon .v-icon {
  font-size: 28px;
}

.kpi-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.kpi-value {
  font-size: 24px;
  font-weight: 700;
  color: #0B2A44;
  line-height: 1.2;
  margin-bottom: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.kpi-title {
  font-size: 12px;
  color: #666;
  margin-bottom: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.kpi-change {
  display: flex;
  align-items: center;
  font-size: 12px;
  font-weight: 600;
}

.kpi-change.positive {
  color: #4CAF50;
}

.kpi-change.neutral {
  color: #FFC107;
}

.content-row {
  margin-bottom: 32px;
}

.card-title {
  display: flex;
  align-items: center;
  color: #0B2A44;
  font-weight: 600;
  font-size: 18px;
}

.title-icon {
  margin-right: 8px;
  color: #0B2A44;
}

.action-card,
.activity-card,
.instruments-card {
  border-radius: 12px;
  height: 100%;
  margin-bottom: 32px;
}

.action-item {
  border-radius: 8px;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.action-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.action-title {
  font-weight: 600;
  color: #0B2A44;
  margin-bottom: 4px;
}

.action-desc {
  font-size: 12px;
  color: #666;
}

.activity-list {
  max-height: 300px;
  overflow-y: auto;
}

.activity-item {
  display: flex;
  align-items: flex-start;
  margin-bottom: 16px;
}

.activity-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-top: 6px;
  margin-right: 12px;
  flex-shrink: 0;
}

.activity-content {
  flex: 1;
}

.activity-text {
  font-size: 14px;
  color: #333;
  margin-bottom: 2px;
}

.activity-time {
  font-size: 12px;
  color: #666;
}

.instrument-item {
  border-radius: 8px;
  transition: transform 0.2s ease;
}

.instrument-item:hover {
  transform: translateY(-2px);
}

.instrument-name {
  font-weight: 600;
  color: #0B2A44;
  margin-bottom: 8px;
}

.instrument-desc {
  font-size: 14px;
  color: #666;
  margin-bottom: 12px;
}

.charts-section {
  margin-bottom: 32px;
}

.chart-card {
  border-radius: 12px;
  height: 100%;
}

.chart-placeholder {
  height: 300px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 20px;
  background: rgba(11, 42, 68, 0.02);
  border-radius: 8px;
  border: 2px dashed rgba(11, 42, 68, 0.1);
}

.chart-container {
  height: 300px;
  width: 100%;
  position: relative;
}

.chart-placeholder {
  height: 300px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 20px;
  background: rgba(11, 42, 68, 0.02);
  border-radius: 8px;
  border: 2px dashed rgba(11, 42, 68, 0.1);
}

.chart-placeholder.large {
  height: 400px;
}

.placeholder-text {
  font-size: 16px;
  font-weight: 600;
  color: #0B2A44;
  margin: 16px 0 8px 0;
}

.placeholder-subtitle {
  font-size: 14px;
  color: #666;
  margin: 0;
}

/* Additional Styles for Enhanced Components */
.stats-row {
  margin-bottom: 32px;
}

.stats-card {
  border-radius: 12px;
  height: 100%;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.stats-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
}

.metrics-grid {
  display: grid;
  gap: 20px;
}

.metric-item {
  padding: 16px;
  background: rgba(11, 42, 68, 0.03);
  border-radius: 8px;
  border-left: 4px solid #0B2A44;
}

.metric-label {
  font-size: 14px;
  color: #666;
  margin-bottom: 8px;
  font-weight: 500;
}

.metric-value {
  font-size: 18px;
  font-weight: 700;
  margin-bottom: 12px;
}

.metric-progress {
  margin-top: 8px;
}

.status-items {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.status-item {
  display: flex;
  align-items: center;
  padding: 12px;
  background: rgba(11, 42, 68, 0.03);
  border-radius: 8px;
  transition: transform 0.2s ease;
}

.status-item:hover {
  transform: translateX(4px);
}

.status-indicator {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  margin-right: 16px;
  flex-shrink: 0;
}

.status-indicator.status-online {
  background: #4CAF50;
  box-shadow: 0 0 0 3px rgba(76, 175, 80, 0.2);
}

.status-indicator.status-warning {
  background: #FFC107;
  box-shadow: 0 0 0 3px rgba(255, 193, 7, 0.2);
  animation: pulse 2s infinite;
}

.status-indicator.status-offline {
  background: #F44336;
  box-shadow: 0 0 0 3px rgba(244, 67, 54, 0.2);
}

@keyframes pulse {
  0% { opacity: 1; }
  50% { opacity: 0.6; }
  100% { opacity: 1; }
}

.status-info {
  flex: 1;
}

.status-name {
  font-size: 14px;
  font-weight: 600;
  color: #333;
  margin-bottom: 2px;
}

.status-value {
  font-size: 12px;
  color: #666;
}

.quick-stats-card {
  border-radius: 12px;
  background: linear-gradient(135deg, #0B2A44 0%, #1E88E5 100%);
  color: white;
}

.quick-stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 20px;
}

.quick-stat {
  display: flex;
  align-items: center;
  padding: 12px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  backdrop-filter: blur(10px);
  transition: transform 0.2s ease, background 0.2s ease;
}

.quick-stat:hover {
  transform: translateY(-2px);
  background: rgba(255, 255, 255, 0.15);
}

.quick-stat-icon {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 12px;
  background: rgba(255, 255, 255, 0.2);
}

.quick-stat-content {
  flex: 1;
}

.quick-stat-label {
  font-size: 12px;
  opacity: 0.8;
  margin-bottom: 2px;
  font-weight: 500;
}

.quick-stat-value {
  font-size: 16px;
  font-weight: 700;
  color: white;
}

/* Enhanced KPI Card Styles */
.kpi-card {
  background: white;
  border: 1px solid rgba(11, 42, 68, 0.08);
  position: relative;
  overflow: hidden;
}

.kpi-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, #0B2A44, #1E88E5, #4CAF50);
}

.kpi-card:hover::before {
  height: 4px;
}

/* Enhanced Action Card Styles */
.action-card,
.activity-card,
.instruments-card {
  background: white;
  border: 1px solid rgba(11, 42, 68, 0.08);
  position: relative;
}

.action-card::before,
.activity-card::before,
.instruments-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, #0B2A44, #1E88E5);
}

/* Enhanced Chart Card Styles */
.chart-card {
  background: white;
  border: 1px solid rgba(11, 42, 68, 0.08);
  position: relative;
}

.chart-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, #1E88E5, #4CAF50);
}

/* Enhanced Instrument Item Styles */
.instrument-item {
  background: white;
  border: 1px solid rgba(11, 42, 68, 0.08);
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.instrument-item::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, #4CAF50, #FFC107);
  transform: scaleX(0);
  transition: transform 0.3s ease;
}

.instrument-item:hover::before {
  transform: scaleX(1);
}

/* Responsive Design */
@media (max-width: 960px) {
  .quick-stats-grid {
    grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
    gap: 12px;
  }
  
  .quick-stat {
    padding: 8px;
  }
  
  .quick-stat-icon {
    width: 32px;
    height: 32px;
    margin-right: 8px;
  }
  
  .quick-stat-value {
    font-size: 14px;
  }
}

@media (max-width: 600px) {
  .dashboard-view {
    padding: 0 16px;
  }
  
  .kpi-card {
    height: 100px;
  }
  
  .kpi-value {
    font-size: 24px;
  }
  
  .quick-stats-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 8px;
  }
  
  .quick-stat {
    flex-direction: column;
    text-align: center;
    padding: 12px;
  }
  
  .quick-stat-icon {
    margin-right: 0;
    margin-bottom: 8px;
  }
}
</style>
