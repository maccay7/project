<template>
  <div class="excel-workbook-viewer">
    <!-- Header with logo and formula bar -->
    <div class="viewer-header">
      <div class="header-left">
        <img src="/DuraCapital logo.png" alt="DuraCapital" class="logo" />
        <span class="excel-filename">{{ fileName || 'Excel Workbook' }}</span>
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
          </div>
        </div>

        <!-- Rows -->
        <div class="excel-rows-container" ref="rowsContainer">
          <div
            v-for="(row, rowIndex) in visibleRows"
            :key="rowIndex"
            class="excel-row"
          >
            <!-- Row header (number) -->
            <div class="excel-header-cell excel-row-header" :style="{ height: getRowHeight(rowIndex) }">
              {{ rowIndex + 1 }}
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
        <span>Detected Tables ({{ detectedTables.length }})</span>
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

function extractValuesIntelligently(data, instrumentType) {
  const requiredFields = getRequiredFieldMappings(instrumentType)
  let extracted = extractSingleInstrumentValues(data, requiredFields)

  const fieldKeys = Object.keys(requiredFields)
  for (const field of fieldKeys) {
    if (!extracted[field] || extracted[field] === '') {
      const synonyms = FINANCIAL_SYNONYMS[field] || [field]
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

const emit = defineEmits(['close', 'sheet-selected', 'single-instrument-extracted', 'table-isolated', 'multi-table-detect'])

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
  return '100px'
}

function getRowHeight(index) {
  return '25px'
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

  // Check if cell is in a detected table
  for (const table of detectedTables.value) {
    if (row >= table.startRow && row <= table.endRow &&
        col >= table.startCol && col <= table.endCol) {
      styles.backgroundColor = '#f8f9fa'
      styles.border = '1px solid #dee2e6'
      // Highlight header row
      if (row === table.startRow) {
        styles.backgroundColor = '#e3f2fd'
        styles.fontWeight = '600'
        styles.color = '#0d47a1'
      }
      break
    }
  }

  // Check merged ranges
  for (const range of mergedRanges.value) {
    if (row >= range.min_row && row <= range.max_row &&
        col >= range.min_col && col <= range.max_col) {
      if (row === range.min_row && col === range.min_col) {
        // Top-left cell of merge – expand
        const colspan = range.max_col - range.min_col + 1
        const rowspan = range.max_row - range.min_row + 1
        styles.width = `calc(${getColumnWidth(col)} * ${colspan})`
        styles.height = `calc(${getRowHeight(row)} * ${rowspan})`
        styles.backgroundColor = '#f0f4ff'
        styles.border = '1px solid #0B2044'
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
  
  // Check if cell has a formula
  if (cellFormulas.value.has(cellRef)) {
    selectedCellFormula.value = cellFormulas.value.get(cellRef)
  } else {
    selectedCellFormula.value = formatCellValue(cell)
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
        const extracted = extractValuesIntelligently(sheet.data, props.instrumentType)
        extractedPreviewValues.value = extracted
        // Emit extracted values to parent
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

function detectTables() {
  detectedTables.value = []
  const data = visibleRows.value
  if (!data || data.length === 0) return

  // Simple table detection: find contiguous regions with headers
  let inTable = false
  let tableStartRow = -1
  let tableStartCol = -1
  let tableEndRow = -1
  let tableEndCol = -1

  for (let row = 0; row < data.length; row++) {
    const rowData = data[row]
    if (!rowData) continue

    let nonEmptyCount = 0
    let firstNonEmptyCol = -1
    let lastNonEmptyCol = -1

    for (let col = 0; col < rowData.length; col++) {
      const cell = rowData[col]
      if (cell !== null && cell !== undefined && cell !== '') {
        nonEmptyCount++
        if (firstNonEmptyCol === -1) firstNonEmptyCol = col
        lastNonEmptyCol = col
      }
    }

    // If row has multiple non-empty cells, it could be part of a table
    if (nonEmptyCount >= 2) {
      if (!inTable) {
        // Start of a new table
        inTable = true
        tableStartRow = row
        tableStartCol = firstNonEmptyCol
        tableEndRow = row
        tableEndCol = lastNonEmptyCol
      } else {
        // Continue table
        tableEndRow = row
        tableEndCol = Math.max(tableEndCol, lastNonEmptyCol)
        tableStartCol = Math.min(tableStartCol, firstNonEmptyCol)
      }
    } else if (inTable && nonEmptyCount === 0) {
      // Empty row ends the table
      inTable = false
      if (tableEndRow - tableStartRow >= 1) {
        detectedTables.value.push({
          startRow: tableStartRow,
          endRow: tableEndRow,
          startCol: tableStartCol,
          endCol: tableEndCol,
          name: `Table ${detectedTables.value.length + 1}`
        })
      }
    }
  }

  // Add the last table if we ended while in one
  if (inTable && tableEndRow - tableStartRow >= 1) {
    detectedTables.value.push({
      startRow: tableStartRow,
      endRow: tableEndRow,
      startCol: tableStartCol,
      endCol: tableEndCol,
      name: `Table ${detectedTables.value.length + 1}`
    })
  }
}

function selectTable(table) {
  selectedTable.value = table
  isTableIsolationMode.value = true
  
  // Convert isolated table data to JSON format for mapping
  if (activeSheet.value && activeSheet.value.fullData) {
    const isolatedData = []
    const headers = []
    
    // Extract headers from the first row of the table
    for (let col = table.startCol; col <= table.endCol; col++) {
      const headerCell = activeSheet.value.fullData[table.startRow]?.[col]
      headers.push(headerCell || `Column ${col}`)
    }
    
    // Extract data rows (skip header row)
    for (let row = table.startRow + 1; row <= table.endRow; row++) {
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
    
    // Emit the isolated table data for mapping
    emit('table-isolated', {
      sheetName: activeSheet.value.name,
      tableName: table.name,
      data: isolatedData,
      headers: headers,
      tableRange: {
        startRow: table.startRow,
        endRow: table.endRow,
        startCol: table.startCol,
        endCol: table.endCol
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
      let maxRows = 100
      let maxCols = 50
      
      if (ref) {
        const range = XLSX.utils.decode_range(ref)
        totalRows = range.e.r - range.s.r + 1
        totalColumns = range.e.c - range.s.c + 1
        
        console.log(`ExcelWorkbookViewer: Sheet "${sheetName}" has ${totalRows} rows, ${totalColumns} columns`)
        
        // Skip sheets that are too large to prevent hanging
        if (totalRows > 10000 || totalColumns > 1000) {
          console.log(`ExcelWorkbookViewer: Skipping sheet "${sheetName}" - too large (${totalRows} rows x ${totalColumns} columns)`)
          continue
        }
        
        // Limit to 100 rows and 50 columns for viewer to prevent hang
        maxRows = Math.min(100, totalRows)
        maxCols = Math.min(50, totalColumns)
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
      
      // Get JSON data for detection - limit to same range as fullData
      const jsonData = XLSX.utils.sheet_to_json(worksheet, { 
        defval: '', 
        raw: false,
        range: maxRows
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
  height: 100%;
  background: #fff;
  border: 1px solid #e0e0e0;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  font-size: 13px;
  overflow: hidden;
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
  grid-template-rows: 25px 1fr;
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
}

.excel-rows-container {
  display: flex;
  flex-direction: column;
}

.excel-row {
  display: flex;
  min-height: 25px;
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
}

.excel-row-header {
  width: 40px;
  flex-shrink: 0;
  border-right: 1px solid #c0c0c0;
  border-bottom: 1px solid #e0e0e0;
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
  font-size: 11px;
  color: #333;
  font-weight: 500;
}
</style>