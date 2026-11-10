// Cleaning operations extracted from InstrumentView
export function applyCleaningOperations(rawData, cleanedSourceData, cleaningOptions, selectedDateFormat, tableDetection = null) {
  if (!rawData.length) return { data: [], operations: [] }
  
  const cleaningSource = cleanedSourceData.length ? cleanedSourceData : rawData
  let data = JSON.parse(JSON.stringify(cleaningSource))
  const operations = []
  const originalLength = data.length
  
  if (tableDetection && tableDetection.type === 'table') {
    data = tableDetection.data
    operations.push('Auto-detected and extracted table data')
  }
  
  if (cleaningOptions.removeDuplicates) {
    const before = data.length
    const seen = new Set()
    data = data.filter(row => { const key = JSON.stringify(row); if (seen.has(key)) return false; seen.add(key); return true })
    const removed = before - data.length
    if (removed > 0) operations.push(`Removed ${removed} duplicate rows`)
  }
  
  if (cleaningOptions.removeEmptyRows) {
    const before = data.length
    data = data.filter(row => Object.values(row).some(v => v !== null && v !== '' && v !== undefined))
    const removed = before - data.length
    if (removed > 0) operations.push(`Removed ${removed} empty rows`)
  }
  
  if (cleaningOptions.trimWhitespace) {
    data = data.map(row => { const newRow = {}; Object.keys(row).forEach(k => { newRow[k] = typeof row[k] === 'string' ? row[k].trim() : row[k] }); return newRow })
    operations.push('Trimmed whitespace from all text fields')
  }
  
  if (cleaningOptions.convertToNumbers) {
    let converted = 0
    data = data.map(row => { const newRow = { ...row }; Object.keys(newRow).forEach(k => { if (typeof newRow[k] === 'string' && !isNaN(newRow[k]) && newRow[k].trim() !== '') { newRow[k] = parseFloat(newRow[k]); converted++ } }); return newRow })
    if (converted > 0) operations.push(`Converted ${converted} text values to numbers`)
  }
  
  if (cleaningOptions.fillMissingText) {
    let filled = 0
    data = data.map(row => { Object.keys(row).forEach(k => { if (row[k] === undefined || row[k] === null || row[k] === '') { row[k] = 'N/A'; filled++ } }); return row })
    if (filled > 0) operations.push(`Filled ${filled} missing values with 'N/A'`)
  }
  
  if (cleaningOptions.dropRowsWithMissing) {
    const before = data.length
    data = data.filter(row => Object.values(row).every(v => v !== null && v !== '' && v !== undefined && (typeof v !== 'number' || !isNaN(v))))
    const removed = before - data.length
    if (removed > 0) operations.push(`Removed ${removed} rows with missing values`)
  }
  
  if (cleaningOptions.removeOutliers) {
    const numericCols = Object.keys(data[0] || {}).filter(col => data.some(row => typeof row[col] === 'number'))
    let removedTotal = 0
    for (const col of numericCols) {
      const before = data.length
      const values = data.map(r => r[col]).filter(v => typeof v === 'number')
      const mean = values.reduce((a, b) => a + b, 0) / values.length
      const std = Math.sqrt(values.map(v => Math.pow(v - mean, 2)).reduce((a, b) => a + b, 0) / values.length)
      const threshold = 3 * std
      data = data.filter(row => Math.abs(row[col] - mean) <= threshold)
      removedTotal += before - data.length
    }
    if (removedTotal > 0) operations.push(`Removed ${removedTotal} outlier rows`)
  }
  
  if (cleaningOptions.standardizeDates) {
    let standardized = 0
    const format = selectedDateFormat || 'YYYY-MM-DD'
    data = data.map(row => {
      Object.keys(row).forEach(k => {
        if (k.toLowerCase().includes('date') && row[k]) {
          const d = new Date(row[k])
          if (!isNaN(d)) {
            const utcDay = String(d.getUTCDate()).padStart(2, '0')
            const utcMonth = String(d.getUTCMonth() + 1).padStart(2, '0')
            const utcYear = d.getUTCFullYear()
            const utcShortYear = utcYear.toString().slice(-2)
            let formattedDate = ''
            if (format === 'YYYY-MM-DD') formattedDate = `${utcYear}-${utcMonth}-${utcDay}`
            else if (format === 'DD-MM-YYYY') formattedDate = `${utcDay}-${utcMonth}-${utcYear}`
            else if (format === 'MM-DD-YYYY') formattedDate = `${utcMonth}-${utcDay}-${utcYear}`
            else if (format === 'DD/MM/YYYY') formattedDate = `${utcDay}/${utcMonth}/${utcYear}`
            else if (format === 'MM/DD/YYYY') formattedDate = `${utcMonth}/${utcDay}/${utcYear}`
            else if (format === 'YYYY/MM/DD') formattedDate = `${utcYear}/${utcMonth}/${utcDay}`
            else if (format === 'DD-MM-YY') formattedDate = `${utcDay}-${utcMonth}-${utcShortYear}`
            else if (format === 'MM-DD-YY') formattedDate = `${utcMonth}-${utcDay}-${utcShortYear}`
            else formattedDate = `${utcYear}-${utcMonth}-${utcDay}`
            row[k] = formattedDate
            standardized++
          }
        }
      })
      return row
    })
    if (standardized > 0) operations.push(`Standardized ${standardized} date values to ${format}`)
  }
  
  if (cleaningOptions.removeSpecialChars) {
    data = data.map(row => { Object.keys(row).forEach(k => { if (typeof row[k] === 'string') row[k] = row[k].replace(/[^a-zA-Z0-9\s]/g, '') }); return row })
    operations.push('Removed special characters from text fields')
  }
  
  if (cleaningOptions.changeCase && cleaningOptions.caseType !== 'none') {
    const caseType = cleaningOptions.caseType === 'upper' ? 'UPPERCASE' : cleaningOptions.caseType === 'lower' ? 'lowercase' : 'Title Case'
    data = data.map(row => { Object.keys(row).forEach(k => { if (typeof row[k] === 'string') { if (cleaningOptions.caseType === 'upper') row[k] = row[k].toUpperCase(); else if (cleaningOptions.caseType === 'lower') row[k] = row[k].toLowerCase(); else if (cleaningOptions.caseType === 'title') row[k] = row[k].replace(/\b\w/g, l => l.toUpperCase()) } }); return row })
    operations.push(`Changed text to ${caseType}`)
  }
  
  if (cleaningOptions.fillWithCustom && cleaningOptions.customFillValue) {
    let filled = 0
    data = data.map(row => { Object.keys(row).forEach(k => { if (row[k] === undefined || row[k] === null || row[k] === '') { row[k] = cleaningOptions.customFillValue; filled++ } }); return row })
    if (filled > 0) operations.push(`Filled ${filled} missing values with custom value`)
  }

  if (cleaningOptions.standardizeCurrency) {
    let normalized = 0
    data = data.map(row => {
      Object.keys(row).forEach(k => {
        const v = row[k]
        if (typeof v === 'string' && /[$€£¥]|\b(ZWG|USD|ZAR|BWP|EUR|GBP|ZMW|KES)\b/i.test(v)) {
          const cleaned = v.replace(/[^\d.\-]/g, '')
          if (cleaned !== '' && !isNaN(Number(cleaned))) {
            row[k] = Number(cleaned)
            normalized++
          }
        }
      })
      return row
    })
    if (normalized > 0) operations.push(`Normalized ${normalized} currency values`)
  }

  return { data, operations }
}
