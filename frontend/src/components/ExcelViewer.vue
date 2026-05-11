<template>
  <div class="excel-viewer-container">
    <v-card class="stats-card" elevation="2">
      <v-card-title class="card-title">
        <v-icon class="title-icon">mdi-microsoft-excel</v-icon>
        Excel Preview (Editable)
      </v-card-title>
      <v-card-text class="pa-0">
        <div v-if="!tableData || tableData.length === 0" class="no-data-message">
          <v-icon size="64" color="#217346">mdi-table-off</v-icon>
          <h3>No Excel File Loaded</h3>
          <p>Upload an Excel file to see the preview</p>
        </div>
        <div v-else class="excel-viewer-wrapper">
          <!-- Excel Ribbon/Toolbar -->
          <div class="excel-ribbon">
            <div class="ribbon-tabs">
              <div class="ribbon-tab active">Home</div>
              <div class="ribbon-tab">Insert</div>
              <div class="ribbon-tab">Page Layout</div>
              <div class="ribbon-tab">Formulas</div>
              <div class="ribbon-tab">Data</div>
              <div class="ribbon-tab">Review</div>
              <div class="ribbon-tab">View</div>
            </div>
            <div class="ribbon-toolbar">
              <!-- File Menu -->
              <div class="ribbon-group">
                <div class="ribbon-group-title">File</div>
                <div class="ribbon-buttons">
                  <button class="ribbon-btn" @click="showFileMenu = !showFileMenu" title="File Menu">
                    <v-icon size="16">mdi-file-excel</v-icon>
                    <span>File</span>
                  </button>
                </div>
              </div>
              
              <!-- Font Group -->
              <div class="ribbon-group">
                <div class="ribbon-group-title">Font</div>
                <div class="ribbon-buttons">
                  <select v-model="cellFont" class="ribbon-select" @change="applyFont">
                    <option value="Calibri">Calibri</option>
                    <option value="Arial">Arial</option>
                    <option value="Times New Roman">Times New Roman</option>
                    <option value="Verdana">Verdana</option>
                  </select>
                  <select v-model="cellFontSize" class="ribbon-select small" @change="applyFontSize">
                    <option value="11">11</option>
                    <option value="12">12</option>
                    <option value="14">14</option>
                    <option value="16">16</option>
                    <option value="18">18</option>
                    <option value="20">20</option>
                  </select>
                  <button class="ribbon-btn" :class="{ active: isBold }" @click="toggleBold" title="Bold">
                    <strong>B</strong>
                  </button>
                  <button class="ribbon-btn" :class="{ active: isItalic }" @click="toggleItalic" title="Italic">
                    <em>I</em>
                  </button>
                  <button class="ribbon-btn" :class="{ active: isUnderline }" @click="toggleUnderline" title="Underline">
                    <u>U</u>
                  </button>
                  <div class="color-picker-wrapper">
                    <input type="color" v-model="cellColor" class="color-picker" @change="applyColor" title="Text Color">
                    <v-icon size="16" :color="cellColor">mdi-format-color-text</v-icon>
                  </div>
                  <div class="color-picker-wrapper">
                    <input type="color" v-model="cellBgColor" class="color-picker" @change="applyBgColor" title="Fill Color">
                    <v-icon size="16" :color="cellBgColor">mdi-format-color-fill</v-icon>
                  </div>
                </div>
              </div>
              
              <!-- Alignment Group -->
              <div class="ribbon-group">
                <div class="ribbon-group-title">Alignment</div>
                <div class="ribbon-buttons">
                  <button class="ribbon-btn" @click="setAlignment('left')" title="Align Left">
                    <v-icon size="16">mdi-format-align-left</v-icon>
                  </button>
                  <button class="ribbon-btn" @click="setAlignment('center')" title="Align Center">
                    <v-icon size="16">mdi-format-align-center</v-icon>
                  </button>
                  <button class="ribbon-btn" @click="setAlignment('right')" title="Align Right">
                    <v-icon size="16">mdi-format-align-right</v-icon>
                  </button>
                  <button class="ribbon-btn" @click="toggleWrapText" :class="{ active: wrapText }" title="Wrap Text">
                    <v-icon size="16">mdi-text-wrap</v-icon>
                  </button>
                </div>
              </div>
              
              <!-- Number Group -->
              <div class="ribbon-group">
                <div class="ribbon-group-title">Number</div>
                <div class="ribbon-buttons">
                  <select v-model="cellFormat" class="ribbon-select" @change="applyNumberFormat">
                    <option value="general">General</option>
                    <option value="number">Number</option>
                    <option value="currency">Currency</option>
                    <option value="percentage">Percentage</option>
                    <option value="date">Date</option>
                  </select>
                  <button class="ribbon-btn" @click="setNumberFormat('currency')" title="Currency">
                    <v-icon size="16">mdi-currency-usd</v-icon>
                  </button>
                  <button class="ribbon-btn" @click="setNumberFormat('percentage')" title="Percentage">
                    <v-icon size="16">mdi-percent</v-icon>
                  </button>
                </div>
              </div>
              
              <!-- Cells Group -->
              <div class="ribbon-group">
                <div class="ribbon-group-title">Cells</div>
                <div class="ribbon-buttons">
                  <button class="ribbon-btn" @click="insertRow" title="Insert Rows">
                    <v-icon size="16">mdi-table-row-plus-after</v-icon>
                  </button>
                  <button class="ribbon-btn" @click="deleteRow" title="Delete Rows">
                    <v-icon size="16">mdi-table-row-remove</v-icon>
                  </button>
                  <button class="ribbon-btn" @click="insertColumn" title="Insert Columns">
                    <v-icon size="16">mdi-table-column-plus-after</v-icon>
                  </button>
                  <button class="ribbon-btn" @click="deleteColumn" title="Delete Columns">
                    <v-icon size="16">mdi-table-column-remove</v-icon>
                  </button>
                  <button class="ribbon-btn" @click="formatPainter" title="Format Painter">
                    <v-icon size="16">mdi-format-painter</v-icon>
                  </button>
                </div>
              </div>
              
              <!-- Editing Group -->
              <div class="ribbon-group">
                <div class="ribbon-group-title">Editing</div>
                <div class="ribbon-buttons">
                  <button class="ribbon-btn" @click="cutCell" title="Cut">
                    <v-icon size="16">mdi-content-cut</v-icon>
                  </button>
                  <button class="ribbon-btn" @click="copyCell" title="Copy">
                    <v-icon size="16">mdi-content-copy</v-icon>
                  </button>
                  <button class="ribbon-btn" @click="pasteCell" title="Paste">
                    <v-icon size="16">mdi-content-paste</v-icon>
                  </button>
                  <button class="ribbon-btn" @click="insertFormula" title="Insert Function">
                    <v-icon size="16">mdi-function</v-icon>
                  </button>
                  <button class="ribbon-btn" @click="fillDown" title="Fill Down">
                    <v-icon size="16">mdi-arrow-down-bold</v-icon>
                  </button>
                  <button class="ribbon-btn" @click="fillRight" title="Fill Right">
                    <v-icon size="16">mdi-arrow-right-bold</v-icon>
                  </button>
                </div>
              </div>
              
              <!-- Alignment Group Extended -->
              <div class="ribbon-group">
                <div class="ribbon-group-title">Alignment</div>
                <div class="ribbon-buttons">
                  <button class="ribbon-btn" @click="setAlignment('left')" title="Align Left">
                    <v-icon size="16">mdi-format-align-left</v-icon>
                  </button>
                  <button class="ribbon-btn" @click="setAlignment('center')" title="Align Center">
                    <v-icon size="16">mdi-format-align-center</v-icon>
                  </button>
                  <button class="ribbon-btn" @click="setAlignment('right')" title="Align Right">
                    <v-icon size="16">mdi-format-align-right</v-icon>
                  </button>
                  <button class="ribbon-btn" @click="mergeAndCenter" title="Merge & Center">
                    <v-icon size="16">mdi-merge-horizontal</v-icon>
                  </button>
                  <button class="ribbon-btn" @click="toggleWrapText" :class="{ active: wrapText }" title="Wrap Text">
                    <v-icon size="16">mdi-text-wrap</v-icon>
                  </button>
                </div>
              </div>
            </div>
          </div>
          
          <!-- File Menu Dropdown -->
          <v-menu v-model="showFileMenu" :close-on-content-click="false">
            <template v-slot:activator="{ props }">
              <div></div>
            </template>
            <v-list>
              <v-list-item @click="downloadExcel">
                <v-list-item-title>Download Excel</v-list-item-title>
              </v-list-item>
              <v-list-item @click="printExcel">
                <v-list-item-title>Print</v-list-item-title>
              </v-list-item>
            </v-list>
          </v-menu>

          <!-- Formula Bar with Cell Reference -->
          <div class="formula-bar">
            <div class="cell-name-box">{{ cellReference }}</div>
            <div class="formula-icon">fx</div>
            <input
              v-model="formulaValue"
              class="formula-input"
              placeholder="Enter value or formula"
              @keydown.enter="applyFormula"
              @input="onFormulaInput"
            />
            <button class="formula-expand-btn" @click="expandFormulaBar">
              <v-icon size="16">mdi-chevron-down</v-icon>
            </button>
          </div>
          
          <!-- Excel Table -->
          <div class="excel-table-wrapper">
            <div class="excel-table-container" ref="tableContainer">
              <table class="excel-table">
                <thead>
                  <tr>
                    <th class="corner-header"></th>
                    <th 
                      v-for="(colIndex) in headers.length" 
                      :key="colIndex" 
                      class="column-header"
                      :class="{ 'selected-header': selectedColumn === colIndex - 1 }"
                      @click="selectColumn(colIndex - 1)"
                    >
                      {{ getColumnLetter(colIndex - 1) }}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(row, rowIndex) in tableData" :key="rowIndex">
                    <td 
                      class="row-header"
                      :class="{ 'selected-header': selectedRow === rowIndex }"
                      @click="selectRow(rowIndex)"
                    >
                      {{ rowIndex + 1 }}
                    </td>
                    <td
                      v-for="(cell, colIndex) in headers"
                      :key="`${rowIndex}-${colIndex}`"
                      class="excel-cell"
                      :class="{ 
                        'selected-cell': selectedCell.row === rowIndex && selectedCell.col === colIndex,
                        'active-cell': activeCell.row === rowIndex && activeCell.col === colIndex,
                        'selected-range': isInRange(rowIndex, colIndex)
                      }"
                      :style="getCellStyle(rowIndex, colIndex)"
                      @click="selectCell(rowIndex, colIndex, row[cell])"
                      @dblclick="editCell(rowIndex, colIndex)"
                      @mousedown="startRangeSelection(rowIndex, colIndex)"
                      @mouseover="updateRangeSelection(rowIndex, colIndex)"
                      @mouseup="endRangeSelection"
                    >
                      <span v-if="!(editingCell.row === rowIndex && editingCell.col === colIndex)" class="cell-content">{{ formatCellValue(row[cell]) }}</span>
                      <input 
                        v-else
                        v-model="editingCell.value"
                        class="cell-edit-input"
                        @blur="finishEditing(rowIndex, colIndex)"
                        @keydown.enter="finishEditing(rowIndex, colIndex)"
                        @keydown.esc="cancelEditing"
                        ref="editInput"
                      />
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            
            <!-- Scrollbars -->
            <div class="vertical-scrollbar" ref="verticalScrollbar">
              <div class="scrollbar-thumb" :style="{ height: verticalThumbHeight + '%' }"></div>
            </div>
            <div class="horizontal-scrollbar" ref="horizontalScrollbar">
              <div class="scrollbar-thumb" :style="{ width: horizontalThumbWidth + '%' }"></div>
            </div>
          </div>
          
          <!-- Sheet Tabs at Bottom -->
          <div class="sheet-tabs-bottom">
            <div class="sheet-tabs-container">
              <button
                v-for="(sheet, index) in sheetNames"
                :key="index"
                :class="['sheet-tab-bottom', { 'active-sheet': activeSheetIndex === index }]"
                @click="switchSheet(index)"
              >
                <v-icon size="14" class="sheet-icon">mdi-table</v-icon>
                {{ sheet }}
              </button>
              <button class="add-sheet-btn" @click="addSheet" title="Insert Worksheet">
                <v-icon size="18">mdi-plus</v-icon>
              </button>
            </div>
            <div class="sheet-scroll-buttons">
              <button class="scroll-btn" @click="scrollSheets(-1)" title="Scroll Left">
                <v-icon size="16">mdi-chevron-left</v-icon>
              </button>
              <button class="scroll-btn" @click="scrollSheets(1)" title="Scroll Right">
                <v-icon size="16">mdi-chevron-right</v-icon>
              </button>
            </div>
            <div class="zoom-controls">
              <button class="zoom-btn" @click="zoomOut" title="Zoom Out">
                <v-icon size="16">mdi-minus</v-icon>
              </button>
              <span class="zoom-level">{{ zoomLevel }}%</span>
              <button class="zoom-btn" @click="zoomIn" title="Zoom In">
                <v-icon size="16">mdi-plus</v-icon>
              </button>
            </div>
          </div>
          
          <!-- Status Bar -->
          <div class="status-bar">
            <div class="status-left">
              <span class="status-item">Ready</span>
              <span class="status-item" v-if="selectedCell.row >= 0 && selectedCell.col >= 0">
                {{ cellReference }}
              </span>
              <span class="status-item" v-if="selectedCell.row >= 0 && selectedCell.col >= 0">
                {{ getCellValue() }}
              </span>
            </div>
            <div class="status-right">
              <span class="status-item">{{ tableData.length }} rows</span>
              <span class="status-item">{{ headers.length }} columns</span>
            </div>
          </div>
        </div>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick, computed } from 'vue'
