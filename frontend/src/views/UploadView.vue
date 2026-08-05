<template>
  <fixed-layout>
    <div class="upload-page">
      <div class="page-header">
        <h1>Upload Dataset</h1>
        <p>Upload financial data for analysis</p>
      </div>

      <v-row>
        <!-- Upload Area -->
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
            </v-card-text>
          </v-card>
        </v-col>

        <!-- Saved Datasets -->
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

      <!-- Action Buttons -->
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

      <!-- Excel Viewer (basic, without mapping controls) -->
<ExcelViewer
  :data="rawData.slice(0, 500)"
  :headers="uploadPreviewHeaders"
  :show-mapping-controls="true"
  :column-mapping="columnMapping"
  :available-file-columns="fileColumns"
  @data-update="onRawExcelUpdate"
  @mapping-update="updateColumnMapping"
/>

      <!-- Dataset Info -->
      <v-card v-if="showPreview && dataset.length" class="info-card">
        <v-card-title><v-icon>mdi-information</v-icon> Dataset Summary</v-card-title>
        <v-card-text>
          <v-row>
            <v-col cols="6" sm="3">
              <div class="info-label">Total Rows</div>
              <div class="info-value">{{ dataset.length }}</div>
            </v-col>
            <v-col cols="6" sm="3">
              <div class="info-label">Total Columns</div>
              <div class="info-value">{{ headers.length }}</div>
            </v-col>
          </v-row>
        </v-card-text>
      </v-card>

      <!-- Worksheet Selection Dialog -->
      <v-dialog v-model="showSheetSelection" max-width="500px" persistent>
        <v-card>
          <v-card-title class="sheet-dialog-title">
            <v-icon left>mdi-file-table</v-icon> Select Worksheet
            <v-spacer></v-spacer>
            <button class="btn-close-dialog" @click="showSheetSelection = false">✕</button>
          </v-card-title>
          <v-card-text class="sheet-dialog-body">
            <p class="sheet-dialog-text">This file contains {{ sheetNames.length }} worksheet(s). Select one to load:</p>
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
            <v-btn color="grey" variant="text" @click="showSheetSelection = false">Cancel</v-btn>
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
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { datasetAPI } from '../services/api'
import sessionManager from '@/services/sessionManager.js'
import { markStepCompleted } from '@/utils/workflowProgress.js'
import * as XLSX from 'xlsx'

const router = useRouter()
const fileInput = ref(null)

// UI state
const isDragging = ref(false)
const isLoading = ref(false)
const showPreview = ref(false)

// Data
const uploadedFile = ref(null)
const dataset = ref([])
const headers = ref([])
const savedDatasets = ref([])
const selectedDatasetId = ref(null)
const selectedDatasetName = ref(null)

// Workbook sheet selection
const workbookData = ref(null)
const sheetNames = ref([])
const selectedSheet = ref(null)
const showSheetSelection = ref(false)

const hasFile = computed(() => uploadedFile.value !== null)
const hasData = computed(() => dataset.value.length > 0)

// ---------- File reading (local, no backend) ----------
async function readFileData(file) {
  const ext = file.name.split('.').pop().toLowerCase()
  let data = []
  try {
    if (ext === 'csv') {
      const text = await file.text()
      const lines = text.split(/\r?\n/).filter(l => l.trim())
      if (lines.length === 0) throw new Error('Empty file')
      let delimiter = ','
      if (lines[0].includes(';') && !lines[0].includes(',')) delimiter = ';'
      const fileHeaders = lines[0].split(delimiter).map(h => h.trim().replace(/^"|"$/g, ''))
      data = lines.slice(1).map(line => {
        const vals = line.split(delimiter).map(v => v.trim().replace(/^"|"$/g, ''))
        const row = {}
        fileHeaders.forEach((h, i) => { row[h] = vals[i] !== undefined ? vals[i] : '' })
        return row
      })
    } else {
      // Excel / ODS / etc. - read full workbook without row limit
      const buffer = await file.arrayBuffer()
      const workbook = XLSX.read(buffer, {
        type: 'array',
        cellDates: false,
        cellNF: false,
        cellText: false,
        defval: ""
      })
      // Store workbook for sheet selection
      workbookData.value = workbook
      sheetNames.value = workbook.SheetNames
      
      // If only one sheet, auto-select it
      if (workbook.SheetNames.length === 1) {
        selectedSheet.value = workbook.SheetNames[0]
        const sheet = workbook.Sheets[selectedSheet.value]
        data = XLSX.utils.sheet_to_json(sheet, { defval: "" })
        if (data.length === 0) throw new Error('No data found in sheet')
      } else {
        // Multiple sheets - show selection dialog
        showSheetSelection.value = true
        return { workbook, sheetNames: workbook.SheetNames, needsSelection: true }
      }
    }
    return data
  } catch (err) {
    console.error('File read error:', err)
    throw new Error(`Failed to parse file: ${err.message}`)
  }
}

