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
          <button class="btn-primary" @click="downloadReport()">
            <v-icon>mdi-download</v-icon> Download
          </button>
        </div>
      </div>
    </div>
  </div>

  <v-snackbar
    v-model="snackbar.show"
    :color="snackbar.color"
    :timeout="snackbar.timeout"
    location="bottom"
  >
    {{ snackbar.message }}
  </v-snackbar>
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
import { Document, Packer, Paragraph, TextRun, ImageRun } from 'docx'
import { saveAs } from 'file-saver'
import html2canvas from 'html2canvas'
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

const snackbar = ref({
  show: false,
  message: '',
  color: 'error',
  timeout: 4000
})

function showSnackbar(message, color = 'error', timeout = 4000) {
  snackbar.value = { show: true, message, color, timeout }
}

const ALL_INSTRUMENTS = ['money-market', 'bonds', 'tbills']
const PORTFOLIO_SNAPSHOT_KEY = '__portfolio_summary__'

async function fetchImageAsBase64(url) {
  try {
    const response = await fetch(url)
    if (!response.ok) return null
    const blob = await response.blob()
    return new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.onloadend = () => resolve(reader.result)
      reader.onerror = reject
      reader.readAsDataURL(blob)
    })
  } catch (e) {
    return null
  }
}

async function resolveSession() {
  const querySid = route.query.session ? String(route.query.session) : null
  if (querySid) {
    const fresh = await sessionManager.getSession(querySid, true)
    if (fresh) {
      sessionManager.setActiveSession(fresh)
      return fresh
    }
  }
  let session = sessionManager.getActiveSession()
  if (!session) {
    const sid = sessionManager.getActiveSessionId()
    if (sid) {
      session = await sessionManager.getSession(sid, true)
      if (session) sessionManager.setActiveSession(session)
    }
  } else {
    const refreshed = await sessionManager.getSession(session.id, true)
    if (refreshed) {
      session = refreshed
      sessionManager.setActiveSession(refreshed)
    }
  }
  return session
}

function resolveValuationDate(session) {
  if (session) {
    if (session.valuationDate) return session.valuationDate
    if (session.valuation_date) return session.valuation_date
  }
  try {
    return (
      sessionStorage.getItem('valuationDate') ||
      sessionStorage.getItem('valuation_date') ||
      localStorage.getItem('valuationDate') ||
      localStorage.getItem('valuation_date') ||
      null
    )
  } catch (e) {
    return null
  }
}

function resolveCurrency(session) {
  if (session) {
    if (session.currency) return session.currency
    if (session.currencyCode) return session.currencyCode
  }
  try {
    return (
      sessionStorage.getItem('currency') ||
      localStorage.getItem('currency') ||
      null
    )
  } catch (e) {
    return null
  }
}

function resolveCountry(session) {
  if (session) {
    if (session.country) return session.country
  }
  try {
    return (
      sessionStorage.getItem('country') ||
      localStorage.getItem('country') ||
      null
    )
  } catch (e) {
    return null
  }
}

function getRequestedInstruments() {
  const many = route.query.instruments
  if (many) {
    const list = String(many)
      .split(',')
      .map(s => s.trim())
      .filter(Boolean)
    if (list.length) return list
  }
  const one = route.query.instrument
  if (one) return [String(one).trim()]
  return [...ALL_INSTRUMENTS]
}

async function loadSummaryData(sessionId, instrumentType) {
  try {
    const snapshot = await sessionManager.getWorksheetData(sessionId, PORTFOLIO_SNAPSHOT_KEY)
    if (snapshot && Array.isArray(snapshot.instrumentsWithDetails)) {
      const match = snapshot.instrumentsWithDetails.find(i => i.id === instrumentType)
      if (match && Array.isArray(match.details) && match.details.length) {
        return { rows: match.details, columns: match.detailHeaders || [] }
      }
    }
  } catch (e) {
    console.warn('Portfolio snapshot read failed, falling back to workflow:', e)
  }

  const wf = await sessionManager.getInstrumentWorkflow(sessionId, instrumentType)
  if (!wf) return null

  if (wf.instrumentSummary && wf.instrumentSummary.rows && wf.instrumentSummary.rows.length) {
    return wf.instrumentSummary
  }

  if (wf.completedInstrumentSummary && wf.completedInstrumentSummary.rows && wf.completedInstrumentSummary.rows.length) {
    return wf.completedInstrumentSummary
  }

  if (wf.portfolioSummary && wf.portfolioSummary.rows && wf.portfolioSummary.rows.length) {
    return wf.portfolioSummary
  }

  if (wf.completedPortfolioSummary && wf.completedPortfolioSummary.rows && wf.completedPortfolioSummary.rows.length) {
    return wf.completedPortfolioSummary
  }

  try {
    const response = await api.calculationsAPI.getInstrumentSummary(sessionId, instrumentType)
    if (response?.success && response?.data?.rows?.length) return response.data
  } catch (err) {
    console.error('Failed to load instrument summary from backend:', err)
  }

  return null
}

