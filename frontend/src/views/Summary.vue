<template>
  <FixedLayout>
    <div class="summary-page">
      <div class="page-header hero-header">
        <div>
          <h1>Portfolio Summary</h1>
          <p class="subtitle">Consolidated valuation across Money Market, Bonds, and T-Bills</p>
          <div class="session-chip" v-if="activeSession">
            <v-icon size="16">mdi-folder-account</v-icon> {{ activeSession.name }}
          </div>
          <div v-else class="session-chip warn">No active session — open Dashboard first</div>
        </div>
        <div class="grand-pill">
          <span class="pill-label">Total portfolio</span>
          <span class="pill-amount">${{ formatNumber(grandTotal) }}</span>
          <span class="pill-sub">{{ totalInstruments }} instruments · {{ completedCount }}/3 classes done</span>
        </div>
      </div>

      <!-- KPI Strip -->
      <div class="kpi-strip">
        <div class="kpi-mini" v-for="k in extendedKpis" :key="k.label">
          <v-icon size="20" :color="k.color">{{ k.icon }}</v-icon>
          <div>
            <span class="kpi-mini-val">{{ k.value }}</span>
            <span class="kpi-mini-lbl">{{ k.label }}</span>
          </div>
        </div>
      </div>

      <!-- Instrument breakdown -->
      <div class="section-header">
        <v-icon color="#0B2044" size="22">mdi-chart-areaspline</v-icon>
        <h2>Instrument breakdown</h2>
      </div>

      <div class="summary-cards">
        <div class="summary-card" v-for="inst in instruments" :key="inst.id">
          <div class="card-top" :style="{ background: inst.gradient }">
            <v-icon size="32" color="white">{{ inst.icon }}</v-icon>
            <h3>{{ inst.name }}</h3>
          </div>
          <div class="card-body">
            <div class="stat-row highlight">
              <span>Total value</span>
              <strong>${{ formatNumber(inst.value) }}</strong>
            </div>
            <div class="stat-row">
              <span>Count</span>
              <strong>{{ inst.count }}</strong>
            </div>
            <div class="stat-row">
              <span>{{ inst.rateLabel }}</span>
              <strong>{{ inst.avgRate !== null && inst.avgRate !== undefined ? inst.avgRate + '%' : '—' }}</strong>
            </div>
            <div class="stat-row">
              <span>FRED benchmark</span>
              <strong>{{ inst.fredBench !== null && inst.fredBench !== undefined ? inst.fredBench + '%' : '—' }}</strong>
            </div>
            <div class="status-badge" :class="inst.statusClass">
              <v-icon size="14">{{ inst.statusIcon }}</v-icon> {{ inst.statusText }}
            </div>
            <button class="btn-open-inst" @click="openInstrument(inst.id)">Open workflow →</button>
          </div>
        </div>
      </div>

      <!-- Distribution bars -->
      <div class="distribution-section">
        <h3>Portfolio Allocation</h3>
        <div class="distribution-bars">
          <div v-for="inst in instruments" :key="inst.id" class="dist-bar-container">
            <div class="dist-label">{{ inst.name }}</div>
            <div class="dist-track">
              <div class="dist-fill" :style="{ width: inst.percent + '%', background: inst.barColor }"></div>
            </div>
            <div class="dist-percent">{{ inst.percent }}%</div>
          </div>
        </div>
      </div>

      <!-- Detailed sections -->
      <div v-for="inst in instrumentsWithDetails" :key="inst.id" class="detail-section">
        <div class="detail-header">
          <h3>{{ inst.name }} – Detailed Instruments ({{ inst.details.length }} rows)</h3>
          <div class="detail-actions">
            <button class="btn-view-details" @click="openDetailModal(inst)">
              <v-icon size="16">mdi-eye</v-icon> View as Excel
            </button>
          </div>
        </div>
      </div>

      <!-- Export buttons -->
      <div class="export-all-section">
        <button class="btn-view-portfolio" @click="openCombinedModal">
          <v-icon>mdi-eye</v-icon> View Portfolio as Excel
        </button>
        <button class="btn-export-all" @click="showExportDialog = true">
          <v-icon>mdi-microsoft-excel</v-icon> Export to Excel
        </button>
      </div>

      <div class="action-buttons">
        <button class="btn-secondary" @click="goToDashboard">Dashboard</button>
        <button class="btn-primary" @click="goToReport">Continue to Report →</button>
      </div>
    </div>

    <!-- Modals -->
    <v-dialog v-model="detailModalVisible" max-width="90%" fullscreen hide-overlay>
      <v-card>
        <v-card-title class="excel-dialog-title">
          Detailed view: {{ selectedInst?.name }}
          <v-spacer></v-spacer>
          <button class="btn-close-dialog" @click="detailModalVisible = false">
            <v-icon>mdi-close</v-icon>
          </button>
        </v-card-title>
        <v-card-text class="pa-0" style="height: calc(100vh - 120px);">
          <ExcelViewer :data="selectedInst?.details || []" :headers="selectedInst?.detailHeaders || []" />
        </v-card-text>
      </v-card>
    </v-dialog>

    <v-dialog v-model="combinedModalVisible" max-width="90%" fullscreen hide-overlay>
      <v-card>
        <v-card-title class="excel-dialog-title">
          Portfolio – Combined Excel View
          <v-spacer></v-spacer>
          <button class="btn-close-dialog" @click="combinedModalVisible = false">
            <v-icon>mdi-close</v-icon>
          </button>
        </v-card-title>
        <v-card-text class="combined-excel-body">
          <div class="combined-section">
            <div class="excel-header">
              <div class="excel-logo-area">
                <img src="/DuraCapital logo.png" alt="DuraCapital" class="excel-logo" />
              </div>
              <div class="excel-title-area">
                <h3 class="excel-company">DuraCapital</h3>
                <h4 class="excel-report-title">Portfolio Summary</h4>
                <p class="excel-session">Session: {{ activeSession?.name || 'N/A' }}</p>
                <p class="excel-date">Valuation Date: {{ new Date().toISOString().split('T')[0] }}</p>
              </div>
            </div>
            <h4 class="combined-section-title">Summary</h4>
            <table class="summary-table">
              <thead>
                <tr>
                  <th>Instrument</th>
                  <th>Face Value ($)</th>
                  <th>Calculated Value ($)</th>
                  <th>Difference ($)</th>
                  <th>Count</th>
                  <th>Avg Rate (%)</th>
                  <th>FRED Benchmark (%)</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="inst in filteredInstruments" :key="inst.id">
                  <td><strong>{{ inst.name }}</strong></td>
                  <td>${{ formatNumber(inst.faceValue || 0) }}</td>
                  <td>${{ formatNumber(inst.value) }}</td>
                  <td>${{ formatNumber(inst.difference || 0) }}</td>
                  <td>{{ inst.count }}</td>
                  <td>{{ inst.avgRate !== null && inst.avgRate !== undefined ? inst.avgRate : '—' }}</td>
                  <td>{{ inst.fredBench !== null && inst.fredBench !== undefined ? inst.fredBench : '—' }}</td>
                  <td><span class="status-badge small" :class="inst.statusClass">{{ inst.statusText }}</span></td>
                </tr>
              </tbody>
            </table>
          </div>

          <div v-for="inst in filteredDetails" :key="inst.id" class="combined-section">
            <h4 class="combined-section-title">
              {{ inst.name }} – Details ({{ inst.details.length }} rows)
              <span v-if="!inst.details.length" class="empty-note">(no data)</span>
            </h4>
            <div v-if="inst.details.length" class="excel-wrapper">
              <ExcelViewer :data="inst.details" :headers="inst.detailHeaders" />
            </div>
            <div v-else class="empty-placeholder">No data available for this instrument.</div>
          </div>
        </v-card-text>
      </v-card>
    </v-dialog>

    <v-dialog v-model="showExportDialog" max-width="500px">
      <v-card>
        <v-card-title>Select instruments to export</v-card-title>
        <v-card-text>
          <div class="export-instrument-select">
            <label v-for="inst in instruments" :key="inst.id" class="export-checkbox">
              <input type="checkbox" v-model="selectedExportInstruments[inst.id]" />
              {{ inst.name }}
              <span v-if="!inst.completed" class="warning-badge">(no data)</span>
            </label>
          </div>
        </v-card-text>
        <v-card-actions>
          <button class="btn-secondary" @click="showExportDialog = false">Cancel</button>
          <button class="btn-primary" @click="exportToExcel">Export</button>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </FixedLayout>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import FixedLayout from '@/components/FixedLayout.vue'
