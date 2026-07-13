// utils/sheetTypeDetector.js

/**
 * Utility functions for detecting sheet type (single vs multi-instrument)
 * and extracting instrument names and values from Excel sheets.
 * 
 * 🔥 FIXED: Improved detection with better pattern matching,
 * enhanced extraction, and confidence scoring.
 */

/**
 * Detect whether a sheet contains a single instrument or multiple instruments
 * @param {Array} data - Sheet data as array of objects
 * @param {string} instrumentType - Type of instrument (money-market, bonds, tbills)
 * @returns {Object} { type: 'single' | 'multi', data: any, confidence: number }
 */
export function detectSheetType(data, instrumentType = 'money-market') {
  if (!data || !data.length) {
    return { type: 'single', data: [], confidence: 0 }
  }

  const rowCount = data.length
  const firstRow = data[0] || {}
  const colCount = Object.keys(firstRow).length
  const allKeys = new Set()
  
  // Collect all unique keys from all rows
  for (const row of data) {
    for (const key of Object.keys(row)) {
      allKeys.add(key.toLowerCase())
    }
  }
  const uniqueKeyCount = allKeys.size

  // 🔥 Check if this is a key-value style (single instrument)
  // Single instrument sheets typically have: few rows, many columns, sparse data
  const isKeyValueStyle = rowCount <= 5 && colCount >= 3 && uniqueKeyCount >= 3
  
  // Check for repeated headers (multi-instrument indicator)
  const hasRepeatedHeaders = checkForRepeatedHeaders(data)
  
  // Check for blank rows separating instruments
  const hasBlankSeparators = checkForBlankRows(data)
  
  // Check for instrument labels (multi-instrument indicator)
  const hasInstrumentLabels = checkForLabels(data, ['Instrument', 'Bond', 'T-Bill', 'Money Market', 'Treasury Bill'])
  
  // Check if we can find all required fields for a single instrument
  const requiredFields = getRequiredFieldMappings(instrumentType)
  const detectedFields = detectFieldsInData(data, requiredFields)
  const allFieldsFound = requiredFields.every(field => detectedFields[field])
  const fieldsFoundCount = requiredFields.filter(field => detectedFields[field]).length
  const fieldMatchRatio = fieldsFoundCount / requiredFields.length

  // 🔥 Enhanced single-instrument detection
  // If it's key-value style and we found most fields, it's likely single instrument
  if (isKeyValueStyle && fieldMatchRatio >= 0.6) {
    return { type: 'single', data, confidence: 0.9 }
  }
  
  // If all fields found and data is small, it's single instrument
  if (allFieldsFound && rowCount <= 5) {
    return { type: 'single', data, confidence: 0.85 }
  }
  
  // If it has repeated headers or many rows with similar structure, it's multi-instrument
  if (hasRepeatedHeaders) {
    return { type: 'multi', data, confidence: 0.9 }
  }
  
  if (hasBlankSeparators && rowCount > 5) {
    return { type: 'multi', data, confidence: 0.85 }
  }
  
  if (hasInstrumentLabels && rowCount > 3) {
    return { type: 'multi', data, confidence: 0.8 }
  }
  
  // If we found all fields but there are more than 3 rows, check if rows are similar
  if (allFieldsFound && rowCount > 3) {
    const rows = data.map(row => JSON.stringify(row))
    const uniqueRows = new Set(rows)
    // If many rows have the same structure (same columns), it's multi-instrument
    if (uniqueRows.size > 1 && uniqueRows.size < rowCount * 0.8) {
      return { type: 'multi', data, confidence: 0.7 }
    }
    return { type: 'single', data, confidence: 0.75 }
  }
  
  // Default heuristic: small dataset with many columns -> single
  if (rowCount <= 3 && colCount >= 3) {
    return { type: 'single', data, confidence: 0.6 }
  }
  
  // Default to multi-instrument for larger datasets
  if (rowCount > 10) {
    return { type: 'multi', data, confidence: 0.7 }
  }
  
  return { type: 'multi', data, confidence: 0.6 }
}

/**
 * Check for repeated headers (indicates multi-instrument)
 */
