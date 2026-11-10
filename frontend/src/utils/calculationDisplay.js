

function firstDefined (...candidates) {
  for (const v of candidates) {
    if (v !== undefined && v !== null && v !== '') return v
  }
  return null
}

function fromSources (aggregates, row, snakeKeys, camelKeys = []) {
  const keys = [...camelKeys, ...snakeKeys]
  for (const k of keys) {
    if (aggregates && aggregates[k] !== undefined && aggregates[k] !== null && aggregates[k] !== '') {
      return aggregates[k]
    }
    if (row && row[k] !== undefined && row[k] !== null && row[k] !== '') {
      return row[k]
    }
  }
  return null
}

/** Prefer aggregate totals; fall back to row only for single-instrument. */
function totalOrRow (aggregates, row, totalSnake, totalCamel, rowSnake, rowCamel) {
  const fromAgg = fromSources(aggregates, null, totalSnake, totalCamel)
  if (fromAgg !== null) return fromAgg
  return fromSources(aggregates, row, rowSnake, rowCamel)
}

export function buildAggregatesFromBackend (aggregates = {}, rowCalc = null, instrumentType) {
  const row = rowCalc && typeof rowCalc === 'object' ? rowCalc : null
  const count = fromSources(aggregates, row, ['instrument_count'], ['instrumentCount'])
    ?? (row ? 1 : null)
  // Multi only when unique instrument count > 1 — never because of duplicate rows.
  const isMulti = !row && Number(count) > 1

  const avgRateValue = firstDefined(
    fromSources(aggregates, null, ['avg_rate'], ['avgRate']),
    fromSources(aggregates, null, ['weighted_avg_rate'], ['weightedAvgRate']),
    fromSources(aggregates, null, ['weighted_avg_coupon'], ['weightedAvgCoupon']),
    fromSources(aggregates, null, ['avg_coupon_rate'], ['avgCouponRate']),
    fromSources(aggregates, null, ['avg_discount_rate'], ['avgDiscountRate']),
    fromSources(aggregates, null, ['avg_ytm'], ['avgYTM']),
    // Single-instrument fallbacks only
    !isMulti ? fromSources(null, row, ['interest_rate'], ['interestRate']) : null,
    !isMulti ? fromSources(null, row, ['coupon_rate'], ['couponRate']) : null,
    !isMulti ? fromSources(null, row, ['discount_rate'], ['discountRate']) : null,
    !isMulti ? fromSources(null, row, ['avg_rate'], ['avgRate']) : null
  )

  const base = {
    totalValue: fromSources(aggregates, row, ['total_value'], ['totalValue']),
    instrumentCount: count,
    avgRate: avgRateValue,
    weightedAvgRate: fromSources(aggregates, row, ['weighted_avg_rate'], ['weightedAvgRate']),
    status: (aggregates?.status ?? row?.status) || null,
    derivations: row?.derivations ?? aggregates?.derivations ?? null,
    display_derivations: row?.display_derivations ?? aggregates?.display_derivations ?? null,
    error: row?.error ?? aggregates?.error ?? null,
    warning: row?.warning ?? aggregates?.warning ?? null,
    missing_fields: row?.missing_fields ?? aggregates?.missing_fields ?? null,
    missing_prerequisites: row?.missing_prerequisites ?? aggregates?.missing_prerequisites ?? null,
    invalid_fields: row?.invalid_fields ?? aggregates?.invalid_fields ?? null,
    calculation_errors: row?.calculation_errors ?? aggregates?.calculation_errors ?? null
  }

  if (instrumentType === 'money-market') {
    return {
      ...base,
      totalPrincipal: totalOrRow(aggregates, row,
        ['total_principal'], ['totalPrincipal'],
        ['principal'], ['principal']),
      totalInterest: totalOrRow(aggregates, row,
        ['total_interest'], ['totalInterest'],
        ['interest_earned', 'total_interest'], ['interestEarned', 'totalInterest']),
      interestEarned: totalOrRow(aggregates, row,
        ['total_interest', 'interest_earned'], ['totalInterest', 'interestEarned'],
        ['interest_earned'], ['interestEarned']),
      // Per-instrument rate only when single; multi uses avg/weighted above
      interestRate: isMulti
        ? avgRateValue
        : fromSources(aggregates, row, ['interest_rate'], ['interestRate']),
      effectiveYield: fromSources(aggregates, row, ['effective_yield'], ['effectiveYield']),
      effectiveAnnualRate: fromSources(aggregates, row, ['effective_annual_rate'], ['effectiveAnnualRate']),
      bondEquivalentYield: fromSources(aggregates, row, ['bond_equivalent_yield'], ['bondEquivalentYield']),
      discountYield: fromSources(aggregates, row, ['discount_yield'], ['discountYield']),
      avgDaysToMaturity: fromSources(aggregates, row, ['avg_days_to_maturity', 'term_days'], ['avgDaysToMaturity', 'termDays']),
      termDays: fromSources(aggregates, row, ['term_days', 'avg_days_to_maturity'], ['termDays', 'avgDaysToMaturity']),
      daysToMaturity: fromSources(aggregates, row, ['days_to_maturity', 'term_days', 'avg_days_to_maturity'], ['daysToMaturity', 'termDays']),
      maturityValue: totalOrRow(aggregates, row,
        ['maturity_value', 'total_value'], ['maturityValue', 'totalValue'],
        ['maturity_value', 'total_value'], ['maturityValue', 'totalValue']),
      presentValue: totalOrRow(aggregates, row,
        ['present_value'], ['presentValue'],
        ['present_value'], ['presentValue']),
      fairValue: totalOrRow(aggregates, row,
        ['fair_value', 'total_value'], ['fairValue', 'totalValue'],
        ['fair_value', 'total_value'], ['fairValue', 'totalValue']),
      yieldCurveRate: fromSources(aggregates, row, ['yield_curve_rate'], ['yieldCurveRate']),
      annualYield: fromSources(aggregates, row, ['annual_yield', 'effective_annual_rate'], ['annualYield'])
    }
  }

  if (instrumentType === 'bonds') {
    return {
      ...base,
      totalFaceValue: totalOrRow(aggregates, row,
        ['total_face_value'], ['totalFaceValue'],
        ['face_value'], ['faceValue']),
      totalMarketValue: totalOrRow(aggregates, row,
        ['total_market_value', 'total_value'], ['totalMarketValue', 'totalValue'],
        ['current_price'], ['currentPrice']),
      // For multi: show mean market price; for single: the instrument price
      currentPrice: fromSources(aggregates, row, ['current_price'], ['currentPrice']),
      pricePer100: fromSources(aggregates, row, ['price_per_100'], ['pricePer100']),
      couponRate: isMulti
        ? fromSources(aggregates, null, ['avg_coupon_rate', 'weighted_avg_coupon'], ['avgCouponRate', 'weightedAvgCoupon'])
        : fromSources(aggregates, row, ['coupon_rate'], ['couponRate']),
      avgCouponRate: firstDefined(
        fromSources(aggregates, null, ['avg_coupon_rate'], ['avgCouponRate']),
        fromSources(aggregates, null, ['weighted_avg_coupon'], ['weightedAvgCoupon']),
        !isMulti ? fromSources(null, row, ['coupon_rate'], ['couponRate']) : null
      ),
      weightedAvgCoupon: fromSources(aggregates, row, ['weighted_avg_coupon'], ['weightedAvgCoupon']),
      totalAnnualIncome: totalOrRow(aggregates, row,
        ['total_coupon_income'], ['totalAnnualIncome'],
        ['annual_coupon'], ['annualCoupon']),
      annualCoupon: isMulti
        ? fromSources(aggregates, null, ['total_coupon_income', 'annual_coupon'], ['totalAnnualIncome', 'annualCoupon'])
        : fromSources(aggregates, row, ['annual_coupon'], ['annualCoupon']),
      couponPerPeriod: fromSources(aggregates, row, ['coupon_per_period', 'coupon_payment'], ['couponPerPeriod']),
      yieldToMaturity: fromSources(aggregates, row, ['yield_to_maturity', 'avg_ytm'], ['yieldToMaturity', 'avgYTM']),
      avgYTM: fromSources(aggregates, row, ['avg_ytm', 'yield_to_maturity'], ['avgYTM', 'yieldToMaturity']),
      currentYield: fromSources(aggregates, row, ['current_yield'], ['currentYield']),
      duration: fromSources(aggregates, row, ['duration', 'avg_duration'], ['duration']),
      modifiedDuration: fromSources(aggregates, row, ['modified_duration'], ['modifiedDuration']),
      accruedInterest: totalOrRow(aggregates, row,
        ['accrued_interest'], ['accruedInterest'],
        ['accrued_interest'], ['accruedInterest']),
      yearsToMaturity: fromSources(aggregates, row, ['years_to_maturity'], ['yearsToMaturity']),
      frequency: fromSources(aggregates, row, ['coupon_frequency', 'frequency'], ['frequency']),
      daysAccrued: fromSources(aggregates, row, ['days_accrued'], ['daysAccrued']),
      yieldCurveRate: fromSources(aggregates, row, ['yield_curve_rate'], ['yieldCurveRate']),
      convexity: fromSources(aggregates, row, ['convexity'], ['convexity']),
      dv01: fromSources(aggregates, row, ['dv01'], ['dv01']),
      presentValue: totalOrRow(aggregates, row,
        ['present_value'], ['presentValue'],
        ['present_value'], ['presentValue']),
      fairValue: totalOrRow(aggregates, row,
        ['fair_value', 'total_value'], ['fairValue', 'totalValue'],
        ['fair_value', 'current_price'], ['fairValue', 'currentPrice']),
      ytmInput: fromSources(aggregates, row, ['ytm_input'], ['ytmInput'])
    }
  }

  // tbills — portfolio totals / averages for multi
  return {
    ...base,
    totalFaceValue: totalOrRow(aggregates, row,
      ['total_face_value'], ['totalFaceValue'],
      ['face_value'], ['faceValue']),
    totalPurchasePrice: totalOrRow(aggregates, row,
      ['total_purchase_price'], ['totalPurchasePrice'],
      ['purchase_price'], ['purchasePrice']),
    totalDiscount: totalOrRow(aggregates, row,
      ['total_discount'], ['totalDiscount'],
      ['discount_amount'], ['discountAmount']),
    discountRate: isMulti
      ? fromSources(aggregates, null, ['avg_discount_rate', 'discount_rate'], ['avgDiscountRate', 'discountRate'])
      : fromSources(aggregates, row, ['discount_rate'], ['discountRate']),
    avgDiscountRate: fromSources(aggregates, row, ['avg_discount_rate', 'discount_rate'], ['avgDiscountRate', 'discountRate']),
    weightedAvgDiscount: fromSources(aggregates, row, ['weighted_avg_discount'], ['weightedAvgDiscount']),
    discountYield: fromSources(aggregates, row, ['discount_yield'], ['discountYield']),
    moneyMarketYield: fromSources(aggregates, row, ['money_market_yield'], ['moneyMarketYield']),
    bondEquivalentYield: fromSources(aggregates, row, ['bond_equivalent_yield'], ['bondEquivalentYield']),
    holdingPeriodYield: fromSources(aggregates, row, ['holding_period_yield'], ['holdingPeriodYield']),
    effectiveAnnualYield: fromSources(aggregates, row, ['effective_annual_yield'], ['effectiveAnnualYield']),
    avgDaysToMaturity: fromSources(aggregates, row, ['avg_days_to_maturity', 'term_days'], ['avgDaysToMaturity', 'termDays']),
    termDays: fromSources(aggregates, row, ['term_days', 'avg_days_to_maturity'], ['termDays', 'avgDaysToMaturity']),
    daysToMaturity: fromSources(aggregates, row, ['days_to_maturity', 'term_days', 'avg_days_to_maturity'], ['daysToMaturity', 'termDays']),
    purchasePrice: isMulti
      ? fromSources(aggregates, null, ['avg_investment', 'purchase_price'], ['avgInvestment', 'purchasePrice'])
      : fromSources(aggregates, row, ['purchase_price'], ['purchasePrice']),
    discountAmount: isMulti
      ? fromSources(aggregates, null, ['total_discount', 'discount_amount'], ['totalDiscount', 'discountAmount'])
      : fromSources(aggregates, row, ['discount_amount'], ['discountAmount']),
    avgInvestment: fromSources(aggregates, row, ['avg_investment'], ['avgInvestment']),
    annualizedYield: fromSources(aggregates, row, ['annualized_yield', 'bond_equivalent_yield'], ['annualizedYield', 'bondEquivalentYield']),
    yieldCurveRate: fromSources(aggregates, row, ['yield_curve_rate'], ['yieldCurveRate']),
    maturityValue: totalOrRow(aggregates, row,
      ['maturity_value', 'total_face_value'], ['maturityValue', 'totalFaceValue'],
      ['maturity_value', 'face_value'], ['maturityValue', 'faceValue']),
    presentValue: totalOrRow(aggregates, row,
      ['present_value', 'total_purchase_price'], ['presentValue', 'totalPurchasePrice'],
      ['present_value', 'purchase_price'], ['presentValue', 'purchasePrice']),
    fairValue: totalOrRow(aggregates, row,
      ['fair_value', 'total_value'], ['fairValue', 'totalValue'],
      ['fair_value', 'face_value'], ['fairValue', 'faceValue'])
  }
}

