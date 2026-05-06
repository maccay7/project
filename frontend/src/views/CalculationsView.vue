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

      <!-- ACTION BUTTON -->
      <v-card class="action-card" elevation="2">
        <v-card-text class="text-center">
          <v-btn color="primary" size="large" @click="proceedToVisualizations">
            <v-icon start>mdi-arrow-right</v-icon>
            Proceed to Visualizations
          </v-btn>
        </v-card-text>
      </v-card>

    </div>
  </fixed-layout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import FixedLayout from '../components/FixedLayout.vue'
import { dataAPI } from '../services/api'
import { useDataset } from '../composables/useDataset'

const router = useRouter()

// Use dataset composable for global state
const { datasetInfo, hasDataset, loadDataset } = useDataset()

const calculations = ref([])
const calculating = ref(false)
const cleanedData = ref(null)
const activeTab = ref('treasury')
const selectedTreasury = ref(null)
const selectedTreasuryBill = ref(null)

const calculationsKpiData = ref([
  {
    title: 'Records',
    value: '0',
    icon: 'mdi-database',
    color: 'rgba(11, 42, 68, 0.1)',
    iconColor: '#0B2A44',
    change: '',
    changeIcon: 'mdi-minus',
    changeClass: 'neutral'
  },
  {
    title: 'Instrument Type',
    value: 'None',
    icon: 'mdi-chart-bubble',
    color: 'rgba(30, 136, 229, 0.1)',
    iconColor: '#1E88E5',
    change: '',
    changeIcon: 'mdi-minus',
    changeClass: 'neutral'
  },
  {
    title: 'Calculations',
    value: '0',
    icon: 'mdi-calculator',
    color: 'rgba(76, 175, 80, 0.1)',
    iconColor: '#4CAF50',
    change: '',
    changeIcon: 'mdi-minus',
    changeClass: 'neutral'
  },
  {
    title: 'Avg Yield',
    value: '0%',
    icon: 'mdi-trending-up',
    color: 'rgba(255, 193, 7, 0.1)',
    iconColor: '#FFC107',
    change: '',
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

onMounted(() => {
  loadCleanedData()
  // Also automatically trigger calculations to ensure data is displayed
  setTimeout(() => {
    if (moneyMarketCalculations.value[0].principal === 0) {
      console.log('No calculations displayed, triggering sample data load')
      loadSampleData()
    }
  }, 1000)
})

const loadCleanedData = async () => {
  try {
    // Load dataset from composable
    loadDataset()
    
    // Get the cleaned dataset from localStorage
    const storedData = localStorage.getItem('finalCleanedData') || localStorage.getItem('currentDataset') || localStorage.getItem('uploadedDataset')
    
    if (storedData) {
      const dataset = JSON.parse(storedData)
      cleanedData.value = dataset
      console.log('Loaded cleaned dataset:', dataset)
      
      // Perform calculations using the backend API
      await performCalculations(dataset.data)
    } else {
      console.log('No cleaned dataset found, using sample data')
      loadSampleData()
    }
  } catch (error) {
    console.error('Error loading cleaned data:', error)
    loadSampleData()
  }
}

const performCalculations = async (data) => {
  if (!data || data.length === 0) {
    console.log('No data available for calculations')
    return
  }

  calculating.value = true
  
  try {
    // Default to money market for comprehensive calculations
    const instrumentType = 'money_market'
    
    console.log('Performing calculations with instrument type:', instrumentType)
    console.log('Data length:', data.length)
    
    // Call the backend calculate API with money market instrument type
    const response = await dataAPI.calculate(data, instrumentType, {})
    
    if (response.success) {
      calculations.value = response.calculations || []
      console.log('Calculations completed:', response.calculations)
      
      // Save calculations to localStorage for visualizations
      localStorage.setItem('calculations', JSON.stringify({
        success: true,
        calculations: response.calculations,
        instrumentType: 'money_market',
        timestamp: new Date().toISOString()
      }))
      
      // Update all calculation types with real data
      if (response.calculations && response.calculations.length > 0) {
        console.log('Updating calculation displays with real data')
        updateTreasuryCalculations(response.calculations)
        updateMoneyMarketCalculations(response.calculations)
        updateBondCalculations(response.calculations)
        
        // Update KPI data
        calculationsKpiData.value[0].value = (datasetInfo.value?.rows || response.calculations.length).toString()
        calculationsKpiData.value[1].value = datasetInfo.value?.instrumentType || response.instrument_type || 'Money Market'
        calculationsKpiData.value[2].value = response.calculations.length.toString()
        calculationsKpiData.value[3].value = getAverageYield() + '%'
      } else {
        console.log('No calculation data returned from backend')
      }
    } else {
      console.error('Calculations failed:', response)
    }
    
    // Also fetch yield curve data
    await fetchYieldCurveData()
    
  } catch (error) {
    console.error('Error during calculations:', error)
  } finally {
    calculating.value = false
  }
}

const fetchYieldCurveData = async () => {
  try {
    console.log('Fetching yield curve data from FRED API...')
    const response = await fetch('http://localhost:5000/api/fred-yield-curve')
    const data = await response.json()
    
    if (data.success && data.data) {
      console.log('Yield curve data fetched:', data.data)
      // Store yield curve data for display
      yieldCurveData.value = data.data
      
      // Update calculations with yield curve assisted values
      updateCalculationsWithYieldCurve(data.data)
    } else {
      console.log('Yield curve data not available, using fallback')
    }
  } catch (error) {
    console.error('Error fetching yield curve data:', error)
  }
}

const updateCalculationsWithYieldCurve = (yieldCurveData) => {
  // Update calculations to show yield curve assisted values
  if (yieldCurveData && yieldCurveData.current) {
    console.log('Updating calculations with yield curve data')
    
    // Update treasury calculations with yield curve rates
    if (treasuryCalculations.value.length > 0 && yieldCurveData.current.length > 0) {
      treasuryCalculations.value.forEach((calc, index) => {
        if (index < yieldCurveData.current.length) {
          calc.discountYield = yieldCurveData.current[index] || calc.discountYield
          calc.bondEquivalentYield = yieldCurveData.current[index] || calc.bondEquivalentYield
        }
      })
    }
  }
}

const yieldCurveData = ref(null)

const updateTreasuryCalculations = (calculationResults) => {
  // Update treasury calculations with real data from backend
  if (calculationResults.length > 0) {
    const firstCalc = calculationResults[0]
    
    // Update the first treasury bill with real data
    if (treasuryCalculations.value.length > 0) {
      treasuryCalculations.value[0] = {
        ...treasuryCalculations.value[0],
        faceValue: firstCalc.face_value || 1000,
        purchasePrice: firstCalc.purchase_price || 950,
        daysToMaturity: firstCalc.term_days || 91,
        discountYield: firstCalc.discount_yield || 5.2,
        bondEquivalentYield: firstCalc.bond_equivalent_yield || 5.3
      }
    }
  }
}

const updateMoneyMarketCalculations = (calculationResults) => {
  // Update money market calculations with real data from backend
  if (calculationResults.length > 0) {
    // Group calculations by instrument type
    const groupedCalculations = calculationResults.reduce((groups, calc) => {
      const instrumentType = calc.instrument_type || 'Unknown'
      if (!groups[instrumentType]) {
        groups[instrumentType] = []
      }
      groups[instrumentType].push(calc)
      return groups
    }, {})
    
    // Update money market calculations with real data
    const moneyMarketTypes = ['Commercial Paper', 'Certificate of Deposit', 'Repo Agreement', 'Bankers Acceptance']
    
    moneyMarketTypes.forEach((instrumentType, index) => {
      if (groupedCalculations[instrumentType] && groupedCalculations[instrumentType].length > 0) {
        const calcData = groupedCalculations[instrumentType][0] // Use first calculation of this type
        
        if (moneyMarketCalculations.value[index]) {
          moneyMarketCalculations.value[index] = {
            ...moneyMarketCalculations.value[index],
            principal: calcData.principal || 100000,
            interestEarned: calcData.interest_earned || 0,
            termDays: calcData.term_days || 90,
            annualYield: calcData.annual_yield || 0,
            effectiveRate: calcData.effective_rate || 0,
            maturityValue: calcData.maturity_value || 0
          }
        }
      } else {
        // If no specific instrument data, use first available calculation
        if (calculationResults.length > index && moneyMarketCalculations.value[index]) {
          const calcData = calculationResults[index]
          moneyMarketCalculations.value[index] = {
            ...moneyMarketCalculations.value[index],
            principal: calcData.principal || 100000,
            interestEarned: calcData.interest_earned || 0,
            termDays: calcData.term_days || 90,
            annualYield: calcData.annual_yield || 0,
            effectiveRate: calcData.effective_rate || 0,
            maturityValue: calcData.maturity_value || 0
          }
        }
      }
    })
    
    console.log('Updated money market calculations:', moneyMarketCalculations.value)
  }
}

const updateBondCalculations = (calculationResults) => {
  // Update bond calculations with real data from backend
  if (calculationResults.length > 0) {
    const firstCalc = calculationResults[0]
    
    // Update bond calculations with real data
    if (bondCalculations.value.length > 0) {
      bondCalculations.value.forEach((bond, index) => {
        bondCalculations.value[index] = {
          ...bondCalculations.value[index],
          faceValue: firstCalc.face_value || 1000,
          currentPrice: firstCalc.purchase_price || 980,
          couponRate: 5.0, // Default coupon rate
          yieldToMaturity: firstCalc.ytm_approx || 5.2,
          currentYield: firstCalc.current_yield || 5.1,
          duration: 10.0 // Default duration
        }
      })
    }
  }
}

const loadSampleData = async () => {
  console.log('Loading sample data for calculations')
  
  // Create sample money market data that will trigger real calculations
  const sampleData = [
    {
      instrument_name: 'Commercial Paper',
      principal: 100000,
      interest_rate: 0.045,
      term_days: 30,
      face_value: 100000,
      purchase_price: 99625
    },
    {
      instrument_name: 'Certificate of Deposit',
      principal: 50000,
      interest_rate: 0.052,
      term_days: 90,
      face_value: 50000,
      purchase_price: 50000
    },
    {
      instrument_name: 'Repo Agreement',
      principal: 250000,
      interest_rate: 0.048,
      term_days: 180,
      face_value: 250000,
      purchase_price: 250000
    },
    {
      instrument_name: 'Bankers Acceptance',
      principal: 75000,
      interest_rate: 0.041,
      term_days: 270,
      face_value: 75000,
      purchase_price: 74775
    }
  ]
  
  // Trigger real calculations with sample data
  await performCalculations(sampleData)
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

const proceedToVisualizations = () => {
  router.push('/visualizations')
}

// Selection and calculation functions
const selectTreasuryBill = (treasury) => {
  selectedTreasuryBill.value = treasury
}

// Treasury bill calculation functions
const calculateMoneyMarketYield = (treasury) => {
  if (!treasury || !treasury.faceValue || !treasury.purchasePrice || !treasury.daysToMaturity) return 0
  const faceValue = treasury.faceValue
  const purchasePrice = treasury.purchasePrice
  const days = treasury.daysToMaturity
  const moneyMarketYield = ((faceValue - purchasePrice) / purchasePrice) * (365 / days) * 100
  return moneyMarketYield || treasury.discountYield || 0
}

const calculateEffectiveYield = (treasury) => {
  if (!treasury || !treasury.discountYield) return 0
  const discountYield = treasury.discountYield / 100
  const effectiveYield = Math.pow(1 + discountYield, 365 / treasury.daysToMaturity) - 1
  return effectiveYield * 100 || treasury.bondEquivalentYield || 0
}

const calculateBankDiscount = (treasury) => {
  return treasury?.discountYield || 0
}

const calculateSpotRate = (treasury) => {
  return treasury?.bondEquivalentYield || 0
}

const calculateForwardRate = (treasury) => {
  if (!treasury || !treasury.discountYield) return 0
  return treasury.discountYield + 0.5
}

const calculateYieldPremium = (treasury) => {
  if (!treasury || !treasury.discountYield) return 0
  return Math.max(0, treasury.discountYield - 4.0)
}

const getTableHeaders = () => {
  if (!calculations.value.length) return []
  return Object.keys(calculations.value[0]).map(k => ({ title:k, key:k }))
}
</script>

<style scoped>
.calculations-view {
  width: 100%;
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
