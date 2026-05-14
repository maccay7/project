<template>
  <FixedLayout>
    <div class="summary-page">
      <div class="page-header">
        <div class="header-title">
          <h1>Portfolio Summary</h1>
          <div class="session-name" v-if="activeSession">
            {{ activeSession.name }}
          </div>
          <div v-else class="session-name warning">
            No active session
          </div>
        </div>
      </div>

      <!-- Instrument Summary Cards -->
      <div class="section-header">
        <v-icon color="#0B2044" size="20">mdi-chart-areaspline</v-icon>
        <h2>Instrument Breakdown</h2>
      </div>

      <div class="summary-cards">
        <div class="summary-card" v-for="inst in instruments" :key="inst.id">
          <div class="card-icon" :style="{ background: inst.gradient }">
            <v-icon size="28" color="white">{{ inst.icon }}</v-icon>
          </div>
          <div class="card-content">
            <h3>{{ inst.name }}</h3>
            <p class="amount">${{ formatNumber(inst.value) }}</p>
            <p class="count">{{ inst.count }} instruments</p>
            <div v-if="inst.completed" class="status-badge completed">
              <v-icon size="12">mdi-check-circle</v-icon> Completed
            </div>
            <div v-else-if="inst.value > 0" class="status-badge in-progress">
              <v-icon size="12">mdi-progress-clock</v-icon> In Progress
            </div>
            <div v-else class="status-badge pending">
              <v-icon size="12">mdi-clock-outline</v-icon> Not Started
            </div>
          </div>
        </div>
      </div>

      <!-- Grand Total Card -->
      <div class="grand-total-card">
        <div class="grand-total-content">
          <div class="grand-total-left">
            <h2>Grand Total</h2>
            <p>Combined value of all instruments</p>
          </div>
          <div class="grand-total-right">
            <div class="grand-total-amount">${{ formatNumber(grandTotal) }}</div>
          </div>
        </div>
      </div>
    </div>
  </FixedLayout>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import FixedLayout from '@/components/FixedLayout.vue'

const router = useRouter()
const activeSession = ref(null)

const instruments = ref([
  { 
    id: 'money-market', 
    name: 'Money Market', 
    icon: 'mdi-chart-line', 
    gradient: 'linear-gradient(135deg, #1E88E5, #0B2044)', 
    value: 0, 
    count: 0,
    completed: false
  },
  { 
    id: 'bonds', 
    name: 'Bonds', 
    icon: 'mdi-chart-timeline', 
    gradient: 'linear-gradient(135deg, #4CAF50, #2E7D32)', 
    value: 0, 
    count: 0,
    completed: false
  },
  { 
    id: 'tbills', 
    name: 'T-Bills', 
    icon: 'mdi-finance', 
    gradient: 'linear-gradient(135deg, #FFC107, #FF9800)', 
    value: 0, 
    count: 0,
    completed: false
  }
])

const grandTotal = computed(() => {
  return instruments.value.reduce((sum, inst) => sum + inst.value, 0)
})

function formatNumber(num) {
  return num.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function loadSummary() {
  const session = localStorage.getItem('active_session')
  if (session) {
    activeSession.value = JSON.parse(session)
  }
  
  if (activeSession.value && activeSession.value.instrumentData) {
    instruments.value.forEach(inst => {
      const data = activeSession.value.instrumentData[inst.id]
      if (data) {
        inst.value = data.totalValue || 0
        inst.count = data.count || 0
        inst.completed = data.completed || false
      }
    })
  }
  
  const summary = JSON.parse(localStorage.getItem('summary_totals') || '{}')
  instruments.value.forEach(inst => {
    if (summary[inst.id] && !inst.value) {
      inst.value = summary[inst.id]
    }
  })
  
  if (activeSession.value && activeSession.value.completedInstruments) {
    instruments.value.forEach(inst => {
      if (activeSession.value.completedInstruments[inst.id]) {
        inst.completed = true
      }
    })
  }
}

onMounted(() => {
  loadSummary()
})
</script>

<style scoped>
.summary-page {
  padding: 30px;
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 30px;
}

.header-title h1 {
  color: #0B2044;
  font-size: 28px;
  font-weight: 700;
  margin: 0 0 12px 0;
}

.session-name {
  font-size: 18px;
  font-weight: 700;
  color: #0B2044;
  background: linear-gradient(135deg, #f8f9ff, #fff);
  padding: 8px 20px;
  border-radius: 30px;
  display: inline-block;
  border: 1px solid rgba(11,32,68,0.1);
  box-shadow: 0 2px 8px rgba(0,0,0,0.05);
}

.session-name.warning {
  background: #FFF3E0;
  color: #E65100;
  border-color: #FFE0B2;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 20px;
  margin-top: 30px;
}

.section-header h2 {
  color: #0B2044;
  font-size: 18px;
  font-weight: 600;
  margin: 0;
}

.summary-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
  margin-bottom: 30px;
}

.summary-card {
  background: white;
  border-radius: 16px;
  padding: 20px;
  display: flex;
  gap: 16px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.05);
  transition: all 0.3s;
  position: relative;
  overflow: hidden;
}

.summary-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, #0B2044, #1E88E5);
  transform: scaleX(0);
  transition: transform 0.3s ease;
}

.summary-card:hover::before {
  transform: scaleX(1);
}

.summary-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 20px rgba(0,0,0,0.1);
}

.card-icon {
  width: 56px;
  height: 56px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.card-content {
  flex: 1;
}

.card-content h3 {
  color: #0B2044;
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 8px;
}

.card-content .amount {
  font-size: 22px;
  font-weight: 700;
  color: #0B2044;
  margin-bottom: 4px;
}

.card-content .count {
  font-size: 11px;
  color: #666;
  margin-bottom: 8px;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 10px;
  border-radius: 20px;
  font-size: 10px;
  font-weight: 600;
}

.status-badge.completed {
  background: #E8F5E9;
  color: #4CAF50;
}

.status-badge.in-progress {
  background: #FFF3E0;
  color: #FF9800;
}

.status-badge.pending {
  background: #f5f5f5;
  color: #999;
}

.grand-total-card {
  background: linear-gradient(135deg, #0B2044, #1a3a6e);
  border-radius: 20px;
  padding: 30px;
  margin-bottom: 30px;
  color: white;
}

.grand-total-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 20px;
}

.grand-total-left h2 {
  font-size: 20px;
  font-weight: 700;
  margin-bottom: 5px;
}

.grand-total-left p {
  opacity: 0.8;
  font-size: 13px;
}

.grand-total-amount {
  font-size: 36px;
  font-weight: 800;
}

@media (max-width: 900px) {
  .summary-cards {
    grid-template-columns: 1fr;
    gap: 16px;
  }
  
  .grand-total-content {
    flex-direction: column;
    text-align: center;
  }
}
</style>