import * as XLSX from 'xlsx'

function normalize(text) {
  if (!text) return ''
  return String(text).toLowerCase().replace(/[_\-:]+/g, ' ').replace(/\s+/g, ' ').trim()
}

function fieldHasWord(haystack, needle) {
  const h = normalize(haystack)
  const n = normalize(needle)
  if (!h || !n) return false
  return ` ${h} `.includes(` ${n} `)
}

export function getRequiredFieldMappings(instrumentType) {
  const mappings = {
    'money-market': ['principal', 'interestRate', 'daysToMaturity', 'issueDate', 'maturityDate', 'instrumentName'],
    'bonds': ['faceValue', 'couponRate', 'yield', 'maturityDate', 'issueDate', 'frequency', 'instrumentName'],
    'tbills': ['faceValue', 'discountRate', 'daysToMaturity', 'auctionDate', 'maturityDate', 'instrumentName'],
  }
  const key = normalize(instrumentType).replace(/\s+/g, '-')
  return mappings[key] || []
}

const SYNONYM_MAP = {
  'principal': ['principal', 'principle', 'amount invested', 'investment amount',
                'initial investment', 'initial amount', 'deposit amount',
                'starting balance', 'opening balance', 'capital',
                'total cost', 'purchase cost', 'cost'],
  'faceValue': ['balance', 'balance amount', 'principal balance',
                'outstanding balance', 'loan balance', 'current balance',
                'face balance', 'amount outstanding',
                'face value', 'par value', 'redemption value', 'maturity value',
                'nominal value', 'nominal amount', 'notional amount',
                'face amount', 'par amount'],
  'interestRate': ['interest rate', 'interestrate', 'annual rate',
                   'annual interest rate', 'nominal rate', 'stated rate',
                   'effective rate', 'apr', 'rate'],
  'discountRate': ['discount rate', 'bank discount', 'discount yield',
                   't-bill rate', 'auction rate', 'discount'],
  'couponRate': ['coupon rate', 'coupon', 'annual coupon', 'fixed rate',
                 'nominal rate', 'stated rate'],
  'yield': ['yield to maturity', 'ytm', 'market yield', 'required return',
            'redemption yield', 'yield'],
  'issueDate': ['issue date', 'start date', 'effective date',
                'settlement date', 'origination date', 'value date',
                'trade date'],
  'maturityDate': ['maturity date', 'end date', 'due date',
                   'redemption date', 'expiry date', 'termination date'],
  'valuationDate': ['valuation date', 'portfolio date', 'report date',
                    'as of date', 'date pfolio'],
  'daysToMaturity': ['days to maturity', 'maturity days', 'duration days',
                     'contract days', 'term days', 'term in days',
                     'tenor', 'term', 'days', 'period'],
  'frequency': ['coupon frequency', 'payment frequency', 'frequency',
                'coupon period', 'payments per year'],
  'auctionDate': ['auction date', 'issue date', 'settlement date'],
  'instrumentName': ['instrument name', 'bond name', 't-bill name',
                     'treasury bill name', 'security name', 'issuer',
                     'parent company name', 'parent company', 'company',
                     'entity', 'short name', 'description', 'name',
                     'counterparty'],
}

function getSynonyms(field) {
  if (SYNONYM_MAP[field]) return SYNONYM_MAP[field]
  const words = String(field || '')
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .toLowerCase()
    .split(/\s+/)
    .filter(Boolean)
  return words.length ? words : [field]
}

