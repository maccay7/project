const fs = require('fs')
const path = require('path')

const viewsDir = path.join(__dirname, '../frontend/src/views')

for (const file of ['MoneyMarket.vue', 'TreasuryBills.vue']) {
  const filePath = path.join(viewsDir, file)
  let content = fs.readFileSync(filePath, 'utf8')

  const replacements = [
    [
      "import { buildWorkflowSnapshot, applyWorkflowToPage } from '@/utils/instrumentSession.js'",
      `import { buildWorkflowSnapshot, applyWorkflowToPage } from '@/utils/instrumentSession.js'
import { useInstrumentConfig } from '@/composables/useInstrumentConfig.js'
import { isStepCompleted as checkStepDone, farthestAllowedIndex as calcFarthestAllowed } from '@/utils/workflowProgress.js'
import { autoMatchColumns as matchColumns, applyMappingToRows, isColumnMapped, getMissingColumns } from '@/utils/instrumentMapping.js'`
    ],
    [
      `:headers="uploadPreviewHeaders"
                  :show-mapping-controls="true"`,
      `:headers="uploadPreviewHeaders"
                  :original-data="originalRawData.slice(0, 500)"
                  :original-headers="originalFileColumns"
                  :show-mapping-controls="true"`
    ],
    [
      `:class="{ 'missing-column': !mappingApplied && !hasRequiredColumn(col), 'mapped-column': mappingApplied }"`,
      `:class="{ 'missing-column': !hasRequiredColumn(col), 'mapped-column': hasRequiredColumn(col) }"`
    ],
    [
      `{{ mappingApplied ? 'mdi-check' : (rawData.length && hasRequiredColumn(col) ? 'mdi-circle-outline' : 'mdi-close') }}`,
      `{{ hasRequiredColumn(col) ? 'mdi-check' : 'mdi-close' }}`
    ],
    [
      `<div v-if="rawData.length && missingColumns.length && !mappingApplied" class="warning-message">`,
      `<div v-if="rawData.length && missingColumns.length" class="warning-message">`
    ],
    [
      `<div v-if="mappingApplied" class="success-message">`,
      `<div v-if="rawData.length && missingColumns.length === 0" class="success-message">`
    ],
    [
      `const mappingApplied = ref(false)

function refreshPage() {
  rawData.value = []`,
      `const mappingApplied = ref(false)
const originalRawData = ref([])
const originalFileColumns = ref([])
const sessionSavedAt = ref(null)
const { requiredColumns, columnVariations, workflowSteps, loadConfig } = useInstrumentConfig()

function refreshPage() {
  rawData.value = []
  originalRawData.value = []
  originalFileColumns.value = []`
    ],
    [
      `  mappingApplied.value = false
}

function isStepCompleted(tab) {
  if (tab === 'upload') return rawData.value.length > 0 && mappingApplied.value
  if (tab === 'cleaning') return cleanedData.value.length > 0
  if (tab === 'calculations') return !!calculations.value.totalValue
  if (tab === 'visualizations') return !!(chartData.value.datasets && chartData.value.datasets.length > 0)
  if (tab === 'summary') return !!calculations.value.totalValue
  if (tab === 'reports') return !!calculations.value.totalValue
  return false
}

const farthestAllowedIndex = computed(() => {
  for (let i = 0; i < steps.length; i++) {
    if (!isStepCompleted(steps[i].tab)) {
      return i
    }
  }
  return steps.length - 1
})`,
      `  mappingApplied.value = false
  sessionSavedAt.value = null
}

const steps = computed(() => {
  if (workflowSteps.value.length) {
    return workflowSteps.value.map(s => ({ tab: s.tab, name: s.name }))
  }
  return [
    { tab: 'upload', name: 'Upload' },
    { tab: 'cleaning', name: 'Clean' },
    { tab: 'calculations', name: 'Calculate' },
    { tab: 'visualizations', name: 'Visualize' },
    { tab: 'summary', name: 'Summary' },
    { tab: 'reports', name: 'Report' }
  ]
})`
    ],
    [
      `const steps = [
  { tab: 'upload', name: 'Upload' },
  { tab: 'cleaning', name: 'Clean' },
  { tab: 'calculations', name: 'Calculate' },
  { tab: 'visualizations', name: 'Visualize' },
  { tab: 'summary', name: 'Summary' },
  { tab: 'reports', name: 'Report' }
]

const activeTab = computed({
  get: () => route.query.tab || 'upload',
  set: (val) => router.push({ query: { ...route.query, tab: val } })
})
const currentStepIndex = computed(() => steps.findIndex(s => s.tab === activeTab.value))
const totalSteps = steps.length`,
      `const activeTab = computed({
  get: () => route.query.tab || 'upload',
  set: (val) => router.push({ query: { ...route.query, tab: val } })
})
const currentStepIndex = computed(() => steps.value.findIndex(s => s.tab === activeTab.value))
const totalSteps = computed(() => steps.value.length)`
    ],
    [
      `const requiredColumns = computed(() => {
  if (instrumentType.value === 'money-market') return ['Date', 'Instrument', 'Rate', 'Amount', 'MaturityDate', 'DaysToMaturity', 'Principal', 'InterestRate', 'DiscountRate', 'Price', 'FaceValue']
  if (instrumentType.value === 'bonds') return ['Date', 'BondName', 'CouponRate', 'FaceValue', 'Yield', 'MaturityDate', 'IssueDate', 'Frequency', 'Price', 'AccruedInterest', 'DaysToMaturity', 'RedemptionValue']
  return ['Date', 'TBillName', 'DiscountRate', 'FaceValue', 'MaturityDate', 'DaysToMaturity', 'IssueDate', 'Price', 'Yield']
})

const columnVariations = {
  Date: ['Date', 'date', 'DATE', 'Transaction Date', 'Trade Date', 'Settlement Date', 'Value Date', 'Start Date', 'Issue Date'],
  Instrument: ['Instrument', 'instrument', 'INSTRUMENT', 'Security', 'Security Name', 'Name', 'Description', 'Asset'],
  Rate: ['Rate', 'rate', 'RATE', 'Interest Rate', 'Coupon Rate', 'Discount Rate', 'Yield', 'Return', 'APR'],
  Amount: ['Amount', 'amount', 'AMOUNT', 'Face Value', 'FaceValue', 'Value', 'Price', 'Notional', 'Principal', 'Investment'],
  MaturityDate: ['MaturityDate', 'Maturity Date', 'Maturity', 'Matures', 'End Date', 'Due Date', 'Expiry Date'],
  DaysToMaturity: ['DaysToMaturity', 'Days to Maturity', 'Tenor', 'Days', 'Term', 'Duration Days'],
  Principal: ['Principal', 'Amount', 'Face Value', 'Notional', 'Investment Amount'],
  InterestRate: ['InterestRate', 'Interest Rate', 'Rate', 'Coupon', 'Yield'],
  DiscountRate: ['DiscountRate', 'Discount Rate', 'discount', 'Rate'],
  Price: ['Price', 'price', 'PRICE', 'Market Price', 'Current Price', 'Purchase Price', 'Bid Price', 'Ask Price'],
  FaceValue: ['FaceValue', 'Face Value', 'Face', 'Value', 'Amount', 'Principal', 'Par Value', 'Nominal'],
  BondName: ['BondName', 'Bond Name', 'bond', 'BOND', 'Security', 'Issuer', 'Description', 'Name'],
  CouponRate: ['CouponRate', 'Coupon Rate', 'coupon', 'Rate', 'Interest Rate', 'Annual Coupon'],
  Yield: ['Yield', 'yield', 'YIELD', 'Yield to Maturity', 'YTM', 'Return', 'Effective Yield'],
  IssueDate: ['IssueDate', 'Issue Date', 'Issued', 'Issuance Date', 'Start Date'],
  Frequency: ['Frequency', 'Payment Frequency', 'Coupon Frequency', 'Period', 'SemiAnnual', 'Quarterly', 'Annual'],
  AccruedInterest: ['AccruedInterest', 'Accrued Interest', 'Accrued', 'Interest Accrued'],
  RedemptionValue: ['RedemptionValue', 'Redemption Value', 'Call Value', 'Maturity Value'],
  TBillName: ['TBillName', 'T-Bill Name', 'TBill', 'T Bill', 'Security', 'Instrument', 'Treasury Bill']
}

const fileSize = computed(() => {`,
      `const fileSize = computed(() => {`
    ],
    [
      `const hasRequiredColumn = (col) => rawData.value.length && Object.keys(rawData.value[0]).includes(col)
const missingColumns = computed(() => requiredColumns.value.filter(col => !hasRequiredColumn(col)))`,
      `const mappingContext = computed(() => ({
  mappingApplied: mappingApplied.value,
  columnMapping: columnMapping.value,
  rawData: rawData.value
}))

const hasRequiredColumn = (col) => isColumnMapped(col, mappingContext.value)
const missingColumns = computed(() => getMissingColumns(requiredColumns.value, mappingContext.value))`
    ],
    [
      `const targetIndex = steps.findIndex(s => s.tab === tab)`,
      `const targetIndex = steps.value.findIndex(s => s.tab === tab)`
    ],
    [
      `    rawData.value = data
    fileColumns.value = Object.keys(data[0] || {})`,
      `    rawData.value = data
    originalRawData.value = JSON.parse(JSON.stringify(data))
    originalFileColumns.value = Object.keys(data[0] || {})
    fileColumns.value = [...originalFileColumns.value]
    columnMapping.value = matchColumns(fileColumns.value, requiredColumns.value, columnVariations.value)`
    ],
    [
      `  uploadedFile.value = null
  rawData.value = []
  cleanedData.value = []`,
      `  uploadedFile.value = null
  rawData.value = []
  originalRawData.value = []
  originalFileColumns.value = []
  cleanedData.value = []`
    ],
    [
      `function applyMappingToData(mapping) {
  if (!rawData.value.length) return false
  const mapped = rawData.value.map(row => {
    const newRow = {}
    requiredColumns.value.forEach(reqCol => {
      const src = mapping[reqCol]
      newRow[reqCol] = (src && row[src] !== undefined) ? row[src] : null
    })
    return newRow
  })
  rawData.value = mapped
  fileColumns.value = requiredColumns.value // after renaming, the available columns are the required ones
  mappingApplied.value = true
  debouncedSave()
  return true
}`,
      `function applyMappingToData(mapping) {
  if (!originalRawData.value.length) return false
  const allMapped = requiredColumns.value.every(col => mapping[col])
  if (!allMapped) return false
  rawData.value = applyMappingToRows(originalRawData.value, requiredColumns.value, mapping)
  fileColumns.value = requiredColumns.value.filter(c => mapping[c])
  mappingApplied.value = true
  debouncedSave()
  return true
}`
    ],
    [
      `function autoMatchColumns() {
  if (!rawData.value.length) return
  fileColumns.value = Object.keys(rawData.value[0])
  const newMapping = {}
  requiredColumns.value.forEach(reqCol => {
    const variations = columnVariations[reqCol] || [reqCol]
    let match = fileColumns.value.find(c => c === reqCol) ||
                fileColumns.value.find(c => c.toLowerCase() === reqCol.toLowerCase()) ||
                fileColumns.value.find(c => variations.some(v => c.toLowerCase().includes(v.toLowerCase()) || v.toLowerCase().includes(c.toLowerCase())))
    newMapping[reqCol] = match || null
  })
  columnMapping.value = newMapping
}`,
      `function autoMatchColumns() {
  if (!originalRawData.value.length && !rawData.value.length) return
  if (!originalFileColumns.value.length) {
    originalFileColumns.value = Object.keys((originalRawData.value[0] || rawData.value[0]) || {})
  }
  fileColumns.value = [...originalFileColumns.value]
  columnMapping.value = matchColumns(fileColumns.value, requiredColumns.value, columnVariations.value)
}`
    ],
    [
      `function updateColumnMapping(newMapping) {
  console.log('🔄 Bottom dropdown changed mapping to:', newMapping) // ← VERIFY IN CONSOLE
  columnMapping.value = newMapping
  // THIS IS THE KEY – apply the mapping immediately, same as the top button
  if (applyMappingToData(newMapping)) {
    if (previewData.value.length) {
      previewCleanedData() // re-run cleaning preview to reflect the renamed columns
    }
  }
}`,
      `function updateColumnMapping(newMapping) {
  columnMapping.value = newMapping
}`
    ],
    [
      `function saveToSession() { saveSessionData(); alert('Data saved to session!') }`,
      `function saveToSession() {
  saveSessionData()
  if (!activeSession.value) { alert('No active session selected.'); return }
  sessionSavedAt.value = new Date().toISOString()
  const sid = activeSession.value.id
  const wf = sessionManager.getInstrumentWorkflow(sid, instrumentType.value)
  sessionManager.addVersion(sid, {
    instrument: instrumentName.value,
    changeType: 'Saved',
    changeTypeClass: 'badge-saved',
    shortDescription: \`💾 Saved \${instrumentName.value} to session\`,
    description: \`Saved changes for \${instrumentName.value}\`,
    fieldsChanged: ['data', 'calculations', 'mapping'],
    modifiedInstruments: [instrumentName.value],
    user: localStorage.getItem('user') || 'System',
    workflows: { [instrumentType.value]: wf }
  })
  window.dispatchEvent(new CustomEvent('session-updated', {
    detail: { sessionId: sid, skipCapture: true }
  }))
  alert('Data saved to session!')
}`
    ],
    [
      `const chartData = ref({ labels: [], datasets: [] }), chartSeriesLabel = ref(''), currentMarketRate = ref(null)`,
      `const chartData = ref({ labels: [], datasets: [] }), chartSeriesLabel = ref(''), currentMarketRate = ref(null)

const workflowState = computed(() => ({
  rawDataLength: rawData.value.length,
  mappingApplied: mappingApplied.value,
  allColumnsMapped: missingColumns.value.length === 0,
  cleanedDataLength: cleanedData.value.length,
  calculations: calculations.value,
  chartData: chartData.value,
  reportsSaved: !!sessionSavedAt.value
}))

function isStepCompleted(tab) {
  return checkStepDone(tab, steps.value, workflowState.value)
}

const farthestAllowedIndex = computed(() => calcFarthestAllowed(steps.value, workflowState.value))`
    ],
    [
      `const uploadPreviewHeaders = computed(() => Object.keys(rawData.value[0] || {}))
const cleanPreviewHeaders = computed(() => Object.keys((cleanedData.value[0]) || {}))
function onRawExcelUpdate(data) { rawData.value = data; debouncedSave() }`,
      `const uploadPreviewHeaders = computed(() => {
  if (mappingApplied.value) {
    return requiredColumns.value.filter(col => isColumnMapped(col, mappingContext.value))
  }
  return originalFileColumns.value.length
    ? originalFileColumns.value
    : Object.keys(rawData.value[0] || {})
})
const cleanPreviewHeaders = computed(() => Object.keys((cleanedData.value[0]) || {}))
function onRawExcelUpdate(data, sourceData) {
  if (sourceData?.length) originalRawData.value = sourceData
  rawData.value = mappingApplied.value
    ? applyMappingToRows(originalRawData.value, requiredColumns.value, columnMapping.value)
    : [...originalRawData.value]
  debouncedSave()
}`
    ],
    [
      `    loaded = applyWorkflowToPage(wf, { rawData, cleanedData, calculations, uploadedFile, cleaningStats })`,
      `    loaded = applyWorkflowToPage(wf, {
      rawData, cleanedData, calculations, uploadedFile, cleaningStats,
      columnMapping, mappingApplied, originalRawData, originalFileColumns
    })
    if (wf.sessionSavedAt) sessionSavedAt.value = wf.sessionSavedAt
    if (originalFileColumns.value.length) fileColumns.value = [...originalFileColumns.value]
    else if (originalRawData.value.length) fileColumns.value = Object.keys(originalRawData.value[0] || {})`
    ]
  ]

  let count = 0
  for (const [from, to] of replacements) {
    if (content.includes(from)) {
      content = content.replace(from, to)
      count++
    }
  }

  // saveSessionData block - remove version events and expand snapshot
  const saveOld = content.match(/const wf = buildWorkflowSnapshot\([\s\S]*?updateSessionCompletion\(\)[\s\S]*?window\.dispatchEvent\(new CustomEvent\('session-updated'/)
  if (saveOld) {
    content = content.replace(
      /const wf = buildWorkflowSnapshot\(\{[\s\S]*?\}\)[\s\S]*?updateSessionCompletion\(\)[\s\S]*?window\.dispatchEvent\(new CustomEvent\('session-updated', \{ detail: \{ sessionId: sid \} \}\)\)\s*\}/,
      `const wf = buildWorkflowSnapshot({
    rawData: rawData.value,
    cleanedData: cleanedData.value,
    calculations: calculations.value,
    activeTab: activeTab.value,
    uploadedFile: uploadedFile.value,
    cleaningStats: cleaningStats.value,
    columnMapping: columnMapping.value,
    mappingApplied: mappingApplied.value,
    originalRawData: originalRawData.value,
    originalFileColumns: originalFileColumns.value,
    chartData: chartData.value,
    fredFilters: { country: effectiveCountry.value, currency: effectiveCurrency.value, maturity: effectiveMaturity.value },
    sessionSavedAt: sessionSavedAt.value
  })
  sessionManager.saveInstrumentWorkflow(sid, instrumentType.value, wf)
  sessionManager.updateSession(sid, { last_tab: activeTab.value })

  const key = \`\${instrumentType.value}_session_\${sid}\`
  localStorage.setItem(\`\${key}_raw\`, JSON.stringify(rawData.value))
  localStorage.setItem(\`\${key}_original\`, JSON.stringify(originalRawData.value))
  localStorage.setItem(\`\${key}_clean\`, JSON.stringify(cleanedData.value))
  localStorage.setItem(\`\${key}_calc\`, JSON.stringify(calculations.value))
  localStorage.setItem(\`\${key}_chartData\`, JSON.stringify(chartData.value))
  localStorage.setItem(\`\${key}_mapping\`, JSON.stringify(columnMapping.value))
  localStorage.setItem(\`\${key}_fredFilters\`, JSON.stringify({ country: effectiveCountry.value, currency: effectiveCurrency.value, maturity: effectiveMaturity.value }))
  if (uploadedFile.value) localStorage.setItem(\`\${instrumentType.value}_uploaded_file_name\`, uploadedFile.value.name)

  updateSessionCompletion()
}`
    )
    count++
  }

  // checkAndReset + onMounted loadConfig
  content = content.replace(
    /async function checkAndReset\(\) \{[\s\S]*?onMounted\(async \(\) => \{\s*const qSid = route\.query\.session/,
    `async function checkAndReset() {
  const currentSessionId = sessionManager.getActiveSessionId() || route.query.session || null
  const currentInstrument = instrumentType.value
  if (currentInstrument !== lastInstrument || currentSessionId !== lastSessionId) {
    lastInstrument = currentInstrument; lastSessionId = currentSessionId
    if (currentSessionId) {
      const s = sessionManager.getSession(String(currentSessionId))
      activeSession.value = s || null
    } else activeSession.value = null
    const loaded = await loadSavedData()
    if (!loaded) { refreshPage(); if (!route.query.tab) activeTab.value = 'upload' }
    else {
      if (!route.query.tab) {
        const savedTab = sessionManager.getInstrumentWorkflow(activeSession.value?.id, instrumentType.value)?.last_tab
        if (savedTab && steps.value.some(s => s.tab === savedTab)) activeTab.value = savedTab
        else activeTab.value = 'upload'
      }
      if (cleanedData.value.length) await calculateMetrics()
      if (activeTab.value === 'visualizations' && !chartData.value.datasets.length) await fetchFredData()
    }
    debouncedSave()
  }
}

onMounted(async () => {
  await loadConfig(instrumentType.value)
  const qSid = route.query.session`
  )

  fs.writeFileSync(filePath, content)
  console.log(file + ': applied ' + count + ' replacements')
}
