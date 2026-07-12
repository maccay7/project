<template>
  <div class="excel-viewer" :class="{ 'has-mapping': showMappingControls }">
    <!-- Sheet Tabs (only if multiple sheets) -->
    <div class="sheet-tabs" v-if="workbookSheets.length > 1">
      <div
        v-for="sheet in workbookSheets"
        :key="sheet.name"
        class="sheet-tab"
        :class="{ active: currentSheetName === sheet.name }"
        @click="selectSheet(sheet.name)"
      >
        {{ sheet.name }}
      </div>
    </div>

    <!-- Luckysheet Container (if enabled) -->
    <div v-if="useLuckysheet" ref="luckysheetContainer" class="luckysheet-container"></div>

    <!-- Traditional Excel Table (fallback) -->
    <div v-else>
      <!-- Formula Bar -->
      <div class="formula-bar" v-if="displayData.length">
        <div class="formula-cell-ref">{{ selectedCellRef }}</div>
        <div class="formula-input-wrapper">
          <span class="formula-prefix">fx</span>
          <input
            ref="formulaInput"
            type="text"
            :value="formulaBarValue"
            @input="updateFormulaBarValue($event.target.value)"
            @blur="applyFormulaBarEdit"
            @keydown.enter.prevent="applyFormulaBarEdit"
            class="formula-input"
            :placeholder="selectedCell ? 'Enter value or formula' : ''"
            style="color: #000000 !important; background: #ffffff !important;"
          />
        </div>
      </div>

      <!-- Toolbar -->
      <div class="excel-toolbar">
        <span>{{ displayData.length }} rows × {{ displayHeaders.length }} columns</span>
        <div class="toolbar-right">
          <div class="pagination-controls">
            <button class="page-btn" @click="prevPage" :disabled="currentPage === 1">←</button>
            <span class="page-info">Page {{ currentPage }} of {{ totalPages }}</span>
            <button class="page-btn" @click="nextPage" :disabled="currentPage === totalPages">→</button>
          </div>
        </div>
      </div>

      <!-- Excel table -->
      <div class="excel-table-wrapper" @scroll="handleScroll">
        <table class="excel-edit-table" :style="tableStyle" style="color: #000000 !important; background: #ffffff !important;">
          <thead>
            <tr>
              <th class="row-number-col" style="width:50px; min-width:50px; max-width:50px; color: #000000 !important; background: #f5f5f5 !important;">#</th>
              <th
                v-for="(header, colIndex) in displayHeaders"
                :key="header"
                :style="headerStyle(header, colIndex)"
                class="header-cell"
                :class="{ 'resizing': resizingColumn === header }"
              >
                <!-- Header dropdown: show for required columns only -->
                <div v-if="showMappingControls && isRequiredColumn(header)" class="header-dropdown">
                  <select
                    :value="getMappingForHeader(header)"
                    @change="onMappingChange(header, $event.target.value)"
                    class="mapping-dropdown"
                    @click.stop
                    style="color: #000000 !important; background: #ffffff !important;"
                  >
                    <option value="__na__">— Select source —</option>
                    <option v-for="fileCol in availableFileColumns" :key="fileCol" :value="fileCol">
                      {{ fileCol }}
                    </option>
                  </select>
                  <span class="header-label" style="color: #000000 !important;">{{ header }}</span>
                </div>
                <span v-else class="header-text" style="color: #000000 !important;">{{ header }}</span>

                <!-- Column resizer -->
                <div
                  class="column-resizer"
                  @mousedown.stop="startColumnResize($event, header, colIndex)"
                ></div>
              </th>
            </tr>
          </thead>
          <tbody>
            <template v-for="(row, rowIndex) in paginatedData" :key="rowIndex">
              <tr
                :style="rowStyle(rowIndex)"
                :class="{ 'selected-row': isRowSelected(rowIndex) }"
                @mousedown="handleRowMouseDown($event, rowIndex)"
              >
                <td class="row-number" style="color: #000000 !important; background: #f8f9ff !important;">
                  {{ (currentPage - 1) * pageSize + rowIndex + 1 }}
                </td>
                <td
                  v-for="(header, colIndex) in displayHeaders"
                  :key="header"
                  :class="{
                    'selected-cell': isCellSelected(rowIndex, colIndex),
                    'editing-cell': isEditingCell(rowIndex, colIndex),
                  }"
                  :style="cellStyle(rowIndex, colIndex)"
                  @click="handleCellClick($event, rowIndex, colIndex)"
                  @dblclick="handleCellDblClick($event, rowIndex, colIndex)"
                  @mousedown="handleCellMouseDown($event, rowIndex, colIndex)"
                  style="color: #000000 !important; background: #ffffff !important;"
                >
                  <div v-if="!isEditingCell(rowIndex, colIndex)" class="cell-content" style="color: #000000 !important; background: #ffffff !important;">
                    {{ row[header] !== undefined ? row[header] : '' }}
                  </div>
                  <input
                    v-else
                    ref="editInput"
                    :value="editValue"
                    @input="editValue = $event.target.value"
                    @blur="finishEditing(true)"
                    @keydown="handleEditKeydown($event)"
                    class="cell-input"
                    type="text"
                    autofocus
                    style="color: #000000 !important; background: #ffffff !important;"
                  />
                </td>
              </tr>
              <!-- Row resizer handle -->
              <tr
                v-if="rowIndex < paginatedData.length - 1"
                class="row-resizer-row"
                @mousedown.stop="startRowResize($event, rowIndex)"
              >
                <td colspan="100" class="row-resizer-cell"></td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>

      <!-- Footer -->
      <div class="excel-footer" v-if="displayData.length">
        <span style="color: #000000 !important;">{{ displayData.length }} rows · {{ displayHeaders.length }} columns</span>
        <span v-if="selectedCell" style="color: #000000 !important;">Cell: {{ selectedCellRef }}</span>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'