export function extractSingleInstrumentValues(data, requiredFields) {
  if (!data || !data.length) return {}
  const values = {}
  const flatMap = {}
  for (const row of data) {
    for (const [k, v] of Object.entries(row || {})) {
      if (v === '' || v === null || v === undefined) continue
      const normKey = normalize(k)
      if (!(normKey in flatMap)) flatMap[normKey] = v
    }
  }
  for (const field of requiredFields || []) {
    if (values[field]) continue
    const synonyms = getSynonyms(field)
    for (const syn of synonyms) {
      for (const [normKey, val] of Object.entries(flatMap)) {
        if (fieldHasWord(normKey, syn)) {
          const str = String(val).trim()
          if (/^[A-Z]{3}$/.test(str) && field !== 'instrumentName') continue
          if (/^\d+(\.\d+)?\s*%$/.test(str) && field !== 'discountRate' &&
              field !== 'couponRate' && field !== 'interestRate' && field !== 'yield') continue
          if (/^-?\d+(\.\d+)?$/.test(str) && field === 'instrumentName') continue
          values[field] = val
          break
        }
      }
      if (values[field]) break
    }
  }
  if (!values.instrumentName) {
    const nameCol = detectInstrumentNameColumn(data)
    if (nameCol && nameCol.columnName) {
      const names = extractInstrumentNames(data, nameCol.columnName)
      if (names.length > 0) values.instrumentName = names[0]
    }
  }
  return values
}

export function detectSheetType(data, instrumentType) {
  if (!data || !data.length) return { type: 'single', data: [], confidence: 0 }
  const rowCount = data.length
  const firstRow = data[0] || {}
  const colCount = Object.keys(firstRow).length
  const requiredFields = getRequiredFieldMappings(instrumentType)
  const extracted = extractSingleInstrumentValues(data, requiredFields)
  const found = requiredFields.filter(f => extracted[f] !== undefined).length
  const ratio = requiredFields.length ? found / requiredFields.length : 0
  if (ratio >= 0.6 && rowCount <= 5) return { type: 'single', data, confidence: 0.9 }
  if (ratio >= 0.6) return { type: 'single', data, confidence: 0.8 }
  if (rowCount > 10) return { type: 'multi', data, confidence: 0.7 }
  return { type: 'multi', data, confidence: 0.6 }
}

export function detectInstrumentNameColumn(data) {
  if (!data || !data.length) return { columnName: null, confidence: 0 }
  const headers = Object.keys(data[0] || {})
  const namePatterns = ['instrument', 'name', 'security', 'bond', 'tbill',
                        'issuer', 'counterparty', 'company', 'entity',
                        'description', 'asset', 'title', 'label', 'id']
  let best = null, bestScore = 0
  for (const h of headers) {
    const lower = h.toLowerCase()
    let score = 0
    for (const p of namePatterns) {
      if (lower === p) score += 3
      else if (lower.includes(p)) score += 2
    }
    const sample = data.slice(0, 10).map(r => r[h]).filter(v => v && v !== '')
    if (sample.length > 0) {
      const nameLike = sample.filter(v => {
        if (typeof v !== 'string') return false
        const c = v.trim()
        return c.length > 1 && !/^[\d.,\-$]+$/.test(c) && /[a-zA-Z]/.test(c)
      }).length
      score += (nameLike / Math.max(sample.length, 1)) * 3
    }
    if (score > bestScore) { bestScore = score; best = h }
  }
  return { columnName: best, confidence: Math.min(bestScore / 8, 1) }
}

export function extractInstrumentNames(data, columnName) {
  if (!data || !data.length || !columnName) return []
  const names = new Set()
  for (const row of data) {
    const v = row[columnName]
    if (v && typeof v === 'string' && v.trim()) names.add(v.trim())
  }
  return Array.from(names)
}

export function looksLikeNumber(value) {
  if (typeof value === 'number') return true
  if (typeof value !== 'string') return false
  return /^[\d,.$\-]+$/.test(value.trim())
}

export function parseNumberValue(value) {
  if (typeof value === 'number') return value
  if (typeof value !== 'string') return NaN
  return parseFloat(value.replace(/[$,]/g, '').trim())
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
  return value
}

export function cleanValue(value) {
  if (value === null || value === undefined || value === '') return ''
  if (typeof value === 'string') return value.trim()
  return value
}

export function getSingleInstrumentConfidence(data, instrumentType) {
  return detectSheetType(data, instrumentType).confidence || 0
}