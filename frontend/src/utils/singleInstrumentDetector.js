/**
 * Single-Instrument Auto-Detection Engine
 *
 * Scans the full 2D worksheet grid (actual cell coordinates) and finds
 * required financial fields across multiple tables, key-value pairs, and
 * irregular layouts — without column mapping or mock/fallback values.
 */

import { getRequiredFieldMappings } from './sheetTypeDetector'

// ─── Field label synonyms (equivalent names) ───────────────────────────────
const FIELD_SYNONYMS = {
  principal: [
    'face value', 'nominal value', 'principal', 'par value', 'par',
    'nominal', 'notional', 'investment amount', 'amount invested', 'capital'
  ],
  interestRate: [
    'interest rate', 'rate', 'coupon rate', 'coupon', 'annual rate',
    'nominal rate', 'investment rate', 'lending rate', 'fixed rate'
  ],
  daysToMaturity: [
    'days to maturity', 'days of maturity', 'remaining days', 'term days',
    'tenor', 'term', 'duration days', 'days', 'maturity days'
  ],
  issueDate: [
    'issue date', 'settlement date', 'trade date', 'value date',
    'loan date', 'start date', 'effective date', 'origination date'
  ],
  maturityDate: [
    'maturity date', 'redemption date', 'expiry date', 'end date',
    'due date', 'maturity'
  ],
  faceValue: [
    'face value', 'nominal value', 'principal', 'par value', 'par',
    'nominal', 'nominal value', 'amount', 'investment amount'
  ],
  couponRate: [
    'coupon rate', 'coupon', 'interest rate', 'rate', 'fixed rate',
    'annual coupon', 'stated coupon'
  ],
  yield: [
    'yield', 'ytm', 'yield to maturity', 'market yield', 'discount yield',
    'investment yield', 'effective yield', 'redemption yield'
  ],
  discountRate: [
    'discount rate', 'discount yield', 'bank discount', 'discount',
    't-bill rate', 'auction rate'
  ],
  frequency: [
    'frequency', 'payment frequency', 'coupon frequency', 'date frequency',
    'semi-annual', 'semi annually', 'semiannual', 'quarterly', 'annual'
  ],
  auctionDate: [
    'auction date', 'issue date', 'settlement date', 'trade date', 'purchase date'
  ],
  instrumentName: [
    'instrument', 'bond name', 'security', 'name', 'description',
    'issuer', 'counterparty', 'pool name', 'instrument name', 'isin'
  ],
  purchasePrice: ['purchase price', 'buy price', 'price paid', 'market price', 'clean price'],
  settlementDate: ['settlement date', 'value date', 'trade date']
}

const NUMERIC_FIELDS = new Set([
  'principal', 'faceValue', 'interestRate', 'couponRate', 'yield',
  'discountRate', 'daysToMaturity', 'purchasePrice', 'price'
])

const DATE_FIELDS = new Set(['issueDate', 'maturityDate', 'auctionDate', 'settlementDate'])

const FIELD_DISPLAY_NAMES = {
  principal: 'Principal / Face Value',
  interestRate: 'Interest Rate',
  daysToMaturity: 'Days to Maturity',
  issueDate: 'Issue Date',
  maturityDate: 'Maturity Date',
  faceValue: 'Face Value',
  couponRate: 'Coupon Rate',
  yield: 'Yield / YTM',
  discountRate: 'Discount Rate',
  frequency: 'Payment Frequency',
  auctionDate: 'Auction Date',
  instrumentName: 'Instrument Name',
  purchasePrice: 'Purchase Price',
  settlementDate: 'Settlement Date'
}

// ─── Helpers ───────────────────────────────────────────────────────────────

function isEmpty(val) {
  if (val === null || val === undefined) return true
  if (typeof val === 'string' && val.trim() === '') return true
  return false
}

function normalizeLabel(text) {
  if (text === null || text === undefined) return ''
  return String(text).toLowerCase().replace(/[_\-:]/g, ' ').replace(/\s+/g, ' ').trim()
}

function looksLikeLabel(text) {
  if (isEmpty(text)) return false
  const s = String(text).trim()
  // Labels are usually text, not pure numbers
  if (typeof text === 'number') return false
  if (/^[\d\.,\-$%]+$/.test(s)) return false
  return /[a-zA-Z]/.test(s)
}

