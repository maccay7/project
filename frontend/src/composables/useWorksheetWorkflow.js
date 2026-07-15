import { ref, computed, toValue } from 'vue'
import * as XLSX from 'xlsx'
import {
  detectSheetType,
  extractSingleInstrumentValues,
  getRequiredFieldMappings,
  detectInstrumentNameColumn,
  extractInstrumentNames
} from '@/utils/sheetTypeDetector'
import { autoMatchColumns, getDisplayColumns } from '@/utils/instrumentMapping'

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

export function useWorksheetWorkflow(instrumentTypeRef) {
  const uploadedFile = ref(null)
  const originalFileBuffer = ref(null)      // full ArrayBuffer for later full parsing
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

  const hasWorkbook = computed(() => workbookSheets.value.length > 0)
  const completedSheets = computed(() => 
    Object.values(worksheetStatus.value).filter(s => s === 'completed').length
  )
  const totalSheets = computed(() => workbookSheets.value.length)
  const progress = computed(() => 
    totalSheets.value > 0 ? (completedSheets.value / totalSheets.value) * 100 : 0
  )

  const currentInstrumentType = computed(() => toValue(instrumentTypeRef))

  // ========== UPLOAD ==========
  // Parse only first 1000 rows per sheet for speed – enough for preview & detection
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

      // Parse only first 1000 rows per sheet for initial detection
      const workbook = XLSX.read(arrayBuffer, { 
        type: 'array', 
        cellDates: true,
        cellStyles: false,
        cellNF: false,
        sheetRows: 1000            // ⬅️ limit rows for speed
      })

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
          column_count: sheetHeaders.length,
        })
      }

      workbookSheets.value = sheets

      worksheetStatus.value = {}
      sheets.forEach(sheet => {
        worksheetStatus.value[sheet.name] = 'not_started'
      })

      uploadProgress.value = 100
      console.log(`Workbook loaded (limited preview): ${sheets.length} sheets`)
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

  // ========== SHEET SELECTION ==========
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

    console.log(`Selected sheet: ${sheetName}, type: ${detection.type}`)
    return { success: true, sheet, type: detection.type }
  }

  // ========== FULL SHEET PARSING (on demand) ==========
  function parseFullSheet(sheetName) {
    if (!originalFileBuffer.value) {
      throw new Error('No file buffer available')
    }
    const workbook = XLSX.read(originalFileBuffer.value, {
      type: 'array',
      cellDates: true,
      cellStyles: false,
      cellNF: false,
      // no row limit
    })
    const worksheet = workbook.Sheets[sheetName]
    if (!worksheet) {
      throw new Error(`Sheet "${sheetName}" not found in full workbook`)
    }
    const jsonData = XLSX.utils.sheet_to_json(worksheet, { defval: '', raw: false })
    return jsonData
  }

  // ========== PROCESS WORKSHEET (re‑parse full sheet) ==========
  async function processWorksheet(sheetName, requiredColumns, columnVariations) {
    // Force full re‑parse of the selected sheet from the buffer
    let sheetData = []
    try {
      sheetData = parseFullSheet(sheetName)
    } catch (err) {
      error.value = `Failed to parse full sheet: ${err.message}`
      return { success: false, error: error.value }
    }

    if (!sheetData || sheetData.length === 0) {
      error.value = `No data found in sheet "${sheetName}"`
      return { success: false, error: error.value }
    }

    worksheetStatus.value[sheetName] = 'in_progress'

    try {
      const detection = detectSheetType(sheetData, currentInstrumentType.value)
      sheetType.value = detection.type

      if (detection.type === 'single') {
        const values = extractValuesIntelligently(sheetData, currentInstrumentType.value)
        extractedValues.value = values
        tabularData.value = convertExtractedToTabular(values)

        // Update the workbookSheets entry with full data
        const sheetIndex = workbookSheets.value.findIndex(s => s.name === sheetName)
        if (sheetIndex !== -1) {
          workbookSheets.value[sheetIndex].data = sheetData
          workbookSheets.value[sheetIndex].row_count = sheetData.length
        }

        worksheetStatus.value[sheetName] = 'completed'
        return {
          success: true,
          type: 'single',
          data: tabularData.value,
          extractedValues: values
        }
      } else {
        // Multi-instrument: use full sheet data
        tabularData.value = sheetData

        // Detect instrument name column
        let nameDetection = detectInstrumentNameColumn(sheetData)
        if (!nameDetection || !nameDetection.columnName) {
          const namePatterns = ['instrument', 'name', 'security', 'bond', 'tbill', 'issuer', 'counterparty', 'company', 'entity']
          let foundCol = null
          for (const header of Object.keys(sheetData[0] || {})) {
            const lowerHeader = header.toLowerCase()
            if (namePatterns.some(p => lowerHeader.includes(p))) {
              foundCol = header
              break
            }
          }
          if (foundCol) {
            nameDetection = { columnName: foundCol, confidence: 0.8 }
          } else if (Object.keys(sheetData[0] || {}).length > 0) {
            nameDetection = { columnName: Object.keys(sheetData[0])[0], confidence: 0.5 }
          }
        }
        instrumentNameColumn.value = nameDetection?.columnName || null
        if (nameDetection?.columnName) {
          detectedInstrumentNames.value = extractInstrumentNames(sheetData, nameDetection.columnName)
          console.log('Detected instrument names:', detectedInstrumentNames.value)
        }

        // Build column mapping
        let columnMapping = null
        if (requiredColumns && columnVariations) {
          const fileHeaders = Object.keys(sheetData[0] || {})
          columnMapping = autoMatchColumns(fileHeaders, requiredColumns, columnVariations)
          if (nameDetection?.columnName && columnMapping['Instrument Name'] !== nameDetection.columnName) {
            if (fileHeaders.includes(nameDetection.columnName)) {
              columnMapping['Instrument Name'] = nameDetection.columnName
            }
          }
          if (!columnMapping['Instrument Name']) {
            const nameCol = fileHeaders.find(h => 
              /name|instrument|security|bond|tbill|issuer|entity/i.test(h)
            )
            if (nameCol) {
              columnMapping['Instrument Name'] = nameCol
            }
          }
        }

        // Filter display columns
        const displayCols = getDisplayColumns(Object.keys(sheetData[0] || {}))
        const filteredData = sheetData.map(row => {
          const newRow = {}
          displayCols.forEach(col => {
            newRow[col] = row[col] !== undefined ? row[col] : ''
          })
          return newRow
        })

        // Update the workbookSheets entry with full data
        const sheetIndex = workbookSheets.value.findIndex(s => s.name === sheetName)
        if (sheetIndex !== -1) {
          workbookSheets.value[sheetIndex].data = sheetData
          workbookSheets.value[sheetIndex].row_count = sheetData.length
        }

        worksheetStatus.value[sheetName] = 'completed'
        return {
          success: true,
          type: 'multi',
          data: filteredData,
          headers: displayCols,
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

  // ========== HELPERS ==========
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