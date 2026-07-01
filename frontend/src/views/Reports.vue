<template>
  <FixedLayout>
    <div class="reports-page">
      <div class="page-header">
        <button class="back-btn" @click="goBack">
          <v-icon>mdi-arrow-left</v-icon> Back
        </button>
        <h1>Generate Report</h1>
        <p>Select report type and generate detailed analysis with appendix</p>
      </div>

      <div class="report-actions-row">
        <v-btn color="#0B2A44" @click="loadDatasetPreview">
          <v-icon left>mdi-eye</v-icon> Preview Dataset
        </v-btn>
        <v-btn color="#1E88E5" @click="generatePreview">
          <v-icon left>mdi-file-document-outline</v-icon> Refresh Report
        </v-btn>
        <v-btn color="#0B2A44" @click="markDone">
          <v-icon left>mdi-check-circle</v-icon> Done
        </v-btn>
        <v-btn color="#4CAF50" @click="downloadFullReport">
          <v-icon left>mdi-download</v-icon> Download Full Report (HTML)
        </v-btn>
      </div>

      <div class="report-options">
        <div class="option-card" @click="selectReportType('current')">
          <div class="option-icon" :class="{ active: selectedType === 'current' }">
            <v-icon size="32">mdi-chart-line</v-icon>
          </div>
          <h3>Current Instrument</h3>
          <p>Generate report for the currently selected instrument</p>
        </div>

        <div class="option-card" @click="selectReportType('session')">
          <div class="option-icon" :class="{ active: selectedType === 'session' }">
            <v-icon size="32">mdi-folder</v-icon>
          </div>
          <h3>Full Session</h3>
          <p>Generate report for all instruments in the session</p>
        </div>
      </div>

      <div class="dataset-preview" v-if="showDatasetPreview">
        <h3>Excel Dataset Preview</h3>
        <div class="dataset-info-row">
          <span><strong>Dataset:</strong> {{ dataset?.name || 'Not loaded' }}</span>
          <span><strong>Instrument:</strong> {{ dataset?.instrument_type || 'Unknown' }}</span>
        </div>
        <div class="preview-content" v-if="dataset && dataset.data && dataset.data.length">
          <ExcelViewer
            :data="dataset.data"
            :headers="Object.keys(dataset.data[0] || {})"
            @data-update="handleDatasetUpdate"
          />
        </div>
        <div v-else class="preview-empty">
          <p>No dataset loaded yet. Use Preview Dataset to load the latest upload.</p>
        </div>
      </div>

      <div class="preview-section" v-if="previewData">
        <h3>Report Preview</h3>
        <v-alert v-if="reportError" type="warning" density="compact" class="mb-3">{{ reportError }}</v-alert>
        <div class="preview-content">
          <pre>{{ JSON.stringify(previewData, null, 2) }}</pre>
        </div>
        <div class="download-row">
          <button class="btn-primary" @click="downloadFullReport">
            <v-icon>mdi-download</v-icon> Download Full Report (HTML)
          </button>
          <button class="btn-secondary" @click="downloadReport('json')">
            <v-icon>mdi-code-json</v-icon> Download JSON
          </button>
        </div>
      </div>
    </div>
  </FixedLayout>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import FixedLayout from '@/components/FixedLayout.vue'
import ExcelViewer from '@/components/ExcelViewer.vue'
import { datasetAPI, fredAPI } from '@/services/api'
import sessionManager from '@/services/sessionManager.js'
import { markStepCompleted } from '@/utils/workflowProgress.js'
import * as XLSX from 'xlsx'

// ----- Image paths -----
const logoUrl = '/DuraCapital logo.png'
const backgroundCoverUrl = '/reportbackground.png'

const router = useRouter()
const route = useRoute()

// ----- State -----
const selectedType = ref('current')
const previewData = ref(null)
const yieldCurveData = ref(null)
const reportError = ref('')
const dataset = ref(null)
const showDatasetPreview = ref(false)
const sessionName = ref('')

