// Instrument-specific column configurations for summaries
export const INSTRUMENT_COLUMNS = {
  'Bonds': [
    'Counterparty',
    'Bond Holder',
    'Instrument Type',
    'Issue Date',
    'Maturity Date',
    'Notional Amount',
    'Currency',
    'Coupon/Interest Rate',
    'Coupon Payment Frequency',
    'Present Value',
    'Impairment'
  ],
  'Money Market': [
    'Counterparty',
    'Instrument Type',
    'Face Value',
    'Currency',
    'Discount Rate',
    'Maturity Date',
    'Days to Maturity',
    'Purchase Price',
    'Yield',
    'Market Value'
  ],
  'Treasury Bills': [
    'Counterparty',
    'Instrument Type',
    'Issue Date',
    'Maturity Date',
    'Face Value',
    'Currency',
    'Discount Rate',
    'Price',
    'Yield',
    'Tenor (Days)'
  ],
  'Corporate Bonds': [
    'Counterparty',
    'Bond Holder',
    'Instrument Type',
    'Issue Date',
    'Maturity Date',
    'Notional Amount',
    'Currency',
    'Coupon/Interest Rate',
    'Coupon Payment Frequency',
    'Present Value',
    'Impairment'
  ]
}

// Total calculation fields per instrument type
export const TOTAL_FIELDS = {
  'Bonds': ['Notional Amount', 'Present Value', 'Impairment'],
  'Money Market': ['Face Value', 'Market Value'],
  'Treasury Bills': ['Face Value'],
  'Corporate Bonds': ['Notional Amount', 'Present Value', 'Impairment']
}

// Helper function to get columns for an instrument type
export function getInstrumentColumns(instrumentType) {
  return INSTRUMENT_COLUMNS[instrumentType] || INSTRUMENT_COLUMNS['Bonds']
}

// Helper function to get total fields for an instrument type
export function getTotalFields(instrumentType) {
  return TOTAL_FIELDS[instrumentType] || TOTAL_FIELDS['Bonds']
}
