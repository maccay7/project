<template>
  <div class="excel-workbook-viewer" :style="{ height: viewerHeight + 'px' }">
    <div class="resize-handle" @mousedown="startResize"></div>
    <div class="viewer-header">
      <div class="header-left">
        <img src="/DuraCapital logo.png" alt="DuraCapital" class="logo" />
        <span class="excel-filename">{{ fileName || 'Excel Workbook' }}</span>
      </div>
      <div class="view-mode-toggle">
        <button
          class="mode-btn"
          :class="{ active: viewMode === 'grid' }"
          @click="viewMode = 'grid'"
        >Table View</button>
        <button
          class="mode-btn"
          :class="{ active: viewMode === 'excel' }"
          @click="viewMode = 'excel'"
          :disabled="!datasetId"
          :title="!datasetId ? 'No dataset id available' : 'Show workbook as it appears in Excel'"
        >Excel View</button>
      </div>
      <div class="formula-bar" v-if="viewMode === 'grid'">
        <div class="formula-bar-label">fx</div>
        <input
          v-model="selectedCellFormula"
          class="formula-bar-input"
          placeholder="Formula or value"
          readonly
        />
      </div>
    </div>

    <!-- Excel View (LibreOffice-rendered HTML) -->
    <div v-if="viewMode === 'excel'" class="excel-view-wrapper">
      <div v-if="renderChecking" class="excel-view-empty">
        <v-icon size="32" class="spin-animation" color="#0B2044">mdi-loading</v-icon>
        <p>Rendering workbook via LibreOffice…</p>
      </div>
      <div v-else-if="renderError" class="excel-view-empty" style="color:#c62828;">
        <v-icon size="48" color="error">mdi-alert-circle-outline</v-icon>
        <p><strong>Could not render the workbook</strong></p>
        <p style="font-size:12px; white-space:pre-wrap; text-align:left; max-width:640px; font-family:monospace;">{{ renderError }}</p>
        <div style="display:flex; gap:8px; margin-top:12px;">
          <button class="mode-btn" @click="checkRender">Retry</button>
        </div>
      </div>
      <iframe
        v-else-if="datasetId && renderHtml"
        :srcdoc="renderHtml"
        class="excel-view-iframe"
        frameborder="0"
        sandbox="allow-same-origin allow-scripts"
        @load="renderChecking = false"
      ></iframe>
      <div v-else-if="datasetId" class="excel-view-empty">
        <v-icon size="48" color="#ccc">mdi-file-question-outline</v-icon>
        <p>The render endpoint returned no content.</p>
        <button class="mode-btn" @click="checkRender" style="margin-top:12px;">Retry</button>
      </div>
      <div v-else class="excel-view-empty">
        <v-icon size="48" color="#ccc">mdi-alert-circle-outline</v-icon>
        <p>No dataset id available — cannot render the original workbook.</p>
      </div>
    </div>

    <!-- Table View wrapper starts here -->
    <template v-if="viewMode === 'grid'">

    <div class="excel-grid-wrapper">
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
            <div class="column-resize-handle" @mousedown="startColumnResize(index, $event)"></div>
          </div>
        </div>

        <div class="excel-rows-container" ref="rowsContainer">
          <div
            v-for="(row, rowIndex) in visibleRows"
            :key="rowIndex"
            class="excel-row"
            :class="{
              'row-selected': isRowInRange(rowIndex),
              'row-selecting': isRowSelectionMode
            }"
            @click="handleRowClick(rowIndex)"
          >
            <div class="excel-header-cell excel-row-header" :style="{ height: getRowHeight(rowIndex) }">
              {{ rowIndex + 1 }}
              <div class="row-resize-handle" @mousedown.stop="startRowResize(rowIndex, $event)"></div>
            </div>
            <div class="excel-cells-container">
              <div
                v-for="(cell, colIndex) in row"
                :key="colIndex"
                class="excel-cell"
                :class="{
                  'excel-cell-selected': selectedCell.row === rowIndex && selectedCell.col === colIndex,
                }"
                :style="getCellStyle(rowIndex, colIndex)"
                :title="formatCellValue(cell)"
                @click="selectCell(rowIndex, colIndex, cell)"
                @dblclick="editCell(rowIndex, colIndex, cell)"
              >
                {{ formatCellValue(cell) }}
              </div>
            </div>
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
        <span v-if="worksheetStatuses[sheet.name] === 'saved'" class="sheet-status-badge saved">
          <v-icon size="12">mdi-check-circle</v-icon>
        </span>
      </div>
    </div>

    <div v-if="detectedTables.length > 0 && !isTableIsolationMode" class="table-detection-panel">
      <div class="table-detection-header">
        <v-icon size="16" class="table-icon">mdi-table-large</v-icon>
        <span>Detected Tables, Sections & Values ({{ detectedTables.length }})</span>
      </div>
      <div class="table-mode-toggle">
        <button
          class="mode-toggle-btn"
          :class="{ active: !isMultiTableMode }"
          @click="isMultiTableMode = false"
        >
          Single Table
        </button>
        <button
          class="mode-toggle-btn"
          :class="{ active: isMultiTableMode }"
          @click="isMultiTableMode = true"
        >
          Multi-Table Select
        </button>
      </div>
      <div class="table-buttons">
        <button
          v-for="(table, index) in detectedTables"
          :key="index"
          class="table-select-btn"
          :class="{
            'table-selected': isMultiTableMode && selectedTables.has(index),
            'table-isolated': !isMultiTableMode && selectedTable === table
          }"
          @click="isMultiTableMode ? toggleTableSelection(index, table) : selectTable(table)"
        >
          <span v-if="isMultiTableMode" class="table-checkbox">
            {{ selectedTables.has(index) ? '✓' : '○' }}
          </span>
          <v-icon v-if="table.type === 'table'" size="12" class="type-icon">mdi-table</v-icon>
          <v-icon v-else-if="table.type === 'section'" size="12" class="type-icon">mdi-text-box</v-icon>
          <v-icon v-else-if="table.type === 'vertical_table'" size="12" class="type-icon">mdi-format-vertical-align-center</v-icon>
          <v-icon v-else-if="table.type === 'values'" size="12" class="type-icon">mdi-chart-bar</v-icon>
          {{ table.name }} (Row {{ table.startRow + 1 }} - {{ table.endRow + 1 }})
        </button>
      </div>
      <div v-if="isMultiTableMode && selectedTables.size > 0" class="multi-table-actions">
        <button class="btn-auto-detect-multi" @click="autoDetectSelectedTables" :disabled="isDetecting">
          <v-icon v-if="!isDetecting" size="16">mdi-magnify</v-icon>
          <v-icon v-else size="16" class="spin-animation">mdi-loading</v-icon>
          {{ isDetecting ? 'Scanning...' : 'Auto Detect' }}
        </button>
        <button class="btn-clear-selection" @click="clearTableSelection">
          <v-icon size="16">mdi-close</v-icon>
          Clear Selection
        </button>
      </div>
    </div>

    <div v-if="isTableIsolationMode && selectedTable" class="table-isolation-header">
      <div class="isolation-info">
        <v-icon size="16" class="table-icon">mdi-table-large</v-icon>
        <span>Working on: {{ selectedTable.name }} (Row {{ selectedTable.startRow + 1 }} - {{ selectedTable.endRow + 1 }})</span>
      </div>
      <button class="exit-isolation-btn" @click="exitTableIsolation">
        <v-icon size="16">mdi-close</v-icon>
        Exit Table Mode
      </button>
    </div>

    <div v-if="isSingleInstrumentSheet && Object.keys(extractedPreviewValues).length > 0" class="single-instrument-preview">
      <div class="preview-header">
        <v-icon size="16" class="preview-icon">mdi-check-circle</v-icon>
        <span>Single Instrument Detected - Auto-Extracted Values</span>
      </div>
      <div class="preview-grid">
        <div
          v-for="(value, key) in extractedPreviewValues"
          :key="key"
          class="preview-item"
        >
          <span class="preview-label">{{ formatFieldName(key) }}:</span>
          <span class="preview-value">{{ formatPreviewValue(value) }}</span>
        </div>
      </div>
    </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import ExcelJS from 'exceljs'
import { API_BASE_URL } from '@/config.js'

