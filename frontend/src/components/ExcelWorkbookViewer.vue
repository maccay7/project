<template>
  <div class="excel-workbook-viewer" :style="{ height: viewerHeight + 'px' }">
    <!-- Resize handle -->
    <div class="resize-handle" @mousedown="startResize"></div>
    <!-- Header with logo and formula bar -->
    <div class="viewer-header">
      <div class="header-left">
        <img src="/DuraCapital logo.png" alt="DuraCapital" class="logo" />
        <span class="excel-filename">{{ fileName || 'Excel Workbook' }}</span>
      </div>
      <!-- Currency selection -->
      <div v-if="availableCurrencies.length > 0" class="currency-selector">
        <label class="currency-label">💰 Currency:</label>
        <select v-model="selectedCurrency" @change="emitCurrencyChange" class="currency-select">
          <option :value="null">-- All Currencies --</option>
          <option v-for="currency in availableCurrencies" :key="currency" :value="currency">
            {{ currency }}
          </option>
        </select>
        <span v-if="selectedCurrency" class="selected-currency-badge">{{ selectedCurrency }}</span>
      </div>
      <!-- Formula bar -->
      <div class="formula-bar">
        <div class="formula-bar-label">fx</div>
        <input 
          v-model="selectedCellFormula" 
          class="formula-bar-input"
          placeholder="Formula or value"
          readonly
        />
      </div>
    </div>

    <!-- Custom Excel grid -->
    <div class="excel-grid-wrapper">
      <div class="excel-grid-container">
        <!-- Column headers (A, B, C...) -->
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

        <!-- Rows -->
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
            <!-- Row header (number) -->
            <div class="excel-header-cell excel-row-header" :style="{ height: getRowHeight(rowIndex) }">
              {{ rowIndex + 1 }}
              <div class="row-resize-handle" @mousedown.stop="startRowResize(rowIndex, $event)"></div>
            </div>
            <!-- Cells -->
            <div class="excel-cells-container">
              <div
                v-for="(cell, colIndex) in row"
                :key="colIndex"
                class="excel-cell"
                :class="{
                  'excel-cell-selected': selectedCell.row === rowIndex && selectedCell.col === colIndex,
                }"
                :style="getCellStyle(rowIndex, colIndex)"
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

    <!-- Sheet tabs (bottom) -->
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

    <!-- Table detection panel -->
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
          <v-icon v-else-if="table.type === 'values'" size="12" class="type-icon">mdi-chart-bar</v-icon>
          {{ table.name }} (Row {{ table.startRow + 1 }} - {{ table.endRow + 1 }})
        </button>
      </div>
      <div v-if="isMultiTableMode && selectedTables.size > 0" class="multi-table-actions">
        <button class="btn-auto-detect-multi" @click="autoDetectSelectedTables">
          <v-icon size="16">mdi-magnify</v-icon>
          Auto Detect Selected Tables ({{ selectedTables.size }})
        </button>
        <button class="btn-clear-selection" @click="clearTableSelection">
          <v-icon size="16">mdi-close</v-icon>
          Clear Selection
        </button>
      </div>
    </div>

    <!-- Table isolation mode header -->
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

    <!-- Single instrument extracted values preview -->
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
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import * as XLSX from 'xlsx'
import {
  detectSheetType,
  extractSingleInstrumentValues,
  getRequiredFieldMappings
} from '@/utils/sheetTypeDetector'

const FINANCIAL_SYNONYMS = {
  principal: ['principal', 'face value', 'nominal value', 'investment amount', 'capital', 'deposit amount', 'initial investment', 'amount invested', 'notional', 'amount'],
  interestRate: ['interest rate', 'rate', 'coupon', 'coupon rate', 'annual rate', 'fixed rate', 'lending rate', 'investment rate', 'yield rate', 'return', 'yield'],
  daysToMaturity: ['days to maturity', 'term', 'tenor', 'maturity days', 'duration days', 'period', 'days'],
  issueDate: ['issue date', 'start date', 'effective date', 'trade date', 'settlement date', 'value date', 'origination date'],
  maturityDate: ['maturity date', 'end date', 'due date', 'redemption date', 'expiry date'],
  faceValue: ['face value', 'par value', 'nominal', 'amount', 'principal'],
  couponRate: ['coupon rate', 'coupon', 'rate', 'interest rate'],
  yield: ['yield', 'ytm', 'yield to maturity', 'return', 'effective yield'],
  frequency: ['frequency', 'payment frequency', 'coupon frequency', 'period', 'semi-annual', 'quarterly', 'annual'],
  discountRate: ['discount rate', 'discount', 'rate', 'bank discount'],
  purchasePrice: ['purchase price', 'buy price', 'price paid', 'acquisition price'],
  redemptionValue: ['redemption value', 'call value', 'maturity value'],
  instrumentName: ['instrument', 'security', 'name', 'description', 'issuer', 'counterparty', 'company', 'entity', 'bond name', 'tbill name'],
  currency: ['currency', 'ccy', 'curr', 'denomination'],
  country: ['country', 'nation', 'jurisdiction', 'region', 'market']
}

function extractValuesIntelligently(data, instrumentType, currencyFilter = null) {
  const requiredFields = getRequiredFieldMappings(instrumentType)
  let extracted = extractSingleInstrumentValues(data, requiredFields)

  // Filter data by currency if specified
  let filteredData = data
  if (currencyFilter) {
    filteredData = data.filter(row => {
      if (!row) return false
      return Object.values(row).some(val => {
        if (typeof val === 'string') {
          return val.toUpperCase().includes(currencyFilter.toUpperCase())
        }
        return false
      })
    })
    // If no data matches currency, use original data
    if (filteredData.length === 0) {
      filteredData = data
    }
  }

  const fieldKeys = Object.keys(requiredFields)
  for (const field of fieldKeys) {
    if (!extracted[field] || extracted[field] === '') {
      const synonyms = FINANCIAL_SYNONYMS[field] || [field]
      
      // Search in filtered data first
      for (const row of filteredData) {
        if (!row || typeof row !== 'object') continue
        for (const [key, value] of Object.entries(row)) {
          if (value === undefined || value === null || value === '') continue
          const keyLower = key.toLowerCase()
          const matched = synonyms.some(syn => 
            keyLower.includes(syn.toLowerCase()) || syn.toLowerCase().includes(keyLower)
          )
          if (matched) {
            extracted[field] = value
            break
          }
        }
        if (extracted[field]) break
      }
      
      // If still not found, search in entire original data (scattered values)
      if (!extracted[field] || extracted[field] === '') {
        for (const row of data) {
          if (!row || typeof row !== 'object') continue
          for (const [key, value] of Object.entries(row)) {
            if (value === undefined || value === null || value === '') continue
            const keyLower = key.toLowerCase()
            const matched = synonyms.some(syn => 
              keyLower.includes(syn.toLowerCase()) || syn.toLowerCase().includes(keyLower)
            )
            if (matched) {
              extracted[field] = value
              break
            }
          }
          if (extracted[field]) break
        }
      }
    }
  }

  if (!extracted.instrumentName || extracted.instrumentName === '') {
    const nameCol = detectInstrumentNameColumn(filteredData)
    if (nameCol && nameCol.columnName) {
      const names = extractInstrumentNames(filteredData, nameCol.columnName)
      if (names && names.length > 0) {
        extracted.instrumentName = names[0]
      }
    }
  }

  return extracted
}

