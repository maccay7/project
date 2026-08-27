import * as XLSX from 'xlsx'

/**
 * Detect table boundaries in a worksheet
 * Finds the actual data table by identifying non-empty cell clusters
 * @param {Array} data - 2D array of worksheet data
 * @returns {Object} Table boundaries { startRow, endRow, startCol, endCol }
 */
function detectTableBoundaries(data) {
  console.log('=== Detecting Table Boundaries ===')
  
  if (!data || data.length === 0) {
    return { startRow: 0, endRow: data.length - 1, startCol: 0, endCol: 0 }
  }

  // Find the first non-empty row
  let startRow = 0
  for (let r = 0; r < data.length; r++) {
    if (data[r].some(cell => cell && String(cell).trim() !== '')) {
      startRow = r
      break
    }
  }

  // Find the last non-empty row
  let endRow = data.length - 1
  for (let r = data.length - 1; r >= startRow; r--) {
    if (data[r].some(cell => cell && String(cell).trim() !== '')) {
      endRow = r
      break
    }
  }

  // Find the first non-empty column
  let startCol = 0
  for (let c = 0; c < data[0].length; c++) {
    let hasContent = false
    for (let r = startRow; r <= endRow; r++) {
      if (data[r] && data[r][c] && String(data[r][c]).trim() !== '') {
        hasContent = true
        break
      }
    }
    if (hasContent) {
      startCol = c
      break
    }
  }

  // Find the last non-empty column
  let endCol = data[0].length - 1
  for (let c = data[0].length - 1; c >= startCol; c--) {
    let hasContent = false
    for (let r = startRow; r <= endRow; r++) {
      if (data[r] && data[r][c] && String(data[r][c]).trim() !== '') {
        hasContent = true
        break
      }
    }
    if (hasContent) {
      endCol = c
      break
    }
  }

  const boundaries = { startRow, endRow, startCol, endCol }
  console.log('Table boundaries:', boundaries)
  console.log('Table size:', endRow - startRow + 1, 'rows x', endCol - startCol + 1, 'cols')
  
  return boundaries
}

/**
 * Detect table orientation (vertical vs horizontal)
 * @param {Array} data - 2D array of worksheet data
 * @param {Object} boundaries - Table boundaries
 * @returns {string} 'vertical' or 'horizontal'
 */
function detectTableOrientation(data, boundaries) {
  const { startRow, endRow, startCol, endCol } = boundaries
  
  // Count label-like cells in first column vs first row
  let firstColLabels = 0
  let firstRowLabels = 0
  
  // Check first column for label-like content
  for (let r = startRow; r <= endRow; r++) {
    const cell = data[r] && data[r][startCol] ? String(data[r][startCol]).trim() : ''
    if (cell && cell.length > 0 && cell.length < 50 && !isNumeric(cell)) {
      firstColLabels++
    }
  }
  
  // Check first row for label-like content
  for (let c = startCol; c <= endCol; c++) {
    const cell = data[startRow] && data[startRow][c] ? String(data[startRow][c]).trim() : ''
    if (cell && cell.length > 0 && cell.length < 50 && !isNumeric(cell)) {
      firstRowLabels++
    }
  }
  
  const orientation = firstColLabels > firstRowLabels ? 'vertical' : 'horizontal'
  console.log('Table orientation:', orientation, `(firstColLabels: ${firstColLabels}, firstRowLabels: ${firstRowLabels})`)
  
  return orientation
}

/**
 * Check if a value is numeric
 */
function isNumeric(value) {
  if (value === null || value === undefined || value === '') return false
  const str = String(value).replace(/[%,\s]/g, '')
  return !isNaN(parseFloat(str)) && isFinite(str)
}

/**
 * Check if a value looks like a date
 */
function isDateLike(value) {
  if (!value || value === '') return false
  const str = String(value).trim()
  
  // Check for common date patterns
  const datePatterns = [
    /^\d{1,2}[-/]\d{1,2}[-/]\d{2,4}$/, // DD-MM-YYYY, MM/DD/YYYY
    /^\d{4}[-/]\d{1,2}[-/]\d{1,2}$/, // YYYY-MM-DD
    /^[A-Za-z]{3}[-/]\d{1,2}[-/]\d{2,4}$/, // Dec-31-2024
    /^\d{1,2}[-/][A-Za-z]{3}[-/]\d{2,4}$/, // 31-Dec-2024
    /^[A-Za-z]{3}\s+\d{1,2},\s+\d{4}$/ // Dec 31, 2024
  ]
  
  if (datePatterns.some(pattern => pattern.test(str))) return true
  
  // Check if it can be parsed as a date
  const date = new Date(str)
  if (!isNaN(date.getTime())) {
    // Check if it's not just a number (e.g., 2024 could be a year, not a date)
    if (!/^\d{4}$/.test(str)) return true
  }
  
  return false
}

