// utils/instrumentSession.js
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
  yieldCurveData,
  fredFilters,
  sessionSavedAt,
  showPreview,
  completedSteps,
  workbookSheets,
  worksheetStatus,
  instrumentSummary,
  portfolioSummary
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
    yieldCurveData: yieldCurveData || [],
    fredFilters: fredFilters || null,
    sessionSavedAt: sessionSavedAt || null,
    showPreview: !!showPreview,
    completedSteps: completedSteps || [],
    workbookSheets: workbookSheets || [],
    worksheetStatus: worksheetStatus || {},
    instrumentSummary: instrumentSummary || { columns: [], rows: [] },
    portfolioSummary: portfolioSummary || { columns: [], rows: [] },
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
  if (wf.yieldCurveData?.length && refs.yieldCurveData) {
    refs.yieldCurveData.value = wf.yieldCurveData
  }
  if (wf.fredFilters && refs.fredFilters) {
    refs.fredFilters.value = { ...refs.fredFilters.value, ...wf.fredFilters }
  }
  if (wf.completedSteps?.length && refs.completedSteps) {
    refs.completedSteps.value = new Set(wf.completedSteps)
  }
  if (wf.showPreview !== undefined && refs.showPreview) {
    refs.showPreview.value = !!wf.showPreview
  }
  if (wf.workbookSheets?.length && refs.workbookSheets) {
    refs.workbookSheets.value = wf.workbookSheets
    ok = true
  }
  if (wf.worksheetStatus && refs.worksheetStatus) {
    refs.worksheetStatus.value = { ...wf.worksheetStatus }
  }
  if (wf.instrumentSummary && refs.instrumentSummary) {
    refs.instrumentSummary.value = { ...wf.instrumentSummary }
  }
  if (wf.portfolioSummary && refs.portfolioSummary) {
    refs.portfolioSummary.value = { ...wf.portfolioSummary }
  }
  return ok
}