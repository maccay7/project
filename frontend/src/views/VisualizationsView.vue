<template>
  <fixed-layout>
    <div class="visualizations-view">

      <!-- Header -->
      <div class="page-header">
        <h1>Data Visualizations</h1>
        <p>Visualize your financial calculations with interactive charts</p>
      </div>

      <!-- Action Buttons -->
      <div class="action-buttons">
        <v-btn color="#0B2A44" @click="loadFromCalculations">
          <v-icon left>mdi-database</v-icon> Load Data from Calculations
        </v-btn>
        <v-btn color="#0B2A44" variant="outlined" @click="clearData" :disabled="!hasData">
          <v-icon left>mdi-delete</v-icon> Clear Data
        </v-btn>
      </div>

      <!-- KPI Cards - Only show when data loaded -->
      <template v-if="hasData">
        <v-card class="stats-card">
          <v-card-title class="card-title">
            <v-icon class="title-icon">mdi-chart-line</v-icon> Calculation Overview
          </v-card-title>
          <v-card-text>
            <v-row>
              <v-col cols="12" sm="6" md="3" v-for="stat in kpiStats" :key="stat.title">
                <v-card class="kpi-card">
                  <v-card-text>
                    <div class="kpi-content">
                      <div class="kpi-icon" :style="{ backgroundColor: stat.color }">
                        <v-icon :color="stat.iconColor" size="28">{{ stat.icon }}</v-icon>
                      </div>
                      <div class="kpi-info">
                        <div class="kpi-value">{{ stat.value }}</div>
                        <div class="kpi-title">{{ stat.title }}</div>
                      </div>
                    </div>
                  </v-card-text>
                </v-card>
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>

        <!-- Yield Curve Chart -->
        <v-card class="chart-card">
          <v-card-title class="card-title">
            <v-icon class="title-icon">mdi-chart-line</v-icon> Yield Curve (FRED API)
          </v-card-title>
          <v-card-text>
            <div class="chart-container">
              <canvas ref="yieldCurveCanvas"></canvas>
            </div>
          </v-card-text>
        </v-card>

        <!-- Comparison Chart -->
        <v-card class="chart-card">
          <v-card-title class="card-title">
            <v-icon class="title-icon">mdi-chart-multiline</v-icon> Instrument Comparison
          </v-card-title>
          <v-card-text>
            <div class="chart-container">
              <canvas ref="comparisonCanvas"></canvas>
            </div>
          </v-card-text>
        </v-card>

        <!-- Proceed Button -->
        <v-card class="action-card">
          <v-card-text class="text-center">
            <v-btn color="#0B2A44" size="large" @click="goToReports">
              Proceed to Reports <v-icon right>mdi-arrow-right</v-icon>
            </v-btn>
          </v-card-text>
        </v-card>
      </template>

      <!-- No Data Message -->
      <v-card v-if="!hasData" class="stats-card">
        <v-card-text class="text-center pa-8">
          <v-icon size="64" color="#999">mdi-chart-line-off</v-icon>
          <h3 class="mt-4">No Data Loaded</h3>
          <p class="text-grey">Click "Load Data from Calculations" to load your calculation results</p>
          <v-btn color="#0B2A44" @click="loadFromCalculations">Load Data from Calculations</v-btn>
        </v-card-text>
      </v-card>

    </div>
  </fixed-layout>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import FixedLayout from '../components/FixedLayout.vue'
import { Chart, registerables } from 'chart.js'

Chart.register(...registerables)

const router = useRouter()

// State
const hasData = ref(false)
const calculationData = ref(null)
const yieldCurveData = ref(null)

// Canvas refs
const yieldCurveCanvas = ref(null)
const comparisonCanvas = ref(null)

// Chart instances
let yieldChart = null
let comparisonChart = null

// KPI Stats
const kpiStats = ref([
  { title: 'Records', value: 0, icon: 'mdi-database', color: 'rgba(11,42,68,0.1)', iconColor: '#0B2A44' },
  { title: 'Instrument Type', value: 'N/A', icon: 'mdi-chart-bubble', color: 'rgba(30,136,229,0.1)', iconColor: '#1E88E5' },
  { title: 'Average Yield', value: '0%', icon: 'mdi-trending-up', color: 'rgba(76,175,80,0.1)', iconColor: '#4CAF50' },
  { title: 'Data Source', value: 'FRED API', icon: 'mdi-api', color: 'rgba(255,193,7,0.1)', iconColor: '#FFC107' }
])

// Load data from calculations page
function loadFromCalculations() {
  try {
    const stored = localStorage.getItem('calculations')
    if (!stored) {
      alert('No calculation data found. Please run calculations first on the Calculations page.')
      return
    }
    
    calculationData.value = JSON.parse(stored)
    hasData.value = true
    
    // Update KPIs
    const calcs = calculationData.value.calculations || []
    kpiStats.value[0].value = calcs.length
    kpiStats.value[1].value = calculationData.value.instrumentType || 'Money Market'
    
    const avgYield = getAverageYield(calcs)
    kpiStats.value[2].value = avgYield + '%'
    
    // Load and render charts
    loadYieldCurve()
    renderComparisonChart(calcs)
    
    alert(`Loaded ${calcs.length} calculation records`)
  } catch (err) {
    console.error('Error loading data:', err)
    alert('Error loading calculation data')
  }
}

