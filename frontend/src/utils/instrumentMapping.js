// ─── Word-boundary matching helpers ────────────────────────────────────────

function normalizeField(text) {
  if (text === null || text === undefined) return ''
  return String(text).toLowerCase().replace(/[_\-:]+/g, ' ').replace(/\s+/g, ' ').trim()
}

function fieldHasWord(haystack, needle) {
  const h = normalizeField(haystack)
  const n = normalizeField(needle)
  if (!h || !n) return false
  return ` ${h} `.includes(` ${n} `)
}

function fieldsOverlap(a, b) {
  const na = normalizeField(a)
  const nb = normalizeField(b)
  if (!na || !nb) return false
  return ` ${na} `.includes(` ${nb} `) || ` ${nb} `.includes(` ${na} `)
}

// ─── Auto-match columns ────────────────────────────────────────────────────

export function autoMatchColumns(fileColumns, requiredColumns, columnVariations) {
  const newMapping = {}
  if (!fileColumns || !fileColumns.length) {
    requiredColumns.forEach(reqCol => {
      newMapping[reqCol] = null
    })
    return newMapping
  }

  const instrumentNameVariations = ['instrument', 'name', 'security', 'bond', 'tbill', 'issuer', 'counterparty', 'company', 'entity', 'description']
  const nameCol = fileColumns.find(col =>
    instrumentNameVariations.some(v => fieldHasWord(col, v)) ||
    instrumentNameVariations.some(v => fieldHasWord(v, col))
  )
  const instrumentNameReq = requiredColumns.find(col =>
    fieldHasWord(col, 'instrument') || fieldHasWord(col, 'name')
  )
  if (instrumentNameReq && nameCol) {
    newMapping[instrumentNameReq] = nameCol
  }

  requiredColumns.forEach(reqCol => {
    if (newMapping[reqCol]) return
    const variations = columnVariations[reqCol] || [reqCol]
    const lowerReq = normalizeField(reqCol)
    let match = fileColumns.find(c => c === reqCol)
    if (!match) {
      match = fileColumns.find(c => normalizeField(c) === lowerReq)
    }
    if (!match) {
      match = fileColumns.find(c =>
        variations.some(v => fieldsOverlap(c, v))
      )
    }
    if (!match) {
      match = fileColumns.find(c => fieldsOverlap(c, reqCol))
    }
    newMapping[reqCol] = match || null
  })
  return newMapping
}

export function applyMappingToRows(sourceData, requiredColumns, mapping) {
  if (!sourceData || !sourceData.length) return []
  return sourceData.map(row => {
    const newRow = {}
    requiredColumns.forEach(reqCol => {
      const srcCol = mapping[reqCol]
      newRow[reqCol] = (srcCol && row[srcCol] !== undefined) ? row[srcCol] : null
    })
    return newRow
  })
}

export function isColumnMapped(col, { mappingApplied, columnMapping, rawData }) {
  if (mappingApplied) {
    return rawData && rawData.length > 0 && Object.keys(rawData[0] || {}).includes(col)
  }
  return !!(columnMapping[col] && columnMapping[col] !== '__na__')
}

export function getMissingColumns(requiredColumns, ctx) {
  return requiredColumns.filter(col => !isColumnMapped(col, ctx))
}

export function getInstrumentNameFromRow(row, mapping, fallback = 'Instrument') {
  if (!row || !mapping) return fallback
  const nameCol = mapping['Instrument Name'] || mapping['Instrument'] || mapping['Name']
  if (nameCol && row[nameCol] !== undefined && row[nameCol] !== null && row[nameCol] !== '') {
    return String(row[nameCol]).trim()
  }
  for (const [key, value] of Object.entries(row)) {
    if (
      fieldHasWord(key, 'instrument') || fieldHasWord(key, 'name') ||
      fieldHasWord(key, 'security') || fieldHasWord(key, 'bond') ||
      fieldHasWord(key, 'tbill') || fieldHasWord(key, 'issuer')
    ) {
      if (value && value !== '') {
        return String(value).trim()
      }
    }
  }
  return fallback
}

export function extractInstrumentNames(data, mapping) {
  if (!data || !data.length) return []
  const names = new Set()
  data.forEach(row => {
    const name = getInstrumentNameFromRow(row, mapping)
    if (name && name !== 'Instrument') {
      names.add(name)
    }
  })
  return Array.from(names)
}

export function prioritizeInstrumentName(mapping, fileColumns, requiredColumns) {
  const result = { ...mapping }
  const nameReq = requiredColumns.find(col =>
    fieldHasWord(col, 'instrument') || fieldHasWord(col, 'name')
  )
  if (!nameReq) return result
  if (result[nameReq] && result[nameReq] !== '__na__') {
    return result
  }
  const nameVariations = ['instrument', 'name', 'security', 'bond', 'tbill', 'issuer', 'counterparty', 'company', 'entity', 'description']
  const bestCol = fileColumns.find(col =>
    nameVariations.some(v => fieldHasWord(col, v)) ||
    nameVariations.some(v => fieldHasWord(v, col))
  )
  if (bestCol) {
    result[nameReq] = bestCol
  }
  return result
}

export function getDisplayColumns(columns) {
  const exclude = ['_raw', '_source', 'index', '__v', 'instrument_name', 'instrument_type', 'Worksheet', 'worksheet']
  const filtered = columns.filter(c => !exclude.includes(c) && !exclude.includes(c.toLowerCase()))
  const seen = new Set()
  return filtered.filter(c => {
    const base = c.replace(/_\d+$/, '').trim()
    const key = base.toLowerCase()
    if (seen.has(key)) return false
    seen.add(key)
    return true
  })
}