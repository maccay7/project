<template>
  <div class="extracted-values-preview">
    <div class="preview-header">
      <h3>Extracted Financial Values</h3>
      <p class="subtitle">Review the automatically extracted values below. Missing fields are highlighted for manual entry.</p>
    </div>

    <div class="values-grid">
      <div 
        v-for="(field, key) in displayFields" 
        :key="key" 
        class="field-item"
        :class="{ 'missing': !extractedValues[key], 'editable': true }"
      >
        <label class="field-label">{{ field.label }}</label>
        <div class="field-value-container">
          <input
            v-if="!extractedValues[key] || editingField === key"
            v-model="tempValues[key]"
            :type="field.type"
            class="field-input"
            :placeholder="field.placeholder"
            @blur="saveValue(key)"
            @keyup.enter="saveValue(key)"
          />
          <span v-else class="field-value" @click="editField(key)">
            {{ formatValue(extractedValues[key], field.type) }}
            <v-icon size="16" class="edit-icon">mdi-pencil</v-icon>
          </span>
        </div>
        <span v-if="!extractedValues[key]" class="missing-badge">Required</span>
      </div>
    </div>

    <div class="preview-actions">
      <div class="status-summary">
        <span class="found-count">{{ foundFieldsCount }}/{{ totalFieldsCount }} fields extracted</span>
        <span v-if="missingFieldsCount > 0" class="missing-count">
          {{ missingFieldsCount }} required fields missing
        </span>
      </div>
      <button 
        class="btn-primary" 
        :disabled="missingFieldsCount > 0"
        @click="confirmValues"
      >
        <v-icon left>mdi-check</v-icon> Confirm & Continue
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { getRequiredFieldMappings } from '@/utils/sheetTypeDetector'

const props = defineProps({
  extractedValues: {
    type: Object,
    default: () => ({})
  },
  instrumentType: {
    type: String,
    default: 'money-market'
  }
})

const emit = defineEmits(['update:extractedValues', 'confirm'])

const tempValues = ref({})
const editingField = ref(null)

const fieldDefinitions = {
  // Money Market
  principal: { label: 'Principal Amount', type: 'number', placeholder: 'Enter principal amount' },
  interestRate: { label: 'Interest Rate (%)', type: 'number', placeholder: 'Enter interest rate' },
  daysToMaturity: { label: 'Days to Maturity', type: 'number', placeholder: 'Enter days to maturity' },
  issueDate: { label: 'Issue Date', type: 'date', placeholder: 'YYYY-MM-DD' },
  maturityDate: { label: 'Maturity Date', type: 'date', placeholder: 'YYYY-MM-DD' },
  purchasePrice: { label: 'Purchase Price', type: 'number', placeholder: 'Enter purchase price' },
  settlementAmount: { label: 'Settlement Amount', type: 'number', placeholder: 'Enter settlement amount' },
  
  // T-Bills
  faceValue: { label: 'Face Value', type: 'number', placeholder: 'Enter face value' },
  discountRate: { label: 'Discount Rate (%)', type: 'number', placeholder: 'Enter discount rate' },
  auctionDate: { label: 'Auction Date', type: 'date', placeholder: 'YYYY-MM-DD' },
  
  // Bonds
  couponRate: { label: 'Coupon Rate (%)', type: 'number', placeholder: 'Enter coupon rate' },
  couponFrequency: { label: 'Coupon Frequency', type: 'text', placeholder: 'e.g., Semi-annual, Quarterly' },
  price: { label: 'Price', type: 'number', placeholder: 'Enter price' },
  yield: { label: 'Yield to Maturity (%)', type: 'number', placeholder: 'Enter YTM' },
  callDate: { label: 'Call Date', type: 'date', placeholder: 'YYYY-MM-DD' },
  callPrice: { label: 'Call Price', type: 'number', placeholder: 'Enter call price' },
  putDate: { label: 'Put Date', type: 'date', placeholder: 'YYYY-MM-DD' },
  putPrice: { label: 'Put Price', type: 'number', placeholder: 'Enter put price' },
  
  // Common
  instrumentName: { label: 'Instrument Name', type: 'text', placeholder: 'Enter instrument name' },
  currency: { label: 'Currency', type: 'text', placeholder: 'e.g., USD, EUR' },
  country: { label: 'Country', type: 'text', placeholder: 'e.g., US, UK' },
  issuer: { label: 'Issuer', type: 'text', placeholder: 'Enter issuer name' },
  dayCountConvention: { label: 'Day Count Convention', type: 'text', placeholder: 'e.g., 30/360, Actual/360' },
  settlementDate: { label: 'Settlement Date', type: 'date', placeholder: 'YYYY-MM-DD' }
}

