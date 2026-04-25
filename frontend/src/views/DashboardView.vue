<template>
  <app-layout>
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
                  <div class="kpi-change" :class="kpi.changeClass">
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
              <v-row>
                <v-col cols="12" sm="6" v-for="action in quickActions" :key="action.title">
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

      <!-- Charts Section -->
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

      <!-- Yield Rate Chart -->
      <v-row>
        <v-col cols="12">
          <v-card class="chart-card" elevation="2">
            <v-card-title class="card-title">
              <v-icon class="title-icon">mdi-trending-up</v-icon>
              Yield Rate Trends (2024)
            </v-card-title>
            <v-card-text>
              <div class="chart-container large">
                <canvas ref="yieldChart" width="800" height="300"></canvas>
              </div>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <!-- Financial Instruments Overview -->
      <v-row>
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
                      <v-chip 
                        :color="instrument.color" 
                        variant="tonal" 
                        size="small"
                        class="mt-2"
                      >
                        {{ instrument.count }} Active
                      </v-chip>
                    </v-card-text>
                  </v-card>
                </v-col>
              </v-row>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <!-- Additional Statistics Row -->
      <v-row class="stats-row">
        <v-col cols="12" md="6">
          <v-card class="stats-card" elevation="2">
            <v-card-title class="card-title">
              <v-icon class="title-icon">mdi-chart-box</v-icon>
              Performance Metrics
            </v-card-title>
            <v-card-text>
              <div class="metrics-grid">
                <div class="metric-item" v-for="metric in performanceMetrics" :key="metric.name">
                  <div class="metric-label">{{ metric.name }}</div>
                  <div class="metric-value" :style="{ color: metric.color }">{{ metric.value }}</div>
                  <div class="metric-progress">
                    <v-progress-linear 
                      :model-value="metric.progress" 
                      :color="metric.color"
                      height="4"
                      rounded
                    ></v-progress-linear>
                  </div>
                </div>
              </div>
            </v-card-text>
          </v-card>
        </v-col>
        <v-col cols="12" md="6">
          <v-card class="stats-card" elevation="2">
            <v-card-title class="card-title">
              <v-icon class="title-icon">mdi-alert-circle</v-icon>
              System Status
            </v-card-title>
            <v-card-text>
              <div class="status-items">
                <div class="status-item" v-for="status in systemStatus" :key="status.name">
                  <div class="status-indicator" :class="status.class"></div>
                  <div class="status-info">
                    <div class="status-name">{{ status.name }}</div>
                    <div class="status-value">{{ status.value }}</div>
                  </div>
                </div>
              </div>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <!-- Quick Stats Bar -->
      <v-row>
        <v-col cols="12">
          <v-card class="quick-stats-card" elevation="2">
            <v-card-text class="pa-4">
              <div class="quick-stats-grid">
                <div class="quick-stat" v-for="stat in quickStats" :key="stat.label">
                  <div class="quick-stat-icon" :style="{ backgroundColor: stat.bgColor }">
                    <v-icon :color="stat.color" size="20">{{ stat.icon }}</v-icon>
                  </div>
                  <div class="quick-stat-content">
                    <div class="quick-stat-label">{{ stat.label }}</div>
                    <div class="quick-stat-value">{{ stat.value }}</div>
                  </div>
                </div>
              </div>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </div>
  </app-layout>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import AppLayout from '../components/AppLayout.vue'
import Chart from 'chart.js/auto'

const router = useRouter()

const monthlyChart = ref()
const pieChart = ref()
const yieldChart = ref()

onMounted(() => {
  nextTick(() => {
    initializeCharts()
  })
})