// ============================================================
// FULL generateReportHtml – copied from MoneyMarket.vue
// ============================================================
function generateReportHtml(data, instrument, session, date, valuationDate) {
  const now = new Date().toLocaleString()
  const valDate = valuationDate || new Date().toISOString().split('T')[0]
  
  const totalValue = data.reduce((s, r) => s + (parseFloat(r.FaceValue || r.Amount || r.Principal || 0)), 0)
  const totalInterest = data.reduce((s, r) => s + (parseFloat(r.InterestEarned || r.Interest || 0)), 0)
  const rates = data.map(r => parseFloat(r.Rate || r.InterestRate || r.CouponRate || r.DiscountRate || 0)).filter(r => !isNaN(r) && r > 0)
  const avgRate = rates.length ? rates.reduce((a, b) => a + b, 0) / rates.length : 0
  
  const instType = instrument.toLowerCase()
  let methodology = ''
  let formulas = ''
  let assumptions = ''
  
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

  // Build instrument rows for appendix
  let instrumentRows = ''
  data.forEach((item, idx) => {
    const name = item.Instrument || item.BondName || item.TBillName || `Instrument ${idx + 1}`
    const faceValue = parseFloat(item.FaceValue || item.Amount || item.Principal || 0)
    const rate = parseFloat(item.Rate || item.InterestRate || item.CouponRate || item.DiscountRate || 0)
    const term = parseFloat(item.Term || item.YearsToMaturity || 0) || (parseFloat(item.MaturityDate) ? (new Date(item.MaturityDate) - new Date(item.IssueDate || Date.now())) / (365 * 24 * 60 * 60 * 1000) : 0)
    const ticker = item.BBTicker || item.Ticker || item.Security || 'N/A'
    instrumentRows += `<tr>
      <td>${name}</td>
      <td>${ticker}</td>
      <td>${faceValue.toFixed(2)}</td>
      <td>${rate.toFixed(4)}%</td>
      <td>${term.toFixed(2)}</td>
      <td>${valDate}</td>
    </tr>`
  })

  // Watermark logo for pages after cover
  const watermarkLogo = `<img src="${logoUrl}" alt="logo" style="position:absolute; top:20px; right:30px; width:80px; opacity:0.15; pointer-events:none;" />`;

  // ----- NEW COVER DESIGN -----
  const html = `<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Valuation Assessment Report - ${session}</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { 
      font-family: 'Arial', sans-serif; 
      color: #000; 
      background: white; 
      line-height: 1.6; 
      margin: 0;
      padding: 0;
    }
    .page { 
      page-break-after: always; 
      padding: 40px 50px; 
      min-height: 100vh; 
      position: relative;
      width: 210mm;
      margin: 0 auto;
      background: white;
    }
    .page:last-child { page-break-after: auto; }

    /* COVER PAGE – white background, image as watermark on right, text centered */
    .cover-page {
      background-color: white;
      background-image: url('${backgroundCoverUrl}');
      background-size: 30%;           /* smaller, like a watermark */
      background-position: right center;
      background-repeat: no-repeat;
      color: black;
      display: flex;
      flex-direction: column;
      justify-content: center;
      align-items: center;
      text-align: center;
      padding: 40px 50px;
      position: relative;
      min-height: 100vh;
      width: 210mm;
      margin: 0 auto;
    }
    .cover-content {
      max-width: 70%;
      position: relative;
      z-index: 2;
      color: black;
    }
    .cover-logo {
      position: absolute;
      top: 30px;
      left: 40px;
      z-index: 3;
    }
    .cover-logo img {
      max-width: 140px;
      height: auto;
      background: white;
      padding: 4px;
    }
    .cover-session-name {
      font-size: 44px;
      font-weight: 300;
      letter-spacing: 2px;
      margin-bottom: 10px;
      color: #000;
    }
    .cover-title {
      font-size: 48px;
      font-weight: 700;
      letter-spacing: 2px;
      margin-bottom: 20px;
      color: #000;
    }
    .cover-subtitle {
      font-size: 28px;
      font-weight: 300;
      opacity: 0.85;
      margin-bottom: 20px;
      color: #000;
    }

    /* Rest of the pages – A4, black text */
    .toc-page h1 { font-size: 28px; color: #0B2044; border-bottom: 3px solid #0B2044; padding-bottom: 15px; margin-bottom: 30px; }
    .toc-item { display: flex; justify-content: space-between; padding: 12px 0; border-bottom: 1px dotted #ddd; font-size: 16px; }
    .toc-item:hover { background: #f5f5f5; }
    .section-title { font-size: 24px; color: #0B2044; border-bottom: 2px solid #0B2044; padding-bottom: 10px; margin: 30px 0 20px 0; }
    .section-title.centered { text-align: center; border-bottom: none; }
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
    .footer {
      margin-top: 40px;
      padding-top: 20px;
      border-top: 1px solid #ddd;
      font-size: 12px;
      color: #999;
      text-align: center;
    }
    .reference-list { list-style: none; padding: 0; }
    .reference-list li { padding: 8px 0; border-bottom: 1px solid #eee; }
    .watermark { position: absolute; top: 20px; right: 30px; opacity: 0.15; pointer-events: none; }
    .watermark img { width: 80px; }

    /* Page numbers */
    @page {
      margin: 20mm 15mm;
      @bottom-center {
        content: "Page " counter(page) " of " counter(pages);
        font-size: 10pt;
        color: #666;
      }
    }
    @media print {
      .page { padding: 40px 50px; width: 210mm; }
      .cover-page { padding: 40px 50px; width: 210mm; }
      .executive-summary { background: #f8f9ff !important; -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
      .watermark { opacity: 0.15 !important; }
    }
  </style>
</head>
<body>

<!-- COVER PAGE (no watermark) -->
<div class="page cover-page">
  <div class="cover-logo">
    <img src="${logoUrl}" alt="Dura Capital Logo" />
  </div>
  <div class="cover-content">
    <div class="cover-session-name">${session}</div>
    <h1 class="cover-title">Valuation Assessment Report</h1>
    <p class="cover-subtitle">${instrument.charAt(0).toUpperCase() + instrument.slice(1)}</p>
  </div>
</div>

<!-- TABLE OF CONTENTS -->
<div class="page toc-page">
  ${watermarkLogo}
  <h1>Table of Contents</h1>
  <div class="toc-item"><span>Introduction</span><span>1</span></div>
  <div class="toc-item"><span>Executive Summary</span><span>2</span></div>
  <div class="toc-item"><span>Methodology</span><span>3</span></div>
  <div class="toc-item"><span>Market Inputs</span><span>4</span></div>
  <div class="toc-item"><span>Results</span><span>5</span></div>
  <div class="toc-item"><span>Conclusion</span><span>6</span></div>
  <div class="toc-item"><span>Appendix</span><span>7</span></div>
  <div class="toc-item"><span>Reference</span><span>8</span></div>
</div>

<!-- INTRODUCTION -->
<div class="page">
  ${watermarkLogo}
  <h1 class="section-title">Introduction</h1>
  <p>Dura Capital (Private) Limited ("Dura Capital", "us", "we") was contracted to provide a fair valuation assessment report of the following ${instrument} instruments as at ${valDate}:</p>
  <ul style="margin: 20px 0 20px 30px;">
    <li>${instrument} instruments</li>
    <li>Valuation as at ${valDate}</li>
    <li>${data.length} individual instruments assessed</li>
  </ul>
  <p>The instruments are classified and measured at fair value through profit or loss in terms of International Financial Reporting Standard 9: Financial Instruments ("IFRS 9") and International Financial Reporting Standard 13: Fair Value Measurement ("IFRS 13") and this forms as the basis to our assessment.</p>
  <br>
  <p><strong>This report is structured in five parts:</strong></p>
  <ul style="margin: 10px 0 20px 30px;">
    <li><strong>Methodology:</strong> Outlines the methods used to value the financial instruments and the discounting factors.</li>
    <li><strong>Market Inputs:</strong> Assesses the reasonability of market data that is used in the valuation models.</li>
    <li><strong>Results:</strong> Compares the client's valuation to our independent assessment.</li>
    <li><strong>Conclusion:</strong> Gives our independent opinion as well as other considerations.</li>
    <li><strong>Appendix:</strong> Detailed instrument-level data and calculations.</li>
  </ul>
</div>

<!-- EXECUTIVE SUMMARY -->
<div class="page">
  ${watermarkLogo}
  <h1 class="section-title">Executive Summary</h1>
  <div class="executive-summary">
    <p><strong>Valuation Assessment Summary</strong></p>
    <p>This report provides a valuation assessment of ${instrument} instruments in accordance with IFRS 13 fair value measurement principles.</p>
    <br>
    <p><strong>Key Findings:</strong></p>
    <ul style="margin-left: 20px;">
      <li>Total Portfolio Value: <span class="highlight">$${totalValue.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</span></li>
      <li>Number of Instruments: <span class="highlight">${data.length}</span></li>
      <li>Average Rate: <span class="highlight">${avgRate.toFixed(2)}%</span></li>
      <li>Valuation Date: <span class="highlight">${valDate}</span></li>
    </ul>
    <br>
    <p><strong>Valuation Approach:</strong></p>
    <p>${methodology}</p>
  </div>
</div>

<!-- METHODOLOGY -->
<div class="page">
  ${watermarkLogo}
  <h1 class="section-title">Methodology</h1>
  <p>The audit team provided us with ${instrument} data. This section outlines the methodologies used to provide a fair value of the fixed income assets in terms of IFRS 13.</p>
  <br>
  <div class="methodology-box">
    <h3>Valuation Approach</h3>
    <p>${methodology}</p>
    <div class="formula">${formulas}</div>
    <p><strong>Assumptions:</strong> ${assumptions}</p>
  </div>
  <br>
  <p>A projection of the future cashflows expected at each payment date was constructed from information provided by the audit team which include capital amount, trade/effective date, maturity date, fixed interest rate, interest payment frequency and capital repayment frequency.</p>
  <br>
  <p><strong>Day Count Convention:</strong> Actual/365-day count convention as provided by the Audit team.</p>
  <p><strong>Discounting:</strong> The sum of all discounted cashflows for each instrument represents the fair value of the instrument in terms of IFRS 13.</p>
</div>

<!-- MARKET INPUTS -->
<div class="page">
  ${watermarkLogo}
  <h1 class="section-title">Market Inputs</h1>
  <p>Market data for Zimbabwe is not available and there have not been any Zimbabwe issued instruments trading on international markets. As such, we have used the OIS SOFR rates from Bloomberg as a risk-free yield curve and added a country risk premium sourced from country risk premiums published by Damodaran.</p>
  <br>
  <p>To determine a smooth yield for the determination of rates for all maturities, we use the Nelson-Siegel-Svensson model which is widely used in practice for fitting the term structure of interest rates.</p>
  <br>
  <p><strong>Key Market Inputs:</strong></p>
  <ul style="margin: 10px 0 20px 30px;">
    <li><strong>Risk-Free Rate:</strong> SOFR OIS curve as at ${valDate}</li>
    <li><strong>Country Risk Premium:</strong> Damodaran Country Risk Premiums</li>
    <li><strong>Credit Spread:</strong> Applied based on counterparty risk assessment</li>
    <li><strong>Yield Curve Model:</strong> Nelson-Siegel-Svensson (NSS)</li>
  </ul>
  <div style="background: #f8f9ff; padding: 20px; border-radius: 8px; text-align: center; margin-top: 20px;">
    <p style="color: #999;"><em>Yield curve chart would be displayed here</em></p>
  </div>
</div>

<!-- RESULTS -->
<div class="page">
  ${watermarkLogo}
  <h1 class="section-title">Results</h1>
  <p>Below is a summary of the key findings of the valuation for ${instrument} instruments.</p>
  <br>
  <h3>Summary of Valuation Results</h3>
  <table>
    <thead>
      <tr>
        <th>Metric</th>
        <th>Value</th>
      </tr>
    </thead>
    <tbody>
      <tr><td>Total Portfolio Value</td><td>$${totalValue.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td></tr>
      <tr><td>Number of Instruments</td><td>${data.length}</td></tr>
      <tr><td>Average Rate</td><td>${avgRate.toFixed(2)}%</td></tr>
      <tr><td>Total Interest Earned</td><td>$${totalInterest.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td></tr>
      <tr><td>Valuation Date</td><td>${valDate}</td></tr>
    </tbody>
  </table>
</div>

<!-- CONCLUSION -->
<div class="page">
  ${watermarkLogo}
  <h1 class="section-title">Conclusion</h1>
  <p>The valuation assessment conducted by Dura Capital provides a comprehensive fair value assessment of the ${instrument} instruments as at ${valDate}.</p>
  <br>
  <p><strong>Key Observations:</strong></p>
  <ul style="margin: 10px 0 20px 30px;">
    <li>The valuation methodology applied is in accordance with IFRS 13 fair value measurement principles.</li>
    <li>Market inputs used are appropriate for the valuation date.</li>
    <li>All material assumptions have been disclosed and are reasonable.</li>
    <li>The valuation is based on information provided by the client and market data as at the valuation date.</li>
  </ul>
  <br>
  <p><strong>Recommendation:</strong> The valuation is reasonable and can be used for financial reporting purposes in accordance with IFRS 13.</p>
  <br>
  <p style="font-style: italic; color: #666;">This report is confidential and prepared solely for the use of the client.</p>
</div>

<!-- APPENDIX -->
<div class="page">
  ${watermarkLogo}
  <h1 class="section-title">Appendix: Detailed Instrument Data</h1>
  <p><strong>Valuation Date:</strong> ${valDate}</p>
  <p><strong>Total Instruments:</strong> ${data.length}</p>
  <br>
  <table class="appendix-table">
    <thead>
      <tr>
        <th>Instrument Name</th>
        <th>BB Ticker</th>
        <th>Face Value ($)</th>
        <th>Rate (%)</th>
        <th>Term (Yrs)</th>
        <th>Valuation Date</th>
      </tr>
    </thead>
    <tbody>
      ${instrumentRows}
    </tbody>
  </table>
  <p style="font-size: 12px; color: #999; margin-top: 10px;"><em>Note: BB Ticker refers to Bloomberg ticker where available. Term is calculated as years to maturity.</em></p>
</div>

<!-- REFERENCE -->
<div class="page">
  ${watermarkLogo}
  <h1 class="section-title">Reference</h1>
  <ul class="reference-list">
    <li>Bloomberg Financial Services – SOFR OIS Yield Curve as at ${valDate}</li>
    <li>Damodaran Country Risk Premiums – Published country risk premiums</li>
    <li>IFRS 13: Fair Value Measurement – International Financial Reporting Standards</li>
    <li>IFRS 9: Financial Instruments – Classification and measurement</li>
    <li>Nelson-Siegel-Svensson model for yield curve fitting</li>
  </ul>
  <br>
  <div class="footer">
    <p>© ${new Date().getFullYear()} Dura Capital (Private) Limited. All rights reserved.</p>
    <p>This report is confidential and prepared solely for the use of the client.</p>
  </div>
</div>

</body>
</html>`

  return html
}

