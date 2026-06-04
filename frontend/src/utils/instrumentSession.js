/** Helpers to save/load instrument page state in session */

export function buildWorkflowSnapshot({
  rawData,
  cleanedData,
  calculations,
  activeTab,
  uploadedFile,
  cleaningStats
}) {
  return {
    data: rawData || [],
    cleanedData: cleanedData || [],
    calculations: calculations || {},
    last_tab: activeTab || 'upload',
    uploaded_file_name: uploadedFile?.name || null,
    cleaningStats: cleaningStats || {},
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
