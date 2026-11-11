// Canonical calculation-input requirements per instrument type.
// Mirrors backend/pages/calculations_details.py validate_row_for_instrument:
// each group is satisfied when ANY alias column exists with a plausible value.
// Cleaning validation and pre-calculation checks both use this registry so
// frontend and backend can never disagree about what is required.

export const normCalcKey = k => String(k).toLowerCase().replace(/[\s_\-]/g, '')

// anyOf entries are compared against normCalcKey(columnName).
export const CALC_REQUIRED_GROUPS = {
  'bonds': [
    { id: 'face_value', label: 'Face Value / Principal',
      anyOf: ['facevalue', 'principal', 'parvalue', 'notional', 'amount'] },
    { id: 'coupon_rate', label: 'Coupon Rate',
      anyOf: ['couponrate', 'interestrate', 'coupon', 'rate'] },
    { id: 'price_or_yield', label: 'Price or Yield to Maturity',
      anyOf: ['price', 'purchaseprice', 'currentprice', 'marketvalue',
              'presentvalue', 'fairvalue', 'yield', 'yieldtomaturity'] },
    { id: 'tenor', label: 'Term (years/days or Valuation+Maturity dates)',
      anyOf: ['yearstomaturity', 'daystomaturity', 'termdays', 'tenor',
              'days', 'valuationdate', 'maturitydate', 'issuedate', 'settlementdate'] },
    { id: 'coupon_frequency', label: 'Coupon Frequency',
      anyOf: ['couponfrequency', 'frequency', 'paymentfrequency',
              'compoundingfrequency', 'paymentsperyear'] },
    { id: 'day_count', label: 'Day Count Convention (for accrued interest)',
      anyOf: ['daycountconvention', 'daycount', 'accrualbasis'], conditional: true },
  ],
  'money-market': [
    { id: 'principal', label: 'Principal / Face Value / Amount',
      anyOf: ['principal', 'facevalue', 'amount', 'notional', 'parvalue'] },
    { id: 'rate_or_price', label: 'Interest/Discount Rate or Purchase Price',
      anyOf: ['interestrate', 'rate', 'couponrate', 'discountrate',
              'yield', 'purchaseprice', 'currentprice', 'price'] },
    { id: 'tenor', label: 'Term (days or Valuation+Maturity dates)',
      anyOf: ['termdays', 'daystomaturity', 'days', 'tenor', 'years', 'tenure',
              'valuationdate', 'maturitydate', 'issuedate', 'settlementdate', 'auctiondate'] },
  ],
  'tbills': [
    { id: 'face_value', label: 'Face Value / Principal',
      anyOf: ['facevalue', 'principal', 'parvalue', 'amount', 'notional'] },
    { id: 'rate_or_price', label: 'Discount Rate / Yield / Purchase Price',
      anyOf: ['discountrate', 'yield', 'yieldtomaturity', 'investoryield',
              'purchaseprice', 'currentprice', 'price', 'interestrate', 'rate'] },
    { id: 'tenor', label: 'Term (days or Valuation+Maturity dates)',
      anyOf: ['termdays', 'daystomaturity', 'days', 'tenor', 'tenure',
              'valuationdate', 'maturitydate', 'issuedate', 'settlementdate', 'auctiondate'] },
  ],
}

const TYPE_ALIASES = {
  'money market': 'money-market', 'moneymarket': 'money-market',
  'money-market': 'money-market', 'mm': 'money-market',
  'tbill': 'tbills', 'tbills': 'tbills', 't-bill': 'tbills',
  't-bills': 'tbills', 'treasury bill': 'tbills', 'treasury bills': 'tbills',
  'treasurybills': 'tbills',
  'bond': 'bonds', 'bonds': 'bonds',
}

export function registryType(instrumentType) {
  const raw = String(instrumentType || '').toLowerCase()
  const n = normCalcKey(instrumentType || '')
  if (TYPE_ALIASES[n] || TYPE_ALIASES[raw]) return TYPE_ALIASES[n] || TYPE_ALIASES[raw]
  // Substring fallback for display names like "Treasury Bills (tbills)".
  if (/t.?bill|treasury/.test(n)) return 'tbills'
  if (/money|moneymarket|^mm$/.test(n)) return 'money-market'
  return 'bonds'
}

function plausibleValue(v) {
  if (v === null || v === undefined) return false
  const s = String(v).trim()
  if (s === '') return false
  // Reject label-like text for value checks (e.g. "Maturity Date" as a value)
  if (/^[A-Z][A-Za-z]+( [A-Z][A-Za-z]+)*$/.test(s) && s.length > 3 &&
      /(date|value|rate|name|type|total|balance|frequency|convention)/i.test(s)) return false
  return true
}

// Validate ONE instrument row against required groups.
// Returns { missing: [{id,label}], satisfied: [ids] } — never mutates row.
export function validateCalcRow(row, instrumentType) {
  const groups = CALC_REQUIRED_GROUPS[registryType(instrumentType)] || []
  const normCols = Object.keys(row || {}).map(k => ({ raw: k, n: normCalcKey(k) }))
  const missing = []
  const satisfied = []
  for (const g of groups) {
    if (g.conditional) { satisfied.push(g.id); continue } // backend decides conditionally
    const hit = normCols.find(c => g.anyOf.includes(c.n) && plausibleValue(row[c.raw]))
    if (hit) satisfied.push(g.id)
    else missing.push({ id: g.id, label: g.label })
  }
  return { missing, satisfied }
}

// Validate every row independently; returns per-row results.
export function validateCalcRows(rows, instrumentType) {
  return (rows || []).map((row, i) => ({
    rowIndex: i,
    name: row?.instrument_name || row?.InstrumentName || row?.instrumentName || row?.name || `row ${i + 1}`,
    ...validateCalcRow(row, instrumentType),
  }))
}
