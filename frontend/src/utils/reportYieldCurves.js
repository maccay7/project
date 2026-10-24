/**
 * Load and render per-instrument yield curves for combined reports.
 * Uses session workflow (Visualizations) first, then FRED with saved filters,
 * then portfolio valuation rows — never mock or duplicated curves.
 */

const COUNTRY_MAP = {
  USA: 'US', US: 'US', GBR: 'GB', GB: 'GB', EUR: 'EUR', JPN: 'JP', JP: 'JP',
  CAN: 'CA', CA: 'CA', AUS: 'AU', AU: 'AU', ZAF: 'ZA', ZA: 'ZA'
}

export const REPORT_INSTRUMENT_META = [
  { key: 'money-market', label: 'Money Market', apiType: 'money-market', color: '#1E88E5' },
  { key: 'bonds', label: 'Bonds', apiType: 'bonds', color: '#4CAF50' },
  { key: 'tbills', label: 'T-Bills', apiType: 'tbills', color: '#FF9800' }
]

function normalizeCountry(country) {
  if (!country) return 'US'
  const u = String(country).toUpperCase()
  return COUNTRY_MAP[u] || u
}

function toNumber(val) {
  if (val === null || val === undefined || val === '') return null
  if (typeof val === 'number') return isNaN(val) ? null : val
  const n = parseFloat(String(val).replace(/[$,%\s]/g, '').replace(/,/g, ''))
  return isNaN(n) ? null : n
}

/** Normalize saved yieldCurveData from session to { x, y, maturityLabel, date, isDateMode } */
export function normalizeYieldPoints(raw) {
  if (!raw || !Array.isArray(raw) || !raw.length) return { points: [], isDateMode: false }

  const points = []
  let isDateMode = false

  for (const p of raw) {
    if (p == null) continue
    if (typeof p === 'object') {
      const rate = toNumber(p.rate ?? p.y ?? p.value)
      if (rate === null) continue

      if (p.date && (p.maturity === undefined || p.maturity === null)) {
        isDateMode = true
        points.push({
          x: new Date(p.date).getTime(),
          y: rate,
          maturityLabel: p.date,
          date: p.date,
          isDate: true
        })
      } else {
        const mat = toNumber(p.maturity ?? p.x) ?? 0
        points.push({
          x: mat,
          y: rate,
          maturityLabel: p.maturityLabel || String(mat),
          date: p.date || null,
          isDate: false
        })
      }
    }
  }

  points.sort((a, b) => {
    if (a.isDate && b.isDate) return a.x - b.x
    return a.x - b.x
  })

  return { points, isDateMode }
}

function pointsFromFredResponse(data) {
  if (!data) return []
  if (data.maturities?.length && data.rates?.length) {
    return data.maturities.map((m, i) => ({
      x: parseFloat(m),
      y: parseFloat(data.rates[i]),
      maturityLabel: data.labels?.[i] || String(m),
      date: data.dates?.[i] || null,
      isDate: false
    })).filter(p => !isNaN(p.y))
  }
  if (data.datasets?.[0]?.data?.length) {
    const ds = data.datasets[0].data
    return ds.map(pt => {
      const y = toNumber(pt.y ?? pt.rate)
      if (y === null) return null
      if (pt.date || (typeof pt.x === 'string' && pt.x.includes('-'))) {
        const d = pt.date || pt.x
        return { x: new Date(d).getTime(), y, maturityLabel: d, date: d, isDate: true }
      }
      return {
        x: parseFloat(pt.x ?? pt.maturity ?? 0),
        y,
        maturityLabel: pt.label || String(pt.x),
        date: pt.date || null,
        isDate: false
      }
    }).filter(Boolean)
  }
  return []
}

