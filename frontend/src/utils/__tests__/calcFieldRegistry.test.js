import { describe, it, expect } from 'vitest'
import { validateCalcRow, validateCalcRows, registryType, CALC_REQUIRED_GROUPS } from '../calcFieldRegistry.js'

describe('calcFieldRegistry', () => {
  it('RBZ-like tbills row passes when price derived and dates present', () => {
    const row = {
      face_value: '497,376.00', purchase_price: 374387.64,
      valuation_date: '31-Dec-25', maturity_date: '22-Sep-28',
      instrument_name: 'RBZ', currency: 'USD',
    }
    const r = validateCalcRow(row, 'tbills')
    expect(r.missing).toEqual([])
  })

  it('flags genuinely missing currency-independent groups per row independently', () => {
    const rows = [
      { face_value: 100, purchase_price: 90, maturity_date: '1/1/30', valuation_date: '1/1/25' },
      { face_value: 200 }, // missing rate/price AND tenor
    ]
    const res = validateCalcRows(rows, 'tbills')
    expect(res[0].missing).toEqual([])
    expect(res[1].missing.map(m => m.id).sort()).toEqual(['rate_or_price', 'tenor'])
  })

  it('does not accept label-like text as a value', () => {
    const row = { face_value: 'Principal', purchase_price: 'Maturity Date', maturity_date: 'x' }
    const r = validateCalcRow(row, 'tbills')
    expect(r.missing.length).toBeGreaterThan(0)
  })

  it('money-market accepts rate OR price OR discount_rate', () => {
    const row = { principal: 500, discount_rate: '10%', maturity_date: '6/1/25', valuation_date: '1/1/25' }
    expect(validateCalcRow(row, 'money-market').missing).toEqual([])
    const row2 = { principal: 500, maturity_date: '6/1/25', valuation_date: '1/1/25' }
    expect(validateCalcRow(row2, 'money-market').missing.map(m => m.id)).toContain('rate_or_price')
  })

  it('bonds accepts coupon_rate via interest_rate alias and tenor via dates', () => {
    const row = { face_value: 1000, interest_rate: '12%', present_value: 900,
                  valuation_date: '1/1/25', maturity_date: '1/1/28', coupon_frequency: 1 }
    expect(validateCalcRow(row, 'bonds').missing).toEqual([])
  })

  it('registryType normalises instrument names', () => {
    expect(registryType('Treasury Bills (tbills)')).toBe('tbills')
    expect(registryType('Money Market')).toBe('money-market')
    expect(registryType('Bonds')).toBe('bonds')
  })
})
