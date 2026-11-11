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
