<template>
  <div class="excel-viewer">
    <div class="excel-toolbar">
      <span>{{ data.length }} rows × {{ displayHeaders.length }} columns</span>
      <div class="toolbar-right">
        <div v-if="showMappingControls" class="mapping-controls">
          <span class="mapping-label">Column mapping:</span>
          <select v-model="mappingMode" class="mapping-mode-select">
            <option value="original">Show original columns</option>
            <option value="mapped">Show mapped columns</option>
          </select>
        </div>
        <div class="pagination-controls">
          <button class="page-btn" @click="prevPage" :disabled="currentPage === 1">← Previous</button>
          <span class="page-info">Page {{ currentPage }} of {{ totalPages }}</span>
          <button class="page-btn" @click="nextPage" :disabled="currentPage === totalPages">Next →</button>
        </div>
      </div>
    </div>
    <div class="excel-table-wrapper">
      <table class="excel-edit-table">
        <thead>
          <tr>
            <th class="row-number-col">#</th>
            <th v-for="(col, idx) in displayHeaders" :key="idx">
              <div v-if="showMappingControls && mappingMode === 'mapped'" class="header-dropdown">
                <select
                  :value="getMappingForHeader(col)"
                  @change="onMappingChange(col, $event.target.value)"
                  class="mapping-dropdown"
                >
                  <option value="__na__">— N/A (hide column) —</option>
                  <option v-for="fileCol in availableFileColumns" :key="fileCol" :value="fileCol">
                    {{ fileCol }}
                  </option>
                </select>
                <span class="header-label">{{ col }}</span>
              </div>
              <span v-else>{{ col }}</span>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, idx) in paginatedData" :key="idx">
            <td class="row-number">{{ (currentPage - 1) * pageSize + idx + 1 }}</td>
            <td v-for="col in displayHeaders" :key="col">
              <input
                type="text"
                :value="getCellValue(row, col)"
                @input="updateCell(row, col, $event.target.value)"
                class="editable-cell"
              />
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  data: { type: Array, required: true },
  headers: { type: Array, required: true },
  showMappingControls: { type: Boolean, default: false },
  columnMapping: { type: Object, default: () => ({}) },
  availableFileColumns: { type: Array, default: () => [] },
  defaultMappedMode: { type: Boolean, default: false }
})

const emit = defineEmits(['data-update', 'mapping-update'])

const pageSize = 15
const currentPage = ref(1)
const mappingMode = ref(props.defaultMappedMode ? 'mapped' : 'original')

watch(() => props.defaultMappedMode, (newVal) => {
  if (newVal && mappingMode.value !== 'mapped') {
    mappingMode.value = 'mapped'
  }
})

const totalPages = computed(() => Math.ceil(props.data.length / pageSize))

const paginatedData = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  const end = start + pageSize
  return props.data.slice(start, end)
})

const displayHeaders = computed(() => {
  if (!props.showMappingControls || mappingMode.value === 'original') {
    return props.headers
  } else {
    return Object.entries(props.columnMapping)
      .filter(([reqCol, srcCol]) => srcCol && srcCol !== '__na__')
      .map(([reqCol]) => reqCol)
  }
})

function getMappingForHeader(requiredCol) {
  return props.columnMapping[requiredCol] || null
}

function getCellValue(row, col) {
  if (!props.showMappingControls || mappingMode.value === 'original') {
    return row[col] !== undefined ? row[col] : ''
  } else {
    const srcCol = props.columnMapping[col]
    if (!srcCol || srcCol === '__na__') return ''
    return row[srcCol] !== undefined ? row[srcCol] : ''
  }
}

function updateCell(row, displayCol, newValue) {
  if (!props.showMappingControls || mappingMode.value === 'original') {
    row[displayCol] = newValue
  } else {
    const srcCol = props.columnMapping[displayCol]
    if (srcCol && srcCol !== '__na__') {
      row[srcCol] = newValue
    }
  }
  emit('data-update', props.data)
}

function onMappingChange(requiredCol, newSrcCol) {
  const newMapping = { ...props.columnMapping }
  if (newSrcCol === '__na__') {
    newMapping[requiredCol] = null
  } else {
    newMapping[requiredCol] = newSrcCol
  }
  emit('mapping-update', newMapping)
}

function prevPage() { if (currentPage.value > 1) currentPage.value-- }
function nextPage() { if (currentPage.value < totalPages.value) currentPage.value++ }

watch(() => props.data, () => { currentPage.value = 1 }, { deep: true })
</script>

<style scoped>
.excel-viewer {
  border: 1px solid #ddd;
  border-radius: 8px;
  overflow: hidden;
  background: white;
  max-width: 100% !important;
}
.excel-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 16px;
  background: #f5f5f5;
  border-bottom: 1px solid #ddd;
  flex-wrap: wrap;
  gap: 12px;
}
.toolbar-right {
  display: flex;
  gap: 16px;
  align-items: center;
  flex-wrap: wrap;
}
.mapping-controls {
  display: flex;
  align-items: center;
  gap: 8px;
}
.mapping-label {
  font-size: 12px;
  color: #555;
}
.mapping-mode-select {
  padding: 4px 8px;
  border-radius: 6px;
  border: 1px solid #ccc;
  background: white;
  font-size: 12px;
}
.pagination-controls {
  display: flex;
  gap: 12px;
  align-items: center;
}
.page-btn {
  background: white;
  border: 1px solid #ccc;
  padding: 4px 12px;
  border-radius: 6px;
  cursor: pointer;
}
.page-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.page-info {
  font-size: 13px;
  color: #555;
}
.excel-table-wrapper {
  overflow-x: auto !important;
  max-height: 500px;
  max-width: 100% !important;
  width: 100% !important;
}
.excel-edit-table {
  max-width: 100% !important;
  table-layout: fixed !important;
  width: 100% !important;
  border-collapse: collapse;
  font-size: 13px;
}
.excel-edit-table th,
.excel-edit-table td {
  border: 1px solid #ddd;
  padding: 6px 8px;
  text-align: left;
  word-break: break-word;
  max-width: 200px; /* adjust as needed */
  overflow: hidden;
  text-overflow: ellipsis;
}
.excel-edit-table th {
  background: #f0f0f0;
  position: sticky;
  top: 0;
  z-index: 10;
}
.row-number-col {
  background: #f8f9ff;
  width: 50px;
  text-align: center;
}
.row-number {
  background: #f8f9ff;
  font-weight: 500;
  text-align: center;
}
.editable-cell {
  width: 100%;
  min-width: 60px;
  border: none;
  padding: 4px;
  font-family: inherit;
  background: transparent;
}
.editable-cell:focus {
  outline: 1px solid #0B2044;
  background: #f8f9ff;
}
.header-dropdown {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.mapping-dropdown {
  font-size: 11px;
  padding: 2px 4px;
  border-radius: 4px;
  border: 1px solid #ccc;
  background: white;
}
.header-label {
  font-weight: normal;
  font-size: 12px;
}
</style>