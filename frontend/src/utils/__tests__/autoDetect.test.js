import { describe, it, expect } from 'vitest'
import * as XLSX from 'xlsx'
import { autoDetectInstrumentFields } from '../autoDetectInstrument.js'

const REQUIRED = ['BondName', 'FaceValue', 'CouponRate', 'Yield',
  'Years to Maturity', 'Maturity Date', 'Issue Date', 'Settlement Date',
  'Valuation Date', 'Last Coupon Date', 'Coupon Frequency',
  'Currency', 'Day Count Convention', 'Instrument Type', 'Status']

function makeWorkbook() {
  const rows = [
    ['Counterparty', 'Richaw'],
    ['Valuation Date', '31-Dec-24'],
    ['Principal', 200059.91],
    ['Instrument Type', 'Bond'],
    ['Interest Rate', '12%'],
    ['Interest Pmt Fequency', 'Semi-annually'],
    ['Maturity Date', '6-May-28'],
    ['Issue Date', '8-May-23'],
    ['Next Coupon Payment Date', '7-May-25'],
    ['Solar companies credit spread', '3%'],
    ['Present Value', 216188.46],
    ['Fair value', 216188.46],
  ]
  const ws = XLSX.utils.aoa_to_sheet(rows)
  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, ws, 'Bond Sheet')
  const out = XLSX.write(wb, { type: 'array', bookType: 'xlsx' })
  const u8 = out instanceof Uint8Array ? out : new Uint8Array(out)
  return u8.buffer.slice(u8.byteOffset, u8.byteOffset + u8.byteLength)
}

describe('autoDetectInstrumentFields regression', () => {
  it('detects counterparty as instrument_name via fallback', async () => {
    const r = await autoDetectInstrumentFields(makeWorkbook(), 'Bond Sheet', REQUIRED, 'bonds')
    const name = r.fields.instrument_name || r.additionalFields.instrument_name
    expect(name).toBe('Richaw')
  })

  it('keeps credit spread out of rate fields', async () => {
    const r = await autoDetectInstrumentFields(makeWorkbook(), 'Bond Sheet', REQUIRED, 'bonds')
    const all = { ...r.fields, ...r.additionalFields }
    const rate = all.coupon_rate ?? all.interest_rate
    expect(rate).toBeDefined()
    expect(String(rate)).toMatch(/12|0\.12/)
    expect(all.spread).toBeDefined()
    expect(String(all.spread)).not.toBe(String(rate))
  })

  it('does not store header text like "PV" as present_value', async () => {
    const r = await autoDetectInstrumentFields(makeWorkbook(), 'Bond Sheet', REQUIRED, 'bonds')
    const pv = r.fields.present_value || r.additionalFields.present_value
    if (pv !== undefined) {
      expect(String(pv)).not.toBe('PV')
      expect(Number.isFinite(parseFloat(String(pv).replace(/[$,\s]/g, '')))).toBe(true)
    }
  })

  it('detects maturity and issue dates without reversal', async () => {
    const r = await autoDetectInstrumentFields(makeWorkbook(), 'Bond Sheet', REQUIRED, 'bonds')
    expect(String(r.fields.maturity_date ?? r.additionalFields.maturity_date)).toMatch(/May-28|2028/)
    expect(String(r.fields.issue_date ?? r.additionalFields.issue_date)).toMatch(/May-23|2023/)
  })
})

