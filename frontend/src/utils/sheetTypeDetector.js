// utils/sheetTypeDetector.js
/**
 * Detects whether a worksheet contains multi-instrument or single-instrument data
 * and provides appropriate extraction logic for each type.
 */

/**
 * Detects the sheet type based on data structure
 * @param {Array} data - The sheet data as array of objects
 * @param {string} instrumentType - The instrument type (Money Market, Bonds, Treasury Bills)
 * @returns {Object} - { type: 'multi' | 'single', confidence: number, reason: string }
 */
export function detectSheetType(data, instrumentType) {
  if (!data || data.length === 0) {
    return { type: 'single', confidence: 0.5, reason: 'Empty data, defaulting to single-instrument' }
  }

  const rowCount = data.length
  const columnCount = Object.keys(data[0] || {}).length

  // Check for tabular structure (multi-instrument indicators)
  const hasTabularStructure = checkTabularStructure(data)
  const hasFieldValuePairStructure = checkFieldValuePairStructure(data)
  const hasMultipleTables = checkMultipleTables(data)
  const hasRepeatedHeaders = checkRepeatedHeaders(data)
  const hasInstrumentLabels = checkInstrumentLabels(data, instrumentType)

  // Scoring system
  let multiScore = 0
  let singleScore = 0

  // Multi-instrument indicators
  if (hasTabularStructure) multiScore += 3
  if (hasRepeatedHeaders) multiScore += 2
  if (hasInstrumentLabels) multiScore += 2
  if (rowCount > 10 && columnCount > 3) multiScore += 1

  // Single-instrument indicators
  if (hasFieldValuePairStructure) singleScore += 3
  if (hasMultipleTables) singleScore += 2
  if (rowCount < 20 && columnCount <= 2) singleScore += 1

  const totalScore = multiScore + singleScore
  const confidence = totalScore > 0 ? Math.max(multiScore, singleScore) / totalScore : 0.5

  if (multiScore > singleScore) {
    return {
      type: 'multi',
      confidence,
      reason: 'Detected tabular structure with multiple instruments'
    }
  } else if (singleScore > multiScore) {
    return {
      type: 'single',
      confidence,
      reason: 'Detected field-value pair or single-instrument structure'
    }
  }

  // Default to multi-instrument for ambiguous cases
  return {
    type: 'multi',
    confidence: 0.5,
    reason: 'Ambiguous structure, defaulting to multi-instrument'
  }
}

/**
 * Checks if data has tabular structure (typical of multi-instrument sheets)
 */
function checkTabularStructure(data) {
  if (data.length < 3) return false

  const firstRow = data[0]
  const keys = Object.keys(firstRow)

  // Check if most rows have similar structure
  let consistentRows = 0
  for (let i = 1; i < Math.min(data.length, 10); i++) {
    const rowKeys = Object.keys(data[i])
    const overlap = keys.filter(k => rowKeys.includes(k)).length
    if (overlap >= keys.length * 0.7) {
      consistentRows++
    }
  }

  return consistentRows >= Math.min(data.length - 1, 7) * 0.7
}

/**
 * Checks if data has field-value pair structure (typical of single-instrument sheets)
 */
function checkFieldValuePairStructure(data) {
  if (data.length < 2) return false

  // Look for pattern where first column is label, second is value
  let fieldValueCount = 0
  for (let i = 0; i < Math.min(data.length, 10); i++) {
    const row = data[i]
    const values = Object.values(row)
    
    if (values.length === 2) {
      const first = values[0]
      const second = values[1]
      
      // Check if first looks like a label (string) and second looks like a value
      if (typeof first === 'string' && first.length > 0 && 
          (typeof second === 'number' || (typeof second === 'string' && !isNaN(second)))) {
        fieldValueCount++
      }
    }
  }

  return fieldValueCount >= Math.min(data.length, 10) * 0.6
}

/**
 * Checks if data has multiple separate tables (typical of single-instrument with sections)
 */
function checkMultipleTables(data) {
  if (data.length < 5) return false

  // Look for blank rows that might separate tables
  let blankRowCount = 0
  for (let row of data) {
    const values = Object.values(row)
    const isEmpty = values.every(v => v === '' || v === null || v === undefined)
    if (isEmpty) blankRowCount++
  }

  return blankRowCount >= 2
}

/**
 * Checks for repeated headers (multi-instrument indicator)
 */
function checkRepeatedHeaders(data) {
  if (data.length < 4) return false

  const firstRowKeys = Object.keys(data[0]).map(k => k.toLowerCase())
  let repeatCount = 0

  for (let i = 1; i < data.length; i++) {
    const currentKeys = Object.keys(data[i]).map(k => k.toLowerCase())
    const matchCount = firstRowKeys.filter(key => currentKeys.includes(key)).length
    if (matchCount > firstRowKeys.length * 0.7) {
      repeatCount++
    }
  }

  return repeatCount >= 2
}

/**
 * Checks for instrument labels (multi-instrument indicator)
 */
function checkInstrumentLabels(data, instrumentType) {
  const labels = ['Instrument', 'Bond', 'T-Bill', 'Money Market', 'Treasury Bill', 'Security', 'Issuer', 
                  'Company', 'Name', 'Description', 'Ticker', 'Symbol', 'Entity']
  const lowerLabels = labels.map(l => l.toLowerCase())
  let labelCount = 0

  for (let row of data) {
    const values = Object.values(row)
    values.forEach(val => {
      if (val && typeof val === 'string') {
        const lowerVal = val.toLowerCase()
        if (lowerLabels.some(label => lowerVal.includes(label))) {
          labelCount++
        }
      }
    })
  }

  return labelCount >= 2
}

