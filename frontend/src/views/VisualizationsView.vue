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
            <v-row class="mb-3">
              <v-col cols="12" md="3">
                <v-select
                  v-model="selectedInstrument"
                  :items="instrumentOptions"
                  label="Instrument"
                  density="compact"
                  @update:model-value="loadYieldCurve"
                />
              </v-col>
              <v-col cols="12" md="3">
                <v-select
                  v-model="fredFilters.country"
                  :items="countryItems"
                  item-title="name"
                  item-value="code"
                  label="Country / region"
                  density="compact"
                  @update:model-value="() => { onCountryChange(); loadYieldCurve() }"
                />
              </v-col>
              <v-col cols="12" md="3">
                <v-select
                  v-model="fredFilters.currency"
                  :items="currencyItems"
                  item-title="name"
                  item-value="code"
                  label="Currency"
                  density="compact"
                  @update:model-value="loadYieldCurve"
                />
              </v-col>
              <v-col cols="12" md="3">
                <v-select
                  v-model="fredFilters.maturity"
                  :items="maturityItems"
                  item-title="name"
                  item-value="code"
                  label="Benchmark maturity"
                  density="compact"
                  @update:model-value="loadYieldCurve"
                />
              </v-col>
            </v-row>
            <p class="fred-note mb-2">
              Market data from FRED — {{ fredFilters.country }} ({{ fredFilters.currency }}). Non-US countries use government bond yields available on FRED.
            </p>
            <v-alert v-if="yieldLoading" type="info" density="compact" class="mb-3">Loading Yield Curve...</v-alert>
            <v-alert v-if="yieldError" type="error" density="compact" class="mb-3">{{ yieldError }}</v-alert>
            <!-- Analytics Display -->
            <v-row v-if="yieldAnalytics && !yieldLoading" class="mb-3">
              <v-col cols="12" sm="6" md="3">
                <v-card class="analytics-card">
                  <v-card-text class="text-center">
                    <div class="analytics-label">Latest Yield</div>
                    <div class="analytics-value">{{ yieldAnalytics.latest_yield }}%</div>
                  </v-card-text>
                </v-card>
              </v-col>
              <v-col cols="12" sm="6" md="3">
                <v-card class="analytics-card">
                  <v-card-text class="text-center">
                    <div class="analytics-label">Highest Yield</div>
                    <div class="analytics-value">{{ yieldAnalytics.highest_yield }}%</div>
                  </v-card-text>
                </v-card>
              </v-col>
              <v-col cols="12" sm="6" md="3">
                <v-card class="analytics-card">
                  <v-card-text class="text-center">
                    <div class="analytics-label">Lowest Yield</div>
                    <div class="analytics-value">{{ yieldAnalytics.lowest_yield }}%</div>
                  </v-card-text>
                </v-card>
              </v-col>
              <v-col cols="12" sm="6" md="3">
                <v-card class="analytics-card">
                  <v-card-text class="text-center">
                    <div class="analytics-label">Average Yield</div>
                    <div class="analytics-value">{{ yieldAnalytics.average_yield }}%</div>
                  </v-card-text>
                </v-card>
              </v-col>
            </v-row>
            <div class="chart-container">
              <canvas ref="yieldCanvas"></canvas>
            </div>
          </v-card-text>
        </v-card>

        <!-- Compare all instruments -->
        <v-card class="chart-card">
          <v-card-title class="card-title">
            <v-icon class="title-icon">mdi-chart-multiline</v-icon> Instrument Comparison (FRED)
          </v-card-title>
          <v-card-text>
            <p class="mb-3">Compare Treasury Bills, Bonds, and Money Market on the same chart.</p>
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
          <v-icon size="64" color="#999">mdi-chart-box-outline</v-icon>
          <h3 class="mt-4">No Data Loaded</h3>
          <p>Click "Load Data" to load calculation results</p>
          <v-btn color="#0B2A44" @click="loadData">Load Data</v-btn>
        </v-card-text>
      </v-card>

    </div>
  </fixed-layout>
</template>

