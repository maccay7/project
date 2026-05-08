<template>
  <fixed-layout>
    <div class="cleaning-view">
      <!-- Header Section -->
      <div class="dashboard-header">
        <h1 class="page-title">Data Cleaning</h1>
        <p class="page-subtitle">Configure and apply data cleaning operations to prepare your dataset</p>
      </div>

      <!-- ACTION BUTTONS -->
      <div class="action-buttons">
        <v-btn color="primary" @click="loadUploadedData">
          <v-icon left>mdi-database</v-icon>
          Load Dataset
        </v-btn>

        <v-btn color="secondary" variant="outlined" @click="resetOptions">
          <v-icon left>mdi-refresh</v-icon>
          Reset Options
        </v-btn>

        <v-btn color="success" variant="outlined" @click="showCleanedDataPreview" v-if="cleaningResults">
          <v-icon left>mdi-eye</v-icon>
          Show Preview of Cleaned Data
        </v-btn>

        <v-btn color="error" variant="outlined" @click="deleteDataset" v-if="uploadId">
          <v-icon left>mdi-delete</v-icon>
          Delete Dataset
        </v-btn>

        <v-btn color="warning" variant="outlined" @click="clearResults">
          <v-icon left>mdi-broom</v-icon>
          Clear Results
        </v-btn>

        <v-btn color="primary" @click="completeProcess" v-if="cleaningResults">
          <v-icon left>mdi-check</v-icon>
          Done
        </v-btn>
      </div>

      <!-- DATA OVERVIEW -->
      <v-card class="stats-card" elevation="2">
        <v-card-title class="card-title">
          <v-icon class="title-icon">mdi-database</v-icon>
          Dataset Overview
        </v-card-title>

        <v-card-text>
          <v-row class="kpi-row">
            <v-col cols="12" sm="6" md="3" v-for="kpi in cleaningKpiData" :key="kpi.title">
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

      <!-- CLEANING OPTIONS -->
      <v-row>
        <v-col cols="12" md="12">
          <v-card class="stats-card" elevation="2">

            <v-card-title class="card-title">
              <v-icon class="title-icon">mdi-broom</v-icon>
              Cleaning Options
            </v-card-title>

            <v-card-text>
              <div class="cleaning-options-container">
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
              </div>

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
      </v-row>

      <!-- DATASET PREVIEWS UNDER CLEANING OPTIONS -->
      <v-row v-if="uploadedData && uploadedData.data">
        <v-col cols="12" md="12">
          <v-card class="stats-card" elevation="2">
            <v-card-title class="card-title">
              <v-icon class="title-icon">mdi-table</v-icon>
              Original Dataset Preview
            </v-card-title>
            <v-card-text>
              <ExcelViewer
                :data="uploadedData.data.slice(0, 10)"
                :headers="Object.keys(uploadedData.data[0] || {})"
                @data-update="handleDataUpdate"
              />
            </v-card-text>
          </v-card>
        </v-col>
        <v-col cols="12" md="12" v-if="cleaningResults && cleaningResults.cleanedData">
          <v-card class="stats-card" elevation="2">
            <v-card-title class="card-title">
              <v-icon class="title-icon">mdi-table-check</v-icon>
              Cleaned Dataset Preview
            </v-card-title>
            <v-card-text>
              <ExcelViewer
                :data="cleaningResults.cleanedData.slice(0, 10)"
                :headers="Object.keys(cleaningResults.cleanedData[0] || {})"
                @data-update="handleCleanedDataUpdate"
              />
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <!-- RESULTS SECTION -->
      <v-row>
        <v-col cols="12" md="12">
          <v-card class="stats-card" elevation="2">

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
                  Cleaning completed successfully!
                </v-alert>

                <!-- Summary Stats -->
                <div class="result-summary">
                  <div class="result-item">
                    <span>Original Rows:</span>
                    <span>{{ cleaningResults.originalRows }}</span>
                  </div>

                  <div class="result-item">
                    <span>Cleaned Rows:</span>
                    <span>{{ cleaningResults.cleanedRows }}</span>
                  </div>

                  <div class="result-item">
                    <span>Total Operations Applied:</span>
                    <span>{{ cleaningResults.totalOperationsApplied }}</span>
                  </div>
                </div>

                <!-- Data Quality Results -->
                <v-divider class="my-3"></v-divider>
                <h4 class="result-category">Data Quality</h4>
                <div class="result-item" v-if="cleaningResults.duplicatesRemoved > 0">
                  <span>Duplicates Removed:</span>
                  <span>{{ cleaningResults.duplicatesRemoved }}</span>
                </div>

                <div class="result-item" v-if="cleaningResults.missingValuesFilled > 0">
                  <span>Missing Values Filled:</span>
                  <span>{{ cleaningResults.missingValuesFilled }}</span>
                </div>

                <div class="result-item" v-if="cleaningResults.outliersRemoved > 0">
                  <span>Outliers Removed:</span>
                  <span>{{ cleaningResults.outliersRemoved }}</span>
                </div>

                <div class="result-item" v-if="cleaningResults.emptyRowsRemoved > 0">
                  <span>Empty Rows Removed:</span>
                  <span>{{ cleaningResults.emptyRowsRemoved }}</span>
                </div>

                <!-- Formatting Results -->
                <v-divider class="my-3" v-if="cleaningResults.textStandardized > 0 || cleaningResults.whitespaceTrimmed > 0 || cleaningResults.numbersNormalized > 0"></v-divider>
                <h4 class="result-category" v-if="cleaningResults.textStandardized > 0 || cleaningResults.whitespaceTrimmed > 0 || cleaningResults.numbersNormalized > 0">Formatting</h4>
                <div class="result-item" v-if="cleaningResults.textStandardized > 0">
                  <span>Text Standardized:</span>
                  <span>{{ cleaningResults.textStandardized }}</span>
                </div>

                <div class="result-item" v-if="cleaningResults.whitespaceTrimmed > 0">
                  <span>Whitespace Trimmed:</span>
                  <span>{{ cleaningResults.whitespaceTrimmed }}</span>
                </div>

                <div class="result-item" v-if="cleaningResults.numbersNormalized > 0">
                  <span>Numbers Normalized:</span>
                  <span>{{ cleaningResults.numbersNormalized }}</span>
                </div>

                <div class="result-item" v-if="cleaningResults.datesFormatted > 0">
                  <span>Dates Formatted:</span>
                  <span>{{ cleaningResults.datesFormatted }}</span>
                </div>

                <div class="result-item" v-if="cleaningResults.emailsValidated > 0">
                  <span>Emails Validated:</span>
                  <span>{{ cleaningResults.emailsValidated }}</span>
                </div>

                <!-- Data Type Results -->
                <v-divider class="my-3" v-if="cleaningResults.dataTypesConverted > 0 || cleaningResults.currencyStandardized > 0 || cleaningResults.percentagesNormalized > 0"></v-divider>
                <h4 class="result-category" v-if="cleaningResults.dataTypesConverted > 0 || cleaningResults.currencyStandardized > 0 || cleaningResults.percentagesNormalized > 0">Data Types</h4>
                <div class="result-item" v-if="cleaningResults.dataTypesConverted > 0">
                  <span>Data Types Converted:</span>
                  <span>{{ cleaningResults.dataTypesConverted }}</span>
                </div>

                <div class="result-item" v-if="cleaningResults.currencyStandardized > 0">
                  <span>Currency Standardized:</span>
                  <span>{{ cleaningResults.currencyStandardized }}</span>
                </div>

                <div class="result-item" v-if="cleaningResults.percentagesNormalized > 0">
                  <span>Percentages Normalized:</span>
                  <span>{{ cleaningResults.percentagesNormalized }}</span>
                </div>

                <!-- Validation Results -->
                <v-divider class="my-3" v-if="cleaningResults.rangesValidated > 0 || cleaningResults.consistencyChecked > 0 || cleaningResults.patternsValidated > 0"></v-divider>
                <h4 class="result-category" v-if="cleaningResults.rangesValidated > 0 || cleaningResults.consistencyChecked > 0 || cleaningResults.patternsValidated > 0">Validation</h4>
                <div class="result-item" v-if="cleaningResults.rangesValidated > 0">
                  <span>Ranges Validated:</span>
                  <span>{{ cleaningResults.rangesValidated }}</span>
                </div>

                <div class="result-item" v-if="cleaningResults.consistencyChecked > 0">
                  <span>Consistency Checked:</span>
                  <span>{{ cleaningResults.consistencyChecked }}</span>
                </div>

                <div class="result-item" v-if="cleaningResults.patternsValidated > 0">
                  <span>Patterns Validated:</span>
                  <span>{{ cleaningResults.patternsValidated }}</span>
                </div>

                <!-- Advanced Results -->
                <v-divider class="my-3" v-if="cleaningResults.specialCharsRemoved > 0 || cleaningResults.phonesStandardized > 0 || cleaningResults.addressesNormalized > 0 || cleaningResults.postalCodesCleaned > 0"></v-divider>
                <h4 class="result-category" v-if="cleaningResults.specialCharsRemoved > 0 || cleaningResults.phonesStandardized > 0 || cleaningResults.addressesNormalized > 0 || cleaningResults.postalCodesCleaned > 0">Advanced Cleaning</h4>
                <div class="result-item" v-if="cleaningResults.specialCharsRemoved > 0">
                  <span>Special Characters Removed:</span>
                  <span>{{ cleaningResults.specialCharsRemoved }}</span>
                </div>

                <div class="result-item" v-if="cleaningResults.phonesStandardized > 0">
                  <span>Phone Numbers Standardized:</span>
                  <span>{{ cleaningResults.phonesStandardized }}</span>
                </div>

                <div class="result-item" v-if="cleaningResults.addressesNormalized > 0">
                  <span>Addresses Normalized:</span>
                  <span>{{ cleaningResults.addressesNormalized }}</span>
                </div>

                <div class="result-item" v-if="cleaningResults.postalCodesCleaned > 0">
                  <span>Postal Codes Cleaned:</span>
                  <span>{{ cleaningResults.postalCodesCleaned }}</span>
                </div>

                <div class="result-actions">
                  <v-btn color="primary" @click="proceedToCalculations">
                    Proceed to Calculations
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

      <!-- CLEANED DATA PREVIEW -->
      <v-card v-if="cleaningResults" class="stats-card cleaned-data-preview" elevation="3">
        <v-card-title class="card-title">
          <v-icon class="title-icon">mdi-table-eye</v-icon>
          Cleaned Data Preview
          <v-spacer></v-spacer>
          <v-chip color="success" size="small">
            {{ cleaningResults.cleanedRows }} rows
          </v-chip>
        </v-card-title>

        <v-card-text>
          <v-alert type="info" class="mb-4">
            <strong>Preview of your cleaned dataset:</strong> Showing first 10 rows of {{ cleaningResults.cleanedRows }} cleaned rows.
            <br>
            <small>Original: {{ cleaningResults.originalRows }} rows → Cleaned: {{ cleaningResults.cleanedRows }} rows</small>
          </v-alert>

          <v-data-table
            :headers="getTableHeaders()"
            :items="filteredData"
            density="compact"
            class="preview-table"
            :loading="cleaning"
            v-model:items-per-page="itemsPerPage"
            :items-per-page-options="[5, 10, 25, 50]"
            :search="search"
          >
            <template v-slot:top>
              <v-toolbar flat color="transparent">
                <v-toolbar-title class="text-subtitle-1">
                  Dataset Columns: {{ Object.keys(uploadedData.value?.data?.[0] || {}).length }}
                </v-toolbar-title>
                <v-spacer></v-spacer>
                <v-text-field
                  v-model="search"
                  label="Search"
                  prepend-inner-icon="mdi-magnify"
                  variant="outlined"
                  density="compact"
                  style="max-width: 300px"
                  clearable
                ></v-text-field>
                <v-btn color="primary" variant="outlined" size="small" @click="exportCleanedData" class="ml-2">
                  <v-icon left>mdi-download</v-icon>
                  Export
                </v-btn>
              </v-toolbar>
            </template>
          </v-data-table>
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
import { dataAPI } from '../services/api'
import { useDataset } from '../composables/useDataset'

