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

function findDensestCluster(sortedPositions, gapThreshold) {
  if (!sortedPositions || sortedPositions.length === 0) {
    return { min: -1, max: -1, count: 0 }
  }
  if (sortedPositions.length === 1) {
    return { min: sortedPositions[0], max: sortedPositions[0], count: 1 }
  }

  let bestStart = 0
  let bestEnd = 0
  let bestCount = 1
  let curStart = 0

  for (let i = 1; i < sortedPositions.length; i++) {
    if (sortedPositions[i] - sortedPositions[i - 1] > gapThreshold) {
      const count = i - curStart
      if (count > bestCount) {
        bestCount = count
        bestStart = curStart
        bestEnd = i - 1
      }
      curStart = i
    }
  }

  const finalCount = sortedPositions.length - curStart
  if (finalCount > bestCount) {
    bestCount = finalCount
    bestStart = curStart
    bestEnd = sortedPositions.length - 1
  }

  return {
    min: sortedPositions[bestStart],
    max: sortedPositions[bestEnd],
    count: bestCount
  }
}

function getTrueRange(worksheet) {
  if (!worksheet) return null

  const declaredRef = worksheet['!ref']
  const declared = declaredRef ? XLSX.utils.decode_range(declaredRef) : null

  const rowPositions = []
  const colPositions = []
  let cellCount = 0
  let minRow = Infinity, maxRow = -1
  let minCol = Infinity, maxCol = -1

  for (const addr in worksheet) {
    if (addr[0] === '!') continue
    let decoded
    try { decoded = XLSX.utils.decode_cell(addr) } catch (e) { continue }
    const cell = worksheet[addr]
    if (!cell) continue
    const hasValue = cell.v !== undefined && cell.v !== null && cell.v !== ''
    const hasFormula = cell.f !== undefined && cell.f !== null && cell.f !== ''
    if (!hasValue && !hasFormula) continue

    cellCount++
    rowPositions.push(decoded.r)
    colPositions.push(decoded.c)
    if (decoded.r < minRow) minRow = decoded.r
    if (decoded.r > maxRow) maxRow = decoded.r
    if (decoded.c < minCol) minCol = decoded.c
    if (decoded.c > maxCol) maxCol = decoded.c
  }

  if (maxRow === -1 || maxCol === -1) return declared

  const height = maxRow - minRow + 1
  const width  = maxCol - minCol + 1
  const area   = height * width

  if (area > 1_000_000 && cellCount / area < 0.001) {
    const uniqueRows = [...new Set(rowPositions)].sort((a, b) => a - b)
    const uniqueCols = [...new Set(colPositions)].sort((a, b) => a - b)

    const ROW_GAP = 50
    const COL_GAP = 10

    const rowCluster = findDensestCluster(uniqueRows, ROW_GAP)
    const colCluster = findDensestCluster(uniqueCols, COL_GAP)

    const rowCoverage = uniqueRows.length ? rowCluster.count / uniqueRows.length : 0
    const colCoverage = uniqueCols.length ? colCluster.count / uniqueCols.length : 0

    if (
      rowCoverage >= 0.5 &&
      colCoverage >= 0.5 &&
      rowCluster.min !== -1 &&
      colCluster.min !== -1
    ) {
      const newMinRow = Math.max(minRow, rowCluster.min)
      const newMaxRow = Math.min(maxRow, rowCluster.max)
      const newMinCol = Math.max(minCol, colCluster.min)
      const newMaxCol = Math.min(maxCol, colCluster.max)

      console.warn(
        `useWorksheetWorkflow: phantom range detected on sheet ` +
        `(declared ${declaredRef || 'n/a'}) — ${area.toLocaleString()} cells claimed, ` +
        `${cellCount.toLocaleString()} real. Trimming to ` +
        `${newMaxRow - newMinRow + 1} rows × ${newMaxCol - newMinCol + 1} columns.`
      )

      return {
        s: { r: newMinRow, c: newMinCol },
        e: { r: newMaxRow, c: newMaxCol }
      }
    }

    const MAX_CLIPPED_ROWS = 10000
    const MAX_CLIPPED_COLS = 200
    const cappedMaxRow = Math.min(maxRow, minRow + MAX_CLIPPED_ROWS - 1)
    const cappedMaxCol = Math.min(maxCol, minCol + MAX_CLIPPED_COLS - 1)

    console.warn(
      `useWorksheetWorkflow: phantom range on sheet (declared ${declaredRef || 'n/a'}) — ` +
      `${area.toLocaleString()} cells claimed, only ${cellCount.toLocaleString()} real. ` +
      `Clipping to ${cappedMaxRow - minRow + 1} rows × ${cappedMaxCol - minCol + 1} columns.`
    )

    return {
      s: { r: minRow, c: minCol },
      e: { r: cappedMaxRow, c: cappedMaxCol }
    }
  }

  return { s: { r: minRow, c: minCol }, e: { r: maxRow, c: maxCol } }
}

