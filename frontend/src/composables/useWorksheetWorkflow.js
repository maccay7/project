// composables/useWorksheetWorkflow.js
/**
 * Shared worksheet workflow composable for all instrument types
 * Handles Excel upload, worksheet selection, type detection, and processing
 * Enhanced with intelligent single-instrument value extraction and synonym matching.
 */

import { ref, computed, toValue } from 'vue'
import * as XLSX from 'xlsx'
import {
  detectSheetType,
  extractSingleInstrumentValues,
  getRequiredFieldMappings,
  detectInstrumentNameColumn,
  extractInstrumentNames
} from '@/utils/sheetTypeDetector'
import { autoMatchColumns } from '@/utils/instrumentMapping'

// Financial synonym dictionary for intelligent value extraction
// This is used as a fallback when the detector doesn't find exact matches
const FINANCIAL_SYNONYMS = {
  // Money Market
  principal: ['principal', 'face value', 'nominal value', 'investment amount', 'capital', 'deposit amount', 'initial investment', 'amount invested', 'notional', 'amount'],
  interestRate: ['interest rate', 'rate', 'coupon', 'coupon rate', 'annual rate', 'fixed rate', 'lending rate', 'investment rate', 'yield rate', 'return', 'yield'],
  daysToMaturity: ['days to maturity', 'term', 'tenor', 'maturity days', 'duration days', 'period', 'days'],
  issueDate: ['issue date', 'start date', 'effective date', 'trade date', 'settlement date', 'value date', 'origination date'],
  maturityDate: ['maturity date', 'end date', 'due date', 'redemption date', 'expiry date'],
  // Bonds
  faceValue: ['face value', 'par value', 'nominal', 'amount', 'principal'],
  couponRate: ['coupon rate', 'coupon', 'rate', 'interest rate'],
  yield: ['yield', 'ytm', 'yield to maturity', 'return', 'effective yield'],
  frequency: ['frequency', 'payment frequency', 'coupon frequency', 'period', 'semi-annual', 'quarterly', 'annual'],
  // T-Bills
  discountRate: ['discount rate', 'discount', 'rate', 'bank discount'],
  purchasePrice: ['purchase price', 'buy price', 'price paid', 'acquisition price'],
  redemptionValue: ['redemption value', 'call value', 'maturity value'],
  // Generic
  instrumentName: ['instrument', 'security', 'name', 'description', 'issuer', 'counterparty', 'company', 'entity', 'bond name', 'tbill name'],
  currency: ['currency', 'ccy', 'curr', 'denomination'],
  country: ['country', 'nation', 'jurisdiction', 'region', 'market']
}

