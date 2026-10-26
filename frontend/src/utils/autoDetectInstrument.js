// [FINAL] autoDetectInstrument.js
import * as XLSX from 'xlsx'

const MAX_DETECT_ROWS = 500
const MAX_LOOKAHEAD = 6

const CURRENCY_SYMBOLS = {
  USD: ['$', 'US$', 'USD$'], EUR: ['€'], GBP: ['£'], JPY: ['¥', 'JP¥'],
  CNY: ['¥', 'CN¥', 'RMB', '元'], INR: ['₹'], ZAR: ['R'], ZWL: ['Z$', 'ZWL$'],
  ZWG: ['ZWG$', 'ZiG'], AUD: ['A$', 'AU$'], CAD: ['C$', 'CA$'],
  CHF: ['CHF', 'Fr'], NZD: ['NZ$'], HKD: ['HK$'], SGD: ['S$'], ZMW: ['ZK'],
  BWP: ['P'], NGN: ['₦'], KES: ['KSh'], EGP: ['E£'], AED: ['د.إ'],
  SAR: ['﷼'], TRY: ['₺'], RUB: ['₽'], BRL: ['R$'], KRW: ['₩'], THB: ['฿'],
  VND: ['₫'], PHP: ['₱'], IDR: ['Rp'], MYR: ['RM'],
}

const CURRENCY_NAMES = {
  USD: ['dollar', 'us dollar', 'united states dollar', 'american dollar'],
  EUR: ['euro', 'euros'], GBP: ['pound', 'pounds', 'british pound', 'sterling'],
  JPY: ['yen', 'japanese yen'], CNY: ['yuan', 'renminbi', 'chinese yuan'],
  INR: ['rupee', 'indian rupee', 'rupees'],
  ZAR: ['rand', 'south african rand'],
  ZWL: ['zimbabwe dollar', 'zimbabwean dollar'],
  ZWG: ['zimbabwe gold', 'zig'], AUD: ['australian dollar'],
  CAD: ['canadian dollar'], CHF: ['swiss franc', 'franc'],
  NZD: ['new zealand dollar'], HKD: ['hong kong dollar'],
  SGD: ['singapore dollar'], NGN: ['naira'],
  KES: ['kenyan shilling', 'shilling'], BWP: ['pula'],
  EGP: ['egyptian pound'], AED: ['dirham', 'uae dirham'],
  SAR: ['riyal', 'saudi riyal'], TRY: ['lira', 'turkish lira'],
  RUB: ['ruble', 'russian ruble'], BRL: ['real', 'brazilian real'],
  KRW: ['won', 'korean won'], THB: ['baht', 'thai baht'],
  VND: ['dong', 'vietnamese dong'], PHP: ['peso', 'philippine peso'],
  IDR: ['rupiah', 'indonesian rupiah'], MYR: ['ringgit', 'malaysian ringgit'],
}

const KNOWN_ISO_CODES = new Set([
  'USD','EUR','GBP','JPY','CNY','INR','AUD','CAD','CHF','MXN','BRL','KRW',
  'RUB','ZAR','TRY','SGD','HKD','NOK','SEK','DKK','PLN','THB','IDR','MYR',
  'PHP','VND','CZK','HUF','RON','ILS','CLP','COP','PEN','ARS','UYU','BOB',
  'PYG','CRC','GTQ','HNL','NIO','PAB','DOP','JMD','TTD','BBD','XCD','BZD',
  'GYD','SRD','AWG','ANG','CUP','HTG','XAF','XOF','XPF','CDF','BIF','DJF',
  'ERN','ETB','KES','MGF','MWK','MZN','RWF','SOS','TZS','UGX','ZMW','BWP',
  'SZL','LSL','NAD','AOA','BGN','HRK','CYP','EEK','LTL','LVL','MKD','RSD',
  'SKK','SIT','UAH','ALL','BYN','MDL','AMD','AZN','GEL','KZT','KGS','TJS',
  'TMT','UZS','AFN','IRR','IQD','JOD','KWD','LBP','OMR','QAR','SAR','SYP',
  'AED','YER','BHD','DZD','EGP','LYD','MAD','MRU','SDG','TND','MVR','NPR',
  'PKR','LKR','BDT','BTN','MMK','BND','KHR','LAK','MOP','TWD','MNT','KPW',
  'FJD','PGK','SBD','VUV','WST','NZD','TOP','ISK','SVC','VEF','ZWL','ZWG',
])

const NON_CURRENCY_WORDS = new Set([
  'AND','BUT','FOR','NOR','NOT','NOW','OUT','PUT','SET','SHE','THE','TWO',
  'USE','VIA','YES','YOU','ALL','ANY','ARE','BIG','CAN','DAY','END','EYE',
  'FEW','GET','HAS','HER','HIS','HOW','ITS','LET','MAN','MAY','NEW','OFF',
  'OLD','ONE','OUR','OWN','RUN','SAW','SAY','SEE','SIR','SIT','SIX','SON',
  'SUN','TEN','TOO','TRY','WAR','WAY','WHO','WHY','WIN','WON','YET',
])