async function loadFredDataFromSession(sessionId, instrumentType) {
  try {
    const wf = await sessionManager.getInstrumentWorkflow(sessionId, instrumentType)
    if (wf && wf.fredFilters && wf.yieldCurveData && wf.yieldCurveData.length > 0) {
      return { fredFilters: wf.fredFilters, yieldCurveData: wf.yieldCurveData }
    }
  } catch (e) {
    console.warn('Could not load Fred data from session:', e)
  }

  try {
    const session = await resolveSession()
    const country = resolveCountry(session)
    const currency = resolveCurrency(session)

    const response = await fetch('http://localhost:5000/api/fred/yield-curve', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        instrument_type: instrumentType,
        country: country,
        currency: currency,
        maturity: null
      })
    })
    const data = await response.json()
    if (data && data.rates && data.rates.length > 0) {
      const points = data.rates.map((rate, idx) => ({
        maturity: data.maturities?.[idx] || idx,
        rate: rate
      }))
      return {
        fredFilters: { country: country, currency: currency, maturity: null },
        yieldCurveData: points
      }
    }
  } catch (e) {
    console.warn('Failed to fetch yield curve from FRED API:', e)
  }

  return { fredFilters: { country: null, currency: null, maturity: null }, yieldCurveData: [] }
}

async function loadDatasetPreview() {
  showDatasetPreview.value = true
  try {
    const session = await resolveSession()
    if (!session) return
    const requested = getRequestedInstruments()
    const primary = requested[0] || null
    if (!primary) return
    const summary = await loadSummaryData(session.id, primary)
    let data = []
    if (summary && summary.rows && summary.rows.length) {
      data = summary.rows
    }
    if (data.length) {
      dataset.value = {
        name: `${primary} dataset (summary)`,
        instrument_type: primary,
        data: data
      }
    }
    await generatePreview()
  } catch (err) {
    console.error('Load dataset preview error', err)
    showSnackbar('Error loading dataset: ' + err.message, 'error')
  }
}

function handleDatasetUpdate(updatedData) {
  if (dataset.value) {
    dataset.value = { ...dataset.value, data: updatedData }
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
    previewData.value = {
      type: 'Empty',
      session: 'N/A',
      allWorkedData: {},
      yieldCurveData: [],
      fredFilters: { country: null, currency: null, maturity: null }
    }
    reportHtml.value = '<p>No active session found. Open a session from the Dashboard first.</p>'
    return
  }
  sessionName.value = session.name || 'Current Session'

  const requested = getRequestedInstruments()
  const primary = requested[0] || null

  const allWorkedData = {}
  const missingInstruments = []

  for (const inst of requested) {
    const summary = await loadSummaryData(session.id, inst)
    if (summary && summary.rows && summary.rows.length) {
      allWorkedData[inst] = summary.rows
    } else {
      missingInstruments.push(inst)
    }
  }

  const currentData = primary && allWorkedData[primary] ? allWorkedData[primary] : []

  const fredData = await loadFredDataFromSession(session.id, primary)
  const valuationDate = resolveValuationDate(session)

  const preview = {
    type: selectedType.value === 'current' ? 'Current Instrument Report' : 'Full Session Report',
    date: new Date().toLocaleString(),
    session: session.name || 'Current Session',
    instrument: primary,
    requestedInstruments: requested,
    missingInstruments: missingInstruments,
    rows: currentData.length,
    columns: currentData.length ? Object.keys(currentData[0]).length : 0,
    sample: currentData.slice(0, 3),
    valuationDate: valuationDate,
    totalValue: currentData.reduce((s, r) => s + (parseFloat(r['Total Value'] || r['Calculated Value'] || 0)), 0),
    allWorkedData: allWorkedData,
    fredFilters: fredData.fredFilters,
    yieldCurveData: fredData.yieldCurveData
  }

  if (selectedType.value === 'session') {
    const allData = {}
    for (const inst of requested) {
      const rows = allWorkedData[inst] || []
      if (rows.length) allData[inst] = rows
    }
    preview.instruments = allData
    preview.totalRows = Object.values(allData).reduce((sum, arr) => sum + arr.length, 0)
    preview.totalValue = Object.values(allData).reduce((sum, arr) => sum + arr.reduce((s, r) => s + (parseFloat(r['Total Value'] || r['Calculated Value'] || 0)), 0), 0)
  }

  previewData.value = preview

  if (missingInstruments.length > 0 && missingInstruments.length < requested.length) {
    reportError.value = `No calculation results found for: ${missingInstruments.join(', ')}. Those instruments were excluded from the report.`
  } else if (missingInstruments.length === requested.length) {
    reportError.value = 'No calculation results available yet. Run calculations on the instruments you want to include first.'
  } else {
    reportError.value = ''
  }

  const data = previewData.value
  const reportTitleName = selectedType.value === 'session'
    ? (data.session || 'Full Session')
    : (data.instrument || 'unknown')

  const date = data.date || new Date().toLocaleString()
  const valuationDateFinal = data.valuationDate

  let fullData = []
  if (selectedType.value === 'session' && data.instruments) {
    for (const [, rows] of Object.entries(data.instruments)) {
      if (rows && rows.length) fullData = fullData.concat(rows)
    }
  } else {
    if (data.allWorkedData && data.instrument && data.allWorkedData[data.instrument]) {
      fullData = data.allWorkedData[data.instrument]
    } else if (data.sample) {
      fullData = data.sample
    }
  }

  if (!fullData.length) {
    const msg = missingInstruments.length > 0
      ? `No calculation results were available for: ${missingInstruments.join(', ')}. Please run calculations on those instruments first.`
      : 'No data available for report. Please run calculations first.'
    reportHtml.value = `<div style="padding:32px;font-family:Arial,sans-serif;color:#333;">
      <h2 style="color:#0B2044;">No Report Data</h2>
      <p>${msg}</p>
      <p style="color:#666;font-size:13px;">Session: <strong>${session.name || 'N/A'}</strong></p>
      <p style="color:#666;font-size:13px;">Requested instruments: ${requested.join(', ')}</p>
    </div>`
    return
  }

  let chartImage = data.chartImage || ''
  if (!chartImage) {
    try {
      const canvas = document.querySelector('.chart-container--fred canvas')
      if (canvas && canvas.toDataURL) {
        chartImage = canvas.toDataURL('image/png', 1.0)
      }
    } catch (e) {
      console.warn('Could not capture chart:', e)
    }
  }

  reportHtml.value = generateReportHtml(
    fullData,
    reportTitleName,
    session.name || 'Current Session',
    date,
    valuationDateFinal,
    chartImage,
    data.fredFilters || null,
    data.yieldCurveData || [],
    data.allWorkedData || {},
    {}
  )
}