/** Build curve from saved portfolio detail rows (maturity vs rate/yield). */
export function buildCurveFromPortfolioDetails(details, instrumentKey) {
  if (!Array.isArray(details) || !details.length) return []

  const rateKeys = [
    'Yield', 'yield', 'Avg Rate', 'avg_rate', 'Interest Rate', 'interest_rate',
    'Coupon Rate', 'coupon_rate', 'Discount Rate', 'discount_rate',
    'Yield to Maturity', 'yield_to_maturity', 'Effective Yield', 'effective_yield'
  ]
  const termKeys = [
    'Days to Maturity', 'days_to_maturity', 'Term', 'term', 'Years to Maturity', 'years_to_maturity'
  ]

  const pick = (row, keys) => {
    for (const k of keys) {
      if (row[k] !== undefined && row[k] !== null && row[k] !== '') return row[k]
    }
    const lower = Object.keys(row).reduce((a, k) => { a[k.toLowerCase()] = row[k]; return a }, {})
    for (const k of keys) {
      const v = lower[k.toLowerCase()]
      if (v !== undefined && v !== null && v !== '') return v
    }
    return null
  }

  const buckets = new Map()

  for (const row of details) {
    const rateRaw = pick(row, rateKeys)
    const termRaw = pick(row, termKeys)
    const rate = toNumber(rateRaw)
    if (rate === null) continue

    let years = null
    const termNum = toNumber(termRaw)
    if (termNum !== null) {
      years = termNum > 50 ? termNum / 365 : termNum
    }
    if (years === null || years <= 0) continue

    const key = years.toFixed(4)
    if (!buckets.has(key)) {
      buckets.set(key, { sumRate: 0, count: 0, years })
    }
    const b = buckets.get(key)
    b.sumRate += rate
    b.count += 1
  }

  if (buckets.size < 2) return []

  return Array.from(buckets.values())
    .map(b => ({
      x: b.years,
      y: b.sumRate / b.count,
      maturityLabel: b.years >= 1 ? `${b.years.toFixed(2)}Y` : `${Math.round(b.years * 365)}D`,
      date: null,
      isDate: false,
      source: 'portfolio_valuation'
    }))
    .sort((a, b) => a.x - b.x)
}

async function fetchFredCurvePoints(api, instrumentType, fredFilters) {
  if (!fredFilters?.country || !api?.fredAPI?.getYieldCurve) return []

  const country = normalizeCountry(fredFilters.country)
  const payload = {
    instrument_type: instrumentType,
    country,
    currency: fredFilters.currency || 'USD'
  }

  if (fredFilters.maturityMode === 'date' && fredFilters.fromDate && fredFilters.toDate) {
    payload.from_date = fredFilters.fromDate
    payload.to_date = fredFilters.toDate
  } else if (fredFilters.maturity) {
    payload.maturity = fredFilters.maturity
  }

  try {
    const res = await api.fredAPI.getYieldCurve(payload)
    if (res?.success && res.data) return pointsFromFredResponse(res.data)
  } catch (e) {
    console.warn('Report FRED fetch failed:', instrumentType, e)
  }
  return []
}

/**
 * Load yield curves for each selected instrument in the current session.
 */
export async function loadReportYieldCurves({
  sessionId,
  selectedInstruments,
  sessionManager,
  api,
  portfolioSummaries = []
}) {
  const curves = []

  for (const meta of REPORT_INSTRUMENT_META) {
    if (!selectedInstruments?.[meta.key]) continue

    const summary = portfolioSummaries.find(s => s.id === meta.key)
    const calc = summary?.calculations
    const hasValuation = calc && (toNumber(calc.totalValue) > 0 || toNumber(calc.instrumentCount) > 0)

    if (!hasValuation) {
      curves.push({
        ...meta,
        status: 'no_valuation',
        message: `No saved valuation results for ${meta.label} in this session. Complete calculations for this instrument first.`,
        points: [],
        fredFilters: null
      })
      continue
    }

    let workflow = null
    try {
      workflow = await sessionManager.getInstrumentWorkflow(sessionId, meta.key)
    } catch (e) {
      console.warn('Workflow load failed', meta.key, e)
    }

    const fredFilters = workflow?.fredFilters || null
    let { points, isDateMode } = normalizeYieldPoints(workflow?.yieldCurveData)
    let dataSource = points.length ? 'session_visualization' : null

    if (!points.length && fredFilters?.country) {
      points = await fetchFredCurvePoints(api, meta.apiType, fredFilters)
      isDateMode = points.some(p => p.isDate)
      if (points.length) dataSource = 'fred_api'
    }

    if (!points.length && summary?.details?.length) {
      points = buildCurveFromPortfolioDetails(summary.details, meta.key)
      isDateMode = false
      if (points.length) dataSource = 'portfolio_valuation'
    }

    // ── Insufficient data (0 or 1 point) → explain, do not fabricate ──
    if (points.length < 2) {
      const reason = points.length === 0
        ? 'no valid (maturity, yield) observations were found'
        : `only ${points.length} valid observation was found (a curve needs at least 2)`
      curves.push({
        ...meta,
        status: 'insufficient',
        message: `Insufficient data to plot a yield curve for ${meta.label}: ${reason}. Open Visualizations for ${meta.label}, refresh the FRED curve and save the session — or ensure portfolio rows include rate and maturity fields.`,
        points: [],
        fredFilters
      })
      continue
    }

    curves.push({
      ...meta,
      status: 'ok',
      points,
      isDateMode,
      fredFilters,
      dataSource,
      svg: buildYieldCurveSvg(points, { title: meta.label, color: meta.color, isDateMode })
    })
  }

  return curves
}

