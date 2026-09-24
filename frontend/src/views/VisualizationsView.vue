<template>
  <fixed-layout>
    <div class="visualizations-view">

      <div class="page-header">
        <h1>Data Visualizations</h1>
        <p>Visualize your financial calculations with interactive charts</p>
      </div>

      <div class="action-buttons">
        <v-btn color="#0B2A44" @click="loadData">
          <v-icon left>mdi-database</v-icon> Load Data
        </v-btn>
        <v-btn color="#0B2A44" variant="outlined" @click="clearData" :disabled="!hasData">
          <v-icon left>mdi-delete</v-icon> Clear Data
        </v-btn>
      </div>

      <template v-if="hasData">

        <v-card class="stats-card">
          <v-card-title class="card-title">
            <v-icon class="title-icon">mdi-chart-line</v-icon> Calculation Overview
          </v-card-title>
          <v-card-text>
            <v-row>
              <v-col cols="12" sm="6" md="3" v-for="stat in kpiStats" :key="stat.title">
                <v-card class="kpi-card">
                  <div class="kpi-top-bar"></div>
                  <v-card-text>
                    <div class="kpi-content">
                      <div class="kpi-icon" :style="{ background: stat.gradient }">
                        <v-icon size="28" color="white">{{ stat.icon }}</v-icon>
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
                <div class="maturity-mode-toggle">
                  <button
                    type="button"
                    class="mode-btn"
                    :class="{ active: fredFilters.maturityMode !== 'date' }"
                    @click="setMaturityMode('tenor')"
                  >Maturity / Tenor</button>
                  <button
                    type="button"
                    class="mode-btn"
                    :class="{ active: fredFilters.maturityMode === 'date' }"
                    @click="setMaturityMode('date')"
                  >Actual Date</button>
                </div>
              </v-col>
            </v-row>

            <v-row class="mb-3" v-if="fredFilters.maturityMode !== 'date'">
              <v-col cols="12" md="4">
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

            <v-row class="mb-3" v-else>
              <v-col cols="12" md="4">
                <v-text-field
                  v-model="fredFilters.fromDate"
                  type="date"
                  label="From Date"
                  density="compact"
                  @update:model-value="loadYieldCurve"
                />
              </v-col>
              <v-col cols="12" md="4">
                <v-text-field
                  v-model="fredFilters.toDate"
                  type="date"
                  label="To Date"
                  density="compact"
                  @update:model-value="loadYieldCurve"
                />
              </v-col>
            </v-row>
            <p v-if="dateRangeError" class="date-error mb-2">{{ dateRangeError }}</p>

            <p class="fred-note mb-2">
              Market data from FRED — {{ fredFilters.country }} ({{ fredFilters.currency }}). Non-US countries use government bond yields available on FRED.
            </p>
            <v-alert v-if="yieldLoading" type="info" density="compact" class="mb-3">Loading Yield Curve...</v-alert>
            <v-alert v-if="yieldError" type="error" density="compact" class="mb-3">{{ yieldError }}</v-alert>
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

        <v-card class="action-card">
          <v-card-text class="text-center">
            <v-btn color="#0B2A44" size="large" @click="goToReports">
              Proceed to Reports <v-icon right>mdi-arrow-right</v-icon>
            </v-btn>
          </v-card-text>
        </v-card>
      </template>

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
import { ref, computed, nextTick, onMounted } from 'vue'
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

const hasData = ref(false)
const calcData = ref(null)
const yieldData = ref(null)
const yieldError = ref('')
const yieldLoading = ref(false)
const selectedInstrument = ref('')
const instrumentOptions = [
  { title: 'All Instruments', value: 'all' },
  { title: 'Treasury Bills', value: 'treasury_bills' },
  { title: 'Bonds', value: 'bonds' },
  { title: 'Money Market', value: 'money_market' }
]

const yieldAnalytics = ref(null)

const { fredFilters, countryItems, currencyItems, maturityItems, loadFilterOptions, onCountryChange } = useFredMarket('1Y')

const yieldCanvas = ref(null)
const compareCanvas = ref(null)
let yieldChart = null
let compareChart = null

const yieldCurveCache = ref(new Map())
const lastYieldCurveRequest = ref({})

const kpiStats = ref([
  { title: 'Records', value: 0, icon: 'mdi-table-large', gradient: 'linear-gradient(135deg, #0B2044, #1a3a6e)' },
  { title: 'Instrument Type', value: 'N/A', icon: 'mdi-shape-outline', gradient: 'linear-gradient(135deg, #1E88E5, #42a5f5)' },
  { title: 'Average Yield', value: '0%', icon: 'mdi-percent-outline', gradient: 'linear-gradient(135deg, #4CAF50, #2E7D32)' },
  { title: 'Data Source', value: 'FRED API', icon: 'mdi-web', gradient: 'linear-gradient(135deg, #FFC107, #FF9800)' }
])

