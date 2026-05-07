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
        </v-card-text>
      </v-card>

      <!-- Yield Curve Chart -->
      <v-card class="chart-card" elevation="2">
        <v-card-title class="card-title">
          <v-icon class="title-icon">mdi-chart-line</v-icon>
          Yield Curve (FRED API)
        </v-card-title>
        <v-card-text>
          <!-- Filters -->
          <v-row class="mb-4">
            <v-col cols="12" md="4">
              <v-select
                v-model="selectedParameter"
                :items="yieldParameters"
                label="Parameter"
                density="compact"
                @update:modelValue="updateYieldCurve"
              ></v-select>
              <v-text-field
                v-if="selectedParameter === 'custom'"
                v-model="customParameter"
                label="Custom Parameter"
                placeholder="Enter parameter (e.g., DGS5)"
                density="compact"
                class="mt-2"
                @input="updateYieldCurve"
              ></v-text-field>
            </v-col>
            <v-col cols="12" md="4">
              <v-select
                v-model="selectedCurrency"
                :items="currencies"
                label="Currency"
                density="compact"
                @update:modelValue="updateYieldCurve"
              ></v-select>
              <v-text-field
                v-if="selectedCurrency === 'Custom'"
                v-model="customCurrency"
                label="Custom Currency"
                placeholder="Enter currency (e.g., ZAR)"
                density="compact"
                class="mt-2"
                @input="updateYieldCurve"
              ></v-text-field>
            </v-col>
            <v-col cols="12" md="4">
              <v-text-field
                v-model="selectedCountry"
                label="Country"
                placeholder="Enter country (e.g., USA, South Africa)"
                density="compact"
                @input="updateYieldCurve"
              ></v-text-field>
            </v-col>
          </v-row>
          <div class="chart-container">
            <canvas 
              ref="yieldCurveChart"
              id="yieldCurveChart"
              width="400"
              height="200"
            ></canvas>
          </div>
        </v-card-text>
      </v-card>

      <!-- Comparison Line Graph for All Instruments -->
      <v-card class="chart-card" elevation="2">
        <v-card-title class="card-title">
          <v-icon class="title-icon">mdi-chart-multiline</v-icon>
          Instrument Comparison
        </v-card-title>
        <v-card-text>
          <div class="chart-container">
            <canvas 
              ref="comparisonChart"
              id="comparisonChart"
              width="400"
              height="200"
            ></canvas>
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
import { ref, onMounted, nextTick, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import FixedLayout from '../components/FixedLayout.vue'

// Import Chart.js
import {
  Chart,
  CategoryScale,
  LinearScale,
  LineElement,
  PointElement,
  LineController,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js'

// Register Chart.js components
Chart.register(
  LineController,
  CategoryScale,
  LinearScale,
  LineElement,
  PointElement,
  Title,
  Tooltip,
  Legend,
  Filler
)

const router = useRouter()

const calculationData = ref<any>(null)
const yieldCurveData = ref<any>(null)
const yieldCurveChart = ref<HTMLCanvasElement | null>(null)
const comparisonChart = ref<HTMLCanvasElement | null>(null)
let yieldCurveChartInstance: any = null
let comparisonChartInstance: any = null

// Filter variables
const selectedParameter = ref('DGS10')
const selectedCurrency = ref('USD')
const selectedCountry = ref('USA')
const customParameter = ref('')
const customCurrency = ref('')
const customCountry = ref('')
const yieldParameters = ref([
  { title: '3-Month Treasury', value: 'DGS3MO' },
  { title: '10-Year Treasury', value: 'DGS10' },
  { title: '30-Year Treasury', value: 'DGS30' },
  { title: '2-Year Treasury', value: 'DGS2' },
  { title: 'Custom', value: 'custom' }
])
const currencies = ref(['USD', 'EUR', 'GBP', 'JPY', 'Custom'])

const recordsValue = computed(() => calculationData.value?.calculations?.length ?? 0)
const instrumentTypeValue = computed(() => calculationData.value?.instrumentType ?? 'N/A')
const avgYieldValue = computed(() => getAverageYield() + '%')

const visualizationsKpiData = ref([
  {
    title: 'Records',
    value: recordsValue,
    icon: 'mdi-database',
    color: 'rgba(11, 42, 68, 0.1)',
    iconColor: '#0B2A44',
    change: '',
    changeIcon: 'mdi-minus',
    changeClass: 'neutral'
  },
  {
    title: 'Instrument Type',
    value: instrumentTypeValue,
    icon: 'mdi-chart-bubble',
    color: 'rgba(30, 136, 229, 0.1)',
    iconColor: '#1E88E5',
    change: '',
    changeIcon: 'mdi-minus',
    changeClass: 'neutral'
  },
  {
    title: 'Average Yield',
    value: avgYieldValue,
    icon: 'mdi-trending-up',
    color: 'rgba(76, 175, 80, 0.1)',
    iconColor: '#4CAF50',
    change: '',
    changeIcon: 'mdi-minus',
    changeClass: 'neutral'
  },
  {
    title: 'Data Source',
    value: 'FRED API',
    icon: 'mdi-api',
    color: 'rgba(255, 193, 7, 0.1)',
    iconColor: '#FFC107',
    change: '',
    changeIcon: 'mdi-check',
    changeClass: 'neutral'
  }
])

onMounted(async () => {
  const stored = localStorage.getItem('calculations')
  if (stored) {
    calculationData.value = JSON.parse(stored)
    console.log('Loaded calculation data for visualizations:', calculationData.value)
  } else {
    loadSampleCalculationData()
  }
  await fetchYieldCurveData()
  nextTick(() => {
    setTimeout(() => {
      initializeYieldCurveChart()
      initializeComparisonChart()
    }, 100)
  })
})


const loadSampleCalculationData = () => {
  calculationData.value = {
    success: true,
    calculations: [
      {
        instrument_type: 'Commercial Paper',
        principal: 100000,
        interest_earned: 369.86,
        term_days: 30,
        annual_yield: 4.5,
        effective_rate: 4.5941,
        maturity_value: 100369.86,
        face_value: 100000,
        purchase_price: 99625
      },
      {
        instrument_type: 'Certificate of Deposit',
        principal: 50000,
        interest_earned: 641.10,
        term_days: 90,
        annual_yield: 5.2,
        effective_rate: 5.3028,
        maturity_value: 50641.10,
        face_value: 50000,
        purchase_price: 50000
      },
      {
        instrument_type: 'Repo Agreement',
        principal: 250000,
        interest_earned: 5917.81,
        term_days: 180,
        annual_yield: 4.8,
        effective_rate: 4.8584,
        maturity_value: 255917.81,
        face_value: 250000,
        purchase_price: 250000
      },
      {
        instrument_type: 'Bankers Acceptance',
        principal: 75000,
        interest_earned: 2274.66,
        term_days: 270,
        annual_yield: 4.1,
        effective_rate: 4.1217,
        maturity_value: 77274.66,
        face_value: 75000,
        purchase_price: 74775
      }
    ],
    instrumentType: 'money_market',
    timestamp: new Date().toISOString()
  }
}

const fetchYieldCurveData = async () => {
  try {
    console.log('Fetching yield curve data from FRED API...')
    const response = await fetch('http://localhost:5000/api/fred-yield-curve')
    const data = await response.json()

    if (data.success && data.data) {
      console.log('Yield curve data fetched:', data.data)
      yieldCurveData.value = data.data
    } else {
      console.error('Yield curve data not available from FRED API')
    }
  } catch (error) {
    console.error('Error fetching yield curve data:', error)
  }
}

const initializeYieldCurveChart = () => {
  if (!yieldCurveChart.value) {
    console.log('Yield curve canvas not available')
    return
  }

  // Destroy existing chart if it exists
  if (yieldCurveChartInstance) {
    yieldCurveChartInstance.destroy()
    yieldCurveChartInstance = null
  }

  console.log('Initializing yield curve chart with data:', yieldCurveData.value)

  const ctx = yieldCurveChart.value.getContext('2d')
  if (!ctx) {
    console.error('Failed to get canvas context')
    return
  }

  const data = yieldCurveData.value || {
    labels: ['3M', '6M', '1Y', '2Y', '5Y', '10Y', '30Y'],
    current: [0.72, 0.82, 0.92, 1.02, 1.12, 4.06, 3.86],
    historical: []
  }

  yieldCurveChartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels: data.labels,
      datasets: [{
        label: 'Yield Curve',
        data: data.current,
        borderColor: '#217346',
        backgroundColor: 'rgba(33, 115, 70, 0.1)',
        borderWidth: 2,
        tension: 0.4,
        fill: true
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        title: {
          display: true,
          text: 'US Treasury Yield Curve (FRED API)',
          font: {
            size: 16,
            weight: 'bold'
          }
        },
        legend: {
          display: true,
          position: 'top'
        },
        tooltip: {
          mode: 'index',
          intersect: false
        }
      },
      scales: {
        x: {
          title: {
            display: true,
            text: 'Maturity'
          }
        },
        y: {
          title: {
            display: true,
            text: 'Yield (%)'
          },
          beginAtZero: true
        }
      }
    }
  })

  console.log('Yield curve chart initialized successfully')
}

