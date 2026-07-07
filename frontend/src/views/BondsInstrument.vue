<template>
  <FixedLayout>
    <div class="instrument-page">
      <!-- Page Header -->
      <div class="page-header">
        <div class="header-left">
          <h1>{{ instrumentName }}</h1>
          <p>{{ instrumentDescription }}</p>
          <div v-if="activeSession" class="session-badge">
            <v-icon small>mdi-folder-outline</v-icon>
            Session: <strong>{{ activeSession.name }}</strong>
          </div>
          <div v-else class="session-badge warning">
            <v-icon small>mdi-alert-outline</v-icon>
            No active session – please select a session from Dashboard
          </div>
        </div>
        <div class="header-right">
          <button v-if="activeSession" class="btn-save-session" @click="saveToSession" title="Save a version to session history">
            <v-icon small>mdi-content-save</v-icon> Save to Session
          </button>
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
              completed: isStepComplete(step.tab),
              disabled: index > farthestAllowedIndex
            }"
            @click="switchTab(step.tab)"
          >
            <div class="step-circle">{{ index + 1 }}</div>
            <div class="step-label">{{ step.name }}</div>
          </div>
        </div>
      </div>

      <!-- Tab content -->
      <div class="tab-content">
        <!-- ===== UPLOAD ===== -->
        <div v-if="activeTab === 'upload'" class="content-card">
          <v-card>
            <v-card-title><v-icon>mdi-cloud-upload-outline</v-icon> Upload {{ instrumentName }} Dataset</v-card-title>
            <v-card-text>
              <div class="upload-area" @dragover.prevent @drop.prevent="handleDrop">
                <input
                  type="file"
                  ref="fileInput"
                  @change="handleFileUpload"
                  accept=".csv,.xlsx,.xls,.xlsm,.xlsb,.xltx,.xltm,.xlam,.ods,.xml,.html,.prn,.dif,.slk,.dbf"
                  style="display: none"
                >
                <v-icon size="48" color="#0B2044" class="upload-icon">mdi-cloud-upload-outline</v-icon>
                <p>Drag & drop or <span class="browse-link" @click="$refs.fileInput.click()">browse</span></p>
                <small>Supported: CSV, Excel (including .xlsm, .xlsb, .ods), and many other spreadsheet formats</small>
              </div>

              <!-- Upload History -->
              <div v-if="uploadHistory.length" class="upload-history">
                <h4><v-icon small>mdi-history</v-icon> Upload History ({{ uploadHistory.length }} files)</h4>
                <div class="history-list">
                  <div v-for="(item, idx) in uploadHistory" :key="idx" class="history-item" @click="loadHistoryFile(item)">
                    <v-icon small>mdi-file-excel-outline</v-icon>
                    <span>{{ item.name }}</span>
                    <small>{{ new Date(item.date).toLocaleString() }}</small>
                    <button class="btn-delete-history" @click.stop="deleteHistoryItem(idx)">
                      <v-icon small color="error">mdi-delete</v-icon>
                    </button>
                  </div>
                </div>
              </div>

              <div v-if="fileLoading" class="loading-container">
                <v-icon size="48" class="spin">mdi-loading</v-icon>
                <p>{{ uploadProgress > 0 ? `Processing file... ${uploadProgress}%` : 'Parsing file... Please wait.' }}</p>
                <v-progress-linear v-if="uploadProgress > 0" :value="uploadProgress" color="#0B2044" height="6"></v-progress-linear>
              </div>

              <div v-if="uploadedFile" class="file-info">
                <v-icon>mdi-file-excel-outline</v-icon>
                <span>{{ uploadedFile.name }}</span>
                <span v-if="fileSize" class="file-size">{{ fileSize }}</span>
                <button class="remove-btn" @click="removeFile">×</button>
                <button class="btn-view-workbook" @click="openWorkbookViewer">View Excel Workbook</button>
                <button class="btn-preview" @click="togglePreview" :disabled="!rawData.length">Preview</button>
                <button class="btn-review-excel" @click="openExcelReview(rawData, 'Uploaded Data')" :disabled="!rawData.length">Review Excel</button>
                <button class="btn-mapping" @click="openMappingDialog" :disabled="!rawData.length">Map Columns</button>
              </div>

              <!-- Worksheet Selector -->
              <div v-if="worksheetWorkflow.workbookSheets.length > 0" class="worksheet-selector-section">
                <WorksheetSelector
                  :workbook-sheets="worksheetWorkflow.workbookSheets"
                  :worksheet-status="worksheetWorkflow.worksheetStatus"
                  :selected-worksheet="worksheetWorkflow.selectedWorksheet"
                  :loading="fileLoading"
                  :error="uploadError"
                  @select-sheet="handleWorksheetSelect"
                  @work-on-sheet="handleWorkOnSheet"
                  @view-results="handleViewResults"
                />
              </div>

              <!-- Preview -->
              <div v-if="rawData.length && showPreview" class="excel-preview-section">
                <h4>File Preview (first {{ Math.min(rawData.length, 500) }} rows)</h4>
                <p class="preview-info">{{ rawData.length }} total rows — edit cells below like Excel</p>
                <ExcelViewer
                  :data="rawData.slice(0, 500)"
                  :headers="uploadPreviewHeaders"
                  :original-data="originalRawData.slice(0, 500)"
                  :original-headers="originalFileColumns"
                  :show-mapping-controls="true"
                  :column-mapping="columnMapping"
                  :available-file-columns="fileColumns"
                  :required-columns="requiredColumns"
                  @data-update="onRawExcelUpdate"
                  @mapping-update="updateColumnMapping"
                />
                <button class="btn-review-excel-small" @click="openExcelReview(rawData, 'Uploaded Data')">Full Screen</button>
              </div>
            </v-card-text>
          </v-card>
        </div>

        <!-- ===== CLEANING ===== -->
        <div v-if="activeTab === 'cleaning'" class="content-card">
          <v-card>
            <v-card-title><v-icon>mdi-broom</v-icon> Data Cleaning</v-card-title>
            <v-card-text>
              <div class="cleaning-options">
                <h4>Cleaning Options</h4>
                <div class="options-grid">
                  <label class="option-item">
                    <input type="checkbox" v-model="cleaningOptions.removeDuplicates" />
                    <span>Remove duplicate rows</span>
                  </label>
                  <label class="option-item">
                    <input type="checkbox" v-model="cleaningOptions.fillMissingText" />
                    <span>Fill missing text values with "N/A"</span>
                  </label>
                  <label class="option-item">
                    <input type="checkbox" v-model="cleaningOptions.trimWhitespace" />
                    <span>Trim whitespace from text fields</span>
                  </label>
                  <label class="option-item">
                    <input type="checkbox" v-model="cleaningOptions.convertToNumbers" />
                    <span>Convert numeric strings to numbers</span>
                  </label>
                  <label class="option-item">
                    <input type="checkbox" v-model="cleaningOptions.dropRowsWithMissing" />
                    <span>Drop rows with missing required字段</span>
                  </label>
                </div>
                <button class="btn-primary" @click="applyCleaning" :disabled="!rawData.length">Apply Cleaning</button>
              </div>

              <div v-if="cleaningStats.totalRows > 0" class="cleaning-stats">
                <h4>Cleaning Statistics</h4>
                <div class="stats-grid">
                  <div class="stat-item">
                    <span class="stat-label">Total Rows</span>
                    <span class="stat-value">{{ cleaningStats.totalRows }}</span>
                  </div>
                  <div class="stat-item">
                    <span class="stat-label">Valid Rows</span>
                    <span class="stat-value">{{ cleaningStats.validRows }}</span>
                  </div>
                  <div class="stat-item">
                    <span class="stat-label">Removed Rows</span>
                    <span class="stat-value">{{ cleaningStats.removedRows }}</span>
                  </div>
                </div>
              </div>

              <div v-if="cleanedData.length" class="cleaned-preview">
                <h4>Cleaned Data Preview</h4>
                <ExcelViewer
                  :data="cleanedData.slice(0, 500)"
                  :headers="Object.keys(cleanedData[0] || {})"
                  @data-update="onCleanedExcelUpdate"
                />
              </div>
            </v-card-text>
          </v-card>
        </div>

        <!-- ===== CALCULATIONS ===== -->
        <div v-if="activeTab === 'calculations'" class="content-card">
          <v-card>
            <v-card-title><v-icon>mdi-calculator</v-icon> Calculations</v-card-title>
            <v-card-text>
              <button class="btn-primary" @click="performCalculations" :disabled="!cleanedData.length && !rawData.length">
                Perform Calculations
              </button>

              <div v-if="Object.keys(calculations).length > 0" class="calculations-results">
                <h4>Calculation Results</h4>
                <div class="results-grid">
                  <div v-for="(value, key) in calculations" :key="key" class="result-item">
                    <span class="result-label">{{ key }}</span>
                    <span class="result-value">{{ formatNumber(value) }}</span>
                  </div>
                </div>
              </div>
            </v-card-text>
          </v-card>
        </div>

        <!-- ===== VISUALIZATIONS ===== -->
        <div v-if="activeTab === 'visualizations'" class="content-card">
          <v-card>
            <v-card-title><v-icon>mdi-chart-line</v-icon> Visualizations</v-card-title>
            <v-card-text>
              <div class="visualization-container">
                <canvas ref="yieldCurveChart"></canvas>
              </div>
            </v-card-text>
          </v-card>
        </div>

        <!-- ===== SUMMARY ===== -->
        <div v-if="activeTab === 'summary'" class="content-card">
          <v-card>
            <v-card-title><v-icon>mdi-file-document-outline</v-icon> Summary</v-card-title>
            <v-card-text>
              <ProfessionalExcelView
                v-if="instrumentSummary.rows.length"
                :data="instrumentSummary.rows"
                :columns="instrumentSummary.columns"
                :title="`${instrumentName} Summary`"
              />
              <div v-else class="no-data">
                <p>No summary data available. Complete the workflow to generate a summary.</p>
              </div>
            </v-card-text>
          </v-card>
        </div>

        <!-- ===== REPORTS ===== -->
        <div v-if="activeTab === 'reports'" class="content-card">
          <v-card>
            <v-card-title><v-icon>mdi-file-chart-outline</v-icon> Reports</v-card-title>
            <v-card-text>
              <button class="btn-primary" @click="generateReport">Generate Report</button>
            </v-card-text>
          </v-card>
        </div>
      </div>
    </div>

    <!-- Excel Workbook Viewer -->
    <v-dialog v-model="showWorkbookViewer" max-width="95%" fullscreen hide-overlay>
      <v-card>
        <v-card-title class="excel-dialog-title">
          <span>Excel Workbook Viewer</span>
          <v-spacer></v-spacer>
          <button class="btn-close-dialog" @click="showWorkbookViewer = false">
            <v-icon>mdi-close</v-icon>
          </button>
        </v-card-title>
        <v-card-text class="pa-0" style="height: calc(100vh - 120px);">
          <ExcelWorkbookViewer
            v-if="originalFileBuffer"
            :file-buffer="originalFileBuffer"
            :file-name="uploadedFile?.name || 'workbook.xlsx'"
          />
        </v-card-text>
      </v-card>
    </v-dialog>

    <!-- Excel Modal Viewer -->
    <v-dialog v-model="showExcelDialog" max-width="95%" fullscreen hide-overlay>
      <v-card>
        <v-card-title class="excel-dialog-title">
          <span>{{ excelDialogTitle }}</span>
          <v-spacer></v-spacer>
          <button class="btn-close-dialog" @click="showExcelDialog = false">
            <v-icon>mdi-close</v-icon>
          </button>
        </v-card-title>
        <v-card-text class="pa-0" style="height: calc(100vh - 120px);">
          <ExcelModalViewer :data="excelData" :columns="excelColumns" />
        </v-card-text>
      </v-card>
    </v-dialog>
  </FixedLayout>
