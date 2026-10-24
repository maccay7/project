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
            <v-spacer></v-spacer>
            <v-chip v-if="selectedInstrumentHasSavedCurve" color="success" size="small">
              Saved for {{ displayInstrumentLabel }}
            </v-chip>
            <v-chip v-else color="warning" size="small">
              Not yet saved for {{ displayInstrumentLabel }}
            </v-chip>
          </v-card-title>
          <v-card-text>
            <v-row class="mb-3">
              <v-col cols="12" md="3">
                <v-select
                  v-model="selectedInstrument"
                  :items="instrumentOptions"
                  label="Instrument"
                  density="compact"
                  @update:model-value="onFilterChange"
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
                  @update:model-value="() => { onCountryChange(); onFilterChange() }"
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
                  @update:model-value="onFilterChange"
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
                  @update:model-value="onFilterChange"
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
                  @update:model-value="onFilterChange"
                />
              </v-col>
              <v-col cols="12" md="4">
                <v-text-field
                  v-model="fredFilters.toDate"
                  type="date"
                  label="To Date"
                  density="compact"
                  @update:model-value="onFilterChange"
                />
              </v-col>
            </v-row>
            <p v-if="dateRangeError" class="date-error mb-2">{{ dateRangeError }}</p>
            <p class="fred-note mb-2">
              Market data from FRED — {{ fredFilters.country }} ({{ fredFilters.currency }}).
            </p>
            <v-alert v-if="yieldLoading" type="info" density="compact" class="mb-3">Loading Yield Curve...</v-alert>
            <v-alert v-if="yieldError" type="error" density="compact" class="mb-3">{{ yieldError }}</v-alert>
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
            <p style="font-size:12px;color:#666;margin-top:8px;">
              The report will use the curve currently saved for each instrument.
            </p>
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
import { ref, computed, nextTick, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import FixedLayout from '../components/FixedLayout.vue'
import api from '@/services/api.js'
import sessionManager from '@/services/sessionManager.js'
import { markStepCompleted } from '@/utils/workflowProgress.js'
import { useFredMarket } from '@/composables/useFredMarket'
import { Chart, registerables } from 'chart.js'
import 'chartjs-adapter-date-fns'

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

const savedCurvePresence = ref({ 'money-market': false, bonds: false, tbills: false })

const selectedInstrumentHasSavedCurve = computed(() => {
  const keys = workflowKeysFor(selectedInstrument.value)
  return keys.length > 0 && keys.every(k => savedCurvePresence.value[k])
})

const displayInstrumentLabel = computed(() => {
  const keys = workflowKeysFor(selectedInstrument.value)
  return keys.map(k => k === 'tbills' ? 'T-Bills' : k === 'bonds' ? 'Bonds' : 'Money Market').join(' + ')
})

function workflowKeysFor(instrumentKey) {
  const s = String(instrumentKey || '').toLowerCase().replace(/[_\s]+/g, '-')
  if (s === 'all') return ['money-market', 'bonds', 'tbills']
  if (s === 'tbills' || s === 't-bills' || s === 'tbill' || s === 'treasury-bills'
      || s === 'treasurybills' || s === 'treasury-bill' || s === 'tbo') {
    return ['tbills']
  }
  if (s === 'bonds' || s === 'bond') return ['bonds']
  if (s === 'money-market' || s === 'moneymarket' || s === 'mm' || s === 'money') {
    return ['money-market']
  }
  return []
}

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

function extractYieldPoints(apiData, isDateMode = false) {
  if (!apiData) return []
  const out = []
  
  if (apiData.datasets?.[0]?.data?.length) {
    for (const pt of apiData.datasets[0].data) {
      const rate = parseFloat(pt.y ?? pt.rate)
      if (isNaN(rate) || rate === 0) continue
      const rawX = pt.x
      const isDate = typeof rawX === 'string' || (typeof rawX === 'number' && rawX > 9999999999)
      if (isDate) {
        const d = pt.date || (typeof rawX === 'string' ? rawX : new Date(rawX).toISOString().slice(0, 10))
        out.push({ x: new Date(d).getTime(), y: rate, maturityLabel: d, rate, date: d, isDate: true })
      } else {
        const mat = parseFloat(rawX)
        if (isNaN(mat)) continue
        out.push({
          x: mat, y: rate,
          maturity: mat,
          maturityLabel: pt.label || String(mat),
          rate,
          date: pt.date || null,
          isDate: false
        })
      }
    }
    return out
  }
  
  if (Array.isArray(apiData.maturities) && Array.isArray(apiData.rates)) {
    apiData.maturities.forEach((m, i) => {
      const rate = parseFloat(apiData.rates[i])
      if (isNaN(rate) || rate === 0) return
      const dateStr = apiData.dates?.[i] || null
      
      if (isDateMode && dateStr) {
        const ts = new Date(dateStr).getTime()
        out.push({
          x: ts, y: rate,
          maturity: null,
          maturityLabel: dateStr,
          rate,
          date: dateStr,
          isDate: true
        })
      } else {
        const mat = parseFloat(m) || 1.0
        out.push({
          x: mat, y: rate,
          maturity: mat,
          maturityLabel: apiData.labels?.[i] || String(m),
          rate,
          date: dateStr,
          isDate: false
        })
      }
    })
    return out
  }
  return out
}

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

    await refreshSavedCurvePresence()

    // If session already has a curve for the current instrument, restore the
    // filters that produced it — so the chart matches what the report will show.
    await restoreFiltersFromSession()

    await loadYieldCurve()
    await loadComparisonChart()
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
  }
}

