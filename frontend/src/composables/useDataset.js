import { ref, computed } from 'vue'

// Global dataset state
const dataset = ref(null)
const datasetStatus = ref('none') // 'none', 'uploaded', 'cleaning', 'completed'

export function useDataset() {
  // Load dataset from localStorage
  const loadDataset = () => {
    try {
      const currentDataset = localStorage.getItem('currentDataset')
      const status = localStorage.getItem('datasetStatus')
      
      if (currentDataset) {
        dataset.value = JSON.parse(currentDataset)
      }
      
      if (status) {
        datasetStatus.value = status
      }
    } catch (error) {
      console.error('Error loading dataset:', error)
    }
  }

  // Save dataset to localStorage
  const saveDataset = (data, status) => {
    try {
      dataset.value = data
      datasetStatus.value = status
      
      localStorage.setItem('currentDataset', JSON.stringify(data))
      localStorage.setItem('datasetStatus', status)
    } catch (error) {
      console.error('Error saving dataset:', error)
    }
  }

  // Clear dataset
  const clearDataset = () => {
    dataset.value = null
    datasetStatus.value = 'none'
    
    localStorage.removeItem('currentDataset')
    localStorage.removeItem('datasetStatus')
    localStorage.removeItem('uploadedDataset')
    localStorage.removeItem('finalCleanedData')
    localStorage.removeItem('datasetInfo')
  }

  // Computed properties for easy access
  const datasetInfo = computed(() => {
    if (!dataset.value) return null
    
    return {
      name: dataset.value.name || 'Unknown',
      rows: dataset.value.data?.length || 0,
      columns: dataset.value.display_headers?.length || Object.keys(dataset.value.data?.[0] || {}).length,
      instrumentType: dataset.value.instrumentType || 'Unknown',
      uploadId: dataset.value.upload_id,
      timestamp: dataset.value.timestamp,
      status: datasetStatus.value
    }
  })

  const hasDataset = computed(() => dataset.value !== null)
  const isUploaded = computed(() => datasetStatus.value === 'uploaded')
  const isCleaning = computed(() => datasetStatus.value === 'cleaning')
  const isCompleted = computed(() => datasetStatus.value === 'completed')

  return {
    // State
    dataset,
    datasetStatus,
    
    // Computed
    datasetInfo,
    hasDataset,
    isUploaded,
    isCleaning,
    isCompleted,
    
    // Methods
    loadDataset,
    saveDataset,
    clearDataset
  }
}