import {
  detectSheetType,
  extractSingleInstrumentValues,
  getRequiredFieldMappings,
  detectInstrumentNameColumn,
  extractInstrumentNames
} from '@/utils/sheetTypeDetector'

const DISPLAY_ROW_LIMIT = 2000

function extractValuesIntelligently(data, instrumentType) {
  const requiredFields = getRequiredFieldMappings(instrumentType)
  const extracted = extractSingleInstrumentValues(data, requiredFields)

  if (!extracted.instrumentName || extracted.instrumentName === '') {
    const nameCol = detectInstrumentNameColumn(data)
    if (nameCol && nameCol.columnName) {
      const names = extractInstrumentNames(data, nameCol.columnName)
      if (names && names.length > 0) {
        extracted.instrumentName = names[0]
      }
    }
  }

  return extracted
}

const props = defineProps({
  workbookData: { type: Object, required: true },
  fileName: { type: String, default: '' },
  instrumentType: { type: String, default: 'money-market' },
  worksheetStatuses: { type: Object, default: () => ({}) },
  datasetId: { type: [String, Number], default: null },
  detectingFromParent: { type: Boolean, default: false }
})

const emit = defineEmits(['close', 'sheet-selected', 'single-instrument-extracted', 'table-isolated', 'multi-table-detect', 'workbook-loaded', 'detect-start', 'detect-end'])

const viewMode = ref('grid')
const renderUrl = computed(() => {
  if (!props.datasetId) return ''
  return `${API_BASE_URL}/api/dataset/${encodeURIComponent(props.datasetId)}/render`
})
const renderChecking = ref(false)
const renderError = ref('')
const renderHtml = ref('')

async function checkRender() {
  renderError.value = ''
  renderHtml.value = ''
  renderChecking.value = true
  try {
    const res = await fetch(renderUrl.value, {
      headers: localStorage.getItem('auth_token') ? { Authorization: `Bearer ${localStorage.getItem('auth_token')}` } : {}
    })
    const ct = (res.headers.get('Content-Type') || '').toLowerCase()
    if (!res.ok || ct.includes('application/json')) {
      let body = ''
      try { body = await res.text() } catch { /* ignore */ }
      let msg = `HTTP ${res.status}`
      try {
        const j = JSON.parse(body)
        msg = `${j.stage ? '[' + j.stage + '] ' : ''}${j.message || msg}${j.fix ? '\n→ ' + j.fix : ''}`
      } catch {
        msg = `${msg}: ${body.slice(0, 400)}`
      }
      renderError.value = msg
      renderChecking.value = false
      return
    }
    renderHtml.value = await res.text()
    renderChecking.value = false
  } catch (e) {
    renderError.value = 'Network error: ' + (e.message || e)
    renderChecking.value = false
  }
}

watch(viewMode, (v) => {
  if (v === 'excel') checkRender()
}, { immediate: true })

// FIX: reset the local detection flag whenever the parent finishes
// its multi-table detection loop. Previously the flag was set to
// true and never cleared, so the blue Auto Detect button became
// permanently disabled after the first click.
watch(() => props.detectingFromParent, (val) => {
  if (!val) isDetecting.value = false
})

const sheets = ref([])
const activeSheetIndex = ref(0)
const visibleRows = ref([])
const columnHeaders = ref([])
const selectedCell = ref({ row: -1, col: -1 })
const selectedCellValue = ref('')
const selectedCellFormula = ref('')
const cellFormulas = ref(new Map())
const mergedRanges = ref([])
const rowsContainer = ref(null)
const detectedTables = ref([])
const selectedTable = ref(null)
const isTableIsolationMode = ref(false)
const isSingleInstrumentSheet = ref(false)
const extractedPreviewValues = ref({})
const selectedTables = ref(new Set())
const isDetecting = ref(false)
const isMultiTableMode = ref(false)

const viewerHeight = ref(600)
const isResizing = ref(false)
const resizeStartY = ref(0)
const resizeStartHeight = ref(0)

const resizingColumn = ref(-1)
const resizingRow = ref(-1)
const resizeStartX = ref(0)
const columnWidths = ref({})
const rowHeights = ref({})

const isSelectingRows = ref(false)
const selectedRowRange = ref({ start: -1, end: -1 })
const isRowSelectionMode = ref(false)

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
  const w = columnWidths.value[index]
  return w ? w + 'px' : '100px'
}

function getRowHeight(index) {
  return (rowHeights.value[index] || 24) + 'px'
}

function startColumnResize(colIndex, e) {
  resizingColumn.value = colIndex
  resizeStartX.value = e.clientX
  e.preventDefault()
  document.addEventListener('mousemove', onColumnResize)
  document.addEventListener('mouseup', stopColumnResize)
}

function onColumnResize(e) {
  if (resizingColumn.value === -1) return
  const deltaX = e.clientX - resizeStartX.value
  const currentWidth = columnWidths.value[resizingColumn.value] || 100
  const newWidth = Math.max(50, currentWidth + deltaX)
  columnWidths.value[resizingColumn.value] = newWidth
  resizeStartX.value = e.clientX
}

function stopColumnResize() {
  resizingColumn.value = -1
  document.removeEventListener('mousemove', onColumnResize)
  document.removeEventListener('mouseup', stopColumnResize)
}

function startRowResize(rowIndex, e) {
  resizingRow.value = rowIndex
  resizeStartY.value = e.clientY
  e.preventDefault()
  document.addEventListener('mousemove', onRowResize)
  document.addEventListener('mouseup', stopRowResize)
}

function onRowResize(e) {
  if (resizingRow.value === -1) return
  const deltaY = e.clientY - resizeStartY.value
  const currentHeight = rowHeights.value[resizingRow.value] || 30
  const newHeight = Math.max(20, currentHeight + deltaY)
  rowHeights.value[resizingRow.value] = newHeight
  resizeStartY.value = e.clientY
}

function stopRowResize() {
  resizingRow.value = -1
  document.removeEventListener('mousemove', onRowResize)
  document.removeEventListener('mouseup', stopRowResize)
}

function handleRowClick(rowIndex) {
  if (!isRowSelectionMode.value) return

  if (selectedRowRange.value.start === -1) {
    selectedRowRange.value.start = rowIndex
    selectedRowRange.value.end = rowIndex
  } else {
    selectedRowRange.value.end = rowIndex
    if (selectedRowRange.value.start > selectedRowRange.value.end) {
      const temp = selectedRowRange.value.start
      selectedRowRange.value.start = selectedRowRange.value.end
      selectedRowRange.value.end = temp
    }
  }
}

function isRowInRange(rowIndex) {
  if (selectedRowRange.value.start === -1) return false
  const start = Math.min(selectedRowRange.value.start, selectedRowRange.value.end)
  const end = Math.max(selectedRowRange.value.start, selectedRowRange.value.end)
  return rowIndex >= start && rowIndex <= end
}

function clearRowSelection() {
  selectedRowRange.value = { start: -1, end: -1 }
}

function createCustomTableFromRows() {
  if (selectedRowRange.value.start === -1 || selectedRowRange.value.end === -1) {
    alert('Please select rows first')
    return
  }

  const startRow = Math.min(selectedRowRange.value.start, selectedRowRange.value.end)
  const endRow = Math.max(selectedRowRange.value.start, selectedRowRange.value.end)

  if (!activeSheet.value || !activeSheet.value.fullData) return

  const customTable = {
    startRow: startRow,
    endRow: endRow,
    startCol: 0,
    endCol: activeSheet.value.fullData[0]?.length - 1 || 0,
    headerRow: startRow,
    headerRowEnd: startRow,
    headerRows: [startRow],
    headerRowCount: 1,
    type: 'custom',
    name: `Custom Table (Rows ${startRow + 1} - ${endRow + 1})`
  }

  selectTable(customTable)
  clearRowSelection()
  isRowSelectionMode.value = false
}

