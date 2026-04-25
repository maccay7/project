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
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const fileInput = ref()
const isDragOver = ref(false)
const uploadedFiles = ref<File[]>([])

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

const addFiles = (files: File[]) => {
  uploadedFiles.value.push(...files.filter(file => 
    file.type.includes('csv') || 
    file.type.includes('sheet') || 
    file.type.includes('json') ||
    file.name.endsWith('.csv') ||
    file.name.endsWith('.xlsx') ||
    file.name.endsWith('.xls') ||
    file.name.endsWith('.json')
  ))
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
