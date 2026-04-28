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

      <!-- Selected Chart Display -->
      <v-card class="chart-card" elevation="2">
        <v-card-title class="card-title">
          <v-icon class="title-icon">{{ getSelectedChartIcon() }}</v-icon>
          {{ getSelectedChartTitle() }}
        </v-card-title>
        <v-card-text>
          <div class="chart-container">
            <!-- Bar Chart -->
            <canvas 
              ref="barChart"
              v-if="selectedChart === 'bar'"
              id="barChart"
              width="400"
              height="200"
            ></canvas>

            <!-- Line Chart -->
            <canvas 
              ref="lineChart"
              v-if="selectedChart === 'line'"
              id="lineChart"
              width="400"
              height="200"
            ></canvas>

            <!-- Pie Chart -->
            <canvas 
              ref="pieChart"
              v-if="selectedChart === 'pie'"
              id="pieChart"
              width="400"
              height="200"
            ></canvas>

            <!-- Area Chart -->
            <canvas 
              ref="areaChart"
              v-if="selectedChart === 'area'"
              id="areaChart"
              width="400"
              height="200"
            ></canvas>

            <!-- Yield Curve Chart -->
            <canvas 
              ref="yieldCurveChart"
              v-if="selectedChart === 'yield-curve'"
              id="yieldCurveChart"
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
  BarElement,
  LineElement,
  PointElement,
  BarController,
  LineController,
  PieController,
  Title,
  Tooltip,
  Legend,
  ArcElement,
  Filler
} from 'chart.js'

// Register Chart.js components
Chart.register(
  BarController,
  LineController,
  PieController,
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler
)

const router = useRouter()

const calculationData = ref<any>(null)
const selectedChart = ref('bar')
const yieldCurveData = ref<any>(null)

// Chart refs for all charts
const barChart = ref<HTMLCanvasElement | null>(null)
const lineChart = ref<HTMLCanvasElement | null>(null)
const pieChart = ref<HTMLCanvasElement | null>(null)
const areaChart = ref<HTMLCanvasElement | null>(null)
const yieldCurveChart = ref<HTMLCanvasElement | null>(null)

// Chart instances
const barChartInstance = ref<any>(null)
const lineChartInstance = ref<any>(null)
const pieChartInstance = ref<any>(null)
const areaChartInstance = ref<any>(null)
const yieldCurveChartInstance = ref<any>(null)

// Chart initialization state
const isInitializing = ref<boolean>(false)

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
  { value: 'area', label: 'Area Chart', icon: 'mdi-chart-area' },
  { value: 'yield-curve', label: 'Yield Curve', icon: 'mdi-chart-line' }
]

onMounted(() => {
  const stored = localStorage.getItem('calculations')
  if (stored) {
    calculationData.value = JSON.parse(stored)
    console.log('Loaded calculation data for visualizations:', calculationData.value)
  } else {
    console.log('No calculation data found, loading sample data for visualizations')
    loadSampleCalculationData()
  }
  
  // Fetch yield curve data
  fetchYieldCurveData()
  
  // Wait for data to load before initializing charts
  nextTick(() => {
    setTimeout(() => {
      initializeSelectedChart()
    }, 100)
  })
})

// Watch for calculation data changes - disabled to prevent conflicts
// watch(calculationData, () => {
//   nextTick(() => {
//     // Only initialize if we have data and no charts are already initialized
//     if (calculationData.value?.calculations && !barChartInstance.value && !lineChartInstance.value) {
//       setTimeout(() => {
//         initializeSelectedChart()
//       }, 100)
//     }
//   })
// }, { deep: true })