function formatCellValue(cell) {
  if (cell === null || cell === undefined || cell === '') return ''

  if (cell instanceof Date) {
    return cell.toLocaleDateString()
  }

  if (typeof cell === 'string') {
    const datePatterns = [
      /^\d{4}-\d{2}-\d{2}$/,
      /^\d{2}\/\d{2}\/\d{4}$/,
      /^\d{2}-\d{2}-\d{4}$/,
      /^\d{4}\/\d{2}\/\d{2}$/,
    ]
    for (const pattern of datePatterns) {
      if (pattern.test(cell)) {
        const date = new Date(cell)
        if (!isNaN(date.getTime())) {
          return cell
        }
      }
    }
  }

  if (typeof cell === 'number') {
    if (cell > 1 && cell < 2958465 && Number.isInteger(cell)) {
      const excelDate = new Date((cell - 25569) * 86400 * 1000)
      if (!isNaN(excelDate.getTime())) {
        return excelDate.toLocaleDateString()
      }
    }
    if (Number.isInteger(cell)) return cell.toString()
    return cell.toFixed(2)
  }

  return String(cell)
}

function getCellStyle(row, col) {
  const styles = {
    width: getColumnWidth(col),
    height: getRowHeight(row),
    textAlign: 'left',
    display: 'flex',
    alignItems: 'center',
    padding: '0 4px',
    margin: '0',
    boxSizing: 'border-box',
    borderRight: '1px solid #d4d4d4',
    borderBottom: '1px solid #d4d4d4',
    backgroundColor: '#ffffff',
    color: '#000',
    fontWeight: 'normal',
    flexShrink: 0,
    cursor: 'cell',
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    fontSize: '12px',
    fontFamily: "'Calibri', 'Aptos', 'Segoe UI', sans-serif"
  }

  // 1. Handle Merged Cells
  for (const range of mergedRanges.value) {
    if (row >= range.min_row && row <= range.max_row &&
        col >= range.min_col && col <= range.max_col) {
      if (row === range.min_row && col === range.min_col) {
        const colspan = range.max_col - range.min_col + 1
        const rowspan = range.max_row - range.min_row + 1
        styles.width = `calc(${getColumnWidth(col)} * ${colspan})`
        styles.height = `calc(${getRowHeight(row)} * ${rowspan})`
        styles.zIndex = 2
        styles.position = 'relative'
      } else {
        styles.display = 'none'
      }
      break
    }
  }

  // 2. Apply EXACT original workbook styles from ExcelJS
  const styleKey = `${row}:${col}`
  const s = activeSheet.value?.cellStyles?.get?.(styleKey)
  if (s) {
    Object.assign(styles, s)
  }

  // 3. Fallback alignment for numbers/currencies ONLY if Excel didn't specify one
  const cellValue = activeSheet.value?.fullData?.[row]?.[col]
  if (cellValue !== undefined && cellValue !== null && cellValue !== '') {
    const hasExplicitAlign = s?.textAlign

    if (!hasExplicitAlign) {
      const strVal = String(cellValue).trim()
      const isNumeric = /^[-+]?[£$€¥]?\s*[\d,]+(\.\d+)?%?$/.test(strVal)

      if (typeof cellValue === 'number' || isNumeric) {
        styles.textAlign = 'right'
      } else {
        styles.textAlign = 'left'
      }
    }
  }

  return styles
}

function selectCell(rowIndex, colIndex, cell) {
  selectedCell.value = { row: rowIndex, col: colIndex }
  selectedCellValue.value = formatCellValue(cell)

  const cellRef = getCellReference(rowIndex, colIndex)

  if (cellFormulas.value.has(cellRef)) {
    selectedCellFormula.value = cellFormulas.value.get(cellRef)
  } else {
    if (cell && typeof cell === 'object' && cell.f) {
      selectedCellFormula.value = cell.f
    } else {
      selectedCellFormula.value = formatCellValue(cell)
    }
  }
}

function getCellReference(rowIndex, colIndex) {
  const colLetter = columnHeaders.value[colIndex] || 'A'
  return `${colLetter}${rowIndex + 1}`
}

function editCell(rowIndex, colIndex, cell) {
  const newValue = prompt('Edit cell value:', formatCellValue(cell))
  if (newValue !== null) {
    if (activeSheet.value && activeSheet.value.fullData) {
      activeSheet.value.fullData[rowIndex][colIndex] = newValue
    }
  }
}

function switchSheet(index) {
  activeSheetIndex.value = index
  selectedTables.value.clear()
  selectedTable.value = null
  isTableIsolationMode.value = false
  loadSheetData()
  emit('sheet-selected', sheets.value[index].name)
}

function loadSheetData() {
  if (!activeSheet.value) return

  const sheet = activeSheet.value
  if (sheet.fullData && sheet.fullData.length > 0) {
    if (isTableIsolationMode.value && selectedTable.value) {
      const table = selectedTable.value
      const isolatedRows = []
      for (let row = table.startRow; row <= table.endRow; row++) {
        if (sheet.fullData[row]) {
          isolatedRows.push(sheet.fullData[row].slice(table.startCol, table.endCol + 1))
        }
      }
      visibleRows.value = isolatedRows
      const colCount = table.endCol - table.startCol + 1
      columnHeaders.value = getColumnHeaders(colCount)
      mergedRanges.value = []
    } else {
      const totalRows = sheet.fullData.length
      const paintCount = Math.min(totalRows, DISPLAY_ROW_LIMIT)
      const painted = new Array(paintCount)
      for (let r = 0; r < paintCount; r++) {
        painted[r] = sheet.fullData[r]
      }
      visibleRows.value = painted

      const colCount = sheet.total_columns || sheet.fullData[0]?.length || 10
      columnHeaders.value = getColumnHeaders(colCount)
      mergedRanges.value = sheet.merged_ranges || []
    }

    columnWidths.value = sheet.columnWidths ? { ...sheet.columnWidths } : {}
    rowHeights.value = sheet.rowHeights ? { ...sheet.rowHeights } : {}

    extractFormulas(sheet)
    detectTables()

    if (sheet.data && sheet.data.length > 0) {
      const detection = detectSheetType(sheet.data, props.instrumentType)
      isSingleInstrumentSheet.value = detection.type === 'single'

      if (isSingleInstrumentSheet.value) {
        const extracted = extractValuesIntelligently(sheet.data, props.instrumentType)
        extractedPreviewValues.value = extracted
        emit('single-instrument-extracted', {
          sheetName: sheet.name,
          extractedValues: extracted
        })
      } else {
        extractedPreviewValues.value = {}
      }
    }
  } else {
    visibleRows.value = []
    columnHeaders.value = []
    mergedRanges.value = []
    detectedTables.value = []
    isSingleInstrumentSheet.value = false
    extractedPreviewValues.value = {}
    cellFormulas.value.clear()
  }
  selectedCell.value = { row: -1, col: -1 }
  selectedCellValue.value = ''
  selectedCellFormula.value = ''
}

function extractFormulas(sheet) {
  cellFormulas.value.clear()

  if (sheet.formulas && typeof sheet.formulas === 'object') {
    for (const [cellRef, formula] of Object.entries(sheet.formulas)) {
      if (formula && typeof formula === 'string' && formula.startsWith('=')) {
        cellFormulas.value.set(cellRef, formula)
      }
    }
  }

  if (sheet.fullData && sheet.fullData.length > 0) {
    for (let row = 0; row < sheet.fullData.length; row++) {
      const rowData = sheet.fullData[row]
      if (!rowData) continue

      for (let col = 0; col < rowData.length; col++) {
        const cell = rowData[col]
        if (cell && typeof cell === 'object' && cell.f) {
          const cellRef = getCellReference(row, col)
          cellFormulas.value.set(cellRef, cell.f)
        }
      }
    }
  }
}

function startResize(e) {
  isResizing.value = true
  resizeStartY.value = e.clientY
  resizeStartHeight.value = viewerHeight.value
  document.addEventListener('mousemove', onResize)
  document.addEventListener('mouseup', stopResize)
}

function onResize(e) {
  if (!isResizing.value) return
  const deltaY = e.clientY - resizeStartY.value
  const newHeight = resizeStartHeight.value + deltaY
  if (newHeight >= 300 && newHeight <= window.innerHeight * 0.9) {
    viewerHeight.value = newHeight
  }
}

function stopResize() {
  isResizing.value = false
  document.removeEventListener('mousemove', onResize)
  document.removeEventListener('mouseup', stopResize)
}