export function reconcilePortfolioTotals (aggregates, calculationRows, instrumentType) {
  const result = { ...(aggregates || {}) }
  const rows = Array.isArray(calculationRows) ? calculationRows : []
  if (!rows.length) return result
  const keyFor = key => String(key).replace(/[^a-z0-9]/gi, '').toLowerCase()
  const totalFields = instrumentType === 'money-market'
    ? {
        totalValue: ['total_value', 'maturity_value'],
        totalPrincipal: ['principal'],
        totalInterest: ['interest_earned', 'total_interest'],
        interestEarned: ['interest_earned', 'total_interest']
      }
    : instrumentType === 'tbills'
      ? {
          totalFaceValue: ['face_value'],
          totalPurchasePrice: ['purchase_price'],
          totalDiscount: ['discount_amount'],
          maturityValue: ['maturity_value', 'face_value'],
          presentValue: ['present_value', 'purchase_price'],
          fairValue: ['fair_value', 'total_value', 'face_value']
        }
      : {
          totalValue: ['current_price', 'total_value'],
          totalMarketValue: ['current_price', 'total_value'],
          totalFaceValue: ['face_value'],
          totalAnnualIncome: ['annual_coupon'],
          annualCoupon: ['annual_coupon'],
          accruedInterest: ['accrued_interest'],
          presentValue: ['present_value'],
          fairValue: ['fair_value', 'total_value', 'current_price']
        }

  for (const [aggregateKey, aliases] of Object.entries(totalFields)) {
    let found = false
    let total = 0
    for (const row of rows) {
      const entries = Object.entries(row || {})
      const valueEntry = aliases
        .map(alias => entries.find(([key]) => keyFor(key) === keyFor(alias))?.[1])
        .find(value => value !== undefined && value !== null && value !== '')
      if (valueEntry === undefined) continue
      const value = typeof valueEntry === 'number' ? valueEntry : Number(valueEntry)
      if (!Number.isFinite(value)) continue
      total += value
      found = true
    }
    result[aggregateKey] = found ? total : null
  }
  return result
}

