// [FINAL] autoDetectInstrument.js
import * as XLSX from 'xlsx'

const MAX_DETECT_ROWS = 2000
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
    'payments per year', 'pmt frequency', 'pmt fequency',
    'interest pmt frequency', 'interest pmt fequency',
    'interest payment frequency', 'coupon fequency',
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
    excludeKeywords: ['risk', 'premium', 'specific', 'collateral', 'pmt',
      'payment frequency', 'spread', 'exch', 'exchange'],
    units: ['%', 'percent', 'bps'],
    contextPatterns: ['interest rate', 'annual rate'],
    typicalRange: [0, 100]
  },
  coupon_rate: {
    semanticConcept: 'coupon rate for bonds',
    valueTypes: ['percentage'],
    keywords: SPECIFIC_ALIASES.coupon_rate,
    rejectPatterns: ['^[A-Z]{3}$'],
    excludeKeywords: ['risk', 'premium', 'specific', 'collateral',
      'discount', 'spread', 'exch', 'exchange'],
    units: ['%', 'percent', 'bps'],
    contextPatterns: ['coupon rate', 'coupon'],
    typicalRange: [0, 100]
  },
  yield_to_maturity: {
    semanticConcept: 'yield to maturity',
    valueTypes: ['percentage'],
    keywords: SPECIFIC_ALIASES.yield,
    rejectPatterns: ['^[A-Z]{3}$'],
    excludeKeywords: ['risk', 'premium', 'specific', 'collateral',
      'discount', 'spread', 'exch', 'exchange'],
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
  last_coupon_date: {
    semanticConcept: 'last coupon payment date',
    valueTypes: ['date'],
    keywords: ['last coupon', 'lastcoupon', 'previous coupon', 'coupon date paid'],
    rejectPatterns: ['^\\d+(?:\\.\\d+)?\\s*%$', '^-?\\d+(?:\\.\\d+)?$', '^[A-Z]{3}$'],
    excludeKeywords: ['next', 'upcoming', 'future'],
    contextPatterns: ['last coupon', 'previous coupon'],
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
      'interest frequency', 'interest pmt frequency',
      'pmt fequency', 'pmt frequency'],
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
    rejectPatterns: ['^[A-Z]{3}$', '^\\d+(?:\\.\\d+)?\\s*%$', '^[A-Z]{2,6}$'],
    units: ['$', '€', '£', '¥', 'R'],
    contextPatterns: ['present value', 'pv', 'current value'],
    minValue: 0, typicalRange: [0, 1000000000],
  },
  carrying_value: {
    semanticConcept: 'carrying value', valueTypes: ['currency'],
    keywords: ['carrying', 'book'],
    rejectPatterns: ['^[A-Z]{3}$', '^\\d+(?:\\.\\d+)?\\s*%$', '^[A-Z]{2,6}$'],
    units: ['$', '€', '£', '¥', 'R'],
    contextPatterns: ['carrying value', 'book value'],
    minValue: 0, typicalRange: [0, 1000000000],
  },
  fair_value: {
    semanticConcept: 'fair value', valueTypes: ['currency'],
    keywords: ['fair'],
    rejectPatterns: ['^[A-Z]{3}$', '^\\d+(?:\\.\\d+)?\\s*%$', '^[A-Z]{2,6}$'],
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
  // Nelson-Siegel-Svensson curve inputs — optional; when present they
  // override the sheet discount_rate in the backend valuation.
  nss_rate: {
    semanticConcept: 'interpolated nss discount rate', valueTypes: ['percentage'],
    keywords: ['nss rate', 'nelson svensson', 'interpolated rate',
      'interpolated nss', 'nss', 'svensson rate'],
    rejectPatterns: ['^[A-Z]{3}$'], units: ['%', 'percent'],
    contextPatterns: ['nelson', 'svensson', 'nss', 'yield curve', 'discount curve'],
    typicalRange: [0, 50],
  },
  beta0: {
    semanticConcept: 'nss beta0 long-run level', valueTypes: ['percentage', 'numeric'],
    keywords: ['beta 0', 'beta0', 'b0', 'level factor', 'long run rate'],
    rejectPatterns: ['^[A-Z]{3}$'], units: ['%', 'percent'],
    contextPatterns: ['nelson', 'svensson', 'nss', 'beta'],
    typicalRange: [-20, 50],
  },
  beta1: {
    semanticConcept: 'nss beta1 short-rate slope', valueTypes: ['percentage', 'numeric'],
    keywords: ['beta 1', 'beta1', 'b1', 'slope factor'],
    rejectPatterns: ['^[A-Z]{3}$'], units: ['%', 'percent'],
    contextPatterns: ['nelson', 'svensson', 'nss', 'beta'],
    typicalRange: [-50, 50],
  },
  beta2: {
    semanticConcept: 'nss beta2 medium-term curvature', valueTypes: ['percentage', 'numeric'],
    keywords: ['beta 2', 'beta2', 'b2', 'curvature factor'],
    rejectPatterns: ['^[A-Z]{3}$'], units: ['%', 'percent'],
    contextPatterns: ['nelson', 'svensson', 'nss', 'beta'],
    typicalRange: [-50, 50],
  },
  beta3: {
    semanticConcept: 'nss beta3 long-term curvature', valueTypes: ['percentage', 'numeric'],
    keywords: ['beta 3', 'beta3', 'b3'],
    rejectPatterns: ['^[A-Z]{3}$'], units: ['%', 'percent'],
    contextPatterns: ['nelson', 'svensson', 'nss', 'beta'],
    typicalRange: [-50, 50],
  },
  tau1: {
    semanticConcept: 'nss tau1 decay parameter', valueTypes: ['numeric'],
    keywords: ['tau 1', 'tau1', 't1', 'decay 1'],
    rejectPatterns: ['%'],
    contextPatterns: ['nelson', 'svensson', 'nss', 'tau'],
    typicalRange: [0.1, 20],
  },
  tau2: {
    semanticConcept: 'nss tau2 decay parameter', valueTypes: ['numeric'],
    keywords: ['tau 2', 'tau2', 't2', 'decay 2'],
    rejectPatterns: ['%'],
    contextPatterns: ['nelson', 'svensson', 'nss', 'tau'],
    typicalRange: [0.1, 20],
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
  const str = String(value).trim()
  if (!str) return false
  // Strict: reject anything containing date separators or letters —
  // parseFloat('10/6/3261') returns 10, which is how dates were being
  // hallucinated into Principal amounts.
  if (/[/-]/.test(str) || /[A-Za-z]/.test(str)) return false
  if (isDateLike(str)) return false
  const cleaned = str.replace(/[%$,\s€£¥₹]/g, '')
  // The entire remaining string must be a plain number (optional sign,
  // digits, one decimal point, optional exponent).
  if (!/^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$/.test(cleaned)) return false
  const n = Number(cleaned)
  return Number.isFinite(n)
}

// Normalize a raw cell into a backend-parseable value.
// Dates -> ISO YYYY-MM-DD; rich-text objects -> inner primitive;
// "[object Object]" and empties -> null (cell skipped).
function normalizeDetectedCellValue(v) {
  if (v === null || v === undefined) return null
  if (v instanceof Date) {
    if (isNaN(v.getTime())) return null
    // Local calendar date — toISOString() would shift back a day for
    // timezones ahead of UTC (Excel stores local-midnight serials).
    const p = n => String(n).padStart(2, '0')
    return `${v.getFullYear()}-${p(v.getMonth() + 1)}-${p(v.getDate())}`
  }
  if (typeof v === 'object') {
    const inner = v.value ?? v.result ?? v.text ?? v.w ?? null
    if (inner === null || inner === undefined) return null
    return normalizeDetectedCellValue(inner)
  }
  const s = String(v).trim()
  if (!s || s === '[object Object]') return null
  return v
}

function isDateLike(value) {
  if (!value || value === '') return false
  const str = String(value).trim()
  if (!str || str.includes('%')) return false
  const patterns = [
    /^\d{1,2}[-/]\d{1,2}[-/]\d{2,4}$/, /^\d{4}[-/]\d{1,2}[-/]\d{1,2}$/,
    /^[A-Za-z]{3}[-/]\d{1,2}[-/]\d{2,4}$/, /^\d{1,2}[-/][A-Za-z]{3}[-/]\d{2,4}$/,
    /^[A-Za-z]{3}\s+\d{1,2},\s+\d{4}$/, /^\d{1,2}\s+[A-Za-z]{3}\s+\d{2,4}$/,
  ]
  if (patterns.some(p => p.test(str))) return true
  // Date() fallback only when the string has a non-digit (separator or
  // month name) — bare numbers like "90" must not parse as years.
  if (/\D/.test(str)) {
    const d = new Date(str)
    if (!isNaN(d.getTime()) && !/^\d{4}$/.test(str)) return true
  }
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
      if (sym.length === 1) {
        // Single-letter symbols (P, R) must be standalone tokens —
        // otherwise "Principal"/"Rate" match as currency.
        const esc = sym.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
        if (new RegExp(`(^|[^A-Za-z])${esc}([^A-Za-z]|$)`).test(str)) return true
      } else if (str.includes(sym)) {
        return true
      }
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

// Offset of data[0][0] within the worksheet's absolute grid. Set per
// detection call so cell refs point to real Excel cells, not data indices.
let CELL_ORIGIN = { r: 0, c: 0 }

function rowColToCellRef(row, col) {
  const R = row + CELL_ORIGIN.r
  const C = col + CELL_ORIGIN.c
  const colLetters = []
  let c = C
  while (c >= 0) {
    colLetters.unshift(String.fromCharCode((c % 26) + 65))
    c = Math.floor(c / 26) - 1
  }
  return colLetters.join('') + (R + 1)
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

// ---- Tabular layout detection -------------------------------------------
// Sheets like "US$ Money Market" store instruments as ROWS under a header
// row. The label->value scanner mistakes headers for values; this detects
// the header row, maps columns to canonical fields and emits one record
// per data row. Summary blocks above/below the table are ignored because
// only rows below the chosen header with >=2 mapped values count.
const TABULAR_ALIASES = {
  'valuation date': 'valuation_date', 'valuation': 'valuation_date',
  'as of date': 'valuation_date', 'asofdate': 'valuation_date',
  'trade date': 'trade_date', 'settlement date': 'settlement_date',
  'issue date': 'issue_date', 'auction date': 'auction_date',
  'maturity date': 'maturity_date', 'redemption date': 'maturity_date',
  'days to maturity': 'days_to_maturity', 'days': 'days_to_maturity',
  'years to maturity': 'years_to_maturity', 'tenure': 'tenure_days',
  'term': 'tenure_days', 'period': 'tenure_days',
  'rate': 'interest_rate', 'rate %': 'interest_rate', 'interest rate': 'interest_rate',
  'annual rate': 'interest_rate', 'coupon rate': 'coupon_rate', 'coupon': 'coupon_rate',
  'discount rate': 'discount_rate', 'yield': 'yield_to_maturity',
  'ytm': 'yield_to_maturity',
  'instrument name': 'instrument_name', 'instrument': 'instrument_name', 'security': 'instrument_id',
  'isin': 'instrument_id', 'short name': 'instrument_name', 'name': 'instrument_name',
  'fund name': 'fund_name', 'portfolio': 'portfolio_name', 'pfolio': 'portfolio_name',
  'pfolio name': 'portfolio_name', 'counterparty': 'counterparty',
  'parent company name': 'parent_company', 'issuer': 'issuer',
  'amount': 'principal', 'principal': 'principal', 'nominal': 'principal',
  'total cost': 'principal', 'total cost (base)': 'principal',
  'face value': 'face_value', 'par value': 'face_value', 'notional': 'face_value',
  'investment': 'face_value', 'total nominal': 'face_value',
  'total value': 'carrying_value', 'carrying value': 'carrying_value',
  'maturity value': 'maturity_value', 'present value': 'present_value',
  'fair value': 'fair_value', 'market value': 'market_value',
  'total present value': 'present_value', 'total carrying value': 'carrying_value',
  'total maturity value': 'maturity_value', 'total cost base': 'principal',
  'currency': 'currency', 'ccy': 'currency', 'currency code': 'currency',
  'instrument type': 'instrument_type', 'type': 'instrument_type',
  'classification': 'instrument_type', 'status': 'status',
  'day count convention': 'day_count_convention', 'day count': 'day_count_convention',
  'accrual basis': 'day_count_convention',
  'impuirement': 'impaired_value', 'impairment': 'impaired_value',
  'weighted rate': 'weighted_rate', 'wam': 'weighted_average_maturity',
  'nss rates': 'nss_rate', 'nss rate': 'nss_rate', 'discount rates': 'discount_rate_curve',
  'interpolated nelson seigel svenson': 'nss_rate', 'interpolated rate': 'nss_rate',
  'nelson seigel svenson': 'nss_rate', 'nelson-svensson': 'nss_rate',
  'beta 0': 'beta0', 'beta0': 'beta0', 'b0': 'beta0',
  'beta 1': 'beta1', 'beta1': 'beta1', 'b1': 'beta1',
  'beta 2': 'beta2', 'beta2': 'beta2', 'b2': 'beta2',
  'beta 3': 'beta3', 'beta3': 'beta3', 'b3': 'beta3',
  'tau 1': 'tau1', 'tau1': 'tau1', 't1': 'tau1',
  'tau 2': 'tau2', 'tau2': 'tau2', 't2': 'tau2',
  'country risk premium': 'country_risk_premium', 'crp': 'country_risk_premium',
  'time value': 'time_value', 'credit impairment': 'credit_impairment',
}
const TABULAR_NORM = s => String(s || '').toLowerCase().replace(/\s+/g, ' ').trim()

// Currency tags inside headers ("Nominal (US$)", "Value ZWG", "US$ MM").
const TABULAR_CCY_RE = /(?:^|[\s(])(usd|us\$|zwg\$?|zig\$?|zwl\$?|bwp\$?|zar\$?|zmk\$?|zmw\$?|eur\$?|gbp\$?|kes\$?)(?=[\s)]|$)/i
function tabularHeaderCurrency(header) {
  const m = String(header || '').match(TABULAR_CCY_RE)
  if (!m) return null
  const t = m[1].toLowerCase().replace(/\$$/, '')
  if (t === 'us' || t === 'usd') return 'USD'
  if (t === 'zwg' || t === 'zig') return 'ZWG'
  if (t === 'zwl') return 'ZWL'
  if (t === 'bwp') return 'BWP'
  if (t === 'zar') return 'ZAR'
  if (t === 'zmw' || t === 'zmk') return 'ZMW'
  if (t === 'eur') return 'EUR'
  if (t === 'gbp') return 'GBP'
  if (t === 'kes') return 'KES'
  return null
}
// Alias lookup key: strip currency tags/parens so "Nominal (US$)" -> "nominal".
const tabularLookupKey = s => TABULAR_NORM(s)
// Alias lookup strips currency tags first: "Principal US$" -> "principal".
const tabularAliasKey = s => TABULAR_NORM(String(s || '').replace(TABULAR_CCY_RE, ' '))
  .replace(TABULAR_CCY_RE, ' ')
  .replace(/[()]/g, ' ')
  .replace(/\s+/g, ' ')
  .trim()

function detectTabularRecords(data, boundaries) {
  // Score each row by how many cells are recognised field headers.
  let bestRow = -1, bestScore = 0
  const rowScores = []
  for (let R = boundaries.startRow; R <= boundaries.endRow; R++) {
    let score = 0
    for (let C = boundaries.startCol; C <= boundaries.endCol; C++) {
      const cell = data[R]?.[C]
      if (typeof cell !== 'string') continue
      const t = tabularAliasKey(cell)
      if (t && TABULAR_ALIASES[t]) score++
    }
    rowScores.push({ R, score })
    if (score > bestScore) { bestScore = score; bestRow = R }
  }
  // Need a convincing header: >=4 recognised columns AND at least one
  // name/identity column — cashflow schedules (Term/Discount rate/
  // Principal/Balance) match aliases but are not instrument tables.
  if (bestRow < 0 || bestScore < 4) return []

  // Map each column to a canonical field. Currency-tagged headers may map
  // several columns to the same field ("Nominal US$" / "Nominal ZWG") —
  // kept as per-currency variants for user selection in the results popup.
  const colField = new Map()
  const colCcy = new Map()
  const colHeader = new Map()
  const fieldCols = new Map()
  for (let C = boundaries.startCol; C <= boundaries.endCol; C++) {
    const cell = data[bestRow]?.[C]
    if (typeof cell !== 'string') continue
    const field = TABULAR_ALIASES[tabularAliasKey(cell)]
    if (!field) continue
    const ccy = tabularHeaderCurrency(cell)
    const seen = fieldCols.get(field) || []
    if (seen.some(ec => (colCcy.get(ec) || null) === ccy)) continue
    colField.set(C, field)
    colCcy.set(C, ccy)
    colHeader.set(C, cell.trim())
    fieldCols.set(field, [...seen, C])
  }
  if (colField.size < 4) return []
  const NAME_FIELDS = new Set(['instrument_name', 'instrument_id', 'fund_name',
    'portfolio_name', 'counterparty', 'issuer', 'parent_company'])
  if (![...colField.values()].some(f => NAME_FIELDS.has(f))) return []

  const records = []
  for (let R = bestRow + 1; R <= boundaries.endRow; R++) {
    // Section boundary: a row that itself looks like a header block
    // (>=4 recognised field headers) starts a new section — stop here
    // so summary blocks ("Time Value", "Fair Value", etc.) are never
    // parsed as instrument rows.
    let headerHits = 0
    for (let C = boundaries.startCol; C <= boundaries.endCol; C++) {
      const cell = data[R]?.[C]
      if (typeof cell !== 'string') continue
      if (TABULAR_ALIASES[tabularLookupKey(cell)]) headerHits++
    }
    if (headerHits >= 4) break
    // Collect raw values per field, grouped by column currency so
    // "Nominal US$" and "Nominal ZWG" become selectable variants.
    const perField = new Map()
    let filled = 0
    for (const [C, field] of colField) {
      const v = normalizeDetectedCellValue(data[R]?.[C])
      if (v === null || v === '') continue
      const ccy = colCcy.get(C) || null
      if (!perField.has(field)) perField.set(field, new Map())
      const variants = perField.get(field)
      if (!variants.has(ccy)) { variants.set(ccy, v); filled++ }
    }
    // A real instrument row needs >=2 mapped values and at least one
    // identity/value anchor; skip totals and blank continuations.
    if (filled < 2) continue
    const scalarOf = f => {
      const vf = perField.get(f)
      if (!vf) return undefined
      const first = vf.values().next().value
      return first && typeof first === 'object' && 'value' in first ? first.value : first
    }
    const anchor = scalarOf('instrument_name') || scalarOf('principal') ||
      scalarOf('face_value') || scalarOf('carrying_value') || scalarOf('maturity_date')
    if (!anchor) continue
    const nameStr = String(anchor)
    if (/^(total|sum|wam|weighted|average|base information|client)/i.test(nameStr.trim())) continue
    // Per-record currency from classification-like columns (US$ MM, ZWG MM).
    const typeStr = String(scalarOf('instrument_type') || '')
    const clsMatch = typeStr.match(/US\$|USD/i) ? 'USD'
      : typeStr.match(/ZWG|ZiG/i) ? 'ZWG'
      : typeStr.match(/ZWL/i) ? 'ZWL'
      : typeStr.match(/BWP/i) ? 'BWP'
      : typeStr.match(/ZAR|\bR\b/i) ? 'ZAR' : null
    // Emit scalar or {value, currencyVariants, selectedCurrency} per field.
    // Strict typing: numeric fields reject date-like values — a string such
    // as "10/6/3261" must never become a Principal/Rate amount.
    const NUMERIC_FIELDS = new Set([
      'principal', 'face_value', 'carrying_value', 'amount', 'nominal',
      'impairment', 'interest_rate', 'discount_rate', 'coupon_rate',
      'yield_to_maturity', 'investor_yield', 'money_market_yield',
      'bond_equivalent_yield', 'price', 'purchase_price', 'current_price',
      'present_value', 'fair_value', 'market_value', 'unit_price',
      'days_to_maturity', 'years_to_maturity', 'tenure_days', 'term_days',
      'coupon_frequency', 'face_value_per_unit', 'quantity', 'units'
    ])
    const warnings = []
    const fields = {}
    for (const [field, variants] of perField) {
      if (NUMERIC_FIELDS.has(field)) {
        for (const [k, v] of [...variants]) {
          if (typeof v === 'string' && isDateLike(v)) {
            variants.delete(k)
            warnings.push(`${field}: rejected date-like value "${v}"`)
          }
        }
        if (variants.size === 0) continue
      }
      if (variants.size > 1) {
        const variantsObj = {}
        for (const [k, v] of variants) variantsObj[k || 'DEFAULT'] = v
        const realKeys = Object.keys(variantsObj).filter(k => k !== 'DEFAULT')
        const sel = (clsMatch && variantsObj[clsMatch] !== undefined) ? clsMatch
          : (realKeys[0] || Object.keys(variantsObj)[0])
        fields[field] = {
          value: variantsObj[sel],
          currencyVariants: variantsObj,
          selectedCurrency: sel,
          currency: sel,
        }
      } else {
        fields[field] = [...variants.values()][0]
      }
    }
    if (clsMatch && !fields.currency) fields.currency = clsMatch
    // No classification column: take the currency of the selected variant
    // on a currency-typed field so the row still carries its currency.
    if (!fields.currency) {
      for (const f of Object.values(fields)) {
        if (f && typeof f === 'object' && f.selectedCurrency) {
          fields.currency = f.selectedCurrency
          break
        }
      }
    }
    // Per-field provenance: worksheet cell ref, original header, raw value.
    // For variant fields prefer the column matching the selected currency.
    const meta = {}
    for (const [C, field] of colField) {
      const raw = data[R]?.[C]
      if (raw === null || raw === undefined || String(raw).trim() === '') continue
      const fObj = fields[field]
      const sel = (fObj && typeof fObj === 'object' && fObj.selectedCurrency) ? fObj.selectedCurrency : null
      const prefer = sel && (colCcy.get(C) || null) === sel
      if (meta[field] && !prefer) continue
      meta[field] = {
        location: rowColToCellRef(R, C),
        originalLabel: colHeader.get(C) || field,
        detectedFrom: 'tabular',
        sourceValue: raw,
      }
    }
    records.push({ rowIndex: R, fields, fieldsWithMetadata: meta, warnings })
  }
  // Require at least 2 instrument rows — single-row "tables" are more
  // likely label/value layouts handled by the pair scanner.
  return records.length >= 2 ? records : []
}

export function autoDetectInstrumentFields(fileBuffer, sheetName, requiredColumns, instrumentType, tableRange = null, tableData = null, customCurrency = null, statusCallback = null) {
  const updateStatus = (s) => { if (statusCallback) statusCallback(s) }
  if (!fileBuffer || !sheetName) throw new Error('File buffer and sheet name are required')
  console.log('=== autoDetectInstrumentFields ===')
  console.log('Sheet:', sheetName, '| Type:', instrumentType, '| Required:', requiredColumns)
  updateStatus('scanning')
  let data = []
  CELL_ORIGIN = { r: 0, c: 0 }
  if (tableData && Array.isArray(tableData) && tableData.length > 0) {
    data = tableData
    // tableData rows are sliced from the sheet grid at tableRange's
    // offset, and that grid itself starts at the worksheet's !ref.s.
    // Absolute cell = !ref.s + tableRange.start + index within tableData.
    try {
      const wb = XLSX.read(fileBuffer, { type: 'array' })
      const ws = wb.Sheets[sheetName]
      if (ws && ws['!ref']) {
        const sr = XLSX.utils.decode_range(ws['!ref']).s
        CELL_ORIGIN = {
          r: sr.r + (tableRange?.startRow || 0),
          c: sr.c + (tableRange?.startCol || 0),
        }
      }
    } catch { /* keep 0,0 — refs stay table-relative */ }
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
    CELL_ORIGIN = { r: range.s.r, c: range.s.c }
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
      // Value cells (currency amounts, dates, percentages) are never labels.
      if (getValueType(labelStr) !== 'text') continue
      const context = getContextualClues(data, R, C, 2)
      let valueHit = null, valueLoc = null, direction = null
      for (let off = 1; off <= MAX_LOOKAHEAD && C + off <= boundaries.endCol; off++) {
        const v = data[R]?.[C + off]
        const nv = normalizeDetectedCellValue(v)
        if (nv !== null) {
          valueHit = nv
          valueLoc = { row: R, col: C + off }
          direction = 'horizontal'
          processedCells.add(`${R}_${C + off}`)
          break
        }
      }
      if (!valueHit) {
        for (let off = 1; off <= MAX_LOOKAHEAD && R + off <= boundaries.endRow; off++) {
          const v = data[R + off]?.[C]
          const nv = normalizeDetectedCellValue(v)
          if (nv !== null) {
            valueHit = nv
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
        const pairKey = `${valueHit}|${R}|${C}`
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
      // Value cells (currency amounts, dates, percentages) are never labels —
      // otherwise "$497,376.00" can "label" the neighbouring PVIF cell.
      if (getValueType(labelStr) !== 'text') continue
      const context = getContextualClues(data, R, C, 2)
      let valueHit = null, valueLoc = null, direction = null
      for (let off = 1; off <= MAX_LOOKAHEAD && C + off <= boundaries.endCol; off++) {
        const v = data[R]?.[C + off]
        const nv = normalizeDetectedCellValue(v)
        if (nv !== null) {
          valueHit = nv; valueLoc = { row: R, col: C + off }
          direction = 'horizontal'; processedCells.add(`${R}_${C + off}`)
          break
        }
      }
      if (!valueHit) {
        for (let off = 1; off <= MAX_LOOKAHEAD && R + off <= boundaries.endRow; off++) {
          const v = data[R + off]?.[C]
          const nv = normalizeDetectedCellValue(v)
          if (nv !== null) {
            valueHit = nv; valueLoc = { row: R + off, col: C }
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
        const pairKey = `${valueHit}|${R}|${C}`
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

  // Fallback: counterparty/issuer labels are easy to miss in Phase2.
  // If no instrument name was found anywhere, scan explicitly for them.
  const hasName = detectedFields.instrument_name || detectedFields.bond_name ||
    detectedFields.instrumentName || additionalFields.instrument_name ||
    additionalFields.bond_name
  if (!hasName) {
    const NAME_LABEL = /counterparty|issuer|obligor|borrower|company name/i
    outer:
    for (let R = boundaries.startRow; R <= boundaries.endRow; R++) {
      for (let C = boundaries.startCol; C <= boundaries.endCol; C++) {
        const label = data[R]?.[C]
        if (!label || !NAME_LABEL.test(String(label))) continue
        for (const [dr, dc] of [[0, 1], [1, 0]]) {
          const v = normalizeDetectedCellValue(data[R + dr]?.[C + dc])
          if (v !== null && typeof v !== 'object' && !/^\d/.test(String(v))) {
            additionalFields.instrument_name = v
            additionalMetadata.instrument_name = {
              location: rowColToCellRef(R + dr, C + dc), confidence: 0.6,
              originalLabel: String(label).trim(), detectedFrom: 'fallback',
            }
            console.log(`[Fallback] instrument_name = "${v}" (counterparty label)`)
            break outer
          }
        }
      }
    }
  }

  // Fallback: standalone ISO currency-code cells (e.g. a bare "USD" in the
  // valuation block). Only set when EXACTLY ONE distinct code appears —
  // never guess between USD/ZWG/etc.
  const hasCurrency = detectedFields.currency || additionalFields.currency
  if (!hasCurrency) {
    const codes = new Set()
    for (let R = boundaries.startRow; R <= boundaries.endRow; R++) {
      for (let C = boundaries.startCol; C <= boundaries.endCol; C++) {
        const cell = data[R]?.[C]
        if (typeof cell !== 'string') continue
        const t = cell.trim()
        if (/^[A-Z]{3}$/.test(t) && KNOWN_ISO_CODES.has(t) && !NON_CURRENCY_WORDS.has(t)) {
          codes.add(t)
        }
      }
    }
    if (codes.size === 1) {
      const code = [...codes][0]
      additionalFields.currency = code
      additionalMetadata.currency = {
        location: 'sheet', confidence: 0.6,
        originalLabel: 'currency code cell', detectedFrom: 'fallback',
      }
      console.log(`[Fallback] currency = "${code}" (single ISO code in sheet)`)
    }
  }

  console.log('=== Detection result ===')
  console.log('Required:', Object.keys(detectedFields))
  console.log('Additional:', Object.keys(additionalFields))
  console.log('Missing:', missingFields)
  const tabularRecords = detectTabularRecords(data, boundaries)
  if (tabularRecords.length) {
    console.log(`[Tabular] ${tabularRecords.length} instrument row(s) under header row`)
  }
  return {
    fields: detectedFields,
    fieldsWithMetadata: detectedMetadata,
    currencies: detectCurrencies(data),
    missingFields,
    additionalFields,
    additionalFieldsWithMetadata: additionalMetadata,
    tabularRecords,
    warnings: []
  }
}