function detectTables() {
  detectedTables.value = []
  const data = activeSheet.value?.fullData || visibleRows.value
  if (!data || data.length === 0) return

  const structures = analyzeWorksheetStructure(data)

  structures.forEach(structure => {
    detectedTables.value.push({
      startRow: structure.startRow,
      endRow: structure.endRow,
      startCol: structure.startCol,
      endCol: structure.endCol,
      headerRow: structure.headerRow,
      headerRowEnd: structure.headerRowEnd !== undefined ? structure.headerRowEnd : structure.headerRow,
      headerRows: Array.isArray(structure.headerRows) ? structure.headerRows : [structure.headerRow],
      headerRowCount: Array.isArray(structure.headerRows) ? structure.headerRows.length : 1,
      type: structure.type,
      name: structure.name,
      fields: structure.fields || null
    })
  })
}

function analyzeWorksheetStructure(data) {
  const cellAnalysis = analyzeCellContent(data)
  const labelValuePairs = detectLabelValuePairs(data, cellAnalysis)
  const tables = detectContentBasedTables(data, cellAnalysis)
  const sections = detectContentSections(data, cellAnalysis)
  return mergeAndPrioritizeStructures(labelValuePairs, tables, sections, data)
}

function analyzeCellContent(data) {
  const analysis = []

  for (let row = 0; row < data.length; row++) {
    const rowAnalysis = []
    for (let col = 0; col < (data[row]?.length || 0); col++) {
      const cell = data[row][col]
      rowAnalysis.push(classifyCellContent(cell, row, col))
    }
    analysis.push(rowAnalysis)
  }

  return analysis
}

function classifyCellContent(cell, row, col) {
  if (cell === null || cell === undefined || cell === '') {
    return { type: 'empty', isHeader: false, isLabel: false, isData: false }
  }

  const text = String(cell).trim()
  const isNumeric = /^[\d\,\.\-\$%]+$/.test(text)
  const isDate = /^\d{4}-\d{2}-\d{2}/.test(text) || /^\d{2}\/\d{2}\/\d{4}/.test(text) || /^\d{2}-\d{2}-\d{4}/.test(text)
  const isPercentage = /%$/.test(text)

  const headerKeywords = ['name', 'date', 'rate', 'value', 'amount', 'price', 'yield', 'coupon', 'maturity', 'issue', 'principal', 'face', 'discount', 'interest', 'term', 'tenor', 'frequency', 'currency', 'country', 'instrument', 'bond', 'bill', 'security', 'type', 'status', 'code', 'id', 'number', 'total', 'balance', 'payment', 'period', 'year', 'month', 'day', 'description', 'category', 'account', 'reference', 'transaction', 'debit', 'credit', 'asset', 'liability', 'equity', 'revenue', 'expense', 'income', 'cost', 'profit', 'loss', 'margin', 'ratio', 'percentage', 'quantity', 'unit', 'measure', 'location', 'address', 'contact', 'phone', 'email', 'customer', 'client', 'vendor', 'supplier', 'product', 'service', 'item', 'sku', 'barcode', 'serial', 'batch', 'lot', 'expiry', 'valid', 'active', 'inactive', 'pending', 'complete', 'open', 'closed', 'approved', 'rejected', 'submitted', 'draft', 'final', 'original', 'current', 'previous', 'next', 'first', 'last', 'beginning', 'ending', 'start', 'end', 'min', 'max', 'avg', 'sum', 'count']
  const isHeaderKeyword = headerKeywords.some(keyword => text.toLowerCase().includes(keyword))
  const isShortText = text.length < 100 && !isNumeric && !isDate
  const isHeader = isShortText && (isHeaderKeyword || /^[A-Z]/.test(text) || text.length > 0)

  const labelPatterns = [/^(.+?)\s*[:=]\s*$/, /^(.+?)\s*$/]
  const isLabel = isShortText && (labelPatterns.some(pattern => pattern.test(text)) || isHeaderKeyword)

  const isData = isNumeric || isDate || isPercentage || (!isHeader && !isLabel && text.length > 0)

  return {
    type: isNumeric ? 'numeric' : isDate ? 'date' : isPercentage ? 'percentage' : 'text',
    isHeader,
    isLabel,
    isData,
    text,
    length: text.length
  }
}

function detectLabelValuePairs(data, cellAnalysis) {
  const pairs = []

  for (let row = 0; row < data.length - 1; row++) {
    for (let col = 0; col < (data[row]?.length || 0); col++) {
      const currentCell = cellAnalysis[row]?.[col]
      const nextCell = cellAnalysis[row + 1]?.[col]
      if (currentCell && nextCell && currentCell.isLabel && nextCell.isData) {
        pairs.push({
          startRow: row,
          endRow: row + 1,
          startCol: col,
          endCol: col,
          headerRow: row,
          headerRowEnd: row,
          headerRows: [row],
          type: 'values',
          name: `${data[row][col]}: ${data[row + 1][col]}`.substring(0, 30)
        })
      }
    }
  }

  const pairMap = new Map()
  for (let row = 0; row < data.length; row++) {
    const rowLen = data[row]?.length || 0
    for (let col = 0; col < rowLen - 1; col++) {
      const currentCell = cellAnalysis[row]?.[col]
      const nextCell = cellAnalysis[row]?.[col + 1]
      if (currentCell && nextCell && currentCell.isLabel && nextCell.isData) {
        pairMap.set(`${row},${col}`, true)
      }
    }
  }

  const consumed = new Set()
  for (let row = 0; row < data.length; row++) {
    const rowLen = data[row]?.length || 0
    for (let col = 0; col < rowLen - 1; col++) {
      const key = `${row},${col}`
      if (!pairMap.has(key) || consumed.has(key)) continue

      const groupRows = [row]
      consumed.add(key)

      let nextRow = row + 1
      while (pairMap.has(`${nextRow},${col}`) && !consumed.has(`${nextRow},${col}`)) {
        consumed.add(`${nextRow},${col}`)
        groupRows.push(nextRow)
        nextRow++
      }
      let prevRow = row - 1
      while (pairMap.has(`${prevRow},${col}`) && !consumed.has(`${prevRow},${col}`)) {
        consumed.add(`${prevRow},${col}`)
        groupRows.unshift(prevRow)
        prevRow--
      }

      if (groupRows.length >= 2) {
        const firstLabel = data[groupRows[0]]?.[col]
        pairs.push({
          startRow: groupRows[0],
          endRow: groupRows[groupRows.length - 1],
          startCol: col,
          endCol: col + 1,
          headerRow: groupRows[0],
          headerRowEnd: groupRows[0],
          headerRows: [groupRows[0]],
          type: 'vertical_table',
          name: `${firstLabel} (vertical, ${groupRows.length} fields)`.substring(0, 40),
          fields: groupRows.map(r => ({
            label: data[r]?.[col],
            value: data[r]?.[col + 1],
            labelCell: { row: r, col: col },
            valueCell: { row: r, col: col + 1 }
          }))
        })
      } else {
        pairs.push({
          startRow: row,
          endRow: row,
          startCol: col,
          endCol: col + 1,
          headerRow: row,
          headerRowEnd: row,
          headerRows: [row],
          type: 'values',
          name: `${data[row][col]}: ${data[row][col + 1]}`.substring(0, 30)
        })
      }
    }
  }

  return pairs
}