const initializeCharts = () => {
  // Monthly Activity Chart
  if (monthlyChart.value) {
    const ctx = monthlyChart.value.getContext('2d')
    if (ctx) {
      new Chart(ctx, {
        type: 'line',
        data: {
          labels: chartData.value.monthlyData.map(d => d.month),
          datasets: [
            {
              label: 'Datasets',
              data: chartData.value.monthlyData.map(d => d.datasets),
              borderColor: '#0B2A44',
              backgroundColor: 'rgba(11, 42, 68, 0.1)',
              borderWidth: 3,
              fill: true,
              tension: 0.4
            },
            {
              label: 'Calculations',
              data: chartData.value.monthlyData.map(d => d.calculations),
              borderColor: '#1E88E5',
              backgroundColor: 'rgba(30, 136, 229, 0.1)',
              borderWidth: 3,
              fill: true,
              tension: 0.4
            },
            {
              label: 'Reports',
              data: chartData.value.monthlyData.map(d => d.reports),
              borderColor: '#4CAF50',
              backgroundColor: 'rgba(76, 175, 80, 0.1)',
              borderWidth: 3,
              fill: true,
              tension: 0.4
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              position: 'top'
            }
          }
        }
      })
    }
  }

  // Pie Chart
  if (pieChart.value) {
    const ctx = pieChart.value.getContext('2d')
    if (ctx) {
      new Chart(ctx, {
        type: 'pie',
        data: {
          labels: chartData.value.instrumentDistribution.map(d => d.name),
          datasets: [{
            data: chartData.value.instrumentDistribution.map(d => d.value),
            backgroundColor: chartData.value.instrumentDistribution.map(d => d.color),
            borderWidth: 2,
            borderColor: '#fff'
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              position: 'bottom'
            }
          }
        }
      })
    }
  }

  // Yield Rate Chart
  if (yieldChart.value) {
    const ctx = yieldChart.value.getContext('2d')
    if (ctx) {
      new Chart(ctx, {
        type: 'line',
        data: {
          labels: chartData.value.yieldRates.map(d => d.date),
          datasets: [{
            label: 'Yield Rate (%)',
            data: chartData.value.yieldRates.map(d => d.rate),
            borderColor: '#0B2A44',
            backgroundColor: 'rgba(11, 42, 68, 0.1)',
            borderWidth: 3,
            fill: true,
            tension: 0.4
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              position: 'top'
            }
          },
          scales: {
            y: {
              beginAtZero: false,
              ticks: {
                callback: function(value) {
                  return value + '%'
                }
              }
            }
          }
        }
      })
    }
  }
}

const kpiData = ref([
  {
    title: 'Total Datasets',
    value: '24',
    icon: 'mdi-database',
    color: 'rgba(11, 42, 68, 0.1)',
    iconColor: '#0B2A44',
    change: '+12%',
    changeIcon: 'mdi-trending-up',
    changeClass: 'positive'
  },
  {
    title: 'Calculations',
    value: '156',
    icon: 'mdi-calculator',
    color: 'rgba(30, 136, 229, 0.1)',
    iconColor: '#1E88E5',
    change: '+8%',
    changeIcon: 'mdi-trending-up',
    changeClass: 'positive'
  },
  {
    title: 'Reports Generated',
    value: '48',
    icon: 'mdi-file-document',
    color: 'rgba(76, 175, 80, 0.1)',
    iconColor: '#4CAF50',
    change: '+15%',
    changeIcon: 'mdi-trending-up',
    changeClass: 'positive'
  },
  {
    title: 'Active Instruments',
    value: '3',
    icon: 'mdi-chart-line',
    color: 'rgba(255, 193, 7, 0.1)',
    iconColor: '#FFC107',
    change: '0%',
    changeIcon: 'mdi-minus',
    changeClass: 'neutral'
  }
])

// Add sample chart data for dashboard
const chartData = ref({
  monthlyData: [
    { month: 'Jan', datasets: 12, calculations: 45, reports: 8 },
    { month: 'Feb', datasets: 15, calculations: 52, reports: 12 },
    { month: 'Mar', datasets: 18, calculations: 68, reports: 15 },
    { month: 'Apr', datasets: 24, calculations: 89, reports: 18 },
    { month: 'May', datasets: 28, calculations: 102, reports: 22 },
    { month: 'Jun', datasets: 32, calculations: 125, reports: 28 }
  ],
  instrumentDistribution: [
    { name: 'Treasury Bills', value: 8, color: '#0B2A44' },
    { name: 'Bonds', value: 12, color: '#1E88E5' },
    { name: 'Money Market', value: 4, color: '#4CAF50' }
  ],
  yieldRates: [
    { date: '2024-01', rate: 4.2 },
    { date: '2024-02', rate: 4.5 },
    { date: '2024-03', rate: 4.8 },
    { date: '2024-04', rate: 5.1 },
    { date: '2024-05', rate: 5.3 },
    { date: '2024-06', rate: 5.0 }
  ]
})

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
  }
])