const dateRangeError = computed(() => {
  if (fredFilters.value.maturityMode !== 'date') return ''
  const { fromDate, toDate } = fredFilters.value
  if (fromDate && toDate && fromDate > toDate) return 'From date must be on or before To date.'
  return ''
})

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
    const inst = (res.data.instrument_type || '').toLowerCase().replace('-', '_')
    kpiStats.value[1].value = inst.replace('_', ' ')
    selectedInstrument.value = inst || 'all'
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

function getAvgYield(calculations) {
  if (!calculations.length) return 0
  const yields = calculations.map(c => parseFloat(c.annual_yield || c.yield_to_maturity || c.bond_equivalent_yield || 0))
  const avg = yields.reduce((a, b) => a + b, 0) / yields.length
  return avg.toFixed(2)
}

function clearData() {
  if (confirm('Clear all data?')) {
    hasData.value = false
    calcData.value = null
    if (yieldChart) { yieldChart.destroy(); yieldChart = null }
    if (compareChart) { compareChart.destroy(); compareChart = null }
    alert('Data cleared')
  }
}

function setMaturityMode(mode) {
  fredFilters.value.maturityMode = mode
  loadYieldCurve()
}

function chartDatasets(payload) {
  if (payload.datasets && payload.datasets.length) {
    return payload.datasets.map(d => {
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

async function loadYieldCurve() {
  if (dateRangeError.value) {
    yieldError.value = dateRangeError.value
    return
  }
  yieldError.value = ''
  yieldLoading.value = true
  try {
    const cacheKey = `${selectedInstrument.value}_${fredFilters.value.country}_${fredFilters.value.currency}_${fredFilters.value.maturityMode}_${fredFilters.value.maturity}_${fredFilters.value.fromDate}_${fredFilters.value.toDate}`
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
    if (lastYieldCurveRequest.value[cacheKey] && Date.now() - lastYieldCurveRequest.value[cacheKey] < 1000) {
      return
    }
    lastYieldCurveRequest.value[cacheKey] = Date.now()

    const params = {
      instrument_type: selectedInstrument.value,
      country: fredFilters.value.country,
      currency: fredFilters.value.currency
    }
    if (fredFilters.value.maturityMode === 'date') {
      params.from_date = fredFilters.value.fromDate
      params.to_date = fredFilters.value.toDate
    } else {
      params.maturity = fredFilters.value.maturity
    }

    const res = await api.fredAPI.getYieldCurve(params)

    if (res?.success && res.data?.datasets?.length) {
      yieldData.value = res.data
      yieldAnalytics.value = res.data.analytics || null
      yieldCurveCache.value.set(cacheKey, {
        data: res.data,
        analytics: res.data.analytics || null,
        timestamp: Date.now()
      })

      const session = sessionManager.getActiveSession()
      const sid = session?.id || sessionManager.getActiveSessionId()
      if (sid) {
        const workflow = await sessionManager.getInstrumentWorkflow(sid, selectedInstrument.value)
        if (workflow) {
          const yieldCurvePoints = []
          if (res.data.datasets[0]?.data) {
            res.data.datasets[0].data.forEach(pt => {
              yieldCurvePoints.push({ maturity: pt.x, rate: pt.y })
            })
          }

          await sessionManager.updateInstrumentWorkflow(sid, selectedInstrument.value, {
            ...workflow,
            fredFilters: { ...fredFilters.value },
            yieldCurveData: yieldCurvePoints
          })
        }
      }
    } else {
      yieldError.value = res?.data?.error || res?.error || 'Unable to load Yield Curve. Please try again.'
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

function renderYieldChart() {
  if (!yieldCanvas.value || !yieldData.value) return
  if (yieldChart) yieldChart.destroy()
  const ctx = yieldCanvas.value.getContext('2d')

  const maturities = yieldData.value.maturities || []
  const maxMaturity = maturities.length ? Math.max(...maturities) : 10
  const selectedMaturityStr = fredFilters.value.maturity || '1Y'

  let effectiveMax = maxMaturity
  let xAxisTitle = 'Maturity'
  let stepSize = 1

  const match = selectedMaturityStr.match(/^(\d+)([YMW])$/)
  if (fredFilters.value.maturityMode === 'date') {
    xAxisTitle = 'Date'
  } else if (match) {
    const num = parseInt(match[1], 10)
    const unit = match[2]
    if (unit === 'Y') {
      xAxisTitle = 'Years'
      stepSize = num > 5 ? 5 : 1
      effectiveMax = Math.min(maxMaturity, num)
    } else if (unit === 'M') {
      xAxisTitle = 'Months'
      effectiveMax = Math.min(maxMaturity, num)
    } else if (unit === 'W') {
      xAxisTitle = 'Weeks'
      effectiveMax = Math.min(maxMaturity, num)
    }
  } else {
    xAxisTitle = 'Years'
    const num = parseFloat(selectedMaturityStr) || 10
    effectiveMax = Math.min(maxMaturity, num)
    stepSize = num > 5 ? 5 : 1
  }

  const filteredData = yieldData.value.datasets.map(ds => {
    let data = ds.data.filter(pt => pt.x <= effectiveMax)
    if (!data.some(pt => pt.x === 0)) {
      data = [{ x: 0, y: data[0]?.y || 0 }, ...data]
    }
    return { ...ds, data }
  })

  if (filteredData.every(ds => ds.data.length === 0)) {
    yieldError.value = 'No yield curve data available for selected range'
    return
  }

  const dataPoints = filteredData[0]?.data || []
  const labelsMap = {}
  dataPoints.forEach(pt => {
    const xVal = pt.x
    const labelIndex = yieldData.value.maturities.findIndex(m => Math.abs(m - xVal) < 0.01)
    if (labelIndex !== -1 && yieldData.value.labels && yieldData.value.labels[labelIndex]) {
      labelsMap[xVal] = yieldData.value.labels[labelIndex]
    }
  })

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
              const label = labelsMap[pt.x] || pt.x.toFixed(0)
              return `${label}: ${pt.y.toFixed(2)}%`
            }
          }
        }
      },
      scales: {
        y: { title: { display: true, text: 'Yield (%)' } },
        x: {
          type: 'linear',
          title: { display: true, text: xAxisTitle },
          min: 0,
          max: effectiveMax,
          ticks: {
            callback: function(value) {
              if (labelsMap[value]) return labelsMap[value]
              if (Number.isInteger(value) && value >= 0) return value.toString()
              return null
            },
            stepSize: stepSize
          }
        }
      }
    }
  })
}