function detectContentBasedTables(data, cellAnalysis) {
  const tables = []

  const rowMeta = []
  for (let row = 0; row < data.length; row++) {
    let textCount = 0
    let headerKeywordCount = 0
    let totalCells = 0
    const rowLen = data[row]?.length || 0
    for (let col = 0; col < rowLen; col++) {
      const c = cellAnalysis[row]?.[col]
      if (c && c.type !== 'empty') {
        totalCells++
        if (c.type === 'text') textCount++
        if (c.isHeader) headerKeywordCount++
      }
    }
    const isTextHeavy =
      totalCells >= 2 &&
      ((textCount / totalCells) >= 0.6 || headerKeywordCount >= 1)
    rowMeta.push({ row, totalCells, textCount, headerKeywordCount, isTextHeavy })
  }

  const headerGroups = []
  let currentGroup = []
  for (const meta of rowMeta) {
    if (meta.isTextHeavy) {
      if (currentGroup.length === 0 || meta.row === currentGroup[currentGroup.length - 1] + 1) {
        currentGroup.push(meta.row)
      } else {
        if (currentGroup.length > 0) headerGroups.push([...currentGroup])
        currentGroup = [meta.row]
      }
    } else {
      if (currentGroup.length > 0) {
        headerGroups.push([...currentGroup])
        currentGroup = []
      }
    }
  }
  if (currentGroup.length > 0) headerGroups.push([...currentGroup])

  for (const group of headerGroups) {
    const headerRowStart = group[0]
    const headerRowEnd = group[group.length - 1]

    let startCol = -1
    let endCol = -1
    for (let r = headerRowStart; r <= headerRowEnd; r++) {
      const rowLen = data[r]?.length || 0
      for (let col = 0; col < rowLen; col++) {
        const c = cellAnalysis[r]?.[col]
        if (c && c.type !== 'empty') {
          if (startCol === -1 || col < startCol) startCol = col
          if (col > endCol) endCol = col
        }
      }
    }
    if (startCol === -1 || endCol === -1) continue

    let endRow = headerRowEnd
    for (let row = headerRowEnd + 1; row < data.length; row++) {
      let hasContent = false
      let textCount = 0
      let totalCells = 0
      for (let col = startCol; col <= endCol; col++) {
        const c = cellAnalysis[row]?.[col]
        if (c && c.type !== 'empty') {
          hasContent = true
          totalCells++
          if (c.type === 'text') textCount++
        }
      }
      if (!hasContent) break
      const isTextHeavy = totalCells >= 2 && (textCount / totalCells) >= 0.7
      if (isTextHeavy) break
      endRow = row
    }

    if (endRow > headerRowEnd) {
      const headerContent = data[headerRowStart].slice(startCol, endCol + 1)
        .filter(cell => cell !== null && cell !== undefined && String(cell).trim() !== '')
        .join(' - ')
        .substring(0, 40)
      const tableName = headerContent || `Table ${tables.length + 1}`

      tables.push({
        startRow: headerRowStart,
        endRow: endRow,
        startCol: startCol,
        endCol: endCol,
        headerRow: headerRowStart,
        headerRowEnd: headerRowEnd,
        headerRows: [...group],
        headerRowCount: group.length,
        type: 'table',
        name: tableName
      })
    }
  }

  return tables
}

function detectContentSections(data, cellAnalysis) {
  const sections = []

  let inSection = false
  let sectionStartRow = -1
  let sectionStartCol = -1
  let sectionEndRow = -1
  let sectionEndCol = -1
  let sectionColumnCount = 0

  for (let row = 0; row < data.length; row++) {
    let hasContent = false
    let firstNonEmptyCol = -1
    let lastNonEmptyCol = -1
    let rowColumnCount = 0

    for (let col = 0; col < (data[row]?.length || 0); col++) {
      if (cellAnalysis[row][col].type !== 'empty') {
        hasContent = true
        rowColumnCount++
        if (firstNonEmptyCol === -1) firstNonEmptyCol = col
        lastNonEmptyCol = col
      }
    }

    if (hasContent) {
      if (!inSection) {
        inSection = true
        sectionStartRow = row
        sectionStartCol = firstNonEmptyCol
        sectionEndRow = row
        sectionEndCol = lastNonEmptyCol
        sectionColumnCount = rowColumnCount
      } else {
        const columnRatio = sectionColumnCount > 0 ? rowColumnCount / sectionColumnCount : 0
        if (columnRatio < 0.5 || columnRatio > 1.5) {
          if (sectionEndRow - sectionStartRow >= 0) {
            const firstRowContent = data[sectionStartRow].slice(sectionStartCol, sectionEndCol + 1)
              .filter(cell => cell && String(cell).trim() !== '')
              .join(' - ')
              .substring(0, 40)
            const sectionName = firstRowContent || `Section ${sections.length + 1}`

            sections.push({
              startRow: sectionStartRow,
              endRow: sectionEndRow,
              startCol: sectionStartCol,
              endCol: sectionEndCol,
              headerRow: sectionStartRow,
              headerRowEnd: sectionStartRow,
              headerRows: [sectionStartRow],
              type: 'section',
              name: sectionName
            })
          }
          sectionStartRow = row
          sectionStartCol = firstNonEmptyCol
          sectionEndRow = row
          sectionEndCol = lastNonEmptyCol
          sectionColumnCount = rowColumnCount
        } else {
          sectionEndRow = row
          sectionEndCol = Math.max(sectionEndCol, lastNonEmptyCol)
          sectionStartCol = Math.min(sectionStartCol, firstNonEmptyCol)
          sectionColumnCount = Math.max(sectionColumnCount, rowColumnCount)
        }
      }
    } else {
      if (inSection) {
        if (sectionEndRow - sectionStartRow >= 0) {
          const firstRowContent = data[sectionStartRow].slice(sectionStartCol, sectionEndCol + 1)
            .filter(cell => cell && String(cell).trim() !== '')
            .join(' - ')
            .substring(0, 40)
          const sectionName = firstRowContent || `Section ${sections.length + 1}`

          sections.push({
            startRow: sectionStartRow,
            endRow: sectionEndRow,
            startCol: sectionStartCol,
            endCol: sectionEndCol,
            headerRow: sectionStartRow,
            headerRowEnd: sectionStartRow,
            headerRows: [sectionStartRow],
            type: 'section',
            name: sectionName
          })
        }
        inSection = false
        sectionColumnCount = 0
      }
    }
  }

  if (inSection && sectionEndRow - sectionStartRow >= 0) {
    const firstRowContent = data[sectionStartRow].slice(sectionStartCol, sectionEndCol + 1)
      .filter(cell => cell && String(cell).trim() !== '')
      .join(' - ')
      .substring(0, 40)
    const sectionName = firstRowContent || `Section ${sections.length + 1}`

    sections.push({
      startRow: sectionStartRow,
      endRow: sectionEndRow,
      startCol: sectionStartCol,
      endCol: sectionEndCol,
      headerRow: sectionStartRow,
      headerRowEnd: sectionStartRow,
      headerRows: [sectionStartRow],
      type: 'section',
      name: sectionName
    })
  }

  return sections
}

function mergeAndPrioritizeStructures(labelValuePairs, tables, sections, data) {
  const allStructures = [...labelValuePairs, ...tables, ...sections]

  allStructures.sort((a, b) => {
    const aSize = (a.endRow - a.startRow + 1) * (a.endCol - a.startCol + 1)
    const bSize = (b.endRow - b.startRow + 1) * (b.endCol - b.startCol + 1)
    return bSize - aSize
  })

  const nonOverlapping = []
  const occupied = new Set()

  for (const structure of allStructures) {
    let overlaps = false
    let overlapCount = 0
    let totalCells = 0

    for (let row = structure.startRow; row <= structure.endRow; row++) {
      for (let col = structure.startCol; col <= structure.endCol; col++) {
        totalCells++
        const key = `${row},${col}`
        if (occupied.has(key)) {
          overlapCount++
        }
      }
    }

    if (totalCells > 0 && overlapCount / totalCells > 0.8) {
      overlaps = true
    }

    if (!overlaps) {
      nonOverlapping.push(structure)
      for (let row = structure.startRow; row <= structure.endRow; row++) {
        for (let col = structure.startCol; col <= structure.endCol; col++) {
          occupied.add(`${row},${col}`)
        }
      }
    }
  }

  nonOverlapping.sort((a, b) => a.startRow - b.startRow)

  return nonOverlapping
}

function selectTable(table) {
  selectedTable.value = table
  isTableIsolationMode.value = true

  if (activeSheet.value && activeSheet.value.fullData) {
    const table2D = []
    for (let r = table.startRow; r <= table.endRow; r++) {
      if (activeSheet.value.fullData[r]) {
        table2D.push(activeSheet.value.fullData[r].slice(table.startCol, table.endCol + 1))
      } else {
        table2D.push([])
      }
    }
    
    const defaultHeaderIdx = table.headerRow !== undefined ? table.headerRow - table.startRow : 0
    
    emit('table-isolated', {
      sheetName: activeSheet.value.name,
      tableName: table.name,
      type: table.type || 'table',
      rawTableData: table2D,
      headerRowIndex: defaultHeaderIdx,
      tableRange: {
        startRow: table.startRow,
        endRow: table.endRow,
        startCol: table.startCol,
        endCol: table.endCol,
        headerRow: table.headerRow,
        headerRowEnd: table.headerRowEnd
      }
    })
  }
}