const recentActivities = ref([
  {
    id: 1,
    text: 'Treasury Bills dataset uploaded',
    time: '2 hours ago',
    color: '#0B2A44'
  },
  {
    id: 2,
    text: 'Bond calculations completed',
    time: '4 hours ago',
    color: '#1E88E5'
  },
  {
    id: 3,
    text: 'Money market analysis generated',
    time: '6 hours ago',
    color: '#4CAF50'
  },
  {
    id: 4,
    text: 'Monthly report exported to PDF',
    time: '1 day ago',
    color: '#FFC107'
  }
])

const instruments = ref([
  {
    name: 'Treasury Bills',
    description: 'Short-term government securities with maturities of one year or less',
    icon: 'mdi-bank',
    color: '#0B2A44',
    count: 8
  },
  {
    name: 'Bonds',
    description: 'Long-term debt instruments with fixed interest payments',
    icon: 'mdi-chart-line',
    color: '#1E88E5',
    count: 12
  },
  {
    name: 'Money Market',
    description: 'Short-term borrowing and lending with maturities of one year or less',
    icon: 'mdi-cash',
    color: '#4CAF50',
    count: 4
  }
])

// Performance Metrics Data
const performanceMetrics = ref([
  {
    name: 'Processing Speed',
    value: '98.5%',
    color: '#4CAF50',
    progress: 98
  },
  {
    name: 'Data Accuracy',
    value: '99.2%',
    color: '#0B2A44',
    progress: 99
  },
  {
    name: 'System Uptime',
    value: '99.8%',
    color: '#1E88E5',
    progress: 100
  },
  {
    name: 'User Satisfaction',
    value: '94.7%',
    color: '#FFC107',
    progress: 95
  }
])

// System Status Data
const systemStatus = ref([
  {
    name: 'Database Connection',
    value: 'Healthy',
    class: 'status-online'
  },
  {
    name: 'API Services',
    value: 'Operational',
    class: 'status-online'
  },
  {
    name: 'Data Processing',
    value: 'Running',
    class: 'status-warning'
  },
  {
    name: 'Backup System',
    value: 'Completed',
    class: 'status-online'
  }
])

// Quick Stats Data
const quickStats = ref([
  {
    label: 'Daily Users',
    value: '1,247',
    icon: 'mdi-account',
    color: '#0B2A44',
    bgColor: 'rgba(11, 42, 68, 0.1)'
  },
  {
    label: 'Transactions',
    value: '8,923',
    icon: 'mdi-swap-horizontal',
    color: '#1E88E5',
    bgColor: 'rgba(30, 136, 229, 0.1)'
  },
  {
    label: 'Data Points',
    value: '45.2K',
    icon: 'mdi-database',
    color: '#4CAF50',
    bgColor: 'rgba(76, 175, 80, 0.1)'
  },
  {
    label: 'Success Rate',
    value: '99.8%',
    icon: 'mdi-check-circle',
    color: '#FFC107',
    bgColor: 'rgba(255, 193, 7, 0.1)'
  },
  {
    label: 'Avg Response',
    value: '0.8s',
    icon: 'mdi-speedometer',
    color: '#F44336',
    bgColor: 'rgba(244, 67, 54, 0.1)'
  },
  {
    label: 'Storage Used',
    value: '2.3GB',
    icon: 'mdi-harddisk',
    color: '#9C27B0',
    bgColor: 'rgba(156, 39, 176, 0.1)'
  }
])

const navigateTo = (route: string) => {
  router.push(route)
}
</script>

<style scoped>
.dashboard-view {
  max-width: 1400px;
  margin: 0 auto;
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
}

.kpi-icon {
  width: 60px;
  height: 60px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 16px;
}

.kpi-info {
  flex: 1;
}

.kpi-value {
  font-size: 28px;
  font-weight: 700;
  color: #0B2A44;
  line-height: 1;
  margin-bottom: 4px;
}

.kpi-title {
  font-size: 14px;
  color: #666;
  margin-bottom: 4px;
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

.chart-container {
  height: 300px;
  position: relative;
}

.chart-container.large {
  height: 400px;
  position: relative;
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