function setMaturityMode(mode) {
  fredFilters.value.maturityMode = mode
  onFilterChange()
}

function onFilterChange() {
  loadYieldCurve()
}

async function refreshSavedCurvePresence() {
  const sid = sessionManager.getActiveSessionId()
  if (!sid) return
  for (const key of ['money-market', 'bonds', 'tbills']) {
    try {
      const wf = await sessionManager.getInstrumentWorkflow(sid, key)
      savedCurvePresence.value[key] = !!(wf?.yieldCurveData && wf.yieldCurveData.length >= 2)
    } catch {
      savedCurvePresence.value[key] = false
    }
  }
}

async function restoreFiltersFromSession() {
  const sid = sessionManager.getActiveSessionId()
  if (!sid) return
  const keys = workflowKeysFor(selectedInstrument.value)
  for (const key of keys) {
    try {
      const wf = await sessionManager.getInstrumentWorkflow(sid, key)
      const f = wf?.fredFilters
      if (f && f.country) {
        if (f.country) fredFilters.value.country = f.country
        if (f.currency) fredFilters.value.currency = f.currency
        if (f.maturity) fredFilters.value.maturity = f.maturity
        if (f.maturityMode) fredFilters.value.maturityMode = f.maturityMode
        if (f.fromDate) fredFilters.value.fromDate = f.fromDate
        if (f.toDate) fredFilters.value.toDate = f.toDate
        return
      }
    } catch { /* keep defaults */ }
  }
}