<script setup>
import { ref, nextTick, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import FixedLayout from '../components/FixedLayout.vue'
import api from '@/services/api.js'
import sessionManager from '@/services/sessionManager.js'
import { markStepCompleted } from '@/utils/workflowProgress.js'
import { useFredMarket } from '@/composables/useFredMarket'
import { Chart, registerables } from 'chart.js'

Chart.register(...registerables)

const router = useRouter()
const route = useRoute()

// State
const hasData = ref(false)
const calcData = ref(null)
const yieldData = ref(null)
const yieldError = ref('')
const yieldLoading = ref(false)
const selectedInstrument = ref('all')
const instrumentOptions = [
  { title: 'All Instruments', value: 'all' },
  { title: 'Treasury Bills', value: 'treasury_bills' },
  { title: 'Bonds', value: 'bonds' },
  { title: 'Money Market', value: 'money_market' }
]

// Analytics state
const yieldAnalytics = ref(null)

const { fredFilters, countryItems, currencyItems, maturityItems, loadFilterOptions, onCountryChange } = useFredMarket('1Y')

const yieldCanvas = ref(null)
const compareCanvas = ref(null)
let yieldChart = null
let compareChart = null

// Yield curve cache for performance optimization
const yieldCurveCache = ref(new Map())
const lastYieldCurveRequest = ref({})

// KPI Stats
const kpiStats = ref([
  { title: 'Records', value: 0, icon: 'mdi-table-large', color: 'rgba(11,42,68,0.1)', iconColor: '#0B2A44' },
  { title: 'Instrument Type', value: 'N/A', icon: 'mdi-shape-outline', color: 'rgba(30,136,229,0.1)', iconColor: '#1E88E5' },
  { title: 'Average Yield', value: '0%', icon: 'mdi-percent-outline', color: 'rgba(76,175,80,0.1)', iconColor: '#4CAF50' },
  { title: 'Data Source', value: 'FRED API', icon: 'mdi-web', color: 'rgba(255,193,7,0.1)', iconColor: '#FFC107' }
])

// Load data from the latest calculation for the selected dataset
async function loadData() {
  try {
    const datasetId = route.query.dataset_id
    if (!datasetId) {
      alert('No dataset selected. Please navigate from Calculations or Upload page.')
      return
    }

    const res = await api.calculationsAPI.getLatest(datasetId)
    if (!res || !res.success) {
      alert('No calculation data found for this dataset. Run calculations first.')
      return
    }

    calcData.value = res.data.result_data || {}
    const calculations = calcData.value.calculations || []
    hasData.value = true

    kpiStats.value[0].value = calculations.length
    const inst = (res.data.instrument_type || 'money_market').toLowerCase().replace('-', '_')
    kpiStats.value[1].value = inst.replace('_', ' ')
    selectedInstrument.value = inst
    kpiStats.value[2].value = (calcData.value.fred?.benchmark_rate ?? getAvgYield(calculations)) + '%'
    if (calcData.value.fred?.maturity) fredFilters.value.maturity = calcData.value.fred.maturity

    await loadYieldCurve()
    await loadComparisonChart()
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

function chartDatasets(payload) {
  if (payload.datasets && payload.datasets.length) {
    return payload.datasets.map(d => {
      // Handle both data formats: array of objects with x/y or array of values
      let chartData
      if (d.data && d.data.length > 0 && typeof d.data[0] === 'object' && 'x' in d.data[0]) {
        chartData = d.data
      } else {
        const maturities = d.maturities || payload.labels || []
        chartData = d.data.map((val, idx) => ({ 
          x: maturities[idx] || idx, 
          y: val 
        }))
      }
      
      return {
        label: d.label,
        data: chartData,
        borderColor: d.borderColor || '#0B2044',
        backgroundColor: 'rgba(11, 42, 68, 0.08)',
        borderWidth: 2,
        fill: false,
        tension: 0.35
      }
    })
  }
  // Fallback: assume payload.labels are maturity strings and payload.current are rates
  const maturities = (payload.labels || []).map(l => parseFloat(l.replace(/[^0-9.]/g, '')) || 0)
  return [{
    label: 'Yield Curve',
    data: (payload.current || []).map((val, idx) => ({ x: maturities[idx] || idx, y: val })),
    borderColor: '#0B2044',
    backgroundColor: 'rgba(11, 42, 68, 0.1)',
    borderWidth: 2,
    fill: true,
    tension: 0.35
  }]
}

// ----- FIXED: loadYieldCurve with proper maturity mapping -----
async function loadYieldCurve() {
  yieldError.value = ''
  yieldLoading.value = true
  try {
    const cacheKey = `${selectedInstrument.value}_${fredFilters.value.country}_${fredFilters.value.currency}`
    if (yieldCurveCache.value.has(cacheKey)) {
      const cached = yieldCurveCache.value.get(cacheKey)
      if (Date.now() - cached.timestamp < 300000) {
        yieldData.value = cached.data
        yieldAnalytics.value = cached.analytics
        await nextTick()
        renderYieldChart()
        return
      }
    }
    const requestKey = `${cacheKey}_${Date.now()}`
    if (lastYieldCurveRequest.value[cacheKey] && Date.now() - lastYieldCurveRequest.value[cacheKey] < 1000) {
      return
    }
    lastYieldCurveRequest.value[cacheKey] = Date.now()

    const res = await api.fredAPI.getYieldCurve(
      selectedInstrument.value,
      fredFilters.value.country,
      fredFilters.value.currency
    )
    if (res?.success && res.data?.datasets?.length) {
      yieldData.value = res.data
      yieldAnalytics.value = res.data.analytics || null
      yieldCurveCache.value.set(cacheKey, {
        data: res.data,
        analytics: res.data.analytics || null,
        timestamp: Date.now()
      })
      await saveFredSettings()
    } else {
      yieldError.value = res?.data?.error || 'Unable to load Yield Curve. Please try again.'
      yieldData.value = null
      yieldAnalytics.value = null
    }
    await nextTick()
    renderYieldChart()
  } catch (err) {
    yieldError.value = 'Unable to load Yield Curve. Please try again.'
    yieldData.value = null
    yieldAnalytics.value = null
    console.error(err)
  } finally {
    yieldLoading.value = false
  }
}

// ----- FIXED: renderYieldChart with meaningful x‑axis -----
function renderYieldChart() {
  if (!yieldCanvas.value || !yieldData.value) return
  if (yieldChart) yieldChart.destroy()
  const ctx = yieldCanvas.value.getContext('2d')

  const maturities = yieldData.value.maturities || []
  const maxMaturity = maturities.length ? Math.max(...maturities) : 10
  const selectedMaturityStr = fredFilters.value.maturity || '1Y'
  
  // Parse maturity to determine label format and scale
  let effectiveMax = maxMaturity
  let xAxisTitle = 'Maturity'
  let stepSize = 1
  let tickCallback = (val) => Number.isInteger(val) ? val : ''
  let minX = 0

  // Determine unit and max based on selected maturity
  const match = selectedMaturityStr.match(/^(\d+)([YMW])$/)
  if (match) {
    const num = parseInt(match[1], 10)
    const unit = match[2]
    if (unit === 'Y') {
      xAxisTitle = 'Years'
      stepSize = num > 5 ? 5 : 1
      effectiveMax = Math.min(maxMaturity, num)
    } else if (unit === 'M') {
      xAxisTitle = 'Months'
      stepSize = 1
      effectiveMax = Math.min(maxMaturity, num)
      minX = 0
    } else if (unit === 'W') {
      xAxisTitle = 'Weeks'
      stepSize = 1
      effectiveMax = Math.min(maxMaturity, num)
      minX = 0
    }
  } else {
    // fallback to years
    xAxisTitle = 'Years'
    const num = parseFloat(selectedMaturityStr) || 10
    effectiveMax = Math.min(maxMaturity, num)
    stepSize = num > 5 ? 5 : 1
  }

  // Filter data points up to effectiveMax
  const filteredData = yieldData.value.datasets.map(ds => {
    const data = ds.data.filter(pt => pt.x <= effectiveMax)
    return { ...ds, data }
  })

  if (filteredData.every(ds => ds.data.length === 0)) {
    yieldError.value = 'No yield curve data available for selected maturity'
    return
  }

  // Determine tick values based on unit
  if (xAxisTitle === 'Months') {
    tickCallback = (val) => Number.isInteger(val) && val >= 0 && val <= effectiveMax ? val : ''
  } else if (xAxisTitle === 'Weeks') {
    tickCallback = (val) => Number.isInteger(val) && val >= 0 && val <= effectiveMax ? val : ''
  } else {
    tickCallback = (val) => Number.isInteger(val) && val >= 0 && val <= effectiveMax ? val : ''
  }

  yieldChart = new Chart(ctx, {
    type: 'line',
    data: { datasets: filteredData },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'top' },
        tooltip: {
          callbacks: {
            label: (ctx) => {
              const pt = ctx.raw
              return `${pt.x.toFixed(0)}${xAxisTitle === 'Months' ? 'M' : xAxisTitle === 'Weeks' ? 'W' : 'Y'}: ${pt.y.toFixed(2)}%`
            }
          }
        }
      },
      scales: {
        y: { title: { display: true, text: 'Yield (%)' } },
        x: {
          type: 'linear',
          title: { display: true, text: xAxisTitle },
          min: minX,
          max: effectiveMax,
          ticks: {
            callback: tickCallback,
            stepSize: stepSize
          }
        }
      }
    }
  })
}

