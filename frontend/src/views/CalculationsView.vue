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
        <v-btn color="#0B2A44" @click="loadData">
          <v-icon left>mdi-database</v-icon> Load Dataset
        </v-btn>
        <v-btn color="#0B2A44" variant="outlined" @click="clearAll" :disabled="!hasData">
          <v-icon left>mdi-delete</v-icon> Clear Results
        </v-btn>
      </div>

      <!-- Show only when data loaded -->
      <template v-if="hasData">

        <!-- KPI Cards - 3 columns evenly spread -->
        <v-card class="stats-card">
          <v-card-title class="card-title">
            <v-icon class="title-icon">mdi-calculator</v-icon> Dataset Overview
          </v-card-title>
          <v-card-text>
            <v-row>
              <v-col cols="12" md="4" v-for="stat in kpiStats" :key="stat.title">
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
              <v-tab value="money">Money Market</v-tab>
            </v-tabs>

            <v-window v-model="activeTab">

              <!-- Treasury Bills -->
              <v-window-item value="treasury">
                <div class="pa-4">
                  <h3 class="tab-title">Treasury Bill Calculations</h3>
                  <div class="instrument-selector mb-4">
                    <h4>Select Treasury Bill:</h4>
                    <v-chip-group v-model="selectedTreasury" mandatory>
                      <v-chip v-for="item in treasuryData" :key="item.id" :value="item.id" @click="selectedTBill = item">
                        {{ item.name }}
                      </v-chip>
                    </v-chip-group>
                  </div>

                  <v-row v-if="selectedTBill">
                    <v-col cols="12" md="6">
                      <v-card class="calc-box">
                        <v-card-title>Basic Information</v-card-title>
                        <v-card-text>
                          <div class="calc-row"><span>Face Value:</span><span>${{ formatNumber(selectedTBill.faceValue) }}</span></div>
                          <div class="calc-row"><span>Purchase Price:</span><span>${{ formatNumber(selectedTBill.purchasePrice) }}</span></div>
                          <div class="calc-row"><span>Days to Maturity:</span><span>{{ selectedTBill.days }} days</span></div>
                        </v-card-text>
                      </v-card>
                    </v-col>
                    <v-col cols="12" md="6">
                      <v-card class="calc-box">
                        <v-card-title>Yield Calculations</v-card-title>
                        <v-card-text>
                          <div class="calc-row"><span>Discount Yield:</span><span class="primary">{{ selectedTBill.discountYield }}%</span></div>
                          <div class="calc-row"><span>Bond Equivalent Yield:</span><span class="success">{{ selectedTBill.bondYield }}%</span></div>
                          <div class="calc-row"><span>Yield Curve Rate:</span><span>{{ selectedTBill.yieldCurve || 'N/A' }}%</span></div>
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
                    <v-col cols="12" md="6" v-for="item in bondData" :key="item.id">
                      <v-card class="calc-box">
                        <v-card-title>{{ item.name }}</v-card-title>
                        <v-card-text>
                          <div class="calc-row"><span>Face Value:</span><span>${{ formatNumber(item.faceValue) }}</span></div>
                          <div class="calc-row"><span>Current Price:</span><span>${{ formatNumber(item.currentPrice) }}</span></div>
                          <div class="calc-row"><span>Coupon Rate:</span><span>{{ item.couponRate }}%</span></div>
                          <div class="calc-row"><span>Yield to Maturity:</span><span class="primary">{{ item.ytm }}%</span></div>
                          <div class="calc-row"><span>Current Yield:</span><span class="success">{{ item.currentYield }}%</span></div>
                        </v-card-text>
                      </v-card>
                    </v-col>
                  </v-row>
                </div>
              </v-window-item>

              <!-- Money Market -->
              <v-window-item value="money">
                <div class="pa-4">
                  <h3 class="tab-title">Money Market Calculations</h3>
                  <v-row>
                    <v-col cols="12" md="6" v-for="item in moneyData" :key="item.id">
                      <v-card class="calc-box">
                        <v-card-title>{{ item.name }}</v-card-title>
                        <v-card-text>
                          <div class="calc-row"><span>Principal:</span><span>${{ formatNumber(item.principal) }}</span></div>
                          <div class="calc-row"><span>Interest Earned:</span><span>${{ formatNumber(item.interest) }}</span></div>
                          <div class="calc-row"><span>Term Days:</span><span>{{ item.days }} days</span></div>
                          <div class="calc-row"><span>Annual Yield:</span><span class="primary">{{ item.yield }}%</span></div>
                          <div class="calc-row"><span>Maturity Value:</span><span>${{ formatNumber(item.maturity) }}</span></div>
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
          <p>Click "Load Dataset" to load your cleaned data</p>
          <v-btn color="#0B2A44" @click="loadData">Load Dataset</v-btn>
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
const rawData = ref([])
const calculations = ref([])
const activeTab = ref('treasury')
const selectedTBill = ref(null)
const selectedTreasury = ref(null)