function looksLikeNumber(val) {
  if (typeof val === 'number' && !isNaN(val)) return true
  if (typeof val !== 'string') return false
  const cleaned = val.replace(/[$,%\s]/g, '').replace(/,/g, '')
  return cleaned !== '' && !isNaN(parseFloat(cleaned))
}

function looksLikeDate(val) {
  if (val instanceof Date) return true
  if (typeof val !== 'string' && typeof val !== 'number') return false
  const s = String(val).trim()
  return (
    /^\d{4}-\d{2}-\d{2}/.test(s) ||
    /^\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}/.test(s) ||
    /^\d{1,2}[\s\-][A-Za-z]{3}[\s\-]\d{2,4}/.test(s) ||
    /^[A-Za-z]{3}[\s\-]\d{2,4}/.test(s)
  )
}

function parseNumeric(val) {
  if (typeof val === 'number') return val
  if (typeof val !== 'string') return null
  const cleaned = val.replace(/[$,%\s]/g, '').replace(/,/g, '')
  const n = parseFloat(cleaned)
  return isNaN(n) ? null : n
}

function parseDate(val) {
  if (val instanceof Date) return val.toISOString().split('T')[0]
  if (typeof val !== 'string') return val
  const s = val.trim()
  if (/^\d{4}-\d{2}-\d{2}/.test(s)) return s.substring(0, 10)
  const dmy = s.match(/^(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})/)
  if (dmy) return `${dmy[3]}-${dmy[2].padStart(2, '0')}-${dmy[1].padStart(2, '0')}`
  const monthMap = {
    jan: '01', feb: '02', mar: '03', apr: '04', may: '05', jun: '06',
    jul: '07', aug: '08', sep: '09', oct: '10', nov: '11', dec: '12'
  }
  const dMonY = s.match(/(\d{1,2})[\s\-]([A-Za-z]{3})[\s\-](\d{4})/)
  if (dMonY && monthMap[dMonY[2].toLowerCase()]) {
    return `${dMonY[3]}-${monthMap[dMonY[2].toLowerCase()]}-${dMonY[1].padStart(2, '0')}`
  }
  return s
}

function cellRef(row, col, sheetStartRow = 0, sheetStartCol = 0) {
  const r = row + sheetStartRow + 1
  let c = col + sheetStartCol
  let letters = ''
  while (c >= 0) {
    letters = String.fromCharCode((c % 26) + 65) + letters
    c = Math.floor(c / 26) - 1
  }
  return `${letters}${r}`
}

function labelMatchesField(labelText, fieldKey) {
  const norm = normalizeLabel(labelText)
  if (!norm) return false
  const synonyms = FIELD_SYNONYMS[fieldKey] || [fieldKey]
  const fieldNorm = normalizeLabel(fieldKey.replace(/([A-Z])/g, ' $1'))

  for (const syn of synonyms) {
    const synNorm = normalizeLabel(syn)
    if (norm === synNorm) return { match: true, score: 100 }
    if (norm.includes(synNorm) || synNorm.includes(norm)) return { match: true, score: 85 }
    // Word overlap
    const labelWords = norm.split(' ')
    const synWords = synNorm.split(' ')
    const overlap = labelWords.filter(w => w.length > 2 && synWords.some(sw => sw.includes(w) || w.includes(sw)))
    if (overlap.length >= Math.min(2, synWords.length)) return { match: true, score: 70 }
  }
  if (norm.includes(fieldNorm) || fieldNorm.includes(norm)) return { match: true, score: 60 }
  return { match: false, score: 0 }
}

function isValidValueForField(value, fieldKey) {
  if (isEmpty(value)) return false
  if (NUMERIC_FIELDS.has(fieldKey)) return looksLikeNumber(value)
  if (DATE_FIELDS.has(fieldKey)) return looksLikeDate(value) || looksLikeNumber(value)
  if (fieldKey === 'frequency') return true
  if (fieldKey === 'instrumentName') return looksLikeLabel(value) || typeof value === 'string'
  return !isEmpty(value)
}