async function loadComparisonChart() {
  try {
    const params = {
      instrument_type: 'all',
      country: fredFilters.value.country,
      currency: fredFilters.value.currency
    }
    const res = await api.fredAPI.getYieldCurve(params)
    if (!res?.success || !res.data?.maturities?.length) return
    await nextTick()
    if (compareChart) compareChart.destroy()
    const ctx = compareCanvas.value?.getContext('2d')
    if (!ctx) return

    const maturities = res.data.maturities || []
    const maxMaturity = maturities.length ? Math.max(...maturities) : 10

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
            max: maxMaturity,
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

async function goToReports() {
  const datasetId = route.query.dataset_id
  if (!datasetId) {
    alert('Dataset reference missing. Please run calculations first.')
    return
  }
  try {
    const session = sessionManager.getActiveSession()
    const sid = session?.id || sessionManager.getActiveSessionId()
    if (sid) {
      await markStepCompleted(String(sid), 'visualizations')

      const workflow = await sessionManager.getInstrumentWorkflow(sid, selectedInstrument.value)
      if (workflow) {
        const yieldCurvePoints = []
        if (yieldData.value?.datasets?.[0]?.data) {
          yieldData.value.datasets[0].data.forEach(pt => {
            yieldCurvePoints.push({ maturity: pt.x, rate: pt.y })
          })
        }

        await sessionManager.updateInstrumentWorkflow(sid, selectedInstrument.value, {
          ...workflow,
          fredFilters: { ...fredFilters.value },
          yieldCurveData: yieldCurvePoints
        })
      }
    }
  } catch (e) {
    console.warn('Failed to save FRED settings:', e)
  }
  router.push({ name: 'reports', query: { dataset_id: datasetId } })
}

onMounted(async () => {
  await loadFilterOptions()
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
.kpi-card { background: white; border-radius: 20px; padding: 18px; display: flex; align-items: center; gap: 12px; position: relative; overflow: hidden; cursor: pointer; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05); transition: all 0.3s ease; }
.kpi-top-bar { position: absolute; top: 0; left: 0; right: 0; height: 4px; background: linear-gradient(90deg, #0B2044, #1E88E5, #4CAF50); transform: scaleX(1); }
.kpi-card:hover { transform: translateY(-5px); box-shadow: 0 12px 28px rgba(0, 0, 0, 0.15); }
.kpi-icon { width: 52px; height: 52px; border-radius: 14px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; transition: transform 0.3s ease; }
.kpi-card:hover .kpi-icon { transform: scale(1.05); }
.kpi-content { display: flex; align-items: center; gap: 12px; height: 100%; }
.kpi-info { flex: 1; }
.kpi-value { font-size: 20px; font-weight: 800; color: #0B2044; }
.kpi-title { font-size: 10px; color: #888; }
.action-card { border-radius: 12px; background: white; border: 1px solid rgba(11,42,68,0.08); text-align: center; padding: 16px; }
.analytics-card { border-radius: 8px; background: #f8f9ff; border: 1px solid #e0e0e0; }
.analytics-label { font-size: 12px; color: #666; margin-bottom: 4px; }
.analytics-value { font-size: 18px; font-weight: 700; color: #0B2044; }
.maturity-mode-toggle { display: flex; gap: 6px; }
.mode-btn { flex: 1; padding: 6px 10px; border: 1px solid #c0c0c0; border-radius: 6px; background: white; cursor: pointer; font-size: 12px; color: #0B2044; }
.mode-btn.active { background: #0B2A44; color: white; border-color: #0B2A44; }
.date-error { color: #c62828; font-size: 12px; }
@media (max-width: 600px) {
  .visualizations-view { padding: 0 16px; }
  .action-buttons { flex-direction: column; }
  .chart-container { height: 300px; }
}
</style>