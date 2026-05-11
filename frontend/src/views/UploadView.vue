<template>
  <fixed-layout>
    <div class="upload-page">

      <!-- Header -->
      <div class="page-header">
        <h1>Upload Dataset</h1>
        <p>Upload your financial data for analysis</p>
      </div>

      <!-- Upload & Saved Datasets -->
      <v-row>
        <!-- Upload Area -->
        <v-col cols="12" md="6">
          <v-card class="upload-box">
            <v-card-text class="text-center">
              <v-icon size="56" color="#0B2A44">mdi-cloud-upload</v-icon>
              <h3>Upload Your File</h3>
              <p>Drag & drop or click to browse</p>

              <div class="drop-area"
                :class="{ 'drag-over': isDragging }"
                @dragover.prevent="isDragging = true"
                @dragleave.prevent="isDragging = false"
                @drop.prevent="handleDrop"
                @click="openFileBrowser">

                <v-icon size="32" color="#1E88E5">mdi-file-upload-outline</v-icon>
                <p>CSV, Excel, or JSON files</p>
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
                    <div class="dataset-rows">{{ ds.sheet_names?.length || 0 }} sheets</div>
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
              <v-btn color="#1E88E5" block @click="goToClean" :disabled="!hasData">
                <v-icon left>mdi-broom</v-icon> Clean Data
              </v-btn>
            </v-col>
          </v-row>
        </v-card-text>
      </v-card>

      <!-- Excel Preview -->
      <ExcelViewer v-if="showPreview"
        :key="fileBase64 || uploadedFile?.name"
        :file-base64="fileBase64"
        :file-name="uploadedFile?.name || ''"
        :data="dataset"
        :headers="headers"
        @data-update="dataset = $event"
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

    </div>
  </fixed-layout>
</template>

<script setup>
import FixedLayout from '../components/FixedLayout.vue'
import ExcelViewer from '../components/ExcelViewer.vue'
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { dataAPI, datasetAPI } from '../services/api'

const router = useRouter()
const fileInput = ref(null)

// UI state
const isDragging = ref(false)
const isLoading = ref(false)
const showPreview = ref(false)

// File data
const uploadedFile = ref(null)
const fileBase64 = ref('')
const dataset = ref([])
const headers = ref([])
const savedDatasets = ref([])
const uploadId = ref('')
const sheetNames = ref([])

// Computed helpers
const hasFile = computed(() => uploadedFile.value !== null)
const hasData = computed(() => dataset.value.length > 0 || fileBase64.value)

// Load saved datasets from backend
async function loadSavedDatasets() {
  try {
    const response = await datasetAPI.getAll()
    if (response.success) {
      savedDatasets.value = response.data
    }
  } catch (err) {
    console.error('Failed to load datasets:', err)
  }
}

// Save current dataset to backend
async function saveDataset(name, base64Data = null, sheets = null) {
  const dataToSave = base64Data || fileBase64.value
  const sheetNamesToSave = sheets || sheetNames.value || []
  if (!dataToSave) {
    console.error('No data to save')
    return false
  }
  
  try {
    const response = await datasetAPI.save(name, dataToSave, sheetNamesToSave, uploadId.value)
    console.log('Save dataset response:', response)
    if (response.success) {
      await loadSavedDatasets()
      console.log('Dataset saved successfully:', name)
      return true
    } else {
      console.error('Save failed with error:', response.error)
    }
  } catch (err) {
    console.error('Failed to save dataset:', err)
  }
  return false
}

// Ask user for dataset name and save
async function savePrompt() {
  console.log('Save button clicked, fileBase64 length:', fileBase64.value.length)
  const name = prompt('Dataset name:', uploadedFile.value?.name?.replace(/\.[^/.]+$/, '') || 'My Dataset')
  if (name?.trim()) {
    const saved = await saveDataset(name.trim(), fileBase64.value, sheetNames.value)
    if (saved) {
      alert('Dataset saved successfully!')
    } else {
      alert('Failed to save dataset. Please upload a file first.')
    }
  }
}

// Load a previously saved dataset
async function loadDataset(idx) {
  const ds = savedDatasets.value[idx]
  if (!ds) return

  console.log('Loading dataset:', ds.name, 'id:', ds.id)

  try {
    const response = await datasetAPI.load(ds.id)
    console.log('Load response:', response)
    
    if (response.success) {
      // Reset state first
      dataset.value = []
      headers.value = []
      
      // Then set new data
      fileBase64.value = response.data.file_base64
      uploadId.value = response.data.upload_id
      uploadedFile.value = { name: ds.name }
      
      // Force show preview
      showPreview.value = true
      
      // Force re-render by toggling
      await new Promise(resolve => setTimeout(resolve, 100))
      
      console.log('Dataset loaded successfully, fileBase64 length:', fileBase64.value.length)
    } else {
      console.error('Load failed:', response.error)
      alert('Failed to load dataset: ' + (response.error || 'Unknown error'))
    }
  } catch (err) {
    console.error('Failed to load dataset:', err)
    alert('Failed to load dataset')
  }
}