// ---- loadComparisonChart ----
async function loadComparisonChart() {
  try {
    const res = await api.fredAPI.getYieldCurve('all', fredFilters.value.country, fredFilters.value.currency)
    if (!res?.success || !res.data?.maturities?.length) return
    await nextTick()
    if (compareChart) compareChart.destroy()
    const ctx = compareCanvas.value?.getContext('2d')
    if (!ctx) return
    
    const maturities = res.data.maturities || []
    const maxMaturity = maturities.length ? Math.max(...maturities) : 10
    const effectiveMax = maxMaturity

    compareChart = new Chart(ctx, {
      type: 'line',
      data: { datasets: chartDatasets(res.data) },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'top' },
          tooltip: {
            callbacks: {
              label: (ctx) => {
                const pt = ctx.raw
                return `${ctx.dataset.label} ${pt.x.toFixed(0)}Y: ${pt.y.toFixed(2)}%`
              }
            }
          }
        },
        scales: {
          y: { title: { display: true, text: 'Yield (%)' } },
          x: {
            type: 'linear',
            title: { display: true, text: 'Maturity (Years)' },
            min: 0,
            max: effectiveMax,
            ticks: {
              callback: (val) => Number.isInteger(val) ? val : '',
              stepSize: 1
            }
          }
        }
      }
    })
  } catch (err) {
    console.error('Comparison chart error:', err)
  }
}

