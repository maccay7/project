// Instrument field mappings and display configurations
// Shared across Money Market, T-Bills, and Bonds

export const FIELD_MAPPINGS = {
  'money-market': {
    'discount_yield': 'Discount Yield',
    'discountYield': 'Discount Yield',
    'effective_yield': 'Effective Yield',
    'effectiveYield': 'Effective Yield',
    'interest_earned': 'Interest Earned',
    'interestEarned': 'Interest Earned',
    'interest_rate': 'Interest Rate',
    'interestRate': 'Interest Rate',
    'principal': 'Principal',
    'term_days': 'Days to Maturity',
    'termDays': 'Days to Maturity',
    'days_to_maturity': 'Days to Maturity',
    'daysToMaturity': 'Days to Maturity',
    'total_value': 'Total Value',
    'totalValue': 'Total Value',
    'yield_curve_rate': 'Yield Curve Rate',
    'yieldCurveRate': 'Yield Curve Rate',
    'valuation_date': 'Valuation Date',
    'valuationDate': 'Valuation Date',
    'maturity_date': 'Maturity Date',
    'maturityDate': 'Maturity Date',
    'issue_date': 'Issue Date',
    'issueDate': 'Issue Date',
    'settlement_date': 'Settlement Date',
    'settlementDate': 'Settlement Date',
    'instrument_name': 'Instrument Name',
    'instrumentName': 'Instrument Name',
    'instrument_type': 'Instrument Type',
    'instrumentType': 'Instrument Type',
    'status': 'Status'
  },
  'bonds': {
    'clean_price': 'Clean Price',
    'dirty_price': 'Dirty Price',
    'current_price': 'Current Price',
    'currentPrice': 'Current Price',
    'price': 'Price',
    'coupon_rate': 'Coupon Rate',
    'couponRate': 'Coupon Rate',
    'annual_coupon': 'Annual Coupon',
    'annualCoupon': 'Annual Coupon',
    'coupon_per_period': 'Coupon per Period',
    'couponPerPeriod': 'Coupon per Period',
    'yield_to_maturity': 'Yield to Maturity',
    'yieldToMaturity': 'Yield to Maturity',
    'current_yield': 'Current Yield',
    'currentYield': 'Current Yield',
    'duration': 'Duration',
    'macaulay_duration': 'Macaulay Duration',
    'macaulayDuration': 'Macaulay Duration',
    'modified_duration': 'Modified Duration',
    'modifiedDuration': 'Modified Duration',
    'convexity': 'Convexity',
    'accrued_interest': 'Accrued Interest',
    'accruedInterest': 'Accrued Interest',
    'face_value': 'Face Value',
    'faceValue': 'Face Value',
    'years_to_maturity': 'Years to Maturity',
    'yearsToMaturity': 'Years to Maturity',
    'price_per_100': 'Price per 100',
    'pricePer100': 'Price per 100',
    'valuation_date': 'Valuation Date',
    'valuationDate': 'Valuation Date',
    'maturity_date': 'Maturity Date',
    'maturityDate': 'Maturity Date',
    'issue_date': 'Issue Date',
    'issueDate': 'Issue Date',
    'settlement_date': 'Settlement Date',
    'settlementDate': 'Settlement Date',
    'last_coupon_date': 'Last Coupon Date',
    'lastCouponDate': 'Last Coupon Date',
    'days_accrued': 'Days Accrued',
    'daysAccrued': 'Days Accrued',
    'coupon_frequency': 'Coupon Frequency',
    'couponFrequency': 'Coupon Frequency',
    'frequency': 'Frequency',
    'total_value': 'Total Value',
    'totalValue': 'Total Value',
    'yield_curve_rate': 'Yield Curve Rate',
    'yieldCurveRate': 'Yield Curve Rate',
    'instrument_name': 'Instrument Name',
    'instrumentName': 'Instrument Name',
    'instrument_type': 'Instrument Type',
    'instrumentType': 'Instrument Type',
    'status': 'Status'
  },
  'tbills': {
    'discount_rate': 'Discount Rate',
    'discountRate': 'Discount Rate',
    'discount_yield': 'Discount Yield',
    'discountYield': 'Discount Yield',
    'investment_yield': 'Investment Yield',
    'investmentYield': 'Investment Yield',
    'bond_equivalent_yield': 'Bond Equivalent Yield',
    'bondEquivalentYield': 'Bond Equivalent Yield',
    'money_market_yield': 'Money Market Yield',
    'moneyMarketYield': 'Money Market Yield',
    'holding_period_yield': 'Holding Period Yield',
    'holdingPeriodYield': 'Holding Period Yield',
    'effective_annual_yield': 'Effective Annual Yield',
    'effectiveAnnualYield': 'Effective Annual Yield',
    'effective_annual_rate': 'Effective Annual Rate',
    'effectiveAnnualRate': 'Effective Annual Rate',
    'present_value': 'Present Value',
    'presentValue': 'Present Value',
    'fair_value': 'Fair Value',
    'fairValue': 'Fair Value',
    'discount_amount': 'Discount Amount',
    'discountAmount': 'Discount Amount',
    'purchase_price': 'Purchase Price',
    'purchasePrice': 'Purchase Price',
    'carrying_value': 'Carrying Value',
    'carryingValue': 'Carrying Value',
    'maturity_value': 'Maturity Value',
    'maturityValue': 'Maturity Value',
    'face_value': 'Face Value',
    'faceValue': 'Face Value',
    'term_days': 'Days to Maturity',
    'termDays': 'Days to Maturity',
    'days_to_maturity': 'Days to Maturity',
    'daysToMaturity': 'Days to Maturity',
    'total_value': 'Total Value',
    'totalValue': 'Total Value',
    'yield_curve_rate': 'Yield Curve Rate',
    'yieldCurveRate': 'Yield Curve Rate',
    'valuation_date': 'Valuation Date',
    'valuationDate': 'Valuation Date',
    'maturity_date': 'Maturity Date',
    'maturityDate': 'Maturity Date',
    'issue_date': 'Issue Date',
    'issueDate': 'Issue Date',
    'settlement_date': 'Settlement Date',
    'settlementDate': 'Settlement Date',
    'auction_date': 'Auction Date',
    'auctionDate': 'Auction Date',
    'instrument_name': 'Instrument Name',
    'instrumentName': 'Instrument Name',
    'instrument_type': 'Instrument Type',
    'instrumentType': 'Instrument Type',
    'status': 'Status'
  }
}