export function hasDisplayableCalculation (agg) {
  if (!agg || typeof agg !== 'object') return false
  if (agg.status === 'error') return false
  const resultKeys = [
    'totalValue', 'totalPrincipal', 'totalInterest', 'interestEarned',
    'totalFaceValue', 'totalMarketValue', 'totalPurchasePrice', 'totalDiscount',
    'currentPrice', 'purchasePrice', 'discountAmount', 'avgRate',
    'weightedAvgRate', 'avgDiscountRate', 'avgCouponRate', 'weightedAvgCoupon',
    'avgYTM', 'annualYield', 'effectiveAnnualRate', 'avgDaysToMaturity',
    'totalAnnualIncome', 'couponPerPeriod', 'duration', 'modifiedDuration',
    'accruedInterest', 'presentValue', 'fairValue'
  ]
  return resultKeys.some(key => {
    const value = agg[key]
    return value !== null && value !== undefined && value !== '' &&
      Number.isFinite(Number(value))
  })
}

export function formatCalculationFailureMessage (calcRow, fallback = 'Calculation could not be completed.') {
  const parts = [calcRow?.error || calcRow?.warning || fallback]
  const missing = [
    ...(calcRow?.missing_fields || []),
    ...(calcRow?.missing_prerequisites || []),
    ...(calcRow?.missingPrerequisites || [])
  ].flat(Infinity).filter(Boolean)
  const invalid = calcRow?.invalid_fields || []
  if (missing.length) parts.push(`Missing: ${missing.join(', ')}`)
  if (invalid.length) {
    parts.push(`Invalid: ${invalid.map(f => (typeof f === 'object' ? `${f.field} (${f.reason})` : f)).join(', ')}`)
  }
  return parts.filter(Boolean).join(' ')
}

