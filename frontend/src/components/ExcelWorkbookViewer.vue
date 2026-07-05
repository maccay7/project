<template>
  <div class="excel-workbook-viewer">
    <div class="excel-toolbar">
      <div class="excel-toolbar-left">
        <span class="excel-filename">{{ fileName || 'Workbook' }}</span>
      </div>
      <div class="excel-toolbar-right">
        <button class="excel-toolbar-btn select-sheet-btn" @click="selectCurrentSheet" title="Select This Worksheet">
          <v-icon>mdi-check</v-icon>
          Select This Worksheet
        </button>
        <button class="excel-toolbar-btn" @click="closeViewer" title="Close">
          <v-icon>mdi-close</v-icon>
        </button>
      </div>
    </div>

    <div class="excel-formula-bar">
      <div class="formula-bar-label">fx</div>
      <div class="formula-bar-input">{{ selectedCellFormula || selectedCellValue }}</div>
    </div>

    <div class="excel-grid-container">
      <div class="excel-column-headers">
        <div class="excel-header-cell excel-corner-cell"></div>
        <div 
          v-for="(col, index) in columnHeaders" 
          :key="index"
          class="excel-header-cell excel-column-header"
          :style="{ width: getColumnWidth(index) }"
        >
          {{ col }}
        </div>
      </div>

      <div class="excel-row-headers">
        <div 
          v-for="(row, rowIndex) in visibleRows" 
          :key="rowIndex"
          class="excel-header-cell excel-row-header"
          :style="{ height: getRowHeight(rowIndex) }"
        >
          {{ rowIndex + 1 }}
        </div>
      </div>

      <div class="excel-cells" ref="cellsContainer">
        <div 
          v-for="(row, rowIndex) in visibleRows" 
          :key="rowIndex"
          class="excel-row"
          :style="{ height: getRowHeight(rowIndex) }"
        >
          <div 
            v-for="(cell, colIndex) in row" 
            :key="colIndex"
            class="excel-cell"
            :class="{ 'excel-cell-selected': selectedCell.row === rowIndex && selectedCell.col === colIndex }"
            :style="{ 
              width: getColumnWidth(colIndex),
              textAlign: getCellAlignment(cell),
              backgroundColor: getCellBackgroundColor(cell),
              color: getCellColor(cell),
              fontWeight: getCellFontWeight(cell)
            }"
            @click="selectCell(rowIndex, colIndex, cell)"
            @dblclick="editCell(rowIndex, colIndex, cell)"
          >
            {{ formatCellValue(cell) }}
          </div>
        </div>
      </div>
    </div>

    <div class="excel-sheet-tabs">
      <div 
        v-for="(sheet, index) in sheets" 
        :key="index"
        class="excel-sheet-tab"
        :class="{ 'excel-sheet-tab-active': activeSheetIndex === index }"
        @click="switchSheet(index)"
      >
        <v-icon size="16" class="sheet-icon">mdi-table</v-icon>
        {{ sheet.name }}
        <span v-if="sheet.total_rows" class="sheet-row-count">({{ sheet.total_rows }} rows)</span>
      </div>
    </div>

    <div class="excel-scrollbar-horizontal" ref="horizontalScrollbar">
      <div class="excel-scrollbar-thumb" :style="{ width: horizontalScrollPercent + '%' }"></div>
    </div>

    <div class="excel-scrollbar-vertical" ref="verticalScrollbar">
      <div class="excel-scrollbar-thumb" :style="{ height: verticalScrollPercent + '%' }"></div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'