const router = useRouter()

// Use dataset composable for global state
const { datasetInfo, hasDataset, loadDataset, saveDataset, clearDataset } = useDataset()

const uploadedData = ref<any>(null)
const cleaning = ref(false)
const cleaningResults = ref<any>(null)
const uploadId = ref<string | null>(null)
const datasetPersisted = ref(true)
const itemsPerPage = ref(10)
const search = ref('')

const rowsValue = computed(() => uploadedData.value?.data?.length || 0)
const columnsValue = computed(() => getColumnCount())
const instrumentValue = computed(() => uploadedData.value?.instrumentType || 'N/A')
const fileValue = computed(() => uploadedData.value?.name || 'N/A')

const filteredData = computed(() => {
  if (!search.value) return getPreviewData()
  const searchTerm = search.value.toLowerCase()
  return getPreviewData().filter((row: any) => {
    return Object.values(row).some((value: any) => 
      String(value).toLowerCase().includes(searchTerm)
    )
  })
})

const cleaningKpiData = ref([
  {
    title: 'Rows',
    value: rowsValue,
    icon: 'mdi-table-row',
    color: 'rgba(11, 42, 68, 0.1)',
    iconColor: '#0B2A44',
    change: '',
    changeIcon: 'mdi-minus',
    changeClass: 'neutral'
  },
  {
    title: 'Columns',
    value: columnsValue,
    icon: 'mdi-column',
    color: 'rgba(30, 136, 229, 0.1)',
    iconColor: '#1E88E5',
    change: '',
    changeIcon: 'mdi-minus',
    changeClass: 'neutral'
  },
  {
    title: 'Instrument',
    value: instrumentValue,
    icon: 'mdi-chart-line',
    color: 'rgba(76, 175, 80, 0.1)',
    iconColor: '#4CAF50',
    change: '',
    changeIcon: 'mdi-minus',
    changeClass: 'neutral'
  },
  {
    title: 'File',
    value: fileValue,
    icon: 'mdi-file-document',
    color: 'rgba(255, 193, 7, 0.1)',
    iconColor: '#FFC107',
    change: '',
    changeIcon: 'mdi-minus',
    changeClass: 'neutral'
  }
])

