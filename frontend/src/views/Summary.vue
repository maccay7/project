<template>
  <FixedLayout>
    <div class="summary-page">
      <div class="page-header hero-header">
        <div>
          <h1>Portfolio Summary</h1>
          <p class="subtitle">Consolidated valuation across Money Market, Bonds, and T-Bills</p>
          <div class="session-chip" v-if="activeSession">
            <v-icon size="16">mdi-folder-account</v-icon> {{ activeSession.name }}
          </div>
          <div v-else class="session-chip warn">No active session — open Dashboard first</div>
        </div>
        <div class="grand-pill">
          <span class="pill-label">Total portfolio</span>
          <span class="pill-amount">${{ formatNumber(grandTotal) }}</span>
          <span class="pill-sub">{{ totalInstruments }} instruments · {{ completedCount }}/3 classes done</span>
        </div>
      </div>

      <div class="kpi-strip">
        <div class="kpi-mini" v-for="k in quickKpis" :key="k.label">
          <v-icon size="20" :color="k.color">{{ k.icon }}</v-icon>
          <div>
            <span class="kpi-mini-val">{{ k.value }}</span>
            <span class="kpi-mini-lbl">{{ k.label }}</span>
          </div>
        </div>
      </div>

      <div class="section-header">
        <v-icon color="#0B2044" size="22">mdi-chart-areaspline</v-icon>
        <h2>Instrument breakdown</h2>
      </div>

      <div class="summary-cards">
        <div class="summary-card" v-for="inst in instruments" :key="inst.id">
          <div class="card-top" :style="{ background: inst.gradient }">
            <v-icon size="32" color="white">{{ inst.icon }}</v-icon>
            <h3>{{ inst.name }}</h3>
          </div>
          <div class="card-body">
            <div class="stat-row highlight">
              <span>Total value</span>
              <strong>${{ formatNumber(inst.value) }}</strong>
            </div>
            <div class="stat-row">
              <span>Count</span>
              <strong>{{ inst.count }}</strong>
            </div>
            <div class="stat-row" v-if="inst.avgRate !== null">
              <span>{{ inst.rateLabel }}</span>
              <strong>{{ inst.avgRate }}%</strong>
            </div>
            <div class="stat-row" v-if="inst.fredBench != null">
              <span>FRED benchmark</span>
              <strong>{{ inst.fredBench }}%</strong>
            </div>
            <div class="status-badge" :class="inst.statusClass">
              <v-icon size="14">{{ inst.statusIcon }}</v-icon> {{ inst.statusText }}
            </div>
            <button class="btn-open-inst" @click="openInstrument(inst.id)">Open workflow →</button>
          </div>
        </div>
      </div>

      <div class="action-buttons">
        <button class="btn-secondary" @click="goToDashboard">Dashboard</button>
        <button class="btn-primary" @click="goToReport">Continue to Report →</button>
      </div>

      <div class="workflow-card">
        <h3><v-icon size="20">mdi-progress-check</v-icon> Session workflow</h3>
        <p class="wf-hint">Each instrument saves upload, clean, calculate, and visualize steps to your session in the database.</p>
        <div class="workflow-steps">
          <span v-for="step in workflowSteps" :key="step" class="wf" :class="{ done: stepDone(step) }">{{ step }}</span>
        </div>
      </div>
    </div>
  </FixedLayout>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import FixedLayout from '@/components/FixedLayout.vue'
import sessionManager from '@/services/sessionManager.js'

const router = useRouter()
const activeSession = ref(null)
const instruments = ref([])

const grandTotal = computed(() => instruments.value.reduce((sum, inst) => sum + inst.value, 0))
const totalInstruments = computed(() => instruments.value.reduce((sum, inst) => sum + (inst.count || 0), 0))
const completedCount = computed(() => instruments.value.filter(i => i.completed).length)

const quickKpis = computed(() => [
  { label: 'Asset classes', value: `${completedCount.value}/3`, icon: 'mdi-layers-triple', color: '#0B2044' },
  { label: 'Session status', value: activeSession.value?.status === 'completed' ? 'Complete' : 'In progress', icon: 'mdi-folder-check', color: '#1E88E5' },
  { label: 'Last updated', value: lastUpdatedLabel.value, icon: 'mdi-clock-outline', color: '#4CAF50' }
])

const lastUpdatedLabel = computed(() => {
  const wfs = activeSession.value?.instrumentWorkflow || {}
  const dates = Object.values(wfs).map(w => w.saved_at).filter(Boolean)
  if (!dates.length) return '—'
  return new Date(Math.max(...dates.map(d => new Date(d).getTime()))).toLocaleDateString()
})

const workflowSteps = ['Upload', 'Clean', 'Calculate', 'Visualize', 'Report']

function stepDone(step) {
  return completedCount.value > 0
}