// ============================================================
// Component logic
// ============================================================

function selectReportType(type) {
  selectedType.value = type
  generatePreview()
}

async function loadFredForReport() {
  reportError.value = ''
  try {
    const res = await fredAPI.getYieldCurve('all')
    if (res?.success && res.data?.datasets?.length) {
      yieldCurveData.value = res.data
    } else {
      reportError.value = 'FRED yield data not available. Check backend .env FRED_API_KEY.'
      yieldCurveData.value = null
    }
  } catch (e) {
    reportError.value = e.message || 'Failed to load FRED data'
    yieldCurveData.value = null
  }
}

async function generatePreview() {
  await loadFredForReport()
  const reportType = selectedType.value

  let session = null
  try {
    const saved = localStorage.getItem('active_session')
    if (saved) {
      const sid = JSON.parse(saved).id
      session = sessionManager.getSession(sid) || JSON.parse(saved)
    } else {
      const all = sessionManager.getAllSessions() || []
      session = all.length ? all[0] : null
    }
  } catch (e) {
    session = null
  }

  if (!session) {
    reportError.value = 'No active session found.'
    previewData.value = null
    return
  }

  sessionName.value = session.name || 'Current Session'
  const instrument = route.query.instrument || 'money-market'

  let data = []
  const wf = sessionManager.getInstrumentWorkflow(session.id, instrument)
  if (wf && wf.cleanedData && wf.cleanedData.length) {
    data = wf.cleanedData
  } else {
    const rawKey = `${instrument}_session_${session.id}_raw`
    const savedRaw = localStorage.getItem(rawKey)
    if (savedRaw) {
      try { data = JSON.parse(savedRaw) } catch(e) {}
    }
  }

  const preview = {
    type: reportType === 'current' ? 'Current Instrument Report' : 'Full Session Report',
    date: new Date().toLocaleString(),
    session: session.name || 'Current Session',
    instrument: instrument,
    rows: data.length,
    columns: data.length ? Object.keys(data[0]).length : 0,
    sample: data.slice(0, 3),
    valuationDate: new Date().toISOString().split('T')[0],
    totalValue: data.reduce((s, r) => s + (parseFloat(r.FaceValue || r.Amount || r.Principal || 0)), 0)
  }

  if (reportType === 'session') {
    const allData = {}
    const instruments = ['money-market', 'bonds', 'tbills']
    for (const inst of instruments) {
      const wf2 = sessionManager.getInstrumentWorkflow(session.id, inst)
      if (wf2 && wf2.cleanedData && wf2.cleanedData.length) {
        allData[inst] = wf2.cleanedData
      } else {
        const rawKey2 = `${inst}_session_${session.id}_raw`
        const savedRaw2 = localStorage.getItem(rawKey2)
        if (savedRaw2) {
          try { allData[inst] = JSON.parse(savedRaw2) } catch(e) {}
        }
      }
    }
    preview.instruments = allData
    preview.totalRows = Object.values(allData).reduce((sum, arr) => sum + arr.length, 0)
    preview.totalValue = Object.values(allData).reduce((sum, arr) => sum + arr.reduce((s, r) => s + (parseFloat(r.FaceValue || r.Amount || r.Principal || 0)), 0), 0)
  }

  previewData.value = preview
  reportError.value = ''
}

