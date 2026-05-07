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
          <div class="excel-toolbar">
            <div class="toolbar-group">
              <v-btn size="small" variant="text" icon="mdi-file-excel" color="#217346"></v-btn>
              <span class="toolbar-label">File</span>
            </div>
            <div class="toolbar-group">
              <v-btn size="small" variant="text" icon="mdi-home" color="#217346"></v-btn>
              <span class="toolbar-label">Home</span>
            </div>
            <div class="toolbar-group">
              <v-btn size="small" variant="text" icon="mdi-insert" color="#217346"></v-btn>
              <span class="toolbar-label">Insert</span>
            </div>
            <div class="toolbar-group">
              <v-btn size="small" variant="text" icon="mdi-formula" color="#217346"></v-btn>
              <span class="toolbar-label">Formulas</span>
            </div>
            <div class="toolbar-group">
              <v-btn size="small" variant="text" icon="mdi-palette" color="#217346"></v-btn>
              <span class="toolbar-label">Format</span>
            </div>
          </div>

          <!-- Formula Bar with Cell Reference -->
          <div class="formula-bar">
            <div class="cell-reference">{{ cellReference }}</div>
            <div class="formula-label">fx</div>
            <input
              v-model="formulaValue"
              class="formula-input"
              placeholder="Enter value or formula"
              @keydown.enter="applyFormula"
              @input="onFormulaInput"
            />
          </div>
          
          <!-- Excel Table -->
          <div class="excel-table-wrapper">
            <div class="excel-table-container">
              <table class="excel-table">
                <thead>
                  <tr>
                    <th class="row-number-header"></th>
                    <th v-for="(header, colIndex) in headers" :key="colIndex" class="excel-header">
                      {{ header }}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(row, rowIndex) in tableData" :key="rowIndex">
                    <td class="row-number">{{ rowIndex + 1 }}</td>
                    <td
                      v-for="(cell, colIndex) in headers"
                      :key="`${rowIndex}-${colIndex}`"
                      class="excel-cell"
                      :class="{ 
                        'selected-cell': selectedCell.row === rowIndex && selectedCell.col === colIndex,
                        'active-cell': activeCell.row === rowIndex && activeCell.col === colIndex
                      }"
                      @click="selectCell(rowIndex, colIndex, row[cell])"
                      @dblclick="editCell(rowIndex, colIndex)"
                    >
                      <span v-if="!(editingCell.row === rowIndex && editingCell.col === colIndex)">{{ row[cell] }}</span>
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
                {{ sheet }}
              </button>
              <button class="add-sheet-btn" @click="addSheet">+</button>
            </div>
            <div class="sheet-scroll-buttons">
              <button class="scroll-btn" @click="scrollSheets(-1)">◀</button>
              <button class="scroll-btn" @click="scrollSheets(1)">▶</button>
            </div>
          </div>
        </div>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
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
  min-height: 600px;
}

.excel-toolbar {
  display: flex;
  gap: 20px;
  padding: 8px 12px;
  background: #217346;
  border-bottom: 1px solid #d4d4d4;
}

.toolbar-group {
  display: flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
}

.toolbar-group:hover {
  background: rgba(255, 255, 255, 0.1);
}

.toolbar-label {
  color: white;
  font-size: 12px;
  font-weight: 500;
}

.formula-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  background: #f3f3f3;
  border-bottom: 1px solid #d4d4d4;
}

.cell-reference {
  width: 50px;
  padding: 4px 8px;
  background: white;
  border: 1px solid #d4d4d4;
  text-align: center;
  font-size: 12px;
  font-weight: 600;
  color: #217346;
}

.formula-label {
  font-style: italic;
  font-weight: bold;
  color: #217346;
  font-size: 14px;
}

.formula-input {
  flex: 1;
  padding: 4px 8px;
  border: 1px solid #d4d4d4;
  border-radius: 2px;
  font-size: 12px;
  font-family: 'Calibri', 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

.formula-input:focus {
  outline: none;
  border-color: #217346;
}

.excel-table-wrapper {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.excel-table-container {
  flex: 1;
  overflow: auto;
  border: 1px solid #d4d4d4;
}

.excel-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
  font-family: 'Calibri', 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

.excel-header {
  background: #217346;
  color: white;
  font-weight: 600;
  padding: 6px 10px;
  text-align: center;
  border-right: 1px solid rgba(255, 255, 255, 0.2);
  border-bottom: 1px solid rgba(255, 255, 255, 0.2);
  white-space: nowrap;
  min-width: 100px;
}

.row-number-header {
  background: #217346;
  color: white;
  font-weight: 600;
  padding: 6px 10px;
  text-align: center;
  border-bottom: 1px solid rgba(255, 255, 255, 0.2);
  min-width: 40px;
}

.row-number {
  background-color: #f3f3f3;
  color: #666;
  font-weight: bold;
  text-align: center;
  padding: 4px 8px;
  border-right: 1px solid #d4d4d4;
  border-bottom: 1px solid #d4d4d4;
  min-width: 40px;
}

.excel-cell {
  padding: 4px 8px;
  border-right: 1px solid #d4d4d4;
  border-bottom: 1px solid #d4d4d4;
  min-width: 80px;
  cursor: pointer;
  outline: none;
  position: relative;
}

.excel-cell:hover {
  background-color: #f0f4ff;
}

.excel-cell.selected-cell {
  background-color: #e3f2fd;
}

.excel-cell.active-cell {
  border: 2px solid #217346;
}

.cell-edit-input {
  width: 100%;
  padding: 2px 4px;
  border: 1px solid #217346;
  font-size: 12px;
  font-family: 'Calibri', 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  background: white;
}

.cell-edit-input:focus {
  outline: none;
}

.excel-table tbody tr:nth-child(even) .excel-cell {
  background-color: #f8f8f8;
}

.sheet-tabs-bottom {
  display: flex;
  align-items: center;
  padding: 6px 12px;
  background: #217346;
  border-top: 1px solid #d4d4d4;
}

.sheet-tabs-container {
  display: flex;
  gap: 2px;
  flex: 1;
  overflow: hidden;
}

.sheet-tab-bottom {
  padding: 6px 16px;
  background: rgba(255, 255, 255, 0.2);
  color: white;
  border: none;
  border-radius: 4px 4px 0 0;
  cursor: pointer;
  font-size: 12px;
  font-weight: 500;
  white-space: nowrap;
  min-width: 80px;
  transition: background 0.2s;
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
  padding: 6px 12px;
  background: rgba(255, 255, 255, 0.2);
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 16px;
  font-weight: bold;
  min-width: 30px;
}

.add-sheet-btn:hover {
  background: rgba(255, 255, 255, 0.3);
}

.sheet-scroll-buttons {
  display: flex;
  gap: 4px;
  margin-left: 8px;
}

.scroll-btn {
  padding: 4px 8px;
  background: rgba(255, 255, 255, 0.2);
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
}

.scroll-btn:hover {
  background: rgba(255, 255, 255, 0.3);
}
</style>