</template>

<script setup>
// ===== IMPORTS =====
import { ref, computed, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import FixedLayout from '@/components/FixedLayout.vue'
import * as XLSX from 'xlsx'
import api from '@/services/api.js'
import sessionManager from '@/services/sessionManager.js'
import { useWorksheetWorkflow } from '@/composables/useWorksheetWorkflow.js'
import ExcelViewer from '@/components/ExcelViewer.vue'
import ExcelWorkbookViewer from '@/components/ExcelWorkbookViewer.vue'
import ExcelModalViewer from '@/components/ExcelModalViewer.vue'
import WorksheetSelector from '@/components/WorksheetSelector.vue'
import ProfessionalExcelView from '@/components/ProfessionalExcelView.vue'
import { markStepCompleted, isStepPersistedCompleted } from '@/utils/workflowProgress.js'
import { buildWorkflowSnapshot, applyWorkflowToPage } from '@/utils/instrumentSession.js'
import { useInstrumentConfig } from '@/composables/useInstrumentConfig'
import { autoMatchColumns, applyMappingToRows, isColumnMapped, getMissingColumns } from '@/utils/instrumentMapping'
import { parseExcel } from '@/utils/intelligentParser'
import { detectSheetType, extractSingleInstrumentValues, getRequiredFieldMappings } from '@/utils/sheetTypeDetector'
import Chart from 'chart.js/auto'
import { API_BASE_URL } from '@/config.js'
import { getInstrumentColumns, getTotalFields } from '@/config/instrumentColumns.js'

// ===== COMPOSABLES =====
const router = useRouter()
const route = useRoute()
const { requiredColumns, columnVariations, workflowSteps, loadConfig } = useInstrumentConfig('bonds')
// worksheetWorkflow will be initialized after instrumentType computed is defined

// ===== REFS =====
const activeSession = ref(null)
const yieldCurveLoading = ref(false)
const yieldCurveError = ref('')
const yieldCurveChart = ref(null)
const chartInstanceRef = { current: null }
const yieldCurveData = ref([])
const chartSeriesLabel = ref('')
const currentMarketRate = ref(null)

const selectedMaturityOption = ref('')
const selectedCountryOption = ref('USA')
const selectedCurrencyOption = ref('USD')

const uploadedFile = ref(null)
const uploadedFileId = ref(null)
const uploadedFilePath = ref(null)
const uploadedFileBase64 = ref(null)
const rawData = ref([])
const cleanedData = ref([])
const previewData = ref([])
const columnMapping = ref({})
const showMappingDialog = ref(false)
const showSavedMappingsDialog = ref(false)
const fileColumns = ref([])
const fixedValuesTracker = ref(new Map())
const calculations = ref({})
const cleaningStats = ref({ totalRows: 0, validRows: 0, removedRows: 0, fixedMissing: 0 })
const fileLoading = ref(false)
const uploadError = ref('')
const showInstrumentExcelPopup = ref(false)
const showPortfolioExcelPopup = ref(false)
const showWorkflowPopup = ref(false)
const selectedWorkflowInstrument = ref(null)
const selectedWorkflowIndex = ref(0)
const sortColumn = ref('')
const sortOrder = ref('asc')
const mappingApplied = ref(false)
const cumulativeRecords = ref([])
const showCumulativeHistory = ref(false)
const originalRawData = ref([])
const originalFileColumns = ref([])
const originalFileBuffer = ref(null)
const sessionSavedAt = ref(null)
const showPreview = ref(false)
const forceUpdate = ref(0)

const savedTemplates = ref({})
const selectedTemplate = ref('')
const newTemplateName = ref('')

const cleaningOptions = ref({
  removeDuplicates: true, fillMissingText: true, dropRowsWithMissing: false, trimWhitespace: true,
  convertToNumbers: true, removeOutliers: false, standardizeDates: false, removeSpecialChars: false,
  changeCase: false, caseType: 'none', fillWithCustom: false, customFillValue: '',
  removeColumnsAllMissing: false, capOutliers: false, removeRowsSpecificColumnEmpty: false,
  specificColumn: '', standardizeNumericRange: false, removeEmptyRows: false, fillForward: false, fillBackward: false
})

// Instrument-specific summary state
const selectedInstrumentType = ref('Bonds')
const instrumentSummary = ref({ columns: [], rows: [] })
const portfolioSummary = ref({ columns: [], rows: [] })
const selectedCalculationInstrument = ref(0)
const showAllCalculationsPopup = ref(false)
const sheetType = ref('multi')
const extractedValues = ref({})
const worksheetStatus = ref({})

const uploadHistory = ref([])
const uploadProgress = ref(0)

const selectedInstruments = ref({ moneyMarket: true, bonds: true, tbills: true })
const reportPreviewDialog = ref(false)
const reportPreviewHtml = ref('')

const showExcelDialog = ref(false)
const excelData = ref([])
const excelColumns = ref([])
const excelDialogTitle = ref('')

const showWorkbookViewer = ref(false)
const currentSheetName = ref('')
const workbookSheets = ref([])

const formulaDialog = ref(false)
const formulaText = ref('')
const selectedCell = ref(null)
const selectedCellRef = ref('')
const formulaBarValue = ref('')
const formulaInput = ref(null)

let saveTimeout = null
let lastInstrument = ''
let lastSessionId = ''
let lastSaveTime = 0
const SAVE_DEBOUNCE_MS = 2000

// ===== COMPUTED =====
const instrumentType = computed(() => 'bonds')
const instrumentName = computed(() => 'Bonds')
const instrumentDescription = computed(() => 'Fixed income securities including government and corporate bonds')

const activeTab = computed({
  get: () => route.query.tab || 'upload',
  set: (val) => router.push({ query: { ...route.query, tab: val } })
})

// Initialize worksheet workflow after instrumentType computed is available
const worksheetWorkflow = useWorksheetWorkflow(instrumentType)

const steps = computed(() => {
  if (workflowSteps.value.length) {
    return workflowSteps.value.map(s => ({ tab: s.tab, name: s.name }))
  }
  return [
    { tab: 'upload', name: 'Upload' },
    { tab: 'cleaning', name: 'Clean' },
    { tab: 'calculations', name: 'Calculate' },
    { tab: 'visualizations', name: 'Visualize' },
    { tab: 'summary', name: 'Summary' },
    { tab: 'reports', name: 'Report' }
  ]
})

const currentStepIndex = computed(() => steps.value.findIndex(s => s.tab === activeTab.value))
const totalSteps = computed(() => steps.value.length)
const farthestAllowedIndex = computed(() => {
  for (let i = 0; i < steps.value.length; i++) {
    if (!isStepComplete(steps.value[i].tab)) return i
  }
  return steps.value.length - 1
})

const fileSize = computed(() => {
  if (!uploadedFile.value) return ''
  const bytes = uploadedFile.value.size
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(2) + ' MB'
})

const uploadPreviewHeaders = computed(() => {
  if (rawData.value.length === 0) return []
  return Object.keys(rawData.value[0])
})

const missingColumns = computed(() => {
  return requiredColumns.value.filter(col => !columnMapping.value[col])
})

const hasCleanedData = computed(() => cleanedData.value.length > 0)

const effectiveCountry = computed(() => selectedCountryOption.value)
const effectiveCurrency = computed(() => selectedCurrencyOption.value)
const effectiveMaturity = computed(() => selectedMaturityOption.value)

// ===== FUNCTIONS =====
function isStepComplete(tab) {
  return isStepPersistedCompleted(activeSession.value?.id, tab)
}

function switchTab(tab) {
  const index = steps.value.findIndex(s => s.tab === tab)
  if (index <= farthestAllowedIndex.value) {
    activeTab.value = tab
  }
}

function handleFileUpload(e) {
  const file = e.target.files[0]
  if (file) {
    const fileCopy = new File([file], file.name, { type: file.type })
    uploadedFile.value = fileCopy
    readFileData(fileCopy)
  }
}

function handleDrop(e) {
  e.preventDefault()
  const file = e.dataTransfer.files[0]
  if (file) {
    const fileCopy = new File([file], file.name, { type: file.type })
    uploadedFile.value = fileCopy
    readFileData(fileCopy)
  }
}

async function readFileData(file) {
  console.log('readFileData called with file:', file.name, 'size:', file.size)
  fileLoading.value = true
  uploadProgress.value = 0
  
  try {
    const result = await worksheetWorkflow.handleFileUpload(file)
    
    if (result.success) {
      workbookSheets.value = worksheetWorkflow.workbookSheets.value
      worksheetStatus.value = worksheetWorkflow.worksheetStatus.value
      originalFileBuffer.value = worksheetWorkflow.originalFileBuffer.value
      
      console.log('✅ Workbook loaded via worksheet workflow:', result.sheets.length, 'sheets')
      
      if (result.sheets.length > 0) {
        const firstSheet = result.sheets[0]
        const selection = worksheetWorkflow.selectWorksheet(firstSheet.name)
        if (selection.success) {
          currentSheetName.value = firstSheet.name
          console.log('✅ Auto-selected first sheet:', firstSheet.name)
        }
      }
      
      addToHistory(file.name, result.sheets[0]?.data || [])
      debouncedSave()
      forceUpdate.value++
    } else {
      throw new Error(result.error || 'Failed to upload workbook')
    }
  } catch (err) {
    console.error('Upload error:', err)
    uploadError.value = err.message
    alert(`Failed to parse file: ${err.message}`)
    rawData.value = []
  } finally {
    fileLoading.value = false
    uploadProgress.value = 0
  }
}

function removeFile() {
  uploadedFile.value = null
  uploadedFileId.value = null
  uploadedFilePath.value = null
  uploadedFileBase64.value = null
  rawData.value = []
  originalRawData.value = []
  originalFileColumns.value = []
  cleanedData.value = []
  previewData.value = []
  calculations.value = {}
  fixedValuesTracker.value.clear()
  mappingApplied.value = false
  columnMapping.value = {}
  fileColumns.value = []
  showPreview.value = false
  uploadError.value = ''
  worksheetWorkflow.reset()
  debouncedSave()
  forceUpdate.value++
  if (fileInput.value) fileInput.value.value = ''
}

// Worksheet selector event handlers
function handleWorksheetSelect(sheetName) {
  worksheetWorkflow.selectWorksheet(sheetName)
  currentSheetName.value = sheetName
}

async function handleWorkOnSheet(sheetName) {
  fileLoading.value = true
  uploadError.value = ''
  
  try {
    const result = await worksheetWorkflow.processWorksheet(
      sheetName,
      requiredColumns.value,
      columnVariations.value
    )
    
    if (result.success) {
      rawData.value = result.tabularData || []
      sheetType.value = result.sheetType || 'multi'
      extractedValues.value = result.extractedValues || {}
      
      worksheetStatus.value[sheetName] = {
        ...worksheetStatus.value[sheetName],
        processed: true,
        sheetType: result.sheetType
      }
      
      if (result.sheetType === 'single') {
        showPreview.value = true
      }
      
      debouncedSave()
      forceUpdate.value++
    } else {
      uploadError.value = result.error || 'Failed to process worksheet'
    }
  } catch (err) {
    console.error('Worksheet processing error:', err)
    uploadError.value = err.message
  } finally {
    fileLoading.value = false
  }
}

function handleViewResults(sheetName) {
  const status = worksheetStatus.value[sheetName]
  if (status?.processed) {
    if (status.sheetType === 'single') {
      activeTab.value = 'summary'
    } else {
      activeTab.value = 'calculations'
    }
  }
}

function togglePreview() {
  showPreview.value = !showPreview.value
}

function openMappingDialog() {
  showMappingDialog.value = true
}

function closeMappingDialog() {
  showMappingDialog.value = false
}

function applyColumnMappingAndClose() {
  applyCurrentMapping()
  showMappingDialog.value = false
}

function applyCurrentMapping() {
  if (!originalRawData.value.length) return
  const hasAnyMapping = requiredColumns.value.some(col => columnMapping.value[col])
  if (!hasAnyMapping) {
    rawData.value = originalRawData.value
    mappingApplied.value = false
    return
  }
  const mappedData = originalRawData.value.map(row => {
    const newRow = {}
    requiredColumns.value.forEach(col => {
      const srcCol = columnMapping.value[col]
      newRow[col] = srcCol ? row[srcCol] : ''
    })
    return newRow
  })
  rawData.value = mappedData
  const allMapped = requiredColumns.value.every(col => columnMapping.value[col])
  mappingApplied.value = allMapped
}

function updateColumnMapping(newMapping) {
  columnMapping.value = { ...newMapping }
  applyCurrentMapping()
  debouncedSave()
}

function refreshFileColumns() {
  if (rawData.value.length) {
    fileColumns.value = Object.keys(rawData.value[0])
  }
}

function onRawExcelUpdate(data, sourceData) {
  if (sourceData?.length) originalRawData.value = sourceData
  rawData.value = data
  debouncedSave()
}

function onCleanedExcelUpdate(data) {
  cleanedData.value = data
  debouncedSave()
}

function applyCleaning() {
  const data = rawData.value.length ? rawData.value : originalRawData.value
  if (!data.length) return
  
  let cleaned = [...data]
  
  if (cleaningOptions.value.removeDuplicates) {
    cleaned = cleaned.filter((row, index, self) =>
      index === self.findIndex(r => JSON.stringify(r) === JSON.stringify(row))
    )
  }
  
  if (cleaningOptions.value.trimWhitespace) {
    cleaned = cleaned.map(row => {
      const newRow = {}
      Object.keys(row).forEach(key => {
        newRow[key] = typeof row[key] === 'string' ? row[key].trim() : row[key]
      })
      return newRow
    })
  }
  
  if (cleaningOptions.value.convertToNumbers) {
    cleaned = cleaned.map(row => {
      const newRow = {}
      Object.keys(row).forEach(key => {
        const val = row[key]
        newRow[key] = typeof val === 'string' && !isNaN(parseFloat(val)) ? parseFloat(val) : val
      })
      return newRow
    })
  }
  
  if (cleaningOptions.value.fillMissingText) {
    cleaned = cleaned.map(row => {
      const newRow = {}
      Object.keys(row).forEach(key => {
        newRow[key] = row[key] === '' || row[key] === null || row[key] === undefined ? 'N/A' : row[key]
      })
      return newRow
    })
  }
  
  if (cleaningOptions.value.dropRowsWithMissing) {
    cleaned = cleaned.filter(row => {
      return requiredColumns.value.every(col => row[col] && row[col] !== '' && row[col] !== 'N/A')
    })
  }
  
  cleanedData.value = cleaned
  cleaningStats.value = {
    totalRows: rawData.value.length,
    validRows: cleanedData.value.length,
    removedRows: rawData.value.length - cleanedData.value.length,
    fixedMissing: 0
  }
  
  markStepCompleted(activeSession.value?.id, 'cleaning')
  debouncedSave()
  forceUpdate.value++
}

async function performCalculations() {
  const data = cleanedData.value.length ? cleanedData.value : rawData.value
  if (!data.length) return
  
  fileLoading.value = true
  
  try {
    const response = await fetch(`${API_BASE_URL}/api/calculate/bonds`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ data })
    })
    
    const result = await response.json()
    
    if (result.success) {
      calculations.value = result.calculations
      markStepCompleted(activeSession.value?.id, 'calculations')
    } else {
      throw new Error(result.error || 'Calculation failed')
    }
  } catch (err) {
    console.error('Calculation error:', err)
    alert(`Calculation failed: ${err.message}`)
  } finally {
    fileLoading.value = false
  }
  
  debouncedSave()
  forceUpdate.value++
}

