<template>
  <fixed-layout>
    <div class="upload-view">
      <!-- Header Section -->
      <div class="dashboard-header">
        <h1 class="page-title">Upload Dataset</h1>
        <p class="page-subtitle">Upload financial data for analysis and calculations</p>
      </div>

      <!-- Top Row: Upload and Saved Datasets -->
      <v-row class="mb-4" align="stretch">
        <v-col cols="12" md="6">
          <!-- Upload Area -->
          <v-card class="upload-card modern-card" elevation="3" hover>
            <v-card-text class="upload-card-content">
              <div class="upload-icon-wrapper">
                <v-icon size="56" color="#0B2A44">mdi-cloud-upload</v-icon>
              </div>
              <h3 class="upload-heading">Upload Dataset</h3>
              <p class="upload-subheading">Drag & drop your files here</p>
              <div
                class="drop-zone-modern"
                :class="{ 'drag-over': isDragOver }"
                @dragover.prevent="isDragOver = true"
                @dragleave.prevent="isDragOver = false"
                @drop.prevent="handleDrop"
                @click="triggerFileInput"
              >
                <v-icon size="32" color="#1E88E5" class="mb-2">mdi-file-upload-outline</v-icon>
                <p class="drop-zone-text">CSV, Excel, or JSON files</p>
                <v-btn color="#0B2A44" variant="elevated" size="small" class="mt-3">
                  Browse Files
                </v-btn>
              </div>
              <input
                ref="fileInput"
                type="file"
                accept=".csv,.xlsx,.xls,.json"
                multiple
                @change="handleFileSelect"
                style="display: none"
              />
            </v-card-text>
          </v-card>
        </v-col>

        <v-col cols="12" md="6">
          <!-- Saved Datasets -->
          <v-card class="saved-card modern-card" elevation="3">
            <v-card-title class="saved-card-title">
              <v-icon class="title-icon">mdi-database</v-icon>
              Saved Datasets
              <v-spacer></v-spacer>
              <v-chip size="small" color="#0B2A44" variant="tonal">{{ savedDatasets.length }}</v-chip>
            </v-card-title>
            <v-card-text class="pa-4">
              <div v-if="savedDatasets.length > 0" class="datasets-list">
                <div
                  v-for="(dataset, index) in savedDatasets"
                  :key="dataset.name"
                  class="dataset-item-modern"
                >
                  <div class="dataset-icon">
                    <v-icon color="#1E88E5">mdi-file-excel</v-icon>
                  </div>
                  <div class="dataset-info">
                    <div class="dataset-name">{{ dataset.name }}</div>
                    <div class="dataset-meta">{{ dataset.rows }} rows • {{ new Date(dataset.timestamp).toLocaleDateString() }}</div>
                  </div>
                  <div class="dataset-actions">
                    <v-btn
                      size="small"
                      color="#0B2A44"
                      variant="text"
                      @click="loadSavedDataset(index)"
                    >
                      <v-icon size="small">mdi-folder-open</v-icon>
                    </v-btn>
                    <v-btn
                      size="small"
                      color="error"
                      variant="text"
                      @click="deleteSavedDataset(index)"
                    >
                      <v-icon size="small">mdi-delete</v-icon>
                    </v-btn>
                  </div>
                </div>
              </div>
              <v-alert v-else type="info" variant="tonal" density="comfortable" class="empty-state">
                <v-icon class="mb-2">mdi-database-off</v-icon>
                <div>No datasets saved yet</div>
                <div class="text-caption">Upload a file to get started</div>
              </v-alert>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <!-- Middle Row: Quick Actions -->
      <v-row class="mb-4">
        <v-col cols="12">
          <v-card class="stats-card" elevation="2">
            <v-card-title class="card-title">
              <v-icon class="title-icon">mdi-lightning-bolt</v-icon>
              Quick Actions
            </v-card-title>
            <v-card-text class="pa-2">
              <v-row>
                <v-col cols="12" sm="6" md="3">
                  <v-card class="action-item" hover @click="navigateTo('/calculations')">
                    <v-card-text class="text-center pa-3">
                      <v-icon color="#0B2A44" size="28" class="mb-1">mdi-calculator</v-icon>
                      <div class="action-title-sm">Calculate Yields</div>
                      <div class="action-desc-sm">Process data</div>
                    </v-card-text>
                  </v-card>
                </v-col>
                <v-col cols="12" sm="6" md="3">
                  <v-card class="action-item" hover @click="navigateTo('/cleaning')">
                    <v-card-text class="text-center pa-3">
                      <v-icon color="#1E88E5" size="28" class="mb-1">mdi-broom</v-icon>
                      <div class="action-title-sm">Clean Data</div>
                      <div class="action-desc-sm">Remove duplicates</div>
                    </v-card-text>
                  </v-card>
                </v-col>
                <v-col cols="12" sm="6" md="3">
                  <v-card class="action-item" hover @click="navigateTo('/visualizations')">
                    <v-card-text class="text-center pa-3">
                      <v-icon color="#4CAF50" size="28" class="mb-1">mdi-chart-line</v-icon>
                      <div class="action-title-sm">Visualize</div>
                      <div class="action-desc-sm">Create charts</div>
                    </v-card-text>
                  </v-card>
                </v-col>
                <v-col cols="12" sm="6" md="3">
                  <v-card class="action-item" hover @click="navigateTo('/reports')">
                    <v-card-text class="text-center pa-3">
                      <v-icon color="#FFC107" size="28" class="mb-1">mdi-file-document</v-icon>
                      <div class="action-title-sm">Generate Report</div>
                      <div class="action-desc-sm">Export results</div>
                    </v-card-text>
                  </v-card>
                </v-col>
              </v-row>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <!-- Excel Preview Toggle Button -->
      <v-card class="stats-card" elevation="2" v-if="uploadedFiles.length > 0">
        <v-card-text class="pa-3">
          <v-row>
            <v-col cols="12" sm="4">
              <v-btn
                color="success"
                size="default"
                block
                @click="loadAndShowExcel"
                :loading="previewLoading"
              >
                <v-icon left>mdi-microsoft-excel</v-icon>
                Load Data to Excel
              </v-btn>
            </v-col>
            <v-col cols="12" sm="4" v-if="showExcelPreview">
              <v-btn
                color="info"
                size="default"
                block
                @click="promptSaveDataset"
              >
                <v-icon left>mdi-content-save</v-icon>
                Save Dataset
              </v-btn>
            </v-col>
            <v-col cols="12" sm="4" v-if="showExcelPreview">
              <v-btn
                color="warning"
                size="default"
                block
                @click="showExcelPreview = false"
              >
                <v-icon left>mdi-eye-off</v-icon>
                Hide Preview
              </v-btn>
            </v-col>
          </v-row>
        </v-card-text>
      </v-card>

      <!-- Data Preview -->
      <ExcelViewer
        v-if="showExcelPreview"
        :file-base64="excelFileBase64"
        :file-name="uploadedFiles.length > 0 ? uploadedFiles[0].name : ''"
        :data="fullDataset.length > 0 ? fullDataset : undefined"
        :headers="previewHeaders.length > 0 ? previewHeaders.map((h: any) => typeof h === 'object' ? h.key : h) : undefined"
        @data-update="handleDataUpdate"
      />

      <!-- Dataset Description -->
      <v-card v-if="showExcelPreview" class="stats-card" elevation="2">
        <v-card-title class="card-title">
          <v-icon class="title-icon">mdi-information</v-icon>
          Dataset Information
        </v-card-title>
        <v-card-text>
          <v-row>
            <v-col cols="12" sm="6" md="3">
              <div class="info-item">
                <div class="info-label">Data Type</div>
                <div class="info-value">{{ datasetMetadata.instrumentType || 'Financial Instruments' }}</div>
              </div>
            </v-col>
            <v-col cols="12" sm="6" md="3">
              <div class="info-item">
                <div class="info-label">Country/Region</div>
                <div class="info-value">{{ datasetMetadata.country || 'Not specified' }}</div>
              </div>
            </v-col>
            <v-col cols="12" sm="6" md="3">
              <div class="info-item">
                <div class="info-label">Currency</div>
                <div class="info-value">{{ datasetMetadata.currency || 'Not specified' }}</div>
              </div>
            </v-col>
            <v-col cols="12" sm="6" md="3">
              <div class="info-item">
                <div class="info-label">Total Records</div>
                <div class="info-value">{{ fullDataset.length }}</div>
              </div>
            </v-col>
          </v-row>
        </v-card-text>
      </v-card>
    </div>
  </fixed-layout>
