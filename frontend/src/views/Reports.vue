<template>
  <FixedLayout>
    <div class="reports-view">
      <!-- Header -->
      <div class="page-header">
        <h1>Generate Report</h1>
        <p>Select report type and generate detailed analysis with appendix</p>
      </div>

      <!-- Action Buttons -->
      <div class="action-buttons">
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

      <!-- Report Options -->
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

      <!-- Dataset Preview -->
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

      <!-- Report Preview -->
      <div class="preview-section" v-if="previewData">
        <h3>Report Preview</h3>
        <v-alert v-if="reportError" type="warning" density="compact" class="mb-3">{{ reportError }}</v-alert>
        
        <!-- Data Visualizations -->
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
                  <span class="stat-value">{{ formatCurrency(data.reduce((s, r) => s + (parseFloat(r['Total Value'] || r['Calculated Value'] || 0)), 0)) }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
        
        <!-- Preview Content (only the report itself, no extra headers) -->
        <div class="preview-content" v-html="reportHtml" v-if="reportHtml"></div>
        <div v-else class="preview-empty">
          <p>No report generated yet. Click "Refresh Report" to generate.</p>
        </div>
        
        <!-- Download Row -->
        <div class="download-row">
          <button class="btn-primary" @click="downloadReport('word')">
            <v-icon>mdi-download</v-icon> Download
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
import sessionManager from '@/services/sessionManager.js'
import { markStepCompleted } from '@/utils/workflowProgress.js'
import { generateReportHtml } from '@/utils/generateReportHtml.js'
import * as XLSX from 'xlsx'
import jsPDF from 'jspdf'
import { Document, Packer, Paragraph, TextRun } from 'docx'
import { saveAs } from 'file-saver'
import api from '@/services/api.js'

const router = useRouter()
const route = useRoute()

const selectedType = ref('current')
const previewData = ref(null)
const reportError = ref('')
const dataset = ref(null)
const showDatasetPreview = ref(false)
const sessionName = ref('')
const reportHtml = ref('')

// Helper: resolve active session
async function resolveSession() {
  let session = sessionManager.getActiveSession()
  if (!session) {
    const sid = sessionManager.getActiveSessionId()
    if (sid) {
      await sessionManager.getSession(sid)
      session = sessionManager.getActiveSession()
    }
  }
  if (!session) {
    const all = await sessionManager.getAllSessions()
    if (all.length) session = all[0]
  }
  return session
}

// Load data from instrument summary (calculated results) - use backend as single source of truth
async function loadSummaryData(sessionId, instrumentType) {
  try {
    const response = await api.calculationsAPI.getInstrumentSummary(sessionId, instrumentType)
    if (response?.success && response?.data) {
      return response.data
    }
  } catch (err) {
    console.error('Failed to load instrument summary from backend:', err)
  }
  
  // Fallback to localStorage if backend fails
  const summaryKey = `${instrumentType}_session_${sessionId}_summary`
  const saved = localStorage.getItem(summaryKey)
  if (saved) {
    try {
      const summary = JSON.parse(saved)
      if (summary.rows && summary.rows.length) {
        return summary
      }
    } catch(e) {}
  }
  // Fallback: try to get from workflow
  const wf = await sessionManager.getInstrumentWorkflow(sessionId, instrumentType)
  if (wf && wf.cleanedData && wf.cleanedData.length) {
    return { rows: wf.cleanedData, columns: Object.keys(wf.cleanedData[0] || {}) }
  }
  if (wf && wf.data && wf.data.length) {
    return { rows: wf.data, columns: Object.keys(wf.data[0] || {}) }
  }
  return null
}

async function loadDatasetPreview() {
  showDatasetPreview.value = true
  try {
    const session = await resolveSession()
    if (!session) {
      alert('No active session found.')
      return
    }
    const instrument = route.query.instrument || 'money-market'
    const summary = await loadSummaryData(session.id, instrument)
    let data = []
    if (summary && summary.rows && summary.rows.length) {
      data = summary.rows
    }
    if (data.length) {
      dataset.value = {
        name: `${instrument} dataset (summary)`,
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

function handleDatasetUpdate(updatedData) {
  if (dataset.value) {
    dataset.value.data = updatedData
  }
}

function selectReportType(type) {
  selectedType.value = type
  generatePreview()
}

async function generatePreview() {
  const session = await resolveSession()
  if (!session) {
    reportError.value = 'No active session found.'
    previewData.value = null
    return
  }

  sessionName.value = session.name || 'Current Session'
  const instrument = route.query.instrument || 'money-market'

  // Load all summary data from all instruments
  const allWorkedData = {}
  const instruments = ['money-market', 'bonds', 'tbills']
  
  for (const inst of instruments) {
    const summary = await loadSummaryData(session.id, inst)
    if (summary && summary.rows && summary.rows.length) {
      allWorkedData[inst] = summary.rows
    }
  }

  // Get data for current instrument
  let currentData = []
  const currentSummary = await loadSummaryData(session.id, instrument)
  if (currentSummary && currentSummary.rows && currentSummary.rows.length) {
    currentData = currentSummary.rows
  }

  const preview = {
    type: selectedType.value === 'current' ? 'Current Instrument Report' : 'Full Session Report',
    date: new Date().toLocaleString(),
    session: session.name || 'Current Session',
    instrument: instrument,
    rows: currentData.length,
    columns: currentData.length ? Object.keys(currentData[0]).length : 0,
    sample: currentData.slice(0, 3),
    valuationDate: new Date().toISOString().split('T')[0],
    totalValue: currentData.reduce((s, r) => s + (parseFloat(r['Total Value'] || r['Calculated Value'] || 0)), 0),
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
    preview.totalValue = Object.values(allData).reduce((sum, arr) => arr.reduce((s, r) => s + (parseFloat(r['Total Value'] || r['Calculated Value'] || 0)), 0), 0)
  }

  previewData.value = preview
  reportError.value = ''

  // Generate HTML for report preview
  if (previewData.value) {
    const data = previewData.value
    const instrumentName = data.instrument || 'unknown'
    const sessionName = data.session || 'Current Session'
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
      if (data.allWorkedData && data.allWorkedData[instrument]) {
        fullData = data.allWorkedData[instrument]
      } else if (data.sample) {
        fullData = data.sample
      }
    }

    if (fullData.length) {
      reportHtml.value = generateReportHtml(fullData, instrumentName, sessionName, date, valuationDate)
    } else {
      reportHtml.value = '<p>No data available for report.</p>'
    }
  }
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
    if (data.allWorkedData && data.allWorkedData[instrument]) {
      fullData = data.allWorkedData[instrument]
    } else if (data.sample) {
      fullData = data.sample
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

function formatForExcel(value, type = 'number', key = '') {
  if (value === null || value === undefined || value === '') return ''
  const num = parseFloat(value)
  if (isNaN(num)) return value
  
  // Round time fields to whole numbers
  const isTimeField = key.toLowerCase().includes('day') || key.toLowerCase().includes('maturity') || key.toLowerCase().includes('duration') || key.toLowerCase().includes('term')
  if (isTimeField) {
    return Math.round(num)
  }
  
  if (type === 'percentage') {
    return Math.round(num * 10) / 10  // Round to 1 decimal place
  } else if (type === 'money') {
    return Math.round(num * 100) / 100  // Round to 2 decimal places
  }
  return num
}

function formatRowForExcel(row) {
  const formatted = {}
  for (const [key, value] of Object.entries(row)) {
    if (key.toLowerCase().includes('rate') || key.toLowerCase().includes('yield') || key.toLowerCase().includes('coupon') || key.toLowerCase().includes('discount')) {
      formatted[key] = formatForExcel(value, 'percentage', key)
    } else if (key.toLowerCase().includes('value') || key.toLowerCase().includes('price') || key.toLowerCase().includes('amount') || key.toLowerCase().includes('principal') || key.toLowerCase().includes('interest')) {
      formatted[key] = formatForExcel(value, 'money', key)
    } else {
      formatted[key] = formatForExcel(value, 'number', key)
    }
  }
  return formatted
}

function downloadReport(format = 'json') {
  if (!previewData.value) {
    alert('No report data available.')
    return
  }

  const data = previewData.value
  const filename = `report_${Date.now()}`

  if (format === 'json') {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
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
    const allData = data.allWorkedData || {}
    for (const [key, rows] of Object.entries(allData)) {
      if (rows.length) {
        const formattedRows = rows.map(row => formatRowForExcel(row))
        const sheet = XLSX.utils.json_to_sheet(formattedRows)
        XLSX.utils.book_append_sheet(workbook, sheet, key.substring(0, 31))
      }
    }
    const summary = [
      ['Report', data.type],
      ['Session', data.session],
      ['Date', data.date],
      ['Valuation Date', data.valuationDate],
      ['Total Value', formatForExcel(data.totalValue, 'money')],
      ['Instruments', data.instrument],
      ['Rows', data.rows]
    ]
    const summarySheet = XLSX.utils.aoa_to_sheet(summary)
    XLSX.utils.book_append_sheet(workbook, summarySheet, 'Summary')
    XLSX.writeFile(workbook, `${filename}.xlsx`)
    return
  }

  if (format === 'csv') {
    const allData = data.allWorkedData || {}
    const firstKey = Object.keys(allData)[0]
    if (firstKey && allData[firstKey].length) {
      const worksheet = XLSX.utils.json_to_sheet(allData[firstKey])
      const csv = XLSX.utils.sheet_to_csv(worksheet)
      const blob = new Blob([csv], { type: 'text/csv' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${filename}.csv`
      a.click()
      URL.revokeObjectURL(url)
    } else {
      alert('No data to export as CSV.')
    }
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
    'tbills': 'Treasury Bills'
  }
  return names[key] || key
}

function formatCurrency(value) {
  if (typeof value !== 'number') return '$0.00'
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value)
}

async function markDone() {
  try {
    const session = await resolveSession()
    if (!session) {
      alert('No active session.')
      return
    }
    const instrument = route.query.instrument || 'money-market'
    await markStepCompleted(session.id, 'reports')
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

onMounted(async () => {
  if (route.query.session && route.query.instrument) {
    await loadDatasetPreview()
  } else {
    await generatePreview()
  }
})
</script>

<style scoped>
.reports-view { padding: 30px; max-width: 1200px; margin: 0 auto; }
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
.viz-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 20px; }
.viz-card { background: #f8f9ff; border-radius: 8px; padding: 16px; border: 1px solid #e8ecf1; }
.viz-card h5 { margin: 0 0 8px 0; color: #0B2044; }
.viz-stats .stat { display: flex; justify-content: space-between; font-size: 13px; }
</style>