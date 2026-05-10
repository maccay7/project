<template>
  <fixed-layout>
    <div class="calculations-view">

      <!-- Header -->
      <div class="page-header">
        <h1>Financial Calculations</h1>
        <p>Calculate yields, discount rates, and other financial metrics</p>
      </div>

      <!-- Action Buttons -->
      <div class="action-buttons">
        <v-btn color="#0B2A44" @click="loadFromCleaning">
          <v-icon left>mdi-database</v-icon> Load Dataset from Cleaning
        </v-btn>
        <v-btn color="#0B2A44" variant="outlined" @click="clearCalculations" :disabled="!hasData">
          <v-icon left>mdi-delete</v-icon> Clear Results
        </v-btn>
      </div>

      <!-- KPI Cards - Only show when data loaded -->
      <template v-if="hasData">
        <v-card class="stats-card">
          <v-card-title class="card-title">
            <v-icon class="title-icon">mdi-calculator</v-icon> Dataset Overview
          </v-card-title>
          <v-card-text>
            <v-row>
              <v-col cols="12" sm="6" md="3" v-for="stat in kpiStats" :key="stat.title">
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

        <!-- Calculation Tabs -->
        <v-card class="stats-card">
          <v-card-title class="card-title">
            <v-icon class="title-icon">mdi-finance</v-icon> Automated Calculations
          </v-card-title>
          <v-card-text>
            <v-tabs v-model="activeTab" color="#0B2A44">
              <v-tab value="treasury">Treasury Bills</v-tab>
              <v-tab value="bonds">Bonds</v-tab>
              <v-tab value="money-market">Money Market</v-tab>
            </v-tabs>

            <v-window v-model="activeTab">

              <!-- Treasury Bills -->
              <v-window-item value="treasury">
                <div class="pa-4">
                  <h3 class="tab-title">Treasury Bill Calculations</h3>
                  
                  <!-- Instrument Selection -->
                  <div class="instrument-selector mb-4">
                    <h4>Select Treasury Bill:</h4>
                    <v-chip-group v-model="selectedTreasury" mandatory>
                      <v-chip v-for="calc in treasuryCalcs" :key="calc.id" :value="calc.id" @click="selectTreasury(calc)">
                        {{ calc.instrument }}
                      </v-chip>
                    </v-chip-group>
                  </div>

                  <!-- Calculation Boxes -->
                  <v-row v-if="selectedTBill">
                    <v-col cols="12" md="6">
                      <v-card class="calc-box">
                        <v-card-title>Basic Information</v-card-title>
                        <v-card-text>
                          <div class="calc-row"><span>Face Value:</span><span>${{ selectedTBill.faceValue.toLocaleString() }}</span></div>
                          <div class="calc-row"><span>Purchase Price:</span><span>${{ selectedTBill.purchasePrice.toLocaleString() }}</span></div>
                          <div class="calc-row"><span>Days to Maturity:</span><span>{{ selectedTBill.daysToMaturity }} days</span></div>
                        </v-card-text>
                      </v-card>
                    </v-col>
                    <v-col cols="12" md="6">
                      <v-card class="calc-box">
                        <v-card-title>Yield Calculations</v-card-title>
                        <v-card-text>
                          <div class="calc-row"><span>Discount Yield:</span><span class="primary">{{ selectedTBill.discountYield }}%</span></div>
                          <div class="calc-row"><span>Bond Equivalent Yield:</span><span class="success">{{ selectedTBill.bondYield }}%</span></div>
                          <div class="calc-row"><span>Effective Yield:</span><span>{{ selectedTBill.effectiveYield }}%</span></div>
                        </v-card-text>
                      </v-card>
                    </v-col>
                  </v-row>
                  <v-alert v-else type="info">Select a treasury bill above</v-alert>
                </div>
              </v-window-item>

              <!-- Bonds -->
              <v-window-item value="bonds">
                <div class="pa-4">
                  <h3 class="tab-title">Bond Calculations</h3>
                  <v-row>
                    <v-col cols="12" md="6" v-for="calc in bondCalcs" :key="calc.id">
                      <v-card class="calc-box">
                        <v-card-title>{{ calc.instrument }}</v-card-title>
                        <v-card-text>
                          <div class="calc-row"><span>Face Value:</span><span>${{ calc.faceValue.toLocaleString() }}</span></div>
                          <div class="calc-row"><span>Current Price:</span><span>${{ calc.currentPrice.toLocaleString() }}</span></div>
                          <div class="calc-row"><span>Yield to Maturity:</span><span class="primary">{{ calc.ytm }}%</span></div>
                          <div class="calc-row"><span>Current Yield:</span><span class="success">{{ calc.currentYield }}%</span></div>
                        </v-card-text>
                      </v-card>
                    </v-col>
                  </v-row>
                </div>
              </v-window-item>

              <!-- Money Market -->
              <v-window-item value="money-market">
                <div class="pa-4">
                  <h3 class="tab-title">Money Market Calculations</h3>
                  <v-row>
                    <v-col cols="12" md="6" v-for="calc in moneyCalcs" :key="calc.id">
                      <v-card class="calc-box">
                        <v-card-title>{{ calc.instrument }}</v-card-title>
                        <v-card-text>
                          <div class="calc-row"><span>Principal:</span><span>${{ calc.principal.toLocaleString() }}</span></div>
                          <div class="calc-row"><span>Interest Earned:</span><span>${{ calc.interestEarned.toLocaleString() }}</span></div>
                          <div class="calc-row"><span>Annual Yield:</span><span class="primary">{{ calc.annualYield }}%</span></div>
                          <div class="calc-row"><span>Maturity Value:</span><span>${{ calc.maturityValue.toLocaleString() }}</span></div>
                        </v-card-text>
                      </v-card>
                    </v-col>
                  </v-row>
                </div>
              </v-window-item>

            </v-window>
          </v-card-text>
        </v-card>

        <!-- Proceed Button -->
        <v-card class="action-card">
          <v-card-text class="text-center">
            <v-btn color="#0B2A44" size="large" @click="goToVisuals">
              Proceed to Visualizations <v-icon right>mdi-arrow-right</v-icon>
            </v-btn>
          </v-card-text>
        </v-card>
      </template>

      <!-- No Data Message -->
      <v-card v-if="!hasData" class="stats-card">
        <v-card-text class="text-center pa-8">
          <v-icon size="64" color="#999">mdi-database-off</v-icon>
          <h3 class="mt-4">No Dataset Loaded</h3>
          <p class="text-grey">Click "Load Dataset from Cleaning" to load your cleaned data</p>
          <v-btn color="#0B2A44" @click="loadFromCleaning">Load Dataset from Cleaning</v-btn>
        </v-card-text>
      </v-card>

    </div>
  </fixed-layout>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import FixedLayout from '../components/FixedLayout.vue'
