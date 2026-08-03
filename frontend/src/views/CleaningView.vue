<template>
  <fixed-layout>
    <div class="cleaning-view">

      <!-- Header -->
      <div class="page-header">
        <h1>Data Cleaning</h1>
        <p>Clean and prepare your dataset for analysis</p>
      </div>

      <!-- Action Buttons -->
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

      <!-- Show only after dataset loaded -->
      <template v-if="dataset && dataset.data">

        <!-- KPI Cards -->
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

        <!-- Excel Viewer with Full Dataset -->
        <v-card class="stats-card">
          <v-card-title class="card-title">
            <v-icon class="title-icon">mdi-microsoft-excel</v-icon> Dataset Viewer (Editable)
          </v-card-title>
          <v-card-text>
            <div v-if="showDatasetPreview">
              <ExcelViewer
                :file-base64="dataset?.file_base64"
                :file-name="dataset?.name || ''"
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

        <!-- Cleaning Options -->
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
                </div>
                <v-progress-linear v-if="isCleaning" indeterminate color="#0B2A44" class="mt-3" />
                <v-btn color="#0B2A44" :disabled="!hasAnyOption" :loading="isCleaning" @click="startCleaning">
                  <v-icon left>mdi-broom</v-icon> Start Cleaning
                </v-btn>
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>

        <!-- Cleaned Dataset Preview using ExcelViewer -->
        <v-row v-if="results && results.cleanedData">
          <v-col cols="12">
            <v-card class="stats-card">
              <v-card-title class="card-title">
                <v-icon class="title-icon">mdi-table-check</v-icon> Cleaned Data Preview
                <v-spacer></v-spacer>
                <v-chip color="green" size="small">Changes Applied</v-chip>
              </v-card-title>
              <v-card-text>
                <!-- ===== CLEANING RESULTS KPI CARDS ===== -->
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

        <!-- Results Summary (fallback) -->
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

      <!-- No Data Message -->
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

const router = useRouter()
const route = useRoute()

// Data
const dataset = ref(null)
const originalDataset = ref(null)
const uploadId = ref(null)
const results = ref(null)
const isCleaning = ref(false)
const showDatasetPreview = ref(false)
const sheetNames = ref([])
const selectedSheet = ref('')

// Cleaning options
const cleaningOptions = ref([
  { key: 'removeDuplicates', label: 'Remove Duplicates', desc: 'Delete duplicate rows', value: true },
  { key: 'fillMissingValues', label: 'Fill Missing Values', desc: 'Replace empty values', value: true },
  { key: 'removeEmptyRows', label: 'Remove Empty Rows', desc: 'Delete rows with no data', value: true },
  { key: 'trimWhitespace', label: 'Trim Whitespace', desc: 'Remove extra spaces', value: true },
  { key: 'standardizeText', label: 'Standardize Text', desc: 'Fix text case', value: false },
  { key: 'formatDates', label: 'Format Dates', desc: 'Convert to YYYY-MM-DD', value: false },
  { key: 'standardizeCurrency', label: 'Standardize Currency', desc: 'Format currency values', value: false }
])

const hasAnyOption = computed(() => cleaningOptions.value.some(o => o.value))

// KPI Stats for Dataset Overview
const kpiStats = computed(() => {
  if (!dataset.value?.data) return []
  return [
    { title: 'Total Rows', value: dataset.value.data.length.toLocaleString(), icon: 'mdi-table-row', gradient: 'linear-gradient(135deg, #0B2044, #1a3a6e)' },
    { title: 'Total Columns', value: Object.keys(dataset.value.data[0] || {}).length, icon: 'mdi-view-column', gradient: 'linear-gradient(135deg, #1E88E5, #42a5f5)' },
    { title: 'Instrument Type', value: dataset.value.instrumentType || 'Financial Instruments', icon: 'mdi-chart-line', gradient: 'linear-gradient(135deg, #4CAF50, #2E7D32)' },
    { title: 'File Name', value: dataset.value.name || 'Dataset', icon: 'mdi-file-document', gradient: 'linear-gradient(135deg, #FFC107, #FF9800)' }
  ]
})

// ===== CLEANING RESULTS KPI STATS =====
const resultStats = computed(() => {
  if (!results.value) return []
  return [
    { title: 'Original Rows', value: results.value.originalRows, icon: 'mdi-table-row', gradient: 'linear-gradient(135deg, #0B2044, #1a3a6e)' },
    { title: 'Cleaned Rows', value: results.value.cleanedRows, icon: 'mdi-check-circle', gradient: 'linear-gradient(135deg, #4CAF50, #2E7D32)' },
    { title: 'Duplicates Removed', value: results.value.duplicatesRemoved || 0, icon: 'mdi-delete', gradient: 'linear-gradient(135deg, #F44336, #d32f2f)' },
    { title: 'Missing Values Filled', value: results.value.missingValuesFilled || 0, icon: 'mdi-pencil', gradient: 'linear-gradient(135deg, #FF9800, #F57C00)' }
  ]
})

