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

      <div class="kpi-strip">
        <div v-for="stat in extendedKpis" :key="stat.label" class="kpi-card">
          <div class="kpi-top-bar"></div>
          <div class="kpi-icon" :style="{ background: stat.gradient }">
            <v-icon size="28" color="white">{{ stat.icon }}</v-icon>
          </div>
          <div class="kpi-info">
            <div class="kpi-value">{{ stat.value }}</div>
            <div class="kpi-title">{{ stat.label }}</div>
          </div>
        </div>
      </div>

      <div class="analytics-section" style="margin-bottom: 24px;">
        <h3 style="margin-bottom: 16px; color: #0B2044; font-size: 18px; font-weight: 600;">
          <i class="fas fa-chart-line" style="color: #1a4d8f; margin-right: 8px;"></i> Descriptive Analytics
        </h3>
        <div class="analytics-cards">
          <div class="kpi-card simple-kpi">
            <div class="kpi-top-bar"></div>
            <div class="kpi-info">
              <div class="kpi-value">{{ analyticsData['Number of Records'] || '0' }}</div>
              <div class="kpi-title">Number of Instruments</div>
            </div>
          </div>
          <div class="kpi-card simple-kpi">
            <div class="kpi-top-bar"></div>
            <div class="kpi-info">
              <div class="kpi-value">${{ analyticsData['Total Face Value'] || '0.00' }}</div>
              <div class="kpi-title">Total Face Value</div>
            </div>
          </div>
          <div class="kpi-card simple-kpi">
            <div class="kpi-top-bar"></div>
            <div class="kpi-info">
              <div class="kpi-value">{{ analyticsData['Weighted Average Yield'] || '0.00' }}%</div>
              <div class="kpi-title">Weighted Avg Yield</div>
            </div>
          </div>
          <div class="kpi-card simple-kpi">
            <div class="kpi-top-bar"></div>
            <div class="kpi-info">
              <div class="kpi-value">{{ analyticsData['Weighted Average Maturity'] || '0.00' }}</div>
              <div class="kpi-title">Weighted Avg Maturity</div>
            </div>
          </div>
          <div class="kpi-card simple-kpi">
            <div class="kpi-top-bar"></div>
            <div class="kpi-info">
              <div class="kpi-value">{{ analyticsData['Average Rate'] || '0.00' }}%</div>
              <div class="kpi-title">Average Rate</div>
            </div>
          </div>
        </div>
      </div>

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

      <div v-for="inst in instrumentsWithDetails" :key="inst.id" class="detail-section">
        <div class="detail-header">
          <h3>{{ inst.name }} – Detailed Instruments ({{ inst.details.length }} rows)</h3>
          <div class="detail-actions">
            <button
              class="btn-view-details"
              @click="openDetailModal(inst)"
              :disabled="!inst.details.length"
            >
              <v-icon size="16">mdi-eye</v-icon>
              {{ inst.details.length ? 'View as Excel' : 'No data' }}
            </button>
          </div>
        </div>
        <div v-if="!inst.details.length" class="empty-note-block">
          No instrument records were found in this session for {{ inst.name }}.
          <span v-if="inst.completed">The class is marked completed but no rows were returned — open the workflow to inspect.</span>
        </div>
      </div>

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
            <span v-if="activeValuationDate" class="valuation-date-footer">Valuation Date: {{ activeValuationDate }}</span>
            <v-spacer></v-spacer>
            <button class="btn-secondary" @click="detailModalVisible = false">Close</button>
          </div>
        </v-card>
      </v-dialog>

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
            <span v-if="activeValuationDate" class="valuation-date-footer">Valuation Date: {{ activeValuationDate }}</span>
            <v-spacer></v-spacer>
            <button class="btn-secondary" @click="combinedModalVisible = false">Close</button>
          </div>
        </v-card>
      </v-dialog>

      <v-dialog v-model="showExportDialog" max-width="500px">
        <v-card>
          <v-card-title>Select instruments to export</v-card-title>
          <v-card-text>
            <div class="export-instrument-select">
              <label class="export-checkbox portfolio-option">
                <input type="checkbox" v-model="downloadPortfolioOption" />
                Portfolio Excel
              </label>
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

    </div>
  </FixedLayout>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import FixedLayout from '@/components/FixedLayout.vue'
