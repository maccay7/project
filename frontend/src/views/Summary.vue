<template>
  <FixedLayout>
    <div class="summary-page">
      <div class="page-header">
        <button class="back-btn" @click="goToDashboard">
          <v-icon>mdi-arrow-left</v-icon> Back to Dashboard
        </button>
        <h1>Portfolio Summary</h1>
        <p>Overall summary of all instruments in current session</p>
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
          </div>
        </div>
      </div>

      <div class="grand-total">
        <h2>Grand Total</h2>
        <p class="total-amount">${{ formatNumber(grandTotal) }}</p>
      </div>

      <div class="action-buttons">
        <button class="btn-primary" @click="downloadSummary">
          <v-icon>mdi-download</v-icon> Download Summary
        </button>
        <button class="btn-secondary" @click="goToDashboard">Back to Dashboard</button>
      </div>
    </div>
  </FixedLayout>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import FixedLayout from '@/components/FixedLayout.vue'

const router = useRouter()

const instruments = ref([
  { id: 'money-market', name: 'Money Market', icon: 'mdi-chart-line', gradient: 'linear-gradient(135deg, #1E88E5, #0B2044)', value: 0, count: 0 },
  { id: 'bonds', name: 'Bonds', icon: 'mdi-chart-timeline', gradient: 'linear-gradient(135deg, #4CAF50, #2E7D32)', value: 0, count: 0 },
  { id: 'tbills', name: 'T-Bills', icon: 'mdi-finance', gradient: 'linear-gradient(135deg, #FFC107, #FF9800)', value: 0, count: 0 }
])

const grandTotal = computed(() => {
  return instruments.value.reduce((sum, inst) => sum + inst.value, 0)
})

function formatNumber(num) {
  return num.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function loadSummary() {
  const summary = JSON.parse(localStorage.getItem('summary_totals') || '{}')
  instruments.value.forEach(inst => {
    inst.value = summary[inst.id] || 0
  })
  
  // Also load from active session
  const session = JSON.parse(localStorage.getItem('active_session') || '{}')
  if (session.instrumentData) {
    instruments.value.forEach(inst => {
      if (session.instrumentData[inst.id]) {
        inst.value = session.instrumentData[inst.id].totalValue || 0
        inst.count = session.instrumentData[inst.id].count || 0
      }
    })
  }
}

function downloadSummary() {
  const report = {
    title: 'Portfolio Summary',
    date: new Date().toLocaleString(),
    instruments: instruments.value.map(inst => ({
      name: inst.name,
      totalValue: inst.value,
      count: inst.count
    })),
    grandTotal: grandTotal.value
  }
  
  const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `summary_${Date.now()}.json`
  a.click()
  URL.revokeObjectURL(url)
}

function goToDashboard() {
  router.push('/dashboard')
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

.back-btn {
  background: transparent;
  border: none;
  color: #0B2044;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border-radius: 8px;
  margin-bottom: 20px;
}

.back-btn:hover {
  background: rgba(11,32,68,0.05);
}

.page-header h1 {
  color: #0B2044;
  font-size: 28px;
  font-weight: 700;
}

.page-header p {
  color: #666;
  font-size: 14px;
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
  padding: 24px;
  display: flex;
  align-items: center;
  gap: 20px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.05);
}

.card-icon {
  width: 60px;
  height: 60px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.card-content h3 {
  color: #0B2044;
  font-size: 16px;
  margin-bottom: 8px;
}

.card-content .amount {
  font-size: 24px;
  font-weight: 700;
  color: #0B2044;
  margin-bottom: 4px;
}

.card-content .count {
  font-size: 12px;
  color: #666;
}

.grand-total {
  background: linear-gradient(135deg, #0B2044, #1a3a6e);
  border-radius: 16px;
  padding: 30px;
  text-align: center;
  color: white;
  margin-bottom: 30px;
}

.grand-total h2 {
  font-size: 18px;
  margin-bottom: 10px;
  opacity: 0.9;
}

.grand-total .total-amount {
  font-size: 42px;
  font-weight: 800;
}

.action-buttons {
  display: flex;
  gap: 16px;
  justify-content: center;
}

.btn-primary {
  background: linear-gradient(135deg, #0B2044, #1E88E5);
  color: white;
  border: none;
  padding: 12px 28px;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.btn-secondary {
  background: white;
  color: #0B2044;
  border: 2px solid #0B2044;
  padding: 12px 28px;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}

@media (max-width: 768px) {
  .summary-cards {
    grid-template-columns: 1fr;
  }
}
</style>