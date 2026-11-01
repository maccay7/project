// Excel upload and parsing logic extracted from InstrumentView
import { ref } from 'vue'
import * as XLSX from 'xlsx'
import { API_BASE_URL } from '@/config.js'

export function useExcelUpload() {
  const uploadedFile = ref(null)
  const uploadedFileId = ref(null)
  const uploadedFilePath = ref(null)
  const uploadedFileBase64 = ref(null)
  const rawData = ref([])
  const originalRawData = ref([])
  const originalFileColumns = ref([])
  const originalFileBuffer = ref(null)
  const originalDatasetId = ref(null)
  const fileLoading = ref(false)
  const uploadError = ref('')
  const uploadProgress = ref(0)
  const uploadHistory = ref([])
  const sheetTotalRows = ref(0)
  const sheetType = ref('multi')
  const currentSheetName = ref('')
  const currentWorkbookName = ref('')

  function handleFileUpload(event) {
    const file = event.target.files[0]
    if (!file) return

    uploadedFile.value = file
    uploadError.value = ''
    fileLoading.value = true
    uploadProgress.value = 0

    const reader = new FileReader()
    reader.onload = (e) => {
      const buffer = e.target.result
      uploadedFileBase64.value = buffer.toString('base64')
      parseExcelFile(buffer, file.name)
    }
    reader.readAsArrayBuffer(file)
  }

  function parseExcelFile(buffer, fileName) {
    try {
      const workbook = XLSX.read(buffer, { type: 'array' })
      const sheetNames = workbook.SheetNames
      
      if (sheetNames.length === 0) {
        uploadError.value = 'No sheets found in workbook'
        fileLoading.value = false
        return
      }

      currentWorkbookName.value = fileName
      sheetTotalRows.value = 0

      const parsedData = {}
      sheetNames.forEach(sheetName => {
        const worksheet = workbook.Sheets[sheetName]
        const json = XLSX.utils.sheet_to_json(worksheet, { defval: '' })
        parsedData[sheetName] = json
        sheetTotalRows.value += json.length
      })

      // Determine sheet type
      const hasMultipleSheets = sheetNames.length > 1
      sheetType.value = hasMultipleSheets ? 'multi' : 'single'
      currentSheetName.value = sheetNames[0]
      rawData.value = parsedData[currentSheetName.value] || []
      originalRawData.value = JSON.parse(JSON.stringify(rawData.value))
      originalFileColumns.value = Object.keys(rawData.value[0] || [])
      originalFileBuffer.value = buffer

      // Add to history
      uploadHistory.value.unshift({
        name: fileName,
        date: new Date().toISOString(),
        data: parsedData
      })

      fileLoading.value = false
      uploadProgress.value = 100
    } catch (error) {
      uploadError.value = `Error parsing file: ${error.message}`
      fileLoading.value = false
    }
  }

  function removeFile() {
    uploadedFile.value = null
    uploadedFileId.value = null
    uploadedFilePath.value = null
    uploadedFileBase64.value = null
    rawData.value = []
    originalRawData.value = []
    originalFileColumns.value = []
    originalFileBuffer.value = null
    originalDatasetId.value = null
    sheetTotalRows.value = 0
    sheetType.value = 'multi'
    currentSheetName.value = ''
    currentWorkbookName.value = ''
    uploadProgress.value = 0
  }

  function deleteHistoryItem(index) {
    uploadHistory.value.splice(index, 1)
  }

  function loadHistoryFile(item) {
    uploadedFile.value = { name: item.name }
    currentWorkbookName.value = item.name
    const sheetNames = Object.keys(item.data)
    sheetType.value = sheetNames.length > 1 ? 'multi' : 'single'
    currentSheetName.value = sheetNames[0]
    rawData.value = item.data[currentSheetName.value] || []
    originalRawData.value = JSON.parse(JSON.stringify(rawData.value))
    originalFileColumns.value = Object.keys(rawData.value[0] || [])
    sheetTotalRows.value = Object.values(item.data).reduce((sum, sheet) => sum + sheet.length, 0)
  }

  function getFileSize() {
    if (!uploadedFile.value) return ''
    const bytes = uploadedFile.value.size
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB'
    return (bytes / (1024 * 1024)).toFixed(2) + ' MB'
  }

  return {
    uploadedFile,
    uploadedFileId,
    uploadedFilePath,
    uploadedFileBase64,
    rawData,
    originalRawData,
    originalFileColumns,
    originalFileBuffer,
    originalDatasetId,
    fileLoading,
    uploadError,
    uploadProgress,
    uploadHistory,
    sheetTotalRows,
    sheetType,
    currentSheetName,
    currentWorkbookName,
    handleFileUpload,
    parseExcelFile,
    removeFile,
    deleteHistoryItem,
    loadHistoryFile,
    getFileSize
  }
}