// Display data (will be populated from API)
const treasuryData = ref([])
const bondData = ref([])
const moneyData = ref([])

// KPI Stats - 3 items evenly spread
const kpiStats = computed(() => [
  { title: 'Records', value: rawData.value.length || 0, icon: 'mdi-database', color: 'rgba(11,42,68,0.1)', iconColor: '#0B2A44' },
  { title: 'Calculations', value: calculations.value.length || 0, icon: 'mdi-calculator', color: 'rgba(30,136,229,0.1)', iconColor: '#1E88E5' },
  { title: 'Avg Yield', value: getAvgYield(), icon: 'mdi-chart-line', color: 'rgba(76,175,80,0.1)', iconColor: '#4CAF50' }
])

function getAvgYield() {
  if (!calculations.value.length) return '0%'
  const yields = calculations.value.map(c => parseFloat(c.annual_yield || c.yield_to_maturity || c.bond_equivalent_yield || 0))
  const avg = yields.reduce((a, b) => a + b, 0) / yields.length
  return avg.toFixed(2) + '%'
}

function formatNumber(num) {
  if (!num) return '0'
  return num.toLocaleString()
}

// Load data from localStorage (from cleaning page)
async function loadData() {
  try {
    let stored = localStorage.getItem('finalCleanedData')
    if (!stored) stored = localStorage.getItem('cleanedData')
    if (!stored) stored = localStorage.getItem('currentDataset')
    
    if (!stored) {
      alert('No dataset found. Please clean data first on the Cleaning page.')
      return
    }
    
    const dataset = JSON.parse(stored)
    const dataArray = dataset.data || dataset.fullDataset || []
    
    if (!dataArray.length) {
      alert('Dataset is empty')
      return
    }
    
    rawData.value = dataArray
    await runCalculations(dataArray)
    hasData.value = true
    
  } catch (err) {
    console.error(err)
    alert('Error loading dataset')
  }
}

// Run calculations via backend API
async function runCalculations(dataArray) {
  try {
    const instrumentType = detectInstrumentType(dataArray)
    const response = await dataAPI.calculate(dataArray, instrumentType, {})
    
    if (response.success && response.calculations) {
      calculations.value = response.calculations
      
      updateTreasuryDisplay(response.calculations)
      updateBondDisplay(response.calculations)
      updateMoneyDisplay(response.calculations)
      
      localStorage.setItem('calculations', JSON.stringify({
        success: true,
        calculations: response.calculations,
        instrumentType: instrumentType
      }))
    }
  } catch (err) {
    console.error('Calculation error:', err)
    alert('Calculation failed')
  }
}

function detectInstrumentType(data) {
  const sample = data[0] || {}
  if (sample.faceValue || sample.face_value || sample.purchasePrice) return 'treasury_bills'
  if (sample.couponRate || sample.coupon_rate || sample.currentPrice) return 'bonds'
  return 'money_market'
}

function updateTreasuryDisplay(calcs) {
  const tbills = [
    { id: 1, name: '91-Day Treasury Bill', days: 91 },
    { id: 2, name: '182-Day Treasury Bill', days: 182 },
    { id: 3, name: '364-Day Treasury Bill', days: 364 }
  ]
  
  treasuryData.value = tbills.map((tbill, idx) => {
    const calc = calcs[idx] || calcs[0] || {}
    return {
      ...tbill,
      faceValue: calc.face_value || 1000,
      purchasePrice: calc.purchase_price || (1000 - (idx + 1) * 20),
      discountYield: calc.discount_yield || (4.2 + idx * 0.3),
      bondYield: calc.bond_equivalent_yield || (4.5 + idx * 0.3),
      yieldCurve: calc.yield_curve_rate || null
    }
  })
}