function normalizeFieldValue(value, fieldKey) {
  if (isEmpty(value)) return null
  if (NUMERIC_FIELDS.has(fieldKey)) {
    const n = parseNumeric(value)
    return n !== null ? n : value
  }
  if (DATE_FIELDS.has(fieldKey)) return parseDate(value)
  if (fieldKey === 'frequency' && typeof value === 'string') {
    const lower = value.toLowerCase()
    if (lower.includes('semi')) return 'Semi-Annual'
    if (lower.includes('quarter')) return 'Quarterly'
    if (lower.includes('annual') || lower.includes('year')) return 'Annual'
    if (lower.includes('month')) return 'Monthly'
  }
  if (typeof value === 'string') return value.trim()
  return value
}

function getMergedValue(worksheet, absRow, absCol) {
  const merges = worksheet.mergedRanges || []
  for (const m of merges) {
    if (absRow >= m.min_row && absRow <= m.max_row &&
        absCol >= m.min_col && absCol <= m.max_col) {
      return worksheet.fullData[m.min_row]?.[m.min_col] ?? ''
    }
  }
  return worksheet.fullData[absRow]?.[absCol] ?? ''
}

function getCellAt(worksheet, table, localRow, localCol) {
  const absRow = (worksheet.startRow || 0) + table.startRow + localRow
  const absCol = (worksheet.startCol || 0) + table.startCol + localCol
  const merged = getMergedValue(worksheet, absRow, absCol)
  if (!isEmpty(merged)) return merged
  return table.cells[localRow]?.[localCol] ?? ''
}

// ─── Step 1: detectAllTablesInWorksheet ────────────────────────────────────

/**
 * Find all separate table regions in a worksheet (2D grid).
 * Multiple tables on one sheet still = one instrument.
 *
 * @param {{ fullData: array[][], name?: string, startRow?: number, startCol?: number }} worksheet
 * @returns {Array} table regions with cell slices and coordinates
 */
export function detectAllTablesInWorksheet(worksheet) {
  const fullData = worksheet?.fullData
  if (!fullData || !fullData.length) return []

  const sheetName = worksheet.name || 'Sheet'
  const rowCount = fullData.length
  const colCount = Math.max(...fullData.map(r => (r || []).length), 0)

  const tables = []
  let regionStart = -1

  for (let r = 0; r < rowCount; r++) {
    const row = fullData[r] || []
    const nonEmpty = row.filter(c => !isEmpty(c)).length

    if (nonEmpty >= 1) {
      if (regionStart === -1) regionStart = r
    } else if (regionStart !== -1) {
      const t = buildTableRegion(fullData, regionStart, r - 1, colCount)
      if (t) {
        tables.push({
          ...t,
          id: tables.length,
          name: `${sheetName} – Table ${tables.length + 1}`,
          sheetName
        })
      }
      regionStart = -1
    }
  }

  if (regionStart !== -1) {
    const t = buildTableRegion(fullData, regionStart, rowCount - 1, colCount)
    if (t) {
      tables.push({
        ...t,
        id: tables.length,
        name: `${sheetName} – Table ${tables.length + 1}`,
        sheetName
      })
    }
  }

  // Single key-value rows scattered without blank separators — treat whole sheet as one table
  if (tables.length === 0) {
    const t = buildTableRegion(fullData, 0, rowCount - 1, colCount)
    if (t) {
      tables.push({ ...t, id: 0, name: `${sheetName} – Full Sheet`, sheetName })
    }
  }

  return tables
}

function buildTableRegion(fullData, startRow, endRow, maxCols) {
  let minCol = maxCols
  let maxCol = -1

  for (let r = startRow; r <= endRow; r++) {
    const row = fullData[r] || []
    for (let c = 0; c < Math.max(row.length, maxCols); c++) {
      if (!isEmpty(row[c])) {
        minCol = Math.min(minCol, c)
        maxCol = Math.max(maxCol, c)
      }
    }
  }

  if (maxCol < minCol) return null

  const cells = []
  for (let r = startRow; r <= endRow; r++) {
    const slice = []
    for (let c = minCol; c <= maxCol; c++) {
      slice.push(fullData[r]?.[c] ?? '')
    }
    cells.push(slice)
  }

  return {
    startRow,
    endRow,
    startCol: minCol,
    endCol: maxCol,
    rowCount: endRow - startRow + 1,
    colCount: maxCol - minCol + 1,
    cells
  }
}

