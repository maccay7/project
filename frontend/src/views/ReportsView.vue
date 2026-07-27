<template>
  <div class="reports-view-fullscreen" v-if="showFullscreenReport">
    <button class="close-fullscreen-btn" @click="showFullscreenReport = false">
      <v-icon>mdi-close</v-icon> Close Report
    </button>
    <iframe :srcdoc="reportHtml" frameborder="0" class="fullscreen-iframe"></iframe>
  </div>
  <div v-else class="reports-view-no-nav">
    <div class="reports-view">
      <div class="page-header">
        <h1>Generate Report</h1>
        <p>Select report type and generate detailed analysis with appendix</p>
      </div>

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
        <v-btn color="#4CAF50" @click="downloadFullReport">
          <v-icon left>mdi-download</v-icon> Download Full Report (HTML)
        </v-btn>
        <v-btn color="#9C27B0" @click="showFullscreenReport = true" v-if="reportHtml">
          <v-icon left>mdi-fullscreen</v-icon> View Fullscreen
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
        <v-alert v-if="reportError" type="warning" density="compact" class="mb-3">{{ reportError }}</v-alert>
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
        <div class="report-preview-iframe-wrapper" v-if="reportHtml">
          <iframe :srcdoc="reportHtml" frameborder="0" style="width:100%; height:70vh; border-radius:8px; border:1px solid #e0e0e0;"></iframe>
        </div>
        <div v-else class="preview-empty">
          <p>No report generated yet. Click "Refresh Report" to generate.</p>
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
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
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
const showFullscreenReport = ref(false)

// ===== Helper Functions =====
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

async function loadSummaryData(sessionId, instrumentType) {
  try {
    const response = await api.calculationsAPI.getInstrumentSummary(sessionId, instrumentType)
    if (response?.success && response?.data) return response.data
  } catch (err) {
    console.error('Failed to load instrument summary from backend:', err)
  }
  const summaryKey = `${instrumentType}_session_${sessionId}_summary`
  const saved = localStorage.getItem(summaryKey)
  if (saved) {
    try {
      const summary = JSON.parse(saved)
      if (summary.rows && summary.rows.length) return summary
    } catch (e) {}
  }
  const wf = await sessionManager.getInstrumentWorkflow(sessionId, instrumentType)
  if (wf && wf.cleanedData && wf.cleanedData.length) {
    return { rows: wf.cleanedData, columns: Object.keys(wf.cleanedData[0] || {}) }
  }
  if (wf && wf.data && wf.data.length) {
    return { rows: wf.data, columns: Object.keys(wf.data[0] || {}) }
  }
  return null
}

// ===== LOAD FRED DATA FROM SESSION =====
async function loadFredDataFromSession(sessionId, instrumentType) {
  try {
    console.log('Loading FRED data from session:', { sessionId, instrumentType })
    const wf = await sessionManager.getInstrumentWorkflow(sessionId, instrumentType)
    console.log('Workflow data:', wf)
    if (wf) {
      console.log('FRED filters from workflow:', wf.fredFilters)
      console.log('Yield curve data from workflow:', wf.yieldCurveData)
      console.log('Yield curve data length:', wf.yieldCurveData?.length || 0)
      // Return immediately if data exists in workflow
      if (wf.fredFilters && wf.yieldCurveData && wf.yieldCurveData.length > 0) {
        console.log('Returning cached FRED data from workflow')
        return {
          fredFilters: wf.fredFilters,
          yieldCurveData: wf.yieldCurveData
        }
      }
    } else {
      console.warn('No workflow data found for instrument type:', instrumentType)
    }
  } catch (e) {
    console.warn('Could not load Fred data from session:', e)
  }
  console.log('Returning default FRED data')
  return { fredFilters: { country: 'US', currency: 'USD', maturity: '1Y' }, yieldCurveData: [] }
}

// ===== Load Dataset Preview =====
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