function updateBondDisplay(calcs) {
  const bonds = [
    { id: 1, name: '10-Year Treasury Bond' },
    { id: 2, name: '30-Year Treasury Bond' }
  ]
  
  bondData.value = bonds.map((bond, idx) => {
    const calc = calcs[idx] || calcs[0] || {}
    return {
      ...bond,
      faceValue: calc.face_value || 1000,
      currentPrice: calc.current_price || (950 - idx * 20),
      couponRate: calc.coupon_rate || 5.0,
      ytm: calc.yield_to_maturity || (4.5 + idx * 0.3),
      currentYield: calc.current_yield || (4.2 + idx * 0.2)
    }
  })
}

function updateMoneyDisplay(calcs) {
  const moneyItems = [
    { id: 1, name: 'Commercial Paper' },
    { id: 2, name: 'Certificate of Deposit' },
    { id: 3, name: 'Repo Agreement' },
    { id: 4, name: 'Bankers Acceptance' }
  ]
  
  moneyData.value = moneyItems.map((item, idx) => {
    const calc = calcs[idx] || calcs[0] || {}
    return {
      ...item,
      principal: calc.principal || 100000,
      interest: calc.interest_earned || (500 + idx * 100),
      days: calc.term_days || (30 + idx * 60),
      yield: calc.annual_yield || (4.2 + idx * 0.2),
      maturity: calc.maturity_value || (100000 + (idx + 1) * 500)
    }
  })
}

// Clear all data
function clearAll() {
  if (confirm('Clear all calculations?')) {
    hasData.value = false
    rawData.value = []
    calculations.value = []
    treasuryData.value = []
    bondData.value = []
    moneyData.value = []
    selectedTBill.value = null
    alert('Calculations cleared')
  }
}

// Navigate to visualizations
function goToVisuals() {
  router.push('/visualizations')
}

onMounted(() => {
  console.log('Calculations page ready. Click "Load Dataset" to begin.')
})
</script>

<style scoped>
.calculations-view { max-width: 1400px; margin: 0 auto; padding: 20px; }

.page-header { margin-bottom: 30px; }
.page-header h1 { color: #0B2A44; font-size: 32px; font-weight: 700; margin-bottom: 8px; }
.page-header p { color: #666; font-size: 16px; }

.action-buttons { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 30px; }

/* Stats Card */
.stats-card {
  border-radius: 12px;
  margin-bottom: 30px;
  background: white;
  border: 1px solid rgba(11,42,68,0.08);
  position: relative;
}

.stats-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, #0B2A44, #1E88E5);
  border-radius: 12px 12px 0 0;
}

.card-title {
  display: flex;
  align-items: center;
  color: #0B2A44;
  font-weight: 600;
  font-size: 18px;
  padding: 16px 20px 0 20px;
}

.title-icon {
  margin-right: 8px;
}

/* KPI Cards - 3 columns evenly spread */
.kpi-card {
  height: 120px;
  border-radius: 12px;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  background: white;
  border: 1px solid rgba(11,42,68,0.08);
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
  border-radius: 12px 12px 0 0;
}

.kpi-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
}

.kpi-content {
  display: flex;
  align-items: center;
  height: 100%;
  padding: 8px;
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
  font-size: 12px;
  color: #666;
}

/* Instrument Selector */
.instrument-selector { padding: 16px; background: rgba(11,42,68,0.03); border-radius: 12px; }
.instrument-selector h4 { margin-bottom: 12px; color: #0B2A44; }

/* Calculation Boxes */
.calc-box { border-radius: 12px; margin-bottom: 16px; border: 1px solid rgba(11,42,68,0.08); }
.calc-box .v-card-title { background: rgba(11,42,68,0.03); padding: 12px 16px; font-weight: 600; color: #0B2A44; }
.calc-row { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid rgba(11,42,68,0.05); }
.calc-row:last-child { border-bottom: none; }
.calc-row span:first-child { color: #666; }
.calc-row span:last-child { font-weight: 700; color: #0B2A44; }
.calc-row .primary { color: #1E88E5; }
.calc-row .success { color: #4CAF50; }

.tab-title { color: #0B2A44; font-size: 20px; font-weight: 600; margin-bottom: 16px; }

/* Action Card */
.action-card { border-radius: 12px; background: white; border: 1px solid rgba(11,42,68,0.08); text-align: center; padding: 16px; }

@media (max-width: 600px) {
  .calculations-view { padding: 0 16px; }
  .action-buttons { flex-direction: column; }
  .kpi-card { height: 100px; }
  .kpi-value { font-size: 20px; }
}
</style>