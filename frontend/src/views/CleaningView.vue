<template>
  <fixed-layout>
    <div class="cleaning-view">

      <div class="page-header">
        <h1>Data Cleaning</h1>
        <p>Clean and prepare your dataset for analysis</p>
      </div>

      <div class="action-buttons">
        <v-btn color="#0B2A44" @click="loadData">
          <v-icon left>mdi-database</v-icon> Load Dataset
        </v-btn>
        <v-btn color="#0B2A44" variant="outlined" @click="toggleDatasetPreview" :disabled="!dataset">
          <v-icon left>mdi-eye</v-icon> Preview Dataset
        </v-btn>
        <v-btn color="#0B2A44" variant="outlined" @click="resetOptions" :disabled="!dataset">
          <v-icon left>mdi-refresh</v-icon> Reset Options
        </v-btn>
        <v-btn color="#0B2A44" variant="outlined" @click="clearResults" :disabled="!dataset">
          <v-icon left>mdi-broom</v-icon> Clear Results
        </v-btn>
        <v-btn color="#0B2A44" variant="outlined" @click="deleteData" v-if="uploadId">
          <v-icon left>mdi-delete</v-icon> Delete Dataset
        </v-btn>
        <v-btn color="#0B2A44" @click="completeProcess" v-if="results">
          <v-icon left>mdi-check</v-icon> Done
        </v-btn>
      </div>

      <template v-if="dataset && dataset.data">

        <v-card class="stats-card">
          <v-card-title class="card-title">
            <v-icon class="title-icon">mdi-database</v-icon> Dataset Overview
          </v-card-title>
          <v-card-text>
            <v-row>
              <v-col cols="12" sm="6" md="3" v-for="stat in kpiStats" :key="stat.title">
                <v-card class="kpi-card">
                  <div class="kpi-top-bar"></div>
                  <v-card-text>
                    <div class="kpi-content">
                      <div class="kpi-icon" :style="{ background: stat.gradient }">
                        <v-icon size="28" color="white">{{ stat.icon }}</v-icon>
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

        <v-card v-if="hasDetectedValues" class="stats-card">
          <v-card-title class="card-title">
            <v-icon class="title-icon">mdi-format-list-checks</v-icon>
            Field Selection
            <v-spacer></v-spacer>
            <v-btn
              v-if="hasAdditionalFields"
              size="small"
              variant="text"
              color="#0B2A44"
              @click="toggleAllAdditional"
            >
              {{ excludedFields.size > 0 ? 'Include all' : 'Exclude additional' }}
            </v-btn>
          </v-card-title>
          <v-card-text>
            <div class="compact-fields-table">
              <div
                v-for="row in detectedValueRows"
                :key="row.key"
                class="compact-field-row"
                :class="{ 'compact-field-row--excluded': !row.included }"
              >
                <label class="compact-checkbox">
                  <input
                    type="checkbox"
                    :checked="row.included"
                    @change="toggleFieldInclusion(row.key)"
                  />
                </label>
                <span class="compact-field-name">{{ row.label }}</span>
                <span class="compact-field-value">{{ row.value }}</span>
              </div>
            </div>
            <div class="compact-summary">
              {{ detectedValueRows.filter(r => r.included).length }} of {{ detectedValueRows.length }} fields included
            </div>
          </v-card-text>
        </v-card>

        <v-card class="stats-card">
          <v-card-title class="card-title">
            <v-icon class="title-icon">mdi-microsoft-excel</v-icon> Dataset Viewer (Editable)
          </v-card-title>
          <v-card-text>
            <div v-if="showDatasetPreview">
              <ExcelViewer
                :data="dataset?.data"
                :headers="dataset?.data ? Object.keys(dataset.data[0] || {}) : []"
                @data-update="handleDataUpdate"
              />
            </div>
            <div v-else class="text-center pa-8">
              <p class="text-grey">Click Preview Dataset to see the editable Excel view.</p>
            </div>
          </v-card-text>
        </v-card>

        <v-row>
          <v-col cols="12">
            <v-card class="stats-card">
              <v-card-title class="card-title">
                <v-icon class="title-icon">mdi-broom</v-icon> Cleaning Options
              </v-card-title>
              <v-card-text>
                <div class="options-container">
                  <v-checkbox v-for="opt in cleaningOptions" :key="opt.key" v-model="opt.value" color="#0B2A44">
                    <template v-slot:label>
                      <div><strong>{{ opt.label }}</strong><div class="desc">{{ opt.desc }}</div></div>
                    </template>
                  </v-checkbox>

                  <div v-if="cleaningOptions.find(o => o.key === 'standardizeDates')?.value" class="date-format-section">
                    <label class="date-format-label">Select Date Format:</label>
                    <v-select
                      v-model="selectedDateFormat"
                      :items="dateFormatOptions"
                      item-title="label"
                      item-value="value"
                      density="compact"
                      variant="outlined"
                      color="#0B2A44"
                      class="date-format-select"
                    ></v-select>
                  </div>

                  <div v-if="cleaningOptions.find(o => o.key === 'changeCase')?.value" class="date-format-section">
                    <label class="date-format-label">Text Case:</label>
                    <v-select
                      v-model="selectedCaseType"
                      :items="caseTypeOptions"
                      item-title="label"
                      item-value="value"
                      density="compact"
                      variant="outlined"
                      color="#0B2A44"
                      class="date-format-select"
                    ></v-select>
                  </div>

                  <div v-if="cleaningOptions.find(o => o.key === 'fillWithCustom')?.value" class="date-format-section">
                    <label class="date-format-label">Custom Fill Value:</label>
                    <v-text-field
                      v-model="customFillValue"
                      placeholder="e.g., Unknown"
                      density="compact"
                      variant="outlined"
                      color="#0B2A44"
                      hide-details
                    ></v-text-field>
                  </div>
                </div>
                <v-progress-linear v-if="isCleaning" indeterminate color="#0B2A44" class="mt-3" />
                <v-btn color="#0B2A44" :disabled="!hasAnyOption" :loading="isCleaning" @click="startCleaning">
                  <v-icon left>mdi-broom</v-icon> Start Cleaning
                </v-btn>
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>

        <v-row v-if="results && results.cleanedData">
          <v-col cols="12">
            <v-card class="stats-card">
              <v-card-title class="card-title">
                <v-icon class="title-icon">mdi-table-check</v-icon> Cleaned Data Preview (Source of Truth)
                <v-spacer></v-spacer>
                <v-chip color="green" size="small">Changes Applied</v-chip>
              </v-card-title>
              <v-card-text>
                <v-row>
                  <v-col cols="12" sm="6" md="3" v-for="stat in resultStats" :key="stat.title">
                    <v-card class="kpi-card result-kpi">
                      <div class="kpi-top-bar"></div>
                      <v-card-text>
                        <div class="kpi-content">
                          <div class="kpi-icon" :style="{ background: stat.gradient }">
                            <v-icon size="28" color="white">{{ stat.icon }}</v-icon>
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

                <ExcelViewer
                  :data="results.cleanedData"
                  :headers="Object.keys(results.cleanedData[0] || {})"
                  @data-update="handleCleanedUpdate"
                />
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>

        <v-row v-if="results">
          <v-col cols="12">
            <v-card class="stats-card">
              <v-card-title class="card-title">
                <v-icon class="title-icon">mdi-chart-line</v-icon> Cleaning Results
              </v-card-title>
              <v-card-text>
                <v-alert type="success" class="mb-3">Cleaning completed!</v-alert>
                <div class="result-item"><span>Original Rows:</span><span>{{ results.originalRows }}</span></div>
                <div class="result-item"><span>Cleaned Rows:</span><span>{{ results.cleanedRows }}</span></div>
                <div class="result-item" v-if="results.duplicatesRemoved"><span>Duplicates Removed:</span><span>{{ results.duplicatesRemoved }}</span></div>
                <div class="result-item" v-if="results.missingValuesFilled"><span>Missing Values Filled:</span><span>{{ results.missingValuesFilled }}</span></div>
                <div class="result-actions">
                  <v-btn color="#0B2A44" @click="goToCalculations">Proceed to Calculations</v-btn>
                  <v-btn color="#0B2A44" variant="outlined" @click="clearResults">Close</v-btn>
                </div>
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>

      </template>

      <v-card v-if="!dataset || !dataset.data" class="stats-card">
        <v-card-text class="text-center pa-8">
          <v-icon size="64" color="#999">mdi-database-off</v-icon>
          <h3 class="mt-4">No Dataset Loaded</h3>
          <p class="text-grey">Click "Load Dataset" to load your uploaded data</p>
          <v-btn color="#0B2A44" @click="loadData">Load Dataset</v-btn>
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
import { dataAPI, datasetAPI } from '../services/api'
import sessionManager from '@/services/sessionManager.js'
import { markStepCompleted } from '@/utils/workflowProgress.js'
import { applyCleaningOperations } from '@/utils/cleaningOperations.js'

