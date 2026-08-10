import * as XLSX from 'xlsx'

/**
 * Auto-detect instrument fields from a worksheet
 * Scans the entire worksheet for label-value pairs in various layouts
 * @param {ArrayBuffer} fileBuffer - Excel file buffer
 * @param {string} sheetName - Name of the sheet to analyze
 * @param {Array} requiredColumns - Array of required column names for the instrument
 * @param {string} instrumentType - Type of instrument (bonds, money-market, treasury-bills)
 * @returns {Object} Detected fields, currencies, and missing fields
 */
export function autoDetectInstrumentFields(fileBuffer, sheetName, requiredColumns, instrumentType) {
  // Parse workbook from buffer
  console.log('=== autoDetectInstrumentFields Started ===')
  console.log('Sheet Name:', sheetName)
  console.log('Instrument Type:', instrumentType)
  console.log('Required Columns:', requiredColumns)

  if (!fileBuffer || !sheetName) {
    throw new Error('File buffer and sheet name are required')
  }

  const workbook = XLSX.read(fileBuffer, { type: 'array', cellStyles: true, cellFormula: true, cellDates: true, cellNF: true })
  const worksheet = workbook.Sheets[sheetName]
  
  if (!worksheet) {
    console.error('Worksheet not found:', sheetName)
    return { fields: {}, currencies: [], missingFields: requiredColumns }
  }

  // Get the full range of the worksheet - expand to capture all data
  let range
  if (worksheet['!ref']) {
    range = XLSX.utils.decode_range(worksheet['!ref'])
  } else {
    // If no ref defined, scan the entire sheet up to reasonable limits
    range = { s: { r: 0, c: 0 }, e: { r: 1000, c: 100 } }
  }
  
  // Expand range to capture all data by scanning for actual content
  let maxRow = 0
  let maxCol = 0
  for (const cellAddress in worksheet) {
    if (cellAddress.startsWith('!')) continue
    const cellRef = XLSX.utils.decode_cell(cellAddress)
    if (cellRef.r > maxRow) maxRow = cellRef.r
    if (cellRef.c > maxCol) maxCol = cellRef.c
  }
  
  // Use the expanded range if it's larger than the defined range
  if (maxRow > range.e.r) range.e.r = maxRow
  if (maxCol > range.e.c) range.e.c = maxCol
  
  console.log('Worksheet Range:', worksheet['!ref'], 'Expanded to:', XLSX.utils.encode_range(range))
  console.log('Rows:', range.e.r + 1, 'Cols:', range.e.c + 1)

  // Convert worksheet to 2D array for scanning
  const data = []
  for (let R = range.s.r; R <= range.e.r; R++) {
    const row = []
    for (let C = range.s.c; C <= range.e.c; C++) {
      const cellAddress = XLSX.utils.encode_cell({ r: R, c: C })
      const cell = worksheet[cellAddress]
      if (cell) {
        row.push(cell.w ?? cell.v ?? '')
      } else {
        row.push('')
      }
    }
    data.push(row)
  }
  
  console.log('Extracted Data Dimensions:', data.length, 'rows x', data[0]?.length || 0, 'cols')
  console.log('Sample Data (first 3 rows):', data.slice(0, 3))

  // Define comprehensive field variations for detection - instrument-specific
  const fieldVariations = {
    // Common fields across all instruments
    'Instrument Name': ['instrument name', 'name', 'bond name', 'security name', 'security', 'bond name', 't-bill name'],
    'Instrument ID': ['instrument id', 'id', 'instrument id', 'security id', 'bond id', 't-bill id'],
    'Instrument Code': ['instrument code', 'code', 'security code'],
    'Security ID': ['security id', 'security identifier', 'sec id'],
    'ISIN': ['isin', 'isin code'],
    'CUSIP': ['cusip', 'cusip code'],
    'Bloomberg Ticker': ['bloomberg ticker', 'bloomberg', 'bbg ticker'],
    'Reuters/Refinitiv Ticker': ['reuters ticker', 'refinitiv ticker', 'reuters'],
    'Counterparty': ['counterparty', 'issuer', 'borrower', 'party', 'entity', 'counter party', 'nhimbe', 'client', 'customer'],
    'Issuer': ['issuer', 'borrower', 'counterparty', 'issuing entity', 'issuing party'],
    'Parent Company': ['parent company', 'parent', 'holding company'],
    'Issuer Country': ['issuer country', 'country of issue', 'issuing country'],
    'Country': ['country', 'jurisdiction', 'nation'],
    'Currency': ['currency', 'denomination', 'ccy', 'currency code', 'curr', 'base currency', 'local currency', 'reporting currency'],
    'Currency Code': ['currency code', 'currency', 'ccy', 'curr'],
    'Base Currency': ['base currency', 'reporting currency', 'functional currency'],
    'Local Currency': ['local currency', 'denomination currency'],
    'Reporting Currency': ['reporting currency', 'base currency', 'functional currency'],
    'Exchange Rate': ['exchange rate', 'exch rate', 'fx rate', 'forex rate', 'conversion rate', 'exch', 'spot rate', 'forward rate', 'fx pair'],
    'FX Rate': ['fx rate', 'exchange rate', 'forex rate', 'conversion rate'],
    'FX Pair': ['fx pair', 'currency pair'],
    'Valuation Date': ['valuation date', 'pricing date', 'as of date', 'value date'],
    'Pricing Date': ['pricing date', 'valuation date', 'price date'],
    'Trade Date': ['trade date', 'transaction date', 'deal date'],
    'Settlement Date': ['settlement date', 'settle date'],
    'Issue Date': ['issue date', 'issuance date', 'start date', 'effective date', 'origination date', 'issue', 'issuing date', 'commencement date'],
    'Effective Date': ['effective date', 'start date', 'issue date', 'commencement date', 'value date'],
    'Start Date': ['start date', 'effective date', 'issue date', 'accrual start date', 'commencement date'],
    'End Date': ['end date', 'maturity date', 'termination date', 'expiry date'],
    'Maturity Date': ['maturity date', 'maturity', 'due date', 'expiry date', 'redemption date', 'maturity', 'repayment date', 'final maturity date'],
    'Tenor': ['tenor', 'term', 'duration'],
    'Term': ['term', 'tenor', 'duration'],
    'Term in Days': ['term in days', 'tenor days', 'days', 'duration days'],
    'Term in Months': ['term in months', 'tenor months', 'months'],
    'Term in Years': ['term in years', 'tenor years', 'years'],
    'Business Day Convention': ['business day convention', 'bdc', 'day convention'],
    'Day Count Convention': ['day count convention', 'day count', 'dcc', 'day count basis'],
    'Calendar': ['calendar', 'holiday calendar'],
    'Settlement Lag': ['settlement lag', 'settlement days'],
    // Note: Instrument Type is NOT detected from worksheet - it comes from current page context only
    'Asset Class': ['asset class', 'classification'],
    'Classification': ['classification', 'category'],
    'Market': ['market', 'exchange', 'venue'],
    'Market Sector': ['market sector', 'sector', 'industry'],
    'Portfolio': ['portfolio', 'portfolio name', 'book'],
    'Portfolio Name': ['portfolio name', 'portfolio'],
    'Book': ['book', 'portfolio', 'trading book'],
    'Position': ['position', 'holding'],
    'Quantity': ['quantity', 'amount', 'units', 'position'],
    'Units': ['units', 'quantity', 'amount'],
    'Nominal Amount': ['nominal amount', 'notional amount', 'face value', 'principal', 'par value'],
    'Face Value': ['face value', 'par value', 'principal', 'face amount', 'par amount', 'nominal value', 'notional', 'nominal amount', 'principal amount', 'investment amount'],
    'Principal': ['principal', 'face value', 'par value', 'nominal amount', 'notional', 'investment amount', 'principal amount'],
    'Par Value': ['par value', 'face value', 'principal', 'par amount'],
    'Nominal Value': ['nominal value', 'face value', 'par value', 'notional', 'nominal amount'],
    'Notional': ['notional', 'nominal value', 'face value', 'principal', 'notional amount'],
    'Outstanding Principal': ['outstanding principal', 'current principal', 'remaining principal'],
    'Current Principal': ['current principal', 'outstanding principal', 'remaining principal'],
    'Original Principal': ['original principal', 'issue amount', 'initial principal'],
    'Carrying Value': ['carrying value', 'book value', 'carrying amount', 'carrying', 'book amount', 'amortised cost'],
    'Book Value': ['book value', 'carrying value', 'amortised cost'],
    'Fair Value': ['fair value', 'fv', 'market value', 'fair market value', 'current value'],
    'Market Value': ['market value', 'fair value', 'current value', 'fair market value'],
    'Present Value': ['present value', 'pv', 'current value', 'present amount'],
    'Amortised Cost': ['amortised cost', 'carrying value', 'book value'],
    'Impairment': ['impairment', 'impairment loss', 'impairment charge', 'credit impairment', 'provision'],
    'Accrued Interest': ['accrued interest', 'accrued', 'interest accrued', 'accrued coupon', 'interest accrual', 'accrued amount'],
    'Clean Price': ['clean price', 'price', 'bond price', 'quoted price'],
    'Dirty Price': ['dirty price', 'full price', 'gross price'],
    'Price': ['price', 'market price', 'clean price', 'dirty price', 'bond price', 'purchase price', 'unit price'],
    'Yield': ['yield', 'ytm', 'yield to maturity', 'rate', 'current yield', 'running yield', 'internal rate of return'],
    'Discount Rate': ['discount rate', 'discount', 'discount yield'],
    'Interest Rate': ['interest rate', 'rate', 'coupon rate', 'coupon', 'annual rate', 'interest', 'yield', 'nominal rate', 'fixed rate', 'floating rate'],
    'Reference Rate': ['reference rate', 'benchmark rate', 'index rate', 'base rate'],
    'Benchmark Rate': ['benchmark rate', 'reference rate', 'index rate', 'base rate'],
    'Spread': ['spread', 'margin', 'credit spread', 'currency spread', 'basis points'],
    'Margin': ['margin', 'spread', 'index margin', 'basis points'],
    'Credit Spread': ['credit spread', 'spread', 'yield spread', 'credit margin'],
    'Currency Spread': ['currency spread', 'spread', 'fx spread'],
    'Valuation Method': ['valuation method', 'pricing method'],
    'Pricing Method': ['pricing method', 'valuation method'],
    'Status': ['status', 'state'],
    'Transaction Type': ['transaction type'],
    'Buy/Sell': ['buy/sell', 'direction', 'side'],
    'Long/Short': ['long/short', 'position'],
    'Quantity Held': ['quantity held', 'position', 'holding'],
    'Purchase Price': ['purchase price', 'buying price', 'acquisition price', 'cost'],
    'Purchase Value': ['purchase value', 'purchase amount', 'investment amount'],
    'Total Cost': ['total cost', 'acquisition cost'],
    'Transaction Cost': ['transaction cost', 'fees', 'commission'],
    'Fees': ['fees', 'transaction cost', 'commission'],
    'Commission': ['commission', 'fees'],
    'Settlement Amount': ['settlement amount', 'proceeds'],
    'Cash Flow': ['cash flow', 'cf'],
    'Cash Flow Date': ['cash flow date', 'payment date'],
    'Cash Flow Frequency': ['cash flow frequency', 'payment frequency', 'frequency'],
    'Payment Date': ['payment date', 'cash flow date'],
    'Payment Frequency': ['payment frequency', 'frequency', 'cash flow frequency', 'coupon frequency'],
    
    // Bond-specific fields
    'Bond Name': ['bond name', 'instrument name', 'name', 'security name'],
    'Bond ID': ['bond id', 'instrument id', 'security id'],
    'Bond Type': ['bond type', 'classification'],
    'Seniority': ['seniority', 'ranking'],
    'Secured/Unsecured': ['secured/unsecured', 'collateral type', 'security'],
    'Coupon Rate': ['coupon rate', 'interest rate', 'coupon', 'rate', 'annual coupon', 'fixed rate', 'nominal rate'],
    'Coupon Frequency': ['coupon frequency', 'frequency', 'payment frequency', 'interest frequency', 'coupon freq', 'pmt frequency', 'interest pmt frequency'],
    'Coupon Date': ['coupon date', 'payment date', 'interest payment date'],
    'First Coupon Date': ['first coupon date', 'next coupon date', 'upcoming coupon date'],
    'Next Coupon Date': ['next coupon date', 'upcoming coupon date', 'first coupon date'],
    'Previous Coupon Date': ['previous coupon date', 'last coupon date'],
    'Last Coupon Date': ['last coupon date', 'previous coupon date'],
    'Call Date': ['call date', 'optional redemption date'],
    'Put Date': ['put date', 'optional put date'],
    'Reset Date': ['reset date', 'rate reset date'],
    'Accrual End Date': ['accrual end date', 'end date'],
    'Settlement Days': ['settlement days', 'settlement lag'],
    'Days Accrued': ['days accrued', 'accrual days'],
    'Days to Maturity': ['days to maturity', 'remaining days', 'term in days'],
    'Remaining Term': ['remaining term', 'days to maturity', 'remaining days'],
    'Coupon Rate': ['coupon rate', 'coupon', 'interest rate', 'coupon/interest rate', 'annual rate', 'rate'],
    'Coupon': ['coupon', 'coupon rate', 'interest rate'],
    'Fixed Rate': ['fixed rate', 'coupon rate'],
    'Floating Rate': ['floating rate', 'variable rate'],
    'Coupon Frequency': ['coupon payment frequency', 'coupon frequency', 'payment frequency', 'frequency', 'payment schedule'],
    'Coupon Amount': ['coupon amount', 'interest amount'],
    'Interest Amount': ['interest amount', 'coupon amount'],
    'Accrued Coupon': ['accrued coupon', 'accrued interest'],
    'Interest Accrual': ['interest accrual', 'accrued interest'],
    'Accrual Factor': ['accrual factor', 'day count fraction'],
    'Clean Price': ['clean price', 'price'],
    'Dirty Price': ['dirty price', 'full price'],
    'Full Price': ['full price', 'dirty price'],
    'Market Price': ['market price', 'price'],
    'Redemption Price': ['redemption price', 'redemption value'],
    'Yield to Maturity': ['yield to maturity', 'ytm', 'yield'],
    'YTM': ['ytm', 'yield to maturity', 'yield'],
    'Yield to Call': ['yield to call', 'ytc'],
    'Yield to Worst': ['yield to worst', 'ytw'],
    'Current Yield': ['current yield', 'running yield'],
    'Running Yield': ['running yield', 'current yield'],
    'Required Return': ['required return', 'discount rate'],
    'Internal Rate of Return': ['internal rate of return', 'irr', 'yield'],
    'Effective Yield': ['effective yield', 'annualised yield'],
    'Coupon Cash Flow': ['coupon cash flow', 'interest cash flow'],
    'Principal Cash Flow': ['principal cash flow', 'redemption cash flow'],
    'Redemption Cash Flow': ['redemption cash flow', 'principal cash flow'],
    'Total Cash Flow': ['total cash flow', 'cash flow'],
    'Discount Factor': ['discount factor', 'pv factor'],
    'Present Value of Coupon': ['present value of coupon', 'pv of coupon'],
    'Present Value of Principal': ['present value of principal', 'pv of principal'],
    'Present Value of Cash Flows': ['present value of cash flows', 'pv of cash flows'],
    'Expected Cash Flow': ['expected cash flow', 'projected cash flow'],
    'Duration': ['duration', 'macaulay duration'],
    'Macaulay Duration': ['macaulay duration', 'duration'],
    'Modified Duration': ['modified duration', 'mod duration'],
    'Effective Duration': ['effective duration'],
    'Key Rate Duration': ['key rate duration', 'krd'],
    'Convexity': ['convexity', 'effective convexity'],
    'Effective Convexity': ['effective convexity', 'convexity'],
    'DV01': ['dv01', 'dollar duration', 'pv01'],
    'PV01': ['pv01', 'dv01', 'dollar duration'],
    'Z-Spread': ['z-spread', 'zero volatility spread'],
    'OAS': ['oas', 'option adjusted spread'],
    'Benchmark Spread': ['benchmark spread', 'yield spread'],
    'Yield Spread': ['yield spread', 'benchmark spread'],
    'Credit Rating': ['credit rating', 'rating'],
    'Rating Agency': ['rating agency', 'rating provider'],
    'Default Probability': ['default probability', 'pd'],
    'Recovery Rate': ['recovery rate', 'rr'],
    'Loss Given Default': ['loss given default', 'lgd'],
    'Hazard Rate': ['hazard rate', 'default intensity'],
    'Credit Curve': ['credit curve', 'default curve'],
    'Yield Curve': ['yield curve', 'benchmark curve'],
    'Benchmark Curve': ['benchmark curve', 'yield curve'],
    'Reset Frequency': ['reset frequency', 'rate reset frequency'],
    'Reference Index': ['reference index', 'index'],
    'Index Rate': ['index rate', 'reference rate'],
    'Rate Floor': ['rate floor', 'minimum rate', 'floor'],
    'Rate Cap': ['rate cap', 'maximum rate', 'cap'],
    'Minimum Rate': ['minimum rate', 'rate floor', 'floor'],
    'Maximum Rate': ['maximum rate', 'rate cap', 'cap'],
    'Next Reset Rate': ['next reset rate', 'upcoming reset rate'],
    
    // Money Market-specific fields
    'Investment Amount': ['investment amount', 'purchase amount', 'principal'],
    'Purchase Amount': ['purchase amount', 'investment amount', 'principal'],
    'Current Value': ['current value', 'market value', 'fair value'],
    'Redemption Value': ['redemption value', 'maturity value'],
    'Maturity Value': ['maturity value', 'redemption value'],
    'Par Value': ['par value', 'face value', 'principal'],
    'Discount Yield': ['discount yield', 'discount rate'],
    'Money Market Yield': ['money market yield', 'mm yield'],
    'Annualised Yield': ['annualised yield', 'effective yield'],
    'Effective Rate': ['effective rate', 'annualised yield'],
    'Interest Amount': ['interest amount', 'interest income'],
    'Discount Amount': ['discount amount', 'discount'],
    'Interest Income': ['interest income', 'interest amount'],
    'Discount Income': ['discount income', 'discount amount'],
    'Accrual Days': ['accrual days', 'days accrued'],
    'Days in Year': ['days in year', 'day count basis'],
    'Compounding Frequency': ['compounding frequency', 'frequency'],
    'Deposit Rate': ['deposit rate', 'interest rate'],
    'Deposit Term': ['deposit term', 'tenor'],
    'Maturity Amount': ['maturity amount', 'redemption amount'],
    'Certificate Number': ['certificate number', 'cert number'],
    'Deposit Type': ['deposit'],
    'Principal Amount': ['principal amount', 'principal'],
    'Call Date': ['call date', 'notice date'],
    'Notice Period': ['notice period', 'call period'],
    'Rate Reset Date': ['rate reset date', 'reset date'],
    'Index Margin': ['index margin', 'spread', 'margin'],
    
    // Treasury Bill-specific fields
    'T-Bill Name': ['t-bill name', 'instrument name', 'name'],
    'T-Bill ID': ['t-bill id', 'instrument id', 'security id'],
    'Government': ['government', 'issuer'],
    'Discount Yield': ['discount yield', 'discount rate'],
    'Investment Yield': ['investment yield', 'bond equivalent yield'],
    'Bond Equivalent Yield': ['bond equivalent yield', 'investment yield'],
    'Price per 100': ['price per 100', 'clean price'],
    'Accrued Discount': ['accrued discount', 'discount amount'],
    'Maturity Proceeds': ['maturity proceeds', 'redemption amount'],
    'Interest Equivalent': ['interest equivalent', 'yield equivalent'],
    'Number of Days': ['number of days', 'days'],
    'Actual Days': ['actual days', 'days'],
    '360-Day Basis': ['360-day basis', 'actual/360'],
    '365-Day Basis': ['365-day basis', 'actual/365'],
    'Actual/360': ['actual/360', '360-day basis'],
    'Actual/365': ['actual/365', '365-day basis'],
    'Actual/Actual': ['actual/actual', 'day count convention'],
    
    // FX/Currency specific fields
    'Source Currency': ['source currency', 'from currency'],
    'Target Currency': ['target currency', 'to currency'],
    'Spot Rate': ['spot rate', 'exchange rate'],
    'Forward Rate': ['forward rate', 'fx forward'],
    'USD Value': ['usd value', 'dollar value'],
    'ZWG Value': ['zwg value', 'zimbabwe dollar value'],
    'EUR Value': ['eur value', 'euro value'],
    'GBP Value': ['gbp value', 'pound value'],
    'ZAR Value': ['zar value', 'rand value'],
    'Converted Fair Value': ['converted fair value', 'fx adjusted fair value'],
    'Converted Carrying Value': ['converted carrying value', 'fx adjusted carrying value'],
    'Converted Present Value': ['converted present value', 'fx adjusted present value'],
    'Converted Market Value': ['converted market value', 'fx adjusted market value'],
    'Converted Impairment': ['converted impairment', 'fx adjusted impairment'],
    'Converted Interest': ['converted interest', 'fx adjusted interest'],
    'Converted Principal': ['converted principal', 'fx adjusted principal'],
    
    // Additional fields that may appear
    'Total Value': ['total value', 'value', 'calculated value'],
    'Instrument Count': ['instrument count', 'count', 'number of instruments', 'quantity'],
    'Foreign Currency Value': ['foreign currency value', 'fcv', 'foreign value', 'local currency value'],
    'Local Currency Value': ['local currency value', 'lcv', 'local value']
  }

  // Add exact required column names as fallback variations
  for (const requiredField of requiredColumns) {
    if (!fieldVariations[requiredField]) {
      fieldVariations[requiredField] = [requiredField.toLowerCase()]
    } else {
      // Add the exact name as a variation if not already present
      const lowerName = requiredField.toLowerCase()
      if (!fieldVariations[requiredField].includes(lowerName)) {
        fieldVariations[requiredField].push(lowerName)
      }
    }
  }

  // Define synonym mapping for equivalent field names
  const synonymMapping = {
    'Face Value': ['Principal', 'Par Value', 'Nominal Value', 'Notional Amount'],
    'Principal': ['Face Value', 'Par Value', 'Nominal Value', 'Notional Amount'],
    'Par Value': ['Face Value', 'Principal', 'Nominal Value', 'Notional Amount'],
    'Nominal Value': ['Face Value', 'Principal', 'Par Value', 'Notional Amount'],
    'Notional Amount': ['Face Value', 'Principal', 'Par Value', 'Nominal Value'],
    'Maturity Date': ['Redemption Date', 'Due Date', 'Expiry Date'],
    'Redemption Date': ['Maturity Date', 'Due Date', 'Expiry Date'],
    'Due Date': ['Maturity Date', 'Redemption Date', 'Expiry Date'],
    'Interest Rate': ['Coupon Rate', 'Coupon', 'Rate'],
    'Coupon Rate': ['Interest Rate', 'Coupon', 'Rate'],
    'Coupon': ['Interest Rate', 'Coupon Rate', 'Rate'],
    'Fair Value': ['Market Value', 'Current Value'],
    'Market Value': ['Fair Value', 'Current Value'],
    'Current Value': ['Fair Value', 'Market Value'],
    'Carrying Value': ['Book Value', 'Amortised Cost'],
    'Book Value': ['Carrying Value', 'Amortised Cost'],
    'Amortised Cost': ['Carrying Value', 'Book Value'],
    'Present Value': ['PV'],
    'PV': ['Present Value'],
    'Exchange Rate': ['FX Rate', 'Conversion Rate'],
    'FX Rate': ['Exchange Rate', 'Conversion Rate'],
    'Conversion Rate': ['Exchange Rate', 'FX Rate'],
    'Maturity Value': ['Redemption Value', 'Redemption Amount'],
    'Redemption Value': ['Maturity Value', 'Redemption Amount'],
    'Redemption Amount': ['Maturity Value', 'Redemption Value'],
    'Accrued Interest': ['Accrued Coupon', 'Interest Accrued'],
    'Accrued Coupon': ['Accrued Interest', 'Interest Accrued'],
    'Interest Accrued': ['Accrued Interest', 'Accrued Coupon'],
    'Yield': ['YTM', 'Yield to Maturity'],
    'YTM': ['Yield', 'Yield to Maturity'],
    'Yield to Maturity': ['Yield', 'YTM']
  }

  console.log('Field variations configured:', Object.keys(fieldVariations).length, 'fields')
  console.log('Synonym mappings configured:', Object.keys(synonymMapping).length, 'groups')

  // Use the provided instrument type from the current page context ONLY
  // Do NOT auto-detect from worksheet - trust the current page/route
  const effectiveInstrumentType = instrumentType || 'bonds'
  console.log('=== INSTRUMENT CONTEXT LOCKED ===')
  console.log('Instrument Type from page context:', effectiveInstrumentType)
  console.log('Required Columns for this instrument:', requiredColumns)
  console.log('Worksheet content will NOT override instrument type')

  // Debug check - AUTO DETECT CONTEXT
  console.log('AUTO DETECT CONTEXT:', {
    instrumentType: effectiveInstrumentType,
    requiredFields: requiredColumns,
    detectedFields: 'will be populated after detection',
    missingFields: 'will be calculated after detection'
  })

  // Don't filter required columns - use all provided columns
  // The instrument-specific filtering was too aggressive and removed important fields
  const filteredRequiredColumns = requiredColumns
  console.log('Using all required columns:', filteredRequiredColumns.length, 'fields')

  // Normalize required columns to lowercase for matching
  const normalizedRequired = filteredRequiredColumns.map(col => col.toLowerCase())
  const detectedFields = {} // { fieldName: { value, location, confidence } }
  const detectedCurrencies = new Set()
  const usedLabelValuePairs = new Set() // Track used label-value pairs to prevent reuse

  console.log('Starting detection with', filteredRequiredColumns.length, 'required fields')
  console.log('Required fields:', filteredRequiredColumns)

  // Helper function to convert row/col to Excel cell reference
  function rowColToCellRef(row, col) {
    const colLetters = []
    let c = col
    while (c >= 0) {
      colLetters.unshift(String.fromCharCode((c % 26) + 65))
      c = Math.floor(c / 26) - 1
    }
    return colLetters.join('') + (row + 1)
  }

  // Helper function to calculate confidence score
  function calculateConfidence(label, matchedVariation, value, fieldName) {
    let score = 0.5 // Base score
    
    // Exact match gets higher score
    if (label.toLowerCase() === matchedVariation.toLowerCase()) {
      score += 0.3
    }
    
    // Value looks valid (not empty, not just whitespace)
    if (value && String(value).trim() !== '') {
      score += 0.1
    }
    
    // Value validation based on field type
    if (isValidValueForField(fieldName, value)) {
      score += 0.2
    }
    
    // Penalize if value looks like text for numeric fields
    if (isNumericField(fieldName) && isNaN(parseFloat(value))) {
      score -= 0.3
    }
    
    // Penalize if value looks like number for text fields
    if (isTextField(fieldName) && !isNaN(parseFloat(value))) {
      score -= 0.2
    }
    
    return Math.max(0, Math.min(score, 1.0))
  }

  // Helper function to check if value is valid for field type
  function isValidValueForField(fieldName, value) {
    if (!value || value === '') return false
    
    const numericFields = ['Principal', 'Face Value', 'Amount', 'Price', 'Interest Rate', 'Discount Rate', 'Yield', 'Coupon Rate', 'Present Value', 'Carrying Value', 'Fair Value', 'Impairment', 'Exchange Rate', 'Rate', 'FaceValue', 'InterestRate', 'DiscountRate']
    const dateFields = ['Date', 'Issue Date', 'Maturity Date', 'Valuation Date', 'Trade Date', 'Settlement Date', 'MaturityDate']
    const textFields = ['Instrument', 'Instrument Name', 'Bond Name', 'Issuer', 'Counterparty', 'Currency']
    
    if (numericFields.includes(fieldName)) {
      // Check if it's a valid number (can include % sign, commas, etc.)
      const numericValue = String(value).replace(/[%,\s]/g, '')
      return !isNaN(parseFloat(numericValue)) && parseFloat(numericValue) !== 0
    }
    
    if (dateFields.includes(fieldName)) {
      // Check if value looks like a date
      return !isNaN(Date.parse(value)) || /^\d{1,2}[-/]\d{1,2}[-/]\d{2,4}$/.test(value) || /^\d{1,2}-[A-Za-z]{3}-\d{2,4}$/.test(value)
    }
    
    if (textFields.includes(fieldName)) {
      // Should be text, not a pure number
      const strValue = String(value).trim()
      return isNaN(parseFloat(strValue)) || strValue.includes('%') || strValue.length > 3
    }
    
    return true
  }

  // Helper function to check if field expects numeric value
  function isNumericField(fieldName) {
    const numericFields = ['Principal', 'Face Value', 'Amount', 'Price', 'Interest Rate', 'Discount Rate', 'Yield', 'Coupon Rate', 'Present Value', 'Carrying Value', 'Fair Value', 'Impairment', 'Exchange Rate', 'Rate', 'FaceValue', 'InterestRate', 'DiscountRate']
    return numericFields.includes(fieldName)
  }

  // Helper function to check if field expects text value
  function isTextField(fieldName) {
    const textFields = ['Instrument', 'Instrument Name', 'Bond Name', 'Issuer', 'Counterparty', 'Currency']
    return textFields.includes(fieldName)
  }

  // Add comprehensive field variations for valuation fields
  const valuationFieldVariations = {
    'Face Value': ['face value', 'principal', 'par value', 'nominal value', 'notional amount', 'facevalue', 'face', 'principal amount', 'nominal', 'notional'],
    'Principal': ['principal', 'face value', 'par value', 'nominal value', 'notional amount', 'principal amount', 'nominal', 'notional', 'face'],
    'FaceValue': ['principal', 'face value', 'par value', 'nominal value', 'notional amount', 'facevalue', 'face', 'principal amount', 'nominal', 'notional'],
    'Interest Rate': ['interest rate', 'coupon rate', 'rate', 'coupon', 'interest', 'interestrate', 'couponrate', 'annual rate'],
    'Coupon Rate': ['coupon rate', 'interest rate', 'coupon', 'rate', 'couponrate', 'interestrate'],
    'CouponRate': ['interest rate', 'coupon rate', 'rate', 'coupon', 'interest', 'interestrate', 'couponrate', 'annual rate'],
    'Yield': ['yield', 'ytm', 'yield to maturity', 'rate of return', 'ytm'],
    'YTM': ['ytm', 'yield', 'yield to maturity'],
    'Price': ['price', 'clean price', 'dirty price', 'market price', 'current price', 'valuation price'],
    'Clean Price': ['clean price', 'price', 'market price'],
    'Dirty Price': ['dirty price', 'gross price', 'full price'],
    'Maturity Date': ['maturity date', 'redemption date', 'due date', 'expiry date', 'maturity', 'maturitydate', 'redemption', 'due'],
    'MaturityDate': ['maturity date', 'redemption date', 'due date', 'expiry date', 'maturity', 'maturitydate', 'redemption', 'due'],
    'Issue Date': ['issue date', 'issuance date', 'start date', 'effective date', 'issuedate', 'issuance'],
    'IssueDate': ['issue date', 'issuance date', 'start date', 'effective date', 'issuedate', 'issuance'],
    'Present Value': ['present value', 'pv', 'current value', 'discounted value', 'presentvalue'],
    'Carrying Value': ['carrying value', 'book value', 'amortised cost', 'carryingvalue', 'bookvalue', 'amortisedcost'],
    'Fair Value': ['fair value', 'market value', 'current value', 'fairvalue', 'marketvalue'],
    'Impairment': ['impairment', 'impairment loss', 'credit impairment', 'impairment loss'],
    'Currency': ['currency', 'denomination', 'ccy', 'currency code', 'curr', 'base currency', 'local currency'],
    'Exchange Rate': ['exchange rate', 'exch rate', 'fx rate', 'forex rate', 'conversion rate', 'exch', 'spot rate', 'exchangerate', 'fxrate'],
    'Amount': ['amount', 'value', 'investment amount', 'purchase amount', 'total amount'],
    'BondName': ['counterparty', 'instrument name', 'bond name', 'security name', 'issuer', 'borrower', 'party', 'entity', 'counter party'],
    'Frequency': ['frequency', 'interest pmt frequency', 'interest payment frequency', 'interest pmt fequency', 'coupon frequency', 'payment frequency', 'pmt frequency', 'annually', 'semi-annually', 'quarterly', 'monthly', 'fequency'],
    'Accrued Interest': ['accrued interest', 'interest accrued', 'accrued coupon', 'interest accrued to', 'accruedinterest'],
    'AccruedInterest': ['interest accrued', 'accrued interest', 'accrued coupon', 'interest accrued to', 'interest accrued to 30 june 2024'],
    'Redemption Value': ['redemption value', 'maturity value', 'redemption amount', 'principal', 'face value'],
    'Date': ['date', 'valuation date', 'pricing date', 'as of date', 'value date', 'valuationdate']
  }

  // Merge valuation field variations with existing field variations
  for (const [field, variations] of Object.entries(valuationFieldVariations)) {
    if (!fieldVariations[field]) {
      fieldVariations[field] = variations
    } else {
      // Add new variations to existing ones
      for (const variation of variations) {
        if (!fieldVariations[field].includes(variation)) {
          fieldVariations[field].push(variation)
        }
      }
    }
  }

  console.log('Valuation field variations added:', Object.keys(valuationFieldVariations).length, 'fields')

  // Helper function to check if label matches field variations
  function labelMatchesField(label, fieldVariations) {
    const normalizedLabel = label.toLowerCase().trim()
    return fieldVariations.some(v => {
      const normalizedVariation = v.toLowerCase().trim()
      // Exact match
      if (normalizedLabel === normalizedVariation) return true
      // Contains match
      if (normalizedLabel.includes(normalizedVariation)) return true
      // Word boundary match (e.g., "Issue Date" matches "Issue")
      if (normalizedVariation.includes(' ') && normalizedLabel.includes(normalizedVariation.split(' ')[0])) return true
      return false
    })
  }

  // First pass: Scan for label-value pairs in the entire worksheet
  // This handles the most common pattern: label in one cell, value in adjacent cell
  console.log('=== Pass 1: Horizontal label-value pairs ===')
  for (let R = 0; R < data.length; R++) {
    for (let C = 0; C < data[R].length - 1; C++) {
      const label = String(data[R][C]).toLowerCase().trim()
      const value = data[R][C + 1]
      
      // Skip empty labels or values
      if (!label || !value || value === '') continue
      
      // Check each required field
      for (const requiredField of filteredRequiredColumns) {
        const variations = fieldVariations[requiredField] || [requiredField.toLowerCase()]
        
        // Check if label matches any variation
        if (labelMatchesField(label, variations)) {
          // Create a unique key for this label-value pair
          const pairKey = `${label}_${value}_${R}_${C}`
          
          // Skip if this label-value pair is already used
          if (usedLabelValuePairs.has(pairKey)) continue
          
          // Only assign if not already detected (first match wins)
          if (!detectedFields[requiredField]) {
            const location = rowColToCellRef(R, C + 1)
            const matchedVariation = variations.find(v => labelMatchesField(label, [v]))
            const confidence = calculateConfidence(label, matchedVariation, value, requiredField)
            
            detectedFields[requiredField] = {
              value: value,
              location: location,
              confidence: confidence
            }
            usedLabelValuePairs.add(pairKey)
            console.log(`Detected "${requiredField}": "${value}" at ${location} (confidence: ${confidence.toFixed(2)})`)
            
            // Detect currency codes
            if (requiredField === 'Currency' || /^[A-Z]{3}$/.test(String(value).toUpperCase())) {
              detectedCurrencies.add(String(value).toUpperCase())
            }
          }
        }
      }
    }
  }
  console.log('Pass 1 detected fields:', Object.keys(detectedFields))

  // Second pass: Scan for vertical label-value pairs (label above value)
  console.log('=== Pass 2: Vertical label-value pairs ===')
  for (let R = 0; R < data.length - 1; R++) {
    for (let C = 0; C < data[R].length; C++) {
      const label = String(data[R][C]).toLowerCase().trim()
      const value = data[R + 1][C]
      
      // Skip empty labels or values
      if (!label || !value || value === '') continue
      
      // Check each required field
      for (const requiredField of filteredRequiredColumns) {
        const variations = fieldVariations[requiredField] || [requiredField.toLowerCase()]
        
        // Check if label matches any variation
        if (labelMatchesField(label, variations)) {
          // Create a unique key for this label-value pair
          const pairKey = `${label}_${value}_${R}_${C}`
          
          // Skip if this label-value pair is already used
          if (usedLabelValuePairs.has(pairKey)) continue
          
          // Only assign if not already detected
          if (!detectedFields[requiredField]) {
            const location = rowColToCellRef(R + 1, C)
            const matchedVariation = variations.find(v => labelMatchesField(label, [v]))
            const confidence = calculateConfidence(label, matchedVariation, value, requiredField)
            
            detectedFields[requiredField] = {
              value: value,
              location: location,
              confidence: confidence
            }
            usedLabelValuePairs.add(pairKey)
            console.log(`Detected "${requiredField}": "${value}" at ${location} (vertical, confidence: ${confidence.toFixed(2)})`)
            
            // Detect currency codes
            if (requiredField === 'Currency' || /^[A-Z]{3}$/.test(String(value).toUpperCase())) {
              detectedCurrencies.add(String(value).toUpperCase())
            }
          }
        }
      }
    }
  }
  console.log('Pass 2 detected fields:', Object.keys(detectedFields))

  // Third pass: Scan for table-like structures with headers in first row
  // This handles structured tables where field names are in a header row
  console.log('=== Pass 3: Table header structures ===')
  for (let R = 0; R < data.length; R++) {
    const row = data[R]
    if (!row || row.length === 0) continue
    
    // Check if this row looks like a header (contains field-like labels)
    const headerLabels = row.map(cell => String(cell).toLowerCase().trim())
    const hasFieldLabels = headerLabels.some(label => 
      Object.values(fieldVariations).flat().some(v => label.includes(v))
    )
    
    if (hasFieldLabels && R + 1 < data.length) {
      // This is likely a header row, get values from next row
      const valueRow = data[R + 1]
      
      for (let C = 0; C < row.length && C < valueRow.length; C++) {
        const label = headerLabels[C]
        const value = valueRow[C]
        
        if (!label || !value || value === '') continue
        
        // Check each required field
        for (const requiredField of filteredRequiredColumns) {
          const variations = fieldVariations[requiredField] || [requiredField.toLowerCase()]
          
          if (labelMatchesField(label, variations)) {
            // Create a unique key for this label-value pair
            const pairKey = `${label}_${value}_${R}_${C}`
            
            // Skip if this label-value pair is already used
            if (usedLabelValuePairs.has(pairKey)) continue
            
            if (!detectedFields[requiredField]) {
              const location = rowColToCellRef(R + 1, C)
              const matchedVariation = variations.find(v => labelMatchesField(label, [v]))
              const confidence = calculateConfidence(label, matchedVariation, value, requiredField)
              
              detectedFields[requiredField] = {
                value: value,
                location: location,
                confidence: confidence
              }
              usedLabelValuePairs.add(pairKey)
              console.log(`Detected "${requiredField}": "${value}" at ${location} (table, confidence: ${confidence.toFixed(2)})`)
              
              if (requiredField === 'Currency' || /^[A-Z]{3}$/.test(String(value).toUpperCase())) {
                detectedCurrencies.add(String(value).toUpperCase())
              }
            }
          }
        }
      }
    }
  }
  console.log('Pass 3 detected fields:', Object.keys(detectedFields))

  // Fourth pass: Scan for currency codes and exchange rates anywhere in the sheet
  console.log('=== Pass 4: Currency codes and exchange rates ===')
  for (let R = 0; R < data.length; R++) {
    for (let C = 0; C < data[R].length; C++) {
      const cellValue = data[R][C]
      
      // Check for currency codes (3-letter uppercase)
      if (cellValue && /^[A-Z]{3}$/.test(String(cellValue))) {
        detectedCurrencies.add(String(cellValue))
      }
      
      // Check if this looks like an exchange rate (decimal number)
      if (cellValue && !isNaN(parseFloat(cellValue)) && parseFloat(cellValue) > 0 && parseFloat(cellValue) < 1000) {
        // Check if there's a label nearby that indicates this is an exchange rate
        if (C > 0 && String(data[R][C-1]).toLowerCase().includes('exch')) {
          if (!detectedFields['Exchange Rate']) {
            const location = rowColToCellRef(R, C)
            detectedFields['Exchange Rate'] = {
              value: cellValue,
              location: location,
              confidence: 0.7
            }
            console.log(`Detected "Exchange Rate": "${cellValue}" at ${location} (confidence: 0.70)`)
          }
        }
        if (C < data[R].length - 1 && String(data[R][C+1]).toLowerCase().includes('exch')) {
          if (!detectedFields['Exchange Rate']) {
            const location = rowColToCellRef(R, C)
            detectedFields['Exchange Rate'] = {
              value: cellValue,
              location: location,
              confidence: 0.7
            }
            console.log(`Detected "Exchange Rate": "${cellValue}" at ${location} (confidence: 0.70)`)
          }
        }
      }
    }
  }
  console.log('Pass 4 detected fields:', Object.keys(detectedFields))
  console.log('Detected currencies:', Array.from(detectedCurrencies))

  // Pass 5: Comprehensive scattered field search - look for values near labels in any direction
  console.log('=== Pass 5: Comprehensive scattered field search ===')
  for (let R = 0; R < data.length; R++) {
    for (let C = 0; C < data[R].length; C++) {
      const cellValue = data[R][C]
      if (!cellValue || String(cellValue).trim() === '') continue
      
      const cellLower = String(cellValue).toLowerCase().trim()
      
      // Check if this cell could be a label for any required field
      for (const requiredField of filteredRequiredColumns) {
        if (detectedFields[requiredField]) continue // Already detected
        
        const variations = fieldVariations[requiredField] || [requiredField.toLowerCase()]
        
        // Check if current cell matches a field label
        if (labelMatchesField(cellLower, variations)) {
          // Search in all 8 directions for a value
          const directions = [
            { dr: 0, dc: 1 },   // Right
            { dr: 1, dc: 0 },   // Down
            { dr: 0, dc: -1 },  // Left
            { dr: -1, dc: 0 },  // Up
            { dr: 1, dc: 1 },   // Down-right
            { dr: 1, dc: -1 },  // Down-left
            { dr: -1, dc: 1 },  // Up-right
            { dr: -1, dc: -1 }  // Up-left
          ]
          
          for (const { dr, dc } of directions) {
            const searchR = R + dr
            const searchC = C + dc
            
            if (searchR >= 0 && searchR < data.length && searchC >= 0 && searchC < data[searchR].length) {
              const nearbyValue = data[searchR][searchC]
              if (nearbyValue && String(nearbyValue).trim() !== '') {
                // Validate the value for this field type
                if (isValidValueForField(requiredField, nearbyValue)) {
                  // Create a unique key for this label-value pair
                  const pairKey = `${cellLower}_${nearbyValue}_${searchR}_${searchC}`
                  
                  // Skip if this label-value pair is already used
                  if (usedLabelValuePairs.has(pairKey)) continue
                  
                  const location = rowColToCellRef(searchR, searchC)
                  const confidence = calculateConfidence(cellLower, cellLower, nearbyValue, requiredField)
                  
                  // Only assign if confidence is reasonable
                  if (confidence >= 0.4) {
                    detectedFields[requiredField] = {
                      value: nearbyValue,
                      location: location,
                      confidence: confidence
                    }
                    usedLabelValuePairs.add(pairKey)
                    console.log(`Detected "${requiredField}": "${nearbyValue}" at ${location} (scattered, confidence: ${confidence.toFixed(2)})`)
                    
                    // Detect currency codes
                    if (requiredField === 'Currency' || /^[A-Z]{3}$/.test(String(nearbyValue).toUpperCase())) {
                      detectedCurrencies.add(String(nearbyValue).toUpperCase())
                    }
                    break // Found a valid value, stop searching directions
                  }
                }
              }
            }
          }
        }
      }
    }
  }
  console.log('Pass 5 detected fields:', Object.keys(detectedFields))

  console.log('=== Final Detection Results ===')
  console.log('Total detected fields:', Object.keys(detectedFields).length)
  console.log('Missing fields:', requiredColumns.filter(col => !detectedFields[col]))

  // Convert detected fields to simple value format for backward compatibility
  const simpleDetectedFields = {}
  for (const [key, fieldData] of Object.entries(detectedFields)) {
    simpleDetectedFields[key] = fieldData.value
  }

  // Return both detected fields and currencies
  const missingFields = requiredColumns.filter(col => !detectedFields[col])
  console.log('AUTO DETECT CONTEXT (FINAL):', {
    instrumentType: effectiveInstrumentType,
    requiredFields: requiredColumns,
    detectedFields: simpleDetectedFields,
    missingFields: missingFields
  })
  
  return {
    fields: simpleDetectedFields,
    fieldsWithMetadata: detectedFields, // Full metadata including location and confidence
    currencies: Array.from(detectedCurrencies),
    missingFields: missingFields
  }
}

