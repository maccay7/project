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

const ENUM_FIELD_NAMES = new Set([
  'Frequency', 'Coupon Frequency', 'Interest Pmt Frequency',
  'InterestPmtFrequency', 'Payment Frequency', 'CouponFrequency',
  'Interest Payment Frequency', 'Coupon Payment Frequency',
  'InterestFrequency', 'PaymentFrequency'
])

// ============================================================================
// Currency helpers
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

function buildCurrencyTokens(code) {
  const symbols = CURRENCY_SYMBOLS[code] || []
  const names = CURRENCY_NAMES[code] || []
  return { code, symbols, names }
}

function isCurrencyCodeStrict(value) {
  if (!value) return false
  const s = String(value).trim().toUpperCase()
  if (!/^[A-Z]{3}$/.test(s)) return false
  if (NON_CURRENCY_WORDS.has(s)) return false
  return KNOWN_ISO_CODES.has(s)
}

function findCurrenciesInText(text) {
  if (!text) return []
  const s = String(text)
  const found = new Set()
  const upper = s.toUpperCase()

  const wordRe = /\b([A-Z]{3})\b/g
  let m
  while ((m = wordRe.exec(upper)) !== null) {
    const code = m[1]
    if (KNOWN_ISO_CODES.has(code)) found.add(code)
  }

  for (const [code, syms] of Object.entries(CURRENCY_SYMBOLS)) {
    for (const sym of syms) {
      if (sym && s.includes(sym)) { found.add(code); break }
    }
  }

  const lower = s.toLowerCase()
  for (const [code, names] of Object.entries(CURRENCY_NAMES)) {
    for (const n of names) {
      if (!n) continue
      const re = new RegExp(`(^|[^a-z])${n}([^a-z]|$)`)
      if (re.test(lower)) { found.add(code); break }
    }
  }

  return Array.from(found)
}

// ============================================================================
// Currency filter
// ============================================================================
function scanForCurrencyMentions(data, code, tokens) {
  const mentions = []
  for (let R = 0; R < data.length; R++) {
    const row = data[R]
    if (!row) continue
    for (let C = 0; C < row.length; C++) {
      const cell = row[C]
      if (cell === null || cell === undefined || cell === '') continue
      const s = String(cell).trim()
      if (s === '') continue

      const upper = s.toUpperCase()
      const codeWordBoundary = new RegExp(`(^|[^A-Z])${code}([^A-Z]|$)`)
      if (codeWordBoundary.test(upper)) {
        mentions.push({ row: R, col: C, raw: s, type: 'code', code })
        continue
      }

      if (tokens.symbols.length) {
        const hitSymbol = tokens.symbols.some(sym => sym && s.includes(sym))
        if (hitSymbol) {
          mentions.push({ row: R, col: C, raw: s, type: 'symbol', code })
          continue
        }
      }

      if (tokens.names.length) {
        const lower = s.toLowerCase()
        const hitName = tokens.names.some(n =>
          n && (lower === n || new RegExp(`(^|[^a-z])${n}([^a-z]|$)`).test(lower))
        )
        if (hitName) {
          mentions.push({ row: R, col: C, raw: s, type: 'name', code })
          continue
        }
      }
    }
  }
  return mentions
}

function findSectionEnd(data, startRow) {
  for (let R = startRow + 1; R < data.length; R++) {
    const row = data[R] || []
    const nonEmpty = row.filter(c => c !== null && c !== undefined && String(c).trim() !== '').length
    if (nonEmpty === 0) return R - 1

    if (nonEmpty <= 2) {
      const cellTexts = row
        .filter(c => c !== null && c !== undefined && String(c).trim() !== '')
        .map(c => String(c).trim())
      const looksLikeTitle = cellTexts.length > 0 && cellTexts.every(t =>
        t.length < 60 && !/^[\d.,%$€£¥₹-]+$/.test(t)
      )
      if (looksLikeTitle) return R - 1
    }
  }
  return data.length - 1
}

function isExchangeRateSectionTitle(titleText, currenciesInTitle) {
  if (!titleText) return false
  if (!currenciesInTitle || currenciesInTitle.length < 2) return false
  const lower = titleText.toLowerCase()
  return /(exch|exchange|fx\b|forex|conversion|convert|\brate\b|\bto\b|→|=|\/)/i.test(lower)
}

function determineMentionScope(data, mention, selectedCode) {
  if (mention.type === 'symbol') {
    return {
      start: Math.max(0, mention.row - 1),
      end: Math.min(data.length - 1, mention.row + 1),
      source: mention,
      skip: false
    }
  }

  const row = data[mention.row] || []
  const nonEmpty = row.filter(c => c !== null && c !== undefined && String(c).trim() !== '').length
  const isSectionTitleLike = nonEmpty <= 3 && mention.col < 3

  if (isSectionTitleLike) {
    const titleText = row.map(c => String(c == null ? '' : c).trim()).filter(Boolean).join(' ')
    const currenciesInTitle = findCurrenciesInText(titleText)

    if (isExchangeRateSectionTitle(titleText, currenciesInTitle)) {
      if (!(currenciesInTitle.length === 1 && currenciesInTitle[0] === selectedCode)) {
        return { start: -1, end: -1, source: mention, skip: true }
      }
    }

    const sectionEnd = findSectionEnd(data, mention.row)
    return { start: mention.row, end: sectionEnd, source: mention, skip: false }
  }

  return {
    start: Math.max(0, mention.row - 2),
    end: Math.min(data.length - 1, mention.row + 2),
    source: mention,
    skip: false
  }
}

function mergeRanges(ranges) {
  if (!ranges.length) return []
  const sorted = [...ranges].sort((a, b) => a.start - b.start)
  const merged = [{ start: sorted[0].start, end: sorted[0].end }]
  for (let i = 1; i < sorted.length; i++) {
    const last = merged[merged.length - 1]
    const curr = sorted[i]
    if (curr.start <= last.end + 1) {
      last.end = Math.max(last.end, curr.end)
    } else {
      merged.push({ start: curr.start, end: curr.end })
    }
  }
  return merged
}

function filterDataByCurrency(data, currencyFilter) {
  const targetCode = normalizeCurrencyToCode(currencyFilter)
  if (!targetCode) {
    return { data, usedFilter: false, matchedMentions: [] }
  }

  const tokens = buildCurrencyTokens(targetCode)
  const mentions = scanForCurrencyMentions(data, targetCode, tokens)

  if (mentions.length === 0) {
    return { data: [], usedFilter: true, matchedMentions: [] }
  }

  const scopes = mentions.map(m => determineMentionScope(data, m, targetCode))
  const keptScopes = scopes.filter(s => !s.skip)

  if (keptScopes.length === 0) {
    return { data: [], usedFilter: true, matchedMentions: mentions }
  }

  const merged = mergeRanges(keptScopes.map(s => ({ start: s.start, end: s.end })))

  const keep = new Set()
  for (const r of merged) {
    for (let i = r.start; i <= r.end; i++) keep.add(i)
  }

  const filtered = data.filter((_, i) => keep.has(i))
  return { data: filtered, usedFilter: true, matchedMentions: mentions }
}