function exitTableIsolation() {
  selectedTable.value = null
  isTableIsolationMode.value = false
}

function toggleTableSelection(index, table) {
  if (selectedTables.value.has(index)) {
    selectedTables.value.delete(index)
  } else {
    selectedTables.value.add(index)
  }
}

function clearTableSelection() {
  selectedTables.value.clear()
}

function autoDetectSelectedTables() {
  if (selectedTables.value.size === 0) {
    alert('Please select at least one table')
    return
  }

  isDetecting.value = true
  emit('detect-start')

  const selectedTableData = []
  for (const index of selectedTables.value) {
    const table = detectedTables.value[index]
    if (table && activeSheet.value && activeSheet.value.fullData) {
      const headerRows = Array.isArray(table.headerRows) && table.headerRows.length
        ? table.headerRows
        : [table.headerRow !== undefined ? table.headerRow : table.startRow]
      const headerRowEnd = headerRows[headerRows.length - 1]

      const headerLabels = []
      for (let col = table.startCol; col <= table.endCol; col++) {
        const parts = []
        for (const hr of headerRows) {
          const v = activeSheet.value.fullData[hr]?.[col]
          if (v !== undefined && v !== null && String(v).trim() !== '') {
            parts.push(String(v).trim())
          }
        }
        headerLabels.push(parts.join(' ') || `Col ${col - table.startCol + 1}`)
      }

      const tableData = {
        tableIndex: index,
        tableName: table.name,
        sheetName: activeSheet.value.name,
        type: table.type || 'table',
        headerRows: [...headerRows],
        headerRowCount: headerRows.length,
        headerLabels: headerLabels,
        range: {
          startRow: table.startRow,
          endRow: table.endRow,
          startCol: table.startCol,
          endCol: table.endCol,
          headerRow: headerRows[0],
          headerRowEnd: headerRowEnd
        },
        data: []
      }

      for (let row = table.startRow; row <= table.endRow; row++) {
        if (activeSheet.value.fullData[row]) {
          tableData.data.push(
            activeSheet.value.fullData[row].slice(table.startCol, table.endCol + 1)
          )
        }
      }

      selectedTableData.push(tableData)
    }
  }

  // Note: do NOT reset isDetecting.value = false here.
  // The parent (InstrumentView) will flip detectingFromParent
  // back to false once its detection loop completes, and the
  // watcher in this file clears the flag.
  emit('multi-table-detect', {
    sheetName: activeSheet.value.name,
    tables: selectedTableData,
    selectedCount: selectedTableData.length,
    instrumentType: props.instrumentType
  })
}

function formatFieldName(key) {
  const fieldMapping = {
    faceValue: 'Face Value',
    issueDate: 'Issue Date',
    maturityDate: 'Maturity Date',
    couponRate: 'Coupon Rate',
    yield: 'Yield',
    price: 'Price',
    discountRate: 'Discount Rate',
    frequency: 'Frequency',
    principal: 'Principal',
    interestRate: 'Interest Rate',
    daysToMaturity: 'Days to Maturity',
    instrumentName: 'Instrument Name',
    currency: 'Currency',
    country: 'Country'
  }
  return fieldMapping[key] || key.charAt(0).toUpperCase() + key.slice(1)
}

function formatPreviewValue(value) {
  if (value === null || value === undefined || value === '') return 'N/A'
  if (value instanceof Date) return value.toLocaleDateString()
  if (typeof value === 'number') {
    if (Number.isInteger(value)) return value.toString()
    return value.toFixed(2)
  }
  return String(value)
}

function closeViewer() {
  emit('close')
}

let isParsing = false

watch(() => props.workbookData, (newData) => {
  if (!newData || isParsing) return

  const hasFullData = newData.sheets && newData.sheets.some(s => s.fullData && s.fullData.length > 0)

  if (hasFullData) {
    sheets.value = newData.sheets
    loadSheetData()
    nextTick(() => emit('workbook-loaded', props.fileName))
  } else if (newData.fileBuffer && sheets.value.length === 0) {
    isParsing = true
    nextTick(async () => {
      await loadWorkbookFromFileBuffer(newData.fileBuffer)
      isParsing = false
    })
  } else if (newData.sheets && newData.sheets.length > 0 && sheets.value.length === 0) {
    sheets.value = newData.sheets
    loadSheetData()
    nextTick(() => emit('workbook-loaded', props.fileName))
  }
}, { immediate: true })

onMounted(() => {
})

onUnmounted(() => {
  isParsing = false
})

