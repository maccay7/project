<template>
  <div class="excel-grid-container">
    <v-card class="stats-card" elevation="2">
      <v-card-title class="card-title">
        <v-icon class="title-icon">mdi-microsoft-excel</v-icon>
        Dataset Preview (Editable)
      </v-card-title>
      <v-card-text class="pa-0">
        <div v-if="data.length === 0" class="no-data-message">
          <v-icon size="64" color="#217346">mdi-table-off</v-icon>
          <h3>No Data Available</h3>
          <p>Upload a file to see the dataset preview</p>
        </div>
        <div v-else class="excel-grid-wrapper">
          <!-- Formula Bar -->
          <div class="formula-bar">
            <v-icon class="formula-icon">mdi-function-variant</v-icon>
            <span class="formula-label">fx</span>
            <input
              type="text"
              class="formula-input"
              :value="selectedCell ? getCellValue(selectedCell.row, selectedCell.col) : ''"
              :placeholder="selectedCell ? `${columnLetters[selectedCell.col]}${selectedCell.row + 1}` : 'Select a cell'"
              readonly
            />
          </div>
          <table class="excel-table">
            <thead>
              <tr>
                <th class="row-number-header"></th>
                <th v-for="(header, colIndex) in headers" :key="colIndex" class="excel-header">
                  <span class="column-letter">{{ columnLetters[colIndex] }}</span>
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, rowIndex) in paginatedData" :key="rowIndex">
                <td class="row-number">{{ startIndex + rowIndex + 1 }}</td>
                <td
                  v-for="(cell, colIndex) in headers"
                  :key="colIndex"
                  class="excel-cell"
                  :class="{ 'selected-cell': selectedCell && selectedCell.row === rowIndex && selectedCell.col === colIndex }"
                  @click="selectCell(rowIndex, colIndex)"
                >
                  {{ formatCellValue(row[cell], row) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <!-- Pagination -->
        <div class="pagination-controls">
          <v-btn size="small" variant="text" :disabled="currentPage === 1" @click="prevPage">
            <v-icon>mdi-chevron-left</v-icon>
            Previous
          </v-btn>
          <span class="page-info">
            Page {{ currentPage }} of {{ totalPages }}
          </span>
          <v-btn size="small" variant="text" :disabled="currentPage === totalPages" @click="nextPage">
            Next
            <v-icon>mdi-chevron-right</v-icon>
          </v-btn>
          <v-select
            v-model="rowsPerPage"
            :items="[10, 25, 50, 100]"
            variant="outlined"
            density="compact"
            style="width: 80px"
            class="ml-4"
          ></v-select>
          <span class="ml-2">rows per page</span>
        </div>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

interface Props {
  headers: string[]
  data: any[]
}

const props = defineProps<Props>()

const emit = defineEmits<{
  (e: 'data-update', data: any[]): void
}>()

const headers = ref<string[]>(props.headers)
const data = ref<any[]>([...props.data])

// Debug: log the data structure
console.log('ExcelGrid data structure:', data.value)
console.log('Sample row:', data.value[0])

// Cell selection
const selectedCell = ref<{ row: number; col: number } | null>(null)

const selectCell = (rowIndex: number, colIndex: number) => {
  selectedCell.value = { row: rowIndex, col: colIndex }
}

const getCellValue = (rowIndex: number, colIndex: number) => {
  if (rowIndex < 0 || rowIndex >= paginatedData.value.length || colIndex < 0 || colIndex >= headers.value.length) {
    return ''
  }
  const row = paginatedData.value[rowIndex]
  const header = headers.value[colIndex]
  const value = row[header] || ''
  
  // For the formula bar, always return the raw value (formula or actual value)
  // If there's a formula field, return that instead
  if (row[`${header}_formula`] !== undefined) {
    return row[`${header}_formula`]
  }
  if (row.formula !== undefined) {
    return row.formula
  }
  
  return value
}

const evaluateFormula = (formula: string): number | string => {
  try {
    // Remove the '=' prefix
    const expression = formula.substring(1).trim()
    
    // If it's a simple number, return it
    if (!isNaN(Number(expression))) {
      return Number(expression)
    }
    
    // Evaluate simple arithmetic expressions (basic safety check)
    // Only allow numbers, basic operators, and parentheses
    if (/^[0-9+\-*/().\s]+$/.test(expression)) {
      // Use Function constructor for evaluation (safer than eval)
      const result = new Function('return ' + expression)()
      return result
    }
    
    // If it contains cell references (like A1, B2), we can't evaluate without a full grid engine
    // Return the formula as-is for now
    return formula
  } catch (e) {
    console.error('Error evaluating formula:', e)
    return formula
  }
}

const formatCellValue = (value: any, row: any) => {
  // If value is a formula, try to evaluate it
  if (typeof value === 'string' && value.trim().startsWith('=')) {
    const result = evaluateFormula(value)
    // If evaluation returned a number, show that. Otherwise show the formula
    return typeof result === 'number' ? result : value
  }
  return value
}

// Excel-style column letters (A, B, C, ..., Z, AA, AB, etc.)
const columnLetters = computed(() => {
  const letters = []
  for (let i = 0; i < headers.value.length; i++) {
    let letter = ''
    let num = i
    while (num >= 0) {
      letter = String.fromCharCode((num % 26) + 65) + letter
      num = Math.floor(num / 26) - 1
      if (num < 0) break
    }
    letters.push(letter)
  }
  return letters
})

// Pagination
const currentPage = ref(1)
const rowsPerPage = ref(10)

const startIndex = computed(() => (currentPage.value - 1) * rowsPerPage.value)
const endIndex = computed(() => Math.min(startIndex.value + rowsPerPage.value, data.value.length))

const paginatedData = computed(() => {
  return data.value.slice(startIndex.value, endIndex.value)
})

const totalPages = computed(() => Math.ceil(data.value.length / rowsPerPage.value))

const prevPage = () => {
  if (currentPage.value > 1) {
    currentPage.value--
  }
}

const nextPage = () => {
  if (currentPage.value < totalPages.value) {
    currentPage.value++
  }
}

console.log('ExcelGrid mounted with', data.value.length, 'rows and', headers.value.length, 'columns')
</script>

<style scoped>
.excel-grid-container {
  width: 100%;
}

.metadata-card {
  border-radius: 12px;
}

.grid-card {
  border-radius: 12px;
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
  color: #0B2A44;
}

.metadata-item {
  margin-bottom: 16px;
}

.metadata-label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  color: #666;
  margin-bottom: 4px;
}

.excel-grid-wrapper {
  overflow-x: auto;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  max-height: 600px;
  overflow-y: auto;
}

.excel-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  font-family: 'Calibri', 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

.excel-table thead {
  position: sticky;
  top: 0;
  z-index: 10;
}

.row-number-header,
.excel-header {
  background: #217346;
  color: white;
  font-weight: 600;
  padding: 8px 6px;
  text-align: center;
  border-right: 1px solid #d4d4d4;
  border-bottom: 1px solid #d4d4d4;
  white-space: nowrap;
  min-width: 100px;
  position: relative;
  font-size: 12px;
  font-family: 'Calibri', 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

.row-number-header {
  background: #d9d9d9;
  color: #333;
}

.column-letter {
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  font-size: 12px;
  font-weight: bold;
}

.row-number {
  background-color: #f3f3f3;
  color: #666;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  font-size: 11px;
  text-align: center;
  padding: 6px 4px;
  border: 1px solid #d4d4d4;
  font-weight: bold;
  user-select: none;
}

.excel-cell {
  border: 1px solid #d4d4d4;
  padding: 6px 8px;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  font-size: 12px;
  text-align: left;
  cursor: cell;
  transition: background-color 0.1s;
  min-width: 80px;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.excel-cell:hover {
  background-color: #f8f8f8;
}

.excel-cell.selected-cell {
  background-color: #217346 !important;
  color: white;
  border: 2px solid #106c2e;
}

.excel-cell.editing-cell {
  background-color: white;
  padding: 0;
}

.excel-cell.formula-cell {
  color: #106c2e;
  font-style: italic;
}

.cell-input {
  width: 100%;
  height: 100%;
  border: 2px solid #217346;
  padding: 4px;
  font-size: 12px;
  background: white;
  outline: none;
  font-family: 'Calibri', 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  cursor: text;
}

.cell-value {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dataset-item {
  border-bottom: 1px solid #e0e0e0;
}

.dataset-item:last-child {
  border-bottom: none;
}

.stats-card {
  border-radius: 8px;
  margin-bottom: 16px;
}

.cell-input:focus {
  outline: none;
  border-color: #217346;
  box-shadow: 0 0 0 2px rgba(33, 115, 70, 0.1);
}

.pagination-controls {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  border-top: 1px solid #e0e0e0;
  gap: 8px;
}

.page-info {
  font-size: 14px;
  color: #666;
  margin: 0 16px;
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

.debug-info {
  font-size: 12px;
  color: #999;
  margin-top: 16px;
  font-family: monospace;
}

.formula-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: #f5f5f5;
  border-bottom: 1px solid #e0e0e0;
}

.formula-icon {
  color: #217346;
}

.formula-label {
  font-weight: 600;
  color: #217346;
  font-size: 12px;
  font-style: italic;
}

.formula-input {
  flex: 1;
  padding: 6px 12px;
  border: 1px solid #d4d4d4;
  border-radius: 4px;
  font-size: 13px;
  font-family: 'Calibri', 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  background: white;
  outline: none;
}

.formula-input:focus {
  outline: none;
  border-color: #217346;
  box-shadow: 0 0 0 2px rgba(33, 115, 70, 0.1);
}
</style>
