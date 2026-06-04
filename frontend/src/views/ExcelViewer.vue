<template>
  <div class="excel-viewer">
    <div class="excel-toolbar">
      <span>{{ data.length }} rows × {{ headers.length }} columns</span>
      <div class="pagination-controls">
        <button class="page-btn" @click="prevPage" :disabled="currentPage === 1">← Previous</button>
        <span class="page-info">Page {{ currentPage }} of {{ totalPages }}</span>
        <button class="page-btn" @click="nextPage" :disabled="currentPage === totalPages">Next →</button>
      </div>
    </div>
    <div class="excel-table-wrapper">
      <table class="excel-edit-table">
        <thead>
          <tr>
            <th class="row-number-col">#</th>
            <th v-for="col in headers" :key="col">{{ col }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, idx) in paginatedData" :key="idx">
            <td class="row-number">{{ (currentPage - 1) * pageSize + idx + 1 }}</td>
            <td v-for="col in headers" :key="col">
              <input type="text" :value="row[col]" @input="updateCell(row, col, $event.target.value)" class="editable-cell" />
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  data: { type: Array, required: true },
  headers: { type: Array, required: true }
})

const emit = defineEmits(['data-update'])

const pageSize = 10
const currentPage = ref(1)

const totalPages = computed(() => Math.ceil(props.data.length / pageSize))

const paginatedData = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  const end = start + pageSize
  return props.data.slice(start, end)
})

function prevPage() {
  if (currentPage.value > 1) currentPage.value--
}
function nextPage() {
  if (currentPage.value < totalPages.value) currentPage.value++
}

function updateCell(row, col, newValue) {
  row[col] = newValue
  emit('data-update', props.data)
}

watch(() => props.data, () => { currentPage.value = 1 }, { deep: true })
</script>

<style scoped>
.excel-viewer {
  border: 1px solid #ddd;
  border-radius: 8px;
  overflow: hidden;
  background: white;
}
.excel-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 16px;
  background: #f5f5f5;
  border-bottom: 1px solid #ddd;
  flex-wrap: wrap;
  gap: 12px;
}
.pagination-controls {
  display: flex;
  gap: 12px;
  align-items: center;
}
.page-btn {
  background: white;
  border: 1px solid #ccc;
  padding: 4px 12px;
  border-radius: 6px;
  cursor: pointer;
}
.page-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.page-info {
  font-size: 13px;
  color: #555;
}
.excel-table-wrapper {
  overflow-x: auto;
  max-height: 500px;
}
.excel-edit-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.excel-edit-table th,
.excel-edit-table td {
  border: 1px solid #ddd;
  padding: 6px 8px;
  text-align: left;
}
.excel-edit-table th {
  background: #f0f0f0;
  position: sticky;
  top: 0;
  z-index: 10;
}
.row-number-col {
  background: #f8f9ff;
  width: 50px;
  text-align: center;
}
.row-number {
  background: #f8f9ff;
  font-weight: 500;
  text-align: center;
}
.editable-cell {
  width: 100%;
  border: none;
  padding: 4px;
  font-family: inherit;
  background: transparent;
}
.editable-cell:focus {
  outline: 1px solid #0B2044;
  background: #f8f9ff;
}
</style>