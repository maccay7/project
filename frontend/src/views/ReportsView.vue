<template>
  <fixed-layout>
    <div class="reports-view">

      <!-- Header Section -->
      <div class="dashboard-header">
        <h1 class="page-title">Report Generation</h1>
        <p class="page-subtitle">Generate comprehensive reports in multiple formats</p>
      </div>

      <!-- DATA OVERVIEW -->
      <v-card class="stats-card" elevation="2">
        <v-card-title class="card-title">
          <v-icon class="title-icon">mdi-file-document</v-icon>
          Report Data Overview
        </v-card-title>

        <v-card-text>
          <v-row class="kpi-row">
            <v-col cols="12" sm="6" md="3" v-for="kpi in reportKpiData" :key="kpi.title">
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

      <!-- CONFIGURATION -->
      <v-card class="config-card" elevation="2">
        <v-card-title class="card-title">
          <v-icon class="title-icon">mdi-cog</v-icon>
          Report Configuration
        </v-card-title>

        <v-card-text>

          
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

      <!-- FORMAT FILTER -->
      <v-card class="stats-card" elevation="2">
        <v-card-title class="card-title">
          <v-icon class="title-icon">mdi-filter</v-icon>
          Export Format
        </v-card-title>

        <v-card-text>
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
        </v-card-text>
      </v-card>

    </div>
  </fixed-layout>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import FixedLayout from '../components/FixedLayout.vue'

const router = useRouter()

const visualizationData = ref<any>(null)
const selectedFormat = ref('pdf')

const recordsValue = computed(() => visualizationData.value?.calculations?.length || 0)
const instrumentTypeValue = computed(() => visualizationData.value?.instrumentType || 'N/A')
const exportFormatValue = computed(() => selectedFormat.value.toUpperCase())
const sectionsValue = computed(() => getSelectedSections().length)

const reportKpiData = ref([
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
    icon: 'mdi-chart-line',
    color: 'rgba(30, 136, 229, 0.1)',
    iconColor: '#1E88E5',
    change: '0%',
    changeIcon: 'mdi-minus',
    changeClass: 'neutral'
  },
  {
    title: 'Export Format',
    value: exportFormatValue,
    icon: 'mdi-file-export',
    color: 'rgba(76, 175, 80, 0.1)',
    iconColor: '#4CAF50',
    change: '0%',
    changeIcon: 'mdi-minus',
    changeClass: 'neutral'
  },
  {
    title: 'Sections',
    value: sectionsValue,
    icon: 'mdi-view-list',
    color: 'rgba(255, 193, 7, 0.1)',
    iconColor: '#FFC107',
    change: '0%',
    changeIcon: 'mdi-minus',
    changeClass: 'neutral'
  }
])

const formatOptions = ref([
  { value: 'pdf', label: 'PDF Document', icon: 'mdi-file-pdf', color: '#0B2A44' },
  { value: 'excel', label: 'Excel Spreadsheet', icon: 'mdi-file-excel', color: '#1E88E5' },
  { value: 'csv', label: 'CSV File', icon: 'mdi-file-delimited', color: '#4CAF50' },
  { value: 'json', label: 'JSON Data', icon: 'mdi-code-json', color: '#FF9800' },
  { value: 'word', label: 'Word Document', icon: 'mdi-file-word', color: '#2196F3' },
  { value: 'powerpoint', label: 'PowerPoint', icon: 'mdi-file-powerpoint', color: '#F44336' },
  { value: 'xml', label: 'XML File', icon: 'mdi-code-tags', color: '#9C27B0' },
  { value: 'html', label: 'HTML Report', icon: 'mdi-language-html5', color: '#E91E63' },
  { value: 'txt', label: 'Text File', icon: 'mdi-file-document', color: '#607D8B' }
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

</script>

<style scoped>
.reports-view {
  max-width: 1400px;
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

/* KPI Styles - Matching DashboardView */
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

/* Card Title Styles */
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

/* Stats Card Styles */
.stats-card {
  border-radius: 12px;
  margin-bottom: 32px;
  background: white;
  border: 1px solid rgba(11, 42, 68, 0.08);
  position: relative;
}

/* Config Card Styles */
.config-card {
  border-radius: 12px;
  margin-bottom: 32px;
  background: white;
  border: 1px solid rgba(11, 42, 68, 0.08);
  position: relative;
}

.config-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, #0B2A44, #1E88E5);
}

/* Preview Card Styles */
.preview-card {
  border-radius: 12px;
  margin-bottom: 32px;
  background: white;
  border: 1px solid rgba(11, 42, 68, 0.08);
  position: relative;
}

.preview-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, #0B2A44, #1E88E5);
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

.section-name {
  font-weight: 600;
  color: #0B2A44;
  margin-top: 8px;
  margin-bottom: 4px;
}

.section-desc {
  font-size: 12px;
  color: #666;
  margin-top: 4px;
}

.sample-section {
  border-radius: 8px;
  transition: transform 0.2s ease;
  border: 1px solid rgba(11, 42, 68, 0.08);
}

.sample-section:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.sample-section.selected {
  border: 2px solid #0B2A44;
  background: rgba(11, 42, 68, 0.05);
}

.sample-title {
  font-weight: 600;
  color: #0B2A44;
  margin-top: 8px;
}

</style>