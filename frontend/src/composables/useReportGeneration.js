// Report generation logic extracted from InstrumentView
import { ref } from 'vue'
import api from '@/services/api.js'

export function useReportGeneration() {
  const reportPreviewDialog = ref(false)
  const reportPreviewHtml = ref('')
  const reportGenerating = ref(false)

  async function generateReport(reportType, data, options = {}) {
    reportGenerating.value = true
    try {
      const payload = {
        report_type: reportType,
        data: data,
        options: options
      }
      
      const response = await api.reportsAPI.generate(payload)
      
      if (response?.success) {
        if (reportType === 'html') {
          reportPreviewHtml.value = response.data.html
          reportPreviewDialog.value = true
        }
        return response.data
      }
    } catch (error) {
      console.error('Report generation error:', error)
      throw error
    } finally {
      reportGenerating.value = false
    }
  }

  async function downloadReport(reportType, data, options = {}) {
    try {
      const payload = {
        report_type: reportType,
        data: data,
        options: options
      }
      
      const response = await api.reportsAPI.download(payload)
      
      if (response?.success) {
        // Create download link
        const url = window.URL.createObjectURL(new Blob([response.data]))
        const link = document.createElement('a')
        link.href = url
        link.download = `report_${reportType}_${new Date().toISOString().split('T')[0]}.${reportType === 'word' ? 'docx' : 'xlsx'}`
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        window.URL.revokeObjectURL(url)
      }
    } catch (error) {
      console.error('Report download error:', error)
      throw error
    }
  }

  function closeReportPreview() {
    reportPreviewDialog.value = false
    reportPreviewHtml.value = ''
  }

  return {
    reportPreviewDialog,
    reportPreviewHtml,
    reportGenerating,
    generateReport,
    downloadReport,
    closeReportPreview
  }
}