// Delete a saved dataset
async function deleteDataset(idx) {
  const ds = savedDatasets.value[idx]
  if (confirm(`Delete "${ds.name}"?`)) {
    try {
      const response = await datasetAPI.delete(ds.id)
      if (response.success) {
        await loadSavedDatasets()
      }
    } catch (err) {
      console.error('Failed to delete dataset:', err)
      alert('Failed to delete dataset')
    }
  }
}

// File handling
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

// Upload file to backend
async function uploadFile(file) {
  uploadedFile.value = file
  await loadPreview()
}

// Load preview from backend
async function loadPreview() {
  if (!uploadedFile.value) return

  console.log('Loading preview for:', uploadedFile.value.name)
  isLoading.value = true
  try {
    const res = await dataAPI.upload(uploadedFile.value, 'treasury_bills')
    console.log('Full upload response:', JSON.stringify(res, null, 2))

    let saved = false
    if (res.data?.file_base64) {
      fileBase64.value = res.data.file_base64
      uploadId.value = res.data.upload_id || ''
      sheetNames.value = res.data.sheet_names || []
      console.log('File loaded as base64, length:', fileBase64.value.length)
      
      // Automatically save to database
      const name = uploadedFile.value.name.replace(/\.[^/.]+$/, '')
      saved = await saveDataset(name, res.data.file_base64, sheetNames.value)
    } else if (res.data?.data) {
      dataset.value = res.data.data
      headers.value = Object.keys(dataset.value[0] || {})
      uploadId.value = res.data.upload_id || ''
      sheetNames.value = res.data.sheet_names || []
      console.log('Data loaded as JSON, rows:', dataset.value.length)
      
      // Cannot auto-save JSON data format - user needs to save manually
    } else {
      console.error('No file_base64 or data in response:', res)
    }
    
    if (saved) {
      console.log('Dataset auto-saved to database')
    } else {
      console.log('Dataset not auto-saved (might be JSON format or error)')
    }
  } catch (err) {
    console.error('Upload error:', err)
    alert('Upload failed')
  } finally {
    isLoading.value = false
  }
}

// Load and display Excel data
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
    if (confirm(`Save "${name}" to datasets?`)) saveDataset(name)
  } else {
    alert('Failed to load data')
  }
}

// Navigate to cleaning page with current data
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

// Load saved datasets when page opens
onMounted(() => {
  loadSavedDatasets()
})
</script>

<style scoped>
.upload-page { max-width: 1400px; margin: 0 auto; padding: 20px; }

/* Header */
.page-header { margin-bottom: 30px; }
.page-header h1 { color: #0B2A44; font-size: 32px; font-weight: 700; margin-bottom: 8px; }
.page-header p { color: #666; font-size: 16px; }

/* Upload Box */
.upload-box { border-radius: 16px; transition: 0.2s; }
.upload-box:hover { transform: translateY(-2px); box-shadow: 0 8px 24px rgba(11,42,68,0.15); }

/* Drop Zone */
.drop-area { border: 2px dashed #0B2A44; border-radius: 12px; padding: 32px 24px; cursor: pointer; transition: 0.3s; background: rgba(11,42,68,0.03); }
.drop-area:hover { background: rgba(11,42,68,0.08); border-color: #1E88E5; }
.drop-area.drag-over { background: rgba(30,136,229,0.1); border-color: #4CAF50; transform: scale(1.02); }

/* Saved Datasets Box */
.saved-box { border-radius: 16px; height: 100%; }
.saved-title { background: linear-gradient(135deg, #0B2A44, #1a3a5a); color: white; padding: 16px 20px; }

/* Dataset Row */
.dataset-row { display: flex; align-items: center; gap: 12px; padding: 12px 16px; background: #f8f9fa; border-radius: 8px; margin-bottom: 8px; }
.dataset-row:hover { background: #f0f4ff; }
.dataset-info { flex: 1; }
.dataset-name { font-weight: 600; color: #0B2A44; }
.dataset-rows { font-size: 12px; color: #666; }

/* Empty State */
.empty-state { text-align: center; padding: 40px; color: #999; }

/* Action Buttons Card */
.action-card { border-radius: 12px; margin-bottom: 20px; background: white; border: 1px solid rgba(11,42,68,0.08); }

/* Info Card */
.info-card { border-radius: 12px; margin-top: 20px; background: white; border: 1px solid rgba(11,42,68,0.08); }
.info-label { font-size: 12px; font-weight: 600; color: #666; margin-bottom: 4px; }
.info-value { font-size: 20px; font-weight: 700; color: #0B2A44; }

/* Mobile Responsive */
@media (max-width: 600px) {
  .upload-page { padding: 0 16px; }
  .drop-area { padding: 20px 16px; }
}
</style>