export function isInstrumentNameColumn (key) {
  const normalized = String(key).replace(/[^a-z0-9]/gi, '').toLowerCase()
  return ['instrument', 'instrumentname', 'name'].includes(normalized)
}

export function omitInstrumentNameColumn (rows) {
  if (!Array.isArray(rows)) return []
  return rows.map(row => Object.fromEntries(
    Object.entries(row || {}).filter(([key]) => !isInstrumentNameColumn(key))
  ))
}

const CALCULATED_FIELD_LABELS = {
  avgrate: 'Average Rate',
  weightedavgrate: 'Weighted Average Rate',
  presentvalue: 'Present Value',
  fairvalue: 'Fair Value',
  effectiveannualrate: 'Effective Annual Rate',
  effectiverate: 'Effective Rate',
  interestearned: 'Interest Earned',
  discountrate: 'Discount Rate',
  discountyield: 'Discount Yield',
  discountamount: 'Discount Amount',
  totalvalue: 'Total Value',
  totalinterest: 'Total Interest',
  totalprincipal: 'Total Principal',
  facevalue: 'Face Value',
  purchaseprice: 'Purchase Price',
  maturityvalue: 'Maturity Value',
  accruedinterest: 'Accrued Interest',
  currentyield: 'Current Yield',
  yieldtomaturity: 'Yield to Maturity',
  bondequivalentyield: 'Bond Equivalent Yield',
  investmentyield: 'Investment Yield',
  holdingperiodyield: 'Holding Period Yield',
  effectiveannualyield: 'Effective Annual Yield',
  couponperperiod: 'Coupon per Period',
  annualcoupon: 'Annual Coupon',
  duration: 'Duration',
  modifiedduration: 'Modified Duration',
  macaulayduration: 'Macaulay Duration',
  convexity: 'Convexity',
  priceper100: 'Price per 100'
}

