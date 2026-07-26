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
  // Money Market Instruments
  principal: ['principal', 'face value', 'par value', 'nominal', 'amount', 'notional', 'investment amount', 'capital', 'deposit amount', 'initial investment', 'starting balance'],
  interestRate: ['interest rate', 'rate', 'yield', 'annual rate', 'nominal rate', 'coupon', 'stated rate', 'apr', 'effective rate'],
  daysToMaturity: ['days to maturity', 'term', 'tenor', 'maturity days', 'duration days', 'period', 'days', 'contract days'],
  issueDate: ['issue date', 'start date', 'effective date', 'trade date', 'settlement date', 'origination date', 'value date'],
  maturityDate: ['maturity date', 'end date', 'due date', 'redemption date', 'expiry date', 'termination date'],
  purchasePrice: ['purchase price', 'buy price', 'acquisition price', 'entry price', 'cost', 'price paid'],
  settlementAmount: ['settlement amount', 'settlement value', 'cash flow', 'proceeds'],
  
  // T-Bills
  faceValue: ['face value', 'par value', 'redemption value', 'maturity value', 'amount', 'principal', 'nominal'],
  discountRate: ['discount rate', 'bank discount', 'discount yield', 'rate', 't-bill rate', 'auction rate', 'discount'],
  auctionDate: ['auction date', 'issue date', 'start date', 'settlement date', 'trade date'],
  
  // Bonds
  couponRate: ['coupon rate', 'coupon', 'interest rate', 'nominal rate', 'stated rate', 'annual coupon', 'fixed rate'],
  couponFrequency: ['coupon frequency', 'frequency', 'payment frequency', 'period', 'semi-annual', 'quarterly', 'annual', 'coupon period'],
  price: ['price', 'market price', 'clean price', 'dirty price', 'current price', 'flat price', 'quoted price'],
  yield: ['yield', 'yield to maturity', 'ytm', 'required return', 'market yield', 'effective yield', 'redemption yield'],
  callDate: ['call date', 'first call date', 'callable date', 'early redemption date'],
  callPrice: ['call price', 'call premium', 'redemption price', 'sinking fund price'],
  putDate: ['put date', 'puttable date', 'putable date'],
  putPrice: ['put price', 'put premium'],
  benchmarkRate: ['benchmark', 'risk-free rate', 'government yield', 'sofr', 'treasury yield'],
  creditSpread: ['credit spread', 'g-spread', 'z-spread', 'asset swap spread', 'oas'],
  inflationRate: ['inflation', 'cpi', 'inflation rate', 'real yield proxy'],
  
  // Common fields
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

    // Accept all Excel-compatible formats - no restrictions
    // XLSX library supports: .xlsx, .xls, .xlsm, .xlsb, .csv, .ods, .xml, .html, .txt, .prn, .dif, .slk, .dbf
    const validExtensions = ['.csv', '.xlsx', '.xls', '.xlsm', '.xlsb', '.xltx', '.xltm', '.xlam', '.ods', '.xml', '.html', '.prn', '.dif', '.slk', '.dbf', '.txt', '.fods', '.numbers']
    const fileName = file.name.toLowerCase()
    const hasValidExtension = validExtensions.some(ext => fileName.endsWith(ext))
    
    // Also accept files without extensions if they appear to be Excel files
    const isLikelyExcel = fileName.includes('excel') || fileName.includes('sheet') || fileName.includes('workbook')
    
    if (!hasValidExtension && !isLikelyExcel) {
      // Try to parse anyway - XLSX library can handle many formats
      console.log('File extension not recognized, attempting to parse anyway')
    }

    loading.value = true
    error.value = ''
    uploadProgress.value = 0

    // Add timeout protection
    const timeoutPromise = new Promise((_, reject) => 
      setTimeout(() => reject(new Error('File parsing timeout - file may be too large or corrupted')), 60000)
    )

    try {
      const arrayBuffer = await Promise.race([
        file.arrayBuffer(),
        timeoutPromise
      ])
      originalFileBuffer.value = arrayBuffer
      uploadedFile.value = new File([file], file.name, { type: file.type })

      uploadProgress.value = 30

      // Parse workbook with simplified options for better compatibility
      let workbook
      try {
        console.log('Starting XLSX parsing...')
        workbook = XLSX.read(arrayBuffer, { 
          type: 'array',
        })
        console.log('XLSX parsing completed successfully')
      } catch (e) {
        console.error('XLSX parsing error:', e)
        console.error('Error stack:', e.stack)
        throw new Error(`Failed to parse Excel file: ${e.message}`)
      }

      // Validate workbook structure
      if (!workbook) {
        throw new Error('Failed to read workbook - invalid file format')
      }

      console.log('Workbook parsed successfully')
      console.log('workbook.SheetNames:', workbook.SheetNames)
      console.log('workbook.Sheets keys:', Object.keys(workbook.Sheets || {}))

      uploadProgress.value = 60

      const sheets = []
      
      // Use SheetNames array directly
      const sheetNames = workbook.SheetNames || []
      
      console.log(`Processing ${sheetNames.length} sheets from workbook`)

      for (const sheetName of sheetNames) {
        console.log(`Starting to process sheet: "${sheetName}"`)
        
        if (!sheetName || typeof sheetName !== 'string') {
          console.warn(`Skipping invalid sheet name: ${sheetName}`)
          continue
        }

        const worksheet = workbook.Sheets[sheetName]
        
        console.log(`Processing sheet "${sheetName}":`, worksheet ? 'found' : 'NOT FOUND')
        
        if (!worksheet || typeof worksheet !== 'object') {
          console.warn(`Skipping invalid sheet: ${sheetName}`)
          continue
        }
        
        try {
          // Check if sheet is hidden
          const isHidden = worksheet['!hidden'] || false
          
          // Get full 2D array data with defensive coding
          let fullData = []
          try {
            // Check if worksheet has a valid range
            const ref = worksheet['!ref']
            if (!ref) {
              console.warn(`Sheet ${sheetName} has no valid range, creating empty sheet`)
              fullData = []
            } else {
              const range = XLSX.utils.decode_range(ref)
              if (!range || typeof range !== 'object') {
                console.warn(`Invalid range for sheet ${sheetName}, creating empty sheet`)
                fullData = []
              } else {
                for (let R = range.s.r; R <= range.e.r; R++) {
                  const row = []
                  for (let C = range.s.c; C <= range.e.c; C++) {
                    const cellAddress = XLSX.utils.encode_cell({ r: R, c: C })
                    const cell = worksheet[cellAddress]
                    // Preserve formula if present, otherwise use value
                    if (cell && cell.f) {
                      row.push(cell.f) // Store formula
                    } else if (cell && cell.v !== undefined) {
                      row.push(cell.v) // Store value
                    } else {
                      row.push('')
                    }
                  }
                  fullData.push(row)
                }
              }
            }
          } catch (e) {
            console.warn(`Failed to parse sheet data for ${sheetName}:`, e)
            fullData = []
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
          
          // Get table information if present
          const tables = []
          if (worksheet['!tables']) {
            for (const tableName in worksheet['!tables']) {
              tables.push(worksheet['!tables'][tableName])
            }
          }
          
          // Also get JSON data for compatibility
          let jsonData = []
          let sheetHeaders = []
          try {
            jsonData = XLSX.utils.sheet_to_json(worksheet, { defval: '', raw: false })
            if (jsonData.length > 0 && jsonData[0]) {
              sheetHeaders = Object.keys(jsonData[0])
            }
          } catch (e) {
            console.warn(`Failed to parse sheet ${sheetName}:`, e)
            jsonData = []
            sheetHeaders = []
          }

          sheets.push({
            name: sheetName,
            data: jsonData,
            headers: sheetHeaders,
            fullData: fullData,
            merged_ranges: mergedRanges,
            tables: tables,
            hidden: isHidden,
            row_count: fullData.length,
            column_count: fullData.length > 0 ? fullData[0].length : 0,
          })
          console.log(`Added sheet ${sheetName} with ${fullData.length} rows, ${jsonData.length} JSON rows`)
        } catch (sheetError) {
          console.error(`Error processing sheet ${sheetName}:`, sheetError)
          console.error('Sheet error stack:', sheetError.stack)
        }
      }

      if (sheets.length === 0) {
        console.warn('No sheets were successfully processed, but continuing with empty array')
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
      cellStyles: true,
      cellNF: true,
    })
    const worksheet = workbook.Sheets[sheetName]
    if (!worksheet) {
      throw new Error(`Sheet "${sheetName}" not found in full workbook`)
    }
    
    // Get full 2D array data
    const range = XLSX.utils.decode_range(worksheet['!ref'] || 'A1')
    const fullData = []
    for (let R = range.s.r; R <= range.e.r; R++) {
      const row = []
      for (let C = range.s.c; C <= range.e.c; C++) {
        const cellAddress = XLSX.utils.encode_cell({ r: R, c: C })
        const cell = worksheet[cellAddress]
        row.push(cell ? cell.v : '')
      }
      fullData.push(row)
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
    
    // Also get JSON data for compatibility
    const jsonData = XLSX.utils.sheet_to_json(worksheet, { defval: '', raw: false })
    
    return { jsonData, fullData, mergedRanges }
  }

  // ========== PROCESS WORKSHEET (re‑parse full sheet) ==========
  async function processWorksheet(sheetName, requiredColumns, columnVariations) {
    // Force full re‑parse of the selected sheet from the buffer
    let parseResult = null
    try {
      parseResult = parseFullSheet(sheetName)
    } catch (err) {
      error.value = `Failed to parse full sheet: ${err.message}`
      return { success: false, error: error.value }
    }

    const sheetData = parseResult?.jsonData || []
    const fullData = parseResult?.fullData || []
    const mergedRanges = parseResult?.mergedRanges || []

    if (!sheetData || sheetData.length === 0) {
      error.value = `No data found in sheet "${sheetName}"`
      return { success: false, error: error.value }
    }

    worksheetStatus.value[sheetName] = 'in_progress'

    try {
      const detection = detectSheetType(sheetData, currentInstrumentType.value)
      sheetType.value = detection.type

      // Update the workbookSheets entry with full data andmerged ranges
      const sheetIndex = workbookSheets.value.findIndex(s => s.name === sheetName)
      if (sheetIndex !== -1) {
        workbookSheets.value[sheetIndex].data = sheetData
        workbookSheets.value[sheetIndex].fullData = fullData
        workbookSheets.value[sheetIndex].merged_ranges = mergedRanges
        workbookSheets.value[sheetIndex].row_count = fullData.length
        workbookSheets.value[sheetIndex].column_count = fullData.length > 0 ? fullData[0].length : 0
      }

      if (detection.type === 'single') {
        const values = extractValuesIntelligently(sheetData, currentInstrumentType.value)
        extractedValues.value = values
        tabularData.value = convertExtractedToTabular(values)

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