<template>
  <fixed-layout>
    <div class="reports-view">

      <!-- Header -->
      <div class="page-header">
        <h1>Report Generation</h1>
        <p>Generate professional valuation reports with appendix and methodology</p>
      </div>

      <!-- Action Buttons -->
      <div class="action-buttons">
        <v-btn color="#0B2A44" @click="loadData">
          <v-icon left>mdi-database</v-icon> Load Data
        </v-btn>
        <v-btn color="#0B2A44" variant="outlined" @click="finishAndReset">
          <v-icon left>mdi-check-circle</v-icon> Done & Reset
        </v-btn>
      </div>

      <!-- Data Overview with KPI Cards -->
      <v-card class="stats-card" v-if="hasData">
        <v-card-title class="card-title">
          <v-icon class="title-icon">mdi-file-excel</v-icon> Report Overview
        </v-card-title>
        <v-card-text>
          <v-row>
            <v-col cols="12" sm="4" v-for="stat in kpiStats" :key="stat.title">
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

      <!-- Excel Viewer -->
      <v-card class="stats-card" v-if="hasData">
        <v-card-title class="card-title">
          <v-icon class="title-icon">mdi-microsoft-excel</v-icon> Data Preview
        </v-card-title>
        <v-card-text>
          <ExcelViewer
            :data="calcData"
            :headers="dataHeaders"
            @data-update="calcData = $event"
          />
        </v-card-text>
      </v-card>

      <!-- Report Sections -->
      <v-card class="stats-card" v-if="hasData">
        <v-card-title class="card-title">
          <v-icon class="title-icon">mdi-cog</v-icon> Report Sections
        </v-card-title>
        <v-card-text>
          <div class="action-buttons small">
            <v-btn size="small" color="#0B2A44" variant="tonal" @click="selectAll">Select All</v-btn>
            <v-btn size="small" color="#0B2A44" variant="tonal" @click="clearAll">Clear</v-btn>
          </div>
          <v-row>
            <v-col cols="12" sm="4" v-for="sec in sections" :key="sec.key">
              <v-card class="section-card" :class="{ selected: sec.selected }" @click="sec.selected = !sec.selected">
                <v-card-text class="text-center">
                  <v-icon :color="sec.color" size="28">{{ sec.icon }}</v-icon>
                  <div class="section-name">{{ sec.name }}</div>
                  <div class="section-desc">{{ sec.desc }}</div>
                </v-card-text>
              </v-card>
            </v-col>
          </v-row>
        </v-card-text>
      </v-card>

      <!-- Generate Button -->
      <v-card class="stats-card" v-if="hasData">
        <v-card-title class="card-title">
          <v-icon class="title-icon">mdi-download</v-icon> Download Report
        </v-card-title>
        <v-card-text>
          <v-row>
            <v-col cols="12" sm="6" md="4">
              <v-btn color="#0B2A44" size="large" @click="downloadJSON" :loading="generating" block>
                <v-icon left>mdi-code-json</v-icon> JSON
              </v-btn>
            </v-col>
            <v-col cols="12" sm="6" md="4">
              <v-btn color="#0B2A44" size="large" @click="downloadCSV" :loading="generating" block>
                <v-icon left>mdi-file-delimited</v-icon> CSV
              </v-btn>
            </v-col>
            <v-col cols="12" sm="6" md="4">
              <v-btn color="#0B2A44" size="large" @click="downloadHTML" :loading="generating" block>
                <v-icon left>mdi-language-html5</v-icon> HTML
              </v-btn>
            </v-col>
            <v-col cols="12" sm="6" md="4">
              <v-btn color="#0B2A44" size="large" @click="downloadPDF" :loading="generating" block>
                <v-icon left>mdi-file-pdf</v-icon> PDF
              </v-btn>
            </v-col>
            <v-col cols="12" sm="6" md="4">
              <v-btn color="#0B2A44" size="large" @click="downloadWord" :loading="generating" block>
                <v-icon left>mdi-file-word</v-icon> Word
              </v-btn>
            </v-col>
            <v-col cols="12" sm="6" md="4">
              <v-btn color="#0B2A44" size="large" @click="downloadExcel" :loading="generating" block>
                <v-icon left>mdi-file-excel</v-icon> Excel
              </v-btn>
            </v-col>
          </v-row>
          <v-alert v-if="reportReady" type="success" class="mt-3">Report downloaded!</v-alert>
        </v-card-text>
      </v-card>

      <!-- No Data Message -->
      <v-card v-if="!hasData" class="stats-card">
        <v-card-text class="text-center pa-8">
          <v-icon size="64" color="#999">mdi-file-excel-off</v-icon>
          <h3 class="mt-4">No Data Loaded</h3>
          <p>Click "Load Data" to load calculation results</p>
          <v-btn color="#0B2A44" @click="loadData">Load Data</v-btn>
        </v-card-text>
      </v-card>

    </div>
  </fixed-layout>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import FixedLayout from '../components/FixedLayout.vue'