// Load data from Upload page using dataset API
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
    uploadId.value = last.id
    sheetNames.value = last.headers || ['Sheet1']
    selectedSheet.value = sheetNames.value[0]
    results.value = null
    alert(`Loaded: ${last.name} (${dataset.value.data?.length || 0} rows)`)
    return
  } catch (err) {
    console.error(err)
    alert('Error loading dataset')
  }
}

// Toggle dataset preview
function toggleDatasetPreview() {
  showDatasetPreview.value = !showDatasetPreview.value
}

// Reset options
function resetOptions() {
  cleaningOptions.value.forEach(o => o.value = false)
  alert('Options reset')
}

// Clear results
function clearResults() {
  results.value = null
  if (originalDataset.value) dataset.value = JSON.parse(JSON.stringify(originalDataset.value))
  alert('Results cleared')
}

// Delete dataset
async function deleteData() {
  if (!uploadId.value) return alert('No dataset ID')
  if (confirm('Delete permanently?')) {
    await dataAPI.deleteDataset(uploadId.value)
    dataset.value = null
    originalDataset.value = null
    uploadId.value = null
    results.value = null
    alert('Dataset deleted')
  }
}

// Handle cleaned data update
function handleCleanedUpdate(newData) {
  if (results.value) {
    results.value.cleanedData = newData
    dataset.value.data = newData
  }
}

// Handle data update from Excel viewer
function handleDataUpdate(newData) {
  if (dataset.value) {
    dataset.value.data = newData
  }
}

// Start cleaning
async function startCleaning() {
  if (!dataset.value?.data) return alert('No data to clean')
  
  isCleaning.value = true
  try {
    const options = {}
    cleaningOptions.value.forEach(opt => { if (opt.value) options[opt.key] = true })
    
    const response = await dataAPI.clean(dataset.value.data, options)
    
    if (response.success) {
      results.value = {
        originalRows: dataset.value.data.length,
        cleanedRows: response.data.length,
        duplicatesRemoved: response.stats?.duplicates_removed || 0,
        missingValuesFilled: response.stats?.missing_values_filled || 0,
        cleanedData: response.data
      }
      dataset.value.data = response.data
      alert(`Cleaning completed! ${results.value.cleanedRows} rows remaining`)
    } else {
      alert('Cleaning failed')
    }
  } catch (err) {
    console.error(err)
    alert('Cleaning failed')
  } finally {
    isCleaning.value = false
  }
}

// Complete process
async function completeProcess() {
  if (!dataset.value || !results.value) return alert('No results to save')
  try {
    const name = dataset.value.name || `cleaned_${Date.now()}`
    const payload = {
      name,
      file_base64: dataset.value.file_base64 || '',
      sheet_names: sheetNames.value || [],
      upload_id: uploadId.value || null,
      data: dataset.value.data || [],
      headers: sheetNames.value || [],
      instrument_type: dataset.value.instrumentType || null
    }
    const res = await datasetAPI.save(payload.name, payload.file_base64, payload.sheet_names, payload.upload_id, payload.data, payload.headers, payload.instrument_type)
    if (res && res.success) {
      alert('Process completed! Cleaned data saved to datasets')
    } else {
      alert('Failed to save cleaned data')
    }
  } catch (err) {
    console.error(err)
    alert('Failed to save cleaned data')
  }
}

// Go to calculations
async function goToCalculations() {
  if (!results.value) return alert('Please clean data first')
  const datasetId = route.query.dataset_id
  if (!datasetId) return alert('Cannot proceed without dataset reference')
  try {
    const session = sessionManager.getActiveSession()
    const sid = session?.id || sessionManager.getActiveSessionId()
    if (sid) await markStepCompleted(String(sid), 'cleaning')
  } catch (e) { console.warn(e) }
  router.push({ name: 'calculations', query: { dataset_id: datasetId } })
}

onMounted(() => {
  if (route.query.dataset_id) {
    loadData()
  }
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
.result-item { display: flex; justify-content: space-between; padding: 12px; background: rgba(11,42,68,0.03); border-radius: 8px; margin-bottom: 8px; }
.result-item span:first-child { color: #666; font-weight: 500; }
.result-item span:last-child { color: #0B2A44; font-weight: 700; }
.result-actions { display: flex; gap: 12px; margin-top: 20px; }
@media (max-width: 600px) {
  .cleaning-view { padding: 0 16px; }
  .action-buttons { flex-direction: column; }
  .result-actions { flex-direction: column; }
}
</style>