// Watch for chart type changes with debouncing
watch(selectedChart, () => {
  nextTick(() => {
    setTimeout(() => {
      initializeSelectedChart()
    }, 50)
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
      console.log('Yield curve data not available, using fallback')
      // Fallback yield curve data
      yieldCurveData.value = {
        labels: ['3M', '6M', '1Y', '2Y', '5Y', '10Y', '30Y'],
        current: [0.72, 0.82, 0.92, 1.02, 1.12, 4.06, 3.86],
        historical: []
      }
    }
  } catch (error) {
    console.error('Error fetching yield curve data:', error)
    // Fallback data
    yieldCurveData.value = {
      labels: ['3M', '6M', '1Y', '2Y', '5Y', '10Y', '30Y'],
      current: [0.72, 0.82, 0.92, 1.02, 1.12, 4.06, 3.86],
      historical: []
    }
  }
}

const initializeAllCharts = () => {
  if (!calculationData.value?.calculations) {
    console.log('No calculation data available for charts')
    return
  }

  const calculations = calculationData.value.calculations
  console.log(`Initializing all charts with ${calculations.length} calculations`)

  // Initialize individual charts
  initializeBarChart(calculations)
  initializeLineChart(calculations)
  initializePieChart(calculations)
  initializeAreaChart(calculations)
  
  console.log('All charts initialized successfully')
}

const initializeSelectedChart = () => {
  if (!calculationData.value?.calculations) {
    console.log('No calculation data available for charts')
    return
  }

  const calculations = calculationData.value.calculations
  const chartType = selectedChart.value
  console.log(`Initializing selected chart: ${chartType}`)

  // Prevent multiple initializations
  if (isInitializing.value) {
    console.log('Chart initialization already in progress, skipping...')
    return
  }

  isInitializing.value = true

  try {
    // Destroy all existing charts first
    if (barChartInstance.value) {
      barChartInstance.value.destroy()
      barChartInstance.value = null
    }
    if (lineChartInstance.value) {
      lineChartInstance.value.destroy()
      lineChartInstance.value = null
    }
    if (pieChartInstance.value) {
      pieChartInstance.value.destroy()
      pieChartInstance.value = null
    }
    if (areaChartInstance.value) {
      areaChartInstance.value.destroy()
      areaChartInstance.value = null
    }

    // Initialize only the selected chart
    switch (chartType) {
      case 'bar':
        initializeBarChart(calculations)
        break
      case 'line':
        initializeLineChart(calculations)
        break
      case 'pie':
        initializePieChart(calculations)
        break
      case 'area':
        initializeAreaChart(calculations)
        break
      case 'yield-curve':
        initializeYieldCurveChart()
        break
    }
    
    console.log(`Selected chart ${chartType} initialized successfully`)
  } catch (error) {
    console.error(`Error initializing chart ${chartType}:`, error)
  } finally {
    isInitializing.value = false
  }
}

const initializeBarChart = (calculations: any[]) => {
  if (!barChart.value || !calculations || calculations.length === 0) return
  
  // Additional canvas context validation
  const canvas = barChart.value
  const ctx = canvas.getContext('2d')
  if (!ctx) {
    console.error('Failed to get 2D context for bar chart canvas')
    return
  }

  if (barChartInstance.value) {
    barChartInstance.value.destroy()
    barChartInstance.value = null
  }

  try {
    const config = getBarChartConfig(calculations)
    barChartInstance.value = new Chart(canvas, config as any)
  } catch (error) {
    console.error('Error creating bar chart:', error)
  }
}

const initializeLineChart = (calculations: any[]) => {
  if (!lineChart.value || !calculations || calculations.length === 0) return
  
  const canvas = lineChart.value
  const ctx = canvas.getContext('2d')
  if (!ctx) {
    console.error('Failed to get 2D context for line chart canvas')
    return
  }

  if (lineChartInstance.value) {
    lineChartInstance.value.destroy()
    lineChartInstance.value = null
  }

  try {
    const config = getLineChartConfig(calculations)
    lineChartInstance.value = new Chart(canvas, config as any)
  } catch (error) {
    console.error('Error creating line chart:', error)
  }
}

const initializePieChart = (calculations: any[]) => {
  if (!pieChart.value || !calculations || calculations.length === 0) return
  
  const canvas = pieChart.value
  const ctx = canvas.getContext('2d')
  if (!ctx) {
    console.error('Failed to get 2D context for pie chart canvas')
    return
  }

  if (pieChartInstance.value) {
    pieChartInstance.value.destroy()
    pieChartInstance.value = null
  }

  try {
    const config = getPieChartConfig(calculations)
    pieChartInstance.value = new Chart(canvas, config as any)
  } catch (error) {
    console.error('Error creating pie chart:', error)
  }
}

const initializeAreaChart = (calculations: any[]) => {
  if (!areaChart.value || !calculations || calculations.length === 0) return
  
  const canvas = areaChart.value
  const ctx = canvas.getContext('2d')
  if (!ctx) {
    console.error('Failed to get 2D context for area chart canvas')
    return
  }

  if (areaChartInstance.value) {
    areaChartInstance.value.destroy()
    areaChartInstance.value = null
  }

  try {
    const config = getAreaChartConfig(calculations)
    areaChartInstance.value = new Chart(canvas, config as any)
  } catch (error) {
    console.error('Error creating area chart:', error)
  }
}

const initializeYieldCurveChart = () => {
  if (!yieldCurveChart.value || !yieldCurveData.value || !yieldCurveData.value.current) return
  
  const canvas = yieldCurveChart.value
  const ctx = canvas.getContext('2d')
  if (!ctx) {
    console.error('Failed to get 2D context for yield curve canvas')
    return
  }

  if (yieldCurveChartInstance.value) {
    yieldCurveChartInstance.value.destroy()
    yieldCurveChartInstance.value = null
  }

  try {
    const config = getYieldCurveChartConfig(yieldCurveData.value)
    yieldCurveChartInstance.value = new Chart(canvas, config as any)
    console.log('Yield curve chart initialized')
  } catch (error) {
    console.error('Error creating yield curve chart:', error)
  }
}

const getBarChartConfig = (calculations: any[]) => {
  const labels = calculations.map(calc => calc.instrument_type || 'Unknown')
  const faceValues = calculations.map(calc => calc.face_value || 0)
  const purchasePrices = calculations.map(calc => calc.purchase_price || 0)

  return {
    type: 'bar',
    data: {
      labels,
      datasets: [
        {
          label: 'Face Value',
          data: faceValues,
          backgroundColor: 'rgba(11, 42, 68, 0.8)',
          borderColor: 'rgba(11, 42, 68, 1)',
          borderWidth: 1
        },
        {
          label: 'Purchase Price',
          data: purchasePrices,
          backgroundColor: 'rgba(30, 136, 229, 0.8)',
          borderColor: 'rgba(30, 136, 229, 1)',
          borderWidth: 1
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        title: {
          display: true,
          text: 'Face Value vs Purchase Price'
        },
        legend: {
          display: true,
          position: 'top'
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: {
            callback: function(value: any) {
              return '$' + value.toLocaleString()
            }
          }
        }
      }
    }
  }
}

const getLineChartConfig = (calculations: any[]) => {
  const labels = calculations.map(calc => calc.instrument_type || 'Unknown')
  const yields = calculations.map(calc => (calc.annual_yield || 0) * 100)
  const effectiveRates = calculations.map(calc => (calc.effective_rate || 0) * 100)

  return {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: 'Annual Yield (%)',
          data: yields,
          borderColor: 'rgba(76, 175, 80, 1)',
          backgroundColor: 'rgba(76, 175, 80, 0.1)',
          tension: 0.1
        },
        {
          label: 'Effective Rate (%)',
          data: effectiveRates,
          borderColor: 'rgba(255, 193, 7, 1)',
          backgroundColor: 'rgba(255, 193, 7, 0.1)',
          tension: 0.1
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        title: {
          display: true,
          text: 'Yield Trend Analysis'
        },
        legend: {
          display: true,
          position: 'top'
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: {
            callback: function(value: any) {
              return value.toFixed(2) + '%'
            }
          }
        }
      }
    }
  }
}

