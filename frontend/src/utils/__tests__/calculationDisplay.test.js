import { describe, it, expect } from 'vitest'
import {
  buildAggregatesFromBackend,
  hasDisplayableCalculation,
  buildValuationExcelRows,
  formatCalculationFailureMessage,
  countUniqueInstruments,
  omitInstrumentNameColumn,
  calculatedValuesOnlyRows,
  resolveCalculatedInstrumentNames,
  getYieldCurveRateForMaturity,
  parseMaturityToYears,
  reconcilePortfolioTotals
} from '../calculationDisplay.js'

describe('buildAggregatesFromBackend — multi-instrument totals', () => {
  it('money-market boxes use portfolio totals, not a single row', () => {
    const aggregates = {
      instrument_count: 3,
      total_rows: 3,
      successful_rows: 3,
      total_value: 305000,
      total_principal: 300000,
      total_interest: 5000,
      weighted_avg_rate: 5.25,
      avg_rate: 5.1,
      avg_days_to_maturity: 90,
      effective_annual_rate: 5.3
    }
    const agg = buildAggregatesFromBackend(aggregates, null, 'money-market')
    expect(agg.totalValue).toBe(305000)
    expect(agg.totalPrincipal).toBe(300000)
    expect(agg.interestEarned).toBe(5000)
    expect(agg.totalInterest).toBe(5000)
    expect(agg.instrumentCount).toBe(3)
    expect(agg.avgRate).toBe(5.1)
    expect(agg.weightedAvgRate).toBe(5.25)
    expect(agg.avgDaysToMaturity).toBe(90)
    expect(hasDisplayableCalculation(agg)).toBe(true)
  })

  it('bonds boxes use portfolio totals for multi', () => {
    const aggregates = {
      instrument_count: 2,
      total_rows: 2,
      total_value: 210000,
      total_face_value: 200000,
      total_market_value: 210000,
      total_coupon_income: 12000,
      weighted_avg_coupon: 6.0,
      avg_coupon_rate: 5.8,
      avg_ytm: 5.5,
      avg_duration: 4.2,
      accrued_interest: 800
    }
    const agg = buildAggregatesFromBackend(aggregates, null, 'bonds')
    expect(agg.totalValue).toBe(210000)
    expect(agg.totalFaceValue).toBe(200000)
    expect(agg.totalMarketValue).toBe(210000)
    expect(agg.totalAnnualIncome).toBe(12000)
    expect(agg.weightedAvgCoupon).toBe(6.0)
    expect(agg.avgCouponRate).toBe(5.8)
    expect(agg.avgYTM).toBe(5.5)
    expect(agg.accruedInterest).toBe(800)
    expect(agg.instrumentCount).toBe(2)
  })

  it('tbills boxes use portfolio totals for multi', () => {
    const aggregates = {
      instrument_count: 4,
      total_rows: 4,
      total_value: 400000,
      total_face_value: 400000,
      total_purchase_price: 392000,
      total_discount: 8000,
      avg_discount_rate: 4.5,
      weighted_avg_discount: 4.6,
      bond_equivalent_yield: 4.7,
      avg_days_to_maturity: 91
    }
    const agg = buildAggregatesFromBackend(aggregates, null, 'tbills')
    expect(agg.totalValue).toBe(400000)
    expect(agg.totalFaceValue).toBe(400000)
    expect(agg.totalPurchasePrice).toBe(392000)
    expect(agg.totalDiscount).toBe(8000)
    expect(agg.avgDiscountRate).toBe(4.5)
    expect(agg.weightedAvgDiscount).toBe(4.6)
    expect(agg.instrumentCount).toBe(4)
  })

  it('single-instrument still maps per-row fields', () => {
    const row = {
      status: 'success',
      principal: 100000,
      interest_rate: 5,
      interest_earned: 1250,
      total_value: 101250,
      term_days: 90
    }
    const agg = buildAggregatesFromBackend({}, row, 'money-market')
    expect(agg.totalValue).toBe(101250)
    expect(agg.totalPrincipal).toBe(100000)
    expect(agg.interestEarned).toBe(1250)
    expect(agg.interestRate).toBe(5)
    expect(agg.instrumentCount).toBe(1)
  })
})

