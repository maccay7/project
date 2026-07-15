export function detectSheetType(data, instrumentType = 'money-market') {
  if (!data || !data.length) {
    return { type: 'single', data: [], confidence: 0 }
  }

  const rowCount = data.length
  const firstRow = data[0] || {}
  const colCount = Object.keys(firstRow).length
  const allKeys = new Set()
  for (const row of data) {
    for (const key of Object.keys(row)) {
      allKeys.add(key.toLowerCase())
    }
  }
  const uniqueKeyCount = allKeys.size

  const isKeyValueStyle = rowCount <= 5 && colCount >= 3 && uniqueKeyCount >= 3
  const hasRepeatedHeaders = checkForRepeatedHeaders(data)
  const hasBlankSeparators = checkForBlankRows(data)
  const hasInstrumentLabels = checkForLabels(data, ['Instrument', 'Bond', 'T-Bill', 'Money Market', 'Treasury Bill'])
  
  const requiredFields = getRequiredFieldMappings(instrumentType)
  const detectedFields = detectFieldsInData(data, requiredFields)
  const allFieldsFound = requiredFields.every(field => detectedFields[field])
  const fieldsFoundCount = requiredFields.filter(field => detectedFields[field]).length
  const fieldMatchRatio = fieldsFoundCount / requiredFields.length

  if (isKeyValueStyle && fieldMatchRatio >= 0.6) {
    return { type: 'single', data, confidence: 0.9 }
  }
  if (allFieldsFound && rowCount <= 5) {
    return { type: 'single', data, confidence: 0.85 }
  }
  if (hasRepeatedHeaders) {
    return { type: 'multi', data, confidence: 0.9 }
  }
  if (hasBlankSeparators && rowCount > 5) {
    return { type: 'multi', data, confidence: 0.85 }
  }
  if (hasInstrumentLabels && rowCount > 3) {
    return { type: 'multi', data, confidence: 0.8 }
  }
  if (allFieldsFound && rowCount > 3) {
    const rows = data.map(row => JSON.stringify(row))
    const uniqueRows = new Set(rows)
    if (uniqueRows.size > 1 && uniqueRows.size < rowCount * 0.8) {
      return { type: 'multi', data, confidence: 0.7 }
    }
    return { type: 'single', data, confidence: 0.75 }
  }
  if (rowCount <= 3 && colCount >= 3) {
    return { type: 'single', data, confidence: 0.6 }
  }
  if (rowCount > 10) {
    return { type: 'multi', data, confidence: 0.7 }
  }
  return { type: 'multi', data, confidence: 0.6 }
}

function checkForRepeatedHeaders(data) {
  if (!data || data.length < 2) return false
  const firstRowKeys = Object.keys(data[0]).map(k => k.toLowerCase())
  let repeatCount = 0, totalChecks = 0
  for (let i = 1; i < Math.min(data.length, 15); i++) {
    const currentKeys = Object.keys(data[i]).map(k => k.toLowerCase())
    if (currentKeys.length === 0) continue
    const matchCount = firstRowKeys.filter(key => currentKeys.includes(key)).length
    const matchRatio = firstRowKeys.length > 0 ? matchCount / firstRowKeys.length : 0
    totalChecks++
    if (matchRatio > 0.5) repeatCount++
  }
  return totalChecks > 0 && repeatCount / totalChecks > 0.4
}

function checkForBlankRows(data) {
  let blankCount = 0
  for (const row of data) {
    const values = Object.values(row)
    const isEmpty = values.every(val => val === '' || val === null || val === undefined)
    if (isEmpty) blankCount++
  }
  return blankCount >= 2
}

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

export function getRequiredFieldMappings(instrumentType) {
  const mappings = {
    'money-market': ['principal', 'interestRate', 'daysToMaturity', 'issueDate', 'maturityDate', 'instrumentName'],
    'bonds': ['faceValue', 'couponRate', 'yield', 'maturityDate', 'issueDate', 'frequency', 'instrumentName'],
    'tbills': ['faceValue', 'discountRate', 'daysToMaturity', 'auctionDate', 'maturityDate', 'instrumentName']
  }
  return mappings[instrumentType] || mappings['money-market']
}

