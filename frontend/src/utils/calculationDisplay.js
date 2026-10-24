/**
 * Maps backend calculation payloads (snake_case aggregates + per-row calcs)
 * to the camelCase keys used by InstrumentView KPI cards and summaries.
 */

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

export function buildAggregatesFromBackend (aggregates = {}, rowCalc = null, instrumentType) {
  const row = rowCalc && typeof rowCalc === 'object' ? rowCalc : null
  const count = fromSources(aggregates, row, ['instrument_count'], ['instrumentCount'])
    ?? (row ? 1 : null)

  // FIXED: avgRate is resolved for ALL instrument types via a broad fallback
  // chain so the primary rate KPI card always shows a value when one exists.
  const avgRateValue = firstDefined(
    fromSources(aggregates, row, ['avg_rate'], ['avgRate']),
    fromSources(aggregates, row, ['weighted_avg_rate'], ['weightedAvgRate']),
    fromSources(aggregates, row, ['weighted_avg_coupon'], ['weightedAvgCoupon']),
    fromSources(aggregates, row, ['avg_coupon_rate'], ['avgCouponRate']),
    fromSources(aggregates, row, ['weighted_avg_discount'], ['weightedAvgDiscount']),
    fromSources(aggregates, row, ['avg_discount_rate'], ['avgDiscountRate']),
    fromSources(aggregates, row, ['avg_ytm'], ['avgYTM'])
  )

  const base = {
    totalValue: fromSources(aggregates, row, ['total_value'], ['totalValue']),
    instrumentCount: count,
    avgRate: avgRateValue,
    status: row?.status ?? aggregates?.status ?? null,
    derivations: row?.derivations ?? aggregates?.derivations ?? null,
    error: row?.error ?? aggregates?.error ?? null,
    warning: row?.warning ?? aggregates?.warning ?? null,
    missing_fields: row?.missing_fields ?? aggregates?.missing_fields ?? null,
    invalid_fields: row?.invalid_fields ?? aggregates?.invalid_fields ?? null
  }

  if (instrumentType === 'money-market') {
    return {
      ...base,
      totalPrincipal: fromSources(aggregates, row, ['total_principal', 'principal'], ['totalPrincipal']),
      totalInterest: fromSources(aggregates, row, ['total_interest', 'interest_earned'], ['totalInterest']),
      interestEarned: fromSources(aggregates, row, ['interest_earned'], ['interestEarned']),
      interestRate: fromSources(aggregates, row, ['interest_rate'], ['interestRate']),
      effectiveYield: fromSources(aggregates, row, ['effective_yield'], ['effectiveYield']),
      effectiveAnnualRate: fromSources(aggregates, row, ['effective_annual_rate'], ['effectiveAnnualRate']),
      bondEquivalentYield: fromSources(aggregates, row, ['bond_equivalent_yield'], ['bondEquivalentYield']),
      discountYield: fromSources(aggregates, row, ['discount_yield'], ['discountYield']),
      avgDaysToMaturity: fromSources(aggregates, row, ['avg_days_to_maturity', 'term_days'], ['avgDaysToMaturity', 'termDays']),
      termDays: fromSources(aggregates, row, ['term_days'], ['termDays']),
      daysToMaturity: fromSources(aggregates, row, ['days_to_maturity', 'term_days'], ['daysToMaturity', 'termDays']),
      maturityValue: fromSources(aggregates, row, ['maturity_value', 'total_value'], ['maturityValue', 'totalValue']),
      presentValue: fromSources(aggregates, row, ['present_value'], ['presentValue']),
      fairValue: fromSources(aggregates, row, ['fair_value'], ['fairValue']),
      yieldCurveRate: fromSources(aggregates, row, ['yield_curve_rate'], ['yieldCurveRate']),
      annualYield: fromSources(aggregates, row, ['annual_yield', 'effective_annual_rate'], ['annualYield'])
    }
  }

  if (instrumentType === 'bonds') {
    return {
      ...base,
      totalFaceValue: fromSources(aggregates, row, ['total_face_value', 'face_value'], ['totalFaceValue', 'faceValue']),
      totalMarketValue: fromSources(aggregates, row, ['total_market_value', 'current_price'], ['totalMarketValue']),
      currentPrice: fromSources(aggregates, row, ['current_price'], ['currentPrice']),
      pricePer100: fromSources(aggregates, row, ['price_per_100'], ['pricePer100']),
      couponRate: fromSources(aggregates, row, ['coupon_rate'], ['couponRate']),
      avgCouponRate: fromSources(aggregates, row, ['avg_coupon_rate'], ['avgCouponRate']),
      weightedAvgCoupon: fromSources(aggregates, row, ['weighted_avg_coupon'], ['weightedAvgCoupon']),
      totalAnnualIncome: fromSources(aggregates, row, ['total_coupon_income', 'annual_coupon'], ['totalAnnualIncome']),
      annualCoupon: fromSources(aggregates, row, ['annual_coupon'], ['annualCoupon']),
      couponPerPeriod: fromSources(aggregates, row, ['coupon_per_period'], ['couponPerPeriod']),
      yieldToMaturity: fromSources(aggregates, row, ['yield_to_maturity'], ['yieldToMaturity']),
      avgYTM: fromSources(aggregates, row, ['avg_ytm'], ['avgYTM']),
      currentYield: fromSources(aggregates, row, ['current_yield'], ['currentYield']),
      duration: fromSources(aggregates, row, ['duration', 'avg_duration'], ['duration']),
      modifiedDuration: fromSources(aggregates, row, ['modified_duration'], ['modifiedDuration']),
      accruedInterest: fromSources(aggregates, row, ['accrued_interest'], ['accruedInterest']),
      yearsToMaturity: fromSources(aggregates, row, ['years_to_maturity'], ['yearsToMaturity']),
      frequency: fromSources(aggregates, row, ['coupon_frequency', 'frequency'], ['frequency']),
      daysAccrued: fromSources(aggregates, row, ['days_accrued'], ['daysAccrued']),
      yieldCurveRate: fromSources(aggregates, row, ['yield_curve_rate'], ['yieldCurveRate']),
      convexity: fromSources(aggregates, row, ['convexity'], ['convexity']),
      dv01: fromSources(aggregates, row, ['dv01'], ['dv01']),
      presentValue: fromSources(aggregates, row, ['present_value'], ['presentValue']),
      fairValue: fromSources(aggregates, row, ['fair_value'], ['fairValue']),
      ytmInput: fromSources(aggregates, row, ['ytm_input'], ['ytmInput'])
    }
  }

  // tbills
  return {
    ...base,
    totalFaceValue: fromSources(aggregates, row, ['total_face_value', 'face_value'], ['totalFaceValue', 'faceValue']),
    totalPurchasePrice: fromSources(aggregates, row, ['total_purchase_price', 'purchase_price'], ['totalPurchasePrice', 'purchasePrice']),
    totalDiscount: fromSources(aggregates, row, ['total_discount', 'discount_amount'], ['totalDiscount']),
    discountRate: fromSources(aggregates, row, ['discount_rate'], ['discountRate']),
    avgDiscountRate: fromSources(aggregates, row, ['avg_discount_rate'], ['avgDiscountRate']),
    weightedAvgDiscount: fromSources(aggregates, row, ['weighted_avg_discount'], ['weightedAvgDiscount']),
    discountYield: fromSources(aggregates, row, ['discount_yield'], ['discountYield']),
    moneyMarketYield: fromSources(aggregates, row, ['money_market_yield'], ['moneyMarketYield']),
    bondEquivalentYield: fromSources(aggregates, row, ['bond_equivalent_yield'], ['bondEquivalentYield']),
    holdingPeriodYield: fromSources(aggregates, row, ['holding_period_yield'], ['holdingPeriodYield']),
    effectiveAnnualYield: fromSources(aggregates, row, ['effective_annual_yield'], ['effectiveAnnualYield']),
    avgDaysToMaturity: fromSources(aggregates, row, ['avg_days_to_maturity', 'term_days'], ['avgDaysToMaturity', 'termDays']),
    termDays: fromSources(aggregates, row, ['term_days'], ['termDays']),
    daysToMaturity: fromSources(aggregates, row, ['days_to_maturity', 'term_days'], ['daysToMaturity', 'termDays']),
    purchasePrice: fromSources(aggregates, row, ['purchase_price'], ['purchasePrice']),
    discountAmount: fromSources(aggregates, row, ['discount_amount'], ['discountAmount']),
    avgInvestment: fromSources(aggregates, row, ['avg_investment'], ['avgInvestment']),
    annualizedYield: fromSources(aggregates, row, ['annualized_yield'], ['annualizedYield']),
    yieldCurveRate: fromSources(aggregates, row, ['yield_curve_rate'], ['yieldCurveRate']),
    maturityValue: fromSources(aggregates, row, ['maturity_value'], ['maturityValue']),
    presentValue: fromSources(aggregates, row, ['present_value'], ['presentValue']),
    fairValue: fromSources(aggregates, row, ['fair_value'], ['fairValue'])
  }
}

export function hasDisplayableCalculation (agg) {
  if (!agg || typeof agg !== 'object') return false
  if (agg.status === 'error') return false
  const tv = agg.totalValue
  if (tv !== null && tv !== undefined && !Number.isNaN(Number(tv))) return true
  const cp = agg.currentPrice ?? agg.totalMarketValue ?? agg.totalPurchasePrice
  if (cp !== null && cp !== undefined && !Number.isNaN(Number(cp))) return true
  return false
}

export function formatCalculationFailureMessage (calcRow, fallback = 'Calculation could not be completed.') {
  const parts = [calcRow?.error || calcRow?.warning || fallback]
  const missing = calcRow?.missing_fields || []
  const invalid = calcRow?.invalid_fields || []
  if (missing.length) parts.push(`Missing: ${missing.join(', ')}`)
  if (invalid.length) {
    parts.push(`Invalid: ${invalid.map(f => (typeof f === 'object' ? `${f.field} (${f.reason})` : f)).join(', ')}`)
  }
  return parts.filter(Boolean).join(' ')
}