const SPECIFIC_ALIASES = {
  principal: [
    'principal', 'principle', 'principal amount', 'principle amount',
    'amount invested', 'investment amount', 'initial investment', 'initial amount',
    'deposit amount', 'starting balance', 'opening balance',
    'capital', 'total cost', 'purchase cost', 'cost',
    'outstanding principal', 'current principal',
  ],
  face_value: [
    'balance', 'balance amount', 'balance_amount',
    'principal balance', 'principal_balance',
    'outstanding balance', 'outstanding_balance',
    'loan balance', 'loan_balance', 'current balance', 'current_balance',
    'face balance', 'face_balance',
    'amount outstanding', 'amount_outstanding',
    'face value', 'facevalue', 'face_value',
    'par value', 'parvalue', 'par_value',
    'redemption value', 'redemptionvalue', 'redemption_value',
    'maturity value', 'maturityvalue', 'maturity_value',
    'nominal value', 'nominalvalue', 'nominal_value',
    'nominal amount', 'notional amount', 'face amount', 'par amount',
    'value', 'amount',
  ],
  interest_rate: [
    'interest rate', 'interestrate', 'interest_rate', 'annual rate',
    'annual interest rate', 'nominal rate', 'stated rate', 'effective rate',
    'apr', 'coupon', 'coupon rate', 'rate %', 'rate%', 'rate',
  ],
  days_to_maturity: [
    'days to maturity', 'daystomaturity', 'days_to_maturity', 'maturity days',
    'duration days', 'contract days', 'term days', 'term_days', 'termdays',
    'term in days', 'tenor', 'term', 'days', 'period',
  ],
  issue_date: [
    'issue date', 'issuedate', 'issue_date', 'start date', 'startdate',
    'start_date', 'effective date', 'effectivedate', 'effective_date',
    'settlement date', 'settlementdate', 'settlement_date',
    'origination date', 'value date', 'valuedate', 'value_date',
    'trade date', 'tradedate', 'trade_date',
  ],
  maturity_date: [
    'maturity date', 'maturitydate', 'maturity_date', 'end date', 'enddate',
    'end_date', 'due date', 'duedate', 'due_date', 'redemption date',
    'redemptiondate', 'redemption_date', 'expiry date', 'expirydate',
    'expiry_date', 'termination date',
  ],
  valuation_date: [
    'valuation', 'valuation date', 'valuationdate', 'valuation_date',
    'portfolio date', 'portfoliodate', 'portfolio_date', 'report date',
    'reportdate', 'report_date', 'as of date', 'asofdate', 'as_of_date',
    'date pfolio', 'datepfolio',
  ],
  purchase_price: [
    'purchase price', 'purchaseprice', 'purchase_price', 'buy price',
    'buyprice', 'buy_price', 'acquisition price', 'entry price',
    'price paid', 'pricepaid', 'price_paid', 'issue price', 'issueprice',
    'issue_price', 'price',
  ],
  current_price: ['current price', 'currentprice', 'current_price'],
  settlement_amount: [
    'settlement amount', 'settlementamount', 'settlement value',
    'cash flow', 'proceeds',
  ],
  market_value: [
    'market value', 'marketvalue', 'market_value', 'current value',
    'currentvalue', 'fair value', 'fairvalue', 'present value',
    'presentvalue', 'total value', 'totalvalue',
  ],
  portfolio_name: ['portfolio name', 'pfolio name', 'portfolio'],
  security: [
    'security', 'security id', 'securityid', 'instrument id',
    'instrumentid', 'isin', 'ticker',
  ],
  instrument_name: [
    'instrument name', 'instrumentname', 'instrument_name',
    'bond name', 'bondname', 'bond_name',
    't-bill name', 'tbill name', 'tbillname', 'tbill_name',
    'treasury bill name', 'security name', 'securityname',
    'issuer', 'parent company name', 'parent company',
    'company', 'entity', 'short name', 'shortname', 'description',
    'name', 'ticker', 'symbol',
  ],
  counterparty: [
    'counterparty', 'counter party', 'counter-party', 'cp',
    'account name', 'client name',
  ],
  classification: ['classification', 'category', 'asset class', 'type'],
  currency: ['currency', 'ccy', 'iso code', 'currency code'],
  country: ['country', 'jurisdiction', 'domicile'],
  sector: ['sector', 'industry', 'industry group'],
  rating: ['credit rating', 'rating', 'moody', 's&p', 'fitch'],
  discount_rate: [
    'discount rate', 'discountrate', 'discount_rate', 'bank discount',
    'bankdiscount', 'discount yield', 'discountyield', 't-bill rate',
    'tbillrate', 'auction rate', 'auctionrate', 'discount',
  ],
  term_days: [
    'term days', 'termdays', 'term_days', 'days to maturity',
    'daystomaturity', 'maturity days', 'maturitydays', 'tenor', 'term', 'days',
  ],
  auction_date: ['auction date', 'auctiondate', 'issue date', 'settlement date'],
  coupon_rate: [
    'coupon rate', 'couponrate', 'coupon_rate', 'coupon', 'annual coupon',
    'annualcoupon', 'fixed rate', 'fixedrate', 'nominal rate', 'nominalrate',
    'stated rate', 'statedrate', 'interest rate', 'interestrate',
  ],
  coupon_frequency: [
    'coupon frequency', 'couponfrequency', 'coupon_frequency',
    'payment frequency', 'paymentfrequency', 'frequency', 'coupon period',
    'payments per year',
  ],
  years_to_maturity: [
    'years to maturity', 'yearstomaturity', 'years_to_maturity',
    'maturity years', 'maturityyears', 'term years', 'termyears',
    'duration years', 'durationyears', 'time to maturity',
    'timetomaturity', 'years', 'year',
  ],
  yield: [
    'yield to maturity', 'yieldtomaturity', 'yield_to_maturity', 'ytm',
    'market yield', 'marketyield', 'required return', 'requiredreturn',
    'redemption yield', 'redemptionyield', 'yield',
  ],
  call_date: ['call date', 'calldate', 'first call date'],
  call_price: ['call price', 'callprice', 'call premium', 'redemption price'],
  put_date: ['put date', 'putdate', 'puttable date'],
  put_price: ['put price', 'putprice', 'put premium'],
}