// ============================================================================
// Table boundary / orientation
// ============================================================================
function detectTableBoundaries(data) {
  if (!data || data.length === 0) {
    return { startRow: 0, endRow: data.length - 1, startCol: 0, endCol: 0 }
  }

  let startRow = 0
  for (let r = 0; r < data.length; r++) {
    if (data[r].some(cell => cell && String(cell).trim() !== '')) { startRow = r; break }
  }

  let endRow = data.length - 1
  for (let r = data.length - 1; r >= startRow; r--) {
    if (data[r].some(cell => cell && String(cell).trim() !== '')) { endRow = r; break }
  }

  let startCol = 0
  for (let c = 0; c < data[0].length; c++) {
    let hasContent = false
    for (let r = startRow; r <= endRow; r++) {
      if (data[r] && data[r][c] && String(data[r][c]).trim() !== '') { hasContent = true; break }
    }
    if (hasContent) { startCol = c; break }
  }

  let endCol = data[0].length - 1
  for (let c = data[0].length - 1; c >= startCol; c--) {
    let hasContent = false
    for (let r = startRow; r <= endRow; r++) {
      if (data[r] && data[r][c] && String(data[r][c]).trim() !== '') { hasContent = true; break }
    }
    if (hasContent) { endCol = c; break }
  }

  return { startRow, endRow, startCol, endCol }
}

function isNumeric(value) {
  if (value === null || value === undefined || value === '') return false
  const str = String(value).replace(/[%,\s]/g, '')
  return !isNaN(parseFloat(str)) && isFinite(str)
}

