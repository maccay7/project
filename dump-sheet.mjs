import * as XLSX from './frontend/node_modules/xlsx/xlsx.mjs'
import fs from 'fs'
const buf = fs.readFileSync('backend/uploads/3b9461b5011a4c269555dd52fa7f0e7f.xlsm')
const wb = XLSX.read(buf, { cellDates: true })
const ws = wb.Sheets['Richaw $205k']
const rows = XLSX.utils.sheet_to_json(ws, { header: 1, defval: '' })
for (let i = 0; i < 45; i++) {
  const r = rows[i] || []
  const cells = r.map((v, j) => v !== '' ? `${XLSX.utils.encode_col(j)}${i+1}=${JSON.stringify(v)}` : null).filter(Boolean)
  if (cells.length) console.log(cells.join(' | '))
}