const getPieChartConfig = (calculations: any[]) => {
  const labels = calculations.map(calc => calc.instrument_type || 'Unknown')
  const principals = calculations.map(calc => calc.principal || 0)

  return {
    type: 'pie',
    data: {
      labels,
      datasets: [
        {
          data: principals,
          backgroundColor: [
            'rgba(11, 42, 68, 0.8)',
            'rgba(30, 136, 229, 0.8)',
            'rgba(76, 175, 80, 0.8)',
            'rgba(255, 193, 7, 0.8)'
          ],
          borderColor: [
            'rgba(11, 42, 68, 1)',
            'rgba(30, 136, 229, 1)',
            'rgba(76, 175, 80, 1)',
            'rgba(255, 193, 7, 1)'
          ],
          borderWidth: 1
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        title: {
          display: true,
          text: 'Principal Distribution'
        },
        legend: {
          display: true,
          position: 'right'
        },
        tooltip: {
          callbacks: {
            label: function(context: any) {
              const label = context.label || ''
              const value = context.parsed || 0
              const total = context.dataset.data.reduce((a: number, b: number) => a + b, 0)
              const percentage = ((value / total) * 100).toFixed(1)
              return `${label}: $${value.toLocaleString()} (${percentage}%)`
            }
          }
        }
      }
    }
  }
}

const getAreaChartConfig = (calculations: any[]) => {
  const labels = calculations.map(calc => calc.instrument_type || 'Unknown')
  const maturityValues = calculations.map(calc => calc.maturity_value || 0)

  return {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: 'Maturity Value',
          data: maturityValues,
          borderColor: 'rgba(11, 42, 68, 1)',
          backgroundColor: 'rgba(11, 42, 68, 0.2)',
          fill: true,
          tension: 0.1
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        title: {
          display: true,
          text: 'Maturity Value Breakdown'
        },
        legend: {
          display: true,
          position: 'top'
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: {
            callback: function(value: any) {
              return '$' + value.toLocaleString()
            }
          }
        }
      }
    }
  }
}

