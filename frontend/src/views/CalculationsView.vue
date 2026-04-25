<template>
  <fixed-layout>
    <div class="calculations-view">
      <!-- Header Section -->
      <div class="dashboard-header">
        <h1 class="page-title">Financial Calculations</h1>
        <p class="page-subtitle">Calculate yields, discount rates, and other financial metrics</p>
      </div>

      <!-- ACTION BUTTONS -->
      <div class="action-buttons">
        <v-btn color="primary" @click="loadSampleData">
          <v-icon left>mdi-database</v-icon>
          Load Sample Data
        </v-btn>

        <v-btn color="secondary" variant="outlined" @click="clearCalculations">
          <v-icon left>mdi-delete</v-icon>
          Clear Results
        </v-btn>

        <v-btn color="success" variant="outlined" @click="exportResults">
          <v-icon left>mdi-download</v-icon>
          Export Results
        </v-btn>
      </div>

      <!-- DATA OVERVIEW -->
      <v-card class="stats-card" elevation="2">
        <v-card-title class="card-title">
          <v-icon class="title-icon">mdi-calculator</v-icon>
          Dataset Overview
        </v-card-title>

        <v-card-text>
          <v-row class="kpi-row">
            <v-col cols="12" sm="6" md="3" v-for="kpi in calculationsKpiData" :key="kpi.title">
              <v-card class="kpi-card" elevation="2">
                <v-card-text>
                  <div class="kpi-content">
                    <div class="kpi-icon" :style="{ backgroundColor: kpi.color }">
                      <v-icon :color="kpi.iconColor">{{ kpi.icon }}</v-icon>
                    </div>
                    <div class="kpi-info">
                      <div class="kpi-value">{{ kpi.value }}</div>
                      <div class="kpi-title">{{ kpi.title }}</div>
                      <div class="kpi-change" :class="kpi.changeClass">
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

      <!-- AUTOMATIC CALCULATIONS -->
      <v-card class="chart-card" elevation="2">
        <v-card-title class="card-title">
          <v-icon class="title-icon">mdi-finance</v-icon>
          Automated Financial Calculations
        </v-card-title>

        <v-card-text>
          <v-alert type="info" variant="tonal" class="mb-4">
            <v-icon left>mdi-database</v-icon>
            Calculations are automatically performed using backend algorithms and yield curve analysis
          </v-alert>

          <v-tabs v-model="activeTab" color="primary">
            <v-tab value="treasury">Treasury Bills</v-tab>
            <v-tab value="bonds">Bonds</v-tab>
            <v-tab value="money-market">Money Market</v-tab>
          </v-tabs>

          <v-window v-model="activeTab">

            <!-- TREASURY BILLS -->
            <v-window-item value="treasury">
              <div class="calculation-results">
                <h3 class="tab-title">Treasury Bill Calculations</h3>
                <p class="tab-desc">
                  Select a financial instrument to view detailed calculations
                </p>

                <!-- Instrument Selection -->
                <v-row class="mb-4">
                  <v-col cols="12">
                    <div class="instrument-selector">
                      <h4 class="selector-title">Select Treasury Bill:</h4>
                      <v-chip-group v-model="selectedTreasury" mandatory>
                        <v-chip
                          v-for="calc in treasuryCalculations"
                          :key="calc.id"
                          :value="calc.id"
                          color="primary"
                          variant="outlined"
                          class="instrument-chip"
                          @click="selectTreasuryBill(calc)"
                        >
                          <v-icon left>mdi-chart-line</v-icon>
                          {{ calc.instrument }}
                        </v-chip>
                      </v-chip-group>
                    </div>
                  </v-col>
                </v-row>

                <!-- Calculation Display Boxes -->
                <v-row v-if="selectedTreasuryBill" class="calculation-boxes">
                  <v-col cols="12" md="6">
                    <v-card class="calc-box" elevation="2">
                      <v-card-title class="calc-box-title">
                        <v-icon class="mr-2" color="primary">mdi-currency-usd</v-icon>
                        Basic Information
                      </v-card-title>
                      <v-card-text>
                        <div class="calc-row">
                          <div class="calc-label">Face Value:</div>
                          <div class="calc-value">${{ selectedTreasuryBill.faceValue.toLocaleString() }}</div>
                        </div>
                        <div class="calc-row">
                          <div class="calc-label">Purchase Price:</div>
                          <div class="calc-value">${{ selectedTreasuryBill.purchasePrice.toLocaleString() }}</div>
                        </div>
                        <div class="calc-row">
                          <div class="calc-label">Days to Maturity:</div>
                          <div class="calc-value">{{ selectedTreasuryBill.daysToMaturity }} days</div>
                        </div>
                        <div class="calc-row">
                          <div class="calc-label">Discount Amount:</div>
                          <div class="calc-value">${{ (selectedTreasuryBill.faceValue - selectedTreasuryBill.purchasePrice).toLocaleString() }}</div>
                        </div>
                      </v-card-text>
                    </v-card>
                  </v-col>

                  <v-col cols="12" md="6">
                    <v-card class="calc-box" elevation="2">
                      <v-card-title class="calc-box-title">
                        <v-icon class="mr-2" color="success">mdi-chart-line</v-icon>
                        Yield Calculations
                      </v-card-title>
                      <v-card-text>
                        <div class="calc-row">
                          <div class="calc-label">Discount Yield:</div>
                          <div class="calc-value primary">{{ selectedTreasuryBill.discountYield }}%</div>
                        </div>
                        <div class="calc-row">
                          <div class="calc-label">Bond Equivalent Yield:</div>
                          <div class="calc-value success">{{ selectedTreasuryBill.bondEquivalentYield }}%</div>
                        </div>
                        <div class="calc-row">
                          <div class="calc-label">Money Market Yield:</div>
                          <div class="calc-value">{{ calculateMoneyMarketYield(selectedTreasuryBill).toFixed(2) }}%</div>
                        </div>
                        <div class="calc-row">
                          <div class="calc-label">Effective Annual Yield:</div>
                          <div class="calc-value">{{ calculateEffectiveYield(selectedTreasuryBill).toFixed(2) }}%</div>
                        </div>
                      </v-card-text>
                    </v-card>
                  </v-col>

                  <v-col cols="12" md="6">
                    <v-card class="calc-box" elevation="2">
                      <v-card-title class="calc-box-title">
                        <v-icon class="mr-2" color="info">mdi-calculator</v-icon>
                        Price Calculations
                      </v-card-title>
                      <v-card-text>
                        <div class="calc-row">
                          <div class="calc-label">Price per $100:</div>
                          <div class="calc-value">${{ (selectedTreasuryBill.purchasePrice / selectedTreasuryBill.faceValue * 100).toFixed(4) }}</div>
                        </div>
                        <div class="calc-row">
                          <div class="calc-label">Price as % of Par:</div>
                          <div class="calc-value">{{ ((selectedTreasuryBill.purchasePrice / selectedTreasuryBill.faceValue) * 100).toFixed(2) }}%</div>
                        </div>
                        <div class="calc-row">
                          <div class="calc-label">Dollar Discount:</div>
                          <div class="calc-value">${{ (selectedTreasuryBill.faceValue - selectedTreasuryBill.purchasePrice).toFixed(2) }}</div>
                        </div>
                        <div class="calc-row">
                          <div class="calc-label">Bank Discount Rate:</div>
                          <div class="calc-value">{{ calculateBankDiscount(selectedTreasuryBill).toFixed(4) }}%</div>
                        </div>
                      </v-card-text>
                    </v-card>
                  </v-col>

                  <v-col cols="12" md="6">
                    <v-card class="calc-box" elevation="2">
                      <v-card-title class="calc-box-title">
                        <v-icon class="mr-2" color="warning">mdi-trending-up</v-icon>
                        Yield Curve Analysis
                      </v-card-title>
                      <v-card-text>
                        <div class="calc-row">
                          <div class="calc-label">Yield Curve Assisted:</div>
                          <div class="calc-value">
                            <v-chip size="small" color="success">Yes</v-chip>
                          </div>
                        </div>
                        <div class="calc-row">
                          <div class="calc-label">Spot Rate:</div>
                          <div class="calc-value">{{ calculateSpotRate(selectedTreasuryBill).toFixed(2) }}%</div>
                        </div>
                        <div class="calc-row">
                          <div class="calc-label">Forward Rate:</div>
                          <div class="calc-value">{{ calculateForwardRate(selectedTreasuryBill).toFixed(2) }}%</div>
                        </div>
                        <div class="calc-row">
                          <div class="calc-label">Yield Premium:</div>
                          <div class="calc-value">{{ calculateYieldPremium(selectedTreasuryBill).toFixed(2) }}%</div>
                        </div>
                      </v-card-text>
                    </v-card>
                  </v-col>
                </v-row>

                <!-- Empty State -->
                <v-alert v-if="!selectedTreasuryBill" type="info" variant="tonal">
                  <v-icon left>mdi-information</v-icon>
                  Please select a treasury bill from the options above to view detailed calculations
                </v-alert>
              </div>
            </v-window-item>

            <!-- BONDS -->
            <v-window-item value="bonds">
              <div class="calculation-results">
                <h3 class="tab-title">Bond Calculations</h3>
                <p class="tab-desc">
                  Automated yield calculations with yield curve integration
                </p>

                <v-row class="mt-4">
                  <v-col cols="12" md="6" v-for="calc in bondCalculations" :key="calc.id">
                    <v-card class="calculation-card" outlined>
                      <v-card-title class="calc-title">
                        <v-icon class="mr-2" color="primary">mdi-bank</v-icon>
                        {{ calc.instrument }}
                      </v-card-title>
                      <v-card-text>
                        <v-row>
                          <v-col cols="6">
                            <div class="calc-item">
                              <div class="calc-label">Face Value</div>
                              <div class="calc-value">${{ calc.faceValue.toLocaleString() }}</div>
                            </div>
                            <div class="calc-item">
                              <div class="calc-label">Current Price</div>
                              <div class="calc-value">${{ calc.currentPrice.toLocaleString() }}</div>
                            </div>
                            <div class="calc-item">
                              <div class="calc-label">Coupon Rate</div>
                              <div class="calc-value">{{ calc.couponRate }}%</div>
                            </div>
                          </v-col>
                          <v-col cols="6">
                            <div class="calc-item">
                              <div class="calc-label">Yield to Maturity</div>
                              <div class="calc-value primary">{{ calc.yieldToMaturity }}%</div>
                            </div>
                            <div class="calc-item">
                              <div class="calc-label">Current Yield</div>
                              <div class="calc-value success">{{ calc.currentYield }}%</div>
                            </div>
                            <div class="calc-item">
                              <div class="calc-label">Duration</div>
                              <div class="calc-value">{{ calc.duration }} years</div>
                            </div>
                          </v-col>
                        </v-row>
                      </v-card-text>
                    </v-card>
                  </v-col>
                </v-row>
              </div>
            </v-window-item>

            <!-- MONEY MARKET -->
            <v-window-item value="money-market">
              <div class="calculation-results">
                <h3 class="tab-title">Money Market Calculations</h3>
                <p class="tab-desc">
                  Automated money market instrument calculations
                </p>

                <v-row class="mt-4">
                  <v-col cols="12" md="6" v-for="calc in moneyMarketCalculations" :key="calc.id">
                    <v-card class="calculation-card" outlined>
                      <v-card-title class="calc-title">
                        <v-icon class="mr-2" color="primary">mdi-cash</v-icon>
                        {{ calc.instrument }}
                      </v-card-title>
                      <v-card-text>
                        <v-row>
                          <v-col cols="6">
                            <div class="calc-item">
                              <div class="calc-label">Principal</div>
                              <div class="calc-value">${{ calc.principal.toLocaleString() }}</div>
                            </div>
                            <div class="calc-item">
                              <div class="calc-label">Interest Earned</div>
                              <div class="calc-value">${{ calc.interestEarned.toLocaleString() }}</div>
                            </div>
                            <div class="calc-item">
                              <div class="calc-label">Term Days</div>
                              <div class="calc-value">{{ calc.termDays }}</div>
                            </div>
                          </v-col>
                          <v-col cols="6">
                            <div class="calc-item">
                              <div class="calc-label">Annual Yield</div>
                              <div class="calc-value primary">{{ calc.annualYield }}%</div>
                            </div>
                            <div class="calc-item">
                              <div class="calc-label">Effective Rate</div>
                              <div class="calc-value success">{{ calc.effectiveRate }}%</div>
                            </div>
                            <div class="calc-item">
                              <div class="calc-label">Maturity Value</div>
                              <div class="calc-value">${{ calc.maturityValue.toLocaleString() }}</div>
                            </div>
                          </v-col>
                        </v-row>
                      </v-card-text>
                    </v-card>
                  </v-col>
                </v-row>
              </div>
            </v-window-item>

          </v-window>
        </v-card-text>
      </v-card>

      <!-- EMPTY STATE -->
      <v-alert v-if="calculations.length === 0" type="info">
        No calculations yet.
      </v-alert>

      <!-- RESULTS -->
      <v-card v-if="calculations.length > 0" class="results-card">

        <v-data-table
          :headers="getTableHeaders()"
          :items="calculations"
        />

        <div class="result-actions">
          <v-btn color="primary" @click="proceedToVisualizations">
            Visualize
          </v-btn>

          <v-btn @click="clearCalculations">
            Close
          </v-btn>
        </div>

      </v-card>

    </div>
  </fixed-layout>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import FixedLayout from '../components/FixedLayout.vue'