function checkForRepeatedHeaders(data) {
  if (!data || data.length < 2) return false
  
  const firstRowKeys = Object.keys(data[0]).map(k => k.toLowerCase())
  let repeatCount = 0
  let totalChecks = 0
  
  for (let i = 1; i < Math.min(data.length, 15); i++) {
    const currentKeys = Object.keys(data[i]).map(k => k.toLowerCase())
    // Skip empty rows
    if (currentKeys.length === 0) continue
    
    const matchCount = firstRowKeys.filter(key => currentKeys.includes(key)).length
    const matchRatio = firstRowKeys.length > 0 ? matchCount / firstRowKeys.length : 0
    
    totalChecks++
    if (matchRatio > 0.5) {
      repeatCount++
    }
  }
  
  // If more than 40% of rows have similar headers, it's multi-instrument
  return totalChecks > 0 && repeatCount / totalChecks > 0.4
}

/**
 * Check for blank rows (indicates multi-instrument)
 */
function checkForBlankRows(data) {
  let blankCount = 0
  for (const row of data) {
    const values = Object.values(row)
    const isEmpty = values.every(val => val === '' || val === null || val === undefined)
    if (isEmpty) blankCount++
  }
  return blankCount >= 2
}

/**
 * Check for instrument labels
 */
function checkForLabels(data, labels) {
  const lowerLabels = labels.map(l => l.toLowerCase())
  let labelCount = 0
  
  for (const row of data) {
    const values = Object.values(row)
    for (const val of values) {
      if (val && typeof val === 'string') {
        const lowerVal = val.toLowerCase()
        if (lowerLabels.some(label => lowerVal.includes(label))) {
          labelCount++
        }
      }
    }
  }
  
  return labelCount >= 2
}

/**
 * Detect which required fields are present in the data
 */
function detectFieldsInData(data, requiredFields) {
  const result = {}
  const allKeys = new Set()
  
  for (const row of data) {
    for (const key of Object.keys(row)) {
      allKeys.add(key.toLowerCase())
    }
  }
  
  for (const field of requiredFields) {
    const fieldLower = field.toLowerCase()
    result[field] = Array.from(allKeys).some(key => 
      key.includes(fieldLower) || fieldLower.includes(key)
    )
  }
  
  return result
}

/**
 * Get required field mappings for an instrument type
 */
export function getRequiredFieldMappings(instrumentType) {
  const mappings = {
    'money-market': ['principal', 'interestRate', 'daysToMaturity', 'issueDate', 'maturityDate', 'instrumentName'],
    'bonds': ['faceValue', 'couponRate', 'yield', 'maturityDate', 'issueDate', 'frequency', 'instrumentName'],
    'tbills': ['faceValue', 'discountRate', 'daysToMaturity', 'auctionDate', 'maturityDate', 'instrumentName']
  }
  
  return mappings[instrumentType] || mappings['money-market']
}

/**
 * 🔥 FIXED: Extract single instrument values with intelligent detection
 */