const getAverageYield = () => {
  if (!calculationData.value?.calculations || calculationData.value.calculations.length === 0) {
    return 0
  }
  const yields = calculationData.value.calculations.map((calc: any) => calc.annual_yield || 0)
  return (yields.reduce((a: number, b: number) => a + b, 0) / yields.length).toFixed(2)
}

const proceedToReports = () => {
  router.push('/reports')
}

const updateYieldCurve = () => {
  // Re-fetch yield curve data with new filters
  fetchYieldCurveData()
}

const initializeComparisonChart = () => {
  const canvas = comparisonChart.value
  if (!canvas) return

  if (comparisonChartInstance) {
    comparisonChartInstance.destroy()
  }

  const ctx = canvas.getContext('2d')
  if (!ctx) return

  comparisonChartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
      datasets: [
        {
          label: 'Treasury Bills',
          data: [3.5, 3.6, 3.7, 3.8, 3.9, 4.0, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6],
          borderColor: '#0B2A44',
          backgroundColor: 'rgba(11, 42, 68, 0.1)',
          tension: 0.4,
          fill: false
        },
        {
          label: 'Bonds',
          data: [4.0, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9, 5.0, 5.1],
          borderColor: '#1E88E5',
          backgroundColor: 'rgba(30, 136, 229, 0.1)',
          tension: 0.4,
          fill: false
        },
        {
          label: 'Money Market',
          data: [2.5, 2.6, 2.7, 2.8, 2.9, 3.0, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6],
          borderColor: '#4CAF50',
          backgroundColor: 'rgba(76, 175, 80, 0.1)',
          tension: 0.4,
          fill: false
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'top'
        },
        title: {
          display: true,
          text: 'Instrument Yield Comparison'
        }
      },
      scales: {
        y: {
          beginAtZero: false,
          title: {
            display: true,
            text: 'Yield Rate (%)'
          }
        }
      }
    }
  })
}
</script>

<style scoped>
.visualizations-view {
  width: 100%;
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

.chart-container {
  height: 400px;
  position: relative;
  background: white;
  border-radius: 8px;
  padding: 16px;
  border: 1px solid rgba(11, 42, 68, 0.08);
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

/* Charts Grid Styles */
.charts-grid {
  margin-bottom: 32px;
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

.yield-curve-card {
  border: 2px solid rgba(255, 193, 7, 0.3);
}

.yield-curve-card::before {
  background: linear-gradient(90deg, #FFC107, #FF9800);
}

.yield-curve-container {
  height: 500px;
}

.chart-buttons {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}

.chart-btn {
  min-width: 120px;
}
</style>