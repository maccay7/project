/** Column mapping helpers shared across instrument pages */

export function autoMatchColumns(fileColumns, requiredColumns, columnVariations) {
  const newMapping = {}
  requiredColumns.forEach(reqCol => {
    const variations = columnVariations[reqCol] || [reqCol]
    let match = fileColumns.find(c => c === reqCol) ||
      fileColumns.find(c => c.toLowerCase() === reqCol.toLowerCase()) ||
      fileColumns.find(c => variations.some(v =>
        c.toLowerCase().includes(v.toLowerCase()) || v.toLowerCase().includes(c.toLowerCase())
      ))
    newMapping[reqCol] = match || null
  })
  return newMapping
}

export function applyMappingToRows(sourceData, requiredColumns, mapping) {
  if (!sourceData.length) return []
  return sourceData.map(row => {
    const newRow = {}
    requiredColumns.forEach(reqCol => {
      const src = mapping[reqCol]
      newRow[reqCol] = (src && row[src] !== undefined) ? row[src] : null
    })
    return newRow
  })
}

export function isColumnMapped(col, { mappingApplied, columnMapping, rawData }) {
  if (mappingApplied) {
    return rawData.length > 0 && Object.keys(rawData[0] || {}).includes(col)
  }
  return !!(columnMapping[col] && columnMapping[col] !== '__na__')
}

export function getMissingColumns(requiredColumns, ctx) {
  return requiredColumns.filter(col => !isColumnMapped(col, ctx))
}

const NUMERIC_COLUMNS = new Set([
  'Rate', 'Amount', 'Principal', 'InterestRate', 'DiscountRate', 'Price', 'FaceValue',
  'CouponRate', 'Yield', 'AccruedInterest', 'DaysToMaturity', 'RedemptionValue'
])
const DATE_COLUMNS = new Set(['Date', 'MaturityDate', 'IssueDate'])

export function validateCellValue(columnName, value) {
  const trimmed = String(value ?? '').trim()
  if (trimmed === '') return { valid: true, value: trimmed }

  if (NUMERIC_COLUMNS.has(columnName)) {
    const num = Number(trimmed.replace(/,/g, ''))
    if (Number.isNaN(num)) {
      return { valid: false, value: trimmed, error: `"${columnName}" must be a number` }
    }
    return { valid: true, value: num }
  }

  if (DATE_COLUMNS.has(columnName)) {
    const parsed = Date.parse(trimmed)
    if (Number.isNaN(parsed)) {
      return { valid: false, value: trimmed, error: `"${columnName}" must be a valid date` }
    }
    return { valid: true, value: trimmed }
  }

  return { valid: true, value: trimmed }
}

export function validateRowEdits(row, columns) {
  const errors = []
  const validated = { ...row }
  for (const col of columns) {
    const result = validateCellValue(col, row[col])
    if (!result.valid) errors.push(result.error)
    else validated[col] = result.value
  }
  return { valid: errors.length === 0, errors, row: validated }
}
