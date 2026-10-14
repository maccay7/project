import * as XLSX from 'xlsx'

// ============================================================================
// Currency constants
// ============================================================================
const CURRENCY_SYMBOLS = {
  USD: ['$', 'US$', 'USD$'],
  EUR: ['€'],
  GBP: ['£'],
  JPY: ['¥', 'JP¥'],
  CNY: ['¥', 'CN¥', 'RMB', '元'],
  INR: ['₹'],
  ZAR: ['R'],
  ZWL: ['Z$', 'ZWL$'],
  ZWG: ['ZWG$', 'ZiG'],
  AUD: ['A$', 'AU$'],
  CAD: ['C$', 'CA$'],
  CHF: ['CHF', 'Fr'],
  NZD: ['NZ$'],
  HKD: ['HK$'],
  SGD: ['S$'],
  ZMW: ['ZK'],
  BWP: ['P'],
  NGN: ['₦'],
  KES: ['KSh'],
  EGP: ['E£'],
  AED: ['د.إ'],
  SAR: ['﷼'],
  TRY: ['₺'],
  RUB: ['₽'],
  BRL: ['R$'],
  KRW: ['₩'],
  THB: ['฿'],
  VND: ['₫'],
  PHP: ['₱'],
  IDR: ['Rp'],
  MYR: ['RM']
}

const CURRENCY_NAMES = {
  USD: ['dollar', 'us dollar', 'united states dollar', 'american dollar'],
  EUR: ['euro', 'euros'],
  GBP: ['pound', 'pounds', 'british pound', 'sterling'],
  JPY: ['yen', 'japanese yen'],
  CNY: ['yuan', 'renminbi', 'chinese yuan'],
  INR: ['rupee', 'indian rupee', 'rupees'],
  ZAR: ['rand', 'south african rand'],
  ZWL: ['zimbabwe dollar', 'zimbabwean dollar'],
  ZWG: ['zimbabwe gold', 'zig'],
  AUD: ['australian dollar'],
  CAD: ['canadian dollar'],
  CHF: ['swiss franc', 'franc'],
  NZD: ['new zealand dollar'],
  HKD: ['hong kong dollar'],
  SGD: ['singapore dollar'],
  NGN: ['naira'],
  KES: ['kenyan shilling', 'shilling'],
  BWP: ['pula'],
  EGP: ['egyptian pound'],
  AED: ['dirham', 'uae dirham'],
  SAR: ['riyal', 'saudi riyal'],
  TRY: ['lira', 'turkish lira'],
  RUB: ['ruble', 'russian ruble'],
  BRL: ['real', 'brazilian real'],
  KRW: ['won', 'korean won'],
  THB: ['baht', 'thai baht'],
  VND: ['dong', 'vietnamese dong'],
  PHP: ['peso', 'philippine peso'],
  IDR: ['rupiah', 'indonesian rupiah'],
  MYR: ['ringgit', 'malaysian ringgit']
}

const KNOWN_ISO_CODES = new Set([
  'USD','EUR','GBP','JPY','CNY','INR','AUD','CAD','CHF','MXN',
  'BRL','KRW','RUB','ZAR','TRY','SGD','HKD','NOK','SEK','DKK',
  'PLN','THB','IDR','MYR','PHP','VND','CZK','HUF','RON','ILS',
  'CLP','COP','PEN','ARS','UYU','BOB','PYG','CRC','GTQ','HNL',
  'NIO','PAB','DOP','JMD','TTD','BBD','XCD','BZD','GYD','SRD',
  'AWG','ANG','CUP','HTG','XAF','XOF','XPF','CDF','BIF','DJF',
  'ERN','ETB','KES','MGF','MWK','MZN','RWF','SOS','TZS','UGX',
  'ZMW','BWP','SZL','LSL','NAD','AOA','BGN','HRK','CYP','EEK',
  'LTL','LVL','MKD','RSD','SKK','SIT','UAH','ALL','BYN','MDL',
  'AMD','AZN','GEL','KZT','KGS','TJS','TMT','UZS','AFN','IRR',
  'IQD','JOD','KWD','LBP','OMR','QAR','SAR','SYP','AED','YER',
  'BHD','DZD','EGP','LYD','MAD','MRU','SDG','TND','MVR','NPR',
  'PKR','LKR','BDT','BTN','MMK','BND','KHR','LAK','MOP','TWD',
  'MNT','KPW','FJD','PGK','SBD','VUV','WST','NZD','TOP','ISK',
  'SVC','VEF','ZWL','ZWG'
])

const NON_CURRENCY_WORDS = new Set([
  'AND','BUT','FOR','NOR','NOT','NOW','OUT','PUT','SET','SHE','THE',
  'TWO','USE','VIA','YES','YOU','ALL','ANY','ARE','BIG','CAN','DAY',
  'END','EYE','FEW','GET','HAS','HER','HIS','HOW','ITS','LET','MAN',
  'MAY','NEW','OFF','OLD','ONE','OUR','OWN','RUN','SAW','SAY','SEE',
  'SIR','SIT','SIX','SON','SUN','TEN','TOO','TRY','WAR','WAY','WHO',
  'WHY','WIN','WON','YET'
])

// ============================================================================
// Instrument Schema - Source of Truth for Required Fields
// ============================================================================
const INSTRUMENT_SCHEMA = {
  'Money Market': {
    required: ['principal', 'interest_rate'],
    valueType: {
      principal: 'currency',
      interest_rate: 'percentage'
    }
  },
  'T-Bills': {
    required: ['face_value', 'discount_rate'],
    valueType: {
      face_value: 'currency',
      discount_rate: 'percentage'
    }
  },
  'Bonds': {
    required: ['face_value', 'coupon_rate', 'yield_to_maturity'],
    valueType: {
      face_value: 'currency',
      coupon_rate: 'percentage',
      yield_to_maturity: 'percentage'
    }
  }
}