export function useWorksheetWorkflow(instrumentTypeRef) {
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

  const hasWorkbook = computed(() => workbookSheets.value.length > 0)
  const completedSheets = computed(() => 
    Object.values(worksheetStatus.value).filter(s => s === 'completed').length
  )
  const totalSheets = computed(() => workbookSheets.value.length)
  const progress = computed(() => 
    totalSheets.value > 0 ? (completedSheets.value / totalSheets.value) * 100 : 0
  )

  const currentInstrumentType = computed(() => toValue(instrumentTypeRef))

  async function uploadFullFileToBackend(file, sessionId = null, instrumentType = 'money-market') {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('instrument_type', instrumentType)
    if (sessionId) {
      formData.append('session_id', sessionId)
    }

    try {
      const apiUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000'
      const response = await fetch(`${apiUrl}/api/dataset/upload`, {
        method: 'POST',
        body: formData
      })
      if (!response.ok) {
        console.warn('Optional backend upload failed (non-critical):', response.status)
        return { success: false, error: `Upload failed: ${response.status}` }
      }
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

  async function handleFileUpload(file) {
    if (!file) {
      error.value = 'No file provided'
      return { success: false, error: 'No file provided' }
    }

    const validExtensions = ['.csv', '.xlsx', '.xls', '.xlsm', '.xlsb', '.xltx', '.xltm', '.xlam', '.ods', '.xml', '.html', '.prn', '.dif', '.slk', '.dbf', '.txt', '.fods', '.numbers']
    const fileName = file.name.toLowerCase()
    const hasValidExtension = validExtensions.some(ext => fileName.endsWith(ext))
    
    const isLikelyExcel = fileName.includes('excel') || fileName.includes('sheet') || fileName.includes('workbook')
    
    if (!hasValidExtension && !isLikelyExcel) {
      console.log('File extension not recognized, attempting to parse anyway')
    }

    loading.value = true
    error.value = ''
    uploadProgress.value = 0

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
      const sheetNames = workbook.SheetNames || []
      
      console.log(`Processing ${sheetNames.length} sheets from workbook`)

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
          const isHidden = worksheet['!hidden'] || false
          
          let rowCount = 0
          let colCount = 0
          let mergedRanges = []
          
          try {
            const trueRange = getTrueRange(worksheet)
            if (trueRange) {
              rowCount = trueRange.e.r - trueRange.s.r + 1
              colCount = trueRange.e.c - trueRange.s.c + 1
              console.log(`Sheet "${sheetName}": ${rowCount} rows, ${colCount} columns`)
            }
            
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
      
      console.log('Storing workbook data for viewer...')
      console.log('originalFileBuffer.value set, byteLength:', originalFileBuffer.value.byteLength)
      
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

  function selectWorksheet(sheetName) {
    const sheet = workbookSheets.value.find(s => s.name === sheetName)
    if (!sheet) {
      error.value = `Sheet "${sheetName}" not found`
      return { success: false, error: error.value }
    }

    selectedWorksheet.value = sheet
    currentSheetName.value = sheetName

    console.log(`Selected sheet: ${sheetName} (${sheet.rowCount} rows, ${sheet.colCount} columns)`)
    return { success: true, sheet }
  }

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
    
    const range = getTrueRange(worksheet)
    if (!range) {
      return { jsonData: [], headers: [], fullData: [], totalRows: 0 }
    }
    
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
    
    const jsonData = XLSX.utils.sheet_to_json(worksheet, { 
      defval: '', 
      raw: false,
      range: previewRows
    })
    
    const headers = jsonData.length > 0 ? Object.keys(jsonData[0]) : []
    
    return { jsonData, headers, fullData, totalRows: range.e.r - range.s.r + 1 }
  }

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
    
    const range = getTrueRange(worksheet) || { s: { r: 0, c: 0 }, e: { r: 0, c: 0 } }
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
    
    const jsonData = XLSX.utils.sheet_to_json(worksheet, { defval: '', raw: false })
    
    return { jsonData, fullData, mergedRanges }
  }

  async function processWorksheet(sheetName, requiredColumns, columnVariations) {
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
        tabularData.value = sheetData

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