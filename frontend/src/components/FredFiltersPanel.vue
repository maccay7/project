<template>
  <div class="fred-filters-vertical">
    <v-combobox
      v-model="filters.country"
      :items="countrySearchItems"
      item-title="title"
      item-value="value"
      label="Country / region (type to search)"
      density="compact"
      clearable
      hide-details
      class="filter-field"
      @update:model-value="onCountryPick"
    />
    <v-combobox
      v-model="filters.currency"
      :items="currencySearchItems"
      item-title="title"
      item-value="value"
      label="Currency (type to search)"
      density="compact"
      clearable
      hide-details
      class="filter-field"
      @update:model-value="emitChange"
    />
    <v-select
      v-model="filters.maturity"
      :items="maturityOptions"
      item-title="name"
      item-value="code"
      label="Benchmark maturity"
      density="compact"
      hide-details
      class="filter-field"
      @update:model-value="emitChange"
    />
    <p class="filter-note">Type any country code (e.g. US, ZA) or pick from list. Data from FRED.</p>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  filters: { type: Object, required: true },
  filterOptions: { type: Object, default: () => ({ countries: [], currencies: [] }) }
})

const emit = defineEmits(['update:filters', 'change'])

const countrySearchItems = computed(() =>
  (props.filterOptions.countries || []).map(c => ({
    title: `${c.name} (${c.code})`,
    value: c.code
  }))
)

const currencySearchItems = computed(() =>
  (props.filterOptions.currencies || []).map(c => ({
    title: `${c.name || c.code}`,
    value: c.code
  }))
)

const maturityOptions = computed(() => {
  const c = (props.filterOptions.countries || []).find(x => x.code === props.filters.country)
  return c?.maturities || []
})

function onCountryPick(val) {
  const code = typeof val === 'object' && val?.value ? val.value : String(val || 'US').toUpperCase().slice(0, 3)
  props.filters.country = code
  const known = (props.filterOptions.countries || []).find(x => x.code === code)
  if (known) props.filters.currency = known.currency
  emitChange()
}

function emitChange() {
  emit('update:filters', { ...props.filters })
  emit('change')
}
</script>

<style scoped>
.fred-filters-vertical {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-width: 360px;
  margin-bottom: 16px;
}
.filter-field { width: 100%; }
.filter-note { font-size: 12px; color: #666; margin: 0; }
</style>