describe('tabular layout detection', () => {
  function makeTabular() {
    const rows = [
      ['Fund Name', 'Portfolio', 'Short Name', 'Maturity Date', 'Issue Date', 'Rate', 'Nominal', 'Present Value', 'Counterparty'],
      ['FUND1', 'Port A', 'INST-001', '2/3/25', '11/4/24', '5.0%', '192.84', '193.47', 'CABS Bank'],
      ['FUND2', 'Port B', 'INST-002', '3/4/25', '12/5/24', '7.5%', '500.00', '510.25', 'OTHER BANK'],
      ['FUND3', 'Port C', 'INST-003', '4/5/25', '1/6/25', '10.0%', '75.50', '76.10', 'THIRD BANK'],
    ]
    const ws = XLSX.utils.aoa_to_sheet(rows)
    const wb = XLSX.utils.book_new()
    XLSX.utils.book_append_sheet(wb, ws, 'MM Sheet')
    const out = XLSX.write(wb, { type: 'array', bookType: 'xlsx' })
    const u8 = out instanceof Uint8Array ? out : new Uint8Array(out)
    return u8.buffer.slice(u8.byteOffset, u8.byteOffset + u8.byteLength)
  }
  const MMREQ = ['Instrument', 'Amount', 'Rate', 'Maturity Date', 'Currency']

  it('emits one independent record per instrument row', async () => {
    const r = await autoDetectInstrumentFields(makeTabular(), 'MM Sheet', MMREQ, 'money-market')
    expect(r.tabularRecords.length).toBe(3)
    expect(r.tabularRecords[0].fields.instrument_name).toContain('INST-001')
    expect(r.tabularRecords[1].fields.instrument_name).toContain('INST-002')
    expect(r.tabularRecords[2].fields.instrument_name).toContain('INST-003')
    // Row isolation: mutating one record must not affect others
    r.tabularRecords[0].fields.principal = 'HACKED'
    expect(r.tabularRecords[1].fields.principal).toBe('500.00')
    expect(r.tabularRecords[2].fields.principal).toBe('75.50')
  })

  it('records cell, header and source value provenance per field', async () => {
    const r = await autoDetectInstrumentFields(makeTabular(), 'MM Sheet', MMREQ, 'money-market')
    const meta = r.tabularRecords[0].fieldsWithMetadata
    expect(meta.principal.location).toMatch(/^[A-Z]+\d+$/)
    expect(meta.principal.originalLabel).toBe('Nominal')
    expect(String(meta.principal.sourceValue)).toContain('192.84')
    expect(meta.maturity_date.originalLabel).toBe('Maturity Date')
    expect(meta.counterparty.originalLabel).toBe('Counterparty')
  })

  it('does not treat headers or summary rows as instruments', async () => {
    const r = await autoDetectInstrumentFields(makeTabular(), 'MM Sheet', MMREQ, 'money-market')
    for (const rec of r.tabularRecords) {
      for (const v of Object.values(rec.fields)) {
        expect(String(v)).not.toMatch(/Fund Name|Portfolio|Short Name|Maturity Date|Counterparty/)
      }
    }
  })
})

describe('absolute cell coordinates', () => {
  it('tableData path resolves refs through sheet !ref origin + table offset', async () => {
    // Sheet used-range starts at B4; table occupies fullData rows 0-3, cols 0-4.
    // First data row must reference real cells (e.g. C6), not table-relative A2.
    const rows = [
      [], [], [], [],
      [null, 'Fund Name', 'Short Name', 'Maturity Date', 'Rate', 'Nominal'],
      [null, 'F1', 'INST-A', '2/3/25', '5%', '100.00'],
      [null, 'F2', 'INST-B', '3/4/25', '7%', '200.00'],
      [null, 'F3', 'INST-C', '4/5/25', '9%', '300.00'],
    ]
    const ws = XLSX.utils.aoa_to_sheet(rows)
    const wb = XLSX.utils.book_new()
    XLSX.utils.book_append_sheet(wb, ws, 'Off')
    const out = XLSX.write(wb, { type: 'array', bookType: 'xlsx' })
    const u8 = out instanceof Uint8Array ? out : new Uint8Array(out)
    const ab = u8.buffer.slice(u8.byteOffset, u8.byteOffset + u8.byteLength)

    // Rebuild fullData exactly like ExcelWorkbookViewer (from !ref.s).
    const ref = XLSX.utils.decode_range(ws['!ref'])
    const fullData = []
    for (let R = ref.s.r; R <= ref.e.r; R++) {
      const row = []
      for (let C = ref.s.c; C <= ref.e.c; C++) {
        const cell = ws[XLSX.utils.encode_cell({ r: R, c: C })]
        row.push(cell ? (cell.w ?? cell.v ?? '') : '')
      }
      fullData.push(row)
    }
    const tableData = fullData.map(r => r.slice(0, 5))
    const tableRange = { startRow: 0, endRow: 3, startCol: 0, endCol: 4, headerRow: 0 }
    const r = await autoDetectInstrumentFields(ab, 'Off', ['Instrument', 'Amount', 'Rate'], 'money-market', tableRange, tableData)
    expect(r.tabularRecords.length).toBe(3)
    const loc = r.tabularRecords[0].fieldsWithMetadata.instrument_name.location
    // !ref.s = {r:4? , c:1}; first instrument row must be a real cell, col >= B.
    expect(loc).toMatch(/^[A-Z]+\d+$/)
    expect(loc).not.toBe('A2') // would indicate table-relative coords
    expect(r.tabularRecords[0].fieldsWithMetadata.instrument_name.originalLabel).toBe('Short Name')
  })
})