const SEMANTIC_FIELD_DEFINITIONS = {
  face_value: {
    semanticConcept: 'face value of security',
    valueTypes: ['currency'],
    keywords: [
      'balance', 'balance amount', 'principal balance', 'principal_balance',
      'outstanding balance', 'outstanding_balance', 'loan balance',
      'face balance', 'amount outstanding',
      ...SPECIFIC_ALIASES.face_value,
    ],
    rejectPatterns: ['^[A-Z]{3}$', '^\\d+(?:\\.\\d+)?\\s*%$',
      '^\\d{1,4}[/\\-.]\\d{1,2}[/\\-.]\\d{1,4}$', '^\\.{3}$', '^-$'],
    excludeKeywords: ['rate', 'yield', 'coupon', 'risk', 'premium', 'specific', 'spread'],
    units: ['$', '€', '£', '¥', 'R'],
    contextPatterns: ['face', 'par', 'redemption', 'maturity value', 'balance'],
    minValue: 1000, typicalRange: [1000, 1000000000]
  },
  principal: {
    semanticConcept: 'monetary principal amount',
    valueTypes: ['currency'],
    keywords: SPECIFIC_ALIASES.principal,
    rejectPatterns: ['^[A-Z]{3}$', '^\\d+(?:\\.\\d+)?\\s*%$',
      '^\\d{1,4}[/\\-.]\\d{1,2}[/\\-.]\\d{1,4}$', '^\\.{3}$', '^-$'],
    excludeKeywords: ['rate', 'yield', 'coupon', 'risk', 'premium', 'specific', 'spread', 'balance'],
    units: ['$', '€', '£', '¥', 'R'],
    contextPatterns: ['principal amount', 'invested amount', 'capital'],
    minValue: 1000, typicalRange: [1000, 1000000000]
  },
  discount_rate: {
    semanticConcept: 'discount rate for t-bills',
    valueTypes: ['percentage'],
    keywords: SPECIFIC_ALIASES.discount_rate,
    rejectPatterns: ['^[A-Z]{3}$'],
    excludeKeywords: ['risk', 'premium', 'specific', 'collateral', 'spread', 'coupon'],
    units: ['%', 'percent', 'bps'],
    contextPatterns: ['discount rate', 'discount yield'],
    typicalRange: [0, 100]
  },
  interest_rate: {
    semanticConcept: 'interest rate',
    valueTypes: ['percentage'],
    keywords: SPECIFIC_ALIASES.interest_rate,
    rejectPatterns: ['^[A-Z]{3}$'],
    excludeKeywords: ['risk', 'premium', 'specific', 'collateral', 'pmt', 'payment frequency'],
    units: ['%', 'percent', 'bps'],
    contextPatterns: ['interest rate', 'annual rate'],
    typicalRange: [0, 100]
  },
  coupon_rate: {
    semanticConcept: 'coupon rate for bonds',
    valueTypes: ['percentage'],
    keywords: SPECIFIC_ALIASES.coupon_rate,
    rejectPatterns: ['^[A-Z]{3}$'],
    excludeKeywords: ['risk', 'premium', 'specific', 'collateral', 'discount'],
    units: ['%', 'percent', 'bps'],
    contextPatterns: ['coupon rate', 'coupon'],
    typicalRange: [0, 100]
  },
  yield_to_maturity: {
    semanticConcept: 'yield to maturity',
    valueTypes: ['percentage'],
    keywords: SPECIFIC_ALIASES.yield,
    rejectPatterns: ['^[A-Z]{3}$'],
    excludeKeywords: ['risk', 'premium', 'specific', 'collateral', 'discount'],
    units: ['%', 'percent', 'bps'],
    contextPatterns: ['yield to maturity', 'ytm'],
    typicalRange: [0, 100]
  },
  instrument_name: {
    semanticConcept: 'instrument or security name',
    valueTypes: ['text'],
    keywords: [
      ...SPECIFIC_ALIASES.instrument_name,
      'parent company name', 'parent company', 'counterparty',
    ],
    rejectPatterns: ['^\\d+\\.\\d+\\s*%$', '^\\d+\\s*%$', '^0+$',
      '^-?\\d+(?:\\.\\d+)?$',
      '^\\d{1,4}[/\\-.]\\d{1,2}[/\\-.]\\d{1,4}$',
      '^[A-Z]{3}$', '^\\.{3}$', '^-$'],
    excludeKeywords: ['%', 'pvif', 'cf', 'rate', 'yield', 'discount',
      'coupon', 'interest', 'risk', 'premium'],
    contextPatterns: ['name', 'security', 'instrument', 'issuer',
      'counterparty', 'company'],
  },
  valuation_date: {
    semanticConcept: 'valuation date',
    valueTypes: ['date'],
    keywords: [...SPECIFIC_ALIASES.valuation_date, 'date', 'as of'],
    rejectPatterns: ['^\\d+(?:\\.\\d+)?\\s*%$', '^-?\\d+(?:\\.\\d+)?$', '^[A-Z]{3}$'],
    contextPatterns: ['valuation date', 'as of date', 'pricing date', 'reporting date'],
  },
  maturity_date: {
    semanticConcept: 'maturity date',
    valueTypes: ['date'],
    keywords: SPECIFIC_ALIASES.maturity_date,
    rejectPatterns: ['^\\d+(?:\\.\\d+)?\\s*%$', '^-?\\d+(?:\\.\\d+)?$', '^[A-Z]{3}$'],
    contextPatterns: ['maturity date', 'redemption date', 'due date', 'expiry date'],
  },
  issue_date: {
    semanticConcept: 'issue date',
    valueTypes: ['date'],
    keywords: SPECIFIC_ALIASES.issue_date,
    rejectPatterns: ['^\\d+(?:\\.\\d+)?\\s*%$', '^-?\\d+(?:\\.\\d+)?$', '^[A-Z]{3}$'],
    contextPatterns: ['issue date', 'issuance date', 'start date'],
  },
  settlement_date: {
    semanticConcept: 'settlement date',
    valueTypes: ['date'],
    keywords: SPECIFIC_ALIASES.issue_date,
    rejectPatterns: ['^\\d+(?:\\.\\d+)?\\s*%$', '^-?\\d+(?:\\.\\d+)?$', '^[A-Z]{3}$'],
    contextPatterns: ['settlement date', 'effective date'],
  },
  next_coupon_date: {
    semanticConcept: 'next coupon payment date',
    valueTypes: ['date'],
    keywords: ['next', 'coupon', 'payment'],
    rejectPatterns: ['^\\d+(?:\\.\\d+)?\\s*%$', '^-?\\d+(?:\\.\\d+)?$', '^[A-Z]{3}$'],
    contextPatterns: ['next coupon', 'next payment', 'coupon payment date'],
  },
  call_date: {
    semanticConcept: 'call date', valueTypes: ['date'],
    keywords: SPECIFIC_ALIASES.call_date,
    rejectPatterns: ['^\\d+(?:\\.\\d+)?\\s*%$', '^-?\\d+(?:\\.\\d+)?$'],
    contextPatterns: ['call date', 'redemption date'],
  },
  put_date: {
    semanticConcept: 'put date', valueTypes: ['date'],
    keywords: SPECIFIC_ALIASES.put_date,
    rejectPatterns: ['^\\d+(?:\\.\\d+)?\\s*%$', '^-?\\d+(?:\\.\\d+)?$'],
    contextPatterns: ['put date'],
  },
  coupon_frequency: {
    semanticConcept: 'coupon payment frequency',
    valueTypes: ['text'],
    keywords: SPECIFIC_ALIASES.coupon_frequency,
    contextPatterns: ['coupon frequency', 'payment frequency',
      'interest frequency', 'interest pmt frequency'],
    allowedValues: ['annually', 'semi-annually', 'quarterly', 'monthly',
      'annual', 'semiannual', '1', '2', '4', '12', 'bullet'],
  },
  day_count_convention: {
    semanticConcept: 'day count convention',
    valueTypes: ['text'],
    keywords: ['day', 'count', 'convention', 'basis'],
    contextPatterns: ['day count', 'day count convention', 'basis'],
    allowedValues: ['30/360', 'actual/360', 'actual/365', 'actual/actual', '30E/360'],
  },
  tenor: {
    semanticConcept: 'tenor or term', valueTypes: ['text'],
    keywords: [...SPECIFIC_ALIASES.term_days, 'bullet'],
    contextPatterns: ['tenor', 'term', 'bullet'],
    allowedValues: ['bullet', 'at maturity', '1', '2', '3', '5', '7', '10'],
  },
  days_to_maturity: {
    semanticConcept: 'days to maturity', valueTypes: ['number'],
    keywords: SPECIFIC_ALIASES.days_to_maturity,
    rejectPatterns: ['^[A-Z]{3}$', '^\\d+(?:\\.\\d+)?\\s*%$'],
    contextPatterns: ['days to maturity', 'days remaining', 'tenor days'],
    minValue: 0, typicalRange: [0, 36500],
  },
  years_to_maturity: {
    semanticConcept: 'years to maturity', valueTypes: ['number'],
    keywords: SPECIFIC_ALIASES.years_to_maturity,
    rejectPatterns: ['^[A-Z]{3}$', '^\\d+(?:\\.\\d+)?\\s*%$'],
    contextPatterns: ['years to maturity', 'maturity years', 'term years'],
    minValue: 0, typicalRange: [0, 100],
  },
  currency: {
    semanticConcept: 'currency', valueTypes: ['text'],
    keywords: SPECIFIC_ALIASES.currency,
    contextPatterns: ['currency', 'denomination', 'iso code'],
  },
  price: {
    semanticConcept: 'price of security', valueTypes: ['currency', 'percentage'],
    keywords: [...SPECIFIC_ALIASES.purchase_price, 'clean price', 'dirty price'],
    rejectPatterns: ['^[A-Z]{3}$'], units: ['$', '€', '£', '¥', 'R', '%'],
    contextPatterns: ['price', 'market price', 'clean price', 'dirty price'],
    minValue: 0, typicalRange: [0, 1000000000],
  },
  accrued_interest: {
    semanticConcept: 'accrued interest', valueTypes: ['currency'],
    keywords: ['accrued', 'interest accrued'],
    rejectPatterns: ['^[A-Z]{3}$', '^\\d+(?:\\.\\d+)?\\s*%$'],
    units: ['$', '€', '£', '¥', 'R'],
    contextPatterns: ['accrued interest', 'interest accrued'],
    minValue: 0, typicalRange: [0, 100000000],
  },
  present_value: {
    semanticConcept: 'present value', valueTypes: ['currency'],
    keywords: ['present', 'pv', 'current value'],
    rejectPatterns: ['^[A-Z]{3}$', '^\\d+(?:\\.\\d+)?\\s*%$'],
    units: ['$', '€', '£', '¥', 'R'],
    contextPatterns: ['present value', 'pv', 'current value'],
    minValue: 0, typicalRange: [0, 1000000000],
  },
  carrying_value: {
    semanticConcept: 'carrying value', valueTypes: ['currency'],
    keywords: ['carrying', 'book'],
    rejectPatterns: ['^[A-Z]{3}$', '^\\d+(?:\\.\\d+)?\\s*%$'],
    units: ['$', '€', '£', '¥', 'R'],
    contextPatterns: ['carrying value', 'book value'],
    minValue: 0, typicalRange: [0, 1000000000],
  },
  fair_value: {
    semanticConcept: 'fair value', valueTypes: ['currency'],
    keywords: ['fair'],
    rejectPatterns: ['^[A-Z]{3}$', '^\\d+(?:\\.\\d+)?\\s*%$'],
    units: ['$', '€', '£', '¥', 'R'],
    contextPatterns: ['fair value', 'market value'],
    minValue: 0, typicalRange: [0, 1000000000],
  },
  country_risk_premium: {
    semanticConcept: 'country risk premium', valueTypes: ['percentage'],
    keywords: ['country risk premium', 'crp', 'country risk'],
    rejectPatterns: ['^[A-Z]{3}$'], units: ['%', 'percent'],
    contextPatterns: ['country risk premium', 'crp'],
    typicalRange: [0, 50],
  },
  spread: {
    semanticConcept: 'spread over benchmark', valueTypes: ['percentage'],
    keywords: ['spread', 'margin over'],
    rejectPatterns: ['^[A-Z]{3}$'], units: ['%', 'percent', 'bps'],
    contextPatterns: ['spread', 'margin over', 'spread over'],
    typicalRange: [0, 20],
  },
  instrument_type: {
    semanticConcept: 'instrument type', valueTypes: ['text'],
    keywords: ['instrument type', 'security type', 'type'],
    contextPatterns: ['instrument type', 'security type'],
    allowedValues: ['treasury bill', 't-bill', 'tbill', 'bond', 'money market', 'note'],
  },
}

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
  const patterns = [
    /^\d{1,2}[-/]\d{1,2}[-/]\d{2,4}$/, /^\d{4}[-/]\d{1,2}[-/]\d{1,2}$/,
    /^[A-Za-z]{3}[-/]\d{1,2}[-/]\d{2,4}$/, /^\d{1,2}[-/][A-Za-z]{3}[-/]\d{2,4}$/,
    /^[A-Za-z]{3}\s+\d{1,2},\s+\d{4}$/, /^\d{1,2}\s+[A-Za-z]{3}\s+\d{2,4}$/,
  ]
  if (patterns.some(p => p.test(str))) return true
  const d = new Date(str)
  if (!isNaN(d.getTime()) && !/^\d{4}$/.test(str)) return true
  return false
}