import sessionManager from '@/services/sessionManager.js'
import api from '@/services/api.js'
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
const downloadPortfolioOption = ref(false)
const sortColumn = ref('')
const sortOrder = ref('asc')
const loading = ref(false)
const error = ref('')

const PORTFOLIO_SNAPSHOT_KEY = '__portfolio_summary__'

const EXCLUDED_COLUMNS = new Set([
  '_raw', '_source', 'index', '__v',
  'instrument_name', 'instrument_type',
  'worksheet', 'workbook', 'valuationtype',
  'currency', 'day_count_convention', 'derivations',
  'discount_amount', 'yield_curve_rate', 'term_days',
  'money_market_yield', 'holding_period_yield',
  'carrying_value'
].map(s => s.toLowerCase().replace(/[_\s\-]+/g, '')))

function isExcludedColumn(col) {
  if (!col) return false
  const normalized = String(col).toLowerCase().replace(/[_\s\-]+/g, '')
  if (EXCLUDED_COLUMNS.has(normalized)) return true
  if (normalized.startsWith('derivation')) return true
  return false
}

function formatColumnHeader(col) {
  if (!col) return col
  return String(col)
    .replace(/_/g, ' ')
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/\b\w/g, c => c.toUpperCase())
}

function getUniqueHeaders(headers) {
  const filtered = headers.filter(h => h && !isExcludedColumn(h))
  const seen = new Set()
  return filtered.filter(h => {
    const base = h.replace(/_\d+$/, '').trim()
    const key = base.toLowerCase()
    if (seen.has(key)) return false
    seen.add(key)
    return true
  })
}

const activeValuationDate = computed(() => {
  const s = activeSession.value
  if (s) {
    if (s.valuationDate) return s.valuationDate
    if (s.valuation_date) return s.valuation_date
  }
  try {
    const stored =
      sessionStorage.getItem('valuationDate') ||
      sessionStorage.getItem('valuation_date') ||
      localStorage.getItem('valuationDate') ||
      localStorage.getItem('valuation_date')
    if (stored) return stored
  } catch (e) { /* ignore */ }
  return null
})

const analyticsData = computed(() => {
  const allDetails = instrumentsWithDetails.value.flatMap(inst => inst.details || [])
  if (!allDetails.length) return {}

  const getValue = (row) => parseFloat(row['Total Value'] ?? row['total_value'] ?? row['Calculated Value'] ?? row['calculated_value'] ?? row['Value'] ?? row['value'] ?? 0)
  const getYield = (row) => parseFloat(row['Yield'] ?? row['yield'] ?? row['Rate'] ?? row['rate'] ?? row['Interest Rate'] ?? row['interest_rate'] ?? row['Coupon Rate'] ?? row['coupon_rate'] ?? row['Discount Rate'] ?? row['discount_rate'] ?? 0)
  const getMaturity = (row) => parseFloat(row['Days to Maturity'] ?? row['days_to_maturity'] ?? row['Term'] ?? row['term'] ?? row['Maturity'] ?? row['maturity'] ?? 0)

  const values = allDetails.map(getValue).filter(v => !isNaN(v) && v > 0)
  const yields = allDetails.map(getYield).filter(v => !isNaN(v))
  const maturities = allDetails.map(getMaturity).filter(v => !isNaN(v) && v > 0)

  const stats = {}
  if (values.length) {
    const sum = values.reduce((a, b) => a + b, 0)
    const avgRate = yields.length ? yields.reduce((a,b) => a+b, 0) / yields.length : null
    stats['Number of Records'] = allDetails.length
    stats['Total Face Value'] = sum
    if (yields.length && values.length) {
      const weightedYield = yields.reduce((a, b, i) => a + b * values[i], 0) / (values.reduce((a, b) => a + b, 1) || 1)
      stats['Weighted Average Yield'] = weightedYield
    }
    if (maturities.length && values.length) {
      const weightedMaturity = maturities.reduce((a, b, i) => a + b * values[i], 0) / (values.reduce((a, b) => a + b, 1) || 1)
      stats['Weighted Average Maturity'] = weightedMaturity
    }
    if (avgRate !== null) stats['Average Rate'] = avgRate
  }
  for (const [k, v] of Object.entries(stats)) {
    if (typeof v === 'number') {
      const isTimeField = /day|maturity|duration|term|month|year|week|time/.test(k.toLowerCase())
      stats[k] = isTimeField
        ? Math.round(v).toLocaleString()
        : v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
    }
  }
  return stats
})