export function extractSingleInstrumentValues(data, requiredFields) {
  if (!data || !data.length) return {}
  const values = {}
  const allRows = data

  for (const row of allRows) {
    const entries = Object.entries(row)
    const nonEmpty = entries.filter(([key, val]) => 
      val !== '' && val !== null && val !== undefined
    )
    for (const [key, val] of entries) {
      if (val === '' || val === null || val === undefined) continue
      const lowerKey = key.toLowerCase()
      for (const field of requiredFields) {
        const fieldLower = field.toLowerCase()
        if (lowerKey.includes(fieldLower) || fieldLower.includes(lowerKey)) {
          if (!values[field]) {
            values[field] = val
          }
        }
      }
    }
  }

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

  for (let i = 0; i < allRows.length - 1; i++) {
    const currentRow = allRows[i]
    const nextRow = allRows[i + 1]
    for (const [key, label] of Object.entries(currentRow)) {
      if (!label || typeof label !== 'string') continue
      const lowerLabel = label.toLowerCase()
      for (const field of requiredFields) {
        const fieldLower = field.toLowerCase()
        const synonyms = getSynonyms(field)
        const matches = synonyms.some(syn => 
          lowerLabel.includes(syn.toLowerCase()) || syn.toLowerCase().includes(lowerLabel)
        )
        if (matches && !values[field]) {
          const val = nextRow[key]
          if (val !== '' && val !== null && val !== undefined) {
            values[field] = val
          }
        }
      }
    }
  }

  const numericFields = ['principal', 'faceValue', 'amount', 'rate', 'yield', 'discountRate', 'couponRate']
  for (const row of allRows) {
    for (const [key, value] of Object.entries(row)) {
      if (value === '' || value === null || value === undefined) continue
      const lowerKey = key.toLowerCase()
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

export function detectInstrumentNameColumn(data) {
  if (!data || !data.length) return { columnName: null, confidence: 0 }
  const headers = Object.keys(data[0] || {})
  const namePatterns = ['instrument', 'name', 'security', 'bond', 'tbill', 'issuer', 'counterparty', 'company', 'entity', 'description', 'asset', 'title', 'label', 'id']
  let bestMatch = null, bestScore = 0
  for (const header of headers) {
    const lowerHeader = header.toLowerCase()
    let score = 0
    for (const pattern of namePatterns) {
      if (lowerHeader === pattern) score += 3
      else if (lowerHeader.includes(pattern)) score += 2
      else if (pattern.includes(lowerHeader) && pattern.length > 3) score += 1
    }
    const sampleValues = data.slice(0, 10).map(row => row[header]).filter(v => v && v !== '')
    if (sampleValues.length > 0) {
      const nameLike = sampleValues.filter(v => {
        if (typeof v !== 'string') return false
        const cleaned = v.trim()
        return cleaned.length > 1 && 
               !/^[\d\.\,\-\$]+$/.test(cleaned) &&
               /[a-zA-Z]/.test(cleaned)
      }).length
      score += (nameLike / Math.max(sampleValues.length, 1)) * 3
    }
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

export function extractInstrumentNames(data, columnName) {
  if (!data || !data.length || !columnName) return []
  const names = new Set()
  for (const row of data) {
    const value = row[columnName]
    if (value && typeof value === 'string' && value.trim()) {
      let cleaned = value.trim()
      cleaned = cleaned.replace(/^(Instrument|Name|Security|Bond|TBill|Asset|ID)\s*[:]\s*/i, '')
      if (cleaned) {
        names.add(cleaned)
      }
    }
  }
  return Array.from(names)
}

export function looksLikeNumber(value) {
  if (typeof value === 'number') return true
  if (typeof value !== 'string') return false
  return /^[\d\,\.\-\$]+$/.test(value.trim())
}

export function parseNumberValue(value) {
  if (typeof value === 'number') return value
  if (typeof value !== 'string') return NaN
  let cleaned = value.replace(/[$,]/g, '').trim()
  return parseFloat(cleaned)
}

export function looksLikeDate(value) {
  if (value instanceof Date) return true
  if (typeof value !== 'string') return false
  return /^\d{4}-\d{2}-\d{2}/.test(value) || 
         /^\d{2}\/\d{2}\/\d{4}/.test(value) ||
         /^\d{2}-\d{2}-\d{4}/.test(value) ||
         /^\d{1,2}\s+[A-Za-z]+\s+\d{4}/.test(value)
}

export function parseDateValue(value) {
  if (value instanceof Date) return value.toISOString().split('T')[0]
  if (typeof value !== 'string') return value
  if (/^\d{4}-\d{2}-\d{2}/.test(value)) return value.substring(0, 10)
  if (/^\d{2}\/\d{2}\/\d{4}/.test(value)) {
    const parts = value.split('/')
    return `${parts[2]}-${parts[0].padStart(2, '0')}-${parts[1].padStart(2, '0')}`
  }
  if (/^\d{2}-\d{2}-\d{4}/.test(value)) {
    const parts = value.split('-')
    return `${parts[2]}-${parts[1].padStart(2, '0')}-${parts[0].padStart(2, '0')}`
  }
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

export function cleanValue(value) {
  if (value === null || value === undefined || value === '') return ''
  if (typeof value === 'string') return value.trim()
  return value
}

export function getSingleInstrumentConfidence(data, instrumentType) {
  const detection = detectSheetType(data, instrumentType)
  return detection.confidence || 0
}