const router = useRouter()
const route = useRoute()

const dataset = ref(null)
const originalDataset = ref(null)
const cleanedSourceData = ref([])
const uploadId = ref(null)
const results = ref(null)
const isCleaning = ref(false)
const showDatasetPreview = ref(false)
const sheetNames = ref([])
const selectedSheet = ref('')

const detectedValues = ref({})
const excludedFields = ref(new Set())

const cleaningOptions = ref([
  { key: 'removeDuplicates', label: 'Remove Duplicates', desc: 'Delete duplicate rows', value: true },
  { key: 'removeEmptyRows', label: 'Remove Empty Rows', desc: 'Delete rows with no data', value: true },
  { key: 'trimWhitespace', label: 'Trim Whitespace', desc: 'Remove extra spaces', value: true },
  { key: 'fillMissingText', label: 'Fill Missing Values', desc: "Replace empty values with 'N/A'", value: true },
  { key: 'convertToNumbers', label: 'Convert Text to Numbers', desc: 'Turn numeric text into numbers', value: false },
  { key: 'dropRowsWithMissing', label: 'Drop Rows with Missing Values', desc: 'Delete rows that have empty cells', value: false },
  { key: 'removeOutliers', label: 'Remove Outlier Rows', desc: 'Drop rows beyond 3 standard deviations', value: false },
  { key: 'standardizeDates', label: 'Format Dates', desc: 'Convert dates to selected format', value: false },
  { key: 'changeCase', label: 'Standardize Text Case', desc: 'Upper, lower or title case', value: false },
  { key: 'removeSpecialChars', label: 'Remove Special Characters', desc: 'Strip symbols from text fields', value: false },
  { key: 'standardizeCurrency', label: 'Standardize Currency', desc: 'Normalize currency symbols and codes', value: false },
  { key: 'fillWithCustom', label: 'Fill Missing with Custom Value', desc: 'Use your own fill value', value: false }
])