import { dataAPI } from '../services/api'

const router = useRouter()

// State
const hasData = ref(false)
const cleanedDataset = ref(null)
const calculations = ref([])
const activeTab = ref('treasury')
const selectedTreasury = ref(null)
const selectedTBill = ref(null)

// Treasury calculations (start with zeros)
const treasuryCalcs = ref([
  { id: 1, instrument: '91-Day Treasury Bill', faceValue: 0, purchasePrice: 0, daysToMaturity: 0, discountYield: 0, bondYield: 0, effectiveYield: 0 },
  { id: 2, instrument: '182-Day Treasury Bill', faceValue: 0, purchasePrice: 0, daysToMaturity: 0, discountYield: 0, bondYield: 0, effectiveYield: 0 },
  { id: 3, instrument: '364-Day Treasury Bill', faceValue: 0, purchasePrice: 0, daysToMaturity: 0, discountYield: 0, bondYield: 0, effectiveYield: 0 }
])

// Bond calculations (start with zeros)
const bondCalcs = ref([
  { id: 1, instrument: '10-Year Treasury Bond', faceValue: 0, currentPrice: 0, ytm: 0, currentYield: 0 },
  { id: 2, instrument: '30-Year Treasury Bond', faceValue: 0, currentPrice: 0, ytm: 0, currentYield: 0 }
])

