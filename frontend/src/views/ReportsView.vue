<template>
  <fixed-layout>
    <div class="reports-view">

      <!-- Header Section -->
      <div class="dashboard-header">
        <h1 class="page-title">Report Generation</h1>
        <p class="page-subtitle">Generate comprehensive reports in multiple formats</p>
      </div>

      <!-- DATA OVERVIEW -->
      <v-card class="stats-card" elevation="2">
        <v-card-title class="card-title">
          <v-icon class="title-icon">mdi-file-document</v-icon>
          Report Data Overview
        </v-card-title>

        <v-card-text>
          <v-row class="kpi-row">
            <v-col cols="12" sm="6" md="3" v-for="kpi in reportKpiData" :key="kpi.title">
              <v-card class="kpi-card" elevation="2">
                <v-card-text>
                  <div class="kpi-content">
                    <div class="kpi-icon" :style="{ backgroundColor: kpi.color }">
                      <v-icon :color="kpi.iconColor">{{ kpi.icon }}</v-icon>
                    </div>
                    <div class="kpi-info">
                      <div class="kpi-value">{{ kpi.value }}</div>
                      <div class="kpi-title">{{ kpi.title }}</div>
                      <div v-if="kpi.change" class="kpi-change" :class="kpi.changeClass">
                        <v-icon size="16">{{ kpi.changeIcon }}</v-icon>
                        {{ kpi.change }}
                      </div>
                    </div>
                  </div>
                </v-card-text>
              </v-card>
            </v-col>
          </v-row>
        </v-card-text>
      </v-card>

      <!-- CONFIGURATION -->
      <v-card class="config-card" elevation="2">
        <v-card-title class="card-title">
          <v-icon class="title-icon">mdi-cog</v-icon>
          Report Configuration
        </v-card-title>

        <v-card-text>

          
          <!-- ACTION BUTTONS -->
          <div class="action-buttons">
            <v-btn
              color="primary"
              variant="tonal"
              class="mr-2"
              @click="selectAllSections"
            >
              <v-icon left>mdi-check-all</v-icon>
              Select All
            </v-btn>

            <v-btn
              color="primary"
              variant="tonal"
              class="mr-2"
              @click="clearSections"
            >
              <v-icon left>mdi-close</v-icon>
              Clear
            </v-btn>
          </div>

          <!-- SECTIONS -->
          <div class="sections-section">
            <h3 class="section-title">Include in Report:</h3>

            <v-row>
              <v-col
                v-for="section in reportSections"
                :key="section.key"
                cols="12"
                sm="6"
                md="4"
              >
                <v-card
                  class="section-card"
                  :class="{ selected: section.selected }"
                  @click="section.selected = !section.selected"
                >
                  <v-card-text class="text-center">
                    <v-icon :color="section.color" size="30">
                      {{ section.icon }}
                    </v-icon>

                    <div class="section-name">
                      {{ section.name }}
                    </div>

                    <div class="section-desc">
                      {{ section.description }}
                    </div>
                  </v-card-text>
                </v-card>
              </v-col>
            </v-row>
          </div>

          
        </v-card-text>
      </v-card>

      <!-- FORMAT FILTER -->
      <v-card class="stats-card" elevation="2">
        <v-card-title class="card-title">
          <v-icon class="title-icon">mdi-filter</v-icon>
          Export Format
        </v-card-title>

        <v-card-text>
          <v-row>
            <v-col cols="12" sm="6">
              <v-select
                v-model="selectedFormat"
                :items="formatOptions"
                label="Export Format"
                variant="outlined"
                item-title="label"
                item-value="value"
              >
                <template v-slot:selection="{ item }">
                  <v-icon class="mr-2" :color="item.raw.color">
                    {{ item.raw.icon }}
                  </v-icon>
                  {{ item.raw.label }}
                </template>
              </v-select>
            </v-col>
          </v-row>
        </v-card-text>
      </v-card>

      <!-- ACTION BUTTONS -->
      <v-card class="action-card" elevation="2">
        <v-card-title class="card-title">
          <v-icon class="title-icon">mdi-cog</v-icon>
          Report Actions
        </v-card-title>

        <v-card-text>
          <div class="action-buttons">
            <v-btn
              color="primary"
              size="large"
              class="mr-4"
              @click="generateReport"
              :loading="isGenerating"
              :disabled="!hasData"
            >
              <v-icon left>mdi-file-document-plus</v-icon>
              Generate Report
            </v-btn>

            <v-btn
              color="success"
              size="large"
              class="mr-4"
              @click="downloadReport"
              :disabled="!reportGenerated"
            >
              <v-icon left>mdi-download</v-icon>
              Download Report
            </v-btn>

            <v-btn
              color="info"
              size="large"
              class="mr-4"
              @click="printReport"
              :disabled="!reportGenerated"
            >
              <v-icon left>mdi-printer</v-icon>
              Print Report
            </v-btn>

            <v-btn
              color="grey"
              size="large"
              @click="goBack"
            >
              <v-icon left>mdi-arrow-left</v-icon>
              Back
            </v-btn>
          </div>

          <v-alert
            v-if="!hasData"
            type="warning"
            variant="tonal"
            class="mt-4"
          >
            No data available. Please upload and process data first.
          </v-alert>

          <v-alert
            v-if="reportGenerated"
            type="success"
            variant="tonal"
            class="mt-4"
          >
            Report generated successfully! You can now download or print the report.
          </v-alert>
        </v-card-text>
      </v-card>

      <!-- REPORT PREVIEW -->
      <v-card v-if="reportGenerated" class="preview-card" elevation="2">
        <v-card-title class="card-title">
          <v-icon class="title-icon">mdi-eye</v-icon>
          Generated Report Preview
        </v-card-title>

        <v-card-text>
          <div class="report-content" v-html="generatedReportContent">
          </div>
        </v-card-text>
      </v-card>

      <!-- EXCEL PREVIEW -->
      <v-card v-if="hasData" class="preview-card" elevation="2">
        <v-card-title class="card-title">
          <v-icon class="title-icon">mdi-microsoft-excel</v-icon>
          Data Preview (Excel Format)
        </v-card-title>

        <v-card-text>
          <ExcelViewer
            v-if="visualizationData && visualizationData.calculations && visualizationData.calculations.length > 0"
            :data="visualizationData.calculations"
            :headers="Object.keys(visualizationData.calculations[0] || {})"
            @data-update="handleDataUpdate"
          />
        </v-card-text>
      </v-card>

    </div>
  </fixed-layout>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import FixedLayout from '../components/FixedLayout.vue'
import ExcelViewer from '../components/ExcelViewer.vue'

