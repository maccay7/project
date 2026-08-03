function normalizeText(value) {
  if (value === null || value === undefined) return ''
  if (typeof value === 'number') return String(value)
  return String(value).toLowerCase().trim().replace(/[_\-+/()]/g, ' ')
}

function cleanText(value) {
  if (value === null || value === undefined) return ''
  if (typeof value === 'number') return String(value)
  return String(value).trim()
}

function isMeaningfulText(value) {
  if (value === null || value === undefined) return false
  const text = cleanText(value)
  return text.length > 0 && text !== 'null' && text !== 'undefined'
}

function looksLikeDate(value) {
  if (value instanceof Date) return true
  if (typeof value !== 'string') return false
  const text = value.trim()
  return /^\d{4}-\d{2}-\d{2}/.test(text) ||
    /^\d{2}\/\d{2}\/\d{4}/.test(text) ||
    /^\d{2}-\d{2}-\d{4}/.test(text) ||
    /^\d{1,2}\s+[A-Za-z]{3}\s+\d{4}/.test(text)
}

function looksLikeNumber(value) {
  if (typeof value === 'number') return !Number.isNaN(value)
  if (typeof value !== 'string') return false
  const text = value.trim()
  return /^[\d,\.\-\$%]+$/.test(text)
}

function parseNumberValue(value) {
  if (typeof value === 'number') return value
  if (typeof value !== 'string') return NaN
  const cleaned = value.replace(/[$,]/g, '').replace(/%$/, '').trim()
  const parsed = parseFloat(cleaned)
  return Number.isNaN(parsed) ? NaN : parsed
}

function isCandidateValue(value) {
  if (value === null || value === undefined || value === '') return false
  return looksLikeNumber(value) || looksLikeDate(value) || (typeof value === 'string' && value.trim().length > 0)
}

function getSynonyms(field) {
  const synonymMap = {
    principal: ['principal', 'face value', 'par value', 'nominal value', 'nominal', 'amount', 'notional', 'investment amount', 'capital', 'deposit amount', 'initial investment', 'starting balance', 'principal amount', 'face amount', 'par amount', 'original amount'],
    interestRate: ['interest rate', 'rate', 'coupon', 'coupon rate', 'yield', 'return', 'apr', 'annual rate', 'interest', 'annual interest rate', 'nominal rate', 'stated rate', 'effective rate', 'annual percentage rate'],
    daysToMaturity: ['days to maturity', 'term', 'tenor', 'maturity days', 'duration days', 'period', 'days', 'contract days', 'term days', 'time to maturity', 'remaining days', 'days remaining'],
    issueDate: ['issue date', 'start date', 'effective date', 'trade date', 'settlement date', 'value date', 'origination date', 'inception date', 'commencement date', 'entry date'],
    maturityDate: ['maturity date', 'end date', 'due date', 'redemption date', 'expiry date', 'maturity', 'expiration date', 'termination date', 'final maturity date'],
    purchasePrice: ['purchase price', 'buy price', 'acquisition price', 'entry price', 'cost', 'price paid', 'investment cost', 'buying price'],
    settlementAmount: ['settlement amount', 'settlement value', 'cash flow', 'proceeds', 'payment amount', 'settlement proceeds'],
    faceValue: ['face value', 'par value', 'redemption value', 'maturity value', 'amount', 'principal', 'nominal', 'face amount', 'par amount', 'nominal value', 'principal amount'],
    discountRate: ['discount rate', 'bank discount', 'discount yield', 'rate', 't bill rate', 't-bill rate', 'auction rate', 'discount', 'bank discount rate', 'treasury discount rate'],
    auctionDate: ['auction date', 'issue date', 'start date', 'settlement date', 'trade date', 'offering date', 'issuance date'],
    couponRate: ['coupon rate', 'coupon', 'rate', 'interest rate', 'nominal rate', 'stated rate', 'annual coupon', 'fixed rate', 'coupon interest rate', 'annual interest rate'],
    couponFrequency: ['coupon frequency', 'frequency', 'payment frequency', 'period', 'semi annual', 'semi-annual', 'quarterly', 'annual', 'coupon period', 'payment period', 'interest payment frequency'],
    price: ['price', 'market price', 'clean price', 'dirty price', 'current price', 'flat price', 'quoted price', 'trading price', 'bond price'],
    yield: ['yield', 'yield to maturity', 'ytm', 'required return', 'market yield', 'effective yield', 'redemption yield', 'current yield', 'yield to call', 'discount yield'],
    callDate: ['call date', 'first call date', 'callable date', 'early redemption date', 'call provision date'],
    callPrice: ['call price', 'call premium', 'redemption price', 'sinking fund price', 'call value'],
    putDate: ['put date', 'puttable date', 'putable date', 'put provision date'],
    putPrice: ['put price', 'put premium', 'put value'],
    instrumentName: ['instrument', 'security', 'name', 'description', 'issuer', 'counterparty', 'company', 'entity', 'bond name', 'tbill name', 'title', 'asset name', 'security name', 'issue name'],
    currency: ['currency', 'ccy', 'curr', 'denomination', 'denom', 'currency code'],
    country: ['country', 'nation', 'jurisdiction', 'region', 'market', 'country of issue', 'issuing country'],
    settlementDate: ['settlement date', 'trade date', 'value date', 'delivery date', 'effective settlement date']
  }
  return synonymMap[field] || [field]
}

