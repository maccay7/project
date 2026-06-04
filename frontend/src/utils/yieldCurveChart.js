/** Turn backend FRED response into Chart.js datasets */
export function toChartDatasets(apiData, fallbackLabel = 'Yield') {
  if (!apiData) return []
  if (apiData.datasets?.length) {
    return apiData.datasets.map(d => ({
      label: d.label,
      data: d.data,
      borderColor: d.borderColor || '#0B2044',
      backgroundColor: 'rgba(11, 42, 68, 0.08)',
      borderWidth: 2,
      tension: 0.35,
      fill: false
    }))
  }
  return [{
    label: fallbackLabel,
    data: apiData.current || [],
    borderColor: '#0B2044',
    backgroundColor: 'rgba(11, 42, 68, 0.1)',
    borderWidth: 2,
    tension: 0.35,
    fill: true
  }]
}

export const INSTRUMENT_API_MAP = {
  'Money Market': 'money_market',
  'Bonds': 'bonds',
  'T-Bills': 'treasury_bills',
  'Treasury Bills': 'treasury_bills'
}