</template>

<script setup lang="ts">
import FixedLayout from '../components/FixedLayout.vue'
import ExcelViewer from '../components/ExcelViewer.vue'
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { dataAPI } from '../services/api'

const router = useRouter()
const fileInput = ref()
const isDragOver = ref(false)
const uploadedFiles = ref<File[]>([])

// Saved datasets state
const savedDatasets = ref<Array<{ name: string; rows: number; columns: number; timestamp: string; data: any[]; headers: string[]; file_base64?: string; sheet_names?: string[] }>>([])

// Initialize from localStorage
try {
  const saved = localStorage.getItem('saved-datasets')
  if (saved) {
    savedDatasets.value = JSON.parse(saved)
  }
} catch (err) {
  console.error('Failed to initialize saved datasets:', err)
}

// Preview data state
const previewData = ref<any[]>([])
const previewHeaders = ref<any[]>([])
const previewLoading = ref(false)
const fullDataset = ref<any[]>([])
const excelFileBase64 = ref<string>('')
const currentPage = ref(1)
const pageSize = ref(10)
const totalPages = ref(0)
const uploadId = ref<string | null>(null)
const showExcelPreview = ref(false)

// ExcelGrid metadata
const datasetMetadata = ref({
  country: 'United States',
  currency: 'USD',
  instrumentType: 'Treasury Bills',
  dateRange: '',
  description: ''
})

// ExcelGrid handlers
const handleDataUpdate = (newData: any[]) => {
  fullDataset.value = newData
  console.log('Dataset updated:', newData.length, 'rows')
}