const router = useRouter()

const visualizationData = ref<any>(null)
const selectedFormat = ref('pdf')
const isGenerating = ref(false)
const reportGenerated = ref(false)
const generatedReportContent = ref('')

const recordsValue = computed(() => visualizationData.value?.calculations?.length || 0)
const instrumentTypeValue = computed(() => visualizationData.value?.instrumentType || 'N/A')
const exportFormatValue = computed(() => selectedFormat.value.toUpperCase())
const sectionsValue = computed(() => getSelectedSections().length)

const hasData = computed(() => visualizationData.value?.calculations && visualizationData.value.calculations.length > 0)

const reportKpiData = ref([
  {
    title: 'Records',
    value: recordsValue,
    icon: 'mdi-database',
    color: 'rgba(11, 42, 68, 0.1)',
    iconColor: '#0B2A44',
    change: '',
    changeIcon: 'mdi-minus',
    changeClass: 'neutral'
  },
  {
    title: 'Instrument Type',
    value: instrumentTypeValue,
    icon: 'mdi-chart-line',
    color: 'rgba(30, 136, 229, 0.1)',
    iconColor: '#1E88E5',
    change: '',
    changeIcon: 'mdi-minus',
    changeClass: 'neutral'
  },
  {
    title: 'Export Format',
    value: exportFormatValue,
    icon: 'mdi-file-export',
    color: 'rgba(76, 175, 80, 0.1)',
    iconColor: '#4CAF50',
    change: '',
    changeIcon: 'mdi-minus',
    changeClass: 'neutral'
  },
  {
    title: 'Sections',
    value: sectionsValue,
    icon: 'mdi-view-list',
    color: 'rgba(255, 193, 7, 0.1)',
    iconColor: '#FFC107',
    change: '',
    changeIcon: 'mdi-minus',
    changeClass: 'neutral'
  }
])

const formatOptions = ref([
  { value: 'pdf', label: 'PDF Document', icon: 'mdi-file-pdf', color: '#0B2A44' },
  { value: 'excel', label: 'Excel Spreadsheet', icon: 'mdi-file-excel', color: '#1E88E5' },
  { value: 'csv', label: 'CSV File', icon: 'mdi-file-delimited', color: '#4CAF50' },
  { value: 'json', label: 'JSON Data', icon: 'mdi-code-json', color: '#FF9800' },
  { value: 'word', label: 'Word Document', icon: 'mdi-file-word', color: '#2196F3' },
  { value: 'powerpoint', label: 'PowerPoint', icon: 'mdi-file-powerpoint', color: '#F44336' },
  { value: 'xml', label: 'XML File', icon: 'mdi-code-tags', color: '#9C27B0' },
  { value: 'html', label: 'HTML Report', icon: 'mdi-language-html5', color: '#E91E63' },
  { value: 'txt', label: 'Text File', icon: 'mdi-file-document', color: '#607D8B' }
])

const reportSections = ref([
  { key: 'summary', name: 'Summary', description: 'Key insights', icon: 'mdi-chart-line', color: '#0B2A44', selected: true },
  { key: 'data', name: 'Data', description: 'Raw results', icon: 'mdi-table', color: '#1E88E5', selected: true },
  { key: 'charts', name: 'Charts', description: 'Visual graphs', icon: 'mdi-chart-pie', color: '#4CAF50', selected: true }
])

onMounted(() => {
  const stored = localStorage.getItem('calculations')
  if (stored) visualizationData.value = JSON.parse(stored)
})

const getSelectedSections = () =>
  reportSections.value.filter(s => s.selected)

const selectAllSections = () => {
  reportSections.value.forEach(s => s.selected = true)
}

const clearSections = () => {
  reportSections.value.forEach(s => s.selected = false)
}

const goBack = () => {
  router.push('/visualizations')
}

const generateReport = () => {
  if (!hasData.value) return
  
  isGenerating.value = true
  
  setTimeout(() => {
    const selectedSections = getSelectedSections()
    const reportContent = generateDuraCapitalReport(selectedSections)
    
    generatedReportContent.value = reportContent
    reportGenerated.value = true
    isGenerating.value = false
  }, 1500)
}

const generateDuraCapitalReport = (selectedSections: any[]) => {
  const calculations = visualizationData.value?.calculations || []
  const instrumentType = visualizationData.value?.instrumentType || 'Money Market'
  const currentDate = new Date().toLocaleDateString()
  
  let reportHTML = `
    <div class="dura-capital-report">
      <header class="report-header">
        <div class="company-info">
          <h1>Dura Capital</h1>
          <h2>Financial Analysis Report</h2>
          <p>Generated: ${currentDate}</p>
        </div>
        <div class="report-details">
          <p><strong>Instrument Type:</strong> ${instrumentType}</p>
          <p><strong>Total Records:</strong> ${calculations.length}</p>
          <p><strong>Report ID:</strong> DC-${Date.now()}</p>
        </div>
      </header>
      
      <div class="report-content">
  `
  
  selectedSections.forEach(section => {
    switch (section.key) {
      case 'summary':
        reportHTML += generateSummarySection(calculations)
        break
      case 'data':
        reportHTML += generateDataSection(calculations)
        break
      case 'charts':
        reportHTML += generateChartsSection(calculations)
        break
    }
  })
  
  reportHTML += `
      </div>
      
      <footer class="report-footer">
        <p>© 2024 Dura Capital - Financial Analysis Report</p>
        <p>This report was generated automatically based on uploaded financial data.</p>
      </footer>
    </div>
  `
  
  return reportHTML
}

const generateSummarySection = (calculations: any[]) => {
  const totalPrincipal = calculations.reduce((sum, calc) => sum + (calc.principal || 0), 0)
  const totalInterest = calculations.reduce((sum, calc) => sum + (calc.interest_earned || 0), 0)
  const avgYield = calculations.reduce((sum, calc) => sum + (calc.yield || 0), 0) / calculations.length
  
  return `
    <section class="report-section">
      <h3>Executive Summary</h3>
      <div class="summary-grid">
        <div class="summary-item">
          <h4>Total Principal</h4>
          <p class="summary-value">$${totalPrincipal.toLocaleString()}</p>
        </div>
        <div class="summary-item">
          <h4>Total Interest Earned</h4>
          <p class="summary-value">$${totalInterest.toLocaleString()}</p>
        </div>
        <div class="summary-item">
          <h4>Average Yield</h4>
          <p class="summary-value">${avgYield.toFixed(2)}%</p>
        </div>
        <div class="summary-item">
          <h4>Number of Instruments</h4>
          <p class="summary-value">${calculations.length}</p>
        </div>
      </div>
    </section>
  `
}