const caseTypeOptions = ref([
  { value: 'upper', label: 'UPPERCASE' },
  { value: 'lower', label: 'lowercase' },
  { value: 'title', label: 'Title Case' }
])
const selectedCaseType = ref('title')
const customFillValue = ref('')

const dateFormatOptions = ref([
  { value: 'YYYY-MM-DD', label: 'YYYY-MM-DD' },
  { value: 'DD-MM-YYYY', label: 'DD-MM-YYYY' },
  { value: 'MM-DD-YYYY', label: 'MM-DD-YYYY' },
  { value: 'DD/MM/YYYY', label: 'DD/MM/YYYY' },
  { value: 'MM/DD/YYYY', label: 'MM/DD/YYYY' },
  { value: 'YYYY/MM/DD', label: 'YYYY/MM/DD' },
  { value: 'DD-MM-YY', label: 'DD-MM-YY' },
  { value: 'MM-DD-YY', label: 'MM-DD-YY' }
])
const selectedDateFormat = ref('YYYY-MM-DD')

const hasAnyOption = computed(() => cleaningOptions.value.some(o => o.value))
const hasDetectedValues = computed(() => Object.keys(detectedValues.value).length > 0)
const hasAdditionalFields = computed(() =>
  detectedValueRows.value.some(r => !r.required)
)
const detectedValueRows = computed(() =>
  Object.entries(detectedValues.value).map(([key, value]) => ({
    key,
    label: getFieldLabel(key),
    value: value === null || value === undefined || value === '' ? 'Not detected' : value,
    included: !excludedFields.value.has(key),
    required: isRequiredField(key)
  }))
)