export function resolveCalculatedInstrumentNames (
  cleanedRows,
  calcRows,
  backendNames = [],
  singleSheetName = ''
) {
  const cleaned = Array.isArray(cleanedRows) ? cleanedRows : []
  const calculations = Array.isArray(calcRows) ? calcRows : []
  const names = Array.isArray(backendNames) ? backendNames : []
  const normalize = value => String(value).replace(/[^a-z0-9]/gi, '').toLowerCase()
  const nameFromRow = row => {
    if (!row || typeof row !== 'object') return ''
    const preferredKeys = [
      'instrumentname', 'instrument', 'name', 'securityname',
      'bondname', 'tbillname', 'ticker', 'isin', 'issuer'
    ]
    const entries = Object.entries(row)
    for (const preferred of preferredKeys) {
      const entry = entries.find(([key]) => normalize(key) === preferred)
      const value = entry?.[1]
      if (value !== null && value !== undefined && String(value).trim()) {
        return String(value).trim()
      }
    }
    return ''
  }
  const singleName = String(singleSheetName || '').trim()
  const count = Math.max(calculations.length, cleaned.length, names.length)
  if (!count) return []

  return Array.from({ length: count }, (_, index) => {
    if (count === 1 && singleName) return singleName
    return nameFromRow(cleaned[index]) ||
      String(names[index] || '').trim() ||
      String(calculations[index]?.instrument_name || calculations[index]?.instrumentName || '').trim() ||
      `Instrument ${index + 1}`
  })
}

