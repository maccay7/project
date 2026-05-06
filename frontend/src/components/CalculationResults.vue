<template>
  <v-card class="calculation-results" elevation="2">
    <v-card-title class="card-title">
      <v-icon class="title-icon">mdi-calculator</v-icon>
      Calculation Results
      <v-spacer></v-spacer>
      <v-btn
        size="small"
        color="success"
        variant="outlined"
        @click="downloadExcel"
        class="mr-2"
      >
        <v-icon left size="small">mdi-microsoft-excel</v-icon>
        Download Excel
      </v-btn>
      <v-btn
        size="small"
        color="primary"
        variant="outlined"
        @click="downloadCSV"
        class="mr-2"
      >
        <v-icon left size="small">mdi-file-delimited</v-icon>
        Download CSV
      </v-btn>
      <v-btn
        size="small"
        color="info"
        variant="outlined"
        @click="refreshCalculations"
      >
        <v-icon left size="small">mdi-refresh</v-icon>
        Refresh
      </v-btn>
    </v-card-title>
    <v-card-text>
      <v-alert type="info" variant="tonal" class="mb-4">
        <v-icon left>mdi-information</v-icon>
        View and download calculations performed on your raw data. Results are shown alongside original data for comparison.
      </v-alert>

      <!-- Calculation Summary -->
      <v-row class="mb-4">
        <v-col cols="12">
          <v-card class="summary-card" outlined>
            <v-card-title class="summary-title">
              <v-icon class="title-icon">mdi-chart-box</v-icon>
              Calculation Summary
            </v-card-title>
            <v-card-text>
              <v-row>
                <v-col cols="12" md="3">
                  <div class="summary-item">
                    <div class="summary-label">Total Rows Processed:</div>
                    <div class="summary-value">{{ calculationData.length }}</div>
                  </div>
                </v-col>
                <v-col cols="12" md="3">
                  <div class="summary-item">
                    <div class="summary-label">Successful Calculations:</div>
                    <div class="summary-value success">{{ successfulCount }}</div>
                  </div>
                </v-col>
                <v-col cols="12" md="3">
                  <div class="summary-item">
                    <div class="summary-label">Failed Calculations:</div>
                    <div class="summary-value error">{{ failedCount }}</div>
                  </div>
                </v-col>
                <v-col cols="12" md="3">
                  <div class="summary-item">
                    <div class="summary-label">Average Yield:</div>
                    <div class="summary-value">{{ averageYield }}%</div>
                  </div>
                </v-col>
              </v-row>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <!-- Calculation Filters -->
      <v-row class="mb-4">
        <v-col cols="12" md="4">
          <label class="filter-label">Filter by Status:</label>
          <v-select
            v-model="filterStatus"
            :items="statusOptions"
            variant="outlined"
            density="compact"
            clearable
          ></v-select>
        </v-col>
        <v-col cols="12" md="4">
          <label class="filter-label">Filter by Yield Range:</label>
          <v-range-slider
            v-model="yieldRange"
            :min="0"
            :max="15"
            step="0.1"
            thumb-label
            density="compact"
          >
            <template v-slot:prepend>
              <span class="range-label">{{ yieldRange[0] }}%</span>
            </template>
            <template v-slot:append>
              <span class="range-label">{{ yieldRange[1] }}%</span>
            </template>
          </v-range-slider>
        </v-col>
        <v-col cols="12" md="4">
          <label class="filter-label">Search:</label>
          <v-text-field
            v-model="searchQuery"
            variant="outlined"
            density="compact"
            placeholder="Search by date, maturity, or ID"
            prepend-inner-icon="mdi-magnify"
          ></v-text-field>
        </v-col>
      </v-row>

      <!-- Results Table -->
      <v-data-table
        :headers="tableHeaders"
        :items="filteredData"
        :loading="loading"
        density="compact"
        class="results-table"
        items-per-page="25"
        :items-per-page-options="[10, 25, 50, 100]"
      >
        <template v-slot:item.status="{ item }">
          <v-chip
            :color="item.status === 'success' ? 'success' : 'error'"
            size="small"
            variant="tonal"
          >
            {{ item.status }}
          </v-chip>
        </template>

        <template v-slot:item.raw_value="{ item }">
          <span class="cell-value">{{ formatNumber(item.raw_value) }}</span>
        </template>

        <template v-slot:item.calculated_yield="{ item }">
          <span class="cell-value highlight">{{ formatNumber(item.calculated_yield) }}%</span>
        </template>

        <template v-slot:item.discount_rate="{ item }">
          <span class="cell-value">{{ formatNumber(item.discount_rate) }}%</span>
        </template>

        <template v-slot:item.price="{ item }">
          <span class="cell-value">{{ formatCurrency(item.price) }}</span>
        </template>

        <template v-slot:item.actions="{ item }">
          <v-btn
            size="small"
            variant="text"
            color="primary"
            @click="viewDetails(item)"
          >
            <v-icon size="small">mdi-eye</v-icon>
          </v-btn>
        </template>
      </v-data-table>
    </v-card-text>

    <!-- Detail Dialog -->
    <v-dialog v-model="detailDialog" max-width="800px">
      <v-card>
        <v-card-title class="card-title">
          <v-icon class="title-icon">mdi-information</v-icon>
          Calculation Details
        </v-card-title>
        <v-card-text v-if="selectedRow">
          <v-row>
            <v-col cols="12" md="6">
              <div class="detail-item">
                <label class="detail-label">Row ID:</label>
                <div class="detail-value">{{ selectedRow.id }}</div>
              </div>
            </v-col>
            <v-col cols="12" md="6">
              <div class="detail-item">
                <label class="detail-label">Status:</label>
                <v-chip
                  :color="selectedRow.status === 'success' ? 'success' : 'error'"
                  size="small"
                  variant="tonal"
                >
                  {{ selectedRow.status }}
                </v-chip>
              </div>
            </v-col>
          </v-row>
          <v-row>
            <v-col cols="12" md="6">
              <div class="detail-item">
                <label class="detail-label">Raw Value:</label>
                <div class="detail-value">{{ formatNumber(selectedRow.raw_value) }}</div>
              </div>
            </v-col>
            <v-col cols="12" md="6">
              <div class="detail-item">
                <label class="detail-label">Calculated Yield:</label>
                <div class="detail-value highlight">{{ formatNumber(selectedRow.calculated_yield) }}%</div>
              </div>
            </v-col>
          </v-row>
          <v-row>
            <v-col cols="12" md="6">
              <div class="detail-item">
                <label class="detail-label">Discount Rate:</label>
                <div class="detail-value">{{ formatNumber(selectedRow.discount_rate) }}%</div>
              </div>
            </v-col>
            <v-col cols="12" md="6">
              <div class="detail-item">
                <label class="detail-label">Price:</label>
                <div class="detail-value">{{ formatCurrency(selectedRow.price) }}</div>
              </div>
            </v-col>
          </v-row>
          <v-row v-if="selectedRow.error_message">
            <v-col cols="12">
              <div class="detail-item">
                <label class="detail-label">Error Message:</label>
                <v-alert type="error" variant="tonal" density="compact">
                  {{ selectedRow.error_message }}
                </v-alert>
              </div>
            </v-col>
          </v-row>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="primary" variant="text" @click="detailDialog = false">
            Close
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-card>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { calculationsAPI } from '../services/api'