function isRequiredField(key) {
  const norm = String(key).toLowerCase().replace(/[-_\s]/g, '')
  const REQUIRED = ['principal', 'interestrate', 'daystomaturity', 'facevalue', 'discountrate', 'couponrate', 'yield', 'maturitydate', 'issuedate', 'frequency', 'instrumentname']
  return REQUIRED.some(f => f.replace(/[-_\s]/g, '') === norm || norm.includes(f) || f.includes(norm))
}

function getFieldLabel(key) {
  const labels = {
    principal: 'Principal', interestRate: 'Interest Rate', daysToMaturity: 'Days to Maturity',
    issueDate: 'Issue Date', maturityDate: 'Maturity Date', faceValue: 'Face Value',
    couponRate: 'Coupon Rate', yield: 'Yield', discountRate: 'Discount Rate',
    frequency: 'Frequency', couponFrequency: 'Coupon Frequency', auctionDate: 'Auction Date',
    instrumentName: 'Instrument Name', purchasePrice: 'Purchase Price',
    settlementDate: 'Settlement Date', currency: 'Currency', country: 'Country'
  }
  return labels[key] || key
}

function toggleFieldInclusion(key) {
  const next = new Set(excludedFields.value)
  if (next.has(key)) next.delete(key)
  else next.add(key)
  excludedFields.value = next
  persistExclusions()
  if (results.value?.cleanedData) {
    rebuildCleanedFromExclusions()
  }
}

function toggleAllAdditional() {
  const additional = new Set()
  for (const row of detectedValueRows.value) {
    if (!row.required) additional.add(row.key)
  }
  if (excludedFields.value.size > 0) {
    excludedFields.value = new Set()
  } else {
    excludedFields.value = additional
  }
  persistExclusions()
  if (results.value?.cleanedData) rebuildCleanedFromExclusions()
}

function persistExclusions() {
  const sid = sessionManager.getActiveSession()?.id || sessionManager.getActiveSessionId()
  const type = normalizeInstrumentType(dataset.value?.instrumentType)
  try {
    if (sid) {
      sessionStorage.setItem(`excluded_fields:${sid}:${type}`, JSON.stringify([...excludedFields.value]))
    }
  } catch (e) { /* ignore */ }
  try {
    if (sid) {
      sessionManager.getInstrumentWorkflow(sid, type)
        .then(wf => {
          if (wf) sessionManager.saveInstrumentWorkflow(sid, type, {
            ...wf,
            excludedDetectedFields: [...excludedFields.value]
          })
        })
        .catch(() => {})
    }
  } catch (e) { /* ignore */ }
}

function rebuildCleanedFromExclusions() {
  if (!cleanedSourceData.value.length) return
  const filtered = cleanedSourceData.value.map(row => {
    const newRow = {}
    for (const [k, v] of Object.entries(row)) {
      const normalizedKey = String(k).toLowerCase().replace(/[-_\s().]+/g, '')
      const isExcluded = [...excludedFields.value].some(excluded =>
        normalizedKey === String(excluded).toLowerCase().replace(/[-_\s().]+/g, '')
      )
      if (!isExcluded) newRow[k] = v
    }
    return newRow
  })
  results.value.cleanedData = filtered
  dataset.value.data = filtered
}

async function loadDetectedValues() {
  const sid = sessionManager.getActiveSession()?.id || sessionManager.getActiveSessionId()
  const type = normalizeInstrumentType(dataset.value?.instrumentType)
  let workflowLoaded = false
  try {
    if (sid) {
      const wf = await sessionManager.getInstrumentWorkflow(sid, type)
      if (wf) {
        workflowLoaded = true
        const fields =
          (wf.autoDetectedFields && Object.keys(wf.autoDetectedFields).length && wf.autoDetectedFields) ||
          (wf.extractedValues && Object.keys(wf.extractedValues).length && wf.extractedValues) ||
          null
        if (fields) detectedValues.value = { ...fields }
        if (Array.isArray(wf.excludedDetectedFields)) {
          excludedFields.value = new Set(wf.excludedDetectedFields)
        }
      }
    }
  } catch (e) { console.warn('read from session workflow failed', e) }

  if (workflowLoaded) return

  try {
    if (!sid) {
      const stored =
        sessionStorage.getItem('detectedValues') ||
        sessionStorage.getItem('detected_values') ||
        sessionStorage.getItem('extracted_values')
      if (stored) detectedValues.value = JSON.parse(stored)
    }
    const storedExcluded = sid
      ? sessionStorage.getItem(`excluded_fields:${sid}:${type}`)
      : null
    if (storedExcluded) excludedFields.value = new Set(JSON.parse(storedExcluded))
  } catch (e) { detectedValues.value = {} }
}