// ============================================================================
// Backend SPECIFIC_ALIASES - Source of Truth for Field Mapping
// Must match backend/pages/calculations_details.py exactly
// ============================================================================
const SPECIFIC_ALIASES = {
  "principal": [
    "principal", "principle", "principal amount", "principle amount",
    "face value", "facevalue", "face_value", "face amount",
    "par value", "parvalue", "par amount",
    "nominal", "nominal amount", "nominal value",
    "notional", "notional amount",
    "investment amount", "initial investment", "initial amount",
    "starting balance", "opening balance", "deposit amount",
    "capital", "total cost", "purchase cost", "cost", "amount", "value",
    "outstanding principal", "current principal",
  ],
  "interest_rate": [
    "interest rate", "interestrate", "interest_rate",
    "annual rate", "annual interest rate",
    "nominal rate", "stated rate", "effective rate",
    "apr", "coupon", "coupon rate",
    "rate %", "rate%", "rate",
  ],
  "days_to_maturity": [
    "days to maturity", "daystomaturity", "days_to_maturity",
    "maturity days", "duration days", "contract days",
    "term days", "term_days", "termdays", "term in days",
    "tenor", "term", "days", "period",
  ],
  "issue_date": [
    "issue date", "issuedate", "issue_date",
    "start date", "startdate", "start_date",
    "effective date", "effectivedate", "effective_date",
    "settlement date", "settlementdate", "settlement_date",
    "origination date", "value date", "valuedate", "value_date",
    "trade date", "tradedate", "trade_date",
  ],
  "maturity_date": [
    "maturity date", "maturitydate", "maturity_date",
    "end date", "enddate", "end_date",
    "due date", "duedate", "due_date",
    "redemption date", "redemptiondate", "redemption_date",
    "expiry date", "expirydate", "expiry_date",
    "termination date",
  ],
  "valuation_date": [
    "valuation", "valuation date", "valuationdate", "valuation_date",
    "portfolio date", "portfoliodate", "portfolio_date",
    "report date", "reportdate", "report_date",
    "as of date", "asofdate", "as_of_date",
    "date pfolio", "datepfolio",
  ],
  "purchase_price": [
    "purchase price", "purchaseprice", "purchase_price",
    "buy price", "buyprice", "buy_price",
    "acquisition price", "entry price",
    "price paid", "pricepaid", "price_paid",
    "issue price", "issueprice", "issue_price",
    "price",
  ],
  "current_price": ["current price", "currentprice", "current_price"],
  "settlement_amount": [
    "settlement amount", "settlementamount",
    "settlement value", "cash flow", "proceeds",
  ],
  "market_value": [
    "market value", "marketvalue", "market_value",
    "current value", "currentvalue",
    "fair value", "fairvalue",
    "present value", "presentvalue",
    "total value", "totalvalue",
  ],
  "portfolio_name": ["portfolio name", "pfolio name", "portfolio"],
  "security": [
    "security", "security id", "securityid",
    "instrument id", "instrumentid", "isin", "ticker",
  ],
  "instrument_name": [
    "parent company name", "parent company",
    "issuer", "company", "entity",
    "short name", "shortname",
    "instrument name", "instrumentname", "instrument_name",
    "instrument", "description", "counterparty",
    "bond name", "bondname", "bond_name", "bond",
    "t-bill name", "tbill name", "tbillname", "tbill_name",
    "tbill", "t-bill", "treasury bill name",
    "security name", "securityname",
    "name", "ticker", "symbol",
  ],
  "classification": ["classification", "category", "asset class", "type"],
  "currency": ["currency", "ccy", "iso code", "currency code"],
  "country": ["country", "jurisdiction", "domicile"],
  "sector": ["sector", "industry", "industry group"],
  "rating": ["credit rating", "rating", "moody", "s&p", "fitch"],
  "face_value": [
    "face value", "facevalue", "face_value",
    "par value", "parvalue", "par_value",
    "redemption value", "redemptionvalue", "redemption_value",
    "maturity value", "maturityvalue", "maturity_value",
    "nominal value", "nominalvalue", "nominal_value",
  ],
  "discount_rate": [
    "discount rate", "discountrate", "discount_rate",
    "bank discount", "bankdiscount",
    "discount yield", "discountyield",
    "t-bill rate", "tbillrate",
    "auction rate", "auctionrate",
    "discount",
  ],
  "term_days": [
    "term days", "termdays", "term_days",
    "days to maturity", "daystomaturity",
    "maturity days", "maturitydays",
    "tenor", "term", "days",
  ],
  "auction_date": ["auction date", "auctiondate", "issue date", "settlement date"],
  "coupon_rate": [
    "coupon rate", "couponrate", "coupon_rate",
    "coupon", "annual coupon", "annualcoupon",
    "fixed rate", "fixedrate",
    "nominal rate", "nominalrate",
    "stated rate", "statedrate",
    "interest rate", "interestrate",
  ],
  "coupon_frequency": [
    "coupon frequency", "couponfrequency", "coupon_frequency",
    "payment frequency", "paymentfrequency",
    "frequency", "coupon period", "payments per year",
  ],
  "years_to_maturity": [
    "years to maturity", "yearstomaturity", "years_to_maturity",
    "maturity years", "maturityyears",
    "term years", "termyears",
    "duration years", "durationyears",
    "time to maturity", "timetomaturity",
    "years", "year",
  ],
  "yield": [
    "yield to maturity", "yieldtomaturity", "yield_to_maturity",
    "ytm", "market yield", "marketyield",
    "required return", "requiredreturn",
    "redemption yield", "redemptionyield",
    "yield",
  ],
  "call_date": ["call date", "calldate", "first call date"],
  "call_price": ["call price", "callprice", "call premium", "redemption price"],
  "put_date": ["put date", "putdate", "puttable date"],
  "put_price": ["put price", "putprice", "put premium"],
}

