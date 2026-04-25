<template>
  <app-layout>
    <div class="reports-view">

      <!-- HEADER -->
      <div class="page-header">
        <h1 class="page-title">Report Generation</h1>
        <p class="page-subtitle">
          Generate comprehensive reports in PDF or Excel format with your financial analysis results
        </p>
      </div>

      <!-- DATA OVERVIEW -->
      <v-card class="overview-card" elevation="2">
        <v-card-title class="card-title">
          <v-icon class="title-icon">mdi-file-document</v-icon>
          Report Data Overview
        </v-card-title>

        <v-card-text>
          <v-row>
            <v-col cols="12" sm="3">
              <div class="stat-item">
                <div class="stat-value">{{ visualizationData?.calculations?.length || 0 }}</div>
                <div class="stat-label">Records</div>
              </div>
            </v-col>

            <v-col cols="12" sm="3">
              <div class="stat-item">
                <div class="stat-value">{{ visualizationData?.instrumentType || 'N/A' }}</div>
                <div class="stat-label">Instrument Type</div>
              </div>
            </v-col>

            <v-col cols="12" sm="3">
              <div class="stat-item">
                <div class="stat-value">{{ selectedFormat.toUpperCase() }}</div>
                <div class="stat-label">Export Format</div>
              </div>
            </v-col>

            <v-col cols="12" sm="3">
              <div class="stat-item">
                <div class="stat-value">{{ getSelectedSections().length }}</div>
                <div class="stat-label">Sections</div>
              </div>
            </v-col>
          </v-row>
        </v-card-text>
      </v-card>

      <!-- CONFIGURATION -->
      <v-card class="config-card" elevation="2">
        <v-card-title class="card-title">
          <v-icon class="title-icon">mdi-cog</v-icon>
          Report Configuration
        </v-card-title>

        <v-card-text>

          <!-- FORMAT SELECT -->
          <v-row>
            <v-col cols="12" sm="6">
              <v-select
                v-model="selectedFormat"
                :items="formatOptions"
                label="Export Format"
                variant="outlined"
                item-title="label"
                item-value="value"
              >
                <template v-slot:selection="{ item }">
                  <v-icon class="mr-2" :color="item.raw.color">
                    {{ item.raw.icon }}
                  </v-icon>
                  {{ item.raw.label }}
                </template>
              </v-select>
            </v-col>
          </v-row>

          <!-- ACTION BUTTONS -->
          <div class="action-buttons">
            <v-btn
              color="primary"
              variant="tonal"
              class="mr-2"
              @click="selectAllSections"
            >
              <v-icon left>mdi-check-all</v-icon>
              Select All
            </v-btn>

            <v-btn
              color="grey"
              variant="tonal"
              class="mr-2"
              @click="clearSections"
            >
              <v-icon left>mdi-close</v-icon>
              Clear
            </v-btn>

            <v-btn
              color="primary"
              variant="outlined"
              @click="goBack"
            >
              <v-icon left>mdi-arrow-left</v-icon>
              Back
            </v-btn>
          </div>

          <!-- SECTIONS -->
          <div class="sections-section">
            <h3 class="section-title">Include in Report:</h3>

            <v-row>
              <v-col
                v-for="section in reportSections"
                :key="section.key"
                cols="12"
                sm="6"
                md="4"
              >
                <v-card
                  class="section-card"
                  :class="{ selected: section.selected }"
                  @click="section.selected = !section.selected"
                >
                  <v-card-text class="text-center">
                    <v-icon :color="section.color" size="30">
                      {{ section.icon }}
                    </v-icon>

                    <div class="section-name">
                      {{ section.name }}
                    </div>

                    <div class="section-desc">
                      {{ section.description }}
                    </div>
                  </v-card-text>
                </v-card>
              </v-col>
            </v-row>
          </div>

          <!-- GENERATE BUTTON -->
          <v-btn
            color="primary"
            size="large"
            class="generate-btn"
            :loading="generating"
            :disabled="getSelectedSections().length === 0"
            @click="generateReport"
          >
            <v-icon left>mdi-download</v-icon>
            Generate {{ selectedFormat.toUpperCase() }} Report
          </v-btn>

        </v-card-text>
      </v-card>

      <!-- PREVIEW -->
      <v-card class="preview-card" elevation="2">
        <v-card-title class="card-title">
          <v-icon class="title-icon">mdi-eye</v-icon>
          Report Preview
        </v-card-title>

        <v-card-text>
          <v-alert type="info" variant="tonal" class="mb-4">
            This report will include selected sections
          </v-alert>

          <v-row>
            <v-col
              v-for="section in reportSections"
              :key="section.key"
              cols="12"
              md="4"
            >
              <v-card
                class="sample-section"
                :class="{ selected: section.selected }"
              >
                <v-card-text class="text-center">
                  <v-icon :color="section.color">
                    {{ section.icon }}
                  </v-icon>
                  <div class="sample-title">{{ section.name }}</div>
                </v-card-text>
              </v-card>
            </v-col>
          </v-row>

        </v-card-text>
      </v-card>

    </div>
  </app-layout>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import AppLayout from '../components/AppLayout.vue'

const router = useRouter()

const visualizationData = ref<any>(null)
const selectedFormat = ref('pdf')
const generating = ref(false)

const formatOptions = ref([
  { value: 'pdf', label: 'PDF Document', icon: 'mdi-file-pdf', color: '#0B2A44' },
  { value: 'excel', label: 'Excel Spreadsheet', icon: 'mdi-table', color: '#1E88E5' }
])

const reportSections = ref([
  { key: 'summary', name: 'Summary', description: 'Key insights', icon: 'mdi-chart-line', color: '#0B2A44', selected: true },
  { key: 'data', name: 'Data', description: 'Raw results', icon: 'mdi-table', color: '#1E88E5', selected: true },
  { key: 'charts', name: 'Charts', description: 'Visual graphs', icon: 'mdi-chart-pie', color: '#4CAF50', selected: true }
])

onMounted(() => {
  const stored = localStorage.getItem('visualizationData')
  if (stored) visualizationData.value = JSON.parse(stored)
})

const getSelectedSections = () =>
  reportSections.value.filter(s => s.selected)

const selectAllSections = () => {
  reportSections.value.forEach(s => s.selected = true)
}

const clearSections = () => {
  reportSections.value.forEach(s => s.selected = false)
}

const goBack = () => {
  router.push('/visualizations')
}

const generateReport = () => {
  generating.value = true

  setTimeout(() => {
    generating.value = false
    alert('Report generated successfully!')
  }, 2000)
}
</script>

<style scoped>
.reports-view {
  max-width: 1200px;
  margin: 0 auto;
}

.page-title {
  font-size: 32px;
  font-weight: 700;
  color: #0B2A44;
}

.page-subtitle {
  color: #666;
}

.stat-item {
  text-align: center;
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: #0B2A44;
}

.action-buttons {
  margin: 20px 0;
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.section-card {
  cursor: pointer;
  border-radius: 10px;
  transition: 0.3s;
}

.section-card:hover {
  transform: translateY(-3px);
}

.section-card.selected {
  border: 2px solid #0B2A44;
  background: rgba(11, 42, 68, 0.05);
}

.generate-btn {
  margin-top: 20px;
  width: 100%;
  height: 50px;
  font-weight: bold;
}
</style>