function downloadFullReport() {
  if (!previewData.value) {
    alert('No report data. Please refresh the report first.')
    return
  }

  const data = previewData.value
  const instrument = data.instrument || 'unknown'
  const session = data.session || 'Current Session'
  const date = data.date || new Date().toLocaleString()
  const valuationDate = data.valuationDate || new Date().toISOString().split('T')[0]

  let fullData = []
  if (selectedType.value === 'session' && data.instruments) {
    for (const [inst, rows] of Object.entries(data.instruments)) {
      if (rows && rows.length) {
        fullData = fullData.concat(rows)
      }
    }
  } else {
    const sessionId = route.query.session
    if (sessionId) {
      const wf = sessionManager.getInstrumentWorkflow(sessionId, instrument)
      if (wf && wf.cleanedData && wf.cleanedData.length) {
        fullData = wf.cleanedData
      } else {
        const rawKey = `${instrument}_session_${sessionId}_raw`
        const savedRaw = localStorage.getItem(rawKey)
        if (savedRaw) {
          try { fullData = JSON.parse(savedRaw) } catch(e) {}
        }
      }
    }
  }

  if (!fullData.length) {
    alert('No data available for the report.')
    return
  }

  const html = generateReportHtml(fullData, instrument, session, date, valuationDate)
  const blob = new Blob([html], { type: 'text/html' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `Dura-Capital-Valuation-Report-${new Date().toISOString().split('T')[0]}.html`
  a.click()
  URL.revokeObjectURL(url)
}

function downloadReport(format = 'json') {
  if (format === 'json') {
    const blob = new Blob([JSON.stringify({ ...previewData.value, yieldCurve: yieldCurveData.value }, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `report_${Date.now()}.json`
    a.click()
    URL.revokeObjectURL(url)
    return
  }
}

function handleDatasetUpdate(updatedData) {
  if (!dataset.value) return
  dataset.value.data = updatedData
}

async function loadDatasetPreview() {
  showDatasetPreview.value = true
  try {
    let session = null
    try {
      const saved = localStorage.getItem('active_session')
      if (saved) {
        const sid = JSON.parse(saved).id
        session = sessionManager.getSession(sid) || JSON.parse(saved)
      } else {
        const all = sessionManager.getAllSessions() || []
        session = all.length ? all[0] : null
      }
    } catch (e) { session = null }

    if (!session) {
      alert('No active session found.')
      return
    }

    const instrument = route.query.instrument || 'money-market'
    let data = []
    const wf = sessionManager.getInstrumentWorkflow(session.id, instrument)
    if (wf && wf.cleanedData && wf.cleanedData.length) {
      data = wf.cleanedData
    } else {
      const rawKey = `${instrument}_session_${session.id}_raw`
      const savedRaw = localStorage.getItem(rawKey)
      if (savedRaw) {
        try { data = JSON.parse(savedRaw) } catch(e) {}
      }
    }

    if (data.length) {
      dataset.value = {
        name: `${instrument} dataset`,
        instrument_type: instrument,
        data: data
      }
      generatePreview()
    } else {
      alert('No data found for this instrument in the session.')
    }
  } catch (err) {
    console.error('Load dataset preview error', err)
    alert('Error loading dataset: ' + err.message)
  }
}

async function markDone() {
  try {
    const session = sessionManager.getActiveSession()
    if (!session) {
      alert('No active session.')
      return
    }
    const instrument = route.query.instrument || 'money-market'
    if (!session.instrumentData) session.instrumentData = {}
    session.instrumentData[instrument] = {
      ...session.instrumentData[instrument],
      completed: true,
      timestamp: new Date().toISOString()
    }
    await sessionManager.updateSession(session.id, { instrumentData: session.instrumentData })
    try { if (session && session.id) await markStepCompleted(String(session.id), 'reports') } catch (e) { console.error(e) }
    alert(`Marked ${instrument} as done in session.`)
    router.push('/dashboard')
  } catch (err) {
    console.error(err)
    alert('Error marking done: ' + err.message)
  }
}

function goBack() {
  router.back()
}

onMounted(() => {
  if (route.query.session && route.query.instrument) {
    loadDatasetPreview()
  } else {
    generatePreview()
  }
})
</script>

<style scoped>
.reports-page { padding: 30px; max-width: 1200px; margin: 0 auto; }
.page-header { margin-bottom: 30px; }
.back-btn { background: transparent; border: none; color: #0B2044; cursor: pointer; display: flex; align-items: center; gap: 8px; padding: 8px 16px; border-radius: 8px; margin-bottom: 20px; }
.page-header h1 { color: #0B2044; font-size: 28px; font-weight: 700; }
.page-header p { color: #666; font-size: 14px; }
.report-actions-row { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 20px; }
.report-options { display: grid; grid-template-columns: repeat(2, 1fr); gap: 24px; margin-bottom: 40px; }
.option-card { background: white; border-radius: 16px; padding: 30px; text-align: center; cursor: pointer; transition: all 0.3s; border: 2px solid transparent; }
.option-card:hover { transform: translateY(-5px); box-shadow: 0 8px 25px rgba(0,0,0,0.1); border-color: #0B2044; }
.option-icon { width: 80px; height: 80px; background: #f5f5f5; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 20px; transition: all 0.3s; }
.option-icon.active { background: #0B2044; color: white; }
.option-card h3 { color: #0B2044; margin-bottom: 10px; }
.option-card p { color: #666; font-size: 13px; }
.preview-section { background: white; border-radius: 16px; padding: 24px; }
.preview-section h3 { color: #0B2044; margin-bottom: 20px; }
.preview-content { background: #f5f5f5; border-radius: 8px; padding: 20px; overflow-x: auto; margin-bottom: 20px; }
.preview-content pre { margin: 0; font-size: 12px; }
.btn-primary { background: linear-gradient(135deg, #0B2044, #1E88E5); color: white; border: none; padding: 12px 28px; border-radius: 10px; font-size: 14px; font-weight: 600; cursor: pointer; display: inline-flex; align-items: center; gap: 8px; }
.download-row { display: flex; gap: 12px; flex-wrap: wrap; }
.btn-secondary { background: #1E88E5; color: white; border: none; padding: 12px 28px; border-radius: 10px; font-size: 14px; font-weight: 600; cursor: pointer; display: inline-flex; align-items: center; gap: 8px; }
.dataset-preview { background: white; border-radius: 16px; padding: 24px; margin-bottom: 24px; }
.dataset-info-row { display: flex; gap: 24px; margin-bottom: 16px; }
.preview-empty { padding: 40px; text-align: center; color: #999; }
</style>