const cleaningOptions = ref([
  // Data Quality Options
  { key:'removeDuplicates', label:'Remove Duplicates', description:'Delete duplicate rows based on all columns', value:true },
  { key:'fillMissingValues', label:'Fill Missing Values', description:'Replace empty/null values with appropriate defaults', value:true },
  { key:'removeOutliers', label:'Remove Outliers', description:'Identify and remove extreme statistical values', value:false },
  { key:'removeEmptyRows', label:'Remove Empty Rows', description:'Delete rows with no data or all null values', value:true },
  
  // Data Formatting Options
  { key:'standardizeText', label:'Standardize Text', description:'Convert text to consistent case and format', value:false },
  { key:'trimWhitespace', label:'Trim Whitespace', description:'Remove leading/trailing spaces from text fields', value:true },
  { key:'normalizeNumbers', label:'Normalize Numbers', description:'Standardize number formatting and decimal places', value:false },
  { key:'formatDates', label:'Format Dates', description:'Convert all dates to consistent format (YYYY-MM-DD)', value:false },
  { key:'validateEmails', label:'Validate Email Formats', description:'Check and fix email address formats', value:false },
  
  // Data Type Options
  { key:'convertDataTypes', label:'Convert Data Types', description:'Auto-detect and convert column data types', value:false },
  { key:'standardizeCurrency', label:'Standardize Currency', description:'Format all currency values consistently', value:false },
  { key:'normalizePercentages', label:'Normalize Percentages', description:'Convert percentage values to decimal format', value:false },
  
  // Data Validation Options
  { key:'validateRanges', label:'Validate Value Ranges', description:'Check if values fall within expected ranges', value:false },
  { key:'checkConsistency', label:'Check Consistency', description:'Verify data consistency across related fields', value:false },
  { key:'validatePatterns', label:'Validate Patterns', description:'Check text fields against expected patterns', value:false },
  
  // Advanced Cleaning Options
  { key:'removeSpecialChars', label:'Remove Special Characters', description:'Clean text by removing unwanted special characters', value:false },
  { key:'standardizePhoneNumbers', label:'Standardize Phone Numbers', description:'Format phone numbers to consistent pattern', value:false },
  { key:'normalizeAddresses', label:'Normalize Addresses', description:'Standardize address formatting and components', value:false },
  { key:'cleanPostalCodes', label:'Clean Postal Codes', description:'Format postal/zip codes consistently', value:false }
])

