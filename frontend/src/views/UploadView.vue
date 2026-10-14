<template>
  <fixed-layout>
    <div class="upload-page">
      <div class="page-header">
        <h1>Upload Dataset</h1>
        <p>Upload financial data for analysis</p>
      </div>

      <v-row>
        <v-col cols="12" md="6">
          <v-card class="upload-box">
            <v-card-text class="text-center">
              <v-icon size="56" color="#0B2A44">mdi-cloud-upload</v-icon>
              <h3>Upload File</h3>
              <p>Drag & drop or click to browse</p>
              <div
                class="drop-area"
                :class="{ 'drag-over': isDragging }"
                @dragover.prevent="isDragging = true"
                @dragleave.prevent="isDragging = false"
                @drop.prevent="handleDrop"
                @click="openFileBrowser"
              >
                <v-icon size="32" color="#1E88E5">mdi-file-upload-outline</v-icon>
                <p>Excel, CSV, or JSON files</p>
                <v-btn color="#0B2A44" size="small">Browse</v-btn>
              </div>
              <input
                ref="fileInput"
                type="file"
                accept=".csv,.xlsx,.xls,.xlsm,.xlsb,.ods,.json"
                @change="handleFileSelect"
                style="display:none"
              />
              <div v-if="isLoading" class="loading-info">
                <v-progress-circular indeterminate size="20" color="#1E88E5" />
                <span class="ml-2">{{ loadingMessage }}</span>
              </div>
            </v-card-text>
          </v-card>
        </v-col>

        <v-col cols="12" md="6">
          <v-card class="saved-box">
            <v-card-title class="saved-title">
              <v-icon>mdi-database</v-icon> My Datasets
              <v-spacer></v-spacer>
              <v-chip size="small" color="white">{{ savedDatasets.length }}</v-chip>
            </v-card-title>
            <v-card-text>
              <div v-if="savedDatasets.length">
                <div v-for="(ds, idx) in savedDatasets" :key="ds.id" class="dataset-row">
                  <v-icon color="#1E88E5">mdi-file-excel</v-icon>
                  <div class="dataset-info">
                    <div class="dataset-name">{{ ds.name }}</div>
                    <div class="dataset-rows">{{ ds.rows || 0 }} rows</div>
                  </div>
                  <v-btn size="small" variant="text" @click="loadDataset(idx)">
                    <v-icon size="small">mdi-folder-open</v-icon>
                  </v-btn>
                  <v-btn size="small" color="error" variant="text" @click="deleteDataset(idx)">
                    <v-icon size="small">mdi-delete</v-icon>
                  </v-btn>
                </div>
              </div>
              <div v-else class="empty-state">
                <v-icon size="40">mdi-database-off</v-icon>
                <div>No saved datasets</div>
                <div class="text-caption">Upload a file to get started</div>
              </div>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <v-card v-if="hasFile || hasData" class="action-card">
        <v-card-text>
          <v-row>
            <v-col cols="12" sm="3">
              <v-btn color="success" block @click="loadExcel" :loading="isLoading">
                <v-icon left>mdi-microsoft-excel</v-icon> Load Data
              </v-btn>
            </v-col>
            <v-col cols="12" sm="3" v-if="showPreview">
              <v-btn color="info" block @click="savePrompt">
                <v-icon left>mdi-content-save</v-icon> Save
              </v-btn>
            </v-col>
            <v-col cols="12" sm="3" v-if="showPreview">
              <v-btn color="warning" block @click="showPreview = false">
                <v-icon left>mdi-eye-off</v-icon> Hide
              </v-btn>
            </v-col>
            <v-col cols="12" sm="3" v-if="hasData">
              <v-btn color="#1E88E5" block @click="goToClean">
                <v-icon left>mdi-broom</v-icon> Clean Data
              </v-btn>
            </v-col>
          </v-row>
        </v-card-text>
      </v-card>

      <ExcelViewer
        v-if="rawData.length"
        :data="previewSlice"
        :headers="headers"
        :show-mapping-controls="true"
        :column-mapping="columnMapping"
        :available-file-columns="fileColumns"
        :mapping-validation="mappingValidation"
        :suggested-mappings="suggestedMapping"
        @data-update="onRawExcelUpdate"
        @mapping-update="updateColumnMapping"
        @request-auto-mapping="suggestMapping"
      />

      <v-card v-if="showPreview && rawData.length" class="info-card">
        <v-card-title><v-icon>mdi-information</v-icon> Dataset Summary</v-card-title>
        <v-card-text>
          <v-row>
            <v-col cols="6" sm="3">
              <div class="info-label">Total Rows</div>
              <div class="info-value">{{ rawData.length.toLocaleString() }}</div>
            </v-col>
            <v-col cols="6" sm="3">
              <div class="info-label">Total Columns</div>
              <div class="info-value">{{ headers.length }}</div>
            </v-col>
            <v-col cols="6" sm="3">
              <div class="info-label">File Size</div>
              <div class="info-value">{{ fileSizeLabel }}</div>
            </v-col>
          </v-row>
        </v-card-text>
      </v-card>

      <!-- Column Mapping Dialog — opens when auto-mapping cannot be validated -->
      <v-dialog v-model="showMappingDialog" max-width="700px" persistent>
        <v-card>
          <v-card-title class="sheet-dialog-title">
            <v-icon left>mdi-table-column</v-icon> Map Columns
            <v-spacer></v-spacer>
            <button class="btn-close-dialog" @click="closeMappingDialog">✕</button>
          </v-card-title>
          <v-card-text class="sheet-dialog-body">
            <p class="sheet-dialog-text">
              Auto-mapping needs confirmation. Map each required field to a column from your file:
            </p>
            <div class="mapping-grid">
              <div v-for="field in requiredFieldNames" :key="field" class="mapping-row">
                <label class="required-label">{{ field }}</label>
                <select v-model="columnMapping[field]" class="mapping-select">
                  <option :value="null">— Select a column —</option>
                  <option v-for="col in fileColumns" :key="col" :value="col">{{ col }}</option>
                </select>
              </div>
            </div>
          </v-card-text>
          <v-card-actions class="sheet-dialog-actions">
            <v-spacer></v-spacer>
            <v-btn color="grey" variant="text" @click="closeMappingDialog">Cancel</v-btn>
            <v-btn color="#0B2A44" @click="applyMappingAndClose">Apply Mapping</v-btn>
          </v-card-actions>
        </v-card>
      </v-dialog>

      <!-- Worksheet Selection Dialog -->
      <v-dialog v-model="showSheetSelection" max-width="500px" persistent>
        <v-card>
          <v-card-title class="sheet-dialog-title">
            <v-icon left>mdi-file-table</v-icon> Select Worksheet
            <v-spacer></v-spacer>
            <button class="btn-close-dialog" @click="cancelSheetSelection">✕</button>
          </v-card-title>
          <v-card-text class="sheet-dialog-body">
            <p class="sheet-dialog-text">
              This file contains {{ sheetNames.length }} worksheet(s). Select one to load:
            </p>
            <div class="sheet-list">
              <div
                v-for="sheet in sheetNames"
                :key="sheet"
                class="sheet-item"
                :class="{ 'selected': selectedSheet === sheet }"
                @click="selectSheet(sheet)"
              >
                <v-icon>mdi-table</v-icon>
                <span>{{ sheet }}</span>
              </div>
            </div>
          </v-card-text>
          <v-card-actions class="sheet-dialog-actions">
            <v-spacer></v-spacer>
            <v-btn color="grey" variant="text" @click="cancelSheetSelection">Cancel</v-btn>
            <v-btn color="#0B2A44" @click="confirmSheetSelection" :disabled="!selectedSheet">Load</v-btn>
          </v-card-actions>
        </v-card>
      </v-dialog>
    </div>
  </fixed-layout>