// ─── Step 2: extractRequiredFieldsFromTables ─────────────────────────────────

/**
 * Scan every cell in every table and collect label→value candidates.
 *
 * @param {Array} tables - from detectAllTablesInWorksheet
 * @param {string[]} requiredFields - field keys for instrument type
 * @param {object} worksheet - full worksheet with mergedRanges
 * @returns {Array} field candidates with scores
 */
export function extractRequiredFieldsFromTables(tables, requiredFields, worksheet = {}) {
  const candidates = []
  const directions = [
    { dr: 0, dc: 1, type: 'right' },
    { dr: 1, dc: 0, type: 'below' },
    { dr: 0, dc: -1, type: 'left' },
    { dr: -1, dc: 0, type: 'above' }
  ]

  for (const table of tables) {
    const rows = table.rowCount
    const cols = table.colCount

    // ── A) Key-value pairs: label cell + adjacent value ──
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const cellVal = getCellAt(worksheet, table, r, c)
        if (!looksLikeLabel(cellVal)) continue

        for (const fieldKey of requiredFields) {
          const { match, score: labelScore } = labelMatchesField(cellVal, fieldKey)
          if (!match) continue

          for (const { dr, dc, type } of directions) {
            const nr = r + dr
            const nc = c + dc
            if (nr < 0 || nc < 0 || nr >= rows || nc >= cols) continue
            const val = getCellAt(worksheet, table, nr, nc)
            if (!isValidValueForField(val, fieldKey)) continue
            if (looksLikeLabel(val) && !NUMERIC_FIELDS.has(fieldKey)) continue

            const absRow = (worksheet.startRow || 0) + table.startRow + nr
            const absCol = (worksheet.startCol || 0) + table.startCol + nc

            candidates.push({
              fieldKey,
              labelText: String(cellVal).trim(),
              rawValue: val,
              tableId: table.id,
              tableName: table.name,
              row: absRow,
              col: absCol,
              labelRow: (worksheet.startRow || 0) + table.startRow + r,
              labelCol: (worksheet.startCol || 0) + table.startCol + c,
              matchType: `key-value-${type}`,
              score: labelScore + (type === 'right' ? 10 : type === 'below' ? 8 : 5)
            })
          }
        }
      }
    }

    // ── B) Column header + data row pattern ──
    if (rows >= 2) {
      for (let headerRowIdx = 0; headerRowIdx < Math.min(3, rows - 1); headerRowIdx++) {
        for (let c = 0; c < cols; c++) {
          const headerVal = getCellAt(worksheet, table, headerRowIdx, c)
          if (!looksLikeLabel(headerVal)) continue

          for (const fieldKey of requiredFields) {
            const { match, score: labelScore } = labelMatchesField(headerVal, fieldKey)
            if (!match) continue

            for (let dataRow = headerRowIdx + 1; dataRow < rows; dataRow++) {
              const val = getCellAt(worksheet, table, dataRow, c)
              if (!isValidValueForField(val, fieldKey)) continue

              const absRow = (worksheet.startRow || 0) + table.startRow + dataRow
              const absCol = (worksheet.startCol || 0) + table.startCol + c

              candidates.push({
                fieldKey,
                labelText: String(headerVal).trim(),
                rawValue: val,
                tableId: table.id,
                tableName: table.name,
                row: absRow,
                col: absCol,
                labelRow: (worksheet.startRow || 0) + table.startRow + headerRowIdx,
                labelCol: absCol,
                matchType: 'column-header',
                score: labelScore + 5
              })
              break // first data row only for single-instrument
            }
          }
        }
      }
    }
  }

  return candidates
}

// ─── Step 3: matchFieldsToValues ─────────────────────────────────────────────

/**
 * Pick the best candidate per required field. No guessing — missing stays missing.
 *
 * @param {Array} candidates - from extractRequiredFieldsFromTables
 * @param {string[]} requiredFields
 * @returns {{ values, sources, missing, detectedCount, totalCount }}
 */