function detectTableOrientation(data, boundaries) {
  const { startRow, endRow, startCol, endCol } = boundaries
  let firstColLabels = 0
  let firstRowLabels = 0
  for (let r = startRow; r <= endRow; r++) {
    const cell = data[r] && data[r][startCol] ? String(data[r][startCol]).trim() : ''
    if (cell && cell.length > 0 && cell.length < 50 && !isNumeric(cell)) firstColLabels++
  }
  for (let c = startCol; c <= endCol; c++) {
    const cell = data[startRow] && data[startRow][c] ? String(data[startRow][c]).trim() : ''
    if (cell && cell.length > 0 && cell.length < 50 && !isNumeric(cell)) firstRowLabels++
  }
  return firstColLabels > firstRowLabels ? 'vertical' : 'horizontal'
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

// ============================================================================
// Header regions
// ============================================================================
function detectHeaderRegions(data, boundaries) {
  const { startRow, endRow, startCol, endCol } = boundaries

  const rowAnalysis = []
  for (let R = startRow; R <= endRow; R++) {
    let textCells = 0, totalCells = 0
    const cells = []
    const rowLen = data[R]?.length || 0
    for (let C = startCol; C <= endCol && C < rowLen; C++) {
      const v = data[R][C]
      const s = v === null || v === undefined ? '' : String(v).trim()
      if (s === '') continue
      totalCells++
      const cleaned = s.replace(/[%,\s$€£¥₹]/g, '')
      const numeric = !isNaN(parseFloat(cleaned)) && isFinite(cleaned)
      if (!numeric) textCells++
      cells.push({ row: R, col: C, value: v })
    }
    const isHeaderRow = totalCells >= 2 && (textCells / totalCells) >= 0.6
    rowAnalysis.push({ row: R, isHeaderRow, cells, totalCells, textCells })
  }

  const colAnalysis = []
  for (let C = startCol; C <= endCol; C++) {
    let textCells = 0, totalCells = 0
    const cells = []
    for (let R = startRow; R <= endRow; R++) {
      if (!data[R] || C >= data[R].length) continue
      const v = data[R][C]
      const s = v === null || v === undefined ? '' : String(v).trim()
      if (s === '') continue
      totalCells++
      const cleaned = s.replace(/[%,\s$€£¥₹]/g, '')
      const numeric = !isNaN(parseFloat(cleaned)) && isFinite(cleaned)
      if (!numeric) textCells++
      cells.push({ row: R, col: C, value: v })
    }
    const isHeaderCol = totalCells >= 2 && (textCells / totalCells) >= 0.6
    colAnalysis.push({ col: C, isHeaderCol, cells, totalCells, textCells })
  }

  const horizontalHeaderCells = []
  let rowGroup = []
  const flushRowGroup = () => {
    if (rowGroup.length === 0 || rowGroup.length > 2) { rowGroup = []; return }
    for (const ra of rowGroup) {
      for (const c of ra.cells) {
        if (c.col < startCol || c.col > endCol) continue
        horizontalHeaderCells.push({ row: c.row, col: c.col, value: c.value })
      }
    }
    rowGroup = []
  }
  for (const ra of rowAnalysis) { if (ra.isHeaderRow) rowGroup.push(ra); else flushRowGroup() }
  flushRowGroup()

  const verticalHeaderCells = []
  let colGroup = []
  const flushColGroup = () => {
    if (colGroup.length === 0 || colGroup.length > 2) { colGroup = []; return }
    for (const ca of colGroup) {
      for (const c of ca.cells) {
        if (c.row < startRow || c.row > endRow) continue
        verticalHeaderCells.push({ row: c.row, col: c.col, value: c.value })
      }
    }
    colGroup = []
  }
  for (const ca of colAnalysis) { if (ca.isHeaderCol) colGroup.push(ca); else flushColGroup() }
  flushColGroup()

  return { horizontalHeaderCells, verticalHeaderCells, rowAnalysis, colAnalysis }
}

// ============================================================================
// Label-like value detection
// ============================================================================
function isLabelLikeValue(value) {
  if (value === null || value === undefined) return false
  const s = String(value).trim()
  if (!s) return false

  if (/^[\d.,%$€£¥₹+\-()\s]+$/.test(s)) return false
  if (isDateLike(s)) return false

  const keywordRe = /\b(name|date|rate|value|amount|price|yield|coupon|discount|maturity|issue|currency|days|count|total|instrument|bond|security|frequency|principal|face|par|tenor|term|spread|margin|duration|convexity|payment|redemption|settlement|valuation|status|type|code|id|number|balance|period|month|year|week|day)\b/i
  if (keywordRe.test(s) && s.length < 60) return true

  const words = s.split(/\s+/).filter(Boolean)
  if (words.length >= 2 && words.length <= 6 && !/\d/.test(s)) {
    const titleCaseCount = words.filter(w => /^[A-Z][a-z]/.test(w)).length
    if (titleCaseCount >= Math.ceil(words.length * 0.6)) return true
  }

  return false
}

// ============================================================================
// Split a field name into words
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

// ============================================================================
// Auto-expand a required column into a rich set of variations
// ============================================================================
function expandFieldNameVariations(fieldName) {
  if (!fieldName) return []
  const variations = new Set()
  const raw = String(fieldName).trim()
  if (!raw) return []

  variations.add(raw.toLowerCase())

  const words = splitIntoWords(raw)
  if (words.length > 1) {
    variations.add(words.join(' ').toLowerCase())
    variations.add(words.join('').toLowerCase())
    variations.add(words.join('-').toLowerCase())
    variations.add(words.join('_').toLowerCase())
  }

  const lower = raw.toLowerCase()

  if (lower.includes('face') || lower.includes('principal') ||
      lower.includes('par') || lower.includes('notional') || lower.includes('nominal')) {
    ;[
      'face value','facevalue','face-value','face_value','face amount','faceamount',
      'principal','principal amount','principalamount','par value','parvalue','par',
      'notional amount','notionalamount','notional','nominal value','nominalvalue','nominal'
    ].forEach(v => variations.add(v))
  }

  if (lower.includes('couponrate') || lower === 'couponrate' ||
      lower.includes('coupon rate') || lower.includes('interest rate') ||
      lower === 'interestrate' || lower === 'rate' || lower === 'coupon') {
    ;[
      'coupon rate','couponrate','coupon-rate','coupon_rate','coupon',
      'interest rate','interestrate','interest-rate','interest_rate',
      'rate','annual rate','annualrate','nominal rate','nominalrate',
      'fixed rate','fixedrate','floating rate','floatingrate'
    ].forEach(v => variations.add(v))
  }

  if (lower.includes('yield') || lower === 'ytm' || lower === 'ytc' || lower === 'ytw') {
    ;['yield','ytm','yield to maturity','yieldtomaturity','yield-to-maturity','ytc','ytw'].forEach(v => variations.add(v))
  }

  if (lower.includes('frequency') || lower.includes('freq') || lower.includes('fequency')) {
    ;[
      'frequency','freq','fequency',
      'coupon frequency','couponfrequency','coupon-frequency',
      'interest frequency','interestfrequency','interest-frequency',
      'interest pmt frequency','interest pmt fequency',
      'interest payment frequency','interestpaymentfrequency',
      'payment frequency','paymentfrequency','pmt frequency','pmtfrequency'
    ].forEach(v => variations.add(v))
  }

  if (lower.includes('maturity')) {
    ;['maturity date','maturitydate','maturity-date','maturity',
      'redemption date','redemptiondate','due date','duedate',
      'expiry date','expirydate','maturity_date'].forEach(v => variations.add(v))
  }

  if (lower.includes('issue') && lower.includes('date')) {
    ;['issue date','issuedate','issue-date','issue_date','issuance date','issuancedate',
      'start date','startdate','effective date','effectivedate'].forEach(v => variations.add(v))
  }

  if (lower.includes('valuation') && lower.includes('date')) {
    ;['valuation date','valuationdate','valuation-date','valuation_date',
      'pricing date','pricingdate','as of date','asofdate',
      'value date','valuedate'].forEach(v => variations.add(v))
  }

  if (lower.includes('settlement') && lower.includes('date')) {
    ;['settlement date','settlementdate','settle date','settledate'].forEach(v => variations.add(v))
  }

  if ((lower.includes('accrued') && lower.includes('interest')) ||
      lower === 'accruedinterest' || lower === 'accrued interest') {
    ;['accrued interest','accruedinterest','accrued-interest','accrued_interest',
      'interest accrued','interestaccrued','interest-accrued',
      'accrued coupon','accruedcoupon','interest accrual','interestaccrual'].forEach(v => variations.add(v))
  }

  if (lower.includes('bondname') || (lower.includes('bond') && lower.includes('name'))) {
    ;['bond name','bondname','counterparty','issuer','instrument name','instrumentname',
      'security name','securityname','name'].forEach(v => variations.add(v))
  }
  if (lower.includes('tbillname') || lower.includes('tbill') || lower.includes('t-bill')) {
    ;['t-bill name','tbillname','t bill name','counterparty','issuer',
      'instrument name','instrumentname','name'].forEach(v => variations.add(v))
  }
  if (lower === 'instrumentname' || lower === 'instrument name' || lower === 'instrument') {
    ;['instrument name','instrumentname','instrument','counterparty','issuer',
      'bond name','bondname','security name','securityname','name'].forEach(v => variations.add(v))
  }

  return Array.from(variations)
}

// ============================================================================
// Best-match selection
// ============================================================================
function findBestMatchingField(label, candidateFields, fieldVariations) {
  const normalizedLabel = String(label).toLowerCase().trim()
  if (!normalizedLabel) return null

  let bestField = null
  let bestScore = 0

  for (const fieldName of candidateFields) {
    const variations = fieldVariations[fieldName] || []
    for (const variation of variations) {
      const nv = String(variation).toLowerCase().trim()
      if (!nv) continue

      let score = 0
      if (normalizedLabel === nv) {
        score = nv.length + 1000
      } else if (normalizedLabel.includes(nv)) {
        score = nv.length
        if (normalizedLabel.startsWith(nv)) score += 5
      } else if (nv.includes(' ') && normalizedLabel.includes(nv.split(' ')[0])) {
        score = nv.split(' ')[0].length
      }

      if (score > bestScore) {
        bestScore = score
        bestField = fieldName
      }
    }
  }

  return bestField
}

// ============================================================================
// NEW — find the first non-empty value cell to the right of a label,
// checking up to `maxOffset` columns. Fixes the "gap" layout issue.
// ============================================================================
function findAdjacentValueRight(data, R, C, maxOffset, endCol) {
  for (let offset = 1; offset <= maxOffset && C + offset <= endCol; offset++) {
    const v = data[R][C + offset]
    if (v !== null && v !== undefined && String(v).trim() !== '') {
      return { value: v, offset }
    }
  }
  return null
}

function findAdjacentValueDown(data, R, C, maxOffset, endRow) {
  for (let offset = 1; offset <= maxOffset && R + offset <= endRow; offset++) {
    const v = data[R + offset]?.[C]
    if (v !== null && v !== undefined && String(v).trim() !== '') {
      return { value: v, offset }
    }
  }
  return null
}

// ============================================================================
// MAIN
// ============================================================================
export function autoDetectInstrumentFields(fileBuffer, sheetName, requiredColumns, instrumentType, tableRange = null, tableData = null, customCurrency = null) {
  console.log('=== autoDetectInstrumentFields Started ===')
  console.log('Sheet Name:', sheetName, '| Instrument:', instrumentType)
  console.log('Required Columns:', requiredColumns)
  console.log('Table Range:', tableRange, '| Table Data Provided:', !!tableData)
  console.log('Custom Currency Filter:', customCurrency)

  if (!fileBuffer || !sheetName) {
    throw new Error('File buffer and sheet name are required')
  }

  const currencyFilter = customCurrency ? String(customCurrency).trim() : null
  const normalizedCurrencyCode = currencyFilter ? normalizeCurrencyToCode(currencyFilter) : null

  let data = []

  if (tableData && Array.isArray(tableData) && tableData.length > 0) {
    data = tableData
  } else {
    const workbook = XLSX.read(fileBuffer, { type: 'array', cellStyles: true, cellFormula: true, cellDates: true, cellNF: true })
    const worksheet = workbook.Sheets[sheetName]

    if (!worksheet) {
      return {
        fields: {}, fieldsWithMetadata: {}, currencies: [],
        missingFields: requiredColumns,
        headerRegions: { horizontalHeaderCells: [], verticalHeaderCells: [], rowAnalysis: [], colAnalysis: [] },
        additionalFields: {}
      }
    }

    let range = worksheet['!ref']
      ? XLSX.utils.decode_range(worksheet['!ref'])
      : { s: { r: 0, c: 0 }, e: { r: 0, c: 0 } }

    let maxRow = 0, maxCol = 0
    for (const cellAddress in worksheet) {
      if (cellAddress.startsWith('!')) continue
      const cellRef = XLSX.utils.decode_cell(cellAddress)
      if (cellRef.r > maxRow) maxRow = cellRef.r
      if (cellRef.c > maxCol) maxCol = cellRef.c
    }
    if (maxRow > range.e.r) range.e.r = maxRow
    if (maxCol > range.e.c) range.e.c = maxCol

    const MAX_ROWS = 1000, MAX_COLS = 100
    if (range.e.r >= MAX_ROWS) range.e.r = MAX_ROWS - 1
    if (range.e.c >= MAX_COLS) range.e.c = MAX_COLS - 1

    for (let R = range.s.r; R <= range.e.r; R++) {
      const row = []
      for (let C = range.s.c; C <= range.e.c; C++) {
        const cellAddress = XLSX.utils.encode_cell({ r: R, c: C })
        const cell = worksheet[cellAddress]
        row.push(cell ? (cell.w ?? cell.v ?? '') : '')
      }
      data.push(row)
    }
  }

  if (currencyFilter) {
    const filterResult = filterDataByCurrency(data, currencyFilter)
    if (filterResult.usedFilter) {
      data = filterResult.data
    }
  }

  // DETECTION MODE
  let tableBoundaries
  const isWholeSheetScan = (!tableRange && !tableData)
  const isSelectedTableScan = (tableRange && tableData)

  if (isWholeSheetScan) {
    let maxRow = data.length - 1
    let maxCol = 0
    for (let i = 0; i < data.length; i++) {
      const len = (data[i] && data[i].length) || 0
      if (len - 1 > maxCol) maxCol = len - 1
    }
    tableBoundaries = { startRow: 0, endRow: maxRow, startCol: 0, endCol: maxCol }
    console.log('=== MODE: WHOLE SHEET SCAN ===')
  } else if (isSelectedTableScan) {
    tableBoundaries = {
      startRow: 0, endRow: data.length - 1,
      startCol: 0, endCol: data[0]?.length - 1 || 0
    }
    console.log('=== MODE: SELECTED TABLE SCAN ===')
  } else if (tableRange) {
    tableBoundaries = {
      startRow: tableRange.startRow, endRow: tableRange.endRow,
      startCol: tableRange.startCol, endCol: tableRange.endCol
    }
    console.log('=== MODE: PROVIDED RANGE ===')
  } else {
    tableBoundaries = detectTableBoundaries(data)
    console.log('=== MODE: FALLBACK ===')
  }

  detectTableOrientation(data, tableBoundaries)
  const headerRegions = detectHeaderRegions(data, tableBoundaries)

  // ---- field variations ----
  const fieldVariations = {
    'Instrument Name': ['instrument name','name','bond name','security name','security','t-bill name'],
    'Instrument ID': ['instrument id','id','security id','bond id','t-bill id'],
    'Instrument Code': ['instrument code','code','security code'],
    'Security ID': ['security id','security identifier','sec id'],
    'ISIN': ['isin','isin code'],
    'CUSIP': ['cusip','cusip code'],
    'Bloomberg Ticker': ['bloomberg ticker','bloomberg','bbg ticker'],
    'Reuters/Refinitiv Ticker': ['reuters ticker','refinitiv ticker','reuters'],
    'Counterparty': ['counterparty','issuer','borrower','party','entity','counter party','client','customer'],
    'Issuer': ['issuer','borrower','counterparty','issuing entity','issuing party'],
    'Parent Company': ['parent company','parent','holding company'],
    'Issuer Country': ['issuer country','country of issue','issuing country'],
    'Country': ['country','jurisdiction','nation'],
    'Currency': ['currency','denomination','ccy','currency code','curr','base currency','local currency','reporting currency'],
    'Currency Code': ['currency code','currency','ccy','curr'],
    'Base Currency': ['base currency','reporting currency','functional currency'],
    'Local Currency': ['local currency','denomination currency'],
    'Reporting Currency': ['reporting currency','base currency','functional currency'],
    'Exchange Rate': ['exchange rate','exch rate','fx rate','forex rate','conversion rate','exch','spot rate','forward rate','fx pair'],
    'FX Rate': ['fx rate','exchange rate','forex rate','conversion rate'],
    'FX Pair': ['fx pair','currency pair'],
    'Valuation Date': ['valuation date','pricing date','as of date','value date'],
    'Pricing Date': ['pricing date','valuation date','price date'],
    'Trade Date': ['trade date','transaction date','deal date'],
    'Settlement Date': ['settlement date','settle date'],
    'Issue Date': ['issue date','issuance date','start date','effective date','origination date','issue','issuing date','commencement date'],
    'Effective Date': ['effective date','start date','issue date','commencement date','value date'],
    'Start Date': ['start date','effective date','issue date','accrual start date','commencement date'],
    'End Date': ['end date','maturity date','termination date','expiry date'],
    'Maturity Date': ['maturity date','maturity','due date','expiry date','redemption date','repayment date','final maturity date'],
    'Tenor': ['tenor','term','duration'],
    'Term': ['term','tenor','duration'],
    'Term in Days': ['term in days','tenor days','days','duration days'],
    'Term in Months': ['term in months','tenor months','months'],
    'Term in Years': ['term in years','tenor years','years'],
    'Business Day Convention': ['business day convention','bdc','day convention'],
    'Day Count Convention': ['day count convention','day count','dcc','day count basis'],
    'Calendar': ['calendar','holiday calendar'],
    'Settlement Lag': ['settlement lag','settlement days'],
    'Asset Class': ['asset class','classification'],
    'Classification': ['classification','category'],
    'Market': ['market','exchange','venue'],
    'Market Sector': ['market sector','sector','industry'],
    'Portfolio': ['portfolio','portfolio name','book'],
    'Portfolio Name': ['portfolio name','portfolio'],
    'Book': ['book','portfolio','trading book'],
    'Position': ['position','holding'],
    'Quantity': ['quantity','amount','units','position'],
    'Units': ['units','quantity','amount'],
    'Nominal Amount': ['nominal amount','notional amount','face value','principal','par value'],
    'Face Value': ['face value','par value','principal','face amount','par amount','nominal value','notional','nominal amount','principal amount','investment amount'],
    'FaceValue': ['face value','principal','par value','notional','facevalue'],
    'Principal': ['principal','face value','par value','nominal amount','notional','investment amount','principal amount'],
    'Par Value': ['par value','face value','principal','par amount'],
    'Nominal Value': ['nominal value','face value','par value','notional','nominal amount'],
    'Notional': ['notional','nominal value','face value','principal','notional amount'],
    'Outstanding Principal': ['outstanding principal','current principal','remaining principal'],
    'Current Principal': ['current principal','outstanding principal','remaining principal'],
    'Original Principal': ['original principal','issue amount','initial principal'],
    'Carrying Value': ['carrying value','book value','carrying amount','carrying','book amount','amortised cost'],
    'Book Value': ['book value','carrying value','amortised cost'],
    'Fair Value': ['fair value','fv','market value','fair market value','current value'],
    'Market Value': ['market value','fair value','current value','fair market value'],
    'Present Value': ['present value','pv','current value','present amount'],
    'Amortised Cost': ['amortised cost','carrying value','book value'],
    'Impairment': ['impairment','impairment loss','impairment charge','credit impairment','provision'],
    'Accrued Interest': ['accrued interest','accrued','interest accrued','accrued coupon','interest accrual','accrued amount'],
    'Clean Price': ['clean price','price','bond price','quoted price'],
    'Dirty Price': ['dirty price','full price','gross price'],
    'Price': ['price','market price','clean price','dirty price','bond price','purchase price','unit price'],
    'Yield': ['yield','ytm','yield to maturity','current yield','running yield','internal rate of return'],
    'Discount Rate': ['discount rate','discount','discount yield'],
    'DiscountRate': ['discount rate','discount','discount yield'],
    'Interest Rate': ['interest rate','coupon rate','coupon','annual rate','interest','nominal rate','fixed rate','floating rate'],
    'InterestRate': ['interest rate','coupon rate','coupon','annual rate','interest','nominal rate','fixed rate','floating rate'],
    'Interest Accrued': ['interest accrued','accrued interest','interest accrued to','accrued interest to'],
    'InterestAccrued': ['interest accrued','accrued interest','interest accrued to','accrued interest to'],
    'Interest Pmt Frequency': ['interest pmt frequency','interest payment frequency','coupon frequency','payment frequency','pmt frequency','interest pmt fequency'],
    'InterestPmtFrequency': ['interest pmt frequency','interest payment frequency','coupon frequency','payment frequency','pmt frequency','interest pmt fequency'],
    'Frequency': ['frequency','interest pmt frequency','interest payment frequency','coupon frequency','payment frequency','pmt frequency','interest pmt fequency'],
    'Reference Rate': ['reference rate','benchmark rate','index rate','base rate'],
    'Benchmark Rate': ['benchmark rate','reference rate','index rate','base rate'],
    'Spread': ['spread','margin','credit spread','currency spread','basis points'],
    'Margin': ['margin','spread','index margin','basis points'],
    'Credit Spread': ['credit spread','spread','yield spread','credit margin'],
    'Currency Spread': ['currency spread','spread','fx spread'],
    'Status': ['status','state'],
    'Bond Name': ['bond name','instrument name','name','security name'],
    'BondName': ['bond name','instrument name','name','security name','counterparty','issuer'],
    'TBillName': ['t-bill name','instrument name','name','security name','counterparty','issuer'],
    'Coupon Rate': ['coupon rate','interest rate','coupon','annual coupon','fixed rate','nominal rate'],
    'CouponRate': ['coupon rate','interest rate','coupon','annual coupon','fixed rate','nominal rate'],
    'Coupon Frequency': ['coupon frequency','frequency','payment frequency','interest frequency','coupon freq','pmt frequency','interest pmt frequency'],
    'CouponFrequency': ['coupon frequency','frequency','payment frequency','interest frequency','coupon freq','pmt frequency','interest pmt frequency'],
    'Coupon Date': ['coupon date','payment date','interest payment date'],
    'Coupon': ['coupon','coupon rate','interest rate'],
    'Coupon Amount': ['coupon amount','interest amount'],
    'Coupon Payment': ['coupon payment','coupon amount','interest amount'],
    'Annual Coupon': ['annual coupon','annual interest','coupon amount'],
    'Accrued Coupon': ['accrued coupon','accrued interest'],
    'Redemption Value': ['redemption value','maturity value','redemption amount','principal','face value','par value','maturity amount','redemption','principal amount'],
    'RedemptionValue': ['redemption value','maturity value','redemption amount','principal','face value','par value','maturity amount','redemption','principal amount'],
    'Maturity Value': ['maturity value','redemption value','redemption amount'],
    'MaturityDate': ['maturity date','maturity','due date','expiry date','redemption date'],
    'IssueDate': ['issue date','issuance date','start date','effective date'],
    'ValuationDate': ['valuation date','pricing date','as of date','value date'],
    'Total Value': ['total value','value','calculated value'],
    'Instrument Count': ['instrument count','count','number of instruments','quantity'],
    'Amount': ['amount','value','investment amount','purchase amount','total amount'],
    'Instrument': ['counterparty','instrument name','bond name','t-bill name','security name','issuer','borrower','party','entity','counter party']
  }

  for (const requiredField of requiredColumns) {
    const autoVars = expandFieldNameVariations(requiredField)
    if (!fieldVariations[requiredField]) {
      fieldVariations[requiredField] = autoVars
    } else {
      for (const v of autoVars) {
        if (!fieldVariations[requiredField].includes(v)) fieldVariations[requiredField].push(v)
      }
    }
  }

  const synonymMapping = {
    'Face Value': ['Principal','Par Value','Nominal Value','Notional Amount'],
    'Principal': ['Face Value','Par Value','Nominal Value','Notional Amount'],
    'Par Value': ['Face Value','Principal','Nominal Value','Notional Amount'],
    'Nominal Value': ['Face Value','Principal','Par Value','Notional Amount'],
    'Notional Amount': ['Face Value','Principal','Par Value','Nominal Value'],
    'Maturity Date': ['Redemption Date','Due Date','Expiry Date'],
    'Redemption Date': ['Maturity Date','Due Date','Expiry Date'],
    'Due Date': ['Maturity Date','Redemption Date','Expiry Date'],
    'Interest Rate': ['Coupon Rate','Coupon','Rate'],
    'Coupon Rate': ['Interest Rate','Coupon','Rate'],
    'Coupon': ['Interest Rate','Coupon Rate','Rate'],
    'Fair Value': ['Market Value','Current Value'],
    'Market Value': ['Fair Value','Current Value'],
    'Current Value': ['Fair Value','Market Value'],
    'Carrying Value': ['Book Value','Amortised Cost'],
    'Book Value': ['Carrying Value','Amortised Cost'],
    'Amortised Cost': ['Carrying Value','Book Value'],
    'Present Value': ['PV'],
    'PV': ['Present Value'],
    'Exchange Rate': ['FX Rate','Conversion Rate'],
    'FX Rate': ['Exchange Rate','Conversion Rate'],
    'Conversion Rate': ['Exchange Rate','FX Rate'],
    'Maturity Value': ['Redemption Value','Redemption Amount'],
    'Redemption Value': ['Maturity Value','Redemption Amount'],
    'Redemption Amount': ['Maturity Value','Redemption Value'],
    'Accrued Interest': ['Accrued Coupon','Interest Accrued'],
    'Accrued Coupon': ['Accrued Interest','Interest Accrued'],
    'Interest Accrued': ['Accrued Interest','Accrued Coupon'],
    'Yield': ['YTM','Yield to Maturity'],
    'YTM': ['Yield','Yield to Maturity'],
    'Yield to Maturity': ['Yield','YTM']
  }

  const filteredRequiredColumns = requiredColumns
  const detectedFields = {}
  const detectedCurrencies = new Set()
  const usedLabelValuePairs = new Set()

  if (normalizedCurrencyCode) {
    detectedCurrencies.add(normalizedCurrencyCode)
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

  function isFieldNumeric(fieldName) {
    if (ENUM_FIELD_NAMES.has(fieldName)) return false
    const lower = String(fieldName).toLowerCase()
    if (/(rate|yield|coupon|discount|price|value|amount|principal|face|par|notional|spread|margin|duration|convexity|payment|fee|cost)/.test(lower)) return true
    return false
  }

  function isFieldEnum(fieldName) {
    return ENUM_FIELD_NAMES.has(fieldName)
  }

  function calculateConfidence(label, matchedVariation, value, fieldName) {
    let score = 0.3
    if (label.toLowerCase() === matchedVariation.toLowerCase()) score += 0.2
    if (value && String(value).trim() !== '') score += 0.2
    if (isValidValueForField(fieldName, value)) score += 0.2
    if (!isTableHeading(value)) score += 0.1

    const principalFields = ['Principal','Face Value','FaceValue','Nominal Value','Notional Amount','Redemption Value','RedemptionValue']
    if (principalFields.includes(fieldName)) {
      const numValue = parseFloat(String(value).replace(/[%,\s$€£¥₹]/g, ''))
      if (!isNaN(numValue)) {
        if (numValue < 1000) score -= 0.3
        else if (numValue >= 1000) score += 0.1
      }
    }
    return Math.max(0.1, Math.min(score, 1.0))
  }

  function isTableHeading(value) {
    const strValue = String(value).trim().toUpperCase()
    const tableHeadings = [
      'CF','PV','FV','NPV','IRR','BALANCE','PRINCIPAL','INTEREST',
      'CASH FLOW','PRESENT VALUE','FUTURE VALUE','NET PRESENT VALUE',
      'INTERNAL RATE OF RETURN','PAYMENT','PMT','RATE','NPER',
      'TOTAL','SUM','SUBTOTAL','GRAND TOTAL','AVERAGE','AVG',
      'MAX','MIN','COUNT','HEADER','LABEL','VALUE','AMOUNT',
      'DATE','PERIOD','YEAR','MONTH','QUARTER','DAY',
      'BEGINNING','ENDING','OPENING','CLOSING','START','END',
      'IN','OUT','INFLOW','OUTFLOW','DEBIT','CREDIT',
      'ASSET','LIABILITY','EQUITY','REVENUE','EXPENSE',
      'BUY','SELL','PURCHASE','SALE','TRANSACTION',
      'ROW','COLUMN','CELL','SHEET','WORKSHEET',
      'YES','NO','TRUE','FALSE','N/A','NA','NULL',
      'CATEGORY','TYPE','CLASS','GROUP','SECTION',
      'INPUT','OUTPUT','RESULT','CALCULATION','FORMULA',
      'COUPON DATES','INTEREST PAYMENT DATES','BUSINESS DESCRIPTION'
    ]
    if (tableHeadings.includes(strValue)) return true
    if (strValue.length <= 3 && /^[A-Z]+$/.test(strValue)) {
      if (!KNOWN_ISO_CODES.has(strValue)) return true
    }
    if (strValue.length <= 10 && /^[A-Z\s]+$/.test(strValue) && strValue.includes(' ')) return true
    if (strValue.includes('-') && strValue.includes(' ')) return true
    return false
  }

  function looksLikeDate(value) {
    const strValue = String(value).trim()
    return !isNaN(Date.parse(strValue)) ||
      /^\d{1,2}[-/]\d{1,2}[-/]\d{2,4}$/.test(strValue) ||
      /^\d{1,2}-[A-Za-z]{3}-\d{2,4}$/.test(strValue) ||
      /^[A-Za-z]{3}[-/]\d{1,2}[-/]\d{2,4}$/.test(strValue) ||
      /^\d{1,2}[-/][A-Za-z]{3}[-/]\d{2,4}$/.test(strValue) ||
      /^[A-Za-z]{3}\s+\d{1,2},\s+\d{4}$/.test(strValue)
  }

  function isValidValueForField(fieldName, value) {
    if (value === null || value === undefined || value === '') return false
    if (isTableHeading(value)) return false

    const s = String(value).trim()
    if (!s) return false

    if (isFieldEnum(fieldName)) {
      if (/^[\d.,%$€£¥₹+\-()\s]+$/.test(s)) return false
      if (isLabelLikeValue(s)) return false
      return true
    }

    if (isFieldNumeric(fieldName)) {
      if (looksLikeDate(s)) return false
      if (isCurrencyCodeStrict(s)) return false
      if (isLabelLikeValue(s)) return false
      const numericValue = s.replace(/[%,\s$€£¥₹()\-]/g, '')
      const num = parseFloat(numericValue)
      if (isNaN(num)) return false
      return true
    }

    const dateFields = ['Date','Issue Date','Maturity Date','Valuation Date','Trade Date','Settlement Date','MaturityDate','Pricing Date','Effective Date','Start Date','End Date','IssueDate','ValuationDate']
    if (dateFields.includes(fieldName)) return looksLikeDate(value)

    const textFields = ['Instrument','Instrument Name','Bond Name','Issuer','Counterparty','Currency','BondName','TBillName','InstrumentName','Currency Code','Base Currency','Local Currency','Reporting Currency','Status','Type']
    if (textFields.includes(fieldName)) {
      if (!s) return false
      return true
    }

    return true
  }

  function bestVariationFor(label, fieldName) {
    const variations = fieldVariations[fieldName] || []
    const normalizedLabel = String(label).toLowerCase().trim()
    let best = null, bestLen = 0
    for (const v of variations) {
      const nv = String(v).toLowerCase().trim()
      if (normalizedLabel.includes(nv) && nv.length > bestLen) {
        best = v; bestLen = nv.length
      }
    }
    return best || fieldName
  }

  // ---------- Pass 1: Horizontal label-value pairs (WITH GAP TOLERANCE) ----------
  console.log('=== Pass 1: Horizontal label-value pairs (gap-tolerant) ===')
  for (let R = tableBoundaries.startRow; R <= tableBoundaries.endRow; R++) {
    for (let C = tableBoundaries.startCol; C < tableBoundaries.endCol; C++) {
      const label = String(data[R][C]).toLowerCase().trim()
      if (!label) continue
      if (isTableHeading(label)) continue

      const valueHit = findAdjacentValueRight(data, R, C, 5, tableBoundaries.endCol)
      if (!valueHit) continue

      const value = valueHit.value
      const valueColOffset = valueHit.offset

      const matchedField = findBestMatchingField(label, filteredRequiredColumns, fieldVariations)
      if (!matchedField) continue
      if (detectedFields[matchedField]) continue

      const pairKey = `${label}_${value}_${R}_${C}`
      if (usedLabelValuePairs.has(pairKey)) continue

      if (!isValidValueForField(matchedField, value)) {
        console.log(`Rejected "${matchedField}": "${value}" at ${rowColToCellRef(R, C + valueColOffset)} (invalid value)`)
        continue
      }

      const location = rowColToCellRef(R, C + valueColOffset)
      const matchedVariation = bestVariationFor(label, matchedField)
      const confidence = calculateConfidence(label, matchedVariation, value, matchedField)

      detectedFields[matchedField] = { value, location, confidence, detectedFrom: 'horizontal_label_value' }
      usedLabelValuePairs.add(pairKey)
      console.log(`Detected "${matchedField}": "${value}" at ${location} (via "${matchedVariation}")`)

      if (matchedField === 'Currency') detectedCurrencies.add(String(value).toUpperCase())
    }
  }

  // ---------- Pass 2: Vertical label-value pairs (WITH GAP TOLERANCE) ----------
  console.log('=== Pass 2: Vertical label-value pairs (gap-tolerant) ===')
  for (let R = tableBoundaries.startRow; R < tableBoundaries.endRow; R++) {
    for (let C = tableBoundaries.startCol; C <= tableBoundaries.endCol; C++) {
      const label = String(data[R][C]).toLowerCase().trim()
      if (!label) continue
      if (isTableHeading(label)) continue

      const valueHit = findAdjacentValueDown(data, R, C, 5, tableBoundaries.endRow)
      if (!valueHit) continue

      const value = valueHit.value
      const valueRowOffset = valueHit.offset

      const matchedField = findBestMatchingField(label, filteredRequiredColumns, fieldVariations)
      if (!matchedField) continue
      if (detectedFields[matchedField]) continue

      const pairKey = `${label}_${value}_${R}_${C}`
      if (usedLabelValuePairs.has(pairKey)) continue

      if (!isValidValueForField(matchedField, value)) {
        console.log(`Rejected "${matchedField}": "${value}" at ${rowColToCellRef(R + valueRowOffset, C)} (invalid value)`)
        continue
      }

      const location = rowColToCellRef(R + valueRowOffset, C)
      const matchedVariation = bestVariationFor(label, matchedField)
      const confidence = calculateConfidence(label, matchedVariation, value, matchedField)

      detectedFields[matchedField] = { value, location, confidence, detectedFrom: 'vertical_label_value' }
      usedLabelValuePairs.add(pairKey)
      console.log(`Detected "${matchedField}": "${value}" at ${location} (vertical)`)

      if (matchedField === 'Currency') detectedCurrencies.add(String(value).toUpperCase())
    }
  }

  // ---------- Pass 3: Table header structures (BEST MATCH, gap-tolerant) ----------
  console.log('=== Pass 3: Table header structures ===')
  for (let R = tableBoundaries.startRow; R <= tableBoundaries.endRow; R++) {
    const row = data[R]
    if (!row || row.length === 0) continue

    const headerLabels = row.map(cell => String(cell).toLowerCase().trim())
    const hasFieldLabels = headerLabels.some(label =>
      Object.values(fieldVariations).flat().some(v => label.includes(v))
    )

    if (hasFieldLabels && R + 1 <= tableBoundaries.endRow) {
      const valueRow = data[R + 1]
      for (let C = tableBoundaries.startCol; C <= tableBoundaries.endCol && C < valueRow.length; C++) {
        const label = headerLabels[C]
        const value = valueRow[C]
        if (!label || !value || value === '') continue

        const matchedField = findBestMatchingField(label, filteredRequiredColumns, fieldVariations)
        if (!matchedField) continue
        if (detectedFields[matchedField]) continue

        const pairKey = `${label}_${value}_${R}_${C}`
        if (usedLabelValuePairs.has(pairKey)) continue

        if (!isValidValueForField(matchedField, value)) continue

        const location = rowColToCellRef(R + 1, C)
        const matchedVariation = bestVariationFor(label, matchedField)
        const confidence = calculateConfidence(label, matchedVariation, value, matchedField)

        detectedFields[matchedField] = { value, location, confidence, detectedFrom: 'table_header' }
        usedLabelValuePairs.add(pairKey)
        if (matchedField === 'Currency') detectedCurrencies.add(String(value).toUpperCase())
      }
    }
  }

  // ---------- Pass 4: Currency codes ----------
  console.log('=== Pass 4: Currency codes ===')
  for (let R = tableBoundaries.startRow; R <= tableBoundaries.endRow; R++) {
    for (let C = tableBoundaries.startCol; C <= tableBoundaries.endCol; C++) {
      const cellValue = data[R][C]
      if (cellValue && /^[A-Z]{3}$/.test(String(cellValue))) {
        const currencyCode = String(cellValue).toUpperCase()
        if (NON_CURRENCY_WORDS.has(currencyCode)) continue
        if (KNOWN_ISO_CODES.has(currencyCode)) {
          let isCurrencyContext = false
          const adjacentLabels = ['currency','currencies','money','cash','amount','value','price','cost','fee','charge']
          for (let dr = -1; dr <= 1; dr++) {
            for (let dc = -1; dc <= 1; dc++) {
              if (dr === 0 && dc === 0) continue
              const cR = R + dr, cC = C + dc
              if (cR >= 0 && cR < data.length && cC >= 0 && cC < data[cR].length) {
                const adj = String(data[cR][cC]).toLowerCase()
                if (adjacentLabels.some(l => adj.includes(l))) { isCurrencyContext = true; break }
              }
            }
            if (isCurrencyContext) break
          }
          if (isCurrencyContext) detectedCurrencies.add(currencyCode)
        }
      }
    }
  }

  // ---------- Pass 5: Scattered search ----------
  console.log('=== Pass 5: Scattered search ===')
  for (let R = tableBoundaries.startRow; R <= tableBoundaries.endRow; R++) {
    for (let C = tableBoundaries.startCol; C <= tableBoundaries.endCol; C++) {
      const cellValue = data[R][C]
      if (!cellValue || String(cellValue).trim() === '') continue
      const cellLower = String(cellValue).toLowerCase().trim()
      if (isTableHeading(cellLower)) continue

      const matchedField = findBestMatchingField(cellLower, filteredRequiredColumns, fieldVariations)
      if (!matchedField) continue
      if (detectedFields[matchedField]) continue

      const directions = [
        { dr: 0, dc: 1 }, { dr: 1, dc: 0 }, { dr: 0, dc: -1 }, { dr: -1, dc: 0 },
        { dr: 1, dc: 1 }, { dr: 1, dc: -1 }, { dr: -1, dc: 1 }, { dr: -1, dc: -1 }
      ]
      let valueFound = false
      for (const { dr, dc } of directions) {
        for (let dist = 1; dist <= 5; dist++) {
          const sR = R + dr * dist, sC = C + dc * dist
          if (sR >= 0 && sR < data.length && sC >= 0 && sC < data[sR].length) {
            const nearbyValue = data[sR][sC]
            if (!nearbyValue || String(nearbyValue).trim() === '') continue
            if (!isValidValueForField(matchedField, nearbyValue)) continue

            const valueStr = String(nearbyValue).trim()
            let isDuplicate = false
            for (const [ef, ed] of Object.entries(detectedFields)) {
              if (ef !== matchedField && String(ed.value).trim() === valueStr) { isDuplicate = true; break }
            }
            if (isDuplicate) continue

            const location = rowColToCellRef(sR, sC)
            const confidence = calculateConfidence(cellLower, bestVariationFor(cellLower, matchedField), nearbyValue, matchedField)
            detectedFields[matchedField] = { value: nearbyValue, location, confidence, detectedFrom: 'scattered' }
            usedLabelValuePairs.add(`${cellLower}_${nearbyValue}_${sR}_${sC}`)
            if (matchedField === 'Currency') detectedCurrencies.add(String(nearbyValue).toUpperCase())
            valueFound = true
            break
          }
        }
        if (valueFound) break
      }
    }
  }

  // ---------- Pass 6: Full worksheet scan ----------
  console.log('=== Pass 6: Full worksheet scan ===')
  const stillMissing = filteredRequiredColumns.filter(col => !detectedFields[col])
  if (stillMissing.length > 0) {
    for (let R = 0; R < data.length; R++) {
      for (let C = 0; C < (data[R]?.length || 0); C++) {
        const label = String(data[R][C]).toLowerCase().trim()
        if (isTableHeading(label)) continue

        const matchedField = findBestMatchingField(label, stillMissing, fieldVariations)
        if (!matchedField) continue
        if (detectedFields[matchedField]) continue

        const directions = [
          { dr: 0, dc: 1 }, { dr: 1, dc: 0 }, { dr: 0, dc: -1 }, { dr: -1, dc: 0 },
          { dr: 1, dc: 1 }, { dr: 1, dc: -1 }, { dr: -1, dc: 1 }, { dr: -1, dc: -1 }
        ]
        for (const { dr, dc } of directions) {
          for (let dist = 1; dist <= 5; dist++) {
            const sR = R + dr * dist, sC = C + dc * dist
            if (sR >= 0 && sR < data.length && sC >= 0 && sC < data[sR].length) {
              const nearbyValue = data[sR][sC]
              if (!nearbyValue || String(nearbyValue).trim() === '') continue
              if (!isValidValueForField(matchedField, nearbyValue)) continue

              const valueStr = String(nearbyValue).trim()
              let isDuplicate = false
              for (const [, ed] of Object.entries(detectedFields)) {
                if (String(ed.value).trim() === valueStr) { isDuplicate = true; break }
              }
              if (isDuplicate) continue

              detectedFields[matchedField] = {
                value: nearbyValue,
                location: rowColToCellRef(sR, sC),
                confidence: 0.5,
                detectedFrom: 'full_scan'
              }
              if (matchedField === 'Currency') detectedCurrencies.add(String(nearbyValue).toUpperCase())
              break
            }
          }
        }
      }
    }
  }

  // Synonym mapping
  for (const [primaryField, synonyms] of Object.entries(synonymMapping)) {
    if (!requiredColumns.includes(primaryField)) continue
    for (const syn of synonyms) {
      if (detectedFields[syn] && !detectedFields[primaryField]) {
        detectedFields[primaryField] = detectedFields[syn]
        delete detectedFields[syn]
      }
    }
  }

  // Instrument name handling — STRICT, no fallback
  if (requiredColumns.includes('Instrument Name') || requiredColumns.includes('BondName') || requiredColumns.includes('TBillName')) {
    const nameField = requiredColumns.includes('Instrument Name') ? 'Instrument Name'
                    : requiredColumns.includes('BondName') ? 'BondName' : 'TBillName'
    if (!detectedFields[nameField]) {
      if (detectedFields['Instrument']) {
        detectedFields[nameField] = detectedFields['Instrument']
      } else if (detectedFields['Counterparty']) {
        detectedFields[nameField] = detectedFields['Counterparty']
      }
      // Otherwise: leave undetected. No fallback.
    }
  }

  const simpleDetectedFields = {}
  for (const [k, fd] of Object.entries(detectedFields)) simpleDetectedFields[k] = fd.value

  const missingFields = requiredColumns.filter(col => !detectedFields[col])

  // ==========================================================================
  // NEW Pass 7: Additional label-value pairs (everything else in the sheet)
  // --------------------------------------------------------------------------
  // Detects any label → value pair whose label does NOT match a required
  // field. This is what makes the popup show the WHOLE sheet, not just the
  // required fields. Returns as `additionalFields` — no calculations use it.
  // ==========================================================================
  console.log('=== Pass 7: Additional label-value pairs (all other sheet content) ===')
  const additionalFields = {}
  const additionalUsedPairs = new Set()

  for (let R = tableBoundaries.startRow; R <= tableBoundaries.endRow; R++) {
    for (let C = tableBoundaries.startCol; C < tableBoundaries.endCol; C++) {
      const labelRaw = data[R][C]
      if (labelRaw === null || labelRaw === undefined) continue
      const label = String(labelRaw).trim()
      if (!label) continue
      if (label.length > 80) continue
      if (isTableHeading(label)) continue
      if (/^[\d.,%$€£¥₹+\-()\s]+$/.test(label)) continue
      if (isDateLike(label)) continue
      if (isCurrencyCodeStrict(label)) continue

      const valueHit = findAdjacentValueRight(data, R, C, 5, tableBoundaries.endCol)
      if (!valueHit) continue
      const value = valueHit.value
      const valueColOffset = valueHit.offset

      // Skip if this label already matched a required field (already handled)
      const matchedReq = findBestMatchingField(label.toLowerCase(), filteredRequiredColumns, fieldVariations)
      if (matchedReq) continue

      // Skip overly long value text (likely a paragraph, not a scalar)
      if (typeof value === 'string' && value.length > 200) continue

      // Skip if this exact label already captured
      if (additionalFields[label]) continue

      const pairKey = `${label}_${value}_${R}_${C}`
      if (additionalUsedPairs.has(pairKey)) continue

      additionalFields[label] = {
        value,
        location: rowColToCellRef(R, C + valueColOffset),
        section: currentSectionName(data, R, tableBoundaries.startRow)
      }
      additionalUsedPairs.add(pairKey)
    }
  }

  function currentSectionName(data, R, startRow) {
    // Walk upward from R to find the nearest text-only row (a section title)
    for (let r = R - 1; r >= startRow; r--) {
      const row = data[r] || []
      const nonEmpty = row.filter(c => c !== null && c !== undefined && String(c).trim() !== '')
      if (nonEmpty.length === 1 && String(nonEmpty[0]).trim().length < 60) {
        const t = String(nonEmpty[0]).trim()
        if (!/^[\d.,%$€£¥₹-]+$/.test(t)) return t
      }
      if (nonEmpty.length === 0) break
    }
    return ''
  }

  console.log('Additional fields detected:', Object.keys(additionalFields))

  console.log('=== Final Detection ===')
  console.log('Detected (required):', Object.keys(detectedFields))
  console.log('Missing (required):', missingFields)
  console.log('Additional (informational):', Object.keys(additionalFields))
  console.log('Currencies:', Array.from(detectedCurrencies))

  return {
    fields: simpleDetectedFields,
    fieldsWithMetadata: detectedFields,
    currencies: Array.from(detectedCurrencies),
    missingFields,
    headerRegions,
    additionalFields
  }
}

function isLabelLike(value) {
  const str = String(value).toLowerCase().trim()
  const labelWords = ['name','value','rate','date','amount','price','yield','coupon','discount','maturity','issue','currency','days','count','total','instrument','bond','security']
  return labelWords.some(word => str.includes(word) && str.length < 20)
}