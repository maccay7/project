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

    <!-- ===== MODALS ===== -->

    <!-- Detail Modal (View as Excel) – White Header with Logo -->
    <v-dialog v-model="detailModalVisible" max-width="90%" fullscreen hide-overlay>
      <v-card>
        <v-card-title class="excel-dialog-title-white">
          <div class="header-left">
            <img src="/DuraCapital logo.png" alt="DuraCapital" class="logo" />
            <div class="header-title">
              <h4>{{ selectedInst?.name || 'Instrument' }} – Detailed View</h4>
              <p class="header-meta"><strong>{{ activeSession?.name || 'N/A' }}</strong></p>
            </div>
          </div>
          <v-spacer></v-spacer>
          <button class="btn-close-dialog" @click="detailModalVisible = false">
            <v-icon>mdi-close</v-icon>
          </button>
        </v-card-title>
        <v-card-text class="pa-0" style="height: calc(100vh - 120px);">
          <div class="excel-table-wrapper">
            <table class="excel-table">
              <thead>
                <tr>
                  <th v-for="header in selectedInst?.detailHeaders || []" :key="header">{{ header }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, idx) in selectedInst?.details || []" :key="idx">
                  <td v-for="header in selectedInst?.detailHeaders || []" :key="header">{{ row[header] }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </v-card-text>
        <div class="popup-footer" style="padding:12px 24px; border-top:1px solid #e0e0e0; background:#f9fafc;">
          <span class="valuation-date-footer">Valuation Date: {{ new Date().toISOString().split('T')[0] }}</span>
          <v-spacer></v-spacer>
          <button class="btn-secondary" @click="detailModalVisible = false">Close</button>
        </div>
      </v-card>
    </v-dialog>

    <!-- Combined Modal (View Portfolio as Excel) – White Header with Logo, NO duplicate header inside -->
    <v-dialog v-model="combinedModalVisible" max-width="90%" fullscreen hide-overlay>
      <v-card>
        <v-card-title class="excel-dialog-title-white">
          <div class="header-left">
            <img src="/DuraCapital logo.png" alt="DuraCapital" class="logo" />
            <div class="header-title">
              <h4>Portfolio – Combined Excel View</h4>
              <p class="header-meta"><strong>{{ activeSession?.name || 'N/A' }}</strong></p>
            </div>
          </div>
          <v-spacer></v-spacer>
          <button class="btn-close-dialog" @click="combinedModalVisible = false">
            <v-icon>mdi-close</v-icon>
          </button>
        </v-card-title>
        <v-card-text class="combined-excel-body">
          <!-- Summary Section (no duplicate header) -->
          <div class="combined-section">
            <h4 class="combined-section-title">Summary</h4>
            <div class="excel-table-wrapper">
              <table class="excel-table">
                <thead>
                  <tr>
                    <th @click="sortByColumn('name')" class="sortable-header">
                      <span>Instrument</span>
                      <span class="sort-indicator" v-if="sortColumn === 'name'">{{ sortOrder === 'asc' ? '▲' : '▼' }}</span>
                    </th>
                    <th @click="sortByColumn('faceValue')" class="sortable-header">
                      <span>Face Value ($)</span>
                      <span class="sort-indicator" v-if="sortColumn === 'faceValue'">{{ sortOrder === 'asc' ? '▲' : '▼' }}</span>
                    </th>
                    <th @click="sortByColumn('value')" class="sortable-header">
                      <span>Calculated Value ($)</span>
                      <span class="sort-indicator" v-if="sortColumn === 'value'">{{ sortOrder === 'asc' ? '▲' : '▼' }}</span>
                    </th>
                    <th @click="sortByColumn('difference')" class="sortable-header">
                      <span>Difference ($)</span>
                      <span class="sort-indicator" v-if="sortColumn === 'difference'">{{ sortOrder === 'asc' ? '▲' : '▼' }}</span>
                    </th>
                    <th @click="sortByColumn('count')" class="sortable-header">
                      <span>Count</span>
                      <span class="sort-indicator" v-if="sortColumn === 'count'">{{ sortOrder === 'asc' ? '▲' : '▼' }}</span>
                    </th>
                    <th @click="sortByColumn('avgRate')" class="sortable-header">
                      <span>Avg Rate (%)</span>
                      <span class="sort-indicator" v-if="sortColumn === 'avgRate'">{{ sortOrder === 'asc' ? '▲' : '▼' }}</span>
                    </th>
                    <th @click="sortByColumn('fredBench')" class="sortable-header">
                      <span>FRED Benchmark (%)</span>
                      <span class="sort-indicator" v-if="sortColumn === 'fredBench'">{{ sortOrder === 'asc' ? '▲' : '▼' }}</span>
                    </th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="inst in sortedInstruments" :key="inst.id">
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
          </div>

          <!-- Detailed sections for each instrument -->
          <div v-for="inst in filteredDetails" :key="inst.id" class="combined-section">
            <h4 class="combined-section-title">
              {{ inst.name }} – Details ({{ inst.details.length }} rows)
              <span v-if="!inst.details.length" class="empty-note">(no data)</span>
            </h4>
            <div v-if="inst.details.length" class="excel-table-wrapper">
              <table class="excel-table">
                <thead>
                  <tr>
                    <th v-for="header in inst.detailHeaders" :key="header">{{ header }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(row, idx) in inst.details" :key="idx">
                    <td v-for="header in inst.detailHeaders" :key="header">{{ row[header] }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div v-else class="empty-placeholder">No data available for this instrument.</div>
          </div>
        </v-card-text>
        <div class="popup-footer" style="padding:12px 24px; border-top:1px solid #e0e0e0; background:#f9fafc;">
          <span class="valuation-date-footer">Valuation Date: {{ new Date().toISOString().split('T')[0] }}</span>
          <v-spacer></v-spacer>
          <button class="btn-secondary" @click="combinedModalVisible = false">Close</button>
          <button class="btn-primary" @click="exportCombinedExcel">📥 Download Excel</button>
        </div>
      </v-card>
    </v-dialog>

    <!-- Export Dialog -->
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
const sortColumn = ref('')
const sortOrder = ref('asc')

const totalFaceValue = computed(() => instruments.value.reduce((sum, inst) => sum + (inst.faceValue || 0), 0))
const grandTotal = computed(() => instruments.value.reduce((sum, inst) => sum + inst.value, 0))
const totalInstruments = computed(() => instruments.value.reduce((sum, inst) => sum + (inst.count || 0), 0))
const completedCount = computed(() => instruments.value.filter(i => i.completed).length)

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

const sortedInstruments = computed(() => {
  if (!sortColumn.value) return filteredInstruments.value
  return [...filteredInstruments.value].sort((a, b) => {
    let valA = a[sortColumn.value]
    let valB = b[sortColumn.value]
    if (typeof valA === 'number' && typeof valB === 'number') {
      return sortOrder.value === 'asc' ? valA - valB : valB - valA
    }
    valA = String(valA || '')
    valB = String(valB || '')
    return sortOrder.value === 'asc' ? valA.localeCompare(valB) : valB.localeCompare(valA)
  })
})

function formatNumber(num) {
  return (num || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function sortByColumn(col) {
  if (sortColumn.value === col) {
    sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortColumn.value = col
    sortOrder.value = 'asc'
  }
}

function openInstrument(id) {
  if (!activeSession.value) { alert('Select a session on the Dashboard first'); router.push('/dashboard'); return }
  router.push({ path: `/instrument/${id}`, query: { session: activeSession.value.id } })
}

function goToDashboard() { router.push('/dashboard') }
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

function exportCombinedExcel() {
  // Export the combined modal view as Excel
  const workbook = XLSX.utils.book_new()
  const valuationDate = new Date().toISOString().split('T')[0]
  const sessionName = activeSession.value?.name || 'N/A'

  // Summary sheet
  const summaryRows = []
  summaryRows.push(['', '', '', ''])
  summaryRows.push(['DuraCapital', '', '', ''])
  summaryRows.push(['Portfolio Summary', '', '', ''])
  summaryRows.push(['', '', '', ''])
  summaryRows.push([
    'Instrument Name',
    'Face Value ($)',
    'Calculated Value ($)',
    'Difference ($)',
    'Count',
    'Avg Rate (%)',
    'FRED Benchmark (%)',
    'Status'
  ])
  filteredInstruments.value.forEach(inst => {
    summaryRows.push([
      inst.name,
      inst.faceValue || 0,
      inst.value,
      (inst.faceValue || 0) - inst.value,
      inst.count,
      inst.avgRate !== null ? inst.avgRate : '—',
      inst.fredBench !== null ? inst.fredBench : '—',
      inst.statusText
    ])
  })
  summaryRows.push([
    'TOTAL',
    totalFaceValue.value,
    grandTotal.value,
    totalFaceValue.value - grandTotal.value,
    totalInstruments.value,
    '',
    '',
    ''
  ])
  const summarySheet = XLSX.utils.aoa_to_sheet(summaryRows)
  summarySheet['!cols'] = [{ wch: 20 }, { wch: 18 }, { wch: 20 }, { wch: 18 }, { wch: 10 }, { wch: 14 }, { wch: 18 }, { wch: 14 }]
  XLSX.utils.book_append_sheet(workbook, summarySheet, 'Summary')

  // Detail sheets
  for (const inst of filteredDetails.value) {
    if (inst.details && inst.details.length) {
      const detailData = [
        [`${inst.name} – Detailed Instruments`],
        [`Session: ${sessionName}`],
        [`Valuation Date: ${valuationDate}`],
        [],
        inst.detailHeaders,
        ...inst.details.map(row => inst.detailHeaders.map(h => row[h] !== undefined ? row[h] : ''))
      ]
      const sheet = XLSX.utils.aoa_to_sheet(detailData)
      sheet['!cols'] = inst.detailHeaders.map(() => ({ wch: 16 }))
      XLSX.utils.book_append_sheet(workbook, sheet, inst.name.substring(0, 31))
    }
  }

  XLSX.writeFile(workbook, `Portfolio_Summary_${sessionName}_${valuationDate}.xlsx`)
  combinedModalVisible.value = false
}

async function loadSummary() {
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
  instruments.value = await Promise.all(templates.map(async (template) => {
    const wf = await sessionManager.getInstrumentWorkflow(sid, template.id)
    let details = []
    let totalValue = 0
    let totalFaceValue = 0
    let totalAvgRate = 0
    let instrumentCount = 0

    // Try to get instrument summary first (this contains calculated rows from each sheet)
    const summaryKey = `${template.id}_session_${sid}_summary`
    const savedSummary = localStorage.getItem(summaryKey)
    if (savedSummary) {
      try {
        const summaryData = JSON.parse(savedSummary)
        if (summaryData.rows && summaryData.rows.length) {
          details = summaryData.rows
          instrumentCount = details.length
          details.forEach(row => {
            const value = parseFloat(row['Total Value'] || row['Calculated Value'] || 0)
            const faceValue = parseFloat(row['Face Value'] || row['Amount'] || row['Principal'] || 0)
            const rate = parseFloat(row['Avg Rate'] || row['Coupon Rate'] || row['Discount Rate'] || 0)
            if (!isNaN(value)) totalValue += value
            if (!isNaN(faceValue)) totalFaceValue += faceValue
            if (!isNaN(rate)) totalAvgRate += rate
          })
        }
      } catch(e) {}
    }

    // Fallback to workflow data
    if (!details.length && wf && wf.cleanedData && wf.cleanedData.length) {
      details = wf.cleanedData
      instrumentCount = details.length
      details.forEach(row => {
        const value = parseFloat(row['Total Value'] || row['Calculated Value'] || 0)
        const faceValue = parseFloat(row['Face Value'] || row['Amount'] || row['Principal'] || 0)
        const rate = parseFloat(row['Avg Rate'] || row['Coupon Rate'] || row['Discount Rate'] || 0)
        if (!isNaN(value)) totalValue += value
        if (!isNaN(faceValue)) totalFaceValue += faceValue
        if (!isNaN(rate)) totalAvgRate += rate
      })
    } else if (!details.length && wf && wf.data && wf.data.length) {
      details = wf.data
      instrumentCount = details.length
    }

    const avgRate = instrumentCount > 0 && totalAvgRate > 0 ? totalAvgRate / instrumentCount : null
    const completed = instrumentCount > 0
    const value = totalValue
    const faceValue = totalFaceValue
    const difference = faceValue - value

    // Try to get FRED benchmark from stored calculations
    let fredBench = null
    if (wf && wf.calculations && wf.calculations.fred) {
      fredBench = wf.calculations.fred.benchmark_rate
    } else {
      // Try to get from localStorage
      const calcKey = `${template.id}_fred_benchmark`
      const savedFred = localStorage.getItem(calcKey)
      if (savedFred) {
        try { fredBench = parseFloat(savedFred) } catch(e) {}
      }
    }

    const headers = details.length ? Object.keys(details[0]) : []
    detailsList.push({
      id: template.id,
      name: template.name,
      details: details,
      detailHeaders: headers
    })

    return {
      ...template,
      value,
      faceValue,
      difference,
      count: instrumentCount,
      avgRate,
      fredBench,
      completed,
      statusClass: completed ? 'completed' : 'pending',
      statusText: completed ? 'Completed' : 'Not started',
      statusIcon: completed ? 'mdi-check-circle' : 'mdi-clock-outline'
    }
  }))

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

  const summaryRows = []
  summaryRows.push(['', '', '', ''])
  summaryRows.push(['DuraCapital', '', '', ''])
  summaryRows.push(['Portfolio Summary', '', '', ''])
  summaryRows.push([`Session: ${activeSession.value.name}`, '', '', ''])
  summaryRows.push([`Valuation Date: ${valuationDate}`, '', '', ''])
  summaryRows.push(['', '', '', ''])
  summaryRows.push([
    'Instrument Name',
    'Face Value ($)',
    'Calculated Value ($)',
    'Difference ($)',
    'Count',
    'Avg Rate (%)',
    'FRED Benchmark (%)',
    'Status'
  ])
  toExport.forEach(inst => {
    summaryRows.push([
      inst.name,
      inst.faceValue || 0,
      inst.value,
      (inst.faceValue || 0) - inst.value,
      inst.count,
      inst.avgRate !== null ? inst.avgRate : '—',
      inst.fredBench !== null ? inst.fredBench : '—',
      inst.statusText
    ])
  })
  summaryRows.push([
    'TOTAL',
    totalFaceValue.value,
    grandTotal.value,
    totalFaceValue.value - grandTotal.value,
    totalInstruments.value,
    '',
    '',
    ''
  ])
  const summarySheet = XLSX.utils.aoa_to_sheet(summaryRows)
  summarySheet['!cols'] = [{ wch: 20 }, { wch: 18 }, { wch: 20 }, { wch: 18 }, { wch: 10 }, { wch: 14 }, { wch: 18 }, { wch: 14 }]
  XLSX.utils.book_append_sheet(workbook, summarySheet, 'Summary')

  for (const inst of instrumentsWithDetails.value) {
    if (selectedExportInstruments.value[inst.id] && inst.details && inst.details.length) {
      const detailData = [
        [`${inst.name} – Detailed Instruments`],
        [`Session: ${activeSession.value.name}`],
        [`Valuation Date: ${valuationDate}`],
        [],
        inst.detailHeaders,
        ...inst.details.map(row => inst.detailHeaders.map(h => row[h] !== undefined ? row[h] : ''))
      ]
      const sheet = XLSX.utils.aoa_to_sheet(detailData)
      sheet['!cols'] = inst.detailHeaders.map(() => ({ wch: 16 }))
      XLSX.utils.book_append_sheet(workbook, sheet, inst.name.substring(0, 31))
    }
  }

  XLSX.writeFile(workbook, `Portfolio_Summary_${activeSession.value.name}_${valuationDate}.xlsx`)
  showExportDialog.value = false
}

onMounted(async () => {
  await loadSummary()
})
</script>

<style scoped>
/* ===== SUMMARY PAGE STYLES ===== */
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

.excel-dialog-title-white {
  background: white;
  color: #0B2044;
  padding: 16px 24px;
  display: flex;
  align-items: center;
  border-bottom: 2px solid #e0e0e0;
}
.excel-dialog-title-white .logo {
  height: 40px;
  width: auto;
  object-fit: contain;
}
.excel-dialog-title-white .header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}
.excel-dialog-title-white .header-title h4 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #0B2044;
}
.excel-dialog-title-white .header-meta {
  margin: 2px 0 0 0;
  font-size: 13px;
  color: #666;
}
.excel-dialog-title-white .btn-close-dialog {
  background: transparent;
  border: none;
  color: #666;
  cursor: pointer;
  padding: 8px;
  border-radius: 50%;
  font-size: 20px;
}
.excel-dialog-title-white .btn-close-dialog:hover {
  background: #f0f0f0;
  color: #0B2044;
}

.btn-close-dialog { background: transparent; border: none; color: #666; cursor: pointer; padding: 8px; border-radius: 50%; }
.btn-close-dialog:hover { background: #f0f0f0; color: #0B2044; }

.combined-excel-body { padding: 16px 24px; max-height: calc(100vh - 140px); overflow-y: auto; background: #f9fafc; }
.combined-section { background: white; border-radius: 12px; padding: 16px 20px; margin-bottom: 20px; box-shadow: 0 1px 4px rgba(0,0,0,0.06); }
.combined-section-title { color: #0B2044; font-size: 16px; font-weight: 600; margin: 0 0 12px 0; display: flex; align-items: center; gap: 10px; }
.empty-note { font-weight: normal; color: #999; font-size: 14px; }
.empty-placeholder { color: #999; padding: 12px 0; font-style: italic; text-align: center; }

.excel-table-wrapper { overflow: auto; border: 1px solid #d4d4d4; border-radius: 4px; background: white; max-height: 500px; margin: 16px 0; }
.excel-table { width: 100%; border-collapse: collapse; font-size: 13px; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #000; }
.excel-table thead { position: sticky; top: 0; z-index: 10; }
.excel-table th { background: #0B2044; color: white; border: 1px solid #1a3a6e; padding: 10px 14px; text-align: left; font-weight: 600; font-size: 12px; white-space: nowrap; letter-spacing: 0.3px; }
.excel-table td { border: 1px solid #d4d4d4; padding: 8px 14px; text-align: left; font-size: 13px; font-variant-numeric: tabular-nums; }
.excel-table tbody tr:nth-child(even) { background: #f9fafc; }
.excel-table tbody tr:hover { background: #e8f0fe; }

.sortable-header { cursor: pointer; transition: background 0.2s; }
.sortable-header:hover { background: #1a3a6e; }
.sort-indicator { margin-left: 6px; font-size: 10px; color: #fff; }

.export-instrument-select { display: flex; flex-direction: column; gap: 12px; margin-top: 12px; }
.export-checkbox { display: flex; align-items: center; gap: 10px; font-size: 16px; cursor: pointer; }
.warning-badge { background: #ffebee; color: #c62828; padding: 2px 8px; border-radius: 12px; font-size: 12px; margin-left: 8px; }

.distribution-section { background: white; border-radius: 12px; padding: 20px; margin: 30px 0; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }
.distribution-section h3 { color: #0B2044; margin-bottom: 16px; }
.distribution-bars { display: flex; flex-direction: column; gap: 12px; }
.dist-bar-container { display: flex; align-items: center; gap: 12px; }
.dist-label { width: 120px; font-weight: 600; color: #0B2044; }
.dist-track { flex: 1; height: 20px; background: #e8ecf1; border-radius: 10px; overflow: hidden; }
.dist-fill { height: 100%; border-radius: 10px; transition: width 0.5s ease; }
.dist-percent { width: 50px; text-align: right; font-weight: 600; color: #0B2044; }

.popup-footer {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 12px;
  padding: 12px 24px;
  background: #f9fafc;
  border-top: 1px solid #e0e0e0;
  flex-shrink: 0;
  flex-wrap: wrap;
}
.valuation-date-footer { color: #666; font-size: 13px; }

@media (max-width: 768px) {
  .summary-page { padding: 16px; }
  .hero-header { flex-direction: column; }
  .grand-pill { width: 100%; text-align: center; }
  .summary-cards { grid-template-columns: 1fr; }
  .kpi-strip { flex-direction: column; }
  .export-all-section { flex-direction: column; align-items: center; }
  .action-buttons { flex-direction: column; align-items: center; }
  .dist-bar-container { flex-wrap: wrap; }
  .dist-label { width: 80px; }
  .excel-dialog-title-white { flex-wrap: wrap; gap: 8px; }
  .excel-dialog-title-white .header-left { flex-wrap: wrap; }
}
</style>