const kpiStats = computed(() => {
  if (!dataset.value?.data) return []
  return [
    { title: 'Total Rows', value: dataset.value.data.length.toLocaleString(), icon: 'mdi-table-row', gradient: 'linear-gradient(135deg, #0B2044, #1a3a6e)' },
    { title: 'Total Columns', value: Object.keys(dataset.value.data[0] || {}).length, icon: 'mdi-view-column', gradient: 'linear-gradient(135deg, #1E88E5, #42a5f5)' },
    { title: 'Instrument Type', value: dataset.value.instrumentType || 'Financial Instruments', icon: 'mdi-chart-line', gradient: 'linear-gradient(135deg, #4CAF50, #2E7D32)' },
    { title: 'File Name', value: dataset.value.name || 'Dataset', icon: 'mdi-file-document', gradient: 'linear-gradient(135deg, #FFC107, #FF9800)' }
  ]
})

const resultStats = computed(() => {
  if (!results.value) return []
  return [
    { title: 'Original Rows', value: results.value.originalRows, icon: 'mdi-table-row', gradient: 'linear-gradient(135deg, #0B2044, #1a3a6e)' },
    { title: 'Cleaned Rows', value: results.value.cleanedRows, icon: 'mdi-check-circle', gradient: 'linear-gradient(135deg, #4CAF50, #2E7D32)' },
    { title: 'Duplicates Removed', value: results.value.duplicatesRemoved || 0, icon: 'mdi-delete', gradient: 'linear-gradient(135deg, #F44336, #d32f2f)' },
    { title: 'Missing Values Filled', value: results.value.missingValuesFilled || 0, icon: 'mdi-pencil', gradient: 'linear-gradient(135deg, #FF9800, #F57C00)' }
  ]
})

async function loadData() {
  try {
    const datasetId = route.query.dataset_id
    if (!datasetId) return alert('No dataset selected. Load from Upload page first.')
    const res = await datasetAPI.load(datasetId)
    if (!res || !res.success) return alert('Failed to load dataset')
    const last = res.data
    dataset.value = {
      name: last.name,
      data: last.data || [],
      file_base64: last.file_base64,
      instrumentType: last.instrument_type || 'Financial Instruments',
      sheetNames: last.headers || ['Sheet1']
    }
    originalDataset.value = JSON.parse(JSON.stringify(dataset.value))
    cleanedSourceData.value = []
    uploadId.value = last.id
    sheetNames.value = last.headers || ['Sheet1']
    selectedSheet.value = sheetNames.value[0]
    results.value = null
    return
  } catch (err) {
    console.error(err)
    alert('Error loading dataset')
  }
}

function toggleDatasetPreview() { showDatasetPreview.value = !showDatasetPreview.value }
function resetOptions() {
  cleaningOptions.value.forEach(o => o.value = false)
  alert('Options reset')
}
function clearResults() {
  results.value = null
  cleanedSourceData.value = []
  if (originalDataset.value) dataset.value = JSON.parse(JSON.stringify(originalDataset.value))
  alert('Results cleared')
}

async function deleteData() {
  if (!uploadId.value) return alert('No dataset ID')
  if (!confirm('Delete permanently?')) return
  try {
    const res = await datasetAPI.delete(uploadId.value)
    if (!res || res.success === false) return alert('Failed to delete dataset: ' + (res?.message || 'Unknown error'))
    dataset.value = null
    originalDataset.value = null
    uploadId.value = null
    results.value = null
    alert('Dataset deleted')
  } catch (err) { console.error(err); alert('Error deleting dataset') }
}