function buildScanContext(data, context = {}) {
  const cells = []
  let rows = []

  if (context.rows && Array.isArray(context.rows) && context.rows.length > 0) {
    const rowItems = context.rows.map((row, rowIndex) => {
      if (Array.isArray(row)) {
        return row.map((value, colIndex) => ({
          rowIndex,
          colIndex,
          value,
          label: '',
          text: cleanText(value)
        }))
      }
      if (row && typeof row === 'object') {
        return Object.entries(row).map(([label, value], colIndex) => ({
          rowIndex,
          colIndex,
          value,
          label,
          text: cleanText(value)
        }))
      }
      return []
    })
    rows = rowItems
    rowItems.forEach((rowCells, rowIndex) => {
      rowCells.forEach(cell => {
        cells.push({ ...cell, rowIndex })
      })
    })
    return { rows, cells, rowCount: rows.length, colCount: rows[0]?.length || 0 }
  }

  if (Array.isArray(data) && data.length > 0) {
    if (Array.isArray(data[0])) {
      rows = data.map((row, rowIndex) => row.map((value, colIndex) => ({ rowIndex, colIndex, value, label: '', text: cleanText(value) })))
    } else if (data[0] && typeof data[0] === 'object') {
      rows = data.map((row, rowIndex) => Object.entries(row).map(([label, value], colIndex) => ({ rowIndex, colIndex, value, label, text: cleanText(value) })))
    }
  }

  rows.forEach((rowCells) => {
    rowCells.forEach((cell) => cells.push(cell))
  })

  return { rows, cells, rowCount: rows.length, colCount: rows[0]?.length || 0 }
}

function getCellAt(scanContext, rowIndex, colIndex) {
  const row = scanContext.rows[rowIndex]
  if (!row) return null
  return row[colIndex] || null
}

function textMatches(text, synonyms) {
  const normalizedText = normalizeText(text)
  if (!normalizedText) return false
  return synonyms.some((synonym) => {
    const normalizedSynonym = normalizeText(synonym)
    return normalizedText === normalizedSynonym || normalizedText.includes(normalizedSynonym) || normalizedSynonym.includes(normalizedText)
  })
}

function extractValueFromCell(cell) {
  const value = cell?.value
  if (value === null || value === undefined || value === '') return null
  if (looksLikeNumber(value)) return parseNumberValue(value)
  if (looksLikeDate(value)) return cleanText(value)
  return cleanText(value)
}

function findFieldValue(scanContext, field, context = {}) {
  const synonyms = getSynonyms(field)
  const candidateCells = []

  for (const cell of scanContext.cells) {
    const labelText = cell.label ? cleanText(cell.label) : ''
    const valueText = cleanText(cell.value)
    if (textMatches(labelText, synonyms) || textMatches(valueText, synonyms)) {
      candidateCells.push(cell)
    }
  }

  const prioritized = []
  for (const cell of candidateCells) {
    const labelText = cell.label ? cleanText(cell.label) : ''
    const valueText = cleanText(cell.value)
    const directValue = extractValueFromCell(cell)

    if (directValue !== null && (field === 'instrumentName' ? typeof directValue === 'string' : true)) {
      prioritized.push({ value: directValue, cell, reason: 'direct-match' })
    }

    const neighbors = [
      getCellAt(scanContext, cell.rowIndex, cell.colIndex + 1),
      getCellAt(scanContext, cell.rowIndex + 1, cell.colIndex),
      getCellAt(scanContext, cell.rowIndex, cell.colIndex - 1),
      getCellAt(scanContext, cell.rowIndex - 1, cell.colIndex),
      getCellAt(scanContext, cell.rowIndex + 1, cell.colIndex + 1),
      getCellAt(scanContext, cell.rowIndex - 1, cell.colIndex + 1)
    ].filter(Boolean)

    for (const neighbor of neighbors) {
      const neighborValue = extractValueFromCell(neighbor)
      if (neighborValue !== null && (field === 'instrumentName' ? typeof neighborValue === 'string' : true)) {
        const label = labelText || neighbor.label || ''
        if (label && !textMatches(label, ['total', 'subtotal', 'grand total', 'notes'])) {
          prioritized.push({ value: neighborValue, cell: neighbor, reason: 'adjacent-match' })
        }
      }
    }
  }

  if (!prioritized.length) {
    return null
  }

  const preferred = prioritized.find((item) => item.reason === 'adjacent-match') || prioritized[0]
  return {
    value: preferred.value,
    source: preferred.cell,
    matchedBy: preferred.reason
  }
}

