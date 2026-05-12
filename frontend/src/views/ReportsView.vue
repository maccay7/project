<template>
  <fixed-layout>
    <div class="reports-view">

      <!-- Header -->
      <div class="page-header">
        <h1>Report Generation</h1>
        <p>Generate Excel reports from your calculation data</p>
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

      <!-- Data Overview -->
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
import { useRouter } from 'vue-router'
import FixedLayout from '../components/FixedLayout.vue'
import ExcelViewer from '../components/ExcelViewer.vue'
import * as XLSX from 'xlsx'

const router = useRouter()

// State
const calcData = ref([])
const instrumentType = ref('')
const generating = ref(false)
const reportReady = ref(false)

// Sections
const sections = ref([
  { key: 'summary', name: 'Summary', desc: 'Key metrics', icon: 'mdi-chart-line', color: '#0B2A44', selected: true },
  { key: 'data', name: 'Data Table', desc: 'All records', icon: 'mdi-table', color: '#1E88E5', selected: true },
  { key: 'yield', name: 'Yield Analysis', desc: 'Yield statistics', icon: 'mdi-chart-timeline', color: '#4CAF50', selected: true }
])

// Computed
const hasData = computed(() => calcData.value?.length > 0)
const dataHeaders = computed(() => calcData.value.length ? Object.keys(calcData.value[0]) : [])

const kpiStats = computed(() => [
  { title: 'Records', value: calcData.value.length || 0, icon: 'mdi-database', color: 'rgba(11,42,68,0.1)', iconColor: '#0B2A44' },
  { title: 'Instrument', value: instrumentType.value || 'N/A', icon: 'mdi-chart-line', color: 'rgba(30,136,229,0.1)', iconColor: '#1E88E5' },
  { title: 'Export', value: 'Excel (.xlsx)', icon: 'mdi-file-excel', color: 'rgba(76,175,80,0.1)', iconColor: '#4CAF50' }
])

// Load data from calculations page
function loadData() {
  try {
    const stored = localStorage.getItem('calculations')
    if (!stored) {
      alert('No calculation data found. Please run calculations first.')
      return
    }
    const data = JSON.parse(stored)
    calcData.value = data.calculations || []
    instrumentType.value = data.instrumentType || 'Money Market'
    alert(`Loaded ${calcData.value.length} records`)
  } catch (err) {
    console.error(err)
    alert('Error loading data')
  }
}

// Select/Deselect sections
function selectAll() { sections.value.forEach(s => s.selected = true) }
function clearAll() { sections.value.forEach(s => s.selected = false) }