const requiredFields = computed(() => getRequiredFieldMappings(props.instrumentType))

const displayFields = computed(() => {
  const fields = {}
  requiredFields.value.forEach(field => {
    fields[field] = fieldDefinitions[field] || { 
      label: field, 
      type: 'text', 
      placeholder: `Enter ${field}` 
    }
  })
  return fields
})

const foundFieldsCount = computed(() => {
  return requiredFields.value.filter(field => props.extractedValues[field]).length
})

const missingFieldsCount = computed(() => {
  return requiredFields.value.filter(field => !props.extractedValues[field]).length
})

const totalFieldsCount = computed(() => requiredFields.value.length)

function formatValue(value, type) {
  if (value === null || value === undefined || value === '') return 'Not set'
  if (type === 'number') {
    const num = parseFloat(value)
    return isNaN(num) ? value : num.toLocaleString()
  }
  return value
}

function editField(key) {
  editingField.value = key
  tempValues.value[key] = props.extractedValues[key] || ''
}

function saveValue(key) {
  const value = tempValues.value[key]
  if (value !== undefined && value !== null && value !== '') {
    emit('update:extractedValues', { ...props.extractedValues, [key]: value })
  }
  editingField.value = null
}

function confirmValues() {
  emit('confirm', props.extractedValues)
}

onMounted(() => {
  // Initialize temp values with extracted values
  Object.keys(props.extractedValues).forEach(key => {
    tempValues.value[key] = props.extractedValues[key]
  })
})
</script>

<style scoped>
.extracted-values-preview {
  background: white;
  border-radius: 12px;
  padding: 24px;
  border: 1px solid #e0e0e0;
}

.preview-header {
  margin-bottom: 24px;
}

.preview-header h3 {
  color: #0B2A44;
  font-size: 20px;
  font-weight: 600;
  margin-bottom: 8px;
}

.subtitle {
  color: #666;
  font-size: 14px;
  margin: 0;
}

.values-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.field-item {
  position: relative;
  padding: 16px;
  background: #f8f9fa;
  border-radius: 8px;
  border: 2px solid transparent;
  transition: all 0.2s;
}

.field-item.missing {
  border-color: #ff9800;
  background: #fff3e0;
}

.field-item.editable:hover {
  border-color: #1E88E5;
}

.field-label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: #0B2A44;
  margin-bottom: 8px;
}

.field-value-container {
  position: relative;
}

.field-input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
  transition: border-color 0.2s;
}

.field-input:focus {
  outline: none;
  border-color: #1E88E5;
}

.field-value {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  background: white;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
  color: #333;
  cursor: pointer;
  transition: background 0.2s;
}

.field-value:hover {
  background: #f0f0f0;
}

.edit-icon {
  opacity: 0.5;
  transition: opacity 0.2s;
}

.field-value:hover .edit-icon {
  opacity: 1;
}

.missing-badge {
  position: absolute;
  top: -8px;
  right: 8px;
  background: #ff9800;
  color: white;
  font-size: 10px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 10px;
  text-transform: uppercase;
}

.preview-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 16px;
  border-top: 1px solid #e0e0e0;
}

.status-summary {
  display: flex;
  gap: 16px;
  font-size: 14px;
}

.found-count {
  color: #4CAF50;
  font-weight: 600;
}

.missing-count {
  color: #ff9800;
  font-weight: 600;
}

.btn-primary {
  background: linear-gradient(135deg, #0B2A44, #1E88E5);
  color: white;
  border: none;
  padding: 12px 24px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  transition: transform 0.2s, box-shadow 0.2s;
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(30, 136, 229, 0.3);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