const router = useRouter()

const calculations = ref([])
const calculating = ref(false)
const cleanedData = ref(null)
const activeTab = ref('treasury')
const selectedTreasury = ref(null)
const selectedTreasuryBill = ref(null)

const recordsValue = computed(() => 0)
const instrumentTypeValue = computed(() => 'None')
const calculationsCountValue = computed(() => calculations.value.length)
const avgYieldValue = computed(() => getAverageYield() + '%')

const calculationsKpiData = ref([
  {
    title: 'Records',
    value: recordsValue,
    icon: 'mdi-database',
    color: 'rgba(11, 42, 68, 0.1)',
    iconColor: '#0B2A44',
    change: '0%',
    changeIcon: 'mdi-minus',
    changeClass: 'neutral'
  },
  {
    title: 'Instrument Type',
    value: instrumentTypeValue,
    icon: 'mdi-chart-bubble',
    color: 'rgba(30, 136, 229, 0.1)',
    iconColor: '#1E88E5',
    change: '0%',
    changeIcon: 'mdi-minus',
    changeClass: 'neutral'
  },
  {
    title: 'Calculations',
    value: calculationsCountValue,
    icon: 'mdi-calculator',
    color: 'rgba(76, 175, 80, 0.1)',
    iconColor: '#4CAF50',
    change: '0%',
    changeIcon: 'mdi-minus',
    changeClass: 'neutral'
  },
  {
    title: 'Avg Yield',
    value: avgYieldValue,
    icon: 'mdi-trending-up',
    color: 'rgba(255, 193, 7, 0.1)',
    iconColor: '#FFC107',
    change: '0%',
    changeIcon: 'mdi-minus',
    changeClass: 'neutral'
  }
])