export function getYieldCurveRateForMaturity (curvePoints, maturity) {
  if (!Array.isArray(curvePoints) || !curvePoints.length || !maturity) return null
  const targetYears = (() => {
    const text = String(maturity).trim().toUpperCase()
    const value = Number.parseFloat(text)
    if (!Number.isFinite(value) || value <= 0) return null
    if (text.endsWith('M')) return value / 12
    if (text.endsWith('W')) return value / 52
    if (text.endsWith('Y')) return value
    return value
  })()
  if (targetYears === null) return null

  const isDateSeries = curvePoints.every(point => point?.isDate === true)
  const points = curvePoints
    .filter(point => point)
    .map(point => ({
      maturity: isDateSeries && (point.maturity === null || point.maturity === undefined)
        ? targetYears
        : Number(point.maturity),
      rate: Number(point.rate),
      isDate: point.isDate === true,
      date: point.date,
      x: Number(point.x)
    }))
    .filter(point =>
      Number.isFinite(point.maturity) &&
      Number.isFinite(point.rate) &&
      point.maturity > 0
    )
    .sort((a, b) => a.maturity - b.maturity)
  if (!points.length) return null

  const exactPoints = points.filter(point => Math.abs(point.maturity - targetYears) < 1e-8)
  if (exactPoints.length) {
    const datedPoints = exactPoints.filter(point => point.isDate)
    if (!datedPoints.length) return exactPoints[0].rate
    datedPoints.sort((a, b) =>
      String(a.date || a.x).localeCompare(String(b.date || b.x))
    )
    return datedPoints[datedPoints.length - 1].rate
  }

  const curvePointsByMaturity = points.filter(point => !point.isDate)
  const upperIndex = curvePointsByMaturity.findIndex(point => point.maturity > targetYears)
  if (upperIndex <= 0) return null
  const lower = curvePointsByMaturity[upperIndex - 1]
  const upper = curvePointsByMaturity[upperIndex]
  const fraction = (targetYears - lower.maturity) / (upper.maturity - lower.maturity)
  return lower.rate + (upper.rate - lower.rate) * fraction
}

export function parseMaturityToYears (maturity) {
  const text = String(maturity || '').trim().toUpperCase()
  const match = text.match(/^(\d+(?:\.\d+)?)\s*([YMW])$/)
  if (match) {
    const value = Number(match[1])
    if (value <= 0) return null
    if (match[2] === 'M') return value / 12
    if (match[2] === 'W') return value / 52
    return value
  }
  const value = Number(text)
  return Number.isFinite(value) && value > 0 ? value : null
}