export function extractSingleInstrumentValues(data, requiredFields) {
  if (!data || !data.length) return {}
  
  const values = {}
  const allRows = data
  
  // 🔥 First pass: Look for key-value pairs (row has exactly one non-empty value)
  for (const row of allRows) {
    const entries = Object.entries(row)
    const nonEmpty = entries.filter(([key, val]) => 
      val !== '' && val !== null && val !== undefined
    )
    
    // If row has exactly one non-empty value, it might be a value cell
    // Look at the key to determine what it is
    for (const [key, val] of entries) {
      if (val === '' || val === null || val === undefined) continue
      const lowerKey = key.toLowerCase()
      
      for (const field of requiredFields) {
        const fieldLower = field.toLowerCase()
        // Check if key matches field name
        if (lowerKey.includes(fieldLower) || fieldLower.includes(lowerKey)) {
          if (!values[field]) {
            values[field] = val
          }
        }
      }
    }
  }
  
  // 🔥 Second pass: Look for values in cells with labels
  for (const row of allRows) {
    for (const [key, value] of Object.entries(row)) {
      if (value === '' || value === null || value === undefined) continue
      const lowerKey = key.toLowerCase()
      
      for (const field of requiredFields) {
        const fieldLower = field.toLowerCase()
        const synonyms = getSynonyms(field)
        const matches = synonyms.some(syn => 
          lowerKey.includes(syn.toLowerCase()) || syn.toLowerCase().includes(lowerKey)
        )
        if (matches && !values[field]) {
          values[field] = value
        }
      }
    }
  }
  
  // 🔥 Third pass: Look for values in adjacent cells
  // If we have a label row and a value row, try to match them
  for (let i = 0; i < allRows.length - 1; i++) {
    const currentRow = allRows[i]
    const nextRow = allRows[i + 1]
    
    for (const [key, label] of Object.entries(currentRow)) {
      if (!label || typeof label !== 'string') continue
      const lowerLabel = label.toLowerCase()
      
      // Check if this label matches any required field
      for (const field of requiredFields) {
        const fieldLower = field.toLowerCase()
        const synonyms = getSynonyms(field)
        const matches = synonyms.some(syn => 
          lowerLabel.includes(syn.toLowerCase()) || syn.toLowerCase().includes(lowerLabel)
        )
        if (matches && !values[field]) {
          // The value is in the same column of the next row
          const val = nextRow[key]
          if (val !== '' && val !== null && val !== undefined) {
            values[field] = val
          }
        }
      }
    }
  }
  
  // 🔥 Fourth pass: Look for numeric values that might be amounts/rates
  const numericFields = ['principal', 'faceValue', 'amount', 'rate', 'yield', 'discountRate', 'couponRate']
  for (const row of allRows) {
    for (const [key, value] of Object.entries(row)) {
      if (value === '' || value === null || value === undefined) continue
      const lowerKey = key.toLowerCase()
      
      // Check if it's a numeric value
      const isNumeric = typeof value === 'number' || 
                        (typeof value === 'string' && /^[\d\,\.\-\$]+$/.test(value.trim()))
      
      if (isNumeric) {
        for (const field of numericFields) {
          const synonyms = getSynonyms(field)
          const matches = synonyms.some(syn => 
            lowerKey.includes(syn.toLowerCase()) || syn.toLowerCase().includes(lowerKey)
          )
          if (matches && !values[field]) {
            values[field] = value
          }
        }
      }
    }
  }
  
  // 🔥 Special handling: look for instrument name if missing
  if (!values.instrumentName || values.instrumentName === '') {
    const nameCol = detectInstrumentNameColumn(data)
    if (nameCol && nameCol.columnName) {
      const names = extractInstrumentNames(data, nameCol.columnName)
      if (names && names.length > 0) {
        values.instrumentName = names[0]
      }
    }
  }
  
  return values
}

/**
 * Get synonyms for a field
 */
function getSynonyms(field) {
  const synonymMap = {
    'principal': ['principal', 'amount', 'face value', 'nominal', 'notional', 'investment', 'capital', 'value'],
    'interestRate': ['interest rate', 'rate', 'coupon', 'coupon rate', 'yield', 'return', 'apr', 'annual rate', 'interest'],
    'daysToMaturity': ['days to maturity', 'term', 'tenor', 'maturity days', 'duration days', 'period', 'days'],
    'issueDate': ['issue date', 'start date', 'effective date', 'trade date', 'settlement date', 'value date', 'origination'],
    'maturityDate': ['maturity date', 'end date', 'due date', 'redemption date', 'expiry date', 'maturity'],
    'faceValue': ['face value', 'par value', 'nominal', 'amount', 'principal', 'value'],
    'couponRate': ['coupon rate', 'coupon', 'rate', 'interest rate', 'coupon'],
    'yield': ['yield', 'ytm', 'yield to maturity', 'return', 'effective yield'],
    'discountRate': ['discount rate', 'discount', 'rate', 'bank discount', 'discount'],
    'frequency': ['frequency', 'payment frequency', 'coupon frequency', 'period', 'semi-annual', 'quarterly', 'annual'],
    'auctionDate': ['auction date', 'issue date', 'start date', 'trade date', 'auction'],
    'instrumentName': ['instrument', 'security', 'name', 'description', 'issuer', 'counterparty', 'company', 'entity', 'bond name', 'tbill name', 'title']
  }
  
  return synonymMap[field] || [field]
}

/**
 * 🔥 FIXED: Detect instrument name column
 */
