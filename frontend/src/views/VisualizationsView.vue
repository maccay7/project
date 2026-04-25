<template>
  <app-layout>
    <div class="visualizations-view">

      <div class="page-header">
        <h1 class="page-title">Data Visualizations</h1>
        <p class="page-subtitle">
          Visualize your financial calculations with interactive charts and graphs
        </p>
      </div>

      <!-- Overview -->
      <v-card class="overview-card" elevation="2">
        <v-card-title class="card-title">
          <v-icon class="title-icon">mdi-chart-line</v-icon>
          Calculation Overview
        </v-card-title>

        <v-card-text>
          <v-row>
            <v-col cols="12" sm="3">
              <div class="stat-item">
                <div class="stat-value">
                  {{ calculationData?.calculations?.length ?? 0 }}
                </div>
                <div class="stat-label">Records</div>
              </div>
            </v-col>

            <v-col cols="12" sm="3">
              <div class="stat-item">
                <div class="stat-value">
                  {{ calculationData?.instrumentType ?? 'N/A' }}
                </div>
                <div class="stat-label">Instrument Type</div>
              </div>
            </v-col>

            <v-col cols="12" sm="3">
              <div class="stat-item">
                <div class="stat-value">{{ getAverageYield() }}%</div>
                <div class="stat-label">Average Yield</div>
              </div>
            </v-col>

            <v-col cols="12" sm="3">
              <div class="stat-item">
                <div class="stat-value">{{ selectedChart }}</div>
                <div class="stat-label">Chart Type</div>
              </div>
            </v-col>
          </v-row>
        </v-card-text>
      </v-card>

      <!-- Chart Selection -->
      <v-card class="selection-card" elevation="2">
        <v-card-title class="card-title">
          <v-icon class="title-icon">mdi-chart-pie</v-icon>
          Select Visualization Type
        </v-card-title>

        <v-card-text>
          <div class="chart-buttons">
            <v-btn
              v-for="chart in chartTypes"
              :key="chart.value"
              :variant="selectedChart === chart.value ? 'flat' : 'outlined'"
              :color="selectedChart === chart.value ? 'primary' : undefined"
              class="chart-btn"
              @click="selectedChart = chart.value"
            >
              <v-icon start>{{ chart.icon }}</v-icon>
              {{ chart.label }}
            </v-btn>
          </div>
        </v-card-text>
      </v-card>

      <!-- Main Chart -->
      <v-card class="main-chart-card" elevation="2">
        <v-card-title class="card-title">
          <v-icon class="title-icon">mdi-chart-line</v-icon>
          {{ getMainChartTitle() }}
        </v-card-title>

        <v-card-text>
          <div class="chart-container">
            <canvas ref="mainChart"></canvas>
          </div>
        </v-card-text>
      </v-card>

      <!-- Action -->
      <v-card class="action-card" elevation="2">
        <v-card-text class="text-center">
          <v-btn color="primary" size="large" @click="proceedToReports">
            <v-icon start>mdi-arrow-right</v-icon>
            Proceed to Report Generation
          </v-btn>
        </v-card-text>
      </v-card>

    </div>
  </app-layout>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import AppLayout from '@/components/AppLayout.vue'

const router = useRouter()

const calculationData = ref<any>(null)
const selectedChart = ref('bar')
const mainChart = ref<HTMLCanvasElement | null>(null)

const chartTypes = [
  { value: 'bar', label: 'Bar Chart', icon: 'mdi-chart-bar' },
  { value: 'line', label: 'Line Chart', icon: 'mdi-chart-line' },
  { value: 'pie', label: 'Pie Chart', icon: 'mdi-chart-pie' },
  { value: 'area', label: 'Area Chart', icon: 'mdi-chart-area' }
]

onMounted(() => {
  const stored = localStorage.getItem('calculations')
  if (stored) {
    calculationData.value = JSON.parse(stored)
  }
})

const getAverageYield = () => {
  const list = calculationData.value?.calculations || []
  if (!list.length) return '0.00'

  const yields = list.map((c: any) =>
    parseFloat((c.yieldRate || '0').replace('%', ''))
  )

  const avg = yields.reduce((a: number, b: number) => a + b, 0) / yields.length
  return avg.toFixed(2)
}

const getMainChartTitle = () => {
  return {
    bar: 'Face Value vs Purchase Price',
    line: 'Yield Trend',
    pie: 'Distribution',
    area: 'Financial Breakdown'
  }[selectedChart.value] || 'Chart'
}

const proceedToReports = () => {
  router.push('/reports')
}
</script>