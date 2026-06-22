<template>
  <div class="excel-viewer">
    <div class="excel-toolbar">
      <span>{{ data.length }} rows × {{ displayHeaders.length }} columns</span>
      <div class="toolbar-right">
        <div v-if="showMappingControls" class="mapping-controls">
          <span class="mapping-label">Column mapping:</span>
          <select v-model="mappingMode" class="mapping-mode-select">
            <option value="original">Original Columns</option>
            <option value="mapped">Mapped Columns</option>
          </select>
        </div>
        <div class="pagination-controls">
          <button class="page-btn" @click="prevPage" :disabled="currentPage === 1">← Previous</button>
          <span class="page-info">Page {{ currentPage }} of {{ totalPages }}</span>
          <button class="page-btn" @click="nextPage" :disabled="currentPage === totalPages">Next →</button>
        </div>
      </div>
    </div>
    <div v-if="validationError" class="validation-banner">{{ validationError }}</div>
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
                :class="{ 'cell-invalid': isCellInvalid(row, col) }"
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
import { validateCellValue } from '@/utils/instrumentMapping.js'

const props = defineProps({
  data: { type: Array, required: true },
  headers: { type: Array, required: true },
  originalData: { type: Array, default: null },
  originalHeaders: { type: Array, default: null },
  showMappingControls: { type: Boolean, default: false },
  columnMapping: { type: Object, default: () => ({}) },
  availableFileColumns: { type: Array, default: () => [] },
  defaultMappedMode: { type: Boolean, default: false }
})

const emit = defineEmits(['data-update', 'mapping-update', 'validation-error'])

const pageSize = 15
const currentPage = ref(1)
const mappingMode = ref(props.defaultMappedMode ? 'mapped' : 'original')
const validationError = ref('')
const invalidCells = ref(new Set())

const sourceData = computed(() => props.originalData?.length ? props.originalData : props.data)
const sourceHeaders = computed(() => props.originalHeaders?.length ? props.originalHeaders : props.headers)

const totalPages = computed(() => Math.max(1, Math.ceil(props.data.length / pageSize)))

const paginatedData = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  return props.data.slice(start, start + pageSize)
})

const displayHeaders = computed(() => {
  if (!props.showMappingControls || mappingMode.value === 'original') {
    return sourceHeaders.value
  }
  return Object.entries(props.columnMapping)
    .filter(([, srcCol]) => srcCol && srcCol !== '__na__')
    .map(([reqCol]) => reqCol)
})

function getMappingForHeader(requiredCol) {
  return props.columnMapping[requiredCol] || '__na__'
}

function getCellValue(row, col) {
  if (!props.showMappingControls || mappingMode.value === 'original') {
    const srcRow = findSourceRow(row)
    return srcRow?.[col] !== undefined ? srcRow[col] : ''
  }
  const srcCol = props.columnMapping[col]
  if (!srcCol || srcCol === '__na__') return ''
  const srcRow = findSourceRow(row)
  return srcRow?.[srcCol] !== undefined ? srcRow[srcCol] : ''
}

function findSourceRow(row) {
  const idx = props.data.indexOf(row)
  if (idx >= 0 && sourceData.value[idx]) return sourceData.value[idx]
  return row
}

function isCellInvalid(row, col) {
  const idx = props.data.indexOf(row)
  const key = `${idx}-${col}`
  return invalidCells.value.has(key)
}

function updateCell(row, displayCol, rawValue) {
  const idx = props.data.indexOf(row)
  const srcRow = idx >= 0 && sourceData.value[idx] ? sourceData.value[idx] : row

  let targetCol = displayCol
  if (props.showMappingControls && mappingMode.value === 'mapped') {
    const srcCol = props.columnMapping[displayCol]
    if (!srcCol || srcCol === '__na__') return
    targetCol = srcCol
  }

  const colForValidation = mappingMode.value === 'mapped' ? displayCol : displayCol
  const result = validateCellValue(colForValidation, rawValue)
  const key = `${idx}-${displayCol}`

  if (!result.valid) {
    invalidCells.value.add(key)
    validationError.value = result.error
    emit('validation-error', result.error)
    srcRow[targetCol] = rawValue
  } else {
    invalidCells.value.delete(key)
    if (invalidCells.value.size === 0) validationError.value = ''
    srcRow[targetCol] = result.value
  }

  if (idx >= 0 && props.data[idx] !== srcRow) {
    if (mappingMode.value === 'original') {
      props.data[idx][targetCol] = srcRow[targetCol]
    }
  }

  emit('data-update', props.data, sourceData.value)
}

function onMappingChange(requiredCol, newSrcCol) {
  const newMapping = { ...props.columnMapping }
  newMapping[requiredCol] = newSrcCol === '__na__' ? null : newSrcCol
  emit('mapping-update', newMapping)
}

function prevPage() { if (currentPage.value > 1) currentPage.value-- }
function nextPage() { if (currentPage.value < totalPages.value) currentPage.value++ }

watch(() => props.data, () => { currentPage.value = 1; invalidCells.value.clear(); validationError.value = '' }, { deep: true })
watch(() => props.defaultMappedMode, (val) => { mappingMode.value = val ? 'mapped' : 'original' })
</script>

<style scoped>
.excel-viewer {
  border: 1px solid #ddd;
  border-radius: 8px;
  overflow: hidden;
  background: white;
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
.validation-banner {
  background: #fff3cd;
  color: #856404;
  padding: 8px 16px;
  font-size: 13px;
  border-bottom: 1px solid #ffc107;
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
  overflow-x: auto;
  max-height: 500px;
}
.excel-edit-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.excel-edit-table th,
.excel-edit-table td {
  border: 1px solid #ddd;
  padding: 6px 8px;
  text-align: left;
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
  border: none;
  padding: 4px;
  font-family: inherit;
  background: transparent;
}
.editable-cell:focus {
  outline: 1px solid #0B2044;
  background: #f8f9ff;
}
.cell-invalid {
  outline: 1px solid #dc3545;
  background: #fff5f5;
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
