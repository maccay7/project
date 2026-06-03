import { ref, computed } from 'vue'
import { datasetAPI } from '@/services/api'

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

  // Load dataset from backend by id (falls back to localStorage)
  const loadDatasetFromBackend = async (id) => {
    if (!id) return loadDataset()
    try {
      const res = await datasetAPI.load(id)
      if (res && res.success && res.data) {
        dataset.value = res.data
        datasetStatus.value = res.data.done ? 'completed' : 'uploaded'
        // mirror to localStorage for backward compatibility
        localStorage.setItem('currentDataset', JSON.stringify(dataset.value))
        localStorage.setItem('datasetStatus', datasetStatus.value)
        return true
      }
    } catch (err) {
      console.error('Backend load failed, falling back to localStorage', err)
    }
    return loadDataset()
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

  // Save dataset to backend (falls back to localStorage)
  const saveDatasetToBackend = async (data, status) => {
    try {
      // Mirror local state first
      dataset.value = data
      datasetStatus.value = status
      localStorage.setItem('currentDataset', JSON.stringify(data))
      localStorage.setItem('datasetStatus', status)

      // If dataset has an id or upload_id, attempt backend save
      const name = data.name || `dataset_${Date.now()}`
      const upload_id = data.id || data.upload_id || null
      const file_base64 = data.file_base64 || ''
      const sheet_names = data.headers || data.sheetNames || []
      const payloadData = data.data || data
      const headers = data.headers || null
      const instrument_type = data.instrumentType || data.instrument_type || null

      const res = await datasetAPI.save(name, file_base64, sheet_names, upload_id, payloadData, headers, instrument_type)
      if (res && res.success && res.data) {
        // update local mirror with returned id/name
        dataset.value.id = res.data.id
        dataset.value.name = res.data.name
        localStorage.setItem('currentDataset', JSON.stringify(dataset.value))
        return true
      }
    } catch (err) {
      console.error('Backend save failed, kept local copy', err)
    }
    return false
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