function detectInstrumentNameColumn(data) {
  if (!data || data.length === 0) return null
  
  const namePatterns = ['instrument', 'name', 'security', 'bond', 'tbill', 'issuer', 'counterparty', 'company', 'entity']
  
  for (const header of Object.keys(data[0] || {})) {
    const lowerHeader = header.toLowerCase()
    if (namePatterns.some(p => lowerHeader.includes(p))) {
      return { columnName: header, confidence: 0.9 }
    }
  }
  
  return { columnName: Object.keys(data[0] || {})[0], confidence: 0.5 }
}

function extractInstrumentNames(data, columnName) {
  if (!data || !columnName) return []
  
  return data
    .map(row => row[columnName])
    .filter(name => name && typeof name === 'string' && name.trim() !== '')
    .slice(0, 10)
}

const props = defineProps({
  workbookData: {
    type: Object,
    required: true
  },
  fileName: {
    type: String,
    default: ''
  },
  instrumentType: {
    type: String,
    default: 'money-market'
  },
  worksheetStatuses: {
    type: Object,
    default: () => ({})
  }
})

const emit = defineEmits(['close', 'sheet-selected', 'single-instrument-extracted', 'table-isolated', 'multi-table-detect', 'currency-change', 'workbook-loaded'])

// ===== STATE =====
const sheets = ref([])
const activeSheetIndex = ref(0)
const visibleRows = ref([])
const columnHeaders = ref([])
const selectedCell = ref({ row: -1, col: -1 })
const selectedCellValue = ref('')
const selectedCellFormula = ref('')
const cellFormulas = ref(new Map()) // Store formulas by cell reference (e.g., "A1", "B2")
const mergedRanges = ref([])
const rowsContainer = ref(null)
const detectedTables = ref([])
const selectedTable = ref(null)
const isTableIsolationMode = ref(false)
const isSingleInstrumentSheet = ref(false)
const extractedPreviewValues = ref({})
const selectedTables = ref(new Set()) // For multi-table selection
const isMultiTableMode = ref(false)

// Currency selection
const selectedCurrency = ref(null)
const availableCurrencies = ref([])

// Viewer resize
const viewerHeight = ref(600)
const isResizing = ref(false)
const resizeStartY = ref(0)
const resizeStartHeight = ref(0)

// Column/row resize
const resizingColumn = ref(-1)
const resizingRow = ref(-1)
const resizeStartX = ref(0)
const columnWidths = ref({})
const rowHeights = ref({})

// Custom row selection for manual table creation
const isSelectingRows = ref(false)
const selectedRowRange = ref({ start: -1, end: -1 })
const isRowSelectionMode = ref(false)

// ===== COMPUTED =====
const activeSheet = computed(() => sheets.value[activeSheetIndex.value] || null)

// ===== METHODS =====
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
  return (columnWidths.value[index] || 100) + 'px'
}

function getRowHeight(index) {
  return (rowHeights.value[index] || 30) + 'px'
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
    // First click - set start
    selectedRowRange.value.start = rowIndex
    selectedRowRange.value.end = rowIndex
  } else {
    // Second click - set end (ensure start <= end)
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
  
  // Create custom table from selected rows
  const customTable = {
    startRow: startRow,
    endRow: endRow,
    startCol: 0,
    endCol: activeSheet.value.fullData[0]?.length - 1 || 0,
    headerRow: startRow,
    type: 'custom',
    name: `Custom Table (Rows ${startRow + 1} - ${endRow + 1})`
  }
  
  selectTable(customTable)
  clearRowSelection()
  isRowSelectionMode.value = false
}

