<template>
  <v-card class="yield-curve-config" elevation="2">
    <v-card-title class="card-title">
      <v-icon class="title-icon">mdi-chart-line</v-icon>
      Yield Curve Configuration
      <v-spacer></v-spacer>
      <v-btn
        size="small"
        color="primary"
        variant="outlined"
        @click="applyConfiguration"
      >
        <v-icon left size="small">mdi-check</v-icon>
        Apply
      </v-btn>
    </v-card-title>
    <v-card-text>
      <v-alert type="info" variant="tonal" class="mb-4">
        <v-icon left>mdi-information</v-icon>
        Configure yield curve parameters based on country, currency, and instrument type. These settings will be used for calculations.
      </v-alert>

      <!-- Preset Configurations -->
      <v-row class="mb-4">
        <v-col cols="12">
          <label class="config-label">Preset Configurations:</label>
          <v-select
            v-model="selectedPreset"
            :items="presets"
            item-title="name"
            item-value="id"
            variant="outlined"
            density="compact"
            @update:model-value="loadPreset"
          >
            <template v-slot:prepend-item>
              <v-list-item
                title="Custom Configuration"
                @click="selectedPreset = 'custom'"
              ></v-list-item>
              <v-divider class="mt-2"></v-divider>
            </template>
          </v-select>
        </v-col>
      </v-row>

      <!-- Country and Currency -->
      <v-row class="mb-4">
        <v-col cols="12" md="6">
          <label class="config-label">Country:</label>
          <v-select
            v-model="config.country"
            :items="countries"
            variant="outlined"
            density="compact"
            @update:model-value="updateCountryDefaults"
          ></v-select>
        </v-col>
        <v-col cols="12" md="6">
          <label class="config-label">Currency:</label>
          <v-select
            v-model="config.currency"
            :items="currencies"
            variant="outlined"
            density="compact"
          ></v-select>
        </v-col>
      </v-row>

      <!-- Yield Curve Parameters -->
      <v-row class="mb-4">
        <v-col cols="12">
          <h3 class="section-title">Yield Curve Parameters</h3>
        </v-col>
      </v-row>

      <v-row class="mb-4">
        <v-col cols="12" md="4">
          <label class="config-label">Curve Type:</label>
          <v-select
            v-model="config.curveType"
            :items="curveTypes"
            variant="outlined"
            density="compact"
          ></v-select>
        </v-col>
        <v-col cols="12" md="4">
          <label class="config-label">Interpolation Method:</label>
          <v-select
            v-model="config.interpolationMethod"
            :items="interpolationMethods"
            variant="outlined"
            density="compact"
          ></v-select>
        </v-col>
        <v-col cols="12" md="4">
          <label class="config-label">Day Count Convention:</label>
          <v-select
            v-model="config.dayCountConvention"
            :items="dayCountConventions"
            variant="outlined"
            density="compact"
          ></v-select>
        </v-col>
      </v-row>

      <!-- Maturities -->
      <v-row class="mb-4">
        <v-col cols="12">
          <label class="config-label">Maturity Points (comma-separated):</label>
          <v-text-field
            v-model="config.maturities"
            variant="outlined"
            density="compact"
            placeholder="e.g., 1M, 3M, 6M, 1Y, 2Y, 5Y, 10Y, 30Y"
            hint="Standard maturity points for yield curve construction"
          ></v-text-field>
        </v-col>
      </v-row>

      <!-- Risk-Free Rate -->
      <v-row class="mb-4">
        <v-col cols="12" md="6">
          <label class="config-label">Risk-Free Rate Source:</label>
          <v-select
            v-model="config.riskFreeRateSource"
            :items="riskFreeRateSources"
            variant="outlined"
            density="compact"
          ></v-select>
        </v-col>
        <v-col cols="12" md="6">
          <label class="config-label">Custom Risk-Free Rate (%):</label>
          <v-text-field
            v-model.number="config.customRiskFreeRate"
            type="number"
            step="0.01"
            variant="outlined"
            density="compact"
            :disabled="config.riskFreeRateSource !== 'custom'"
          ></v-text-field>
        </v-col>
      </v-row>

      <!-- Advanced Parameters -->
      <v-row class="mb-4">
        <v-col cols="12">
          <h3 class="section-title">Advanced Parameters</h3>
        </v-col>
      </v-row>

      <v-row class="mb-4">
        <v-col cols="12" md="4">
          <label class="config-label">Minimum Yield (%):</label>
          <v-text-field
            v-model.number="config.minYield"
            type="number"
            step="0.01"
            variant="outlined"
            density="compact"
          ></v-text-field>
        </v-col>
        <v-col cols="12" md="4">
          <label class="config-label">Maximum Yield (%):</label>
          <v-text-field
            v-model.number="config.maxYield"
            type="number"
            step="0.01"
            variant="outlined"
            density="compact"
          ></v-text-field>
        </v-col>
        <v-col cols="12" md="4">
          <label class="config-label">Smoothing Factor:</label>
          <v-text-field
            v-model.number="config.smoothingFactor"
            type="number"
            step="0.1"
            min="0"
            max="1"
            variant="outlined"
            density="compact"
            hint="0 = no smoothing, 1 = maximum smoothing"
          ></v-text-field>
        </v-col>
      </v-row>

      <!-- FRED API Configuration -->
      <v-row class="mb-4">
        <v-col cols="12">
          <h3 class="section-title">FRED API Configuration</h3>
        </v-col>
      </v-row>

      <v-row class="mb-4">
        <v-col cols="12" md="6">
          <label class="config-label">FRED Series ID:</label>
          <v-text-field
            v-model="config.fredSeriesId"
            variant="outlined"
            density="compact"
            placeholder="e.g., DGS10 for 10-Year Treasury"
            hint="FRED series ID for yield curve data"
          ></v-text-field>
        </v-col>
        <v-col cols="12" md="6">
          <label class="config-label">Update Frequency:</label>
          <v-select
            v-model="config.updateFrequency"
            :items="updateFrequencies"
            variant="outlined"
            density="compact"
          ></v-select>
        </v-col>
      </v-row>

      <!-- Country-Specific Settings -->
      <v-row class="mb-4">
        <v-col cols="12">
          <h3 class="section-title">Country-Specific Settings</h3>
        </v-col>
      </v-row>

      <v-row class="mb-4">
        <v-col cols="12" md="4">
          <label class="config-label">Tax Rate (%):</label>
          <v-text-field
            v-model.number="config.taxRate"
            type="number"
            step="0.01"
            variant="outlined"
            density="compact"
          ></v-text-field>
        </v-col>
        <v-col cols="12" md="4">
          <label class="config-label">Inflation Expectation (%):</label>
          <v-text-field
            v-model.number="config.inflationExpectation"
            type="number"
            step="0.01"
            variant="outlined"
            density="compact"
          ></v-text-field>
        </v-col>
        <v-col cols="12" md="4">
          <label class="config-label">Credit Spread Adjustment (%):</label>
          <v-text-field
            v-model.number="config.creditSpread"
            type="number"
            step="0.01"
            variant="outlined"
            density="compact"
          ></v-text-field>
        </v-col>
      </v-row>

      <!-- Save/Load Configuration -->
      <v-row class="mt-4">
        <v-col cols="12">
          <v-divider class="mb-4"></v-divider>
          <div class="config-actions">
            <v-btn
              color="success"
              variant="outlined"
              @click="saveConfiguration"
              class="mr-2"
            >
              <v-icon left>mdi-content-save</v-icon>
              Save Configuration
            </v-btn>
            <v-btn
              color="info"
              variant="outlined"
              @click="loadConfiguration"
              class="mr-2"
            >
              <v-icon left>mdi-folder-open</v-icon>
              Load Configuration
            </v-btn>
            <v-btn
              color="warning"
              variant="outlined"
              @click="resetToDefaults"
            >
              <v-icon left>mdi-refresh</v-icon>
              Reset to Defaults
            </v-btn>
          </div>
        </v-col>
      </v-row>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'

