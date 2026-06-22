/** Helpers to save/load instrument page state in session */

export function buildWorkflowSnapshot({
  rawData,
  cleanedData,
  calculations,
  activeTab,
  uploadedFile,
  cleaningStats,
  columnMapping,
  mappingApplied,
  originalRawData,
  originalFileColumns,
  chartData,
  fredFilters,
  sessionSavedAt
}) {
  return {
    data: rawData || [],
    cleanedData: cleanedData || [],
    calculations: calculations || {},
    last_tab: activeTab || 'upload',
    uploaded_file_name: uploadedFile?.name || null,
    cleaningStats: cleaningStats || {},
    columnMapping: columnMapping || {},
    mappingApplied: !!mappingApplied,
    originalRawData: originalRawData || [],
    originalFileColumns: originalFileColumns || [],
    chartData: chartData || null,
    fredFilters: fredFilters || null,
    sessionSavedAt: sessionSavedAt || null,
    saved_at: new Date().toISOString()
  }
}

export function applyWorkflowToPage(wf, refs) {
  if (!wf) return false
  let ok = false
  if (wf.data?.length) {
    refs.rawData.value = wf.data
    ok = true
  }
  if (wf.originalRawData?.length) {
    refs.originalRawData.value = JSON.parse(JSON.stringify(wf.originalRawData))
    ok = true
  } else if (wf.data?.length && refs.originalRawData) {
    refs.originalRawData.value = JSON.parse(JSON.stringify(wf.data))
  }
  if (wf.originalFileColumns?.length && refs.originalFileColumns) {
    refs.originalFileColumns.value = [...wf.originalFileColumns]
  } else if (wf.data?.length && refs.originalFileColumns) {
    refs.originalFileColumns.value = Object.keys(wf.data[0] || {})
  }
  if (wf.columnMapping && refs.columnMapping) {
    refs.columnMapping.value = { ...wf.columnMapping }
  }
  if (refs.mappingApplied) {
    refs.mappingApplied.value = !!wf.mappingApplied
  }
  if (wf.cleanedData?.length) {
    refs.cleanedData.value = wf.cleanedData
    ok = true
  } else if (wf.data?.length) {
    refs.cleanedData.value = wf.data
  }
  if (wf.calculations && Object.keys(wf.calculations).length) {
    refs.calculations.value = wf.calculations
    ok = true
  }
  if (wf.uploaded_file_name) {
    refs.uploadedFile.value = { name: wf.uploaded_file_name, size: 0 }
    ok = true
  }
  if (wf.cleaningStats) refs.cleaningStats.value = wf.cleaningStats
  return ok
}
