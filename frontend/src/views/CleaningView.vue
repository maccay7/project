```vue
<template>
  <app-layout>
    <div class="cleaning-view">

      <!-- HEADER -->
      <div class="page-header">
        <h1 class="page-title">Data Cleaning</h1>
        <p class="page-subtitle">
          Configure and apply data cleaning operations to prepare your dataset
        </p>
      </div>

      <!-- ACTION BUTTONS -->
      <div class="action-buttons">
        <v-btn color="primary" @click="loadSampleData">
          <v-icon left>mdi-database</v-icon>
          Load Sample
        </v-btn>

        <v-btn color="secondary" variant="outlined" @click="resetOptions">
          <v-icon left>mdi-refresh</v-icon>
          Reset Options
        </v-btn>

        <v-btn color="error" variant="outlined" @click="clearResults">
          <v-icon left>mdi-delete</v-icon>
          Clear Results
        </v-btn>
      </div>

      <!-- DATA OVERVIEW -->
      <v-card class="overview-card" elevation="2">
        <v-card-title class="card-title">
          <v-icon class="title-icon">mdi-database</v-icon>
          Dataset Overview
        </v-card-title>

        <v-card-text>
          <v-row>
            <v-col cols="12" sm="3">
              <div class="stat-item">
                <div class="stat-value">{{ uploadedData?.data.length || 0 }}</div>
                <div class="stat-label">Rows</div>
              </div>
            </v-col>

            <v-col cols="12" sm="3">
              <div class="stat-item">
                <div class="stat-value">{{ getColumnCount() }}</div>
                <div class="stat-label">Columns</div>
              </div>
            </v-col>

            <v-col cols="12" sm="3">
              <div class="stat-item">
                <div class="stat-value">{{ uploadedData?.instrumentType || 'N/A' }}</div>
                <div class="stat-label">Instrument</div>
              </div>
            </v-col>

            <v-col cols="12" sm="3">
              <div class="stat-item">
                <div class="stat-value">{{ uploadedData?.name || 'N/A' }}</div>
                <div class="stat-label">File</div>
              </div>
            </v-col>
          </v-row>
        </v-card-text>
      </v-card>

      <!-- CLEANING OPTIONS -->
      <v-row>
        <v-col cols="12" md="6">
          <v-card elevation="2">

            <v-card-title class="card-title">
              <v-icon class="title-icon">mdi-broom</v-icon>
              Cleaning Options
            </v-card-title>

            <v-card-text>
              <v-checkbox
                v-for="option in cleaningOptions"
                :key="option.key"
                v-model="option.value"
                color="primary"
              >
                <template v-slot:label>
                  <div>
                    <strong>{{ option.label }}</strong>
                    <div class="desc">{{ option.description }}</div>
                  </div>
                </template>
              </v-checkbox>

              <v-progress-linear
                v-if="cleaning"
                indeterminate
                color="primary"
                class="mt-3"
              />

              <v-btn
                color="primary"
                :disabled="!isAnyOptionSelected"
                :loading="cleaning"
                @click="performCleaning"
              >
                <v-icon left>mdi-broom</v-icon>
                Start Cleaning
              </v-btn>
            </v-card-text>

          </v-card>
        </v-col>

        <!-- RESULTS -->
        <v-col cols="12" md="6">
          <v-card elevation="2">

            <v-card-title class="card-title">
              <v-icon class="title-icon">mdi-chart-line</v-icon>
              Results
            </v-card-title>

            <v-card-text>

              <v-alert v-if="!cleaningResults" type="info">
                Configure options and start cleaning
              </v-alert>

              <div v-if="cleaningResults">

                <v-alert type="success" class="mb-3">
                  Cleaning completed
                </v-alert>

                <div class="result-item">
                  <span>Original:</span>
                  <span>{{ cleaningResults.originalRows }}</span>
                </div>

                <div class="result-item">
                  <span>Cleaned:</span>
                  <span>{{ cleaningResults.cleanedRows }}</span>
                </div>

                <div class="result-item">
                  <span>Duplicates removed:</span>
                  <span>{{ cleaningResults.duplicatesRemoved }}</span>
                </div>

                <div class="result-item">
                  <span>Missing filled:</span>
                  <span>{{ cleaningResults.missingValuesFilled }}</span>
                </div>

                <div class="result-actions">
                  <v-btn color="primary" @click="proceedToCalculations">
                    Proceed
                  </v-btn>

                  <v-btn variant="outlined" @click="clearResults">
                    Close
                  </v-btn>
                </div>

              </div>

            </v-card-text>

          </v-card>
        </v-col>
      </v-row>

      <!-- PREVIEW -->
      <v-card v-if="cleaningResults" class="preview-card">
        <v-card-title>Preview</v-card-title>

        <v-data-table
          :headers="getTableHeaders()"
          :items="getPreviewData()"
          density="compact"
        />
      </v-card>

    </div>
  </app-layout>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import AppLayout from '../components/AppLayout.vue'

const router = useRouter()

const uploadedData = ref(null)
const cleaning = ref(false)
const cleaningResults = ref(null)

const cleaningOptions = ref([
  { key:'removeDuplicates', label:'Remove duplicates', description:'Delete duplicate rows', value:true },
  { key:'fillMissingValues', label:'Fill missing', description:'Replace empty values', value:true },
  { key:'removeOutliers', label:'Remove outliers', description:'Remove extreme values', value:false }
])

onMounted(() => {
  const data = localStorage.getItem('uploadedData')
  if (data) uploadedData.value = JSON.parse(data)
})

const isAnyOptionSelected = computed(() =>
  cleaningOptions.value.some(o => o.value)
)

const loadSampleData = () => {
  uploadedData.value = {
    name:'sample.csv',
    instrumentType:'Treasury',
    data:[{a:1,b:2},{a:2,b:null}]
  }
}

const resetOptions = () => {
  cleaningOptions.value.forEach(o => o.value = false)
}

const clearResults = () => {
  cleaningResults.value = null
}

const performCleaning = () => {
  cleaning.value = true

  setTimeout(()=>{
    cleaningResults.value = {
      originalRows: uploadedData.value?.data.length || 0,
      cleanedRows: 10,
      duplicatesRemoved: 2,
      missingValuesFilled: 3
    }
    cleaning.value = false
  },1500)
}

const getColumnCount = () =>
  uploadedData.value?.data?.length
    ? Object.keys(uploadedData.value.data[0]).length
    : 0

const getTableHeaders = () => {
  if (!uploadedData.value?.data.length) return []
  return Object.keys(uploadedData.value.data[0]).map(k => ({ title:k, key:k }))
}

const getPreviewData = () =>
  uploadedData.value?.data.slice(0,10) || []

const proceedToCalculations = () => {
  localStorage.setItem('cleanedData', JSON.stringify({
    ...uploadedData.value,
    cleaningResults: cleaningResults.value
  }))
  router.push('/calculations')
}
</script>

<style scoped>
.cleaning-view { max-width:1200px; margin:auto; }

.action-buttons {
  display:flex;
  gap:10px;
  margin-bottom:20px;
}

.result-item {
  display:flex;
  justify-content:space-between;
  margin-bottom:8px;
}

.result-actions {
  display:flex;
  justify-content:space-between;
  margin-top:15px;
}

.desc {
  font-size:12px;
  color:#666;
}
</style>
```
