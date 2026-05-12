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
        <v-btn color="#0B2A44" @click="loadData">
          <v-icon left>mdi-database</v-icon> Load Data
        </v-btn>
        <v-btn color="#0B2A44" variant="outlined" @click="clearData" :disabled="!hasData">
          <v-icon left>mdi-delete</v-icon> Clear Data
        </v-btn>
      </div>

      <!-- Show only when data loaded -->
      <template v-if="hasData">

        <!-- KPI Cards -->
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
              <canvas ref="yieldCanvas"></canvas>
            </div>
          </v-card-text>
        </v-card>

        <!-- Instrument Comparison Chart -->
        <v-card class="chart-card">
          <v-card-title class="card-title">
            <v-icon class="title-icon">mdi-chart-bar</v-icon> Instrument Comparison
          </v-card-title>
          <v-card-text>
            <div class="chart-container">
              <canvas ref="compareCanvas"></canvas>
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
          <p>Click "Load Data" to load calculation results</p>
          <v-btn color="#0B2A44" @click="loadData">Load Data</v-btn>
        </v-card-text>
      </v-card>

    </div>
  </fixed-layout>
</template>

<script setup>
import { ref, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import FixedLayout from '../components/FixedLayout.vue'
import { Chart, registerables } from 'chart.js'

Chart.register(...registerables)

const router = useRouter()

// State
const hasData = ref(false)
const calcData = ref(null)
const yieldData = ref(null)

// Canvas refs
const yieldCanvas = ref(null)
const compareCanvas = ref(null)

// Chart instances
let yieldChart = null
let compareChart = null

// KPI Stats (will update when data loads)
const kpiStats = ref([
  { title: 'Records', value: 0, icon: 'mdi-database', color: 'rgba(11,42,68,0.1)', iconColor: '#0B2A44' },
  { title: 'Instrument Type', value: 'N/A', icon: 'mdi-chart-bubble', color: 'rgba(30,136,229,0.1)', iconColor: '#1E88E5' },
  { title: 'Average Yield', value: '0%', icon: 'mdi-trending-up', color: 'rgba(76,175,80,0.1)', iconColor: '#4CAF50' },
  { title: 'Data Source', value: 'FRED API', icon: 'mdi-api', color: 'rgba(255,193,7,0.1)', iconColor: '#FFC107' }
])

// Load data from calculations page
async function loadData() {
  try {
    const stored = localStorage.getItem('calculations')
    if (!stored) {
      alert('No calculation data found. Run calculations first on the Calculations page.')
      return
    }
    
    calcData.value = JSON.parse(stored)
    hasData.value = true
    
    // Update KPI cards
    const calculations = calcData.value.calculations || []
    kpiStats.value[0].value = calculations.length
    kpiStats.value[1].value = calcData.value.instrumentType || 'Money Market'
    kpiStats.value[2].value = getAvgYield(calculations) + '%'
    
    // Render charts
    await loadYieldCurve()
    renderCompareChart(calculations)
    
    console.log(`Loaded ${calculations.length} records`)
  } catch (err) {
    console.error(err)
    alert('Error loading data')
  }
}

// Get average yield
function getAvgYield(calculations) {
  if (!calculations.length) return 0
  const yields = calculations.map(c => parseFloat(c.annual_yield || c.yield_to_maturity || c.bond_equivalent_yield || 0))
  const avg = yields.reduce((a, b) => a + b, 0) / yields.length
  return avg.toFixed(2)
}

// Clear all data
function clearData() {
  if (confirm('Clear all data?')) {
    hasData.value = false
    calcData.value = null
    if (yieldChart) { yieldChart.destroy(); yieldChart = null }
    if (compareChart) { compareChart.destroy(); compareChart = null }
    alert('Data cleared')
  }
}

// Load yield curve from backend
async function loadYieldCurve() {
  try {
    const res = await fetch('http://localhost:5000/api/fred-yield-curve')
    const data = await res.json()
    
    if (data.success && data.data) {
      yieldData.value = data.data
    } else {
      // Fallback data if API fails
      yieldData.value = {
        labels: ['3M', '6M', '1Y', '2Y', '5Y', '10Y', '30Y'],
        current: [4.2, 4.4, 4.6, 4.8, 4.5, 4.3, 4.1]
      }
    }
    await nextTick()
    renderYieldChart()
  } catch (err) {
    console.error(err)
    yieldData.value = {
      labels: ['3M', '6M', '1Y', '2Y', '5Y', '10Y', '30Y'],
      current: [4.2, 4.4, 4.6, 4.8, 4.5, 4.3, 4.1]
    }
    renderYieldChart()
  }
}

// Render yield curve chart
function renderYieldChart() {
  if (!yieldCanvas.value || !yieldData.value) return
  if (yieldChart) yieldChart.destroy()
  
  const ctx = yieldCanvas.value.getContext('2d')
  yieldChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: yieldData.value.labels,
      datasets: [{
        label: 'Yield Curve',
        data: yieldData.value.current,
        borderColor: '#0B2A44',
        backgroundColor: 'rgba(11, 42, 68, 0.1)',
        borderWidth: 2,
        fill: true,
        tension: 0.4
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
        y: { title: { display: true, text: 'Yield (%)' }, beginAtZero: true },
        x: { title: { display: true, text: 'Maturity' } }
      }
    }
  })
}

// Render comparison chart (bar chart)
function renderCompareChart(calculations) {
  if (!compareCanvas.value) return
  if (compareChart) compareChart.destroy()
  
  // Use instrument names and yields from calculation data
  const instruments = calculations.map(c => c.instrument_type || c.instrument_name || 'Unknown')
  const yields = calculations.map(c => parseFloat(c.annual_yield || c.yield_to_maturity || c.bond_equivalent_yield || 0))
  
  const ctx = compareCanvas.value.getContext('2d')
  compareChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: instruments,
      datasets: [{
        label: 'Yield (%)',
        data: yields,
        backgroundColor: '#0B2A44',
        borderRadius: 4
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
.title-icon { margin-right: 8px; }

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