// ============================================================================
// Semantic Field Definitions - Meaning-based, not name-based
// ============================================================================
const SEMANTIC_FIELD_DEFINITIONS = {
  // ===== AMOUNTS =====
  principal: {
    semanticConcept: 'monetary principal amount',
    valueTypes: ['currency'],
    keywords: SPECIFIC_ALIASES.principal,
    units: ['$', '€', '£', '¥', 'R', 'USD', 'EUR', 'GBP', 'ZAR', 'BWP', 'ZWG'],
    contextPatterns: ['value', 'amount', 'principal', 'face', 'par'],
    minValue: 1000,
    typicalRange: [1000, 1000000000]
  },
  face_value: {
    semanticConcept: 'face value of security',
    valueTypes: ['currency'],
    keywords: SPECIFIC_ALIASES.face_value,
    units: ['$', '€', '£', '¥', 'R', 'USD', 'EUR', 'GBP', 'ZAR', 'BWP', 'ZWG'],
    contextPatterns: ['face', 'par', 'redemption', 'maturity value'],
    minValue: 1000,
    typicalRange: [1000, 1000000000]
  },
  price: {
    semanticConcept: 'price of security',
    valueTypes: ['currency', 'percentage'],
    keywords: SPECIFIC_ALIASES.purchase_price,
    units: ['$', '€', '£', '¥', 'R', 'USD', 'EUR', 'GBP', 'ZAR', '%'],
    contextPatterns: ['price', 'market price', 'clean price', 'dirty price'],
    minValue: 0,
    typicalRange: [0, 1000000000]
  },
  accrued_interest: {
    semanticConcept: 'accrued interest',
    valueTypes: ['currency'],
    keywords: ['accrued', 'interest', 'accrual'],
    units: ['$', '€', '£', '¥', 'R', 'USD', 'EUR', 'GBP', 'ZAR', 'BWP', 'ZWG'],
    contextPatterns: ['accrued interest', 'interest accrued'],
    minValue: 0,
    typicalRange: [0, 100000000]
  },
  present_value: {
    semanticConcept: 'present value',
    valueTypes: ['currency'],
    keywords: ['present', 'pv', 'current'],
    units: ['$', '€', '£', '¥', 'R', 'USD', 'EUR', 'GBP', 'ZAR', 'BWP', 'ZWG'],
    contextPatterns: ['present value', 'pv', 'current value'],
    minValue: 0,
    typicalRange: [0, 1000000000]
  },
  carrying_value: {
    semanticConcept: 'carrying value',
    valueTypes: ['currency'],
    keywords: ['carrying', 'book', 'balance'],
    units: ['$', '€', '£', '¥', 'R', 'USD', 'EUR', 'GBP', 'ZAR', 'BWP', 'ZWG'],
    contextPatterns: ['carrying value', 'book value', 'balance'],
    minValue: 0,
    typicalRange: [0, 1000000000]
  },
  fair_value: {
    semanticConcept: 'fair value',
    valueTypes: ['currency'],
    keywords: ['fair', 'market'],
    units: ['$', '€', '£', '¥', 'R', 'USD', 'EUR', 'GBP', 'ZAR', 'BWP', 'ZWG'],
    contextPatterns: ['fair value', 'market value'],
    minValue: 0,
    typicalRange: [0, 1000000000]
  },

  // ===== RATES =====
  interest_rate: {
    semanticConcept: 'interest rate for money market',
    valueTypes: ['percentage'],
    keywords: SPECIFIC_ALIASES.interest_rate,
    excludeKeywords: ['coupon', 'yield', 'discount', 'spread', 'margin'],
    units: ['%', 'percent', 'bps', 'basis points'],
    contextPatterns: ['interest rate', 'annual rate'],
    typicalRange: [0, 100]
  },
  discount_rate: {
    semanticConcept: 'discount rate for t-bills',
    valueTypes: ['percentage'],
    keywords: SPECIFIC_ALIASES.discount_rate,
    excludeKeywords: ['yield', 'coupon', 'interest', 'spread'],
    units: ['%', 'percent', 'bps'],
    contextPatterns: ['discount rate', 'discount yield'],
    typicalRange: [0, 100]
  },
  coupon_rate: {
    semanticConcept: 'coupon rate for bonds',
    valueTypes: ['percentage'],
    keywords: SPECIFIC_ALIASES.coupon_rate,
    excludeKeywords: ['yield', 'discount', 'interest'],
    units: ['%', 'percent', 'bps'],
    contextPatterns: ['coupon rate', 'coupon'],
    typicalRange: [0, 100]
  },
  yield_to_maturity: {
    semanticConcept: 'yield to maturity',
    valueTypes: ['percentage'],
    keywords: SPECIFIC_ALIASES.yield,
    excludeKeywords: ['coupon', 'discount', 'interest'],
    units: ['%', 'percent', 'bps'],
    contextPatterns: ['yield', 'ytm', 'yield to maturity'],
    typicalRange: [0, 100]
  },
  country_risk_premium: {
    semanticConcept: 'country risk premium',
    valueTypes: ['percentage'],
    keywords: ['country', 'risk', 'premium', 'crp'],
    units: ['%', 'percent', 'bps'],
    contextPatterns: ['country risk premium', 'crp', 'risk premium'],
    typicalRange: [0, 50]
  },
  spread: {
    semanticConcept: 'spread over benchmark',
    valueTypes: ['percentage', 'bps'],
    keywords: ['spread', 'margin', 'over'],
    units: ['%', 'percent', 'bps', 'basis points'],
    contextPatterns: ['spread', 'margin over', 'spread over'],
    typicalRange: [0, 20]
  },

  // ===== DATES =====
  valuation_date: {
    semanticConcept: 'valuation date',
    valueTypes: ['date'],
    keywords: SPECIFIC_ALIASES.valuation_date,
    contextPatterns: ['valuation date', 'as of date', 'pricing date', 'reporting date']
  },
  issue_date: {
    semanticConcept: 'issue date',
    valueTypes: ['date'],
    keywords: SPECIFIC_ALIASES.issue_date,
    contextPatterns: ['issue date', 'issuance date', 'start date', 'trade date', 'purchase date']
  },
  maturity_date: {
    semanticConcept: 'maturity date',
    valueTypes: ['date'],
    keywords: SPECIFIC_ALIASES.maturity_date,
    contextPatterns: ['maturity date', 'redemption date', 'due date', 'expiry date']
  },
  settlement_date: {
    semanticConcept: 'settlement date',
    valueTypes: ['date'],
    keywords: SPECIFIC_ALIASES.issue_date,
    contextPatterns: ['settlement date', 'effective date']
  },
  next_coupon_date: {
    semanticConcept: 'next coupon payment date',
    valueTypes: ['date'],
    keywords: ['next', 'coupon', 'payment'],
    contextPatterns: ['next coupon', 'next payment', 'coupon payment date']
  },
  call_date: {
    semanticConcept: 'call date',
    valueTypes: ['date'],
    keywords: SPECIFIC_ALIASES.call_date,
    contextPatterns: ['call date', 'redemption date']
  },
  put_date: {
    semanticConcept: 'put date',
    valueTypes: ['date'],
    keywords: SPECIFIC_ALIASES.put_date,
    contextPatterns: ['put date']
  },

  // ===== TERMS/ATTRIBUTES =====
  coupon_frequency: {
    semanticConcept: 'coupon payment frequency',
    valueTypes: ['text'],
    keywords: SPECIFIC_ALIASES.coupon_frequency,
    contextPatterns: ['coupon frequency', 'payment frequency', 'interest frequency', 'frequency'],
    allowedValues: ['annually', 'semi-annually', 'quarterly', 'monthly', 'annual', 'semiannual', 'quarterly', 'monthly', '1', '2', '4', '12']
  },
  day_count_convention: {
    semanticConcept: 'day count convention',
    valueTypes: ['text'],
    keywords: ['day', 'count', 'convention', 'basis'],
    contextPatterns: ['day count', 'day count convention', 'basis'],
    allowedValues: ['30/360', 'actual/360', 'actual/365', 'actual/actual', '30E/360']
  },
  tenor: {
    semanticConcept: 'tenor or term',
    valueTypes: ['text', 'number'],
    keywords: SPECIFIC_ALIASES.term_days,
    contextPatterns: ['tenor', 'term', 'duration', 'maturity']
  },
  days_to_maturity: {
    semanticConcept: 'days to maturity',
    valueTypes: ['number'],
    keywords: SPECIFIC_ALIASES.days_to_maturity,
    contextPatterns: ['days to maturity', 'days remaining', 'tenor days'],
    minValue: 0,
    typicalRange: [0, 36500]
  },
  years_to_maturity: {
    semanticConcept: 'years to maturity',
    valueTypes: ['number'],
    keywords: SPECIFIC_ALIASES.years_to_maturity,
    contextPatterns: ['years to maturity', 'maturity years', 'term years'],
    minValue: 0,
    typicalRange: [0, 100]
  },
  currency: {
    semanticConcept: 'currency',
    valueTypes: ['text'],
    keywords: SPECIFIC_ALIASES.currency,
    contextPatterns: ['currency', 'denomination', 'iso code'],
    allowedValues: ['USD', 'EUR', 'GBP', 'ZAR', 'BWP', 'ZWG', 'CHF', 'JPY', 'CNY', 'INR', 'AUD', 'CAD', 'SGD', 'HKD', 'NZD']
  },
  instrument_type: {
    semanticConcept: 'instrument type',
    valueTypes: ['text'],
    keywords: ['instrument', 'type', 'security', 'bond', 'bill', 'note'],
    contextPatterns: ['instrument type', 'security type', 'type']
  },
  issuer: {
    semanticConcept: 'issuer name',
    valueTypes: ['text'],
    keywords: ['issuer', 'borrower', 'entity', 'company'],
    contextPatterns: ['issuer', 'borrower', 'issuing entity']
  },
  bond_name: {
    semanticConcept: 'bond or instrument name',
    valueTypes: ['text'],
    keywords: ['name', 'bond', 'instrument', 'security'],
    contextPatterns: ['bond name', 'instrument name', 'security name']
  }
}