const generateDataSection = (calculations: any[]) => {
  let tableHTML = `
    <section class="report-section">
      <h3>Detailed Financial Data</h3>
      <table class="data-table">
        <thead>
          <tr>
            <th>Instrument Name</th>
            <th>Principal</th>
            <th>Interest Rate</th>
            <th>Term (Days)</th>
            <th>Interest Earned</th>
            <th>Maturity Value</th>
            <th>Yield (%)</th>
          </tr>
        </thead>
        <tbody>
  `
  
  calculations.forEach(calc => {
    tableHTML += `
      <tr>
        <td>${calc.instrument_name || calc.instrument_type || 'N/A'}</td>
        <td>$${(calc.principal || 0).toLocaleString()}</td>
        <td>${((calc.interest_rate || 0) * 100).toFixed(2)}%</td>
        <td>${calc.term_days || 0}</td>
        <td>$${(calc.interest_earned || 0).toLocaleString()}</td>
        <td>$${(calc.maturity_value || calc.principal + (calc.interest_earned || 0)).toLocaleString()}</td>
        <td>${(calc.yield || 0).toFixed(2)}%</td>
      </tr>
    `
  })
  
  tableHTML += `
        </tbody>
      </table>
    </section>
  `
  
  return tableHTML
}

const generateChartsSection = (calculations: any[]) => {
  return `
    <section class="report-section">
      <h3>Visual Analytics</h3>
      <div class="charts-grid">
        <div class="chart-placeholder">
          <h4>Principal Distribution</h4>
          <p>Chart showing principal amounts across instruments</p>
        </div>
        <div class="chart-placeholder">
          <h4>Yield Analysis</h4>
          <p>Chart showing yield rates across instruments</p>
        </div>
        <div class="chart-placeholder">
          <h4>Interest Performance</h4>
          <p>Chart showing interest earned by instrument</p>
        </div>
      </div>
    </section>
  `
}

const downloadReport = () => {
  if (!generatedReportContent.value) return
  
  const format = selectedFormat.value
  const currentDate = new Date().toISOString().split('T')[0]
  
  switch (format) {
    case 'html':
      downloadHTMLReport(currentDate)
      break
    case 'pdf':
      downloadPDFReport(currentDate)
      break
    case 'excel':
      downloadExcelReport(currentDate)
      break
    case 'csv':
      downloadCSVReport(currentDate)
      break
    case 'json':
      downloadJSONReport(currentDate)
      break
    case 'word':
      downloadWordReport(currentDate)
      break
    case 'powerpoint':
      downloadPowerPointReport(currentDate)
      break
    case 'xml':
      downloadXMLReport(currentDate)
      break
    case 'txt':
      downloadTextReport(currentDate)
      break
    default:
      downloadHTMLReport(currentDate)
  }
}

const downloadHTMLReport = (date: string) => {
  const cssStyles = `
    <style>
      /* Reset and base styles */
      * {
        box-sizing: border-box;
      }
      
      body {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif !important;
        color: #333 !important;
        margin: 20px !important;
        padding: 0 !important;
        background: white !important;
        line-height: 1.6 !important;
      }
      
      /* Main report container */
      .dura-capital-report {
        max-width: 1200px !important;
        margin: 0 auto !important;
        padding: 0 !important;
      }
      
      /* Header styles */
      .report-header {
        border-bottom: 3px solid #0B2A44 !important;
        padding-bottom: 24px !important;
        margin-bottom: 32px !important;
        display: flex !important;
        justify-content: space-between !important;
        align-items: flex-start !important;
      }
      
      .company-info h1 {
        color: #0B2A44 !important;
        margin: 0 0 8px 0 !important;
        font-size: 28px !important;
        font-weight: 700 !important;
      }
      
      .company-info h2 {
        color: #1E88E5 !important;
        margin: 0 0 8px 0 !important;
        font-size: 20px !important;
        font-weight: 500 !important;
      }
      
      .company-info p {
        color: #666 !important;
        margin: 0 !important;
        font-size: 14px !important;
      }
      
      .report-details {
        text-align: right !important;
      }
      
      .report-details p {
        margin: 4px 0 !important;
        font-weight: 500 !important;
        font-size: 14px !important;
      }
      
      .report-details strong {
        color: #0B2A44 !important;
      }
      
      /* Section styles */
      .report-section {
        margin-bottom: 32px !important;
        padding: 0 !important;
      }
      
      .report-section h3 {
        color: #0B2A44 !important;
        font-size: 22px !important;
        font-weight: 600 !important;
        margin-bottom: 20px !important;
        border-bottom: 2px solid #1E88E5 !important;
        padding-bottom: 8px !important;
      }
      
      /* Summary grid */
      .summary-grid {
        display: grid !important;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)) !important;
        gap: 20px !important;
        margin-top: 20px !important;
      }
      
      .summary-item {
        background: white !important;
        border: 1px solid #e0e0e0 !important;
        border-radius: 8px !important;
        padding: 20px !important;
        text-align: center !important;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05) !important;
      }
      
      .summary-item h4 {
        color: #666 !important;
        font-size: 14px !important;
        font-weight: 500 !important;
        margin: 0 0 12px 0 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
      }
      
      .summary-value {
        font-size: 24px !important;
        font-weight: 700 !important;
        color: #0B2A44 !important;
        margin: 0 !important;
      }
      
      /* Data table */
      .data-table {
        width: 100% !important;
        border-collapse: collapse !important;
        margin-top: 20px !important;
        background: white !important;
        border-radius: 8px !important;
        overflow: hidden !important;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05) !important;
      }
      
      .data-table th {
        background-color: #0B2A44 !important;
        color: white !important;
        padding: 16px 12px !important;
        text-align: left !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        border: none !important;
      }
      
      .data-table td {
        padding: 12px !important;
        border-bottom: 1px solid #e0e0e0 !important;
        text-align: left !important;
        font-size: 14px !important;
      }
      
      .data-table tr:hover {
        background-color: #f5f5f5 !important;
      }
      
      .data-table tr:last-child td {
        border-bottom: none !important;
      }
      
      /* Charts grid */
      .charts-grid {
        display: grid !important;
        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)) !important;
        gap: 24px !important;
        margin-top: 20px !important;
      }
      
      .chart-placeholder {
        background: white !important;
        border: 2px dashed #1E88E5 !important;
        border-radius: 8px !important;
        padding: 32px !important;
        text-align: center !important;
        min-height: 200px !important;
        display: flex !important;
        flex-direction: column !important;
        justify-content: center !important;
        align-items: center !important;
      }
      
      .chart-placeholder h4 {
        color: #0B2A44 !important;
        margin: 0 0 12px 0 !important;
        font-size: 18px !important;
        font-weight: 600 !important;
      }
      
      .chart-placeholder p {
        color: #666 !important;
        margin: 0 !important;
        font-size: 14px !important;
      }
      
      /* Footer */
      .report-footer {
        border-top: 2px solid #0B2A44 !important;
        padding-top: 24px !important;
        margin-top: 48px !important;
        text-align: center !important;
        color: #666 !important;
        font-size: 14px !important;
      }
      
      .report-footer p {
        margin: 4px 0 !important;
      }
      
      /* Print styles */
      @media print {
        body { 
          margin: 10px !important; 
          font-size: 12px !important;
        }
        .report-header { 
          flex-direction: column !important; 
          align-items: flex-start !important; 
        }
        .report-details { 
          text-align: left !important; 
          margin-top: 16px !important; 
        }
        .summary-grid { 
          grid-template-columns: 1fr !important; 
        }
        .charts-grid { 
          grid-template-columns: 1fr !important; 
        }
        .summary-item {
          break-inside: avoid !important;
        }
        .data-table {
          break-inside: avoid !important;
        }
      }
    </style>
  `
  
  const fullHTML = `
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>Dura Capital Financial Report</title>
      ${cssStyles}
    </head>
    <body>
      ${generatedReportContent.value}
    </body>
    </html>
  `
  
  const blob = new Blob([fullHTML], { type: 'text/html' })
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `Dura-Capital-Report-${date}.html`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  window.URL.revokeObjectURL(url)
}