onMounted(() => {
  loadUploadedData()
})

const isAnyOptionSelected = computed(() =>
  cleaningOptions.value.some(o => o.value)
)

const loadUploadedData = async () => {
  try {
    // Use dataset composable to load data
    loadDataset()
    
    // Get the current dataset from localStorage
    const storedData = localStorage.getItem('currentDataset')
    if (storedData) {
      const dataset = JSON.parse(storedData)
      uploadedData.value = dataset
      uploadId.value = dataset.upload_id
      console.log('Loaded uploaded dataset from composable:', dataset)
    } else {
      // Fallback to uploadedDataset key if currentDataset not found
      const fallbackData = localStorage.getItem('uploadedDataset')
      if (fallbackData) {
        const dataset = JSON.parse(fallbackData)
        uploadedData.value = dataset
        uploadId.value = dataset.upload_id
        console.log('Loaded uploaded dataset from fallback:', dataset)
      } else {
        console.log('No uploaded dataset found, loading sample data')
        loadSampleData()
      }
    }
  } catch (error) {
    console.error('Error loading uploaded dataset:', error)
    loadSampleData()
  }
}

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

const deleteDataset = async () => {
  if (!uploadId.value) {
    console.error('No upload ID available for deletion')
    return
  }

  try {
    const response = await dataAPI.deleteDataset(uploadId.value)
    
    if (response.success) {
      console.log('Dataset deleted successfully')
      // Clear localStorage
      localStorage.removeItem('uploadedDataset')
      // Reset data
      uploadedData.value = null
      uploadId.value = null
      cleaningResults.value = null
      datasetPersisted.value = false
    } else {
      console.error('Failed to delete dataset:', response)
    }
  } catch (error) {
    console.error('Error deleting dataset:', error)
  }
}

