<template>
  <fixed-layout>
    <div class="upload-view">
      <!-- Header Section -->
      <div class="dashboard-header">
        <h1 class="page-title">Upload Dataset</h1>
        <p class="page-subtitle">Upload financial data for analysis and calculations</p>
      </div>

      <!-- Upload Area -->
      <v-card class="stats-card" elevation="2">
        <v-card-title class="card-title">
          <v-icon class="title-icon">mdi-upload</v-icon>
          Data Upload
        </v-card-title>
        <v-card-text>
          <v-row>
            <v-col cols="12">
              <div class="upload-area">
                <v-card
                  class="drop-zone"
                  :class="{ 'drag-over': isDragOver }"
                  @dragover.prevent="isDragOver = true"
                  @dragleave.prevent="isDragOver = false"
                  @drop.prevent="handleDrop"
                  @click="triggerFileInput"
                >
                  <v-card-text class="text-center pa-8">
                    <v-icon size="64" color="#0B2A44" class="mb-4">mdi-cloud-upload</v-icon>
                    <h3 class="upload-title">Drop files here or click to browse</h3>
                    <p class="upload-desc">Support for CSV, Excel, and JSON files</p>
                    <v-btn color="primary" variant="outlined" class="mt-4">
                      <v-icon left>mdi-folder-open</v-icon>
                      Choose Files
                    </v-btn>
                  </v-card-text>
                </v-card>
                <input
                  ref="fileInput"
                  type="file"
                  accept=".csv,.xlsx,.xls,.json"
                  multiple
                  @change="handleFileSelect"
                  style="display: none"
                />
              </div>
            </v-col>
          </v-row>
        </v-card-text>
      </v-card>

      <!-- Saved Datasets -->
      <v-card class="stats-card" elevation="2">
        <v-card-title class="card-title">
          <v-icon class="title-icon">mdi-database</v-icon>
          Saved Datasets
        </v-card-title>
        <v-card-text>
          <v-list v-if="savedDatasets.length > 0">
            <v-list-item
              v-for="(dataset, index) in savedDatasets"
              :key="index"
              class="dataset-item"
            >
              <template #prepend>
                <v-icon color="#0B2A44">
                  mdi-file-excel
                </v-icon>
              </template>
              <v-list-item-title>{{ dataset.name }}</v-list-item-title>
              <v-list-item-subtitle>
                {{ dataset.rows }} rows, {{ dataset.columns }} columns • Saved: {{ new Date(dataset.timestamp).toLocaleDateString() }}
              </v-list-item-subtitle>
              <template #append>
                <v-btn
                  size="small"
                  color="primary"
                  variant="text"
                  @click="loadSavedDataset(index)"
                >
                  <v-icon left size="small">mdi-folder-open</v-icon>
                  Load
                </v-btn>
                <v-btn
                  size="small"
                  color="error"
                  variant="text"
                  @click="deleteSavedDataset(index)"
                >
                  <v-icon left size="small">mdi-delete</v-icon>
                  Delete
                </v-btn>
              </template>
            </v-list-item>
          </v-list>
          <v-alert v-else type="info" variant="tonal">
            No saved datasets yet. Upload a file and save it to access it later.
          </v-alert>
        </v-card-text>
      </v-card>

      <!-- Excel Preview Toggle Button -->
      <v-card class="stats-card" elevation="2" v-if="uploadedFiles.length > 0">
        <v-card-text class="pa-4">
          <v-btn
            color="success"
            size="large"
            block
            @click="loadAndShowExcel"
            :loading="previewLoading"
          >
            <v-icon left size="large">mdi-microsoft-excel</v-icon>
            Load Data to Excel
          </v-btn>
          <v-btn
            v-if="showExcelPreview"
            color="info"
            size="small"
            block
            class="mt-2"
            @click="promptSaveDataset"
          >
            <v-icon left size="small">mdi-content-save</v-icon>
            Save Dataset
          </v-btn>
          <v-btn
            v-if="showExcelPreview"
            color="warning"
            size="small"
            block
            class="mt-2"
            @click="showExcelPreview = false"
          >
            <v-icon left size="small">mdi-eye-off</v-icon>
            Hide Excel Preview
          </v-btn>
        </v-card-text>
      </v-card>

      <!-- Data Preview -->
      <ExcelGrid
        v-if="showExcelPreview"
        :headers="previewHeaders.map(h => typeof h === 'object' ? h.key : h)"
        :data="fullDataset"
        @data-update="handleDataUpdate"
      />

      <!-- Quick Actions -->
      <v-card class="stats-card" elevation="2">
        <v-card-title class="card-title">
          <v-icon class="title-icon">mdi-lightning-bolt</v-icon>
          Quick Actions
        </v-card-title>
        <v-card-text>
          <v-row>
            <v-col cols="12" sm="6" md="3">
              <v-card class="action-item" hover @click="navigateTo('/calculations')">
                <v-card-text class="text-center pa-4">
                  <v-icon color="#0B2A44" size="32" class="mb-2">mdi-calculator</v-icon>
                  <div class="action-title">Calculate Yields</div>
                  <div class="action-desc">Process uploaded data</div>
                </v-card-text>
              </v-card>
            </v-col>
            <v-col cols="12" sm="6" md="3">
              <v-card class="action-item" hover @click="navigateTo('/cleaning')">
                <v-card-text class="text-center pa-4">
                  <v-icon color="#1E88E5" size="32" class="mb-2">mdi-broom</v-icon>
                  <div class="action-title">Clean Data</div>
                  <div class="action-desc">Remove duplicates</div>
                </v-card-text>
              </v-card>
            </v-col>
            <v-col cols="12" sm="6" md="3">
              <v-card class="action-item" hover @click="navigateTo('/visualizations')">
                <v-card-text class="text-center pa-4">
                  <v-icon color="#4CAF50" size="32" class="mb-2">mdi-chart-line</v-icon>
                  <div class="action-title">Visualize</div>
                  <div class="action-desc">Create charts</div>
                </v-card-text>
              </v-card>
            </v-col>
            <v-col cols="12" sm="6" md="3">
              <v-card class="action-item" hover @click="navigateTo('/reports')">
                <v-card-text class="text-center pa-4">
                  <v-icon color="#FFC107" size="32" class="mb-2">mdi-file-document</v-icon>
                  <div class="action-title">Generate Report</div>
                  <div class="action-desc">Export results</div>
                </v-card-text>
              </v-card>
            </v-col>
          </v-row>
        </v-card-text>
      </v-card>
    </div>
  </fixed-layout>