describe('reconcilePortfolioTotals', () => {
  it('sums money-market results across successful and partial instruments', () => {
    const reconciled = reconcilePortfolioTotals({
      totalValue: 0,
      totalPrincipal: 0,
      totalInterest: 0,
      avgRate: 6.5
    }, [
      { status: 'success', principal: 100, interest_earned: 5, total_value: 105 },
      { status: 'partial', principal: 200, total_interest: 8, maturity_value: 208 }
    ], 'money-market')

    expect(reconciled.totalValue).toBe(313)
    expect(reconciled.totalPrincipal).toBe(300)
    expect(reconciled.totalInterest).toBe(13)
    expect(reconciled.interestEarned).toBe(13)
    expect(reconciled.avgRate).toBe(6.5)
  })

  it('sums applicable T-Bill and bond totals from their own result rows', () => {
    const tBills = reconcilePortfolioTotals({}, [
      { face_value: 100, purchase_price: 98, discount_amount: 2 },
      { face_value: 200, purchase_price: 195, discount_amount: 5 }
    ], 'tbills')
    expect(tBills.totalFaceValue).toBe(300)
    expect(tBills.totalPurchasePrice).toBe(293)
    expect(tBills.totalDiscount).toBe(7)

    const bonds = reconcilePortfolioTotals({}, [
      { face_value: 100, current_price: 101, annual_coupon: 6, accrued_interest: 1 },
      { face_value: 200, current_price: 198, annual_coupon: 10, accrued_interest: 2 }
    ], 'bonds')
    expect(bonds.totalValue).toBe(299)
    expect(bonds.totalMarketValue).toBe(299)
    expect(bonds.totalFaceValue).toBe(300)
    expect(bonds.totalAnnualIncome).toBe(16)
    expect(bonds.accruedInterest).toBe(3)
  })

  it('does not present an aggregate zero when no row calculated that value', () => {
    const reconciled = reconcilePortfolioTotals({ totalValue: 0 }, [
      { status: 'partial', principal: 100 }
    ], 'money-market')
    expect(reconciled.totalValue).toBeNull()
    expect(reconciled.totalPrincipal).toBe(100)
  })

  it('preserves aggregate totals when the response has no detail rows', () => {
    expect(reconcilePortfolioTotals(
      { totalValue: 250 },
      [],
      'money-market'
    )).toEqual({ totalValue: 250 })
  })
})

describe('buildValuationExcelRows', () => {
  it('merges cleaned inputs with calc outputs without blank overwrite', () => {
    const cleaned = [{ 'Instrument Name': 'MM-1', Principal: 100000, 'Interest Rate': 5 }]
    const calcs = [{ instrument_name: 'MM-1', total_value: 101250, interest_earned: 1250 }]
    const rows = buildValuationExcelRows(cleaned, calcs, 'money-market')
    expect(rows).toHaveLength(1)
    expect(rows[0].Principal).toBe(100000)
    expect(rows[0]['Interest Rate']).toBe(5)
    expect(rows[0].total_value).toBe(101250)
    expect(rows[0].interest_earned).toBe(1250)
    expect(rows[0]['Instrument Type']).toBe('money-market')
  })

  describe('omitInstrumentNameColumn', () => {
    it('hides instrument name aliases but preserves instrument type and valuation data', () => {
      expect(omitInstrumentNameColumn([{
        Instrument: 'MM-1',
        'Instrument Name': 'MM-1',
        instrument_name: 'MM-1',
        'Instrument Type': 'money-market',
        Principal: 100000
      }])).toEqual([{
        'Instrument Type': 'money-market',
        Principal: 100000
      }])
    })
  })

  it('uses the cleaned instrument identity and deduplicates backend aliases', () => {
    const rows = buildValuationExcelRows(
      [{ instrument_name: 'Bond A', instrument_type: 'bonds', face_value: 100000 }],
      [{
        instrument_name: 'Bond A',
        instrument_type: 'bonds',
        face_value: 100000,
        total_value: 102500,
        totalValue: 102500
      }],
      'bonds'
    )
    expect(rows[0]['Instrument Name']).toBe('Bond A')
    expect(rows[0]['Instrument Type']).toBe('bonds')
    expect(rows[0].instrument_name).toBeUndefined()
    expect(rows[0].instrument_type).toBeUndefined()
    expect(Object.keys(rows[0]).filter(key =>
      key.replace(/([a-z0-9])([A-Z])/g, '$1_$2').toLowerCase() === 'total_value'
    )).toHaveLength(1)
  })
})

describe('calculatedValuesOnlyRows', () => {
  it('keeps calculated outputs and removes cleaned inputs and row metadata', () => {
    const rows = calculatedValuesOnlyRows([
      {
        'Instrument Type': 'money-market',
        'Instrument Name': 'MM-1',
        Currency: 'USD',
        Principal: 100000,
        'Interest Rate': 5,
        'Maturity Date': '2025-12-31',
        presentValue: 101250,
        present_value: 101250,
        avg_rate: 5,
        'Interest Earned': 1250,
        fair_value: null,
        Workbook: 'Portfolio.xlsx',
        Worksheet: 'Sheet1',
        status: 'success',
        error: null
      },
      {
        'Instrument Type': 'money-market',
        'Instrument Name': 'MM-2',
        Currency: 'USD',
        Principal: 200000,
        present_value: 202500,
        'Interest Earned': 2500
      },
      {
        'Instrument Type': 'money-market',
        'Instrument Name': 'MM-3',
        Principal: 50000,
        error: 'Missing required inputs'
      }
    ], ['Principal', 'Interest Rate', 'Maturity Date'], 'money-market')

    expect(rows).toEqual([
      {
        'Instrument Name': 'MM-1',
        'Instrument Type': 'money-market',
        Currency: 'USD',
        'Present Value': 101250,
        'Average Rate': 5,
        'Interest Earned': 1250,
        'Fair Value': ''
      },
      {
        'Instrument Name': 'MM-2',
        'Instrument Type': 'money-market',
        Currency: 'USD',
        'Present Value': 202500,
        'Average Rate': '',
        'Interest Earned': 2500,
        'Fair Value': ''
      },
      {
        'Instrument Name': 'MM-3',
        'Instrument Type': 'money-market',
        Currency: '',
        'Present Value': '',
        'Average Rate': '',
        'Interest Earned': '',
        'Fair Value': ''
      }
    ])
    expect(rows.every(row => Object.keys(row).join('|') === Object.keys(rows[0]).join('|'))).toBe(true)
  })
})

