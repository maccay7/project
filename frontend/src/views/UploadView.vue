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

      <!-- File List -->
      <v-card class="stats-card" elevation="2" v-if="uploadedFiles.length > 0">
        <v-card-title class="card-title">
          <v-icon class="title-icon">mdi-file-multiple</v-icon>
          Uploaded Files
        </v-card-title>
        <v-card-text>
          <v-list>
            <v-list-item
              v-for="(file, index) in uploadedFiles"
              :key="index"
              class="file-item"
            >
              <template #prepend>
                <v-icon :color="getFileIcon(file.type).color">
                  {{ getFileIcon(file.type).icon }}
                </v-icon>
              </template>
              <v-list-item-title>{{ file.name }}</v-list-item-title>
              <v-list-item-subtitle>{{ formatFileSize(file.size) }}</v-list-item-subtitle>
              <template #append>
                <v-btn
                  icon
                  variant="text"
                  color="error"
                  @click="removeFile(index)"
                >
                  <v-icon>mdi-delete</v-icon>
                </v-btn>
              </template>
            </v-list-item>
          </v-list>
        </v-card-text>
      </v-card>

      <!-- Data Preview -->
      <v-card class="stats-card" elevation="2" v-if="previewData.length > 0">
        <v-card-title class="card-title">
          <v-icon class="title-icon">mdi-eye</v-icon>
          Data Preview
        </v-card-title>
        <v-card-text>
          <v-alert type="info" variant="tonal" class="mb-4">
            <v-icon left>mdi-information</v-icon>
            Showing first 10 rows of uploaded data. Full dataset will be processed in calculations.
          </v-alert>
          
          <v-data-table
            :headers="previewHeaders"
            :items="previewData"
            :loading="previewLoading"
            density="compact"
            class="preview-table"
            items-per-page="10"
            hide-default-footer
          >
            <template v-slot:bottom>
              <div class="text-center pa-4">
                <v-btn
                  variant="outlined"
                  color="primary"
                  @click="loadFullPreview"
                  :loading="previewLoading"
                >
                  <v-icon left>mdi-refresh</v-icon>
                  Load More Data
                </v-btn>
              </div>
            </template>
          </v-data-table>

          <div class="preview-stats" v-if="previewData.length > 0">
            <v-row>
              <v-col cols="12" sm="6" md="3">
                <div class="stat-item">
                  <div class="stat-value">{{ totalRows }}</div>
                  <div class="stat-label">Total Rows</div>
                </div>
              </v-col>
              <v-col cols="12" sm="6" md="3">
                <div class="stat-item">
                  <div class="stat-value">{{ totalColumns }}</div>
                  <div class="stat-label">Total Columns</div>
                </div>
              </v-col>
              <v-col cols="12" sm="6" md="3">
                <div class="stat-item">
                  <div class="stat-value">{{ fileTypes.length }}</div>
                  <div class="stat-label">File Types</div>
                </div>
              </v-col>
              <v-col cols="12" sm="6" md="3">
                <div class="stat-item">
                  <div class="stat-value">{{ formatFileSize(totalSize) }}</div>
                  <div class="stat-label">Total Size</div>
                </div>
              </v-col>
            </v-row>
          </div>
        </v-card-text>
      </v-card>

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
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const fileInput = ref()
const isDragOver = ref(false)
const uploadedFiles = ref<File[]>([])

// Preview data state
const previewData = ref<any[]>([])
const previewHeaders = ref<any[]>([])
const previewLoading = ref(false)

// Computed properties for stats
const totalRows = computed(() => previewData.value.length)
const totalColumns = computed(() => previewHeaders.value.length)
const fileTypes = computed(() => [...new Set(uploadedFiles.value.map(f => getFileIcon(f.type).icon))])
const totalSize = computed(() => uploadedFiles.value.reduce((acc, file) => acc + file.size, 0))

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
  try {
    if (uploadedFiles.value.length > 0) {
      const result = await processFile(uploadedFiles.value[0])
      previewData.value = result.data
      previewHeaders.value = result.headers.map(h => ({ title: h, key: h, sortable: true }))
    }
  } catch (error) {
    console.error('Error loading preview:', error)
  } finally {
    previewLoading.value = false
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