</template>

<script setup lang="ts">
import FixedLayout from '../components/FixedLayout.vue'
import ExcelGrid from '../components/ExcelGrid.vue'
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { dataAPI } from '../services/api'

const router = useRouter()
const fileInput = ref()
const isDragOver = ref(false)
const uploadedFiles = ref<File[]>([])

// Saved datasets state
const savedDatasets = ref<Array<{ name: string; rows: number; columns: number; timestamp: string; data: any[]; headers: string[] }>>([])

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
  if (fullDataset.value.length === 0) {
    alert('No data to save. Please upload a file first.')
    return
  }

  const dataset = {
    name,
    rows: fullDataset.value.length,
    columns: previewHeaders.value.length,
    timestamp: new Date().toISOString(),
    data: fullDataset.value,
    headers: previewHeaders.value.map((h: any) => typeof h === 'object' ? h.key : h)
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
  fullDataset.value = dataset.data
  previewHeaders.value = dataset.headers.map((h: string) => ({ title: h, key: h, sortable: true }))
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
    currentPage.value = 1
    
    // Upload and preview the selected file
    const file = uploadedFiles.value[index]
    console.log('Selected file:', file)
    
    const response = await dataAPI.upload(file, 'treasury_bills')
    console.log('API response:', response)
    
    if (response.success) {
      console.log('Upload successful, processing data...')
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
      
      // Save to multiple localStorage keys for persistence across pages
      localStorage.setItem('uploadedDataset', JSON.stringify(datasetToSave))
      localStorage.setItem('currentDataset', JSON.stringify(datasetToSave)) // For other pages
      localStorage.setItem('datasetStatus', 'uploaded') // Status indicator
      localStorage.setItem('datasetInfo', JSON.stringify({
        name: response.data.name,
        rows: response.data.data.length,
        columns: response.data.display_headers?.length || 0,
        instrumentType: response.data.instrument_type,
        uploadId: response.data.upload_id
      })) // Quick info for other pages
      
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