<template>
  <FixedLayout>
    <div class="summary-page">
      <div class="page-header">
        <div class="header-title">
          <h1>Portfolio Summary</h1>
          <div class="session-name" v-if="activeSession">{{ activeSession.name }}</div>
          <div v-else class="session-name warning">No active session</div>
        </div>
      </div>
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
            <div class="card-stats">
              <div class="stat-item">
                <div class="stat-label">Total Value</div>
                <div class="stat-value">${{ formatNumber(inst.value) }}</div>
              </div>
              <div class="stat-item">
                <div class="stat-label">Count</div>
                <div class="stat-value">{{ inst.count }}</div>
              </div>
              <div class="stat-item" v-if="inst.avgRate !== null">
                <div class="stat-label">{{ inst.rateLabel }}</div>
                <div class="stat-value">{{ inst.avgRate }}%</div>
              </div>
              <div class="stat-item" v-if="inst.weightedAvg !== null">
                <div class="stat-label">Weighted Avg</div>
                <div class="stat-value">{{ inst.weightedAvg }}%</div>
              </div>
              <div class="stat-item" v-if="inst.totalInterest !== null">
                <div class="stat-label">{{ inst.interestLabel }}</div>
                <div class="stat-value">${{ formatNumber(inst.totalInterest) }}</div>
              </div>
            </div>
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
import FixedLayout from '@/components/FixedLayout.vue'

const activeSession = ref(null)
const instruments = ref([])

const grandTotal = computed(() => instruments.value.reduce((sum, inst) => sum + inst.value, 0))

function formatNumber(num) {
  return num.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function loadSummary() {
  const session = localStorage.getItem('active_session')
  if (session) activeSession.value = JSON.parse(session)

  const templates = [
    { id: 'money-market', name: 'Money Market', icon: 'mdi-chart-line', gradient: 'linear-gradient(135deg, #1E88E5, #0B2044)', rateLabel: 'Avg Interest Rate', interestLabel: 'Total Interest' },
    { id: 'bonds', name: 'Bonds', icon: 'mdi-chart-timeline', gradient: 'linear-gradient(135deg, #4CAF50, #2E7D32)', rateLabel: 'Avg Coupon Rate', interestLabel: 'Annual Income' },
    { id: 'tbills', name: 'T-Bills', icon: 'mdi-finance', gradient: 'linear-gradient(135deg, #FFC107, #FF9800)', rateLabel: 'Avg Discount Rate', interestLabel: 'Total Discount' }
  ]

  instruments.value = templates.map(template => {
    let data = null
    if (activeSession.value && activeSession.value.instrumentData && activeSession.value.instrumentData[template.id]) {
      data = activeSession.value.instrumentData[template.id]
    } else {
      const key = `${template.id}_session_${activeSession.value?.id || ''}_calc`
      const savedCalc = localStorage.getItem(key)
      if (savedCalc) data = JSON.parse(savedCalc)
    }

    let avgRate = null
    let weightedAvg = null
    let totalInterest = null
    if (data) {
      if (template.id === 'money-market') {
        avgRate = data.avgRate
        weightedAvg = data.weightedAvgRate
        totalInterest = data.totalInterest
      } else if (template.id === 'bonds') {
        avgRate = data.avgCouponRate
        weightedAvg = data.weightedAvgCoupon
        totalInterest = data.totalAnnualIncome
      } else if (template.id === 'tbills') {
        avgRate = data.avgDiscountRate
        weightedAvg = data.weightedAvgDiscount
        totalInterest = data.totalDiscount
      }
    }

    return {
      ...template,
      value: data?.totalValue || 0,
      count: data?.instrumentCount || 0,
      completed: data?.completed || false,
      avgRate: avgRate !== undefined && avgRate !== null ? parseFloat(avgRate).toFixed(2) : null,
      weightedAvg: weightedAvg !== undefined && weightedAvg !== null ? parseFloat(weightedAvg).toFixed(2) : null,
      totalInterest: totalInterest !== undefined && totalInterest !== null ? parseFloat(totalInterest) : null
    }
  })
}

onMounted(() => { loadSummary() })
</script>

<style scoped>
.summary-page { padding: 30px; max-width: 1200px; margin: 0 auto; }
.page-header { margin-bottom: 30px; }
.header-title h1 { color: #0B2044; font-size: 28px; font-weight: 700; margin: 0 0 12px 0; }
.session-name { font-size: 18px; font-weight: 700; color: #0B2044; background: linear-gradient(135deg, #f8f9ff, #fff); padding: 8px 20px; border-radius: 30px; display: inline-block; border: 1px solid rgba(11,32,68,0.1); box-shadow: 0 2px 8px rgba(0,0,0,0.05); }
.session-name.warning { background: #FFF3E0; color: #E65100; border-color: #FFE0B2; }
.section-header { display: flex; align-items: center; gap: 10px; margin-bottom: 20px; margin-top: 30px; }
.section-header h2 { color: #0B2044; font-size: 18px; font-weight: 600; margin: 0; }
.summary-cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; margin-bottom: 30px; }
.summary-card { background: white; border-radius: 16px; padding: 20px; display: flex; gap: 16px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); transition: all 0.3s; position: relative; overflow: hidden; }
.summary-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; background: linear-gradient(90deg, #0B2044, #1E88E5); transform: scaleX(0); transition: transform 0.3s ease; }
.summary-card:hover::before { transform: scaleX(1); }
.summary-card:hover { transform: translateY(-3px); box-shadow: 0 8px 20px rgba(0,0,0,0.1); }
.card-icon { width: 56px; height: 56px; border-radius: 14px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.card-content { flex: 1; }
.card-content h3 { color: #0B2044; font-size: 16px; font-weight: 600; margin-bottom: 12px; }
.card-stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(80px, 1fr)); gap: 12px; margin-bottom: 12px; }
.stat-item { text-align: center; }
.stat-label { font-size: 10px; color: #888; margin-bottom: 4px; text-transform: uppercase; letter-spacing: 0.5px; }
.stat-value { font-size: 16px; font-weight: 700; color: #0B2044; }
.status-badge { display: inline-flex; align-items: center; gap: 4px; padding: 3px 10px; border-radius: 20px; font-size: 10px; font-weight: 600; }
.status-badge.completed { background: #E8F5E9; color: #4CAF50; }
.status-badge.in-progress { background: #FFF3E0; color: #FF9800; }
.status-badge.pending { background: #f5f5f5; color: #999; }
.grand-total-card { background: linear-gradient(135deg, #0B2044, #1a3a6e); border-radius: 20px; padding: 30px; margin-bottom: 30px; color: white; }
.grand-total-content { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 20px; }
.grand-total-left h2 { font-size: 20px; font-weight: 700; margin-bottom: 5px; }
.grand-total-left p { opacity: 0.8; font-size: 13px; }
.grand-total-amount { font-size: 36px; font-weight: 800; }
@media (max-width: 900px) { .summary-cards { grid-template-columns: 1fr; gap: 16px; } .grand-total-content { flex-direction: column; text-align: center; } }
</style>