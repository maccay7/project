// utils/instrumentMapping.js
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