function isPercentage(value) {
  if (!value) return false
  const str = String(value).trim()
  if (str.includes('%')) return true
  if (isNumeric(str)) {
    const num = parseFloat(str.replace(/[%,\s]/g, ''))
    return num >= 0 && num <= 100 && /^[\d.,\s%]+$/.test(str)
  }
  return false
}

function isCurrency(value) {
  if (!value) return false
  const str = String(value).trim()
  for (const symbols of Object.values(CURRENCY_SYMBOLS)) {
    for (const sym of symbols) {
      if (str.includes(sym)) return true
    }
  }
  if (isNumeric(str)) {
    const num = parseFloat(str.replace(/[%,\s$€£¥₹R]/g, ''))
    return num >= 1000
  }
  return false
}

function getValueType(value) {
  if (value === null || value === undefined || value === '') return 'empty'
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

function getContextualClues(data, row, col, maxDistance = 3) {
  const clues = []
  for (let dr = -maxDistance; dr <= maxDistance; dr++) {
    for (let dc = -maxDistance; dc <= maxDistance; dc++) {
      if (dr === 0 && dc === 0) continue
      const r = row + dr
      const c = col + dc
      if (r >= 0 && r < data.length && c >= 0 && c < data[r].length) {
        const cell = data[r][c]
        if (cell && String(cell).trim() !== '') clues.push(String(cell).trim())
      }
    }
  }
  return clues.join(' ')
}

function splitIntoWords(str) {
  if (!str) return []
  return String(str)
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .replace(/([A-Z]+)([A-Z][a-z])/g, '$1 $2')
    .replace(/[_\-]+/g, ' ')
    .trim()
    .split(/\s+/)
    .filter(Boolean)
}

function detectCurrencies(data) {
  const currencies = new Set()
  for (let r = 0; r < data.length; r++) {
    for (let c = 0; c < (data[r]?.length || 0); c++) {
      const cell = data[r][c]
      if (!cell) continue
      const str = String(cell).trim()
      for (const [code, symbols] of Object.entries(CURRENCY_SYMBOLS)) {
        for (const sym of symbols) {
          if (str.includes(sym)) currencies.add(code)
        }
      }
      if (/^[A-Z]{3}$/.test(str.toUpperCase())) {
        const code = str.toUpperCase()
        if (KNOWN_ISO_CODES.has(code) && !NON_CURRENCY_WORDS.has(code)) currencies.add(code)
      }
    }
  }
  return Array.from(currencies)
}

function calculateSemanticMatchScore(label, value, fieldDef, context) {
  const labelLower = String(label || '').toLowerCase().trim()
  const valueStr = String(value || '').trim()
  const valueType = getValueType(value)
  if (valueType === 'empty') return 0
  if (fieldDef.rejectPatterns) {
    for (const pattern of fieldDef.rejectPatterns) {
      try {
        if (new RegExp(pattern, 'i').test(valueStr)) return 0
      } catch (e) { /* bad pattern */ }
    }
  }
  if (fieldDef.excludeKeywords) {
    for (const ex of fieldDef.excludeKeywords) {
      if (labelLower.includes(ex.toLowerCase())) return 0
    }
  }
  if (fieldDef.valueTypes && fieldDef.valueTypes.length > 0) {
    if (!fieldDef.valueTypes.includes(valueType)) return 0
  }
  if (fieldDef.allowedValues && fieldDef.allowedValues.length > 0) {
    const vLower = valueStr.toLowerCase()
    if (!fieldDef.allowedValues.some(a => vLower === a.toLowerCase())) return 0
  }
  let score = 0.3
  if (fieldDef.keywords) {
    for (const keyword of fieldDef.keywords) {
      const kw = keyword.toLowerCase().trim()
      if (!kw) continue
      if (labelLower === kw) { score += 0.55; break }
      if (new RegExp(`(^|[\\s_\\-])${kw.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}($|[\\s_\\-])`).test(labelLower)) {
        score += 0.40; break
      }
      if (labelLower.includes(kw)) { score += 0.20; break }
    }
  }
  if (fieldDef.contextPatterns && context) {
    const ctxLower = context.toLowerCase()
    for (const p of fieldDef.contextPatterns) {
      if (ctxLower.includes(p.toLowerCase())) { score += 0.15; break }
    }
  }
  if (fieldDef.typicalRange && isNumeric(valueStr)) {
    const num = parseFloat(valueStr.replace(/[%,\s$€£¥₹R]/g, ''))
    const [min, max] = fieldDef.typicalRange
    if (num >= min && num <= max) score += 0.10
    else if (fieldDef.minValue && num < fieldDef.minValue) return 0
  }
  return Math.min(score, 1.0)
}

export function autoDetectInstrumentFields(fileBuffer, sheetName, requiredColumns, instrumentType, tableRange = null, tableData = null, customCurrency = null, statusCallback = null) {
  const updateStatus = (s) => { if (statusCallback) statusCallback(s) }
  if (!fileBuffer || !sheetName) throw new Error('File buffer and sheet name are required')
  console.log('=== autoDetectInstrumentFields ===')
  console.log('Sheet:', sheetName, '| Type:', instrumentType, '| Required:', requiredColumns)
  updateStatus('scanning')
  let data = []
  if (tableData && Array.isArray(tableData) && tableData.length > 0) {
    data = tableData
  } else {
    const workbook = XLSX.read(fileBuffer, {
      type: 'array', cellDates: true, cellNF: true
    })
    const worksheet = workbook.Sheets[sheetName]
    if (!worksheet) {
      return { fields: {}, fieldsWithMetadata: {}, currencies: [],
               missingFields: requiredColumns, additionalFields: {} }
    }
    let range = worksheet['!ref']
      ? XLSX.utils.decode_range(worksheet['!ref'])
      : { s: { r: 0, c: 0 }, e: { r: 0, c: 0 } }
    let maxRow = 0, maxCol = 0
    for (const addr in worksheet) {
      if (addr.startsWith('!')) continue
      const ref = XLSX.utils.decode_cell(addr)
      if (ref.r > maxRow) maxRow = ref.r
      if (ref.c > maxCol) maxCol = ref.c
    }
    if (maxRow < range.e.r) range.e.r = maxRow
    if (maxCol < range.e.c) range.e.c = maxCol
    if ((range.e.r - range.s.r + 1) > MAX_DETECT_ROWS) {
      range.e.r = range.s.r + MAX_DETECT_ROWS - 1
    }
    for (let R = range.s.r; R <= range.e.r; R++) {
      const row = []
      for (let C = range.s.c; C <= range.e.c; C++) {
        const cell = worksheet[XLSX.utils.encode_cell({ r: R, c: C })]
        row.push(cell ? (cell.w ?? cell.v ?? '') : '')
      }
      data.push(row)
    }
  }
  updateStatus('analyzing')
  const boundaries = tableRange && !tableData
    ? { startRow: tableRange.startRow, endRow: tableRange.endRow,
        startCol: tableRange.startCol, endCol: tableRange.endCol }
    : { startRow: 0, endRow: data.length - 1,
        startCol: 0, endCol: Math.max(...data.map(r => r?.length || 0)) - 1 }
  const semanticFieldMap = new Map()
  for (const [key, def] of Object.entries(SEMANTIC_FIELD_DEFINITIONS)) {
    const norm = (k) => k.toLowerCase().replace(/[-_\s]/g, '')
    const isReq = (requiredColumns || []).some(col => norm(col) === norm(key))
    semanticFieldMap.set(key, { definition: def, isRequired: isReq })
  }
  const normalizedSemanticKeys = new Set(
    Array.from(semanticFieldMap.keys()).map(k => k.toLowerCase().replace(/[-_\s]/g, ''))
  )
  for (const col of (requiredColumns || [])) {
    const normCol = col.toLowerCase().replace(/[-_\s]/g, '')
    if (!normalizedSemanticKeys.has(normCol)) {
      semanticFieldMap.set(col, {
        definition: {
          valueTypes: ['currency', 'percentage', 'number', 'date', 'text'],
          keywords: splitIntoWords(col),
          rejectPatterns: [],
        },
        isRequired: true
      })
      normalizedSemanticKeys.add(normCol)
    }
  }
  const requiredNames = Array.from(semanticFieldMap.entries())
    .filter(([_, v]) => v.isRequired).map(([k]) => k)
  updateStatus('detecting')
  const detectedFields = {}
  const detectedMetadata = {}
  const usedPairs = new Set()
  const processedCells = new Set()
  let allRequiredFound = false
  for (let R = boundaries.startRow; R <= boundaries.endRow && !allRequiredFound; R++) {
    for (let C = boundaries.startCol; C <= boundaries.endCol && !allRequiredFound; C++) {
      const cellKey = `${R}_${C}`
      if (processedCells.has(cellKey)) continue
      const label = data[R]?.[C]
      if (!label || String(label).trim() === '') continue
      const labelStr = String(label).trim()
      if (labelStr.length > 80) continue
      if (/^\d+(?:\.\d+)?\s*%$/.test(labelStr)) continue
      if (/^\d{1,4}[/\-.]\d{1,2}[/\-.]\d{1,4}$/.test(labelStr)) continue
      if (/^-?\d+(?:\.\d+)?$/.test(labelStr)) continue
      const context = getContextualClues(data, R, C, 2)
      let valueHit = null, valueLoc = null, direction = null
      for (let off = 1; off <= MAX_LOOKAHEAD && C + off <= boundaries.endCol; off++) {
        const v = data[R]?.[C + off]
        if (v && String(v).trim() !== '') {
          valueHit = v
          valueLoc = { row: R, col: C + off }
          direction = 'horizontal'
          processedCells.add(`${R}_${C + off}`)
          break
        }
      }
      if (!valueHit) {
        for (let off = 1; off <= MAX_LOOKAHEAD && R + off <= boundaries.endRow; off++) {
          const v = data[R + off]?.[C]
          if (v && String(v).trim() !== '') {
            valueHit = v
            valueLoc = { row: R + off, col: C }
            direction = 'vertical'
            processedCells.add(`${R + off}_${C}`)
            break
          }
        }
      }
      if (!valueHit) continue
      let best = null, bestScore = 0.5
      for (const [colName, { definition, isRequired }] of semanticFieldMap) {
        if (!isRequired) continue
        if (detectedFields[colName]) continue
        const score = calculateSemanticMatchScore(labelStr, valueHit, definition, context)
        if (score > bestScore) { bestScore = score; best = { colName, score } }
      }
      if (best) {
        const pairKey = `${labelStr}|${valueHit}|${R}|${C}`
        if (!usedPairs.has(pairKey)) {
          const loc = valueLoc ? rowColToCellRef(valueLoc.row, valueLoc.col) : rowColToCellRef(R, C + 1)
          detectedFields[best.colName] = valueHit
          detectedMetadata[best.colName] = {
            location: loc, confidence: best.score,
            originalLabel: labelStr, detectedFrom: direction,
          }
          usedPairs.add(pairKey)
          console.log(`[Phase1] ${best.colName} = "${valueHit}" @ ${loc} (score ${best.score.toFixed(2)})`)
          const found = requiredNames.filter(n => detectedFields[n])
          if (found.length === requiredNames.length) allRequiredFound = true
        }
      }
    }
  }
  const additionalFields = {}
  const additionalMetadata = {}
  let additionalCount = 0
  const MAX_ADDITIONAL = 40
  for (let R = boundaries.startRow; R <= boundaries.endRow && additionalCount < MAX_ADDITIONAL; R++) {
    for (let C = boundaries.startCol; C <= boundaries.endCol && additionalCount < MAX_ADDITIONAL; C++) {
      const cellKey = `${R}_${C}`
      if (processedCells.has(cellKey)) continue
      const label = data[R]?.[C]
      if (!label || String(label).trim() === '') continue
      const labelStr = String(label).trim()
      if (labelStr.length > 80) continue
      if (/^\d+(?:\.\d+)?\s*%$/.test(labelStr)) continue
      if (/^\d{1,4}[/\-.]\d{1,2}[/\-.]\d{1,4}$/.test(labelStr)) continue
      if (/^-?\d+(?:\.\d+)?$/.test(labelStr)) continue
      const context = getContextualClues(data, R, C, 2)
      let valueHit = null, valueLoc = null, direction = null
      for (let off = 1; off <= MAX_LOOKAHEAD && C + off <= boundaries.endCol; off++) {
        const v = data[R]?.[C + off]
        if (v && String(v).trim() !== '') {
          valueHit = v; valueLoc = { row: R, col: C + off }
          direction = 'horizontal'; processedCells.add(`${R}_${C + off}`)
          break
        }
      }
      if (!valueHit) {
        for (let off = 1; off <= MAX_LOOKAHEAD && R + off <= boundaries.endRow; off++) {
          const v = data[R + off]?.[C]
          if (v && String(v).trim() !== '') {
            valueHit = v; valueLoc = { row: R + off, col: C }
            direction = 'vertical'; processedCells.add(`${R + off}_${C}`)
            break
          }
        }
      }
      if (!valueHit) continue
      let best = null, bestScore = 0.55
      for (const [colName, { definition, isRequired }] of semanticFieldMap) {
        if (isRequired) continue
        if (additionalFields[colName]) continue
        const score = calculateSemanticMatchScore(labelStr, valueHit, definition, context)
        if (score > bestScore) { bestScore = score; best = { colName, score } }
      }
      if (best) {
        const pairKey = `${labelStr}|${valueHit}|${R}|${C}`
        if (!usedPairs.has(pairKey)) {
          const loc = valueLoc ? rowColToCellRef(valueLoc.row, valueLoc.col) : rowColToCellRef(R, C + 1)
          additionalFields[best.colName] = valueHit
          additionalMetadata[best.colName] = {
            location: loc, confidence: best.score,
            originalLabel: labelStr, detectedFrom: direction,
          }
          usedPairs.add(pairKey)
          additionalCount++
          console.log(`[Phase2] ${best.colName} = "${valueHit}" @ ${loc} (score ${best.score.toFixed(2)})`)
        }
      }
    }
  }
  const missingFields = (requiredColumns || []).filter(c => !detectedFields[c])
  console.log('=== Detection result ===')
  console.log('Required:', Object.keys(detectedFields))
  console.log('Additional:', Object.keys(additionalFields))
  console.log('Missing:', missingFields)
  return {
    fields: detectedFields,
    fieldsWithMetadata: detectedMetadata,
    currencies: detectCurrencies(data),
    missingFields,
    additionalFields,
    additionalFieldsWithMetadata: additionalMetadata,
    warnings: []
  }
}