const totalFaceValue = computed(() => instruments.value.reduce((sum, inst) => sum + (inst.faceValue || 0), 0))
const grandTotal = computed(() => instruments.value.reduce((sum, inst) => sum + (inst.value || 0), 0))
const totalInstruments = computed(() => instruments.value.reduce((sum, inst) => sum + (inst.count || 0), 0))
const completedCount = computed(() => instruments.value.filter(i => i.completed).length)

const extendedKpis = computed(() => [
  { label: 'Total Face Value', value: '$' + formatNumber(totalFaceValue.value), icon: 'mdi-cash', gradient: 'linear-gradient(135deg, #0B2044, #1a3a6e)' },
  { label: 'Total Calculated', value: '$' + formatNumber(grandTotal.value), icon: 'mdi-calculator', gradient: 'linear-gradient(135deg, #1E88E5, #42a5f5)' },
  { label: 'Difference', value: '$' + formatNumber(totalFaceValue.value - grandTotal.value), icon: 'mdi-arrow-right', gradient: 'linear-gradient(135deg, #FFC107, #FF9800)' },
  { label: 'Instrument Types', value: `${completedCount.value}/3`, icon: 'mdi-chart-pie', gradient: 'linear-gradient(135deg, #4CAF50, #2E7D32)' }
])

const filteredInstruments = computed(() => instruments.value.filter(inst => selectedExportInstruments.value[inst.id]))
const filteredDetails = computed(() => instrumentsWithDetails.value.filter(inst => selectedExportInstruments.value[inst.id]))

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
  if (num === undefined || num === null) return '0.00'
  const rounded = Math.round(num * 100) / 100
  return rounded.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
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
  if (!activeSession.value) {
    alert('Select a session on the Dashboard first')
    router.push('/dashboard')
    return
  }
  // Ensure the session we're opening is the one the Dashboard/InstrumentView will read.
  try {
    sessionManager.setActiveSession(activeSession.value)
    localStorage.setItem('dura_active_session_id', activeSession.value.id)
  } catch (e) { /* ignore */ }
  router.push({ path: `/instrument/${id}`, query: { session: activeSession.value.id } })
}

function goToDashboard() { router.push('/dashboard') }

function goToReport() {
  if (!activeSession.value) { alert('No active session'); return }
  const lastInstrument = localStorage.getItem('dura_last_instrument') || 'money-market'
  router.push({ path: `/instrument/${lastInstrument}`, query: { session: activeSession.value.id, tab: 'reports' } })
}

