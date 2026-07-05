<template>
  <FixedLayout>
    <div class="reports-page">
      <div class="page-header">
        <button class="back-btn" @click="goBack">
          <v-icon>mdi-arrow-left</v-icon> Back
        </button>
        <h1>Generate Report</h1>
        <p>Select report type and generate detailed analysis with appendix</p>
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
        <v-btn color="#4CAF50" @click="downloadFullReport">
          <v-icon left>mdi-download</v-icon> Download Full Report (HTML)
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
        
        <!-- Dynamic Visualizations -->
        <div class="visualizations-section" v-if="previewData.allWorkedData">
          <h4>📊 Data Visualizations</h4>
          <div class="viz-grid">
            <div class="viz-card" v-for="(data, key) in previewData.allWorkedData" :key="key">
              <h5>{{ formatInstrumentName(key) }}</h5>
              <div class="viz-stats">
                <div class="stat">
                  <span class="stat-label">Records:</span>
                  <span class="stat-value">{{ Array.isArray(data) ? data.length : (data.rows?.length || 0) }}</span>
                </div>
                <div class="stat" v-if="Array.isArray(data) && data.length">
                  <span class="stat-label">Total Value:</span>
                  <span class="stat-value">{{ formatCurrency(data.reduce((s, r) => s + (parseFloat(r.FaceValue || r.Amount || r.Principal || 0)), 0)) }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
        
        <div class="preview-content">
          <pre>{{ JSON.stringify(previewData, null, 2) }}</pre>
        </div>
        <div class="download-row">
          <button class="btn-primary" @click="downloadFullReport">
            <v-icon>mdi-download</v-icon> Download Full Report (HTML)
          </button>
          <button class="btn-secondary" @click="downloadReport('json')">
            <v-icon>mdi-code-json</v-icon> Download JSON
          </button>
          <button class="btn-secondary" @click="downloadReport('excel')">
            <v-icon>mdi-file-excel</v-icon> Download Excel
          </button>
          <button class="btn-secondary" @click="downloadReport('pdf')">
            <v-icon>mdi-file-pdf</v-icon> Download PDF
          </button>
          <button class="btn-secondary" @click="downloadReport('word')">
            <v-icon>mdi-file-word</v-icon> Download Word
          </button>
          <button class="btn-secondary" @click="downloadReport('csv')">
            <v-icon>mdi-file-csv</v-icon> Download CSV
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
import { markStepCompleted } from '@/utils/workflowProgress.js'
import { generateReportHtml, resolveActiveSession, loadInstrumentData } from '@/utils/generateReportHtml.js'
import * as XLSX from 'xlsx'
import jsPDF from 'jspdf'
import pdfMake from 'pdfmake'
import { Document, Packer, Paragraph, TextRun } from 'docx'
import { saveAs } from 'file-saver'

const logoUrl = '/DuraCapital logo.png'
const backgroundCoverUrl = '/reportbackground.png'

const router = useRouter()
const route = useRoute()

const selectedType = ref('current')
const previewData = ref(null)
const yieldCurveData = ref(null)
const reportError = ref('')
const dataset = ref(null)
const showDatasetPreview = ref(false)
const sessionName = ref('')

// ---- REPORT GENERATION (shared with ReportsView) ----

function selectReportType(type) {
  selectedType.value = type
  generatePreview()
}

async function generatePreview() {
  let session = resolveActiveSession(sessionManager)
  if (!session) {
    const sid = sessionManager.getActiveSessionId()
    if (sid) {
      await sessionManager.loadSessionFromDb(sid)
      session = sessionManager.getSession(sid)
    }
  }

  if (!session) {
    reportError.value = 'No active session found.'
    previewData.value = null
    return
  }

  sessionName.value = session.name || 'Current Session'
  const instrument = route.query.instrument || 'money-market'

  // Load all worked data from all instruments
  const allWorkedData = {}
  const instruments = ['money-market', 'bonds', 'tbills']
  
  for (const inst of instruments) {
    let data = []
    const wf = sessionManager.getInstrumentWorkflow(session.id, inst)
    
    // Try to get cleaned data first
    if (wf && wf.cleanedData && wf.cleanedData.length) {
      data = wf.cleanedData
    } else {
      // Fall back to raw data
      const rawKey = `${inst}_session_${session.id}_raw`
      const savedRaw = localStorage.getItem(rawKey)
      if (savedRaw) {
        try { data = JSON.parse(savedRaw) } catch(e) {}
      }
    }
    
    // Also try to get portfolio summary data
    const summaryKey = `${inst}_session_${session.id}_summary`
    const savedSummary = localStorage.getItem(summaryKey)
    if (savedSummary) {
      try {
        const summary = JSON.parse(savedSummary)
        if (summary.rows && summary.rows.length) {
          allWorkedData[`${inst}_summary`] = summary
        }
      } catch(e) {}
    }
    
    if (data.length) {
      allWorkedData[inst] = data
    }
  }

  let data = loadInstrumentData(sessionManager, session.id, instrument)

  const preview = {
    type: selectedType.value === 'current' ? 'Current Instrument Report' : 'Full Session Report',
    date: new Date().toLocaleString(),
    session: session.name || 'Current Session',
    instrument: instrument,
    rows: data.length,
    columns: data.length ? Object.keys(data[0]).length : 0,
    sample: data.slice(0, 3),
    valuationDate: new Date().toISOString().split('T')[0],
    totalValue: data.reduce((s, r) => s + (parseFloat(r.FaceValue || r.Amount || r.Principal || 0)), 0),
    allWorkedData: allWorkedData
  }

  if (selectedType.value === 'session') {
    const allData = {}
    for (const inst of instruments) {
      const rows = allWorkedData[inst] || []
      if (rows.length) allData[inst] = rows
    }
    preview.instruments = allData
    preview.totalRows = Object.values(allData).reduce((sum, arr) => sum + arr.length, 0)
    preview.totalValue = Object.values(allData).reduce((sum, arr) => sum + arr.reduce((s, r) => s + (parseFloat(r.FaceValue || r.Amount || r.Principal || 0)), 0), 0)
  }

  previewData.value = preview
  reportError.value = ''
}

function downloadFullReport() {
  if (!previewData.value) {
    alert('No report data. Please refresh the report first.')
    return
  }

  const data = previewData.value
  const instrument = data.instrument || 'unknown'
  const session = data.session || 'Current Session'
  const date = data.date || new Date().toLocaleString()
  const valuationDate = data.valuationDate || new Date().toISOString().split('T')[0]

  let fullData = []
  if (selectedType.value === 'session' && data.instruments) {
    for (const [inst, rows] of Object.entries(data.instruments)) {
      if (rows && rows.length) {
        fullData = fullData.concat(rows)
      }
    }
  } else {
    const sessionId = route.query.session
    if (sessionId) {
      const wf = sessionManager.getInstrumentWorkflow(sessionId, instrument)
      if (wf && wf.cleanedData && wf.cleanedData.length) {
        fullData = wf.cleanedData
      } else {
        const rawKey = `${instrument}_session_${sessionId}_raw`
        const savedRaw = localStorage.getItem(rawKey)
        if (savedRaw) {
          try { fullData = JSON.parse(savedRaw) } catch(e) {}
        }
      }
    }
  }

  if (!fullData.length) {
    alert('No data available for the report.')
    return
  }

  const html = generateReportHtml(fullData, instrument, session, date, valuationDate)
  const blob = new Blob([html], { type: 'text/html' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `Dura-Capital-Valuation-Report-${new Date().toISOString().split('T')[0]}.html`
  a.click()
  URL.revokeObjectURL(url)
}

function downloadReport(format = 'json') {
  if (!previewData.value) {
    alert('No report data available.')
    return
  }

  const data = previewData.value
  const filename = `report_${Date.now()}`

  if (format === 'json') {
    const blob = new Blob([JSON.stringify({ ...data, yieldCurve: yieldCurveData.value }, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${filename}.json`
    a.click()
    URL.revokeObjectURL(url)
    return
  }

  if (format === 'excel') {
    const workbook = XLSX.utils.book_new()
    const worksheet = XLSX.utils.json_to_sheet(data.allWorkedData || {})
    XLSX.utils.book_append_sheet(workbook, worksheet, 'Report')
    XLSX.writeFile(workbook, `${filename}.xlsx`)
    return
  }

  if (format === 'csv') {
    const worksheet = XLSX.utils.json_to_sheet(data.allWorkedData || {})
    const csv = XLSX.utils.sheet_to_csv(worksheet)
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${filename}.csv`
    a.click()
    URL.revokeObjectURL(url)
    return
  }

  if (format === 'pdf') {
    const doc = new jsPDF()
    doc.setFontSize(16)
    doc.text('Dura Capital Valuation Report', 20, 20)
    doc.setFontSize(12)
    doc.text(`Date: ${data.date}`, 20, 30)
    doc.text(`Session: ${data.session}`, 20, 40)
    doc.text(`Instrument: ${data.instrument}`, 20, 50)
    doc.text(`Total Records: ${data.rows}`, 20, 60)
    doc.text(`Total Value: ${formatCurrency(data.totalValue)}`, 20, 70)
    doc.save(`${filename}.pdf`)
    return
  }

  if (format === 'word') {
    const doc = new Document({
      sections: [{
        properties: {},
        children: [
          new Paragraph({
            children: [new TextRun({ text: 'Dura Capital Valuation Report', bold: true, size: 32 })]
          }),
          new Paragraph({ text: `Date: ${data.date}` }),
          new Paragraph({ text: `Session: ${data.session}` }),
          new Paragraph({ text: `Instrument: ${data.instrument}` }),
          new Paragraph({ text: `Total Records: ${data.rows}` }),
          new Paragraph({ text: `Total Value: ${formatCurrency(data.totalValue)}` })
        ]
      }]
    })
    Packer.toBlob(doc).then(blob => {
      saveAs(blob, `${filename}.docx`)
    })
    return
  }
}

function formatInstrumentName(key) {
  const names = {
    'money-market': 'Money Market',
    'bonds': 'Bonds',
    'tbills': 'Treasury Bills',
    'money-market_summary': 'Money Market Summary',
    'bonds_summary': 'Bonds Summary',
    'tbills_summary': 'Treasury Bills Summary'
  }
  return names[key] || key
}

function formatCurrency(value) {
  if (typeof value !== 'number') return '$0.00'
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value)
}

function handleDatasetUpdate(updatedData) {
  if (!dataset.value) return
  dataset.value.data = updatedData
}

async function loadDatasetPreview() {
  showDatasetPreview.value = true
  try {
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
    const wf = sessionManager.getInstrumentWorkflow(session.id, instrument)
    if (wf && wf.cleanedData && wf.cleanedData.length) {
      data = wf.cleanedData
    } else {
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
    const session = sessionManager.getActiveSession()
    if (!session) {
      alert('No active session.')
      return
    }
    const instrument = route.query.instrument || 'money-market'
    if (!session.instrumentData) session.instrumentData = {}
    session.instrumentData[instrument] = {
      ...session.instrumentData[instrument],
      completed: true,
      timestamp: new Date().toISOString()
    }
    await sessionManager.updateSession(session.id, { instrumentData: session.instrumentData })
    try { if (session && session.id) await markStepCompleted(String(session.id), 'reports') } catch (e) { console.error(e) }
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
  if (route.query.session && route.query.instrument) {
    loadDatasetPreview()
  } else {
    generatePreview()
  }
})
</script>

<style scoped>
.reports-page { padding: 30px; max-width: 1200px; margin: 0 auto; }
.page-header { margin-bottom: 30px; }
.back-btn { background: transparent; border: none; color: #0B2044; cursor: pointer; display: flex; align-items: center; gap: 8px; padding: 8px 16px; border-radius: 8px; margin-bottom: 20px; }
.page-header h1 { color: #0B2044; font-size: 28px; font-weight: 700; }
.page-header p { color: #666; font-size: 14px; }
.report-actions-row { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 20px; }
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