import luckysheet from 'luckysheet'
import 'luckysheet/dist/plugins/css/pluginsCss.css'
import 'luckysheet/dist/plugins/plugins.css'
import 'luckysheet/dist/css/luckysheet.css'

export default {
  name: 'ExcelViewer',
  props: {
    data: { type: Array, required: true },
    headers: { type: Array, default: () => [] },
    originalData: { type: Array, default: () => [] },
    originalHeaders: { type: Array, default: () => [] },
    showMappingControls: { type: Boolean, default: false },
    columnMapping: { type: Object, default: () => ({}) },
    availableFileColumns: { type: Array, default: () => [] },
    requiredColumns: { type: Array, default: () => [] },
    workbookSheets: { type: Array, default: () => [] },
    currentSheetName: { type: String, default: '' },
    useLuckysheet: { type: Boolean, default: false },
  },
  emits: ['data-update', 'mapping-update', 'sheet-selected'],
  setup(props, { emit }) {
    // ─── Internal state ──────────────────────────────────
    const internalData = ref([])
    const selectedCell = ref(null)
    const selectedRange = ref(null)
    const editingCell = ref(null)
    const editValue = ref('')
    const editInput = ref(null)

    const luckysheetContainer = ref(null)
    const luckysheetInitialized = ref(false)

    const formulaInput = ref(null)
    const formulaBarValue = ref('')

    const columnWidths = ref({})
    const rowHeights = ref({})

    const resizingColumn = ref(null)
    const resizingRow = ref(null)
    const resizeStartX = ref(0)
    const resizeStartY = ref(0)
    const resizeStartWidth = ref(0)
    const resizeStartHeight = ref(0)

    const scrollLeft = ref(0)

    const pageSize = ref(100)
    const currentPage = ref(1)
    const loadAllMode = ref(false)

    // ─── Computed ─────────────────────────────────────────
    const displayData = computed(() => internalData.value)

    const displayHeaders = computed(() => {
      if (displayData.value.length) {
        const keys = Object.keys(displayData.value[0])
        if (keys.length) return keys
      }
      if (props.headers && props.headers.length) return props.headers
      if (props.originalHeaders && props.originalHeaders.length) return props.originalHeaders
      if (props.availableFileColumns && props.availableFileColumns.length) return props.availableFileColumns
      return []
    })

    const totalPages = computed(() => Math.max(1, Math.ceil(displayData.value.length / pageSize.value)))
    const paginatedData = computed(() => {
      if (loadAllMode.value) return displayData.value
      const start = (currentPage.value - 1) * pageSize.value
      return displayData.value.slice(start, start + pageSize.value)
    })

    const defaultColumnWidth = 120
    const defaultRowHeight = 32

    const selectedCellRef = computed(() => {
      if (!selectedCell.value) return ''
      const colLetter = String.fromCharCode(65 + selectedCell.value.col)
      const rowNum = (currentPage.value - 1) * pageSize.value + selectedCell.value.row + 1
      return colLetter + rowNum
    })

    // ─── Helpers for mapping dropdown ────────────────────
    function isRequiredColumn(header) {
      return props.requiredColumns.includes(header)
    }

    function getMappingForHeader(header) {
      return props.columnMapping[header] || '__na__'
    }

    function getCellRawValue(row, col) {
      const header = displayHeaders.value[col]
      if (!header) return ''
      return row[header] !== undefined ? row[header] : ''
    }

    function setCellValue(row, col, newValue) {
      const header = displayHeaders.value[col]
      if (!header) return
      const rowData = displayData.value[row]
      if (rowData) {
        rowData[header] = newValue
        emit('data-update', internalData.value, props.originalData)
      }
    }

    // ─── Selection ─────────────────────────────────────────
    function isCellSelected(rowIndex, colIndex) {
      if (!selectedCell.value) return false
      if (selectedRange.value) {
        const { startRow, startCol, endRow, endCol } = selectedRange.value
        const minRow = Math.min(startRow, endRow)
        const maxRow = Math.max(startRow, endRow)
        const minCol = Math.min(startCol, endCol)
        const maxCol = Math.max(startCol, endCol)
        return rowIndex >= minRow && rowIndex <= maxRow &&
               colIndex >= minCol && colIndex <= maxCol
      }
      return selectedCell.value.row === rowIndex && selectedCell.value.col === colIndex
    }

    function isRowSelected(rowIndex) {
      if (!selectedRange.value) return false
      const { startRow, endRow } = selectedRange.value
      const minRow = Math.min(startRow, endRow)
      const maxRow = Math.max(startRow, endRow)
      return rowIndex >= minRow && rowIndex <= maxRow
    }

    function selectCell(row, col, extend = false) {
      if (row < 0 || row >= paginatedData.value.length) return
      if (col < 0 || col >= displayHeaders.value.length) return

      if (extend && selectedCell.value) {
        const anchorRow = selectedCell.value.row
        const anchorCol = selectedCell.value.col
        selectedRange.value = {
          startRow: anchorRow,
          startCol: anchorCol,
          endRow: row,
          endCol: col,
        }
        selectedCell.value = { row, col }
      } else {
        selectedCell.value = { row, col }
        selectedRange.value = null
      }
      updateFormulaBarFromSelection()
      if (editingCell.value) cancelEditing()
    }

    // ─── Formula Bar ──────────────────────────────────────
    function updateFormulaBarFromSelection() {
      if (!selectedCell.value) {
        formulaBarValue.value = ''
        return
      }
      const { row, col } = selectedCell.value
      const val = getCellRawValue(paginatedData.value[row], col)
      formulaBarValue.value = val !== undefined ? val : ''
    }

    function updateFormulaBarValue(newVal) {
      formulaBarValue.value = newVal
    }

    function applyFormulaBarEdit() {
      if (!selectedCell.value) return
      const { row, col } = selectedCell.value
      const newVal = formulaBarValue.value
      setCellValue(row, col, newVal)
    }

    // ─── Click / Dblclick ──────────────────────────────────
    let clickTimer = null
    const CLICK_DELAY = 200

    function handleCellClick(event, rowIndex, colIndex) {
      if (editingCell.value) {
        const { row: editRow, col: editCol } = editingCell.value
        if (editRow !== rowIndex || editCol !== colIndex) {
          finishEditing(true)
        }
      }

      if (clickTimer) {
        clearTimeout(clickTimer)
        clickTimer = null
        return
      }

      clickTimer = setTimeout(() => {
        clickTimer = null
        if (event.shiftKey) {
          selectCell(rowIndex, colIndex, true)
        } else {
          selectCell(rowIndex, colIndex, false)
        }
      }, CLICK_DELAY)
    }

    function handleCellDblClick(event, rowIndex, colIndex) {
      if (clickTimer) {
        clearTimeout(clickTimer)
        clickTimer = null
      }
      selectCell(rowIndex, colIndex, false)
      startEditing(rowIndex, colIndex)
    }

    function handleCellMouseDown(event, rowIndex, colIndex) {}
    function handleRowMouseDown(event, rowIndex) {}

    // ─── Editing ──────────────────────────────────────────
    function isEditingCell(rowIndex, colIndex) {
      if (!editingCell.value) return false
      return editingCell.value.row === rowIndex && editingCell.value.col === colIndex
    }

    function startEditing(row, col) {
      if (row < 0 || row >= paginatedData.value.length) return
      if (col < 0 || col >= displayHeaders.value.length) return
      const val = getCellRawValue(paginatedData.value[row], col)
      editingCell.value = { row, col }
      editValue.value = val !== undefined ? val : ''
      nextTick(() => {
        if (editInput.value) {
          editInput.value.focus()
          editInput.value.select()
        }
      })
    }

    function finishEditing(save) {
      if (!editingCell.value) return
      const { row, col } = editingCell.value
      if (save) {
        const newVal = editValue.value
        setCellValue(row, col, newVal)
        updateFormulaBarFromSelection()
      }
      editingCell.value = null
      editValue.value = ''
    }

    function cancelEditing() {
      finishEditing(false)
    }

    function handleEditKeydown(event) {
      if (event.key === 'Enter') {
        event.preventDefault()
        finishEditing(true)
        if (selectedCell.value) {
          const { row, col } = selectedCell.value
          const nextRow = Math.min(paginatedData.value.length - 1, row + 1)
          selectCell(nextRow, col, false)
        }
      } else if (event.key === 'Escape') {
        cancelEditing()
      } else if (event.key === 'Tab') {
        event.preventDefault()
        finishEditing(true)
        const { row, col } = editingCell.value || selectedCell.value
        let newCol
        if (event.shiftKey) {
          newCol = Math.max(0, col - 1)
        } else {
          newCol = Math.min(displayHeaders.value.length - 1, col + 1)
        }
        if (newCol !== col) {
          selectCell(row, newCol, false)
          startEditing(row, newCol)
        }
      }
    }

    // ─── Keyboard Navigation ─────────────────────────────
    function handleKeyDown(event) {
      if (editingCell.value) return
      if (!selectedCell.value) return
      const { row, col } = selectedCell.value
      let newRow = row, newCol = col
      let handled = true
      switch (event.key) {
        case 'ArrowUp': newRow = Math.max(0, row - 1); break
        case 'ArrowDown': newRow = Math.min(paginatedData.value.length - 1, row + 1); break
        case 'ArrowLeft': newCol = Math.max(0, col - 1); break
        case 'ArrowRight': newCol = Math.min(displayHeaders.value.length - 1, col + 1); break
        case 'Enter':
          startEditing(row, col)
          handled = false
          break
        case 'Tab':
          event.preventDefault()
          if (event.shiftKey) {
            newCol = Math.max(0, col - 1)
          } else {
            newCol = Math.min(displayHeaders.value.length - 1, col + 1)
          }
          break
        default:
          handled = false
      }
      if (handled) {
        event.preventDefault()
        if (newRow !== row || newCol !== col) {
          selectCell(newRow, newCol, event.shiftKey)
        }
      }
    }

    // ─── Column Resizing ──────────────────────────────────
    function startColumnResize(event, header, colIndex) {
      resizingColumn.value = header
      resizeStartX.value = event.clientX
      resizeStartWidth.value = columnWidths.value[header] || defaultColumnWidth
      document.addEventListener('mousemove', onColumnResize)
      document.addEventListener('mouseup', stopColumnResize)
      event.preventDefault()
    }

    function onColumnResize(event) {
      if (!resizingColumn.value) return
      const delta = event.clientX - resizeStartX.value
      const newWidth = Math.max(40, resizeStartWidth.value + delta)
      columnWidths.value = {
        ...columnWidths.value,
        [resizingColumn.value]: newWidth,
      }
    }

    function stopColumnResize() {
      resizingColumn.value = null
      document.removeEventListener('mousemove', onColumnResize)
      document.removeEventListener('mouseup', stopColumnResize)
    }

    function headerStyle(header, colIndex) {
      const width = columnWidths.value[header] || defaultColumnWidth
      return {
        width: width + 'px',
        minWidth: width + 'px',
        maxWidth: width + 'px',
        position: 'sticky',
        top: 0,
        zIndex: 2,
        background: '#f5f5f5',
        borderBottom: '2px solid #0B2044',
        padding: '8px 4px',
        textAlign: 'left',
        whiteSpace: 'nowrap',
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        boxSizing: 'border-box',
        color: '#000000 !important',
      }
    }

    // ─── Row Resizing ─────────────────────────────────────
    function startRowResize(event, rowIndex) {
      const globalIndex = (currentPage.value - 1) * pageSize + rowIndex
      resizingRow.value = globalIndex
      resizeStartY.value = event.clientY
      resizeStartHeight.value = rowHeights.value[globalIndex] || defaultRowHeight
      document.addEventListener('mousemove', onRowResize)
      document.addEventListener('mouseup', stopRowResize)
      event.preventDefault()
    }

    function onRowResize(event) {
      if (resizingRow.value === null) return
      const delta = event.clientY - resizeStartY.value
      const newHeight = Math.max(20, resizeStartHeight.value + delta)
      rowHeights.value = {
        ...rowHeights.value,
        [resizingRow.value]: newHeight,
      }
    }

    function stopRowResize() {
      resizingRow.value = null
      document.removeEventListener('mousemove', onRowResize)
      document.removeEventListener('mouseup', stopRowResize)
    }

    function rowStyle(rowIndex) {
      const globalIndex = (currentPage.value - 1) * pageSize + rowIndex
      const height = rowHeights.value[globalIndex] || defaultRowHeight
      return {
        height: height + 'px',
        maxHeight: height + 'px',
      }
    }

    function cellStyle(rowIndex, colIndex) {
      const globalIndex = (currentPage.value - 1) * pageSize + rowIndex
      const height = rowHeights.value[globalIndex] || defaultRowHeight
      return {
        padding: '4px 8px',
        borderRight: '1px solid #e0e0e0',
        borderBottom: '1px solid #e0e0e0',
        whiteSpace: 'nowrap',
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        position: 'relative',
        height: height + 'px',
        maxHeight: height + 'px',
        color: '#000000 !important',
        background: '#ffffff !important',
      }
    }

    // ─── Scroll ────────────────────────────────────────────
    function handleScroll(event) {
      scrollLeft.value = event.target.scrollLeft
    }

    const tableStyle = computed(() => ({
      width: '100%',
      borderCollapse: 'collapse',
      tableLayout: 'fixed',
      color: '#000000 !important',
      background: '#ffffff !important',
    }))

    // ─── Pagination ──────────────────────────────────────
    function prevPage() { if (currentPage.value > 1) currentPage.value-- }
    function nextPage() { if (currentPage.value < totalPages.value) currentPage.value++ }
    function loadAllRows() {
      loadAllMode.value = true
      currentPage.value = 1
    }

    // ─── Sheet Selection ──────────────────────────────────
    function selectSheet(sheetName) {
      const sheet = props.workbookSheets.find(s => s.name === sheetName)
      if (sheet) {
        // Use fullData if available, else data
        const sheetData = sheet.fullData || sheet.data || []
        // Convert fullData to objects with headers if fullData is array of arrays
        if (Array.isArray(sheetData) && sheetData.length > 0 && Array.isArray(sheetData[0])) {
          // Use the first row as headers? No – we should use the raw data as is, but we need to convert to objects for display.
          // However, for raw display, we want to preserve all rows and columns, even if empty.
          // So we'll treat each row as an object with column names like "Col1", "Col2"...
          const headers = sheet.headers || []
          if (headers.length === 0) {
            // Generate numeric headers
            const maxCols = sheetData.reduce((max, row) => Math.max(max, row.length), 0)
            for (let i = 0; i < maxCols; i++) {
              headers.push(`Col${i+1}`)
            }
          }
          const jsonData = sheetData.map(row => {
            const obj = {}
            headers.forEach((h, i) => { obj[h] = row[i] !== undefined ? row[i] : '' })
            return obj
          })
          internalData.value = jsonData
        } else {
          internalData.value = sheetData
        }
        currentPage.value = 1
        selectedCell.value = null
        selectedRange.value = null
        editingCell.value = null
        emit('sheet-selected', sheetName, sheet.data, sheet.headers)
      }
    }

    // ─── Mapping change from header dropdown ──────────────
    function onMappingChange(header, newSrcCol) {
      const newMapping = { ...props.columnMapping }
      newMapping[header] = newSrcCol === '__na__' ? null : newSrcCol
      emit('mapping-update', newMapping)
    }

    // ─── Luckysheet Initialization ─────────────────────────
    function initializeLuckysheet() {
      if (!props.useLuckysheet || !luckysheetContainer.value || luckysheetInitialized.value) return
      
      const sheetData = internalData.value.map(row => Object.values(row))
      const headers = displayHeaders.value
      
      sheetData.unshift(headers)
      
      const options = {
        container: luckysheetContainer.value,
        data: [sheetData],
        title: props.currentSheetName || 'Sheet 1',
        showinfobar: false,
        showsheetbar: false,
        showstatisticBar: false,
        enableAddRow: false,
        enableAddBackTop: false,
        userInfo: false,
        showConfigWindowResize: true,
        forceCalculation: false,
        rowHeaderWidth: 46,
        columnHeaderHeight: 25,
        defaultColWidth: 120,
        defaultRowHeight: 30,
        lang: 'en',
        showGrid: true,
        showToolbar: true,
        showFormulaBar: true,
      }
      
      try {
        luckysheet.create(options)
        luckysheetInitialized.value = true
      } catch (error) {
        console.error('Luckysheet initialization error:', error)
      }
    }

    function destroyLuckysheet() {
      if (luckysheetInitialized.value) {
        try {
          luckysheet.destroy()
          luckysheetInitialized.value = false
        } catch (error) {
          console.error('Luckysheet destroy error:', error)
        }
      }
    }

    // ─── Watchers ──────────────────────────────────────────
    watch(
      () => props.data,
      (newData) => {
        internalData.value = newData.map(row => ({ ...row }))
        
        if (props.useLuckysheet) {
          nextTick(() => {
            initializeLuckysheet()
          })
        }
        
        selectedCell.value = null
        selectedRange.value = null
        editingCell.value = null
        currentPage.value = 1
      },
      { immediate: true, deep: true }
    )

    watch(() => props.useLuckysheet, (newValue) => {
      if (newValue) {
        nextTick(() => initializeLuckysheet())
      } else {
        destroyLuckysheet()
      }
    })

    watch(selectedCell, () => {
      updateFormulaBarFromSelection()
    })

    // ─── Lifecycle ─────────────────────────────────────────
    onMounted(() => {
      document.addEventListener('keydown', handleKeyDown)
      
      if (props.useLuckysheet) {
        nextTick(() => {
          initializeLuckysheet()
        })
      }
    })

    onBeforeUnmount(() => {
      document.removeEventListener('keydown', handleKeyDown)
      document.removeEventListener('mousemove', onColumnResize)
      document.removeEventListener('mouseup', stopColumnResize)
      document.removeEventListener('mousemove', onRowResize)
      document.removeEventListener('mouseup', stopRowResize)
      
      destroyLuckysheet()
    })

    // ─── Expose ────────────────────────────────────────────
    return {
      internalData,
      displayData,
      displayHeaders,
      paginatedData,
      totalPages,
      currentPage,
      pageSize,
      selectedCell,
      selectedRange,
      editingCell,
      editValue,
      editInput,
      formulaInput,
      formulaBarValue,
      columnWidths,
      rowHeights,
      resizingColumn,
      resizingRow,
      scrollLeft,
      defaultColumnWidth,
      defaultRowHeight,
      tableStyle,
      selectedCellRef,
      isRequiredColumn,
      getMappingForHeader,
      setCellValue,
      isCellSelected,
      isRowSelected,
      isEditingCell,
      selectCell,
      handleCellClick,
      handleCellDblClick,
      handleCellMouseDown,
      handleRowMouseDown,
      startEditing,
      finishEditing,
      cancelEditing,
      handleEditKeydown,
      startColumnResize,
      onColumnResize,
      stopColumnResize,
      headerStyle,
      startRowResize,
      onRowResize,
      stopRowResize,
      rowStyle,
      cellStyle,
      handleScroll,
      prevPage,
      nextPage,
      onMappingChange,
      updateFormulaBarFromSelection,
      updateFormulaBarValue,
      applyFormulaBarEdit,
      workbookSheets: computed(() => props.workbookSheets),
      currentSheetName: computed(() => props.currentSheetName),
      selectSheet,
      luckysheetContainer,
    }
  },
}
</script>