const downloadPDFReport = (date: string) => {
  // Generate report with only essential sections to avoid duplication
  const calculations = visualizationData.value?.calculations || []
  const currentDate = new Date().toLocaleDateString()
  const instrumentType = visualizationData.value?.instrumentType || 'Money Market'
  
  // Create clean report HTML without duplication
  let reportHTML = `
    <div class="dura-capital-report">
      <header class="report-header">
        <div class="company-info">
          <h1>Dura Capital</h1>
          <h2>Financial Analysis Report</h2>
          <p>Generated: ${currentDate}</p>
        </div>
        <div class="report-details">
          <p><strong>Instrument Type:</strong> ${instrumentType}</p>
          <p><strong>Total Records:</strong> ${calculations.length}</p>
          <p><strong>Report ID:</strong> DC-${Date.now()}</p>
        </div>
      </header>
      
      <div class="report-content">`
  
  // Add only summary section
  const totalPrincipal = calculations.reduce((sum: any, calc: any) => sum + (calc.principal || 0), 0)
  const totalInterest = calculations.reduce((sum: any, calc: any) => sum + (calc.interest_earned || 0), 0)
  const avgYield = calculations.length > 0 ? calculations.reduce((sum: any, calc: any) => sum + (calc.yield || 0), 0) / calculations.length : 0
  
  reportHTML += `
        <section class="report-section">
          <h3>Executive Summary</h3>
          <div class="summary-grid">
            <div class="summary-item">
              <h4>Total Principal</h4>
              <p class="summary-value">$${totalPrincipal.toLocaleString()}</p>
            </div>
            <div class="summary-item">
              <h4>Total Interest Earned</h4>
              <p class="summary-value">$${totalInterest.toLocaleString()}</p>
            </div>
            <div class="summary-item">
              <h4>Average Yield</h4>
              <p class="summary-value">${avgYield.toFixed(2)}%</p>
            </div>
            <div class="summary-item">
              <h4>Number of Instruments</h4>
              <p class="summary-value">${calculations.length}</p>
            </div>
          </div>
        </section>
        
        <section class="report-section">
          <h3>Detailed Financial Data</h3>
          <table class="data-table">
            <thead>
              <tr>
                <th>Instrument Name</th>
                <th>Principal</th>
                <th>Interest Rate</th>
                <th>Term (Days)</th>
                <th>Interest Earned</th>
                <th>Maturity Value</th>
                <th>Yield (%)</th>
              </tr>
            </thead>
            <tbody>`
  
  calculations.forEach((calc: any) => {
    reportHTML += `
              <tr>
                <td>${calc.instrument_name || calc.instrument_type || 'N/A'}</td>
                <td>$${(calc.principal || 0).toLocaleString()}</td>
                <td>${((calc.interest_rate || 0) * 100).toFixed(2)}%</td>
                <td>${calc.term_days || 0}</td>
                <td>$${(calc.interest_earned || 0).toLocaleString()}</td>
                <td>$${((calc.maturity_value || calc.principal + (calc.interest_earned || 0)) || 0).toLocaleString()}</td>
                <td>${(calc.yield || 0).toFixed(2)}%</td>
              </tr>`
  })
  
  reportHTML += `
            </tbody>
          </table>
        </section>
      </div>
      
      <footer class="report-footer">
        <p>© 2024 Dura Capital - Financial Analysis Report</p>
        <p>This report was generated automatically based on uploaded financial data.</p>
      </footer>
    </div>`
  
  // Wrap the report HTML with proper document structure and enhanced CSS for PDF
  const fullContent = `
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="UTF-8">
      <title>Dura Capital Financial Report</title>
      <style>
        body {
          font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
          color: #333;
          margin: 0;
          padding: 20px;
          background: #fff;
        }
        
        .dura-capital-report {
          max-width: 1200px;
          margin: 0 auto;
          padding: 0;
        }
        
        .report-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          padding: 30px;
          background: linear-gradient(135deg, #0B2A44 0%, #1E88E5 100%);
          color: white;
          margin: -20px -20px 30px -20px;
          border-radius: 0 0 12px 12px;
        }
        
        .company-info h1 {
          margin: 0 0 8px 0;
          font-size: 28px;
          font-weight: 700;
          color: white;
        }
        
        .company-info h2 {
          margin: 0 0 12px 0;
          font-size: 18px;
          font-weight: 400;
          color: rgba(255, 255, 255, 0.9);
        }
        
        .company-info p {
          margin: 0;
          font-size: 14px;
          color: rgba(255, 255, 255, 0.8);
        }
        
        .report-details {
          text-align: right;
        }
        
        .report-details p {
          margin: 6px 0;
          font-size: 14px;
          font-weight: 500;
        }
        
        .report-details strong {
          color: rgba(255, 255, 255, 0.8);
        }
        
        .report-content {
          padding: 0 20px;
        }
        
        .report-section {
          margin-bottom: 40px;
        }
        
        .report-section h3 {
          color: #0B2A44;
          font-size: 22px;
          font-weight: 600;
          margin: 0 0 20px 0;
          padding-bottom: 10px;
          border-bottom: 3px solid #1E88E5;
        }
        
        .summary-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
          gap: 20px;
          margin-bottom: 30px;
        }
        
        .summary-item {
          background: white;
          border: 1px solid #e0e0e0;
          border-radius: 12px;
          padding: 24px;
          text-align: center;
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
          transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        
        .summary-item:hover {
          transform: translateY(-2px);
          box-shadow: 0 8px 20px rgba(0, 0, 0, 0.12);
        }
        
        .summary-item h4 {
          color: #666;
          font-size: 14px;
          font-weight: 500;
          margin: 0 0 12px 0;
          text-transform: uppercase;
          letter-spacing: 1px;
        }
        
        .summary-value {
          font-size: 32px;
          font-weight: 700;
          color: #0B2A44;
          margin: 0;
          line-height: 1.2;
        }
        
        .data-table {
          width: 100%;
          border-collapse: collapse;
          margin: 20px 0;
          background: white;
          border-radius: 12px;
          overflow: hidden;
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
        }
        
        .data-table th {
          background: #0B2A44;
          color: white;
          padding: 16px 12px;
          text-align: left;
          font-weight: 600;
          font-size: 14px;
          border: none;
        }
        
        .data-table td {
          padding: 14px 12px;
          border-bottom: 1px solid #f0f0f0;
          text-align: left;
          font-size: 14px;
        }
        
        .data-table tr:hover {
          background: #f8f9fa;
        }
        
        .data-table tr:last-child td {
          border-bottom: none;
        }
        
        .report-footer {
          margin-top: 50px;
          padding: 30px 20px;
          border-top: 2px solid #e0e0e0;
          text-align: center;
          background: #f8f9fa;
          border-radius: 12px;
        }
        
        .report-footer p {
          margin: 8px 0;
          font-size: 14px;
          color: #666;
        }
        
        @media print {
          body { margin: 0; padding: 10px; font-size: 12px; }
          .report-header { margin: -10px -10px 20px -10px; padding: 20px; }
          .summary-grid { grid-template-columns: 1fr; }
          .summary-item { break-inside: avoid; margin-bottom: 15px; }
          .data-table { break-inside: avoid; }
          .data-table th, .data-table td { padding: 8px 6px; font-size: 11px; }
          .summary-value { font-size: 24px; }
        }
      </style>
    </head>
    <body>
      ${reportHTML}
    </body>
    </html>`
  
  const blob = new Blob([fullContent], { type: 'text/html' })
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `Dura-Capital-Report-${date}.html`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  window.URL.revokeObjectURL(url)
  
  // Open print dialog for PDF creation
  setTimeout(() => {
    window.print()
  }, 500)
}