// ============================================================================
// Helper Functions
// ============================================================================
function normalizeCurrencyToCode(input) {
  if (!input) return null
  const raw = String(input).trim()
  if (!raw) return null
  const upper = raw.toUpperCase()

  if (/^[A-Z]{3}$/.test(upper)) return upper

  for (const [code, syms] of Object.entries(CURRENCY_SYMBOLS)) {
    if (syms.some(s => s === raw)) return code
  }

  const lower = raw.toLowerCase()
  for (const [code, names] of Object.entries(CURRENCY_NAMES)) {
    if (names.some(n => lower === n || lower.includes(n))) return code
  }

  if (/^[A-Z]{3}$/i.test(raw)) return upper
  return null
}

function isNumeric(value) {
  if (value === null || value === undefined || value === '') return false
  const str = String(value).replace(/[%,\s]/g, '')
  return !isNaN(parseFloat(str)) && isFinite(str)
}

function isDateLike(value) {
  if (!value || value === '') return false
  const str = String(value).trim()
  const datePatterns = [
    /^\d{1,2}[-/]\d{1,2}[-/]\d{2,4}$/,
    /^\d{4}[-/]\d{1,2}[-/]\d{1,2}$/,
    /^[A-Za-z]{3}[-/]\d{1,2}[-/]\d{2,4}$/,
    /^\d{1,2}[-/][A-Za-z]{3}[-/]\d{2,4}$/,
    /^[A-Za-z]{3}\s+\d{1,2},\s+\d{4}$/
  ]
  if (datePatterns.some(pattern => pattern.test(str))) return true
  const date = new Date(str)
  if (!isNaN(date.getTime())) { if (!/^\d{4}$/.test(str)) return true }
  return false
}

function isPercentage(value) {
  if (!value) return false
  const str = String(value).trim()
  if (str.includes('%')) return true
  if (isNumeric(str)) {
    const num = parseFloat(str.replace(/[%,\s]/g, ''))
    return num >= 0 && num <= 100
  }
  return false
}

function isCurrency(value) {
  if (!value) return false
  const str = String(value).trim()
  
  // Check for currency symbols
  for (const symbols of Object.values(CURRENCY_SYMBOLS)) {
    for (const sym of symbols) {
      if (str.includes(sym)) return true
    }
  }
  
  // Check if it's a large number (typical for currency amounts)
  if (isNumeric(str)) {
    const num = parseFloat(str.replace(/[%,\s$€£¥₹R]/g, ''))
    return num >= 1000
  }
  
  return false
}

function getValueType(value) {
  if (!value) return 'unknown'
  const str = String(value).trim()
  
  if (isDateLike(str)) return 'date'
  if (isPercentage(str)) return 'percentage'
  if (isCurrency(str)) return 'currency'
  if (isNumeric(str)) return 'numeric'
  
  return 'text'
}

function rowColToCellRef(row, col) {
  const colLetters = []
  let c = col
  while (c >= 0) {
    colLetters.unshift(String.fromCharCode((c % 26) + 65))
    c = Math.floor(c / 26) - 1
  }
  return colLetters.join('') + (row + 1)
}

// ============================================================================
// Semantic Field Matching
// ============================================================================
function calculateSemanticMatchScore(label, value, fieldDef, context) {
  let score = 0
  const labelLower = String(label || '').toLowerCase()
  const valueStr = String(value || '').trim()
  const valueType = getValueType(value)
  
  // 1. Check if value type matches expected type
  if (fieldDef.valueTypes && fieldDef.valueTypes.length > 0) {
    if (fieldDef.valueTypes.includes(valueType)) {
      score += 0.4
    } else {
      return 0 // Wrong type - immediate rejection
    }
  }
  
  // 2. Keyword matching in label
  if (fieldDef.keywords) {
    for (const keyword of fieldDef.keywords) {
      if (labelLower.includes(keyword)) {
        score += 0.3
        // Exact match gets bonus
        if (labelLower === keyword || labelLower === keyword + ' rate' || labelLower === keyword + ' value') {
          score += 0.2
        }
      }
    }
  }
  
  // 3. Exclude keywords (to disambiguate similar fields)
  if (fieldDef.excludeKeywords) {
    for (const exclude of fieldDef.excludeKeywords) {
      if (labelLower.includes(exclude)) {
        score -= 0.5
      }
    }
  }
  
  // 4. Context patterns (surrounding text)
  if (fieldDef.contextPatterns && context) {
    const contextLower = context.toLowerCase()
    for (const pattern of fieldDef.contextPatterns) {
      if (contextLower.includes(pattern)) {
        score += 0.2
      }
    }
  }
  
  // 5. Value range validation
  if (fieldDef.typicalRange && isNumeric(valueStr)) {
    const num = parseFloat(valueStr.replace(/[%,\s$€£¥₹R]/g, ''))
    const [min, max] = fieldDef.typicalRange
    if (num >= min && num <= max) {
      score += 0.1
    } else if (fieldDef.minValue && num < fieldDef.minValue) {
      score -= 0.3
    }
  }
  
  // 6. Unit matching
  if (fieldDef.units) {
    for (const unit of fieldDef.units) {
      if (valueStr.includes(unit) || labelLower.includes(unit.toLowerCase())) {
        score += 0.1
      }
    }
  }
  
  return Math.max(0, Math.min(score, 1.0))
}