// Auto-calculated treasury bill data (would come from backend)
const treasuryCalculations = ref([
  {
    id: 1,
    instrument: '91-Day Treasury Bill',
    faceValue: 0,
    purchasePrice: 0,
    daysToMaturity: 0,
    discountYield: 0,
    bondEquivalentYield: 0
  },
  {
    id: 2,
    instrument: '182-Day Treasury Bill',
    faceValue: 0,
    purchasePrice: 0,
    daysToMaturity: 0,
    discountYield: 0,
    bondEquivalentYield: 0
  },
  {
    id: 3,
    instrument: '364-Day Treasury Bill',
    faceValue: 0,
    purchasePrice: 0,
    daysToMaturity: 0,
    discountYield: 0,
    bondEquivalentYield: 0
  },
  {
    id: 4,
    instrument: '2-Year Treasury Note',
    faceValue: 0,
    purchasePrice: 0,
    daysToMaturity: 0,
    discountYield: 0,
    bondEquivalentYield: 0
  }
])

// Auto-calculated bond data (would come from backend)
const bondCalculations = ref([
  {
    id: 1,
    instrument: '10-Year Treasury Bond',
    faceValue: 0,
    currentPrice: 0,
    couponRate: 0,
    yieldToMaturity: 0,
    currentYield: 0,
    duration: 0
  },
  {
    id: 2,
    instrument: '30-Year Treasury Bond',
    faceValue: 0,
    currentPrice: 0,
    couponRate: 0,
    yieldToMaturity: 0,
    currentYield: 0,
    duration: 0
  },
  {
    id: 3,
    instrument: 'Corporate Bond AAA',
    faceValue: 0,
    currentPrice: 0,
    couponRate: 0,
    yieldToMaturity: 0,
    currentYield: 0,
    duration: 0
  },
  {
    id: 4,
    instrument: 'Corporate Bond BBB',
    faceValue: 0,
    currentPrice: 0,
    couponRate: 0,
    yieldToMaturity: 0,
    currentYield: 0,
    duration: 0
  }
])

