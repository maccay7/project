// composables/useWorksheetWorkflow.js
/**
 * Shared worksheet workflow composable for all instrument types
 * Handles Excel upload, worksheet selection, type detection, and processing
 */

import { ref, computed, toValue } from 'vue'
import * as XLSX from 'xlsx'
import { detectSheetType, extractSingleInstrumentValues, getRequiredFieldMappings } from '@/utils/sheetTypeDetector'
import { autoMatchColumns } from '@/utils/instrumentMapping'

export function useWorksheetWorkflow(instrumentTypeRef) {
  // ===== STATE =====
  const uploadedFile = ref(null)
  const originalFileBuffer = ref(null)
  const workbookSheets = ref([]) // All sheets from uploaded workbook
  const currentSheetName = ref('')
  const worksheetStatus = ref({}) // { sheetName: 'not_started' | 'in_progress' | 'completed' }
  const selectedWorksheet = ref(null)
  
  const sheetType = ref('multi')
  const extractedValues = ref({})
  const tabularData = ref([])
  
  const loading = ref(false)
  const error = ref('')
  const uploadProgress = ref(0)

  // ===== COMPUTED =====
  const hasWorkbook = computed(() => workbookSheets.value.length > 0)
  const completedSheets = computed(() => 
    Object.values(worksheetStatus.value).filter(s => s === 'completed').length
  )
  const totalSheets = computed(() => workbookSheets.value.length)
  const progress = computed(() => 
    totalSheets.value > 0 ? (completedSheets.value / totalSheets.value) * 100 : 0
  )

  // Current instrument type as a computed (so it updates when route changes)
  const currentInstrumentType = computed(() => toValue(instrumentTypeRef))

  // ===== UPLOAD FUNCTIONS =====
  async function handleFileUpload(file) {
    if (!file) {
      error.value = 'No file provided'
      return { success: false, error: 'No file provided' }
    }

    loading.value = true
    error.value = ''
    uploadProgress.value = 0

    try {
      // Read file as array buffer
      const arrayBuffer = await file.arrayBuffer()
      originalFileBuffer.value = arrayBuffer
      uploadedFile.value = new File([file], file.name, { type: file.type })

      // Parse workbook with XLSX
      const workbook = XLSX.read(arrayBuffer, { type: 'array', cellDates: true })

      // Extract all sheets
      const sheets = []
      for (const sheetName of workbook.SheetNames) {
        const worksheet = workbook.Sheets[sheetName]
        const jsonData = XLSX.utils.sheet_to_json(worksheet, { defval: '', raw: false })
        const sheetHeaders = jsonData.length > 0 ? Object.keys(jsonData[0]) : []

        sheets.push({
          name: sheetName,
          data: jsonData,
          headers: sheetHeaders,
          row_count: jsonData.length,
          column_count: sheetHeaders.length
        })
      }

      workbookSheets.value = sheets

      // Initialize worksheet status
      worksheetStatus.value = {}
      sheets.forEach(sheet => {
        worksheetStatus.value[sheet.name] = 'not_started'
      })

      uploadProgress.value = 100
      console.log(`✅ Workbook loaded: ${sheets.length} sheets`)
      return { success: true, sheets }
    } catch (err) {
      error.value = `Failed to parse workbook: ${err.message}`
      console.error('Upload error:', err)
      return { success: false, error: err.message }
    } finally {
      loading.value = false
      uploadProgress.value = 0
    }
  }

  // ===== WORKSHEET SELECTION =====
  function selectWorksheet(sheetName) {
    const sheet = workbookSheets.value.find(s => s.name === sheetName)
    if (!sheet) {
      error.value = `Sheet "${sheetName}" not found`
      return { success: false, error: error.value }
    }

    selectedWorksheet.value = sheet
    currentSheetName.value = sheetName

    // Auto-detect sheet type using the current instrument type
    const detection = detectSheetType(sheet.data, currentInstrumentType.value)
    sheetType.value = detection.type

    console.log(`📋 Selected sheet: ${sheetName}, type: ${detection.type}`)
    return { success: true, sheet, type: detection.type }
  }

  // ===== WORKSHEET PROCESSING =====
  async function processWorksheet(sheetName, requiredColumns, columnVariations) {
    const sheet = workbookSheets.value.find(s => s.name === sheetName)
    if (!sheet) {
      error.value = `Sheet "${sheetName}" not found`
      return { success: false, error: error.value }
    }

    worksheetStatus.value[sheetName] = 'in_progress'

    try {
      const detection = detectSheetType(sheet.data, currentInstrumentType.value)
      sheetType.value = detection.type

      if (detection.type === 'single') {
        // Single-instrument: auto-extract values
        const fieldMappings = getRequiredFieldMappings(currentInstrumentType.value)
        const values = extractSingleInstrumentValues(sheet.data, fieldMappings)
        extractedValues.value = values
        tabularData.value = convertExtractedToTabular(values)

        console.log('📋 Single-instrument sheet processed')
        worksheetStatus.value[sheetName] = 'completed'
        return {
          success: true,
          type: 'single',
          data: tabularData.value,
          extractedValues: values
        }
      } else {
        // Multi-instrument: prepare for mapping
        tabularData.value = sheet.data

        // Auto-match columns if variations provided
        let columnMapping = null
        if (requiredColumns && columnVariations) {
          columnMapping = autoMatchColumns(sheet.headers, requiredColumns, columnVariations)
        }

        console.log('📊 Multi-instrument sheet processed, ready for mapping')
        worksheetStatus.value[sheetName] = 'completed'
        return {
          success: true,
          type: 'multi',
          data: sheet.data,
          headers: sheet.headers,
          columnMapping
        }
      }
    } catch (err) {
      error.value = `Failed to process worksheet: ${err.message}`
      worksheetStatus.value[sheetName] = 'not_started'
      console.error('Processing error:', err)
      return { success: false, error: err.message }
    }
  }

  // ===== HELPER FUNCTIONS =====
  function convertExtractedToTabular(extractedValues) {
    const row = {}
    const columnMapping = {
      faceValue: 'Face Value',
      issueDate: 'Issue Date',
      maturityDate: 'Maturity Date',
      couponRate: 'Coupon Rate',
      yield: 'Yield',
      price: 'Price',
      discountRate: 'Discount Rate',
      frequency: 'Frequency'
    }

    for (const [key, value] of Object.entries(extractedValues)) {
      const columnName = columnMapping[key] || key
      row[columnName] = value
    }
    return [row]
  }

  // Get current worksheet data (for saving)
  function getCurrentData() {
    if (sheetType.value === 'single') {
      return {
        type: 'single',
        extractedValues: extractedValues.value,
        data: tabularData.value
      }
    } else {
      return {
        type: 'multi',
        data: tabularData.value,
        sheets: workbookSheets.value,
        selectedSheet: currentSheetName.value
      }
    }
  }

  // ===== RESET =====
  function reset() {
    uploadedFile.value = null
    originalFileBuffer.value = null
    workbookSheets.value = []
    currentSheetName.value = ''
    worksheetStatus.value = {}
    selectedWorksheet.value = null
    sheetType.value = 'multi'
    extractedValues.value = {}
    tabularData.value = []
    loading.value = false
    error.value = ''
    uploadProgress.value = 0
  }

  // ===== STATE SNAPSHOT (for save/restore) =====
  function getStateSnapshot() {
    return {
      uploadedFileName: uploadedFile.value?.name || null,
      workbookSheets: workbookSheets.value,
      worksheetStatus: worksheetStatus.value,
      currentSheetName: currentSheetName.value,
      sheetType: sheetType.value,
      extractedValues: extractedValues.value,
      tabularData: tabularData.value
    }
  }

  function restoreState(snapshot) {
    if (!snapshot) return

    workbookSheets.value = snapshot.workbookSheets || []
    worksheetStatus.value = snapshot.worksheetStatus || {}
    currentSheetName.value = snapshot.currentSheetName || ''
    sheetType.value = snapshot.sheetType || 'multi'
    extractedValues.value = snapshot.extractedValues || {}
    tabularData.value = snapshot.tabularData || []

    // Restore the file name (but buffer cannot be restored – will need re-upload)
    if (snapshot.uploadedFileName) {
      uploadedFile.value = { name: snapshot.uploadedFileName, size: 0 }
    }

    // Find the selected sheet
    if (currentSheetName.value) {
      const sheet = workbookSheets.value.find(s => s.name === currentSheetName.value)
      if (sheet) selectedWorksheet.value = sheet
    }
  }

  // ===== EXPOSE =====
  return {
    // State
    uploadedFile,
    originalFileBuffer,
    workbookSheets,
    currentSheetName,
    worksheetStatus,
    selectedWorksheet,
    sheetType,
    extractedValues,
    tabularData,
    loading,
    error,
    uploadProgress,

    // Computed
    hasWorkbook,
    completedSheets,
    totalSheets,
    progress,

    // Functions
    handleFileUpload,
    selectWorksheet,
    processWorksheet,
    getCurrentData,
    reset,
    getStateSnapshot,
    restoreState
  }
}