function getContextualClues(data, row, col, maxDistance = 3) {
  const clues = []
  
  // Look at surrounding cells for context
  for (let dr = -maxDistance; dr <= maxDistance; dr++) {
    for (let dc = -maxDistance; dc <= maxDistance; dc++) {
      if (dr === 0 && dc === 0) continue
      
      const r = row + dr
      const c = col + dc
      
      if (r >= 0 && r < data.length && c >= 0 && c < data[r].length) {
        const cell = data[r][c]
        if (cell && String(cell).trim() !== '') {
          clues.push(String(cell).trim())
        }
      }
    }
  }
  
  return clues.join(' ')
}

// ============================================================================
// Worksheet Structure Analysis
// ============================================================================
function detectWorksheetStructure(data) {
  const structure = {
    hasHorizontalHeaders: false,
    hasVerticalHeaders: false,
    hasKeyValuePairs: false,
    sections: [],
    tables: []
  }
  
  if (!data || data.length === 0) return structure
  
  // Detect horizontal headers (text in first row)
  const firstRow = data[0] || []
  const textInFirstRow = firstRow.filter(cell => 
    cell && !isNumeric(cell) && !isDateLike(cell) && String(cell).trim().length > 0
  ).length
  
  if (textInFirstRow >= 2) {
    structure.hasHorizontalHeaders = true
  }
  
  // Detect vertical headers (text in first column)
  let textInFirstCol = 0
  for (let r = 0; r < data.length; r++) {
    const cell = data[r] && data[r][0]
    if (cell && !isNumeric(cell) && !isDateLike(cell) && String(cell).trim().length > 0) {
      textInFirstCol++
    }
  }
  
  if (textInFirstCol >= 2) {
    structure.hasVerticalHeaders = true
  }
  
  // Detect key-value pairs (label in one cell, value adjacent)
  let kvPairs = 0
  for (let r = 0; r < data.length; r++) {
    for (let c = 0; c < (data[r]?.length || 0) - 1; c++) {
      const cell = data[r][c]
      const nextCell = data[r][c + 1]
      
      if (cell && nextCell) {
        const cellStr = String(cell).trim()
        const nextStr = String(nextCell).trim()
        
        // Label-like followed by value-like
        if (!isNumeric(cellStr) && !isDateLike(cellStr) && 
            (isNumeric(nextStr) || isDateLike(nextStr) || isCurrency(nextStr) || isPercentage(nextStr))) {
          kvPairs++
        }
      }
    }
  }
  
  if (kvPairs >= 2) {
    structure.hasKeyValuePairs = true
  }
  
  // Detect sections (rows with single text cell, followed by content)
  for (let r = 0; r < data.length; r++) {
    const row = data[r] || []
    const nonEmpty = row.filter(c => c !== null && c !== undefined && String(c).trim() !== '')
    
    if (nonEmpty.length === 1) {
      const text = String(nonEmpty[0]).trim()
      if (!isNumeric(text) && !isDateLike(text) && text.length > 0 && text.length < 60) {
        structure.sections.push({ row: r, title: text })
      }
    }
  }
  
  return structure
}

// ============================================================================
// Currency Detection
// ============================================================================
function detectCurrencies(data) {
  const currencies = new Set()
  
  for (let r = 0; r < data.length; r++) {
    for (let c = 0; c < (data[r]?.length || 0); c++) {
      const cell = data[r][c]
      if (!cell) continue
      
      const str = String(cell).trim()
      
      // Check for currency symbols
      for (const [code, symbols] of Object.entries(CURRENCY_SYMBOLS)) {
        for (const sym of symbols) {
          if (str.includes(sym)) {
            currencies.add(code)
          }
        }
      }
      
      // Check for ISO codes
      if (/^[A-Z]{3}$/.test(str.toUpperCase())) {
        const code = str.toUpperCase()
        if (KNOWN_ISO_CODES.has(code) && !NON_CURRENCY_WORDS.has(code)) {
          currencies.add(code)
        }
      }
    }
  }
  
  return Array.from(currencies)
}