function formatForExcel(value, type = 'number', key = '') {
  if (value === null || value === undefined || value === '') return ''
  const num = parseFloat(value)
  if (isNaN(num)) return value

  const isTimeField = key.toLowerCase().includes('day') || key.toLowerCase().includes('maturity') || key.toLowerCase().includes('duration') || key.toLowerCase().includes('term')
  if (isTimeField) return Math.round(num)

  if (type === 'percentage') return Math.round(num * 10) / 10
  if (type === 'money') return Math.round(num * 100) / 100
  return num
}

function formatRowForExcel(row) {
  const formatted = {}
  for (const [key, value] of Object.entries(row)) {
    const lc = key.toLowerCase()
    if (lc.includes('rate') || lc.includes('yield') || lc.includes('coupon') || lc.includes('discount')) {
      formatted[key] = formatForExcel(value, 'percentage', key)
    } else if (lc.includes('value') || lc.includes('price') || lc.includes('amount') || lc.includes('principal') || lc.includes('interest')) {
      formatted[key] = formatForExcel(value, 'money', key)
    } else {
      formatted[key] = formatForExcel(value, 'number', key)
    }
  }
  return formatted
}

async function downloadReport() {
  if (!previewData.value || !reportHtml.value) {
    showSnackbar('No report preview available to export.', 'warning')
    return
  }

  const data = previewData.value

  try {
    const session = await resolveSession()
    if (!session) return

    const filenameSuffix = data.valuationDate ? `-${data.valuationDate}` : ''

    const endpoint = 'http://localhost:5000/api/report/generate-word'

    const requested = Array.isArray(data.requestedInstruments) ? data.requestedInstruments : []
    const instrumentTypeParam = requested.length > 1
      ? requested.join(',')
      : (requested[0] || null)

    const response = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: session.id,
        report_html: reportHtml.value,
        instrument_type: instrumentTypeParam,
        file_name: `Dura-Capital-Valuation-Report${filenameSuffix}.docx`
      })
    })

    const result = await response.json()

    if (!result.success) {
      showSnackbar(
        `Failed to generate Word report: ` + (result.message || 'Unknown error'),
        'error'
      )
      return
    }

    const downloadPath = `http://localhost:5000/api/report/download-word/${session.id}`

    const downloadResponse = await fetch(downloadPath)
    if (!downloadResponse.ok) {
      showSnackbar('Failed to download the generated report.', 'error')
      return
    }

    const blob = await downloadResponse.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download =
      result.data?.file_name ||
      `Dura-Capital-Valuation-Report${filenameSuffix}.docx`
    a.click()
    URL.revokeObjectURL(url)
  } catch (err) {
    console.error('Error downloading Word report:', err)
    showSnackbar('Error downloading Word report: ' + err.message, 'error')
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
    if (!session) return
    await markStepCompleted(String(session.id), 'reports')
    router.push('/dashboard')
  } catch (err) {
    console.error(err)
    showSnackbar('Error marking done: ' + err.message, 'error')
  }
}

onMounted(async () => {
  if (route.query.session) {
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