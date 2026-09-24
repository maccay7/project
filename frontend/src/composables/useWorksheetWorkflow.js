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

function extractValuesIntelligently(data, instrumentType) {
  const requiredFields = getRequiredFieldMappings(instrumentType)
  const extracted = extractSingleInstrumentValues(data, requiredFields)

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

  // ========== UPLOAD FULL FILE TO BACKEND ==========
  async function uploadFullFileToBackend(file, sessionId = null, instrumentType = 'money-market') {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('instrument_type', instrumentType)
    if (sessionId) {
      formData.append('session_id', sessionId)
    }

    try {
      const apiUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000'
      const response = await fetch(`${apiUrl}/api/upload`, {
        method: 'POST',
        body: formData
      })
      const result = await response.json()
      if (result.success) {
        console.log('Full file uploaded to backend:', result.data)
        return { success: true, data: result.data }
      } else {
        return { success: false, error: result.message }
      }
    } catch (err) {
      console.error('Failed to upload full file to backend:', err)
      return { success: false, error: err.message }
    }
  }

  // ========== UPLOAD ==========
  // Parse only metadata (sheet names, row counts, column counts) - NOT full data
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
          cellStyles: true,
          cellFormula: true,
          cellDates: true,
          cellNF: true
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

      if (!workbook.SheetNames || !workbook.SheetNames.length) {
        throw new Error('No worksheets found in uploaded workbook')
      }

      console.log('Workbook parsed successfully')
      console.log('workbook.SheetNames:', workbook.SheetNames)
      console.log('workbook.Sheets keys:', Object.keys(workbook.Sheets || {}))

      uploadProgress.value = 60

      const sheets = []
      
      // Use SheetNames array directly
      const sheetNames = workbook.SheetNames || []
      
      console.log(`Processing ${sheetNames.length} sheets from workbook`)

      // Extract only metadata (sheet names, row counts, column counts) - NOT full data
      for (const sheetName of sheetNames) {
        console.log(`Extracting metadata for sheet: "${sheetName}"`)
        
        if (!sheetName || typeof sheetName !== 'string') {
          console.warn(`Skipping invalid sheet name: ${sheetName}`)
          continue
        }

        const worksheet = workbook.Sheets[sheetName]
        
        if (!worksheet || typeof worksheet !== 'object') {
          console.warn(`Skipping invalid sheet: ${sheetName}`)
          continue
        }
        
        try {
          // Check if sheet is hidden
          const isHidden = worksheet['!hidden'] || false
          
          // Extract only metadata - row count, column count, merged ranges
          let rowCount = 0
          let colCount = 0
          let mergedRanges = []
          
          try {
            const ref = worksheet['!ref']
            if (ref) {
              const range = XLSX.utils.decode_range(ref)
              if (range && typeof range === 'object') {
                rowCount = range.e.r - range.s.r + 1
                colCount = range.e.c - range.s.c + 1
                console.log(`Sheet "${sheetName}": ${rowCount} rows, ${colCount} columns`)
              }
            }
            
            // Get merged ranges
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
          } catch (e) {
            console.warn(`Failed to extract metadata for sheet ${sheetName}:`, e)
          }
          
          sheets.push({
            name: sheetName,
            rowCount: rowCount,
            colCount: colCount,
            mergedRanges: mergedRanges,
            isHidden: isHidden
            // NO fullData, jsonData, headers - those will be loaded on demand from backend
          })
        } catch (e) {
          console.warn(`Failed to process sheet ${sheetName}:`, e)
          console.error('Sheet error stack:', e.stack)
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
      console.log(`Workbook metadata extracted: ${sheets.length} sheets`)
      
      // Store workbook data for ExcelWorkbookViewer
      console.log('Storing workbook data for viewer...')
      console.log('originalFileBuffer.value set, byteLength:', originalFileBuffer.value.byteLength)
      
      // Upload full file to backend to preserve complete dataset
      console.log('Uploading full file to backend for preservation...')
      const uploadResult = await uploadFullFileToBackend(file, null, currentInstrumentType.value)
      if (uploadResult.success) {
        console.log('Full file uploaded successfully, dataset_id:', uploadResult.data.dataset_id)
        sheets.forEach(sheet => {
          sheet.datasetId = uploadResult.data.dataset_id
          sheet.metadata = uploadResult.data.metadata
        })
      } else {
        console.warn('Failed to upload full file to backend:', uploadResult.error)
        // Continue anyway - frontend can still work with preview data
      }
      
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

    // Don't detect type yet - will do after loading preview data
    console.log(`Selected sheet: ${sheetName} (${sheet.rowCount} rows, ${sheet.colCount} columns)`)
    return { success: true, sheet }
  }

  // ========== PREVIEW SHEET PARSING (chunked, on demand) ==========
  function parseSheetPreview(sheetName, maxRows = 100) {
    if (!originalFileBuffer.value) {
      throw new Error('No file buffer available')
    }
    const workbook = XLSX.read(originalFileBuffer.value, {
      type: 'array',
      cellStyles: true,
      cellFormula: true,
      cellDates: true,
      cellNF: true
    })
    const worksheet = workbook.Sheets[sheetName]
    if (!worksheet) {
      throw new Error(`Sheet "${sheetName}" not found in workbook`)
    }
    
    // Get limited preview data
    const ref = worksheet['!ref']
    if (!ref) {
      return { jsonData: [], headers: [], fullData: [] }
    }
    
    const range = XLSX.utils.decode_range(ref)
    const previewRows = Math.min(maxRows, range.e.r - range.s.r + 1)
    
    const fullData = []
    for (let R = range.s.r; R < range.s.r + previewRows; R++) {
      const row = []
      for (let C = range.s.c; C <= range.e.c; C++) {
        const cellAddress = XLSX.utils.encode_cell({ r: R, c: C })
        const cell = worksheet[cellAddress]
        row.push(cell ? cell.v : '')
      }
      fullData.push(row)
    }
    
    // Get JSON data for preview
    const jsonData = XLSX.utils.sheet_to_json(worksheet, { 
      defval: '', 
      raw: false,
      range: previewRows
    })
    
    const headers = jsonData.length > 0 ? Object.keys(jsonData[0]) : []
    
    return { jsonData, headers, fullData, totalRows: range.e.r - range.s.r + 1 }
  }

  // ========== FULL SHEET PARSING (on demand, for backend processing) ==========
  function parseFullSheet(sheetName) {
    if (!originalFileBuffer.value) {
      throw new Error('No file buffer available')
    }
    const workbook = XLSX.read(originalFileBuffer.value, {
      type: 'array',
      cellStyles: true,
      cellFormula: true,
      cellDates: true,
      cellNF: true
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

  // ========== PROCESS WORKSHEET (use preview data for UI, full data for backend) ==========
  async function processWorksheet(sheetName, requiredColumns, columnVariations) {
    // Load preview data only (100 rows) for UI processing
    let parseResult = null
    try {
      parseResult = parseSheetPreview(sheetName, 100)
    } catch (err) {
      error.value = `Failed to parse sheet preview: ${err.message}`
      return { success: false, error: error.value }
    }

    const sheetData = parseResult?.jsonData || []
    const fullData = parseResult?.fullData || []
    const headers = parseResult?.headers || []
    const totalRows = parseResult?.totalRows || 0

    if (!sheetData || sheetData.length === 0) {
      error.value = `No data found in sheet "${sheetName}"`
      return { success: false, error: error.value }
    }

    worksheetStatus.value[sheetName] = 'in_progress'

    try {
      const detection = detectSheetType(sheetData, currentInstrumentType.value)
      sheetType.value = detection.type

      // Update the workbookSheets entry with preview data
      const sheetIndex = workbookSheets.value.findIndex(s => s.name === sheetName)
      if (sheetIndex !== -1) {
        workbookSheets.value[sheetIndex].data = sheetData
        workbookSheets.value[sheetIndex].fullData = fullData
        workbookSheets.value[sheetIndex].headers = headers
        workbookSheets.value[sheetIndex].totalRows = totalRows
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
          extractedValues: values,
          totalRows: totalRows
        }
      } else {
        // Multi-instrument: use preview data for UI
        tabularData.value = sheetData

        // Detect instrument name column
        let nameDetection = detectInstrumentNameColumn(sheetData)
        if (!nameDetection || !nameDetection.columnName) {
          const namePatterns = ['instrument', 'name', 'security', 'bond', 'tbill', 'issuer', 'counterparty', 'company', 'entity']
          let foundCol = null
          for (const header of headers) {
            const lowerHeader = header.toLowerCase()
            if (namePatterns.some(p => lowerHeader.includes(p))) {
              foundCol = header
              break
            }
          }
          if (foundCol) {
            nameDetection = { columnName: foundCol, confidence: 0.8 }
          } else if (headers.length > 0) {
            nameDetection = { columnName: headers[0], confidence: 0.5 }
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
          columnMapping = autoMatchColumns(headers, requiredColumns, columnVariations)
          if (nameDetection?.columnName && columnMapping['Instrument Name'] !== nameDetection.columnName) {
            if (headers.includes(nameDetection.columnName)) {
              columnMapping['Instrument Name'] = nameDetection.columnName
            }
          }
          if (!columnMapping['Instrument Name']) {
            const nameCol = headers.find(h => 
              /name|instrument|security|bond|tbill|issuer|entity/i.test(h)
            )
            if (nameCol) {
              columnMapping['Instrument Name'] = nameCol
            }
          }
        }

        // Filter display columns
        const displayCols = getDisplayColumns(headers)
        const filteredData = sheetData.map(row => {
          const newRow = {}
          displayCols.forEach(col => {
            newRow[col] = row[col] !== undefined ? row[col] : ''
          })
          return newRow
        })

        worksheetStatus.value[sheetName] = 'completed'
        return {
          success: true,
          type: 'multi',
          data: filteredData,
          headers: headers,
          totalRows: totalRows,
          columnMapping: columnMapping,
          instrumentNameColumn: instrumentNameColumn.value
        }
      }
    } catch (err) {
      error.value = `Failed to process worksheet: ${err.message}`
      worksheetStatus.value[sheetName] = 'error'
      return { success: false, error: error.value }
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
    parseSheetPreview,
    parseFullSheet,
    processWorksheet,
    getCurrentData,
    reset,
    getStateSnapshot,
    restoreState
  }
}