function formatCellValue(cell) {
  if (cell === null || cell === undefined || cell === '') return ''
  
  // Check if it's a date object
  if (cell instanceof Date) {
    return cell.toLocaleDateString()
  }
  
  // Check if it's a date string (common Excel date formats)
  if (typeof cell === 'string') {
    const datePatterns = [
      /^\d{4}-\d{2}-\d{2}$/, // YYYY-MM-DD
      /^\d{2}\/\d{2}\/\d{4}$/, // MM/DD/YYYY
      /^\d{2}-\d{2}-\d{4}$/, // DD-MM-YYYY
      /^\d{4}\/\d{2}\/\d{2}$/, // YYYY/MM/DD
    ]
    for (const pattern of datePatterns) {
      if (pattern.test(cell)) {
        const date = new Date(cell)
        if (!isNaN(date.getTime())) {
          return cell // Return original date string to preserve format
        }
      }
    }
  }
  
  // Check if it's a number that might be an Excel serial date
  if (typeof cell === 'number') {
    // Excel dates are typically between 1 (Jan 1, 1900) and 2958465 (Dec 31, 9999)
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

function isMergedCell(row, col) {
  for (const range of mergedRanges.value) {
    if (row >= range.min_row && row <= range.max_row &&
        col >= range.min_col && col <= range.max_col) {
      return !(row === range.min_row && col === range.min_col)
    }
  }
  return false
}

function getCellStyle(row, col) {
  const styles = {
    width: getColumnWidth(col),
    height: getRowHeight(row),
    textAlign: 'left',
    display: 'flex',
    alignItems: 'center',
    padding: '2px 6px',
    borderRight: '1px solid #e0e0e0',
    borderBottom: '1px solid #e0e0e0',
    backgroundColor: 'transparent',
    color: '#000',
    fontWeight: 'normal',
    flexShrink: 0,
    cursor: 'cell',
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    fontSize: '13px'
  }

  // Check if cell is in a detected table - ONLY highlight header rows
  for (const table of detectedTables.value) {
    if (row >= table.startRow && row <= table.endRow &&
        col >= table.startCol && col <= table.endCol) {
      // Only highlight actual header row (not just startRow)
      const headerRowToUse = table.headerRow !== undefined ? table.headerRow : table.startRow
      if (row === headerRowToUse) {
        styles.backgroundColor = 'rgba(227, 242, 253, 0.3)'
        styles.fontWeight = '600'
        styles.color = '#0d47a1'
        styles.borderBottom = '2px solid #0d47a1'
      }
      // No highlighting for body cells
      break
    }
  }

  // Check merged ranges - use very transparent highlighting to avoid obscuring content
  for (const range of mergedRanges.value) {
    if (row >= range.min_row && row <= range.max_row &&
        col >= range.min_col && col <= range.max_col) {
      if (row === range.min_row && col === range.min_col) {
        // Top-left cell of merge – expand
        const colspan = range.max_col - range.min_col + 1
        const rowspan = range.max_row - range.min_row + 1
        styles.width = `calc(${getColumnWidth(col)} * ${colspan})`
        styles.height = `calc(${getRowHeight(row)} * ${rowspan})`
        // Use very transparent background to avoid band effect
        styles.backgroundColor = 'rgba(240, 244, 255, 0.08)'
        // Use thinner border to avoid band effect
        styles.border = '1px solid rgba(11, 32, 68, 0.15)'
        styles.zIndex = 2
        styles.position = 'relative'
      } else {
        // Hide non-top-left cells in merge
        styles.display = 'none'
      }
      break
    }
  }

  // Number alignment
  const cellValue = activeSheet.value?.fullData?.[row]?.[col]
  if (typeof cellValue === 'number') {
    styles.textAlign = 'right'
  }

  return styles
}

function selectCell(rowIndex, colIndex, cell) {
  selectedCell.value = { row: rowIndex, col: colIndex }
  selectedCellValue.value = formatCellValue(cell)
  
  // Get cell reference (e.g., "A1", "B2")
  const cellRef = getCellReference(rowIndex, colIndex)
  
  // Check if cell has a formula - show formula in formula bar
  if (cellFormulas.value.has(cellRef)) {
    selectedCellFormula.value = cellFormulas.value.get(cellRef)
  } else {
    // Check if cell is an object with formula property
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
  // Simple prompt-based editing (can be enhanced with inline editor)
  const newValue = prompt('Edit cell value:', formatCellValue(cell))
  if (newValue !== null) {
    if (activeSheet.value && activeSheet.value.fullData) {
      activeSheet.value.fullData[rowIndex][colIndex] = newValue
    }
  }
}

function switchSheet(index) {
  activeSheetIndex.value = index
  loadSheetData()
  emit('sheet-selected', sheets.value[index].name)
}

function loadSheetData() {
  if (!activeSheet.value) return

  const sheet = activeSheet.value
  if (sheet.fullData && sheet.fullData.length > 0) {
    // Apply table isolation if active
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
      // Clear merged ranges in isolation mode for simplicity
      mergedRanges.value = []
    } else {
      visibleRows.value = sheet.fullData
      const colCount = sheet.total_columns || sheet.fullData[0]?.length || 10
      columnHeaders.value = getColumnHeaders(colCount)
      mergedRanges.value = sheet.merged_ranges || []
    }
    
    // Extract formulas from sheet data if available
    extractFormulas(sheet)
    
    detectTables()
    
    // Auto-detect single instrument sheet and extract values
    if (sheet.data && sheet.data.length > 0) {
      const detection = detectSheetType(sheet.data, props.instrumentType)
      isSingleInstrumentSheet.value = detection.type === 'single'
      
      if (isSingleInstrumentSheet.value) {
        const extracted = extractValuesIntelligently(sheet.data, props.instrumentType, selectedCurrency.value)
        extractedPreviewValues.value = extracted
        // Emit extracted values to parent
        emit('single-instrument-extracted', {
          sheetName: sheet.name,
          extractedValues: extracted,
          selectedCurrency: selectedCurrency.value
        })
      } else {
        extractedPreviewValues.value = {}
      }
    }
    
    // Detect currencies from full data
    if (sheet.fullData && sheet.fullData.length > 0) {
      availableCurrencies.value = detectCurrencies(sheet.fullData)
    } else {
      availableCurrencies.value = []
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
  // Reset selection
  selectedCell.value = { row: -1, col: -1 }
  selectedCellValue.value = ''
  selectedCellFormula.value = ''
}

function extractFormulas(sheet) {
  cellFormulas.value.clear()
  
  // If sheet has formula data, extract it
  if (sheet.formulas && typeof sheet.formulas === 'object') {
    for (const [cellRef, formula] of Object.entries(sheet.formulas)) {
      if (formula && typeof formula === 'string' && formula.startsWith('=')) {
        cellFormulas.value.set(cellRef, formula)
      }
    }
  }
  
  // Also check if fullData contains formula objects
  if (sheet.fullData && sheet.fullData.length > 0) {
    for (let row = 0; row < sheet.fullData.length; row++) {
      const rowData = sheet.fullData[row]
      if (!rowData) continue
      
      for (let col = 0; col < rowData.length; col++) {
        const cell = rowData[col]
        // Check if cell is an object with formula property
        if (cell && typeof cell === 'object' && cell.f) {
          const cellRef = getCellReference(row, col)
          cellFormulas.value.set(cellRef, cell.f)
        }
      }
    }
  }
}

function detectCurrencies(data) {
  const currencySet = new Set()
  const currencyPatterns = [
    /\b(USD|EUR|GBP|JPY|CNY|ZWG|ZAR|AUD|CAD|CHF|INR|BRL|RUB|KRW|SGD|HKD|NOK|SEK|DKK|MXN|TRY|PLN|THB|IDR|MYR|PHP|VND|CZK|HUF|RON|BGN|HRK|RSD|UAH|ILS|SAR|AED|QAR|KWD|BHD|OMR|JOD|LBP|EGP|NGN|KES|GHS|ZMW|BWP|NAD|SZL|LSL|MZN|AOA|CDF|BIF|DJF|ERN|ETB|KMF|MGA|MWK|MUR|RWF|SCR|SOS|TZS|UGX|XAF|XOF|XPF)\b/i,
    /\$|€|£|¥|₹|₽|₩|₫|฿|RM|₱|₫|₪|₺|zł|₫/i
  ]
  
  data.forEach(row => {
    if (!row) return
    row.forEach(cell => {
      if (typeof cell === 'string') {
        for (const pattern of currencyPatterns) {
          const match = cell.match(pattern)
          if (match) {
            const currency = match[0].toUpperCase()
            if (currency === '$') currencySet.add('USD')
            else if (currency === '€') currencySet.add('EUR')
            else if (currency === '£') currencySet.add('GBP')
            else if (currency === '¥') currencySet.add('JPY')
            else currencySet.add(currency)
          }
        }
      }
    })
  })
  return Array.from(currencySet).sort()
}

function emitCurrencyChange() {
  emit('currency-change', selectedCurrency.value)
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
  // Limit height between 300px and 90vh
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
  const data = visibleRows.value
  if (!data || data.length === 0) return

  // Enhanced content-based structure detection
  const structures = analyzeWorksheetStructure(data)
  
  // Convert detected structures to the expected format
  structures.forEach(structure => {
    detectedTables.value.push({
      startRow: structure.startRow,
      endRow: structure.endRow,
      startCol: structure.startCol,
      endCol: structure.endCol,
      headerRow: structure.headerRow,
      type: structure.type,
      name: structure.name
    })
  })
}

function analyzeWorksheetStructure(data) {
  const structures = []
  
  // Step 1: Analyze each cell to classify its content type
  const cellAnalysis = analyzeCellContent(data)
  
  // Step 2: Detect label-value pairs (vertical and horizontal)
  const labelValuePairs = detectLabelValuePairs(data, cellAnalysis)
  
  // Step 3: Detect tables with headers based on content patterns
  const tables = detectContentBasedTables(data, cellAnalysis)
  
  // Step 4: Detect sections (areas with related content)
  const sections = detectContentSections(data, cellAnalysis)
  
  // Step 5: Merge and prioritize structures
  const mergedStructures = mergeAndPrioritizeStructures(labelValuePairs, tables, sections, data)
  
  return mergedStructures
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
  
  // Check if it looks like a header based on content
  const headerKeywords = ['name', 'date', 'rate', 'value', 'amount', 'price', 'yield', 'coupon', 'maturity', 'issue', 'principal', 'face', 'discount', 'interest', 'term', 'tenor', 'frequency', 'currency', 'country', 'instrument', 'bond', 'bill', 'security']
  const isHeaderKeyword = headerKeywords.some(keyword => text.toLowerCase().includes(keyword))
  const isShortText = text.length < 50 && !isNumeric && !isDate
  const isHeader = isShortText && (isHeaderKeyword || /^[A-Z]/.test(text))
  
  // Check if it looks like a label
  const labelPatterns = [/^(.+?)\s*[:=]\s*$/, /^(.+?)\s*$/]
  const isLabel = isShortText && (labelPatterns.some(pattern => pattern.test(text)) || isHeaderKeyword)
  
  // Check if it's data
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
  
  // Detect vertical label-value pairs (label in row N, value in row N+1)
  for (let row = 0; row < data.length - 1; row++) {
    for (let col = 0; col < (data[row]?.length || 0); col++) {
      const currentCell = cellAnalysis[row][col]
      const nextCell = cellAnalysis[row + 1][col]
      
      if (currentCell.isLabel && nextCell.isData) {
        pairs.push({
          startRow: row,
          endRow: row + 1,
          startCol: col,
          endCol: col,
          headerRow: row,
          type: 'values',
          name: `${data[row][col]}: ${data[row + 1][col]}`.substring(0, 30)
        })
      }
    }
  }
  
  // Detect horizontal label-value pairs (label in col N, value in col N+1)
  for (let row = 0; row < data.length; row++) {
    for (let col = 0; col < (data[row]?.length - 1); col++) {
      const currentCell = cellAnalysis[row][col]
      const nextCell = cellAnalysis[row][col + 1]
      
      if (currentCell.isLabel && nextCell.isData) {
        pairs.push({
          startRow: row,
          endRow: row,
          startCol: col,
          endCol: col + 1,
          headerRow: row,
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
  
  // Look for rows that could be headers based on content
  const potentialHeaderRows = []
  for (let row = 0; row < data.length; row++) {
    let headerCount = 0
    let totalCells = 0
    
    for (let col = 0; col < (data[row]?.length || 0); col++) {
      if (cellAnalysis[row][col].type !== 'empty') {
        totalCells++
        if (cellAnalysis[row][col].isHeader) {
          headerCount++
        }
      }
    }
    
    // If more than 50% of non-empty cells look like headers, consider it a header row
    if (totalCells >= 2 && headerCount / totalCells >= 0.5) {
      potentialHeaderRows.push(row)
    }
  }
  
  // For each potential header row, find the extent of the table
  for (const headerRow of potentialHeaderRows) {
    let startCol = -1
    let endCol = -1
    
    // Find the column range of the header
    for (let col = 0; col < (data[headerRow]?.length || 0); col++) {
      if (cellAnalysis[headerRow][col].type !== 'empty') {
        if (startCol === -1) startCol = col
        endCol = col
      }
    }
    
    if (startCol === -1) continue
    
    // Find the end of the table (look for data rows below)
    let endRow = headerRow
    let consecutiveEmptyRows = 0
    
    for (let row = headerRow + 1; row < data.length; row++) {
      let hasData = false
      
      for (let col = startCol; col <= endCol; col++) {
        if (cellAnalysis[row][col]?.type !== 'empty') {
          hasData = true
          break
        }
      }
      
      if (hasData) {
        endRow = row
        consecutiveEmptyRows = 0
      } else {
        consecutiveEmptyRows++
        if (consecutiveEmptyRows >= 2) break
      }
    }
    
    // Only add if we have at least one data row
    if (endRow > headerRow) {
      tables.push({
        startRow: headerRow,
        endRow: endRow,
        startCol: startCol,
        endCol: endCol,
        headerRow: headerRow,
        type: 'table',
        name: `Table ${tables.length + 1}`
      })
    }
  }
  
  return tables
}

function detectContentSections(data, cellAnalysis) {
  const sections = []
  
  // Detect contiguous areas of content that aren't tables
  let inSection = false
  let sectionStartRow = -1
  let sectionStartCol = -1
  let sectionEndRow = -1
  let sectionEndCol = -1
  let consecutiveEmptyRows = 0
  
  for (let row = 0; row < data.length; row++) {
    let hasContent = false
    let firstNonEmptyCol = -1
    let lastNonEmptyCol = -1
    
    for (let col = 0; col < (data[row]?.length || 0); col++) {
      if (cellAnalysis[row][col].type !== 'empty') {
        hasContent = true
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
      } else {
        sectionEndRow = row
        sectionEndCol = Math.max(sectionEndCol, lastNonEmptyCol)
        sectionStartCol = Math.min(sectionStartCol, firstNonEmptyCol)
      }
      consecutiveEmptyRows = 0
    } else {
      consecutiveEmptyRows++
      if (inSection && consecutiveEmptyRows >= 2) {
        // End of section
        if (sectionEndRow - sectionStartRow >= 1) {
          sections.push({
            startRow: sectionStartRow,
            endRow: sectionEndRow,
            startCol: sectionStartCol,
            endCol: sectionEndCol,
            headerRow: sectionStartRow,
            type: 'section',
            name: `Section ${sections.length + 1}`
          })
        }
        inSection = false
      }
    }
  }
  
  // Add final section if still in one
  if (inSection && sectionEndRow - sectionStartRow >= 1) {
    sections.push({
      startRow: sectionStartRow,
      endRow: sectionEndRow,
      startCol: sectionStartCol,
      endCol: sectionEndCol,
      headerRow: sectionStartRow,
      type: 'section',
      name: `Section ${sections.length + 1}`
    })
  }
  
  return sections
}

function mergeAndPrioritizeStructures(labelValuePairs, tables, sections, data) {
  const allStructures = [...labelValuePairs, ...tables, ...sections]
  
  // Sort by size (larger structures first) to prioritize tables over individual pairs
  allStructures.sort((a, b) => {
    const aSize = (a.endRow - a.startRow + 1) * (a.endCol - a.startCol + 1)
    const bSize = (b.endRow - b.startRow + 1) * (b.endCol - b.startCol + 1)
    return bSize - aSize
  })
  
  // Remove overlapping structures (keep larger ones)
  const nonOverlapping = []
  const occupied = new Set()
  
  for (const structure of allStructures) {
    let overlaps = false
    
    for (let row = structure.startRow; row <= structure.endRow; row++) {
      for (let col = structure.startCol; col <= structure.endCol; col++) {
        const key = `${row},${col}`
        if (occupied.has(key)) {
          overlaps = true
          break
        }
      }
      if (overlaps) break
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
  
  // Sort by row position for display order
  nonOverlapping.sort((a, b) => a.startRow - b.startRow)
  
  return nonOverlapping
}

function detectSections(data) {
  if (!data || data.length === 0) return

  // Detect sections: areas with data that might contain tables
  // More lenient to detect tables within sections while avoiding fake Value Areas
  
  let inSection = false
  let sectionStartRow = -1
  let sectionStartCol = -1
  let sectionEndRow = -1
  let sectionEndCol = -1
  let sectionName = ''
  let consecutiveEmptyRows = 0

  for (let row = 0; row < data.length; row++) {
    const rowData = data[row]
    if (!rowData) continue

    let nonEmptyCount = 0
    let firstNonEmptyCol = -1
    let lastNonEmptyCol = -1
    let rowContent = ''

    for (let col = 0; col < rowData.length; col++) {
      const cell = rowData[col]
      if (cell !== null && cell !== undefined && cell !== '') {
        nonEmptyCount++
        if (firstNonEmptyCol === -1) firstNonEmptyCol = col
        lastNonEmptyCol = col
        if (typeof cell === 'string') {
          rowContent += cell + ' '
        }
      }
    }

    // Track consecutive empty rows
    if (nonEmptyCount === 0) {
      consecutiveEmptyRows++
    } else {
      consecutiveEmptyRows = 0
    }

    // Detect sections with at least 2 columns
    if (nonEmptyCount >= 2 && !inSection) {
      inSection = true
      sectionStartRow = row
      sectionStartCol = firstNonEmptyCol
      sectionEndRow = row
      sectionEndCol = lastNonEmptyCol
      sectionName = rowContent.trim().substring(0, 30) || `Section ${detectedTables.value.length + 1}`
    } else if (inSection && nonEmptyCount >= 1) {
      // Continue section
      sectionEndRow = row
      sectionEndCol = Math.max(sectionEndCol, lastNonEmptyCol)
      sectionStartCol = Math.min(sectionStartCol, firstNonEmptyCol)
    } else if (inSection && consecutiveEmptyRows >= 3) {
      // Multiple consecutive empty rows end the section
      inSection = false
      // Only add section if it has at least 2 rows
      if (sectionEndRow - sectionStartRow >= 1) {
        detectedTables.value.push({
          startRow: sectionStartRow,
          endRow: sectionEndRow,
          startCol: sectionStartCol,
          endCol: sectionEndCol,
          headerRow: sectionStartRow,
          type: 'section',
          name: sectionName
        })
      }
    }
  }

  // Add last section if still in one and has at least 2 rows
  if (inSection && sectionEndRow - sectionStartRow >= 1) {
    detectedTables.value.push({
      startRow: sectionStartRow,
      endRow: sectionEndRow,
      startCol: sectionStartCol,
      endCol: sectionEndCol,
      headerRow: sectionStartRow,
      type: 'section',
      name: sectionName
    })
  }

  // Disabled: detectScatteredValues was creating fake Value Areas from individual rows
  // Only detect actual tables and sections, not individual cells
  // detectScatteredValues(data)
}

function detectScatteredValues(data) {
  if (!data || data.length === 0) return

  // Find individual cells with important values (monetary, dates, percentages, etc.)
  const importantCells = []
  
  for (let row = 0; row < data.length; row++) {
    const rowData = data[row]
    if (!rowData) continue

    for (let col = 0; col < rowData.length; col++) {
      const cell = rowData[col]
      if (cell === null || cell === undefined || cell === '') continue

      // Check if cell contains important data
      const isMonetary = typeof cell === 'string' && (cell.match(/\$|€|£|¥|USD|EUR|GBP|ZWG/i) || cell.match(/\d+[,.]\d+/))
      const isPercentage = typeof cell === 'string' && cell.match(/\d+%|\d+\.\d+%/)
      const isDate = typeof cell === 'string' && cell.match(/\d{4}-\d{2}-\d{2}|\d{2}\/\d{2}\/\d{4}|\d{2}-\d{2}-\d{4}/)
      const isNumber = typeof cell === 'number'
      const isLongText = typeof cell === 'string' && cell.length > 20

      if (isMonetary || isPercentage || isDate || isNumber || isLongText) {
        importantCells.push({
          row,
          col,
          value: cell,
          type: isMonetary ? 'monetary' : isPercentage ? 'percentage' : isDate ? 'date' : isNumber ? 'number' : 'text'
        })
      }
    }
  }

  // Group nearby important cells into value areas
  if (importantCells.length > 0) {
    let currentArea = null
    
    for (const cell of importantCells) {
      if (!currentArea) {
        currentArea = {
          startRow: cell.row,
          endRow: cell.row,
          startCol: cell.col,
          endCol: cell.col,
          cells: [cell]
        }
      } else {
        // Check if this cell is close to the current area
        const rowDiff = Math.abs(cell.row - currentArea.endRow)
        const colDiff = Math.abs(cell.col - currentArea.endCol)
        
        if (rowDiff <= 2 && colDiff <= 3) {
          // Extend current area
          currentArea.endRow = Math.max(currentArea.endRow, cell.row)
          currentArea.endCol = Math.max(currentArea.endCol, cell.col)
          currentArea.startRow = Math.min(currentArea.startRow, cell.row)
          currentArea.startCol = Math.min(currentArea.startCol, cell.col)
          currentArea.cells.push(cell)
        } else {
          // Save current area and start new one
          if (currentArea.cells.length >= 1) {
            detectedTables.value.push({
              startRow: currentArea.startRow,
              endRow: currentArea.endRow,
              startCol: currentArea.startCol,
              endCol: currentArea.endCol,
              headerRow: currentArea.startRow,
              type: 'values',
              name: `Value Area ${detectedTables.value.length + 1}`
            })
          }
          currentArea = {
            startRow: cell.row,
            endRow: cell.row,
            startCol: cell.col,
            endCol: cell.col,
            cells: [cell]
          }
        }
      }
    }
    
    // Add the last area
    if (currentArea && currentArea.cells.length >= 1) {
      detectedTables.value.push({
        startRow: currentArea.startRow,
        endRow: currentArea.endRow,
        startCol: currentArea.startCol,
        endCol: currentArea.endCol,
        headerRow: currentArea.startRow,
        type: 'values',
        name: `Value Area ${detectedTables.value.length + 1}`
      })
    }
  }
}

function selectTable(table) {
  selectedTable.value = table
  isTableIsolationMode.value = true
  
  // Convert isolated table/section data to JSON format for mapping
  if (activeSheet.value && activeSheet.value.fullData) {
    const isolatedData = []
    const headers = []
    
    // Extract headers from the header row of the table/section
    const headerRowIndex = table.headerRow !== undefined ? table.headerRow : table.startRow
    for (let col = table.startCol; col <= table.endCol; col++) {
      const headerCell = activeSheet.value.fullData[headerRowIndex]?.[col]
      headers.push(headerCell || `Column ${col}`)
    }
    
    // Extract data rows (skip header row)
    for (let row = headerRowIndex + 1; row <= table.endRow; row++) {
      const rowData = {}
      for (let col = table.startCol; col <= table.endCol; col++) {
        const cellValue = activeSheet.value.fullData[row]?.[col]
        rowData[headers[col - table.startCol]] = cellValue !== undefined ? cellValue : ''
      }
      // Only add non-empty rows
      if (Object.values(rowData).some(v => v !== '')) {
        isolatedData.push(rowData)
      }
    }
    
    // Emit the isolated table/section data for mapping
    emit('table-isolated', {
      sheetName: activeSheet.value.name,
      tableName: table.name,
      type: table.type || 'table',
      data: isolatedData,
      headers: headers,
      tableRange: {
        startRow: table.startRow,
        endRow: table.endRow,
        startCol: table.startCol,
        endCol: table.endCol,
        headerRow: headerRowIndex
      },
      selectedCurrency: selectedCurrency.value
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

  const selectedTableData = []
  for (const index of selectedTables.value) {
    const table = detectedTables.value[index]
    if (table && activeSheet.value && activeSheet.value.fullData) {
      const tableData = {
        tableIndex: index,
        tableName: table.name,
        sheetName: activeSheet.value.name,
        range: {
          startRow: table.startRow,
          endRow: table.endRow,
          startCol: table.startCol,
          endCol: table.endCol
        },
        data: []
      }

      // Extract table data
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

  // Emit to parent for auto-detection
  emit('multi-table-detect', {
    sheetName: activeSheet.value.name,
    tables: selectedTableData,
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

// ===== WATCHERS =====
watch(() => props.workbookData, (newData) => {
  console.log('ExcelWorkbookViewer: workbookData changed', newData)
  if (newData && newData.sheets) {
    sheets.value = newData.sheets
    console.log('ExcelWorkbookViewer: sheets loaded', sheets.value.length, 'sheets')
    console.log('ExcelWorkbookViewer: fileBuffer present?', !!newData.fileBuffer)
    console.log('ExcelWorkbookViewer: first sheet has fullData?', !!newData.sheets[0]?.fullData)
    
    // Emit workbook-loaded event with file name
    emit('workbook-loaded', props.fileName)
    
    // If sheets don't have fullData, parse from fileBuffer
    if (newData.fileBuffer && (!newData.sheets[0]?.fullData || newData.sheets[0]?.fullData?.length === 0)) {
      console.log('ExcelWorkbookViewer: Loading from fileBuffer')
      loadWorkbookFromFileBuffer(newData.fileBuffer)
    } else {
      console.log('ExcelWorkbookViewer: Loading from existing fullData')
      loadSheetData()
    }
  }
}, { immediate: true, deep: true })

// ===== LIFECYCLE =====
onMounted(() => {
  console.log('ExcelWorkbookViewer: mounted')
  if (props.workbookData && props.workbookData.sheets) {
    sheets.value = props.workbookData.sheets
    console.log('ExcelWorkbookViewer: sheets loaded on mount', sheets.value.length, 'sheets')
    console.log('ExcelWorkbookViewer: fileBuffer present?', !!props.workbookData.fileBuffer)
    console.log('ExcelWorkbookViewer: first sheet has fullData?', !!props.workbookData.sheets[0]?.fullData)
    
    // If sheets don't have fullData, parse from fileBuffer
    if (props.workbookData.fileBuffer && (!props.workbookData.sheets[0]?.fullData || props.workbookData.sheets[0]?.fullData?.length === 0)) {
      console.log('ExcelWorkbookViewer: Loading from fileBuffer on mount')
      loadWorkbookFromFileBuffer(props.workbookData.fileBuffer)
    } else {
      console.log('ExcelWorkbookViewer: Loading from existing fullData on mount')
      loadSheetData()
    }
  }
})

// ===== LOAD WORKBOOK FROM FILE BUFFER =====
function loadWorkbookFromFileBuffer(fileBuffer) {
  if (!fileBuffer) {
    console.error('ExcelWorkbookViewer: fileBuffer is null/undefined')
    return
  }
  
  console.log('ExcelWorkbookViewer: fileBuffer type:', fileBuffer.constructor.name)
  console.log('ExcelWorkbookViewer: fileBuffer byteLength:', fileBuffer.byteLength || fileBuffer.length || 'unknown')
  
  try {
    console.log('Loading workbook from file buffer for viewer...')
    const workbook = XLSX.read(fileBuffer, {
      type: 'array',
      cellDates: true,
      cellStyles: true,
      cellNF: true,
      cellFormula: true
    })
    
    console.log('ExcelWorkbookViewer: Workbook parsed successfully')
    console.log('ExcelWorkbookViewer: Sheet names:', workbook.SheetNames)
    
    const loadedSheets = []
    for (const sheetName of workbook.SheetNames) {
      console.log(`ExcelWorkbookViewer: Processing sheet "${sheetName}"`)
      const worksheet = workbook.Sheets[sheetName]
      
      // Get full 2D array data
      const ref = worksheet['!ref']
      let fullData = []
      let totalRows = 0
      let totalColumns = 0
      let maxRows = 500
      let maxCols = 100
      
      if (ref) {
        const range = XLSX.utils.decode_range(ref)
        totalRows = range.e.r - range.s.r + 1
        totalColumns = range.e.c - range.s.c + 1
        
        console.log(`ExcelWorkbookViewer: Sheet "${sheetName}" has ${totalRows} rows, ${totalColumns} columns`)
        
        // Skip sheets that are too large to prevent hanging
        if (totalRows > 50000 || totalColumns > 500) {
          console.log(`ExcelWorkbookViewer: Skipping sheet "${sheetName}" - too large (${totalRows} rows x ${totalColumns} columns)`)
          continue
        }
        
        // Limit to reasonable size for display to prevent browser hanging
        maxRows = Math.min(500, totalRows)
        maxCols = Math.min(100, totalColumns)
        console.log(`ExcelWorkbookViewer: Loading ${maxRows} rows x ${maxCols} columns for display`)
        
        for (let R = range.s.r; R < range.s.r + maxRows; R++) {
          const row = []
          for (let C = range.s.c; C < range.s.c + maxCols; C++) {
            const cellAddress = XLSX.utils.encode_cell({ r: R, c: C })
            const cell = worksheet[cellAddress]
            // Extract actual value for display - use formatted value (w) or raw value (v)
            if (cell) {
              row.push(cell.w ?? cell.v ?? '')
            } else {
              row.push('')
            }
          }
          fullData.push(row)
        }
      }
      
      // Get merged ranges
      const mergedRanges = []
      if (worksheet['!merges']) {
        for (const merge of worksheet['!merges']) {
          mergedRanges.push({
            min_row: merge.s.r,
            max_row: merge.e.r,
            min_col: merge.s.c,
            max_col: merge.e.c
          })
        }
      }
      
      // Get JSON data for detection - use full range
      const jsonData = XLSX.utils.sheet_to_json(worksheet, { 
        defval: '', 
        raw: false
      })
      
      loadedSheets.push({
        name: sheetName,
        fullData: fullData,
        data: jsonData,
        total_rows: totalRows,
        total_columns: totalColumns,
        merged_ranges: mergedRanges
      })
      
      console.log(`ExcelWorkbookViewer: Sheet "${sheetName}" loaded with ${fullData.length} rows`)
    }
    
    sheets.value = loadedSheets
    console.log(`ExcelWorkbookViewer: Total ${loadedSheets.length} sheets loaded from file buffer`)
    loadSheetData()
  } catch (err) {
    console.error('ExcelWorkbookViewer: Failed to load workbook from file buffer:', err)
    console.error('ExcelWorkbookViewer: Error stack:', err.stack)
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

.viewer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 16px;
  background: linear-gradient(180deg, #f5f5f5 0%, #e8e8e8 100%);
  border-bottom: 1px solid #d0d0d0;
  flex-shrink: 0;
  gap: 16px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}

.formula-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  background: #fff;
  border: 1px solid #c0c0c0;
  border-radius: 3px;
  padding: 4px 8px;
}

.formula-bar-label {
  font-style: italic;
  font-family: 'Times New Roman', serif;
  font-weight: bold;
  color: #666;
  font-size: 14px;
}

.formula-bar-input {
  flex: 1;
  border: none;
  outline: none;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  font-size: 13px;
  color: #333;
  background: transparent;
}

.logo {
  height: 32px;
  width: auto;
  object-fit: contain;
}

.excel-filename {
  font-weight: 600;
  color: #0B2044;
  font-size: 14px;
}

.excel-grid-wrapper {
  flex: 1;
  overflow: auto;
  position: relative;
}

.excel-grid-container {
  display: grid;
  grid-template-rows: 30px 1fr;
  min-width: 100%;
  min-height: 100%;
}

.excel-column-headers {
  display: flex;
  position: sticky;
  top: 0;
  z-index: 10;
  background: linear-gradient(180deg, #f5f5f5 0%, #e8e8e8 100%);
  border-bottom: 1px solid #d0d0d0;
  min-height: 30px;
}

.excel-rows-container {
  display: flex;
  flex-direction: column;
}

.excel-row {
  display: flex;
  min-height: 30px;
  border-bottom: 1px solid #e0e0e0;
}

.excel-cells-container {
  display: flex;
  flex: 1;
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
  flex-shrink: 0;
}

.excel-corner-cell {
  width: 40px;
  border-right: 1px solid #c0c0c0;
}

.excel-column-header {
  flex-shrink: 0;
  border-right: 1px solid #c0c0c0;
  position: relative;
}

.column-resize-handle {
  position: absolute;
  right: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  cursor: col-resize;
  background: transparent;
}

.column-resize-handle:hover {
  background: rgba(0, 0, 0, 0.1);
}

.excel-row-header {
  width: 40px;
  flex-shrink: 0;
  border-right: 1px solid #c0c0c0;
  border-bottom: 1px solid #e0e0e0;
  position: relative;
}

.row-resize-handle {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 4px;
  cursor: row-resize;
  background: transparent;
}

.row-resize-handle:hover {
  background: rgba(0, 0, 0, 0.1);
}

.row-selected {
  background-color: rgba(227, 242, 253, 0.3) !important;
}

.row-selecting {
  cursor: pointer;
}

.row-selecting:hover {
  background-color: rgba(227, 242, 253, 0.15);
}

.excel-cell {
  flex-shrink: 0;
  cursor: cell;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 13px;
  border-right: 1px solid #e0e0e0;
  border-bottom: 1px solid #e0e0e0;
}

.excel-cell-selected {
  outline: 2px solid #0B2044;
  outline-offset: -2px;
  background: #e8f0fe !important;
}

.excel-sheet-tabs {
  display: flex;
  padding: 4px 12px;
  background: linear-gradient(180deg, #f5f5f5 0%, #e8e8e8 100%);
  border-top: 1px solid #d0d0d0;
  gap: 2px;
  overflow-x: auto;
  flex-shrink: 0;
}

.excel-sheet-tab {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 14px;
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

.sheet-row-count {
  color: #999;
  font-size: 10px;
  margin-left: 4px;
}

.sheet-status-badge {
  margin-left: 6px;
  padding: 2px 6px;
  border-radius: 10px;
  font-size: 10px;
  font-weight: 600;
}

.sheet-status-badge.saved {
  background-color: #4CAF50;
  color: white;
}

.table-detection-panel {
  display: flex;
  flex-direction: column;
  padding: 8px 12px;
  background: #f8f9fa;
  border-top: 1px solid #e0e0e0;
  gap: 8px;
  flex-shrink: 0;
}

.table-detection-header {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  color: #0B2044;
  font-size: 12px;
}

.table-icon {
  color: #0B2044;
}

.table-mode-toggle {
  display: flex;
  gap: 4px;
}

.mode-toggle-btn {
  flex: 1;
  padding: 6px 12px;
  background: #e0e0e0;
  border: 1px solid #c0c0c0;
  border-radius: 4px;
  cursor: pointer;
  font-size: 11px;
  color: #333;
  transition: all 0.2s;
}

.mode-toggle-btn:hover {
  background: #d0d0d0;
}

.mode-toggle-btn.active {
  background: #0B2044;
  color: white;
  border-color: #0B2044;
}

.table-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.table-select-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  background: white;
  border: 1px solid #c0c0c0;
  border-radius: 4px;
  cursor: pointer;
  font-size: 11px;
  color: #333;
  transition: all 0.2s;
}

.table-select-btn:hover {
  background: #f0f0f0;
  border-color: #0B2044;
}

.table-select-btn.table-selected {
  background: #e8f0fe;
  border-color: #0B2044;
  color: #0B2044;
  font-weight: 500;
}

.table-select-btn.table-isolated {
  background: #d4edda;
  border-color: #28a745;
  color: #155724;
}

.table-checkbox {
  font-weight: bold;
  color: #0B2044;
}

.multi-table-actions {
  display: flex;
  gap: 8px;
  margin-top: 4px;
}

.btn-auto-detect-multi {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: #0B2044;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  font-weight: 500;
  transition: background 0.2s;
}

.btn-auto-detect-multi:hover {
  background: #1a3a6e;
}

.btn-clear-selection {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  background: #f0f0f0;
  color: #666;
  border: 1px solid #c0c0c0;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  transition: background 0.2s;
}

.btn-clear-selection:hover {
  background: #e0e0e0;
}

.table-isolation-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: #e3f2fd;
  border-top: 1px solid #0B2044;
  flex-shrink: 0;
}

.isolation-info {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  color: #0d47a1;
  font-size: 12px;
}

.exit-isolation-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 12px;
  background: #fff;
  border: 1px solid #dc3545;
  border-radius: 4px;
  cursor: pointer;
  font-size: 11px;
  color: #dc3545;
  transition: all 0.2s;
}

.exit-isolation-btn:hover {
  background: #dc3545;
  color: #fff;
}

.single-instrument-preview {
  display: flex;
  flex-direction: column;
  padding: 12px;
  background: #e8f5e9;
  border-top: 1px solid #4caf50;
  flex-shrink: 0;
}

.preview-header {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  color: #2e7d32;
  font-size: 12px;
  margin-bottom: 8px;
}

.preview-icon {
  color: #4caf50;
}

.preview-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 8px;
}

.preview-item {
  display: flex;
  flex-direction: column;
  padding: 6px 8px;
  background: #fff;
  border: 1px solid #c8e6c9;
  border-radius: 4px;
}

.preview-label {
  font-size: 10px;
  color: #666;
  font-weight: 600;
  margin-bottom: 2px;
}

.preview-value {
  font-size: 12px;
  color: #333;
}

/* Currency selector styles */
.currency-selector {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 12px;
  background: #f0f4ff;
  border-radius: 4px;
  margin: 0 12px;
}

.currency-label {
  font-size: 13px;
  font-weight: 600;
  color: #0B2044;
}

.currency-select {
  padding: 4px 8px;
  border: 1px solid #0B2044;
  border-radius: 4px;
  font-size: 12px;
  background: white;
  color: #0B2044;
  min-width: 120px;
}

.selected-currency-badge {
  padding: 2px 8px;
  background: #0B2044;
  color: white;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
}

.resize-handle {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 8px;
  background: linear-gradient(to bottom, transparent, #e0e0e0);
  cursor: ns-resize;
  border-top: 1px solid #d0d0d0;
  z-index: 100;
}

.resize-handle:hover {
  background: linear-gradient(to bottom, transparent, #c0c0c0);
}
</style>