// ---------- Upload & Preview ----------
async function uploadFile(file) {
  uploadedFile.value = file
  isLoading.value = true
  try {
    const parsed = await readFileData(file)
    
    // Check if sheet selection is needed
    if (parsed && parsed.needsSelection) {
      // Sheet selection dialog will be shown
      isLoading.value = false
      return
    }
    
    dataset.value = parsed
    headers.value = Object.keys(parsed[0] || {})
    showPreview.value = true
    // Auto-save prompt after successful load
    const name = file.name.replace(/\.[^/.]+$/, '')
    if (confirm(`Load successful. Save "${name}" to datasets?`)) {
      await saveDataset(name)
    }
  } catch (err) {
    alert(err.message)
    dataset.value = []
    headers.value = []
    uploadedFile.value = null
    showPreview.value = false
  } finally {
    isLoading.value = false
  }
}

// ---------- Sheet Selection Functions ----------
function selectSheet(sheetName) {
  selectedSheet.value = sheetName
}

async function confirmSheetSelection() {
  if (!selectedSheet.value || !workbookData.value) {
    showSheetSelection.value = false
    return
  }
  
  isLoading.value = true
  try {
    const sheet = workbookData.value.Sheets[selectedSheet.value]
    const data = XLSX.utils.sheet_to_json(sheet, { defval: "" })
    
    if (data.length === 0) {
      alert('No data found in selected sheet')
      showSheetSelection.value = false
      isLoading.value = false
      return
    }
    
    dataset.value = data
    headers.value = Object.keys(data[0] || {})
    showPreview.value = true
    showSheetSelection.value = false
    
    // Auto-save prompt
    const name = uploadedFile.value.name.replace(/\.[^/.]+$/, '')
    if (confirm(`Load successful. Save "${name}" to datasets?`)) {
      await saveDataset(name)
    }
  } catch (err) {
    alert(`Failed to load sheet: ${err.message}`)
  } finally {
    isLoading.value = false
  }
}

async function loadExcel() {
  if (!uploadedFile.value) {
    alert('Please select a file first')
    return
  }
  if (dataset.value.length) {
    showPreview.value = true
    return
  }
  await uploadFile(uploadedFile.value)
}

// ---------- Dataset persistence (via datasetAPI) ----------
async function loadSavedDatasets() {
  try {
    const res = await datasetAPI.getAll()
    if (res && res.success) savedDatasets.value = res.data || []
  } catch (err) {
    console.error('Load datasets error', err)
  }
}

async function saveDataset(name) {
  if (!dataset.value.length && !uploadedFile.value) {
    alert('No data to save')
    return false
  }
  try {
    const payload = {
      name,
      file_base64: '',
      sheet_names: headers.value,
      upload_id: selectedDatasetId.value || null,
      data: dataset.value,
      headers: headers.value
    }
    const res = await datasetAPI.save(
      payload.name,
      payload.file_base64,
      payload.sheet_names,
      payload.upload_id,
      payload.data,
      payload.headers
    )
    if (res && res.success) {
      selectedDatasetId.value = res.data.id
      selectedDatasetName.value = res.data.name
      await loadSavedDatasets()
      return true
    }
  } catch (err) {
    console.error('Save dataset error', err)
  }
  return false
}

async function savePrompt() {
  const name = prompt('Dataset name:', uploadedFile.value?.name?.replace(/\.[^/.]+$/, '') || 'My Dataset')
  if (name?.trim()) {
    if (await saveDataset(name.trim())) alert('Dataset saved!')
    else alert('Save failed')
  }
}

async function loadDataset(idx) {
  const ds = savedDatasets.value[idx]
  if (!ds) return
  try {
    const res = await datasetAPI.load(ds.id)
    if (res && res.success) {
      const data = res.data || {}
      if (data.data && data.data.length) {
        dataset.value = data.data
        headers.value = data.headers || Object.keys(data.data[0] || {})
        uploadedFile.value = { name: data.name }
        selectedDatasetId.value = data.id
        selectedDatasetName.value = data.name
        showPreview.value = true
      } else {
        alert('Dataset has no data')
      }
    }
  } catch (err) {
    console.error('Load dataset error', err)
    alert('Failed to load dataset')
  }
}