import ExcelViewer from '../components/ExcelViewer.vue'
import * as XLSX from 'xlsx'
import sessionManager from '@/services/sessionManager.js'
import { markStepCompleted } from '@/utils/workflowProgress.js'
import { generateReportHtml, resolveActiveSession, loadInstrumentData } from '@/utils/generateReportHtml.js'

const router = useRouter()
const route = useRoute()

// State
const calcData = ref([])
const instrumentType = ref('')
const sessionName = ref('')
const generating = ref(false)
const reportReady = ref(false)

// Sections
const sections = ref([
  { key: 'summary', name: 'Summary', desc: 'Key metrics', icon: 'mdi-chart-line', color: '#0B2A44', selected: true },
  { key: 'data', name: 'Data Table', desc: 'All records', icon: 'mdi-table', color: '#1E88E5', selected: true },
  { key: 'yield', name: 'Yield Analysis', desc: 'Yield statistics', icon: 'mdi-chart-timeline', color: '#4CAF50', selected: true },
  { key: 'appendix', name: 'Appendix', desc: 'Detailed instrument breakdown', icon: 'mdi-file-document', color: '#FF9800', selected: true }
])

// Computed
const hasData = computed(() => calcData.value?.length > 0)
const dataHeaders = computed(() => calcData.value.length ? Object.keys(calcData.value[0]) : [])

const kpiStats = computed(() => [
  { title: 'Records', value: calcData.value.length || 0, icon: 'mdi-database', color: 'rgba(11,42,68,0.1)', iconColor: '#0B2A44' },
  { title: 'Instrument', value: instrumentType.value || 'N/A', icon: 'mdi-chart-line', color: 'rgba(30,136,229,0.1)', iconColor: '#1E88E5' },
  { title: 'Export', value: 'Excel (.xlsx)', icon: 'mdi-file-excel', color: 'rgba(76,175,80,0.1)', iconColor: '#4CAF50' }
])

// ---- REPORT GENERATION ----
// Uses shared generator from utils/generateReportHtml.js

// Load data from the current session and instrument
async function loadData() {
  try {
    const instrument = route.query.instrument || 'money-market'
    let sessionId = route.query.session || sessionManager.getActiveSessionId()
    if (!sessionId) {
      const session = resolveActiveSession(sessionManager)
      sessionId = session?.id
    }
    if (!sessionId) {
      alert('No session selected. Please navigate from Dashboard or Instrument page.')
      return
    }

    const session = sessionManager.getSession(sessionId)
    if (!session) {
      alert('Session not found.')
      return
    }

    sessionName.value = session.name || 'Current Session'

    const data = loadInstrumentData(sessionManager, sessionId, instrument)

    if (!data.length) {
      alert('No data found for this instrument in the session. Please upload and process data first.')
      return
    }

    calcData.value = data
    instrumentType.value = instrument.charAt(0).toUpperCase() + instrument.slice(1)
    alert(`Loaded ${data.length} records for ${instrumentType.value}`)
  } catch (err) {
    console.error(err)
    alert('Error loading data: ' + err.message)
  }
}

// Select/Deselect sections
function selectAll() { sections.value.forEach(s => s.selected = true) }
function clearAll() { sections.value.forEach(s => s.selected = false) }