interface YieldCurveConfig {
  country: string
  currency: string
  curveType: string
  interpolationMethod: string
  dayCountConvention: string
  maturities: string
  riskFreeRateSource: string
  customRiskFreeRate: number
  minYield: number
  maxYield: number
  smoothingFactor: number
  fredSeriesId: string
  updateFrequency: string
  taxRate: number
  inflationExpectation: number
  creditSpread: number
}

interface Preset {
  id: string
  name: string
  config: Partial<YieldCurveConfig>
}

const emit = defineEmits<{
  (e: 'config-update', config: YieldCurveConfig): void
}>()

// Default configuration
const defaultConfig: YieldCurveConfig = {
  country: 'United States',
  currency: 'USD',
  curveType: 'Nelson-Siegel',
  interpolationMethod: 'Linear',
  dayCountConvention: 'Actual/365',
  maturities: '1M, 3M, 6M, 1Y, 2Y, 3Y, 5Y, 7Y, 10Y, 20Y, 30Y',
  riskFreeRateSource: 'FRED',
  customRiskFreeRate: 2.0,
  minYield: 0,
  maxYield: 15,
  smoothingFactor: 0.5,
  fredSeriesId: 'DGS10',
  updateFrequency: 'Daily',
  taxRate: 0,
  inflationExpectation: 2.0,
  creditSpread: 0
}

const config = ref<YieldCurveConfig>({ ...defaultConfig })
const selectedPreset = ref<string>('custom')

