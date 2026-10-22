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
  // NO FALLBACK - return empty if no valid FRED data
  return []
}

/**
 * Build a linear x-axis config where every integer year from 0 to maxYears
 * gets an explicit tick — no auto-skip. Use in live Chart.js components
 * (Dashboard / Visualizations) so a 10-year chart shows 0,1,2,…,10.
 *
 * Usage:
 *   import { buildLinearXAxisConfig } from '@/services/yieldCurveChart'
 *   options: {
 *     scales: {
 *       x: buildLinearXAxisConfig(this.horizonYears),   // e.g. 10
 *       y: { ...existing y-axis config... }
 *     }
 *   }
 */
export function buildLinearXAxisConfig(maxYears, { maxRotation = 0 } = {}) {
  const max = Math.max(0, Math.ceil(maxYears))
  return {
    type: 'linear',
    min: 0,
    max,
    ticks: {
      stepSize: 1,
      autoSkip: false,
      maxRotation,
      minRotation: maxRotation,
      callback: value => (Number.isInteger(value) ? value : null)
    },
    grid: { color: 'rgba(0,0,0,0.06)' },
    title: { display: true, text: 'Years from start' }
  }
}

export const INSTRUMENT_API_MAP = {
  'Money Market': 'money_market',
  'Bonds': 'bonds',
  'T-Bills': 'treasury_bills',
  'Treasury Bills': 'treasury_bills'
}