// Download functions
function downloadJSON() {
  generating.value = true
  setTimeout(() => {
    const data = calcData.value
    const instrument = instrumentType.value
    const session = sessionName.value || 'Current Session'
    const date = new Date().toLocaleString()
    const valuationDate = new Date().toISOString().split('T')[0]
    
    const reportData = {
      metadata: {
        title: 'Valuation Assessment Report',
        session: session,
        instrument: instrument,
        valuationDate: valuationDate,
        reportDate: date,
        preparedBy: 'Dura Capital (Private) Limited'
      },
      summary: {
        totalValue: data.reduce((s, r) => s + (parseFloat(r.FaceValue || r.Amount || r.Principal || 0)), 0),
        recordCount: data.length,
        averageRate: data.map(r => parseFloat(r.Rate || r.InterestRate || r.CouponRate || r.DiscountRate || 0)).filter(r => !isNaN(r) && r > 0).reduce((a, b) => a + b, 0) / data.length || 0
      },
      data: data
    }
    
    const blob = new Blob([JSON.stringify(reportData, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `Report_${session}_${instrument}.json`
    a.click()
    URL.revokeObjectURL(url)
    
    reportReady.value = true
    generating.value = false
    setTimeout(() => { reportReady.value = false }, 3000)
  }, 500)
}

function downloadCSV() {
  generating.value = true
  setTimeout(() => {
    const data = calcData.value
    const headers = Object.keys(data[0] || {})
    const csvContent = [
      headers.join(','),
      ...data.map(row => headers.map(h => `"${row[h] || ''}"`).join(','))
    ].join('\n')
    
    const blob = new Blob([csvContent], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `Report_${sessionName.value}_${instrumentType.value}.csv`
    a.click()
    URL.revokeObjectURL(url)
    
    reportReady.value = true
    generating.value = false
    setTimeout(() => { reportReady.value = false }, 3000)
  }, 500)
}

function downloadHTML() {
  generating.value = true
  setTimeout(() => {
    const html = generateReportHtml(calcData.value, instrumentType.value, sessionName.value, new Date().toLocaleString(), new Date().toISOString().split('T')[0])
    const blob = new Blob([html], { type: 'text/html' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `Report_${sessionName.value}_${instrumentType.value}.html`
    a.click()
    URL.revokeObjectURL(url)
    
    reportReady.value = true
    generating.value = false
    setTimeout(() => { reportReady.value = false }, 3000)
  }, 500)
}

function downloadPDF() {
  generating.value = true
  setTimeout(() => {
    const html = generateReportHtml(calcData.value, instrumentType.value, sessionName.value, new Date().toLocaleString(), new Date().toISOString().split('T')[0])
    const win = window.open('', '_blank')
    win.document.write(html)
    win.document.close()
    win.focus()
    setTimeout(() => {
      win.print()
    }, 500)
    
    reportReady.value = true
    generating.value = false
    setTimeout(() => { reportReady.value = false }, 3000)
  }, 500)
}

function downloadWord() {
  generating.value = true
  setTimeout(() => {
    const htmlContent = generateReportHtml(calcData.value, instrumentType.value, sessionName.value, new Date().toLocaleString(), new Date().toISOString().split('T')[0])
    const wordContent = `
      <html xmlns:o='urn:schemas-microsoft-com:office:office' 
            xmlns:w='urn:schemas-microsoft-com:office:word'
            xmlns='http://www.w3.org/TR/REC-html40'>
      <head>
        <meta charset="utf-8">
        <title>Valuation Assessment Report</title>
      </head>
      <body>
        ${htmlContent.replace('<!DOCTYPE html><html><head>', '').replace('</body></html>', '')}
      </body>
      </html>
    `
    const blob = new Blob([wordContent], { type: 'application/msword' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `Report_${sessionName.value}_${instrumentType.value}.doc`
    a.click()
    URL.revokeObjectURL(url)
    
    reportReady.value = true
    generating.value = false
    setTimeout(() => { reportReady.value = false }, 3000)
  }, 500)
}

function downloadExcel() {
  generating.value = true
  setTimeout(() => {
    const data = calcData.value
    const instrument = instrumentType.value
    const session = sessionName.value || 'Current Session'
    const date = new Date().toLocaleString()
    const valuationDate = new Date().toISOString().split('T')[0]
    
    const wb = XLSX.utils.book_new()
    
    // Cover
    const coverData = [
      ['DURA CAPITAL (PRIVATE) LIMITED'],
      ['VALUATION ASSESSMENT REPORT'],
      [''],
      [instrument],
      [''],
      ['Valuation Date:', valuationDate],
      ['Report Date:', date],
      ['Prepared for:', session],
      [''],
      ['Confidential'],
      [''],
      ['© Dura Capital (Private) Limited']
    ]
    const coverSheet = XLSX.utils.aoa_to_sheet(coverData)
    coverSheet['!cols'] = [{ wch: 40 }]
    XLSX.utils.book_append_sheet(wb, coverSheet, 'Cover')
    
    // Summary
    const totalValue = data.reduce((s, r) => s + (parseFloat(r.FaceValue || r.Amount || r.Principal || 0)), 0)
    const totalInterest = data.reduce((s, r) => s + (parseFloat(r.InterestEarned || r.Interest || 0)), 0)
    const rates = data.map(r => parseFloat(r.Rate || r.InterestRate || r.CouponRate || r.DiscountRate || 0)).filter(r => !isNaN(r) && r > 0)
    const avgRate = rates.length ? rates.reduce((a, b) => a + b, 0) / rates.length : 0
    
    const summaryData = [
      ['EXECUTIVE SUMMARY'],
      [''],
      ['Metric', 'Value'],
      ['Total Portfolio Value', totalValue],
      ['Number of Instruments', data.length],
      ['Average Rate (%)', avgRate],
      ['Total Interest Earned', totalInterest],
      ['Valuation Date', valuationDate],
      [''],
      ['METHODOLOGY'],
      [''],
      ['Approach:', 'Discounted cash flow valuation'],
      ['Day Count:', 'Actual/365'],
      ['Discount Rate:', 'SOFR OIS + Country Risk Premium'],
      [''],
      ['RESULTS'],
      [''],
      ['The valuation has been performed in accordance with IFRS 13.']
    ]
    const summarySheet = XLSX.utils.aoa_to_sheet(summaryData)
    summarySheet['!cols'] = [{ wch: 30 }, { wch: 30 }]
    XLSX.utils.book_append_sheet(wb, summarySheet, 'Summary')
    
    // Data
    const headers = Object.keys(data[0] || {})
    const dataRows = [headers]
    data.forEach(item => {
      dataRows.push(Object.values(item))
    })
    const dataSheet = XLSX.utils.aoa_to_sheet(dataRows)
    XLSX.utils.book_append_sheet(wb, dataSheet, 'Data')
    
    // Appendix
    const appendixData = [
      ['APPENDIX: DETAILED INSTRUMENT DATA'],
      ['Valuation Date:', valuationDate],
      [''],
      ['Instrument Name', 'BB Ticker', 'Face Value ($)', 'Rate (%)', 'Term (Yrs)', 'Valuation Date']
    ]
    data.forEach((item, idx) => {
      const name = item.Instrument || item.BondName || item.TBillName || `Instrument ${idx + 1}`
      const faceValue = parseFloat(item.FaceValue || item.Amount || item.Principal || 0)
      const rate = parseFloat(item.Rate || item.InterestRate || item.CouponRate || item.DiscountRate || 0)
      const term = parseFloat(item.Term || item.YearsToMaturity || 0) || (parseFloat(item.MaturityDate) ? (new Date(item.MaturityDate) - new Date(item.IssueDate || Date.now())) / (365 * 24 * 60 * 60 * 1000) : 0)
      const ticker = item.BBTicker || item.Ticker || item.Security || 'N/A'
      appendixData.push([name, ticker, faceValue, rate, term, valuationDate])
    })
    const appendixSheet = XLSX.utils.aoa_to_sheet(appendixData)
    appendixSheet['!cols'] = [{ wch: 25 }, { wch: 15 }, { wch: 18 }, { wch: 12 }, { wch: 12 }, { wch: 15 }]
    XLSX.utils.book_append_sheet(wb, appendixSheet, 'Appendix')
    
    // Methodology
    const methodologyData = [
      ['METHODOLOGY & ASSUMPTIONS'],
      [''],
      ['Valuation Approach:', 'Discounted cash flow methodology'],
      ['Fair Value Formula:', 'PV = Σ CF_t / (1 + r)^t'],
      ['Day Count Convention:', 'Actual/365'],
      ['Discount Rate Source:', 'SOFR OIS + Country Risk Premium'],
      ['Country Risk Premium:', 'Damodaran Country Risk Premiums'],
      ['Yield Curve Model:', 'Nelson-Siegel-Svensson'],
      [''],
      ['Key Assumptions:'],
      ['- All monetary values are in base currency'],
      ['- Rates are annualized unless otherwise stated'],
      ['- Cashflows are discounted at appropriate market rates']
    ]
    const methodologySheet = XLSX.utils.aoa_to_sheet(methodologyData)
    methodologySheet['!cols'] = [{ wch: 30 }, { wch: 50 }]
    XLSX.utils.book_append_sheet(wb, methodologySheet, 'Methodology')
    
    XLSX.writeFile(wb, `Dura-Capital-Valuation-Report-${new Date().toISOString().split('T')[0]}.xlsx`)
    
    reportReady.value = true
    generating.value = false
    setTimeout(() => { reportReady.value = false }, 3000)
  }, 500)
}

async function finishAndReset() {
  if (confirm('Complete & Reset?')) {
    try {
      const sid = route.query.session || null
      if (sid) await markStepCompleted(String(sid), 'reports')
    } catch (e) { console.warn(e) }
    calcData.value = []
    instrumentType.value = ''
    sections.value.forEach(s => s.selected = true)
    router.push('/upload')
  }
}

onMounted(() => {
  if (route.query.session && route.query.instrument) {
    loadData()
  }
})
</script>

<style scoped>
.reports-view { max-width: 1400px; margin: 0 auto; padding: 20px; }
.page-header { margin-bottom: 30px; }
.page-header h1 { color: #0B2A44; font-size: 32px; font-weight: 700; margin-bottom: 8px; }
.page-header p { color: #666; font-size: 16px; }
.action-buttons { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 20px; }
.action-buttons.small { margin-bottom: 16px; }
.stats-card { border-radius: 12px; margin-bottom: 24px; background: white; border: 1px solid rgba(11,42,68,0.08); position: relative; }
.stats-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; background: linear-gradient(90deg, #0B2A44, #1E88E5); border-radius: 12px 12px 0 0; }
.card-title { display: flex; align-items: center; color: #0B2A44; font-weight: 600; font-size: 18px; padding: 16px 20px 0 20px; }
.title-icon { margin-right: 8px; }
.kpi-card { height: 120px; border-radius: 12px; transition: transform 0.2s ease, box-shadow 0.2s ease; background: white; border: 1px solid rgba(11,42,68,0.08); position: relative; }
.kpi-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; background: linear-gradient(90deg, #0B2A44, #1E88E5, #4CAF50); border-radius: 12px 12px 0 0; }
.kpi-card:hover { transform: translateY(-2px); box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1); }
.kpi-content { display: flex; align-items: center; height: 100%; padding: 8px; }
.kpi-icon { width: 56px; height: 56px; border-radius: 12px; display: flex; align-items: center; justify-content: center; margin-right: 12px; flex-shrink: 0; }
.kpi-info { flex: 1; min-width: 0; display: flex; flex-direction: column; justify-content: center; }
.kpi-value { font-size: 24px; font-weight: 700; color: #0B2A44; line-height: 1; margin-bottom: 4px; }
.kpi-title { font-size: 12px; color: #666; }
.section-card { cursor: pointer; transition: 0.2s; border: 2px solid transparent; border-radius: 12px; }
.section-card:hover { transform: translateY(-2px); }
.section-card.selected { border-color: #1E88E5; background: rgba(30,136,229,0.05); }
.section-name { font-weight: 600; margin-top: 8px; color: #0B2A44; }
.section-desc { font-size: 11px; color: #666; }
@media (max-width: 600px) { .reports-view { padding: 0 16px; } .action-buttons { flex-direction: column; } .kpi-card { height: 100px; } .kpi-value { font-size: 20px; } }
</style>