<style scoped>
.excel-viewer {
  border: 1px solid #d6dee9;
  border-radius: 14px;
  overflow: hidden;
  background: #f7fafc;
  font-size: 13px;
  max-width: 100%;
  box-shadow: inset 0 0 0 1px rgba(255,255,255,0.6);
}
.sheet-tabs {
  display: flex;
  background: #f5f5f5;
  border-bottom: 1px solid #ddd;
  overflow-x: auto;
}
.sheet-tab {
  padding: 8px 16px;
  cursor: pointer;
  border-right: 1px solid #ddd;
  background: #f5f5f5;
  white-space: nowrap;
  font-size: 13px;
  color: #555;
  transition: background 0.2s;
}
.sheet-tab:hover { background: #e8e8e8; }
.sheet-tab.active {
  background: white;
  color: #0B2044;
  font-weight: 600;
  border-bottom: 2px solid #0B2044;
}
.luckysheet-container { width: 100%; height: 500px; background: #fff; }
.formula-bar {
  display: flex;
  align-items: center;
  padding: 4px 8px;
  background: #fafafa;
  border-bottom: 1px solid #ddd;
  gap: 8px;
  font-size: 13px;
}
.formula-cell-ref {
  min-width: 60px;
  font-weight: 600;
  color: #0B2044;
  background: white;
  padding: 2px 6px;
  border: 1px solid #ccc;
  border-radius: 4px;
  text-align: center;
}
.formula-input-wrapper {
  flex: 1;
  display: flex;
  align-items: center;
  background: white;
  border: 1px solid #ccc;
  border-radius: 4px;
  padding: 0 4px;
}
.formula-prefix {
  font-weight: 600;
  color: #0B2044;
  margin-right: 4px;
  padding: 0 4px;
  background: #f0f0f0;
  border-radius: 3px;
}
.formula-input {
  flex: 1;
  border: none;
  outline: none;
  padding: 4px 6px;
  font-family: inherit;
  font-size: inherit;
  background: transparent;
  min-height: 28px;
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
  font-size: 13px;
}
.page-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.page-info { font-size: 13px; color: #555; }
.excel-table-wrapper {
  overflow: auto;
  max-height: 500px;
  width: 100%;
  position: relative;
}
.excel-edit-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  table-layout: fixed;
}
.excel-edit-table th,
.excel-edit-table td {
  border: 1px solid #cbd6e2;
  box-sizing: border-box;
  background: #fff;
}
.excel-edit-table th {
  background: #eef4fb;
  font-weight: 700;
  color: #0B2044;
  user-select: none;
  position: sticky;
  top: 0;
  z-index: 2;
}
.header-cell {
  position: relative;
  padding-right: 8px;
}
.header-text {
  display: inline-block;
  width: calc(100% - 12px);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.header-dropdown {
  display: flex;
  flex-direction: column;
  gap: 2px;
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
.column-resizer {
  position: absolute;
  right: 0;
  top: 0;
  width: 6px;
  height: 100%;
  cursor: col-resize;
  background: transparent;
  z-index: 3;
  transition: background 0.1s;
}
.column-resizer:hover,
.column-resizer.active {
  background: #0B2044;
  opacity: 0.4;
}
.row-resizer-row {
  height: 6px;
  cursor: row-resize;
  background: transparent;
  transition: background 0.1s;
}
.row-resizer-row:hover {
  background: #0B2044;
  opacity: 0.15;
}
.row-resizer-cell {
  padding: 0 !important;
  border: none !important;
  height: 6px;
}
.row-number-col {
  background: #f8f9ff;
  width: 50px;
  min-width: 50px;
  max-width: 50px;
  text-align: center;
}
.row-number {
  background: #f8f9ff;
  font-weight: 500;
  text-align: center;
}
.selected-cell {
  background: #e3f2fd !important;
  outline: 2px solid #0B2044;
  outline-offset: -2px;
}
.selected-row { background: #f5f8ff; }
.editing-cell { padding: 0 !important; }
.cell-content {
  padding: 4px 8px;
  min-height: 24px;
  word-break: break-all;
}
.cell-input {
  width: 100%;
  height: 100%;
  border: none;
  outline: none;
  padding: 4px 8px;
  background: white;
  font-family: inherit;
  font-size: inherit;
  box-sizing: border-box;
}
.excel-footer {
  padding: 6px 12px;
  background: #fafafa;
  border-top: 1px solid #e0e0e0;
  font-size: 12px;
  color: #666;
  display: flex;
  justify-content: space-between;
}
.excel-viewer td,
.excel-viewer td *,
.excel-viewer .cell-content,
.excel-viewer .cell-content * {
  color: #000000 !important;
  background: #ffffff !important;
}
</style>