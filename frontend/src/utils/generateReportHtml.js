/**
 * Generate IFRS‑style report HTML with yield curve appendix from session filters.
 * @param {Array} data - The instrument data rows.
 * @param {string} instrument - Instrument type (e.g., 'money-market').
 * @param {string} session - Session name.
 * @param {string} date - Report generation date.
 * @param {string} valuationDate - Valuation date (YYYY-MM-DD).
 * @param {string} chartImageData - Base64 PNG of yield curve chart.
 * @param {Object} fredFilters - { country, currency, maturity } from session.
 * @param {Array} yieldCurveData - Array of { maturity, maturityLabel, rate }.
 * @returns {string} Full HTML report.
 */
export function generateReportHtml(
  data,
  instrument,
  session,
  date,
  valuationDate,
  chartImageData = '',
  fredFilters = { country: 'US', currency: 'USD', maturity: '1Y' },
  yieldCurveData = []
) {
  const valDate = valuationDate || new Date().toISOString().split('T')[0]
  const totalValue = data.reduce((s, r) => s + (parseFloat(r.FaceValue || r.Amount || r.Principal || 0)), 0)
  const totalInterest = data.reduce((s, r) => s + (parseFloat(r.InterestEarned || r.Interest || 0)), 0)
  const rates = data.map(r => parseFloat(r.Rate || r.InterestRate || r.CouponRate || r.DiscountRate || 0)).filter(r => !isNaN(r) && r > 0)
  const avgRate = rates.length ? rates.reduce((a, b) => a + b, 0) / rates.length : 0

  const instType = instrument.toLowerCase()
  let methodology = '',
    formulas = '',
    assumptions = ''
  if (instType.includes('money') || instType === 'money-market') {
    methodology = 'Money Market Instruments: Short-term debt instruments valued using discounted cash flow methodology.'
    formulas = 'Fair value = F / (1 + r·t/365) where F = Face value, r = annualized interest rate, t = days to maturity.'
    assumptions = 'Simple interest convention (365 days/year). Weighted average rate = Σ (Rate × Amount) / Σ Amount.'
  } else if (instType.includes('bond')) {
    methodology = 'Corporate Bonds: Fixed income securities valued using present value of future cash flows.'
    formulas = 'Fair value = Σ C/(1+y)^t + FV/(1+y)^n where C = annual coupon payment, y = yield to maturity, FV = face value, n = years to maturity.'
    assumptions = 'Coupon payments are annualized. Duration = Σ (t × PV(C_t)) / Price.'
  } else if (instType.includes('tbill') || instType.includes('t-bill')) {
    methodology = 'Treasury Bills: Short-term government securities valued using discount yield methodology.'
    formulas = 'Discount amount = Face value × (Discount rate/100) × (Days to maturity/360). Effective yield = (Face value / Price − 1) × (365 / Days to maturity) × 100.'
    assumptions = 'Bank discount basis (360 days/year) for discount rate; bond equivalent yield uses 365 days.'
  } else {
    methodology = 'General fixed income valuation methodology.'
    formulas = 'Present value of expected future cash flows discounted at appropriate market rates.'
    assumptions = 'Standard market conventions applied.'
  }

  let instrumentRows = ''
  data.forEach((item, idx) => {
    const name = item.Instrument || item.BondName || item.TBillName || `Instrument ${idx + 1}`
    const faceValue = parseFloat(item.FaceValue || item.Amount || item.Principal || 0)
    const rate = parseFloat(item.Rate || item.InterestRate || item.CouponRate || item.DiscountRate || 0)
    const term = parseFloat(item.Term || item.YearsToMaturity || 0) || (parseFloat(item.MaturityDate) ? (new Date(item.MaturityDate) - new Date(item.IssueDate || Date.now())) / (365 * 24 * 60 * 60 * 1000) : 0)
    const ticker = item.BBTicker || item.Ticker || item.Security || 'N/A'
    instrumentRows += `<tr><td>${name}</td><td>${ticker}</td><td>${faceValue.toFixed(2)}</td><td>${rate.toFixed(4)}%</td><td>${term.toFixed(2)}</td><td>${valDate}</td></tr>`
  })

  // Build appendix rows from yieldCurveData
  let appendixRows = ''
  if (yieldCurveData && yieldCurveData.length) {
    appendixRows = yieldCurveData.map(point => `
      <tr>
        <td>${point.maturityLabel || point.maturity || ''}</td>
        <td>${point.maturity || 0}</td>
        <td>${point.rate || 0}%</td>
      </tr>
    `).join('')
  }

  const logoUrl = '/DuraCapital logo.png'
  const backgroundCoverUrl = '/reportbackground.png'
  const chartHtml = chartImageData ?
    `<div class="chart-container"><img src="${chartImageData}" alt="Yield Curve" style="max-width:100%; height:auto; border-radius:8px; border:1px solid #e0e0e0;" /><p class="chart-caption">FRED Yield Curve – ${instrument} (${fredFilters.country} / ${fredFilters.currency})</p></div>` :
    '<p>Yield curve chart not available.</p>'

  return `<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Valuation Assessment Report - ${session}</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: 'Arial', sans-serif; color: #000; background: white; line-height: 1.6; margin: 0; padding: 0; }
    .page { page-break-after: always; padding: 40px 50px; min-height: 100vh; position: relative; width: 210mm; margin: 0 auto; background: white; }
    .page:last-child { page-break-after: auto; }
    .cover-page { background-color: white; background-image: url('${backgroundCoverUrl}'); background-size: 30%; background-position: right center; background-repeat: no-repeat; color: black; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; padding: 40px 50px; position: relative; min-height: 100vh; width: 210mm; margin: 0 auto; }
    .cover-content { max-width: 70%; position: relative; z-index: 2; color: black; }
    .cover-logo { position: absolute; top: 30px; left: 40px; z-index: 3; }
    .cover-logo img { max-width: 140px; height: auto; background: white; padding: 4px; }
    .cover-session-name { font-size: 44px; font-weight: 300; letter-spacing: 2px; margin-bottom: 10px; color: #000; }
    .cover-title { font-size: 48px; font-weight: 700; letter-spacing: 2px; margin-bottom: 20px; color: #000; }
    .cover-subtitle { font-size: 28px; font-weight: 300; opacity: 0.85; margin-bottom: 20px; color: #000; }
    .toc-page h1 { font-size: 28px; color: #0B2044; border-bottom: 3px solid #0B2044; padding-bottom: 15px; margin-bottom: 30px; }
    .toc-item { display: flex; justify-content: space-between; padding: 12px 0; border-bottom: 1px dotted #ddd; font-size: 16px; }
    .section-title { font-size: 24px; color: #0B2044; border-bottom: 2px solid #0B2044; padding-bottom: 10px; margin: 30px 0 20px 0; }
    .executive-summary { background: #f8f9ff; padding: 25px; border-radius: 10px; border-left: 4px solid #0B2044; margin-bottom: 25px; }
    .executive-summary .highlight { color: #0B2044; font-weight: 700; }
    .methodology-box { background: #f8f9ff; padding: 20px; border-radius: 8px; margin: 15px 0; }
    .methodology-box .formula { font-family: 'Courier New', monospace; font-size: 16px; background: white; padding: 10px 15px; border-radius: 6px; border: 1px solid #e0e0e0; margin: 10px 0; }
    table { width: 100%; border-collapse: collapse; margin: 20px 0; font-size: 14px; }
    th { background: #0B2044; color: white; padding: 12px 10px; text-align: left; }
    td { padding: 10px; border-bottom: 1px solid #eee; }
    tr:hover { background: #f5f8ff; }
    .appendix-table { font-size: 12px; }
    .appendix-table th { background: #1a3a6e; }
    .appendix-table td { padding: 6px 8px; }
    .footer { margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 12px; color: #999; text-align: center; }
    .reference-list { list-style: none; padding: 0; }
    .reference-list li { padding: 8px 0; border-bottom: 1px solid #eee; }
    .chart-container { margin: 20px 0; text-align: center; }
    .chart-container img { max-width: 100%; height: auto; border-radius: 8px; border: 1px solid #e0e0e0; }
    .chart-caption { font-size: 12px; color: #666; margin-top: 5px; }
    @media print { .page { padding: 40px 50px; width: 210mm; } .cover-page { padding: 40px 50px; width: 210mm; } }
  </style>
</head>
<body>
<div class="page cover-page">
  <div class="cover-logo"><img src="${logoUrl}" alt="Dura Capital Logo" /></div>
  <div class="cover-content">
    <div class="cover-session-name">${session}</div>
    <h1 class="cover-title">Valuation Assessment Report</h1>
    <p class="cover-subtitle">${instrument.charAt(0).toUpperCase() + instrument.slice(1)}</p>
  </div>
</div>
<div class="page toc-page">
  <h1>Table of Contents</h1>
  <div class="toc-item"><span>Introduction</span><span>1</span></div>
  <div class="toc-item"><span>Executive Summary</span><span>2</span></div>
  <div class="toc-item"><span>Methodology</span><span>3</span></div>
  <div class="toc-item"><span>Market Inputs</span><span>4</span></div>
  <div class="toc-item"><span>Results</span><span>5</span></div>
  <div class="toc-item"><span>Yield Curve</span><span>6</span></div>
  <div class="toc-item"><span>Conclusion</span><span>7</span></div>
  <div class="toc-item"><span>Appendix</span><span>8</span></div>
  <div class="toc-item"><span>Reference</span><span>9</span></div>
</div>
<div class="page"><h1 class="section-title">Introduction</h1><p>Dura Capital (Private) Limited was contracted to provide a fair valuation assessment report of the following ${instrument} instruments as at ${valDate}.</p><ul style="margin:20px 0 20px 30px;"><li>${instrument} instruments</li><li>Valuation as at ${valDate}</li><li>${data.length} individual instruments assessed</li></ul></div>
<div class="page"><h1 class="section-title">Executive Summary</h1><div class="executive-summary"><p><strong>Key Findings:</strong></p><ul style="margin-left:20px;"><li>Total Portfolio Value: <span class="highlight">$${totalValue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span></li><li>Number of Instruments: <span class="highlight">${data.length}</span></li><li>Average Rate: <span class="highlight">${avgRate.toFixed(2)}%</span></li><li>Valuation Date: <span class="highlight">${valDate}</span></li></ul><p><strong>Valuation Approach:</strong> ${methodology}</p></div></div>
<div class="page"><h1 class="section-title">Methodology</h1><div class="methodology-box"><p>${methodology}</p><div class="formula">${formulas}</div><p><strong>Assumptions:</strong> ${assumptions}</p></div></div>
<div class="page"><h1 class="section-title">Market Inputs</h1><p>Rates sourced from FRED for ${valDate}. Filters used: Country = ${fredFilters.country}, Currency = ${fredFilters.currency}, Maturity = ${fredFilters.maturity}.</p></div>
<div class="page"><h1 class="section-title">Results</h1><table><thead><tr><th>Metric</th><th>Value</th></tr></thead><tbody><tr><td>Total Portfolio Value</td><td>$${totalValue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td></tr><tr><td>Number of Instruments</td><td>${data.length}</td></tr><tr><td>Average Rate</td><td>${avgRate.toFixed(2)}%</td></tr><tr><td>Total Interest Earned</td><td>$${totalInterest.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td></tr><tr><td>Valuation Date</td><td>${valDate}</td></tr></tbody></table></div>
<div class="page"><h1 class="section-title">Yield Curve</h1><p>The following yield curve was used as a benchmark for valuation, sourced from FRED.</p>${chartHtml}</div>
<div class="page"><h1 class="section-title">Conclusion</h1><p>The valuation assessment is in accordance with IFRS 13 fair value measurement principles as at ${valDate}.</p></div>
<div class="page"><h1 class="section-title">Appendix: Detailed Instrument Data</h1><table class="appendix-table"><thead><tr><th>Instrument Name</th><th>BB Ticker</th><th>Face Value ($)</th><th>Rate (%)</th><th>Term (Yrs)</th><th>Valuation Date</th></tr></thead><tbody>${instrumentRows}</tbody></table>
${appendixRows ? `
<br>
<h2 style="font-size:18px; color:#0B2044; margin-top:20px;">FRED Yield Curve Data</h2>
<p><strong>Country:</strong> ${fredFilters.country} &nbsp;|&nbsp; <strong>Currency:</strong> ${fredFilters.currency} &nbsp;|&nbsp; <strong>Maturity:</strong> ${fredFilters.maturity}</p>
<table class="appendix-table">
  <thead><tr><th>Maturity Label</th><th>Term (Yr)</th><th>Rate (%)</th></tr></thead>
  <tbody>${appendixRows}</tbody>
</table>
` : ''}
</div>
<div class="page"><h1 class="section-title">Reference</h1><ul class="reference-list"><li>FRED – Federal Reserve Economic Data</li><li>IFRS 13: Fair Value Measurement</li><li>IFRS 9: Financial Instruments</li></ul><div class="footer"><p>© ${new Date().getFullYear()} Dura Capital (Private) Limited. Report generated ${date || valDate}.</p></div></div>
</body></html>`
}