const downloadExcelReport = (date: string) => {
  const calculations = visualizationData.value?.calculations || []
  const currentDate = new Date().toLocaleDateString()
  
  // Create CSV content that matches the exact format from the image
  let csvContent = "DURA CAPITAL FINANCIAL REPORT\n"
  csvContent += "Generated on: " + currentDate + "\n"
  csvContent += "Report ID: DC-" + Date.now() + "\n"
  csvContent += "Instrument Type: " + (visualizationData.value?.instrumentType || 'Money Market') + "\n"
  csvContent += "Total Records: " + calculations.length + "\n\n"
  
  csvContent += "EXECUTIVE SUMMARY\n"
  csvContent += "=====================================\n"
  csvContent += "Metric,Value,Description\n"
  
  const totalPrincipal = calculations.reduce((sum: any, calc: any) => sum + (calc.principal || 0), 0)
  const totalInterest = calculations.reduce((sum: any, calc: any) => sum + (calc.interest_earned || 0), 0)
  const avgYield = calculations.length > 0 ? calculations.reduce((sum: any, calc: any) => sum + (calc.yield || 0), 0) / calculations.length : 0
  
  csvContent += '"Total Principal","$' + totalPrincipal.toLocaleString() + '","Sum of all instrument principals"\n'
  csvContent += '"Total Interest Earned","$' + totalInterest.toLocaleString() + '","Total interest generated across all instruments"\n'
  csvContent += '"Average Yield","' + avgYield.toFixed(2) + '%","Average yield rate across all instruments"\n'
  csvContent += '"Number of Instruments","' + calculations.length + '","Total number of financial instruments"\n\n'
  
  csvContent += "FINANCIAL INSTRUMENTS ANALYSIS\n"
  csvContent += "=====================================\n"
  csvContent += '"Instrument Name","Principal Amount","Interest Rate","Term (Days)","Interest Earned","Maturity Value","Yield (%)"\n'
  
  calculations.forEach((calc: any) => {
    const instrumentName = calc.instrument_name || calc.instrument_type || 'N/A'
    const principal = (calc.principal || 0).toLocaleString()
    const interestRate = ((calc.interest_rate || 0) * 100).toFixed(2)
    const termDays = calc.term_days || 0
    const interestEarned = (calc.interest_earned || 0).toLocaleString()
    const maturityValue = (calc.maturity_value || calc.principal + (calc.interest_earned || 0)).toLocaleString()
    const yieldRate = (calc.yield || 0).toFixed(2)
    
    csvContent += '"' + instrumentName + '","$' + principal + '","' + interestRate + '%","' + termDays + '","$' + interestEarned + '","$' + maturityValue + '","' + yieldRate + '%"\n'
  })
  
  csvContent += "\n"
  csvContent += "PERFORMANCE METRICS\n"
  csvContent += "=====================================\n"
  csvContent += '"Metric","Value","Analysis"\n'
  csvContent += '"Highest Principal","$' + Math.max(...calculations.map((c: any) => c.principal || 0)).toLocaleString() + '","Largest single investment"\n'
  csvContent += '"Lowest Principal","$' + Math.min(...calculations.map((c: any) => c.principal || 0)).toLocaleString() + '","Smallest single investment"\n'
  csvContent += '"Average Term","' + (calculations.reduce((sum: any, calc: any) => sum + (calc.term_days || 0), 0) / calculations.length).toFixed(0) + ' days","Average investment duration"\n'
  csvContent += '"Total Portfolio Value","$' + (totalPrincipal + totalInterest).toLocaleString() + '","Total value including interest"\n'
  
  csvContent += "\n"
  csvContent += "© 2024 Dura Capital - Financial Analysis Report\n"
  csvContent += "This report was generated automatically based on uploaded financial data.\n"
  
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `Dura-Capital-Report-${date}.csv`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  window.URL.revokeObjectURL(url)
}

const downloadCSVReport = (date: string) => {
  downloadExcelReport(date) // CSV and Excel use the same function
}