interface CalculationRow {
  id: string
  status: 'success' | 'error'
  raw_value: number
  calculated_yield: number
  discount_rate: number
  price: number
  error_message?: string
  [key: string]: any
}

interface Props {
  calculationData: CalculationRow[]
  instrumentType?: string
}

const props = withDefaults(defineProps<Props>(), {
  calculationData: () => [],
  instrumentType: 'money_market'
})

const emit = defineEmits<{
  (e: 'refresh'): void
}>()

const loading = ref(false)
const filterStatus = ref<string | null>(null)
const yieldRange = ref([0, 15])
const searchQuery = ref('')
const detailDialog = ref(false)
const selectedRow = ref<CalculationRow | null>(null)

const statusOptions = ['success', 'error']

const tableHeaders = [
  { title: 'Status', key: 'status', sortable: true },
  { title: 'Row ID', key: 'id', sortable: true },
  { title: 'Raw Value', key: 'raw_value', sortable: true },
  { title: 'Calculated Yield (%)', key: 'calculated_yield', sortable: true },
  { title: 'Discount Rate (%)', key: 'discount_rate', sortable: true },
  { title: 'Price', key: 'price', sortable: true },
  { title: 'Actions', key: 'actions', sortable: false }
]

// Computed properties
const successfulCount = computed(() => 
  props.calculationData.filter(row => row.status === 'success').length
)

