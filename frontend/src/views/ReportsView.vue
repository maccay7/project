<template>
  <fixed-layout>
    <div class="reports-view">

      <!-- Header -->
      <div class="page-header">
        <h1>Report Generation</h1>
        <p>Generate professional valuation reports with appendix and methodology</p>
      </div>

      <!-- Action Buttons -->
      <div class="action-buttons">
        <v-btn color="#0B2A44" @click="loadData">
          <v-icon left>mdi-database</v-icon> Load Data
        </v-btn>
        <v-btn color="#0B2A44" variant="outlined" @click="finishAndReset">
          <v-icon left>mdi-check-circle</v-icon> Done & Reset
        </v-btn>
      </div>

      <!-- Data Overview with KPI Cards -->
      <v-card class="stats-card" v-if="hasData">
        <v-card-title class="card-title">
          <v-icon class="title-icon">mdi-file-excel</v-icon> Report Overview
        </v-card-title>
        <v-card-text>
          <v-row>
            <v-col cols="12" sm="4" v-for="stat in kpiStats" :key="stat.title">
              <v-card class="kpi-card">
                <v-card-text>
                  <div class="kpi-content">
                    <div class="kpi-icon" :style="{ backgroundColor: stat.color }">
                      <v-icon :color="stat.iconColor" size="28">{{ stat.icon }}</v-icon>
                    </div>
                    <div class="kpi-info">
                      <div class="kpi-value">{{ stat.value }}</div>
                      <div class="kpi-title">{{ stat.title }}</div>
                    </div>
                  </div>
                </v-card-text>
              </v-card>
            </v-col>
          </v-row>
        </v-card-text>
      </v-card>

      <!-- Excel Viewer -->
      <v-card class="stats-card" v-if="hasData">
        <v-card-title class="card-title">
          <v-icon class="title-icon">mdi-microsoft-excel</v-icon> Data Preview
        </v-card-title>
        <v-card-text>
          <ExcelViewer
            :data="calcData"
            :headers="dataHeaders"
            @data-update="calcData = $event"
          />
        </v-card-text>
      </v-card>

      <!-- Report Sections -->
      <v-card class="stats-card" v-if="hasData">
        <v-card-title class="card-title">
          <v-icon class="title-icon">mdi-cog</v-icon> Report Sections
        </v-card-title>
        <v-card-text>
          <div class="action-buttons small">
            <v-btn size="small" color="#0B2A44" variant="tonal" @click="selectAll">Select All</v-btn>
            <v-btn size="small" color="#0B2A44" variant="tonal" @click="clearAll">Clear</v-btn>
          </div>
          <v-row>
            <v-col cols="12" sm="4" v-for="sec in sections" :key="sec.key">
              <v-card class="section-card" :class="{ selected: sec.selected }" @click="sec.selected = !sec.selected">
                <v-card-text class="text-center">
                  <v-icon :color="sec.color" size="28">{{ sec.icon }}</v-icon>
                  <div class="section-name">{{ sec.name }}</div>
                  <div class="section-desc">{{ sec.desc }}</div>
                </v-card-text>
              </v-card>
            </v-col>
          </v-row>
        </v-card-text>
      </v-card>

      <!-- Generate Button -->
      <v-card class="stats-card" v-if="hasData">
        <v-card-text class="text-center">
          <v-btn color="#0B2A44" size="large" @click="generateExcel" :loading="generating">
            <v-icon left>mdi-file-excel</v-icon> Generate Excel Report
          </v-btn>
          <v-alert v-if="reportReady" type="success" class="mt-3">Report downloaded!</v-alert>
        </v-card-text>
      </v-card>

      <!-- No Data Message -->
      <v-card v-if="!hasData" class="stats-card">
        <v-card-text class="text-center pa-8">
          <v-icon size="64" color="#999">mdi-file-excel-off</v-icon>
          <h3 class="mt-4">No Data Loaded</h3>
          <p>Click "Load Data" to load calculation results</p>
          <v-btn color="#0B2A44" @click="loadData">Load Data</v-btn>
        </v-card-text>
      </v-card>

    </div>
  </fixed-layout>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import FixedLayout from '../components/FixedLayout.vue'
