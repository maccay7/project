<template>
  <fixed-layout>
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

      <!-- Charts Section - Backend Data Required -->
      <v-row class="charts-section">
        <v-col cols="12" md="8">
          <v-card class="chart-card" elevation="2">
            <v-card-title class="card-title">
              <v-icon class="title-icon">mdi-chart-line</v-icon>
              Monthly Activity Trends
            </v-card-title>
            <v-card-text>
              <v-alert type="info" variant="tonal" class="mb-4">
                <v-icon left>mdi-database</v-icon>
                Chart requires backend data connection
              </v-alert>
              <div class="chart-placeholder">
                <v-icon size="64" color="#0B2A44">mdi-chart-line</v-icon>
                <p class="placeholder-text">Monthly activity trends will display here when connected to backend</p>
                <p class="placeholder-subtitle">Expected data: Monthly datasets, calculations, and reports</p>
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
              <v-alert type="info" variant="tonal" class="mb-4">
                <v-icon left>mdi-database</v-icon>
                Chart requires backend data connection
              </v-alert>
              <div class="chart-placeholder">
                <v-icon size="48" color="#1E88E5">mdi-chart-pie</v-icon>
                <p class="placeholder-text">Instrument distribution will display here when connected to backend</p>
                <p class="placeholder-subtitle">Expected data: Treasury Bills, Bonds, Money Market</p>
              </div>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <!-- Yield Rate Chart - Backend Data Required -->
      <v-row class="mb-8">
        <v-col cols="12">
          <v-card class="chart-card" elevation="2">
            <v-card-title class="card-title">
              <v-icon class="title-icon">mdi-trending-up</v-icon>
              Yield Rate Trends (2024)
            </v-card-title>
            <v-card-text>
              <v-alert type="info" variant="tonal" class="mb-4">
                <v-icon left>mdi-database</v-icon>
                Chart requires backend data connection
              </v-alert>
              <div class="chart-placeholder large">
                <v-icon size="80" color="#4CAF50">mdi-trending-up</v-icon>
                <p class="placeholder-text">Yield rate trends will display here when connected to backend</p>
                <p class="placeholder-subtitle">Expected data: Monthly yield rates for all instruments</p>
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
              <!-- Top Row - 3 Stats -->
              <v-row class="mb-3">
                <v-col cols="12" sm="4" v-for="stat in quickStats.slice(0, 3)" :key="stat.label">
                  <div class="quick-stat">
                    <div class="quick-stat-icon" :style="{ backgroundColor: stat.bgColor }">
                      <v-icon :color="stat.color" size="20">{{ stat.icon }}</v-icon>
                    </div>
                    <div class="quick-stat-content">
                      <div class="quick-stat-label">{{ stat.label }}</div>
                      <div class="quick-stat-value">{{ stat.value }}</div>
                    </div>
                  </div>
                </v-col>
              </v-row>
              
              <!-- Bottom Row - 3 Stats -->
              <v-row>
                <v-col cols="12" sm="4" v-for="stat in quickStats.slice(3, 6)" :key="stat.label">
                  <div class="quick-stat">
                    <div class="quick-stat-icon" :style="{ backgroundColor: stat.bgColor }">
                      <v-icon :color="stat.color" size="20">{{ stat.icon }}</v-icon>
                    </div>
                    <div class="quick-stat-content">
                      <div class="quick-stat-label">{{ stat.label }}</div>
                      <div class="quick-stat-value">{{ stat.value }}</div>
                    </div>
                  </div>
                </v-col>
              </v-row>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </div>
  </fixed-layout>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import FixedLayout from '../components/FixedLayout.vue'

const router = useRouter()

const kpiData = ref([
  {
    title: 'Total Datasets',
    value: '0',
    icon: 'mdi-database',
    color: 'rgba(11, 42, 68, 0.1)',
    iconColor: '#0B2A44',
    change: '0%',
    changeIcon: 'mdi-minus',
    changeClass: 'neutral'
  },
  {
    title: 'Calculations',
    value: '0',
    icon: 'mdi-calculator',
    color: 'rgba(30, 136, 229, 0.1)',
    iconColor: '#1E88E5',
    change: '0%',
    changeIcon: 'mdi-minus',
    changeClass: 'neutral'
  },
  {
    title: 'Reports Generated',
    value: '0',
    icon: 'mdi-file-document',
    color: 'rgba(76, 175, 80, 0.1)',
    iconColor: '#4CAF50',
    change: '0%',
    changeIcon: 'mdi-minus',
    changeClass: 'neutral'
  },
  {
    title: 'Active Instruments',
    value: '0',
    icon: 'mdi-chart-line',
    color: 'rgba(255, 193, 7, 0.1)',
    iconColor: '#FFC107',
    change: '0%',
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

// Performance Metrics Data
const performanceMetrics = ref([
  {
    name: 'Processing Speed',
    value: '0%',
    color: '#4CAF50',
    progress: 0
  },
  {
    name: 'Data Accuracy',
    value: '0%',
    color: '#0B2A44',
    progress: 0
  },
  {
    name: 'System Uptime',
    value: '0%',
    color: '#1E88E5',
    progress: 0
  },
  {
    name: 'User Satisfaction',
    value: '0%',
    color: '#FFC107',
    progress: 0
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
    value: '0',
    icon: 'mdi-account',
    color: '#0B2A44',
    bgColor: 'rgba(11, 42, 68, 0.1)'
  },
  {
    label: 'Transactions',
    value: '0',
    icon: 'mdi-swap-horizontal',
    color: '#1E88E5',
    bgColor: 'rgba(30, 136, 229, 0.1)'
  },
  {
    label: 'Data Points',
    value: '0',
    icon: 'mdi-database',
    color: '#4CAF50',
    bgColor: 'rgba(76, 175, 80, 0.1)'
  },
  {
    label: 'Success Rate',
    value: '0%',
    icon: 'mdi-check-circle',
    color: '#FFC107',
    bgColor: 'rgba(255, 193, 7, 0.1)'
  },
  {
    label: 'Avg Response',
    value: '0s',
    icon: 'mdi-speedometer',
    color: '#F44336',
    bgColor: 'rgba(244, 67, 54, 0.1)'
  },
  {
    label: 'Storage Used',
    value: '0GB',
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
