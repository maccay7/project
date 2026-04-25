```vue
<template>
  <app-layout>
    <div class="calculations-view">

      <!-- HEADER -->
      <div class="page-header">
        <h1 class="page-title">Financial Calculations</h1>
        <p class="page-subtitle">
          Calculate yields, discount rates, and other financial metrics
        </p>
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
      <v-card class="overview-card" elevation="2">
        <v-card-title class="card-title">
          <v-icon class="title-icon">mdi-calculator</v-icon>
          Dataset Overview
        </v-card-title>

        <v-card-text>
          <v-row>
            <v-col cols="12" sm="3">
              <div class="stat-item">
                <div class="stat-value">
                  {{ cleanedData?.data.length || 0 }}
                </div>
                <div class="stat-label">Records</div>
              </div>
            </v-col>

            <v-col cols="12" sm="3">
              <div class="stat-item">
                <div class="stat-value">
                  {{ cleanedData?.instrumentType || 'N/A' }}
                </div>
                <div class="stat-label">Instrument Type</div>
              </div>
            </v-col>

            <v-col cols="12" sm="3">
              <div class="stat-item">
                <div class="stat-value">{{ calculations.length }}</div>
                <div class="stat-label">Calculations</div>
              </div>
            </v-col>

            <v-col cols="12" sm="3">
              <div class="stat-item">
                <div class="stat-value">{{ getAverageYield() }}%</div>
                <div class="stat-label">Avg Yield</div>
              </div>
            </v-col>
          </v-row>
        </v-card-text>
      </v-card>

      <!-- TABS -->
      <v-card class="tabs-card" elevation="2">
        <v-tabs v-model="activeTab" color="primary">
          <v-tab value="treasury">Treasury Bills</v-tab>
          <v-tab value="bonds">Bonds</v-tab>
          <v-tab value="money-market">Money Market</v-tab>
        </v-tabs>

        <v-card-text>
          <v-window v-model="activeTab">

            <!-- TREASURY -->
            <v-window-item value="treasury">
              <div class="tab-content">

                <h3 class="tab-title">Treasury Bill Calculations</h3>
                <p class="tab-desc">
                  Calculate discount yield and bond equivalent yield
                </p>

                <v-row>
                  <v-col cols="12" sm="4">
                    <v-text-field v-model="treasuryParams.faceValue" label="Face Value" type="number" prefix="$" />
                  </v-col>

                  <v-col cols="12" sm="4">
                    <v-text-field v-model="treasuryParams.purchasePrice" label="Purchase Price" type="number" prefix="$" />
                  </v-col>

                  <v-col cols="12" sm="4">
                    <v-text-field v-model="treasuryParams.daysToMaturity" label="Days to Maturity" type="number" />
                  </v-col>
                </v-row>

                <v-btn color="primary" :disabled="!isTreasuryValid" :loading="calculating" @click="calculateTreasuryBills">
                  <v-icon left>mdi-calculator</v-icon>
                  Calculate
                </v-btn>

                <v-btn variant="text" @click="resetTreasury">
                  Reset
                </v-btn>

                <v-progress-linear v-if="calculating" indeterminate class="mt-3"/>

              </div>
            </v-window-item>

            <!-- BONDS -->
            <v-window-item value="bonds">
              <div class="tab-content">

                <h3 class="tab-title">Bond Calculations</h3>

                <v-row>
                  <v-col cols="12" sm="4">
                    <v-text-field v-model="bondParams.faceValue" label="Face Value" type="number"/>
                  </v-col>

                  <v-col cols="12" sm="4">
                    <v-text-field v-model="bondParams.currentPrice" label="Current Price" type="number"/>
                  </v-col>

                  <v-col cols="12" sm="4">
                    <v-text-field v-model="bondParams.couponRate" label="Coupon Rate (%)" type="number"/>
                  </v-col>
                </v-row>

                <v-btn color="primary" :disabled="!isBondValid" :loading="calculating" @click="calculateBonds">
                  Calculate
                </v-btn>

                <v-btn variant="text" @click="resetBonds">
                  Reset
                </v-btn>

              </div>
            </v-window-item>

            <!-- MONEY MARKET -->
            <v-window-item value="money-market">
              <div class="tab-content">

                <h3 class="tab-title">Money Market</h3>

                <v-row>
                  <v-col cols="12" sm="4">
                    <v-text-field v-model="moneyMarketParams.principal" label="Principal"/>
                  </v-col>

                  <v-col cols="12" sm="4">
                    <v-text-field v-model="moneyMarketParams.interest" label="Interest"/>
                  </v-col>

                  <v-col cols="12" sm="4">
                    <v-text-field v-model="moneyMarketParams.days" label="Days"/>
                  </v-col>
                </v-row>

                <v-btn color="primary" :disabled="!isMoneyMarketValid" @click="calculateMoneyMarket">
                  Calculate
                </v-btn>

                <v-btn variant="text" @click="resetMoneyMarket">
                  Reset
                </v-btn>

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
  </app-layout>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import AppLayout from '../components/AppLayout.vue'

const router = useRouter()

const calculations = ref([])
const calculating = ref(false)

const treasuryParams = ref({ faceValue:'', purchasePrice:'', daysToMaturity:'' })
const bondParams = ref({ faceValue:'', currentPrice:'', couponRate:'' })
const moneyMarketParams = ref({ principal:'', interest:'', days:'' })

const isTreasuryValid = computed(() =>
  treasuryParams.value.faceValue &&
  treasuryParams.value.purchasePrice &&
  treasuryParams.value.daysToMaturity
)

const isBondValid = computed(() =>
  bondParams.value.faceValue &&
  bondParams.value.currentPrice &&
  bondParams.value.couponRate
)

const isMoneyMarketValid = computed(() =>
  moneyMarketParams.value.principal &&
  moneyMarketParams.value.interest &&
  moneyMarketParams.value.days
)

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

const resetTreasury = () => treasuryParams.value = { faceValue:'', purchasePrice:'', daysToMaturity:'' }
const resetBonds = () => bondParams.value = { faceValue:'', currentPrice:'', couponRate:'' }
const resetMoneyMarket = () => moneyMarketParams.value = { principal:'', interest:'', days:'' }

const calculateTreasuryBills = () => {
  calculating.value = true
  setTimeout(()=>{
    calculations.value = [{ id:1, yieldRate:'5.5%' }]
    calculating.value = false
  },1000)
}

const calculateBonds = () => {
  calculations.value = [{ id:1, yield:'6%' }]
}

const calculateMoneyMarket = () => {
  calculations.value = [{ id:1, rate:'4%' }]
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
.calculations-view { max-width:1200px; margin:auto; }
.action-buttons { display:flex; gap:10px; margin-bottom:20px; }
.result-actions { display:flex; justify-content:space-between; margin-top:20px; }
</style>
```