/**
 * Extract value from adjacent cells around a label
 * @param {Array} data - 2D array of worksheet data
 * @param {number} row - Row index of the label
 * @param {number} col - Column index of the label
 * @param {string} fieldType - Type of field being detected
 * @returns {string|null} Extracted value or null
 */
function extractValueFromAdjacent(data, row, col, fieldType) {
  // Check right cell (most common pattern)
  if (col + 1 < data[row].length) {
    const rightValue = data[row][col + 1]
    if (rightValue && rightValue !== '' && !isLabelLike(rightValue)) {
      return rightValue
    }
  }
  
  // Check left cell
  if (col - 1 >= 0) {
    const leftValue = data[row][col - 1]
    if (leftValue && leftValue !== '' && !isLabelLike(leftValue)) {
      return leftValue
    }
  }
  
  // Check below cell
  if (row + 1 < data.length && col < data[row + 1].length) {
    const belowValue = data[row + 1][col]
    if (belowValue && belowValue !== '' && !isLabelLike(belowValue)) {
      return belowValue
    }
  }
  
  // Check above cell
  if (row - 1 >= 0 && col < data[row - 1].length) {
    const aboveValue = data[row - 1][col]
    if (aboveValue && aboveValue !== '' && !isLabelLike(aboveValue)) {
      return aboveValue
    }
  }
  
  return null
}

/**
 * Check if a value looks like a label (not a data value)
 * @param {string} value - Value to check
 * @returns {boolean} True if value looks like a label
 */
function isLabelLike(value) {
  const str = String(value).toLowerCase().trim()
  const labelWords = ['name', 'value', 'rate', 'date', 'amount', 'price', 'yield', 'coupon', 'discount', 'maturity', 'issue', 'currency', 'days', 'count', 'total', 'instrument', 'bond', 'security']
  return labelWords.some(word => str.includes(word) && str.length < 20)
}