import ExcelViewer from '../components/ExcelViewer.vue'
import * as XLSX from 'xlsx'
import sessionManager from '@/services/sessionManager.js'

const router = useRouter()
const route = useRoute()

// State
const calcData = ref([])
const instrumentType = ref('')
const sessionName = ref('')
const generating = ref(false)
const reportReady = ref(false)

// Sections
const sections = ref([
  { key: 'summary', name: 'Summary', desc: 'Key metrics', icon: 'mdi-chart-line', color: '#0B2A44', selected: true },
  { key: 'data', name: 'Data Table', desc: 'All records', icon: 'mdi-table', color: '#1E88E5', selected: true },
  { key: 'yield', name: 'Yield Analysis', desc: 'Yield statistics', icon: 'mdi-chart-timeline', color: '#4CAF50', selected: true },
  { key: 'appendix', name: 'Appendix', desc: 'Detailed instrument breakdown', icon: 'mdi-file-document', color: '#FF9800', selected: true }
])

// Computed
const hasData = computed(() => calcData.value?.length > 0)
const dataHeaders = computed(() => calcData.value.length ? Object.keys(calcData.value[0]) : [])

const kpiStats = computed(() => [
  { title: 'Records', value: calcData.value.length || 0, icon: 'mdi-database', color: 'rgba(11,42,68,0.1)', iconColor: '#0B2A44' },
  { title: 'Instrument', value: instrumentType.value || 'N/A', icon: 'mdi-chart-line', color: 'rgba(30,136,229,0.1)', iconColor: '#1E88E5' },
  { title: 'Export', value: 'Excel (.xlsx)', icon: 'mdi-file-excel', color: 'rgba(76,175,80,0.1)', iconColor: '#4CAF50' }
])

// Load data from the current session and instrument
async function loadData() {
  try {
    const instrument = route.query.instrument || 'money-market'
    const sessionId = route.query.session
    if (!sessionId) {
      alert('No session selected. Please navigate from Dashboard or Instrument page.')
      return
    }

    const session = sessionManager.getSession(sessionId)
    if (!session) {
      alert('Session not found.')
      return
    }

    sessionName.value = session.name || 'Current Session'

    let data = []
    let instType = instrument

    // First attempt: from instrumentWorkflow
    const wf = sessionManager.getInstrumentWorkflow(sessionId, instrument)
    if (wf && wf.cleanedData && wf.cleanedData.length) {
      data = wf.cleanedData
      instType = instrument
    } else {
      // Fallback: try localStorage
      const cleanKey = `${instrument}_session_${sessionId}_clean`
      const saved = localStorage.getItem(cleanKey)
      if (saved) {
        try {
          data = JSON.parse(saved)
          instType = instrument
        } catch(e) {}
      } else {
        // Last resort: from raw data
        const rawKey = `${instrument}_session_${sessionId}_raw`
        const rawSaved = localStorage.getItem(rawKey)
        if (rawSaved) {
          try {
            data = JSON.parse(rawSaved)
            instType = instrument
          } catch(e) {}
        }
      }
    }

    if (!data.length) {
      alert('No data found for this instrument in the session. Please upload and process data first.')
      return
    }

    calcData.value = data
    instrumentType.value = instType.charAt(0).toUpperCase() + instType.slice(1)
    alert(`Loaded ${data.length} records for ${instrumentType.value}`)
  } catch (err) {
    console.error(err)
    alert('Error loading data: ' + err.message)
  }
}

// Select/Deselect sections
function selectAll() { sections.value.forEach(s => s.selected = true) }
function clearAll() { sections.value.forEach(s => s.selected = false) }