/**
 * Auto-detect instrument fields from a worksheet
 * Scans the entire worksheet for label-value pairs in various layouts
 * @param {ArrayBuffer} fileBuffer - Excel file buffer
 * @param {string} sheetName - Name of the sheet to analyze
 * @param {Array} requiredColumns - Array of required column names for the instrument
 * @param {string} instrumentType - Type of instrument (bonds, money-market, treasury-bills)
 * @param {Object} tableRange - Optional table boundaries {startRow, endRow, startCol, endCol}
 * @param {Array} tableData - Optional pre-extracted table data (2D array)
 * @returns {Object} Detected fields, currencies, and missing fields
 */
export function autoDetectInstrumentFields(fileBuffer, sheetName, requiredColumns, instrumentType, tableRange = null, tableData = null) {
  // Parse workbook from buffer
  console.log('=== autoDetectInstrumentFields Started ===')
  console.log('Sheet Name:', sheetName)
  console.log('Instrument Type:', instrumentType)
  console.log('Required Columns:', requiredColumns)
  console.log('Table Range:', tableRange)
  console.log('Table Data Provided:', !!tableData)

  if (!fileBuffer || !sheetName) {
    throw new Error('File buffer and sheet name are required')
  }

  let data = []
  
  // If tableData is provided, use it directly (for multi-table detection)
  if (tableData && Array.isArray(tableData) && tableData.length > 0) {
    console.log('Using provided table data:', tableData.length, 'rows')
    console.log('Table data sample:', tableData.slice(0, 3))
    data = tableData
  } else {
    // Otherwise, parse the entire worksheet (for single-table detection)
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
  }
  
  console.log('Extracted Data Dimensions:', data.length, 'rows x', data[0]?.length || 0, 'cols')
  console.log('Sample Data (first 3 rows):', data.slice(0, 3))

  // Detect table boundaries for single-instrument detection
  // If tableRange is provided (multi-table mode), use it directly
  let tableBoundaries
  if (tableRange) {
    // When tableData is provided, the data is already extracted as a 0-based array
    // So we need to adjust boundaries to be relative to the table data (0-based)
    if (tableData) {
      tableBoundaries = {
        startRow: 0,
        endRow: data.length - 1,
        startCol: 0,
        endCol: data[0]?.length - 1 || 0
      }
      console.log('Using relative table boundaries for multi-table detection:', tableBoundaries)
    } else {
      // When no tableData, use absolute coordinates (single-table mode with range)
      tableBoundaries = {
        startRow: tableRange.startRow,
        endRow: tableRange.endRow,
        startCol: tableRange.startCol,
        endCol: tableRange.endCol
      }
      console.log('Using provided table range for single-table detection:', tableBoundaries)
    }
  } else {
    // Otherwise, detect boundaries from the data (single-table mode)
    tableBoundaries = detectTableBoundaries(data)
  }
  
  const tableOrientation = detectTableOrientation(data, tableBoundaries)
  
  console.log('=== SINGLE INSTRUMENT DETECTION CONTEXT ===')
  console.log('Worksheet Name (Instrument Name):', sheetName)
  console.log('Table Boundaries:', tableBoundaries)
  console.log('Table Orientation:', tableOrientation)
  console.log('Detection will be limited to table boundaries only')

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
    'DiscountRate': ['discount rate', 'discount', 'discount yield', 'rate', 'yield'],
    'Interest Rate': ['interest rate', 'rate', 'coupon rate', 'coupon', 'annual rate', 'interest', 'yield', 'nominal rate', 'fixed rate', 'floating rate'],
    'InterestRate': ['interest rate', 'rate', 'coupon rate', 'coupon', 'annual rate', 'interest', 'yield', 'nominal rate', 'fixed rate', 'floating rate', 'discount rate'],
    'Interest Accrued': ['interest accrued', 'accrued interest', 'interest accrued to', 'accrued interest to', 'interest accrued to 30 june 2024'],
    'InterestAccrued': ['interest accrued', 'accrued interest', 'interest accrued to', 'accrued interest to', 'interest accrued to 30 june 2024'],
    'Interest Pmt Frequency': ['interest pmt frequency', 'interest payment frequency', 'coupon frequency', 'payment frequency', 'frequency', 'pmt frequency', 'interest pmt fequency', 'annually', 'semi-annually', 'quarterly', 'monthly'],
    'InterestPmtFrequency': ['interest pmt frequency', 'interest payment frequency', 'coupon frequency', 'payment frequency', 'frequency', 'pmt frequency', 'interest pmt fequency', 'annually', 'semi-annually', 'quarterly', 'monthly'],
    'Frequency': ['frequency', 'interest pmt frequency', 'interest payment frequency', 'coupon frequency', 'payment frequency', 'pmt frequency', 'annually', 'semi-annually', 'quarterly', 'monthly', 'fequency'],
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
    'TBillName': ['t-bill name', 'instrument name', 'name', 'counterparty', 'issuer', 'borrower', 'party', 'entity', 'nhimbe', 'solgas', 'glytime', 'richaw', 'centragrid', 'gzh', 'zimcampus'],
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
    let score = 0.3 // Base score (lowered from 0.5)
    
    const dateFields = ['Date', 'Issue Date', 'Maturity Date', 'Valuation Date', 'Trade Date', 'Settlement Date', 'MaturityDate']
    
    // Exact match gets higher score
    if (label.toLowerCase() === matchedVariation.toLowerCase()) {
      score += 0.2
    }
    
    // Value looks valid (not empty, not just whitespace)
    if (value && String(value).trim() !== '') {
      score += 0.2
    }
    
    // Value validation based on field type (made more lenient)
    if (isValidValueForField(fieldName, value)) {
      score += 0.2
    }
    
    // Bonus for values that look like actual data (not headings)
    if (!isTableHeading(value)) {
      score += 0.1
    }
    
    return Math.max(0.1, Math.min(score, 1.0))
  }

  // Helper function to check if a value is a table heading (should not be used as data value)
  function isTableHeading(value) {
    const strValue = String(value).trim().toUpperCase()
    
    // Common table headings that should never be used as data values
    const tableHeadings = [
      'CF', 'PV', 'FV', 'NPV', 'IRR', 'BALANCE', 'PRINCIPAL', 'INTEREST',
      'CASH FLOW', 'PRESENT VALUE', 'FUTURE VALUE', 'NET PRESENT VALUE',
      'INTERNAL RATE OF RETURN', 'PAYMENT', 'PMT', 'RATE', 'NPER',
      'TOTAL', 'SUM', 'SUBTOTAL', 'GRAND TOTAL', 'AVERAGE', 'AVG',
      'MAX', 'MIN', 'COUNT', 'HEADER', 'LABEL', 'VALUE', 'AMOUNT',
      'DATE', 'PERIOD', 'YEAR', 'MONTH', 'QUARTER', 'DAY',
      'BEGINNING', 'ENDING', 'OPENING', 'CLOSING', 'START', 'END',
      'IN', 'OUT', 'INFLOW', 'OUTFLOW', 'DEBIT', 'CREDIT',
      'ASSET', 'LIABILITY', 'EQUITY', 'REVENUE', 'EXPENSE',
      'BUY', 'SELL', 'PURCHASE', 'SALE', 'TRANSACTION',
      'ROW', 'COLUMN', 'CELL', 'SHEET', 'WORKSHEET',
      'YES', 'NO', 'TRUE', 'FALSE', 'N/A', 'NA', 'NULL',
      'CATEGORY', 'TYPE', 'CLASS', 'GROUP', 'SECTION',
      'INPUT', 'OUTPUT', 'RESULT', 'CALCULATION', 'FORMULA'
    ]
    
    // Check if value matches any table heading
    if (tableHeadings.includes(strValue)) return true
    
    // Check if value is a very short abbreviation (likely a heading)
    if (strValue.length <= 3 && /^[A-Z]+$/.test(strValue)) {
      // Allow common currency codes
      if (!['USD', 'EUR', 'GBP', 'ZAR', 'ZWG', 'JPY', 'CAD', 'AUD'].includes(strValue)) {
        return true
      }
    }
    
    // Check if value looks like a column header (all caps, short)
    if (strValue.length <= 10 && /^[A-Z\s]+$/.test(strValue) && strValue.includes(' ')) {
      return true
    }
    
    return false
  }

  // Helper function to check if value is valid for field type
  function isValidValueForField(fieldName, value) {
    if (!value || value === '') return false
    
    // Reject table headings
    if (isTableHeading(value)) return false
    
    const numericFields = ['Principal', 'Face Value', 'Amount', 'Price', 'Interest Rate', 'Discount Rate', 'Yield', 'Coupon Rate', 'Present Value', 'Carrying Value', 'Fair Value', 'Impairment', 'Exchange Rate', 'Rate', 'FaceValue', 'InterestRate', 'DiscountRate']
    const dateFields = ['Date', 'Issue Date', 'Maturity Date', 'Valuation Date', 'Trade Date', 'Settlement Date', 'MaturityDate']
    const textFields = ['Instrument', 'Instrument Name', 'Bond Name', 'Issuer', 'Counterparty', 'Currency']
    
    if (numericFields.includes(fieldName)) {
      // Made more lenient - just check if it can be parsed as a number
      const strValue = String(value).trim()
      const currencySymbolRegex = /[%,\s$€£¥₹]/g
      const numericValue = strValue.replace(currencySymbolRegex, '')
      
      // Allow any numeric value, even if it looks like a date or text
      if (!isNaN(parseFloat(numericValue))) {
        return true
      }
      
      return false
    }
    
    if (dateFields.includes(fieldName)) {
      // Check if value looks like a date
      return !isNaN(Date.parse(value)) || /^\d{1,2}[-/]\d{1,2}[-/]\d{2,4}$/.test(value) || /^\d{1,2}-[A-Za-z]{3}-\d{2,4}$/.test(value)
    }
    
    if (textFields.includes(fieldName)) {
      // Accept any text value
      return String(value).trim().length > 0
    }
    
    return true // Accept any value for other fields
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
    'InterestRate': ['interest rate', 'coupon rate', 'rate', 'coupon', 'interest', 'interestrate', 'couponrate', 'annual rate', 'yield', 'discount rate'],
    'Coupon Rate': ['coupon rate', 'interest rate', 'coupon', 'rate', 'couponrate', 'interestrate'],
    'CouponRate': ['interest rate', 'coupon rate', 'rate', 'coupon', 'interest', 'interestrate', 'couponrate', 'annual rate'],
    'Yield': ['yield', 'ytm', 'yield to maturity', 'rate of return', 'ytm'],
    'Discount Rate': ['discount rate', 'discount', 'discount yield', 'rate'],
    'DiscountRate': ['discount rate', 'discount', 'discount yield', 'rate', 'yield'],
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
    'TBillName': ['counterparty', 'instrument name', 't-bill name', 'security name', 'issuer', 'borrower', 'party', 'entity', 'counter party', 'nhimbe', 'solgas', 'glytime', 'richaw', 'centragrid', 'gzh', 'zimcampus'],
    'Instrument': ['counterparty', 'instrument name', 'bond name', 't-bill name', 'security name', 'issuer', 'borrower', 'party', 'entity', 'counter party', 'nhimbe', 'solgas', 'glytime', 'richaw', 'centragrid', 'gzh', 'zimcampus'],
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

  // First pass: Scan for label-value pairs within table boundaries
  // This handles the most common pattern: label in one cell, value in adjacent cell
  console.log('=== Pass 1: Horizontal label-value pairs (within table boundaries) ===')
  for (let R = tableBoundaries.startRow; R <= tableBoundaries.endRow; R++) {
    for (let C = tableBoundaries.startCol; C < tableBoundaries.endCol; C++) {
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
            
            // Reject low-confidence matches (removed threshold to catch all fields)
            if (confidence < 0.0) {
              console.log(`Rejected "${requiredField}": "${value}" at ${location} (confidence: ${confidence.toFixed(2)} too low)`)
              continue
            }
            
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

  // Second pass: Scan for vertical label-value pairs within table boundaries (label above value)
  console.log('=== Pass 2: Vertical label-value pairs (within table boundaries) ===')
  for (let R = tableBoundaries.startRow; R < tableBoundaries.endRow; R++) {
    for (let C = tableBoundaries.startCol; C <= tableBoundaries.endCol; C++) {
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
            
            // Reject low-confidence matches (removed threshold to catch all fields)
            if (confidence < 0.0) {
              console.log(`Rejected "${requiredField}": "${value}" at ${location} (vertical, confidence: ${confidence.toFixed(2)} too low)`)
              continue
            }
            
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

  // Third pass: Scan for table-like structures with headers within table boundaries
  // This handles structured tables where field names are in a header row
  console.log('=== Pass 3: Table header structures (within table boundaries) ===')
  for (let R = tableBoundaries.startRow; R <= tableBoundaries.endRow; R++) {
    const row = data[R]
    if (!row || row.length === 0) continue
    
    // Check if this row looks like a header (contains field-like labels)
    const headerLabels = row.map(cell => String(cell).toLowerCase().trim())
    const hasFieldLabels = headerLabels.some(label => 
      Object.values(fieldVariations).flat().some(v => label.includes(v))
    )
    
    if (hasFieldLabels && R + 1 <= tableBoundaries.endRow) {
      // This is likely a header row, get values from next row
      const valueRow = data[R + 1]
      
      for (let C = tableBoundaries.startCol; C <= tableBoundaries.endCol && C < valueRow.length; C++) {
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
              
              // Reject low-confidence matches (removed threshold to catch all fields)
              if (confidence < 0.0) {
                console.log(`Rejected "${requiredField}": "${value}" at ${location} (table, confidence: ${confidence.toFixed(2)} too low)`)
                continue
              }
              
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

  // Fourth pass: Scan for currency codes and exchange rates within table boundaries
  console.log('=== Pass 4: Currency codes and exchange rates (within table boundaries) ===')
  for (let R = tableBoundaries.startRow; R <= tableBoundaries.endRow; R++) {
    for (let C = tableBoundaries.startCol; C <= tableBoundaries.endCol; C++) {
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

  // Pass 5: Comprehensive scattered field search within table boundaries - look for values near labels in any direction
  console.log('=== Pass 5: Comprehensive scattered field search (within table boundaries) ===')
  for (let R = tableBoundaries.startRow; R <= tableBoundaries.endRow; R++) {
    for (let C = tableBoundaries.startCol; C <= tableBoundaries.endCol; C++) {
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
          
          let valueFound = false
          for (const { dr, dc } of directions) {
            const searchR = R + dr
            const searchC = C + dc
            
            if (searchR >= 0 && searchR < data.length && searchC >= 0 && searchC < data[searchR].length) {
              const nearbyValue = data[searchR][searchC]
              if (nearbyValue && String(nearbyValue).trim() !== '') {
                // Validate the value for this field type
                if (isValidValueForField(requiredField, nearbyValue)) {
                  // CRITICAL: Check if this value is already assigned to another field
                  const valueStr = String(nearbyValue).trim()
                  let isDuplicate = false
                  for (const [existingField, existingData] of Object.entries(detectedFields)) {
                    if (existingField !== requiredField && String(existingData.value).trim() === valueStr) {
                      console.log(`Rejected "${requiredField}": "${nearbyValue}" (value already assigned to "${existingField}")`)
                      isDuplicate = true
                      break // Break out of duplicate check loop
                    }
                  }
                  
                  // If duplicate, skip this value entirely and continue to next direction
                  if (isDuplicate) continue
                  
                  // Create a unique key for this label-value pair
                  const pairKey = `${cellLower}_${nearbyValue}_${searchR}_${searchC}`
                  
                  // Skip if this label-value pair is already used
                  if (usedLabelValuePairs.has(pairKey)) continue
                  
                  const location = rowColToCellRef(searchR, searchC)
                  const confidence = calculateConfidence(cellLower, cellLower, nearbyValue, requiredField)
                  
                  // Only assign if confidence is high enough (removed threshold to catch all fields)
                  if (confidence >= 0.0) {
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
                    valueFound = true
                    break // Found a valid value, stop searching directions
                  }
                }
              }
            }
          }
          
          // If we found a value, move to next required field
          if (valueFound) break
        }
      }
    }
  }
  console.log('Pass 5 detected fields:', Object.keys(detectedFields))

  console.log('=== Final Detection Results ===')
  console.log('Total detected fields:', Object.keys(detectedFields).length)
  console.log('Missing fields:', requiredColumns.filter(col => !detectedFields[col]))

  // CRITICAL: Instrument name handling
  // For single-instrument detection (no tableData provided), instrument name MUST come from worksheet name
  // For multi-table detection (tableData provided), use detected "Instrument" field or table name
  if (requiredColumns.includes('Instrument Name') || requiredColumns.includes('BondName') || requiredColumns.includes('TBillName')) {
    const instrumentNameField = requiredColumns.includes('Instrument Name') ? 'Instrument Name' : 
                                requiredColumns.includes('BondName') ? 'BondName' : 'TBillName'
    
    if (tableData) {
      // Multi-table mode: use detected Instrument field if available, otherwise use a placeholder
      if (detectedFields['Instrument']) {
        detectedFields[instrumentNameField] = detectedFields['Instrument']
      } else if (detectedFields['Counterparty']) {
        detectedFields[instrumentNameField] = detectedFields['Counterparty']
      } else {
        // Fallback to a generic name based on table position
        detectedFields[instrumentNameField] = {
          value: 'Instrument',
          location: 'N/A',
          confidence: 0.5
        }
      }
    } else {
      // Single-table mode: Force instrument name to be the worksheet name
      detectedFields[instrumentNameField] = {
        value: sheetName,
        location: 'Worksheet Name',
        confidence: 1.0
      }
      console.log(`FORCED: ${instrumentNameField} = "${sheetName}" (from worksheet name)`)
    }
  }

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