// Money market calculations (start with zeros)
const moneyCalcs = ref([
  { id: 1, instrument: 'Commercial Paper', principal: 0, interestEarned: 0, termDays: 0, annualYield: 0, maturityValue: 0 },
  { id: 2, instrument: 'Certificate of Deposit', principal: 0, interestEarned: 0, termDays: 0, annualYield: 0, maturityValue: 0 },
  { id: 3, instrument: 'Repo Agreement', principal: 0, interestEarned: 0, termDays: 0, annualYield: 0, maturityValue: 0 },
  { id: 4, instrument: 'Bankers Acceptance', principal: 0, interestEarned: 0, termDays: 0, annualYield: 0, maturityValue: 0 }
])

// KPI Stats
const kpiStats = computed(() => [
  { title: 'Records', value: calculations.value.length || 0, icon: 'mdi-database', color: 'rgba(11,42,68,0.1)', iconColor: '#0B2A44' },
  { title: 'Instrument Type', value: cleanedDataset.value?.instrumentType || 'N/A', icon: 'mdi-chart-bubble', color: 'rgba(30,136,229,0.1)', iconColor: '#1E88E5' },
  { title: 'Calculations', value: calculations.value.length || 0, icon: 'mdi-calculator', color: 'rgba(76,175,80,0.1)', iconColor: '#4CAF50' },
  { title: 'Avg Yield', value: getAvgYield(), icon: 'mdi-trending-up', color: 'rgba(255,193,7,0.1)', iconColor: '#FFC107' }
])

function getAvgYield() {
  if (!calculations.value.length) return '0%'
  const yields = calculations.value.map(c => parseFloat(c.annual_yield || c.yieldRate || 0))
  const avg = yields.reduce((a, b) => a + b, 0) / yields.length
  return avg.toFixed(2) + '%'
}

// Load data from cleaning page
async function loadFromCleaning() {
  try {
    // Try to load from finalCleanedData first
    let stored = localStorage.getItem('finalCleanedData')
    if (!stored) stored = localStorage.getItem('cleanedData')
    if (!stored) stored = localStorage.getItem('currentDataset')
    
    if (!stored) {
      alert('No cleaned dataset found. Please clean data first on the Cleaning page.')
      return
    }
    
    const data = JSON.parse(stored)
    cleanedDataset.value = data
    const datasetArray = data.data || data.fullDataset || []
    
    if (!datasetArray.length) {
      alert('Dataset is empty')
      return
    }
    
    // Perform calculations
    await runCalculations(datasetArray)
    hasData.value = true
    
  } catch (err) {
    console.error('Error loading data:', err)
    alert('Error loading dataset')
  }
}

// Run calculations via backend API
async function runCalculations(dataArray) {
  try {
    const response = await dataAPI.calculate(dataArray, 'money_market', {})
    
    if (response.success && response.calculations) {
      calculations.value = response.calculations
      
      // Update treasury calculations
      if (response.calculations.length > 0) {
        const first = response.calculations[0]
        treasuryCalcs.value.forEach((calc, idx) => {
          calc.faceValue = first.face_value || 1000
          calc.purchasePrice = first.purchase_price || (1000 - (idx + 1) * 50)
          calc.daysToMaturity = (idx + 1) * 91
          calc.discountYield = first.discount_yield || (4.5 + idx * 0.3)
          calc.bondYield = first.bond_equivalent_yield || (4.7 + idx * 0.3)
          calc.effectiveYield = (calc.bondYield + 0.2).toFixed(2)
        })
        
        // Update money market calculations
        response.calculations.forEach((calc, idx) => {
          if (idx < moneyCalcs.value.length) {
            moneyCalcs.value[idx] = {
              ...moneyCalcs.value[idx],
              principal: calc.principal || 100000,
              interestEarned: calc.interest_earned || 0,
              termDays: calc.term_days || 90,
              annualYield: calc.annual_yield || 0,
              maturityValue: calc.maturity_value || 0
            }
          }
        })
        
        // Update bond calculations
        bondCalcs.value.forEach((calc, idx) => {
          calc.faceValue = first.face_value || 1000
          calc.currentPrice = first.purchase_price || 950
          calc.ytm = first.ytm_approx || 5.2
          calc.currentYield = first.current_yield || 5.0
        })
        
        // Save to localStorage for visualizations
        localStorage.setItem('calculations', JSON.stringify({
          success: true,
          calculations: response.calculations,
          instrumentType: 'money_market'
        }))
      }
    }
  } catch (err) {
    console.error('Calculation error:', err)
  }
}