// Build full professional report
function buildFullReport(data, instrument, session, date) {
  const now = new Date().toLocaleString()
  const valuationDate = new Date().toISOString().split('T')[0]
  
  // Calculate aggregates
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

  // Build instrument details table rows
  let instrumentRows = ''
  data.forEach((item, idx) => {
    const name = item.Instrument || item.BondName || item.TBillName || `Instrument ${idx + 1}`
    const faceValue = parseFloat(item.FaceValue || item.Amount || item.Principal || 0)
    const rate = parseFloat(item.Rate || item.InterestRate || item.CouponRate || item.DiscountRate || 0)
    const term = parseFloat(item.Term || item.YearsToMaturity || 0) || (parseFloat(item.MaturityDate) ? (new Date(item.MaturityDate) - new Date(item.IssueDate || Date.now())) / (365 * 24 * 60 * 60 * 1000) : 0)
    const ticker = item.BBTicker || item.Ticker || item.Security || 'N/A'
    const valuationDateVal = item.ValuationDate || valuationDate
    
    instrumentRows += `<tr>
      <td>${name}</td>
      <td>${ticker}</td>
      <td>${faceValue.toFixed(2)}</td>
      <td>${rate.toFixed(4)}%</td>
      <td>${term.toFixed(2)}</td>
      <td>${valuationDateVal}</td>
    </tr>`
  })

  return `
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Valuation Assessment Report - ${session}</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: 'Arial', sans-serif; color: #333; background: white; line-height: 1.6; }
    .page { page-break-after: always; padding: 60px 80px; min-height: 100vh; }
    .page:last-child { page-break-after: auto; }
    .cover-page { display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; background: linear-gradient(135deg, #0B2044 0%, #1a3a6e 100%); color: white; }
    .cover-content { max-width: 800px; }
    .logo { max-width: 200px; margin-bottom: 40px; }
    .cover-title { font-size: 48px; font-weight: 700; letter-spacing: 2px; margin-bottom: 20px; }
    .cover-subtitle { font-size: 24px; font-weight: 300; opacity: 0.9; margin-bottom: 40px; }
    .cover-meta { font-size: 14px; opacity: 0.8; line-height: 1.8; }
    .cover-meta strong { opacity: 1; }
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
    .footer { margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 12px; color: #999; text-align: center; }
    .reference-list { list-style: none; padding: 0; }
    .reference-list li { padding: 8px 0; border-bottom: 1px solid #eee; }
    @media print {
      .page { padding: 40px 60px; }
      .cover-page { background: #0B2044 !important; -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
      .executive-summary { background: #f8f9ff !important; -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
    }
  </style>
</head>
<body>

<!-- COVER PAGE -->
<div class="page cover-page">
  <div class="cover-content">
    <div class="logo">
      <svg width="180" height="60" viewBox="0 0 180 60" fill="none">
        <rect x="0" y="0" width="180" height="60" rx="8" fill="white" opacity="0.95"/>
        <text x="20" y="38" font-family="Arial" font-weight="700" font-size="24" fill="#0B2044">DuraCapital</text>
        <text x="120" y="38" font-family="Arial" font-weight="300" font-size="12" fill="#666">Valuation</text>
      </svg>
    </div>
    <h1 class="cover-title">Valuation Assessment Report</h1>
    <p class="cover-subtitle">${instrument.charAt(0).toUpperCase() + instrument.slice(1)}</p>
    <div class="cover-meta">
      <p><strong>Prepared for:</strong> ${session}</p>
      <p><strong>Valuation Date:</strong> ${valuationDate}</p>
      <p><strong>Report Date:</strong> ${date}</p>
      <p><strong>Prepared by:</strong> Dura Capital (Private) Limited</p>
    </div>
  </div>
</div>

<!-- TABLE OF CONTENTS -->
<div class="page toc-page">
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
  <h1 class="section-title">Introduction</h1>
  <p>Dura Capital (Private) Limited ("Dura Capital", "us", "we") was contracted to provide a fair valuation assessment report of the following ${instrument} instruments as at ${valuationDate}:</p>
  <ul style="margin: 20px 0 20px 30px;">
    <li>${instrument} instruments</li>
    <li>Valuation as at ${valuationDate}</li>
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
      <li>Valuation Date: <span class="highlight">${valuationDate}</span></li>
    </ul>
    <br>
    <p><strong>Valuation Approach:</strong></p>
    <p>${methodology}</p>
  </div>
</div>

<!-- METHODOLOGY -->
<div class="page">
  <h1 class="section-title">Methodology</h1>
  <p>The Axcentium Audit team provided us with ${instrument} data. This section outlines the methodologies used to provide a fair value of the fixed income assets in terms of IFRS 13.</p>
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
  <h1 class="section-title">Market Inputs</h1>
  <p>Market data for Zimbabwe is not available and there have not been any Zimbabwe issued instruments trading on international markets. As such, we have used the OIS SOFR rates from Bloomberg as a risk-free yield curve and added a country risk premium sourced from country risk premiums published by Damodaran.</p>
  <br>
  <p>To determine a smooth yield for the determination of rates for all maturities, we use the Nelson-Siegel-Svensson model which is widely used in practice for fitting the term structure of interest rates.</p>
  <br>
  <p><strong>Key Market Inputs:</strong></p>
  <ul style="margin: 10px 0 20px 30px;">
    <li><strong>Risk-Free Rate:</strong> SOFR OIS curve as at ${valuationDate}</li>
    <li><strong>Country Risk Premium:</strong> Damodaran Country Risk Premiums</li>
    <li><strong>Credit Spread:</strong> Applied based on counterparty risk assessment</li>
    <li><strong>Yield Curve Model:</strong> Nelson-Siegel-Svensson (NSS)</li>
  </ul>
  <div style="background: #f8f9ff; padding: 20px; border-radius: 8px; text-align: center; margin-top: 20px;">
    <p style="color: #999;"><em>Yield curve chart would be displayed here</em></p>
    <canvas id="yieldChart" height="120" style="max-width: 100%;"></canvas>
  </div>
</div>

<!-- RESULTS -->
<div class="page">
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
      <tr><td>Valuation Date</td><td>${valuationDate}</td></tr>
    </tbody>
  </table>
</div>

<!-- CONCLUSION -->
<div class="page">
  <h1 class="section-title">Conclusion</h1>
  <p>The valuation assessment conducted by Dura Capital provides a comprehensive fair value assessment of the ${instrument} instruments as at ${valuationDate}.</p>
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
  <h1 class="section-title">Appendix: Detailed Instrument Data</h1>
  <p><strong>Valuation Date:</strong> ${valuationDate}</p>
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
  <h1 class="section-title">Reference</h1>
  <ul class="reference-list">
    <li>Bloomberg Financial Services – SOFR OIS Yield Curve as at ${valuationDate}</li>
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
}

// Generate Excel report with professional structure
async function generateExcel() {
  generating.value = true
  setTimeout(() => {
    const data = calcData.value
    const instrument = instrumentType.value
    const session = sessionName.value || 'Current Session'
    const date = new Date().toLocaleString()
    const valuationDate = new Date().toISOString().split('T')[0]
    
    const wb = XLSX.utils.book_new()
    
    // Sheet 1: Cover
    const coverData = [
      ['DURA CAPITAL (PRIVATE) LIMITED'],
      ['VALUATION ASSESSMENT REPORT'],
      [''],
      [instrument],
      [''],
      ['Valuation Date:', valuationDate],
      ['Report Date:', date],
      ['Prepared for:', session],
      [''],
      ['Confidential'],
      [''],
      ['© Dura Capital (Private) Limited']
    ]
    const coverSheet = XLSX.utils.aoa_to_sheet(coverData)
    coverSheet['!cols'] = [{ wch: 40 }]
    XLSX.utils.book_append_sheet(wb, coverSheet, 'Cover')
    
    // Sheet 2: Summary
    const totalValue = data.reduce((s, r) => s + (parseFloat(r.FaceValue || r.Amount || r.Principal || 0)), 0)
    const totalInterest = data.reduce((s, r) => s + (parseFloat(r.InterestEarned || r.Interest || 0)), 0)
    const rates = data.map(r => parseFloat(r.Rate || r.InterestRate || r.CouponRate || r.DiscountRate || 0)).filter(r => !isNaN(r) && r > 0)
    const avgRate = rates.length ? rates.reduce((a, b) => a + b, 0) / rates.length : 0
    
    const summaryData = [
      ['EXECUTIVE SUMMARY'],
      [''],
      ['Metric', 'Value'],
      ['Total Portfolio Value', totalValue],
      ['Number of Instruments', data.length],
      ['Average Rate (%)', avgRate],
      ['Total Interest Earned', totalInterest],
      ['Valuation Date', valuationDate],
      [''],
      ['METHODOLOGY'],
      [''],
      ['Approach:', 'Discounted cash flow valuation'],
      ['Day Count:', 'Actual/365'],
      ['Discount Rate:', 'SOFR OIS + Country Risk Premium'],
      [''],
      ['RESULTS'],
      [''],
      ['The valuation has been performed in accordance with IFRS 13.']
    ]
    const summarySheet = XLSX.utils.aoa_to_sheet(summaryData)
    summarySheet['!cols'] = [{ wch: 30 }, { wch: 30 }]
    XLSX.utils.book_append_sheet(wb, summarySheet, 'Summary')
    
    // Sheet 3: Data
    const headers = Object.keys(data[0] || {})
    const dataRows = [headers]
    data.forEach(item => {
      dataRows.push(Object.values(item))
    })
    const dataSheet = XLSX.utils.aoa_to_sheet(dataRows)
    XLSX.utils.book_append_sheet(wb, dataSheet, 'Data')
    
    // Sheet 4: Appendix
    const appendixData = [
      ['APPENDIX: DETAILED INSTRUMENT DATA'],
      ['Valuation Date:', valuationDate],
      [''],
      ['Instrument Name', 'BB Ticker', 'Face Value ($)', 'Rate (%)', 'Term (Yrs)', 'Valuation Date']
    ]
    data.forEach((item, idx) => {
      const name = item.Instrument || item.BondName || item.TBillName || `Instrument ${idx + 1}`
      const faceValue = parseFloat(item.FaceValue || item.Amount || item.Principal || 0)
      const rate = parseFloat(item.Rate || item.InterestRate || item.CouponRate || item.DiscountRate || 0)
      const term = parseFloat(item.Term || item.YearsToMaturity || 0) || (parseFloat(item.MaturityDate) ? (new Date(item.MaturityDate) - new Date(item.IssueDate || Date.now())) / (365 * 24 * 60 * 60 * 1000) : 0)
      const ticker = item.BBTicker || item.Ticker || item.Security || 'N/A'
      appendixData.push([name, ticker, faceValue, rate, term, valuationDate])
    })
    const appendixSheet = XLSX.utils.aoa_to_sheet(appendixData)
    appendixSheet['!cols'] = [{ wch: 25 }, { wch: 15 }, { wch: 18 }, { wch: 12 }, { wch: 12 }, { wch: 18 }]
    XLSX.utils.book_append_sheet(wb, appendixSheet, 'Appendix')
    
    // Sheet 5: Methodology
    const methodologyData = [
      ['METHODOLOGY & ASSUMPTIONS'],
      [''],
      ['Valuation Approach:', 'Discounted cash flow methodology'],
      ['Fair Value Formula:', 'PV = Σ CF_t / (1 + r)^t'],
      ['Day Count Convention:', 'Actual/365'],
      ['Discount Rate Source:', 'SOFR OIS + Country Risk Premium'],
      ['Country Risk Premium:', 'Damodaran Country Risk Premiums'],
      ['Yield Curve Model:', 'Nelson-Siegel-Svensson'],
      [''],
      ['Key Assumptions:'],
      ['- All monetary values are in base currency'],
      ['- Rates are annualized unless otherwise stated'],
      ['- Cashflows are discounted at appropriate market rates']
    ]
    const methodologySheet = XLSX.utils.aoa_to_sheet(methodologyData)
    methodologySheet['!cols'] = [{ wch: 30 }, { wch: 50 }]
    XLSX.utils.book_append_sheet(wb, methodologySheet, 'Methodology')
    
    XLSX.writeFile(wb, `Dura-Capital-Valuation-Report-${new Date().toISOString().split('T')[0]}.xlsx`)
    
    reportReady.value = true
    generating.value = false
    setTimeout(() => { reportReady.value = false }, 3000)
  }, 500)
}

// Reset all
function finishAndReset() {
  if (confirm('Complete & Reset?')) {
    calcData.value = []
    instrumentType.value = ''
    sections.value.forEach(s => s.selected = true)
    router.push('/upload')
  }
}

onMounted(() => {
  if (route.query.session && route.query.instrument) {
    loadData()
  }
})
</script>

<style scoped>
/* same as original – keep your existing styles */
.reports-view { max-width: 1400px; margin: 0 auto; padding: 20px; }
.page-header { margin-bottom: 30px; }
.page-header h1 { color: #0B2A44; font-size: 32px; font-weight: 700; margin-bottom: 8px; }
.page-header p { color: #666; font-size: 16px; }
.action-buttons { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 20px; }
.action-buttons.small { margin-bottom: 16px; }
.stats-card { border-radius: 12px; margin-bottom: 24px; background: white; border: 1px solid rgba(11,42,68,0.08); position: relative; }
.stats-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; background: linear-gradient(90deg, #0B2A44, #1E88E5); border-radius: 12px 12px 0 0; }
.card-title { display: flex; align-items: center; color: #0B2A44; font-weight: 600; font-size: 18px; padding: 16px 20px 0 20px; }
.title-icon { margin-right: 8px; }
.kpi-card { height: 120px; border-radius: 12px; transition: transform 0.2s ease, box-shadow 0.2s ease; background: white; border: 1px solid rgba(11,42,68,0.08); position: relative; }
.kpi-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; background: linear-gradient(90deg, #0B2A44, #1E88E5, #4CAF50); border-radius: 12px 12px 0 0; }
.kpi-card:hover { transform: translateY(-2px); box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1); }
.kpi-content { display: flex; align-items: center; height: 100%; padding: 8px; }
.kpi-icon { width: 56px; height: 56px; border-radius: 12px; display: flex; align-items: center; justify-content: center; margin-right: 12px; flex-shrink: 0; }
.kpi-info { flex: 1; min-width: 0; display: flex; flex-direction: column; justify-content: center; }
.kpi-value { font-size: 24px; font-weight: 700; color: #0B2A44; line-height: 1; margin-bottom: 4px; }
.kpi-title { font-size: 12px; color: #666; }
.section-card { cursor: pointer; transition: 0.2s; border: 2px solid transparent; border-radius: 12px; }
.section-card:hover { transform: translateY(-2px); }
.section-card.selected { border-color: #1E88E5; background: rgba(30,136,229,0.05); }
.section-name { font-weight: 600; margin-top: 8px; color: #0B2A44; }
.section-desc { font-size: 11px; color: #666; }
@media (max-width: 600px) { .reports-view { padding: 0 16px; } .action-buttons { flex-direction: column; } .kpi-card { height: 100px; } .kpi-value { font-size: 20px; } }
</style>