import * as XLSX from 'xlsx'

interface Props {
  fileBase64?: string
  fileName?: string
  data?: any[]
  headers?: string[]
}

const props = defineProps<Props>()

const emit = defineEmits<{
  (e: 'data-update', data: any[]): void
}>()

const tableData = ref<any[]>([])
const headers = ref<string[]>([])
const sheetNames = ref<string[]>([])
const activeSheetIndex = ref(0)
const workbook = ref<XLSX.WorkBook | null>(null)
const formulaValue = ref('')
const selectedCell = ref({ row: -1, col: -1 })
const activeCell = ref({ row: -1, col: -1 })
const editingCell = ref({ row: -1, col: -1, value: '' })
const cellReference = ref('A1')
const editInput = ref<HTMLInputElement | null>(null)
const showFileMenu = ref(false)

// Formatting state
const cellFont = ref('Calibri')
const cellFontSize = ref('11')
const cellColor = ref('#000000')
const cellBgColor = ref('#ffffff')
const isBold = ref(false)
const isItalic = ref(false)
const isUnderline = ref(false)
const wrapText = ref(false)
const cellFormat = ref('general')
const cellAlignment = ref('left')
const zoomLevel = ref(100)

// Cell styles storage
const cellStyles = ref<Map<string, any>>(new Map())

