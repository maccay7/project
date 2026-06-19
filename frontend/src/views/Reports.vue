<template>
  <FixedLayout>
    <div class="reports-page">
      <div class="page-header">
        <button class="back-btn" @click="goBack">
          <v-icon>mdi-arrow-left</v-icon> Back
        </button>
        <h1>Generate Report</h1>
        <p>Select report type and generate detailed analysis</p>
      </div>

      <div class="report-actions-row">
        <v-btn color="#0B2A44" @click="loadDatasetPreview">
          <v-icon left>mdi-eye</v-icon> Preview Dataset
        </v-btn>
        <v-btn color="#1E88E5" @click="generatePreview">
          <v-icon left>mdi-file-document-outline</v-icon> Refresh Report
        </v-btn>
        <v-btn color="#0B2A44" @click="markDone">
          <v-icon left>mdi-check-circle</v-icon> Done
        </v-btn>
      </div>

      <div class="report-options">
        <div class="option-card" @click="selectReportType('current')">
          <div class="option-icon" :class="{ active: selectedType === 'current' }">
            <v-icon size="32">mdi-chart-line</v-icon>
          </div>
          <h3>Current Instrument</h3>
          <p>Generate report for the currently selected instrument</p>
        </div>

        <div class="option-card" @click="selectReportType('session')">
          <div class="option-icon" :class="{ active: selectedType === 'session' }">
            <v-icon size="32">mdi-folder</v-icon>
          </div>
          <h3>Full Session</h3>
          <p>Generate report for all instruments in the session</p>
        </div>
      </div>

      <div class="dataset-preview" v-if="showDatasetPreview">
        <h3>Excel Dataset Preview</h3>
        <div class="dataset-info-row">
          <span><strong>Dataset:</strong> {{ dataset?.name || 'Not loaded' }}</span>
          <span><strong>Instrument:</strong> {{ dataset?.instrument_type || 'Unknown' }}</span>
        </div>
        <div class="preview-content" v-if="dataset && dataset.data && dataset.data.length">
          <ExcelViewer
            :data="dataset.data"
            :headers="Object.keys(dataset.data[0] || {})"
            @data-update="handleDatasetUpdate"
          />
        </div>
        <div v-else class="preview-empty">
          <p>No dataset loaded yet. Use Preview Dataset to load the latest upload.</p>
        </div>
      </div>

      <div class="preview-section" v-if="previewData">
        <h3>Report Preview</h3>
        <v-alert v-if="reportError" type="warning" density="compact" class="mb-3">{{ reportError }}</v-alert>
        <div class="preview-content">
          <pre>{{ JSON.stringify(previewData, null, 2) }}</pre>
        </div>
        <div class="download-row">
          <button class="btn-primary" @click="downloadReport('html')">
            <v-icon>mdi-download</v-icon> Download HTML (with charts)
          </button>
          <button class="btn-secondary" @click="downloadReport('json')">
            <v-icon>mdi-code-json</v-icon> Download JSON
          </button>
        </div>
      </div>
    </div>
  </FixedLayout>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import FixedLayout from '@/components/FixedLayout.vue'
import ExcelViewer from '@/components/ExcelViewer.vue'
import { datasetAPI, fredAPI } from '@/services/api'
import sessionManager from '@/services/sessionManager.js'

const router = useRouter()
const route = useRoute()

const selectedType = ref('current')
const previewData = ref(null)
const yieldCurveData = ref(null)
const reportError = ref('')
const dataset = ref(null)
const showDatasetPreview = ref(false)

function selectReportType(type) {
  selectedType.value = type
  generatePreview()
}

async function loadFredForReport() {
  reportError.value = ''
  try {
    const res = await fredAPI.getYieldCurve('all')
    if (res?.success && res.data?.datasets?.length) {
      yieldCurveData.value = res.data
    } else {
      reportError.value = 'FRED yield data not available. Check backend .env FRED_API_KEY.'
      yieldCurveData.value = null
    }
  } catch (e) {
    reportError.value = e.message || 'Failed to load FRED data'
    yieldCurveData.value = null
  }
}

