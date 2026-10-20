<template>
  <div class="redirect-message">
    <h2>Redirecting to Reports...</h2>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()

onMounted(() => {
  const sessionId = route.query.session
  if (sessionId) {
    router.replace({ path: '/instrument/money-market', query: { session: sessionId, tab: 'reports' } })
  } else {
    router.replace({ path: '/instrument/money-market', query: { tab: 'reports' } })
  }
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
