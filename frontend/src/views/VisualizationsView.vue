<template>
  <fixed-layout>
    <div class="visualizations-view">

      <!-- Header Section -->
      <div class="dashboard-header">
        <h1 class="page-title">Data Visualizations</h1>
        <p class="page-subtitle">Visualize your financial calculations with interactive charts and graphs</p>
      </div>

      <!-- Overview -->
      <v-card class="stats-card" elevation="2">
        <v-card-title class="card-title">
          <v-icon class="title-icon">mdi-chart-line</v-icon>
          Calculation Overview
        </v-card-title>

        <v-card-text>
          <v-row class="kpi-row">
            <v-col cols="12" sm="6" md="3" v-for="kpi in visualizationsKpiData" :key="kpi.title">
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
        </v-card-text>
      </v-card>

      <!-- Chart Selection -->
      <v-card class="selection-card" elevation="2">
        <v-card-title class="card-title">
          <v-icon class="title-icon">mdi-chart-pie</v-icon>
          Select Visualization Type
        </v-card-title>

        <v-card-text>
          <div class="chart-buttons">
            <v-btn
              v-for="chart in chartTypes"
              :key="chart.value"
              :variant="selectedChart === chart.value ? 'flat' : 'outlined'"
              :color="selectedChart === chart.value ? 'primary' : undefined"
              class="chart-btn"
              @click="selectedChart = chart.value"
            >
              <v-icon start>{{ chart.icon }}</v-icon>
              {{ chart.label }}
            </v-btn>
          </div>
        </v-card-text>
      </v-card>

      <!-- Main Chart -->
      <v-card class="main-chart-card" elevation="2">
        <v-card-title class="card-title">
          <v-icon class="title-icon">mdi-chart-line</v-icon>
          {{ getMainChartTitle() }}
        </v-card-title>

        <v-card-text>
          <div class="chart-container">
            <canvas ref="mainChart"></canvas>
          </div>
        </v-card-text>
      </v-card>

      <!-- Action -->
      <v-card class="action-card" elevation="2">
        <v-card-text class="text-center">
          <v-btn color="primary" size="large" @click="proceedToReports">
            <v-icon start>mdi-arrow-right</v-icon>
            Proceed to Report Generation
          </v-btn>
        </v-card-text>
      </v-card>

    </div>
  </fixed-layout>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick, computed } from 'vue'
import { useRouter } from 'vue-router'
import FixedLayout from '../components/FixedLayout.vue'

const router = useRouter()

const calculationData = ref<any>(null)
const selectedChart = ref('bar')
const mainChart = ref<HTMLCanvasElement | null>(null)

const recordsValue = computed(() => calculationData.value?.calculations?.length ?? 0)
const instrumentTypeValue = computed(() => calculationData.value?.instrumentType ?? 'N/A')
const avgYieldValue = computed(() => getAverageYield() + '%')
const chartTypeValue = computed(() => selectedChart.value)

const visualizationsKpiData = ref([
  {
    title: 'Records',
    value: recordsValue,
    icon: 'mdi-database',
    color: 'rgba(11, 42, 68, 0.1)',
    iconColor: '#0B2A44',
    change: '0%',
    changeIcon: 'mdi-minus',
    changeClass: 'neutral'
  },
  {
    title: 'Instrument Type',
    value: instrumentTypeValue,
    icon: 'mdi-chart-bubble',
    color: 'rgba(30, 136, 229, 0.1)',
    iconColor: '#1E88E5',
    change: '0%',
    changeIcon: 'mdi-minus',
    changeClass: 'neutral'
  },
  {
    title: 'Average Yield',
    value: avgYieldValue,
    icon: 'mdi-trending-up',
    color: 'rgba(76, 175, 80, 0.1)',
    iconColor: '#4CAF50',
    change: '0%',
    changeIcon: 'mdi-minus',
    changeClass: 'neutral'
  },
  {
    title: 'Chart Type',
    value: chartTypeValue,
    icon: 'mdi-chart-pie',
    color: 'rgba(255, 193, 7, 0.1)',
    iconColor: '#FFC107',
    change: '0%',
    changeIcon: 'mdi-minus',
    changeClass: 'neutral'
  }
])

const chartTypes = [
  { value: 'bar', label: 'Bar Chart', icon: 'mdi-chart-bar' },
  { value: 'line', label: 'Line Chart', icon: 'mdi-chart-line' },
  { value: 'pie', label: 'Pie Chart', icon: 'mdi-chart-pie' },
  { value: 'area', label: 'Area Chart', icon: 'mdi-chart-area' }
]

onMounted(() => {
  const stored = localStorage.getItem('calculations')
  if (stored) {
    calculationData.value = JSON.parse(stored)
  }
})

const getAverageYield = () => {
  const list = calculationData.value?.calculations || []
  if (!list.length) return '0.00'

  const yields = list.map((c: any) =>
    parseFloat((c.yieldRate || '0').replace('%', ''))
  )

  const avg = yields.reduce((a: number, b: number) => a + b, 0) / yields.length
  return avg.toFixed(2)
}

const getMainChartTitle = () => {
  return {
    bar: 'Face Value vs Purchase Price',
    line: 'Yield Trend',
    pie: 'Distribution',
    area: 'Financial Breakdown'
  }[selectedChart.value] || 'Chart'
}

const proceedToReports = () => {
  router.push('/reports')
}
</script>

<style scoped>
.visualizations-view {
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

.stats-card {
  border-radius: 12px;
  margin-bottom: 32px;
  background: white;
  border: 1px solid rgba(11, 42, 68, 0.08);
  position: relative;
}

.stats-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, #0B2A44, #1E88E5);
}

.chart-card {
  border-radius: 12px;
  margin-bottom: 32px;
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
  background: linear-gradient(90deg, #0B2A44, #1E88E5);
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

.chart-placeholder {
  height: 400px;
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

.action-buttons {
  margin: 20px 0;
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

/* KPI Styles - Matching DashboardView and ReportsView */
.kpi-row {
  margin-bottom: 32px;
}

.kpi-card {
  height: 120px;
  border-radius: 12px;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  background: white;
  border: 1px solid rgba(11, 42, 68, 0.08);
  position: relative;
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

.kpi-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
}

.kpi-card:hover::before {
  height: 4px;
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

.kpi-change.negative {
  color: #F44336;
}
</style>