function handleCleanedUpdate(newData) {
  if (results.value) {
    cleanedSourceData.value = newData.map((row, index) => ({
      ...(cleanedSourceData.value[index] || {}),
      ...row
    }))
    const excludedNow = new Set(excludedFields.value)
    const originalCols = Object.keys(cleanedSourceData.value[0] || {})
    const currentCols = new Set(Object.keys(newData[0] || {}))
    for (const col of originalCols) {
      if (!currentCols.has(col)) excludedNow.add(col)
    }
    excludedFields.value = excludedNow
    persistExclusions()
    rebuildCleanedFromExclusions()
  }
}

function handleDataUpdate(newData) {
  if (!dataset.value) return
  if (results.value) {
    cleanedSourceData.value = newData.map((row, index) => ({
      ...(cleanedSourceData.value[index] || {}),
      ...row
    }))
    rebuildCleanedFromExclusions()
  } else {
    dataset.value.data = newData
  }
}

async function startCleaning() {
  if (!dataset.value?.data) return alert('No data to clean')
  isCleaning.value = true
  try {
    const options = {}
    cleaningOptions.value.forEach(opt => { if (opt.value) options[opt.key] = true })
    options.dateFormat = selectedDateFormat.value
    options.caseType = selectedCaseType.value
    options.customFillValue = customFillValue.value

    const { data: cleanedRows, operations } = applyCleaningOperations(
      dataset.value.data, cleanedSourceData.value, options, selectedDateFormat.value
    )
    cleanedSourceData.value = cleanedRows
    let cleaned = cleanedRows
    if (excludedFields.value.size > 0) {
      cleaned = cleaned.map(row => Object.fromEntries(
        Object.entries(row).filter(([key]) => {
          const normalizedKey = String(key).toLowerCase().replace(/[-_\s().]+/g, '')
          return ![...excludedFields.value].some(excluded =>
            normalizedKey === String(excluded).toLowerCase().replace(/[-_\s().]+/g, '')
          )
        })
      ))
    }
    results.value = {
      originalRows: dataset.value.data.length,
      cleanedRows: cleaned.length,
      duplicatesRemoved: 0,
      missingValuesFilled: 0,
      cleanedData: cleaned,
      operations
    }
    dataset.value.data = cleaned
    alert(`Cleaning completed! ${results.value.cleanedRows} rows remaining`)
  } catch (err) {
    console.error(err)
    alert('Cleaning failed')
  } finally {
    isCleaning.value = false
  }
}

async function completeProcess() {
  if (!dataset.value || !results.value) return alert('No results to save')
  try {
    const name = dataset.value.name || `cleaned_${Date.now()}`
    const res = await datasetAPI.save(
      name,
      dataset.value.file_base64 || '',
      sheetNames.value || [],
      uploadId.value || null,
      dataset.value.data || [],
      sheetNames.value || [],
      dataset.value.instrumentType || null
    )
    if (res && res.success) alert('Process completed! Cleaned data saved to datasets')
    else alert('Failed to save cleaned data')
  } catch (err) { console.error(err); alert('Failed to save cleaned data') }
}

function normalizeInstrumentType(raw) {
  if (!raw) return 'money-market'
  const s = String(raw).toLowerCase().trim().replace(/[_\s]+/g, '-')
  if (s.includes('bond')) return 'bonds'
  if (s.includes('t-bill') || s.includes('tbill') || s.includes('treasury') || s.includes('tbo')) return 'tbills'
  if (s.includes('money') || s === 'mm') return 'money-market'
  return 'money-market'
}