const downloadJSONReport = (date: string) => {
  const calculations = visualizationData.value?.calculations || []
  const reportData = {
    report: {
      company: "Dura Capital",
      title: "Financial Analysis Report",
      generatedDate: new Date().toISOString(),
      reportId: `DC-${Date.now()}`,
      instrumentType: visualizationData.value?.instrumentType || 'Money Market',
      totalRecords: calculations.length
    },
    summary: {
      totalPrincipal: calculations.reduce((sum, calc) => sum + (calc.principal || 0), 0),
      totalInterestEarned: calculations.reduce((sum, calc) => sum + (calc.interest_earned || 0), 0),
      averageYield: calculations.length > 0 ? calculations.reduce((sum, calc) => sum + (calc.yield || 0), 0) / calculations.length : 0,
      numberOfInstruments: calculations.length
    },
    calculations: calculations,
    metadata: {
      exportFormat: "JSON",
      version: "1.0",
      generatedBy: "Dura Capital Financial System"
    }
  }
  
  const blob = new Blob([JSON.stringify(reportData, null, 2)], { type: 'application/json' })
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `Dura-Capital-Report-${date}.json`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  window.URL.revokeObjectURL(url)
}

const downloadWordReport = (date: string) => {
  // Create a simplified HTML document that Word can open
  const wordContent = `
    <!DOCTYPE html>
    <html xmlns:o="urn:schemas-microsoft-com:office:office">
    <head>
      <meta charset="UTF-8">
      <title>Dura Capital Financial Report</title>
      <style>
        body { font-family: 'Calibri', sans-serif; margin: 20px; color: #333; }
        .header { border-bottom: 2px solid #0B2A44; padding-bottom: 20px; margin-bottom: 30px; }
        .company-info h1 { color: #0B2A44; margin: 0; font-size: 24px; }
        .company-info h2 { color: #1E88E5; margin: 5px 0; font-size: 18px; }
        .section { margin-bottom: 30px; }
        .section h3 { color: #0B2A44; border-bottom: 1px solid #1E88E5; padding-bottom: 5px; }
        .summary-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; margin: 20px 0; }
        .summary-item { border: 1px solid #ddd; padding: 15px; text-align: center; }
        .data-table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        .data-table th, .data-table td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        .data-table th { background-color: #0B2A44; color: white; }
        .footer { border-top: 1px solid #0B2A44; padding-top: 20px; margin-top: 40px; text-align: center; font-size: 12px; }
      </style>
    </head>
    <body>
      ${generatedReportContent.value}
    </body>
    </html>
  `
  
  const blob = new Blob([wordContent], { type: 'application/msword' })
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `Dura-Capital-Report-${date}.doc`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  window.URL.revokeObjectURL(url)
}