const failedCount = computed(() => 
  props.calculationData.filter(row => row.status === 'error').length
)

const averageYield = computed(() => {
  const successful = props.calculationData.filter(row => row.status === 'success')
  if (successful.length === 0) return 0
  const sum = successful.reduce((acc, row) => acc + row.calculated_yield, 0)
  return (sum / successful.length).toFixed(2)
})

const filteredData = computed(() => {
  let data = [...props.calculationData]

  // Filter by status
  if (filterStatus.value) {
    data = data.filter(row => row.status === filterStatus.value)
  }

  // Filter by yield range
  data = data.filter(row => 
    row.calculated_yield >= yieldRange.value[0] && 
    row.calculated_yield <= yieldRange.value[1]
  )

  // Filter by search query
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    data = data.filter(row => 
      String(row.id).toLowerCase().includes(query) ||
      String(row.raw_value).toLowerCase().includes(query) ||
      String(row.calculated_yield).toLowerCase().includes(query)
    )
  }

  return data
})

// Methods
const formatNumber = (value: number): string => {
  if (value === null || value === undefined) return 'N/A'
  return value.toLocaleString(undefined, { 
    minimumFractionDigits: 2,
    maximumFractionDigits: 4 
  })
}

const formatCurrency = (value: number): string => {
  if (value === null || value === undefined) return 'N/A'
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD'
  }).format(value)
}

const viewDetails = (row: CalculationRow) => {
  selectedRow.value = row
  detailDialog.value = true
}

const refreshCalculations = () => {
  emit('refresh')
}

const downloadExcel = () => {
  // Create Excel-compatible content
  const headers = tableHeaders.map(h => h.title).join(',')
  const rows = filteredData.value.map(row => [
    row.status,
    row.id,
    row.raw_value,
    row.calculated_yield,
    row.discount_rate,
    row.price
  ].join(','))
  
  const csvContent = [headers, ...rows].join('\n')
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  const url = URL.createObjectURL(blob)
  
  link.setAttribute('href', url)
  link.setAttribute('download', `calculations_${props.instrumentType}_${new Date().toISOString().split('T')[0]}.csv`)
  link.style.visibility = 'hidden'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

const downloadCSV = () => {
  downloadExcel()
}
</script>

<style scoped>
.calculation-results {
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

.summary-card {
  border-radius: 8px;
}

.summary-title {
  display: flex;
  align-items: center;
  color: #0B2A44;
  font-weight: 600;
  font-size: 16px;
  font-size: 16px;
}

.summary-item {
  text-align: center;
  padding: 12px;
}

.summary-label {
  font-size: 12px;
  color: #666;
  margin-bottom: 4px;
}

.summary-value {
  font-size: 24px;
  font-weight: 700;
  color: #0B2A44;
}

.summary-value.success {
  color: #4CAF50;
}

.summary-value.error {
  color: #F44336;
}

.filter-label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  color: #666;
  margin-bottom: 4px;
}

.range-label {
  font-size: 12px;
  color: #666;
  font-weight: 600;
}

.results-table {
  font-size: 13px;
}

.cell-value {
  font-family: 'Courier New', monospace;
  font-size: 13px;
}

.cell-value.highlight {
  font-weight: 700;
  color: #1E88E5;
}

.detail-item {
  margin-bottom: 16px;
}

.detail-label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  color: #666;
  margin-bottom: 4px;
}

.detail-value {
  font-size: 14px;
  color: #333;
}

.detail-value.highlight {
  font-weight: 700;
  color: #1E88E5;
}
</style>