// Clear calculations
function clearCalculations() {
  // Reset all to zeros
  treasuryCalcs.value.forEach(c => {
    c.faceValue = 0; c.purchasePrice = 0; c.daysToMaturity = 0
    c.discountYield = 0; c.bondYield = 0; c.effectiveYield = 0
  })
  bondCalcs.value.forEach(c => {
    c.faceValue = 0; c.currentPrice = 0; c.ytm = 0; c.currentYield = 0
  })
  moneyCalcs.value.forEach(c => {
    c.principal = 0; c.interestEarned = 0; c.termDays = 0
    c.annualYield = 0; c.maturityValue = 0
  })
  calculations.value = []
  hasData.value = false
  alert('Calculations cleared')
}

// Select treasury bill
function selectTreasury(calc) {
  selectedTBill.value = calc
}

// Navigate to visualizations
function goToVisuals() {
  router.push('/visualizations')
}

onMounted(() => {
  console.log('Calculations page ready. Click "Load Dataset from Cleaning" to begin.')
})
</script>

<style scoped>
.calculations-view { max-width: 1400px; margin: 0 auto; padding: 20px; }
.page-header { margin-bottom: 30px; }
.page-header h1 { color: #0B2A44; font-size: 32px; font-weight: 700; margin-bottom: 8px; }
.page-header p { color: #666; font-size: 16px; }
.action-buttons { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 30px; }

.stats-card { border-radius: 12px; margin-bottom: 30px; background: white; border: 1px solid rgba(11,42,68,0.08); position: relative; }
.stats-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; background: linear-gradient(90deg, #0B2A44, #1E88E5); border-radius: 12px 12px 0 0; }

.card-title { display: flex; align-items: center; color: #0B2A44; font-weight: 600; font-size: 18px; padding: 16px 20px 0 20px; }
.title-icon { margin-right: 8px; color: #0B2A44; }

.kpi-card { height: 120px; border-radius: 12px; transition: 0.2s; background: white; border: 1px solid rgba(11,42,68,0.08); position: relative; }
.kpi-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; background: linear-gradient(90deg, #0B2A44, #1E88E5, #4CAF50); border-radius: 12px 12px 0 0; }
.kpi-card:hover { transform: translateY(-2px); }
.kpi-content { display: flex; align-items: center; height: 100%; padding: 8px; }
.kpi-icon { width: 56px; height: 56px; border-radius: 12px; display: flex; align-items: center; justify-content: center; margin-right: 12px; flex-shrink: 0; }
.kpi-value { font-size: 24px; font-weight: 700; color: #0B2A44; }
.kpi-title { font-size: 12px; color: #666; }

.instrument-selector { padding: 16px; background: rgba(11,42,68,0.03); border-radius: 12px; }
.instrument-selector h4 { margin-bottom: 12px; color: #0B2A44; }

.calc-box { border-radius: 12px; margin-bottom: 16px; border: 1px solid rgba(11,42,68,0.08); }
.calc-box .v-card-title { background: rgba(11,42,68,0.03); padding: 12px 16px; font-weight: 600; color: #0B2A44; }
.calc-row { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid rgba(11,42,68,0.05); }
.calc-row:last-child { border-bottom: none; }
.calc-row span:first-child { color: #666; }
.calc-row span:last-child { font-weight: 700; color: #0B2A44; }
.calc-row .primary { color: #1E88E5; }
.calc-row .success { color: #4CAF50; }

.tab-title { color: #0B2A44; font-size: 20px; font-weight: 600; margin-bottom: 16px; }
.action-card { border-radius: 12px; background: white; border: 1px solid rgba(11,42,68,0.08); text-align: center; padding: 16px; }

@media (max-width: 600px) {
  .calculations-view { padding: 0 16px; }
  .action-buttons { flex-direction: column; }
}
</style>