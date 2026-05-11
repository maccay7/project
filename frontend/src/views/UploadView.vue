<template>
  <fixed-layout>
    <div class="upload-page">

      <!-- Header -->
      <div class="page-header">
        <h1>Upload Dataset</h1>
        <p>Upload financial data for analysis</p>
      </div>

      <!-- Upload & Saved Datasets -->
      <v-row>
        <!-- Upload Area -->
        <v-col cols="12" md="6">
          <v-card class="upload-box">
            <v-card-text class="text-center">
              <v-icon size="56" color="#0B2A44">mdi-cloud-upload</v-icon>
              <h3>Upload File</h3>
              <p>Drag & drop or click to browse</p>
              <div class="drop-area" :class="{ 'drag-over': isDragging }"
                @dragover.prevent="isDragging = true"
                @dragleave.prevent="isDragging = false"
                @drop.prevent="handleDrop" @click="openFileBrowser">
                <v-icon size="32" color="#1E88E5">mdi-file-upload-outline</v-icon>
                <p>Excel, CSV, or JSON files</p>
                <v-btn color="#0B2A44" size="small">Browse</v-btn>
              </div>
              <input ref="fileInput" type="file" accept=".csv,.xlsx,.xls,.json" @change="handleFileSelect" style="display:none">
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
                  <v-btn size="small" variant="text" @click="loadDataset(idx)"><v-icon size="small">mdi-folder-open</v-icon></v-btn>
                  <v-btn size="small" color="error" variant="text" @click="deleteDataset(idx)"><v-icon size="small">mdi-delete</v-icon></v-btn>
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

      <!-- Excel Viewer -->
      <ExcelViewer v-if="showPreview"
        :key="fileBase64 || uploadedFile?.name"
        :file-base64="fileBase64"
        :file-name="uploadedFile?.name || ''"
        :data="dataset"
        :headers="headers"
        @data-update="dataset = $event"
        @headers-update="headers = $event"
      />

      <!-- Dataset Info -->
      <v-card v-if="showPreview && dataset.length" class="info-card">
        <v-card-title><v-icon>mdi-information</v-icon> Dataset Summary</v-card-title>
        <v-card-text>
          <v-row>
            <v-col cols="6" sm="3"><div class="info-label">Total Rows</div><div class="info-value">{{ dataset.length }}</div></v-col>
            <v-col cols="6" sm="3"><div class="info-label">Total Columns</div><div class="info-value">{{ headers.length }}</div></v-col>
          </v-row>
        </v-card-text>
      </v-card>

    </div>
  </fixed-layout>
</template>

<script setup>
import FixedLayout from '../components/FixedLayout.vue'
import ExcelViewer from '../components/ExcelViewer.vue'
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { dataAPI } from '../services/api'

const router = useRouter()
const fileInput = ref(null)

// UI state
const isDragging = ref(false)
const isLoading = ref(false)
const showPreview = ref(false)

// Data
const uploadedFile = ref(null)
const fileBase64 = ref('')
const dataset = ref([])
const headers = ref([])
const savedDatasets = ref([])

// Computed
const hasFile = computed(() => uploadedFile.value !== null)
const hasData = computed(() => dataset.value.length > 0 || fileBase64.value)

// Load saved datasets
function loadSavedDatasets() {
  try {
    const saved = localStorage.getItem('saved-datasets')
    if (saved) savedDatasets.value = JSON.parse(saved)
  } catch (err) { console.error(err) }
}

// Save dataset
async function saveDataset(name) {
  if (!fileBase64.value && !dataset.value.length) {
    alert('No data to save')
    return false
  }
  const newDs = {
    id: Date.now(), name, rows: dataset.value.length,
    file_base64: fileBase64.value, data: dataset.value, headers: headers.value,
    timestamp: new Date().toISOString()
  }
  const existing = savedDatasets.value.findIndex(d => d.name === name)
  if (existing !== -1) savedDatasets.value[existing] = newDs
  else savedDatasets.value.push(newDs)
  localStorage.setItem('saved-datasets', JSON.stringify(savedDatasets.value))
  return true
}

async function savePrompt() {
  const name = prompt('Dataset name:', uploadedFile.value?.name?.replace(/\.[^/.]+$/, '') || 'My Dataset')
  if (name?.trim()) {
    if (await saveDataset(name.trim())) alert('Dataset saved!')
    else alert('Save failed')
  }
}

// Load dataset
function loadDataset(idx) {
  const ds = savedDatasets.value[idx]
  if (!ds) return
  if (ds.file_base64) { fileBase64.value = ds.file_base64; dataset.value = [] }
  else if (ds.data) { dataset.value = ds.data; fileBase64.value = '' }
  if (ds.headers) headers.value = ds.headers
  showPreview.value = true
  uploadedFile.value = { name: ds.name }
}

// Delete dataset
function deleteDataset(idx) {
  const ds = savedDatasets.value[idx]
  if (confirm(`Delete "${ds.name}"?`)) {
    savedDatasets.value.splice(idx, 1)
    localStorage.setItem('saved-datasets', JSON.stringify(savedDatasets.value))
  }
}

// File handling
function openFileBrowser() { fileInput.value?.click() }
function handleFileSelect(e) {
  const files = Array.from(e.target.files || [])
  if (files.length) uploadFile(files[0])
}
function handleDrop(e) {
  isDragging.value = false
  const files = Array.from(e.dataTransfer?.files || [])
  if (files.length) uploadFile(files[0])
}

// Upload to backend
async function uploadFile(file) {
  uploadedFile.value = file
  await loadPreview()
}

async function loadPreview() {
  if (!uploadedFile.value) return
  isLoading.value = true
  try {
    const res = await dataAPI.upload(uploadedFile.value, 'treasury_bills')
    if (res.data?.file_base64) {
      fileBase64.value = res.data.file_base64
      dataset.value = []
    } else if (res.data?.data) {
      dataset.value = res.data.data
      headers.value = Object.keys(dataset.value[0] || {})
    }
  } catch (err) {
    console.error(err)
    alert('Upload failed')
  } finally {
    isLoading.value = false
  }
}

// Load Excel
async function loadExcel() {
  if (dataset.value.length || fileBase64.value) {
    showPreview.value = true
    return
  }
  if (!uploadedFile.value) {
    alert('Upload a file first')
    return
  }
  await loadPreview()
  if (dataset.value.length || fileBase64.value) {
    showPreview.value = true
    const name = uploadedFile.value.name.replace(/\.[^/.]+$/, '')
    if (confirm(`Save "${name}" to datasets?`)) await saveDataset(name)
  } else {
    alert('Failed to load data')
  }
}

// Go to cleaning
function goToClean() {
  if (!dataset.value.length && !fileBase64.value) {
    alert('Load data first')
    return
  }
  localStorage.setItem('cleaningDataset', JSON.stringify({
    fullDataset: dataset.value,
    excelFileBase64: fileBase64.value,
    previewHeaders: headers.value
  }))
  router.push('/cleaning')
}

onMounted(() => { loadSavedDatasets() })
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
@media (max-width: 600px) {
  .upload-page { padding: 0 16px; }
  .drop-area { padding: 20px 16px; }
}
</style>s