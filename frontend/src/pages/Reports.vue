<template>
  <div class="card">
    <h3>Generate Report</h3>
    <button @click="generatePreview">Generate</button>
    <button @click="downloadReport">Download JSON</button>
    <button @click="markDone">Done (mark current dataset)</button>
  </div>
</template>

<script setup>
import { datasetAPI } from '@/services/api'
import { onMounted } from 'vue'

function generatePreview() { /* noop for simple page */ }

function downloadReport() { alert('Download not implemented in minimal page') }

async function markDone() {
  try {
    const current = JSON.parse(localStorage.getItem('currentDataset') || '{}')
    const id = current.id
    if (!id) return alert('No current dataset selected')
    const res = await datasetAPI.markDone(id)
    if (res && res.success) alert('Dataset marked done')
    else alert('Failed to mark dataset')
  } catch (e) { console.error(e); alert('Error') }
}
</script>