</template>

<script setup>
import FixedLayout from '../components/FixedLayout.vue'
import ExcelViewer from '../components/ExcelViewer.vue'
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { datasetAPI } from '../services/api'
import { API_BASE_URL } from '../config.js'
import sessionManager from '@/services/sessionManager.js'
import { markStepCompleted } from '@/utils/workflowProgress.js'
import * as XLSX from 'xlsx'

const router = useRouter()
const fileInput = ref(null)

const isDragging = ref(false)
const isLoading = ref(false)
const loadingMessage = ref('')
const showPreview = ref(false)

const rawData = ref([])
const dataset = computed(() => rawData.value)

const headers = ref([])
const fileColumns = ref([])
const savedDatasets = ref([])
const selectedDatasetId = ref(null)
const selectedDatasetName = ref(null)

const uploadedFile = ref(null)
const fileSizeLabel = ref('—')

const workbookData = ref(null)
const sheetNames = ref([])
const selectedSheet = ref(null)
const showSheetSelection = ref(false)

const instrumentDetection = ref(null)
const suggestedMapping = ref({})
const mappingValidation = ref(null)
const dependencyValidation = ref(null)
const showMappingDialog = ref(false)
const selectedInstrumentType = ref(null)
const columnMapping = ref({})

const requiredFieldNames = computed(() => {
  const m = suggestedMapping.value || {}
  const keys = Object.keys(m)
  if (keys.length) return keys
  return Object.keys(columnMapping.value)
})