// Country-specific defaults
const countryDefaults: Record<string, Partial<YieldCurveConfig>> = {
  'United States': {
    currency: 'USD',
    fredSeriesId: 'DGS10',
    dayCountConvention: 'Actual/365',
    taxRate: 0
  },
  'United Kingdom': {
    currency: 'GBP',
    fredSeriesId: 'GB10YR',
    dayCountConvention: 'Actual/365',
    taxRate: 0
  },
  'Germany': {
    currency: 'EUR',
    fredSeriesId: 'GB10YR',
    dayCountConvention: '30/360',
    taxRate: 0
  },
  'Japan': {
    currency: 'JPY',
    fredSeriesId: 'JP10YR',
    dayCountConvention: 'Actual/365',
    taxRate: 0
  },
  'Canada': {
    currency: 'CAD',
    fredSeriesId: 'CAN10YR',
    dayCountConvention: 'Actual/365',
    taxRate: 0
  }
}

// Preset configurations
const presets: Preset[] = [
  {
    id: 'us-treasury',
    name: 'US Treasury',
    config: {
      country: 'United States',
      currency: 'USD',
      curveType: 'Nelson-Siegel',
      fredSeriesId: 'DGS10',
      dayCountConvention: 'Actual/365'
    }
  },
  {
    id: 'uk-gilt',
    name: 'UK Gilt',
    config: {
      country: 'United Kingdom',
      currency: 'GBP',
      curveType: 'Nelson-Siegel-Svensson',
      fredSeriesId: 'GB10YR',
      dayCountConvention: 'Actual/365'
    }
  },
  {
    id: 'eu-bund',
    name: 'EU Bund',
    config: {
      country: 'Germany',
      currency: 'EUR',
      curveType: 'Nelson-Siegel',
      fredSeriesId: 'GB10YR',
      dayCountConvention: '30/360'
    }
  },
  {
    id: 'jp-jgb',
    name: 'Japan JGB',
    config: {
      country: 'Japan',
      currency: 'JPY',
      curveType: 'Nelson-Siegel',
      fredSeriesId: 'JP10YR',
      dayCountConvention: 'Actual/365'
    }
  }
]

// Option lists
const countries = [
  'United States',
  'United Kingdom',
  'Germany',
  'France',
  'Japan',
  'Canada',
  'Australia',
  'Switzerland',
  'China',
  'Other'
]

const currencies = [
  'USD',
  'EUR',
  'GBP',
  'JPY',
  'CAD',
  'AUD',
  'CHF',
  'CNY',
  'Other'
]

const curveTypes = [
  'Nelson-Siegel',
  'Nelson-Siegel-Svensson',
  'Spline',
  'Linear',
  'Cubic Spline'
]

const interpolationMethods = [
  'Linear',
  'Cubic Spline',
  'Log-Linear',
  'Zero-Coupon'
]

const dayCountConventions = [
  'Actual/365',
  'Actual/360',
  '30/360',
  '30E/360',
  'Actual/Actual'
]

const riskFreeRateSources = [
  'FRED',
  'ECB',
  'BOE',
  'BOJ',
  'Custom'
]

const updateFrequencies = [
  'Daily',
  'Weekly',
  'Monthly',
  'Quarterly'
]

// Methods
const updateCountryDefaults = () => {
  const defaults = countryDefaults[config.value.country]
  if (defaults) {
    Object.assign(config.value, defaults)
  }
}

const loadPreset = (presetId: string) => {
  if (presetId === 'custom') return
  
  const preset = presets.find(p => p.id === presetId)
  if (preset) {
    Object.assign(config.value, preset.config)
  }
}

const applyConfiguration = () => {
  emit('config-update', config.value)
}

const saveConfiguration = () => {
  localStorage.setItem('yieldCurveConfig', JSON.stringify(config.value))
  console.log('Configuration saved to localStorage')
}

const loadConfiguration = () => {
  const saved = localStorage.getItem('yieldCurveConfig')
  if (saved) {
    try {
      config.value = JSON.parse(saved)
      console.log('Configuration loaded from localStorage')
    } catch (error) {
      console.error('Error loading configuration:', error)
    }
  }
}

const resetToDefaults = () => {
  config.value = { ...defaultConfig }
  selectedPreset.value = 'custom'
}

// Load saved configuration on mount
loadConfiguration()

// Watch for config changes
watch(config, (newConfig) => {
  emit('config-update', newConfig)
}, { deep: true })
</script>

<style scoped>
.yield-curve-config {
  border-radius: 12px;
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

.config-label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  color: #666;
  margin-bottom: 4px;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: #0B2A44;
  margin-bottom: 12px;
}

.config-actions {
  display: flex;
  gap: 8px;
}
</style>