async function generatePreview() {
  await loadFredForReport()
  const reportType = selectedType.value // use current selection

  // Get session data
  let session = null
  try {
    const saved = localStorage.getItem('active_session')
    if (saved) {
      const sid = JSON.parse(saved).id
      session = sessionManager.getSession(sid) || JSON.parse(saved)
    } else {
      const all = sessionManager.getAllSessions() || []
      session = all.length ? all[0] : null
    }
  } catch (e) {
    session = null
  }

  if (!session) {
    reportError.value = 'No active session found.'
    previewData.value = null
    return
  }

  const instrument = route.query.instrument || 'money-market'

  // Get data for the instrument (prefer cleaned data)
  let data = []
  const wf = sessionManager.getInstrumentWorkflow(session.id, instrument)
  if (wf && wf.cleanedData && wf.cleanedData.length) {
    data = wf.cleanedData
  } else {
    // Try raw data
    const rawKey = `${instrument}_session_${session.id}_raw`
    const savedRaw = localStorage.getItem(rawKey)
    if (savedRaw) {
      try { data = JSON.parse(savedRaw) } catch(e) {}
    }
  }

  const preview = {
    type: reportType === 'current' ? 'Current Instrument Report' : 'Full Session Report',
    date: new Date().toLocaleString(),
    session: session.name || 'Current Session',
    instrument: instrument,
    rows: data.length,
    columns: data.length ? Object.keys(data[0]).length : 0,
    sample: data.slice(0, 3)
  }

  if (reportType === 'session') {
    // Gather all instruments
    const allData = {}
    const instruments = ['money-market', 'bonds', 'tbills']
    for (const inst of instruments) {
      const wf2 = sessionManager.getInstrumentWorkflow(session.id, inst)
      if (wf2 && wf2.cleanedData && wf2.cleanedData.length) {
        allData[inst] = wf2.cleanedData
      } else {
        const rawKey2 = `${inst}_session_${session.id}_raw`
        const savedRaw2 = localStorage.getItem(rawKey2)
        if (savedRaw2) {
          try { allData[inst] = JSON.parse(savedRaw2) } catch(e) {}
        }
      }
    }
    preview.instruments = allData
    preview.totalRows = Object.values(allData).reduce((sum, arr) => sum + arr.length, 0)
  }

  previewData.value = preview
  reportError.value = ''
}

function buildReportHtml() {
  const yc = yieldCurveData.value
  const chartBlock = yc?.datasets?.length
    ? `<h2>Yield Curves (FRED)</h2><canvas id="fredChart" height="120"></canvas>
       <script src="https://cdn.jsdelivr.net/npm/chart.js"><\/script>
       <script>
         const ctx = document.getElementById('fredChart').getContext('2d');
         new Chart(ctx, {
           type: 'line',
           data: {
             labels: ${JSON.stringify(yc.labels)},
             datasets: ${JSON.stringify(yc.datasets.map(d => ({
               label: d.label,
               data: d.data,
               borderColor: d.borderColor || '#0B2044',
               tension: 0.35
             })))}
           },
           options: { responsive: true, plugins: { legend: { position: 'top' } } }
         });
       <\/script>`
    : '<p><em>FRED yield curves not loaded.</em></p>'

  return `<!DOCTYPE html><html><head><meta charset="utf-8"><title>DuraCapital Report</title>
    <style>body{font-family:Arial,sans-serif;margin:40px;color:#333}h1{color:#0B2044}
    pre{background:#f5f5f5;padding:16px;border-radius:8px;overflow:auto}</style></head><body>
    <h1>DuraCapital Report</h1><p>Generated: ${new Date().toLocaleString()}</p>
    ${chartBlock}
    <h2>Report Data</h2><pre>${JSON.stringify(previewData.value, null, 2)}</pre>
    </body></html>`
}