function chartDatasets(payload) {
  if (payload.datasets && payload.datasets.length) {
    return payload.datasets.map(d => {
      let chartData
      if (d.data && d.data.length > 0 && typeof d.data[0] === 'object' && 'x' in d.data[0]) {
        chartData = d.data
      } else {
        const maturities = d.maturities || payload.labels || []
        chartData = d.data.map((val, idx) => ({ x: maturities[idx] || idx, y: val }))
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
        await nextTick()
        renderYieldChart()
        await persistYieldCurveToSession(cached.data)
        await refreshSavedCurvePresence()
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
      currency: fredFilters.value.currency,
      maturity: fredFilters.value.maturity // Always send maturity
    }
    if (fredFilters.value.maturityMode === 'date') {
      params.from_date = fredFilters.value.fromDate
      params.to_date = fredFilters.value.toDate
    }

    const res = await api.fredAPI.getYieldCurve(params)

    if (res?.success && (res.data?.datasets?.length || res.data?.maturities?.length)) {
      yieldData.value = res.data
      yieldCurveCache.value.set(cacheKey, {
        data: res.data,
        timestamp: Date.now()
      })
      await persistYieldCurveToSession(res.data)
      await refreshSavedCurvePresence()
    } else {
      yieldError.value = res?.data?.error || res?.error || 'Unable to load Yield Curve. Please try again.'
      yieldData.value = null
    }
    await nextTick()
    renderYieldChart()
  } catch (err) {
    yieldError.value = 'Unable to load Yield Curve. Please try again.'
    yieldData.value = null
    console.error(err)
  } finally {
    yieldLoading.value = false
  }
}

async function persistYieldCurveToSession(apiData) {
  const session = sessionManager.getActiveSession()
  const sid = session?.id || sessionManager.getActiveSessionId()
  if (!sid) return

  const isDateMode = fredFilters.value.maturityMode === 'date'
  const points = extractYieldPoints(apiData, isDateMode)
  if (!points.length) return

  const targetKeys = workflowKeysFor(selectedInstrument.value)
  const filters = {
    country: fredFilters.value.country,
    currency: fredFilters.value.currency,
    maturity: fredFilters.value.maturity,
    maturityMode: fredFilters.value.maturityMode,
    fromDate: fredFilters.value.fromDate,
    toDate: fredFilters.value.toDate
  }

  for (const key of targetKeys) {
    try {
      const workflow = await sessionManager.getInstrumentWorkflow(sid, key)
      const base = workflow || {}
      await sessionManager.saveInstrumentWorkflow(sid, key, {
        ...base,
        fredFilters: filters,
        yieldCurveData: points,
        yieldCurveSavedAt: new Date().toISOString()
      })
    } catch (e) {
      console.warn('Failed to persist yield curve for', key, e)
    }
  }
}

function renderYieldChart() {
  if (!yieldCanvas.value || !yieldData.value) return
  if (yieldChart) yieldChart.destroy()
  const ctx = yieldCanvas.value.getContext('2d')

  let xAxisTitle = 'Maturity'
  let xScaleOptions = {}
  let filteredData = []

  if (fredFilters.value.maturityMode === 'date') {
    xAxisTitle = 'Date'
    filteredData = yieldData.value.datasets.map(ds => {
      const dateFilteredData = ds.data
        .filter(pt => pt.date !== null && pt.date !== undefined)
        .sort((a, b) => new Date(a.date) - new Date(b.date))
      const data = dateFilteredData.map(pt => ({
        x: new Date(pt.date).getTime(),
        y: pt.y,
        label: pt.date,
        originalDate: pt.date
      }))
      return { ...ds, data }
    })
    xScaleOptions = {
      type: 'time',
      time: { unit: 'month', displayFormats: { month: 'MMM yyyy' } },
      title: { display: true, text: xAxisTitle },
      ticks: { maxRotation: 45, minRotation: 45 }
    }
  } else {
    const maturities = yieldData.value.maturities || []
    const maxMaturity = maturities.length ? Math.max(...maturities) : 10
    const selectedMaturityStr = fredFilters.value.maturity || '1Y'
    let effectiveMax = maxMaturity
    const match = selectedMaturityStr.match(/^(\d+)([YMW])$/)
    if (match) {
      const num = parseInt(match[1], 10)
      xAxisTitle = match[2] === 'Y' ? 'Years' : match[2] === 'M' ? 'Months' : 'Weeks'
      effectiveMax = Math.min(maxMaturity, num)
    } else {
      effectiveMax = Math.min(maxMaturity, parseFloat(selectedMaturityStr) || 10)
    }
    filteredData = yieldData.value.datasets.map(ds => {
      let data = ds.data.filter(pt => pt.x <= effectiveMax)
      if (!data.some(pt => pt.x === 0)) data = [{ x: 0, y: data[0]?.y || 0 }, ...data]
      return { ...ds, data }
    })
    xScaleOptions = {
      type: 'linear',
      title: { display: true, text: xAxisTitle },
      min: 0,
      max: effectiveMax,
      ticks: {
        autoSkip: false,
        stepSize: 1,
        callback: value => Number.isInteger(value) && value >= 0 && value <= effectiveMax ? value.toString() : null
      }
    }
  }

  if (filteredData.every(ds => ds.data.length === 0)) {
    yieldError.value = 'No yield curve data available for selected range'
    return
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
            label: ctx => `${ctx.raw.label || ctx.raw.x}: ${ctx.raw.y.toFixed(2)}%`
          }
        }
      },
      scales: {
        y: { title: { display: true, text: 'Yield (%)' } },
        x: xScaleOptions
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
        plugins: { legend: { position: 'top' } },
        scales: {
          y: { title: { display: true, text: 'Yield (%)' } },
          x: {
            type: 'linear',
            title: { display: true, text: 'Maturity (Years)' },
            min: 0,
            max: maxMaturity,
            ticks: { autoSkip: false, stepSize: 1 }
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
  // If a FRED load is still in flight, wait for it so the session save is current.
  if (yieldLoading.value) {
    await new Promise(resolve => {
      const check = setInterval(() => {
        if (!yieldLoading.value) { clearInterval(check); resolve() }
      }, 100)
      setTimeout(() => { clearInterval(check); resolve() }, 8000)
    })
  }
  try {
    const session = sessionManager.getActiveSession()
    const sid = session?.id || sessionManager.getActiveSessionId()
    if (sid) {
      await markStepCompleted(String(sid), 'visualizations')
      if (yieldData.value) await persistYieldCurveToSession(yieldData.value)
      await refreshSavedCurvePresence()
    }
  } catch (e) {
    console.warn('Failed to save FRED settings:', e)
  }
  router.push({ name: 'reports', query: { dataset_id: datasetId } })
}

onMounted(async () => {
  try {
    await loadFilterOptions()
  } catch (e) {
    console.warn('FRED filter options failed to load:', e?.message || e)
  }
  if (route.query.dataset_id) {
    loadData().catch(err => console.error('loadData failed:', err))
  }
})
</script>

<style scoped>
.visualizations-view { max-width: 1400px; margin: 0 auto; padding: 20px; }
.page-header { margin-bottom: 30px; }
.page-header h1 { color: #0B2A44; font-size: 32px; font-weight: 700; margin-bottom: 8px; }
.page-header p { color: #666; font-size: 16px; }
.action-buttons { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 30px; }
.stats-card, .chart-card { border-radius: 12px; margin-bottom: 30px; background: white; border: 1px solid rgba(11,42,68,0.08); position: relative; }
.stats-card::before, .chart-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; background: linear-gradient(90deg, #0B2A44, #1E88E5); border-radius: 12px 12px 0 0; }
.card-title { display: flex; align-items: center; color: #0B2A44; font-weight: 600; font-size: 18px; padding: 16px 20px 0 20px; }
.title-icon { margin-right: 8px; }
.fred-note { font-size: 13px; color: #666; }
.chart-container { height: 400px; position: relative; padding: 16px; }
.kpi-card { background: white; border-radius: 20px; padding: 18px; display: flex; align-items: center; gap: 12px; position: relative; overflow: hidden; cursor: pointer; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05); transition: all 0.3s ease; }
.kpi-top-bar { position: absolute; top: 0; left: 0; right: 0; height: 4px; background: linear-gradient(90deg, #0B2044, #1E88E5, #4CAF50); }
.kpi-card:hover { transform: translateY(-5px); box-shadow: 0 12px 28px rgba(0, 0, 0, 0.15); }
.kpi-icon { width: 52px; height: 52px; border-radius: 14px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; transition: transform 0.3s ease; }
.kpi-card:hover .kpi-icon { transform: scale(1.05); }
.kpi-content { display: flex; align-items: center; gap: 12px; height: 100%; }
.kpi-info { flex: 1; }
.kpi-value { font-size: 20px; font-weight: 800; color: #0B2044; }
.kpi-title { font-size: 10px; color: #888; }
.action-card { border-radius: 12px; background: white; border: 1px solid rgba(11,42,68,0.08); text-align: center; padding: 16px; }
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