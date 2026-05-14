<template>
  <FixedLayout>
    <div class="instrument-page">
      <!-- Page Header -->
      <div class="page-header">
        <div class="header-left">
          <button class="back-btn" @click="goToDashboard">
            <v-icon>mdi-arrow-left</v-icon> Back to Dashboard
          </button>
          <h1>{{ instrumentName }}</h1>
          <p>{{ instrumentDescription }}</p>
        </div>
        <div class="header-right">
          <div class="step-indicator">
            Step {{ currentStepIndex + 1 }} of {{ totalSteps }}
          </div>
        </div>
      </div>

      <!-- Progress Bar -->
      <div class="progress-bar-container">
        <div class="progress-steps">
          <div 
            v-for="(step, index) in steps" 
            :key="step.tab"
            class="progress-step"
            :class="{ 
              active: activeTab === step.tab,
              completed: getTabStatus(step.tab)
            }"
            @click="switchTab(step.tab)"
          >
            <div class="step-circle">{{ index + 1 }}</div>
            <div class="step-label">{{ step.name }}</div>
          </div>
        </div>
      </div>

      <!-- Content based on active tab -->
      <div class="tab-content">
        <!-- UPLOAD TAB -->
        <div v-if="activeTab === 'upload'" class="content-card">
          <v-card>
            <v-card-title>
              <v-icon>mdi-upload</v-icon>
              Upload {{ instrumentName }} Dataset
            </v-card-title>
            <v-card-text>
              <div class="upload-area" @dragover.prevent @drop.prevent="handleDrop">
                <input type="file" ref="fileInput" @change="handleFileUpload" accept=".csv,.xlsx,.xls" style="display: none">
                <v-icon size="48" color="#0B2044">mdi-cloud-upload</v-icon>
                <p>Drag & drop or <span class="browse-link" @click="$refs.fileInput.click()">browse</span></p>
                <small>Supported: CSV, Excel files</small>
              </div>
              
              <div v-if="uploadedFile" class="file-info">
                <v-icon>mdi-file-excel</v-icon>
                <span>{{ uploadedFile.name }}</span>
                <span class="file-size">{{ fileSize }}</span>
                <button class="remove-btn" @click="removeFile">×</button>
              </div>

              <!-- Excel Preview -->
              <div v-if="rawData.length > 0" class="excel-preview-section">
                <h4>File Preview:</h4>
                <div class="preview-toolbar">
                  <span class="preview-info">Showing {{ rawData.length }} rows × {{ Object.keys(rawData[0] || {}).length }} columns</span>
                  <div class="preview-controls">
                    <button @click="previewStartRow = Math.max(0, previewStartRow - 10)" :disabled="previewStartRow === 0" class="preview-btn">← Previous</button>
                    <span>Rows {{ previewStartRow + 1 }} - {{ Math.min(previewEndRow, rawData.length) }}</span>
                    <button @click="previewStartRow = Math.min(rawData.length - previewRows, previewStartRow + 10)" :disabled="previewEndRow >= rawData.length" class="preview-btn">Next →</button>
                  </div>
                </div>
                <div class="table-wrapper">
                  <table class="data-table">
                    <thead>
                      <tr>
                        <th>#</th>
                        <th v-for="col in previewColumnsList" :key="col">{{ col }}</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="(row, idx) in paginatedPreviewData" :key="idx">
                        <td class="row-number">{{ previewStartRow + idx + 1 }}</td>
                        <td v-for="col in previewColumnsList" :key="col">{{ formatCellValue(row[col]) }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>

              <!-- Column Mapping Dialog -->
              <v-dialog v-model="showMappingDialog" max-width="600px">
                <v-card>
                  <v-card-title>
                    <v-icon>mdi-map</v-icon>
                    Map Columns
                  </v-card-title>
                  <v-card-text>
                    <p>Please map the required columns to columns in your file:</p>
                    <div class="mapping-grid">
                      <div v-for="reqCol in requiredColumns" :key="reqCol" class="mapping-row">
                        <label class="required-label">{{ reqCol }}:</label>
                        <select v-model="columnMapping[reqCol]" class="mapping-select">
                          <option :value="null">-- Select column --</option>
                          <option v-for="fileCol in fileColumns" :key="fileCol" :value="fileCol">
                            {{ fileCol }}
                          </option>
                        </select>
                      </div>
                    </div>
                    <div class="mapping-hint">
                      <v-icon size="16">mdi-information</v-icon>
                      <small>Column names are matched automatically. You can adjust the mapping above.</small>
                    </div>
                  </v-card-text>
                  <v-card-actions>
                    <button class="btn-secondary" @click="showMappingDialog = false">Cancel</button>
                    <button class="btn-primary" @click="applyColumnMapping">Apply Mapping</button>
                  </v-card-actions>
                </v-card>
              </v-dialog>

              <div class="required-columns">
                <h4>Required Columns:</h4>
                <div class="columns-list">
                  <span v-for="col in requiredColumns" :key="col" class="column-badge" :class="{ 'missing-column': !hasRequiredColumn(col) }">
                    <v-icon size="12">{{ hasRequiredColumn(col) ? 'mdi-check' : 'mdi-close' }}</v-icon>
                    {{ col }}
                  </span>
                </div>
                <div v-if="missingColumns.length > 0" class="warning-message">
                  <v-icon color="warning">mdi-alert</v-icon>
                  <span>Missing required columns. Click "Map Columns" to fix.</span>
                </div>
              </div>

              <div class="navigation-buttons">
                <button v-if="missingColumns.length > 0 && rawData.length > 0" class="btn-warning" @click="autoMatchColumns">
                  Map Columns
                </button>
                <button class="btn-primary" @click="uploadData" :disabled="!uploadedFile || missingColumns.length > 0">
                  Upload & Continue
                </button>
                <button class="btn-secondary" @click="goToDashboard">Cancel</button>
              </div>
            </v-card-text>
          </v-card>
        </div>

        <!-- CLEANING TAB -->
        <div v-if="activeTab === 'cleaning'" class="content-card">
          <v-card>
            <v-card-title>
              <v-icon>mdi-broom</v-icon>
              Clean {{ instrumentName }} Data
            </v-card-title>
            <v-card-text>
              <div v-if="!hasData" class="empty-state">
                <v-icon size="48" color="#ccc">mdi-database</v-icon>
                <p>No data uploaded yet. Please upload a dataset first.</p>
                <button class="btn-primary" @click="switchTab('upload')">Go to Upload</button>
              </div>
              
              <div v-else>
                <div class="cleaning-stats">
                  <div class="stat-card">
                    <div class="stat-value">{{ cleaningStats.totalRows }}</div>
                    <div class="stat-label">Total Rows</div>
                  </div>
                  <div class="stat-card">
                    <div class="stat-value">{{ cleaningStats.validRows }}</div>
                    <div class="stat-label">Valid Rows</div>
                  </div>
                  <div class="stat-card">
                    <div class="stat-value">{{ cleaningStats.removedRows }}</div>
                    <div class="stat-label">Removed Rows</div>
                  </div>
                  <div class="stat-card">
                    <div class="stat-value">{{ cleaningStats.fixedMissing }}</div>
                    <div class="stat-label">Missing Fixed</div>
                  </div>
                </div>

                <div class="cleaning-actions">
                  <button class="btn-primary" @click="cleanData" :disabled="cleanedData.length > 0">
                    <v-icon>mdi-broom</v-icon> Auto-Clean Data
                  </button>
                </div>

                <div v-if="cleanedData.length > 0" class="preview-section">
                  <h4>Cleaned Data Preview:</h4>
                  <div class="highlight-box">
                    <p>✓ Removed {{ cleaningStats.removedRows }} invalid rows</p>
                    <p>✓ Fixed {{ cleaningStats.fixedMissing }} missing values</p>
                  </div>
                  
                  <div class="preview-toolbar">
                    <span class="preview-info">Clean Data: {{ cleanedData.length }} rows</span>
                    <div class="preview-controls">
                      <button @click="cleanPreviewStartRow = Math.max(0, cleanPreviewStartRow - 10)" :disabled="cleanPreviewStartRow === 0" class="preview-btn">← Previous</button>
                      <span>Rows {{ cleanPreviewStartRow + 1 }} - {{ Math.min(cleanPreviewEndRow, cleanedData.length) }}</span>
                      <button @click="cleanPreviewStartRow = Math.min(cleanedData.length - cleanPreviewRows, cleanPreviewStartRow + 10)" :disabled="cleanPreviewEndRow >= cleanedData.length" class="preview-btn">Next →</button>
                    </div>
                  </div>
                  <div class="table-wrapper">
                    <table class="data-table">
                      <thead>
                        <tr>
                          <th>#</th>
                          <th v-for="col in cleanPreviewColumnsList" :key="col">{{ col }}</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr v-for="(row, idx) in paginatedCleanPreview" :key="idx">
                          <td class="row-number">{{ cleanPreviewStartRow + idx + 1 }}</td>
                          <td v-for="col in cleanPreviewColumnsList" :key="col">{{ formatCellValue(row[col]) }}</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>

                <div class="navigation-buttons">
                  <button class="btn-secondary" @click="switchTab('upload')">Previous</button>
                  <button class="btn-primary" @click="switchTab('calculations')" :disabled="!hasCleanedData">Next: Calculations</button>
                  <button class="btn-secondary" @click="goToDashboard">Dashboard</button>
                </div>
              </div>
            </v-card-text>
          </v-card>
        </div>

        <!-- CALCULATIONS TAB -->
        <div v-if="activeTab === 'calculations'" class="content-card">
          <v-card>
            <v-card-title>
              <v-icon>mdi-calculator</v-icon>
              {{ instrumentName }} Calculations
            </v-card-title>
            <v-card-text>
              <div v-if="!hasCleanedData" class="empty-state">
                <v-icon size="48" color="#ccc">mdi-calculator</v-icon>
                <p>No cleaned data available. Please clean your data first.</p>
                <button class="btn-primary" @click="switchTab('cleaning')">Go to Cleaning</button>
              </div>
              
              <div v-else>
                <div class="calculations-grid">
                  <div v-for="calc in calculationsList" :key="calc.name" class="calculation-card">
                    <div class="calc-name">{{ calc.name }}</div>
                    <div class="calc-value">{{ calc.value }}</div>
                    <div class="calc-unit">{{ calc.unit }}</div>
                  </div>
                </div>

                <div class="navigation-buttons">
                  <button class="btn-secondary" @click="switchTab('cleaning')">Previous</button>
                  <button class="btn-primary" @click="switchTab('visualizations')">Next: Visualizations</button>
                  <button class="btn-secondary" @click="goToDashboard">Dashboard</button>
                </div>
              </div>
            </v-card-text>
          </v-card>
        </div>

        <!-- VISUALIZATIONS TAB -->
        <div v-if="activeTab === 'visualizations'" class="content-card">
          <v-card>
            <v-card-title>
              <v-icon>mdi-chart-line</v-icon>
              {{ instrumentName }} Visualizations
            </v-card-title>
            <v-card-text>
              <div class="visualization-placeholder">
                <v-icon size="64" color="#0B2044">mdi-chart-line</v-icon>
                <h3>Visualizations Coming Soon</h3>
                <p>Yield curve and other visualizations will be displayed here once the backend API is integrated.</p>
                <div class="placeholder-note">
                  <v-icon>mdi-information</v-icon>
                  <span>Backend API integration in progress</span>
                </div>
              </div>

              <div class="navigation-buttons">
                <button class="btn-secondary" @click="switchTab('calculations')">Previous</button>
                <button class="btn-primary" @click="switchTab('summary')">Next: Summary</button>
                <button class="btn-secondary" @click="goToDashboard">Dashboard</button>
              </div>
            </v-card-text>
          </v-card>
        </div>

        <!-- SUMMARY TAB -->
        <div v-if="activeTab === 'summary'" class="content-card">
          <v-card>
            <v-card-title>
              <v-icon>mdi-file-document</v-icon>
              {{ instrumentName }} Summary
            </v-card-title>
            <v-card-text>
              <div class="summary-grid">
                <div class="summary-section">
                  <h3>Portfolio Overview</h3>
                  <p><strong>Total Value:</strong> ${{ calculations.totalValue?.toLocaleString() || 0 }}</p>
                  <p><strong>Number of Instruments:</strong> {{ calculations.instrumentCount || 0 }}</p>
                  <p><strong>Data Processed:</strong> {{ cleanedData.length }} records</p>
                </div>
                <div class="summary-section">
                  <h3>Key Metrics</h3>
                  <div v-for="calc in calculationsList" :key="calc.name">
                    <p><strong>{{ calc.name }}:</strong> {{ calc.value }} {{ calc.unit }}</p>
                  </div>
                </div>
              </div>

              <div class="summary-progress">
                <div class="progress-bar">
                  <div class="progress-fill" style="width: 100%"></div>
                </div>
                <p class="progress-text">✓ Upload ✓ Clean ✓ Calculate — Ready for Report</p>
              </div>

              <div class="navigation-buttons">
                <button class="btn-secondary" @click="switchTab('visualizations')">Previous</button>
                <button class="btn-primary" @click="switchTab('reports')">Move to Report →</button>
                <button class="btn-secondary" @click="goToDashboard">Dashboard</button>
              </div>
            </v-card-text>
          </v-card>
        </div>

        <!-- REPORTS TAB -->
        <div v-if="activeTab === 'reports'" class="content-card">
          <v-card>
            <v-card-title>
              <v-icon>mdi-file-pdf</v-icon>
              Generate {{ instrumentName }} Report
            </v-card-title>
            <v-card-text>
              <div class="report-options">
                <div class="report-preview">
                  <h3>Report Preview</h3>
                  <div class="report-content">
                    <p><strong>Instrument:</strong> {{ instrumentName }}</p>
                    <p><strong>Date Generated:</strong> {{ new Date().toLocaleString() }}</p>
                    <p><strong>Total Value:</strong> ${{ calculations.totalValue?.toLocaleString() || 0 }}</p>
                    <p><strong>Records Processed:</strong> {{ cleanedData.length }}</p>
                  </div>
                  
                  <div class="report-data-preview">
                    <h5>Data Preview (First 5 rows)</h5>
                    <div class="table-wrapper">
                      <table class="data-table">
                        <thead>
                          <tr>
                            <th>#</th>
                            <th v-for="col in reportPreviewColumns" :key="col">{{ col }}</th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr v-for="(row, idx) in reportDataPreview" :key="idx">
                            <td>{{ idx + 1 }}</td>
                            <td v-for="col in reportPreviewColumns" :key="col">{{ formatCellValue(row[col]) }}</td>
                          </tr>
                        </tbody>
                       </table>
                    </div>
                  </div>
                </div>
                <div class="report-actions">
                  <button class="btn-primary" @click="downloadReport">
                    <v-icon>mdi-download</v-icon> Download JSON Report
                  </button>
                  <button class="btn-success" @click="saveToSummary">
                    <v-icon>mdi-content-save</v-icon> Save to Summary
                  </button>
                </div>
              </div>

              <div class="navigation-buttons">
                <button class="btn-secondary" @click="switchTab('summary')">Previous</button>
                <button class="btn-primary" @click="goToDashboard">Finish & Dashboard</button>
              </div>
            </v-card-text>
          </v-card>
        </div>
      </div>
    </div>
  </FixedLayout>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import FixedLayout from '@/components/FixedLayout.vue'
import * as XLSX from 'xlsx'

const router = useRouter()
const route = useRoute()

// Instrument type from route
const instrumentType = computed(() => route.params.type || route.path.split('/').pop())
const instrumentName = computed(() => {
  const names = { 'money-market': 'Money Market', bonds: 'Bonds', tbills: 'T-Bills' }
  return names[instrumentType.value] || 'Instrument'
})

const instrumentDescription = computed(() => {
  const descriptions = {
    'money-market': 'Short-term debt instruments including treasury bills, commercial paper',
    'bonds': 'Fixed income securities including government and corporate bonds',
    'tbills': 'Treasury bills - short-term government securities'
  }
  return descriptions[instrumentType.value] || 'Financial instrument management'
})

// Steps
const steps = [
  { tab: 'upload', name: 'Upload' },
  { tab: 'cleaning', name: 'Clean' },
  { tab: 'calculations', name: 'Calculate' },
  { tab: 'visualizations', name: 'Visualize' },
  { tab: 'summary', name: 'Summary' },
  { tab: 'reports', name: 'Report' }
]

const currentStepIndex = computed(() => steps.findIndex(s => s.tab === activeTab.value))
const totalSteps = steps.length

const activeTab = computed({
  get: () => route.query.tab || 'upload',
  set: (val) => router.push({ query: { tab: val } })
})

// Data
const uploadedFile = ref(null)
const rawData = ref([])
const cleanedData = ref([])
const columnMapping = ref({})
const showMappingDialog = ref(false)
const fileColumns = ref([])

// Required columns
const requiredColumns = computed(() => {
  const columns = {
    'money-market': ['Date', 'Instrument', 'Rate', 'Amount'],
    'bonds': ['Date', 'BondName', 'CouponRate', 'FaceValue', 'Yield'],
    'tbills': ['Date', 'TBillName', 'DiscountRate', 'FaceValue']
  }
  return columns[instrumentType.value] || ['Date', 'Amount']
})

// Column name variations for auto-matching
const columnVariations = {
  'Date': ['Date', 'date', 'DATE', 'Transaction Date', 'Trade Date', 'Settlement Date', 'Value Date'],
  'Instrument': ['Instrument', 'instrument', 'INSTRUMENT', 'Security', 'Security Name', 'Name', 'Description'],
  'Rate': ['Rate', 'rate', 'RATE', 'Interest Rate', 'Coupon Rate', 'Discount Rate', 'Yield'],
  'Amount': ['Amount', 'amount', 'AMOUNT', 'Face Value', 'FaceValue', 'Value', 'Price', 'Notional', 'Principal'],
  'BondName': ['BondName', 'Bond Name', 'bond', 'BOND', 'Security', 'Issuer'],
  'CouponRate': ['CouponRate', 'Coupon Rate', 'coupon', 'Rate', 'Interest Rate'],
  'FaceValue': ['FaceValue', 'Face Value', 'Face', 'Value', 'Amount', 'Principal', 'Par Value'],
  'Yield': ['Yield', 'yield', 'YIELD', 'Yield to Maturity', 'YTM', 'Return'],
  'TBillName': ['TBillName', 'T-Bill Name', 'TBill', 'T Bill', 'Security', 'Instrument'],
  'DiscountRate': ['DiscountRate', 'Discount Rate', 'discount', 'Rate']
}

// Preview
const previewRows = ref(10)
const previewStartRow = ref(0)
const previewEndRow = computed(() => Math.min(previewStartRow.value + previewRows.value, rawData.value.length))
const previewColumnsList = computed(() => {
  if (rawData.value.length === 0) return []
  return Object.keys(rawData.value[0]).slice(0, 8)
})
const paginatedPreviewData = computed(() => rawData.value.slice(previewStartRow.value, previewEndRow.value))

// Clean Preview
const cleanPreviewRows = ref(10)
const cleanPreviewStartRow = ref(0)
const cleanPreviewEndRow = computed(() => Math.min(cleanPreviewStartRow.value + cleanPreviewRows.value, cleanedData.value.length))
const cleanPreviewColumnsList = computed(() => {
  if (cleanedData.value.length === 0) return []
  return Object.keys(cleanedData.value[0]).slice(0, 8)
})
const paginatedCleanPreview = computed(() => cleanedData.value.slice(cleanPreviewStartRow.value, cleanPreviewEndRow.value))

// Report Preview
const reportPreviewColumns = computed(() => {
  if (cleanedData.value.length === 0) return []
  return Object.keys(cleanedData.value[0]).slice(0, 6)
})
const reportDataPreview = computed(() => cleanedData.value.slice(0, 5))

// File size
const fileSize = computed(() => {
  if (!uploadedFile.value) return ''
  const bytes = uploadedFile.value.size
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(2) + ' MB'
})

// Column validation
const hasRequiredColumn = (col) => {
  if (rawData.value.length === 0) return false
  return Object.keys(rawData.value[0]).includes(col)
}

const missingColumns = computed(() => {
  if (rawData.value.length === 0) return []
  return requiredColumns.value.filter(col => !hasRequiredColumn(col))
})

// Cleaning stats
const cleaningStats = ref({ totalRows: 0, validRows: 0, removedRows: 0, fixedMissing: 0 })

// Calculations
const calculations = ref({ totalValue: 0, instrumentCount: 0 })

const calculationsList = computed(() => {
  const list = []
  if (instrumentType.value === 'money-market') {
    list.push({ name: 'Total Portfolio Value', value: `$${calculations.value.totalValue?.toLocaleString() || 0}`, unit: 'USD' })
    list.push({ name: 'Average Interest Rate', value: calculations.value.avgRate || 0, unit: '%' })
    list.push({ name: 'Number of Instruments', value: calculations.value.instrumentCount || 0, unit: 'items' })
  } 
  else if (instrumentType.value === 'bonds') {
    list.push({ name: 'Total Portfolio Value', value: `$${calculations.value.totalValue?.toLocaleString() || 0}`, unit: 'USD' })
    list.push({ name: 'Average Coupon Rate', value: calculations.value.avgCouponRate || 0, unit: '%' })
    list.push({ name: 'Number of Bonds', value: calculations.value.instrumentCount || 0, unit: 'issues' })
  }
  else if (instrumentType.value === 'tbills') {
    list.push({ name: 'Total Portfolio Value', value: `$${calculations.value.totalValue?.toLocaleString() || 0}`, unit: 'USD' })
    list.push({ name: 'Average Discount Rate', value: calculations.value.avgDiscountRate || 0, unit: '%' })
    list.push({ name: 'Number of T-Bills', value: calculations.value.instrumentCount || 0, unit: 'securities' })
  }
  return list
})

const hasData = computed(() => rawData.value.length > 0)
const hasCleanedData = computed(() => cleanedData.value.length > 0)

// Navigation
function goToDashboard() { router.push('/dashboard') }
function switchTab(tab) { activeTab.value = tab }

function handleFileUpload(event) { uploadedFile.value = event.target.files[0] }
function handleDrop(event) { uploadedFile.value = event.dataTransfer.files[0] }
function removeFile() { uploadedFile.value = null; rawData.value = []; cleanedData.value = [] }

function formatCellValue(value) {
  if (value === undefined || value === null) return '-'
  if (typeof value === 'number') return value.toFixed(2)
  if (typeof value === 'string' && value.length > 30) return value.substring(0, 27) + '...'
  return value
}

// Column matching functions
function autoMatchColumns() {
  if (rawData.value.length === 0) return
  fileColumns.value = Object.keys(rawData.value[0])
  const newMapping = {}
  
  requiredColumns.value.forEach(reqCol => {
    const variations = columnVariations[reqCol] || [reqCol]
    let matchedColumn = null
    
    matchedColumn = fileColumns.value.find(col => col === reqCol)
    if (!matchedColumn) {
      matchedColumn = fileColumns.value.find(col => col.toLowerCase() === reqCol.toLowerCase())
    }
    if (!matchedColumn) {
      matchedColumn = fileColumns.value.find(col => {
        return variations.some(variation => 
          col.toLowerCase().includes(variation.toLowerCase()) ||
          variation.toLowerCase().includes(col.toLowerCase())
        )
      })
    }
    newMapping[reqCol] = matchedColumn || null
  })
  
  columnMapping.value = newMapping
  showMappingDialog.value = true
}

function applyColumnMapping() {
  if (rawData.value.length === 0) return
  
  const mappedData = rawData.value.map(row => {
    const newRow = {}
    requiredColumns.value.forEach(reqCol => {
      const sourceCol = columnMapping.value[reqCol]
      if (sourceCol && row[sourceCol] !== undefined) {
        newRow[reqCol] = row[sourceCol]
      } else {
        newRow[reqCol] = null
      }
    })
    return newRow
  })
  
  rawData.value = mappedData
  showMappingDialog.value = false
  alert('Columns mapped successfully!')
}

async function uploadData() {
  if (!uploadedFile.value) return
  const file = uploadedFile.value
  const extension = file.name.split('.').pop().toLowerCase()
  let data = []
  
  if (extension === 'csv') {
    const text = await file.text()
    const lines = text.split('\n')
    const headers = lines[0].split(',')
    data = lines.slice(1).map(line => {
      const values = line.split(',')
      const row = {}
      headers.forEach((h, i) => row[h.trim()] = values[i])
      return row
    })
  } else {
    const buffer = await file.arrayBuffer()
    const workbook = XLSX.read(buffer)
    const worksheet = workbook.Sheets[workbook.SheetNames[0]]
    data = XLSX.utils.sheet_to_json(worksheet)
  }
  
  rawData.value = data
  activeTab.value = 'cleaning'
  updateStatus('upload', true)
}

function cleanData() {
  const required = requiredColumns.value
  let cleaned = rawData.value.filter(row => required.every(col => row[col] !== undefined && row[col] !== null && row[col] !== ''))

  let missingCount = 0
  cleaned = cleaned.map(row => {
    required.forEach(col => {
      if (!row[col] || row[col] === '') {
        missingCount++
        if (col.includes('Rate') || col.includes('Yield')) row[col] = 0
        else if (col.includes('Amount') || col.includes('Value')) row[col] = 0
        else row[col] = 'N/A'
      }
    })
    
    if (row.Rate) row.Rate = parseFloat(row.Rate) || 0
    if (row.Amount) row.Amount = parseFloat(row.Amount) || 0
    if (row.CouponRate) row.CouponRate = parseFloat(row.CouponRate) || 0
    if (row.FaceValue) row.FaceValue = parseFloat(row.FaceValue) || 0
    if (row.Yield) row.Yield = parseFloat(row.Yield) || 0
    if (row.DiscountRate) row.DiscountRate = parseFloat(row.DiscountRate) || 0
    return row
  })

  cleanedData.value = cleaned
  cleaningStats.value = {
    totalRows: rawData.value.length,
    validRows: cleaned.length,
    removedRows: rawData.value.length - cleaned.length,
    fixedMissing: missingCount
  }

  calculateMetrics()
  updateStatus('cleaning', true)
}

function calculateMetrics() {
  let totalValue = 0, totalRate = 0
  
  if (instrumentType.value === 'money-market') {
    totalValue = cleanedData.value.reduce((sum, row) => sum + (row.Amount || 0), 0)
    totalRate = cleanedData.value.reduce((sum, row) => sum + (row.Rate || 0), 0)
    calculations.value = {
      totalValue, instrumentCount: cleanedData.value.length,
      avgRate: (totalRate / cleanedData.value.length).toFixed(2)
    }
  } 
  else if (instrumentType.value === 'bonds') {
    totalValue = cleanedData.value.reduce((sum, row) => sum + (row.FaceValue || 0), 0)
    totalRate = cleanedData.value.reduce((sum, row) => sum + (row.CouponRate || 0), 0)
    calculations.value = {
      totalValue, instrumentCount: cleanedData.value.length,
      avgCouponRate: (totalRate / cleanedData.value.length).toFixed(2)
    }
  }
  else if (instrumentType.value === 'tbills') {
    totalValue = cleanedData.value.reduce((sum, row) => sum + (row.FaceValue || 0), 0)
    totalRate = cleanedData.value.reduce((sum, row) => sum + (row.DiscountRate || 0), 0)
    calculations.value = {
      totalValue, instrumentCount: cleanedData.value.length,
      avgDiscountRate: (totalRate / cleanedData.value.length).toFixed(2)
    }
  }
}

function downloadReport() {
  const report = {
    instrument: instrumentName.value,
    date: new Date().toLocaleString(),
    calculations: calculations.value,
    cleaningStats: cleaningStats.value,
    totalRecords: cleanedData.value.length,
    data: cleanedData.value.slice(0, 100)
  }
  const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${instrumentType.value}_report_${Date.now()}.json`
  a.click()
  URL.revokeObjectURL(url)
  updateStatus('reports', true)
}

function saveToSummary() {
  const session = JSON.parse(localStorage.getItem('active_session') || '{}')
  const summary = JSON.parse(localStorage.getItem('summary_totals') || '{}')
  summary[instrumentType.value] = calculations.value.totalValue
  localStorage.setItem('summary_totals', JSON.stringify(summary))
  
  // Update session data
  if (session.id) {
    if (!session.instrumentData) session.instrumentData = {}
    session.instrumentData[instrumentType.value] = {
      totalValue: calculations.value.totalValue,
      count: calculations.value.instrumentCount,
      completed: true
    }
    session.completedInstruments = session.completedInstruments || {}
    session.completedInstruments[instrumentType.value] = true
    localStorage.setItem('active_session', JSON.stringify(session))
    
    // Update sessions list
    const sessions = JSON.parse(localStorage.getItem('sessions_list') || '[]')
    const index = sessions.findIndex(s => s.id === session.id)
    if (index !== -1) sessions[index] = session
    localStorage.setItem('sessions_list', JSON.stringify(sessions))
  }
  
  updateStatus('summary', true)
  alert('Saved to Summary!')
}

function updateStatus(tab, completed) {
  const statuses = JSON.parse(localStorage.getItem(`instrument_${instrumentType.value}_status`) || '{}')
  statuses[tab] = completed
  localStorage.setItem(`instrument_${instrumentType.value}_status`, JSON.stringify(statuses))
}

function getTabStatus(tab) {
  const statuses = JSON.parse(localStorage.getItem(`instrument_${instrumentType.value}_status`) || '{}')
  return statuses[tab] || false
}

onMounted(() => {
  const savedData = localStorage.getItem(`${instrumentType.value}_cleaned_data`)
  if (savedData) {
    cleanedData.value = JSON.parse(savedData)
    calculateMetrics()
  }
})
</script>

<style scoped>
.instrument-page {
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 25px;
  padding: 0 10px;
}

.back-btn {
  background: transparent;
  border: none;
  color: #0B2044;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border-radius: 8px;
  margin-bottom: 10px;
  transition: all 0.2s;
}

.back-btn:hover {
  background: rgba(11,32,68,0.05);
  transform: translateX(-3px);
}

.header-left h1 {
  color: #0B2044;
  font-size: 28px;
  font-weight: 700;
  margin-bottom: 5px;
}

.header-left p {
  color: #666;
  font-size: 14px;
}

.step-indicator {
  background: white;
  padding: 8px 16px;
  border-radius: 20px;
  font-size: 13px;
  color: #0B2044;
  font-weight: 600;
}

.progress-bar-container {
  margin-bottom: 30px;
  padding: 0 10px;
}

.progress-steps {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: white;
  padding: 20px;
  border-radius: 16px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.05);
}

.progress-step {
  flex: 1;
  text-align: center;
  cursor: pointer;
}

.step-circle {
  width: 36px;
  height: 36px;
  background: #e0e0e0;
  color: #999;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  transition: all 0.3s;
}

.progress-step.active .step-circle {
  background: #0B2044;
  color: white;
  box-shadow: 0 0 0 4px rgba(11,32,68,0.2);
}

.progress-step.completed .step-circle {
  background: #4CAF50;
  color: white;
}

.step-label {
  font-size: 11px;
  color: #999;
  margin-top: 8px;
}

.progress-step.active .step-label {
  color: #0B2044;
  font-weight: 600;
}

.content-card {
  margin-bottom: 20px;
}

.upload-area {
  border: 2px dashed #ccc;
  border-radius: 12px;
  padding: 50px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s;
}

.upload-area:hover {
  border-color: #0B2044;
  background: #f8f9ff;
}

.browse-link {
  color: #0B2044;
  cursor: pointer;
  font-weight: 600;
}

.file-info {
  margin-top: 20px;
  padding: 12px;
  background: #f5f5f5;
  border-radius: 8px;
  display: flex;
  align-items: center;
  gap: 10px;
}

.file-size {
  font-size: 11px;
  color: #999;
  margin-left: auto;
}

.remove-btn {
  margin-left: auto;
  background: none;
  border: none;
  font-size: 20px;
  cursor: pointer;
  color: #f44336;
}

.excel-preview-section, .preview-toolbar {
  margin-top: 20px;
}

.preview-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 15px;
  background: #f5f5f5;
  border-radius: 8px;
  flex-wrap: wrap;
  gap: 10px;
}

.preview-info {
  font-size: 12px;
  color: #666;
}

.preview-controls {
  display: flex;
  align-items: center;
  gap: 10px;
}

.preview-btn {
  background: white;
  border: 1px solid #ddd;
  padding: 4px 12px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 12px;
}

.preview-btn:hover:not(:disabled) {
  background: #0B2044;
  color: white;
}

.preview-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.row-number {
  background: #f8f9ff;
  font-weight: 500;
  color: #0B2044;
  width: 50px;
  text-align: center;
}

.mapping-grid {
  display: flex;
  flex-direction: column;
  gap: 15px;
  margin: 20px 0;
}

.mapping-row {
  display: flex;
  align-items: center;
  gap: 15px;
}

.required-label {
  width: 120px;
  font-weight: 600;
  color: #0B2044;
}

.mapping-select {
  flex: 1;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 14px;
}

.mapping-hint {
  margin-top: 15px;
  padding: 10px;
  background: #f8f9ff;
  border-radius: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
  color: #666;
}

.required-columns {
  margin: 20px 0;
}

.columns-list {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 10px;
}

.column-badge {
  background: #e8ecf1;
  padding: 6px 12px;
  border-radius: 20px;
  font-size: 12px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.missing-column {
  background: #FFEBEE;
  color: #c62828;
}

.warning-message {
  margin-top: 10px;
  padding: 8px 12px;
  background: #FFF3E0;
  border-radius: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #E65100;
}

.btn-warning {
  background: #FF9800;
  color: white;
  border: none;
  padding: 12px 20px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}

.cleaning-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  margin-bottom: 30px;
}

.stat-card {
  text-align: center;
  padding: 20px;
  background: linear-gradient(135deg, #f8f9ff, #fff);
  border-radius: 12px;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #0B2044;
}

.stat-label {
  font-size: 12px;
  color: #666;
  margin-top: 8px;
}

.cleaning-actions {
  text-align: center;
  margin: 20px 0;
}

.highlight-box {
  background: #e8f5e9;
  padding: 12px;
  border-radius: 8px;
  margin-bottom: 20px;
}

.calculations-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
  margin-bottom: 30px;
}

.calculation-card {
  padding: 25px;
  background: linear-gradient(135deg, #f8f9ff, #fff);
  border-radius: 12px;
  text-align: center;
  border: 1px solid rgba(11,32,68,0.1);
}

.calc-name {
  font-size: 14px;
  color: #666;
  margin-bottom: 10px;
}

.calc-value {
  font-size: 28px;
  font-weight: 700;
  color: #0B2044;
  margin-bottom: 5px;
}

.calc-unit {
  font-size: 12px;
  color: #999;
}

.visualization-placeholder {
  text-align: center;
  padding: 60px;
  background: #f8f9ff;
  border-radius: 12px;
}

.visualization-placeholder h3 {
  color: #0B2044;
  margin: 20px 0 10px;
}

.visualization-placeholder p {
  color: #666;
  margin-bottom: 20px;
}

.placeholder-note {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: #e3f2fd;
  border-radius: 20px;
  font-size: 12px;
  color: #0B2044;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
  margin-bottom: 30px;
}

.summary-section {
  padding: 20px;
  background: #f8f9ff;
  border-radius: 12px;
}

.summary-section h3 {
  color: #0B2044;
  margin-bottom: 15px;
}

.summary-section p {
  margin: 8px 0;
  color: #555;
}

.summary-progress {
  margin: 20px 0;
  padding: 15px;
  background: #f8f9ff;
  border-radius: 12px;
}

.progress-bar {
  height: 8px;
  background: #e0e0e0;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 10px;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #4CAF50, #2E7D32);
  border-radius: 4px;
}

.progress-text {
  font-size: 12px;
  color: #4CAF50;
  font-weight: 500;
  margin: 0;
}

.report-options {
  padding: 20px;
}

.report-preview {
  background: #f8f9ff;
  padding: 20px;
  border-radius: 12px;
  margin-bottom: 20px;
}

.report-content {
  margin-top: 15px;
  padding: 15px;
  background: white;
  border-radius: 8px;
}

.report-data-preview {
  margin-top: 20px;
}

.report-data-preview h5 {
  color: #0B2044;
  margin-bottom: 10px;
}

.report-actions {
  display: flex;
  gap: 15px;
  justify-content: center;
  margin-bottom: 20px;
}

.table-wrapper {
  overflow-x: auto;
  margin: 15px 0;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th, .data-table td {
  padding: 10px;
  text-align: left;
  border-bottom: 1px solid #e0e0e0;
}

.data-table th {
  background: #f5f5f5;
  font-weight: 600;
  color: #0B2044;
}

.empty-state {
  text-align: center;
  padding: 60px;
  color: #999;
}

.empty-state p {
  margin: 20px 0;
}

.navigation-buttons {
  display: flex;
  gap: 15px;
  justify-content: center;
  margin-top: 30px;
  padding-top: 20px;
  border-top: 1px solid #e0e0e0;
}

.btn-primary {
  background: linear-gradient(135deg, #0B2044, #1E88E5);
  color: white;
  border: none;
  padding: 12px 28px;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 15px rgba(11,32,68,0.3);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  background: white;
  color: #0B2044;
  border: 2px solid #0B2044;
  padding: 12px 28px;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
}

.btn-secondary:hover {
  background: #0B2044;
  color: white;
  transform: translateY(-2px);
}

.btn-success {
  background: linear-gradient(135deg, #4CAF50, #2E7D32);
  color: white;
  border: none;
  padding: 12px 28px;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
}

.btn-success:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 15px rgba(76, 175, 80, 0.3);
}
</style>