function downloadReport(format = 'html') {
  if (format === 'json') {
    const blob = new Blob([JSON.stringify({ ...previewData.value, yieldCurve: yieldCurveData.value }, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `report_${Date.now()}.json`
    a.click()
    URL.revokeObjectURL(url)
    return
  }
  const blob = new Blob([buildReportHtml()], { type: 'text/html' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `report_${Date.now()}.html`
  a.click()
  URL.revokeObjectURL(url)
}

function handleDatasetUpdate(updatedData) {
  if (!dataset.value) return
  dataset.value.data = updatedData
}

async function loadDatasetPreview() {
  showDatasetPreview.value = true
  try {
    // Get session and instrument
    let session = null
    try {
      const saved = localStorage.getItem('active_session')
      if (saved) {
        const sid = JSON.parse(saved).id
        session = sessionManager.getSession(sid) || JSON.parse(saved)
      } else {
        const all = sessionManager.getAllSessions() || []
        session = all.length ? all[0] : null
      }
    } catch (e) { session = null }

    if (!session) {
      alert('No active session found.')
      return
    }

    const instrument = route.query.instrument || 'money-market'
    let data = []
    // Try to get cleaned data
    const wf = sessionManager.getInstrumentWorkflow(session.id, instrument)
    if (wf && wf.cleanedData && wf.cleanedData.length) {
      data = wf.cleanedData
    } else {
      // Fallback to raw data
      const rawKey = `${instrument}_session_${session.id}_raw`
      const savedRaw = localStorage.getItem(rawKey)
      if (savedRaw) {
        try { data = JSON.parse(savedRaw) } catch(e) {}
      }
    }

    if (data.length) {
      dataset.value = {
        name: `${instrument} dataset`,
        instrument_type: instrument,
        data: data
      }
      generatePreview()
    } else {
      alert('No data found for this instrument in the session.')
    }
  } catch (err) {
    console.error('Load dataset preview error', err)
    alert('Error loading dataset: ' + err.message)
  }
}

async function markDone() {
  try {
    // Mark the session instrument as done
    const session = sessionManager.getActiveSession()
    if (!session) {
      alert('No active session.')
      return
    }
    const instrument = route.query.instrument || 'money-market'
    // Update session instrumentData
    if (!session.instrumentData) session.instrumentData = {}
    session.instrumentData[instrument] = {
      ...session.instrumentData[instrument],
      completed: true,
      timestamp: new Date().toISOString()
    }
    sessionManager.updateSession(session.id, { instrumentData: session.instrumentData })
    alert(`Marked ${instrument} as done in session.`)
    router.push('/dashboard')
  } catch (err) {
    console.error(err)
    alert('Error marking done: ' + err.message)
  }
}

function goBack() {
  router.back()
}

onMounted(() => {
  // If session and instrument are in query, auto-load
  if (route.query.session && route.query.instrument) {
    loadDatasetPreview()
  } else {
    generatePreview()
  }
})
</script>

<style scoped>
/* same as original – keep your styles */
.reports-page { padding: 30px; max-width: 1200px; margin: 0 auto; }
.page-header { margin-bottom: 30px; }
.back-btn { background: transparent; border: none; color: #0B2044; cursor: pointer; display: flex; align-items: center; gap: 8px; padding: 8px 16px; border-radius: 8px; margin-bottom: 20px; }
.page-header h1 { color: #0B2044; font-size: 28px; font-weight: 700; }
.page-header p { color: #666; font-size: 14px; }
.report-options { display: grid; grid-template-columns: repeat(2, 1fr); gap: 24px; margin-bottom: 40px; }
.option-card { background: white; border-radius: 16px; padding: 30px; text-align: center; cursor: pointer; transition: all 0.3s; border: 2px solid transparent; }
.option-card:hover { transform: translateY(-5px); box-shadow: 0 8px 25px rgba(0,0,0,0.1); border-color: #0B2044; }
.option-icon { width: 80px; height: 80px; background: #f5f5f5; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 20px; transition: all 0.3s; }
.option-icon.active { background: #0B2044; color: white; }
.option-card h3 { color: #0B2044; margin-bottom: 10px; }
.option-card p { color: #666; font-size: 13px; }
.preview-section { background: white; border-radius: 16px; padding: 24px; }
.preview-section h3 { color: #0B2044; margin-bottom: 20px; }
.preview-content { background: #f5f5f5; border-radius: 8px; padding: 20px; overflow-x: auto; margin-bottom: 20px; }
.preview-content pre { margin: 0; font-size: 12px; }
.btn-primary { background: linear-gradient(135deg, #0B2044, #1E88E5); color: white; border: none; padding: 12px 28px; border-radius: 10px; font-size: 14px; font-weight: 600; cursor: pointer; display: inline-flex; align-items: center; gap: 8px; }
.download-row { display: flex; gap: 12px; flex-wrap: wrap; }
.btn-secondary { background: #1E88E5; color: white; border: none; padding: 12px 28px; border-radius: 10px; font-size: 14px; font-weight: 600; cursor: pointer; display: inline-flex; align-items: center; gap: 8px; }
.dataset-preview { background: white; border-radius: 16px; padding: 24px; margin-bottom: 24px; }
.dataset-info-row { display: flex; gap: 24px; margin-bottom: 16px; }
.preview-empty { padding: 40px; text-align: center; color: #999; }
</style>