<template>
  <FixedLayout>
    <div class="reports-page">
      <div class="page-header">
        <button class="back-btn" @click="goBack">
          <v-icon>mdi-arrow-left</v-icon> Back
        </button>
        <h1>Generate Report</h1>
        <p>Select report type and generate detailed analysis</p>
      </div>

      <div class="report-actions-row">
        <v-btn color="#0B2A44" @click="loadDatasetPreview">
          <v-icon left>mdi-eye</v-icon> Preview Dataset
        </v-btn>
        <v-btn color="#1E88E5" @click="generatePreview">
          <v-icon left>mdi-file-document-outline</v-icon> Refresh Report
        </v-btn>
        <v-btn color="#0B2A44" @click="markDone">
          <v-icon left>mdi-check-circle</v-icon> Done
        </v-btn>
      </div>

      <div class="report-options">
        <div class="option-card" @click="selectReportType('current')">
          <div class="option-icon" :class="{ active: selectedType === 'current' }">
            <v-icon size="32">mdi-chart-line</v-icon>
          </div>
          <h3>Current Instrument</h3>
          <p>Generate report for the currently selected instrument</p>
        </div>

        <div class="option-card" @click="selectReportType('session')">
          <div class="option-icon" :class="{ active: selectedType === 'session' }">
            <v-icon size="32">mdi-folder</v-icon>
          </div>
          <h3>Full Session</h3>
          <p>Generate report for all instruments in the session</p>
        </div>
      </div>

      <div class="dataset-preview" v-if="showDatasetPreview">
        <h3>Excel Dataset Preview</h3>
        <div class="dataset-info-row">
          <span><strong>Dataset:</strong> {{ dataset?.name || 'Not loaded' }}</span>
          <span><strong>Instrument:</strong> {{ dataset?.instrument_type || 'Unknown' }}</span>
        </div>
        <div class="preview-content" v-if="dataset && dataset.data && dataset.data.length">
          <ExcelViewer
            :data="dataset.data"
            :headers="Object.keys(dataset.data[0] || {})"
            @data-update="handleDatasetUpdate"
          />
        </div>
        <div v-else class="preview-empty">
          <p>No dataset loaded yet. Use Preview Dataset to load the latest upload.</p>
        </div>
      </div>

      <div class="preview-section" v-if="previewData">
        <h3>Report Preview</h3>
        <div class="preview-content">
          <pre>{{ JSON.stringify(previewData, null, 2) }}</pre>
        </div>
        <button class="btn-primary" @click="downloadReport">
          <v-icon>mdi-download</v-icon> Download Report
        </button>
      </div>
    </div>
  </FixedLayout>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import FixedLayout from '@/components/FixedLayout.vue'
import ExcelViewer from '@/components/ExcelViewer.vue'
import { datasetAPI } from '@/services/api'

const router = useRouter()
const route = useRoute()

const selectedType = ref('current')
const previewData = ref(null)
const dataset = ref(null)
const showDatasetPreview = ref(false)

function selectReportType(type) {
  selectedType.value = type
  generatePreview()
}

function generatePreview() {
  const reportType = localStorage.getItem('report_type') || selectedType.value
  const session = JSON.parse(localStorage.getItem('active_session') || '{}')

  if (reportType === 'current') {
    previewData.value = {
      type: 'Current Instrument Report',
      date: new Date().toLocaleString(),
      session: session.name || 'Current Session',
      instrument: route.query.instrument || dataset.value?.instrument_type || 'Selected Instrument',
      rows: dataset.value?.data?.length || 0,
      columns: dataset.value?.data ? Object.keys(dataset.value.data[0] || {}).length : 0,
      sample: dataset.value?.data?.slice(0, 3) || []
    }
  } else {
    previewData.value = {
      type: 'Full Session Report',
      date: new Date().toLocaleString(),
      session: session.name || 'Current Session',
      instruments: session.instrumentData || {},
      totalRows: dataset.value?.data?.length || 0,
      summary: dataset.value ? 'Loaded dataset ready for analysis' : 'No dataset loaded'
    }
  }
}

function downloadReport() {
  const blob = new Blob([JSON.stringify(previewData.value, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `report_${Date.now()}.json`
  a.click()
  URL.revokeObjectURL(url)
}

function handleDatasetUpdate(updatedData) {
  if (!dataset.value) return
  dataset.value.data = updatedData
}

async function loadDatasetPreview() {
  showDatasetPreview.value = true
  try {
    const current = JSON.parse(localStorage.getItem('currentDataset') || '{}')
    if (current.id) {
      const res = await datasetAPI.load(current.id)
      if (res && res.success) {
        dataset.value = res.data
        generatePreview()
        return
      }
    }
    if (current.data) {
      dataset.value = current
      generatePreview()
      return
    }
    const stored = JSON.parse(localStorage.getItem('cleanedData') || localStorage.getItem('currentDataset') || '{}')
    if (stored?.data) {
      dataset.value = stored
      generatePreview()
    }
  } catch (err) {
    console.error('Load dataset preview error', err)
  }
}

async function markDone() {
  try {
    const current = JSON.parse(localStorage.getItem('currentDataset') || '{}')
    const id = current.id
    if (!id) return alert('No current dataset selected')
    const res = await datasetAPI.markDone(id)
    if (res && res.success) {
      alert('Dataset marked done — it will no longer be available for processing')
    } else {
      alert('Failed to mark dataset')
    }
  } catch (err) { console.error(err); alert('Error marking dataset') }
}

function goBack() {
  router.back()
}

onMounted(() => {
  generatePreview()
})
</script>

<style scoped>
.reports-page {
  padding: 30px;
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 30px;
}

.back-btn {
  background: transparent;
  border: none;
  color: #0B2044;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border-radius: 8px;
  margin-bottom: 20px;
}

.page-header h1 {
  color: #0B2044;
  font-size: 28px;
  font-weight: 700;
}

.page-header p {
  color: #666;
  font-size: 14px;
}

.report-options {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 24px;
  margin-bottom: 40px;
}

.option-card {
  background: white;
  border-radius: 16px;
  padding: 30px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s;
  border: 2px solid transparent;
}

.option-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 8px 25px rgba(0,0,0,0.1);
  border-color: #0B2044;
}

.option-icon {
  width: 80px;
  height: 80px;
  background: #f5f5f5;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 20px;
  transition: all 0.3s;
}

.option-icon.active {
  background: #0B2044;
  color: white;
}

.option-card h3 {
  color: #0B2044;
  margin-bottom: 10px;
}

.option-card p {
  color: #666;
  font-size: 13px;
}

.preview-section {
  background: white;
  border-radius: 16px;
  padding: 24px;
}

.preview-section h3 {
  color: #0B2044;
  margin-bottom: 20px;
}

.preview-content {
  background: #f5f5f5;
  border-radius: 8px;
  padding: 20px;
  overflow-x: auto;
  margin-bottom: 20px;
}

.preview-content pre {
  margin: 0;
  font-size: 12px;
}

.btn-primary {
  background: linear-gradient(135deg, #0B2044, #1E88E5);
  color: white;
  border: none;
  padding: 12px 28px;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
</style>