// Auto-calculated money market data (would come from backend)
const moneyMarketCalculations = ref([
  {
    id: 1,
    instrument: 'Commercial Paper',
    principal: 0,
    interestEarned: 0,
    termDays: 0,
    annualYield: 0,
    effectiveRate: 0,
    maturityValue: 0
  },
  {
    id: 2,
    instrument: 'Certificate of Deposit',
    principal: 0,
    interestEarned: 0,
    termDays: 0,
    annualYield: 0,
    effectiveRate: 0,
    maturityValue: 0
  },
  {
    id: 3,
    instrument: 'Repo Agreement',
    principal: 0,
    interestEarned: 0,
    termDays: 0,
    annualYield: 0,
    effectiveRate: 0,
    maturityValue: 0
  },
  {
    id: 4,
    instrument: 'Bankers Acceptance',
    principal: 0,
    interestEarned: 0,
    termDays: 0,
    annualYield: 0,
    effectiveRate: 0,
    maturityValue: 0
  }
])

const loadSampleData = () => {
  calculations.value = [{ id:1, yieldRate:'5.2%' }]
}

const clearCalculations = () => {
  calculations.value = []
}

const exportResults = () => {
  const blob = new Blob([JSON.stringify(calculations.value)], { type:'application/json'})
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = 'results.json'
  a.click()
}