// Range selection
const rangeStart = ref({ row: -1, col: -1 })
const rangeEnd = ref({ row: -1, col: -1 })
const isSelectingRange = ref(false)

// Row/column selection
const selectedRow = ref(-1)
const selectedColumn = ref(-1)

// Scrollbar
const verticalThumbHeight = ref(50)
const horizontalThumbWidth = ref(50)

// Clipboard state
const clipboard = ref<{ value: any; style: any } | null>(null)
const clipboardOperation = ref<'copy' | 'cut' | null>(null)
const formatPainterActive = ref(false)
const formatPainterStyle = ref<any>(null)

const addRow = () => {
  const newRow: any = {}
  headers.value.forEach(header => {
    newRow[header] = ''
  })
  tableData.value.push(newRow)
  emit('data-update', tableData.value)
}

// Formatting functions
const applyFont = () => {
  if (selectedCell.value.row >= 0 && selectedCell.value.col >= 0) {
    const key = `${selectedCell.value.row}-${selectedCell.value.col}`
    const style = cellStyles.value.get(key) || {}
    style.font = cellFont.value
    cellStyles.value.set(key, style)
  }
}

const applyFontSize = () => {
  if (selectedCell.value.row >= 0 && selectedCell.value.col >= 0) {
    const key = `${selectedCell.value.row}-${selectedCell.value.col}`
    const style = cellStyles.value.get(key) || {}
    style.fontSize = cellFontSize.value + 'px'
    cellStyles.value.set(key, style)
  }
}