import sessionManager from '@/services/sessionManager.js'
import ExcelViewer from '@/components/ExcelViewer.vue'
import * as XLSX from 'xlsx'

const router = useRouter()
const activeSession = ref(null)
const instruments = ref([])
const instrumentsWithDetails = ref([])
const detailModalVisible = ref(false)
const selectedInst = ref(null)
const combinedModalVisible = ref(false)
const showExportDialog = ref(false)
const selectedExportInstruments = ref({})

const totalFaceValue = computed(() => instruments.value.reduce((sum, inst) => sum + (inst.faceValue || 0), 0))

const extendedKpis = computed(() => [
  { label: 'Total Face Value', value: '$' + formatNumber(totalFaceValue.value), icon: 'mdi-cash', color: '#0B2044' },
  { label: 'Total Calculated', value: '$' + formatNumber(grandTotal.value), icon: 'mdi-calculator', color: '#1E88E5' },
  { label: 'Difference', value: '$' + formatNumber(totalFaceValue.value - grandTotal.value), icon: 'mdi-arrow-right', color: '#FF9800' },
  { label: 'Instrument Types', value: `${completedCount.value}/3`, icon: 'mdi-chart-pie', color: '#4CAF50' }
])

const filteredInstruments = computed(() => {
  return instruments.value.filter(inst => selectedExportInstruments.value[inst.id])
})
const filteredDetails = computed(() => {
  return instrumentsWithDetails.value.filter(inst => selectedExportInstruments.value[inst.id])
})
const grandTotal = computed(() => instruments.value.reduce((sum, inst) => sum + inst.value, 0))
const totalInstruments = computed(() => instruments.value.reduce((sum, inst) => sum + (inst.count || 0), 0))
const completedCount = computed(() => instruments.value.filter(i => i.completed).length)