// ===== Generate Preview =====
async function generatePreview() {
  const session = await resolveSession()
  if (!session) {
    reportError.value = 'No active session found.'
    previewData.value = null
    return
  }
  sessionName.value = session.name || 'Current Session'
  const instrument = route.query.instrument || 'money-market'
  const allWorkedData = {}
  const instruments = ['money-market', 'bonds', 'tbills']
  for (const inst of instruments) {
    const summary = await loadSummaryData(session.id, inst)
    if (summary && summary.rows && summary.rows.length) {
      allWorkedData[inst] = summary.rows
    }
  }
  let currentData = []
  const currentSummary = await loadSummaryData(session.id, instrument)
  if (currentSummary && currentSummary.rows && currentSummary.rows.length) {
    currentData = currentSummary.rows
  }

  // 🔥 Load FRED data from session
  const fredData = await loadFredDataFromSession(session.id, instrument)

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
    allWorkedData: allWorkedData,
    fredFilters: fredData.fredFilters,
    yieldCurveData: fredData.yieldCurveData
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

  // Generate HTML
  if (previewData.value) {
    const data = previewData.value
    const instrumentName = data.instrument || 'unknown'
    const sessionName = data.session || 'Current Session'
    const date = data.date || new Date().toLocaleString()
    const valuationDate = data.valuationDate || new Date().toISOString().split('T')[0]
    let fullData = []
    if (selectedType.value === 'session' && data.instruments) {
      for (const [inst, rows] of Object.entries(data.instruments)) {
        if (rows && rows.length) fullData = fullData.concat(rows)
      }
    } else {
      if (data.allWorkedData && data.allWorkedData[instrument]) {
        fullData = data.allWorkedData[instrument]
      } else if (data.sample) {
        fullData = data.sample
      }
    }
    if (fullData.length) {
      let chartImage = data.chartImage || ''
      if (!chartImage) {
        try {
          console.log('Attempting to capture chart from DOM...')
          const canvas = document.querySelector('.chart-container--fred canvas')
          if (canvas && canvas.toDataURL) {
            chartImage = canvas.toDataURL('image/png', 1.0)
            console.log('Chart captured from DOM:', chartImage ? 'success' : 'failed')
          } else {
            console.warn('No canvas found in DOM for chart capture')
          }
        } catch (e) {
          console.warn('Could not capture chart:', e)
        }
      }
      console.log('Using chart image for report:', chartImage ? 'yes' : 'no')
      reportHtml.value = generateReportHtml(
        fullData,
        instrumentName,
        sessionName,
        date,
        valuationDate,
        chartImage,
        data.fredFilters || { country: 'US', currency: 'USD', maturity: '1Y' },
        data.yieldCurveData || [],
        data.allWorkedData || {}
      )
    } else {
      reportHtml.value = '<p>No data available for report. Please run calculations first.</p>'
    }
  }
}

// ===== Download Full Report =====
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
      if (rows && rows.length) fullData = fullData.concat(rows)
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
  const html = generateReportHtml(
    fullData,
    instrument,
    session,
    date,
    valuationDate,
    '',
    data.fredFilters || { country: 'US', currency: 'USD', maturity: '1Y' },
    data.yieldCurveData || [],
    data.allWorkedData || {}
  )
  const blob = new Blob([html], { type: 'text/html' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `Dura-Capital-Valuation-Report-${new Date().toISOString().split('T')[0]}.html`
  a.click()
  URL.revokeObjectURL(url)
}

// ===== Other helper functions =====
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
    return Math.round(num * 10) / 10
  } else if (type === 'money') {
    return Math.round(num * 100) / 100
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
    // Use the HTML report for PDF to preserve formatting
    const htmlContent = reportHtml.value
    if (!htmlContent) {
      alert('No report content available. Please generate the report first.')
      return
    }
    
    // Create a print window to generate PDF
    const printWindow = window.open('', '_blank')
    printWindow.document.write(htmlContent)
    printWindow.document.close()
    printWindow.focus()
    setTimeout(() => {
      printWindow.print()
    }, 500)
    return
  }

  if (format === 'word') {
    // Use the HTML report for Word to preserve formatting
    const htmlContent = reportHtml.value
    if (!htmlContent) {
      alert('No report content available. Please generate the report first.')
      return
    }
    
    // Create HTML blob with Word MIME type
    const htmlWithWordHeader = `
      <html xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:w="urn:schemas-microsoft-com:office:word">
      <head><meta charset="utf-8"><title>Report</title></head>
      <body>${htmlContent}</body>
      </html>
    `
    const blob = new Blob(['\ufeff', htmlWithWordHeader], { type: 'application/msword' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${filename}.doc`
    a.click()
    URL.revokeObjectURL(url)
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

onMounted(async () => {
  if (route.query.session && route.query.instrument) {
    await loadDatasetPreview()
  } else {
    await generatePreview()
  }
})
</script>

<style scoped>
.reports-view-no-nav { min-height: 100vh; background: #f5f7fa; padding-top: 20px; }
.reports-view { padding: 30px; max-width: 1200px; margin: 0 auto; }
.page-header { margin-bottom: 30px; }
.back-btn { background: transparent; border: none; color: #0B2044; cursor: pointer; display: flex; align-items: center; gap: 8px; padding: 8px 16px; border-radius: 8px; margin-bottom: 20px; }
.page-header h1 { color: #0B2044; font-size: 28px; font-weight: 700; }
.page-header p { color: #666; font-size: 14px; }
.report-actions-row { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 20px; }
.report-options { display: grid; grid-template-columns: repeat(2, 1fr); gap: 24px; margin-bottom: 40px; }
.option-card { background: white; border-radius: 16px; padding: 30px; text-align: center; cursor: pointer; transition: all 0.3s; border: 2px solid transparent; }
.option-card:hover { transform: translateY(-5px); box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1); border-color: #0B2044; }
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
.report-preview-iframe-wrapper { margin: 16px 0; border-radius: 8px; overflow: hidden; border: 1px solid #e0e0e0; background: white; }
.reports-view-fullscreen { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: white; z-index: 2000; }
.close-fullscreen-btn { position: fixed; top: 20px; right: 20px; z-index: 2001; background: #0B2044; color: white; border: none; padding: 12px 24px; border-radius: 8px; cursor: pointer; display: flex; align-items: center; gap: 8px; font-size: 14px; font-weight: 600; box-shadow: 0 4px 12px rgba(0,0,0,0.3); }
.close-fullscreen-btn:hover { background: #1E88E5; }
.fullscreen-iframe { width: 100%; height: 100%; border: none; }
</style>