function detectInstrumentNameColumn(data) {
  if (!data || !data.length) return { columnName: null, confidence: 0 }
  const headers = Object.keys(data[0] || {})
  const namePatterns = ['instrument', 'name', 'security', 'bond', 'tbill', 'issuer', 'counterparty', 'company', 'entity', 'description', 'asset', 'title']
  let bestMatch = null
  let bestScore = 0

  for (const header of headers) {
    const lowerHeader = header.toLowerCase()
    let score = 0
    for (const pattern of namePatterns) {
      if (lowerHeader === pattern) score += 3
      else if (lowerHeader.includes(pattern)) score += 2
      else if (pattern.includes(lowerHeader) && pattern.length > 3) score += 1
    }

    const sampleValues = data.slice(0, 10).map((row) => row[header]).filter((value) => value && value !== '')
    if (sampleValues.length > 0) {
      const nameLike = sampleValues.filter((value) => {
        if (typeof value !== 'string') return false
        const cleaned = value.trim()
        return cleaned.length > 1 && !/^[\d\.\,\-\$]+$/.test(cleaned) && /[a-zA-Z]/.test(cleaned)
      }).length
      score += (nameLike / Math.max(sampleValues.length, 1)) * 3
    }

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

function extractInstrumentNames(data, columnName) {
  if (!data || !data.length || !columnName) return []
  const names = new Set()
  for (const row of data) {
    const value = row[columnName]
    if (value && typeof value === 'string' && value.trim()) {
      const cleaned = value.trim().replace(/^(Instrument|Name|Security|Bond|TBill|Asset|ID)\s*[:]\s*/i, '')
      if (cleaned) names.add(cleaned)
    }
  }
  return Array.from(names)
}

function detectFieldsInData(data, requiredFields, context = {}) {
  const scanContext = buildScanContext(data, context)
  const result = {}
  for (const field of requiredFields) {
    const found = findFieldValue(scanContext, field, context)
    result[field] = Boolean(found?.value !== undefined && found?.value !== null && found?.value !== '')
  }
  return result
}

export function detectSheetType(data, instrumentType = 'money-market', context = {}) {
  if (!data || !data.length) {
    return { type: 'single', data: [], confidence: 0 }
  }

  const scanContext = buildScanContext(data, context)
  const requiredFields = getRequiredFieldMappings(instrumentType)
  const detectedFields = detectFieldsInData(data, requiredFields, context)
  const fieldsFoundCount = requiredFields.filter((field) => detectedFields[field]).length
  const fieldMatchRatio = requiredFields.length > 0 ? fieldsFoundCount / requiredFields.length : 0
  const hasLabelValuePattern = scanContext.cells.some((cell, index) => {
    const nextCell = scanContext.cells[index + 1]
    if (!nextCell) return false
    const currentLabel = normalizeText(cell.label || cell.value)
    const nextValue = extractValueFromCell(nextCell)
    return currentLabel && nextValue !== null && currentLabel.length > 1 && currentLabel.length < 80
  })

  const strongSingleSignals = fieldsFoundCount >= 2 && (fieldMatchRatio >= 0.33 || hasLabelValuePattern)
  const veryStrongSingleSignals = fieldsFoundCount >= 3 && fieldMatchRatio >= 0.5
  const repeatedHeaders = checkForRepeatedHeaders(data)
  const hasBlankSeparators = checkForBlankRows(data)
  const hasInstrumentLabels = checkForLabels(data, ['Instrument', 'Bond', 'T-Bill', 'Money Market', 'Treasury Bill'])

  if (veryStrongSingleSignals || strongSingleSignals) {
    return { type: 'single', data, confidence: 0.95 }
  }
  if (scanContext.rowCount <= 6 && (fieldMatchRatio >= 0.2 || hasLabelValuePattern)) {
    return { type: 'single', data, confidence: 0.85 }
  }
  if (repeatedHeaders) {
    return { type: 'multi', data, confidence: 0.9 }
  }
  if (hasBlankSeparators && scanContext.rowCount > 5) {
    return { type: 'multi', data, confidence: 0.85 }
  }
  if (hasInstrumentLabels && scanContext.rowCount > 3) {
    return { type: 'multi', data, confidence: 0.8 }
  }
  if (scanContext.rowCount > 10) {
    return { type: 'multi', data, confidence: 0.7 }
  }
  return { type: 'single', data, confidence: 0.65 }
}

function checkForRepeatedHeaders(data) {
  if (!data || data.length < 2) return false
  const firstRowKeys = Object.keys(data[0] || {}).map((key) => key.toLowerCase())
  let repeatCount = 0
  let totalChecks = 0
  for (let i = 1; i < Math.min(data.length, 15); i++) {
    const currentKeys = Object.keys(data[i] || {}).map((key) => key.toLowerCase())
    if (currentKeys.length === 0) continue
    const matchCount = firstRowKeys.filter((key) => currentKeys.includes(key)).length
    const matchRatio = firstRowKeys.length > 0 ? matchCount / firstRowKeys.length : 0
    totalChecks++
    if (matchRatio > 0.5) repeatCount++
  }
  return totalChecks > 0 && repeatCount / totalChecks > 0.4
}

function checkForBlankRows(data) {
  let blankCount = 0
  for (const row of data) {
    const values = Object.values(row || {})
    const isEmpty = values.every((value) => value === '' || value === null || value === undefined)
    if (isEmpty) blankCount++
  }
  return blankCount >= 2
}

function checkForLabels(data, labels) {
  const lowerLabels = labels.map((label) => label.toLowerCase())
  let labelCount = 0
  for (const row of data) {
    const values = Object.values(row || {})
    for (const value of values) {
      if (value && typeof value === 'string') {
        const lowerValue = value.toLowerCase()
        if (lowerLabels.some((label) => lowerValue.includes(label))) {
          labelCount++
        }
      }
    }
  }
  return labelCount >= 2
}

export function getRequiredFieldMappings(instrumentType) {
  const mappings = {
    'money-market': ['principal', 'interestRate', 'daysToMaturity', 'issueDate', 'maturityDate', 'instrumentName'],
    'bonds': ['faceValue', 'couponRate', 'yield', 'maturityDate', 'issueDate', 'couponFrequency', 'instrumentName'],
    'tbills': ['faceValue', 'discountRate', 'daysToMaturity', 'auctionDate', 'maturityDate', 'instrumentName']
  }
  return mappings[instrumentType] || mappings['money-market']
}

export function extractSingleInstrumentValues(data, requiredFields, context = {}) {
  if (!data || !data.length) return {}

  const scanContext = buildScanContext(data, context)
  const values = {}
  const metadata = {}

  const fieldList = Array.isArray(requiredFields) ? requiredFields : getRequiredFieldMappings('money-market')
  for (const field of fieldList) {
    const found = findFieldValue(scanContext, field, context)
    if (found?.value !== undefined && found?.value !== null && found?.value !== '') {
      values[field] = found.value
      metadata[field] = {
        field,
        value: found.value,
        sourceLocation: found.source ? { row: found.source.rowIndex + 1, column: found.source.colIndex + 1 } : null,
        sourceLabel: found.source?.label || '',
        matchedBy: found.matchedBy || 'label-match'
      }
    }
  }

  if (!values.instrumentName || values.instrumentName === '') {
    const nameDetection = detectInstrumentNameColumn(data)
    if (nameDetection?.columnName) {
      const names = extractInstrumentNames(data, nameDetection.columnName)
      if (names && names.length > 0) {
        values.instrumentName = names[0]
        metadata.instrumentName = {
          field: 'instrumentName',
          value: values.instrumentName,
          sourceLocation: { row: 1, column: 1 },
          sourceLabel: nameDetection.columnName,
          matchedBy: 'instrument-name-column'
        }
      }
    }
  }

  return { values, metadata }
}

export function isLikelyNumber(value) {
  return looksLikeNumber(value)
}

export function parseNumberValue(value) {
  return parseNumberValueInternal(value)
}

export function isLikelyDate(value) {
  return looksLikeDate(value)
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
    jan: '01', feb: '02', mar: '03', apr: '04', may: '05', jun: '06', jul: '07', aug: '08', sep: '09', oct: '10', nov: '11', dec: '12'
  }
  const match = value.match(/^(\d{1,2})\s+([A-Za-z]{3})\s+(\d{4})/)
  if (match) {
    const month = monthMap[match[2].toLowerCase()]
    if (month) return `${match[3]}-${month}-${match[1].padStart(2, '0')}`
  }
  return value
}

export function cleanValue(value) {
  return cleanText(value)
}

export function getSingleInstrumentConfidence(data, instrumentType) {
  const detection = detectSheetType(data, instrumentType)
  return detection.confidence || 0
}