function openDetailModal(inst) {
  if (!inst.details || !inst.details.length) return
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

/* ---------- Excel helpers (unchanged, but kept working) ---------- */
function isPercentageField(col) {
  const lowerCol = String(col).toLowerCase()
  return lowerCol.includes('rate') || lowerCol.includes('yield') || lowerCol.includes('discount') || lowerCol.includes('coupon')
}

function formatForExcel(value, type = 'number', key = '') {
  if (value === null || value === undefined || value === '') return ''
  const num = parseFloat(value)
  if (isNaN(num)) return value
  const isTimeField = String(key).toLowerCase().includes('day') ||
    String(key).toLowerCase().includes('maturity') ||
    String(key).toLowerCase().includes('duration') ||
    String(key).toLowerCase().includes('term')
  if (isTimeField) return Math.round(num)
  if (type === 'percentage' || type === 'money') return Math.round(num * 100) / 100
  return num
}

function exportCombinedExcel() {
  const workbook = XLSX.utils.book_new()
  const valuationDate = activeValuationDate.value || ''
  const sessionName = activeSession.value?.name || 'N/A'

  const summaryRows = []
  summaryRows.push(['', '', '', ''])
  summaryRows.push(['DuraCapital', '', '', ''])
  summaryRows.push(['Portfolio Summary', '', '', ''])
  summaryRows.push(['', '', '', ''])
  summaryRows.push(['Instrument Name','Face Value ($)','Calculated Value ($)','Difference ($)','Count','Avg Rate (%)','FRED Benchmark (%)','Status'])
  filteredInstruments.value.forEach(inst => {
    summaryRows.push([
      inst.name,
      formatForExcel(inst.faceValue, 'money'),
      formatForExcel(inst.value, 'money'),
      formatForExcel((inst.faceValue || 0) - inst.value, 'money'),
      inst.count,
      inst.avgRate !== null ? formatForExcel(inst.avgRate, 'percentage') : '—',
      inst.fredBench !== null ? formatForExcel(inst.fredBench, 'percentage') : '—',
      inst.statusText
    ])
  })
  summaryRows.push(['TOTAL', formatForExcel(totalFaceValue.value, 'money'), formatForExcel(grandTotal.value, 'money'),
    formatForExcel(totalFaceValue.value - grandTotal.value, 'money'), totalInstruments.value, '', '', ''])
  const summarySheet = XLSX.utils.aoa_to_sheet(summaryRows)
  summarySheet['!cols'] = [{ wch: 20 },{ wch: 18 },{ wch: 20 },{ wch: 18 },{ wch: 10 },{ wch: 14 },{ wch: 18 },{ wch: 14 }]
  XLSX.utils.book_append_sheet(workbook, summarySheet, 'Summary')

  for (const inst of filteredDetails.value) {
    if (inst.details && inst.details.length) {
      const headers = getUniqueHeaders(inst.detailHeaders)
      const headerRows = [[`${inst.name} – Detailed Instruments`], [`Session: ${sessionName}`]]
      if (valuationDate) headerRows.push([`Valuation Date: ${valuationDate}`])
      headerRows.push([])
      const detailData = [...headerRows, headers.map(formatColumnHeader), ...inst.details.map(row => headers.map(h => row[h] !== undefined ? row[h] : ''))]
      const sheet = XLSX.utils.aoa_to_sheet(detailData)
      sheet['!cols'] = headers.map(() => ({ wch: 16 }))
      XLSX.utils.book_append_sheet(workbook, sheet, inst.name.substring(0, 31))
    }
  }

  const filenameSuffix = valuationDate ? `_${valuationDate}` : ''
  XLSX.writeFile(workbook, `Portfolio_Summary_${sessionName}${filenameSuffix}.xlsx`)
  combinedModalVisible.value = false
}

function downloadPortfolioExcel() {
  const hasSelection = Object.values(selectedExportInstruments.value).some(v => v === true)
  if (!hasSelection) {
    instruments.value.forEach(inst => {
      if (inst.completed || inst.value > 0) selectedExportInstruments.value[inst.id] = true
    })
  }
  exportCombinedExcel()
  showExportDialog.value = false
}

function exportToExcel() {
  if (!activeSession.value) { alert('No active session'); return }
  const toExport = instruments.value.filter(inst => selectedExportInstruments.value[inst.id])
  if (toExport.length === 0 && !downloadPortfolioOption.value) { alert('No instruments selected for export'); return }

  const workbook = XLSX.utils.book_new()
  const valuationDate = activeValuationDate.value || ''
  const summaryRows = []
  summaryRows.push(['', '', '', ''])
  summaryRows.push(['DuraCapital', '', '', ''])
  summaryRows.push(['Portfolio Summary', '', '', ''])
  summaryRows.push([`Session: ${activeSession.value.name}`, '', '', ''])
  if (valuationDate) summaryRows.push([`Valuation Date: ${valuationDate}`, '', '', ''])
  summaryRows.push(['', '', '', ''])
  summaryRows.push(['Instrument Name','Face Value ($)','Calculated Value ($)','Difference ($)','Count','Avg Rate (%)','FRED Benchmark (%)','Status'])
  toExport.forEach(inst => {
    summaryRows.push([
      inst.name,
      formatForExcel(inst.faceValue, 'money'),
      formatForExcel(inst.value, 'money'),
      formatForExcel((inst.faceValue || 0) - inst.value, 'money'),
      inst.count,
      inst.avgRate !== null ? formatForExcel(inst.avgRate, 'percentage') : '—',
      inst.fredBench !== null ? formatForExcel(inst.fredBench, 'percentage') : '—',
      inst.statusText
    ])
  })
  summaryRows.push(['TOTAL', formatForExcel(totalFaceValue.value, 'money'), formatForExcel(grandTotal.value, 'money'),
    formatForExcel(totalFaceValue.value - grandTotal.value, 'money'), totalInstruments.value, '', '', ''])
  const summarySheet = XLSX.utils.aoa_to_sheet(summaryRows)
  summarySheet['!cols'] = [{ wch: 20 },{ wch: 18 },{ wch: 20 },{ wch: 18 },{ wch: 10 },{ wch: 14 },{ wch: 18 },{ wch: 14 }]
  XLSX.utils.book_append_sheet(workbook, summarySheet, 'Summary')

  for (const inst of toExport) {
    const instDetails = instrumentsWithDetails.value.find(d => d.id === inst.id)
    if (instDetails?.details && instDetails.details.length) {
      const headers = getUniqueHeaders(instDetails.detailHeaders)
      const headerRows = [[`${inst.name} – Detailed Instruments`], [`Session: ${activeSession.value.name}`]]
      if (valuationDate) headerRows.push([`Valuation Date: ${valuationDate}`])
      headerRows.push([])
      const detailData = [...headerRows, headers.map(formatColumnHeader), ...instDetails.details.map(row => headers.map(h => row[h] !== undefined ? row[h] : ''))]
      const sheet = XLSX.utils.aoa_to_sheet(detailData)
      sheet['!cols'] = headers.map(() => ({ wch: 16 }))
      XLSX.utils.book_append_sheet(workbook, sheet, inst.name.substring(0, 31))
    }
  }

  const filenameSuffix = valuationDate ? `_${valuationDate}` : ''
  XLSX.writeFile(workbook, `Portfolio_Summary_${activeSession.value.name}${filenameSuffix}.xlsx`)
  if (downloadPortfolioOption.value) downloadPortfolioExcel()
  showExportDialog.value = false
}

/* ---------- Snapshot publish (now uses real instrument rows) ---------- */
async function publishPortfolioSnapshot(sid) {
  try {
    const instrumentsWithDetailsList = []

    for (const inst of instruments.value) {
      const wf = await sessionManager.getInstrumentWorkflow(sid, inst.id)
      const instSummary = wf?.instrumentSummary || { rows: [], columns: [] }
      const aggCalc = wf?.allCalculations || wf?.calculations || {}

      instrumentsWithDetailsList.push({
        id: inst.id,
        name: inst.name,
        details: instSummary.rows || [],
        detailHeaders: instSummary.columns || [],
        aggregate: aggCalc,
        completed: inst.completed,
        count: inst.count,
        value: inst.value,
        avgRate: inst.avgRate
      })
    }

    const snapshot = {
      sessionId: String(sid),
      sessionName: activeSession.value?.name || '',
      valuationDate: activeValuationDate.value,
      generatedAt: new Date().toISOString(),
      instruments: instruments.value.map(inst => ({
        id: inst.id,
        name: inst.name,
        value: inst.value,
        faceValue: inst.faceValue,
        difference: inst.difference,
        count: inst.count,
        avgRate: inst.avgRate,
        fredBench: inst.fredBench,
        completed: inst.completed,
        statusText: inst.statusText
      })),
      instrumentsWithDetails: instrumentsWithDetailsList
    }

    await sessionManager.saveWorksheetData(sid, PORTFOLIO_SNAPSHOT_KEY, snapshot)
  } catch (e) {
    console.warn('Failed to publish portfolio summary snapshot:', e)
  }
}

/* ---------- The FIXED summary loader ---------- */
async function loadSummary() {
  loading.value = true
  error.value = ''

  try {
    // --- 1. Resolve session robustly ---
    let session = sessionManager.getActiveSession()
    if (session) {
      // Force-refresh so we pick up the latest instrumentWorkflow saved
      // by InstrumentView just before navigation.
      try {
        const fresh = await sessionManager.getSession(session.id, true)
        if (fresh) {
          session = fresh
          sessionManager.setActiveSession(fresh)
        }
      } catch (e) {
        console.warn('Force refresh before summary failed:', e)
      }
    }
    if (!session) {
      const sid = sessionManager.getActiveSessionId()
      if (sid) {
        await sessionManager.getSession(sid, true)
        session = sessionManager.getActiveSession()
      }
    }
    if (!session) {
      const route = router.currentRoute.value
      const sessionId = route.query.session || route.query.session_id
      if (sessionId) {
        await sessionManager.getSession(sessionId, true)
        session = sessionManager.getActiveSession()
      }
    }
    if (!session) {
      try {
        const localSid = localStorage.getItem('dura_active_session_id') || sessionStorage.getItem('dura_active_session_id')
        if (localSid) {
          await sessionManager.getSession(localSid, true)
          session = sessionManager.getActiveSession()
        }
      } catch (e) { console.warn('Failed to get session from storage:', e) }
    }
    activeSession.value = session

    if (!activeSession.value) {
      instruments.value = []
      instrumentsWithDetails.value = []
      loading.value = false
      return
    }

    const sid = activeSession.value.id

    // --- 2. Optional: try backend summaries for aggregates only ---
    let backendSummaries = []
    try {
      const response = await api.portfolioAPI.getSummaries(sid)
      if (response?.success && Array.isArray(response.data)) backendSummaries = response.data
    } catch (e) {
      console.warn('Backend portfolio summaries unavailable, using workflow data:', e)
    }

    const templates = [
      { id: 'money-market', name: 'Money Market', icon: 'mdi-chart-line', gradient: 'linear-gradient(135deg, #1E88E5, #0B2044)', rateLabel: 'Avg interest rate', barColor: '#1E88E5' },
      { id: 'bonds', name: 'Bonds', icon: 'mdi-chart-timeline', gradient: 'linear-gradient(135deg, #4CAF50, #2E7D32)', rateLabel: 'Avg coupon', barColor: '#4CAF50' },
      { id: 'tbills', name: 'T-Bills', icon: 'mdi-finance', gradient: 'linear-gradient(135deg, #FFC107, #FF9800)', rateLabel: 'Avg discount', barColor: '#FF9800' }
    ]

    const getVal = (row, ...keys) => {
      for (const key of keys) {
        const val = row[key]
        if (val !== undefined && val !== null && val !== '') {
          const num = parseFloat(val)
          if (!isNaN(num)) return num
        }
      }
      return 0
    }

    const detailsList = []
    const instrumentResults = []

    for (const template of templates) {
      const backendSummary = backendSummaries.find(s => s.id === template.id)

      let details = []
      let detailHeaders = []
      let totalValue = 0, totalFaceValue = 0, totalRateSum = 0, rateCount = 0
      let totalFredBench = 0, fredBenchCount = 0
      let instrumentCount = 0

      // === Always load the workflow: this is the source of truth for instrument rows ===
      let wfType = null
      try {
        wfType = await sessionManager.getInstrumentWorkflow(sid, template.id)
      } catch (e) {
        console.warn(`Failed to read workflow for ${template.id}:`, e)
      }

      const instSummary = wfType?.instrumentSummary || { rows: [], columns: [] }
      const aggCalc = wfType?.allCalculations || wfType?.calculations || {}

      // Prefer backend-published details if present AND non-empty, else workflow's instrumentSummary
      if (backendSummary && Array.isArray(backendSummary.details) && backendSummary.details.length > 0) {
        details = backendSummary.details
        detailHeaders = backendSummary.detailHeaders || instSummary.columns || []
        totalValue = backendSummary.totalValue ?? 0
        totalFaceValue = backendSummary.faceValue ?? 0
        instrumentCount = backendSummary.count ?? details.length
        totalRateSum = backendSummary.avgRate ?? 0
        rateCount = instrumentCount > 0 ? 1 : 0
      } else {
        // The important change: use instrument-level rows, not portfolio-summary rows
        details = instSummary.rows || []
        detailHeaders = instSummary.columns || []

        totalValue = aggCalc.totalValue ?? aggCalc.total_value ?? 0
        totalFaceValue = aggCalc.totalPrincipal ?? aggCalc.total_principal
          ?? aggCalc.totalFaceValue ?? aggCalc.total_face_value ?? 0
        instrumentCount = aggCalc.instrumentCount ?? aggCalc.instrument_count ?? details.length
        totalRateSum = aggCalc.avgRate ?? aggCalc.avg_rate
          ?? aggCalc.weightedAvgRate ?? aggCalc.weighted_avg_rate ?? 0
        rateCount = totalRateSum ? 1 : 0

        if (aggCalc.fred?.benchmark_rate != null) {
          totalFredBench = aggCalc.fred.benchmark_rate
          fredBenchCount = 1
        }

        // Fallback if aggregates were not persisted
        if ((!totalValue || !instrumentCount) && details.length) {
          totalValue = 0
          totalFaceValue = 0
          let rateSum = 0
          let cnt = 0
          details.forEach(row => {
            const v = getVal(row, 'Total Value', 'total_value', 'Calculated Value', 'calculated_value', 'Value', 'value')
            const fv = getVal(row, 'Face Value', 'face_value', 'Amount', 'amount', 'Principal', 'principal', 'Total Principal', 'total_principal')
            const r = getVal(row, 'Average Rate', 'average_rate', 'Avg Rate', 'avg_rate', 'Rate', 'rate', 'Coupon Rate', 'coupon_rate', 'Discount Rate', 'discount_rate', 'Interest Rate', 'interest_rate')
            totalValue += v
            totalFaceValue += fv
            if (r) { rateSum += r; cnt++ }
          })
          if (!instrumentCount) instrumentCount = details.length
          if (!totalRateSum && cnt) totalRateSum = rateSum / cnt
        }
      }

      // Dedupe by instrument identity so count reflects unique instruments, not spreadsheet rows
      const dedupedDetails = dedupeInstruments(details)
      const finalCount = instrumentCount > 0
        ? Math.min(instrumentCount, dedupedDetails.length || instrumentCount)
        : dedupedDetails.length

      const avgRate = rateCount > 0 ? totalRateSum : (totalRateSum || null)
      const avgFredBench = fredBenchCount > 0 ? totalFredBench / fredBenchCount : null
      const completed = dedupedDetails.length > 0 || totalValue > 0 || finalCount > 0

      detailsList.push({
        id: template.id,
        name: template.name,
        details: dedupedDetails,
        detailHeaders: detailHeaders.length ? getUniqueHeaders(detailHeaders) : ['No Data']
      })

      instrumentResults.push({
        ...template,
        value: totalValue,
        faceValue: totalFaceValue,
        difference: totalFaceValue - totalValue,
        count: finalCount,
        avgRate: avgRate,
        fredBench: avgFredBench,
        completed,
        statusClass: completed ? 'completed' : 'pending',
        statusText: completed ? 'Completed' : 'Not started',
        statusIcon: completed ? 'mdi-check-circle' : 'mdi-clock-outline'
      })
    }

    instrumentsWithDetails.value = detailsList
    instruments.value = instrumentResults

    const total = instruments.value.reduce((sum, inst) => sum + (inst.value || 0), 0)
    instruments.value = instruments.value.map(inst => ({
      ...inst,
      percent: total > 0 ? (((inst.value || 0) / total) * 100).toFixed(1) : 0
    }))

    const initSelections = {}
    instruments.value.forEach(inst => {
      initSelections[inst.id] = inst.completed || inst.value > 0
    })
    selectedExportInstruments.value = initSelections

    await publishPortfolioSnapshot(sid)

  } catch (err) {
    console.error('Error loading summary:', err)
    error.value = err.message || 'Failed to load summary data'
    instruments.value = []
    instrumentsWithDetails.value = []
  } finally {
    loading.value = false
  }
}

/**
 * Dedupe instrument rows to derive a unique-instrument count.
 * Prefers common identifier fields; falls back to the full row signature.
 */
function dedupeInstruments(rows) {
  if (!Array.isArray(rows)) return []
  const idFields = [
    'Instrument Name', 'instrument_name', 'InstrumentName',
    'BondName', 'Bond Name', 'TBillName', 'T-Bill Name',
    'BB Ticker', 'BBTicker', 'Ticker', 'ISIN', 'CUSIP'
  ]
  const seen = new Set()
  const out = []
  for (const row of rows) {
    if (!row || typeof row !== 'object') continue
    let id = null
    for (const f of idFields) {
      if (row[f] !== undefined && row[f] !== null && row[f] !== '') { id = String(row[f]).trim(); break }
    }
    if (!id) id = JSON.stringify(row)
    if (seen.has(id)) continue
    seen.add(id)
    out.push(row)
  }
  return out
}

const handleSessionUpdate = async (event) => {
  const { sessionId } = event.detail || {}
  if (!sessionId) { await loadSummary(); return }
  if (activeSession.value?.id === sessionId) await loadSummary()
}

onMounted(async () => {
  await loadSummary()
  window.addEventListener('session-updated', handleSessionUpdate)
})

onBeforeUnmount(() => {
  window.removeEventListener('session-updated', handleSessionUpdate)
})
</script>

<style scoped>
/* keep your existing styles — nothing structural changed here */
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
.kpi-strip { display: grid; grid-template-columns: repeat(4, 1fr); gap: 24px; margin-bottom: 28px; }
.kpi-card { background: white; border-radius: 20px; padding: 18px; display: flex; align-items: center; gap: 12px; position: relative; overflow: hidden; cursor: pointer; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05); transition: all 0.3s ease; }
.kpi-card.simple-kpi { padding: 20px; justify-content: center; text-align: center; }
.kpi-card.simple-kpi .kpi-info { text-align: center; }
.kpi-card.simple-kpi .kpi-value { font-size: 20px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 100%; }
.kpi-top-bar { position: absolute; top: 0; left: 0; right: 0; height: 4px; background: linear-gradient(90deg, #0B2044, #1E88E5, #4CAF50); }
.kpi-card:hover { transform: translateY(-5px); box-shadow: 0 12px 28px rgba(0, 0, 0, 0.15); }
.kpi-icon { width: 52px; height: 52px; border-radius: 14px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; transition: transform 0.3s ease; }
.kpi-card:hover .kpi-icon { transform: scale(1.05); }
.kpi-info { flex: 1; }
.kpi-value { font-size: 20px; font-weight: 800; color: #0B2044; }
.kpi-title { font-size: 10px; color: #888; }
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
.btn-view-details:hover:not(:disabled) { background: #1a3a6e; }
.btn-view-details:disabled { opacity: 0.5; cursor: not-allowed; }
.empty-note-block { padding: 10px 12px; background: #fff8e1; border-left: 4px solid #ffb300; color: #6d4c00; border-radius: 6px; font-size: 13px; }
.export-all-section { display: flex; justify-content: center; gap: 16px; margin: 32px 0 20px; flex-wrap: wrap; }
.btn-export-all, .btn-view-portfolio { border: none; padding: 10px 24px; border-radius: 40px; font-size: 14px; font-weight: 600; cursor: pointer; display: inline-flex; align-items: center; gap: 8px; transition: all 0.3s; box-shadow: 0 2px 6px rgba(0,0,0,0.1); }
.btn-export-all { background: #4CAF50; color: white; }
.btn-export-all:hover { background: #45a049; transform: translateY(-2px); box-shadow: 0 6px 12px rgba(0,0,0,0.15); }
.btn-view-portfolio { background: #0B2044; color: white; }
.btn-view-portfolio:hover { background: #1a3a6e; transform: translateY(-2px); box-shadow: 0 6px 12px rgba(0,0,0,0.15); }
.excel-dialog-title-white { background: white; color: #0B2044; padding: 16px 24px; display: flex; align-items: center; border-bottom: 2px solid #e0e0e0; }
.excel-dialog-title-white .logo { height: 40px; width: auto; object-fit: contain; }
.excel-dialog-title-white .header-left { display: flex; align-items: center; gap: 16px; }
.excel-dialog-title-white .header-title h4 { margin: 0; font-size: 18px; font-weight: 600; color: #0B2044; }
.excel-dialog-title-white .header-meta { margin: 2px 0 0 0; font-size: 13px; color: #666; }
.excel-dialog-title-white .btn-close-dialog { background: transparent; border: none; color: #666; cursor: pointer; padding: 8px; border-radius: 50%; font-size: 20px; }
.excel-dialog-title-white .btn-close-dialog:hover { background: #f0f0f0; color: #0B2044; }
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
.popup-footer { display: flex; justify-content: flex-end; align-items: center; gap: 12px; padding: 12px 24px; background: #f9fafc; border-top: 1px solid #e0e0e0; flex-shrink: 0; flex-wrap: wrap; }
.valuation-date-footer { color: #666; font-size: 13px; }
.analytics-cards { display: grid; grid-template-columns: repeat(5, 1fr); gap: 24px; margin-bottom: 28px; }
@media (max-width: 768px) {
  .summary-page { padding: 16px; }
  .hero-header { flex-direction: column; }
  .grand-pill { width: 100%; text-align: center; }
  .summary-cards { grid-template-columns: 1fr; }
  .kpi-strip { grid-template-columns: repeat(2, 1fr); }
  .analytics-cards { grid-template-columns: repeat(2, 1fr); }
  .export-all-section { flex-direction: column; align-items: center; }
  .action-buttons { flex-direction: column; align-items: center; }
  .dist-bar-container { flex-wrap: wrap; }
  .dist-label { width: 80px; }
}
</style>