let _isHandingOff = false
async function goToCalculations() {
  if (_isHandingOff) return
  if (!results.value) return alert('Please clean data first')
  const sid = sessionManager.getActiveSession()?.id || sessionManager.getActiveSessionId()
  if (!sid) return alert('No active session. Open Dashboard first.')
  _isHandingOff = true

  const rawType = dataset.value?.instrumentType
  const normalizedType = normalizeInstrumentType(rawType)

  // Map excluded *normalized* field names back to the actual column
  // headers present in the cleaned data.
  const ALIAS_TO_HEADER = {
    face_value: ['Face Value', 'FaceValue', 'face_value', 'faceValue', 'Par Value', 'Principal'],
    principal: ['Principal', 'principal', 'Face Value', 'Amount'],
    interest_rate: ['Interest Rate', 'interest_rate', 'interestRate', 'Rate'],
    coupon_rate: ['Coupon Rate', 'coupon_rate', 'couponRate', 'Coupon'],
    discount_rate: ['Discount Rate', 'discount_rate', 'discountRate', 'Discount'],
    days_to_maturity: ['Days to Maturity', 'days_to_maturity', 'daysToMaturity', 'Term', 'Term Days'],
    term_days: ['Term Days', 'term_days', 'termDays', 'Days to Maturity', 'Term'],
    issue_date: ['Issue Date', 'issue_date', 'issueDate', 'Start Date'],
    maturity_date: ['Maturity Date', 'maturity_date', 'maturityDate', 'End Date'],
    valuation_date: ['Valuation Date', 'valuation_date', 'valuationDate', 'As of Date'],
    yield: ['Yield', 'yield', 'Yield to Maturity', 'YTM'],
    yield_to_maturity: ['Yield to Maturity', 'yield_to_maturity', 'yieldToMaturity', 'YTM', 'Yield'],
    coupon_frequency: ['Coupon Frequency', 'coupon_frequency', 'couponFrequency', 'Frequency'],
    purchase_price: ['Purchase Price', 'purchase_price', 'purchasePrice', 'Price'],
    current_price: ['Current Price', 'current_price', 'currentPrice', 'Price'],
    instrument_name: ['Instrument Name', 'instrument_name', 'instrumentName', 'Name'],
  }

  const cleanedHeaders = new Set(
    Object.keys((results.value.cleanedData?.[0]) || {})
  )
  const translatedExclusions = new Set()
  for (const excludedKey of excludedFields.value) {
    const candidates = ALIAS_TO_HEADER[excludedKey]
    if (!candidates) {
      // If it's already a raw header present in the cleaned data, keep it.
      if (cleanedHeaders.has(excludedKey)) translatedExclusions.add(excludedKey)
      continue
    }
    // Only add aliases that actually exist as columns
    for (const header of candidates) {
      if (cleanedHeaders.has(header)) translatedExclusions.add(header)
    }
  }

  try {
    await markStepCompleted(String(sid), 'cleaning')

    const wf = await sessionManager.getInstrumentWorkflow(sid, normalizedType) || {}
    await sessionManager.saveInstrumentWorkflow(sid, normalizedType, {
      ...wf,
      cleanedData: results.value.cleanedData,
      cleanedSourceData: cleanedSourceData.value,
      rawData: originalDataset.value?.data || dataset.value.data,
      instrumentType: normalizedType,
      sheetType: wf.sheetType || 'multi',
      calculations: {},
      allCalculations: {},
      selectedCalculations: {},
      instrumentSummary: { columns: [], rows: [] },
      portfolioSummary: { columns: [], rows: [] },
      completedInstrumentSummary: wf.completedInstrumentSummary || { columns: [], rows: [] },
      completedPortfolioSummary: wf.completedPortfolioSummary || { columns: [], rows: [] },
      // Store BOTH forms so the exclusion filter in calculateMetrics
      excludedDetectedFields: Array.from(new Set([
        ...excludedFields.value,
        ...translatedExclusions
      ])),
      last_tab: 'calculations',
      sessionSavedAt: new Date().toISOString()
    })
  } catch (e) {
    console.warn('Failed to persist cleaned data to session workflow:', e)
    alert('Could not save cleaned data to session. Check the browser console.')
    _isHandingOff = false
    return
  }

  try { localStorage.setItem('dura_last_instrument', normalizedType) } catch (e) { /* ignore */ }
  router.push({
    path: `/instrument/${normalizedType}`,
    query: { session: sid, tab: 'calculations' }
  })
  _isHandingOff = false
}

onMounted(async () => {
  if (route.query.dataset_id) await loadData()
  await loadDetectedValues()
})
</script>