function formatNumber(num) {
  return (num || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function openInstrument(id) {
  if (!activeSession.value) { alert('Select a session on the Dashboard first'); router.push('/dashboard'); return }
  router.push({ path: `/instrument/${id}`, query: { session: activeSession.value.id } })
}
function goToDashboard() { 
  try { if (activeSession.value) sessionManager.setActiveSession(activeSession.value) } catch(e) { console.warn(e) }
  router.push('/dashboard') 
}
function goToReport() {
  if (!activeSession.value) { alert('No active session'); return }
  router.push({ path: '/instrument/money-market', query: { session: activeSession.value.id, tab: 'reports' } })
}
function openDetailModal(inst) {
  selectedInst.value = inst
  detailModalVisible.value = true
}
function openCombinedModal() {
  const hasSelection = Object.values(selectedExportInstruments.value).some(v => v === true)
  if (!hasSelection) {
    instruments.value.forEach(inst => {
      if (inst.completed || inst.value > 0) {
        selectedExportInstruments.value[inst.id] = true
      }
    })
  }
  combinedModalVisible.value = true
}

async function loadSummary() {
  let session = null
  try {
    session = sessionManager.getActiveSession()
    if (!session) {
      const all = sessionManager.getAllSessions()
      session = all[0] || null
    }
    if (!session) {
      const sid = sessionManager.getActiveSessionId()
      if (sid) {
        const loaded = await sessionManager.loadSessionFromDb(sid)
        if (loaded) {
          session = sessionManager.getSession(sid)
        }
      }
    }
    if (!session) {
      const sid = sessionManager.getActiveSessionId()
      if (sid) {
        const loaded = await sessionManager.loadSessionFromDb(sid)
        if (loaded) {
          session = sessionManager.getSession(sid)
        }
      }
    }
  } catch(e) {
    console.warn('Error getting session:', e)
  }
  activeSession.value = session

  if (!activeSession.value) {
    console.warn('No active session found')
    instruments.value = []
    instrumentsWithDetails.value = []
    return
  }

  const sid = activeSession.value.id
  const templates = [
    { id: 'money-market', name: 'Money Market', icon: 'mdi-chart-line', gradient: 'linear-gradient(135deg, #1E88E5, #0B2044)', rateLabel: 'Avg interest rate', barColor: '#1E88E5' },
    { id: 'bonds', name: 'Bonds', icon: 'mdi-chart-timeline', gradient: 'linear-gradient(135deg, #4CAF50, #2E7D32)', rateLabel: 'Avg coupon', barColor: '#4CAF50' },
    { id: 'tbills', name: 'T-Bills', icon: 'mdi-finance', gradient: 'linear-gradient(135deg, #FFC107, #FF9800)', rateLabel: 'Avg discount', barColor: '#FF9800' }
  ]

  const detailsList = []
  instruments.value = templates.map(template => {
    let wf = null
    try {
      wf = sessionManager.getInstrumentWorkflow(sid, template.id)
    } catch(e) { console.warn(e) }
    
    let cleanedData = []
    let calculations = {}
    if (wf && (wf.calculations?.totalValue || wf.cleanedData?.length)) {
      cleanedData = wf.cleanedData || []
      calculations = wf.calculations || {}
    } 
    if (!calculations.totalValue) {
      const cleanKey = `${template.id}_session_${sid}_clean`
      const calcKey = `${template.id}_session_${sid}_calc`
      const savedClean = localStorage.getItem(cleanKey)
      const savedCalc = localStorage.getItem(calcKey)
      if (savedClean) {
        try { cleanedData = JSON.parse(savedClean) } catch(e) {}
      }
      if (savedCalc) {
        try { calculations = JSON.parse(savedCalc) } catch(e) {}
      }
    }
    if (!calculations.totalValue && activeSession.value.instrumentData?.[template.id]) {
      const data = activeSession.value.instrumentData[template.id]
      calculations = { ...data, ...calculations }
    }
    
    const completed = !!calculations.totalValue
    const value = parseFloat(calculations.totalValue) || 0
    const headers = cleanedData.length ? Object.keys(cleanedData[0]) : []
    detailsList.push({
      id: template.id,
      name: template.name,
      details: cleanedData,
      detailHeaders: headers
    })
    let avgRate = null
    if (template.id === 'money-market') avgRate = calculations.avgRate
    else if (template.id === 'bonds') avgRate = calculations.avgCouponRate
    else avgRate = calculations.avgDiscountRate
    if (avgRate === undefined) avgRate = null
    
    let faceValue = 0
    if (cleanedData && cleanedData.length) {
      cleanedData.forEach(row => {
        const fv = parseFloat(row.FaceValue || row.Amount || row.Principal || 0)
        if (!isNaN(fv)) faceValue += fv
      })
    }
    if (faceValue === 0 && value > 0) faceValue = value
    const difference = faceValue - value

    return {
      ...template,
      value,
      faceValue,
      difference,
      count: calculations.instrumentCount || 0,
      avgRate,
      fredBench: calculations.fred?.benchmark_rate ?? null,
      completed,
      statusClass: completed ? 'completed' : value > 0 ? 'in-progress' : 'pending',
      statusText: completed ? 'Completed' : value > 0 ? 'In progress' : 'Not started',
      statusIcon: completed ? 'mdi-check-circle' : value > 0 ? 'mdi-progress-clock' : 'mdi-clock-outline'
    }
  })
  instrumentsWithDetails.value = detailsList

  const total = instruments.value.reduce((sum, inst) => sum + inst.value, 0)
  instruments.value = instruments.value.map(inst => ({
    ...inst,
    percent: total > 0 ? ((inst.value / total) * 100).toFixed(1) : 0
  }))

  const initSelections = {}
  instruments.value.forEach(inst => {
    initSelections[inst.id] = inst.completed || inst.value > 0
  })
  selectedExportInstruments.value = initSelections
}

function exportToExcel() {
  if (!activeSession.value) { alert('No active session'); return }
  const toExport = instruments.value.filter(inst => selectedExportInstruments.value[inst.id])
  if (toExport.length === 0) { alert('No instruments selected for export'); return }

  const workbook = XLSX.utils.book_new()
  const valuationDate = new Date().toISOString().split('T')[0]
  
  // Create summary sheet with logo and professional formatting
  const summaryRows = []
  
  // Add header rows with logo placeholder and company info
  summaryRows.push({ '': '', '': '', '': '' }) // Empty row for spacing
  summaryRows.push({ '': 'DuraCapital', '': '', '': '' }) // Company name
  summaryRows.push({ '': 'Portfolio Summary', '': '', '': '' }) // Report title
  summaryRows.push({ '': `Session: ${activeSession.value.name}`, '': '', '': '' }) // Session name
  summaryRows.push({ '': `Valuation Date: ${valuationDate}`, '': '', '': '' }) // Valuation date
  summaryRows.push({ '': '', '': '', '': '' }) // Empty row for spacing
  
  // Add column headers
  summaryRows.push({
    'Instrument Name': 'Instrument Name',
    'Face Value': 'Face Value',
    'Calculated Value': 'Calculated Value',
    'Difference': 'Difference',
    'Yield (%)': 'Yield (%)',
    'Valuation Date': 'Valuation Date',
    'Maturity Date': 'Maturity Date'
  })
  
  // Add data rows
  const dataRows = []
  toExport.forEach(inst => {
    const faceValue = inst.faceValue || 0
    const calculatedValue = inst.value || 0
    const diff = faceValue - calculatedValue
    let maturityDate = '—'
    const detailInst = instrumentsWithDetails.value.find(d => d.id === inst.id);
    if (detailInst && detailInst.details && detailInst.details.length) {
      const firstRow = detailInst.details[0]
      if (firstRow) {
        maturityDate = firstRow.MaturityDate || firstRow.Maturity || firstRow['Maturity Date'] || '—'
      }
    }
    dataRows.push({
      'Instrument Name': inst.name,
      'Face Value': faceValue,
      'Calculated Value': calculatedValue,
      'Difference': diff,
      'Yield (%)': inst.avgRate !== null ? inst.avgRate : '—',
      'Valuation Date': valuationDate,
      'Maturity Date': maturityDate
    });
  });
  summaryRows.push(...dataRows);

  // Add totals row
  const totals = {
    'Instrument Name': 'TOTAL',
    'Face Value': dataRows.reduce((s, r) => s + r['Face Value'], 0),
    'Calculated Value': dataRows.reduce((s, r) => s + r['Calculated Value'], 0),
    'Difference': dataRows.reduce((s, r) => s + r['Difference'], 0),
    'Yield (%)': '—',
    'Valuation Date': '',
    'Maturity Date': ''
  };
  summaryRows.push(totals);
  
  const summarySheet = XLSX.utils.json_to_sheet(summaryRows);
  XLSX.utils.book_append_sheet(workbook, summarySheet, 'Summary');

  for (const inst of instrumentsWithDetails.value) {
    if (selectedExportInstruments.value[inst.id] && inst.details && inst.details.length) {
      const enrichedDetails = inst.details.map(row => {
        const newRow = { ...row };
        const face = parseFloat(row.FaceValue || row.Amount || row.Principal || 0);
        const calcVal = parseFloat(row['Calculated Value']) || (inst.value / inst.details.length);
        newRow['Calculated Value'] = calcVal;
        newRow['Difference'] = face - calcVal;
        newRow['Yield (%)'] = row.Yield || row['Yield'] || row.Rate || row['Rate'] || row.CouponRate || row['Coupon Rate'] || row.DiscountRate || row['Discount Rate'] || '—';
        newRow['Valuation Date'] = row.ValuationDate || row['Valuation Date'] || valuationDate;
        newRow['Maturity Date'] = row.MaturityDate || row.Maturity || row['Maturity Date'] || '—';
        return newRow;
      });
      const sheet = XLSX.utils.json_to_sheet(enrichedDetails);
      XLSX.utils.book_append_sheet(workbook, sheet, inst.name.substring(0, 31));
    }
  }
  
  const instrumentTotals = []
  toExport.forEach(inst => {
    const detailInst = instrumentsWithDetails.value.find(d => d.id === inst.id);
    if (detailInst && detailInst.details && detailInst.details.length) {
      const faceSum = detailInst.details.reduce((s, row) => s + (parseFloat(row.FaceValue || row.Amount || row.Principal || 0)), 0);
      const calcSum = detailInst.details.reduce((s, row) => s + (parseFloat(row['Calculated Value']) || 0), 0);
      instrumentTotals.push({
        'Instrument Type': inst.name,
        'Total Face Value': faceSum,
        'Total Calculated Value': calcSum,
        'Total Difference': faceSum - calcSum,
        'Average Yield (%)': inst.avgRate || '—',
        'Instrument Count': inst.count || detailInst.details.length
      })
    }
  })
  if (instrumentTotals.length > 0) {
    const totalsSheet = XLSX.utils.json_to_sheet(instrumentTotals)
    XLSX.utils.book_append_sheet(workbook, totalsSheet, 'Instrument Totals')
  }
  
  XLSX.writeFile(workbook, `Portfolio_Summary_${activeSession.value.name || 'session'}_${valuationDate}.xlsx`);
  showExportDialog.value = false;
}

onMounted(() => {
  loadSummary().catch(err => console.error('Error loading summary:', err))
})
</script>

<style scoped>
.summary-page { padding: 28px; max-width: 1200px; margin: 0 auto; }
.hero-header { display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 20px; margin-bottom: 24px; }
.hero-header h1 { color: #0B2044; font-size: 32px; margin: 0 0 8px; }
.subtitle { color: #666; margin: 0; }
.session-chip { display: inline-flex; align-items: center; gap: 6px; margin-top: 12px; padding: 6px 12px; background: #e8ecf1; border-radius: 20px; font-size: 13px; }
.session-chip.warn { background: #fff3e0; color: #e65100; }
.grand-pill { text-align: right; padding: 20px 28px; background: linear-gradient(135deg, #0B2044, #1E88E5); border-radius: 14px; color: white; box-shadow: 0 8px 24px rgba(11,32,68,0.2); }
.pill-label { display: block; font-size: 12px; opacity: 0.9; }
.pill-amount { font-size: 30px; font-weight: 700; display: block; }
.pill-sub { font-size: 12px; opacity: 0.85; }
.kpi-strip { display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 28px; }
.kpi-mini { display: flex; align-items: center; gap: 12px; padding: 14px 20px; background: white; border-radius: 12px; box-shadow: 0 2px 12px rgba(0,0,0,0.06); flex: 1; min-width: 160px; }
.kpi-mini-val { display: block; font-weight: 700; color: #0B2044; font-size: 16px; }
.kpi-mini-lbl { font-size: 12px; color: #666; }
.section-header { display: flex; align-items: center; gap: 10px; margin-bottom: 20px; flex-wrap: wrap; }
.section-header h2 { color: #0B2044; margin: 0; font-size: 20px; }
.summary-cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; }
.summary-card { border-radius: 12px; overflow: hidden; box-shadow: 0 4px 16px rgba(11,32,68,0.1); background: white; }
.card-top { padding: 20px; color: white; display: flex; align-items: center; gap: 12px; }
.card-top h3 { margin: 0; font-size: 18px; }
.card-body { padding: 16px; }
.stat-row { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #eee; font-size: 14px; }
.stat-row.highlight strong { color: #0B2044; font-size: 16px; }
.status-badge { margin-top: 12px; padding: 8px 12px; border-radius: 8px; font-size: 12px; display: inline-flex; align-items: center; gap: 6px; }
.status-badge.completed { background: #e8f5e9; color: #2e7d32; }
.status-badge.in-progress { background: #e3f2fd; color: #1565c0; }
.status-badge.pending { background: #f5f5f5; color: #757575; }
.status-badge.small { padding: 4px 10px; font-size: 11px; }
.btn-open-inst { margin-top: 12px; width: 100%; padding: 10px; background: #0B2044; color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 13px; }
.btn-open-inst:hover { background: #1a3a6e; }
.action-buttons { display: flex; gap: 16px; justify-content: center; margin-top: 32px; }
.btn-primary, .btn-secondary { padding: 12px 28px; border-radius: 10px; font-size: 14px; font-weight: 600; cursor: pointer; border: none; }
.btn-primary { background: linear-gradient(135deg, #0B2044, #1E88E5); color: white; }
.btn-secondary { background: white; color: #0B2044; border: 2px solid #0B2044; }
.detail-section { margin-top: 32px; background: white; border-radius: 12px; padding: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }
.detail-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; flex-wrap: wrap; gap: 10px; }
.detail-header h3 { color: #0B2044; margin: 0; }
.detail-actions { display: flex; gap: 8px; }
.btn-view-details { background: #0B2044; color: white; border: none; padding: 4px 12px; border-radius: 20px; font-size: 12px; cursor: pointer; display: inline-flex; align-items: center; gap: 4px; }
.btn-view-details:hover { background: #1a3a6e; }
.export-all-section { display: flex; justify-content: center; gap: 16px; margin: 32px 0 20px; flex-wrap: wrap; }
.btn-export-all, .btn-view-portfolio { border: none; padding: 10px 24px; border-radius: 40px; font-size: 14px; font-weight: 600; cursor: pointer; display: inline-flex; align-items: center; gap: 8px; transition: all 0.3s; box-shadow: 0 2px 6px rgba(0,0,0,0.1); }
.btn-export-all { background: #4CAF50; color: white; }
.btn-export-all:hover { background: #45a049; transform: translateY(-2px); box-shadow: 0 6px 12px rgba(0,0,0,0.15); }
.btn-view-portfolio { background: #0B2044; color: white; }
.btn-view-portfolio:hover { background: #1a3a6e; transform: translateY(-2px); box-shadow: 0 6px 12px rgba(0,0,0,0.15); }
.excel-dialog-title { background: #0B2044; color: white; padding: 16px 24px; display: flex; align-items: center; }
.btn-close-dialog { background: transparent; border: none; color: white; cursor: pointer; padding: 8px; border-radius: 50%; }
.btn-close-dialog:hover { background: rgba(255,255,255,0.1); }
.export-instrument-select { display: flex; flex-direction: column; gap: 12px; margin-top: 12px; }
.export-checkbox { display: flex; align-items: center; gap: 10px; font-size: 16px; cursor: pointer; }
.warning-badge { background: #ffebee; color: #c62828; padding: 2px 8px; border-radius: 12px; font-size: 12px; margin-left: 8px; }
.combined-excel-body { padding: 16px 24px; max-height: calc(100vh - 140px); overflow-y: auto; background: #f9fafc; }
.combined-section { background: white; border-radius: 12px; padding: 16px 20px; margin-bottom: 20px; box-shadow: 0 1px 4px rgba(0,0,0,0.06); }
.combined-section-title { color: #0B2044; font-size: 16px; font-weight: 600; margin: 0 0 12px 0; display: flex; align-items: center; gap: 10px; }
.empty-note { font-weight: normal; color: #999; font-size: 14px; }
.empty-placeholder { color: #999; padding: 12px 0; font-style: italic; text-align: center; }
.summary-table { width: 100%; border-collapse: collapse; font-size: 14px; }
.summary-table th { text-align: left; padding: 10px 8px; background: #f0f2f5; color: #0B2044; font-weight: 600; border-bottom: 2px solid #e0e0e0; }
.summary-table td { padding: 8px; border-bottom: 1px solid #eee; }
.summary-table tr:hover { background: #f8f9ff; }
.excel-wrapper { border: 1px solid #e8ecf1; border-radius: 8px; overflow: hidden; }
.excel-header { display: flex; align-items: center; gap: 20px; margin-bottom: 24px; padding-bottom: 16px; border-bottom: 2px solid #0B2044; }
.excel-logo-area { flex-shrink: 0; }
.excel-logo { max-height: 60px; max-width: 200px; object-fit: contain; }
.excel-title-area { flex: 1; }
.excel-company { color: #0B2044; font-size: 24px; font-weight: 700; margin: 0 0 4px 0; }
.excel-report-title { color: #1E88E5; font-size: 18px; font-weight: 600; margin: 0 0 8px 0; }
.excel-session, .excel-date { color: #666; font-size: 14px; margin: 2px 0; }

.distribution-section { background: white; border-radius: 12px; padding: 20px; margin: 30px 0; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }
.distribution-section h3 { color: #0B2044; margin-bottom: 16px; }
.distribution-bars { display: flex; flex-direction: column; gap: 12px; }
.dist-bar-container { display: flex; align-items: center; gap: 12px; }
.dist-label { width: 120px; font-weight: 600; color: #0B2044; }
.dist-track { flex: 1; height: 20px; background: #e8ecf1; border-radius: 10px; overflow: hidden; }
.dist-fill { height: 100%; border-radius: 10px; transition: width 0.5s ease; }
.dist-percent { width: 50px; text-align: right; font-weight: 600; color: #0B2044; }
</style>