const handleHeadersUpdate = (newHeaders: string[]) => {
  previewHeaders.value = newHeaders.map(h => ({ title: h, key: h, sortable: true }))
  console.log('Headers updated:', newHeaders)
}

const handleMetadataUpdate = (metadata: any) => {
  datasetMetadata.value = metadata
  console.log('Metadata updated:', metadata)
}

// Saved datasets functions
const SAVED_DATASETS_KEY = 'saved-datasets'

const loadSavedDatasets = () => {
  try {
    const saved = localStorage.getItem(SAVED_DATASETS_KEY)
    console.log('Loading saved datasets from localStorage:', saved)
    if (saved) {
      savedDatasets.value = JSON.parse(saved)
      console.log('Loaded datasets:', savedDatasets.value)
    } else {
      console.log('No saved datasets found in localStorage')
    }
  } catch (err) {
    console.error('Failed to load saved datasets:', err)
  }
}

const saveDataset = (name: string) => {
  if (excelFileBase64.value === '' && fullDataset.value.length === 0) {
    alert('No data to save. Please upload a file first.')
    return
  }

  const dataset: any = {
    name,
    timestamp: new Date().toISOString()
  }

  // Save base64 data if available (Excel files with new format)
  if (excelFileBase64.value !== '') {
    dataset.file_base64 = excelFileBase64.value
    dataset.rows = 0 // Will be determined when loaded
    dataset.columns = 0
    dataset.sheet_names = [] // Will be determined when loaded
  } else {
    // Fallback to old format
    dataset.rows = fullDataset.value.length
    dataset.columns = previewHeaders.value.length
    dataset.data = fullDataset.value
    dataset.headers = previewHeaders.value.map((h: any) => typeof h === 'object' ? h.key : h)
  }

  const existingIndex = savedDatasets.value.findIndex((d: any) => d.name === name)
  if (existingIndex !== -1) {
    savedDatasets.value[existingIndex] = dataset
  } else {
    savedDatasets.value.push(dataset)
  }

  localStorage.setItem(SAVED_DATASETS_KEY, JSON.stringify(savedDatasets.value))
  console.log('Dataset saved:', name)
}

const loadSavedDataset = (index: number) => {
  const dataset = savedDatasets.value[index]
  
  // Check if dataset has base64 data (new format)
  if (dataset.file_base64) {
    excelFileBase64.value = dataset.file_base64
  } else {
    // Fallback to old format
    fullDataset.value = dataset.data
    previewHeaders.value = dataset.headers.map((h: string) => ({ title: h, key: h, sortable: true }))
  }
  
  showExcelPreview.value = true
  console.log('Dataset loaded:', dataset.name)
}

const deleteSavedDataset = (index: number) => {
  if (confirm('Are you sure you want to delete this dataset?')) {
    savedDatasets.value.splice(index, 1)
    localStorage.setItem(SAVED_DATASETS_KEY, JSON.stringify(savedDatasets.value))
    console.log('Dataset deleted')
  }
}

const promptSaveDataset = () => {
  const name = prompt('Enter a name for this dataset:')
  if (name && name.trim()) {
    saveDataset(name.trim())
    alert('Dataset saved successfully!')
  }
}

// Load saved datasets on mount
onMounted(() => {
  loadSavedDatasets()
  console.log('savedDatasets.value after mount:', savedDatasets.value)
  console.log('savedDatasets.value.length:', savedDatasets.value.length)
})

// Toggle Excel preview and load data if needed
const toggleExcelPreview = async () => {
  console.log('toggleExcelPreview called, current state:', showExcelPreview.value)
  console.log('uploadedFiles:', uploadedFiles.value.length)
  console.log('fullDataset:', fullDataset.value.length)
  
  if (!showExcelPreview.value) {
    // Show preview - load data if not already loaded
    if (fullDataset.value.length === 0) {
      console.log('Loading full preview...')
      await loadFullPreview()
      console.log('Full preview loaded, dataset length:', fullDataset.value.length)
    }
    showExcelPreview.value = true
    console.log('showExcelPreview set to true')
  } else {
    // Hide preview
    showExcelPreview.value = false
    console.log('showExcelPreview set to false')
  }
}

// Explicit function to load data and show Excel
const loadAndShowExcel = async () => {
  console.log('loadAndShowExcel called')
  console.log('uploadedFiles:', uploadedFiles.value.length)
  
  if (uploadedFiles.value.length === 0) {
    console.error('No files uploaded')
    alert('Please upload a file first')
    return
  }
  
  console.log('Loading full preview...')
  await loadFullPreview()
  console.log('Full preview loaded, dataset length:', fullDataset.value.length)
  console.log('previewHeaders:', previewHeaders.value)
  console.log('First row of data:', fullDataset.value[0])
  console.log('Headers being passed to ExcelGrid:', previewHeaders.value.map(h => typeof h === 'object' ? h.title : h))
  
  if (fullDataset.value.length > 0) {
    showExcelPreview.value = true
    console.log('showExcelPreview set to true')
    
    // Auto-save the dataset with the filename
    const filename = uploadedFiles.value[0].name.replace(/\.[^/.]+$/, '') // Remove file extension
    saveDataset(filename)
    console.log('Dataset auto-saved with name:', filename)
  } else {
    console.error('No data loaded from backend')
    alert('Failed to load data. Please check the console for details.')
  }
}