// Generate Excel report
async function generateExcel() {
  generating.value = true
  
  setTimeout(() => {
    const selected = sections.value.filter(s => s.selected)
    const data = calcData.value
    const instrument = instrumentType.value
    const date = new Date().toLocaleDateString()
    
    // Create workbook
    const wb = XLSX.utils.book_new()
    const rows = []
    
    // Header
    rows.push(['DURA CAPITAL FINANCIAL REPORT'])
    rows.push(['Generated:', date])
    rows.push(['Instrument Type:', instrument])
    rows.push(['Total Records:', data.length])
    rows.push([])
    
    selected.forEach(section => {
      rows.push([section.name.toUpperCase()])
      rows.push([])
      
      if (section.key === 'summary') {
        const totalPrincipal = data.reduce((s, c) => s + (c.principal || 0), 0)
        const totalInterest = data.reduce((s, c) => s + (c.interest_earned || 0), 0)
        const avgYield = data.length ? data.reduce((s, c) => s + (c.annual_yield || c.yield || 0), 0) / data.length : 0
        
        rows.push(['Metric', 'Value'])
        rows.push(['Total Principal', totalPrincipal])
        rows.push(['Total Interest Earned', totalInterest])
        rows.push(['Average Yield (%)', avgYield.toFixed(2)])
        rows.push(['Number of Instruments', data.length])
        rows.push([])
      }
      
      if (section.key === 'data') {
        const headers = ['Instrument Name', 'Principal', 'Interest Rate', 'Term Days', 'Interest Earned', 'Maturity Value', 'Yield (%)']
        rows.push(headers)
        
        data.forEach(item => {
          rows.push([
            item.instrument_name || item.instrument_type || 'N/A',
            item.principal || 0,
            ((item.interest_rate || 0) * 100).toFixed(2),
            item.term_days || 0,
            item.interest_earned || 0,
            item.maturity_value || 0,
            (item.annual_yield || item.yield || 0).toFixed(2)
          ])
        })
        rows.push([])
      }
      
      if (section.key === 'yield') {
        const yields = data.map(c => c.annual_yield || c.yield || 0)
        const avgYield = yields.length ? yields.reduce((a, b) => a + b, 0) / yields.length : 0
        const maxYield = yields.length ? Math.max(...yields) : 0
        const minYield = yields.length ? Math.min(...yields.filter(y => y > 0)) : 0
        
        rows.push(['Metric', 'Value'])
        rows.push(['Average Yield (%)', avgYield.toFixed(2)])
        rows.push(['Maximum Yield (%)', maxYield.toFixed(2)])
        rows.push(['Minimum Yield (%)', minYield.toFixed(2)])
        rows.push([])
        rows.push(['Instrument', 'Yield (%)'])
        
        data.forEach(item => {
          rows.push([
            item.instrument_name || item.instrument_type || 'N/A',
            (item.annual_yield || item.yield || 0).toFixed(2)
          ])
        })
        rows.push([])
      }
    })
    
    rows.push(['© 2024 Dura Capital - Financial Analysis Report'])
    
    // Create worksheet
    const ws = XLSX.utils.aoa_to_sheet(rows)
    ws['!cols'] = [{ wch: 30 }, { wch: 20 }, { wch: 20 }, { wch: 15 }, { wch: 20 }, { wch: 20 }, { wch: 15 }]
    
    XLSX.utils.book_append_sheet(wb, ws, 'Report')
    
    // Download
    XLSX.writeFile(wb, `Dura-Capital-Report-${new Date().toISOString().split('T')[0]}.xlsx`)
    
    reportReady.value = true
    generating.value = false
    setTimeout(() => { reportReady.value = false }, 3000)
  }, 500)
}

// Reset all
function finishAndReset() {
  if (confirm('Complete & Reset? This will clear all data.')) {
    localStorage.clear()
    router.push('/upload')
  }
}

onMounted(() => {
  const stored = localStorage.getItem('calculations')
  if (stored) {
    const data = JSON.parse(stored)
    calcData.value = data.calculations || []
    instrumentType.value = data.instrumentType || 'Money Market'
  }
})
</script>

<style scoped>
.reports-view { max-width: 1400px; margin: 0 auto; padding: 20px; }
.page-header { margin-bottom: 30px; }
.page-header h1 { color: #0B2A44; font-size: 32px; font-weight: 700; margin-bottom: 8px; }
.page-header p { color: #666; font-size: 16px; }
.action-buttons { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 20px; }
.action-buttons.small { margin-bottom: 16px; }
.stats-card { border-radius: 12px; margin-bottom: 24px; background: white; border: 1px solid rgba(11,42,68,0.08); position: relative; }
.stats-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; background: linear-gradient(90deg, #0B2A44, #1E88E5); }
.card-title { display: flex; align-items: center; color: #0B2A44; font-weight: 600; font-size: 18px; padding: 16px 20px 0 20px; }
.title-icon { margin-right: 8px; }
.kpi-card { height: 100px; border-radius: 12px; transition: 0.2s; }
.kpi-card:hover { transform: translateY(-2px); }
.kpi-content { display: flex; align-items: center; height: 100%; padding: 8px; }
.kpi-icon { width: 50px; height: 50px; border-radius: 12px; display: flex; align-items: center; justify-content: center; margin-right: 12px; }
.kpi-value { font-size: 24px; font-weight: 700; color: #0B2A44; }
.kpi-title { font-size: 12px; color: #666; }
.section-card { cursor: pointer; transition: 0.2s; border: 2px solid transparent; border-radius: 12px; }
.section-card:hover { transform: translateY(-2px); }
.section-card.selected { border-color: #1E88E5; background: rgba(30,136,229,0.05); }
.section-name { font-weight: 600; margin-top: 8px; color: #0B2A44; }
.section-desc { font-size: 11px; color: #666; }
@media (max-width: 600px) {
  .reports-view { padding: 0 16px; }
  .action-buttons { flex-direction: column; }
}
</style>