export function calculatedValuesOnlyRows (rows, inputFields = [], instrumentType = '', instrumentNames = []) {
  if (!Array.isArray(rows)) return []
  const normalize = key => String(key).replace(/[^a-z0-9]/gi, '').toLowerCase()
  const excluded = new Set([
    ...inputFields.map(normalize),
    'workbook', 'worksheet', 'status', 'error', 'errors',
    'warning', 'warnings', 'calculationerrors', 'derivations',
    'displayderivations', 'missingfields', 'missingprerequisites',
    'invalidfields', 'parvalue', 'notional', 'daycountconvention',
    'country', 'valuationcurrency'
  ])
  const displayName = key => {
    const normalized = normalize(key)
    if (CALCULATED_FIELD_LABELS[normalized]) return CALCULATED_FIELD_LABELS[normalized]
    return String(key)
      .replace(/([a-z0-9])([A-Z])/g, '$1 $2')
      .replace(/[_-]+/g, ' ')
      .replace(/\s+/g, ' ')
      .trim()
      .replace(/\b\w/g, char => char.toUpperCase())
  }
  const resultRows = []
  const metricColumns = []
  const metricKeys = new Set()
  let hasCurrency = false

  rows.forEach((sourceRow, index) => {
    const row = sourceRow || {}
    const valuesByKey = new Map()
    let name = ''
    let type = ''
    let currency = ''
    for (const [key, value] of Object.entries(row)) {
      const normalized = normalize(key)
      if (['instrumentname', 'instrument', 'name'].includes(normalized)) {
        if (value !== null && value !== undefined && String(value).trim()) name ||= value
        continue
      }
      if (normalized === 'instrumenttype') {
        if (value !== null && value !== undefined && String(value).trim()) type ||= value
        continue
      }
      if (['currency', 'currencycode', 'ccy'].includes(normalized)) {
        if (value !== null && value !== undefined && String(value).trim()) currency ||= value
        hasCurrency = true
        continue
      }
      if (
        excluded.has(normalized) ||
        /^(error|warning|missing|invalid|derivation)/i.test(String(key))
      ) continue

      const label = displayName(key)
      if (!metricKeys.has(normalized)) {
        metricKeys.add(normalized)
        metricColumns.push([normalized, label])
      }
      if (
        !valuesByKey.has(normalized) &&
        value !== null && value !== undefined && value !== ''
      ) {
        valuesByKey.set(normalized, value)
      }
    }
    if (!valuesByKey.size && !name && !type) return
    const resolvedName = instrumentNames[index] !== undefined && instrumentNames[index] !== null
      ? String(instrumentNames[index]).trim()
      : ''
    resultRows.push({
      name: resolvedName || name || `Instrument ${index + 1}`,
      type: type || instrumentType || '',
      currency,
      valuesByKey
    })
  })

  const columns = [
    ['Instrument Name', row => row.name],
    ['Instrument Type', row => row.type]
  ]
  if (hasCurrency) columns.push(['Currency', row => row.currency])
  metricColumns.forEach(([key, label]) => columns.push([label, row =>
    row.valuesByKey.get(key) ?? ''
  ]))

  return resultRows.map(row => Object.fromEntries(
    columns.map(([label, getValue]) => [label, getValue(row)])
  ))
}

// Calculated-values-only rows with display columns — drops columns that are
// empty across every row (keeps 'Instrument Name'). This is the single
// pipeline used by the Calculations page and mirrored by Summary views.
export function calculatedValuesDisplayRows (rows, inputFields = [], instrumentType = '', instrumentNames = []) {
  const result = calculatedValuesOnlyRows(rows, inputFields, instrumentType, instrumentNames)
  if (!result.length) return result
  const keys = Object.keys(result[0])
  const nonEmpty = new Set()
  result.forEach(row => {
    keys.forEach(key => {
      const value = row[key]
      if (value !== '' && value !== null && value !== undefined) nonEmpty.add(key)
    })
  })
  const keep = keys.filter(key => nonEmpty.has(key) || key === 'Instrument Name')
  return result.map(row =>
    Object.fromEntries(keep.map(key => [key, row[key] ?? '']))
  )
}

/**
 * Build Excel-ready rows that reconcile cleaned valuation inputs with
 * per-instrument calculation outputs (no duplicate columns).
 */