function openWorkbookViewer() {
  showWorkbookViewer.value = true
}

function openExcelReview(data, title) {
  excelData.value = data
  excelColumns.value = data.length > 0 ? Object.keys(data[0]) : []
  excelDialogTitle.value = title
  showExcelDialog.value = true
}

function formatNumber(num) {
  if (num === null || num === undefined || isNaN(num)) return '0'
  return num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function addToHistory(name, data) {
  uploadHistory.value.unshift({
    name,
    date: new Date().toISOString(),
    data: JSON.parse(JSON.stringify(data))
  })
  if (uploadHistory.value.length > 10) {
    uploadHistory.value.pop()
  }
  saveUploadHistory()
}

function loadHistoryFile(item) {
  uploadedFile.value = { name: item.name, size: 0 }
  rawData.value = item.data
  originalRawData.value = JSON.parse(JSON.stringify(item.data))
  originalFileColumns.value = Object.keys(item.data[0] || {})
  fileColumns.value = [...originalFileColumns.value]
  columnMapping.value = autoMatchColumns(fileColumns.value, requiredColumns.value, columnVariations.value)
  applyCurrentMapping()
  showPreview.value = true
  forceUpdate.value++
}

function deleteHistoryItem(idx) {
  uploadHistory.value.splice(idx, 1)
  saveUploadHistory()
}

function saveUploadHistory() {
  localStorage.setItem('bonds_upload_history', JSON.stringify(uploadHistory.value))
}

function generateReport() {
  alert('Report generation feature coming soon')
}

function notifySessionUpdated(explicitSave = false, options = {}) {
  const sessionId = activeSession.value?.id || sessionManager.getActiveSessionId()
  if (!sessionId) return
  
  const detail = {
    sessionId,
    explicitSave,
    instrument: 'bonds',
    ...options
  }
  
  window.dispatchEvent(new CustomEvent('session-updated', { detail }))
}

function saveToSession() {
  if (!activeSession.value) {
    alert('Please select or create a session on the Dashboard first.')
    return
  }
  saveSessionData()
  sessionSavedAt.value = new Date().toISOString()
  
  const versionData = {
    instrument: instrumentType.value,
    tab: activeTab.value,
    description: `Saved ${instrumentName.value} - ${activeTab.value}`,
    data: {
      rawData: rawData.value,
      cleanedData: cleanedData.value,
      calculations: calculations.value,
      columnMapping: columnMapping.value,

      worksheetStatus: worksheetStatus.value,
      workbookSheets: workbookSheets.value,
      instrumentSummary: instrumentSummary.value,
      portfolioSummary: portfolioSummary.value
    }
  }
  sessionManager.addVersion(activeSession.value.id, versionData)
  
  notifySessionUpdated(true, {
    changeType: 'Saved',
    instrument: instrumentName.value,
    shortDescription: `Saved ${instrumentName.value} to session`,
    modifiedInstruments: [instrumentName.value]
  })
  alert('Saved to session. A new version has been recorded in Version History.')
}

function saveSessionData() {
  if (!activeSession.value) return
  const sid = activeSession.value.id
  const wf = buildWorkflowSnapshot({
    rawData: rawData.value,
    cleanedData: cleanedData.value,
    calculations: calculations.value,
    activeTab: activeTab.value,
    uploadedFile: uploadedFile.value,
    cleaningStats: cleaningStats.value,
    columnMapping: columnMapping.value,
    mappingApplied: mappingApplied.value,
    originalRawData: originalRawData.value,
    originalFileColumns: originalFileColumns.value,
    yieldCurveData: yieldCurveData.value,
    sessionSavedAt: sessionSavedAt.value,
    showPreview: showPreview.value,
    completedSteps: [],
    workbookSheets: workbookSheets.value,
    worksheetStatus: worksheetStatus.value,
    instrumentSummary: instrumentSummary.value,
    portfolioSummary: portfolioSummary.value,
    worksheetWorkflowState: worksheetWorkflow.getStateSnapshot()
  })
  sessionManager.saveInstrumentWorkflow(sid, instrumentType.value, wf)
  sessionManager.updateSession(sid, { last_tab: activeTab.value })

  const key = `${instrumentType.value}_session_${sid}`
  localStorage.setItem(`${key}_raw`, JSON.stringify(rawData.value))
  localStorage.setItem(`${key}_original`, JSON.stringify(originalRawData.value))
  localStorage.setItem(`${key}_clean`, JSON.stringify(cleanedData.value))
  localStorage.setItem(`${key}_calc`, JSON.stringify(calculations.value))
  localStorage.setItem(`${key}_mapping`, JSON.stringify(columnMapping.value))
  localStorage.setItem(`${key}_showPreview`, JSON.stringify(showPreview.value))
  localStorage.setItem(`${key}_workbookSheets`, JSON.stringify(workbookSheets.value))
  localStorage.setItem(`${key}_worksheetStatus`, JSON.stringify(worksheetStatus.value))
  localStorage.setItem(`${key}_sheetType`, JSON.stringify(sheetType.value))
  localStorage.setItem(`${key}_extractedValues`, JSON.stringify(extractedValues.value))
  localStorage.setItem(`${key}_currentSheetName`, JSON.stringify(currentSheetName.value))
  if (uploadedFile.value) localStorage.setItem(`${instrumentType.value}_uploaded_file_name`, uploadedFile.value.name)
}

async function loadSavedData() {
  if (!activeSession.value) return false
  const sid = activeSession.value.id
  let wf = sessionManager.getInstrumentWorkflow(sid, instrumentType.value)
  if (!wf) {
    await sessionManager.loadSessionFromDb(sid)
    wf = sessionManager.getInstrumentWorkflow(sid, instrumentType.value)
  }
  if (wf) {
    const loaded = applyWorkflowToPage(wf, {
      rawData, cleanedData, calculations, uploadedFile, cleaningStats,
      columnMapping, mappingApplied, originalRawData, originalFileColumns,
      yieldCurveData, showPreview, workbookSheets,
      worksheetStatus, instrumentSummary, portfolioSummary
    })
    if (wf.sessionSavedAt) sessionSavedAt.value = wf.sessionSavedAt
    if (originalFileColumns.value.length) fileColumns.value = [...originalFileColumns.value]
    else if (originalRawData.value.length) fileColumns.value = Object.keys(originalRawData.value[0] || {})
    if (wf.last_tab && !route.query.tab) activeTab.value = wf.last_tab
    if (wf.worksheetWorkflowState) {
      worksheetWorkflow.restoreState(wf.worksheetWorkflowState)
    }
    const key = `${instrumentType.value}_session_${sid}`
    const savedSheetType = localStorage.getItem(`${key}_sheetType`)
    if (savedSheetType) sheetType.value = JSON.parse(savedSheetType)
    const savedExtractedValues = localStorage.getItem(`${key}_extractedValues`)
    if (savedExtractedValues) extractedValues.value = JSON.parse(savedExtractedValues)
    const savedCurrentSheetName = localStorage.getItem(`${key}_currentSheetName`)
    if (savedCurrentSheetName) currentSheetName.value = JSON.parse(savedCurrentSheetName)
    applyCurrentMapping()
    showPreview.value = false
    forceUpdate.value++
    return loaded
  }
  return false
}

function debouncedSave(explicitSave = false) {
  if (saveTimeout) clearTimeout(saveTimeout)
  const now = Date.now()
  if (!explicitSave && now - lastSaveTime < SAVE_DEBOUNCE_MS) return
  saveTimeout = setTimeout(() => {
    saveSessionData()
    lastSaveTime = Date.now()
  }, explicitSave ? 100 : SAVE_DEBOUNCE_MS)
}

// ===== WATCHERS & LIFECYCLE =====
watch([rawData, cleanedData], () => debouncedSave(), { deep: true })

onMounted(async () => {
  await loadConfig()
  activeSession.value = sessionManager.getActiveSession()
  await loadSavedData()
  
  const history = localStorage.getItem('bonds_upload_history')
  if (history) {
    try {
      uploadHistory.value = JSON.parse(history)
    } catch(e) {}
  }
})

onBeforeUnmount(() => {
  if (saveTimeout) clearTimeout(saveTimeout)
})
</script>

<style scoped>
/* Add styles similar to MoneyMarket.vue */
.instrument-page {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header-left h1 {
  margin: 0;
  color: #0B2044;
}

.header-left p {
  margin: 5px 0 0 0;
  color: #666;
}

.session-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 5px 10px;
  background: #e8f5e9;
  color: #2e7d32;
  border-radius: 4px;
  margin-top: 10px;
}

.session-badge.warning {
  background: #fff3e0;
  color: #e65100;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 15px;
}

.btn-save-session {
  padding: 8px 16px;
  background: #0B2044;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.step-indicator {
  color: #666;
  font-size: 14px;
}

.progress-bar-container {
  margin-bottom: 20px;
}

.progress-steps {
  display: flex;
  gap: 10px;
}

.progress-step {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 15px;
  background: #f5f5f5;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
}

.progress-step.active {
  background: #0B2044;
  color: white;
}

.progress-step.completed {
  background: #4caf50;
  color: white;
}

.progress-step.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.step-circle {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: rgba(255,255,255,0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
}

.content-card {
  margin-bottom: 20px;
}

.upload-area {
  border: 2px dashed #ccc;
  border-radius: 8px;
  padding: 40px;
  text-align: center;
  cursor: pointer;
  transition: border-color 0.2s;
}

.upload-area:hover {
  border-color: #0B2044;
}

.upload-icon {
  color: #0B2044;
}

.browse-link {
  color: #0B2044;
  text-decoration: underline;
  cursor: pointer;
}

.file-info {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px;
  background: #f5f5f5;
  border-radius: 4px;
  margin-top: 20px;
}

.remove-btn {
  background: none;
  border: none;
  font-size: 20px;
  cursor: pointer;
  color: #f44336;
}

.btn-view-workbook,
.btn-preview,
.btn-mapping {
  padding: 6px 12px;
  background: #0B2044;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  margin-left: 10px;
}

.btn-primary {
  padding: 10px 20px;
  background: #0B2044;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.btn-secondary {
  padding: 10px 20px;
  background: #666;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.loading-container {
  text-align: center;
  padding: 40px;
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.worksheet-selector-section {
  margin-top: 20px;
}

.excel-preview-section {
  margin-top: 20px;
}

.cleaning-options {
  margin-bottom: 20px;
}

.options-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 10px;
  margin: 15px 0;
}

.option-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.cleaning-stats {
  margin: 20px 0;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 15px;
  margin: 15px 0;
}

.stat-item {
  text-align: center;
  padding: 15px;
  background: #f5f5f5;
  border-radius: 4px;
}

.stat-label {
  display: block;
  color: #666;
  margin-bottom: 5px;
}

.stat-value {
  display: block;
  font-size: 24px;
  font-weight: bold;
  color: #0B2044;
}

.calculations-results {
  margin-top: 20px;
}

.results-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 15px;
  margin: 15px 0;
}

.result-item {
  padding: 15px;
  background: #f5f5f5;
  border-radius: 4px;
}

.result-label {
  display: block;
  color: #666;
  margin-bottom: 5px;
}

.result-value {
  display: block;
  font-size: 20px;
  font-weight: bold;
  color: #0B2044;
}

.visualization-container {
  height: 400px;
  padding: 20px;
}

.no-data {
  text-align: center;
  padding: 40px;
  color: #666;
}

.excel-dialog-title {
  display: flex;
  align-items: center;
  padding: 15px;
  background: #0B2044;
  color: white;
}

.btn-close-dialog {
  background: none;
  border: none;
  color: white;
  font-size: 24px;
  cursor: pointer;
}
</style>