/**
 * Detects instrument name column in multi-instrument data
 * @param {Array} data - The sheet data
 * @returns {Object} - { columnName: string, confidence: number }
 */
export function detectInstrumentNameColumn(data) {
  if (!data || data.length < 2) return { columnName: null, confidence: 0 }

  const headers = Object.keys(data[0])
  const nameKeywords = ['name', 'instrument', 'company', 'issuer', 'security', 'entity', 'ticker', 'symbol', 'description']
  
  let bestMatch = null
  let bestConfidence = 0

  for (const header of headers) {
    const lowerHeader = header.toLowerCase()
    let confidence = 0
    
    // Direct match
    if (nameKeywords.some(keyword => lowerHeader === keyword)) {
      confidence = 0.9
    }
    // Partial match
    else if (nameKeywords.some(keyword => lowerHeader.includes(keyword))) {
      confidence = 0.7
    }
    // Check if column contains varied string values (likely names)
    else {
      const uniqueValues = new Set()
      for (let i = 0; i < Math.min(data.length, 20); i++) {
        const val = data[i][header]
        if (val && typeof val === 'string' && val.length > 2) {
          uniqueValues.add(val)
        }
      }
      // If column has many unique string values, it might be names
      if (uniqueValues.size >= 3 && uniqueValues.size <= data.length * 0.8) {
        confidence = 0.5
      }
    }

    if (confidence > bestConfidence) {
      bestMatch = header
      bestConfidence = confidence
    }
  }

  return { columnName: bestMatch, confidence: bestConfidence }
}

/**
 * Extracts instrument names from multi-instrument data
 * @param {Array} data - The sheet data
 * @param {string} columnName - The column containing instrument names
 * @returns {Array} - Array of instrument names
 */
export function extractInstrumentNames(data, columnName) {
  if (!data || !columnName) return []

  const names = []
  const seen = new Set()

  for (const row of data) {
    const name = row[columnName]
    if (name && typeof name === 'string' && name.trim()) {
      const trimmedName = name.trim()
      if (!seen.has(trimmedName)) {
        seen.add(trimmedName)
        names.push(trimmedName)
      }
    }
  }

  return names
}

/**
 * Extracts values from single-instrument sheet using field-value pairs
 * @param {Array} data - The sheet data
 * @param {Object} requiredFields - Map of field labels to extract (label -> target key)
 * @returns {Object} - Extracted values
 */
export function extractSingleInstrumentValues(data, requiredFields) {
  const extracted = {}
  const dataMap = new Map()

  // Build a map of normalized labels to values
  for (let row of data) {
    const values = Object.values(row)
    if (values.length >= 2) {
      const label = String(values[0] || '').toLowerCase().trim()
      const value = values[1]
      if (label && value !== undefined && value !== null && value !== '') {
        dataMap.set(label, value)
      }
    }
  }

  // Extract required fields
  for (const [targetKey, possibleLabels] of Object.entries(requiredFields)) {
    for (const label of possibleLabels) {
      const normalizedLabel = label.toLowerCase()
      for (const [dataLabel, dataValue] of dataMap.entries()) {
        if (dataLabel.includes(normalizedLabel) || normalizedLabel.includes(dataLabel)) {
          extracted[targetKey] = dataValue
          break
        }
      }
      if (extracted[targetKey]) break
    }
  }

  return extracted
}

/**
 * Gets required field mappings for each instrument type
 * @param {string} instrumentType - The instrument type
 * @returns {Object} - Map of target keys to possible label variations
 */
export function getRequiredFieldMappings(instrumentType) {
  const mappings = {
    'money-market': {
      faceValue: ['Face Value', 'Principal', 'Amount', 'Notional'],
      issueDate: ['Issue Date', 'Date', 'Start Date'],
      maturityDate: ['Maturity Date', 'Maturity', 'End Date'],
      couponRate: ['Coupon Rate', 'Coupon', 'Interest Rate', 'Rate'],
      yield: ['Yield', 'YTM', 'Yield to Maturity'],
      price: ['Price', 'Market Price', 'Clean Price']
    },
    'bonds': {
      faceValue: ['Face Value', 'Principal', 'Par Value', 'Amount'],
      issueDate: ['Issue Date', 'Date', 'Start Date'],
      maturityDate: ['Maturity Date', 'Maturity', 'End Date'],
      couponRate: ['Coupon Rate', 'Coupon', 'Interest Rate'],
      yield: ['Yield', 'YTM', 'Yield to Maturity'],
      price: ['Price', 'Market Price', 'Clean Price'],
      frequency: ['Frequency', 'Payment Frequency', 'Coupon Frequency']
    },
    'tbills': {
      faceValue: ['Face Value', 'Principal', 'Amount', 'Notional'],
      issueDate: ['Issue Date', 'Date', 'Auction Date'],
      maturityDate: ['Maturity Date', 'Maturity', 'End Date'],
      discountRate: ['Discount Rate', 'Discount', 'Rate'],
      price: ['Price', 'Market Price', 'Issue Price']
    }
  }

  return mappings[instrumentType] || mappings['money-market']
}