function formatNumber(num) {
  return (num || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function openInstrument(id) {
  if (!activeSession.value) {
    alert('Select a session on the Dashboard first')
    router.push('/dashboard')
    return
  }
  router.push({ path: `/instrument/${id}`, query: { session: activeSession.value.id } })
}

function goToDashboard() {
  router.push('/dashboard')
}

function goToReport() {
  if (!activeSession.value) {
    alert('No active session')
    return
  }
  router.push({ path: '/instrument/money-market', query: { session: activeSession.value.id, tab: 'reports' } })
}

async function loadSummary() {
  const aid = sessionManager.getActiveSessionId()
  if (aid) {
    await sessionManager.loadSessionFromDb(aid)
    activeSession.value = sessionManager.getSession(aid)
  } else {
    const all = sessionManager.getAllSessions()
    activeSession.value = all[0] || null
  }

  const templates = [
    { id: 'money-market', name: 'Money Market', icon: 'mdi-chart-line', gradient: 'linear-gradient(135deg, #1E88E5, #0B2044)', rateLabel: 'Avg interest rate' },
    { id: 'bonds', name: 'Bonds', icon: 'mdi-chart-timeline', gradient: 'linear-gradient(135deg, #4CAF50, #2E7D32)', rateLabel: 'Avg coupon' },
    { id: 'tbills', name: 'T-Bills', icon: 'mdi-finance', gradient: 'linear-gradient(135deg, #FFC107, #FF9800)', rateLabel: 'Avg discount' }
  ]

  instruments.value = templates.map(template => {
    const wf = activeSession.value ? sessionManager.getInstrumentWorkflow(activeSession.value.id, template.id) : null
    const calc = wf?.calculations || activeSession.value?.instrumentData?.[template.id] || {}
    const completed = !!wf?.calculations?.totalValue || !!calc.completed
    const value = parseFloat(calc.totalValue) || 0
    return {
      ...template,
      value,
      count: calc.instrumentCount || 0,
      avgRate: calc.avgRate || calc.avgCouponRate || calc.avgDiscountRate || null,
      fredBench: calc.fred?.benchmark_rate ?? null,
      completed,
      statusClass: completed ? 'completed' : value > 0 ? 'in-progress' : 'pending',
      statusText: completed ? 'Completed' : value > 0 ? 'In progress' : 'Not started',
      statusIcon: completed ? 'mdi-check-circle' : value > 0 ? 'mdi-progress-clock' : 'mdi-clock-outline'
    }
  })
}

onMounted(loadSummary)
</script>

<style scoped>
.summary-page { padding: 28px; max-width: 1200px; margin: 0 auto; }
.hero-header { display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 20px; margin-bottom: 24px; }
.hero-header h1 { color: #0B2044; font-size: 32px; margin: 0 0 8px; }
.subtitle { color: #666; margin: 0; }
.session-chip { display: inline-flex; align-items: center; gap: 6px; margin-top: 12px; padding: 6px 12px; background: #e8ecf1; border-radius: 20px; font-size: 13px; }
.session-chip.warn { background: #fff3e0; color: #e65100; }
.grand-pill { text-align: right; padding: 20px 28px; background: linear-gradient(135deg, #0B2044, #1E88E5); border-radius: 14px; color: white; box-shadow: 0 8px 24px rgba(11,32,68,0.2); }
.pill-label { display: block; font-size: 12px; opacity: 0.9; }
.pill-amount { font-size: 30px; font-weight: 700; display: block; }
.pill-sub { font-size: 12px; opacity: 0.85; }
.kpi-strip { display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 28px; }
.kpi-mini { display: flex; align-items: center; gap: 12px; padding: 14px 20px; background: white; border-radius: 12px; box-shadow: 0 2px 12px rgba(0,0,0,0.06); flex: 1; min-width: 160px; }
.kpi-mini-val { display: block; font-weight: 700; color: #0B2044; font-size: 16px; }
.kpi-mini-lbl { font-size: 12px; color: #666; }
.section-header { display: flex; align-items: center; gap: 10px; margin-bottom: 20px; }
.section-header h2 { color: #0B2044; margin: 0; font-size: 20px; }
.summary-cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; }
.summary-card { border-radius: 12px; overflow: hidden; box-shadow: 0 4px 16px rgba(11,32,68,0.1); background: white; }
.card-top { padding: 20px; color: white; display: flex; align-items: center; gap: 12px; }
.card-top h3 { margin: 0; font-size: 18px; }
.card-body { padding: 16px; }
.stat-row { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #eee; font-size: 14px; }
.stat-row.highlight strong { color: #0B2044; font-size: 16px; }
.status-badge { margin-top: 12px; padding: 8px 12px; border-radius: 8px; font-size: 12px; display: inline-flex; align-items: center; gap: 6px; }
.status-badge.completed { background: #e8f5e9; color: #2e7d32; }
.status-badge.in-progress { background: #e3f2fd; color: #1565c0; }
.status-badge.pending { background: #f5f5f5; color: #757575; }
.btn-open-inst { margin-top: 12px; width: 100%; padding: 10px; background: #0B2044; color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 13px; }
.btn-open-inst:hover { background: #1a3a6e; }
.action-buttons { display: flex; gap: 16px; justify-content: center; margin-top: 32px; }
.btn-primary, .btn-secondary { padding: 12px 28px; border-radius: 10px; font-size: 14px; font-weight: 600; cursor: pointer; border: none; }
.btn-primary { background: linear-gradient(135deg, #0B2044, #1E88E5); color: white; }
.btn-secondary { background: white; color: #0B2044; border: 2px solid #0B2044; }
.workflow-card { margin-top: 32px; padding: 24px; background: linear-gradient(135deg, #f8f9ff, #fff); border-radius: 12px; border: 1px solid #e8ecf1; }
.wf-hint { color: #666; font-size: 13px; margin: 8px 0 16px; }
.workflow-steps { display: flex; gap: 12px; flex-wrap: wrap; }
.wf { padding: 8px 16px; border-radius: 20px; background: #e0e0e0; font-size: 13px; }
.wf.done { background: #0B2044; color: white; }
</style>