// Clear all data
function clearData() {
  if (confirm('Clear all visualization data?')) {
    hasData.value = false
    calculationData.value = null
    if (yieldChart) { yieldChart.destroy(); yieldChart = null }
    if (comparisonChart) { comparisonChart.destroy(); comparisonChart = null }
    alert('Data cleared')
  }
}

// Get average yield from calculations
function getAverageYield(calculations) {
  if (!calculations.length) return 0
  const yields = calculations.map(c => parseFloat(c.annual_yield || c.yieldRate || 0))
  const avg = yields.reduce((a, b) => a + b, 0) / yields.length
  return avg.toFixed(2)
}

// Load yield curve from FRED API
async function loadYieldCurve() {
  try {
    const response = await fetch('http://localhost:5000/api/fred-yield-curve')
    const data = await response.json()
    
    if (data.success && data.data) {
      yieldCurveData.value = data.data
      await nextTick()
      renderYieldCurveChart()
    } else {
      // Use fallback data
      yieldCurveData.value = {
        labels: ['3M', '6M', '1Y', '2Y', '5Y', '10Y', '30Y'],
        current: [4.2, 4.4, 4.6, 4.8, 4.5, 4.3, 4.1]
      }
      renderYieldCurveChart()
    }
  } catch (err) {
    console.error('Error fetching yield curve:', err)
    yieldCurveData.value = {
      labels: ['3M', '6M', '1Y', '2Y', '5Y', '10Y', '30Y'],
      current: [4.2, 4.4, 4.6, 4.8, 4.5, 4.3, 4.1]
    }
    renderYieldCurveChart()
  }
}

// Render yield curve chart
function renderYieldCurveChart() {
  if (!yieldCurveCanvas.value || !yieldCurveData.value) return
  
  if (yieldChart) yieldChart.destroy()
  
  const ctx = yieldCurveCanvas.value.getContext('2d')
  yieldChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: yieldCurveData.value.labels,
      datasets: [{
        label: 'Yield Curve',
        data: yieldCurveData.value.current,
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
        legend: { position: 'top' },
        tooltip: { mode: 'index', intersect: false }
      },
      scales: {
        y: { title: { display: true, text: 'Yield (%)' }, beginAtZero: true },
        x: { title: { display: true, text: 'Maturity' } }
      }
    }
  })
}

// Render comparison chart from calculation data
function renderComparisonChart(calculations) {
  if (!comparisonCanvas.value) return
  if (comparisonChart) comparisonChart.destroy()
  
  const instruments = calculations.map(c => c.instrument_type || c.instrument_name || 'Unknown')
  const yields = calculations.map(c => parseFloat(c.annual_yield || c.yieldRate || 0))
  
  const ctx = comparisonCanvas.value.getContext('2d')
  comparisonChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: instruments,
      datasets: [{
        label: 'Annual Yield (%)',
        data: yields,
        backgroundColor: 'rgba(11, 42, 68, 0.7)',
        borderColor: '#0B2A44',
        borderWidth: 1
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'top' },
        tooltip: { callbacks: { label: (ctx) => `${ctx.raw}%` } }
      },
      scales: {
        y: { title: { display: true, text: 'Yield (%)' }, beginAtZero: true }
      }
    }
  })
}

// Navigate to reports
function goToReports() {
  router.push('/reports')
}

onMounted(() => {
  console.log('Visualizations page ready. Click "Load Data from Calculations" to begin.')
})
</script>

<style scoped>
.visualizations-view { max-width: 1400px; margin: 0 auto; padding: 20px; }
.page-header { margin-bottom: 30px; }
.page-header h1 { color: #0B2A44; font-size: 32px; font-weight: 700; margin-bottom: 8px; }
.page-header p { color: #666; font-size: 16px; }

.action-buttons { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 30px; }

.stats-card { border-radius: 12px; margin-bottom: 30px; background: white; border: 1px solid rgba(11,42,68,0.08); position: relative; }
.stats-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; background: linear-gradient(90deg, #0B2A44, #1E88E5); border-radius: 12px 12px 0 0; }

.chart-card { border-radius: 12px; margin-bottom: 30px; background: white; border: 1px solid rgba(11,42,68,0.08); position: relative; }
.chart-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; background: linear-gradient(90deg, #0B2A44, #1E88E5); }

.card-title { display: flex; align-items: center; color: #0B2A44; font-weight: 600; font-size: 18px; padding: 16px 20px 0 20px; }
.title-icon { margin-right: 8px; color: #0B2A44; }

.chart-container { height: 400px; position: relative; padding: 16px; }

.kpi-card { height: 120px; border-radius: 12px; transition: 0.2s; background: white; border: 1px solid rgba(11,42,68,0.08); position: relative; }
.kpi-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; background: linear-gradient(90deg, #0B2A44, #1E88E5, #4CAF50); }
.kpi-card:hover { transform: translateY(-2px); }
.kpi-content { display: flex; align-items: center; height: 100%; padding: 8px; }
.kpi-icon { width: 56px; height: 56px; border-radius: 12px; display: flex; align-items: center; justify-content: center; margin-right: 12px; flex-shrink: 0; }
.kpi-value { font-size: 24px; font-weight: 700; color: #0B2A44; }
.kpi-title { font-size: 12px; color: #666; }

.action-card { border-radius: 12px; background: white; border: 1px solid rgba(11,42,68,0.08); text-align: center; padding: 16px; }

@media (max-width: 600px) {
  .visualizations-view { padding: 0 16px; }
  .action-buttons { flex-direction: column; }
  .chart-container { height: 300px; }
}
</style>