async function loadWorkbookFromFileBuffer(fileBuffer) {
  if (!fileBuffer) return

  const t0 = performance.now()
  console.log(`ExcelWorkbookViewer: parse START — ${fileBuffer.byteLength} bytes`)

  try {
    const workbook = new ExcelJS.Workbook()
    await workbook.xlsx.load(fileBuffer)

    console.log(`ExcelWorkbookViewer: parse finished in ${(performance.now() - t0).toFixed(0)}ms, ${workbook.worksheets.length} sheet(s)`)

    const loadedSheets = []
    
    const MAX_ROWS = 2000
    const MAX_COLS = 100

    // --- STYLE FIX: Extract real theme colors from workbook ---
    const defaultThemeColors = [
      '#FFFFFF', '#000000', '#E7E6E6', '#44546A',
      '#4472C4', '#ED7D31', '#A5A5A5', '#FFC000',
      '#5B9BD5', '#70AD47', '#0563C1', '#954F72'
    ];
    let workbookThemeColors = defaultThemeColors;
    if (workbook.model && workbook.model.theme && workbook.model.theme.colors) {
      workbookThemeColors = workbook.model.theme.colors;
      while (workbookThemeColors.length < 12) {
        workbookThemeColors.push(defaultThemeColors[workbookThemeColors.length]);
      }
    }

    const indexedColors = {
      0: '#000000', 1: '#FFFFFF', 2: '#FF0000', 3: '#00FF00',
      4: '#0000FF', 5: '#FFFF00', 6: '#FF00FF', 7: '#00FFFF',
      8: '#000000', 9: '#FFFFFF', 10: '#FF0000', 11: '#00FF00',
      12: '#0000FF', 13: '#FFFF00', 14: '#FF00FF', 15: '#00FFFF',
      16: '#800000', 17: '#008000', 18: '#000080', 19: '#808000',
      20: '#800080', 21: '#008080', 22: '#C0C0C0', 23: '#808080',
      24: '#9999FF', 25: '#993366', 26: '#FFFFCC', 27: '#CCFFFF',
      28: '#660066', 29: '#FF8080', 30: '#0066CC', 31: '#CCCCFF',
      32: '#000080', 33: '#FF00FF', 34: '#FFFF00', 35: '#00FFFF',
      36: '#800080', 37: '#800000', 38: '#008080', 39: '#0000FF',
      40: '#00CCFF', 41: '#CCFFFF', 42: '#CCFFCC', 43: '#FFFF99',
      44: '#99CCFF', 45: '#FF99CC', 46: '#CC99FF', 47: '#FFCC99',
      48: '#3366FF', 49: '#33CCCC', 50: '#99CC00', 51: '#FFCC00',
      52: '#FF9900', 53: '#FF6600', 54: '#666699', 55: '#969696',
      56: '#003366', 57: '#339966', 58: '#003300', 59: '#333300',
      60: '#993300', 61: '#993366', 62: '#333399', 63: '#333333',
      64: 'transparent'
    };

    function applyTint(hex, tint) {
      if (!tint || tint === 0) return hex;
      let r = parseInt(hex.slice(1, 3), 16);
      let g = parseInt(hex.slice(3, 5), 16);
      let b = parseInt(hex.slice(5, 7), 16);
      
      if (tint < 0) {
        const factor = 1 + tint;
        r = Math.round(r * factor);
        g = Math.round(g * factor);
        b = Math.round(b * factor);
      } else {
        r = Math.round(r + (255 - r) * tint);
        g = Math.round(g + (255 - g) * tint);
        b = Math.round(b + (255 - b) * tint);
      }
      
      return '#' + [r, g, b].map(c => Math.max(0, Math.min(255, c)).toString(16).padStart(2, '0')).join('');
    }

    const getColorHex = (colorObj) => {
      if (!colorObj) return null;
      
      let baseHex = null;
      
      if (colorObj.argb) {
        const argb = colorObj.argb;
        if (argb === '00000000') return null; // Transparent
        baseHex = '#' + argb.slice(-6);
      } else if (colorObj.indexed !== undefined) {
        if (colorObj.indexed === 64) return null; // System background
        baseHex = indexedColors[colorObj.indexed];
        if (baseHex === 'transparent') return null;
      } else if (colorObj.theme !== undefined) {
        baseHex = workbookThemeColors[colorObj.theme] || null;
      }
      
      if (baseHex && colorObj.tint) {
        baseHex = applyTint(baseHex, colorObj.tint);
      }
      
      return baseHex;
    };

    workbook.eachSheet((worksheet) => {
      let maxRow = 0
      let maxCol = 0
      
      // 1. Find bounds quickly using eachRow (stops at MAX_ROWS)
      worksheet.eachRow({ includeEmpty: true }, (row, rowNumber) => {
        if (rowNumber > MAX_ROWS) return false;
        if (rowNumber > maxRow) maxRow = rowNumber;
        row.eachCell({ includeEmpty: true }, (cell, colNumber) => {
          if (colNumber > MAX_COLS) return;
          if (colNumber > maxCol) maxCol = colNumber;
        })
      })

      if (maxRow === 0 || maxCol === 0) {
        loadedSheets.push({
          name: worksheet.name, fullData: [], data: [], total_rows: 0, total_columns: 0, merged_ranges: [], cellStyles: new Map(), columnWidths: {}, rowHeights: {}
        })
        return
      }

      const fullData = []
      const styleMap = new Map()

      for (let r = 0; r < maxRow; r++) {
        fullData.push(new Array(maxCol).fill(''))
      }

      // 2. Parse cells directly
      worksheet.eachRow({ includeEmpty: true }, (row, rowNumber) => {
        if (rowNumber > maxRow) return;
        const rIdx = rowNumber - 1;
        
        row.eachCell({ includeEmpty: true }, (cell, colNumber) => {
          if (colNumber > maxCol) return;
          const cIdx = colNumber - 1;

          let val = cell.value
          if (val && typeof val === 'object') {
            if (val.text) val = val.text
            else if (val.result) val = val.result
            else if (val instanceof Date) val = val.toLocaleDateString()
            else val = String(val)
          }
          fullData[rIdx][cIdx] = val !== null && val !== undefined ? val : ''

          const style = {}
          if (cell.font) {
            if (cell.font.bold) style.fontWeight = '700'
            const fontColor = getColorHex(cell.font.color);
            if (fontColor) style.color = fontColor;
            if (cell.font.size) style.fontSize = cell.font.size + 'px'
            if (cell.font.name) style.fontFamily = cell.font.name
            if (cell.font.italic) style.fontStyle = 'italic'
          }
          
          if (cell.fill && cell.fill.type === 'pattern') {
            const fillColor = getColorHex(cell.fill.fgColor);
            if (fillColor) style.backgroundColor = fillColor;
          }
          
          if (cell.alignment) {
            if (cell.alignment.horizontal) style.textAlign = cell.alignment.horizontal
            if (cell.alignment.vertical) style.alignItems = cell.alignment.vertical === 'middle' ? 'center' : cell.alignment.vertical
            if (cell.alignment.wrapText) style.whiteSpace = 'normal'
          }

          const borderCss = (edge) => {
            if (!edge) return null
            const st = typeof edge.style === 'string' ? edge.style : (['thin', 'medium', 'thick', 'dashed', 'dotted', 'double', 'hair'][edge.style - 1] || 'thin')
            const w = (st === 'medium' || st === 'thick' || st === 'double') ? '2px' : '1px'
            const color = getColorHex(edge.color) || '#d4d4d4'
            return `${w} ${st} ${color}`
          }

          const t = borderCss(cell.border?.top);    if (t) style.borderTop = t
          const b = borderCss(cell.border?.bottom); if (b) style.borderBottom = b
          const l = borderCss(cell.border?.left);   if (l) style.borderLeft = l
          const r = borderCss(cell.border?.right);  if (r) style.borderRight = r

          if (Object.keys(style).length > 0) {
            styleMap.set(`${rIdx}:${cIdx}`, style)
          }
        })
      })

      const mergedRanges = []
      if (worksheet.model && worksheet.model.merges) {
        worksheet.model.merges.forEach((mergeStr) => {
          const [start, end] = mergeStr.split(':')
          const startCell = worksheet.getCell(start)
          const endCell = worksheet.getCell(end)

          mergedRanges.push({
            min_row: Math.max(0, startCell.row - 1),
            max_row: Math.min(maxRow - 1, endCell.row - 1),
            min_col: Math.max(0, startCell.col - 1),
            max_col: Math.min(maxCol - 1, endCell.col - 1)
          })
        })
      }

      const sheetColWidths = {}
      worksheet.columns.forEach((col, idx) => {
        if (idx < maxCol && col.width) {
          sheetColWidths[idx] = Math.round(col.width * 7 + 5)
        }
      })

      const sheetRowHeights = {}
      worksheet.eachRow({ includeEmpty: false }, (row, idx) => {
        const rIdx = idx - 1
        if (rIdx >= 0 && rIdx < maxRow && row.height) {
          sheetRowHeights[rIdx] = Math.round(row.height * 1.33)
        }
      })

      const jsonData = []
      if (fullData.length > 0) {
        const headerRow = fullData[0].map((h, i) => h === '' || h === null ? `Column${i + 1}` : String(h))
        const sampleRows = Math.min(500, fullData.length)
        for (let r = 1; r < sampleRows; r++) {
          const obj = {}
          for (let c = 0; c < headerRow.length; c++) {
            obj[headerRow[c]] = fullData[r][c] ?? ''
          }
          jsonData.push(obj)
        }
      }

      loadedSheets.push({
        name: worksheet.name,
        fullData: fullData,
        data: jsonData,
        total_rows: maxRow,
        total_columns: maxCol,
        merged_ranges: mergedRanges,
        cellStyles: styleMap,
        columnWidths: sheetColWidths,
        rowHeights: sheetRowHeights
      })
      
      console.log(`ExcelWorkbookViewer: Sheet "${worksheet.name}" loaded with ${maxRow} rows × ${maxCol} columns`)
    })

    sheets.value = loadedSheets
    activeSheetIndex.value = 0
    console.log(`ExcelWorkbookViewer: parse DONE in ${(performance.now() - t0).toFixed(0)}ms — ${loadedSheets.length} sheet(s)`)
    emit('workbook-loaded', props.fileName)

    nextTick(() => {
      if (loadedSheets.length > 0) {
        emit('sheet-selected', loadedSheets[0].name)
      }
      loadSheetData()
    })

  } catch (err) {
    console.error('ExcelWorkbookViewer: parse FAILED', err)
  }
}
</script>

<style scoped>
.excel-workbook-viewer {
  display: flex;
  flex-direction: column;
  background: #fff;
  border: 1px solid #e0e0e0;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  font-size: 13px;
  position: relative;
}