// Computed properties for stats
const totalRows = computed(() => fullDataset.value.length || previewData.value.length)
const totalColumns = computed(() => previewHeaders.value.length)
const fileTypes = computed(() => [...new Set(uploadedFiles.value.map(f => getFileIcon(f.type).icon))])
const totalSize = computed(() => uploadedFiles.value.reduce((acc, file) => acc + file.size, 0))

// Pagination computed properties
const paginatedData = computed(() => {
  if (fullDataset.value.length > 0) {
    const start = (currentPage.value - 1) * pageSize.value
    const end = start + pageSize.value
    return fullDataset.value.slice(start, end)
  }
  return previewData.value
})

const hasNextPage = computed(() => currentPage.value < totalPages.value)
const hasPreviousPage = computed(() => currentPage.value > 1)
const startRow = computed(() => {
  if (fullDataset.value.length > 0) {
    return (currentPage.value - 1) * pageSize.value + 1
  }
  return 1
})
const endRow = computed(() => {
  if (fullDataset.value.length > 0) {
    const end = currentPage.value * pageSize.value
    return Math.min(end, fullDataset.value.length)
  }
  return previewData.value.length
})

const triggerFileInput = () => {
  fileInput.value?.click()
}

const handleFileSelect = (event: Event) => {
  const target = event.target as HTMLInputElement
  if (target.files) {
    addFiles(Array.from(target.files))
  }
}

const handleDrop = (event: DragEvent) => {
  isDragOver.value = false
  if (event.dataTransfer?.files) {
    addFiles(Array.from(event.dataTransfer.files))
  }
}

const addFiles = async (files: File[]) => {
  const validFiles = files.filter(file => 
    file.type.includes('csv') || 
    file.type.includes('sheet') || 
    file.type.includes('json') ||
    file.name.endsWith('.csv') ||
    file.name.endsWith('.xlsx') ||
    file.name.endsWith('.xls') ||
    file.name.endsWith('.json')
  )
  
  uploadedFiles.value.push(...validFiles)
  
  // Auto-generate preview for first valid file
  if (validFiles.length > 0 && previewData.value.length === 0) {
    await loadFullPreview()
  }
}

const removeFile = (index: number) => {
  uploadedFiles.value.splice(index, 1)
}

const previewFile = async (index: number) => {
  console.log('previewFile called with index:', index)
  console.log('uploadedFiles:', uploadedFiles.value)
  
  previewLoading.value = true
  try {
    // Reset preview data
    previewData.value = []
    previewHeaders.value = []
    fullDataset.value = []
    excelFileBase64.value = ''
    currentPage.value = 1
    
    // Upload and preview the selected file
    const file = uploadedFiles.value[index]
    console.log('Selected file:', file)
    
    const response = await dataAPI.upload(file, 'treasury_bills')
    console.log('API response:', response)
    
    if (response.success) {
      console.log('Upload successful, processing data...')
      
      // Check if response contains base64 Excel file (new format)
      if (response.data.file_base64) {
        excelFileBase64.value = response.data.file_base64
        uploadId.value = response.data.upload_id
        
        // Save dataset to localStorage for all pages
        const datasetToSave = {
          name: response.data.file_name,
          file_base64: response.data.file_base64,
          sheet_names: response.data.sheet_names,
          upload_id: response.data.upload_id,
          timestamp: new Date().toISOString()
        }
        
        // Save to multiple localStorage keys for persistence across pages
        localStorage.setItem('uploadedDataset', JSON.stringify(datasetToSave))
        localStorage.setItem('currentDataset', JSON.stringify(datasetToSave))
        localStorage.setItem('datasetStatus', 'uploaded')
        localStorage.setItem('datasetInfo', JSON.stringify({
          name: response.data.file_name,
          sheets: response.data.sheet_names?.length || 0,
          uploadId: response.data.upload_id
        }))
        
        console.log('Dataset saved to localStorage for all pages')
        console.log('Excel file base64 loaded, sheets:', response.data.sheet_names)
      } else {
        // Fallback to old format
        fullDataset.value = response.data.data
        uploadId.value = response.data.upload_id
        
        // Save dataset to localStorage for all pages
        const datasetToSave = {
          name: response.data.name,
          instrumentType: response.data.instrument_type,
          data: response.data.data,
          display_headers: response.data.display_headers,
          upload_id: response.data.upload_id,
          size: response.data.size,
          timestamp: new Date().toISOString()
        }
        
        localStorage.setItem('uploadedDataset', JSON.stringify(datasetToSave))
        localStorage.setItem('currentDataset', JSON.stringify(datasetToSave))
        localStorage.setItem('datasetStatus', 'uploaded')
        localStorage.setItem('datasetInfo', JSON.stringify({
          name: response.data.name,
          rows: response.data.data.length,
          columns: response.data.display_headers?.length || 0,
          instrumentType: response.data.instrument_type,
          uploadId: response.data.upload_id
        }))
        
        console.log('Dataset saved to localStorage for all pages')
        
        // Calculate total pages
        totalPages.value = Math.ceil(fullDataset.value.length / pageSize.value)
        
        // Use display headers from backend if available, otherwise generate from data
        if (response.data.display_headers && response.data.display_headers.length > 0) {
          console.log('Using display headers from backend:', response.data.display_headers)
          const dataKeys = Object.keys(fullDataset.value[0])
          previewHeaders.value = response.data.display_headers.map((header, index) => ({
            title: header,
            key: dataKeys[index] || `col_${index}`,
            sortable: true
          }))
        } else if (fullDataset.value.length > 0) {
          console.log('Generating headers from data keys')
          const headers = Object.keys(fullDataset.value[0])
          previewHeaders.value = headers.map(h => ({ title: h, key: h, sortable: true }))
        }
        
        console.log('Preview data loaded:', fullDataset.value.length, 'rows total')
        console.log('Total pages:', totalPages.value)
        console.log('Headers:', previewHeaders.value)
      }
    } else {
      console.error('Upload failed:', response)
    }
  } catch (error) {
    console.error('Error previewing file:', error)
  } finally {
    previewLoading.value = false
  }
}