export function buildValuationExcelRows (cleanedRows, calcRows, instrumentType) {
  const cleaned = Array.isArray(cleanedRows) ? cleanedRows : []
  const calcs = Array.isArray(calcRows) ? calcRows : []
  if (!cleaned.length && !calcs.length) return []

  const count = Math.max(cleaned.length, calcs.length)
  const rows = []
  for (let i = 0; i < count; i++) {
    const input = cleaned[i] || {}
    const calc = calcs[i] || {}
    const merged = { ...input }
    const normalizeColumn = key => String(key)
      .trim()
      .replace(/([a-z0-9])([A-Z])/g, '$1_$2')
      .replace(/[\s-]+/g, '_')
      .replace(/_+/g, '_')
      .toLowerCase()
    const seenColumns = new Set(Object.keys(merged).map(normalizeColumn))

    // Prefer calculated output keys; never overwrite a non-empty cleaned input
    // with a blank calculated field.
    for (const [k, v] of Object.entries(calc)) {
      if (v === null || v === undefined || v === '') continue
      if (['status', 'error', 'warning', 'derivations', 'display_derivations',
        'calculation_errors', 'missing_fields', 'invalid_fields',
        'missing_prerequisites'].includes(k)) continue
      const normalizedKey = normalizeColumn(k)
      if (seenColumns.has(normalizedKey)) continue
      merged[k] = v
      seenColumns.add(normalizedKey)
    }

    const instrumentName = firstDefined(
      merged['Instrument Name'], merged.instrument_name,
      calc['Instrument Name'], calc.instrument_name
    )
    delete merged.instrument_name
    if (instrumentName !== null) merged['Instrument Name'] = instrumentName
    else merged['Instrument Name'] = `Instrument ${i + 1}`

    const instrumentTypeValue = firstDefined(
      merged['Instrument Type'], merged.instrument_type,
      calc['Instrument Type'], calc.instrument_type, instrumentType
    )
    delete merged.instrument_type
    if (instrumentTypeValue !== null) merged['Instrument Type'] = instrumentTypeValue
    rows.push(merged)
  }

  // Filter out columns that are empty throughout all rows
  if (rows.length > 0) {
    const allColumns = new Set()
    rows.forEach(row => Object.keys(row).forEach(k => allColumns.add(k)))
    const nonEmptyColumns = new Set()
    allColumns.forEach(col => {
      const hasValue = rows.some(row => {
        const val = row[col]
        return val !== null && val !== undefined && val !== ''
      })
      if (hasValue) nonEmptyColumns.add(col)
    })
    // Ensure Instrument Type and Instrument Name are the first columns
    const priorityColumns = ['Instrument Type', 'Instrument Name']
    const orderedColumns = []
    priorityColumns.forEach(col => {
      if (nonEmptyColumns.has(col)) {
        orderedColumns.push(col)
        nonEmptyColumns.delete(col)
      }
    })
    // Add remaining columns in their original order
    nonEmptyColumns.forEach(col => orderedColumns.push(col))
    // Keep only non-empty columns in the correct order
    return rows.map(row => {
      const filtered = {}
      orderedColumns.forEach(col => {
        filtered[col] = row[col]
      })
      return filtered
    })
  }

  return rows
}

const GENERIC_INSTRUMENT_NAMES = new Set([
  'instrument', 'instrument-1', 'n/a', 'na', '-', 'none', 'null',
  'security', 'name', 'unnamed', ''
])

function _pickIdentityField (row, keys) {
  if (!row || typeof row !== 'object') return null
  for (const k of keys) {
    const v = row[k]
    if (v === undefined || v === null) continue
    const s = String(v).trim()
    if (s && !GENERIC_INSTRUMENT_NAMES.has(s.toLowerCase())) return s.toLowerCase()
  }
  return null
}

function _fingerprint (row) {
  if (!row || typeof row !== 'object') return null
  const named = _pickIdentityField(row, [
    'instrument_name', 'instrumentName', 'Instrument Name', 'Instrument',
    'BondName', 'TBillName', 'isin', 'ISIN', 'Ticker', 'ticker',
    'instrument_id', 'Instrument ID', 'security_id', 'Security ID',
    'cusip', 'CUSIP'
  ])
  if (named) return 'n:' + named
  const parts = [
    row.face_value ?? row.faceValue ?? row['Face Value'] ?? row.principal ?? row.Principal,
    row.interest_rate ?? row.interestRate ?? row['Interest Rate'] ??
      row.coupon_rate ?? row.couponRate ?? row['Coupon Rate'] ??
      row.discount_rate ?? row.discountRate ?? row['Discount Rate'],
    row.term_days ?? row.termDays ?? row['Term Days'] ??
      row['Days to Maturity'] ?? row.days_to_maturity,
      row.maturity_date ?? row.maturityDate ?? row['Maturity Date'],
      row.currency ?? row.Currency
  ]
  const fp = parts.map(v => (v === undefined || v === null || v === '' ? '' : String(v))).join('|')
  return fp.replace(/\|/g, '') === '' ? null : 'f:' + fp
}

/**
 * Count distinct instruments, not spreadsheet rows.
 * Duplicate rows (same name/ISIN or same amount+rate+term) collapse to one.
 */
export function countUniqueInstruments (rows) {
  if (!Array.isArray(rows) || !rows.length) return 0
  const seen = new Set()
  let unlabeled = 0
  for (const row of rows) {
    const nested = row && typeof row.calculation === 'object' ? { ...row.calculation, ...row } : row
    const fp = _fingerprint(nested)
    if (fp) seen.add(fp)
    else unlabeled += 1
  }
  return seen.size + unlabeled
}
