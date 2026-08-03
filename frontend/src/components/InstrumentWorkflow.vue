<template>
  <div class="instrument-workflow">
    <div class="workflow-header">
      <h2>{{ instrumentName }}</h2>
      <v-btn color="grey" variant="text" @click="$router.push('/')">← Back to Dashboard</v-btn>
    </div>

    <!-- Step content based on current step -->
    <div class="step-content">
      <!-- Upload Step -->
      <div v-if="currentStep === 'upload'">
        <v-card>
          <v-card-title>Upload Data</v-card-title>
          <v-card-text>
            <input type="file" @change="uploadFile" accept=".xlsx,.csv" />
            <v-btn color="#0B2A44" class="mt-3" @click="loadSample" v-if="!data">Load Sample Data</v-btn>
            <div v-if="data" class="mt-3">
              <v-alert type="success">Loaded {{ data.length }} rows</v-alert>
              <v-btn color="primary" @click="nextStep">Proceed to Clean →</v-btn>
            </div>
          </v-card-text>
        </v-card>
      </div>

      <!-- Clean Step -->
      <div v-if="currentStep === 'clean'">
        <v-card>
          <v-card-title>Clean Data</v-card-title>
          <v-card-text>
            <v-checkbox v-for="opt in cleanOptions" :key="opt.key" v-model="opt.value" :label="opt.label"></v-checkbox>
            <v-btn color="#0B2A44" @click="cleanData" :loading="cleaning">Start Cleaning</v-btn>
            <div v-if="cleanedStats" class="mt-3">
              <v-alert type="success">Rows: {{ cleanedStats.originalRows }} → {{ cleanedStats.cleanedRows }}</v-alert>
              <v-btn color="primary" @click="nextStep">Proceed to Calculate →</v-btn>
            </div>
          </v-card-text>
        </v-card>
      </div>

      <!-- Calculate Step -->
      <div v-if="currentStep === 'calculate'">
        <v-card>
          <v-card-title>Calculations</v-card-title>
          <v-card-text>
            <v-btn color="#0B2A44" @click="calculate" :loading="calculating">Calculate Yields</v-btn>
            <div v-if="calculations.length" class="mt-3">
              <v-alert type="success">{{ calculations.length }} calculations completed</v-alert>
              <div class="calc-preview">
                <div v-for="calc in calculations.slice(0, 3)" :key="calc.id">
                  Principal: ${{ calc.principal }} | Yield: {{ calc.annual_yield }}%
                </div>
              </div>
              <v-btn color="primary" @click="nextStep">Proceed to Visualize →</v-btn>
            </div>
          </v-card-text>
        </v-card>
      </div>

      <!-- Visualize Step -->
      <div v-if="currentStep === 'visualize'">
        <v-card>
          <v-card-title>Visualizations</v-card-title>
          <v-card-text>
            <canvas ref="yieldCanvas" height="300"></canvas>
            <v-btn color="primary" class="mt-3" @click="nextStep">Proceed to Reports →</v-btn>
          </v-card-text>
        </v-card>
      </div>

      <!-- Reports Step -->
      <div v-if="currentStep === 'reports'">
        <v-card>
          <v-card-title>Generate Report</v-card-title>
          <v-card-text>
            <v-btn color="#0B2A44" @click="downloadReport('word')">Download</v-btn>
            <v-btn color="success" class="ml-2" @click="completeAndFinish">Finish & Save</v-btn>
          </v-card-text>
        </v-card>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { dataAPI } from '../services/api'
import api from '../services/api'
import sessionManager from '@/services/sessionManager.js'
import { markStepCompleted } from '@/utils/workflowProgress.js'
import * as XLSX from 'xlsx'
import Chart from 'chart.js/auto'

const route = useRoute()
const router = useRouter()
const instrument = route.params.type
const sessionId = route.query.session
const currentStep = ref(route.query.step || 'upload')

const instrumentName = computed(() => {
  const names = { treasury_bills: 'Treasury Bills', bonds: 'Bonds', money_market: 'Money Market' }
  return names[instrument] || instrument
})

// Data states
const data = ref(null)
const cleanedStats = ref(null)
const calculations = ref([])
const cleaning = ref(false)
const calculating = ref(false)

const cleanOptions = ref([
  { key: 'removeDuplicates', label: 'Remove Duplicates', value: true },
  { key: 'fillMissingValues', label: 'Fill Missing Values', value: true },
  { key: 'trimWhitespace', label: 'Trim Whitespace', value: true }
])