export function matchFieldsToValues(candidates, requiredFields) {
  const values = {}
  const sources = {}
  const missing = []

  for (const fieldKey of requiredFields) {
    const fieldCandidates = candidates
      .filter(c => c.fieldKey === fieldKey)
      .sort((a, b) => b.score - a.score)

    if (fieldCandidates.length === 0) {
      missing.push(fieldKey)
      values[fieldKey] = null
      continue
    }

    const best = fieldCandidates[0]
    const normalized = normalizeFieldValue(best.rawValue, fieldKey)

    if (normalized === null || normalized === undefined || normalized === '') {
      missing.push(fieldKey)
      values[fieldKey] = null
      continue
    }

    values[fieldKey] = normalized
    sources[fieldKey] = {
      label: best.labelText,
      table: best.tableName,
      cellRef: cellRef(best.row, best.col, 0, 0),
      row: best.row + 1,
      col: best.col + 1,
      matchType: best.matchType
    }
  }

  const detectedCount = requiredFields.filter(f => values[f] !== null && values[f] !== undefined).length

  return {
    values,
    sources,
    missing,
    detectedCount,
    totalCount: requiredFields.length
  }
}

// ─── Orchestrator ────────────────────────────────────────────────────────────

/**
 * Full single-instrument auto-detect pipeline.
 *
 * @param {{ fullData, mergedRanges?, name?, startRow?, startCol? }} worksheet
 * @param {string} instrumentType - 'money-market' | 'bonds' | 'tbills'
 */
export function detectSingleInstrumentFromWorksheet(worksheet, instrumentType = 'money-market') {
  const requiredFields = getRequiredFieldMappings(instrumentType)

  const tables = detectAllTablesInWorksheet(worksheet)
  if (!tables.length) {
    return {
      success: false,
      error: 'No data tables found on this worksheet.',
      values: {},
      sources: {},
      missing: requiredFields,
      tables: [],
      detectedCount: 0,
      totalCount: requiredFields.length
    }
  }

  const candidates = extractRequiredFieldsFromTables(tables, requiredFields, worksheet)
  const matched = matchFieldsToValues(candidates, requiredFields)

  return {
    success: matched.detectedCount > 0,
    values: matched.values,
    sources: matched.sources,
    missing: matched.missing,
    tables,
    candidates,
    detectedCount: matched.detectedCount,
    totalCount: matched.totalCount,
    instrumentType
  }
}

export function getFieldDisplayName(fieldKey) {
  return FIELD_DISPLAY_NAMES[fieldKey] || fieldKey.replace(/([A-Z])/g, ' $1').replace(/^./, s => s.toUpperCase())
}

export function buildPreviewRows(detectionResult) {
  const { values, sources, missing, instrumentType } = detectionResult
  const requiredFields = getRequiredFieldMappings(instrumentType)
  const rows = []

  for (const fieldKey of requiredFields) {
    const val = values[fieldKey]
    const src = sources[fieldKey]
    rows.push({
      fieldKey,
      fieldLabel: getFieldDisplayName(fieldKey),
      value: val !== null && val !== undefined ? val : '',
      status: val !== null && val !== undefined && val !== '' ? 'detected' : 'missing',
      source: src ? `${src.table} (${src.cellRef}) – "${src.label}"` : '',
      sourceDetail: src || null
    })
  }

  return rows
}

/**
 * Convert detected values to one backend-ready row (for cleaning/calculations).
 */
export function detectedValuesToDataRow(values, instrumentType) {
  const columnMap = {
    principal: 'Principal',
    interestRate: 'Interest Rate',
    daysToMaturity: 'Days to Maturity',
    issueDate: 'Issue Date',
    maturityDate: 'Maturity Date',
    faceValue: 'Face Value',
    couponRate: 'Coupon Rate',
    yield: 'Yield',
    discountRate: 'Discount Rate',
    frequency: 'Frequency',
    auctionDate: 'Auction Date',
    instrumentName: 'Instrument Name',
    purchasePrice: 'Purchase Price',
    settlementDate: 'Settlement Date'
  }

  const row = { 'Instrument Type': instrumentType }
  for (const [key, col] of Object.entries(columnMap)) {
    if (values[key] !== null && values[key] !== undefined && values[key] !== '') {
      row[col] = values[key]
    }
  }
  return row
}