const getAverageYield = () => {
  if (calculations.value.length === 0) return '0.0'
  const yields = calculations.value.map(calc => parseFloat((calc as any).yieldRate?.replace('%', '') || '0'))
  const avg = yields.reduce((sum, yieldRate) => sum + yieldRate, 0) / yields.length
  return avg.toFixed(1)
}

// Selection and calculation functions
const selectTreasuryBill = (treasury) => {
  selectedTreasuryBill.value = treasury
}

// Treasury bill calculation functions (returning zeros - backend only)
const calculateMoneyMarketYield = (treasury) => {
  // Would calculate Money Market Yield from backend data
  return 0
}

const calculateEffectiveYield = (treasury) => {
  // Would calculate Effective Annual Yield from backend data
  return 0
}

const calculateBankDiscount = (treasury) => {
  // Would calculate Bank Discount Rate from backend data
  return 0
}

const calculateSpotRate = (treasury) => {
  // Would calculate Spot Rate using yield curve data from backend
  return 0
}

const calculateForwardRate = (treasury) => {
  // Would calculate Forward Rate using yield curve data from backend
  return 0
}

const calculateYieldPremium = (treasury) => {
  // Would calculate Yield Premium from backend data
  return 0
}

const getTableHeaders = () => {
  if (!calculations.value.length) return []
  return Object.keys(calculations.value[0]).map(k => ({ title:k, key:k }))
}

const proceedToVisualizations = () => {
  router.push('/visualizations')
}
</script>

<style scoped>
.calculations-view { 
  max-width: 1400px; 
  margin: 0 auto; 
}

.dashboard-header {
  margin-bottom: 32px;
}