// Chart
const yieldCanvas = ref(null)
let yieldChart = null

// Navigation
function nextStep() {
  const steps = ['upload', 'clean', 'calculate', 'visualize', 'reports']
  const idx = steps.indexOf(currentStep.value)
  if (idx < steps.length - 1) {
    const prev = currentStep.value
    const next = steps[idx + 1]
    // mark the previous step as completed (persisted)
    try { markStepCompleted(sessionId, prev) } catch (e) { console.error(e) }
    currentStep.value = next
    router.replace({ query: { ...route.query, step: currentStep.value } })
  }
}

// Upload
async function uploadFile(event) {
  const file = event.target.files[0]
  if (!file) return
  const formData = new FormData()
  formData.append('file', file)
  formData.append('instrument_type', instrument)
  try {
    const res = await dataAPI.upload(file, instrument)
    if (res.data?.file_base64) {
      data.value = res.data.data || []
      sessionManager.updateSessionData(sessionId, 'data', data.value, data.value.length)
    }
  } catch (err) { console.error(err) }
}

function loadSample() {
  // Sample data removed - should be loaded from backend/database
  console.warn('Sample data loading is disabled. Please upload a file or load from session.')
  data.value = []
}

// Clean
async function cleanData() {
  cleaning.value = true
  try {
    const options = {}
    cleanOptions.value.forEach(o => { if (o.value) options[o.key] = true })
    const res = await dataAPI.clean(data.value, options)
    cleanedStats.value = { originalRows: data.value.length, cleanedRows: res.data.length }
    data.value = res.data
    sessionManager.updateSessionData(sessionId, 'cleanedData', data.value, data.value.length)
  } catch (err) { console.error(err) }
  finally { cleaning.value = false }
}

// Calculate
async function calculate() {
  calculating.value = true
  try {
    const res = await dataAPI.calculate(data.value, instrument, {})
    calculations.value = res.calculations
    sessionManager.updateSessionData(sessionId, 'calculations', calculations.value, calculations.value.length)
  } catch (err) { console.error(err) }
  finally { calculating.value = false }
}

// Visualize - draw yield curve (fetch from backend FRED endpoint)
async function drawYieldCurve() {
  if (!yieldCanvas.value) return
  if (yieldChart) yieldChart.destroy()
  try {
    const res = await api.fredAPI.getYieldCurve(instrument)
    const labels = (res && res.success && res.data && res.data.labels) ? res.data.labels : ['3M', '6M', '1Y', '2Y', '5Y', '10Y', '30Y']
    const values = (res && res.success && res.data && res.data.current) ? res.data.current : [4.2, 4.4, 4.6, 4.8, 4.5, 4.3, 4.1]
    const ctx = yieldCanvas.value.getContext('2d')
    yieldChart = new Chart(ctx, {
      type: 'line',
      data: { labels, datasets: [{ label: 'Yield Curve', data: values, borderColor: '#0B2A44', fill: true }] },
      options: { responsive: true, maintainAspectRatio: false }
    })
  } catch (err) {
    console.error('Failed to load yield curve from backend', err)
    if (yieldChart) {
      yieldChart.destroy()
      yieldChart = null
    }
  }
}
watch(currentStep, (step) => { if (step === 'visualize') setTimeout(drawYieldCurve, 100) })

// Report
function downloadReport() {
  if (!calculations.value.length) return
  const ws = XLSX.utils.json_to_sheet(calculations.value)
  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, ws, `${instrumentName.value} Report`)
  XLSX.writeFile(wb, `${instrumentName.value}_Report.xlsx`)
}

function completeAndFinish() {
  alert('Session completed and saved!')
  router.push('/')
}

// Load existing session
onMounted(() => {
  if (sessionId) {
    const session = sessionManager.getSession(sessionId)
    if (session?.data) data.value = session.data
    if (session?.cleanedData) { data.value = session.cleanedData; cleanedStats.value = { cleanedRows: session.cleanedData.length } }
    if (session?.calculations) calculations.value = session.calculations
  }
  if (!sessionId && instrument) {
    const newSession = sessionManager.createSession(instrument)
    router.replace({ query: { session: newSession.id, step: currentStep.value } })
  }
})
</script>

<style scoped>
.instrument-workflow {
  padding: 20px;
  max-width: 900px;
  margin: 0 auto;
}
.workflow-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.calc-preview { background: #f5f5f5; padding: 12px; border-radius: 8px; margin-top: 12px; }
</style>