// ---- Navigation ----
async function goToReports() {
  const datasetId = route.query.dataset_id
  if (!datasetId) {
    alert('Dataset reference missing. Please run calculations first.')
    return
  }
  try {
    const session = sessionManager.getActiveSession()
    const sid = session?.id || sessionManager.getActiveSessionId()
    if (sid) await markStepCompleted(String(sid), 'visualizations')
  } catch (e) { console.warn(e) }
  router.push({ name: 'reports', query: { dataset_id: datasetId } })
}

// ---- Save FRED settings (optional) ----
async function saveFredSettings() {
  // could be implemented to store in localStorage or backend
}

// ---- Load FRED settings ----
async function loadFredSettings() {
  // could be implemented
}

// ---- Lifecycle ----
onMounted(async () => {
  await loadFilterOptions()
  await loadFredSettings()
  if (route.query.dataset_id) loadData()
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
.title-icon { margin-right: 8px; }
.fred-note { font-size: 13px; color: #666; }
.chart-container { height: 400px; position: relative; padding: 16px; }
.kpi-card { height: 120px; border-radius: 12px; transition: 0.2s; background: white; border: 1px solid rgba(11,42,68,0.08); position: relative; }
.kpi-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; background: linear-gradient(90deg, #0B2A44, #1E88E5, #4CAF50); }
.kpi-card:hover { transform: translateY(-2px); }
.kpi-content { display: flex; align-items: center; height: 100%; padding: 8px; }
.kpi-icon { width: 56px; height: 56px; border-radius: 12px; display: flex; align-items: center; justify-content: center; margin-right: 12px; flex-shrink: 0; }
.kpi-value { font-size: 24px; font-weight: 700; color: #0B2A44; }
.kpi-title { font-size: 12px; color: #666; }
.action-card { border-radius: 12px; background: white; border: 1px solid rgba(11,42,68,0.08); text-align: center; padding: 16px; }
.analytics-card { border-radius: 8px; background: #f8f9ff; border: 1px solid #e0e0e0; }
.analytics-label { font-size: 12px; color: #666; margin-bottom: 4px; }
.analytics-value { font-size: 18px; font-weight: 700; color: #0B2044; }
@media (max-width: 600px) {
  .visualizations-view { padding: 0 16px; }
  .action-buttons { flex-direction: column; }
  .chart-container { height: 300px; }
}
</style>