.page-title {
  color: #0B2A44;
  font-size: 32px;
  font-weight: 700;
  margin-bottom: 8px;
}

.page-subtitle {
  color: #666;
  font-size: 16px;
  margin: 0;
}

.action-buttons { 
  display: flex; 
  gap: 12px; 
  margin-bottom: 32px; 
}

.stats-card {
  border-radius: 12px;
  margin-bottom: 32px;
  background: white;
  border: 1px solid rgba(11, 42, 68, 0.08);
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
}

.chart-card {
  border-radius: 12px;
  margin-bottom: 32px;
  background: white;
  border: 1px solid rgba(11, 42, 68, 0.08);
  position: relative;
}

.chart-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, #0B2A44, #1E88E5);
}

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

.result-actions { 
  display: flex; 
  justify-content: space-between; 
  margin-top: 20px; 
}

.stat-item {
  text-align: center;
  padding: 16px;
  background: rgba(11, 42, 68, 0.03);
  border-radius: 8px;
  transition: transform 0.2s ease;
}

.stat-item:hover {
  transform: translateY(-2px);
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: #0B2A44;
  margin-bottom: 4px;
}

.stat-label {
  font-size: 14px;
  color: #666;
  font-weight: 500;
}

/* KPI Styles - Matching DashboardView and ReportsView */
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
  width: 60px;
  height: 60px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 16px;
}

.kpi-info {
  flex: 1;
}

.kpi-value {
  font-size: 28px;
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

/* Calculation Results Styles */
.calculation-results {
  padding: 16px 0;
}

.calculation-card {
  border-radius: 12px;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  border: 1px solid rgba(11, 42, 68, 0.08);
}

.calculation-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
}

.calc-title {
  font-size: 16px;
  font-weight: 600;
  color: #0B2A44;
  background: rgba(11, 42, 68, 0.03);
  border-bottom: 1px solid rgba(11, 42, 68, 0.08);
}

.calc-item {
  margin-bottom: 16px;
  padding: 12px;
  background: rgba(11, 42, 68, 0.02);
  border-radius: 8px;
  transition: background-color 0.2s ease;
}

.calc-item:hover {
  background: rgba(11, 42, 68, 0.05);
}

.calc-label {
  font-size: 12px;
  color: #666;
  font-weight: 500;
  margin-bottom: 4px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.calc-value {
  font-size: 18px;
  font-weight: 700;
  color: #0B2A44;
}

.calc-value.primary {
  color: #1E88E5;
}

.calc-value.success {
  color: #4CAF50;
}

.tab-title {
  color: #0B2A44;
  font-size: 20px;
  font-weight: 600;
  margin-bottom: 8px;
}

.tab-desc {
  color: #666;
  font-size: 14px;
  margin-bottom: 16px;
}

/* Instrument Selector Styles */
.instrument-selector {
  padding: 16px;
  background: rgba(11, 42, 68, 0.02);
  border-radius: 12px;
  border: 1px solid rgba(11, 42, 68, 0.08);
}

.selector-title {
  color: #0B2A44;
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 12px;
}

.instrument-chip {
  margin: 4px;
  transition: all 0.2s ease;
}

.instrument-chip:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

/* Calculation Boxes Styles */
.calculation-boxes {
  margin-top: 24px;
}

.calc-box {
  border-radius: 12px;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  border: 1px solid rgba(11, 42, 68, 0.08);
  height: 100%;
}

.calc-box:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
}

.calc-box-title {
  font-size: 16px;
  font-weight: 600;
  color: #0B2A44;
  background: rgba(11, 42, 68, 0.03);
  border-bottom: 1px solid rgba(11, 42, 68, 0.08);
}

.calc-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid rgba(11, 42, 68, 0.05);
}

.calc-row:last-child {
  border-bottom: none;
}

.calc-label {
  font-size: 14px;
  color: #666;
  font-weight: 500;
}

.calc-value {
  font-size: 16px;
  font-weight: 700;
  color: #0B2A44;
}

.calc-value.primary {
  color: #1E88E5;
}

.calc-value.success {
  color: #4CAF50;
}
</style>
```