const getYieldCurveChartConfig = (yieldData: any) => {
  const labels = yieldData.labels || ['3M', '6M', '1Y', '2Y', '5Y', '10Y', '30Y']
  const currentRates = yieldData.current || [0.72, 0.82, 0.92, 1.02, 1.12, 4.06, 3.86]
  const historicalRates = yieldData.historical || []

  const datasets = [
    {
      label: 'Current Yield Curve',
      data: currentRates,
      borderColor: 'rgba(11, 42, 68, 1)',
      backgroundColor: 'rgba(11, 42, 68, 0.1)',
      borderWidth: 3,
      tension: 0.1,
      fill: false
    }
  ]

  if (historicalRates.length > 0) {
    datasets.push({
      label: 'Historical Yield Curve',
      data: historicalRates,
      borderColor: 'rgba(30, 136, 229, 1)',
      backgroundColor: 'rgba(30, 136, 229, 0.1)',
      borderWidth: 2,
      tension: 0.1,
      fill: false,
      borderDash: [5, 5] as any
    })
  }

  return {
    type: 'line',
    data: {
      labels,
      datasets
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        title: {
          display: true,
          text: 'FRED Yield Curve Analysis (Real-time Data)',
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
          callbacks: {
            label: function(context: any) {
              const label = context.dataset.label || ''
              const value = context.parsed.y || 0
              return `${label}: ${value.toFixed(2)}%`
            }
          }
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
          beginAtZero: true,
          title: {
            display: true,
            text: 'Yield (%)'
          },
          ticks: {
            callback: function(value: any) {
              return value.toFixed(2) + '%'
            }
          }
        }
      },
      interaction: {
        intersect: false,
        mode: 'index'
      }
    }
  }
}

const getAverageYield = () => {
  const list = calculationData.value?.calculations || []
  if (!list.length) return '0.00'

  const yields = list.map((c: any) => c.annual_yield || 0)

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

const getSelectedChartIcon = () => {
  const chart = chartTypes.find(c => c.value === selectedChart.value)
  return chart?.icon || 'mdi-chart-line'
}

const getSelectedChartTitle = () => {
  const titles = {
    bar: 'Face Value vs Purchase Price',
    line: 'Yield Trend Analysis',
    pie: 'Principal Distribution',
    area: 'Maturity Value Breakdown',
    'yield-curve': 'FRED Yield Curve Analysis'
  }
  return titles[selectedChart.value as keyof typeof titles] || 'Chart'
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