const toggleBold = () => {
  isBold.value = !isBold.value
  if (selectedCell.value.row >= 0 && selectedCell.value.col >= 0) {
    const key = `${selectedCell.value.row}-${selectedCell.value.col}`
    const style = cellStyles.value.get(key) || {}
    style.fontWeight = isBold.value ? 'bold' : 'normal'
    cellStyles.value.set(key, style)
  }
}

const toggleItalic = () => {
  isItalic.value = !isItalic.value
  if (selectedCell.value.row >= 0 && selectedCell.value.col >= 0) {
    const key = `${selectedCell.value.row}-${selectedCell.value.col}`
    const style = cellStyles.value.get(key) || {}
    style.fontStyle = isItalic.value ? 'italic' : 'normal'
    cellStyles.value.set(key, style)
  }
}

const toggleUnderline = () => {
  isUnderline.value = !isUnderline.value
  if (selectedCell.value.row >= 0 && selectedCell.value.col >= 0) {
    const key = `${selectedCell.value.row}-${selectedCell.value.col}`
    const style = cellStyles.value.get(key) || {}
    style.textDecoration = isUnderline.value ? 'underline' : 'none'
    cellStyles.value.set(key, style)
  }
}

const applyColor = () => {
  if (selectedCell.value.row >= 0 && selectedCell.value.col >= 0) {
    const key = `${selectedCell.value.row}-${selectedCell.value.col}`
    const style = cellStyles.value.get(key) || {}
    style.color = cellColor.value
    cellStyles.value.set(key, style)
  }
}

const applyBgColor = () => {
  if (selectedCell.value.row >= 0 && selectedCell.value.col >= 0) {
    const key = `${selectedCell.value.row}-${selectedCell.value.col}`
    const style = cellStyles.value.get(key) || {}
    style.backgroundColor = cellBgColor.value
    cellStyles.value.set(key, style)
  }
}

const setAlignment = (align: string) => {
  cellAlignment.value = align
  if (selectedCell.value.row >= 0 && selectedCell.value.col >= 0) {
    const key = `${selectedCell.value.row}-${selectedCell.value.col}`
    const style = cellStyles.value.get(key) || {}
    style.textAlign = align
    cellStyles.value.set(key, style)
  }
}

const toggleWrapText = () => {
  wrapText.value = !wrapText.value
  if (selectedCell.value.row >= 0 && selectedCell.value.col >= 0) {
    const key = `${selectedCell.value.row}-${selectedCell.value.col}`
    const style = cellStyles.value.get(key) || {}
    style.whiteSpace = wrapText.value ? 'pre-wrap' : 'nowrap'
    cellStyles.value.set(key, style)
  }
}

const applyNumberFormat = () => {
  if (selectedCell.value.row >= 0 && selectedCell.value.col >= 0) {
    const key = `${selectedCell.value.row}-${selectedCell.value.col}`
    const style = cellStyles.value.get(key) || {}
    style.numberFormat = cellFormat.value
    cellStyles.value.set(key, style)
  }
}

const setNumberFormat = (format: string) => {
  cellFormat.value = format
  applyNumberFormat()
}

const insertRow = () => {
  const newRow: any = {}
  headers.value.forEach(header => {
    newRow[header] = ''
  })
  if (selectedCell.value.row >= 0) {
    tableData.value.splice(selectedCell.value.row + 1, 0, newRow)
  } else {
    tableData.value.push(newRow)
  }
  emit('data-update', tableData.value)
}

const deleteRow = () => {
  if (selectedCell.value.row >= 0) {
    tableData.value.splice(selectedCell.value.row, 1)
    selectedCell.value = { row: -1, col: -1 }
    emit('data-update', tableData.value)
  }
}

const fillDown = () => {
  if (selectedCell.value.row >= 0 && selectedCell.value.col >= 0) {
    const header = headers.value[selectedCell.value.col]
    const value = tableData.value[selectedCell.value.row][header]
    for (let i = selectedCell.value.row + 1; i < tableData.value.length; i++) {
      tableData.value[i][header] = value
    }
    emit('data-update', tableData.value)
  }
}

const expandFormulaBar = () => {
  // Toggle formula bar height
  const formulaBar = document.querySelector('.formula-bar') as HTMLElement
  if (formulaBar) {
    if (formulaBar.style.height === '60px') {
      formulaBar.style.height = '36px'
    } else {
      formulaBar.style.height = '60px'
    }
  }
}

const getColumnLetter = (colIndex: number) => {
  let letter = ''
  let temp = colIndex
  while (temp >= 0) {
    letter = String.fromCharCode((temp % 26) + 65) + letter
    temp = Math.floor(temp / 26) - 1
  }
  return letter
}

const selectColumn = (colIndex: number) => {
  selectedColumn.value = colIndex
  selectedRow.value = -1
}

const selectRow = (rowIndex: number) => {
  selectedRow.value = rowIndex
  selectedColumn.value = -1
}

const isInRange = (row: number, col: number) => {
  if (rangeStart.value.row === -1 || rangeEnd.value.row === -1) return false
  const minRow = Math.min(rangeStart.value.row, rangeEnd.value.row)
  const maxRow = Math.max(rangeStart.value.row, rangeEnd.value.row)
  const minCol = Math.min(rangeStart.value.col, rangeEnd.value.col)
  const maxCol = Math.max(rangeStart.value.col, rangeEnd.value.col)
  return row >= minRow && row <= maxRow && col >= minCol && col <= maxCol
}