const props = defineProps({
  workbookData: {
    type: Object,
    required: true
  },
  fileName: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['close', 'selectSheet'])

const sheets = ref([])
const activeSheetIndex = ref(0)
const visibleRows = ref([])
const columnHeaders = ref([])
const selectedCell = ref({ row: -1, col: -1 })
const selectedCellValue = ref('')
const selectedCellFormula = ref('')
const cellsContainer = ref(null)
const horizontalScrollbar = ref(null)
const verticalScrollbar = ref(null)
const horizontalScrollPercent = ref(0)
const verticalScrollPercent = ref(0)

const activeSheet = computed(() => sheets.value[activeSheetIndex.value] || null)

function getColumnHeaders(count) {
  const headers = []
  for (let i = 0; i < count; i++) {
    let header = ''
    let num = i + 1
    while (num > 0) {
      const remainder = (num - 1) % 26
      header = String.fromCharCode(65 + remainder) + header
      num = Math.floor((num - 1) / 26)
    }
    headers.push(header)
  }
  return headers
}

function getColumnWidth(index) {
  const defaultWidth = 100
  const widths = [120, 150, 100, 100, 100, 120, 100, 100, 100, 100]
  return (widths[index % widths.length] || defaultWidth) + 'px'
}

function getRowHeight(index) {
  return '25px'
}

function formatCellValue(cell) {
  if (cell === null || cell === undefined) return ''
  if (typeof cell === 'number') {
    if (cell % 1 !== 0) return cell.toFixed(2)
    return cell.toString()
  }
  return String(cell)
}

function getCellAlignment(cell) {
  if (typeof cell === 'number') return 'right'
  return 'left'
}

function getCellBackgroundColor(cell) {
  return 'transparent'
}

function getCellColor(cell) {
  return '#000'
}

function getCellFontWeight(cell) {
  return 'normal'
}

function selectCell(rowIndex, colIndex, cell) {
  selectedCell.value = { row: rowIndex, col: colIndex }
  selectedCellValue.value = formatCellValue(cell)
  selectedCellFormula.value = ''
}

function editCell(rowIndex, colIndex, cell) {
  // Read-only viewer - no editing
}

function switchSheet(index) {
  activeSheetIndex.value = index
  loadSheetData()
}

function selectCurrentSheet() {
  if (activeSheet.value) {
    emit('selectSheet', {
      sheetIndex: activeSheetIndex.value,
      sheetName: activeSheet.value.name,
      data: activeSheet.value.data,
      headers: activeSheet.value.headers
    })
  }
}

function loadSheetData() {
  if (!activeSheet.value) return
  
  const sheet = activeSheet.value
  const data = sheet.data || []
  const headers = sheet.headers || []
  
  visibleRows.value = data.slice(0, 30) // Show first 30 rows for performance
  columnHeaders.value = getColumnHeaders(Math.max(headers.length, 10))
}

function closeViewer() {
  emit('close')
}

onMounted(() => {
  if (props.workbookData && props.workbookData.sheets) {
    sheets.value = props.workbookData.sheets
    loadSheetData()
  }
})
</script>

<style scoped>
.excel-workbook-viewer {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #fff;
  border: 1px solid #e0e0e0;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  font-size: 13px;
}

.excel-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: linear-gradient(180deg, #f5f5f5 0%, #e8e8e8 100%);
  border-bottom: 1px solid #d0d0d0;
}

.excel-toolbar-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.excel-filename {
  font-weight: 600;
  color: #333;
}

.excel-toolbar-right {
  display: flex;
  gap: 4px;
}

.excel-toolbar-btn {
  padding: 6px 12px;
  border: 1px solid #c0c0c0;
  background: linear-gradient(180deg, #fff 0%, #f0f0f0 100%);
  border-radius: 3px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 4px;
  color: #333;
  font-size: 12px;
}

.excel-toolbar-btn:hover {
  background: linear-gradient(180deg, #f0f0f0 0%, #e0e0e0 100%);
}

.select-sheet-btn {
  background: #0B2044;
  color: white;
  border-color: #0B2044;
}

.select-sheet-btn:hover {
  background: #1a3a6e;
}

.excel-formula-bar {
  display: flex;
  align-items: center;
  padding: 4px 8px;
  background: #fff;
  border-bottom: 1px solid #d0d0d0;
  gap: 8px;
}

.formula-bar-label {
  width: 24px;
  height: 24px;
  background: linear-gradient(180deg, #f5f5f5 0%, #e8e8e8 100%);
  border: 1px solid #c0c0c0;
  border-radius: 3px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-style: italic;
  font-weight: bold;
  color: #666;
  font-size: 12px;
}

.formula-bar-input {
  flex: 1;
  padding: 4px 8px;
  border: 1px solid #c0c0c0;
  border-radius: 2px;
  background: #fff;
  color: #333;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 12px;
}

.excel-grid-container {
  flex: 1;
  display: grid;
  grid-template-columns: 40px 1fr;
  grid-template-rows: 25px 1fr;
  overflow: hidden;
  position: relative;
}

.excel-column-headers {
  grid-column: 2;
  grid-row: 1;
  display: flex;
  background: linear-gradient(180deg, #f5f5f5 0%, #e8e8e8 100%);
  border-bottom: 1px solid #d0d0d0;
  overflow: hidden;
}

.excel-row-headers {
  grid-column: 1;
  grid-row: 2;
  background: linear-gradient(180deg, #f5f5f5 0%, #e8e8e8 100%);
  border-right: 1px solid #d0d0d0;
  overflow: hidden;
}

.excel-cells {
  grid-column: 2;
  grid-row: 2;
  overflow: auto;
  background: #fff;
}

.excel-header-cell {
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #c0c0c0;
  background: linear-gradient(180deg, #f5f5f5 0%, #e8e8e8 100%);
  font-weight: 600;
  color: #333;
  font-size: 11px;
  user-select: none;
}

.excel-corner-cell {
  grid-column: 1;
  grid-row: 1;
  background: linear-gradient(180deg, #f5f5f5 0%, #e8e8e8 100%);
  border: 1px solid #d0d0d0;
}

.excel-column-header {
  flex-shrink: 0;
  border-right: 1px solid #c0c0c0;
}

.excel-row-header {
  border-bottom: 1px solid #c0c0c0;
}

.excel-row {
  display: flex;
  border-bottom: 1px solid #e0e0e0;
}

.excel-cell {
  flex-shrink: 0;
  border-right: 1px solid #e0e0e0;
  padding: 2px 4px;
  cursor: cell;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 12px;
}

.excel-cell-selected {
  outline: 2px solid #0B2044;
  outline-offset: -2px;
  background: #e8f0fe !important;
}

.excel-sheet-tabs {
  display: flex;
  padding: 4px 8px;
  background: linear-gradient(180deg, #f5f5f5 0%, #e8e8e8 100%);
  border-top: 1px solid #d0d0d0;
  gap: 2px;
  overflow-x: auto;
}

.excel-sheet-tab {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 12px;
  background: #e0e0e0;
  border: 1px solid #c0c0c0;
  border-radius: 3px 3px 0 0;
  cursor: pointer;
  color: #333;
  font-size: 12px;
  white-space: nowrap;
}

.excel-sheet-tab:hover {
  background: #d0d0d0;
}

.excel-sheet-tab-active {
  background: #fff;
  border-bottom: 1px solid #fff;
  margin-bottom: -1px;
}

.sheet-icon {
  color: #666;
}

.sheet-row-count {
  color: #999;
  font-size: 10px;
  margin-left: 4px;
}

.excel-scrollbar-horizontal {
  position: absolute;
  bottom: 35px;
  left: 40px;
  right: 0;
  height: 12px;
  background: #f0f0f0;
  border: 1px solid #c0c0c0;
}

.excel-scrollbar-vertical {
  position: absolute;
  top: 25px;
  right: 0;
  bottom: 35px;
  width: 12px;
  background: #f0f0f0;
  border: 1px solid #c0c0c0;
}

.excel-scrollbar-thumb {
  background: linear-gradient(180deg, #a0a0a0 0%, #808080 100%);
  border-radius: 2px;
}
</style>