<style scoped>
.cleaning-view { max-width: 1400px; margin: 0 auto; padding: 20px; }
.page-header { margin-bottom: 30px; }
.page-header h1 { color: #0B2A44; font-size: 32px; font-weight: 700; margin-bottom: 8px; }
.page-header p { color: #666; font-size: 16px; }
.action-buttons { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 30px; }
.stats-card { border-radius: 12px; margin-bottom: 30px; background: white; border: 1px solid rgba(11,42,68,0.08); position: relative; }
.stats-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; background: linear-gradient(90deg, #0B2A44, #1E88E5); border-radius: 12px 12px 0 0; }
.card-title { display: flex; align-items: center; color: #0B2A44; font-weight: 600; font-size: 18px; padding: 16px 20px 0 20px; }
.title-icon { margin-right: 8px; color: #0B2A44; }
.kpi-card { background: white; border-radius: 20px; padding: 18px; display: flex; align-items: center; gap: 12px; position: relative; overflow: hidden; cursor: pointer; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05); transition: all 0.3s ease; }
.kpi-top-bar { position: absolute; top: 0; left: 0; right: 0; height: 4px; background: linear-gradient(90deg, #0B2044, #1E88E5, #4CAF50); transform: scaleX(1); }
.kpi-card:hover { transform: translateY(-5px); box-shadow: 0 12px 28px rgba(0, 0, 0, 0.15); }
.kpi-icon { width: 52px; height: 52px; border-radius: 14px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; transition: transform 0.3s ease; }
.kpi-card:hover .kpi-icon { transform: scale(1.05); }
.kpi-content { display: flex; align-items: center; gap: 12px; height: 100%; }
.kpi-info { flex: 1; }
.kpi-value { font-size: 20px; font-weight: 800; color: #0B2044; }
.kpi-title { font-size: 10px; color: #888; }
.result-kpi { height: 100px; }
.options-container { max-height: 300px; overflow-y: auto; margin-bottom: 20px; }
.desc { font-size: 12px; color: #666; margin-top: 4px; }
.v-checkbox { margin-bottom: 12px; padding: 8px; border-radius: 6px; }
.v-checkbox:hover { background: rgba(11,42,68,0.03); }
.date-format-section { margin-top: 16px; padding: 12px; background: rgba(11,42,68,0.03); border-radius: 8px; border-left: 3px solid #0B2A44; }
.date-format-label { display: block; font-weight: 600; color: #0B2A44; margin-bottom: 8px; font-size: 14px; }
.date-format-select { margin-top: 8px; }
.result-item { display: flex; justify-content: space-between; padding: 12px; background: rgba(11,42,68,0.03); border-radius: 8px; margin-bottom: 8px; }
.result-item span:first-child { color: #666; font-weight: 500; }
.result-item span:last-child { color: #0B2A44; font-weight: 700; }
.result-actions { display: flex; gap: 12px; margin-top: 20px; }

.compact-fields-table {
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin-bottom: 8px;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  overflow: hidden;
  background: white;
}
.compact-field-row {
  display: grid;
  grid-template-columns: 26px 1fr 1.4fr;
  gap: 8px;
  align-items: center;
  padding: 6px 12px;
  font-size: 13px;
  border-bottom: 1px solid #f0f0f0;
  transition: background 0.15s;
}
.compact-field-row:last-child { border-bottom: none; }
.compact-field-row:hover { background: #f8f9ff; }
.compact-field-row--excluded { background: #fff4f4; opacity: 0.65; }
.compact-field-row--excluded .compact-field-name,
.compact-field-row--excluded .compact-field-value {
  text-decoration: line-through;
  color: #999;
}
.compact-checkbox input { width: 15px; height: 15px; cursor: pointer; accent-color: #0B2044; }
.compact-field-name { font-weight: 600; color: #0B2044; font-size: 12px; }
.compact-field-value { font-family: 'Courier New', monospace; color: #2e7d32; font-size: 12px; font-weight: 600; text-align: right; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.compact-summary { font-size: 12px; color: #666; padding: 6px 12px; background: #f0f4ff; border-radius: 6px; }

@media (max-width: 600px) {
  .cleaning-view { padding: 0 16px; }
  .action-buttons { flex-direction: column; }
  .result-actions { flex-direction: column; }
}
</style>