const getCellStyle = (row: number, col: number) => {
  const key = `${row}-${col}`
  const style = cellStyles.value.get(key) || {}
  return {
    fontFamily: style.font || cellFont.value,
    fontSize: style.fontSize || cellFontSize.value + 'px',
    color: style.color || cellColor.value,
    backgroundColor: style.backgroundColor || cellBgColor.value,
    fontWeight: style.fontWeight || (isBold.value ? 'bold' : 'normal'),
    fontStyle: style.fontStyle || (isItalic.value ? 'italic' : 'normal'),
    textDecoration: style.textDecoration || (isUnderline.value ? 'underline' : 'none'),
    textAlign: style.textAlign || cellAlignment.value,
    whiteSpace: style.whiteSpace || (wrapText.value ? 'pre-wrap' : 'nowrap')
  }
}

const startRangeSelection = (row: number, col: number) => {
  isSelectingRange.value = true
  rangeStart.value = { row, col }
  rangeEnd.value = { row, col }
}

const updateRangeSelection = (row: number, col: number) => {
  if (isSelectingRange.value) {
    rangeEnd.value = { row, col }
  }
}

const endRangeSelection = () => {
  isSelectingRange.value = false
}

const formatCellValue = (value: any) => {
  if (value === null || value === undefined) return ''
  const strValue = String(value)
  
  if (cellFormat.value === 'currency') {
    const num = parseFloat(strValue.replace(/[^0-9.-]/g, ''))
    if (!isNaN(num)) {
      return '$' + num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
    }
  } else if (cellFormat.value === 'percentage') {
    const num = parseFloat(strValue.replace(/[^0-9.-]/g, ''))
    if (!isNaN(num)) {
      return (num * 100).toFixed(2) + '%'
    }
  } else if (cellFormat.value === 'number') {
    const num = parseFloat(strValue.replace(/[^0-9.-]/g, ''))
    if (!isNaN(num)) {
      return num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
    }
  }
  
  return strValue
}

const zoomIn = () => {
  if (zoomLevel.value < 200) {
    zoomLevel.value += 10
  }
}

const zoomOut = () => {
  if (zoomLevel.value > 50) {
    zoomLevel.value -= 10
  }
}

const getCellValue = () => {
  if (selectedCell.value.row >= 0 && selectedCell.value.col >= 0) {
    const header = headers.value[selectedCell.value.col]
    return tableData.value[selectedCell.value.row][header] || ''
  }
  return ''
}

// Column operations
const insertColumn = () => {
  const newHeader = `Column_${headers.value.length + 1}`
  headers.value.push(newHeader)
  tableData.value.forEach(row => {
    row[newHeader] = ''
  })
  emit('data-update', tableData.value)
}

const deleteColumn = () => {
  if (selectedCell.value.col >= 0) {
    const header = headers.value[selectedCell.value.col]
    headers.value.splice(selectedCell.value.col, 1)
    tableData.value.forEach(row => {
      delete row[header]
    })
    selectedCell.value = { row: -1, col: -1 }
    emit('data-update', tableData.value)
  }
}

// Clipboard operations
const cutCell = () => {
  if (selectedCell.value.row >= 0 && selectedCell.value.col >= 0) {
    const header = headers.value[selectedCell.value.col]
    const key = `${selectedCell.value.row}-${selectedCell.value.col}`
    clipboard.value = {
      value: tableData.value[selectedCell.value.row][header],
      style: cellStyles.value.get(key) || {}
    }
    clipboardOperation.value = 'cut'
    tableData.value[selectedCell.value.row][header] = ''
    emit('data-update', tableData.value)
  }
}

const copyCell = () => {
  if (selectedCell.value.row >= 0 && selectedCell.value.col >= 0) {
    const header = headers.value[selectedCell.value.col]
    const key = `${selectedCell.value.row}-${selectedCell.value.col}`
    clipboard.value = {
      value: tableData.value[selectedCell.value.row][header],
      style: cellStyles.value.get(key) || {}
    }
    clipboardOperation.value = 'copy'
  }
}

const pasteCell = () => {
  if (clipboard.value && selectedCell.value.row >= 0 && selectedCell.value.col >= 0) {
    const header = headers.value[selectedCell.value.col]
    const key = `${selectedCell.value.row}-${selectedCell.value.col}`
    tableData.value[selectedCell.value.row][header] = clipboard.value.value
    if (clipboard.value.style) {
      cellStyles.value.set(key, clipboard.value.style)
    }
    emit('data-update', tableData.value)
    
    if (clipboardOperation.value === 'cut') {
      clipboard.value = null
      clipboardOperation.value = null
    }
  }
}

// Format painter
const formatPainter = () => {
  if (formatPainterActive.value) {
    formatPainterActive.value = false
    formatPainterStyle.value = null
  } else if (selectedCell.value.row >= 0 && selectedCell.value.col >= 0) {
    const key = `${selectedCell.value.row}-${selectedCell.value.col}`
    formatPainterStyle.value = cellStyles.value.get(key) || {}
    formatPainterActive.value = true
  }
}