async function deleteDataset(idx) {
  const ds = savedDatasets.value[idx]
  if (!ds) return
  if (confirm(`Delete "${ds.name}"?`)) {
    try {
      await datasetAPI.delete(ds.id)
      await loadSavedDatasets()
      if (selectedDatasetId.value === ds.id) {
        selectedDatasetId.value = null
        dataset.value = []
        headers.value = []
        uploadedFile.value = null
        showPreview.value = false
      }
    } catch (err) {
      console.error('Delete dataset error', err)
    }
  }
}

// ---------- Navigation & UI helpers ----------
function openFileBrowser() {
  fileInput.value?.click()
}

function handleFileSelect(e) {
  const files = Array.from(e.target.files || [])
  if (files.length) uploadFile(files[0])
}

function handleDrop(e) {
  isDragging.value = false
  const files = Array.from(e.dataTransfer?.files || [])
  if (files.length) uploadFile(files[0])
}

async function goToClean() {
  if (!dataset.value.length) {
    alert('Load data first')
    return
  }
  // If not saved yet, ask to save
  if (!selectedDatasetId.value) {
    const name = uploadedFile.value?.name?.replace(/\.[^/.]+$/, '') || `Dataset-${Date.now()}`
    saveDataset(name).then(async saved => {
      if (saved) {
        try { const sid = sessionManager.getActiveSession()?.id || sessionManager.getActiveSessionId(); if (sid) await markStepCompleted(String(sid), 'upload') } catch (e) { console.warn(e) }
        router.push({ name: 'cleaning', query: { dataset_id: selectedDatasetId.value } })
      } else {
        alert('Unable to save dataset before cleaning')
      }
    })
  } else {
    try { const sid = sessionManager.getActiveSession()?.id || sessionManager.getActiveSessionId(); if (sid) await markStepCompleted(String(sid), 'upload') } catch (e) { console.warn(e) }
    router.push({ name: 'cleaning', query: { dataset_id: selectedDatasetId.value } })
  }
}

onMounted(() => {
  loadSavedDatasets()
})
</script>

<style scoped>
/* (same as your original styles – unchanged) */
.upload-page { max-width: 1400px; margin: 0 auto; padding: 20px; }
.page-header { margin-bottom: 30px; }
.page-header h1 { color: #0B2A44; font-size: 32px; font-weight: 700; margin-bottom: 8px; }
.page-header p { color: #666; font-size: 16px; }
.upload-box { border-radius: 16px; transition: 0.2s; }
.upload-box:hover { transform: translateY(-2px); box-shadow: 0 8px 24px rgba(11,42,68,0.15); }
.drop-area { border: 2px dashed #0B2A44; border-radius: 12px; padding: 32px 24px; cursor: pointer; transition: 0.3s; background: rgba(11,42,68,0.03); }
.drop-area:hover { background: rgba(11,42,68,0.08); border-color: #1E88E5; }
.drop-area.drag-over { background: rgba(30,136,229,0.1); border-color: #4CAF50; transform: scale(1.02); }
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

/* Worksheet Selection Dialog Styles */
.sheet-dialog-title {
  background: linear-gradient(135deg, #0B2A44, #1a3a5a);
  color: white;
  padding: 16px 20px;
  display: flex;
  align-items: center;
}
.sheet-dialog-body {
  padding: 20px;
}
.sheet-dialog-text {
  margin-bottom: 16px;
  color: #666;
  font-size: 14px;
}
.sheet-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.sheet-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}
.sheet-item:hover {
  border-color: #1E88E5;
  background: rgba(30, 136, 229, 0.05);
}
.sheet-item.selected {
  border-color: #0B2A44;
  background: rgba(11, 42, 68, 0.08);
}
.sheet-item .v-icon {
  color: #0B2A44;
}
.sheet-item span {
  font-weight: 500;
  color: #0B2A44;
}
.sheet-dialog-actions {
  padding: 12px 20px;
  border-top: 1px solid #e0e0e0;
}
.btn-close-dialog {
  background: none;
  border: none;
  color: white;
  font-size: 20px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  transition: background 0.2s;
}
.btn-close-dialog:hover {
  background: rgba(255, 255, 255, 0.1);
}

@media (max-width: 600px) {
  .upload-page { padding: 0 16px; }
  .drop-area { padding: 20px 16px; }
}
</style>