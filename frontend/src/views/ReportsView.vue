<template>
  <div class="redirect-message">
    <h2>Opening Report...</h2>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()

onMounted(() => {
  const sessionId = route.query.session || localStorage.getItem('dura_active_session_id') || null
  const lastInstrument = localStorage.getItem('dura_last_instrument') || 'money-market'
  router.replace({ path: `/instrument/${lastInstrument}`, query: { session: sessionId, tab: 'reports' } })
})
</script>

<style scoped>
.redirect-message {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: #f5f7fa;
  text-align: center;
}
.redirect-message h2 {
  color: #0B2044;
  margin-bottom: 16px;
}
</style>