// Merge and center
const mergeAndCenter = () => {
  if (rangeStart.value.row >= 0 && rangeEnd.value.row >= 0) {
    const minRow = Math.min(rangeStart.value.row, rangeEnd.value.row)
    const maxRow = Math.max(rangeStart.value.row, rangeEnd.value.row)
    const minCol = Math.min(rangeStart.value.col, rangeEnd.value.col)
    const maxCol = Math.max(rangeStart.value.col, rangeEnd.value.col)
    
    // Store merge info in all cells in the range
    for (let row = minRow; row <= maxRow; row++) {
      for (let col = minCol; col <= maxCol; col++) {
        const key = `${row}-${col}`
        const style = cellStyles.value.get(key) || {}
        style.merged = true
        style.mergeStart = `${minRow}-${minCol}`
        style.mergeEnd = `${maxRow}-${maxCol}`
        style.textAlign = 'center'
        cellStyles.value.set(key, style)
      }
    }
  }
}

// Fill right
const fillRight = () => {
  if (selectedCell.value.row >= 0 && selectedCell.value.col >= 0) {
    const value = tableData.value[selectedCell.value.row][headers.value[selectedCell.value.col]]
    for (let i = selectedCell.value.col + 1; i < headers.value.length; i++) {
      tableData.value[selectedCell.value.row][headers.value[i]] = value
    }
    emit('data-update', tableData.value)
  }
}

const insertFormula = () => {
  if (activeCell.value.row >= 0 && activeCell.value.col >= 0) {
    const header = headers.value[activeCell.value.col]
    formulaValue.value = '='
    tableData.value[activeCell.value.row][header] = '='
    emit('data-update', tableData.value)
  }
}

const formatCells = () => {
  alert('Formatting options would appear here (bold, italic, colors, etc.)')
}

const downloadExcel = () => {
  try {
    const worksheet = XLSX.utils.json_to_sheet(tableData.value)
    const newWorkbook = XLSX.utils.book_new()
    XLSX.utils.book_append_sheet(newWorkbook, worksheet, 'Data')
    XLSX.writeFile(newWorkbook, 'dataset.xlsx')
    showFileMenu.value = false
  } catch (error) {
    console.error('Error downloading Excel:', error)
  }
}

const printExcel = () => {
  window.print()
  showFileMenu.value = false
}

const getCellReference = (row: number, col: number) => {
  const colLetter = String.fromCharCode(65 + (col % 26))
  return `${colLetter}${row + 1}`
}

const switchSheet = (index: number) => {
  activeSheetIndex.value = index
  loadSheet(index)
}

const scrollSheets = (direction: number) => {
  const newIndex = activeSheetIndex.value + direction
  if (newIndex >= 0 && newIndex < sheetNames.value.length) {
    switchSheet(newIndex)
  }
}

const addSheet = () => {
  const newSheetName = `Sheet${sheetNames.value.length + 1}`
  sheetNames.value = [...sheetNames.value, newSheetName]
  // In a real implementation, you would add a new sheet to the workbook
}

const loadSheet = (index: number) => {
  if (!workbook.value) return
  
  const sheetName = sheetNames.value[index]
  const worksheet = workbook.value.Sheets[sheetName]
  const jsonData = XLSX.utils.sheet_to_json(worksheet) as any[]
  
  if (jsonData.length > 0 && jsonData[0]) {
    headers.value = Object.keys(jsonData[0])
    tableData.value = jsonData
  } else {
    headers.value = []
    tableData.value = []
  }
  
  // Reset selection
  selectedCell.value = { row: -1, col: -1 }
  activeCell.value = { row: -1, col: -1 }
  formulaValue.value = ''
  cellReference.value = 'A1'
}

const selectCell = (rowIndex: number, colIndex: number, value: any) => {
  selectedCell.value = { row: rowIndex, col: colIndex }
  activeCell.value = { row: rowIndex, col: colIndex }
  cellReference.value = getCellReference(rowIndex, colIndex)
  
  // Show value in formula bar
  const cellValue = value !== undefined && value !== null ? String(value) : ''
  formulaValue.value = cellValue.startsWith('=') ? cellValue : cellValue
}

const editCell = (rowIndex: number, colIndex: number) => {
  const header = headers.value[colIndex]
  const value = tableData.value[rowIndex][header]
  editingCell.value = { 
    row: rowIndex, 
    col: colIndex, 
    value: value !== undefined && value !== null ? String(value) : ''
  }
  
  nextTick(() => {
    if (editInput.value) {
      editInput.value.focus()
      editInput.value.select()
    }
  })
}

const finishEditing = (rowIndex: number, colIndex: number) => {
  if (editingCell.value.row === rowIndex && editingCell.value.col === colIndex) {
    const header = headers.value[colIndex]
    const newValue = editingCell.value.value
    
    // Check if it's a formula
    if (newValue.startsWith('=')) {
      // Store as formula (in a real implementation, you would evaluate it)
      tableData.value[rowIndex][header] = newValue
    } else {
      tableData.value[rowIndex][header] = newValue
    }
    
    emit('data-update', tableData.value)
  }
  
  editingCell.value = { row: -1, col: -1, value: '' }
}

const cancelEditing = () => {
  editingCell.value = { row: -1, col: -1, value: '' }
}

const onFormulaInput = () => {
  // Update the active cell value in real-time
  if (activeCell.value.row >= 0 && activeCell.value.col >= 0) {
    const header = headers.value[activeCell.value.col]
    tableData.value[activeCell.value.row][header] = formulaValue.value
  }
}

const applyFormula = () => {
  if (activeCell.value.row >= 0 && activeCell.value.col >= 0) {
    const header = headers.value[activeCell.value.col]
    tableData.value[activeCell.value.row][header] = formulaValue.value
    emit('data-update', tableData.value)
  }
}