// ===== 🔥 FIXED: Enhanced extraction for single-instrument sheets =====
function extractValuesIntelligently(data, instrumentType) {
  // First, use the detector's built-in extraction
  const requiredFields = getRequiredFieldMappings(instrumentType)
  let extracted = extractSingleInstrumentValues(data, requiredFields)

  // Then, fill any missing values using the synonym fallback
  const fieldKeys = Object.keys(requiredFields)
  for (const field of fieldKeys) {
    if (!extracted[field] || extracted[field] === '') {
      const synonyms = FINANCIAL_SYNONYMS[field] || [field]
      // Search through all cells for any synonym
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

  // 🔥 Special handling: look for instrument name if missing
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

export function useWorksheetWorkflow(instrumentTypeRef) {
  // ===== STATE =====
  const uploadedFile = ref(null)
  const originalFileBuffer = ref(null)
  const workbookSheets = ref([])
  const currentSheetName = ref('')
  const worksheetStatus = ref({})
  const selectedWorksheet = ref(null)
  
  const sheetType = ref('multi')
  const extractedValues = ref({})
  const tabularData = ref([])
  const instrumentNameColumn = ref(null)
  const detectedInstrumentNames = ref([])
  
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

  const currentInstrumentType = computed(() => toValue(instrumentTypeRef))

  // ===== UPLOAD FUNCTIONS =====
  async function handleFileUpload(file) {
    if (!file) {
      error.value = 'No file provided'
      return { success: false, error: 'No file provided' }
    }

    const validExtensions = ['.csv', '.xlsx', '.xls', '.xlsm', '.xlsb', '.xltx', '.xltm', '.xlam', '.ods', '.xml', '.html', '.prn', '.dif', '.slk', '.dbf']
    const fileName = file.name.toLowerCase()
    const hasValidExtension = validExtensions.some(ext => fileName.endsWith(ext))
    
    if (!hasValidExtension) {
      error.value = 'Invalid file type. Please upload a valid spreadsheet file.'
      return { success: false, error: error.value }
    }

    loading.value = true
    error.value = ''
    uploadProgress.value = 0

    try {
      const arrayBuffer = await file.arrayBuffer()
      originalFileBuffer.value = arrayBuffer
      uploadedFile.value = new File([file], file.name, { type: file.type })

      const workbook = XLSX.read(arrayBuffer, { 
        type: 'array', 
        cellDates: true,
        cellStyles: true,
        cellNF: true,
        sheetStubs: true
      })

      const sheets = []
      for (const sheetName of workbook.SheetNames) {
        const worksheet = workbook.Sheets[sheetName]
        
        const range = XLSX.utils.decode_range(worksheet['!ref'] || 'A1')
        
        // Keep full data for tables
        const fullData = []
        for (let row = range.s.r; row <= range.e.r; row++) {
          const rowData = []
          for (let col = range.s.c; col <= range.e.c; col++) {
            const cellAddress = XLSX.utils.encode_cell({ r: row, c: col })
            const cell = worksheet[cellAddress]
            rowData.push(cell ? (cell.v !== undefined ? cell.v : '') : '')
          }
          fullData.push(rowData)
        }
        
        const jsonData = XLSX.utils.sheet_to_json(worksheet, { defval: '', raw: false })
        const sheetHeaders = jsonData.length > 0 ? Object.keys(jsonData[0]) : []

        sheets.push({
          name: sheetName,
          data: jsonData,
          headers: sheetHeaders,
          fullData: fullData,
          row_count: jsonData.length,
          column_count: sheetHeaders.length,
          full_row_count: range.e.r - range.s.r + 1,
          full_column_count: range.e.c - range.s.c + 1,
          range: worksheet['!ref']
        })
      }

      workbookSheets.value = sheets

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

    const detection = detectSheetType(sheet.data, currentInstrumentType.value)
    sheetType.value = detection.type

    console.log(`📋 Selected sheet: ${sheetName}, type: ${detection.type}`)
    return { success: true, sheet, type: detection.type }
  }

  // ===== 🔥 FIXED: WORKSHEET PROCESSING with better name detection =====
  async function processWorksheet(sheetName, requiredColumns, columnVariations) {
    const sheet = workbookSheets.value.find(s => s.name === sheetName)
    if (!sheet) {
      error.value = `Sheet "${sheetName}" not found`
      return { success: false, error: error.value }
    }

    worksheetStatus.value[sheetName] = 'in_progress'

    try {
      // First, use the intelligent detector to get type and extracted values
      const detection = detectSheetType(sheet.data, currentInstrumentType.value)
      sheetType.value = detection.type

      if (detection.type === 'single') {
        // Use the enhanced extraction that combines detector + synonym fallback
        const values = extractValuesIntelligently(sheet.data, currentInstrumentType.value)
        extractedValues.value = values
        tabularData.value = convertExtractedToTabular(values)

        console.log('📋 Single-instrument sheet processed with intelligent extraction:', values)
        worksheetStatus.value[sheetName] = 'completed'
        return {
          success: true,
          type: 'single',
          data: tabularData.value,
          extractedValues: values
        }
      } else {
        // ===== MULTI-INSTRUMENT: Better column detection =====
        tabularData.value = sheet.data

        // 🔥 First try to detect instrument name column
        let nameDetection = detectInstrumentNameColumn(sheet.data)
        
        // If no name column found, try harder
        if (!nameDetection || !nameDetection.columnName) {
          // Search through all column names for common patterns
          const namePatterns = ['instrument', 'name', 'security', 'bond', 'tbill', 'issuer', 'counterparty', 'company', 'entity']
          let foundCol = null
          for (const header of sheet.headers) {
            const lowerHeader = header.toLowerCase()
            if (namePatterns.some(p => lowerHeader.includes(p))) {
              foundCol = header
              break
            }
          }
          if (foundCol) {
            nameDetection = { columnName: foundCol, confidence: 0.8 }
          } else if (sheet.headers.length > 0) {
            // Fallback: use first column as name
            nameDetection = { columnName: sheet.headers[0], confidence: 0.5 }
          }
        }
        
        instrumentNameColumn.value = nameDetection?.columnName || null
        if (nameDetection?.columnName) {
          detectedInstrumentNames.value = extractInstrumentNames(sheet.data, nameDetection.columnName)
          console.log('📋 Detected instrument names:', detectedInstrumentNames.value)
        }

        // 🔥 Build column mapping with Instrument Name prioritized
        let columnMapping = null
        if (requiredColumns && columnVariations) {
          columnMapping = autoMatchColumns(sheet.headers, requiredColumns, columnVariations)
          
          // Ensure Instrument Name is properly mapped
          if (nameDetection?.columnName && columnMapping['Instrument Name'] !== nameDetection.columnName) {
            // Check if the detected column is in the file columns
            if (sheet.headers.includes(nameDetection.columnName)) {
              columnMapping['Instrument Name'] = nameDetection.columnName
              console.log(`✅ Mapped Instrument Name to: ${nameDetection.columnName}`)
            }
          }
          
          // If still no mapping for Instrument Name, try to find any column with 'name'
          if (!columnMapping['Instrument Name']) {
            const nameCol = sheet.headers.find(h => 
              /name|instrument|security|bond|tbill|issuer|entity/i.test(h)
            )
            if (nameCol) {
              columnMapping['Instrument Name'] = nameCol
            }
          }
        }

        console.log('📊 Multi-instrument sheet processed, ready for mapping')
        worksheetStatus.value[sheetName] = 'completed'
        return {
          success: true,
          type: 'multi',
          data: sheet.data,
          headers: sheet.headers,
          columnMapping,
          instrumentNameColumn: nameDetection?.columnName || null,
          instrumentNames: detectedInstrumentNames.value
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
      frequency: 'Frequency',
      instrumentName: 'Instrument'
    }

    for (const [key, value] of Object.entries(extractedValues)) {
      const columnName = columnMapping[key] || key
      row[columnName] = value
    }
    return [row]
  }

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
    instrumentNameColumn.value = null
    detectedInstrumentNames.value = []
  }

  // ===== STATE SNAPSHOT =====
  function getStateSnapshot() {
    return {
      uploadedFileName: uploadedFile.value?.name || null,
      workbookSheets: workbookSheets.value,
      worksheetStatus: worksheetStatus.value,
      currentSheetName: currentSheetName.value,
      sheetType: sheetType.value,
      extractedValues: extractedValues.value,
      tabularData: tabularData.value,
      instrumentNameColumn: instrumentNameColumn.value,
      detectedInstrumentNames: detectedInstrumentNames.value
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
    instrumentNameColumn.value = snapshot.instrumentNameColumn || null
    detectedInstrumentNames.value = snapshot.detectedInstrumentNames || []

    if (snapshot.uploadedFileName) {
      uploadedFile.value = { name: snapshot.uploadedFileName, size: 0 }
    }

    if (currentSheetName.value) {
      const sheet = workbookSheets.value.find(s => s.name === currentSheetName.value)
      if (sheet) selectedWorksheet.value = sheet
    }
  }

  // ===== EXPOSE =====
  return {
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
    hasWorkbook,
    completedSheets,
    totalSheets,
    progress,
    instrumentNameColumn,
    detectedInstrumentNames,
    handleFileUpload,
    selectWorksheet,
    processWorksheet,
    getCurrentData,
    reset,
    getStateSnapshot,
    restoreState
  }
}