export function detectInstrumentNameColumn(data) {
  if (!data || !data.length) return { columnName: null, confidence: 0 }
  
  const headers = Object.keys(data[0] || {})
  const namePatterns = ['instrument', 'name', 'security', 'bond', 'tbill', 'issuer', 'counterparty', 'company', 'entity', 'description', 'asset', 'title', 'label', 'id']
  
  let bestMatch = null
  let bestScore = 0
  
  for (const header of headers) {
    const lowerHeader = header.toLowerCase()
    let score = 0
    
    // Check for exact matches first
    for (const pattern of namePatterns) {
      if (lowerHeader === pattern) score += 3
      else if (lowerHeader.includes(pattern)) score += 2
      else if (pattern.includes(lowerHeader) && pattern.length > 3) score += 1
    }
    
    // Check if values in this column look like names (text, not numbers)
    const sampleValues = data.slice(0, 10).map(row => row[header]).filter(v => v && v !== '')
    if (sampleValues.length > 0) {
      const nameLike = sampleValues.filter(v => {
        if (typeof v !== 'string') return false
        // Check if it looks like a name (letters, spaces, not purely numeric)
        const cleaned = v.trim()
        return cleaned.length > 1 && 
               !/^[\d\.\,\-\$]+$/.test(cleaned) &&
               /[a-zA-Z]/.test(cleaned)
      }).length
      score += (nameLike / Math.max(sampleValues.length, 1)) * 3
    }
    
    // Boost score if the column contains unique values (likely identifiers)
    const uniqueValues = new Set(sampleValues)
    const uniqueness = sampleValues.length > 0 ? uniqueValues.size / sampleValues.length : 0
    score += uniqueness * 1.5
    
    if (score > bestScore) {
      bestScore = score
      bestMatch = header
    }
  }
  
  return {
    columnName: bestMatch,
    confidence: Math.min(bestScore / 8, 1)
  }
}

/**
 * Extract instrument names from a column
 */
export function extractInstrumentNames(data, columnName) {
  if (!data || !data.length || !columnName) return []
  
  const names = new Set()
  for (const row of data) {
    const value = row[columnName]
    if (value && typeof value === 'string' && value.trim()) {
      // Clean up common prefixes/suffixes
      let cleaned = value.trim()
      // Remove common prefixes like "Instrument: " or "Name: "
      cleaned = cleaned.replace(/^(Instrument|Name|Security|Bond|TBill|Asset|ID)\s*[:]\s*/i, '')
      if (cleaned) {
        names.add(cleaned)
      }
    }
  }
  
  return Array.from(names)
}

/**
 * Check if a value looks like a number
 */
export function looksLikeNumber(value) {
  if (typeof value === 'number') return true
  if (typeof value !== 'string') return false
  return /^[\d\,\.\-\$]+$/.test(value.trim())
}

/**
 * Parse number from various formats
 */
export function parseNumberValue(value) {
  if (typeof value === 'number') return value
  if (typeof value !== 'string') return NaN
  
  let cleaned = value.replace(/[$,]/g, '').trim()
  return parseFloat(cleaned)
}

/**
 * Check if a value looks like a date
 */
export function looksLikeDate(value) {
  if (value instanceof Date) return true
  if (typeof value !== 'string') return false
  return /^\d{4}-\d{2}-\d{2}/.test(value) || 
         /^\d{2}\/\d{2}\/\d{4}/.test(value) ||
         /^\d{2}-\d{2}-\d{4}/.test(value) ||
         /^\d{1,2}\s+[A-Za-z]+\s+\d{4}/.test(value)
}

/**
 * Parse date from various formats
 */
export function parseDateValue(value) {
  if (value instanceof Date) return value.toISOString().split('T')[0]
  if (typeof value !== 'string') return value
  
  // Try ISO format
  if (/^\d{4}-\d{2}-\d{2}/.test(value)) return value.substring(0, 10)
  
  // Try MM/DD/YYYY
  if (/^\d{2}\/\d{2}\/\d{4}/.test(value)) {
    const parts = value.split('/')
    return `${parts[2]}-${parts[0].padStart(2, '0')}-${parts[1].padStart(2, '0')}`
  }
  
  // Try DD/MM/YYYY
  if (/^\d{2}-\d{2}-\d{4}/.test(value)) {
    const parts = value.split('-')
    return `${parts[2]}-${parts[1].padStart(2, '0')}-${parts[0].padStart(2, '0')}`
  }
  
  // Try "DD Mon YYYY" format
  const monthMap = {
    'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04', 'may': '05', 'jun': '06',
    'jul': '07', 'aug': '08', 'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12'
  }
  const match = value.match(/^(\d{1,2})\s+([A-Za-z]{3})\s+(\d{4})/)
  if (match) {
    const month = monthMap[match[2].toLowerCase()]
    if (month) {
      return `${match[3]}-${month}-${match[1].padStart(2, '0')}`
    }
  }
  
  return value
}

/**
 * 🔥 NEW: Clean a value for display
 */
export function cleanValue(value) {
  if (value === null || value === undefined || value === '') return ''
  if (typeof value === 'string') return value.trim()
  return value
}

/**
 * 🔥 NEW: Get a confidence score for a single-instrument detection
 */
export function getSingleInstrumentConfidence(data, instrumentType) {
  const detection = detectSheetType(data, instrumentType)
  return detection.confidence || 0
}