const loadExcelFile = (base64: string) => {
  try {
    console.log('Loading Excel file from base64...')
    const binaryString = atob(base64)
    const bytes = new Uint8Array(binaryString.length)
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i)
    }
    
    const workbookData = XLSX.read(bytes, { type: 'array', cellStyles: true })
    workbook.value = workbookData
    sheetNames.value = workbookData.SheetNames
    activeSheetIndex.value = 0
    loadSheet(0)
    
    const worksheet = workbookData.Sheets[sheetNames.value[0]]
    const jsonData = XLSX.utils.sheet_to_json(worksheet)
    emit('data-update', jsonData)
    
    console.log('Excel file loaded with sheets:', sheetNames.value)
    console.log('Table data rows:', tableData.value.length)
    console.log('Headers:', headers.value)
  } catch (error) {
    console.error('Error loading Excel file:', error)
  }
}

const loadOldData = (data: any[], headerList?: string[]) => {
  if (data && data.length > 0) {
    tableData.value = data
    const computedHeaders = headerList || Object.keys(data[0])
    headers.value = computedHeaders
    sheetNames.value = ['Data']
    activeSheetIndex.value = 0
    emit('data-update', data)
    console.log('Old format data loaded:', data.length, 'rows')
  }
}

watch(() => props.fileBase64, (newBase64) => {
  console.log('fileBase64 changed:', !!newBase64)
  if (newBase64) {
    loadExcelFile(newBase64)
  }
}, { immediate: true })

watch(() => props.data, (newData) => {
  console.log('data changed:', newData?.length)
  if (newData && newData.length > 0 && !props.fileBase64) {
    loadOldData(newData, props.headers)
  }
}, { immediate: true })
</script>

<style scoped>
.excel-viewer-container {
  width: 100%;
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
  color: #217346;
}

.no-data-message {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  text-align: center;
  background: #f9f9f9;
  min-height: 400px;
}

.no-data-message h3 {
  color: #0B2A44;
  margin: 16px 0 8px 0;
}

.no-data-message p {
  color: #666;
  margin: 4px 0;
}

.excel-viewer-wrapper {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 700px;
}

/* Excel Ribbon */
.excel-ribbon {
  background: #217346;
  border-bottom: 1px solid #d4d4d4;
}

.ribbon-tabs {
  display: flex;
  background: #1e5f3a;
  padding: 0 8px;
}

.ribbon-tab {
  padding: 8px 16px;
  color: rgba(255, 255, 255, 0.7);
  font-size: 12px;
  cursor: pointer;
  border-bottom: 3px solid transparent;
  transition: all 0.2s;
}

.ribbon-tab:hover {
  color: white;
  background: rgba(255, 255, 255, 0.1);
}

.ribbon-tab.active {
  color: white;
  border-bottom-color: #ffffff;
  background: rgba(255, 255, 255, 0.15);
}

.ribbon-toolbar {
  display: flex;
  gap: 4px;
  padding: 8px 12px;
  background: #f3f2f1;
  border-bottom: 1px solid #d4d4d4;
}

.ribbon-group {
  padding: 4px 8px;
  border-right: 1px solid #d4d4d4;
}

.ribbon-group:last-child {
  border-right: none;
}

.ribbon-group-title {
  font-size: 10px;
  color: #666;
  margin-bottom: 4px;
  text-transform: uppercase;
  font-weight: 600;
}

.ribbon-buttons {
  display: flex;
  gap: 2px;
  align-items: center;
}

.ribbon-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4px 8px;
  background: white;
  border: 1px solid #d4d4d4;
  border-radius: 2px;
  cursor: pointer;
  font-size: 11px;
  color: #333;
  min-width: 32px;
  min-height: 32px;
  transition: all 0.15s;
}

.ribbon-btn:hover {
  background: #e3f2fd;
  border-color: #217346;
}

.ribbon-btn.active {
  background: #217346;
  color: white;
  border-color: #217346;
}

.ribbon-select {
  padding: 4px 8px;
  border: 1px solid #d4d4d4;
  border-radius: 2px;
  font-size: 11px;
  background: white;
  cursor: pointer;
}

.ribbon-select.small {
  width: 50px;
}

.color-picker-wrapper {
  position: relative;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.color-picker {
  position: absolute;
  width: 100%;
  height: 100%;
  opacity: 0;
  cursor: pointer;
}

/* Formula Bar */
.formula-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  background: #ffffff;
  border-bottom: 1px solid #d4d4d4;
  transition: height 0.2s;
}

.cell-name-box {
  width: 60px;
  padding: 4px 8px;
  background: white;
  border: 1px solid #d4d4d4;
  text-align: center;
  font-size: 12px;
  font-weight: 600;
  color: #217346;
}

.formula-icon {
  font-style: italic;
  font-weight: bold;
  color: #217346;
  font-size: 14px;
}

.formula-input {
  flex: 1;
  padding: 6px 10px;
  border: 1px solid #d4d4d4;
  border-radius: 2px;
  font-size: 12px;
  font-family: 'Calibri', 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

.formula-input:focus {
  outline: none;
  border-color: #217346;
}

.formula-expand-btn {
  padding: 4px 8px;
  background: white;
  border: 1px solid #d4d4d4;
  border-radius: 2px;
  cursor: pointer;
}

.formula-expand-btn:hover {
  background: #f3f2f1;
}

/* Excel Table */
.excel-table-wrapper {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  position: relative;
}

.excel-table-container {
  flex: 1;
  overflow: auto;
  border: 1px solid #d4d4d4;
  position: relative;
}

.excel-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 11px;
  font-family: 'Calibri', 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  transform-origin: top left;
}