export const INPUT_FIELDS = {
  'money-market': [
    'principal', 'interest_rate', 'days_to_maturity', 'issue_date', 'maturity_date',
    'valuation_date', 'settlement_date', 'day_count_convention', 'currency',
    'instrument_name', 'instrument_type', 'status'
  ],
  'bonds': [
    'face_value', 'coupon_rate', 'years_to_maturity', 'issue_date', 'maturity_date',
    'valuation_date', 'settlement_date', 'last_coupon_date', 'coupon_frequency',
    'day_count_convention', 'currency', 'instrument_name', 'instrument_type', 'status'
  ],
  'tbills': [
    'face_value', 'discount_rate', 'days_to_maturity', 'issue_date', 'maturity_date',
    'valuation_date', 'settlement_date', 'auction_date', 'day_count_convention',
    'currency', 'instrument_name', 'instrument_type', 'status'
  ]
}

export const SEMANTIC_FIELD_GROUPS = {
  principal: ['principal', 'face_value', 'amount', 'notional', 'par_value', 'investment'],
  rate: ['interest_rate', 'coupon_rate', 'discount_rate', 'yield', 'yield_to_maturity', 'ytm'],
  maturity: ['maturity_date', 'maturity', 'end_date', 'expiry_date'],
  issue: ['issue_date', 'issue', 'start_date', 'effective_date'],
  valuation: ['valuation_date', 'valuation', 'as_of_date', 'date'],
  settlement: ['settlement_date', 'settlement', 'trade_date', 'trade'],
  coupon: ['coupon_rate', 'coupon', 'interest_rate'],
  frequency: ['coupon_frequency', 'frequency', 'payment_frequency'],
  currency: ['currency', 'ccy', 'currency_code'],
  days: ['days_to_maturity', 'term_days', 'duration_days', 'tenor_days'],
  years: ['years_to_maturity', 'term_years', 'duration_years', 'tenor_years'],
  price: ['price', 'purchase_price', 'current_price', 'clean_price', 'dirty_price'],
  instrument: ['instrument_name', 'name', 'security', 'bond_name', 'tbill_name', 'description'],
  type: ['instrument_type', 'type', 'asset_type', 'security_type']
}

export function formatInstrumentTypeLabel(type) {
  if (type === 'money-market') return 'Money Market (money-market)'
  if (type === 'tbills') return 'Treasury Bills (tbills)'
  if (type === 'bonds') return 'Bonds (bonds)'
  return type || 'Unknown'
}

export function normalizeKeyForMatch(key) {
  if (!key) return ''
  return String(key).toLowerCase().replace(/[\s_-]/g, '').replace(/[^\w]/g, '')
}

export function findSemanticType(key) {
  const normalized = normalizeKeyForMatch(key)
  for (const [type, patterns] of Object.entries(SEMANTIC_FIELD_GROUPS)) {
    for (const pattern of patterns) {
      const patternNorm = normalizeKeyForMatch(pattern)
      if (normalized.includes(patternNorm) || patternNorm.includes(normalized)) {
        return type
      }
    }
  }
  return null
}

export function isSemanticMatch(detectedKey, targetField, semanticType) {
  const detectedNorm = normalizeKeyForMatch(detectedKey)
  const targetNorm = normalizeKeyForMatch(targetField)
  
  // Direct match
  if (detectedNorm === targetNorm) return true
  
  // Semantic match if same type
  if (semanticType) {
    const detectedSemantic = findSemanticType(detectedKey)
    const targetSemantic = findSemanticType(targetField)
    if (detectedSemantic && targetSemantic && detectedSemantic === targetSemantic) {
      return true
    }
  }
  
  return false
}

export function mapBackendFieldsToDisplayNames(row, instrumentType) {
  const mappings = FIELD_MAPPINGS[instrumentType] || {}
  const mapped = {}
  for (const [key, value] of Object.entries(row)) {
    const displayKey = mappings[key] || key
    mapped[displayKey] = value
  }
  return mapped
}

export function filterToCalculatedFields(row, instrumentType) {
  const inputFields = INPUT_FIELDS[instrumentType] || []
  const inputFieldNorms = new Set(inputFields.map(f => normalizeKeyForMatch(f)))
  const calculated = {}
  for (const [key, value] of Object.entries(row)) {
    const keyNorm = normalizeKeyForMatch(key)
    if (!inputFieldNorms.has(keyNorm)) {
      calculated[key] = value
    }
  }
  return calculated
}

export function getCalculatedInstrumentNames(calcRows, backendNames = []) {
  const names = new Set()
  for (const row of calcRows) {
    const name = row['Instrument Name'] || row.instrument_name || row['TBillName'] || row.tbills_name
    if (name) names.add(name)
  }
  return Array.from(names)
}
