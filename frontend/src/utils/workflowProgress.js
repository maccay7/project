/** Sequential workflow step completion – each step green only when its process finished and all prior steps are done. */

export function checkStepCriteria(tab, state) {
  const {
    rawDataLength,
    mappingApplied,
    allColumnsMapped,
    cleanedDataLength,
    calculations,
    chartData,
    reportsSaved
  } = state

  switch (tab) {
    case 'upload':
      return rawDataLength > 0 && mappingApplied && allColumnsMapped
    case 'cleaning':
      return cleanedDataLength > 0
    case 'calculations':
      return !!(calculations && calculations.totalValue)
    case 'visualizations':
      return !!(chartData?.datasets && chartData.datasets.length > 0)
    case 'summary':
      return !!(calculations && calculations.totalValue)
    case 'reports':
      return !!reportsSaved || !!(calculations && calculations.totalValue)
    default:
      return false
  }
}

export function isStepCompleted(tab, steps, state) {
  const idx = steps.findIndex(s => s.tab === tab)
  if (idx === -1) return false
  for (let i = 0; i <= idx; i++) {
    if (!checkStepCriteria(steps[i].tab, state)) return false
  }
  return true
}

export function farthestAllowedIndex(steps, state) {
  for (let i = 0; i < steps.length; i++) {
    if (!checkStepCriteria(steps[i].tab, state)) return i
  }
  return steps.length - 1
}