const downloadPowerPointReport = (date: string) => {
  // Create a simple HTML presentation that can be imported into PowerPoint
  const calculations = visualizationData.value?.calculations || []
  
  let pptContent = `
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="UTF-8">
      <title>Dura Capital Financial Report</title>
      <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
        .slide { background: white; margin: 20px 0; padding: 40px; border: 1px solid #ddd; min-height: 600px; }
        .slide h1 { color: #0B2A44; text-align: center; margin-bottom: 30px; }
        .slide h2 { color: #1E88E5; border-bottom: 2px solid #1E88E5; padding-bottom: 10px; }
        .summary-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; margin: 30px 0; }
        .summary-item { text-align: center; padding: 20px; background: #f9f9f9; border-radius: 8px; }
        .summary-item h3 { color: #0B2A44; margin: 0 0 10px 0; }
        .summary-item p { font-size: 24px; font-weight: bold; color: #1E88E5; margin: 0; }
        .data-table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        .data-table th, .data-table td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        .data-table th { background-color: #0B2A44; color: white; }
        .footer { text-align: center; font-size: 12px; color: #666; margin-top: 30px; }
      </style>
    </head>
    <body>
      <div class="slide">
        <h1>Dura Capital Financial Report</h1>
        <h2>Executive Summary</h2>
        <div class="summary-grid">
          <div class="summary-item">
            <h3>Total Principal</h3>
            <p>$${calculations.reduce((sum, calc) => sum + (calc.principal || 0), 0).toLocaleString()}</p>
          </div>
          <div class="summary-item">
            <h3>Total Interest Earned</h3>
            <p>$${calculations.reduce((sum, calc) => sum + (calc.interest_earned || 0), 0).toLocaleString()}</p>
          </div>
          <div class="summary-item">
            <h3>Average Yield</h3>
            <p>${calculations.length > 0 ? (calculations.reduce((sum, calc) => sum + (calc.yield || 0), 0) / calculations.length).toFixed(2) : 0}%</p>
          </div>
          <div class="summary-item">
            <h3>Number of Instruments</h3>
            <p>${calculations.length}</p>
          </div>
        </div>
        <div class="footer">Generated: ${new Date().toLocaleDateString()}</div>
      </div>
      
      <div class="slide">
        <h1>Dura Capital Financial Report</h1>
        <h2>Detailed Financial Data</h2>
        <table class="data-table">
          <thead>
            <tr>
              <th>Instrument Name</th>
              <th>Principal</th>
              <th>Interest Rate</th>
              <th>Term (Days)</th>
              <th>Interest Earned</th>
            </tr>
          </thead>
          <tbody>
            ${calculations.map(calc => `
              <tr>
                <td>${calc.instrument_name || calc.instrument_type || 'N/A'}</td>
                <td>$${(calc.principal || 0).toLocaleString()}</td>
                <td>${((calc.interest_rate || 0) * 100).toFixed(2)}%</td>
                <td>${calc.term_days || 0}</td>
                <td>$${(calc.interest_earned || 0).toLocaleString()}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
        <div class="footer">Generated: ${new Date().toLocaleDateString()}</div>
      </div>
    </body>
    </html>
  `
  
  const blob = new Blob([pptContent], { type: 'text/html' })
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `Dura-Capital-Report-${date}.html`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  window.URL.revokeObjectURL(url)
}

const downloadXMLReport = (date: string) => {
  const calculations = visualizationData.value?.calculations || []
  
  const xmlContent = `<?xml version="1.0" encoding="UTF-8"?>
<report>
  <metadata>
    <company>Dura Capital</company>
    <title>Financial Analysis Report</title>
    <generatedDate>${new Date().toISOString()}</generatedDate>
    <reportId>DC-${Date.now()}</reportId>
    <instrumentType>${visualizationData.value?.instrumentType || 'Money Market'}</instrumentType>
    <totalRecords>${calculations.length}</totalRecords>
  </metadata>
  
  <summary>
    <totalPrincipal>${calculations.reduce((sum, calc) => sum + (calc.principal || 0), 0)}</totalPrincipal>
    <totalInterestEarned>${calculations.reduce((sum, calc) => sum + (calc.interest_earned || 0), 0)}</totalInterestEarned>
    <averageYield>${calculations.length > 0 ? calculations.reduce((sum, calc) => sum + (calc.yield || 0), 0) / calculations.length : 0}</averageYield>
    <numberOfInstruments>${calculations.length}</numberOfInstruments>
  </summary>
  
  <calculations>
    ${calculations.map(calc => `
    <calculation>
      <instrumentName>${calc.instrument_name || calc.instrument_type || 'N/A'}</instrumentName>
      <principal>${calc.principal || 0}</principal>
      <interestRate>${calc.interest_rate || 0}</interestRate>
      <termDays>${calc.term_days || 0}</termDays>
      <interestEarned>${calc.interest_earned || 0}</interestEarned>
      <maturityValue>${calc.maturity_value || calc.principal + (calc.interest_earned || 0)}</maturityValue>
      <yield>${calc.yield || 0}</yield>
    </calculation>
    `).join('')}
  </calculations>
</report>`
  
  const blob = new Blob([xmlContent], { type: 'application/xml' })
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `Dura-Capital-Report-${date}.xml`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  window.URL.revokeObjectURL(url)
}

const downloadTextReport = (date: string) => {
  const calculations = visualizationData.value?.calculations || []
  
  let textContent = "DURA CAPITAL FINANCIAL REPORT\n"
  textContent += "=".repeat(50) + "\n\n"
  textContent += `Generated: ${new Date().toLocaleDateString()}\n`
  textContent += `Report ID: DC-${Date.now()}\n`
  textContent += `Instrument Type: ${visualizationData.value?.instrumentType || 'Money Market'}\n`
  textContent += `Total Records: ${calculations.length}\n\n`
  
  textContent += "EXECUTIVE SUMMARY\n"
  textContent += "-".repeat(30) + "\n"
  textContent += `Total Principal: $${calculations.reduce((sum, calc) => sum + (calc.principal || 0), 0).toLocaleString()}\n`
  textContent += `Total Interest Earned: $${calculations.reduce((sum, calc) => sum + (calc.interest_earned || 0), 0).toLocaleString()}\n`
  textContent += `Average Yield: ${calculations.length > 0 ? (calculations.reduce((sum, calc) => sum + (calc.yield || 0), 0) / calculations.length).toFixed(2) : 0}%\n`
  textContent += `Number of Instruments: ${calculations.length}\n\n`
  
  textContent += "DETAILED FINANCIAL DATA\n"
  textContent += "-".repeat(30) + "\n"
  textContent += "Instrument Name".padEnd(25) + "Principal".padEnd(15) + "Rate".padEnd(10) + "Term".padEnd(8) + "Interest".padEnd(12) + "Yield\n"
  textContent += "=".repeat(80) + "\n"
  
  calculations.forEach(calc => {
    textContent += `${(calc.instrument_name || calc.instrument_type || 'N/A').padEnd(25)}`
    textContent += `$${(calc.principal || 0).toLocaleString().padEnd(14)}`
    textContent += `${((calc.interest_rate || 0) * 100).toFixed(2)}%`.padEnd(10)
    textContent += `${(calc.term_days || 0).toString().padEnd(8)}`
    textContent += `$${(calc.interest_earned || 0).toLocaleString().padEnd(11)}`
    textContent += `${(calc.yield || 0).toFixed(2)}%\n`
  })
  
  textContent += "\n" + "=".repeat(50) + "\n"
  textContent += "© 2024 Dura Capital - Financial Analysis Report\n"
  textContent += "This report was generated automatically based on uploaded financial data.\n"
  
  const blob = new Blob([textContent], { type: 'text/plain' })
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `Dura-Capital-Report-${date}.txt`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  window.URL.revokeObjectURL(url)
}

const printReport = () => {
  if (!generatedReportContent.value) return
  
  const printWindow = window.open('', '_blank')
  if (printWindow) {
    printWindow.document.write(`
      <!DOCTYPE html>
      <html>
        <head>
          <title>Dura Capital Financial Report</title>
          <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .report-header { border-bottom: 2px solid #0B2A44; padding-bottom: 20px; margin-bottom: 30px; }
            .company-info h1 { color: #0B2A44; margin: 0; }
            .company-info h2 { color: #1E88E5; margin: 5px 0; }
            .report-details { margin-top: 15px; }
            .report-section { margin-bottom: 30px; }
            .summary-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; }
            .summary-item { border: 1px solid #ddd; padding: 15px; text-align: center; }
            .summary-value { font-size: 1.5em; font-weight: bold; color: #0B2A44; }
            .data-table { width: 100%; border-collapse: collapse; margin-top: 20px; }
            .data-table th, .data-table td { border: 1px solid #ddd; padding: 8px; text-align: left; }
            .data-table th { background-color: #f5f5f5; font-weight: bold; }
            .charts-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
            .chart-placeholder { border: 1px solid #ddd; padding: 20px; text-align: center; }
            .report-footer { border-top: 1px solid #ddd; padding-top: 20px; margin-top: 40px; text-align: center; color: #666; }
            @media print { body { margin: 10px; } }
          </style>
        </head>
        <body>
          ${generatedReportContent.value}
        </body>
      </html>
    `)
    printWindow.document.close()
    printWindow.print()
    printWindow.close()
  }
}

</script>

<style scoped>
.reports-view {
  width: 100%;
  margin: 0 auto;
}

.page-title {
  font-size: 32px;
}

.action-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-bottom: 24px;
}

.sections-section {
  margin-top: 24px;
}

.section-title {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 16px;
  color: #0B2A44;
}

.section-card {
  cursor: pointer;
  transition: all 0.3s ease;
  border: 2px solid transparent;
}

.section-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.section-card.selected {
  border-color: #1E88E5;
  background-color: rgba(30, 136, 229, 0.05);
}

.section-name {
  font-weight: 600;
  margin-top: 8px;
  color: #0B2A44;
}

.section-desc {
  font-size: 14px;
  color: #666;
  margin-top: 4px;
}

.sample-section {
  border: 2px solid transparent;
  transition: all 0.3s ease;
}

.sample-section.selected {
  border-color: #4CAF50;
  background-color: rgba(76, 175, 80, 0.05);
}

.sample-title {
  font-weight: 600;
  margin-top: 8px;
  color: #0B2A44;
}

.report-content {
  background: #f8f9fa;
  border: 1px solid #dee2e6;
  border-radius: 8px;
  padding: 24px;
  margin-top: 16px;
}

/* Report specific styles */
:deep(.dura-capital-report) {
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  color: #333;
}

:deep(.report-header) {
  border-bottom: 3px solid #0B2A44;
  padding-bottom: 24px;
  margin-bottom: 32px;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

:deep(.company-info h1) {
  color: #0B2A44;
  margin: 0 0 8px 0;
  font-size: 28px;
  font-weight: 700;
}

:deep(.company-info h2) {
  color: #1E88E5;
  margin: 0 0 8px 0;
  font-size: 20px;
  font-weight: 500;
}

:deep(.report-details) {
  text-align: right;
}

:deep(.report-details p) {
  margin: 4px 0;
  font-weight: 500;
}

:deep(.report-section) {
  margin-bottom: 32px;
}

:deep(.report-section h3) {
  color: #0B2A44;
  font-size: 22px;
  font-weight: 600;
  margin-bottom: 20px;
  border-bottom: 2px solid #1E88E5;
  padding-bottom: 8px;
}

:deep(.summary-grid) {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
  margin-top: 20px;
}

:deep(.summary-item) {
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 20px;
  text-align: center;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

:deep(.summary-item h4) {
  color: #666;
  font-size: 14px;
  font-weight: 500;
  margin: 0 0 12px 0;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

:deep(.summary-value) {
  font-size: 24px;
  font-weight: 700;
  color: #0B2A44;
  margin: 0;
}

:deep(.data-table) {
  width: 100%;
  border-collapse: collapse;
  margin-top: 20px;
  background: white;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

:deep(.data-table th) {
  background-color: #0B2A44;
  color: white;
  padding: 16px 12px;
  text-align: left;
  font-weight: 600;
  font-size: 14px;
}

:deep(.data-table td) {
  padding: 12px;
  border-bottom: 1px solid #e0e0e0;
  text-align: left;
}

:deep(.data-table tr:hover) {
  background-color: #f5f5f5;
}

:deep(.charts-grid) {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 24px;
  margin-top: 20px;
}

:deep(.chart-placeholder) {
  background: white;
  border: 2px dashed #1E88E5;
  border-radius: 8px;
  padding: 32px;
  text-align: center;
  min-height: 200px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
}

:deep(.chart-placeholder h4) {
  color: #0B2A44;
  margin: 0 0 12px 0;
  font-size: 18px;
  font-weight: 600;
}

:deep(.chart-placeholder p) {
  color: #666;
  margin: 0;
  font-size: 14px;
}

:deep(.report-footer) {
  border-top: 2px solid #0B2A44;
  padding-top: 24px;
  margin-top: 48px;
  text-align: center;
  color: #666;
  font-size: 14px;
}

:deep(.report-footer p) {
  margin: 4px 0;
}

@media (max-width: 768px) {
  :deep(.report-header) {
    flex-direction: column;
    align-items: flex-start;
  }
  
  :deep(.report-details) {
    text-align: left;
    margin-top: 16px;
  }
  
  :deep(.summary-grid) {
    grid-template-columns: 1fr;
  }
  
  :deep(.charts-grid) {
    grid-template-columns: 1fr;
  }
  
  .action-buttons {
    flex-direction: column;
  }
  
  .action-buttons .v-btn {
    width: 100%;
  }
}

.page-subtitle {
  color: #666;
}

/* KPI Styles - Matching DashboardView */
.kpi-row {
  margin-bottom: 32px;
}

.kpi-card {
  height: 120px;
  border-radius: 12px;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  background: white;
  border: 1px solid rgba(11, 42, 68, 0.08);
  position: relative;
}

.kpi-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, #0B2A44, #1E88E5, #4CAF50);
}

.kpi-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
}

.kpi-card:hover::before {
  height: 4px;
}

.kpi-content {
  display: flex;
  align-items: center;
  height: 100%;
}

.kpi-icon {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 12px;
  flex-shrink: 0;
}

.kpi-icon .v-icon {
  font-size: 28px;
}

.kpi-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.kpi-value {
  font-size: 24px;
  font-weight: 700;
  color: #0B2A44;
  line-height: 1;
  margin-bottom: 4px;
}

.kpi-title {
  font-size: 14px;
  color: #666;
  margin-bottom: 4px;
}

.kpi-change {
  display: flex;
  align-items: center;
  font-size: 12px;
  font-weight: 600;
}

.kpi-change.positive {
  color: #4CAF50;
}

.kpi-change.neutral {
  color: #FFC107;
}

.kpi-change.negative {
  color: #F44336;
}

/* Card Title Styles */
.card-title {
  display: flex;
  align-items: center;
  color: #0B2A44;
  font-weight: 600;
  font-size: 18px;
}

.title-icon {
  margin-right: 8px;
  color: #0B2A44;
}

/* Stats Card Styles */
.stats-card {
  border-radius: 12px;
  margin-bottom: 32px;
  background: white;
  border: 1px solid rgba(11, 42, 68, 0.08);
  position: relative;
}

/* Config Card Styles */
.config-card {
  border-radius: 12px;
  margin-bottom: 32px;
  background: white;
  border: 1px solid rgba(11, 42, 68, 0.08);
  position: relative;
}

.config-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, #0B2A44, #1E88E5);
}

/* Preview Card Styles */
.preview-card {
  border-radius: 12px;
  margin-bottom: 32px;
  background: white;
  border: 1px solid rgba(11, 42, 68, 0.08);
  position: relative;
}

.preview-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, #0B2A44, #1E88E5);
}

.stats-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, #0B2A44, #1E88E5);
}

.action-buttons {
  margin: 20px 0;
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.section-card {
  cursor: pointer;
  border-radius: 10px;
  transition: 0.3s;
}

.section-card:hover {
  transform: translateY(-3px);
}

.section-card.selected {
  border: 2px solid #0B2A44;
  background: rgba(11, 42, 68, 0.05);
}

.section-name {
  font-weight: 600;
  color: #0B2A44;
  margin-top: 8px;
  margin-bottom: 4px;
}

.section-desc {
  font-size: 12px;
  color: #666;
  margin-top: 4px;
}

.sample-section {
  border-radius: 8px;
  transition: transform 0.2s ease;
  border: 1px solid rgba(11, 42, 68, 0.08);
}

.sample-section:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.sample-section.selected {
  border: 2px solid #0B2A44;
  background: rgba(11, 42, 68, 0.05);
}

.sample-title {
  font-weight: 600;
  color: #0B2A44;
  margin-top: 8px;
}

</style>