const getFileIcon = (type: string) => {
  if (type.includes('csv') || type.endsWith('.csv')) {
    return { icon: 'mdi-file-delimited', color: '#4CAF50' }
  }
  if (type.includes('sheet') || type.endsWith('.xlsx') || type.endsWith('.xls')) {
    return { icon: 'mdi-file-excel', color: '#1E88E5' }
  }
  if (type.includes('json') || type.endsWith('.json')) {
    return { icon: 'mdi-code-json', color: '#FFC107' }
  }
  return { icon: 'mdi-file', color: '#666' }
}

const formatFileSize = (bytes: number) => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

// File parsing functions
const parseCSV = (text: string) => {
  const lines = text.split('\n').filter(line => line.trim())
  if (lines.length === 0) return { headers: [], data: [] }
  
  const headers = lines[0].split(',').map(h => h.trim().replace(/"/g, ''))
  const data = lines.slice(1, 11).map(line => {
    const values = line.split(',').map(v => v.trim().replace(/"/g, ''))
    const row: any = {}
    headers.forEach((header, index) => {
      row[header] = values[index] || ''
    })
    return row
  })
  
  return { headers, data }
}

const parseJSON = (text: string) => {
  try {
    const parsed = JSON.parse(text)
    if (Array.isArray(parsed) && parsed.length > 0) {
      const headers = Object.keys(parsed[0])
      const data = parsed.slice(0, 10)
      return { headers, data }
    }
  } catch {
    return { headers: [], data: [] }
  }
  return { headers: [], data: [] }
}

const processFile = async (file: File) => {
  const text = await file.text()
  
  if (file.name.endsWith('.csv')) {
    return parseCSV(text)
  } else if (file.name.endsWith('.json')) {
    return parseJSON(text)
  } else {
    // For Excel files, show basic info
    return {
      headers: ['File Name', 'Size', 'Type', 'Last Modified'],
      data: [{
        'File Name': file.name,
        'Size': formatFileSize(file.size),
        'Type': file.type || 'Unknown',
        'Last Modified': new Date(file.lastModified).toLocaleDateString()
      }]
    }
  }
}

const loadFullPreview = async () => {
  previewLoading.value = true
  console.log('loadFullPreview called')
  try {
    if (uploadedFiles.value.length > 0) {
      // Upload file to backend and get full dataset
      const file = uploadedFiles.value[0]
      console.log('Uploading file:', file.name, file.size)
      const response = await dataAPI.upload(file, 'treasury_bills')
      console.log('Upload response:', response)
      
      if (response.success) {
        console.log('Response data:', response.data)
        
        // Check if response contains base64 Excel file (new format)
        if (response.data.file_base64) {
          excelFileBase64.value = response.data.file_base64
          console.log('Excel file base64 loaded, sheets:', response.data.sheet_names)
          uploadId.value = response.data.upload_id
          
          // Save to localStorage with new format
          const datasetToSave = {
            name: response.data.file_name,
            file_base64: response.data.file_base64,
            sheet_names: response.data.sheet_names,
            upload_id: response.data.upload_id,
            timestamp: new Date().toISOString()
          }
          localStorage.setItem('uploadedDataset', JSON.stringify(datasetToSave))
        } else {
          // Fallback to old format if backend still returns parsed data
          fullDataset.value = response.data.data
          console.log('fullDataset set to:', fullDataset.value.length, 'rows')
          uploadId.value = response.data.upload_id
          currentPage.value = 1
          
          // Calculate total pages
          totalPages.value = Math.ceil(fullDataset.value.length / pageSize.value)
          
          // Use display headers from backend if available, otherwise generate from data
          if (response.data.display_headers && response.data.display_headers.length > 0) {
            console.log('Using display headers from backend in loadFullPreview:', response.data.display_headers)
            const dataKeys = Object.keys(fullDataset.value[0])
            console.log('Data keys from first row:', dataKeys)
            previewHeaders.value = response.data.display_headers.map((header, index) => ({
              title: header,
              key: dataKeys[index] || `col_${index}`,
              sortable: true
            }))
            console.log('previewHeaders set to:', previewHeaders.value)
          } else if (fullDataset.value.length > 0) {
            console.log('Generating headers from data keys in loadFullPreview')
            const headers = Object.keys(fullDataset.value[0])
            previewHeaders.value = headers.map(h => ({ title: h, key: h, sortable: true }))
            console.log('previewHeaders set to:', previewHeaders.value)
          } else {
            console.error('No data in response.data.data')
          }
          
          console.log('Full preview loaded:', fullDataset.value.length, 'rows total')
          console.log('Total pages:', totalPages.value)
          
          // Log first row data for debugging
          if (fullDataset.value.length > 0) {
            console.log('First row data:', fullDataset.value[0])
            console.log('First row keys:', Object.keys(fullDataset.value[0]))
          }
        }
      }
    }
  } catch (error) {
    console.error('Error loading preview:', error)
  } finally {
    previewLoading.value = false
  }
}

const nextPage = () => {
  if (hasNextPage.value) {
    currentPage.value++
  }
}

const previousPage = () => {
  if (hasPreviousPage.value) {
    currentPage.value--
  }
}

const navigateTo = (route: string) => {
  router.push(route)
}
</script>

<style scoped>
.upload-view {
  max-width: 1400px;
  margin: 0 auto;
}

/* Global styles for blue headers - not scoped */
:deep(.styled-headers thead th) {
  background: linear-gradient(135deg, #0B2A44 0%, #1a3a5a 100%) !important;
  color: white !important;
  font-weight: 700 !important;
  text-align: center !important;
  font-size: 13px !important;
  padding: 14px 6px !important;
  border-bottom: 3px solid #0B2A44 !important;
}

:deep(.styled-headers .v-data-table__th) {
  background: linear-gradient(135deg, #0B2A44 0%, #1a3a5a 100%) !important;
  color: white !important;
  font-weight: 700 !important;
  text-align: center !important;
  font-size: 12px !important;
  padding: 10px 6px !important;
  height: 40px !important;
  min-height: 40px !important;
  line-height: 1.3 !important;
  vertical-align: middle !important;
  border-right: 1px solid rgba(255, 255, 255, 0.15) !important;
  border-bottom: none !important;
  border-top: none !important;
  border-left: none !important;
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.1) !important;
  letter-spacing: 0.3px !important;
  text-transform: none !important;
}

/* Perfect header styling - no division lines, same as data rows */
:deep(.preview-table.styled-headers table thead th),
:deep(.styled-headers table thead th),
:deep(.styled-headers thead tr th) {
  background: linear-gradient(135deg, #0B2A44 0%, #1a3a5a 100%) !important;
  color: white !important;
  font-weight: 700 !important;
  text-align: center !important;
  font-size: 12px !important;
  padding: 10px 6px !important;
  height: 40px !important;
  min-height: 40px !important;
  line-height: 1.3 !important;
  vertical-align: middle !important;
  border-right: 1px solid rgba(255, 255, 255, 0.15) !important;
  border-bottom: none !important;
  border-top: none !important;
  border-left: none !important;
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.1) !important;
  letter-spacing: 0.3px !important;
  text-transform: none !important;
}

/* Compact row styling with deep selectors */
:deep(.styled-headers tbody tr),
:deep(.styled-headers .v-data-table__tr) {
  height: 40px !important;
  min-height: 40px !important;
}

:deep(.styled-headers tbody td),
:deep(.styled-headers .v-data-table__td) {
  height: 40px !important;
  min-height: 40px !important;
  padding: 10px 6px !important;
  vertical-align: middle !important;
  line-height: 1.3 !important;
  text-align: center !important;
  font-size: 12px !important;
  color: #333333 !important;
  font-weight: 400 !important;
  border-bottom: 1px solid #e8e8e8 !important;
  border-right: 1px solid #f0f0f0 !important;
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
}

:deep(.styled-headers tbody tr:nth-child(even) td),
:deep(.styled-headers .v-data-table__tr:nth-child(even) .v-data-table__td) {
  background-color: #fafafa !important;
}

:deep(.styled-headers tbody tr:hover td),
:deep(.styled-headers .v-data-table__tr:hover .v-data-table__td) {
  background-color: #f5f9ff !important;
  transition: background-color 0.15s ease !important;
}

.dashboard-header {
  margin-bottom: 32px;
}

.page-title {
  color: #0B2A44;
  font-size: 32px;
  font-weight: 700;
  margin-bottom: 8px;
}

.page-subtitle {
  color: #666;
  font-size: 16px;
  margin: 0;
}

.stats-card {
  border-radius: 12px;
  margin-bottom: 32px;
  background: white;
  border: 1px solid rgba(11, 42, 68, 0.08);
  position: relative;
  display: flex;
  flex-direction: column;
}

.equal-height {
  height: 100%;
  min-height: 400px;
}

.equal-height .v-card-text {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 16px !important;
}

/* Override for Saved Datasets to not center */
.equal-height .v-card-text:not(.upload-card-text) {
  justify-content: flex-start;
  align-items: stretch;
}

.upload-card-text {
  justify-content: center !important;
  align-items: center !important;
}

.upload-area {
  width: 100%;
  height: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
}

.drop-zone {
  width: 100%;
  height: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 300px;
}

.drop-zone .v-card-text {
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
}

.saved-datasets-container {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
}

/* Modern Card Styles */
.modern-card {
  border-radius: 16px !important;
  overflow: hidden;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.modern-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(11, 42, 68, 0.15) !important;
}

/* Upload Card Styles */
.upload-card {
  background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
  border: 2px solid #e3e8ee;
}

.upload-card-content {
  text-align: center;
  padding: 32px !important;
}

.upload-icon-wrapper {
  margin-bottom: 16px;
}

.upload-heading {
  font-size: 24px;
  font-weight: 700;
  color: #0B2A44;
  margin-bottom: 8px;
}

.upload-subheading {
  font-size: 14px;
  color: #666;
  margin-bottom: 24px;
}

.drop-zone-modern {
  background: rgba(11, 42, 68, 0.03);
  border: 2px dashed #0B2A44;
  border-radius: 12px;
  padding: 32px 24px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.drop-zone-modern:hover {
  background: rgba(11, 42, 68, 0.08);
  border-color: #1E88E5;
}

.drop-zone-modern.drag-over {
  background: rgba(30, 136, 229, 0.1);
  border-color: #4CAF50;
  transform: scale(1.02);
}

.drop-zone-text {
  font-size: 14px;
  color: #666;
  margin-bottom: 0;
}

/* Saved Card Styles */
.saved-card {
  background: white;
  border: 1px solid #e3e8ee;
  height: 100%;
  min-height: 400px;
  display: flex;
  flex-direction: column;
}

.saved-card .v-card-text {
  flex-grow: 1;
  display: flex;
  flex-direction: column;
}

.saved-card-title {
  background: linear-gradient(135deg, #0B2A44 0%, #1a3a5a 100%);
  color: white;
  padding: 16px 20px;
  font-size: 16px;
  font-weight: 600;
}

.saved-card-title .title-icon {
  margin-right: 8px;
}

.datasets-list {
  max-height: 320px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.dataset-item-modern {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  background: #f8f9fa;
  border-radius: 8px;
  transition: background 0.2s ease;
  gap: 12px;
}

.dataset-item-modern:hover {
  background: #f0f4ff;
}

.dataset-icon {
  flex-shrink: 0;
}

.dataset-info {
  flex-grow: 1;
  min-width: 0;
}

.dataset-name {
  font-weight: 600;
  color: #0B2A44;
  font-size: 14px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.dataset-meta {
  font-size: 12px;
  color: #666;
  margin-top: 2px;
}

.dataset-actions {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}

.empty-state {
  text-align: center;
  padding: 32px;
  background: #f8f9fa;
  border-radius: 8px;
}

.empty-state .v-icon {
  font-size: 48px;
  color: #0B2A44;
  margin-bottom: 12px;
}

.stats-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, #0B2A44, #1E88E5);
}

.card-title {
  display: flex;
  align-items: center;
  color: #0B2A44;
  font-weight: 600;
  font-size: 18px;
}

.title-icon {
  margin-right: 8px;
  color: #0B2A44;
}

.upload-area {
  margin-bottom: 16px;
}

.drop-zone {
  border: 2px dashed #0B2A44;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
  background: rgba(11, 42, 68, 0.02);
}

.drop-zone:hover {
  border-color: #1E88E5;
  background: rgba(30, 136, 229, 0.05);
}

.drop-zone.drag-over {
  border-color: #4CAF50;
  background: rgba(76, 175, 80, 0.1);
}

.upload-title {
  color: #0B2A44;
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 8px;
}

.upload-desc {
  color: #666;
  font-size: 14px;
  margin-bottom: 16px;
}

.file-item {
  border-radius: 8px;
  margin-bottom: 8px;
  transition: transform 0.2s ease;
}

.file-item:hover {
  transform: translateX(4px);
}

.action-item {
  border-radius: 8px;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  height: 100%;
}

.action-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.action-title {
  font-weight: 600;
  color: #0B2A44;
  margin-bottom: 4px;
}

.action-desc {
  font-size: 12px;
  color: #666;
}

.action-title-sm {
  font-weight: 600;
  color: #0B2A44;
  margin-bottom: 2px;
  font-size: 14px;
}

.action-desc-sm {
  font-size: 11px;
  color: #666;
}

.saved-datasets-container {
  max-height: 200px;
  overflow-y: auto;
}

.info-item {
  padding: 12px;
  background: #f9f9f9;
  border-radius: 8px;
  margin-bottom: 8px;
}

.info-label {
  font-size: 12px;
  font-weight: 600;
  color: #666;
  margin-bottom: 4px;
}

.info-value {
  font-size: 14px;
  font-weight: 600;
  color: #0B2A44;
}

/* Preview Table Styles */
.preview-table {
  border-radius: 8px;
  overflow: hidden;
}

/* Blue Header Styling - Direct Vuetify targeting */
.styled-headers .v-data-table__th {
  background: linear-gradient(135deg, #0B2A44 0%, #1a3a5a 100%) !important;
  color: white !important;
  font-weight: 700 !important;
  text-align: center !important;
  font-size: 13px !important;
  padding: 14px 6px !important;
  border-bottom: 3px solid #0B2A44 !important;
  border-right: 1px solid rgba(255, 255, 255, 0.1) !important;
  position: sticky !important;
  top: 0 !important;
  z-index: 10 !important;
  letter-spacing: 0.5px !important;
  box-shadow: 0 2px 4px rgba(11, 42, 68, 0.2) !important;
}

/* Alternative targeting for Vuetify 3 */
.styled-headers thead th {
  background: linear-gradient(135deg, #0B2A44 0%, #1a3a5a 100%) !important;
  color: white !important;
  font-weight: 700 !important;
  text-align: center !important;
  font-size: 13px !important;
  padding: 14px 6px !important;
  border-bottom: 3px solid #0B2A44 !important;
}

/* More specific targeting */
.v-data-table.styled-headers thead th {
  background: linear-gradient(135deg, #0B2A44 0%, #1a3a5a 100%) !important;
  color: white !important;
  font-weight: 700 !important;
  text-align: center !important;
  font-size: 13px !important;
  padding: 14px 6px !important;
}

/* Force blue headers with multiple selectors */
.styled-headers .v-data-table__wrapper table thead th,
.styled-headers .v-data-table__wrapper table thead td,
.preview-table.styled-headers thead th,
.preview-table.styled-headers thead td {
  background: linear-gradient(135deg, #0B2A44 0%, #1a3a5a 100%) !important;
  color: white !important;
  font-weight: 700 !important;
  text-align: center !important;
  font-size: 13px !important;
  padding: 14px 6px !important;
}

/* Table cell alignment - Optimized compact size */
.styled-headers .v-data-table__td {
  text-align: center !important;
  padding: 10px 6px !important;
  font-size: 12px !important;
  border-bottom: 1px solid #e8e8e8 !important;
  color: #333333 !important;
  font-weight: 400 !important;
  background-color: #ffffff !important;
  vertical-align: middle !important;
  height: 40px !important;
  min-height: 40px !important;
  line-height: 1.3 !important;
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
  border-right: 1px solid #f0f0f0 !important;
}

/* Optimized alternating row colors */
.styled-headers .v-data-table__tr:nth-child(even) .v-data-table__td {
  background-color: #fafafa !important;
}

/* Compact hover effect */
.styled-headers .v-data-table__tr:hover .v-data-table__td {
  background-color: #f5f9ff !important;
  transition: background-color 0.15s ease !important;
}

/* Optimize row height */
.styled-headers .v-data-table__tr {
  height: 40px !important;
  min-height: 40px !important;
}

/* Compact table rows */
.styled-headers tbody tr {
  height: 40px !important;
  min-height: 40px !important;
}

/* Optimized cell dimensions */
.styled-headers tbody td {
  height: 40px !important;
  min-height: 40px !important;
  padding: 10px 6px !important;
  vertical-align: middle !important;
  line-height: 1.3 !important;
}

/* Table styling for consistent feel */
.styled-headers .v-data-table {
  border: 1px solid #e0e0e0 !important;
  border-radius: 8px !important;
  overflow: hidden !important;
}

.styled-headers .v-data-table__wrapper {
  border-radius: 8px !important;
}

.preview-stats {
  margin-top: 24px;
  padding: 16px;
  background: rgba(11, 42, 68, 0.03);
  border-radius: 8px;
}

.preview-stats .stat-item {
  text-align: center;
  padding: 16px;
  background: white;
  border-radius: 8px;
  transition: transform 0.2s ease;
}

.preview-stats .stat-item:hover {
  transform: translateY(-2px);
}

.preview-stats .stat-value {
  font-size: 24px;
  font-weight: 700;
  color: #0B2A44;
  margin-bottom: 4px;
}

.preview-stats .stat-label {
  font-size: 14px;
  color: #666;
  font-weight: 500;
}

/* Pagination Styles */
.pagination-info {
  font-size: 14px;
  color: #666;
  margin-bottom: 8px;
}

.pagination-controls {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
}

.pagination-controls span {
  font-size: 14px;
  color: #0B2A44;
  font-weight: 500;
  min-width: 100px;
  text-align: center;
}

/* Responsive Design */
@media (max-width: 600px) {
  .upload-view {
    padding: 0 16px;
  }
  
  .drop-zone {
    padding: 16px;
  }
  
  .upload-title {
    font-size: 16px;
  }
}
</style>