const SAMPLE_ROWS = 500
const PREVIEW_ROWS = 500

const hasFile = computed(() => uploadedFile.value !== null)
const hasData = computed(() => rawData.value.length > 0)
const previewSlice = computed(() => rawData.value.slice(0, PREVIEW_ROWS))

function humanSize(bytes) {
  if (bytes === 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  return `${(bytes / Math.pow(1024, i)).toFixed(i === 0 ? 0 : 1)} ${units[i]}`
}

function resetDataState() {
  rawData.value = []
  headers.value = []
  fileColumns.value = []
  uploadedFile.value = null
  fileSizeLabel.value = '—'
  showPreview.value = false
}

function releaseWorkbook() {
  workbookData.value = null
  sheetNames.value = []
  selectedSheet.value = null
}

async function readFileData(file) {
  const ext = (file.name.split('.').pop() || '').toLowerCase()

  if (ext === 'csv' || ext === 'json') {
    const text = await file.text()

    if (ext === 'json') {
      const parsed = JSON.parse(text)
      if (Array.isArray(parsed)) return parsed
      if (parsed && Array.isArray(parsed.data)) return parsed.data
      throw new Error('JSON must be an array of objects or { data: [...] }')
    }

    const lines = text.split(/\r?\n/).filter(l => l.trim())
    if (lines.length === 0) throw new Error('Empty file')

    let delimiter = ','
    if (lines[0].includes(';') && !lines[0].includes(',')) delimiter = ';'
    if (lines[0].includes('\t') && !lines[0].includes(',')) delimiter = '\t'

    const fileHeaders = lines[0]
      .split(delimiter)
      .map(h => h.trim().replace(/^"|"$/g, ''))

    const rows = new Array(lines.length - 1)
    for (let i = 1; i < lines.length; i++) {
      const vals = lines[i].split(delimiter).map(v => v.trim().replace(/^"|"$/g, ''))
      const row = {}
      for (let j = 0; j < fileHeaders.length; j++) {
        row[fileHeaders[j]] = vals[j] !== undefined ? vals[j] : ''
      }
      rows[i - 1] = row
    }
    return rows
  }

  const buffer = await file.arrayBuffer()
  const workbook = XLSX.read(buffer, {
    type: 'array',
    dense: true,
    cellDates: false,
    cellNF: false,
    cellStyles: false,
    cellText: false,
    defval: ''
  })

  workbookData.value = workbook
  sheetNames.value = workbook.SheetNames

  if (workbook.SheetNames.length === 1) {
    selectedSheet.value = workbook.SheetNames[0]
    const sheet = workbook.Sheets[selectedSheet.value]
    const data = XLSX.utils.sheet_to_json(sheet, { defval: '', raw: false })
    if (data.length === 0) {
      releaseWorkbook()
      throw new Error('No data found in sheet')
    }
    releaseWorkbook()
    return data
  }

  showSheetSelection.value = true
  return { needsSelection: true }
}

async function uploadFile(file) {
  resetDataState()
  uploadedFile.value = file
  fileSizeLabel.value = humanSize(file.size)
  isLoading.value = true
  loadingMessage.value = `Reading ${file.name} (${fileSizeLabel.value})…`

  try {
    const parsed = await readFileData(file)

    if (parsed && parsed.needsSelection) {
      isLoading.value = false
      loadingMessage.value = ''
      return
    }

    applyParsedData(parsed)
    await postLoadSetup(file.name)
  } catch (err) {
    console.error('File read error:', err)
    alert(err.message)
    resetDataState()
  } finally {
    isLoading.value = false
    loadingMessage.value = ''
  }
}

function applyParsedData(data) {
  rawData.value = data
  headers.value = data.length ? Object.keys(data[0] || {}) : []
  fileColumns.value = headers.value
  showPreview.value = true
}

async function postLoadSetup(fileName) {
  const sample = rawData.value.slice(0, SAMPLE_ROWS)
  await detectInstrumentType(sample)
}

function selectSheet(sheetName) {
  selectedSheet.value = sheetName
}

function cancelSheetSelection() {
  showSheetSelection.value = false
  releaseWorkbook()
  resetDataState()
}

async function confirmSheetSelection() {
  if (!selectedSheet.value || !workbookData.value) {
    cancelSheetSelection()
    return
  }

  isLoading.value = true
  loadingMessage.value = `Loading sheet "${selectedSheet.value}"…`

  try {
    const sheet = workbookData.value.Sheets[selectedSheet.value]
    const data = XLSX.utils.sheet_to_json(sheet, { defval: '', raw: false })

    if (data.length === 0) {
      alert('No data found in selected sheet')
      cancelSheetSelection()
      return
    }

    applyParsedData(data)
    showSheetSelection.value = false
    releaseWorkbook()

    await postLoadSetup(uploadedFile.value?.name || 'dataset')
  } catch (err) {
    alert(`Failed to load sheet: ${err.message}`)
  } finally {
    isLoading.value = false
    loadingMessage.value = ''
  }
}

async function loadExcel() {
  if (!uploadedFile.value) {
    alert('Please select a file first')
    return
  }
  if (rawData.value.length) {
    showPreview.value = true
    return
  }
  await uploadFile(uploadedFile.value)
}

async function detectInstrumentType(sample) {
  try {
    const response = await fetch(`${API_BASE_URL}/api/detect-instrument`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ data: sample })
    })
    const result = await response.json()
    if (result.success) {
      instrumentDetection.value = result.data
      selectedInstrumentType.value = result.data.instrument_type || null
      await suggestMapping()
      await validateDependencies()
    }
  } catch (err) {
    console.error('Instrument detection error:', err)
  }
}