// ============================================================================
// Main Detection Function
// ============================================================================
export function autoDetectInstrumentFields(fileBuffer, sheetName, requiredColumns, instrumentType, tableRange = null, tableData = null, customCurrency = null, statusCallback = null) {
  console.log('=== autoDetectInstrumentFields Started ===')
  console.log('Sheet Name:', sheetName, '| Instrument:', instrumentType)
  console.log('Required Columns:', requiredColumns)
  console.log('Table Range:', tableRange, '| Table Data Provided:', !!tableData)
  console.log('Custom Currency Filter:', customCurrency)

  const updateStatus = (status) => {
    if (statusCallback) statusCallback(status)
  }

  if (!fileBuffer || !sheetName) {
    throw new Error('File buffer and sheet name are required')
  }

  updateStatus('scanning')

  // ========================================================================
  // STEP 1: Read worksheet data ONCE
  // ========================================================================
  let data = []
  let actualUsedRange = null

  if (tableData && Array.isArray(tableData) && tableData.length > 0) {
    // Use provided table data (selected section mode)
    data = tableData
    console.log('Using provided table data (selected section mode)')
  } else {
    // Read from workbook (whole worksheet mode)
    const workbook = XLSX.read(fileBuffer, { 
      type: 'array', 
      cellStyles: true, 
      cellFormula: true, 
      cellDates: true, 
      cellNF: true 
    })
    const worksheet = workbook.Sheets[sheetName]

    if (!worksheet) {
      return {
        fields: {},
        fieldsWithMetadata: {},
        currencies: [],
        missingFields: requiredColumns,
        additionalFields: {}
      }
    }

    // Get actual used range from worksheet
    let range = worksheet['!ref']
      ? XLSX.utils.decode_range(worksheet['!ref'])
      : { s: { r: 0, c: 0 }, e: { r: 0, c: 0 } }

    // Find actual max row and col with data
    let maxRow = 0, maxCol = 0
    for (const cellAddress in worksheet) {
      if (cellAddress.startsWith('!')) continue
      const cellRef = XLSX.utils.decode_cell(cellAddress)
      if (cellRef.r > maxRow) maxRow = cellRef.r
      if (cellRef.c > maxCol) maxCol = cellRef.c
    }
    
    // Use actual data bounds, not hardcoded limits
    if (maxRow > range.e.r) range.e.r = maxRow
    if (maxCol > range.e.c) range.e.c = maxCol
    
    actualUsedRange = range

    // Read data only within actual used range
    for (let R = range.s.r; R <= range.e.r; R++) {
      const row = []
      for (let C = range.s.c; C <= range.e.c; C++) {
        const cellAddress = XLSX.utils.encode_cell({ r: R, c: C })
        const cell = worksheet[cellAddress]
        row.push(cell ? (cell.w ?? cell.v ?? '') : '')
      }
      data.push(row)
    }
    
    console.log(`Read worksheet: ${range.e.r + 1} rows x ${range.e.c + 1} cols (actual used range)`)
  }

  updateStatus('analyzing')

  // ========================================================================
  // STEP 2: Apply currency filter if specified
  // ========================================================================
  let currencyFilterCode = null
  if (customCurrency) {
    currencyFilterCode = normalizeCurrencyToCode(customCurrency)
    if (currencyFilterCode) {
      console.log('Currency filter applied:', currencyFilterCode)
    }
  }

  // ========================================================================
  // STEP 3: Determine scan boundaries
  // ========================================================================
  let boundaries
  if (tableRange && tableData) {
    // Selected section mode - use provided data as-is
    boundaries = {
      startRow: 0,
      endRow: data.length - 1,
      startCol: 0,
      endCol: data[0]?.length - 1 || 0
    }
    console.log('=== MODE: SELECTED SECTION SCAN ===')
  } else if (tableRange) {
    // Range provided mode
    boundaries = {
      startRow: tableRange.startRow,
      endRow: tableRange.endRow,
      startCol: tableRange.startCol,
      endCol: tableRange.endCol
    }
    console.log('=== MODE: PROVIDED RANGE SCAN ===')
  } else {
    // Whole worksheet mode - use actual used range
    boundaries = {
      startRow: 0,
      endRow: data.length - 1,
      startCol: 0,
      endCol: Math.max(...data.map(row => row?.length || 0)) - 1
    }
    console.log('=== MODE: WHOLE WORKSHEET SCAN ===')
  }

  // ========================================================================
  // STEP 4: Analyze worksheet structure
  // ========================================================================
  const structure = detectWorksheetStructure(data)
  console.log('Worksheet structure:', structure)

  // ========================================================================
  // STEP 5: Build semantic field map from ALL semantic definitions
  // ========================================================================
  const semanticFieldMap = new Map()

  // Map ALL semantic definitions for comprehensive scanning
  for (const [semanticKey, def] of Object.entries(SEMANTIC_FIELD_DEFINITIONS)) {
    semanticFieldMap.set(semanticKey, {
      semanticKey,
      definition: def,
      isRequired: requiredColumns.includes(semanticKey) || requiredColumns.some(col => col.toLowerCase().replace(/[-_\s]/g, '') === semanticKey.toLowerCase().replace(/[-_\s]/g, ''))
    })
  }

  // Also add any required columns that don't have semantic definitions
  for (const col of requiredColumns) {
    if (!semanticFieldMap.has(col)) {
      semanticFieldMap.set(col, {
        semanticKey: col,
        definition: {
          valueTypes: [],
          keywords: splitIntoWords(col),
          contextPatterns: []
        },
        isRequired: true
      })
    }
  }

  console.log('Semantic field map (all fields):', Array.from(semanticFieldMap.keys()))
  console.log('Required columns:', requiredColumns)

  updateStatus('detecting')

  // ========================================================================
  // STEP 6: TWO-PHASE DETECTION - REQUIRED FIRST, THEN ADDITIONAL
  // ========================================================================
  console.log('=== TWO-PHASE DETECTION START ===')
  console.log('Phase 1: Scan for REQUIRED fields only')
  console.log('Phase 2: Scan for ADDITIONAL fields (if capacity allows)')

  // NEW: Support multiple currency variants per field
  // Structure: detectedFields[fieldName] = { currencyVariants: { USD: value, ZWG: value }, selectedCurrency: 'USD' }
  const detectedFields = {}
  const detectedFieldsWithMetadata = {}
  const usedLabelValuePairs = new Set()
  const processedCells = new Set()

  // Phase 1: Scan ONLY for required fields
  let allRequiredFound = false
  const requiredFieldNames = Array.from(semanticFieldMap.entries())
    .filter(([_, { isRequired }]) => isRequired)
    .map(([name]) => name)

  console.log('Required fields to find:', requiredFieldNames)

  for (let R = boundaries.startRow; R <= boundaries.endRow && !allRequiredFound; R++) {
    for (let C = boundaries.startCol; C <= boundaries.endCol && !allRequiredFound; C++) {
      const cellKey = `${R}_${C}`
      if (processedCells.has(cellKey)) continue

      const label = data[R]?.[C]
      if (!label || String(label).trim() === '') continue

      const labelStr = String(label).trim()
      const labelLower = labelStr.toLowerCase()

      // Skip if it looks like a pure value, not a label
      const isPureNumeric = isNumeric(labelStr)
      const isPureDate = isDateLike(labelStr)
      const isPureCurrency = isCurrency(labelStr) && labelStr.length < 10
      const isPurePercentage = isPercentage(labelStr)

      const isTextTerm = /^[A-Z]{3}$/.test(labelStr.toUpperCase()) ||
                          /^(annually|semi-annually|quarterly|monthly|annual|semiannual|daily)$/i.test(labelStr) ||
                          /^(30\/360|actual\/360|actual\/365|actual\/actual|30E\/360)$/i.test(labelStr) ||
                          /^(bond|bill|note|money market)$/i.test(labelStr)

      if ((isPureNumeric || isPureDate || isPureCurrency || isPurePercentage) && !isTextTerm) {
        continue
      }

      // Get context
      const context = getContextualClues(data, R, C, 2)

      // Detect currency from context for this specific cell
      let contextCurrency = null
      const contextForCurrency = getContextualClues(data, R, C, 3)
      for (const [code, symbols] of Object.entries(CURRENCY_SYMBOLS)) {
        for (const sym of symbols) {
          if (contextForCurrency.includes(sym)) {
            contextCurrency = code
            break
          }
        }
        if (contextCurrency) break
      }

      // Try horizontal value lookup
      let valueHit = null
      let valueLocation = null
      let direction = null

      for (let offset = 1; offset <= 5 && C + offset <= boundaries.endCol; offset++) {
        const val = data[R]?.[C + offset]
        if (val && String(val).trim() !== '') {
          valueHit = val
          valueLocation = { row: R, col: C + offset }
          direction = 'horizontal'
          processedCells.add(`${R}_${C + offset}`)
          break
        }
      }

      if (!valueHit) {
        for (let offset = 1; offset <= 5 && R + offset <= boundaries.endRow; offset++) {
          const val = data[R + offset]?.[C]
          if (val && String(val).trim() !== '') {
            valueHit = val
            valueLocation = { row: R + offset, col: C }
            direction = 'vertical'
            processedCells.add(`${R + offset}_${C}`)
            break
          }
        }
      }

      if (!valueHit) continue

      // Check ONLY required fields in Phase 1
      let bestMatch = null
      let bestScore = 0

      for (const [colName, { semanticKey, definition, isRequired }] of semanticFieldMap) {
        if (!isRequired) continue // Skip additional fields in Phase 1
        if (detectedFields[colName]) continue

        const score = calculateSemanticMatchScore(labelStr, valueHit, definition, context)

        if (score > 0.35) { // Higher threshold for required fields
          console.log(`[Phase 1] Score for "${colName}": ${score.toFixed(2)} (label: "${labelStr}", value: "${valueHit}")`)
        }

        if (score > bestScore && score > 0.35) {
          bestScore = score
          bestMatch = { colName, semanticKey, score, isRequired }
        }
      }

      if (bestMatch) {
        const pairKey = `${labelStr}_${valueHit}_${R}_${C}`
        if (!usedLabelValuePairs.has(pairKey)) {
          const location = valueLocation ? rowColToCellRef(valueLocation.row, valueLocation.col) : rowColToCellRef(R, C + 1)

          // Detect currency for this value
          let detectedCurrency = null
          const valueStr = String(valueHit)
          if (isCurrency(valueStr)) {
            for (const [code, symbols] of Object.entries(CURRENCY_SYMBOLS)) {
              for (const sym of symbols) {
                if (valueStr.includes(sym)) {
                  detectedCurrency = code
                  break
                }
              }
              if (detectedCurrency) break
            }
          }

          if (!detectedCurrency) {
            detectedCurrency = contextCurrency
          }

          const fieldName = bestMatch.colName
          const currencyKey = detectedCurrency || 'UNKNOWN'

          // Check if this field already exists - if so, add as variant
          if (detectedFields[fieldName]) {
            // Field already detected - check if this is a different value
            const existingValue = String(detectedFields[fieldName].value)
            const newValue = String(valueHit)

            if (existingValue !== newValue) {
              // Different value - add as currency variant
              if (!detectedFields[fieldName].currencyVariants) {
                detectedFields[fieldName].currencyVariants = {}
              }

              // Use the detected currency, or generate a key if none
              const variantKey = detectedCurrency || `VARIANT_${Object.keys(detectedFields[fieldName].currencyVariants).length}`
              detectedFields[fieldName].currencyVariants[variantKey] = valueHit
              console.log(`[Phase 1] Added variant for "${fieldName}": ${variantKey} = ${valueHit}`)
            }
          } else {
            // First detection of this field - initialize with currency variants structure
            detectedFields[fieldName] = {
              currencyVariants: {},
              selectedCurrency: currencyKey,
              value: valueHit,
              location,
              confidence: bestMatch.score,
              detectedFrom: direction,
              semanticMatch: bestMatch.semanticKey,
              currency: detectedCurrency
            }
            detectedFields[fieldName].currencyVariants[currencyKey] = valueHit
          }

          detectedFieldsWithMetadata[fieldName] = detectedFields[fieldName]

          usedLabelValuePairs.add(pairKey)
          console.log(`[Phase 1] Detected required field "${fieldName}": "${valueHit}" (${detectedCurrency || 'no currency'}) at ${location}`)

          // Check if all required fields found
          const foundRequired = requiredFieldNames.filter(name => detectedFields[name])
          if (foundRequired.length === requiredFieldNames.length) {
            allRequiredFound = true
            console.log('[Phase 1] All required fields found!')
          }
        }
      }
    }
  }

  console.log('=== Phase 1 Complete ===')
  console.log('Required fields found:', requiredFieldNames.filter(name => detectedFields[name]).length, '/', requiredFieldNames.length)

  // Phase 2: Scan for additional fields (only if not already at capacity)
  console.log('=== Phase 2: Scanning for additional fields ===')
  const maxAdditionalFields = 50 // Limit to prevent performance issues
  let additionalFieldsFound = 0

  for (let R = boundaries.startRow; R <= boundaries.endRow && additionalFieldsFound < maxAdditionalFields; R++) {
    for (let C = boundaries.startCol; C <= boundaries.endCol && additionalFieldsFound < maxAdditionalFields; C++) {
      const cellKey = `${R}_${C}`
      if (processedCells.has(cellKey)) continue

      const label = data[R]?.[C]
      if (!label || String(label).trim() === '') continue

      const labelStr = String(label).trim()
      const labelLower = labelStr.toLowerCase()

      const isPureNumeric = isNumeric(labelStr)
      const isPureDate = isDateLike(labelStr)
      const isPureCurrency = isCurrency(labelStr) && labelStr.length < 10
      const isPurePercentage = isPercentage(labelStr)

      const isTextTerm = /^[A-Z]{3}$/.test(labelStr.toUpperCase()) ||
                          /^(annually|semi-annually|quarterly|monthly|annual|semiannual|daily)$/i.test(labelStr) ||
                          /^(30\/360|actual\/360|actual\/365|actual\/actual|30E\/360)$/i.test(labelStr) ||
                          /^(bond|bill|note|money market)$/i.test(labelStr)

      if ((isPureNumeric || isPureDate || isPureCurrency || isPurePercentage) && !isTextTerm) {
        continue
      }

      const context = getContextualClues(data, R, C, 2)

      // Detect currency from context for this specific cell
      let contextCurrency = null
      const contextForCurrency = getContextualClues(data, R, C, 3)
      for (const [code, symbols] of Object.entries(CURRENCY_SYMBOLS)) {
        for (const sym of symbols) {
          if (contextForCurrency.includes(sym)) {
            contextCurrency = code
            break
          }
        }
        if (contextCurrency) break
      }

      // Try horizontal value lookup
      let valueHit = null
      let valueLocation = null
      let direction = null

      for (let offset = 1; offset <= 5 && C + offset <= boundaries.endCol; offset++) {
        const val = data[R]?.[C + offset]
        if (val && String(val).trim() !== '') {
          valueHit = val
          valueLocation = { row: R, col: C + offset }
          direction = 'horizontal'
          processedCells.add(`${R}_${C + offset}`)
          break
        }
      }

      if (!valueHit) {
        for (let offset = 1; offset <= 5 && R + offset <= boundaries.endRow; offset++) {
          const val = data[R + offset]?.[C]
          if (val && String(val).trim() !== '') {
            valueHit = val
            valueLocation = { row: R + offset, col: C }
            direction = 'vertical'
            processedCells.add(`${R + offset}_${C}`)
            break
          }
        }
      }

      if (!valueHit) continue

      // Check ONLY additional fields in Phase 2
      let bestMatch = null
      let bestScore = 0

      for (const [colName, { semanticKey, definition, isRequired }] of semanticFieldMap) {
        if (isRequired) continue // Skip required fields in Phase 2
        if (detectedFields[colName]) continue

        const score = calculateSemanticMatchScore(labelStr, valueHit, definition, context)

        if (score > 0.4) { // Higher threshold for additional fields to reduce false positives
          console.log(`[Phase 2] Score for "${colName}": ${score.toFixed(2)} (label: "${labelStr}", value: "${valueHit}")`)
        }

        if (score > bestScore && score > 0.4) {
          bestScore = score
          bestMatch = { colName, semanticKey, score, isRequired }
        }
      }

      if (bestMatch) {
        const pairKey = `${labelStr}_${valueHit}_${R}_${C}`
        if (!usedLabelValuePairs.has(pairKey)) {
          const location = valueLocation ? rowColToCellRef(valueLocation.row, valueLocation.col) : rowColToCellRef(R, C + 1)

          // Detect currency for this value
          let detectedCurrency = null
          const valueStr = String(valueHit)
          if (isCurrency(valueStr)) {
            for (const [code, symbols] of Object.entries(CURRENCY_SYMBOLS)) {
              for (const sym of symbols) {
                if (valueStr.includes(sym)) {
                  detectedCurrency = code
                  break
                }
              }
              if (detectedCurrency) break
            }
          }

          if (!detectedCurrency) {
            detectedCurrency = contextCurrency
          }

          const fieldName = bestMatch.colName
          const currencyKey = detectedCurrency || 'UNKNOWN'

          // Check if this field already exists - if so, add as variant
          if (detectedFields[fieldName]) {
            // Field already detected - check if this is a different value
            const existingValue = String(detectedFields[fieldName].value)
            const newValue = String(valueHit)

            if (existingValue !== newValue) {
              // Different value - add as currency variant
              if (!detectedFields[fieldName].currencyVariants) {
                detectedFields[fieldName].currencyVariants = {}
              }

              const variantKey = detectedCurrency || `VARIANT_${Object.keys(detectedFields[fieldName].currencyVariants).length}`
              detectedFields[fieldName].currencyVariants[variantKey] = valueHit
              console.log(`[Phase 2] Added variant for "${fieldName}": ${variantKey} = ${valueHit}`)
            }
          } else {
            // First detection of this field - initialize with currency variants structure
            detectedFields[fieldName] = {
              currencyVariants: {},
              selectedCurrency: currencyKey,
              value: valueHit,
              location,
              confidence: bestMatch.score,
              detectedFrom: direction,
              semanticMatch: bestMatch.semanticKey,
              currency: detectedCurrency
            }
            detectedFields[fieldName].currencyVariants[currencyKey] = valueHit
          }

          detectedFieldsWithMetadata[fieldName] = detectedFields[fieldName]

          usedLabelValuePairs.add(pairKey)
          additionalFieldsFound++
          console.log(`[Phase 2] Detected additional field "${fieldName}": "${valueHit}" (${detectedCurrency || 'no currency'}) at ${location}`)
        }
      }
    }
  }

  console.log('=== Phase 2 Complete ===')
  console.log('Additional fields found:', additionalFieldsFound)

  console.log('=== Detection Complete ===')
  console.log('Total detected fields:', Object.keys(detectedFields).length)
  console.log('Detected fields:', Object.keys(detectedFields))

  // ========================================================================
  // STEP 7: Separate into primary (required) and additional fields
  // ========================================================================
  const primaryFields = {}
  const primaryFieldsWithMetadata = {}
  const additionalFields = {}

  for (const [colName, detection] of Object.entries(detectedFields)) {
    const { semanticKey, isRequired } = semanticFieldMap.get(colName) || { isRequired: false }

    // Extract the selected value (based on selectedCurrency or default to the value field)
    const selectedValue = detection.selectedCurrency && detection.currencyVariants[detection.selectedCurrency]
      ? detection.currencyVariants[detection.selectedCurrency]
      : detection.value

    if (isRequired) {
      primaryFields[colName] = selectedValue
      primaryFieldsWithMetadata[colName] = detection
    } else {
      additionalFields[colName] = selectedValue
    }
  }

  console.log('Primary (required) fields:', Object.keys(primaryFields).length)
  console.log('Additional fields:', Object.keys(additionalFields).length)
  console.log('Missing required fields:', requiredColumns.filter(col => !primaryFields[col]))

  // ========================================================================
  // STEP 8: Detect currencies
  // ========================================================================
  const currencies = detectCurrencies(data)
  if (customCurrency) {
    const normalized = normalizeCurrencyToCode(customCurrency)
    if (normalized && !currencies.includes(normalized)) {
      currencies.push(normalized)
    }
  }
  console.log('Detected currencies:', currencies)

  // ========================================================================
  // STEP 9: Build result
  // ========================================================================
  const missingFields = requiredColumns.filter(col => !primaryFields[col])

  console.log('=== Final Detection Result ===')
  console.log('Primary (required) fields:', Object.keys(primaryFields))
  console.log('Additional fields:', Object.keys(additionalFields))
  console.log('Missing required fields:', missingFields)

  return {
    fields: primaryFields,
    fieldsWithMetadata: primaryFieldsWithMetadata,
    currencies,
    missingFields,
    additionalFields
  }
}

// ============================================================================
// Utility Functions
// ============================================================================
function splitIntoWords(str) {
  if (!str) return []
  const withSpaces = String(str)
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .replace(/([A-Z]+)([A-Z][a-z])/g, '$1 $2')
    .replace(/[_\-]+/g, ' ')
    .trim()
  return withSpaces.split(/\s+/).filter(Boolean)
}