const handleDataUpdate = (newData: any[]) => {
  if (uploadedData.value && uploadedData.value.data) {
    uploadedData.value.data = newData
    console.log('Original dataset updated:', newData.length, 'rows')
  }
}

const handleCleanedDataUpdate = (newData: any[]) => {
  if (cleaningResults.value && cleaningResults.value.cleanedData) {
    cleaningResults.value.cleanedData = newData
    console.log('Cleaned dataset updated:', newData.length, 'rows')
  }
}

const performCleaning = async () => {
  if (!uploadedData.value?.data) {
    console.error('No data available for cleaning')
    return
  }

  cleaning.value = true

  try {
    // Prepare cleaning options
    const options = {}
    cleaningOptions.value.forEach(option => {
      if (option.value) {
        options[option.key] = true
      }
    })

    // Call the cleaning API
    const response = await dataAPI.clean(uploadedData.value.data, options)
    
    if (response.success) {
      cleaningResults.value = response.stats
      // Update the uploaded data with cleaned data
      uploadedData.value.data = response.data
      console.log('Cleaning completed successfully:', response.stats)
    } else {
      console.error('Cleaning failed:', response)
    }
  } catch (error) {
    console.error('Error during cleaning:', error)
  } finally {
    cleaning.value = false
  }
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

const showCleanedDataPreview = () => {
  // Scroll to the preview section
  const previewSection = document.querySelector('.cleaned-data-preview')
  if (previewSection) {
    previewSection.scrollIntoView({ behavior: 'smooth' })
  }
}

const exportCleanedData = () => {
  if (!uploadedData.value?.data) {
    alert('No data to export')
    return
  }

  try {
    // Convert data to CSV
    const headers = Object.keys(uploadedData.value.data[0])
    const csvContent = [
      headers.join(','),
      ...uploadedData.value.data.map(row => 
        headers.map(header => {
          const value = row[header]
          // Handle values with commas by wrapping in quotes
          if (typeof value === 'string' && value.includes(',')) {
            return `"${value}"`
          }
          return value
        }).join(',')
      )
    ].join('\n')

    // Create download link
    const blob = new Blob([csvContent], { type: 'text/csv' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `cleaned_dataset_${new Date().toISOString().split('T')[0]}.csv`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.URL.revokeObjectURL(url)
  } catch (error) {
    console.error('Error exporting data:', error)
    alert('Error exporting data')
  }
}

const completeProcess = () => {
  // Save the final cleaned data to localStorage for all pages
  const finalData = {
    ...uploadedData.value,
    cleaningResults: cleaningResults.value,
    timestamp: new Date().toISOString()
  }
  
  // Save to multiple localStorage keys for persistence across pages
  localStorage.setItem('finalCleanedData', JSON.stringify(finalData))
  localStorage.setItem('currentDataset', JSON.stringify(finalData)) // For other pages
  localStorage.setItem('datasetStatus', 'completed') // Status indicator
  
  // Show completion message
  alert('Process completed successfully! Your cleaned data has been saved and is available on all pages.')
  
  console.log('Process completed:', finalData)
}

const proceedToCalculations = () => {
  localStorage.setItem('cleanedData', JSON.stringify({
    ...uploadedData.value,
    cleaningResults: cleaningResults.value
  }))
  router.push('/calculations')
}
</script>

<style scoped>
.cleaning-view {
  width: 100%;
  margin: 0 auto;
}

.dashboard-header {
  margin-bottom: 0;
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
  margin-bottom: 0;
}

.stats-card {
  border-radius: 12px;
  margin-bottom: 0;
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

/* KPI Styles - Matching DashboardView and ReportsView */
.kpi-row {
  margin-bottom: 0;
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

.result-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background: rgba(11, 42, 68, 0.03);
  border-radius: 8px;
  margin-bottom: 8px;
  transition: transform 0.2s ease;
}

.result-item:hover {
  transform: translateX(4px);
}

.result-item span:first-child {
  color: #666;
  font-weight: 500;
}

.result-item span:last-child {
  color: #0B2A44;
  font-weight: 700;
}

.result-actions {
  display: flex;
  gap: 12px;
  margin-top: 20px;
}

.desc {
  font-size: 12px;
  color: #666;
  margin-top: 4px;
}

.result-summary {
  margin-bottom: 16px;
}

.result-category {
  color: #0B2A44;
  font-size: 14px;
  font-weight: 600;
  margin: 12px 0 8px 0;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* Enhanced checkbox styling for better organization */
.v-checkbox {
  margin-bottom: 12px;
  padding: 8px;
  border-radius: 6px;
  transition: background-color 0.2s ease;
}

.v-checkbox:hover {
  background-color: rgba(11, 42, 68, 0.03);
}

.v-checkbox :deep(.v-label) {
  color: #333;
  font-size: 14px;
}

/* Scrollable options container */
.cleaning-options-container {
  max-height: 400px;
  overflow-y: auto;
  width: 100%;
}

/* Enhanced cleaned data preview */
.cleaned-data-preview {
  border: 2px solid rgba(76, 175, 80, 0.3);
  box-shadow: 0 4px 12px rgba(76, 175, 80, 0.15);
}

.cleaned-data-preview .v-card-title {
  background: linear-gradient(135deg, rgba(76, 175, 80, 0.1) 0%, rgba(76, 175, 80, 0.05) 100%);
  border-bottom: 2px solid rgba(76, 175, 80, 0.2);
}

.preview-table {
  border-radius: 8px;
  overflow: hidden;
}

.preview-table :deep(.v-data-table__thead) {
  background: linear-gradient(135deg, #0B2A44 0%, #1a3a5a 100%);
}

.preview-table :deep(.v-data-table__thead th) {
  color: white !important;
  font-weight: 600 !important;
}

/* Action buttons styling */
.action-buttons {
  display: flex;
  gap: 12px;
  margin-bottom: 0;
  flex-wrap: wrap;
}

.action-buttons .v-btn {
  min-width: 140px;
}

/* Scrollbar styling */
.cleaning-options-container::-webkit-scrollbar {
  width: 6px;
}

.cleaning-options-container::-webkit-scrollbar-track {
  background: rgba(11, 42, 68, 0.05);
  border-radius: 3px;
}

.cleaning-options-container::-webkit-scrollbar-thumb {
  background: rgba(11, 42, 68, 0.2);
  border-radius: 3px;
}

.cleaning-options-container::-webkit-scrollbar-thumb:hover {
  background: rgba(11, 42, 68, 0.3);
}

/* Enhanced checkbox styling */
.v-checkbox {
  margin-bottom: 16px;
}

.v-checkbox :deep(.v-label) {
  color: #333;
}

/* Responsive Design */
@media (max-width: 600px) {
  .cleaning-view {
    padding: 0 16px;
  }
  
  .action-buttons {
    flex-direction: column;
    gap: 8px;
  }
  
  .result-actions {
    flex-direction: column;
    gap: 8px;
  }
  
  .stat-value {
    font-size: 20px;
  }
}
</style>
```