/** Simple SVG line chart for report export (no canvas capture needed). */
export function buildYieldCurveSvg(points, { title = 'Yield Curve', color = '#0B2044', isDateMode = false, width = 720, height = 280 } = {}) {
  const valid = points.filter(p => p.y != null && !isNaN(p.y) && p.x != null && !isNaN(p.x))
  if (valid.length < 2) return ''

  const xs = valid.map(p => p.x)
  const ys = valid.map(p => p.y)
  const dataMinX = Math.min(...xs)
  const dataMaxX = Math.max(...xs)

  // Numeric mode: axis starts at 0 (yield curves conventionally originate at the short end).
  // Date mode: use the actual date range.
  const plotMinX = isDateMode ? dataMinX : 0
  const plotMaxX = isDateMode ? dataMaxX : Math.ceil(dataMaxX)

  // Decide whether to rotate labels (based on how many ticks we will draw)
  let labelCount
  if (isDateMode) {
    const yearSet = new Set()
    for (const p of valid) yearSet.add(new Date(p.x).getFullYear())
    labelCount = yearSet.size
  } else {
    labelCount = plotMaxX - plotMinX + 1
  }
  const rotate = labelCount > 12

  const pad = { l: 56, r: 24, t: 36, b: rotate ? 68 : 48 }
  const plotW = width - pad.l - pad.r
  const plotH = height - pad.t - pad.b

  const minY = Math.min(...ys)
  const maxY = Math.max(...ys)
  const yPad = (maxY - minY) * 0.08 || 0.5
  const yMin = minY - yPad
  const yMax = maxY + yPad

  const sx = x => pad.l + ((x - plotMinX) / (plotMaxX - plotMinX || 1)) * plotW
  const sy = y => pad.t + plotH - ((y - yMin) / (yMax - yMin || 1)) * plotH

  const poly = valid.map(p => `${sx(p.x).toFixed(1)},${sy(p.y).toFixed(1)}`).join(' ')

  // ── X-axis labels: every year in numeric mode, one per year in date mode ──
  const labelY = height - 12
  const xLabels = []

  if (isDateMode) {
    const seenYears = new Set()
    for (const p of valid) {
      const year = new Date(p.x).getFullYear()
      if (seenYears.has(year)) continue
      seenYears.add(year)
      const xPos = sx(p.x).toFixed(1)
      if (rotate) {
        xLabels.push(`<text x="${xPos}" y="${labelY}" text-anchor="end" font-size="10" fill="#555" transform="rotate(-45 ${xPos} ${labelY})">${year}</text>`)
      } else {
        xLabels.push(`<text x="${xPos}" y="${labelY}" text-anchor="middle" font-size="10" fill="#555">${year}</text>`)
      }
    }
  } else {
    for (let yr = plotMinX; yr <= plotMaxX; yr++) {
      const xPos = sx(yr).toFixed(1)
      if (rotate) {
        xLabels.push(`<text x="${xPos}" y="${labelY}" text-anchor="end" font-size="10" fill="#555" transform="rotate(-45 ${xPos} ${labelY})">${yr}</text>`)
      } else {
        xLabels.push(`<text x="${xPos}" y="${labelY}" text-anchor="middle" font-size="10" fill="#555">${yr}</text>`)
      }
    }
  }

  return `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" role="img" aria-label="${escapeHtml(title)} yield curve">
  <rect width="100%" height="100%" fill="#fafbff"/>
  <text x="${pad.l}" y="22" font-size="14" font-weight="600" fill="${color}">${escapeHtml(title)} — Yield Curve (%)</text>
  <line x1="${pad.l}" y1="${pad.t + plotH}" x2="${pad.l + plotW}" y2="${pad.t + plotH}" stroke="#ccc"/>
  <line x1="${pad.l}" y1="${pad.t}" x2="${pad.l}" y2="${pad.t + plotH}" stroke="#ccc"/>
  <text x="12" y="${pad.t + plotH / 2}" font-size="10" fill="#666" transform="rotate(-90 12 ${pad.t + plotH / 2})">Rate (%)</text>
  <text x="${pad.l + plotW / 2}" y="${height - 2}" text-anchor="middle" font-size="10" fill="#666">${isDateMode ? 'Date' : 'Maturity (years)'}</text>
  <polyline fill="none" stroke="${color}" stroke-width="2.5" points="${poly}"/>
  ${valid.map(p => `<circle cx="${sx(p.x).toFixed(1)}" cy="${sy(p.y).toFixed(1)}" r="3.5" fill="${color}"/>`).join('')}
  ${xLabels.join('')}
</svg>`
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

function formatFilters(f) {
  if (!f) return '—'
  const parts = []
  if (f.country) parts.push(`Country: ${f.country}`)
  if (f.currency) parts.push(`Currency: ${f.currency}`)
  if (f.maturityMode === 'date' && f.fromDate && f.toDate) {
    parts.push(`Date range: ${f.fromDate} to ${f.toDate}`)
  } else if (f.maturity) {
    parts.push(`Maturity focus: ${f.maturity}`)
  }
  return parts.length ? parts.join(' · ') : '—'
}

function appendixTableForCurve(curve) {
  if (!curve.points?.length) return ''
  const header = curve.isDateMode
    ? '<tr><th>Date</th><th>Rate (%)</th></tr>'
    : '<tr><th>Maturity</th><th>Term (Yr)</th><th>Rate (%)</th></tr>'

  const rows = curve.points.map(p => {
    if (curve.isDateMode) {
      return `<tr><td>${escapeHtml(p.maturityLabel || p.date || '')}</td><td>${Number(p.y).toFixed(4)}</td></tr>`
    }
    return `<tr><td>${escapeHtml(p.maturityLabel || '')}</td><td>${Number(p.x).toFixed(4)}</td><td>${Number(p.y).toFixed(4)}</td></tr>`
  }).join('')

  return `<table class="appendix-table"><thead>${header}</thead><tbody>${rows}</tbody></table>`
}

const SOURCE_LABELS = {
  session_visualization: 'Saved from Visualizations (this session)',
  fred_api: 'FRED API (filters saved for this instrument)',
  portfolio_valuation: 'Derived from saved valuation rows (rate vs maturity)'
}

/** HTML block for Yield Curve report page — one section per instrument. */
export function buildReportYieldCurvesSectionHtml(curves) {
  if (!curves?.length) {
    return '<p>No instruments selected for yield curve display.</p>'
  }

  return curves.map(curve => {
    // Any non-ok status renders a clear message, never an empty chart
    if (curve.status !== 'ok' || !curve.svg || !curve.points?.length) {
      return `<div class="yield-curve-instrument-block" style="margin-bottom:28px;padding:16px;background:#fff8f0;border-left:4px solid #FF9800;border-radius:8px;">
        <h3 style="color:#0B2044;font-size:18px;margin-bottom:8px;">${escapeHtml(curve.label)}</h3>
        <p style="color:#666;font-size:14px;">${escapeHtml(curve.message || 'No live yield-curve data available for this instrument.')}</p>
      </div>`
    }

    const src = SOURCE_LABELS[curve.dataSource] || 'Live FRED'
    return `<div class="yield-curve-instrument-block" style="margin-bottom:32px;">
      <h3 style="color:#0B2044;font-size:18px;margin-bottom:6px;">${escapeHtml(curve.label)}</h3>
      <p style="font-size:13px;color:#555;margin-bottom:4px;"><strong>Benchmark source:</strong> ${escapeHtml(src)}</p>
      <p style="font-size:13px;color:#555;margin-bottom:12px;"><strong>Market filters:</strong> ${escapeHtml(formatFilters(curve.fredFilters))}</p>
      <div class="chart-container">${curve.svg}</div>
    </div>`
  }).join('')
}

/** Appendix HTML for all instrument curves. */
export function buildReportYieldCurvesAppendixHtml(curves, valuationDate) {
  const ok = curves.filter(c => c.status === 'ok' && c.points?.length)
  if (!ok.length) {
    return '<p>No yield curve data points available for selected instruments.</p>'
  }

  return ok.map(curve => `
    <h3 style="font-size:16px;color:#0B2044;margin:20px 0 8px;">${escapeHtml(curve.label)} — FRED / Benchmark Data</h3>
    <p style="font-size:12px;color:#666;">Valuation date context: ${escapeHtml(valuationDate || '—')} · ${escapeHtml(formatFilters(curve.fredFilters))}</p>
    ${appendixTableForCurve(curve)}
  `).join('')
}