.view-mode-toggle { display: flex; gap: 4px; margin-left: auto; margin-right: 12px; }
.mode-btn { padding: 4px 12px; border: 1px solid #c0c0c0; background: #f5f5f5; color: #333; border-radius: 4px; font-size: 12px; cursor: pointer; transition: all 0.15s; }
.mode-btn:hover:not(:disabled) { background: #e8e8e8; }
.mode-btn.active { background: #0B2044; color: #fff; border-color: #0B2044; }
.mode-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.excel-view-wrapper { flex: 1; min-height: 0; background: #fff; overflow: hidden; }
.excel-view-iframe { width: 100%; height: 100%; border: 0; display: block; }
.excel-view-empty { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; color: #999; padding: 24px; text-align: center; }
.excel-view-empty p { margin: 12px 0 0 0; font-size: 13px; }

.viewer-header { display: flex; justify-content: space-between; align-items: center; padding: 8px 16px; background: linear-gradient(180deg, #f5f5f5 0%, #e8e8e8 100%); border-bottom: 1px solid #d0d0d0; flex-shrink: 0; gap: 16px; }
.header-left { display: flex; align-items: center; gap: 12px; flex-shrink: 0; }
.formula-bar { display: flex; align-items: center; gap: 8px; flex: 1; background: #fff; border: 1px solid #c0c0c0; border-radius: 3px; padding: 4px 8px; }
.formula-bar-label { font-style: italic; font-family: 'Times New Roman', serif; font-weight: bold; color: #666; font-size: 14px; }
.formula-bar-input { flex: 1; border: none; outline: none; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; font-size: 13px; color: #333; background: transparent; }
.logo { height: 32px; width: auto; object-fit: contain; }
.excel-filename { font-weight: 600; color: #0B2044; font-size: 14px; }
.excel-grid-wrapper { flex: 1; overflow: auto; position: relative; }
.excel-grid-container { display: grid; grid-template-rows: 30px 1fr; min-width: 100%; min-height: 100%; }
.excel-column-headers { display: flex; position: sticky; top: 0; z-index: 10; background: linear-gradient(180deg, #f5f5f5 0%, #e8e8e8 100%); border-bottom: 1px solid #d0d0d0; min-height: 30px; }
.excel-rows-container { display: flex; flex-direction: column; }
.excel-row { display: flex; min-height: 20px; border-bottom: 1px solid #d4d4d4; margin: 0; padding: 0; }
.excel-cells-container { display: flex; flex: 1; }
.excel-header-cell { display: flex; align-items: center; justify-content: center; border: 1px solid #c0c0c0; background: #f3f3f3; font-weight: 600; color: #333; font-size: 11px; user-select: none; flex-shrink: 0; }
.excel-corner-cell { width: 40px; border-right: 1px solid #c0c0c0; }
.excel-column-header { flex-shrink: 0; border-right: 1px solid #c0c0c0; position: relative; }
.column-resize-handle { position: absolute; right: 0; top: 0; bottom: 0; width: 4px; cursor: col-resize; background: transparent; }
.column-resize-handle:hover { background: rgba(0, 0, 0, 0.1); }
.excel-row-header { width: 40px; flex-shrink: 0; border-right: 1px solid #c0c0c0; border-bottom: 1px solid #e0e0e0; position: relative; }
.row-resize-handle { position: absolute; bottom: 0; left: 0; right: 0; height: 4px; cursor: row-resize; background: transparent; }
.row-resize-handle:hover { background: rgba(0, 0, 0, 0.1); }
.row-selected { background-color: rgba(227, 242, 253, 0.3) !important; }
.row-selecting { cursor: pointer; }
.row-selecting:hover { background-color: rgba(227, 242, 253, 0.15); }
.excel-cell { flex-shrink: 0; cursor: cell; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-size: 12px; border-right: 1px solid #d4d4d4; border-bottom: 1px solid #d4d4d4; background: #ffffff; font-family: 'Calibri', 'Aptos', 'Segoe UI', sans-serif; box-sizing: border-box; margin: 0; }
.excel-cell-selected { outline: 2px solid #0B2044; outline-offset: -2px; background: #e8f0fe !important; }
.excel-sheet-tabs { display: flex; padding: 4px 12px; background: linear-gradient(180deg, #f5f5f5 0%, #e8e8e8 100%); border-top: 1px solid #d0d0d0; gap: 2px; overflow-x: auto; flex-shrink: 0; }
.excel-sheet-tab { display: flex; align-items: center; gap: 4px; padding: 4px 14px; background: #e0e0e0; border: 1px solid #c0c0c0; border-radius: 3px 3px 0 0; cursor: pointer; color: #333; font-size: 12px; white-space: nowrap; }
.excel-sheet-tab:hover { background: #d0d0d0; }
.excel-sheet-tab-active { background: #fff; border-bottom: 1px solid #fff; margin-bottom: -1px; }
.sheet-row-count { color: #999; font-size: 10px; margin-left: 4px; }
.sheet-status-badge { margin-left: 6px; padding: 2px 6px; border-radius: 10px; font-size: 10px; font-weight: 600; }
.sheet-status-badge.saved { background-color: #4CAF50; color: white; }
.table-detection-panel { display: flex; flex-direction: column; padding: 8px 12px; background: #f8f9fa; border-top: 1px solid #e0e0e0; gap: 8px; flex-shrink: 0; }
.table-detection-header { display: flex; align-items: center; gap: 6px; font-weight: 600; color: #0B2044; font-size: 12px; }
.table-icon { color: #0B2044; }
.table-mode-toggle { display: flex; gap: 4px; }
.mode-toggle-btn { flex: 1; padding: 6px 12px; background: #e0e0e0; border: 1px solid #c0c0c0; border-radius: 4px; cursor: pointer; font-size: 11px; color: #333; transition: all 0.2s; }
.mode-toggle-btn:hover { background: #d0d0d0; }
.mode-toggle-btn.active { background: #0B2044; color: white; border-color: #0B2044; }
.table-buttons { display: flex; flex-wrap: wrap; gap: 6px; }
.table-select-btn { display: flex; align-items: center; gap: 6px; padding: 6px 10px; background: white; border: 1px solid #c0c0c0; border-radius: 4px; cursor: pointer; font-size: 11px; color: #333; transition: all 0.2s; }
.table-select-btn:hover { background: #f0f0f0; border-color: #0B2044; }
.table-select-btn.table-selected { background: #e8f0fe; border-color: #0B2044; color: #0B2044; font-weight: 500; }
.table-select-btn.table-isolated { background: #d4edda; border-color: #28a745; color: #155724; }
.table-checkbox { font-weight: bold; color: #0B2044; }
.multi-table-actions { display: flex; gap: 8px; margin-top: 4px; }
.btn-auto-detect-multi { display: flex; align-items: center; gap: 6px; padding: 8px 16px; background: #0B2044; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 12px; font-weight: 500; transition: background 0.2s; }
.btn-auto-detect-multi:hover:not(:disabled) { background: #1a3a6e; }
.btn-auto-detect-multi:disabled { opacity: 0.6; cursor: not-allowed; }
.spin-animation { animation: spin 1s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
.btn-clear-selection { display: flex; align-items: center; gap: 6px; padding: 8px 12px; background: #f0f0f0; color: #666; border: 1px solid #c0c0c0; border-radius: 4px; cursor: pointer; font-size: 12px; transition: background 0.2s; }
.btn-clear-selection:hover { background: #e0e0e0; }
.table-isolation-header { display: flex; justify-content: space-between; align-items: center; padding: 8px 12px; background: #e3f2fd; border-top: 1px solid #0B2044; flex-shrink: 0; }
.isolation-info { display: flex; align-items: center; gap: 6px; font-weight: 600; color: #0d47a1; font-size: 12px; }
.exit-isolation-btn { display: flex; align-items: center; gap: 4px; padding: 4px 12px; background: #fff; border: 1px solid #dc3545; border-radius: 4px; cursor: pointer; font-size: 11px; color: #dc3545; transition: all 0.2s; }
.exit-isolation-btn:hover { background: #dc3545; color: #fff; }
.single-instrument-preview { display: flex; flex-direction: column; padding: 12px; background: #e8f5e9; border-top: 1px solid #4caf50; flex-shrink: 0; }
.preview-header { display: flex; align-items: center; gap: 6px; font-weight: 600; color: #2e7d32; font-size: 12px; margin-bottom: 8px; }
.preview-icon { color: #4caf50; }
.preview-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 8px; }
.preview-item { display: flex; flex-direction: column; padding: 6px 8px; background: #fff; border: 1px solid #c8e6c9; border-radius: 4px; }
.preview-label { font-size: 10px; color: #666; font-weight: 600; margin-bottom: 2px; }
.preview-value { font-size: 12px; color: #333; }
.resize-handle { position: absolute; bottom: 0; left: 0; right: 0; height: 8px; background: linear-gradient(to bottom, transparent, #e0e0e0); cursor: ns-resize; border-top: 1px solid #d0d0d0; z-index: 100; }
.resize-handle:hover { background: linear-gradient(to bottom, transparent, #c0c0c0); }
</style>