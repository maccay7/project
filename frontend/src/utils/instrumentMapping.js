// utils/instrumentMapping.js

/**
 * 🔥 FIXED: Auto-match columns with better prioritization
 * @param {string[]} fileColumns - Column names from the uploaded file
 * @param {string[]} requiredColumns - Required columns for the instrument type
 * @param {Object} columnVariations - Variations for each required column
 * @returns {Object} mapping object { requiredColumn: fileColumn }
 */
export function autoMatchColumns(fileColumns, requiredColumns, columnVariations) {
  const newMapping = {}
  
  // If no columns, return empty mapping
  if (!fileColumns || !fileColumns.length) {
    requiredColumns.forEach(reqCol => {
      newMapping[reqCol] = null
    })
    return newMapping
  }

  // 🔥 First, prioritize "Instrument Name" column
  const instrumentNameVariations = ['instrument', 'name', 'security', 'bond', 'tbill', 'issuer', 'counterparty', 'company', 'entity', 'description']
  const nameCol = fileColumns.find(col => 
    instrumentNameVariations.some(v => col.toLowerCase().includes(v)) ||
    instrumentNameVariations.some(v => v.includes(col.toLowerCase()))
  )
  
  // Find "Instrument Name" in required columns
  const instrumentNameReq = requiredColumns.find(col => 
    col.toLowerCase().includes('instrument') || col.toLowerCase().includes('name')
  )
  
  // Map instrument name first if found
  if (instrumentNameReq && nameCol) {
    newMapping[instrumentNameReq] = nameCol
    console.log(`✅ Auto-mapped Instrument Name: "${nameCol}" → "${instrumentNameReq}"`)
  }

  // Now map the rest
  requiredColumns.forEach(reqCol => {
    // Skip if already mapped
    if (newMapping[reqCol]) return
    
    const variations = columnVariations[reqCol] || [reqCol]
    const lowerReq = reqCol.toLowerCase()
    
    // Try exact match first
    let match = fileColumns.find(c => c === reqCol)
    
    // Then case-insensitive exact match
    if (!match) {
      match = fileColumns.find(c => c.toLowerCase() === lowerReq)
    }
    
    // Then pattern match with variations
    if (!match) {
      match = fileColumns.find(c => {
        const lowerCol = c.toLowerCase()
        return variations.some(v => 
          lowerCol.includes(v.toLowerCase()) || 
          v.toLowerCase().includes(lowerCol)
        )
      })
    }
    
    // If still no match, check if the required column name appears as substring of any column
    if (!match) {
      match = fileColumns.find(c => 
        c.toLowerCase().includes(lowerReq) || 
        lowerReq.includes(c.toLowerCase())
      )
    }
    
    newMapping[reqCol] = match || null
  })
  
  return newMapping
}

/**
 * Apply mapping to transform raw data rows
 * @param {Array} sourceData - Raw data rows
 * @param {string[]} requiredColumns - Required columns
 * @param {Object} mapping - Column mapping
 * @returns {Array} Mapped data rows
 */
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

/**
 * Check if a required column is mapped
 * @param {string} col - Required column name
 * @param {Object} ctx - Context with mappingApplied, columnMapping, rawData
 * @returns {boolean}
 */
export function isColumnMapped(col, { mappingApplied, columnMapping, rawData }) {
  if (mappingApplied) {
    return rawData && rawData.length > 0 && Object.keys(rawData[0] || {}).includes(col)
  }
  return !!(columnMapping[col] && columnMapping[col] !== '__na__')
}

/**
 * Get list of missing columns
 * @param {string[]} requiredColumns - Required columns
 * @param {Object} ctx - Context with columnMapping and mappingApplied
 * @returns {string[]} Missing columns
 */
export function getMissingColumns(requiredColumns, ctx) {
  return requiredColumns.filter(col => !isColumnMapped(col, ctx))
}

/**
 * 🔥 NEW: Get the instrument name from a row using the mapping
 * @param {Object} row - Data row
 * @param {Object} mapping - Column mapping
 * @param {string} fallback - Fallback name
 * @returns {string} Instrument name
 */
export function getInstrumentNameFromRow(row, mapping, fallback = 'Instrument') {
  if (!row || !mapping) return fallback
  
  // Check if Instrument Name is mapped
  const nameCol = mapping['Instrument Name'] || mapping['Instrument'] || mapping['Name']
  if (nameCol && row[nameCol] !== undefined && row[nameCol] !== null && row[nameCol] !== '') {
    return String(row[nameCol]).trim()
  }
  
  // Try to find any column that looks like a name
  for (const [key, value] of Object.entries(row)) {
    const lowerKey = key.toLowerCase()
    if (lowerKey.includes('instrument') || lowerKey.includes('name') || 
        lowerKey.includes('security') || lowerKey.includes('bond') || 
        lowerKey.includes('tbill') || lowerKey.includes('issuer')) {
      if (value && value !== '') {
        return String(value).trim()
      }
    }
  }
  
  return fallback
}

/**
 * 🔥 NEW: Extract instrument names from a dataset
 * @param {Array} data - Data rows
 * @param {Object} mapping - Column mapping
 * @returns {string[]} Array of instrument names
 */
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

/**
 * 🔥 NEW: Prioritize instrument name column in mapping
 * @param {Object} mapping - Existing mapping
 * @param {string[]} fileColumns - File columns
 * @param {string[]} requiredColumns - Required columns
 * @returns {Object} Updated mapping
 */
export function prioritizeInstrumentName(mapping, fileColumns, requiredColumns) {
  const result = { ...mapping }
  
  // Find instrument name required column
  const nameReq = requiredColumns.find(col => 
    col.toLowerCase().includes('instrument') || col.toLowerCase().includes('name')
  )
  
  if (!nameReq) return result
  
  // Check if already mapped
  if (result[nameReq] && result[nameReq] !== '__na__') {
    return result
  }
  
  // Find best column for instrument name
  const nameVariations = ['instrument', 'name', 'security', 'bond', 'tbill', 'issuer', 'counterparty', 'company', 'entity', 'description']
  const bestCol = fileColumns.find(col => 
    nameVariations.some(v => col.toLowerCase().includes(v)) ||
    nameVariations.some(v => v.includes(col.toLowerCase()))
  )
  
  if (bestCol) {
    result[nameReq] = bestCol
    console.log(`✅ Prioritized Instrument Name: "${bestCol}" → "${nameReq}"`)
  }
  
  return result
}