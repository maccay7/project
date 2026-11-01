// Excel export utilities extracted from InstrumentView
import * as XLSX from 'xlsx'

export function downloadCalculatedInstrumentsExcel(summaryRows, dedupeColumns, formatColumnHeader, activeValuationDate, activeSessionName) {
  if (!summaryRows.length) {
    throw new Error('No calculated instruments to export')
  }
  
  const workbook = XLSX.utils.book_new()
  const allColumns = new Set()
  summaryRows.forEach(row => {
    Object.keys(row).forEach(key => allColumns.add(key))
  })
  
  const columns = dedupeColumns(Array.from(allColumns)).filter(col => {
    const normalized = String(col).toLowerCase().replace(/[_\s\-]+/g, '')
    // Exclude Worksheet, Workbook, and Ordered Derivations
    if (normalized === 'worksheet' || normalized === 'workbook') return false
    if (normalized === 'orderedderivations' || normalized === 'ordered_derivations') return false
    return true
  })
  
  const data = [columns.map(formatColumnHeader)]
  summaryRows.forEach(row => {
    const dataRow = columns.map(col => {
      const value = row[col]
      return value !== undefined && value !== null ? value : ''
    })
    data.push(dataRow)
  })
  
  const worksheet = XLSX.utils.aoa_to_sheet(data)
  const columnWidths = columns.map(col => {
    const isNumeric = col.toLowerCase().includes('value') || col.toLowerCase().includes('amount') || col.toLowerCase().includes('rate') || col.toLowerCase().includes('yield') || col.toLowerCase().includes('price') || col.toLowerCase().includes('principal') || col.toLowerCase().includes('interest') || col.toLowerCase().includes('discount') || col.toLowerCase().includes('coupon')
    const isDate = col.toLowerCase().includes('date')
    const isName = col.toLowerCase().includes('name') || col.toLowerCase().includes('instrument') || col.toLowerCase().includes('ticker') || col.toLowerCase().includes('worksheet') || col.toLowerCase().includes('workbook')
    if (isNumeric) return { wch: 18 }
    if (isDate) return { wch: 14 }
    if (isName) return { wch: 25 }
    return { wch: 20 }
  })
  
  worksheet['!cols'] = columnWidths
  const range = XLSX.utils.decode_range(worksheet['!ref'])
  
  // Style header row
  for (let C = range.s.c; C <= range.e.c; ++C) {
    const cellAddress = XLSX.utils.encode_cell({ r: 0, c: C })
    if (!worksheet[cellAddress]) continue
    worksheet[cellAddress].s = {
      font: { bold: true, color: { rgb: "FFFFFF" } },
      fill: { fgColor: { rgb: "0B2044" } },
      alignment: { horizontal: "center", vertical: "center" }
    }
  }
  
  // Style data rows
  for (let R = range.s.r + 1; R <= range.e.r; ++R) {
    for (let C = range.s.c; C <= range.e.c; ++C) {
      const cellAddress = XLSX.utils.encode_cell({ r: R, c: C })
      if (!worksheet[cellAddress]) continue
      const colName = columns[C]
      const isNumeric = colName.toLowerCase().includes('value') || colName.toLowerCase().includes('amount') || colName.toLowerCase().includes('rate') || colName.toLowerCase().includes('yield') || colName.toLowerCase().includes('price') || colName.toLowerCase().includes('percentage')
      worksheet[cellAddress].s = {
        alignment: {
          horizontal: isNumeric ? "right" : "left",
          vertical: "center"
        }
      }
    }
  }
  
  XLSX.utils.book_append_sheet(workbook, worksheet, 'Calculated Instruments')
  const suffix = activeValuationDate ? `_${activeValuationDate}` : ''
  const fileName = `Calculated_Instruments_${activeSessionName || 'Session'}${suffix}.xlsx`
  XLSX.writeFile(workbook, fileName)
}