.corner-header {
  background: #d4d4d4;
  border: 1px solid #999;
  min-width: 40px;
  width: 40px;
}

.column-header {
  background: #d4d4d4;
  color: #333;
  font-weight: 600;
  padding: 6px 10px;
  text-align: center;
  border: 1px solid #999;
  border-bottom: 1px solid #999;
  white-space: nowrap;
  min-width: 100px;
  cursor: pointer;
  user-select: none;
}

.column-header:hover {
  background: #c5c5c5;
}

.column-header.selected-header {
  background: #217346;
  color: white;
}

.row-header {
  background: #d4d4d4;
  color: #333;
  font-weight: 600;
  text-align: center;
  padding: 4px 8px;
  border: 1px solid #999;
  border-right: 1px solid #999;
  min-width: 40px;
  width: 40px;
  cursor: pointer;
  user-select: none;
}

.row-header:hover {
  background: #c5c5c5;
}

.row-header.selected-header {
  background: #217346;
  color: white;
}

.excel-cell {
  padding: 4px 8px;
  border: 1px solid #d4d4d4;
  min-width: 80px;
  cursor: pointer;
  outline: none;
  position: relative;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.excel-cell:hover {
  background-color: #e3f2fd;
}

.excel-cell.selected-cell {
  background-color: #bbdefb;
}

.excel-cell.active-cell {
  border: 2px solid #217346;
  z-index: 10;
}

.excel-cell.selected-range {
  background-color: #e3f2fd;
}

.cell-content {
  display: block;
}

.cell-edit-input {
  width: 100%;
  padding: 2px 4px;
  border: 1px solid #217346;
  font-size: 11px;
  font-family: 'Calibri', 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  background: white;
}

.cell-edit-input:focus {
  outline: none;
}

.excel-table tbody tr:nth-child(even) .excel-cell:not(.selected-cell):not(.active-cell):not(.selected-range) {
  background-color: #f8f8f8;
}

/* Scrollbars */
.vertical-scrollbar {
  position: absolute;
  right: 0;
  top: 0;
  width: 12px;
  height: 100%;
  background: #f1f1f1;
  border-left: 1px solid #d4d4d4;
}

.horizontal-scrollbar {
  position: absolute;
  bottom: 0;
  left: 40px;
  right: 0;
  height: 12px;
  background: #f1f1f1;
  border-top: 1px solid #d4d4d4;
}

.scrollbar-thumb {
  background: #c5c5c5;
  border-radius: 2px;
}

.scrollbar-thumb:hover {
  background: #999;
}

/* Sheet Tabs */
.sheet-tabs-bottom {
  display: flex;
  align-items: center;
  padding: 4px 8px;
  background: #217346;
  border-top: 1px solid #d4d4d4;
  gap: 8px;
}

.sheet-tabs-container {
  display: flex;
  gap: 2px;
  flex: 1;
  overflow-x: auto;
  min-width: 0;
}

.sheet-tab-bottom {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  background: rgba(255, 255, 255, 0.2);
  color: white;
  border: none;
  border-radius: 3px;
  cursor: pointer;
  font-size: 11px;
  font-weight: 500;
  white-space: nowrap;
  transition: all 0.2s;
}

.sheet-icon {
  font-size: 12px;
}

.sheet-tab-bottom:hover {
  background: rgba(255, 255, 255, 0.3);
}

.sheet-tab-bottom.active-sheet {
  background: white;
  color: #217346;
  font-weight: 600;
}

.add-sheet-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 6px 10px;
  background: rgba(255, 255, 255, 0.2);
  color: white;
  border: none;
  border-radius: 3px;
  cursor: pointer;
  font-size: 18px;
  font-weight: bold;
  min-width: 28px;
  height: 28px;
  transition: background 0.2s;
}

.add-sheet-btn:hover {
  background: rgba(255, 255, 255, 0.3);
}

.sheet-scroll-buttons {
  display: flex;
  gap: 2px;
}

.scroll-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 4px 8px;
  background: rgba(255, 255, 255, 0.2);
  color: white;
  border: none;
  border-radius: 3px;
  cursor: pointer;
  font-size: 12px;
  min-width: 28px;
  height: 28px;
  transition: background 0.2s;
}

.scroll-btn:hover {
  background: rgba(255, 255, 255, 0.3);
}

/* Zoom Controls */
.zoom-controls {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 8px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 3px;
}

.zoom-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 4px 8px;
  background: rgba(255, 255, 255, 0.2);
  color: white;
  border: none;
  border-radius: 2px;
  cursor: pointer;
  font-size: 14px;
  min-width: 24px;
  height: 24px;
  transition: background 0.2s;
}

.zoom-btn:hover {
  background: rgba(255, 255, 255, 0.3);
}

.zoom-level {
  color: white;
  font-size: 11px;
  font-weight: 600;
  min-width: 40px;
  text-align: center;
}

/* Status Bar */
.status-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 12px;
  background: #217346;
  border-top: 1px solid #d4d4d4;
  color: white;
  font-size: 11px;
}

.status-left,
.status-right {
  display: flex;
  gap: 16px;
  align-items: center;
}

.status-item {
  color: rgba(255, 255, 255, 0.9);
}

/* Responsive */
@media (max-width: 768px) {
  .ribbon-toolbar {
    overflow-x: auto;
  }
  
  .ribbon-group {
    min-width: max-content;
  }
}
</style>