describe('resolveCalculatedInstrumentNames', () => {
  it('prefers the corresponding cleaned instrument names for multi-instrument results', () => {
    expect(resolveCalculatedInstrumentNames(
      [{ 'Instrument Name': 'Cleaned A' }, { BondName: 'Cleaned B' }],
      [{ instrument_name: 'Backend A' }, { instrument_name: 'Backend B' }],
      ['Backend A', 'Backend B'],
      'Portfolio Sheet'
    )).toEqual(['Cleaned A', 'Cleaned B'])
  })

  it('uses the worksheet name for a single instrument result', () => {
    expect(resolveCalculatedInstrumentNames(
      [{ 'Instrument Name': 'Cleaned Name' }],
      [{ instrument_name: 'Backend Name' }],
      ['Backend Name'],
      'Bond Sheet'
    )).toEqual(['Bond Sheet'])
  })
})

describe('getYieldCurveRateForMaturity', () => {
  const curve = [
    { maturity: 0.5, rate: 4.2, isDate: false },
    { maturity: 1, rate: 4.6, isDate: false },
    { maturity: null, rate: 8.8, isDate: true }
  ]

  it('selects the exact maturity point from the active yield curve', () => {
    expect(getYieldCurveRateForMaturity(curve, '6M')).toBe(4.2)
    expect(getYieldCurveRateForMaturity(curve, '1Y')).toBe(4.6)
  })

  it('interpolates between curve points and ignores date-series points', () => {
    expect(getYieldCurveRateForMaturity(curve, '9M')).toBeCloseTo(4.4)
    expect(getYieldCurveRateForMaturity(curve, '3Y')).toBeNull()
  })

  it('uses the latest observation for the selected maturity in date-range mode', () => {
    expect(getYieldCurveRateForMaturity([
      { maturity: 1, rate: 4.1, date: '2026-01-01', isDate: true },
      { maturity: 1, rate: 4.3, date: '2026-02-01', isDate: true }
    ], '1Y')).toBe(4.3)
  })

  it('preserves a zero-percent curve rate', () => {
    expect(getYieldCurveRateForMaturity([
      { maturity: 1, rate: 0, isDate: false }
    ], '1Y')).toBe(0)
  })
})

describe('parseMaturityToYears', () => {
  it.each([
    ['1Y', 1],
    ['6M', 0.5],
    ['13W', 0.25],
    ['2.5Y', 2.5],
    ['1.5 Y', 1.5]
  ])('converts %s to years', (maturity, expected) => {
    expect(parseMaturityToYears(maturity)).toBeCloseTo(expected)
  })

  it('returns null for invalid or non-positive maturities', () => {
    expect(parseMaturityToYears('')).toBeNull()
    expect(parseMaturityToYears('abc')).toBeNull()
    expect(parseMaturityToYears('0Y')).toBeNull()
    expect(parseMaturityToYears('-1')).toBeNull()
  })
})

describe('countUniqueInstruments', () => {
  it('counts unique identities rather than repeated worksheet rows', () => {
    expect(countUniqueInstruments([
      { 'Instrument Name': 'MM-1', Principal: 100000 },
      { 'Instrument Name': 'MM-1', Principal: 100000 }
    ])).toBe(1)
  })

  it('uses an input fingerprint only when an instrument identifier is absent', () => {
    expect(countUniqueInstruments([
      { 'Face Value': 100000, 'Discount Rate': 5, 'Term Days': 90 },
      { face_value: 100000, discount_rate: 5, term_days: 90 },
      { face_value: 120000, discount_rate: 5, term_days: 90 }
    ])).toBe(2)
  })
})

describe('formatCalculationFailureMessage', () => {
  it('includes missing and invalid fields', () => {
    const msg = formatCalculationFailureMessage({
      error: 'Cannot calculate',
      missing_fields: ['face_value'],
      invalid_fields: [{ field: 'term_days', reason: 'must be > 0' }]
    })
    expect(msg).toContain('face_value')
    expect(msg).toContain('term_days')
  })

  it('recognizes partial calculations with available metrics and reports prerequisites', () => {
    expect(hasDisplayableCalculation({
      status: 'partial',
      totalPrincipal: 100000,
      totalValue: null
    })).toBe(true)
    const msg = formatCalculationFailureMessage({
      missing_prerequisites: [['interest_rate', 'term_days']]
    })
    expect(msg).toContain('interest_rate')
    expect(msg).toContain('term_days')
  })
})
