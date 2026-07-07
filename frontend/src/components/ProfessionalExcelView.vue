<template>
  <div class="professional-excel-view">
    <!-- Excel-style toolbar -->
    <div class="excel-toolbar">
      <div class="toolbar-left">
        <span class="row-count">{{ data.length }} rows × {{ columns.length }} columns</span>
      </div>
      <div class="toolbar-right">
        <button class="toolbar-btn" @click="exportToExcel" title="Export to Excel">
          <v-icon small>mdi-microsoft-excel</v-icon> Export
        </button>
        <button class="toolbar-btn" @click="printView" title="Print">
          <v-icon small>mdi-printer</v-icon> Print
        </button>
      </div>
    </div>

    <!-- Excel table with professional styling -->
    <div class="excel-table-container">
      <table class="excel-table">
        <thead>
          <tr class="header-row">
            <th class="row-number-header">#</th>
            <th
              v-for="(column, colIndex) in columns"
              :key="column"
              class="header-cell"
              :style="{ width: columnWidths[column] || 'auto' }"
            >
              <div class="header-content">
                <span class="header-text">{{ column }}</span>
              </div>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(row, rowIndex) in paginatedData"
            :key="rowIndex"
            class="data-row"
            :class="{ 'even-row': rowIndex % 2 === 0, 'odd-row': rowIndex % 2 === 1 }"
          >
            <td class="row-number-cell">{{ startRowIndex + rowIndex + 1 }}</td>
            <td
              v-for="(column, colIndex) in columns"
              :key="`${rowIndex}-${colIndex}`"
              class="data-cell"
            >
              {{ formatCellValue(row[column], column) }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Pagination -->
    <div class="pagination-bar" v-if="totalPages > 1">
      <div class="pagination-info">
        Showing {{ startRowIndex + 1 }} - {{ Math.min(endRowIndex, data.length) }} of {{ data.length }} rows
      </div>
      <div class="pagination-controls">
        <button
          class="pagination-btn"
          @click="prevPage"
          :disabled="currentPage === 1"
        >
          <v-icon small>mdi-chevron-left</v-icon> Previous
        </button>
        <span class="page-indicator">Page {{ currentPage }} of {{ totalPages }}</span>
        <button
          class="pagination-btn"
          @click="nextPage"
          :disabled="currentPage === totalPages"
        >
          Next <v-icon small>mdi-chevron-right</v-icon>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import * as XLSX from 'xlsx'

const props = defineProps({
  data: {
    type: Array,
    default: () => []
  },
  columns: {
    type: Array,
    default: () => []
  },
  title: {
    type: String,
    default: 'Summary'
  },
  pageSize: {
    type: Number,
    default: 100
  },
  columnFormats: {
    type: Object,
    default: () => ({})
  }
})

const currentPage = ref(1)
const columnWidths = ref({})

const totalPages = computed(() => Math.ceil(props.data.length / props.pageSize))

const startRowIndex = computed(() => (currentPage.value - 1) * props.pageSize)
const endRowIndex = computed(() => startRowIndex.value + props.pageSize)

const paginatedData = computed(() => {
  return props.data.slice(startRowIndex.value, endRowIndex.value)
})

function prevPage() {
  if (currentPage.value > 1) {
    currentPage.value--
  }
}

function nextPage() {
  if (currentPage.value < totalPages.value) {
    currentPage.value++
  }
}

function formatCellValue(value, column) {
  if (value === null || value === undefined || value === '') {
    return ''
  }

  // Check if column has a specific format
  if (props.columnFormats[column]) {
    const format = props.columnFormats[column]
    
    if (format === 'currency') {
      return formatCurrency(value)
    } else if (format === 'percentage') {
      return formatPercentage(value)
    } else if (format === 'number') {
      return formatNumber(value)
    } else if (format === 'date') {
      return formatDate(value)
    }
  }

  // Auto-detect format based on value
  if (typeof value === 'number') {
    // Check if it looks like a percentage (0-1 or 0-100)
    if (column.toLowerCase().includes('rate') || column.toLowerCase().includes('yield') || column.toLowerCase().includes('return')) {
      if (value <= 1) {
        return formatPercentage(value * 100)
      }
      return formatPercentage(value)
    }
    // Check if it looks like currency
    if (column.toLowerCase().includes('price') || column.toLowerCase().includes('amount') || column.toLowerCase().includes('value')) {
      return formatCurrency(value)
    }
    return formatNumber(value)
  }

  return value
}

function formatCurrency(value) {
  if (typeof value !== 'number') return value
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(value)
}

function formatPercentage(value) {
  if (typeof value !== 'number') return value
  return new Intl.NumberFormat('en-US', {
    style: 'percent',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(value / 100)
}

function formatNumber(value) {
  if (typeof value !== 'number') return value
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(value)
}

function formatDate(value) {
  if (typeof value === 'string') {
    const date = new Date(value)
    if (!isNaN(date.getTime())) {
      return new Intl.DateTimeFormat('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      }).format(date)
    }
  }
  return value
}

function exportToExcel() {
  const worksheet = XLSX.utils.json_to_sheet(props.data)
  const workbook = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(workbook, worksheet, props.title)
  XLSX.writeFile(workbook, `${props.title.replace(/\s+/g, '_')}.xlsx`)
}

function printView() {
  window.print()
}

onMounted(() => {
  // Set default column widths based on content
  props.columns.forEach(column => {
    columnWidths.value[column] = '150px'
  })
})
</script>

<style scoped>
.professional-excel-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #ffffff;
  border: 1px solid #d4d4d4;
  border-radius: 4px;
  overflow: hidden;
}

.excel-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: linear-gradient(to bottom, #f8f9fa, #e9ecef);
  border-bottom: 1px solid #d4d4d4;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.row-count {
  font-size: 12px;
  color: #666;
  font-weight: 500;
}

.toolbar-right {
  display: flex;
  gap: 8px;
}

.toolbar-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  background: #ffffff;
  border: 1px solid #adadad;
  border-radius: 2px;
  font-size: 12px;
  color: #000000;
  cursor: pointer;
  transition: background 0.1s;
}

.toolbar-btn:hover:not(:disabled) {
  background: #e1e1e1;
}

.toolbar-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.excel-table-container {
  flex: 1;
  overflow: auto;
  position: relative;
}

.excel-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 11px;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

.header-row {
  background: linear-gradient(to bottom, #f8f9fa, #e9ecef);
  position: sticky;
  top: 0;
  z-index: 10;
}

.row-number-header {
  width: 50px;
  min-width: 50px;
  max-width: 50px;
  padding: 6px 8px;
  text-align: center;
  font-weight: 600;
  color: #000000;
  background: #f0f0f0;
  border: 1px solid #d4d4d4;
  border-right: 2px solid #d4d4d4;
  font-size: 10px;
}

.header-cell {
  padding: 8px 12px;
  text-align: left;
  font-weight: 600;
  color: #000000;
  background: #f0f0f0;
  border: 1px solid #d4d4d4;
  white-space: nowrap;
  user-select: none;
}

.header-content {
  display: flex;
  align-items: center;
  gap: 4px;
}

.header-text {
  color: #000000;
}

.data-row {
  transition: background 0.05s;
}

.data-row:hover {
  background: #e8f4ff !important;
}

.even-row {
  background: #ffffff;
}

.odd-row {
  background: #f9f9f9;
}

.row-number-cell {
  width: 50px;
  min-width: 50px;
  max-width: 50px;
  padding: 6px 8px;
  text-align: center;
  font-size: 10px;
  color: #666;
  background: #f5f5f5;
  border: 1px solid #d4d4d4;
  border-right: 2px solid #d4d4d4;
}

.data-cell {
  padding: 6px 12px;
  text-align: left;
  color: #000000;
  border: 1px solid #d4d4d4;
  white-space: nowrap;
}

.pagination-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: #f8f9fa;
  border-top: 1px solid #d4d4d4;
}

.pagination-info {
  font-size: 12px;
  color: #666;
}

.pagination-controls {
  display: flex;
  align-items: center;
  gap: 12px;
}

.pagination-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 12px;
  background: #ffffff;
  border: 1px solid #adadad;
  border-radius: 2px;
  font-size: 12px;
  color: #000000;
  cursor: pointer;
}

.pagination-btn:hover:not(:disabled) {
  background: #e1e1e1;
}

.pagination-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.page-indicator {
  font-size: 12px;
  color: #666;
  font-weight: 500;
}

/* Print styles */
@media print {
  .excel-toolbar,
  .pagination-bar {
    display: none;
  }
  
  .professional-excel-view {
    border: none;
  }
  
  .excel-table {
    font-size: 10px;
  }
}
</style>
