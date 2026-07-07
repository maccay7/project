<template>
  <div class="worksheet-selector">
    <div class="selector-header">
      <h3>📑 Worksheets</h3>
      <div class="progress-info">
        <span>{{ completedSheets }}/{{ totalSheets }} completed</span>
        <div class="progress-bar">
          <div class="progress-fill" :style="{ width: `${progress}%` }"></div>
        </div>
      </div>
    </div>
    
    <div v-if="loading" class="loading-state">
      <v-icon size="32" class="spin">mdi-loading</v-icon>
      <p>Loading workbook...</p>
    </div>
    
    <div v-else-if="error" class="error-state">
      <v-icon color="error" size="32">mdi-alert-circle</v-icon>
      <p>{{ error }}</p>
    </div>
    
    <div v-else-if="!hasWorkbook" class="empty-state">
      <v-icon size="48" color="#ccc">mdi-file-excel-outline</v-icon>
      <p>No workbook loaded</p>
    </div>
    
    <div v-else class="worksheets-list">
      <div
        v-for="sheet in workbookSheets"
        :key="sheet.name"
        class="worksheet-item"
        :class="{
          'selected': selectedWorksheet?.name === sheet.name,
          'completed': worksheetStatus[sheet.name] === 'completed',
          'in-progress': worksheetStatus[sheet.name] === 'in_progress'
        }"
        @click="selectSheet(sheet.name)"
      >
        <div class="sheet-info">
          <div class="sheet-icon">
            <v-icon :color="getStatusColor(sheet.name)">
              {{ getStatusIcon(sheet.name) }}
            </v-icon>
          </div>
          <div class="sheet-details">
            <div class="sheet-name">{{ sheet.name }}</div>
            <div class="sheet-meta">
              {{ sheet.row_count }} rows · {{ sheet.column_count }} columns
            </div>
          </div>
        </div>
        <div class="sheet-status">
          <span class="status-badge" :class="worksheetStatus[sheet.name]">
            {{ getStatusText(sheet.name) }}
          </span>
        </div>
        <button
          v-if="worksheetStatus[sheet.name] !== 'completed'"
          class="btn-work-on-sheet"
          @click.stop="workOnSheet(sheet.name)"
          :disabled="worksheetStatus[sheet.name] === 'in-progress'"
        >
          <v-icon small>mdi-pencil</v-icon>
          Work on Sheet
        </button>
        <button
          v-else
          class="btn-view-results"
          @click.stop="viewResults(sheet.name)"
        >
          <v-icon small>mdi-eye</v-icon>
          View Results
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  workbookSheets: {
    type: Array,
    default: () => []
  },
  worksheetStatus: {
    type: Object,
    default: () => ({})
  },
  selectedWorksheet: {
    type: Object,
    default: null
  },
  loading: {
    type: Boolean,
    default: false
  },
  error: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['select-sheet', 'work-on-sheet', 'view-results'])

const hasWorkbook = computed(() => props.workbookSheets.length > 0)
const completedSheets = computed(() => 
  Object.values(props.worksheetStatus).filter(s => s === 'completed').length
)
const totalSheets = computed(() => props.workbookSheets.length)
const progress = computed(() => 
  totalSheets.value > 0 ? (completedSheets.value / totalSheets.value) * 100 : 0
)

function getStatusColor(sheetName) {
  const status = props.worksheetStatus[sheetName]
  switch (status) {
    case 'completed': return '#4CAF50'
    case 'in_progress': return '#2196F3'
    default: return '#999'
  }
}

function getStatusIcon(sheetName) {
  const status = props.worksheetStatus[sheetName]
  switch (status) {
    case 'completed': return 'mdi-check-circle'
    case 'in_progress': return 'mdi-clock-outline'
    default: return 'mdi-file-outline'
  }
}

function getStatusText(sheetName) {
  const status = props.worksheetStatus[sheetName]
  switch (status) {
    case 'completed': return 'Completed'
    case 'in_progress': return 'In Progress'
    default: return 'Not Started'
  }
}

function selectSheet(sheetName) {
  emit('select-sheet', sheetName)
}

function workOnSheet(sheetName) {
  emit('work-on-sheet', sheetName)
}

function viewResults(sheetName) {
  emit('view-results', sheetName)
}
</script>

<style scoped>
.worksheet-selector {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.selector-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 12px;
}

.selector-header h3 {
  margin: 0;
  color: #0B2044;
  font-size: 18px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.progress-info {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 13px;
  color: #666;
}

.progress-bar {
  width: 100px;
  height: 6px;
  background: #e0e0e0;
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #4CAF50, #2E7D32);
  transition: width 0.3s ease;
}

.loading-state,
.error-state,
.empty-state {
  text-align: center;
  padding: 40px 20px;
  color: #999;
}

.loading-state p,
.error-state p,
.empty-state p {
  margin: 12px 0 0;
  font-size: 14px;
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.worksheets-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 400px;
  overflow-y: auto;
}

.worksheet-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: #f8f9ff;
  border: 2px solid transparent;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  flex-wrap: wrap;
  gap: 12px;
}

.worksheet-item:hover {
  border-color: #0B2044;
  background: #eef2ff;
  transform: translateY(-1px);
}

.worksheet-item.selected {
  border-color: #0B2044;
  background: #e8ecf1;
}

.worksheet-item.completed {
  border-color: #4CAF50;
  background: #e8f5e9;
}

.worksheet-item.in-progress {
  border-color: #2196F3;
  background: #e3f2fd;
}

.sheet-info {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  min-width: 200px;
}

.sheet-icon {
  flex-shrink: 0;
}

.sheet-details {
  flex: 1;
}

.sheet-name {
  font-weight: 600;
  color: #0B2044;
  font-size: 14px;
}

.sheet-meta {
  font-size: 12px;
  color: #666;
  margin-top: 2px;
}

.sheet-status {
  flex-shrink: 0;
}

.status-badge {
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
}

.status-badge.completed {
  background: #4CAF50;
  color: white;
}

.status-badge.in-progress {
  background: #2196F3;
  color: white;
}

.status-badge.not_started {
  background: #e0e0e0;
  color: #666;
}

.btn-work-on-sheet,
.btn-view-results {
  flex-shrink: 0;
  padding: 6px 12px;
  border: none;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  transition: all 0.2s;
}

.btn-work-on-sheet {
  background: #0B2044;
  color: white;
}

.btn-work-on-sheet:hover:not(:disabled) {
  background: #1a3a6e;
  transform: translateY(-1px);
}

.btn-work-on-sheet:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-view-results {
  background: #4CAF50;
  color: white;
}

.btn-view-results:hover {
  background: #45a049;
  transform: translateY(-1px);
}
</style>