async function suggestMapping() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/suggest-mapping`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        source_fields: fileColumns.value,
        instrument_type: selectedInstrumentType.value
      })
    })
    const result = await response.json()
    if (result.success) {
      suggestedMapping.value = result.data.mappings
      mappingValidation.value = result.data.validation
      if (result.data.validation.is_valid) {
        columnMapping.value = { ...suggestedMapping.value }
        await persistColumnMapping()
      } else {
        columnMapping.value = { ...result.data.mappings }
        showMappingDialog.value = true
      }
    }
  } catch (err) {
    console.error('Mapping suggestion error:', err)
  }
}

async function validateDependencies() {
  try {
    const first = rawData.value[0] || {}
    const availableFields = {}
    for (const f of fileColumns.value) availableFields[f] = first[f] ?? null

    const response = await fetch(`${API_BASE_URL}/api/validate-dependencies`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        available_fields: availableFields,
        instrument_type: selectedInstrumentType.value
      })
    })
    const result = await response.json()
    if (result.success) dependencyValidation.value = result.data
  } catch (err) {
    console.error('Dependency validation error:', err)
  }
}

async function persistColumnMapping() {
  try {
    const sid = sessionManager.getActiveSession()?.id || sessionManager.getActiveSessionId()
    if (!sid) return
    const key = selectedInstrumentType.value || 'upload-dataset'
    const existing = await sessionManager.getInstrumentWorkflow(sid, key) || {}
    await sessionManager.saveInstrumentWorkflow(sid, key, {
      ...existing,
      columnMapping: { ...columnMapping.value },
      fileColumns: [...fileColumns.value],
      uploadedFile: uploadedFile.value?.name || existing.uploadedFile || null,
      updatedAt: Date.now()
    })
  } catch (e) {
    console.warn('persistColumnMapping failed:', e)
  }
}

async function updateColumnMapping(mapping) {
  columnMapping.value = { ...mapping }
  await persistColumnMapping()
}

function closeMappingDialog() {
  showMappingDialog.value = false
}

async function applyMappingAndClose() {
  await persistColumnMapping()
  showMappingDialog.value = false
  showPreview.value = true
}

function onRawExcelUpdate(updated) {
  const rest = rawData.value.slice(updated.length)
  rawData.value = [...updated, ...rest]

  // Refresh header/column list from the updated preview so downstream is not stale.
  if (updated.length > 0 && updated[0]) {
    const newHeaders = Object.keys(updated[0] || {})
    headers.value = newHeaders
    fileColumns.value = newHeaders
  }
}

async function loadSavedDatasets() {
  try {
    const res = await datasetAPI.getAll()
    if (res && res.success) savedDatasets.value = res.data || []
  } catch (err) {
    console.error('Load datasets error', err)
  }
}

async function saveDataset(name) {
  if (!rawData.value.length) {
    alert('No data to save')
    return false
  }
  try {
    isLoading.value = true
    loadingMessage.value = 'Saving dataset…'

    const res = await datasetAPI.save(
      name,
      '',
      [],
      selectedDatasetId.value || null,
      rawData.value,
      headers.value
    )

    if (res && res.success) {
      selectedDatasetId.value = res.data.id
      selectedDatasetName.value = res.data.name
      await loadSavedDatasets()
      return true
    }
  } catch (err) {
    console.error('Save dataset error', err)
  } finally {
    isLoading.value = false
    loadingMessage.value = ''
  }
  return false
}

async function savePrompt() {
  const fallback = uploadedFile.value?.name?.replace(/\.[^/.]+$/, '') || 'My Dataset'
  const name = prompt('Dataset name:', fallback)
  if (name?.trim()) {
    if (await saveDataset(name.trim())) alert('Dataset saved!')
    else alert('Save failed')
  }
}

async function loadDataset(idx) {
  const ds = savedDatasets.value[idx]
  if (!ds) return
  try {
    isLoading.value = true
    loadingMessage.value = 'Loading dataset…'

    const res = await datasetAPI.load(ds.id)
    if (res && res.success) {
      const data = res.data || {}
      if (!data.data || !data.data.length) {
        alert('Dataset has no data')
        return
      }

      rawData.value = data.data
      headers.value = data.headers || Object.keys(data.data[0] || {})
      fileColumns.value = headers.value
      uploadedFile.value = { name: data.name }
      fileSizeLabel.value = '—'
      selectedDatasetId.value = data.id
      selectedDatasetName.value = data.name
      showPreview.value = true

      await detectInstrumentType(rawData.value.slice(0, SAMPLE_ROWS))
    } else {
      alert('Failed to load dataset: ' + (res?.message || 'Unknown error'))
    }
  } catch (err) {
    console.error('Load dataset error', err)
    alert('Failed to load dataset: ' + err.message)
  } finally {
    isLoading.value = false
    loadingMessage.value = ''
  }
}

async function deleteDataset(idx) {
  const ds = savedDatasets.value[idx]
  if (!ds) return
  if (!confirm(`Delete "${ds.name}"?`)) return
  try {
    await datasetAPI.delete(ds.id)
    await loadSavedDatasets()
    if (selectedDatasetId.value === ds.id) {
      resetDataState()
      selectedDatasetId.value = null
    }
  } catch (err) {
    console.error('Delete dataset error', err)
  }
}

function openFileBrowser() { fileInput.value?.click() }

function handleFileSelect(e) {
  const files = Array.from(e.target.files || [])
  if (files.length) uploadFile(files[0])
  e.target.value = ''
}

function handleDrop(e) {
  isDragging.value = false
  const files = Array.from(e.dataTransfer?.files || [])
  if (files.length) uploadFile(files[0])
}

async function goToClean() {
  if (!rawData.value.length) {
    alert('Load data first')
    return
  }

  const markUploadStep = async () => {
    try {
      const sid = sessionManager.getActiveSession()?.id || sessionManager.getActiveSessionId()
      if (sid) await markStepCompleted(String(sid), 'upload')
    } catch (e) { console.warn(e) }
  }

  if (!selectedDatasetId.value) {
    const name = uploadedFile.value?.name?.replace(/\.[^/.]+$/, '') || `Dataset-${Date.now()}`
    const saved = await saveDataset(name)
    if (!saved) {
      alert('Unable to save dataset before cleaning')
      return
    }
  }

  await markUploadStep()
  router.push({ name: 'cleaning', query: { dataset_id: selectedDatasetId.value } })
}

onMounted(() => {
  loadSavedDatasets()
})

onUnmounted(() => {
  rawData.value = []
  releaseWorkbook()
})
</script>

<style scoped>
.upload-page { max-width: 1400px; margin: 0 auto; padding: 20px; }
.page-header { margin-bottom: 30px; }
.page-header h1 { color: #0B2A44; font-size: 32px; font-weight: 700; margin-bottom: 8px; }
.page-header p { color: #666; font-size: 16px; }
.upload-box { border-radius: 16px; transition: 0.2s; }
.upload-box:hover { transform: translateY(-2px); box-shadow: 0 8px 24px rgba(11,42,68,0.15); }
.drop-area { border: 2px dashed #0B2A44; border-radius: 12px; padding: 32px 24px; cursor: pointer; transition: 0.3s; background: rgba(11,42,68,0.03); }
.drop-area:hover { background: rgba(11,42,68,0.08); border-color: #1E88E5; }
.drop-area.drag-over { background: rgba(30,136,229,0.1); border-color: #4CAF50; transform: scale(1.02); }
.loading-info { margin-top: 12px; display: flex; align-items: center; justify-content: center; color: #1E88E5; font-size: 13px; }
.saved-box { border-radius: 16px; height: 100%; }
.saved-title { background: linear-gradient(135deg, #0B2A44, #1a3a5a); color: white; padding: 16px 20px; }
.dataset-row { display: flex; align-items: center; gap: 12px; padding: 12px 16px; background: #f8f9fa; border-radius: 8px; margin-bottom: 8px; }
.dataset-row:hover { background: #f0f4ff; }
.dataset-info { flex: 1; }
.dataset-name { font-weight: 600; color: #0B2A44; }
.dataset-rows { font-size: 12px; color: #666; }
.empty-state { text-align: center; padding: 40px; color: #999; }
.action-card { border-radius: 12px; margin-bottom: 20px; background: white; border: 1px solid rgba(11,42,68,0.08); }
.info-card { border-radius: 12px; margin-top: 20px; background: white; border: 1px solid rgba(11,42,68,0.08); }
.info-label { font-size: 12px; font-weight: 600; color: #666; margin-bottom: 4px; }
.info-value { font-size: 20px; font-weight: 700; color: #0B2A44; }

/* Worksheet / Mapping Dialog */
.sheet-dialog-title { background: linear-gradient(135deg, #0B2A44, #1a3a5a); color: white; padding: 16px 20px; display: flex; align-items: center; }
.sheet-dialog-body { padding: 20px; }
.sheet-dialog-text { margin-bottom: 16px; color: #666; font-size: 14px; }
.sheet-list { display: flex; flex-direction: column; gap: 8px; }
.sheet-item { display: flex; align-items: center; gap: 12px; padding: 12px 16px; border: 2px solid #e0e0e0; border-radius: 8px; cursor: pointer; transition: all 0.2s; }
.sheet-item:hover { border-color: #1E88E5; background: rgba(30, 136, 229, 0.05); }
.sheet-item.selected { border-color: #0B2A44; background: rgba(11, 42, 68, 0.08); }
.sheet-item .v-icon { color: #0B2A44; }
.sheet-item span { font-weight: 500; color: #0B2A44; }
.sheet-dialog-actions { padding: 12px 20px; border-top: 1px solid #e0e0e0; }
.btn-close-dialog { background: none; border: none; color: white; font-size: 20px; cursor: pointer; padding: 4px 8px; border-radius: 4px; transition: background 0.2s; }
.btn-close-dialog:hover { background: rgba(255, 255, 255, 0.1); }

.mapping-grid { display: flex; flex-direction: column; gap: 12px; }
.mapping-row { display: flex; align-items: center; gap: 12px; }
.required-label { width: 160px; font-weight: 600; color: #0B2A44; font-size: 14px; }
.mapping-select { flex: 1; padding: 8px 12px; border: 1px solid #ccc; border-radius: 6px; font-size: 14px; background: white; }
.mapping-select:focus { outline: none; border-color: #0B2A44; box-shadow: 0 0 0 2px rgba(11,32,68,0.15); }

@media (max-width: 600px) {
  .upload-page { padding: 0 16px; }
  .drop-area { padding: 20px 16px; }
}
</style>