<template>
  <FixedLayout>
    <div class="instrument-page">
      <!-- Page Header -->
      <div class="page-header">
        <div class="header-left">
          <h1>{{ instrumentLabel }}</h1>
          <p>{{ instrumentDescription }}</p>
          <div v-if="activeSession" class="session-badge">
            <v-icon small>mdi-folder-outline</v-icon>
            Session: <strong>{{ activeSession.name }}</strong>
            <span class="version-badge" v-if="activeSession.version_count !== undefined">
              (v{{ activeSession.version_count }})
            </span>
          </div>
          <div v-else class="session-badge warning">
            <v-icon small>mdi-alert-outline</v-icon>
            No active session – please select a session from Dashboard
          </div>
        </div>
        <div class="header-right">
          <button v-if="activeSession" class="btn-save-session" @click="saveToSession" :disabled="isSaving">
            <v-icon small>mdi-content-save</v-icon> Save to Session
          </button>
          <div class="step-indicator">Step {{ currentStepIndex + 1 }} of {{ totalSteps }}</div>
        </div>
      </div>

      <!-- Progress Bar -->
      <div class="progress-bar-container">
        <div class="progress-steps">
          <div
            v-for="(step, index) in steps"
            :key="step.tab"
            class="progress-step"
            :class="{ active: activeTab === step.tab, completed: isStepComplete(step.tab), disabled: index > farthestAllowedIndex }"
            @click="switchTab(step.tab)"
          >
            <div class="step-circle">{{ index + 1 }}</div>
            <div class="step-label">{{ step.name }}</div>
          </div>
        </div>
      </div>

      <!-- Tab content wrapper with overflow scroll -->
      <div class="tab-content-wrapper">
        <!-- ===== UPLOAD ===== -->
        <div v-if="activeTab === 'upload'" class="content-card">
          <v-card>
            <v-card-title>Upload {{ instrumentLabel }} Dataset</v-card-title>
            <v-card-text>
              <!-- Valuation Date Selector -->
              <div class="valuation-date-section">
                <label class="filter-label">Valuation Date</label>
                <input 
                  type="date" 
                  v-model="valuationDate" 
                  class="date-input"
                />
              </div>

              <div class="upload-area" @dragover.prevent @drop.prevent="handleDrop">
                <input
                  type="file"
                  ref="fileInput"
                  @change="handleFileUpload"
                  accept=".csv,.xlsx,.xls,.xlsm,.xlsb,.xltx,.xltm,.xlam,.ods,.xml,.html,.prn,.dif,.slk,.dbf"
                  style="display: none"
                />
                <p>Drag & drop or <span class="browse-link" @click="$refs.fileInput.click()">browse</span></p>
                <small>Supported: CSV, Excel (including .xlsm, .xlsb, .ods), and many other spreadsheet formats</small>
              </div>

              <div v-if="uploadHistory.length" class="upload-history">
                <h4>Upload History ({{ uploadHistory.length }} files)</h4>
                <div class="history-list">
                  <div v-for="(item, idx) in uploadHistory" :key="idx" class="history-item" @click="loadHistoryFile(item)">
                    <span>{{ item.name }}</span>
                    <small>{{ new Date(item.date).toLocaleString() }}</small>
                    <button class="btn-delete-history" @click.stop="deleteHistoryItem(idx)">×</button>
                  </div>
                </div>
              </div>

              <div v-if="fileLoading" class="loading-container">
                <p>{{ uploadProgress > 0 ? `Processing file... ${uploadProgress}%` : 'Parsing file... Please wait.' }}</p>
                <v-progress-linear v-if="uploadProgress > 0" :value="uploadProgress" color="#0B2044" height="6"></v-progress-linear>
              </div>

              <div v-if="uploadedFile" class="file-info">
                <span>{{ uploadedFile.name }}</span>
                <span v-if="fileSize" class="file-size">{{ fileSize }}</span>
                <button class="remove-btn" @click="removeFile">×</button>
                <button class="btn-auto-detect-green" @click="() => autoDetectSingleInstrument()" :disabled="isDetecting || !currentSheetName" v-if="currentSheetName">
                  <v-icon v-if="!isDetecting" size="16">mdi-magnify</v-icon>
                  <v-icon v-else size="16" class="spin-animation">mdi-loading</v-icon>
                  {{ getDetectionButtonText() }}
                </button>
                <button class="btn-view-workbook" @click="openWorkbookViewer">View Excel Workbook</button>
                <button class="btn-preview" @click="togglePreview" :disabled="!worksheetSelected">Preview</button>
                <button class="btn-review-excel" @click="openExcelReview(rawData, 'Uploaded Data')" :disabled="!worksheetSelected">Review Excel</button>
                <button v-if="sheetType === 'multi'" class="btn-mapping" @click="openMappingDialog" :disabled="!worksheetSelected">Map Columns</button>
              </div>

              <!-- Worksheet Selector - hidden after a sheet is processed -->
              <div v-if="worksheetWorkflow.workbookSheets.length > 0 && !worksheetSelected" class="worksheet-selector-section">
                <WorksheetSelector
                  :workbook-sheets="worksheetWorkflow.workbookSheets"
                  :worksheet-status="worksheetWorkflow.worksheetStatus"
                  :selected-worksheet="worksheetWorkflow.selectedWorksheet"
                  :loading="fileLoading"
                  :error="uploadError"
                  :is-detecting="isDetecting"
                  @select-sheet="handleWorksheetSelect"
                  @work-on-sheet="handleWorkOnSheet"
                  @view-results="handleViewResults"
                  @auto-detect-sheet="handleAutoDetectSheet"
                />
              </div>

              <!-- ===== PREVIEW SECTION ===== -->
              <div v-if="rawData.length && showPreview" class="excel-preview-section">
                <h4 v-if="sheetType === 'single'">File Preview – {{ currentSheetName || 'Selected Sheet' }}</h4>
                <h4 v-else>File Preview – {{ currentSheetName || 'Selected Sheet' }}</h4>
                <p v-if="sheetType === 'single'" class="preview-info">
                  {{ rawData.length }} total rows — edit cells below like Excel
                </p>
                <p v-else class="preview-info">{{ rawData.length }} total rows — edit cells below like Excel</p>
                
                <!-- Multiple Instruments: Show mapped dataset in Excel viewer with mapping controls -->
                <ExcelViewer
                  v-if="sheetType === 'multi' && rawData.length"
                  :data="rawData.slice(0, 500)"
                  :headers="uploadPreviewHeaders"
                  :original-data="originalRawData.slice(0, 500)"
                  :original-headers="originalFileColumns"
                  :show-mapping-controls="true"
                  :column-mapping="columnMapping"
                  :available-file-columns="fileColumns"
                  :required-columns="requiredColumns"
                  :workbook-sheets="[]"
                  :current-sheet-name="currentSheetName"
                  @data-update="onRawExcelUpdate"
                  @mapping-update="updateColumnMapping"
                ></ExcelViewer>
                
                <!-- Single Instrument: Show extracted values in Excel viewer -->
                <ExcelViewer
                  v-else-if="sheetType === 'single' && rawData.length"
                  :data="rawData.slice(0, 500)"
                  :headers="uploadPreviewHeaders"
                  :original-data="originalRawData.slice(0, 500)"
                  :original-headers="originalFileColumns"
                  :show-mapping-controls="false"
                  :column-mapping="{}"
                  :available-file-columns="fileColumns"
                  :required-columns="requiredColumns"
                  :workbook-sheets="[]"
                  :current-sheet-name="currentSheetName"
                  @data-update="onRawExcelUpdate"
                ></ExcelViewer>
                
                <!-- Preview actions - removed "Full Screen" button -->
                <div v-if="sheetType === 'multi'" class="preview-actions">
                  <button class="btn-primary" @click="saveFinalMapping">Save Mapping</button>
                </div>
              </div>

              <!-- ===== MAPPING DIALOG (only shown for multi) ===== -->
              <v-dialog v-model="showMappingDialog" max-width="650px">
                <v-card>
                  <v-card-title class="mapping-dialog-title">
                    Map Columns – {{ instrumentLabel }}
                    <v-spacer></v-spacer>
                    <span class="mapping-count">{{ requiredColumns.length }} required fields</span>
                  </v-card-title>
                  <v-card-text class="mapping-dialog-body">
                    <div class="mapping-grid">
                      <div v-for="reqCol in requiredColumns" :key="reqCol" class="mapping-row">
                        <label class="required-label">{{ reqCol }}</label>
                        <div class="dropdown-wrapper">
                          <select v-model="columnMapping[reqCol]" class="mapping-select">
                            <option :value="null">— Select a column —</option>
                            <option v-for="fileCol in fileColumns" :key="fileCol" :value="fileCol">{{ fileCol }}</option>
                          </select>
                        </div>
                      </div>
                    </div>

                    <div v-if="missingColumns.length" class="warning-message">
                      <span>Missing mappings for: {{ missingColumns.join(', ') }}</span>
                    </div>
                    <div v-if="!missingColumns.length && Object.values(columnMapping).some(v => v)" class="success-message">
                      <span>All columns mapped! Ready to continue.</span>
                    </div>

                    <div style="margin-top: 16px; text-align: right;">
                      <button class="btn-secondary small" @click="showSavedMappingsDialog = true">Manage Saved Mappings</button>
                    </div>
                  </v-card-text>
                  <v-card-actions>
                    <button class="btn-secondary" @click="closeMappingDialog">Cancel</button>
                    <button class="btn-primary" @click="applyColumnMappingAndClose">Apply Mapping</button>
                  </v-card-actions>
                </v-card>
              </v-dialog>

              <!-- Saved Mappings Popup -->
              <v-dialog v-model="showSavedMappingsDialog" max-width="700px">
                <v-card>
                  <v-card-title class="saved-mappings-popup-title">
                    Saved Mappings
                    <v-spacer></v-spacer>
                    <button class="btn-close-dialog" @click="showSavedMappingsDialog = false">×</button>
                  </v-card-title>
                  <v-card-text class="saved-mappings-popup-body">
                    <!-- Save New Mapping Section -->
                    <div class="save-section">
                      <div class="save-row">
                        <input 
                          v-model="newTemplateName" 
                          class="template-input" 
                          placeholder="Enter mapping name..." 
                          @keyup.enter="saveCurrentMappingAsTemplate"
                        />
                        <button class="btn-primary" @click="saveCurrentMappingAsTemplate">Save Mapping</button>
                      </div>
                    </div>

                    <!-- Saved Mappings List -->
                    <div v-if="!savedTemplates.length" class="empty-state">
                      <p>No saved mappings yet.</p>
                    </div>
                    <div v-else class="saved-mappings-list">
                      <div v-for="template in savedTemplates" :key="template.id" class="saved-mapping-item">
                        <div class="mapping-name">{{ template.name }}</div>
                        <div class="mapping-meta">Saved: {{ new Date(template.created_at).toLocaleDateString() }}</div>
                        <div class="mapping-actions">
                          <button class="btn-secondary small" @click="loadTemplateFromPopup(template.id)">Load</button>
                          <button class="btn-secondary small danger" @click="deleteTemplateFromPopup(template.id)">Delete</button>
                        </div>
                      </div>
                    </div>
                  </v-card-text>
                </v-card>
              </v-dialog>

              <!-- Multi-Table Detection Success Popup -->
              <v-dialog v-model="showMultiTableDetectionSuccess" max-width="700px">
                <v-card>
                  <v-card-title class="detection-success-title">
                    Multi-Table Detection Successful ✓
                    <v-spacer></v-spacer>
                    <button class="btn-close-dialog" @click="showMultiTableDetectionSuccess = false">×</button>
                  </v-card-title>
                  <v-card-text class="detection-success-body">
                    <div class="instrument-type-display">
                      <strong>Instrument:</strong> {{ instrumentType === 'money-market' ? 'Money Market' : instrumentType === 'treasury-bills' ? 'Treasury Bills' : 'Bonds' }}
                      ({{ instrumentType }})
                    </div>
                    
                    <!-- Currency Selection for Auto-Detection -->
                    <div class="currency-selection-section">
                      <label class="currency-label">Select Currency to Include in Auto-Detected Values:</label>
                      <v-select
                        v-model="selectedCurrency"
                        @change="handleCurrencyChange"
                        :items="currencyOptions"
                        label="Currency"
                        variant="outlined"
                        density="compact"
                        hide-details
                        class="currency-select-vuetify"
                      ></v-select>
                      <div v-if="selectedCurrency === 'custom'" class="custom-currency-input-wrapper">
                        <v-text-field
                          v-model="customCurrency"
                          label="Custom Currency Code"
                          placeholder="e.g., ZWG"
                          variant="outlined"
                          density="compact"
                          maxlength="3"
                          hide-details
                          @input="handleCustomCurrencyInput"
                          class="custom-currency-field-vuetify"
                        >
                          <template v-slot:append>
                            <span class="currency-code-badge">{{ customCurrency.length }}/3</span>
                          </template>
                        </v-text-field>
                      </div>
                      <div v-if="detectedCurrencies.length > 0" class="detected-currencies-info">
                        <strong>Detected Currencies in Section:</strong> {{ detectedCurrencies.join(', ') }}
                      </div>
                      <div v-if="selectedCurrency && selectedCurrency !== 'custom'" class="selected-currency-info">
                        Including values for: <strong>{{ selectedCurrency }}</strong>
                      </div>
                      <div v-else-if="selectedCurrency === 'custom' && customCurrency" class="selected-currency-info">
                        Including values for custom currency: <strong>{{ customCurrency.toUpperCase() }}</strong>
                      </div>
                      <div v-else class="selected-currency-info">
                        Including values for all detected currencies
                      </div>
                    </div>
                    
                    <div class="multi-table-summary">
                      <strong>{{ multiTableDetectionResults.length }} table(s) selected</strong>
                      <p style="margin: 8px 0 0 0; font-size: 13px; color: #666;">All detected fields from selected tables will be combined into a single instrument for calculations.</p>
                    </div>
                    
                    <div class="multi-instruments-list">
                      <div v-for="(instrument, index) in multiTableDetectionResults" :key="index" class="multi-instrument-item">
                        <div class="multi-instrument-header">
                          <strong>Table {{ index + 1 }}: {{ instrument.tableName }}</strong>
                          <span class="field-count-badge">{{ Object.keys(instrument.fields).length }} fields</span>
                        </div>
                        <div class="multi-instrument-fields">
                          <div v-for="(value, field) in instrument.fields" :key="field" class="multi-detected-field-item">
                            <span class="multi-detected-field-label">{{ field }}:</span>
                            <span class="multi-detected-field-value">{{ formatDetectedValue(field, typeof value === 'object' && value !== null ? value.value : value) }}</span>
                            <span v-if="instrument.fieldsWithMetadata?.[field]?.location" class="multi-detected-field-location">@ {{ instrument.fieldsWithMetadata[field].location }}</span>
                          </div>
                        </div>
                        <div v-if="instrument.missingFields.length > 0" class="multi-missing-fields">
                          <span class="missing-label">Missing:</span>
                          {{ instrument.missingFields.join(', ') }}
                        </div>
                      </div>
                    </div>
                  </v-card-text>
                  <v-card-actions>
                    <button class="btn-secondary" @click="showMultiTableDetectionSuccess = false">Close</button>
                    <button class="btn-primary" @click="useMultiTableDetectedFields">Use Combined Fields</button>
                  </v-card-actions>
                </v-card>
              </v-dialog>

              <!-- Auto Detection Success Popup -->
              <v-dialog v-model="showDetectionSuccess" max-width="500px">
                <v-card>
                  <v-card-title class="detection-success-title">
                    Auto Detection Successful ✓
                    <v-spacer></v-spacer>
                    <button class="btn-close-dialog" @click="showDetectionSuccess = false">×</button>
                  </v-card-title>
                  <v-card-text class="detection-success-body">
                    <!-- Show instrument type from detection time (stored) -->
                    <div class="instrument-type-display">
                      <strong>Instrument:</strong> {{ detectedInstrumentType === 'money-market' ? 'Money Market' : detectedInstrumentType === 'treasury-bills' ? 'Treasury Bills' : 'Bonds' }}
                      ({{ detectedInstrumentType }})
                    </div>
                    
                    <div class="detected-fields-list">
                      <div v-if="Object.keys(autoDetectedFields).length > 0">
                        <h4>Detected Fields ({{ Object.keys(autoDetectedFields).length }})</h4>
                        <div v-for="(value, field) in autoDetectedFields" :key="field" class="detected-field-item">
                          <span class="detected-field-label">{{ field }}:</span>
                          <span class="detected-field-value">{{ formatDetectedValue(field, typeof value === 'object' && value !== null ? value.value : value) }}</span>
                          <span v-if="autoDetectedFieldsWithMetadata[field]?.location" class="detected-field-location">@ {{ autoDetectedFieldsWithMetadata[field].location }}</span>
                          <!-- DEBUG: Show currency variants info -->
                          <div v-if="typeof value === 'object' && value !== null" class="debug-info" style="font-size: 11px; color: #666; margin-top: 4px;">
                            <span v-if="value.currencyVariants">Currency variants: {{ Object.keys(value.currencyVariants).join(', ') }}</span>
                            <span v-else>No currency variants ({{ typeof value }})</span>
                          </div>
                          <!-- Currency selector for fields with multiple currency variants -->
                          <div v-if="typeof value === 'object' && value?.currencyVariants && Object.keys(value.currencyVariants).length > 1" class="currency-variant-selector">
                            <select v-model="value.selectedCurrency" @change="updateSelectedCurrency(field, value.selectedCurrency)" class="currency-select">
                              <option v-for="(variantValue, currency) in value.currencyVariants" :key="currency" :value="currency">
                                {{ currency }}: {{ formatDetectedValue(field, variantValue) }}
                              </option>
                            </select>
                          </div>
                        </div>
                      </div>

                      <div v-if="Object.keys(autoDetectedAdditionalFields).length > 0">
                        <h4>Additional Detected Fields ({{ Object.keys(autoDetectedAdditionalFields).length }})</h4>
                        <div v-for="(value, field) in autoDetectedAdditionalFields" :key="'add-' + field" class="detected-field-item">
                          <span class="detected-field-label">{{ field }}:</span>
                          <span class="detected-field-value">{{ formatDetectedValue(field, typeof value === 'object' && value !== null ? value.value : value) }}</span>
                          <!-- Currency selector for additional fields with multiple currency variants -->
                          <div v-if="typeof value === 'object' && value?.currencyVariants && Object.keys(value.currencyVariants).length > 1" class="currency-variant-selector">
                            <select v-model="value.selectedCurrency" @change="updateSelectedCurrency(field, value.selectedCurrency, true)" class="currency-select">
                              <option v-for="(variantValue, currency) in value.currencyVariants" :key="currency" :value="currency">
                                {{ currency }}: {{ formatDetectedValue(field, variantValue) }}
                              </option>
                            </select>
                          </div>
                        </div>
                      </div>

                      <div v-if="Object.keys(autoDetectedFields).length === 0 && Object.keys(autoDetectedAdditionalFields).length === 0" class="no-detection-message">
                        <p>No required fields detected in this worksheet.</p>
                        <p>Try selecting a different section or check if the field names match the expected format.</p>
                      </div>
                    </div>
                    
                    <!-- Show missing fields if any -->
                    <div v-if="Object.keys(autoDetectedFields).length < requiredColumns.length" class="missing-fields-warning">
                      <p><strong>Missing Required Fields:</strong></p>
                      <ul>
                        <li v-for="col in requiredColumns.filter(c => !autoDetectedFields[c])" :key="col">{{ col }}</li>
                      </ul>
                    </div>
                    
                    <!-- Show additional detected fields that aren't in required columns -->
                    <div v-if="autoDetectedAdditionalFields && Object.keys(autoDetectedAdditionalFields).length > 0" class="additional-fields-section">
                      <h4>Additional Detected Fields ({{ Object.keys(autoDetectedAdditionalFields).length }})</h4>
                      <p class="section-hint">These fields were detected but are not required for calculations.</p>
                      <div v-for="(field, label) in autoDetectedAdditionalFields" :key="label" class="additional-field-item">
                        <span class="additional-field-label">{{ label }}:</span>
                        <span class="additional-field-value">{{ formatDetectedValue(label, typeof field === 'object' && field !== null ? field.value : field) }}</span>
                        <span v-if="typeof field === 'object' && field?.location" class="additional-field-location">@ {{ field.location }}</span>
                        <!-- Currency selector for additional fields with multiple currency variants -->
                        <div v-if="typeof field === 'object' && field?.currencyVariants && Object.keys(field.currencyVariants).length > 1" class="currency-variant-selector">
                          <select v-model="field.selectedCurrency" @change="updateSelectedCurrency(label, field.selectedCurrency, true)" class="currency-select">
                            <option v-for="(variantValue, currency) in field.currencyVariants" :key="currency" :value="currency">
                              {{ currency }}: {{ formatDetectedValue(label, variantValue) }}
                            </option>
                          </select>
                        </div>
                      </div>
                    </div>
                  </v-card-text>
                  <v-card-actions>
                    <button class="btn-secondary" @click="showDetectionSuccess = false">Close</button>
                    <button class="btn-primary" @click="useDetectedFields">Work on This Worksheet</button>
                  </v-card-actions>
                </v-card>
              </v-dialog>

              <!-- Workbook Viewer Dialog -->
              <v-dialog v-model="showWorkbookViewer" max-width="95%" persistent>
                <v-card style="height: 90vh;">
                  <v-card-title class="excel-dialog-title-no-logo">
                    <span>Excel Workbook – {{ currentSheetName || 'Select a sheet' }}</span>
                    <v-spacer></v-spacer>
                    <button class="btn-auto-detect-green" @click="() => autoDetectSingleInstrument()" v-if="currentSheetName && workbookSheets.length" :disabled="isDetecting">
                      <v-icon v-if="!isDetecting" size="16">mdi-magnify</v-icon>
                      <v-icon v-else size="16" class="spin-animation">mdi-loading</v-icon>
                      {{ getDetectionButtonText() }}
                    </button>
                    <button class="btn-work-on-sheet" @click="workOnSelectedSheet" v-if="currentSheetName && workbookSheets.length">
                      Work on This Sheet
                    </button>
                    <button class="btn-close-dialog" @click="showWorkbookViewer = false">×</button>
                  </v-card-title>
                  <v-card-text class="pa-0" style="height: calc(90vh - 120px);">
                    <ExcelWorkbookViewer
                      v-if="showWorkbookViewer"
                      :workbook-data="{ sheets: [], fileBuffer: originalFileBuffer }"
                      :file-name="uploadedFile?.name || 'Workbook'"
                      :instrument-type="instrumentType"
                      :worksheet-statuses="worksheetStatuses"
                      @close="showWorkbookViewer = false"
                      @sheet-selected="handleSheetSelectedFromViewer"
                      @single-instrument-extracted="handleSingleInstrumentExtracted"
                      @table-isolated="handleTableIsolated"
                      @multi-table-detect="handleMultiTableDetect"
                      @workbook-loaded="handleWorkbookLoaded"
                      @detect-start="isDetecting = true"
                      @detect-end="isDetecting = false"
                    />
                  </v-card-text>
                  <div class="popup-footer">
                    <span v-if="activeValuationDate" class="valuation-date-footer">Valuation Date: {{ activeValuationDate }}</span>
                    <v-spacer></v-spacer>
                    <button class="btn-secondary" @click="showWorkbookViewer = false">Close</button>
                  </div>
                </v-card>
              </v-dialog>

              <!-- ===== Required Columns / Extracted Values ===== -->
              <div class="required-columns">
                <h4 v-if="sheetType === 'multi'">Required Columns</h4>
                <h4 v-else>Required Values (Single Instrument)</h4>
                
                <!-- Multi-sheet: Column badges -->
                <div v-if="sheetType === 'multi'" class="columns-list">
                  <span v-for="col in requiredColumns" :key="col" class="column-badge" :class="{ 'missing-column': !hasRequiredColumn(col), 'mapped-column': hasRequiredColumn(col) }">
                    <span class="badge-icon">{{ hasRequiredColumn(col) ? '✓' : '○' }}</span>
                    {{ col }}
                  </span>
                </div>
                
                <!-- Single-sheet: Extracted values table (like mapping preview) -->
                <div v-else class="extracted-values-table">
                  <div class="table-header">
                    <span class="header-field">Field</span>
                    <span class="header-value">Extracted Value</span>
                    <span class="header-status">Status</span>
                  </div>
                  <div v-for="(value, key) in extractedValues" :key="key" class="table-row" :class="{ 'row-missing': !value || value === 'N/A' }">
                    <span class="row-field">{{ key }}</span>
                    <div class="row-value">
                      <input
                        v-if="value && value !== 'N/A'"
                        type="text"
                        class="value-input"
                        :value="value"
                        @input="updateExtractedValue(key, $event.target.value)"
                        @blur="updateExtractedValue(key, $event.target.value)"
                      />
                      <input
                        v-else
                        type="text"
                        class="value-input placeholder"
                        placeholder="Enter value..."
                        @input="updateExtractedValue(key, $event.target.value)"
                        @blur="updateExtractedValue(key, $event.target.value)"
                      />
                      <button class="btn-clear-value" @click="clearExtractedValue(key)" title="Clear value">×</button>
                    </div>
                    <span class="row-status" :class="{ 'status-missing': !value || value === 'N/A' }">
                      {{ value && value !== 'N/A' ? '✓ Detected' : '! Missing' }}
                    </span>
                  </div>
                </div>
                
                <!-- Status messages -->
                <div v-if="rawData.length && sheetType === 'multi' && missingColumns.length" class="warning-message">
                  <span class="warning-icon">⚠</span>
                  <span>Missing required columns. Use the dropdowns on the column headers or click "Map Columns" to assign them.</span>
                </div>
                <div v-if="rawData.length && sheetType === 'multi' && missingColumns.length === 0 && mappingApplied" class="success-message">
                  <span class="success-icon">✓</span>
                  <span>All columns mapped. Ready to continue.</span>
                </div>
                <div v-if="sheetType === 'single' && Object.keys(extractedValues).length > 0" class="values-summary">
                  <span class="summary-text">
                    {{ Object.values(extractedValues).filter(v => v && v !== 'N/A').length }} of {{ Object.keys(extractedValues).length }} required values detected
                  </span>
                </div>
              </div>

              <div class="navigation-buttons">
                <button class="btn-primary" @click="continueAfterUpload" :disabled="!uploadedFile || !rawData.length">Continue</button>
                <button class="btn-secondary" @click="goToDashboard">Cancel</button>
              </div>
            </v-card-text>
          </v-card>
        </div>

        <!-- ===== CLEANING ===== -->
        <div v-if="activeTab === 'cleaning'" class="content-card">
          <v-card>
            <v-card-title>Clean {{ instrumentLabel }} Data</v-card-title>
            <v-card-text>
              <div v-if="!hasData" class="empty-state">
                <p>No data uploaded yet.</p>
                <button class="btn-primary" @click="switchTab('upload')">Go to Upload</button>
              </div>
              <div v-else>
                <div class="cleaning-options-panel">
                  <h3>Cleaning Filters</h3>
                  <div class="filter-scroll-container">
                    <div class="options-list">
                      <label class="option-checkbox"><input type="checkbox" v-model="cleaningOptions.removeDuplicates"> Remove duplicate rows</label>
                      <label class="option-checkbox"><input type="checkbox" v-model="cleaningOptions.fillMissingText"> Fill missing text with "N/A"</label>
                      <label class="option-checkbox"><input type="checkbox" v-model="cleaningOptions.dropRowsWithMissing"> Drop rows with ANY missing value</label>
                      <label class="option-checkbox"><input type="checkbox" v-model="cleaningOptions.trimWhitespace"> Trim whitespace</label>
                      <label class="option-checkbox"><input type="checkbox" v-model="cleaningOptions.convertToNumbers"> Convert text numbers to numeric</label>
                      <label class="option-checkbox"><input type="checkbox" v-model="cleaningOptions.removeOutliers"> Remove outliers (3σ)</label>
                      <label class="option-checkbox"><input type="checkbox" v-model="cleaningOptions.standardizeDates"> Standardize dates to selected format:
                        <select v-model="selectedDateFormat" class="date-format-select-inline" :disabled="!cleaningOptions.standardizeDates">
                          <option v-for="format in dateFormatOptions" :key="format.value" :value="format.value">{{ format.label }}</option>
                        </select>
                      </label>
                      <label class="option-checkbox"><input type="checkbox" v-model="cleaningOptions.removeSpecialChars"> Remove special characters</label>
                      <label class="option-checkbox"><input type="checkbox" v-model="cleaningOptions.changeCase"> Change text case:
                        <select v-model="cleaningOptions.caseType"><option value="none">None</option><option value="upper">UPPER</option><option value="lower">lower</option><option value="title">Title</option></select>
                      </label>
                      <label class="option-checkbox"><input type="checkbox" v-model="cleaningOptions.fillWithCustom"> Fill missing with custom value:
                        <input type="text" v-model="cleaningOptions.customFillValue" placeholder="Value" style="width:100px">
                      </label>
                      <label class="option-checkbox"><input type="checkbox" v-model="cleaningOptions.removeColumnsAllMissing"> Remove columns where ALL values are missing</label>
                      <label class="option-checkbox"><input type="checkbox" v-model="cleaningOptions.capOutliers"> Cap outliers at 3σ</label>
                      <label class="option-checkbox"><input type="checkbox" v-model="cleaningOptions.removeRowsSpecificColumnEmpty"> Remove rows where a specific column is empty:
                        <select v-model="cleaningOptions.specificColumn"><option value="">-- Select --</option><option v-for="col in Object.keys(rawData[0]||{})" :key="col" :value="col">{{ col }}</option></select>
                      </label>
                      <label class="option-checkbox"><input type="checkbox" v-model="cleaningOptions.standardizeNumericRange"> Standardize numeric columns to [0,1]</label>
                      <label class="option-checkbox"><input type="checkbox" v-model="cleaningOptions.removeEmptyRows"> Remove completely empty rows</label>
                      <label class="option-checkbox"><input type="checkbox" v-model="cleaningOptions.fillForward"> Forward fill missing values</label>
                      <label class="option-checkbox"><input type="checkbox" v-model="cleaningOptions.fillBackward"> Backward fill missing values</label>
                    </div>
                  </div>
                  <div class="cleaning-buttons">
                    <button class="btn-primary" @click="applyCleaning">Clean Data</button>
                  </div>
                </div>

                <!-- ===== NEW: Detected Values for Single Instrument ===== -->
                <div v-if="sheetType === 'single'" class="detected-values-section">
                  <h3>Detected Values (Single Instrument)</h3>
                  <p class="section-hint">Review the values detected by Auto Detection. Exclude values you don't want to use for calculations.</p>

                  <div v-if="Object.keys(autoDetectedFields).length > 0" class="detected-values-table">
                    <div class="table-header">
                      <span class="header-field">Field</span>
                      <span class="header-value">Extracted Value</span>
                      <span class="header-status">Status</span>
                      <span class="header-action">Action</span>
                    </div>
                    <div v-for="(value, key) in autoDetectedFields" :key="key" class="table-row" :class="{ 'row-excluded': excludedDetectedFields.has(key) }">
                      <span class="row-field">{{ key }}</span>
                      <div class="row-value">
                        <span class="value-display">{{ formatDetectedValue(key, typeof value === 'object' && value !== null ? value.value : value) }}</span>
                      </div>
                      <span class="row-status" :class="{ 'status-excluded': excludedDetectedFields.has(key), 'status-included': !excludedDetectedFields.has(key) }">
                        {{ excludedDetectedFields.has(key) ? 'Excluded' : 'Included' }}
                      </span>
                      <div class="row-action">
                        <button 
                          class="btn-toggle-exclude" 
                          @click="toggleExcludeField(key)"
                          :class="{ 'btn-exclude': !excludedDetectedFields.has(key), 'btn-include': excludedDetectedFields.has(key) }"
                        >
                          {{ excludedDetectedFields.has(key) ? 'Include' : 'Exclude' }}
                        </button>
                      </div>
                    </div>
                    <!-- Display currency separately if it was selected but not in autoDetectedFields -->
                    <div v-if="selectedCurrency && !autoDetectedFields['Currency']" class="table-row">
                      <span class="row-field">Currency</span>
                      <div class="row-value">
                        <span class="value-display">{{ selectedCurrency === 'custom' ? customCurrency?.toUpperCase() : selectedCurrency }}</span>
                      </div>
                      <span class="row-status status-included">Included</span>
                      <div class="row-action">
                        <button class="btn-toggle-exclude btn-include" disabled>Included</button>
                      </div>
                    </div>

                    <div class="detected-values-summary">
                      <span class="summary-text">
                        {{ Object.keys(autoDetectedFields).length + (selectedCurrency && !autoDetectedFields['Currency'] ? 1 : 0) - excludedDetectedFields.size }} of {{ Object.keys(autoDetectedFields).length + (selectedCurrency && !autoDetectedFields['Currency'] ? 1 : 0) }} values included for calculations
                      </span>
                    </div>

                    <!-- Add Field Section -->
                    <div class="add-field-section">
                      <h4>Add Field</h4>
                      <p class="section-hint">Add a custom field that will be included in calculations.</p>
                      <div class="add-field-form">
                        <input
                          v-model="newFieldName"
                          type="text"
                          placeholder="Field name (e.g., CustomRate)"
                          class="add-field-input"
                        />
                        <input
                          v-model="newFieldValue"
                          type="text"
                          placeholder="Value (e.g., 0.05)"
                          class="add-field-input"
                        />
                        <button class="btn-add-field" @click="addCustomField">Add Field</button>
                      </div>
                    </div>
                  </div>
                  
                  <div v-else class="no-detection-message-cleaning">
                    <p>No fields detected. Please run Auto Detection to detect values from your worksheet.</p>
                  </div>
                </div>
                <div v-if="cleanedData.length" class="preview-section">
                  <h4>Cleaned Data ({{ cleanedData.length }} rows)</h4>
                  <div class="excel-scroll-wrapper">
                    <ExcelViewer :data="cleanedData" :headers="cleanPreviewHeaders" @data-update="onCleanedExcelUpdate" />
                  </div>
                </div>

                <!-- ===== FIXED: Redesigned Cleaning Summary with KPI Cards ===== -->
                <div v-if="cleanedData.length" class="cleaning-summary-cards">
                  <v-row>
                    <v-col cols="12" sm="6" md="3" v-for="stat in cleaningResultStats" :key="stat.title">
                      <v-card class="kpi-card result-kpi">
                        <div class="kpi-top-bar"></div>
                        <v-card-text>
                          <div class="kpi-content">
                            <div class="kpi-icon" :style="{ background: stat.gradient }">
                              <v-icon size="28" color="white">{{ stat.icon }}</v-icon>
                            </div>
                            <div class="kpi-info">
                              <div class="kpi-value">{{ stat.value }}</div>
                              <div class="kpi-title">{{ stat.title }}</div>
                            </div>
                          </div>
                        </v-card-text>
                      </v-card>
                    </v-col>
                  </v-row>
                  
                  <!-- ===== NEW: Cleaning Operations Performed ===== -->
                  <div v-if="cleaningOperationsSummary.length" class="cleaning-operations-summary">
                    <h4 class="operations-title">Operations Performed:</h4>
                    <ul class="operations-list">
                      <li v-for="(operation, index) in cleaningOperationsSummary" :key="index" class="operation-item">
                        <v-icon size="16" color="#4CAF50">mdi-check-circle</v-icon>
                        {{ operation }}
                      </li>
                    </ul>
                  </div>
                  
                  <p class="success-text text-center">✓ Data is now clean and ready for calculations</p>
                </div>

                <div class="navigation-buttons">
                  <button class="btn-secondary" @click="switchTab('upload')">Previous</button>
                  <button class="btn-primary" @click="continueAfterCleaning" :disabled="!cleanedData.length || isCalculating">
                    <v-icon v-if="isCalculating" size="16" class="spin-animation">mdi-loading</v-icon>
                    {{ isCalculating ? 'Calculating...' : 'Continue' }}
                  </button>
                  <button class="btn-secondary" @click="goToDashboard">Dashboard</button>
                </div>
              </div>
            </v-card-text>
          </v-card>
        </div>

        <!-- ===== CALCULATIONS ===== -->
        <div v-if="activeTab === 'calculations'" class="content-card">
          <v-card>
            <v-card-title class="calc-header">
              {{ instrumentLabel }} Calculations
              <span v-if="currentlyViewingInstrument" class="viewing-badge">
                Currently Viewing: <strong>{{ currentlyViewingInstrument }}</strong>
              </span>
              <v-spacer></v-spacer>
              <button
                v-if="instrumentSummary.rows.length >= 2 && sheetType === 'multi'"
                class="btn-calculated-instruments"
                @click="openAllCalculationsPopup"
              >
                Calculated Instruments
              </button>
            </v-card-title>
            <v-card-text>
              <div v-if="!hasCleanedData" class="empty-state">
                <p>No cleaned data. Please clean first.</p>
                <button class="btn-primary" @click="switchTab('cleaning')">Go to Cleaning</button>
              </div>
              <div v-else>
                <div class="summary-cards">
                  <div class="summary-card total" @click="showFormula('Total Portfolio Value')">
                    <div class="card-label">Total Portfolio Value</div>
                    <div class="card-value">{{ formatNumber(allCalculations.totalValue || 0) }}</div>
                  </div>
                  <div class="summary-card rate" @click="showFormula('Average Rate')">
                    <div class="card-label">{{ rateLabel }}</div>
                    <div class="card-value">{{ formatNumber(allCalculations.avgRate || 0) }}%</div>
                  </div>
                  <div class="summary-card count" @click="showFormula('Number of Instruments')">
                    <div class="card-label">Number of Instruments</div>
                    <div class="card-value">{{ allCalculations.instrumentCount || 0 }}</div>
                  </div>
                </div>

                <div v-if="allCalculations.fred?.benchmark_rate" class="comparison-card fred-calc-card">
                  <div class="comparison-item">
                    <span class="comparison-label">FRED market benchmark ({{ allCalculations.fred.series_label }}):</span>
                    <span class="comparison-value market">{{ formatNumber(allCalculations.fred.benchmark_rate) }}%</span>
                  </div>
                  <div class="comparison-item">
                    <span class="comparison-label">Spread vs your portfolio:</span>
                    <span class="comparison-value" :class="(allCalculations.fred.spread_vs_market || 0) >= 0 ? 'negative' : 'positive'">{{ formatNumber(allCalculations.fred.spread_vs_market) }}%</span>
                  </div>
                  <small class="fred-meta">{{ allCalculations.fred.country_name || allCalculations.fred.country }} · {{ allCalculations.fred.currency }} · {{ allCalculations.fred.maturity }} · FRED</small>
                  <small v-if="allCalculations.fred.note" class="fred-meta">{{ allCalculations.fred.note }}</small>
                </div>

                <!-- Field Detection Results -->
                <div v-if="fieldDetectionResults.summary && fieldDetectionResults.summary.total_fields_detected > 0" class="field-detection-card">
                  <div class="field-detection-header">
                    <v-icon small>mdi-magnify</v-icon>
                    Field Detection Results
                    <button class="btn-toggle-detection" @click="showFieldDetection = !showFieldDetection">
                      {{ showFieldDetection ? 'Hide' : 'Show Details' }}
                    </button>
                  </div>
                  <div class="detection-summary">
                    <span class="detection-stat">
                      <strong>{{ fieldDetectionResults.summary.total_fields_detected }}</strong> fields detected
                    </span>
                    <span class="detection-stat input">
                      <strong>{{ fieldDetectionResults.summary.input_fields }}</strong> inputs
                    </span>
                    <span class="detection-stat existing">
                      <strong>{{ fieldDetectionResults.summary.existing_fields }}</strong> existing values
                    </span>
                    <span class="detection-stat derived">
                      <strong>{{ fieldDetectionResults.summary.derived_fields }}</strong> derived
                    </span>
                    <span class="detection-stat missing">
                      <strong>{{ fieldDetectionResults.summary.missing_fields }}</strong> missing
                    </span>
                  </div>
                  <div v-if="showFieldDetection" class="detection-details">
                    <div v-for="(field, fieldName) in fieldDetectionResults.detected_fields" :key="fieldName" class="detection-field-item">
                      <span class="field-name">{{ fieldName }}</span>
                      <span class="field-value">{{ field.value !== null ? field.value : 'N/A' }}</span>
                      <span class="field-type" :class="field.value_type">{{ field.value_type }}</span>
                      <span class="field-source">{{ field.source }}</span>
                      <span class="field-confidence">{{ Math.round(field.confidence * 100) }}%</span>
                    </div>
                  </div>
                </div>

                <div class="calculations-section">
                  <h3>{{ instrumentLabel }} Calculations</h3>
                  
                  <!-- Calculating Animation -->
                  <div v-if="isCalculating" class="calculating-animation">
                    <v-icon size="16" class="spin-animation">mdi-loading</v-icon>
                    <span>Calculating...</span>
                  </div>
                  
                  <div v-else class="calculations-grid">
                    <div
                      v-for="calc in calculationFields"
                      :key="calc.key"
                      class="calculation-card"
                      @click="showFormula(calc.key)"
                    >
                      <div class="calc-name">{{ calc.label }}</div>
                      <div class="calc-value">{{ formatCalcValue(calc.key, calc.value) }}</div>
                    </div>
                  </div>
                </div>

                <v-dialog v-model="showAllCalculationsPopup" max-width="95%" width="1400px" persistent>
                  <v-card>
                    <div class="popup-header-white">
                      <div class="header-left">
                        <div class="header-title">
                          <h4>Calculated Instruments</h4>
                          <p class="header-meta"><strong>{{ activeSession?.name || '' }}</strong></p>
                        </div>
                      </div>
                      <button class="close-btn" @click="closeAllCalculationsPopup">×</button>
                    </div>
                    <v-card-text class="popup-body">
                      <div v-if="instrumentSummary.rows.length === 0" class="empty-state">
                        <p>No instruments detected. Please process a worksheet first.</p>
                      </div>
                      <div v-else class="excel-table-container">
                        <div class="search-bar-container">
                          <input 
                            type="text" 
                            v-model="instrumentSearchQuery" 
                            placeholder="Search instruments..." 
                            class="search-input"
                          />
                          <v-icon class="search-icon">mdi-magnify</v-icon>
                        </div>
                        <p class="popup-instruction">View all calculated instrument values below.</p>
                        <table class="excel-table">
                          <thead>
                            <tr>
                              <th v-for="col in instrumentSummaryColumnsForDisplay" :key="col">{{ col }}</th>
                            </tr>
                          </thead>
                          <tbody>
                            <tr
                              v-for="(row, idx) in sortedInstrumentSummaryRows"
                              :key="idx"
                            >
                              <td v-for="col in instrumentSummaryColumnsForDisplay" :key="col">
                                {{ formatTableCell(row[col], col) }}
                              </td>
                            </tr>
                          </tbody>
                        </table>
                      </div>
                    </v-card-text>
                    <v-card-actions class="popup-footer">
                      <span v-if="currentlyViewingInstrument" class="viewing-indicator">
                        <v-icon small>mdi-eye</v-icon> Currently viewing: <strong>{{ currentlyViewingInstrument }}</strong>
                      </span>
                      <v-spacer></v-spacer>
                      <button class="btn-primary" @click="downloadCalculatedInstrumentsExcel" style="margin-right: 10px;">
                        <v-icon small style="margin-right: 5px;">mdi-download</v-icon> Download Excel
                      </button>
                      <button class="btn-secondary" @click="closeAllCalculationsPopup">Close</button>
                    </v-card-actions>
                  </v-card>
                </v-dialog>

                <div class="navigation-buttons">
                  <button class="btn-secondary" @click="switchTab('cleaning')">Previous</button>
                  <button class="btn-primary" @click="continueToVisualizations">Continue</button>
                  <button class="btn-secondary" @click="goToDashboard">Dashboard</button>
                </div>
              </div>
            </v-card-text>
          </v-card>
        </div>

        <!-- ===== VISUALIZATIONS ===== -->
        <div v-if="activeTab === 'visualizations'" class="content-card">
          <v-card>
            <v-card-title><v-icon>mdi-chart-line</v-icon> {{ instrumentLabel }} – Yield Curve</v-card-title>
            <v-card-text>
              <div v-if="hasCleanedData && yieldCurveData.length" class="comparison-card">
                <div class="comparison-item">
                  <span class="comparison-label">Portfolio Average Rate:</span>
                  <span class="comparison-value portfolio">{{ formatNumber(portfolioAvgRate) }}%</span>
                </div>
                <div class="comparison-item">
                  <span class="comparison-label">Benchmark Yield ({{ selectedMaturityOptionLabel }}):</span>
                  <span class="comparison-value market">{{ benchmarkYield !== null ? formatNumber(benchmarkYield) + '%' : '—' }}</span>
                </div>
                <div class="comparison-difference" :class="{ 'positive': benchmarkYield - portfolioAvgRate > 0, 'negative': benchmarkYield - portfolioAvgRate < 0 }">
                  Difference: {{ benchmarkYield !== null ? formatNumber(benchmarkYield - portfolioAvgRate) : '—' }}%
                </div>
              </div>

              <div class="filters-row">
                <div class="filter-group">
                  <label>Country / Region</label>
                  <select v-model="selectedCountryOption" @change="onCountrySelectChange" class="filter-select">
                    <option v-for="opt in displayCountryOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
                    <option value="__custom__">✏️ Custom...</option>
                  </select>
                  <input
                    v-if="selectedCountryOption === '__custom__'"
                    v-model="customCountryInput"
                    @input="onCustomCountryInput"
                    placeholder="Type country code (e.g. ZAF)"
                    class="filter-custom-input"
                  />
                </div>
                <div class="filter-group">
                  <label>Currency</label>
                  <select v-model="selectedCurrencyOption" @change="onCurrencySelectChange" class="filter-select">
                    <option v-for="opt in displayCurrencyOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
                    <option value="__custom__">✏️ Custom...</option>
                  </select>
                  <input
                    v-if="selectedCurrencyOption === '__custom__'"
                    v-model="customCurrencyInput"
                    @input="onCustomCurrencyInput"
                    placeholder="Type currency code (e.g. ZWL)"
                    class="filter-custom-input"
                  />
                </div>
                <div class="filter-group">
                  <label>Maturity / Date Range</label>
                  <div class="maturity-toggle">
                    <button 
                      class="toggle-btn" 
                      :class="{ active: maturityMode === 'maturity' }"
                      @click="maturityMode = 'maturity'"
                    >Maturity</button>
                    <button 
                      class="toggle-btn" 
                      :class="{ active: maturityMode === 'dateRange' }"
                      @click="maturityMode = 'dateRange'"
                    >Date Range</button>
                  </div>
                  <select v-if="maturityMode === 'maturity'" v-model="selectedMaturityOption" @change="onMaturitySelectChange" class="filter-select">
                    <option v-for="opt in maturityOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
                    <option value="__custom__">✏️ Custom...</option>
                  </select>
                  <input
                    v-if="maturityMode === 'maturity' && selectedMaturityOption === '__custom__'"
                    v-model="customMaturityInput"
                    @input="onCustomMaturityInput"
                    placeholder="e.g. 3Y, 6M, 13W"
                    class="filter-custom-input"
                  />
                  <div v-if="maturityMode === 'dateRange'" class="date-range-inputs">
                    <input 
                      type="date" 
                      v-model="yieldCurveStartDate" 
                      class="date-input-small"
                      placeholder="Start Date"
                    />
                    <input 
                      type="date" 
                      v-model="yieldCurveEndDate" 
                      class="date-input-small"
                      placeholder="End Date"
                    />
                  </div>
                </div>
                <button class="btn-secondary refresh-btn" @click="fetchYieldCurve" :disabled="yieldCurveLoading">Refresh curve</button>
              </div>

              <div v-if="yieldCurveLoading" class="loading-container">
                <v-icon size="48" class="spin">mdi-loading</v-icon>
                <p>Fetching yield curve from FRED...</p>
              </div>
              <div v-else-if="yieldCurveError && !yieldCurveData.length" class="error-container">
                <v-icon color="error" size="48">mdi-alert-circle-outline</v-icon>
                <p>{{ yieldCurveError }}</p>
                <button class="btn-primary" @click="fetchYieldCurve">Retry</button>
              </div>
              <div v-else-if="yieldCurveData.length" class="chart-container chart-container--fred">
                <canvas ref="yieldCurveChart" width="800" height="400" style="background: white; border-radius: 8px;"></canvas>
                <div class="chart-footer">
                  <small>Source: FRED – {{ chartSeriesLabel }} ({{ getCountryLabel(effectiveCountry) }} / {{ getCurrencyLabel(effectiveCurrency) }})</small>
                </div>
              </div>
              <div v-else class="visualization-placeholder">
                <v-icon size="64" color="#0B2044">mdi-chart-line</v-icon>
                <h3>No Yield Curve Loaded</h3>
                <p>Click the <strong>Refresh curve</strong> button above to fetch the latest yield curve.</p>
                <button class="btn-primary" @click="fetchYieldCurve" style="margin-top: 16px;">Load Yield Curve</button>
              </div>

              <div class="navigation-buttons">
                <button class="btn-secondary" @click="switchTab('calculations')">Previous</button>
                <button class="btn-primary" @click="continueFromVisualizations">Continue</button>
                <button class="btn-secondary" @click="goToDashboard">Dashboard</button>
              </div>
            </v-card-text>
          </v-card>
        </div>

        <!-- ===== SUMMARY ===== -->
        <div v-if="activeTab === 'summary'" class="content-card">
          <v-card class="summary-pro-card">
            <v-card-title>
              <v-icon>mdi-file-document-outline</v-icon> {{ instrumentLabel }} – Executive Summary
            </v-card-title>
            <v-card-text>
              <div v-if="!instrumentSummary.rows.length && !completedInstrumentSummary.rows.length" class="empty-state">
                <p>No summary data available. Please run calculations first.</p>
              </div>
              <div v-else>
                <!-- Summary Tabs -->
                <div class="summary-tabs">
                  <button 
                    class="summary-tab" 
                    :class="{ active: activeSummaryTab === 'current' }"
                    @click="activeSummaryTab = 'current'"
                    :disabled="!instrumentSummary.rows.length"
                  >
                    <v-icon size="16">mdi-file</v-icon>
                    Current Summary
                    <span class="tab-count">{{ instrumentSummary.rows.length }}</span>
                  </button>
                  <button 
                    class="summary-tab" 
                    :class="{ active: activeSummaryTab === 'previous' }"
                    @click="activeSummaryTab = 'previous'"
                    :disabled="!currentWorkbookPreviousSummaries.length"
                  >
                    <v-icon size="16">mdi-history</v-icon>
                    Previous Summaries
                    <span class="tab-count">{{ currentWorkbookPreviousSummaries.length }}</span>
                  </button>
                  <button 
                    class="summary-tab" 
                    :class="{ active: activeSummaryTab === 'all' }"
                    @click="activeSummaryTab = 'all'"
                    :disabled="!instrumentSummary.rows.length && !currentWorkbookPreviousSummaries.length"
                  >
                    <v-icon size="16">mdi-view-list</v-icon>
                    View All
                    <span class="tab-count">{{ instrumentSummary.rows.length + currentWorkbookPreviousSummaries.length }}</span>
                  </button>
                </div>

                <!-- Current Summary Section -->
                <div v-if="activeSummaryTab === 'current' || activeSummaryTab === 'all'" class="summary-section">
                  <div v-if="instrumentSummary.rows.length" class="section-header">
                    <h3>
                      <v-icon size="20" style="color: #4CAF50;">mdi-file</v-icon>
                      Current Selection Summary
                      <span class="worksheet-badge">{{ currentSheetName || 'Current' }}</span>
                    </h3>
                    <button class="btn-secondary btn-sm" @click="viewCurrentSummary">
                      <v-icon size="14">mdi-table-large</v-icon> View Excel
                    </button>
                  </div>
                  
                  <div v-if="instrumentSummary.rows.length" class="analytics-section" style="margin-bottom: 24px;">
                    <h3 style="margin-bottom: 16px; color: #0B2044; font-size: 18px; font-weight: 600;">
                      <i class="fas fa-chart-line" style="color: #1a4d8f; margin-right: 8px;"></i> Descriptive Analytics
                    </h3>
                    <div class="analytics-cards">
                      <div class="kpi-card simple-kpi">
                        <div class="kpi-top-bar"></div>
                        <div class="kpi-info">
                          <div class="kpi-value">{{ descriptiveAnalytics['Number of Records'] || '0' }}</div>
                          <div class="kpi-title">Number of Instruments</div>
                        </div>
                      </div>
                      <div class="kpi-card simple-kpi">
                        <div class="kpi-top-bar"></div>
                        <div class="kpi-info">
                          <div class="kpi-value">{{ descriptiveAnalytics['Total Face Value'] || '0.00' }}</div>
                          <div class="kpi-title">Total Face Value</div>
                        </div>
                      </div>
                      <div class="kpi-card simple-kpi">
                        <div class="kpi-top-bar"></div>
                        <div class="kpi-info">
                          <div class="kpi-value">{{ descriptiveAnalytics['Weighted Average Yield'] || '0.00' }}%</div>
                          <div class="kpi-title">Weighted Avg Yield</div>
                        </div>
                      </div>
                      <div class="kpi-card simple-kpi">
                        <div class="kpi-top-bar"></div>
                        <div class="kpi-info">
                          <div class="kpi-value">{{ descriptiveAnalytics['Weighted Average Maturity'] || '0.00' }}</div>
                          <div class="kpi-title">Weighted Avg Maturity</div>
                        </div>
                      </div>
                      <div class="kpi-card simple-kpi">
                        <div class="kpi-top-bar"></div>
                        <div class="kpi-info">
                          <div class="kpi-value">{{ descriptiveAnalytics['Average Rate'] || '0.00' }}%</div>
                          <div class="kpi-title">Average Rate</div>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div v-if="instrumentSummary.rows.length" class="quality-control-section" style="margin-bottom: 24px;">
                    <h3 style="margin-bottom: 16px; color: #0B2044; font-size: 18px; font-weight: 600;">
                      <i class="fas fa-check-circle" style="color: #1a4d8f; margin-right: 8px;"></i> Quality Control
                    </h3>
                    <div class="quality-cards">
                      <div class="kpi-card simple-kpi">
                        <div class="kpi-top-bar"></div>
                        <div class="kpi-info">
                          <div class="kpi-value">{{ dataQualitySummary.completeness || 0 }}%</div>
                          <div class="kpi-title">Data Completeness</div>
                        </div>
                      </div>
                      <div class="kpi-card simple-kpi">
                        <div class="kpi-top-bar"></div>
                        <div class="kpi-info">
                          <div class="kpi-value">{{ dataQualitySummary.columnsMapped || 0 }} / {{ requiredColumns.length }}</div>
                          <div class="kpi-title">Columns Mapped</div>
                        </div>
                      </div>
                      <div class="kpi-card simple-kpi">
                        <div class="kpi-top-bar"></div>
                        <div class="kpi-info">
                          <div class="kpi-value">{{ dataQualitySummary.rowsProcessed || 0 }}</div>
                          <div class="kpi-title">Rows Processed</div>
                        </div>
                      </div>
                      <div class="kpi-card simple-kpi">
                        <div class="kpi-top-bar"></div>
                        <div class="kpi-info">
                          <div class="kpi-value">{{ dataQualitySummary.duplicatesRemoved || 0 }}</div>
                          <div class="kpi-title">Duplicates Removed</div>
                        </div>
                      </div>
                      <div class="kpi-card simple-kpi">
                        <div class="kpi-top-bar"></div>
                        <div class="kpi-info">
                          <div class="kpi-value">{{ dataQualitySummary.missingValuesFixed || 0 }}</div>
                          <div class="kpi-title">Missing Values Fixed</div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- Previous Summaries Section -->
                <div v-if="activeSummaryTab === 'previous' || activeSummaryTab === 'all'" class="summary-section">
                  <div v-if="currentWorkbookPreviousSummaries.length" class="section-header">
                    <h3>
                      <v-icon size="20" style="color: #2196F3;">mdi-history</v-icon>
                      Previous Summaries (Current Workbook)
                      <span class="worksheet-badge">{{ currentWorkbookPreviousSummaries.length }} records</span>
                    </h3>
                    <div style="display: flex; gap: 10px;">
                      <button class="btn-secondary btn-sm" @click="viewPreviousSummariesExcel">
                        <v-icon size="14">mdi-table-large</v-icon> View Excel
                      </button>
                      <button class="btn-secondary btn-sm" @click="exportSummary">
                        <v-icon size="14">mdi-download</v-icon> Export All
                      </button>
                    </div>
                  </div>
                  
                  <!-- Excel-style table display for previous summaries -->
                  <div v-if="currentWorkbookPreviousSummaries.length" class="excel-table-container" style="margin-top: 20px;">
                    <table class="excel-table">
                      <thead>
                        <tr>
                          <th>Instrument Name</th>
                          <th>Worksheet</th>
                          <th>Instrument Type</th>
                          <th>Total Value</th>
                          <th>Average Rate</th>
                          <th>Workbook</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr v-for="(row, idx) in currentWorkbookPreviousSummaries.slice(0, 20)" :key="idx">
                          <td>{{ row['Instrument Name'] || row['instrument_name'] || `Record ${idx + 1}` }}</td>
                          <td>{{ row['Worksheet'] || row['worksheet'] || 'Unknown' }}</td>
                          <td>{{ row['Instrument Type'] || row['instrument_type'] || 'N/A' }}</td>
                          <td>{{ formatNumber(row['Total Value'] || row['total_value'] || 0) }}</td>
                          <td>{{ formatNumber(row['Average Rate'] || row['average_rate'] || 0) }}%</td>
                          <td>{{ row['Workbook'] || 'Unknown' }}</td>
                        </tr>
                      </tbody>
                    </table>
                    <div v-if="currentWorkbookPreviousSummaries.length > 20" class="show-more-indicator" style="padding: 10px; text-align: center; color: #666;">
                      ... and {{ currentWorkbookPreviousSummaries.length - 20 }} more records (click View Excel to see all)
                    </div>
                  </div>
                  <div v-else class="empty-state">
                    <p>No previous summaries for current workbook.</p>
                  </div>
                </div>

                <div class="summary-report" v-if="activeSummaryTab === 'current'">
                  <div class="excel-viewer-button" style="text-align: center; margin-top: 20px;">
                    <button class="btn-primary" @click="viewCurrentSummary" style="font-size: 18px; padding: 16px 40px;">
                      📊 View Current Valuations
                    </button>
                  </div>
                  <div class="workbook-actions" style="text-align: center; margin-top: 30px; padding: 20px; background: #f8f9fa; border-radius: 8px;">
                    <h4 style="margin-bottom: 15px; color: #0B2044;">Continue Working</h4>
                    <div style="display: flex; gap: 15px; justify-content: center; flex-wrap: wrap;">
                      <button class="btn-secondary" @click="continueWorkingOnCurrent" style="padding: 12px 24px;">
                        <v-icon size="16" style="margin-right: 8px;">mdi-pencil</v-icon>
                        Continue on Current Sheet
                      </button>
                      <button class="btn-primary" @click="chooseAnotherSheet" style="padding: 12px 24px;">
                        <v-icon size="16" style="margin-right: 8px;">mdi-table-multiple</v-icon>
                        Choose Another Sheet
                      </button>
                    </div>
                    <p style="margin-top: 12px; font-size: 13px; color: #666;">
                      Current worksheet: <strong>{{ currentSheetName || 'Not selected' }}</strong>
                    </p>
                  </div>
                </div>

                <div class="summary-report" v-if="activeSummaryTab === 'previous'">
                  <div class="excel-viewer-button" style="text-align: center; margin-top: 20px;">
                    <button class="btn-primary" @click="viewPreviousSummary" style="font-size: 18px; padding: 16px 40px;">
                      📊 View Last Previous Valuation
                    </button>
                  </div>
                  <div class="workbook-actions" style="text-align: center; margin-top: 30px; padding: 20px; background: #f8f9fa; border-radius: 8px;">
                    <h4 style="margin-bottom: 15px; color: #0B2044;">Continue Working</h4>
                    <div style="display: flex; gap: 15px; justify-content: center; flex-wrap: wrap;">
                      <button class="btn-secondary" @click="continueWorkingOnCurrent" style="padding: 12px 24px;">
                        <v-icon size="16" style="margin-right: 8px;">mdi-pencil</v-icon>
                        Continue on Current Sheet
                      </button>
                      <button class="btn-primary" @click="chooseAnotherSheet" style="padding: 12px 24px;">
                        <v-icon size="16" style="margin-right: 8px;">mdi-table-multiple</v-icon>
                        Choose Another Sheet
                      </button>
                    </div>
                    <p style="margin-top: 12px; font-size: 13px; color: #666;">
                      Current worksheet: <strong>{{ currentSheetName || 'Not selected' }}</strong>
                    </p>
                  </div>
                </div>

                <div class="summary-report" v-if="activeSummaryTab === 'all'">
                  <div class="excel-viewer-button" style="text-align: center; margin-top: 20px;">
                    <button class="btn-primary" @click="viewAllSummaries" style="font-size: 18px; padding: 16px 40px;">
                      📊 View All Valuations
                    </button>
                  </div>
                  <div class="workbook-actions" style="text-align: center; margin-top: 30px; padding: 20px; background: #f8f9fa; border-radius: 8px;">
                    <h4 style="margin-bottom: 15px; color: #0B2044;">Continue Working</h4>
                    <div style="display: flex; gap: 15px; justify-content: center; flex-wrap: wrap;">
                      <button class="btn-secondary" @click="continueWorkingOnCurrent" style="padding: 12px 24px;">
                        <v-icon size="16" style="margin-right: 8px;">mdi-pencil</v-icon>
                        Continue on Current Sheet
                      </button>
                      <button class="btn-primary" @click="chooseAnotherSheet" style="padding: 12px 24px;">
                        <v-icon size="16" style="margin-right: 8px;">mdi-table-multiple</v-icon>
                        Choose Another Sheet
                      </button>
                    </div>
                    <p style="margin-top: 12px; font-size: 13px; color: #666;">
                      Current worksheet: <strong>{{ currentSheetName || 'Not selected' }}</strong>
                    </p>
                  </div>
                </div>

                <div class="summary-report" v-if="activeSummaryTab === 'all'">
                  <div class="excel-viewer-button" style="text-align: center; margin-top: 20px;">
                    <button class="btn-primary" @click="exportSummary" style="font-size: 18px; padding: 16px 40px;">
                      📊 Export All Summaries (Current + Previous)
                    </button>
                  </div>
                  <div class="workbook-actions" style="text-align: center; margin-top: 30px; padding: 20px; background: #f8f9fa; border-radius: 8px;">
                    <h4 style="margin-bottom: 15px; color: #0B2044;">Continue Working</h4>
                    <div style="display: flex; gap: 15px; justify-content: center; flex-wrap: wrap;">
                      <button class="btn-secondary" @click="continueWorkingOnCurrent" style="padding: 12px 24px;">
                        <v-icon size="16" style="margin-right: 8px;">mdi-pencil</v-icon>
                        Continue on Current Sheet
                      </button>
                      <button class="btn-primary" @click="chooseAnotherSheet" style="padding: 12px 24px;">
                        <v-icon size="16" style="margin-right: 8px;">mdi-table-multiple</v-icon>
                        Choose Another Sheet
                      </button>
                    </div>
                    <p style="margin-top: 12px; font-size: 13px; color: #666;">
                      Current worksheet: <strong>{{ currentSheetName || 'Not selected' }}</strong>
                    </p>
                  </div>
                </div>
              </div>

              <Teleport to="body">
                <div v-if="showInstrumentExcelPopup" class="excel-popup-overlay" @click="closeInstrumentExcelPopup">
                  <div class="excel-popup-content" @click.stop>
                    <div class="popup-header-white">
                      <div class="header-left">
                        <div class="header-title">
                          <h4>Instrument Summary – {{ selectedInstrumentType }}</h4>
                          <p class="header-meta"><strong>{{ activeSession?.name || 'N/A' }}</strong></p>
                        </div>
                      </div>
                      <button class="close-btn" @click="closeInstrumentExcelPopup">×</button>
                    </div>
                    <div class="popup-body">
                      <div class="search-bar-container">
                        <input 
                          type="text" 
                          v-model="instrumentSearchQuery" 
                          placeholder="Search instruments..." 
                          class="search-input"
                        />
                        <v-icon class="search-icon">mdi-magnify</v-icon>
                      </div>
                      <p class="popup-instruction" v-if="excelPopupMode === 'current'">
                        <strong>Current Valuations:</strong> Calculations from the current worksheet/section
                      </p>
                      <p class="popup-instruction" v-else-if="excelPopupMode === 'previous'">
                        <strong>Last Previous Valuation:</strong> Most recent previous calculation from this workbook
                      </p>
                      <p class="popup-instruction" v-else-if="excelPopupMode === 'all'">
                        <strong>All Valuations:</strong> Current and all previous calculations from this workbook
                      </p>
                      <div class="excel-table-wrapper">
                        <table class="excel-table">
                          <thead>
                            <tr>
                              <th v-for="col in instrumentSummaryColumnsForDisplay" :key="col" @click="sortByColumn(col)" class="sortable-header">
                                <span>{{ col }}</span>
                                <span class="sort-indicator" v-if="sortColumn === col">{{ sortOrder === 'asc' ? '▲' : '▼' }}</span>
                              </th>
                            </tr>
                          </thead>
                          <tbody>
                            <tr v-for="(row, idx) in paginatedInstrumentSummaryRows" :key="idx">
                              <td v-for="col in instrumentSummaryColumnsForDisplay" :key="col">{{ formatCellValue(row[col], col) }}</td>
                            </tr>
                          </tbody>
                        </table>
                      </div>
                      <div v-if="totalPages > 1" class="pagination-controls">
                        <button @click="currentPage = 1" :disabled="currentPage === 1">First</button>
                        <button @click="currentPage--" :disabled="currentPage === 1">Previous</button>
                        <span>Page {{ currentPage }} of {{ totalPages }}</span>
                        <button @click="currentPage++" :disabled="currentPage === totalPages">Next</button>
                        <button @click="currentPage = totalPages" :disabled="currentPage === totalPages">Last</button>
                      </div>
                    </div>
                    <div class="popup-footer">
                      <span v-if="activeValuationDate" class="valuation-date-footer">Valuation Date: {{ activeValuationDate }}</span>
                      <button class="btn-secondary" @click="closeInstrumentExcelPopup">Close</button>
                    </div>
                  </div>
                </div>
              </Teleport>

              <div v-if="showWorkflowPopup" class="excel-popup-overlay" @click="closeWorkflowPopup">
                <div class="excel-popup-content" @click.stop>
                  <div class="popup-header-white">
                    <h3>🔄 Workflow Options</h3>
                    <button class="close-btn" @click="closeWorkflowPopup">×</button>
                  </div>
                  <div class="popup-body">
                    <p><strong>Instrument:</strong> {{ selectedWorkflowInstrument?.['Instrument Name'] || `Instrument ${selectedWorkflowIndex + 1}` }}</p>
                    <p><strong>Type:</strong> {{ selectedWorkflowInstrument?.['Instrument Type'] || selectedInstrumentType }}</p>
                    <div class="workflow-options">
                      <button class="workflow-option-btn" @click="navigateToUpload"><v-icon>mdi-upload</v-icon><span>Upload New Data</span></button>
                      <button class="workflow-option-btn" @click="navigateToCleaning"><v-icon>mdi-broom</v-icon><span>Cleaning</span></button>
                      <button class="workflow-option-btn" @click="navigateToCalculations"><v-icon>mdi-calculator</v-icon><span>Calculations</span></button>
                      <button class="workflow-option-btn" @click="navigateToVisualizations"><v-icon>mdi-chart-line</v-icon><span>Visualizations</span></button>
                    </div>
                  </div>
                  <div class="popup-footer">
                    <button class="btn-secondary" @click="closeWorkflowPopup">Close</button>
                  </div>
                </div>
              </div>

              <div class="navigation-buttons">
                <button class="btn-secondary" @click="switchTab('visualizations')">Previous</button>
                <button class="btn-primary" @click="goToReportTab">Continue to Report →</button>
                <button class="btn-primary" @click="goToPortfolioSummary" style="margin-left:10px;">Continue to Portfolio Summary →</button>
                <button class="btn-secondary" @click="goToDashboard">Dashboard</button>
              </div>
            </v-card-text>
          </v-card>
        </div>

        <!-- ===== REPORTS ===== -->
        <div v-if="activeTab === 'reports'" class="content-card">
          <v-card>
            <v-card-title><v-icon>mdi-file-pdf-box</v-icon> Generate Combined Report</v-card-title>
            <v-card-text>
              <div class="report-options">
                <div class="instrument-selection">
                  <h3>Select Instruments to Include</h3>
                  <div class="selection-cards">
                    <div class="selection-card" :class="{ active: selectedInstruments['money-market'] }" @click="selectedInstruments['money-market'] = !selectedInstruments['money-market']">
                      <v-icon size="28" color="#1E88E5">mdi-chart-line</v-icon>
                      <span>Money Market</span>
                      <div class="check-indicator" v-if="selectedInstruments['money-market']"><v-icon size="16" color="#4CAF50">mdi-check-circle-outline</v-icon></div>
                    </div>
                    <div class="selection-card" :class="{ active: selectedInstruments.bonds }" @click="selectedInstruments.bonds = !selectedInstruments.bonds">
                      <v-icon size="28" color="#4CAF50">mdi-chart-timeline</v-icon>
                      <span>Bonds</span>
                      <div class="check-indicator" v-if="selectedInstruments.bonds"><v-icon size="16" color="#4CAF50">mdi-check-circle-outline</v-icon></div>
                    </div>
                    <div class="selection-card" :class="{ active: selectedInstruments.tbills }" @click="selectedInstruments.tbills = !selectedInstruments.tbills">
                      <v-icon size="28" color="#FF9800">mdi-finance</v-icon>
                      <span>T-Bills</span>
                      <div class="check-indicator" v-if="selectedInstruments.tbills"><v-icon size="16" color="#4CAF50">mdi-check-circle-outline</v-icon></div>
                    </div>
                  </div>
                  <div class="selection-actions">
                    <button class="btn-secondary" @click="selectAllInstruments">Select All</button>
                    <button class="btn-secondary" @click="deselectAllInstruments">Deselect All</button>
                  </div>
                </div>
                <div class="report-actions">
                  <button class="btn-preview" @click="previewReport">Preview Report</button>
                  <button class="btn-preview" @click="downloadCombinedReport('word')">Download</button>
                </div>
              </div>
              <div class="navigation-buttons">
                <button class="btn-secondary" @click="switchTab('summary')">Previous</button>
                <button class="btn-primary" @click="goToDashboard">Finish & Dashboard</button>
              </div>
            </v-card-text>
          </v-card>
        </div>
      </div>
    </div>

    <!-- Excel Review Dialog -->
    <v-dialog v-model="showExcelDialog" max-width="90%" fullscreen hide-overlay>
      <v-card>
        <v-card-title class="excel-dialog-title-white">
          <div class="header-left">
            <img src="/DuraCapital logo.png" alt="DuraCapital" class="logo" />
            <div class="header-title"><h4>{{ excelDialogTitle }}</h4><p class="header-meta"><strong>{{ activeSession?.name || 'N/A' }}</strong></p></div>
          </div>
          <v-spacer></v-spacer>
          <button class="btn-close-dialog" @click="closeExcelDialog"><v-icon>mdi-close</v-icon></button>
        </v-card-title>
        <v-card-text class="excel-dialog-content pa-0">
          <ExcelViewer :data="excelData" :headers="excelColumns" @data-update="onExcelDataUpdate" />
        </v-card-text>
        <div class="popup-footer">
          <span v-if="activeValuationDate" class="valuation-date-footer">Valuation Date: {{ activeValuationDate }}</span>
          <v-spacer></v-spacer>
          <button class="btn-secondary" @click="closeExcelDialog">Close</button>
        </div>
      </v-card>
    </v-dialog>

    <!-- Formula Dialog -->
    <v-dialog v-model="formulaDialog" max-width="700px">
      <v-card>
        <v-card-title class="formula-dialog-title">
          <v-icon>mdi-ruler</v-icon> Calculation Breakdown
          <v-spacer></v-spacer>
          <button class="btn-close-dialog" @click="formulaDialog = false"><v-icon>mdi-close</v-icon></button>
        </v-card-title>
        <v-card-text class="formula-content">
          <div class="formula-section">
            <h4>Formula Used:</h4>
            <div class="formula-text">{{ formulaText }}</div>
          </div>
          <v-divider v-if="formulaCalculationDetails"></v-divider>
          <div v-if="formulaCalculationDetails" class="calculation-details">
            <h4>Workings with Exact Figures:</h4>
            <div class="calculation-steps">
              <div v-for="(step, idx) in formulaCalculationDetails" :key="idx" class="calculation-step">
                <div class="step-header">
                  <span class="step-label">{{ step.label }}</span>
                  <span class="step-value">{{ step.value }}</span>
                </div>
                <div v-if="step.formula" class="step-formula">{{ step.formula }}</div>
              </div>
            </div>
            <v-divider v-if="formulaCalculationDetails.breakdown"></v-divider>
            <div v-if="formulaCalculationDetails.breakdown" class="breakdown-section">
              <button class="btn-secondary small" @click="showIndividualBreakdown = !showIndividualBreakdown">
                <v-icon small>{{ showIndividualBreakdown ? 'mdi-chevron-up' : 'mdi-chevron-down' }}</v-icon>
                {{ showIndividualBreakdown ? 'Hide' : 'Show' }} Formula Component Breakdown
              </button>
              <div v-if="showIndividualBreakdown" class="breakdown-components">
                <h5>{{ formulaCalculationDetails.breakdown.title }}</h5>
                <div v-for="(component, cIdx) in formulaCalculationDetails.breakdown.components" :key="cIdx" class="component-breakdown">
                  <div class="component-header">
                    <span class="component-name">{{ component.componentName }}</span>
                  </div>
                  <div class="component-calculation">
                    <span class="component-data">{{ component.calculation }}</span>
                  </div>
                  <div class="component-formula">{{ component.formula }}</div>
                </div>
              </div>
            </div>
          </div>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <button class="btn-secondary" @click="formulaDialog = false">Close</button>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Report Preview Dialog -->
    <v-dialog v-model="reportPreviewDialog" max-width="90%" fullscreen hide-overlay>
      <v-card>
        <v-card-title class="excel-dialog-title-white">
          <div class="header-left">
            <img src="/DuraCapital logo.png" alt="DuraCapital" class="logo" />
            <div class="header-title"><h4>Report Preview</h4><p class="header-meta"><strong>{{ activeSession?.name || 'N/A' }}</strong></p></div>
          </div>
          <v-spacer></v-spacer>
          <button class="btn-close-dialog" @click="reportPreviewDialog = false"><v-icon>mdi-close</v-icon></button>
        </v-card-title>
        <v-card-text class="report-preview-content" style="padding:0;">
          <iframe :srcdoc="reportPreviewHtml" frameborder="0" style="width:100%; height:80vh;"></iframe>
        </v-card-text>
        <div class="popup-footer">
          <span v-if="activeValuationDate" class="valuation-date-footer">Valuation Date: {{ activeValuationDate }}</span>
          <v-spacer></v-spacer>
          <button class="btn-preview" @click="downloadFromPreview('word')">Download</button>
        </div>
      </v-card>
    </v-dialog>

    <!-- Modal Excel Viewer -->
    <ExcelModalViewer
      :visible="showModalViewer"
      :fileData="viewerFileData"
      @close="showModalViewer = false"
      @update:visible="(val) => showModalViewer = val"
      @process-sheet="handleProcessSheetFromModal"
    />

    <!-- Snackbar for notifications -->
    <v-snackbar
      v-model="snackbar.show"
      :color="snackbar.color"
      :timeout="snackbar.timeout"
      location="bottom"
    >
      {{ snackbar.message }}
    </v-snackbar>
  </FixedLayout>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import FixedLayout from '@/components/FixedLayout.vue'
import * as XLSX from 'xlsx'
import api from '@/services/api.js'
import sessionManager from '@/services/sessionManager.js'
import mappingTemplateManager from '@/services/mappingTemplateManager.js'
import { useFredMarket } from '@/composables/useFredMarket'
import { useWorksheetWorkflow } from '@/composables/useWorksheetWorkflow.js'
import ExcelViewer from '@/components/ExcelViewer.vue'
import ExcelModalViewer from '@/components/ExcelModalViewer.vue'
import ExcelWorkbookViewer from '@/components/ExcelWorkbookViewer.vue'
import WorksheetSelector from '@/components/WorksheetSelector.vue'
import { markStepCompleted, isStepPersistedCompleted } from '@/utils/workflowProgress.js'
import { autoMatchColumns, isColumnMapped, getMissingColumns } from '@/utils/instrumentMapping'
import { detectSheetType, extractSingleInstrumentValues, getRequiredFieldMappings } from '@/utils/sheetTypeDetector'
import { autoDetectInstrumentFields } from '@/utils/autoDetectInstrument.js'
import Chart from 'chart.js/auto'
import 'chartjs-adapter-date-fns'
import { useInstrumentConfig } from '@/composables/useInstrumentConfig'

function autoDetectTable(data) {
  if (!data || data.length === 0) return { type: 'empty', data: [] }

  const firstRow = data[0]
  let hasHeaders = false
  if (firstRow && typeof firstRow === 'object') {
    const values = Object.values(firstRow)
    hasHeaders = values.some(v => typeof v === 'string' && v.length > 0 && isNaN(v) && !v.match(/^[\d\.,\-]+$/))
  }

  if (!hasHeaders) {
    const columnCount = Math.max(...data.map(row => Object.keys(row).length))
    const headers = Array.from({ length: columnCount }, (_, i) => `Column ${i + 1}`)
    const tableData = data.map(row => {
      const obj = {}
      const values = Object.values(row)
      headers.forEach((h, idx) => {
        obj[h] = values[idx] !== undefined ? values[idx] : ''
      })
      return obj
    })
    return { type: 'table', headers, data: tableData }
  }

  return { type: 'columns', data }
}

const router = useRouter()
const route = useRoute()

const FIELD_MAPPINGS = {
  'money-market': {
    'discount_yield': 'Discount Yield',
    'discountYield': 'Discount Yield',
    'effective_yield': 'Effective Yield',
    'effectiveYield': 'Effective Yield',
    'interest_earned': 'Interest Earned',
    'interestEarned': 'Interest Earned',
    'interest_rate': 'Interest Rate',
    'interestRate': 'Interest Rate',
    'principal': 'Principal',
    'term_days': 'Days to Maturity',
    'termDays': 'Days to Maturity',
    'total_value': 'Total Value',
    'totalValue': 'Total Value',
    'yield_curve_rate': 'Yield Curve Rate',
    'yieldCurveRate': 'Yield Curve Rate',
    'instrument_name': 'Instrument Name',
    'instrument_type': 'Instrument Type',
    'status': 'Status'
  },
  'bonds': {
    'clean_price': 'Clean Price',
    'dirty_price': 'Dirty Price',
    'coupon_rate': 'Coupon Rate',
    'couponRate': 'Coupon Rate',
    'yield_to_maturity': 'Yield to Maturity',
    'yieldToMaturity': 'Yield to Maturity',
    'current_yield': 'Current Yield',
    'currentYield': 'Current Yield',
    'macaulay_duration': 'Macaulay Duration',
    'macaulayDuration': 'Macaulay Duration',
    'modified_duration': 'Modified Duration',
    'modifiedDuration': 'Modified Duration',
    'convexity': 'Convexity',
    'accrued_interest': 'Accrued Interest',
    'accruedInterest': 'Accrued Interest',
    'face_value': 'Face Value',
    'faceValue': 'Face Value',
    'total_value': 'Total Value',
    'totalValue': 'Total Value',
    'instrument_name': 'Instrument Name',
    'instrument_type': 'Instrument Type',
    'status': 'Status'
  },
  'tbills': {
    'discount_rate': 'Discount Rate',
    'discountRate': 'Discount Rate',
    'discount_yield': 'Discount Yield',
    'discountYield': 'Discount Yield',
    'investment_yield': 'Investment Yield',
    'investmentYield': 'Investment Yield',
    'bond_equivalent_yield': 'Bond Equivalent Yield',
    'bondEquivalentYield': 'Bond Equivalent Yield',
    'face_value': 'Face Value',
    'faceValue': 'Face Value',
    'purchase_price': 'Purchase Price',
    'purchasePrice': 'Purchase Price',
    'total_value': 'Total Value',
    'totalValue': 'Total Value',
    'days_to_maturity': 'Days to Maturity',
    'daysToMaturity': 'Days to Maturity',
    'instrument_name': 'Instrument Name',
    'instrument_type': 'Instrument Type',
    'status': 'Status'
  }
}

const INPUT_FIELDS = {
  'money-market': [
    'Principal', 'Interest Rate', 'Discount Rate', 'Purchase Price',
    'Issue Date', 'Maturity Date', 'Settlement Date', 'Days to Maturity',
    'Compounding Frequency', 'Day Count Convention',
    'Status', 'Error', 'Instrument Name', 'Instrument Type'
  ],
  'bonds': [
    'Face Value', 'Par Value', 'Coupon Rate', 'Coupon Frequency',
    'Yield to Maturity', 'Issue Date', 'Maturity Date', 'Settlement Date',
    'Years to Maturity', 'Frequency', 'Day Count Convention',
    'Status', 'Error', 'Instrument Name', 'Instrument Type'
  ],
  'tbills': [
    'Face Value', 'Discount Rate', 'Purchase Price',
    'Issue Date', 'Maturity Date', 'Settlement Date', 'Days to Maturity',
    'Day Count Convention',
    'Status', 'Error', 'Instrument Name', 'Instrument Type'
  ]
}

const CALCULATED_FIELDS = {
  'money-market': [
    'total_value', 'calculated_value', 'present_value', 'fair_value', 'market_value',
    'interest_earned', 'simple_interest', 'compound_interest',
    'discount_amount', 'discount_yield', 'money_market_yield',
    'holding_period_yield', 'annualized_holding_period_yield',
    'effective_yield', 'effective_annual_rate', 'annual_percentage_yield',
    'current_yield', 'yield_to_maturity',
    'yield_curve_rate', 'benchmark_valuation', 'real_yield',
    'investment_return', 'investment_cost', 'net_investment', 'gross_investment'
  ],
  'bonds': [
    'total_value', 'calculated_value', 'present_value', 'fair_value', 'market_value',
    'clean_price', 'dirty_price', 'current_price',
    'coupon_payment', 'annual_coupon',
    'current_yield', 'yield_to_maturity', 'yield_to_call', 'yield_to_worst',
    'macaulay_duration', 'modified_duration', 'effective_duration',
    'dollar_duration', 'convexity', 'dv01', 'pvbp',
    'accrued_interest', 'settlement_value', 'redemption_value',
    'days_accrued', 'days_to_next_coupon', 'days_to_maturity',
    'benchmark_spread', 'g_spread', 'i_spread', 'z_spread',
    'real_yield', 'nominal_yield', 'effective_annual_yield',
    'holding_period_return', 'total_return', 'capital_gain_loss',
    'coupon_income', 'unrealized_gain_loss', 'realized_gain_loss',
    'yield_curve_rate'
  ],
  'tbills': [
    'total_value', 'calculated_value', 'present_value', 'fair_value', 'market_value',
    'discount_amount', 'discount_yield', 'investment_yield',
    'bond_equivalent_yield', 'holding_period_yield',
    'annualized_holding_period_yield', 'money_market_yield',
    'purchase_price', 'redemption_value',
    'days_to_maturity', 'yield_curve_rate'
  ]
}

function mapBackendFieldsToDisplayNames(row, instrumentType) {
  const mapping = FIELD_MAPPINGS[instrumentType] || {}
  const mappedRow = {}
  
  for (const [key, value] of Object.entries(row)) {
    const displayKey = mapping[key] || key
    mappedRow[displayKey] = value
  }
  
  return mappedRow
}

function filterToCalculatedFields(row, instrumentType) {
  const inputFields = INPUT_FIELDS[instrumentType] || []
  const filteredRow = {}
  
  const alwaysInclude = ['Instrument Name', 'Instrument Type', 'Worksheet', 'Workbook']
  
  for (const [key, value] of Object.entries(row)) {
    if (alwaysInclude.includes(key)) {
      filteredRow[key] = value
      continue
    }
    
    const isInput = inputFields.includes(key)
    
    if (!isInput) {
      filteredRow[key] = value
    }
  }
  
  return filteredRow
}

const VALID_FREQUENCIES = /^(annual(ly)?|semi[- ]?annual(ly)?|quarter(ly)?|month(ly)?|weekly|daily|at maturity|zero|bullet|1|2|4|12|52|365)$/i

function isPlausibleValue(canonicalKey, value) {
  if (value === null || value === undefined || value === '') return false

  const lc = String(canonicalKey).toLowerCase()

  if (lc.includes('frequency') || lc.includes('interest') && lc.includes('payment') && lc.includes('frequency') || lc.includes('payment') && lc.includes('frequency')) {
    return VALID_FREQUENCIES.test(String(value).trim())
  }

  if (lc.includes('rate') || lc.includes('yield') || lc.includes('coupon') || lc.includes('discount')) {
    const n = typeof value === 'number' ? value : parseFloat(String(value).replace(/[%,$\s]/g, ''))
    if (isNaN(n)) return false
    return n >= 0 && n <= 100
  }

  if (lc.includes('value') || lc.includes('amount') || lc.includes('price') || lc.includes('principal') || lc.includes('face') || lc.includes('notional') || lc.includes('nominal') || lc.includes('par')) {
    const n = typeof value === 'number' ? value : parseFloat(String(value).replace(/[$,\s]/g, ''))
    if (isNaN(n)) return false
    return n >= 0
  }

  if (lc.includes('date') || lc.includes('maturity') || lc.includes('auction') || lc.includes('settlement') || lc.includes('issue') || lc.includes('coupon') && lc.includes('date')) {
    const d = new Date(value)
    return !isNaN(d.getTime())
  }

  if (lc.includes('days') || lc.includes('term') || lc.includes('tenor') || lc.includes('maturity') && !lc.includes('date')) {
    const n = typeof value === 'number' ? value : parseFloat(String(value))
    if (isNaN(n)) return false
    return n >= 0 && Number.isInteger(n)
  }

  return true
}

function normalizeDetectedFields(fields, fieldsWithMetadata, instrumentType, requiredColsOverride = null) {
  const normalised = {}
  const normalisedMeta = {}
  const usedCanonical = new Set()
  
  const targetColumns = requiredColsOverride || requiredColumns.value || []
  console.log('normalizeDetectedFields target columns:', targetColumns)
  console.log('normalizeDetectedFields input fields:', Object.keys(fields || {}))

  const nameStyleFields = ['InstrumentName', 'BondName', 'TBillName', 'Instrument Name', 'Bond Name', 'T-Bill Name', 'Counterparty', 'Issuer', 'Name', 'Security', 'Security Name', 'Counter Party', 'Counterparty Name', 'Issuer Name', 'Instrument']
  const faceValueFields = ['FaceValue', 'Principal', 'Notional', 'Par', 'ParValue', 'Nominal', 'NominalValue', 'Amount', 'Face Value', 'Par Value', 'Principal Amount', 'Investment Amount', 'Issue Amount', 'Redemption Value', 'Maturity Value', 'Nominal Amount', 'Face Amount', 'Par Amount', 'Notional Amount', 'Purchase Price', 'Future Value']
  const rateFields = ['CouponRate', 'InterestRate', 'DiscountRate', 'Yield', 'YieldToMaturity', 'Rate', 'Interest Rate', 'Coupon Rate', 'Discount Rate', 'Current Yield', 'Yield Rate', 'YTM', 'Discount', 'Coupon', 'Investment Yield', 'Effective Annual Yield', 'Benchmark Rate', 'Reference Rate', 'Spread', 'Margin']
  const dateFields = ['IssueDate', 'MaturityDate', 'SettlementDate', 'ValuationDate', 'AuctionDate', 'NextCouponDate', 'Issue Date', 'Maturity Date', 'Settlement Date', 'Valuation Date', 'Auction Date', 'Next Coupon Date', 'Redemption Date', 'Due Date', 'Expiry Date', 'Value Date', 'Pricing Date', 'Trade Date', 'Effective Date', 'Start Date', 'End Date', 'Call Date', 'Put Date', 'Coupon Date']
  const frequencyFields = ['CouponFrequency', 'InterestPaymentFrequency', 'PaymentFrequency', 'Frequency', 'Coupon Frequency', 'Interest Payment Frequency', 'Payment Freq', 'Pmt Frequency', 'Coupon Freq', 'Interest Pmt Frequency', 'Compounding Frequency']
  const termFields = ['DaysToMaturity', 'Term', 'Tenor', 'Days to Maturity', 'Term (Days)', 'Tenor (Days)', 'Duration', 'Years to Maturity', 'Term in Days', 'Term in Months', 'Term in Years', 'Tenor Days', 'Tenor Months', 'Tenor Years', 'Accrued Days', 'Days in Coupon Period', 'Term to Maturity']
  const currencyFields = ['Currency', 'CurrencyCode', 'Currency Code', 'CCY', 'Denomination', 'Base Currency', 'Local Currency', 'Reporting Currency', 'Exchange Rate', 'FX Rate']
  const statusFields = ['Status', 'State', 'Type', 'Category', 'Classification']
  const priceFields = ['Price', 'Purchase Price', 'Clean Price', 'Dirty Price', 'Market Price', 'Current Price', 'Price per 100', 'Call Price', 'Put Price']
  const interestFields = ['Accrued Interest', 'Interest Accrued', 'Coupon', 'Coupon Amount', 'Coupon Payment', 'Annual Coupon', 'Interest Earned', 'Interest Income', 'Discount Amount']
  const durationFields = ['Macaulay Duration', 'Modified Duration', 'Convexity', 'DV01']
  const returnFields = ['Capital Gain Loss', 'Total Return', 'Profit Return', 'Market Value', 'Present Value', 'Carrying Value', 'Book Value', 'Fair Value', 'Maturity Value', 'Current Value', 'Purchase Cost']

  function isSemanticMatch(detectedKey, targetField, semanticType) {
    const detectedLower = String(detectedKey).toLowerCase().replace(/[\s_\-()]+/g, '')
    const targetLower = String(targetField).toLowerCase().replace(/[\s_\-()]+/g, '')
    
    if (detectedLower === targetLower) return true
    if (detectedLower.includes(targetLower) || targetLower.includes(detectedLower)) return true
    
    const semanticFields = {
      'name': nameStyleFields,
      'faceValue': faceValueFields,
      'rate': rateFields,
      'date': dateFields,
      'frequency': frequencyFields,
      'term': termFields,
      'currency': currencyFields,
      'status': statusFields,
      'price': priceFields,
      'interest': interestFields,
      'duration': durationFields,
      'return': returnFields
    }
    
    const fields = semanticFields[semanticType] || []
    const detectedInList = fields.some(f => f.toLowerCase().replace(/[\s_\-()]+/g, '') === detectedLower)
    const targetInList = fields.some(f => f.toLowerCase().replace(/[\s_\-()]+/g, '') === targetLower)
    
    return detectedInList && targetInList
  }

  const detectedSemantics = {}
  for (const [rawKey, rawValue] of Object.entries(fields || {})) {
    const keyLower = String(rawKey).toLowerCase().replace(/[\s_\-()]+/g, '')
    
    if (nameStyleFields.some(f => {
      const fLower = f.toLowerCase().replace(/[\s_\-()]+/g, '')
      return keyLower.includes(fLower) || fLower.includes(keyLower)
    })) {
      detectedSemantics[rawKey] = 'name'
    } else if (faceValueFields.some(f => {
      const fLower = f.toLowerCase().replace(/[\s_\-()]+/g, '')
      return keyLower.includes(fLower) || fLower.includes(keyLower)
    })) {
      detectedSemantics[rawKey] = 'faceValue'
    } else if (rateFields.some(f => {
      const fLower = f.toLowerCase().replace(/[\s_\-()]+/g, '')
      return keyLower.includes(fLower) || fLower.includes(keyLower)
    })) {
      detectedSemantics[rawKey] = 'rate'
    } else if (dateFields.some(f => {
      const fLower = f.toLowerCase().replace(/[\s_\-()]+/g, '')
      return keyLower.includes(fLower) || fLower.includes(keyLower)
    })) {
      detectedSemantics[rawKey] = 'date'
    } else if (frequencyFields.some(f => {
      const fLower = f.toLowerCase().replace(/[\s_\-()]+/g, '')
      return keyLower.includes(fLower) || fLower.includes(keyLower)
    })) {
      detectedSemantics[rawKey] = 'frequency'
    } else if (termFields.some(f => {
      const fLower = f.toLowerCase().replace(/[\s_\-()]+/g, '')
      return keyLower.includes(fLower) || fLower.includes(keyLower)
    })) {
      detectedSemantics[rawKey] = 'term'
    } else if (currencyFields.some(f => {
      const fLower = f.toLowerCase().replace(/[\s_\-()]+/g, '')
      return keyLower.includes(fLower) || fLower.includes(keyLower)
    })) {
      detectedSemantics[rawKey] = 'currency'
    } else if (statusFields.some(f => {
      const fLower = f.toLowerCase().replace(/[\s_\-()]+/g, '')
      return keyLower.includes(fLower) || fLower.includes(keyLower)
    })) {
      detectedSemantics[rawKey] = 'status'
    } else if (priceFields.some(f => {
      const fLower = f.toLowerCase().replace(/[\s_\-()]+/g, '')
      return keyLower.includes(fLower) || fLower.includes(keyLower)
    })) {
      detectedSemantics[rawKey] = 'price'
    } else if (interestFields.some(f => {
      const fLower = f.toLowerCase().replace(/[\s_\-()]+/g, '')
      return keyLower.includes(fLower) || fLower.includes(keyLower)
    })) {
      detectedSemantics[rawKey] = 'interest'
    } else if (durationFields.some(f => {
      const fLower = f.toLowerCase().replace(/[\s_\-()]+/g, '')
      return keyLower.includes(fLower) || fLower.includes(keyLower)
    })) {
      detectedSemantics[rawKey] = 'duration'
    } else if (returnFields.some(f => {
      const fLower = f.toLowerCase().replace(/[\s_\-()]+/g, '')
      return keyLower.includes(fLower) || fLower.includes(keyLower)
    })) {
      detectedSemantics[rawKey] = 'return'
    } else {
      detectedSemantics[rawKey] = 'generic'
    }
  }

  console.log('Detected semantics:', detectedSemantics)

  const rawEntries = Object.entries(fields || {}).sort(
    (a, b) => String(b[0]).length - String(a[0]).length
  )

  for (const [rawKey, rawValue] of rawEntries) {
    const semantic = detectedSemantics[rawKey]
    
    let matchedCanonical = null
    for (const targetCol of targetColumns) {
      const targetLower = String(targetCol).toLowerCase().replace(/[\s_\-()]+/g, '')
      const rawKeyLower = String(rawKey).toLowerCase().replace(/[\s_\-()]+/g, '')
      
      if (rawKeyLower === targetLower) {
        matchedCanonical = targetCol
        console.log(`Exact match "${rawKey}" to "${targetCol}"`)
        break
      }
      
      if (semantic && isSemanticMatch(rawKey, targetCol, semantic)) {
        matchedCanonical = targetCol
        console.log(`Matched "${rawKey}" to "${targetCol}" (${semantic})`)
        break
      }
      
      if (rawKeyLower.includes(targetLower) || targetLower.includes(rawKeyLower)) {
        matchedCanonical = targetCol
        console.log(`Generic match "${rawKey}" to "${targetCol}"`)
        break
      }
    }
    
    if (!matchedCanonical) {
      console.log(`No match found for "${rawKey}" - will keep as-is`)
      matchedCanonical = rawKey
    }
    
    if (usedCanonical.has(matchedCanonical)) {
      console.log(`Skipping "${matchedCanonical}" - already mapped`)
      continue
    }

    const actualValue =
      rawValue && typeof rawValue === 'object' && 'value' in rawValue
        ? rawValue.value
        : rawValue

    if (semantic !== 'generic' && !isPlausibleValue(matchedCanonical, actualValue)) {
      console.log(`Rejected "${matchedCanonical}": "${actualValue}" (implausible value)`)
      continue
    }

    normalised[matchedCanonical] = actualValue
    usedCanonical.add(matchedCanonical)

    const meta = fieldsWithMetadata ? fieldsWithMetadata[rawKey] : null
    if (meta) normalisedMeta[matchedCanonical] = meta
  }

  console.log('Normalized fields:', normalised)
  return { fields: normalised, fieldsWithMetadata: normalisedMeta }
}

function scanSheetForMissingFields(missingFields, instrumentType, requiredColsOverride = null) {
  if (!originalFileBuffer.value || !currentSheetName.value) return {}
  if (!missingFields || missingFields.length === 0) return {}

  const targetColumns = requiredColsOverride || requiredColumns.value || []
  console.log('Secondary scan for missing fields:', missingFields)
  console.log('Target columns:', targetColumns)

  const nameStyleFields = ['InstrumentName', 'BondName', 'TBillName', 'Instrument Name', 'Bond Name', 'T-Bill Name', 'Counterparty', 'Issuer', 'Name', 'Security', 'Security Name', 'Counter Party', 'Counterparty Name', 'Issuer Name', 'Instrument']
  const faceValueFields = ['FaceValue', 'Principal', 'Notional', 'Par', 'ParValue', 'Nominal', 'NominalValue', 'Amount', 'Face Value', 'Par Value', 'Principal Amount', 'Investment Amount', 'Issue Amount', 'Redemption Value', 'Maturity Value', 'Nominal Amount', 'Face Amount', 'Par Amount', 'Notional Amount', 'Purchase Price', 'Future Value']
  const rateFields = ['CouponRate', 'InterestRate', 'DiscountRate', 'Yield', 'YieldToMaturity', 'Rate', 'Interest Rate', 'Coupon Rate', 'Discount Rate', 'Current Yield', 'Yield Rate', 'YTM', 'Discount', 'Coupon', 'Investment Yield', 'Effective Annual Yield', 'Benchmark Rate', 'Reference Rate', 'Spread', 'Margin']
  const dateFields = ['IssueDate', 'MaturityDate', 'SettlementDate', 'ValuationDate', 'AuctionDate', 'NextCouponDate', 'Issue Date', 'Maturity Date', 'Settlement Date', 'Valuation Date', 'Auction Date', 'Next Coupon Date', 'Redemption Date', 'Due Date', 'Expiry Date', 'Value Date', 'Pricing Date', 'Trade Date', 'Effective Date', 'Start Date', 'End Date', 'Call Date', 'Put Date', 'Coupon Date']
  const frequencyFields = ['CouponFrequency', 'InterestPaymentFrequency', 'PaymentFrequency', 'Frequency', 'Coupon Frequency', 'Interest Payment Frequency', 'Payment Freq', 'Pmt Frequency', 'Coupon Freq', 'Interest Pmt Frequency', 'Compounding Frequency']
  const termFields = ['DaysToMaturity', 'Term', 'Tenor', 'Days to Maturity', 'Term (Days)', 'Tenor (Days)', 'Duration', 'Years to Maturity', 'Term in Days', 'Term in Months', 'Term in Years', 'Tenor Days', 'Tenor Months', 'Tenor Years', 'Accrued Days', 'Days in Coupon Period', 'Term to Maturity']
  const currencyFields = ['Currency', 'CurrencyCode', 'Currency Code', 'CCY', 'Denomination', 'Base Currency', 'Local Currency', 'Reporting Currency', 'Exchange Rate', 'FX Rate']
  const statusFields = ['Status', 'State', 'Type', 'Category', 'Classification']
  const priceFields = ['Price', 'Purchase Price', 'Clean Price', 'Dirty Price', 'Market Price', 'Current Price', 'Price per 100', 'Call Price', 'Put Price']
  const interestFields = ['Accrued Interest', 'Interest Accrued', 'Coupon', 'Coupon Amount', 'Coupon Payment', 'Annual Coupon', 'Interest Earned', 'Interest Income', 'Discount Amount']
  const durationFields = ['Macaulay Duration', 'Modified Duration', 'Convexity', 'DV01']
  const returnFields = ['Capital Gain Loss', 'Total Return', 'Profit Return', 'Market Value', 'Present Value', 'Carrying Value', 'Book Value', 'Fair Value', 'Maturity Value', 'Current Value', 'Purchase Cost']

  function isSemanticMatch(detectedKey, targetField, semanticType) {
    const detectedLower = String(detectedKey).toLowerCase().replace(/[\s_\-()]+/g, '')
    const targetLower = String(targetField).toLowerCase().replace(/[\s_\-()]+/g, '')
    
    if (detectedLower === targetLower) return true
    if (detectedLower.includes(targetLower) || targetLower.includes(detectedLower)) return true
    
    const semanticFields = {
      'name': nameStyleFields,
      'faceValue': faceValueFields,
      'rate': rateFields,
      'date': dateFields,
      'frequency': frequencyFields,
      'term': termFields,
      'currency': currencyFields,
      'status': statusFields,
      'price': priceFields,
      'interest': interestFields,
      'duration': durationFields,
      'return': returnFields
    }
    
    const fields = semanticFields[semanticType] || []
    const detectedInList = fields.some(f => f.toLowerCase().replace(/[\s_\-()]+/g, '') === detectedLower)
    const targetInList = fields.some(f => f.toLowerCase().replace(/[\s_\-()]+/g, '') === targetLower)
    
    return detectedInList && targetInList
  }

  const targetSemantics = {}
  for (const targetCol of targetColumns) {
    const targetLower = targetCol.toLowerCase().replace(/[\s_\-()]+/g, '')
    
    if (nameStyleFields.some(f => {
      const fLower = f.toLowerCase().replace(/[\s_\-()]+/g, '')
      return targetLower.includes(fLower) || fLower.includes(targetLower)
    })) {
      targetSemantics[targetCol] = 'name'
    } else if (faceValueFields.some(f => {
      const fLower = f.toLowerCase().replace(/[\s_\-()]+/g, '')
      return targetLower.includes(fLower) || fLower.includes(targetLower)
    })) {
      targetSemantics[targetCol] = 'faceValue'
    } else if (rateFields.some(f => {
      const fLower = f.toLowerCase().replace(/[\s_\-()]+/g, '')
      return targetLower.includes(fLower) || fLower.includes(targetLower)
    })) {
      targetSemantics[targetCol] = 'rate'
    } else if (dateFields.some(f => {
      const fLower = f.toLowerCase().replace(/[\s_\-()]+/g, '')
      return targetLower.includes(fLower) || fLower.includes(targetLower)
    })) {
      targetSemantics[targetCol] = 'date'
    } else if (frequencyFields.some(f => {
      const fLower = f.toLowerCase().replace(/[\s_\-()]+/g, '')
      return targetLower.includes(fLower) || fLower.includes(targetLower)
    })) {
      targetSemantics[targetCol] = 'frequency'
    } else if (termFields.some(f => {
      const fLower = f.toLowerCase().replace(/[\s_\-()]+/g, '')
      return targetLower.includes(fLower) || fLower.includes(targetLower)
    })) {
      targetSemantics[targetCol] = 'term'
    } else if (currencyFields.some(f => {
      const fLower = f.toLowerCase().replace(/[\s_\-()]+/g, '')
      return targetLower.includes(fLower) || fLower.includes(targetLower)
    })) {
      targetSemantics[targetCol] = 'currency'
    } else if (statusFields.some(f => {
      const fLower = f.toLowerCase().replace(/[\s_\-()]+/g, '')
      return targetLower.includes(fLower) || fLower.includes(targetLower)
    })) {
      targetSemantics[targetCol] = 'status'
    } else if (priceFields.some(f => {
      const fLower = f.toLowerCase().replace(/[\s_\-()]+/g, '')
      return targetLower.includes(fLower) || fLower.includes(targetLower)
    })) {
      targetSemantics[targetCol] = 'price'
    } else if (interestFields.some(f => {
      const fLower = f.toLowerCase().replace(/[\s_\-()]+/g, '')
      return targetLower.includes(fLower) || fLower.includes(targetLower)
    })) {
      targetSemantics[targetCol] = 'interest'
    } else if (durationFields.some(f => {
      const fLower = f.toLowerCase().replace(/[\s_\-()]+/g, '')
      return targetLower.includes(fLower) || fLower.includes(targetLower)
    })) {
      targetSemantics[targetCol] = 'duration'
    } else if (returnFields.some(f => {
      const fLower = f.toLowerCase().replace(/[\s_\-()]+/g, '')
      return targetLower.includes(fLower) || fLower.includes(targetLower)
    })) {
      targetSemantics[targetCol] = 'return'
    }
  }

  console.log('Target semantics:', targetSemantics)

  const found = {}

  try {
    const wb = XLSX.read(originalFileBuffer.value, {
      type: 'array',
      cellDates: true,
      cellNF: false,
      cellText: true
    })
    const sheet = wb.Sheets[currentSheetName.value]
    if (!sheet) return {}

    const aoa = XLSX.utils.sheet_to_json(sheet, {
      header: 1,
      raw: false,
      defval: '',
      blankrows: false
    })

    console.log(`Secondary scan scanning all ${aoa.length} rows`)

    const foundFields = new Set()
    const maxRows = Math.min(aoa.length, 10000)

    for (let r = 0; r < maxRows; r++) {
      if (foundFields.size === missingFields.length) {
        console.log(`Secondary scan found all ${missingFields.length} fields, stopping at row ${r}`)
        break
      }
      
      const row = aoa[r]
      if (!row) continue
      for (let c = 0; c < row.length; c++) {
        const cell = row[c]
        if (cell === null || cell === undefined || cell === '') continue

        const cellLower = String(cell).toLowerCase().replace(/[\s_\-()]+/g, '')

        let cellSemantic = null
        
        if (nameStyleFields.some(f => {
          const fLower = f.toLowerCase().replace(/[\s_\-()]+/g, '')
          return cellLower.includes(fLower) || fLower.includes(cellLower)
        })) {
          cellSemantic = 'name'
        } else if (faceValueFields.some(f => {
          const fLower = f.toLowerCase().replace(/[\s_\-()]+/g, '')
          return cellLower.includes(fLower) || fLower.includes(cellLower)
        })) {
          cellSemantic = 'faceValue'
        } else if (rateFields.some(f => {
          const fLower = f.toLowerCase().replace(/[\s_\-()]+/g, '')
          return cellLower.includes(fLower) || fLower.includes(cellLower)
        })) {
          cellSemantic = 'rate'
        } else if (dateFields.some(f => {
          const fLower = f.toLowerCase().replace(/[\s_\-()]+/g, '')
          return cellLower.includes(fLower) || fLower.includes(cellLower)
        })) {
          cellSemantic = 'date'
        } else if (frequencyFields.some(f => {
          const fLower = f.toLowerCase().replace(/[\s_\-()]+/g, '')
          return cellLower.includes(fLower) || fLower.includes(cellLower)
        })) {
          cellSemantic = 'frequency'
        } else if (termFields.some(f => {
          const fLower = f.toLowerCase().replace(/[\s_\-()]+/g, '')
          return cellLower.includes(fLower) || fLower.includes(cellLower)
        })) {
          cellSemantic = 'term'
        } else if (currencyFields.some(f => {
          const fLower = f.toLowerCase().replace(/[\s_\-()]+/g, '')
          return cellLower.includes(fLower) || fLower.includes(cellLower)
        })) {
          cellSemantic = 'currency'
        } else if (statusFields.some(f => {
          const fLower = f.toLowerCase().replace(/[\s_\-()]+/g, '')
          return cellLower.includes(fLower) || fLower.includes(cellLower)
        })) {
          cellSemantic = 'status'
        } else if (priceFields.some(f => {
          const fLower = f.toLowerCase().replace(/[\s_\-()]+/g, '')
          return cellLower.includes(fLower) || fLower.includes(cellLower)
        })) {
          cellSemantic = 'price'
        } else if (interestFields.some(f => {
          const fLower = f.toLowerCase().replace(/[\s_\-()]+/g, '')
          return cellLower.includes(fLower) || fLower.includes(cellLower)
        })) {
          cellSemantic = 'interest'
        } else if (durationFields.some(f => {
          const fLower = f.toLowerCase().replace(/[\s_\-()]+/g, '')
          return cellLower.includes(fLower) || fLower.includes(cellLower)
        })) {
          cellSemantic = 'duration'
        } else if (returnFields.some(f => {
          const fLower = f.toLowerCase().replace(/[\s_\-()]+/g, '')
          return cellLower.includes(fLower) || fLower.includes(cellLower)
        })) {
          cellSemantic = 'return'
        }

        if (!cellSemantic) continue

        for (const missingField of missingFields) {
          if (found[missingField] !== undefined) continue
          if (!targetSemantics[missingField]) continue
          if (targetSemantics[missingField] !== cellSemantic) continue

          if (!isSemanticMatch(cell, missingField, cellSemantic)) continue

          let value = null
          for (let cc = c + 1; cc < Math.min(c + 7, row.length); cc++) {
            const next = row[cc]
            if (next !== null && next !== undefined && next !== '') {
              value = next
              break
            }
          }
          if (value === null && r + 1 < aoa.length) {
            const below = aoa[r + 1] ? aoa[r + 1][c] : ''
            if (below !== null && below !== undefined && below !== '') {
              value = below
            }
          }

          if (value !== null && isPlausibleValue(missingField, value)) {
            found[missingField] = value
            foundFields.add(missingField)
            console.log(`[secondary scan] recovered "${missingField}": "${value}" at row ${r}, col ${c}`)
          }
        }
      }
    }
  } catch (e) {
    console.error('scanSheetForMissingFields failed:', e)
  }

  console.log('Secondary scan found:', found)
  return found
}

const instrumentType = ref('')

const instrumentConfigs = ref({
  'money-market': {
    label: 'Money Market',
    description: 'Short-term debt instruments including treasury bills, commercial paper',
    defaultMaturity: '1Y',
    maturityOptions: [
      { value: '1M', label: '1 Month' },
      { value: '3M', label: '3 Months' },
      { value: '6M', label: '6 Months' },
      { value: '1Y', label: '1 Year' }
    ],
    rateLabel: 'Avg Interest Rate',
    primaryRateKey: 'avgRate',
    weightedRateKey: 'weightedAvgRate',
    fredDefault: '1Y',
    calculationFields: [
      { key: 'totalValue', label: 'Total Value (Maturity)' },
      { key: 'totalPrincipal', label: 'Total Principal' },
      { key: 'interestEarned', label: 'Interest Earned' },
      { key: 'totalInterest', label: 'Total Interest' },
      { key: 'interestRate', label: 'Interest Rate', suffix: '%' },
      { key: 'avgRate', label: 'Average Rate', suffix: '%' },
      { key: 'weightedAvgRate', label: 'Weighted Average Rate', suffix: '%' },
      { key: 'effectiveYield', label: 'Effective Yield', suffix: '%' },
      { key: 'effectiveAnnualRate', label: 'Effective Annual Rate', suffix: '%' },
      { key: 'bondEquivalentYield', label: 'Bond Equivalent Yield', suffix: '%' },
      { key: 'discountYield', label: 'Discount Yield', suffix: '%' },
      { key: 'avgDaysToMaturity', label: 'Average Days to Maturity', suffix: ' days' },
      { key: 'termDays', label: 'Term Days' },
      { key: 'daysToMaturity', label: 'Days to Maturity' },
      { key: 'maturityValue', label: 'Maturity Value' },
      { key: 'presentValue', label: 'Present Value' },
      { key: 'fairValue', label: 'Fair Value' },
      { key: 'yieldCurveRate', label: 'Benchmark Rate', suffix: '%' },
      { key: 'annualYield', label: 'Annual Yield', suffix: '%' }
    ],
    summaryMetrics: [
      { key: 'totalValue', label: 'Total Portfolio Value' },
      { key: 'instrumentCount', label: 'Number of Instruments' },
      { key: 'avgRate', label: 'Average Interest Rate', suffix: '%' },
      { key: 'weightedAvgRate', label: 'Weighted Average Rate', suffix: '%' }
    ]
  },
  'bonds': {
    label: 'Bonds',
    description: 'Fixed income securities including government and corporate bonds',
    defaultMaturity: '10Y',
    maturityOptions: [
      { value: '2Y', label: '2 Years' },
      { value: '5Y', label: '5 Years' },
      { value: '10Y', label: '10 Years' },
      { value: '30Y', label: '30 Years' }
    ],
    rateLabel: 'Avg Coupon Rate',
    primaryRateKey: 'avgCouponRate',
    weightedRateKey: 'weightedAvgCoupon',
    fredDefault: '10Y',
    calculationFields: [
      { key: 'totalValue', label: 'Total Market Value' },
      { key: 'totalFaceValue', label: 'Total Face Value' },
      { key: 'totalMarketValue', label: 'Total Market Value' },
      { key: 'currentPrice', label: 'Current Price' },
      { key: 'pricePer100', label: 'Price per 100' },
      { key: 'couponRate', label: 'Coupon Rate', suffix: '%' },
      { key: 'avgCouponRate', label: 'Average Coupon Rate', suffix: '%' },
      { key: 'weightedAvgCoupon', label: 'Weighted Average Coupon', suffix: '%' },
      { key: 'totalAnnualIncome', label: 'Total Annual Coupon Income' },
      { key: 'annualCoupon', label: 'Annual Coupon' },
      { key: 'couponPerPeriod', label: 'Coupon per Period' },
      { key: 'yieldToMaturity', label: 'Yield to Maturity', suffix: '%' },
      { key: 'avgYTM', label: 'Average YTM', suffix: '%' },
      { key: 'currentYield', label: 'Current Yield', suffix: '%' },
      { key: 'duration', label: 'Macaulay Duration (years)' },
      { key: 'modifiedDuration', label: 'Modified Duration (years)' },
      { key: 'accruedInterest', label: 'Accrued Interest' },
      { key: 'presentValue', label: 'Present Value' },
      { key: 'fairValue', label: 'Fair Value' },
      { key: 'yearsToMaturity', label: 'Years to Maturity' },
      { key: 'frequency', label: 'Coupon Frequency' },
      { key: 'daysAccrued', label: 'Days Accrued' },
      { key: 'yieldCurveRate', label: 'Benchmark Rate', suffix: '%' }
    ],
    summaryMetrics: [
      { key: 'totalValue', label: 'Total Portfolio Value' },
      { key: 'instrumentCount', label: 'Number of Instruments' },
      { key: 'avgCouponRate', label: 'Average Coupon Rate', suffix: '%' },
      { key: 'weightedAvgCoupon', label: 'Weighted Average Coupon', suffix: '%' },
      { key: 'avgYTM', label: 'Average YTM', suffix: '%' },
      { key: 'duration', label: 'Duration (years)' }
    ]
  },
  'tbills': {
    label: 'T-Bills',
    description: 'Treasury bills - short-term government securities',
    defaultMaturity: '13W',
    maturityOptions: [
      { value: '4W', label: '4 Weeks' },
      { value: '13W', label: '13 Weeks' },
      { value: '26W', label: '26 Weeks' },
      { value: '52W', label: '52 Weeks' }
    ],
    rateLabel: 'Avg Discount Rate',
    primaryRateKey: 'avgDiscountRate',
    weightedRateKey: 'weightedAvgDiscount',
    fredDefault: '13W',
    calculationFields: [
      { key: 'totalValue', label: 'Total Value (Face Value)' },
      { key: 'totalFaceValue', label: 'Total Face Value' },
      { key: 'totalPurchasePrice', label: 'Total Purchase Price' },
      { key: 'totalDiscount', label: 'Total Discount Amount' },
      { key: 'discountRate', label: 'Discount Rate', suffix: '%' },
      { key: 'avgDiscountRate', label: 'Average Discount Rate', suffix: '%' },
      { key: 'weightedAvgDiscount', label: 'Weighted Average Discount', suffix: '%' },
      { key: 'discountYield', label: 'Discount Yield', suffix: '%' },
      { key: 'moneyMarketYield', label: 'Money Market Yield', suffix: '%' },
      { key: 'bondEquivalentYield', label: 'Bond Equivalent Yield', suffix: '%' },
      { key: 'holdingPeriodYield', label: 'Holding Period Yield', suffix: '%' },
      { key: 'effectiveAnnualYield', label: 'Effective Annual Yield', suffix: '%' },
      { key: 'avgDaysToMaturity', label: 'Average Days to Maturity', suffix: ' days' },
      { key: 'termDays', label: 'Term Days' },
      { key: 'daysToMaturity', label: 'Days to Maturity' },
      { key: 'maturityValue', label: 'Maturity Value' },
      { key: 'presentValue', label: 'Present Value' },
      { key: 'fairValue', label: 'Fair Value' },
      { key: 'yieldCurveRate', label: 'Benchmark Rate', suffix: '%' },
      { key: 'avgInvestment', label: 'Average Investment' },
      { key: 'annualizedYield', label: 'Annualized Yield', suffix: '%' }
    ],
    summaryMetrics: [
      { key: 'totalValue', label: 'Total Portfolio Value' },
      { key: 'instrumentCount', label: 'Number of Instruments' },
      { key: 'avgDiscountRate', label: 'Average Discount Rate', suffix: '%' },
      { key: 'weightedAvgDiscount', label: 'Weighted Average Discount', suffix: '%' },
      { key: 'effectiveYield', label: 'Effective Yield', suffix: '%' }
    ]
  }
})

const config = computed(() => instrumentConfigs.value[instrumentType.value] || instrumentConfigs.value['money-market'])
const instrumentLabel = computed(() => config.value.label)
const instrumentDescription = computed(() => config.value.description)
const maturityOptions = computed(() => config.value.maturityOptions)
const rateLabel = computed(() => config.value.rateLabel)

const { requiredColumns, columnVariations, workflowSteps, loadConfig } = useInstrumentConfig(instrumentType.value)
const { fredFilters, loadFilterOptions, fetchBenchmark } = useFredMarket(() => config.value.defaultMaturity)
const worksheetWorkflow = useWorksheetWorkflow(instrumentType.value)

watch(() => route.params.type, (newType) => {
  const type = newType || route.path.split('/').pop() || ''
  if (type && instrumentType.value !== type) {
    instrumentType.value = type
    loadConfig(type).catch((e) => {
      console.error('Failed to load config:', e)
    })
    if (worksheetWorkflow.reset) worksheetWorkflow.reset()
  }
}, { immediate: true })

const activeSession = ref(null)
const valuationDate = ref(new Date().toISOString().split('T')[0])
const yieldCurveLoading = ref(false)
const yieldCurveError = ref('')
const yieldCurveChart = ref(null)
const chartInstanceRef = { current: null }
const yieldCurveData = ref([])
const chartSeriesLabel = ref('')
const chartImageData = ref('')

const worksheetStatuses = ref({})

const selectedMaturityOption = ref('')
const selectedCountryOption = ref('')
const selectedCurrencyOption = ref('')
const customCountryInput = ref('')
const customCurrencyInput = ref('')
const customMaturityInput = ref('')
const maturityMode = ref('maturity')
const yieldCurveStartDate = ref('')
const yieldCurveEndDate = ref('')

const uploadedFile = ref(null)
const uploadedFileId = ref(null)
const uploadedFilePath = ref(null)
const uploadedFileBase64 = ref(null)
const rawData = ref([])
const cleanedData = ref([])
const previewData = ref([])
const columnMapping = ref({})
const showMappingDialog = ref(false)
const showSavedMappingsDialog = ref(false)
const fileColumns = ref([])
const fixedValuesTracker = ref(new Map())
const calculations = ref({})
const allCalculations = ref({})
const selectedCalculations = ref({})
const cleaningStats = ref({ 
  totalRows: 0, 
  validRows: 0, 
  removedRows: 0, 
  fixedMissing: 0,
  removedEmptyRows: 0,
  removedSpecificColumnEmpty: 0,
  standardizedNumeric: 0,
  filledForward: 0,
  filledBackward: 0,
  removedDuplicates: 0,
  operationsPerformed: []
})
const fileLoading = ref(false)
const uploadError = ref('')
const uploadProgress = ref(0)

const showInstrumentExcelPopup = ref(false)
const showWorkflowPopup = ref(false)
const showDetectionSuccess = ref(false)
const showMultiTableDetectionSuccess = ref(false)
const customCurrency = ref('')
const excelPopupMode = ref('current')
const multiTableDetectionResults = ref([])
const selectedWorkflowInstrument = ref(null)
const selectedWorkflowIndex = ref(0)
const sortColumn = ref('')
const sortOrder = ref('asc')
const currentPage = ref(1)
const rowsPerPage = ref(10)
const mappingApplied = ref(false)
const cumulativeRecords = ref([])
const showCumulativeHistory = ref(false)
const originalRawData = ref([])
const originalFileColumns = ref([])
const originalFileBuffer = ref(null)
const sheetTotalRows = ref(0)
const sessionSavedAt = ref(null)
const showPreview = ref(false)
const worksheetSelected = ref(false)
const forceUpdate = ref(0)

const snackbar = ref({
  show: false,
  message: '',
  color: 'error',
  timeout: 4000
})

function showSnackbar(message, color = 'error', timeout = 4000) {
  snackbar.value = {
    show: true,
    message,
    color,
    timeout
  }
}

const savedTemplates = ref([])
const selectedTemplate = ref(null)
const newTemplateName = ref('')
const currentMappingTemplateId = ref(null)

const cleaningOptions = ref({
  removeDuplicates: true, fillMissingText: false, dropRowsWithMissing: false, trimWhitespace: true,
  convertToNumbers: true, removeOutliers: false, standardizeDates: false, removeSpecialChars: false,
  changeCase: false, caseType: 'none', fillWithCustom: false, customFillValue: '',
  removeColumnsAllMissing: false, capOutliers: false, removeRowsSpecificColumnEmpty: false,
  specificColumn: '', standardizeNumericRange: false, removeEmptyRows: false, fillForward: true, fillBackward: false
})

const dateFormatOptions = ref([
  { value: 'YYYY-MM-DD', label: 'YYYY-MM-DD' },
  { value: 'DD-MM-YYYY', label: 'DD-MM-YYYY' },
  { value: 'MM-DD-YYYY', label: 'MM-DD-YYYY' },
  { value: 'DD/MM/YYYY', label: 'DD/MM/YYYY' },
  { value: 'MM/DD/YYYY', label: 'MM/DD/YYYY' },
  { value: 'YYYY/MM/DD', label: 'YYYY/MM/DD' },
  { value: 'DD-MM-YY', label: 'DD-MM-YY' },
  { value: 'MM-DD-YY', label: 'MM-DD-YY' }
])
const selectedDateFormat = ref('YYYY-MM-DD')

const selectedInstrumentType = computed(() => instrumentLabel.value)
const instrumentSummary = ref({ columns: [], rows: [] })
const completedInstrumentSummary = ref({ columns: [], rows: [] })
const portfolioSummary = ref({ columns: [], rows: [] })
const completedPortfolioSummary = ref({ columns: [], rows: [] })
const fieldDetectionResults = ref({ detected_fields: {}, summary: {} })
const showFieldDetection = ref(false)
const activeSummaryTab = ref('current')
const selectedCalculationInstrument = ref(-1)
const currentlyViewingInstrument = ref(null)
const showAllCalculationsPopup = ref(false)
const sheetType = ref('multi')
const extractedValues = ref({})
const worksheetStatus = ref({})
const uploadHistory = ref([])
const currentWorkbookName = ref('')

const selectedInstruments = ref({ 'money-market': true, bonds: true, tbills: true })
const reportPreviewDialog = ref(false)
const reportPreviewHtml = ref('')

const showExcelDialog = ref(false)
const excelData = ref([])
const excelColumns = ref([])
const excelDialogTitle = ref('')
const showInstrumentResultsTable = ref(false)

const showWorkbookViewer = ref(false)
const workbookSheets = ref([])
const currentSheetName = ref('')
const selectedSectionId = ref('')
const singleInstrumentExtractedValues = ref({})
const isolatedTableData = ref(null)
const autoDetectedFields = ref({})
const autoDetectedFieldsWithMetadata = ref({})
const autoDetectedAdditionalFields = ref({})
const detectedCurrencies = ref([])
const detectedInstrumentType = ref('')
const selectedCurrency = ref('')
const isDetecting = ref(false)
const detectionStatus = ref('idle')
const isCalculating = ref(false)

const getDetectionButtonText = () => {
  switch (detectionStatus.value) {
    case 'idle': return 'Auto Detect'
    case 'scanning': return 'Scanning...'
    case 'analyzing': return 'Analysing worksheet...'
    case 'detecting': return 'Detecting fields...'
    case 'validating': return 'Validating results...'
    case 'complete': return 'Detection complete'
    default: return 'Auto Detect'
  }
}
const isUsingDetectedFields = ref(false)
const excludedDetectedFields = ref(new Set())
const newFieldName = ref('')
const newFieldValue = ref('')

const showModalViewer = ref(false)
const viewerFileData = ref(null)

const formulaDialog = ref(false)
const formulaText = ref('')
const formulaCalculationDetails = ref(null)
const showCalculationDetails = ref(false)
const showIndividualBreakdown = ref(false)
const formulas = ref({})
const manualInputs = ref({})

let saveTimeout = null
let lastInstrument = ''
let lastSessionId = ''
let lastSaveTime = 0
const SAVE_DEBOUNCE_MS = 2000

const selectedSummaryWorksheet = ref('')
const availableSummaryWorksheets = computed(() => [])

const mappingShownForSheet = ref({})

const currentSummaryRows = computed(() => {
  return instrumentSummary.value.rows
})

const activeValuationDate = computed(() => {
  const s = activeSession.value
  if (s) {
    if (s.valuationDate) return s.valuationDate
    if (s.valuation_date) return s.valuation_date
  }
  try {
    return (
      valuationDate.value ||
      sessionStorage.getItem('valuationDate') ||
      sessionStorage.getItem('valuation_date') ||
      localStorage.getItem('valuationDate') ||
      localStorage.getItem('valuation_date') ||
      null
    )
  } catch (e) { return null }
})

const descriptiveAnalytics = computed(() => {
  const rows = currentSummaryRows.value
  if (!rows.length) return {}

  if (allCalculations.value && (allCalculations.value.totalValue !== undefined || allCalculations.value.instrumentCount !== undefined)) {
    const stats = {}
    stats['Number of Records'] = allCalculations.value.instrumentCount || rows.length
    stats['Total Face Value'] = allCalculations.value.totalValue || 0
    stats['Weighted Average Yield'] = allCalculations.value.avgRate || allCalculations.value.weightedAvgRate || 0
    stats['Weighted Average Maturity'] = allCalculations.value.avgDaysToMaturity || 0
    stats['Average Rate'] = allCalculations.value.avgRate || 0

    for (const [k, v] of Object.entries(stats)) {
      if (typeof v === 'number') {
        const isTimeField = k.toLowerCase().includes('day') || k.toLowerCase().includes('maturity') || k.toLowerCase().includes('duration') || k.toLowerCase().includes('term') || k.toLowerCase().includes('month') || k.toLowerCase().includes('year') || k.toLowerCase().includes('week') || k.toLowerCase().includes('time')
        if (isTimeField) {
          stats[k] = Math.round(v).toLocaleString()
        } else {
          stats[k] = v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
        }
      }
    }
    return stats
  }

  console.warn('⚠️ No backend aggregate data available, using frontend fallback for descriptiveAnalytics')

  const getValue = (row) => parseFloat(row['Total Value'] ?? row['total_value'] ?? row['Calculated Value'] ?? row['calculated_value'] ?? row['Value'] ?? row['value'] ?? 0)
  const getYield = (row) => parseFloat(row['Yield'] ?? row['yield'] ?? row['Rate'] ?? row['rate'] ?? row['Interest Rate'] ?? row['interest_rate'] ?? row['Coupon Rate'] ?? row['coupon_rate'] ?? row['Discount Rate'] ?? row['discount_rate'] ?? 0)
  const getMaturity = (row) => parseFloat(row['Days to Maturity'] ?? row['days_to_maturity'] ?? row['Term'] ?? row['term'] ?? row['Maturity'] ?? row['maturity'] ?? 0)

  const values = rows.map(getValue).filter(v => !isNaN(v) && v > 0)
  const yields = rows.map(getYield).filter(v => !isNaN(v))
  const maturities = rows.map(getMaturity).filter(v => !isNaN(v) && v > 0)

  const stats = {}
  if (values.length) {
    const sum = values.reduce((a, b) => a + b, 0)
    const avgRate = yields.length ? yields.reduce((a,b) => a+b, 0) / yields.length : null
    stats['Number of Records'] = values.length
    stats['Total Face Value'] = sum
    if (yields.length && values.length) {
      const weightedYield = yields.reduce((a, b, i) => a + b * values[i], 0) / (values.reduce((a, b) => a + b, 1) || 1)
      stats['Weighted Average Yield'] = weightedYield
    }
    if (maturities.length && values.length) {
      const weightedMaturity = maturities.reduce((a, b, i) => a + b * values[i], 0) / (values.reduce((a, b) => a + b, 1) || 1)
      stats['Weighted Average Maturity'] = weightedMaturity
    }
    if (avgRate !== null) stats['Average Rate'] = avgRate
  }
  for (const [k, v] of Object.entries(stats)) {
    if (typeof v === 'number') {
      const isTimeField = k.toLowerCase().includes('day') || k.toLowerCase().includes('maturity') || k.toLowerCase().includes('duration') || k.toLowerCase().includes('term') || k.toLowerCase().includes('month') || k.toLowerCase().includes('year') || k.toLowerCase().includes('week') || k.toLowerCase().includes('time')
      if (isTimeField) {
        stats[k] = Math.round(v).toLocaleString()
      } else {
        stats[k] = v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
      }
    }
  }
  return stats
})

const dataQualitySummary = computed(() => {
  const rows = currentSummaryRows.value
  const totalCols = requiredColumns.value.length || 1
  const mappedCols = requiredColumns.value.filter(col => columnMapping.value[col] && columnMapping.value[col] !== '__na__').length
  const completeness = rows.length > 0 ? Math.min(100, Math.round((mappedCols / totalCols) * 100)) : 0

  return {
    rowsProcessed: cleaningStats.value.totalRows || rows.length || 0,
    columnsMapped: mappedCols,
    totalColumns: totalCols,
    completeness: completeness,
    duplicatesRemoved: cleaningStats.value.removedRows || 0,
    missingValuesFixed: cleaningStats.value.fixedMissing || 0,
    worksheetStatus: worksheetStatus.value[selectedSummaryWorksheet.value]?.processed ? 'Completed' : 'Pending'
  }
})

function loadSummaryForWorksheet() { forceUpdate.value++ }

const displayCountryOptions = [
  { value: 'USA', label: 'United States' },
  { value: 'GBR', label: 'United Kingdom' },
  { value: 'EUR', label: 'Eurozone' },
  { value: 'JPN', label: 'Japan' },
  { value: 'CAN', label: 'Canada' }
]
const displayCurrencyOptions = [
  { value: 'USD', label: 'USD' },
  { value: 'EUR', label: 'EUR' },
  { value: 'GBP', label: 'GBP' },
  { value: 'JPY', label: 'JPY' },
  { value: 'CAD', label: 'CAD' }
]

const activeTab = computed({
  get: () => route.query.tab || 'upload',
  set: (val) => router.push({ query: { ...route.query, tab: val } })
})

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
})

const currentStepIndex = computed(() => steps.value.findIndex(s => s.tab === activeTab.value))
const totalSteps = computed(() => steps.value.length)
const farthestAllowedIndex = computed(() => {
  for (let i = 0; i < steps.value.length; i++) {
    if (!isStepComplete(steps.value[i].tab)) return i
  }
  return steps.value.length - 1
})

const fileSize = computed(() => {
  if (!uploadedFile.value) return ''
  const bytes = uploadedFile.value.size
  if (bytes === 0) return ''
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(2) + ' MB'
})

const mappingContext = computed(() => ({
  mappingApplied: mappingApplied.value,
  columnMapping: columnMapping.value,
  rawData: rawData.value
}))

const hasRequiredColumn = (col) => isColumnMapped(col, mappingContext.value)
const missingColumns = computed(() => getMissingColumns(requiredColumns.value, mappingContext.value))
const hasData = computed(() => rawData.value.length > 0)
const hasCleanedData = computed(() => cleanedData.value.length > 0)

const uploadPreviewHeaders = computed(() => {
  if (Object.values(columnMapping.value).some(v => v)) {
    return requiredColumns.value
  }
  return originalFileColumns.value.length ? originalFileColumns.value : Object.keys(rawData.value[0] || {})
})

const cleanPreviewHeaders = computed(() => Object.keys((cleanedData.value[0]) || {}))

const portfolioAvgRate = computed(() => allCalculations.value.avgRate || 0)

const effectiveMaturity = computed(() => {
  if (selectedMaturityOption.value === '__custom__') return customMaturityInput.value || config.value.defaultMaturity
  return selectedMaturityOption.value
})
const effectiveCountry = computed(() => {
  if (selectedCountryOption.value === '__custom__') return customCountryInput.value || ''
  return selectedCountryOption.value || ''
})
const effectiveCurrency = computed(() => {
  if (selectedCurrencyOption.value === '__custom__') return customCurrencyInput.value || ''
  return selectedCurrencyOption.value || ''
})

const selectedMaturityOptionLabel = computed(() => {
  if (selectedMaturityOption.value === '__custom__') return customMaturityInput.value || 'Custom'
  const opt = maturityOptions.value.find(o => o.value === selectedMaturityOption.value)
  return opt ? opt.label : selectedMaturityOption.value
})

const benchmarkYield = computed(() => {
  if (!effectiveMaturity.value || !yieldCurveData.value.length) return null
  return getRateForMaturity(effectiveMaturity.value)
})

function getDisplayColumns() {
  const exclude = [
    '_raw', '_source', 'index', '__v',
    'instrument_name', 'instrument_type',
    'discount_yield', 'effective_yield', 'interest_earned',
    '_row_index', 'term_days', 'total_value',
    'total_interest', 'avg_rate', 'weighted_avg_rate',
    'avg_days_to_maturity', 'total_principal', 'annual_yield',
    'effective_annual_rate', 'instrument_count', 'fred_benchmark',
    'coupon_rate', 'coupon_payment', 'accrued_interest',
    'clean_price', 'dirty_price', 'yield_to_maturity',
    'discount_rate', 'investment_yield', 'maturity_value',
    'present_value', 'purchase_price', 'issue_price',
    'days_to_maturity', 'face_value', 'principal',
    'bond_equivalent_yield', 'currency',
    'Valuation Type', 'Workbook', 'Worksheet'
  ]

  let allColumns = [...(instrumentSummary.value.columns || [])]
  if (completedInstrumentSummary.value.columns) {
    allColumns = [...allColumns, ...completedInstrumentSummary.value.columns]
  }

  const cols = allColumns.filter(c => !exclude.includes(c))
  const seen = new Set()
  return cols.filter(c => {
    const base = c.replace(/_\d+$/, '').trim()
    const key = base.toLowerCase()
    if (seen.has(key)) return false
    seen.add(key)
    return true
  })
}

const instrumentSummaryColumnsForDisplay = computed(() => getDisplayColumns())

const currencyOptions = computed(() => [
  { title: '-- All Currencies --', value: '' },
  { title: 'USD', value: 'USD' },
  { title: 'EUR', value: 'EUR' },
  { title: 'ZWG', value: 'ZWG' },
  { title: '-- Custom (type below) --', value: 'custom' }
])

const instrumentSearchQuery = ref('')

const sortedInstrumentSummaryRows = computed(() => {
  let rows = []
  
  if (excelPopupMode.value === 'current') {
    rows = instrumentSummary.value.rows.map(row => ({
      ...row,
      'Valuation Type': 'Current'
    }))
  } else if (excelPopupMode.value === 'previous') {
    const allPrevious = completedInstrumentSummary.value.rows || []
    if (allPrevious.length > 0) {
      const lastSummary = allPrevious[allPrevious.length - 1]
      rows = [lastSummary].map(row => ({
        ...row,
        'Valuation Type': 'Previous'
      }))
    }
  } else if (excelPopupMode.value === 'all') {
    const currentRows = instrumentSummary.value.rows.map(row => ({
      ...row,
      'Valuation Type': 'Current'
    }))
    
    const previousRows = (completedInstrumentSummary.value.rows || []).map(row => ({
      ...row,
      'Valuation Type': 'Previous'
    }))
    
    rows = [...currentRows, ...previousRows]
  }
  
  if (instrumentSearchQuery.value) {
    const query = instrumentSearchQuery.value.toLowerCase()
    rows = rows.filter(row => {
      return Object.values(row).some(val => 
        String(val).toLowerCase().includes(query)
      )
    })
  }
  
  if (!sortColumn.value) return rows
  return [...rows].sort((a, b) => {
    let valA = a[sortColumn.value]
    let valB = b[sortColumn.value]
    if (typeof valA === 'number' && typeof valB === 'number') {
      return sortOrder.value === 'asc' ? valA - valB : valB - valA
    }
    valA = String(valA || '')
    valB = String(valB || '')
    return sortOrder.value === 'asc' ? valA.localeCompare(valB) : valB.localeCompare(valA)
  })
})

const paginatedInstrumentSummaryRows = computed(() => {
  const rows = sortedInstrumentSummaryRows.value
  const start = (currentPage.value - 1) * rowsPerPage.value
  const end = start + rowsPerPage.value
  return rows.slice(start, end)
})

const totalPages = computed(() => {
  return Math.ceil(sortedInstrumentSummaryRows.value.length / rowsPerPage.value)
})

const currentWorkbookPreviousSummaries = computed(() => {
  if (!currentWorkbookName.value || !completedInstrumentSummary.value.rows) return []
  return completedInstrumentSummary.value.rows.filter(
    row => row['Workbook'] === currentWorkbookName.value
  )
})

const calculationFields = computed(() => {
  const fields = config.value.calculationFields || []
  const allCalc = allCalculations.value || {}
  const selectedCalc = selectedCalculations.value || {}
  
  return fields.map(field => {
    let value = selectedCalc[field.key] !== undefined ? selectedCalc[field.key] :
                allCalc[field.key] !== undefined ? allCalc[field.key] :
                selectedCalc[toSnakeCase(field.key)] !== undefined ? selectedCalc[toSnakeCase(field.key)] :
                allCalc[toSnakeCase(field.key)] !== undefined ? allCalc[toSnakeCase(field.key)] : null
    
    if (value === null || value === undefined) {
      const agg = allCalc.agg || selectedCalc.agg || {}
      value = agg[field.key] !== undefined ? agg[field.key] :
              agg[toSnakeCase(field.key)] !== undefined ? agg[toSnakeCase(field.key)] : null
    }
    
    return {
      ...field,
      value
    }
  })
})

function toSnakeCase(str) {
  if (!str || typeof str !== 'string') return str
  try {
    return str.replace(/[A-Z]/g, letter => `_${letter.toLowerCase()}`)
  } catch (e) {
    return str
  }
}

function normalizeFieldName(fieldName) {
  if (!fieldName) return fieldName
  if (typeof fieldName !== 'string') return fieldName
  const fieldMap = {
    'CouponRate': 'coupon_rate',
    'CouponFrequency': 'coupon_frequency',
    'MaturityDate': 'maturity_date',
    'BondName': 'instrument_name',
    'settlement_date': 'issue_date',
    'next_coupon_date': 'next_coupon_date',
    'valuation_date': 'valuation_date',
    'present_value': 'present_value',
    'accrued_interest': 'accrued_interest',
    'carrying_value': 'carrying_value',
    'discount_rate': 'discount_rate',
    'price': 'price',
    'interest_rate': 'interest_rate',
    'yield_to_maturity': 'yield_to_maturity',
    'spread': 'spread',
    'principal': 'face_value',
    'fair_value': 'fair_value',
    'tenor': 'tenor',
    'country_risk_premium': 'country_risk_premium'
  }
  try {
    return fieldMap[fieldName] || toSnakeCase(fieldName)
  } catch (e) {
    return fieldName
  }
}

function formatCalcValue(key, value) {
  if (value === null || value === undefined) return '—'
  const field = config.value.calculationFields.find(f => f.key === key)
  if (!field) return value
  
  if (typeof value === 'number' && !isNaN(value)) {
    const isTimeField = key.toLowerCase().includes('day') || key.toLowerCase().includes('maturity') || key.toLowerCase().includes('duration') || key.toLowerCase().includes('term') || key.toLowerCase().includes('month') || key.toLowerCase().includes('year') || key.toLowerCase().includes('week') || key.toLowerCase().includes('time')
    if (isTimeField) {
      const rounded = Math.round(value)
      if (field.prefix) return field.prefix + rounded.toLocaleString()
      if (field.suffix) return rounded.toLocaleString() + field.suffix
      return rounded.toLocaleString()
    }
    const rounded = Math.round(value * 100) / 100
    if (field.prefix) return field.prefix + rounded.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
    if (field.suffix) return rounded.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + field.suffix
    return rounded.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  }
  
  if (field.prefix) return field.prefix + value
  if (field.suffix) return value + field.suffix
  return value
}

function isStepComplete(tab) {
  return isStepPersistedCompleted(activeSession.value?.id, tab)
}

function switchTab(tab) {
  const idx = steps.value.findIndex(s => s.tab === tab)
  if (idx > farthestAllowedIndex.value) {
    return
  }
  saveSessionData()
  activeTab.value = tab
  forceUpdate.value++
  nextTick(() => {
    const container = document.querySelector('.tab-content-wrapper')
    if (container) container.scrollTop = 0
  })
}

function goToDashboard() { saveSessionData(); router.push('/dashboard') }
function goToCalculations() { activeTab.value = 'calculations'; forceUpdate.value++ }
function goToPortfolioSummary() { 
  saveSessionData(); 
  const sessionId = activeSession.value?.id || sessionManager.getActiveSessionId() || localStorage.getItem('dura_active_session_id')
  console.log('goToPortfolioSummary - sessionId:', sessionId)
  if (sessionId) {
    sessionManager.setActiveSession({ id: sessionId })
    localStorage.setItem('dura_active_session_id', sessionId)
    router.push({ path: '/summary', query: { session: sessionId } })
  } else {
    console.error('No session ID available for navigation')
    router.push('/summary')
  }
}

async function goToReportTab() {
  saveSessionData()
  activeTab.value = 'reports'
  const sid = activeSession.value?.id || sessionManager.getActiveSessionId()
  if (sid) {
    await markStepCompleted(String(sid), 'summary')
    await markStepCompleted(String(sid), 'visualizations')
    await markStepCompleted(String(sid), 'calculations')
    await markStepCompleted(String(sid), 'cleaning')
    await markStepCompleted(String(sid), 'upload')
  }
  forceUpdate.value++
}

function parseMaturityToYears(mat) {
  const num = parseFloat(mat)
  if (mat.endsWith('M')) return num / 12
  if (mat.endsWith('W')) return num / 52
  if (mat.endsWith('Y')) return num
  return num
}

function getRateForMaturity(mat) {
  if (!mat || !yieldCurveData.value.length) return null
  const targetYears = parseMaturityToYears(mat)
  let closest = null
  let minDiff = Infinity
  for (const point of yieldCurveData.value) {
    const diff = Math.abs(point.maturity - targetYears)
    if (diff < minDiff) {
      minDiff = diff
      closest = point
    }
  }
  if (closest && minDiff < 0.5) return closest.rate
  return null
}

function getCountryLabel(code) {
  const allCountries = [
    ...displayCountryOptions,
    { value: 'ZAF', label: 'South Africa' },
    { value: 'AUS', label: 'Australia' },
    { value: 'CHE', label: 'Switzerland' },
    { value: 'NZL', label: 'New Zealand' },
    { value: 'NOR', label: 'Norway' },
    { value: 'SWE', label: 'Sweden' },
    { value: 'DNK', label: 'Denmark' },
    { value: 'BRA', label: 'Brazil' },
    { value: 'MEX', label: 'Mexico' },
    { value: 'IND', label: 'India' },
    { value: 'CHN', label: 'China' },
    { value: 'KOR', label: 'South Korea' },
    { value: 'SGP', label: 'Singapore' },
    { value: 'HKG', label: 'Hong Kong' },
    { value: 'RUS', label: 'Russia' },
    { value: 'TUR', label: 'Turkey' },
    { value: 'SAU', label: 'Saudi Arabia' },
    { value: 'ARE', label: 'UAE' },
    { value: 'ISR', label: 'Israel' }
  ]
  const found = allCountries.find(c => c.value === code)
  return found ? found.label : code
}

function getCurrencyLabel(code) {
  const allCurrencies = [
    ...displayCurrencyOptions,
    { value: 'AUD', label: 'AUD' },
    { value: 'CHF', label: 'CHF' },
    { value: 'NZD', label: 'NZD' },
    { value: 'NOK', label: 'NOK' },
    { value: 'SEK', label: 'SEK' },
    { value: 'DKK', label: 'DKK' },
    { value: 'ZAR', label: 'ZAR' },
    { value: 'BRL', label: 'BRL' },
    { value: 'MXN', label: 'MXN' },
    { value: 'INR', label: 'INR' },
    { value: 'CNY', label: 'CNY' },
    { value: 'KRW', label: 'KRW' },
    { value: 'SGD', label: 'SGD' },
    { value: 'HKD', label: 'HKD' },
    { value: 'RUB', label: 'RUB' },
    { value: 'TRY', label: 'TRY' },
    { value: 'SAR', label: 'SAR' },
    { value: 'AED', label: 'AED' },
    { value: 'ILS', label: 'ILS' }
  ]
  const found = allCurrencies.find(c => c.value === code)
  return found ? found.label : code
}

function formatNumber(num, isTimeField = false) {
  if (num === undefined || num === null || num === '') return '—'
  if (isTimeField) {
    const rounded = Math.round(num)
    return rounded.toLocaleString()
  }
  const rounded = Math.round(num * 100) / 100
  return rounded.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function formatTimeValue(num) {
  if (num === undefined || num === null || num === '') return '—'
  const rounded = Math.round(num)
  return rounded.toLocaleString()
}

function computeAnalytics(rows) {
  if (!rows || !rows.length) return {}
  const getValue = (row) => parseFloat(row['Total Value'] ?? row['total_value'] ?? row['Calculated Value'] ?? row['calculated_value'] ?? row['Value'] ?? row['value'] ?? 0)
  const getYield = (row) => parseFloat(row['Yield'] ?? row['yield'] ?? row['Rate'] ?? row['rate'] ?? row['Interest Rate'] ?? row['interest_rate'] ?? row['Coupon Rate'] ?? row['coupon_rate'] ?? row['Discount Rate'] ?? row['discount_rate'] ?? 0)
  const getMaturity = (row) => parseFloat(row['Days to Maturity'] ?? row['days_to_maturity'] ?? row['Term'] ?? row['term'] ?? row['Maturity'] ?? row['maturity'] ?? 0)
  const values = rows.map(getValue).filter(v => !isNaN(v) && v > 0)
  const yields = rows.map(getYield).filter(v => !isNaN(v))
  const maturities = rows.map(getMaturity).filter(v => !isNaN(v) && v > 0)

  const stats = {}
  if (values.length) {
    const sum = values.reduce((a, b) => a + b, 0)
    const avgRate = yields.length ? yields.reduce((a,b) => a+b, 0) / yields.length : null
    stats['Number of Records'] = values.length
    stats['Total Face Value'] = sum
    if (yields.length && values.length) {
      const weightedYield = yields.reduce((a, b, i) => a + b * values[i], 0) / (values.reduce((a, b) => a + b, 1) || 1)
      stats['Weighted Average Yield'] = weightedYield
    }
    if (maturities.length && values.length) {
      const weightedMaturity = maturities.reduce((a, b, i) => a + b * values[i], 0) / (values.reduce((a, b) => a + b, 1) || 1)
      stats['Weighted Average Maturity'] = weightedMaturity
    }
    if (avgRate !== null) stats['Average Rate'] = avgRate
  }
  return stats
}

function computeAggregate(rows) {
  const agg = {
    totalValue: 0,
    instrumentCount: 0,
    avgRate: 0,
    weightedAvgRate: 0,
    totalInterest: null,
    interestEarned: null,
    annualYield: null,
    effectiveAnnualRate: null,
    avgDaysToMaturity: null,
    totalPrincipal: 0,
    avgCouponRate: 0,
    weightedAvgCoupon: 0,
    totalAnnualIncome: null,
    avgYTM: null,
    duration: null,
    avgDiscountRate: 0,
    weightedAvgDiscount: 0,
    totalDiscount: null,
    effectiveYield: null,
    bondEquivalentYield: null,
    totalPurchasePrice: null,
    avgInvestment: null,
    holdingPeriodYield: null,
    annualizedYield: null,
    pricePer100: null
  }

  if (!rows || !rows.length) return agg

  const getNumber = (row, ...keys) => {
    for (const key of keys) {
      const val = row[key]
      if (val !== undefined && val !== null && val !== '') {
        const num = parseFloat(val)
        if (!isNaN(num)) return num
      }
    }
    return 0
  }

  let total = 0, count = 0, rateSum = 0, weightedSum = 0

  rows.forEach(row => {
    const value = getNumber(row, 'Total Value', 'total_value', 'Calculated Value', 'calculated_value', 'Value', 'value')
    const rate = getNumber(row, 'Avg Rate', 'avg_rate', 'Rate', 'rate', 'Interest Rate', 'interest_rate', 'Coupon Rate', 'coupon_rate', 'Discount Rate', 'discount_rate', 'Yield', 'yield')
    total += value
    count++
    rateSum += rate
    weightedSum += value * rate
  })

  const avgRate = count > 0 ? rateSum / count : 0
  const weightedAvg = total > 0 ? weightedSum / total : 0

  const daysValues = rows.map(r => parseFloat(r['Days to Maturity'] || r['days_to_maturity'] || r['Term'] || r['term'] || r['Avg Days to Maturity'] || r['avg_days_to_maturity'] || NaN)).filter(v => !isNaN(v) && v > 0)
  const avgDays = daysValues.length ? daysValues.reduce((a, b) => a + b, 0) / daysValues.length : null

  agg.totalValue = total
  agg.instrumentCount = count
  agg.avgRate = avgRate
  agg.weightedAvgRate = weightedAvg
  agg.totalInterest = null
  agg.interestEarned = null
  agg.annualYield = avgRate || null
  agg.effectiveAnnualRate = null
  agg.avgDaysToMaturity = avgDays
  agg.totalPrincipal = total

  const couponSum = rows.reduce((sum, row) => sum + getNumber(row, 'Avg Coupon Rate', 'avg_coupon_rate', 'Coupon Rate', 'coupon_rate'), 0)
  agg.avgCouponRate = count > 0 ? couponSum / count : 0
  agg.weightedAvgCoupon = weightedAvg
  agg.totalAnnualIncome = null
  agg.avgYTM = avgRate || null
  agg.duration = null

  const discountSum = rows.reduce((sum, row) => sum + getNumber(row, 'Avg Discount Rate', 'avg_discount_rate', 'Discount Rate', 'discount_rate'), 0)
  agg.avgDiscountRate = count > 0 ? discountSum / count : 0
  agg.weightedAvgDiscount = weightedAvg
  agg.totalDiscount = null
  agg.effectiveYield = null
  agg.bondEquivalentYield = null
  agg.totalPurchasePrice = null
  agg.avgInvestment = count > 0 ? total / count : null
  agg.holdingPeriodYield = null
  agg.annualizedYield = null
  agg.pricePer100 = null

  return agg
}

function runInstrumentCalculations(row, instrumentType) {
  const results = {}
  const getNumber = (val) => { const num = parseFloat(val); return isNaN(num) ? 0 : num }

  const nameCol = columnMapping.value['Instrument Name'] || 'Instrument'
  const instrumentName = row[nameCol] || row['Instrument'] || row['Name'] || 'Instrument'

  const amount = getNumber(row['Amount'] || row['FaceValue'] || row['Principal'] || row['Value'] || 0)
  const rate = getNumber(row['Rate'] || row['InterestRate'] || row['CouponRate'] || row['DiscountRate'] || row['Yield'] || 0)
  const days = getNumber(row['DaysToMaturity'] || row['Term'] || row['Maturity'] || null)

  if (instrumentType === 'money-market') {
    const interest = amount * (rate / 100) * (days / 360)
    results['Instrument Name'] = instrumentName
    results['Total Value'] = amount
    results['total_value'] = amount
    results['Instrument Count'] = 1
    results['instrument_count'] = 1
    results['Avg Rate'] = rate
    results['avg_rate'] = rate
    results['Weighted Avg Rate'] = rate
    results['weighted_avg_rate'] = rate
    results['Total Interest'] = interest
    results['total_interest'] = interest
    results['Interest Earned'] = interest
    results['interest_earned'] = interest
    results['Annual Yield'] = rate
    results['annual_yield'] = rate
    results['Effective Annual Rate'] = rate
    results['effective_annual_rate'] = rate
    results['Avg Days to Maturity'] = days
    results['avg_days_to_maturity'] = days
    results['Total Principal'] = amount
    results['total_principal'] = amount
  } else if (instrumentType === 'bonds') {
    const coupon = amount * (rate / 100)
    results['Instrument Name'] = instrumentName
    results['Total Value'] = amount
    results['total_value'] = amount
    results['Instrument Count'] = 1
    results['instrument_count'] = 1
    results['Avg Coupon Rate'] = rate
    results['avg_coupon_rate'] = rate
    results['Weighted Avg Coupon'] = rate
    results['weighted_avg_coupon'] = rate
    results['Total Annual Income'] = coupon
    results['total_annual_income'] = coupon
    results['Avg YTM'] = rate
    results['avg_ytm'] = rate
  } else {
    const discount = amount * (rate / 100) * (days / 360)
    const price = amount - discount
    results['Instrument Name'] = instrumentName
    results['Total Value'] = amount
    results['total_value'] = amount
    results['Instrument Count'] = 1
    results['instrument_count'] = 1
    results['Avg Discount Rate'] = rate
    results['avg_discount_rate'] = rate
    results['Weighted Avg Discount'] = rate
    results['weighted_avg_discount'] = rate
    results['Total Discount'] = discount
    results['total_discount'] = discount
    results['Effective Yield'] = rate
    results['effective_yield'] = rate
    results['Bond Equivalent Yield'] = rate
    results['bond_equivalent_yield'] = rate
    results['Price per 100'] = 100 * (1 - (rate / 100) * (days / 360))
    results['price_per_100'] = results['Price per 100']
    results['Total Purchase Price'] = price
    results['total_purchase_price'] = price
    results['Avg Investment'] = price
    results['avg_investment'] = price
    results['Holding Period Yield'] = rate
    results['holding_period_yield'] = rate
    results['Annualized Yield'] = rate
    results['annualized_yield'] = rate
    results['Avg Days to Maturity'] = days
    results['avg_days_to_maturity'] = days
  }
  return results
}

function processInstrumentData(sheetName, data, instrumentType) {
  if (!data || !data.length) return

  const rows = data.map((row, index) => {
    const nameCol = columnMapping.value['Instrument Name'] || 'Instrument'
    const instrumentName = row[nameCol] || row['Instrument'] || row['Name'] || `Instrument ${index + 1}`
    const enrichedRow = { ...row, 'Instrument Name': instrumentName }
    const result = runInstrumentCalculations(enrichedRow, instrumentType)
    return {
      'Instrument Name': instrumentName,
      'Instrument Type': instrumentType,
      ...result,
      'Worksheet': sheetName
    }
  })

  const existingRows = instrumentSummary.value.rows || []
  const mergedRows = [...existingRows]
  rows.forEach(newRow => {
    const id = newRow['Instrument Name'] + '_' + (newRow['Worksheet'] || '')
    const exists = mergedRows.some(r => (r['Instrument Name'] || '') + '_' + (r['Worksheet'] || '') === id)
    if (!exists) mergedRows.push(newRow)
  })

  const allCols = new Set()
  mergedRows.forEach(r => Object.keys(r).forEach(k => allCols.add(k)))
  instrumentSummary.value = { columns: Array.from(allCols), rows: mergedRows }

  console.warn('processInstrumentData uses deprecated frontend calculations. Use backend calculateMetrics instead.')

  const agg = computeAggregate(mergedRows)
  const uniqueNames = new Set(mergedRows.map(r => r['Instrument Name']))
  agg.instrumentCount = uniqueNames.size

  allCalculations.value = agg
  selectedCalculations.value = agg
  calculations.value = agg

  saveSessionData()
  return { success: true, rows, aggregate: agg }
}

const fileInput = ref(null)

function loadUploadHistory() {
  const key = `${instrumentType.value}_upload_history`
  const saved = localStorage.getItem(key)
  uploadHistory.value = saved ? JSON.parse(saved) : []
}

function saveUploadHistory() {
  const key = `${instrumentType.value}_upload_history`
  localStorage.setItem(key, JSON.stringify(uploadHistory.value))
}

function addToHistory(filename, data, fileData = null) {
  const existing = uploadHistory.value.find(h => h.name === filename && (Date.now() - h.date) < 5000)
  if (existing) return
  uploadHistory.value.unshift({
    name: filename,
    date: Date.now(),
    data: JSON.stringify(data),
    fileData: fileData
  })
  if (uploadHistory.value.length > 5) uploadHistory.value.pop()
  saveUploadHistory()
}

async function loadHistoryFile(item) {
  if (!item.fileData) {
    alert('This file cannot be loaded because the file data is missing. Please upload the file again.')
    return
  }
  
  if (confirm(`Load ${item.name}? Current unsaved data will be lost.`)) {
    const base64String = item.fileData.split(',')[1]
    const binaryString = atob(base64String)
    const bytes = new Uint8Array(binaryString.length)
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i)
    }
    const arrayBuffer = bytes.buffer

    originalFileBuffer.value = arrayBuffer
    uploadedFile.value = { name: item.name, size: arrayBuffer.byteLength }

    try {
      const result = await worksheetWorkflow.handleFileUpload(new File([arrayBuffer], item.name))
      if (result.success) {
        workbookSheets.value = worksheetWorkflow.workbookSheets.value
        worksheetStatus.value = worksheetWorkflow.worksheetStatus.value
        originalFileBuffer.value = worksheetWorkflow.originalFileBuffer.value
        showSnackbar(`Loaded ${item.name} from history`, 'success')
        
        clearActiveCache(true)
        
        showWorkbookViewer.value = true
        activeTab.value = 'upload'
        forceUpdate.value++
      } else {
        console.error('Workbook parse failed:', result.error)
        showSnackbar('Failed to parse workbook', 'error')
      }
    } catch (err) {
      console.error('Failed to parse workbook from history:', err)
      showSnackbar('Failed to load file', 'error')
    }

    saveSessionData()
  }
}

function deleteHistoryItem(idx) {
  uploadHistory.value.splice(idx, 1)
  saveUploadHistory()
}

function handleFileUpload(e) {
  const file = e.target.files[0]
  if (file) {
    console.log('File details:', {
      name: file.name,
      size: file.size,
      type: file.type,
      lastModified: file.lastModified
    })
    const fileCopy = new File([file], file.name, { type: file.type })
    uploadedFile.value = fileCopy
    worksheetStatuses.value = {}
    readFileData(fileCopy)
  } else {
    console.warn('No file selected')
  }
}

function handleDrop(e) {
  e.preventDefault()
  const file = e.dataTransfer.files[0]
  if (file) {
    const fileCopy = new File([file], file.name, { type: file.type })
    uploadedFile.value = fileCopy
    worksheetStatuses.value = {}
    readFileData(fileCopy)
  }
}

async function readFileData(file) {
  fileLoading.value = true
  uploadError.value = ''

  try {
    const base64Promise = new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = (e) => {
        uploadedFileBase64.value = e.target.result
        resolve(e.target.result)
      }
      reader.onerror = reject
      reader.readAsDataURL(file)
    })
    await base64Promise

    const result = await worksheetWorkflow.handleFileUpload(file)

    if (result.success) {
      workbookSheets.value = worksheetWorkflow.workbookSheets.value
      worksheetStatus.value = worksheetWorkflow.worksheetStatus.value
      originalFileBuffer.value = worksheetWorkflow.originalFileBuffer.value
      worksheetStatuses.value = {}
      
      clearActiveCache(false)
      
      worksheetSelected.value = false
      currentSheetName.value = ''
      showPreview.value = false
      sheetType.value = 'multi'

      addToHistory(file.name, result.sheets[0]?.data || [], uploadedFileBase64.value)
      debouncedSave()
      forceUpdate.value++
    } else {
      throw new Error(result.error || 'Failed to upload workbook')
    }
  } catch (err) {
    console.error('Upload error:', err)
    console.error('Error stack:', err.stack)
    uploadError.value = err.message
    showSnackbar(`Failed to parse file: ${err.message}`, 'error')
    rawData.value = []
  } finally {
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
  cleanedData.value = []
  previewData.value = []
  calculations.value = {}
  allCalculations.value = {}
  selectedCalculations.value = {}
  fixedValuesTracker.value.clear()
  mappingApplied.value = false
  columnMapping.value = {}
  fileColumns.value = []
  showPreview.value = false
  worksheetSelected.value = false
  uploadError.value = ''
  sheetTotalRows.value = 0
  worksheetWorkflow.reset()
  debouncedSave()
  forceUpdate.value++
  if (fileInput.value) fileInput.value.value = ''
}

function handleWorksheetSelect(sheetName) {
  console.log(`🔄 handleWorksheetSelect: Selecting worksheet "${sheetName}"`)
  
  const result = worksheetWorkflow.selectWorksheet(sheetName)
  if (result.success) {
    currentSheetName.value = sheetName
    worksheetSelected.value = true
    
    clearActiveCache(true)
    
    const sheet = workbookSheets.value.find(s => s.name === sheetName)
    if (sheet) {
      const previewResult = worksheetWorkflow.parseSheetPreview(sheetName, 100)
      if (previewResult) {
        rawData.value = previewResult.jsonData || []
        originalRawData.value = JSON.parse(JSON.stringify(previewResult.jsonData || []))
        fileColumns.value = previewResult.headers || []
        originalFileColumns.value = [...fileColumns.value]
        sheetTotalRows.value = previewResult.totalRows || 0
      }
      sheetType.value = 'multi'
      
      if (rawData.value.length > 0) {
        const detection = detectSheetType(rawData.value, instrumentType.value)
        sheetType.value = detection.type
        if (detection.type === 'multi') {
          columnMapping.value = autoMatchColumns(fileColumns.value, requiredColumns.value, columnVariations.value)
          showMappingDialog.value = true
        } else {
          columnMapping.value = {}
          mappingApplied.value = true
        }
      }
      
      showPreview.value = true
      activeTab.value = 'upload'
      forceUpdate.value++
    }
  }
}

function clearActiveCache(preservePreviousValuations = true) {
  console.log('🔄 Clearing active cache for worksheet/section change, preservePreviousValuations:', preservePreviousValuations)
  
  if (preservePreviousValuations) {
    if (instrumentSummary.value.rows.length > 0) {
      completedInstrumentSummary.value = JSON.parse(JSON.stringify(instrumentSummary.value))
      console.log('💾 Saved current instrument summary as completed (previous valuations)')
    }
    if (portfolioSummary.value.rows.length > 0) {
      completedPortfolioSummary.value = JSON.parse(JSON.stringify(portfolioSummary.value))
      console.log('💾 Saved current portfolio summary as completed (previous valuations)')
    }
  }
  
  if (!isUsingDetectedFields.value) {
    cleanedData.value = []
    calculations.value = {}
    allCalculations.value = {}
    selectedCalculations.value = {}
    columnMapping.value = {}
    autoDetectedFields.value = {}
    autoDetectedFieldsWithMetadata.value = {}
    autoDetectedAdditionalFields.value = {}
    extractedValues.value = {}
    rawData.value = []
    originalRawData.value = []
  } else {
    calculations.value = {}
    allCalculations.value = {}
    selectedCalculations.value = {}
    columnMapping.value = {}
  }
  
  instrumentSummary.value = { columns: [], rows: [] }
  portfolioSummary.value = { columns: [], rows: [] }
  
  if (!preservePreviousValuations) {
    completedInstrumentSummary.value = { columns: [], rows: [] }
    completedPortfolioSummary.value = { columns: [], rows: [] }
  }
  
  fieldDetectionResults.value = { detected_fields: {}, summary: {} }
  showMultiTableDetectionSuccess.value = false
  multiTableDetectionResults.value = []
  
  rawData.value = []
  originalRawData.value = []
  previewData.value = []
  fileColumns.value = []
  originalFileColumns.value = []
  extractedValues.value = {}
  singleInstrumentExtractedValues.value = {}
  isolatedTableData.value = null
  
  mappingApplied.value = false
  showMappingDialog.value = false
  fixedValuesTracker.value.clear()
  
  cleaningStats.value = {
    totalRows: 0,
    cleanedRows: 0,
    modifiedRows: 0,
    duplicateRows: 0,
    missingValueRows: 0
  }
  
  formulas.value = {}
  manualInputs.value = {}
  
  console.log('✅ Active cache cleared - workbook data preserved for viewer')
}

function handleSheetSelectedFromViewer(sheetName) {
  console.log(`🔄 handleSheetSelectedFromViewer: Switching to worksheet "${sheetName}"`)
  console.log('🔄 Current activeTab:', activeTab.value)
  console.log('🔄 isUsingDetectedFields:', isUsingDetectedFields.value)
  currentSheetName.value = sheetName
}

function handleSingleInstrumentExtracted({ sheetName, extractedValues }) {
  currentSheetName.value = sheetName
  singleInstrumentExtractedValues.value = extractedValues
}

function handleTableIsolated({ sheetName, tableName, data, headers, tableRange }) {
  console.log(`🔄 handleTableIsolated: Switching to section "${tableName}" in worksheet "${sheetName}"`)
  
  currentSheetName.value = sheetName
  
  clearActiveCache(true)
  
  isolatedTableData.value = {
    sheetName,
    tableName,
    data,
    headers,
    tableRange
  }
  
  showWorkbookViewer.value = false
  rawData.value = data
  originalRawData.value = JSON.parse(JSON.stringify(data))
  fileColumns.value = headers
  originalFileColumns.value = [...headers]
  currentMappingTemplateId.value = null
  showMappingDialog.value = true
  mappingApplied.value = false
  columnMapping.value = autoMatchColumns(headers, requiredColumns.value, columnVariations.value)
  applyCurrentMapping()
  worksheetSelected.value = true
  showPreview.value = true
}

async function handleAutoDetectSheet(sheetName) {
  if (!originalFileBuffer.value) {
    alert('File buffer not available')
    return
  }
  currentSheetName.value = sheetName
  await autoDetectSingleInstrument()
}

async function handleWorkOnSheet(sheetName) {
  fileLoading.value = true
  uploadError.value = ''
  
  console.log(`🔄 handleWorkOnSheet: Switching to worksheet "${sheetName}"`)
  
  clearActiveCache(true)

  try {
    const result = await worksheetWorkflow.processWorksheet(
      sheetName,
      requiredColumns.value,
      columnVariations.value
    )

    if (result.success) {
      const sheetData = result.data || []
      rawData.value = sheetData
      sheetType.value = result.type || 'multi'
      extractedValues.value = result.extractedValues || {}

      if (sheetData.length > 0) {
        const headers = Object.keys(sheetData[0])
        originalRawData.value = JSON.parse(JSON.stringify(sheetData))
        fileColumns.value = headers
        originalFileColumns.value = [...headers]
      } else {
        const sheet = workbookSheets.value.find(s => s.name === sheetName)
        if (sheet && sheet.headers && sheet.headers.length) {
          fileColumns.value = sheet.headers
          originalFileColumns.value = [...sheet.headers]
        }
        originalRawData.value = []
      }

      worksheetStatus.value[sheetName] = {
        ...worksheetStatus.value[sheetName],
        processed: true,
        sheetType: result.type
      }

      worksheetSelected.value = true

      if (result.type === 'multi') {
        currentMappingTemplateId.value = null
        const headers = Object.keys(sheetData[0] || {})
        if (headers.length) {
          columnMapping.value = autoMatchColumns(headers, requiredColumns.value, columnVariations.value)
        }
        applyCurrentMapping()
        if (!mappingShownForSheet.value[sheetName]) {
          mappingShownForSheet.value[sheetName] = true
          showMappingDialog.value = true
        }
        showPreview.value = true
      } else {
        columnMapping.value = {}
        mappingApplied.value = true
        showMappingDialog.value = false
        const fieldMappings = getRequiredFieldMappings(instrumentType.value)
        extractedValues.value = extractSingleInstrumentValues(rawData.value, fieldMappings) || {}
        const tabularData = convertExtractedToTabular(extractedValues.value)
        rawData.value = tabularData
        originalRawData.value = JSON.parse(JSON.stringify(tabularData))
        fileColumns.value = Object.keys(tabularData[0] || {})
        originalFileColumns.value = [...fileColumns.value]
        showPreview.value = true
      }

      debouncedSave()
      forceUpdate.value++
    } else {
      uploadError.value = result.error || 'Failed to process worksheet'
    }
  } catch (err) {
    console.error('Worksheet processing error:', err)
    uploadError.value = err.message
  } finally {
    fileLoading.value = false
  }
}

function handleViewResults(sheetName) {
  const status = worksheetStatus.value[sheetName]
  if (status?.processed) {
    activeTab.value = 'calculations'
  }
}

function applyCurrentMapping() {
  if (!originalRawData.value.length) {
    console.warn('applyCurrentMapping: originalRawData is empty')
    return
  }
  if (sheetType.value === 'single') {
    rawData.value = originalRawData.value
    mappingApplied.value = true
    return
  }

  const required = requiredColumns.value || []
  const hasAnyMapping = required.some(
    col => columnMapping.value[col] && columnMapping.value[col] !== '__na__'
  )

  if (!hasAnyMapping) {
    rawData.value = originalRawData.value
    mappingApplied.value = false
    showPreview.value = true
    return
  }

  const transformed = originalRawData.value.map(row => {
    const out = {}
    for (const reqCol of required) {
      const srcCol = columnMapping.value[reqCol]
      out[reqCol] = (srcCol && srcCol !== '__na__' && row[srcCol] !== undefined)
        ? row[srcCol]
        : ''
    }
    return out
  })

  rawData.value = transformed
  mappingApplied.value = true
  showPreview.value = true
}

function updateColumnMapping(newMapping) {
  columnMapping.value = { ...newMapping }
  applyCurrentMapping()
  debouncedSave()
}

async function saveFinalMapping() {
  if (currentMappingTemplateId.value) {
    try {
      console.log('Updating existing template from preview:', currentMappingTemplateId.value)
      const result = await mappingTemplateManager.updateTemplate(currentMappingTemplateId.value, {
        columnMapping: columnMapping.value,
        fileColumns: fileColumns.value
      })
      console.log('Update result:', result)
      if (result) {
        await loadSavedTemplates()
        showSnackbar('Mapping saved successfully', 'success')
      } else {
        showSnackbar('Failed to update mapping: No response from server', 'error')
      }
    } catch (e) {
      console.error('Error updating template:', e)
      showSnackbar('Failed to update mapping: ' + (e.message || e), 'error')
    }
  } else {
    const templateName = `${instrumentType.value} - ${uploadedFile.value?.name || 'Custom'} - ${new Date().toLocaleDateString()}`
    try {
      console.log('Creating new template from preview:', templateName)
      const result = await mappingTemplateManager.saveTemplate(
        templateName,
        instrumentType.value,
        columnMapping.value,
        requiredColumns.value,
        fileColumns.value
      )
      if (result) {
        currentMappingTemplateId.value = result.id
        await loadSavedTemplates()
        showSnackbar('Mapping saved successfully', 'success')
      } else {
        showSnackbar('Failed to save mapping: No response from server', 'error')
      }
    } catch (e) {
      console.error('Error saving template:', e)
      showSnackbar('Failed to save mapping: ' + (e.message || e), 'error')
    }
  }
  debouncedSave()
}

function refreshFileColumns() {
  if (originalRawData.value.length) {
    originalFileColumns.value = Object.keys(originalRawData.value[0] || {})
    fileColumns.value = [...originalFileColumns.value]
  } else if (rawData.value.length) {
    originalFileColumns.value = Object.keys(rawData.value[0] || {})
    fileColumns.value = [...originalFileColumns.value]
  } else {
    fileColumns.value = []
  }
  if (sheetType.value === 'multi') {
    const autoMapping = autoMatchColumns(fileColumns.value, requiredColumns.value, columnVariations.value)
    const merged = { ...columnMapping.value }
    for (const [key, val] of Object.entries(autoMapping)) {
      if (!merged[key]) merged[key] = val
    }
    columnMapping.value = merged
  }
  applyCurrentMapping()
  forceUpdate.value++
}

function getCellValue(cell) {
  if (cell == null) return ""
  
  if (typeof cell === 'object' && cell !== null) {
    if (cell.w !== undefined && cell.w !== null) return cell.w
    if (cell.v !== undefined && cell.v !== null) return cell.v
    if (cell.f !== undefined && cell.f !== null) return cell.f
    if (Array.isArray(cell)) return cell.join(', ')
    try {
      return JSON.stringify(cell)
    } catch {
      return String(cell)
    }
  }
  
  return cell
}

function openMappingDialog() {
  if (sheetType.value === 'single') {
    return
  }
  refreshFileColumns()

  if (!fileColumns.value.length && rawData.value.length) {
    const headers = Object.keys(rawData.value[0] || {})
    if (headers.length) {
      fileColumns.value = headers
      originalFileColumns.value = [...headers]
    }
  }
  if (!fileColumns.value.length && originalRawData.value.length) {
    const headers = Object.keys(originalRawData.value[0] || {})
    if (headers.length) {
      fileColumns.value = headers
      originalFileColumns.value = [...headers]
    }
  }

  if (!fileColumns.value.length && workbookSheets.value.length && currentSheetName.value) {
    const sheet = workbookSheets.value.find(s => s.name === currentSheetName.value)
    if (sheet && sheet.headers && sheet.headers.length) {
      fileColumns.value = sheet.headers
      originalFileColumns.value = [...sheet.headers]
    }
  }

  showMappingDialog.value = true
}

function closeMappingDialog() {
  showMappingDialog.value = false
}

async function applyColumnMappingAndClose() {
  applyCurrentMapping()

  if (currentMappingTemplateId.value) {
    try {
      await mappingTemplateManager.updateTemplate(currentMappingTemplateId.value, {
        columnMapping: columnMapping.value,
        fileColumns: fileColumns.value
      })
    } catch (e) {
      console.error('Error updating template on apply:', e)
    }
  }

  showMappingDialog.value = false
  showPreview.value = true
  forceUpdate.value++
}

function resetMapping() {
  const empty = {}
  requiredColumns.value.forEach(col => empty[col] = null)
  columnMapping.value = empty
  applyCurrentMapping()
}

async function openWorkbookViewer() {
  console.log('=== openWorkbookViewer called ===')
  console.log('uploadedFile.value:', uploadedFile.value)
  console.log('originalFileBuffer.value:', originalFileBuffer.value)
  console.log('workbookSheets.value:', workbookSheets.value)
  console.log('workbookSheets.value.length:', workbookSheets.value?.length)
  console.log('worksheetWorkflow.workbookSheets.value:', worksheetWorkflow.workbookSheets.value)
  console.log('worksheetWorkflow.workbookSheets.value.length:', worksheetWorkflow.workbookSheets.value?.length)
  console.log('currentSheetName.value:', currentSheetName.value)

  if (!originalFileBuffer.value) {
    alert('File buffer not available. Please upload a file first.')
    return
  }
  if (originalFileBuffer.value.byteLength === 0) {
    alert('File buffer is empty. Please re-upload the file.')
    return
  }

  if (worksheetWorkflow.workbookSheets.value?.length > 0) {
    workbookSheets.value = [...worksheetWorkflow.workbookSheets.value]
    console.log('Using pre-parsed sheets from workflow:', workbookSheets.value.length)
  } else {
    workbookSheets.value = []
    console.log('No pre-parsed sheets available, will parse from buffer')
  }

  if (activeSession.value?.id) {
    loadWorksheetStatuses()
  }

  console.log('Setting showWorkbookViewer.value = true')

  try {
    showWorkbookViewer.value = true
    console.log('showWorkbookViewer.value after set:', showWorkbookViewer.value)

    await nextTick()
    console.log('After nextTick, showWorkbookViewer.value:', showWorkbookViewer.value)
  } catch (error) {
    console.error('Error opening workbook viewer:', error)
    alert('Failed to open workbook viewer: ' + error.message)
  }
}



function workOnSelectedSheet() {
  if (!currentSheetName.value) {
    alert('Please select a sheet first')
    return
  }
  
  if (!originalFileBuffer.value) {
    alert('File buffer not available')
    return
  }
  handleWorkOnSheet(currentSheetName.value)
  showWorkbookViewer.value = false
}

async function autoDetectSingleInstrument() {
  if (!currentSheetName.value || !originalFileBuffer.value) {
    alert('Please select a sheet first')
    return
  }

  if (isDetecting.value) {
    console.log('Detection already in progress, ignoring duplicate request')
    return
  }
  isDetecting.value = true
  detectionStatus.value = 'scanning'

  autoDetectedFields.value = {}
  autoDetectedFieldsWithMetadata.value = {}
  autoDetectedAdditionalFields.value = {}
  detectedCurrencies.value = []
  detectedInstrumentType.value = ''
  excludedDetectedFields.value.clear()
  showDetectionSuccess.value = false

  console.log(`🔍 Starting auto-detection on sheet: "${currentSheetName.value}"`)

  try {
    if (!requiredColumns.value || requiredColumns.value.length === 0) {
      console.log('⚠️ Required columns not loaded, loading config...')
      await loadConfig()
      console.log('✅ Config loaded, required columns:', requiredColumns.value)
    }

    detectionStatus.value = 'analyzing'
    
    let currencyFilter = null
    if (selectedCurrency.value) {
      if (selectedCurrency.value === 'custom') {
        currencyFilter = customCurrency.value?.toUpperCase() || null
      } else {
        currencyFilter = selectedCurrency.value.toUpperCase()
      }
    }

    console.log(`🔍 Starting auto-detection on sheet: "${currentSheetName.value}"`)
    console.log('Currency filter:', currencyFilter)
    console.log('Required columns:', requiredColumns.value)
    console.log('Instrument type:', instrumentType.value)

    detectionStatus.value = 'detecting'

    const detectionPromise = autoDetectInstrumentFields(
      originalFileBuffer.value,
      currentSheetName.value,
      requiredColumns.value,
      instrumentType.value,
      null,
      null,
      currencyFilter,
      (status) => {
        detectionStatus.value = status
      }
    )
    
    const timeoutPromise = new Promise((_, reject) => 
      setTimeout(() => reject(new Error('Detection timeout - scan took too long')), 30000)
    )
    
    const detectionResult = await Promise.race([detectionPromise, timeoutPromise])

    console.log('=== Detection Result ===')
    console.log('Raw detected fields:', detectionResult?.fields)
    console.log('Detected currencies:', detectionResult?.currencies)
    console.log('Missing fields:', detectionResult?.missingFields)
    console.log('Additional fields:', Object.keys(detectionResult?.additionalFields || {}))

    detectionStatus.value = 'validating'
    
    console.log('=== Normalizing Detected Fields ===')
    const normalized = normalizeDetectedFields(
      detectionResult?.fields,
      detectionResult?.fieldsWithMetadata,
      instrumentType.value,
      requiredColumns.value
    )
    console.log('Normalized fields:', normalized.fields)
    console.log('Normalized fields with metadata:', normalized.fieldsWithMetadata)

    detectionStatus.value = 'complete'

    const mergedFields = { ...normalized.fields }
    const mergedFieldsWithMetadata = { ...normalized.fieldsWithMetadata }
    for (const [key, value] of Object.entries(detectionResult?.additionalFields || {})) {
      if (!(key in mergedFields)) {
        mergedFields[key] = value
        mergedFieldsWithMetadata[key] = value
      }
    }

    console.log('=== Merged Detection Results ===')
    console.log('Primary fields:', Object.keys(normalized.fields).length)
    console.log('Additional fields:', Object.keys(detectionResult?.additionalFields || {}).length)
    console.log('Total merged fields:', Object.keys(mergedFields).length)

    // Auto-calculate days_to_maturity if missing but dates are present
    if (!mergedFields.days_to_maturity && !mergedFields.term_days && !mergedFields.daysToMaturity) {
      const issueDate = mergedFields.issue_date || mergedFields.valuation_date || mergedFields.settlement_date
      const maturityDate = mergedFields.maturity_date
      
      if (issueDate && maturityDate) {
        try {
          const issue = new Date(issueDate)
          const maturity = new Date(maturityDate)
          
          if (!isNaN(issue.getTime()) && !isNaN(maturity.getTime())) {
            const daysDiff = Math.ceil((maturity - issue) / (1000 * 60 * 60 * 24))
            
            if (daysDiff > 0) {
              mergedFields.days_to_maturity = daysDiff
              mergedFieldsWithMetadata.days_to_maturity = {
                value: daysDiff,
                location: 'auto-calculated from dates',
                source: 'auto-calculation',
                confidence: 1.0
              }
              console.log(`✅ Auto-calculated days_to_maturity: ${daysDiff} days (from ${issueDate} to ${maturityDate})`)
            }
          }
        } catch (e) {
          console.log('Could not auto-calculate days_to_maturity from dates:', e.message)
        }
      }
    }

    autoDetectedFields.value = mergedFields
    autoDetectedFieldsWithMetadata.value = mergedFieldsWithMetadata
    autoDetectedAdditionalFields.value = detectionResult?.additionalFields || {}
    detectedCurrencies.value = detectionResult?.currencies || []
    detectedInstrumentType.value = instrumentType.value

    await nextTick()

    console.log('=== Setting State for Popup ===')
    console.log('autoDetectedFields:', autoDetectedFields.value)
    console.log('autoDetectedFieldsWithMetadata:', autoDetectedFieldsWithMetadata.value)
    console.log('autoDetectedAdditionalFields:', autoDetectedAdditionalFields.value)
    console.log('detectedCurrencies:', detectedCurrencies.value)
    
    if (!selectedCurrency.value) {
      if (detectedCurrencies.value.length === 1) {
        selectedCurrency.value = detectedCurrencies.value[0]
      } else if (detectedCurrencies.value.length > 1) {
        selectedCurrency.value = ''
      }
    }
    
    showDetectionSuccess.value = true
  } catch (error) {
    console.error('Auto Detect error:', error)
    if (Object.keys(autoDetectedFields.value).length > 0) {
      console.log('Showing partial detection results despite error')
      showDetectionSuccess.value = true
    } else {
      alert('Auto Detect failed: ' + error.message)
    }
  } finally {
    isDetecting.value = false
  }
}

async function handleMultiTableDetect(event) {
  if (isDetecting.value) {
    return
  }
  isDetecting.value = true

  autoDetectedFields.value = {}
  autoDetectedFieldsWithMetadata.value = {}
  autoDetectedAdditionalFields.value = {}
  detectedCurrencies.value = []
  detectedInstrumentType.value = ''
  selectedCurrency.value = ''
  excludedDetectedFields.value.clear()
  showDetectionSuccess.value = false

  try {
    const detectedInstruments = []
    
    let currencyFilter = null
    if (selectedCurrency.value) {
      if (selectedCurrency.value === 'custom') {
        currencyFilter = customCurrency.value?.toUpperCase() || null
      } else {
        currencyFilter = selectedCurrency.value.toUpperCase()
      }
    }
    
    for (const table of event.tables) {
      console.log(`Processing table: ${table.tableName}`)
      console.log(`Table range: Row ${table.range.startRow + 1} - ${table.range.endRow + 1}, Col ${table.range.startCol} - ${table.range.endCol}`)
      console.log(`Table data length:`, table.data?.length)
      console.log(`Table data sample:`, table.data?.slice(0, 3))
      
      try {
        const tableData = table.data
        
        const detectionResult = await autoDetectInstrumentFields(
          originalFileBuffer.value,
          event.sheetName,
          requiredColumns.value,
          event.instrumentType,
          table.range,
          tableData,
          currencyFilter,
          (status) => {
            detectionStatus.value = status
          }
        )

        console.log(`Detection result for ${table.tableName}:`, detectionResult)

        const normalized = normalizeDetectedFields(
          detectionResult?.fields,
          detectionResult?.fieldsWithMetadata,
          event.instrumentType,
          requiredColumns.value
        )

        const mergedFields = { ...normalized.fields }
        const mergedFieldsWithMetadata = { ...normalized.fieldsWithMetadata }
        for (const [key, value] of Object.entries(detectionResult?.additionalFields || {})) {
          if (!(key in mergedFields)) {
            mergedFields[key] = value
            mergedFieldsWithMetadata[key] = value
          }
        }

        console.log(`Merged fields for ${table.tableName}:`, Object.keys(mergedFields).length)

        if (Object.keys(mergedFields).length > 0) {
          detectedInstruments.push({
            tableName: table.tableName,
            instrumentName: mergedFields.InstrumentName || table.tableName,
            fields: mergedFields,
            fieldsWithMetadata: mergedFieldsWithMetadata,
            currencies: detectionResult.currencies || [],
            missingFields: requiredColumns.value.filter(c => !mergedFields[c]),
            range: table.range
          })
        }
      } catch (error) {
        console.error(`Error detecting table ${table.tableName}:`, error)
      }
    }

    if (detectedInstruments.length > 0) {
      multiTableDetectionResults.value = detectedInstruments
      showMultiTableDetectionSuccess.value = true
      showWorkbookViewer.value = false
    } else {
      showMultiTableDetectionSuccess.value = true
      showWorkbookViewer.value = false
    }
  } finally {
    isDetecting.value = false
  }
}

function useMultiTableDetectedFields() {
  showMultiTableDetectionSuccess.value = false
  showWorkbookViewer.value = false

  const combinedFields = {}
  for (const instrument of multiTableDetectionResults.value) {
    for (const [key, fieldObj] of Object.entries(instrument.fields)) {
      const actualValue = typeof fieldObj === 'object' && fieldObj !== null ? fieldObj.value : fieldObj
      if (!(key in combinedFields)) {
        combinedFields[key] = actualValue
      }
    }
  }

  if (!combinedFields.InstrumentName && multiTableDetectionResults.value.length > 0) {
    combinedFields.InstrumentName = multiTableDetectionResults.value[0].instrumentName || ''
  }

  console.log('=== Use Multi-Table Detected Fields ===')
  console.log('Combined fields:', combinedFields)
  console.log('Keys:', Object.keys(combinedFields))

  const tabularData = [combinedFields]

  rawData.value = tabularData
  originalRawData.value = JSON.parse(JSON.stringify(tabularData))
  cleanedData.value = JSON.parse(JSON.stringify(tabularData))
  
  const headers = Object.keys(combinedFields)
  fileColumns.value = headers
  originalFileColumns.value = [...headers]
  
  worksheetSelected.value = true
  showPreview.value = true
  sheetType.value = 'single'
  mappingApplied.value = true
  
  extractedValues.value = combinedFields
  autoDetectedFields.value = combinedFields
  
  activeTab.value = 'cleaning'
  
}

function formatDetectedValue(field, value) {
  if (value === null || value === undefined) return '—'

  const lc = String(field).toLowerCase()

  if (lc.includes('frequency') || lc.includes('coupon') && lc.includes('frequency')) {
    return String(value)
  }

  if (lc.includes('interest') && lc.includes('payment') && lc.includes('frequency')) {
    return String(value)
  }
  if (lc.includes('payment') && lc.includes('frequency')) {
    return String(value)
  }

  if (lc.includes('date') || lc.includes('maturity')) {
    try {
      const date = new Date(value)
      if (!isNaN(date.getTime())) {
        return date.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
      }
    } catch {}
  }

  if (lc.includes('rate') || lc.includes('yield') || lc.includes('coupon') || lc.includes('discount')) {
    const num = parseFloat(value)
    if (!isNaN(num)) return num.toFixed(2) + '%'
  }

  if (lc.includes('value') || lc.includes('amount') || lc.includes('price') || lc.includes('principal')) {
    const num = parseFloat(value)
    if (!isNaN(num)) return num.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  }

  return String(value)
}

function updateSelectedCurrency(fieldName, currency, isAdditional = false) {
  const targetFields = isAdditional ? autoDetectedAdditionalFields : autoDetectedFields
  const fieldData = targetFields[fieldName]

  if (fieldData && fieldData.currencyVariants && fieldData.currencyVariants[currency]) {
    fieldData.selectedCurrency = currency
    fieldData.value = fieldData.currencyVariants[currency]
    fieldData.currency = currency
    console.log(`Updated ${fieldName} to use ${currency}: ${fieldData.value}`)
  }
}

async function handleCustomCurrencyInput() {
  if (customCurrency.value) {
    customCurrency.value = customCurrency.value.toUpperCase()
  }
  
  if (customCurrency.value && customCurrency.value.length === 3) {
    try {
      const detectionResult = await autoDetectInstrumentFields(
        originalFileBuffer.value,
        currentSheetName.value,
        requiredColumns.value,
        instrumentType.value,
        null,
        null,
        customCurrency.value,
        (status) => {
          detectionStatus.value = status
        }
      )

      const normalized = normalizeDetectedFields(
        detectionResult?.fields,
        detectionResult?.fieldsWithMetadata,
        instrumentType.value,
        requiredColumns.value
      )

      if (Object.keys(normalized.fields).length > 0) {
        autoDetectedFields.value = normalized.fields
        autoDetectedFieldsWithMetadata.value = normalized.fieldsWithMetadata
        detectedCurrencies.value = detectionResult?.currencies || []
      }
    } catch (error) {
      console.error('Error re-running detection with custom currency:', error)
    }
  }
}

async function handleCurrencyChange() {
  console.log('handleCurrencyChange called with selectedCurrency:', selectedCurrency.value)
  
  if (!currentSheetName.value || !originalFileBuffer.value) {
    console.log('Missing sheet name or file buffer')
    return
  }

  if (isDetecting.value) {
    console.log('Detection already in progress')
    return
  }
  isDetecting.value = true

  try {
    let currencyFilter = null
    if (selectedCurrency.value) {
      if (selectedCurrency.value === 'custom') {
        currencyFilter = customCurrency.value?.toUpperCase() || null
      } else {
        currencyFilter = selectedCurrency.value.toUpperCase()
      }
    }
    
    console.log('Currency filter for re-detection:', currencyFilter)

    const detectionResult = await autoDetectInstrumentFields(
      originalFileBuffer.value,
      currentSheetName.value,
      requiredColumns.value,
      instrumentType.value,
      null,
      null,
      currencyFilter,
      (status) => {
        detectionStatus.value = status
      }
    )

    console.log('Detection result after currency change:', detectionResult)

    const normalized = normalizeDetectedFields(
      detectionResult?.fields,
      detectionResult?.fieldsWithMetadata,
      instrumentType.value,
      requiredColumns.value
    )

    const mergedFields = { ...normalized.fields }
    const mergedFieldsWithMetadata = { ...normalized.fieldsWithMetadata }
    for (const [key, value] of Object.entries(detectionResult?.additionalFields || {})) {
      if (!(key in mergedFields)) {
        mergedFields[key] = value
        mergedFieldsWithMetadata[key] = value
      }
    }

    if (Object.keys(mergedFields).length > 0) {
      // Auto-calculate days_to_maturity if missing but dates are present
      if (!mergedFields.days_to_maturity && !mergedFields.term_days && !mergedFields.daysToMaturity) {
        const issueDate = mergedFields.issue_date || mergedFields.valuation_date || mergedFields.settlement_date
        const maturityDate = mergedFields.maturity_date
        
        if (issueDate && maturityDate) {
          try {
            const issue = new Date(issueDate)
            const maturity = new Date(maturityDate)
            
            if (!isNaN(issue.getTime()) && !isNaN(maturity.getTime())) {
              const daysDiff = Math.ceil((maturity - issue) / (1000 * 60 * 60 * 24))
              
              if (daysDiff > 0) {
                mergedFields.days_to_maturity = daysDiff
                mergedFieldsWithMetadata.days_to_maturity = {
                  value: daysDiff,
                  location: 'auto-calculated from dates',
                  source: 'auto-calculation',
                  confidence: 1.0
                }
                console.log(`✅ Auto-calculated days_to_maturity: ${daysDiff} days (from ${issueDate} to ${maturityDate})`)
              }
            }
          } catch (e) {
            console.log('Could not auto-calculate days_to_maturity from dates:', e.message)
          }
        }
      }

      autoDetectedFields.value = mergedFields
      autoDetectedFieldsWithMetadata.value = mergedFieldsWithMetadata
      autoDetectedAdditionalFields.value = detectionResult?.additionalFields || {}
      detectedCurrencies.value = detectionResult?.currencies || []
      detectedInstrumentType.value = instrumentType.value
      console.log('Updated detected fields:', autoDetectedFields.value)
      console.log('Total fields after merge:', Object.keys(mergedFields).length)
    } else {
      console.log('No fields detected with currency filter')
    }
    
    showDetectionSuccess.value = true
  } catch (error) {
    console.error('Error re-running detection with currency change:', error)
  } finally {
    isDetecting.value = false
  }
}

async function useDetectedFields() {
  console.log('=== useDetectedFields Called ===')
  console.log('Input autoDetectedFields.value:', autoDetectedFields.value)
  console.log('Input autoDetectedFieldsWithMetadata.value:', autoDetectedFieldsWithMetadata.value)
  console.log('Input autoDetectedAdditionalFields.value:', autoDetectedAdditionalFields.value)

  const preservedDetectedFields = JSON.parse(JSON.stringify(autoDetectedFields.value))
  const preservedDetectedFieldsWithMetadata = JSON.parse(JSON.stringify(autoDetectedFieldsWithMetadata.value))
  const preservedDetectedAdditionalFields = JSON.parse(JSON.stringify(autoDetectedAdditionalFields.value))
  const preservedDetectedCurrencies = JSON.parse(JSON.stringify(detectedCurrencies.value))

  const mergedDetectedFields = { ...preservedDetectedFields }
  for (const [key, value] of Object.entries(preservedDetectedAdditionalFields)) {
    if (!(key in mergedDetectedFields)) {
      mergedDetectedFields[key] = value
    }
  }

  console.log('Merged fields for Cleaning:', Object.keys(mergedDetectedFields).length)

  autoDetectedFields.value = mergedDetectedFields
  autoDetectedFieldsWithMetadata.value = preservedDetectedFieldsWithMetadata
  autoDetectedAdditionalFields.value = preservedDetectedAdditionalFields
  detectedCurrencies.value = preservedDetectedCurrencies

  console.log('=== Detection fields restored BEFORE tab switch ===')
  console.log('autoDetectedFields:', Object.keys(autoDetectedFields.value).length)

  isUsingDetectedFields.value = true

  showDetectionSuccess.value = false
  showWorkbookViewer.value = false

  const values = {}

  for (const [key, value] of Object.entries(autoDetectedFields.value)) {
    if (typeof value === 'object' && value !== null) {
      if (value.currencyVariants && value.selectedCurrency && value.currencyVariants[value.selectedCurrency]) {
        values[key] = value.currencyVariants[value.selectedCurrency]
        console.log(`Primary field ${key}: using ${value.selectedCurrency} variant = ${values[key]}`)
      } else {
        values[key] = value.value
      }
    } else {
      values[key] = value
    }
  }

  console.log('Adding additional detected fields...')
  console.log('Additional fields count:', Object.keys(autoDetectedAdditionalFields.value).length)
  for (const [key, value] of Object.entries(autoDetectedAdditionalFields.value)) {
    if (!(key in values)) {
      if (typeof value === 'object' && value !== null) {
        if (value.currencyVariants && value.selectedCurrency && value.currencyVariants[value.selectedCurrency]) {
          values[key] = value.currencyVariants[value.selectedCurrency]
          console.log(`Additional field ${key}: using ${value.selectedCurrency} variant = ${values[key]}`)
        } else {
          values[key] = value.value
        }
      } else {
        values[key] = value
      }
      console.log(`Added additional field: ${key} = ${values[key]}`)
    }
  }

  if (selectedCurrency.value && selectedCurrency.value !== 'custom') {
    values['Currency'] = selectedCurrency.value
  } else if (selectedCurrency.value === 'custom' && customCurrency.value) {
    values['Currency'] = customCurrency.value.toUpperCase()
  }

  console.log('=== Use Detected Fields ===')
  console.log('Values to be used:', values)
  console.log('Keys:', Object.keys(values))
  console.log('Number of values:', Object.keys(values).length)
  console.log('Primary fields:', Object.keys(autoDetectedFields.value).length)
  console.log('Additional fields:', Object.keys(autoDetectedAdditionalFields.value).length)
  
  extractedValues.value = values
  
  rawData.value = [{ ...values }]
  originalRawData.value = [{ ...values }]
  cleanedData.value = [{ ...values }]
  fileColumns.value = Object.keys(values)
  originalFileColumns.value = [...fileColumns.value]
  
  console.log('Data state after setting:')
  console.log('rawData.value:', JSON.stringify(rawData.value))
  console.log('cleanedData.value:', JSON.stringify(cleanedData.value))
  console.log('fileColumns.value:', JSON.stringify(fileColumns.value))
  console.log('extractedValues.value:', JSON.stringify(extractedValues.value))
  console.log('autoDetectedFields.value (should remain unchanged):', JSON.stringify(autoDetectedFields.value))
  
  console.log('DEBUG - extractedValues keys:', Object.keys(extractedValues.value))
  console.log('DEBUG - cleanedData[0]:', JSON.stringify(cleanedData.value[0]))
  console.log('DEBUG - fileColumns:', JSON.stringify(fileColumns.value))
  
  worksheetSelected.value = true
  showPreview.value = true
  sheetType.value = 'single'
  mappingApplied.value = true
  
  console.log('Before setting activeTab to cleaning, current value:', activeTab.value)
  
  showWorkbookViewer.value = false
  
  await nextTick()
  activeTab.value = 'cleaning'
  await nextTick()
  
  console.log('After setting activeTab to cleaning, current value:', activeTab.value)

  console.log('=== Tab Switched to Cleaning ===')
  console.log('Cleaning tab will show cleanedData:', cleanedData.value)
  console.log('Cleaning tab will show autoDetectedFields:', autoDetectedFields.value)
  console.log('Cleaning tab will show extractedValues:', extractedValues.value)
  console.log('Active tab set to:', activeTab.value)
}

function handleProcessSheetFromViewer(sheetName, sheetData, sheetHeaders) {
  console.log(`🔄 handleProcessSheetFromViewer: Processing worksheet "${sheetName}"`)
  console.log('🔄 This function sets activeTab to upload - this may be overwriting the cleaning tab')
  
  currentSheetName.value = sheetName
  
  clearActiveCache(true)
  
  originalRawData.value = sheetData || []
  rawData.value = sheetData.map(row => {
    const normalized = {}
    for (const [key, value] of Object.entries(row)) {
      const extracted = getCellValue(value)
      normalized[key] = extracted
    }
    return normalized
  })
  
  fileColumns.value = sheetHeaders || []
  originalFileColumns.value = [...fileColumns.value]
  worksheetSelected.value = true
  showPreview.value = true
  const detection = detectSheetType(sheetData, instrumentType.value)
  sheetType.value = detection.type
  if (detection.type === 'multi') {
    currentMappingTemplateId.value = null
    columnMapping.value = autoMatchColumns(fileColumns.value, requiredColumns.value, columnVariations.value)
    showMappingDialog.value = true
  } else {
    columnMapping.value = {}
    mappingApplied.value = true
  }
  applyCurrentMapping()
  showWorkbookViewer.value = false
  activeTab.value = 'upload'
  forceUpdate.value++
  debouncedSave()
}

function handleSheetSelected(sheetName, sheetData, sheetHeaders) {
  console.log('Sheet selected:', sheetName)
  currentSheetName.value = sheetName
  rawData.value = sheetData
}

function handleProcessSheet(sheetName, sheetData, sheetHeaders) {
  console.log('Processing sheet:', sheetName)
  showWorkbookViewer.value = false
  rawData.value = sheetData
  applyCurrentMapping()
}

function handleProcessSheetFromModal(payload) {
  console.log('Processing from modal viewer:', payload.sheetName)
  worksheetStatus.value[payload.sheetName] = 'in_progress'

  rawData.value = payload.data
  originalRawData.value = JSON.parse(JSON.stringify(payload.data))
  originalFileColumns.value = payload.headers || []
  fileColumns.value = [...originalFileColumns.value]
  currentSheetName.value = payload.sheetName

  const sheetDetection = detectSheetType(payload.data, instrumentType.value)
  sheetType.value = sheetDetection.type

  if (sheetDetection.type === 'single') {
    handleSingleInstrumentSheet(payload.data, payload.sheetName)
  } else {
    handleMultiInstrumentSheet(payload.data, payload.headers)
  }
}

function handleMultiInstrumentSheet(data, headers) {
  columnMapping.value = autoMatchColumns(headers, requiredColumns.value, columnVariations.value)
  applyCurrentMapping()
  showMappingDialog.value = true
  console.log('Multi-instrument sheet processed, mapping dialog shown')
}

function handleSingleInstrumentSheet(data, sheetName) {
  const fieldMappings = getRequiredFieldMappings(instrumentType.value)
  const extractedValues = extractSingleInstrumentValues(data, fieldMappings)
  const tabularData = convertExtractedToTabular(extractedValues)
  rawData.value = tabularData
  originalRawData.value = JSON.parse(JSON.stringify(tabularData))
  fileColumns.value = Object.keys(tabularData[0] || {})
  originalFileColumns.value = [...fileColumns.value]
  columnMapping.value = {}
  mappingApplied.value = true
  applyCurrentMapping()
  activeTab.value = 'preview'
  console.log('Single-instrument sheet processed, skipping to preview')
}

function convertExtractedToTabular(extractedValues) {
  const row = {}
  const columnMapping = {
    faceValue: 'Face Value',
    issueDate: 'Issue Date',
    maturityDate: 'Maturity Date',
    couponRate: 'Coupon Rate',
    yield: 'Yield',
    price: 'Price',
    discountRate: 'Discount Rate',
    frequency: 'Frequency'
  }

  for (const [key, value] of Object.entries(extractedValues)) {
    const columnName = columnMapping[key] || key
    row[columnName] = value
  }

  return [row]
}

function updateExtractedValue(key, value) {
  extractedValues.value[key] = value
}

function clearExtractedValue(key) {
  extractedValues.value[key] = 'N/A'
}

function toggleExcludeField(fieldKey) {
  if (excludedDetectedFields.value.has(fieldKey)) {
    excludedDetectedFields.value.delete(fieldKey)
  } else {
    excludedDetectedFields.value.add(fieldKey)
  }
  excludedDetectedFields.value = new Set(excludedDetectedFields.value)
}

function addCustomField() {
  if (!newFieldName.value.trim() || !newFieldValue.value.trim()) {
    alert('Please enter both field name and value')
    return
  }

  const fieldName = newFieldName.value.trim()
  const fieldValue = newFieldValue.value.trim()

  autoDetectedFields.value[fieldName] = {
    value: fieldValue,
    currencyVariants: {},
    selectedCurrency: 'CUSTOM',
    currency: null,
    location: 'custom',
    confidence: 1.0,
    detectedFrom: 'custom',
    semanticMatch: fieldName
  }

  extractedValues.value[fieldName] = fieldValue

  if (cleanedData.value.length > 0) {
    cleanedData.value[0][fieldName] = fieldValue
  }

  if (rawData.value.length > 0) {
    rawData.value[0][fieldName] = fieldValue
  }

  if (!fileColumns.value.includes(fieldName)) {
    fileColumns.value.push(fieldName)
  }

  console.log(`Added custom field: ${fieldName} = ${fieldValue}`)

  newFieldName.value = ''
  newFieldValue.value = ''

  debouncedSave()
}

async function loadWorksheetStatuses() {
  if (!activeSession.value?.id) return
  
  try {
    const worksheets = await sessionManager.getAllWorksheets(activeSession.value.id)
    worksheetStatuses.value = {}
    for (const [name, data] of Object.entries(worksheets)) {
      worksheetStatuses.value[name] = data.status || 'saved'
    }
  } catch (err) {
    console.error('Failed to load worksheet statuses:', err)
  }
}

function markWorksheetAsSaved() {
  const worksheetName = currentSheetName.value
  if (worksheetName) {
    worksheetStatuses.value[worksheetName] = 'saved'
    console.log('Marked worksheet as saved:', worksheetName)
  }
}

function findMatchingRequiredColumn(column, requiredColumns) {
  const lowerColumn = column.toLowerCase()
  return requiredColumns.find(req =>
    req.toLowerCase() === lowerColumn ||
    lowerColumn.includes(req.toLowerCase()) ||
    req.toLowerCase().includes(lowerColumn)
  )
}

function autoDetectColumns(data, instrumentType) {
  if (!data || data.length === 0) return { success: false }

  const firstRow = data[0]
  let matchCount = 0

  const systemColumns = []
  if (instrumentType === 'money-market') {
    systemColumns.push('instrument_type', 'face_value', 'purchase_price', 'days_to_maturity', 'issue_date', 'maturity_date', 'coupon_rate', 'yield')
  } else if (instrumentType === 'bonds') {
    systemColumns.push('instrument_type', 'face_value', 'coupon_rate', 'coupon_frequency', 'issue_date', 'maturity_date', 'yield_to_maturity', 'current_price')
  } else if (instrumentType === 'tbills') {
    systemColumns.push('instrument_type', 'face_value', 'purchase_price', 'days_to_maturity', 'issue_date', 'maturity_date', 'discount_rate')
  }

  Object.keys(firstRow).forEach(col => {
    const normalizedCol = col.toLowerCase().trim()
    systemColumns.forEach(sysCol => {
      const normalizedSysCol = sysCol.toLowerCase().trim()
      if (normalizedCol === normalizedSysCol ||
          normalizedCol.includes(normalizedSysCol) ||
          normalizedSysCol.includes(normalizedCol)) {
        matchCount++
      }
    })
  })

  const matchRatio = matchCount / systemColumns.length
  console.log(`Auto-detection: ${matchCount}/${systemColumns.length} matches (${(matchRatio * 100).toFixed(1)}%)`)

  return { success: matchRatio > 0.4, data: data }
}

function buildDynamicColumns(results) {
  const allFields = new Set()
  const excludeFields = ['_raw', '_source', 'index', '__v']

  results.forEach(result => {
    Object.keys(result).forEach(key => {
      if (result[key] !== null && result[key] !== undefined && result[key] !== '' && !excludeFields.includes(key)) {
        allFields.add(key)
      }
    })
  })

  return [...allFields]
}

function editInstrumentRow(index, field, value) {
  instrumentSummary.value.rows[index][field] = value
  console.log(`Edited instrument row ${index}, field ${field}: ${value}`)
}

function editPortfolioRow(index, field, value) {
  portfolioSummary.value.rows[index][field] = value
  console.log(`Edited portfolio row ${index}, field ${field}: ${value}`)
}

function formatCellValue(value, col) {
  if (value === null || value === undefined || value === '') return '-'

  if (typeof value === 'number' && !isNaN(value)) {
    const isTimeField = col.toLowerCase().includes('day') || col.toLowerCase().includes('maturity') || col.toLowerCase().includes('duration') || col.toLowerCase().includes('term')
    if (isTimeField) {
      const rounded = Math.round(value)
      return rounded.toLocaleString()
    }
    const rounded = Math.round(value * 100) / 100
    if (isPercentageField(col)) {
      return rounded.toFixed(2) + '%'
    }
    return rounded.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  }

  if (isDateField(value)) {
    const d = new Date(value)
    return d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })
  }

  return value
}

function isPercentageField(col) {
  const lowerCol = col.toLowerCase()
  return lowerCol.includes('rate') || lowerCol.includes('yield') || lowerCol.includes('discount') || lowerCol.includes('coupon')
}

function isDateField(value) {
  return value instanceof Date || (typeof value === 'string' && /^\d{4}-\d{2}-\d{2}/.test(value))
}

function isNumericField(col) {
  const numericFields = [
    'notional amount', 'face value', 'present value', 'impairment',
    'market value', 'purchase price', 'price', 'yield', 'discount rate',
    'coupon', 'interest'
  ]
  const lowerCol = col.toLowerCase()
  return numericFields.some(f => lowerCol.includes(f))
}

const hasNumericColumns = computed(() => {
  return portfolioSummary.value.columns.some(col => isNumericField(col))
})

function calculateTotal(field) {
  let total = 0
  portfolioSummary.value.rows.forEach(row => {
    const val = parseFloat(row[field])
    if (!isNaN(val)) total += val
  })
  const rounded = Math.round(total * 100) / 100
  return rounded.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function exportSummary() {
  const currentData = instrumentSummary.value.rows || []
  const completedData = completedInstrumentSummary.value.rows || []
  
  if (!currentData.length && !completedData.length) { return }

  const allColumns = new Set()
  currentData.forEach(row => Object.keys(row).forEach(k => allColumns.add(k)))
  completedData.forEach(row => Object.keys(row).forEach(k => allColumns.add(k)))
  const displayCols = Array.from(allColumns)
  
  const wb = XLSX.utils.book_new()
  
  if (currentData.length) {
    const currentSheetData = currentData.map(row => {
      const obj = {}
      displayCols.forEach(col => {
        const value = row[col]
        if (typeof value === 'number' && !isNaN(value)) {
          const rounded = Math.round(value * 100) / 100
          obj[col] = rounded.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
        } else {
          obj[col] = value
        }
      })
      return obj
    })
    
    const wsCurrent = XLSX.utils.json_to_sheet(currentSheetData)
    XLSX.utils.book_append_sheet(wb, wsCurrent, 'Current Selection')
  }
  
  if (completedData.length) {
    const completedSheetData = completedData.map(row => {
      const obj = {}
      displayCols.forEach(col => {
        const value = row[col]
        if (typeof value === 'number' && !isNaN(value)) {
          const rounded = Math.round(value * 100) / 100
          obj[col] = rounded.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
        } else {
          obj[col] = value
        }
      })
      return obj
    })
    
    const wsCompleted = XLSX.utils.json_to_sheet(completedSheetData)
    XLSX.utils.book_append_sheet(wb, wsCompleted, 'All Completed History')
  }
  
  const summaryInfo = [
    ['Instrument Summary Export'],
    ['Export Date', new Date().toLocaleString()],
    ['Current Sheet', currentSheetName.value || 'N/A'],
    [''],
    ['Current Selection Records', currentData.length],
    ['Total Completed Records', completedData.length],
    ['Total Columns', displayCols.length],
    [''],
    ['Note: "Current Selection" shows results from the current worksheet/section only.'],
    ['"All Completed History" shows accumulated results from all processed selections.'],
    ['All calculated fields from the Calculations page are included.']
  ]
  const wsInfo = XLSX.utils.aoa_to_sheet(summaryInfo)
  XLSX.utils.book_append_sheet(wb, wsInfo, 'Summary Info')
  
  const suffix = activeValuationDate.value ? `_${activeValuationDate.value}` : ''
  XLSX.writeFile(wb, `instrument_summary${suffix}.xlsx`)
}

function viewCurrentSummary() {
  excelPopupMode.value = 'current'
  showInstrumentExcelPopup.value = true
  sortColumn.value = ''
  sortOrder.value = 'asc'
  currentPage.value = 1
  console.log('Opening Current Valuations popup')
  console.log('Current workbook:', currentWorkbookName.value)
}

function viewPreviousSummary() {
  excelPopupMode.value = 'previous'
  showInstrumentExcelPopup.value = true
  sortColumn.value = ''
  sortOrder.value = 'asc'
  currentPage.value = 1
  console.log('Opening Last Previous Valuation popup')
}

function viewAllSummaries() {
  excelPopupMode.value = 'all'
  showInstrumentExcelPopup.value = true
  sortColumn.value = ''
  sortOrder.value = 'asc'
  currentPage.value = 1
  console.log('Opening All Valuations popup')
}

function viewInstrumentSummaryExcel() {
  excelPopupMode.value = 'current'
  showInstrumentExcelPopup.value = true
  sortColumn.value = ''
  sortOrder.value = 'asc'
  currentPage.value = 1
  console.log('Opening Instrument Summary Excel popup')
  console.log('Current workbook:', currentWorkbookName.value)
}

function viewPreviousSummariesExcel() {
  excelPopupMode.value = 'previous'
  showInstrumentExcelPopup.value = true
  sortColumn.value = ''
  sortOrder.value = 'asc'
  currentPage.value = 1
  console.log('Opening Previous Summaries Excel popup')
}

function handleWorkbookLoaded(fileName) {
  console.log('=== handleWorkbookLoaded called ===')
  console.log('fileName:', fileName)
  console.log('showWorkbookViewer.value:', showWorkbookViewer.value)
  console.log('workbookSheets.value.length:', workbookSheets.value?.length)
  currentWorkbookName.value = fileName || 'Unknown'

  nextTick(() => {
    const dialog = document.querySelector('.v-dialog')
    console.log('Dialog element in DOM:', !!dialog)
    if (dialog) {
      console.log('Dialog display:', window.getComputedStyle(dialog).display)
      console.log('Dialog visibility:', window.getComputedStyle(dialog).visibility)
    }
  })
}

function closeInstrumentExcelPopup() {
  showInstrumentExcelPopup.value = false
}

function continueWorkingOnCurrent() {
  console.log('Continue on Current Sheet - returning to workbook view:', currentSheetName.value)
  console.log('Current workbook:', currentWorkbookName.value)
  
  clearActiveCache(true)
  
  showWorkbookViewer.value = true
  activeTab.value = 'upload'
  forceUpdate.value++
}

function chooseAnotherSheet() {
  console.log('Choose Another Sheet - returning to workbook view')
  console.log('Current workbook:', currentWorkbookName.value)
  
  clearActiveCache(true)
  
  currentSheetName.value = ''
  worksheetSelected.value = false
  
  showWorkbookViewer.value = true
  activeTab.value = 'upload'
  forceUpdate.value++
}

function sortByColumn(col) {
  if (sortColumn.value === col) {
    sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortColumn.value = col
    sortOrder.value = 'asc'
  }
}

function formatForExcel(value, type = 'number', key = '') {
  if (value === null || value === undefined || value === '') return ''
  const num = parseFloat(value)
  if (isNaN(num)) return value
  
  const isTimeField = key.toLowerCase().includes('day') || key.toLowerCase().includes('maturity') || key.toLowerCase().includes('duration') || key.toLowerCase().includes('term')
  if (isTimeField) {
    return Math.round(num)
  }
  
  if (type === 'percentage') {
    return Math.round(num * 100) / 100
  } else if (type === 'money') {
    return Math.round(num * 100) / 100
  }
  return num
}

function exportInstrumentSummaryExcel() {
  const rows = instrumentSummary.value.rows
  if (!rows.length) {
    return
  }

  try {
    const wb = XLSX.utils.book_new()
    const displayCols = getDisplayColumns()

    let allRows = [...rows]
    
    if (activeSession.value?.id) {
      sessionManager.getAllWorksheets(activeSession.value.id).then(worksheets => {
        console.log('Aggregating data from worksheets:', Object.keys(worksheets))
        
        for (const [worksheetName, worksheetData] of Object.entries(worksheets)) {
          if (worksheetData.instrumentSummary && worksheetData.instrumentSummary.rows) {
            const worksheetRows = worksheetData.instrumentSummary.rows.map(row => ({
              ...row,
              Worksheet: worksheetName
            }))
            allRows = [...allRows, ...worksheetRows]
          }
        }
        
        console.log('Total rows after aggregation:', allRows.length)
        
        const data = allRows.map(row => {
          const obj = {}
          displayCols.forEach(col => {
            let val = row[col] !== undefined ? row[col] : ''
            if (isPercentageField(col)) {
              val = formatForExcel(val, 'percentage', col)
            } else if (col.toLowerCase().includes('value') || col.toLowerCase().includes('price') || col.toLowerCase().includes('amount') || col.toLowerCase().includes('principal') || col.toLowerCase().includes('interest')) {
              val = formatForExcel(val, 'money', col)
            } else {
              val = formatForExcel(val, 'number', col)
            }
            obj[col] = val
          })
          return obj
        })
        const ws1 = XLSX.utils.json_to_sheet(data)
        XLSX.utils.book_append_sheet(wb, ws1, 'Instruments')

        const analytics = computeAnalytics(allRows)
        const analyticsRows = Object.entries(analytics).map(([key, value]) => {
          let formattedValue = value
          if (isPercentageField(key)) {
            formattedValue = formatForExcel(value, 'percentage', key)
          } else if (key.toLowerCase().includes('value') || key.toLowerCase().includes('amount') || key.toLowerCase().includes('interest')) {
            formattedValue = formatForExcel(value, 'money', key)
          } else {
            formattedValue = formatForExcel(value, 'number', key)
          }
          return { Metric: key, Value: formattedValue }
        })
        const ws2 = XLSX.utils.json_to_sheet(analyticsRows)
        XLSX.utils.book_append_sheet(wb, ws2, 'Analytics')

        XLSX.writeFile(wb, `instrument_summary_${Date.now()}.xlsx`)
      }).catch(err => {
        console.error('Failed to aggregate worksheets:', err)
        exportCurrentRowsOnly(wb, displayCols, rows)
      })
    } else {
      exportCurrentRowsOnly(wb, displayCols, rows)
    }
  } catch (e) {
    console.error(e)
    showSnackbar('Failed to export Excel: ' + e.message, 'error')
  }
}

function exportCurrentRowsOnly(wb, displayCols, rows) {
  const data = rows.map(row => {
    const obj = {}
    displayCols.forEach(col => {
      let val = row[col] !== undefined ? row[col] : ''
      if (isPercentageField(col)) {
        val = formatForExcel(val, 'percentage', col)
      } else if (col.toLowerCase().includes('value') || col.toLowerCase().includes('price') || col.toLowerCase().includes('amount') || col.toLowerCase().includes('principal') || col.toLowerCase().includes('interest')) {
        val = formatForExcel(val, 'money', col)
      } else {
        val = formatForExcel(val, 'number', col)
      }
      obj[col] = val
    })
    return obj
  })
  const ws1 = XLSX.utils.json_to_sheet(data)
  XLSX.utils.book_append_sheet(wb, ws1, 'Instruments')

  const analytics = computeAnalytics(rows)
  const analyticsRows = Object.entries(analytics).map(([key, value]) => {
    let formattedValue = value
    if (isPercentageField(key)) {
      formattedValue = formatForExcel(value, 'percentage', key)
    } else if (key.toLowerCase().includes('value') || key.toLowerCase().includes('amount') || key.toLowerCase().includes('interest')) {
      formattedValue = formatForExcel(value, 'money', key)
    } else {
      formattedValue = formatForExcel(value, 'number', key)
    }
    return { Metric: key, Value: formattedValue }
  })
  const ws2 = XLSX.utils.json_to_sheet(analyticsRows)
  XLSX.utils.book_append_sheet(wb, ws2, 'Analytics')

  XLSX.writeFile(wb, `instrument_summary_${Date.now()}.xlsx`)
}

function openWorkflowPopup(row, idx) {
  selectedWorkflowInstrument.value = row
  selectedWorkflowIndex.value = idx
  showWorkflowPopup.value = true
  console.log('Opening workflow popup for instrument:', row['Instrument Name'] || `Instrument ${idx + 1}`)
}

function closeWorkflowPopup() {
  showWorkflowPopup.value = false
  selectedWorkflowInstrument.value = null
  selectedWorkflowIndex.value = 0
}

function navigateToUpload() {
  switchTab('upload')
  closeWorkflowPopup()
}

function navigateToCleaning() {
  switchTab('cleaning')
  closeWorkflowPopup()
}

function navigateToCalculations() {
  switchTab('calculations')
  closeWorkflowPopup()
}

function navigateToVisualizations() {
  switchTab('visualizations')
  closeWorkflowPopup()
}

function goToPreviousStep() {
  const currentTab = activeTab.value
  const tabOrder = ['upload', 'cleaning', 'calculations', 'visualizations', 'summary']
  const currentIndex = tabOrder.indexOf(currentTab)

  if (currentIndex > 0) {
    switchTab(tabOrder[currentIndex - 1])
  }
}

function handleSheetSelection(sheetData) {
  if (sheetData && sheetData.data) {
    rawData.value = sheetData.data
    originalRawData.value = JSON.parse(JSON.stringify(sheetData.data))
    originalFileColumns.value = sheetData.headers || []
    fileColumns.value = [...originalFileColumns.value]
    columnMapping.value = autoMatchColumns(fileColumns.value, requiredColumns.value, columnVariations.value)
    applyCurrentMapping()
    showPreview.value = true
    addToHistory(`${uploadedFile.value.name} - ${sheetData.sheetName}`, sheetData.data, uploadedFileBase64.value)
    debouncedSave()
    forceUpdate.value++
  }
  showWorkbookViewer.value = false
}

function openExcelReview(data, title) {
  if (!data?.length) {
    if (cleanedData.value.length) data = cleanedData.value
    else if (rawData.value.length) data = rawData.value
    else { return }
  }
  excelData.value = data
  excelColumns.value = Object.keys(data[0] || {})
  excelDialogTitle.value = title || 'Data Review'
  showExcelDialog.value = true
}

function openInstrumentDataExcel() {
  const instrumentData = []

  const calcRow = {
    'Metric': 'Calculations'
  }

  const fields = config.value.calculationFields
  fields.forEach(field => {
    const value = selectedCalculations.value[field.key] ?? allCalculations.value[field.key]
    if (value !== undefined) {
      let displayValue = value
      if (typeof value === 'number' && !isNaN(value)) {
        const isTimeField = field.key.toLowerCase().includes('day') || field.key.toLowerCase().includes('maturity') || field.key.toLowerCase().includes('duration') || field.key.toLowerCase().includes('term')
        if (isTimeField) {
          const rounded = Math.round(value)
          if (field.prefix) displayValue = field.prefix + rounded.toLocaleString()
          else if (field.suffix) displayValue = rounded.toLocaleString() + field.suffix
          else displayValue = rounded.toLocaleString()
        } else {
          const rounded = Math.round(value * 100) / 100
          if (field.prefix) displayValue = field.prefix + rounded.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
          else if (field.suffix) displayValue = rounded.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + field.suffix
          else displayValue = rounded.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
        }
      } else if (field.prefix) {
        displayValue = field.prefix + value
      } else if (field.suffix) {
        displayValue = value + field.suffix
      }
      calcRow[field.label] = displayValue
    }
  })

  instrumentData.push(calcRow)

  if (allCalculations.value.fred) {
    const fredRow = {
      'Metric': 'FRED Benchmark',
      'Series ID': allCalculations.value.fred.series_id || '',
      'Series Label': allCalculations.value.fred.series_label || '',
      'Benchmark Rate': formatNumber(allCalculations.value.fred.benchmark_rate || 0),
      'Spread vs Market': formatNumber(allCalculations.value.fred.spread_vs_market || 0),
      'Country': allCalculations.value.fred.country || '',
      'Currency': allCalculations.value.fred.currency || '',
      'Maturity': allCalculations.value.fred.maturity || ''
    }
    instrumentData.push(fredRow)
  }

  excelData.value = instrumentData
  excelColumns.value = Object.keys(instrumentData[0] || {})
  excelDialogTitle.value = `${instrumentLabel} - Calculations & Yield Curve`
  showExcelDialog.value = true
}

function downloadCalculatedInstrumentsExcel() {
  const summaryRows = instrumentSummary.value.rows || []
  if (!summaryRows.length) {
    showSnackbar('No calculated instruments to export', 'error')
    return
  }

  const workbook = XLSX.utils.book_new()
  
  const allColumns = new Set()
  summaryRows.forEach(row => {
    Object.keys(row).forEach(key => allColumns.add(key))
  })
  const columns = Array.from(allColumns)

  const data = [columns]

  summaryRows.forEach(row => {
    const dataRow = columns.map(col => {
      const value = row[col]
      return value !== undefined && value !== null ? value : ''
    })
    data.push(dataRow)
  })

  const worksheet = XLSX.utils.aoa_to_sheet(data)
  
  const columnWidths = columns.map(col => {
    const isNumeric = col.toLowerCase().includes('value') || col.toLowerCase().includes('amount') || col.toLowerCase().includes('rate') || col.toLowerCase().includes('yield') || col.toLowerCase().includes('price') || col.toLowerCase().includes('principal') || col.toLowerCase().includes('interest') || col.toLowerCase().includes('discount') || col.toLowerCase().includes('coupon')
    const isDate = col.toLowerCase().includes('date')
    const isName = col.toLowerCase().includes('name') || col.toLowerCase().includes('instrument') || col.toLowerCase().includes('ticker') || col.toLowerCase().includes('worksheet') || col.toLowerCase().includes('workbook')
    
    if (isNumeric) return { wch: 18 }
    if (isDate) return { wch: 14 }
    if (isName) return { wch: 25 }
    return { wch: 20 }
  })
  worksheet['!cols'] = columnWidths

  const range = XLSX.utils.decode_range(worksheet['!ref'])
  for (let C = range.s.c; C <= range.e.c; ++C) {
    const cellAddress = XLSX.utils.encode_cell({ r: 0, c: C })
    if (!worksheet[cellAddress]) continue
    worksheet[cellAddress].s = {
      font: { bold: true, color: { rgb: "FFFFFF" } },
      fill: { fgColor: { rgb: "0B2044" } },
      alignment: { horizontal: "center", vertical: "center" }
    }
  }

  for (let R = range.s.r + 1; R <= range.e.r; ++R) {
    for (let C = range.s.c; C <= range.e.c; ++C) {
      const cellAddress = XLSX.utils.encode_cell({ r: R, c: C })
      if (!worksheet[cellAddress]) continue
      
      const colName = columns[C]
      const isNumeric = colName.toLowerCase().includes('value') || colName.toLowerCase().includes('amount') || colName.toLowerCase().includes('rate') || colName.toLowerCase().includes('yield') || colName.toLowerCase().includes('price') || colName.toLowerCase().includes('percentage')
      
      worksheet[cellAddress].s = {
        alignment: {
          horizontal: isNumeric ? "right" : "left",
          vertical: "center"
        }
      }
    }
  }

  XLSX.utils.book_append_sheet(workbook, worksheet, 'Calculated Instruments')

  const suffix = activeValuationDate.value ? `_${activeValuationDate.value}` : ''
  const fileName = `Calculated_Instruments_${activeSession.value?.name || 'Session'}${suffix}.xlsx`
  XLSX.writeFile(workbook, fileName)
}

function closeExcelDialog() {
  showExcelDialog.value = false
  excelData.value = []
}

function onRawExcelUpdate(data, sourceData) {
  if (sourceData?.length) originalRawData.value = sourceData
  rawData.value = data
  debouncedSave()
}

function onCleanedExcelUpdate(data) {
  cleanedData.value = data
  debouncedSave()
  calculateMetrics()
}

function onExcelDataUpdate(data) {
  excelData.value = data
  if (activeTab.value === 'upload') rawData.value = data
  if (cleanedData.value.length) cleanedData.value = data
  debouncedSave()
}

async function continueAfterUpload() {
  if (!uploadedFile.value) { return }
  if (!rawData.value.length) { return }

  saveSessionData()
  await nextTick()
  activeTab.value = 'cleaning'
  await nextTick()
  forceUpdate.value++
  const sid = activeSession.value?.id || sessionManager.getActiveSessionId()
  if (sid) {
    await markStepCompleted(String(sid), 'upload')
  }
}

const cleaningResultStats = computed(() => {
  if (!cleaningStats.value || !cleanedData.value.length) return []
  return [
    { title: 'Original Rows', value: cleaningStats.value.totalRows || 0, icon: 'mdi-table-row', gradient: 'linear-gradient(135deg, #0B2044, #1a3a6e)' },
    { title: 'Cleaned Rows', value: cleanedData.value.length, icon: 'mdi-check-circle', gradient: 'linear-gradient(135deg, #4CAF50, #2E7D32)' },
    { title: 'Duplicates Removed', value: cleaningStats.value.removedRows || 0, icon: 'mdi-delete', gradient: 'linear-gradient(135deg, #F44336, #d32f2f)' },
    { title: 'Missing Values Fixed', value: cleaningStats.value.fixedMissing || 0, icon: 'mdi-pencil', gradient: 'linear-gradient(135deg, #FF9800, #F57C00)' }
  ]
})

const cleaningOperationsSummary = computed(() => {
  if (!cleaningStats.value || !cleaningStats.value.operationsPerformed) return []
  return cleaningStats.value.operationsPerformed
})

function applyCleaning() {
  if (!rawData.value.length) {
    return
  }

  try {
    const tableDetection = autoDetectTable(rawData.value)
    let data = JSON.parse(JSON.stringify(rawData.value))
    const operations = []
    const originalLength = data.length

    if (tableDetection.type === 'table') {
      data = tableDetection.data
      operations.push('Auto-detected and extracted table data')
    }

    if (cleaningOptions.value.removeDuplicates) {
      const before = data.length
      const seen = new Set()
      data = data.filter(row => { const key = JSON.stringify(row); if (seen.has(key)) return false; seen.add(key); return true })
      const removed = before - data.length
      if (removed > 0) operations.push(`Removed ${removed} duplicate rows`)
    }
    if (cleaningOptions.value.removeEmptyRows) {
      const before = data.length
      data = data.filter(row => Object.values(row).some(v => v !== null && v !== '' && v !== undefined))
      const removed = before - data.length
      if (removed > 0) operations.push(`Removed ${removed} empty rows`)
    }
    if (cleaningOptions.value.trimWhitespace) {
      data = data.map(row => { const newRow = {}; Object.keys(row).forEach(k => { newRow[k] = typeof row[k] === 'string' ? row[k].trim() : row[k] }); return newRow })
      operations.push('Trimmed whitespace from all text fields')
    }
    if (cleaningOptions.value.convertToNumbers) {
      let converted = 0
      data = data.map(row => { const newRow = { ...row }; Object.keys(newRow).forEach(k => { if (typeof newRow[k] === 'string' && !isNaN(newRow[k]) && newRow[k].trim() !== '') { newRow[k] = parseFloat(newRow[k]); converted++ } }); return newRow })
      if (converted > 0) operations.push(`Converted ${converted} text values to numbers`)
    }
    if (cleaningOptions.value.fillMissingText) {
      let filled = 0
      data = data.map(row => { Object.keys(row).forEach(k => { if (row[k] === undefined || row[k] === null || row[k] === '') { row[k] = 'N/A'; filled++ } }); return row })
      if (filled > 0) operations.push(`Filled ${filled} missing values with 'N/A'`)
    }
    if (cleaningOptions.value.dropRowsWithMissing) {
      const before = data.length
      data = data.filter(row => Object.values(row).every(v => v !== null && v !== '' && v !== undefined && (typeof v !== 'number' || !isNaN(v))))
      const removed = before - data.length
      if (removed > 0) operations.push(`Removed ${removed} rows with missing values`)
    }
    if (cleaningOptions.value.removeOutliers) {
      const numericCols = Object.keys(data[0] || {}).filter(col => data.some(row => typeof row[col] === 'number'))
      let removedTotal = 0
      for (const col of numericCols) {
        const before = data.length
        const values = data.map(r => r[col]).filter(v => typeof v === 'number')
        const mean = values.reduce((a, b) => a + b, 0) / values.length
        const std = Math.sqrt(values.map(v => Math.pow(v - mean, 2)).reduce((a, b) => a + b, 0) / values.length)
        const threshold = 3 * std
        data = data.filter(row => Math.abs(row[col] - mean) <= threshold)
        removedTotal += before - data.length
      }
      if (removedTotal > 0) operations.push(`Removed ${removedTotal} outlier rows`)
    }
    if (cleaningOptions.value.standardizeDates) {
      let standardized = 0
      const format = selectedDateFormat.value || 'YYYY-MM-DD'
      data = data.map(row => { 
        Object.keys(row).forEach(k => { 
          if (k.toLowerCase().includes('date') && row[k]) { 
            const d = new Date(row[k]); 
            if (!isNaN(d)) { 
              let formattedDate = ''
              if (format === 'YYYY-MM-DD') {
                formattedDate = d.toISOString().split('T')[0]
              } else if (format === 'DD-MM-YYYY') {
                formattedDate = d.toLocaleDateString('en-GB').replace(/\//g, '-')
              } else if (format === 'MM-DD-YYYY') {
                formattedDate = d.toLocaleDateString('en-US').replace(/\//g, '-')
              } else if (format === 'DD/MM/YYYY') {
                formattedDate = d.toLocaleDateString('en-GB')
              } else if (format === 'MM/DD/YYYY') {
                formattedDate = d.toLocaleDateString('en-US')
              } else if (format === 'YYYY/MM/DD') {
                const year = d.getFullYear()
                const month = String(d.getMonth() + 1).padStart(2, '0')
                const day = String(d.getDate()).padStart(2, '0')
                formattedDate = `${year}/${month}/${day}`
              } else if (format === 'DD-MM-YY') {
                const year = String(d.getFullYear()).slice(-2)
                const month = String(d.getMonth() + 1).padStart(2, '0')
                const day = String(d.getDate()).padStart(2, '0')
                formattedDate = `${day}-${month}-${year}`
              } else if (format === 'MM-DD-YY') {
                const year = String(d.getFullYear()).slice(-2)
                const month = String(d.getMonth() + 1).padStart(2, '0')
                const day = String(d.getDate()).padStart(2, '0')
                formattedDate = `${month}-${day}-${year}`
              } else {
                formattedDate = d.toISOString().split('T')[0]
              }
              row[k] = formattedDate
              standardized++ 
            } 
          } 
        }); 
        return row 
      })
      if (standardized > 0) operations.push(`Standardized ${standardized} date values to ${format}`)
    }
    if (cleaningOptions.value.removeSpecialChars) {
      data = data.map(row => { Object.keys(row).forEach(k => { if (typeof row[k] === 'string') row[k] = row[k].replace(/[^a-zA-Z0-9\s]/g, '') }); return row })
      operations.push('Removed special characters from text fields')
    }
    if (cleaningOptions.value.changeCase && cleaningOptions.value.caseType !== 'none') {
      const caseType = cleaningOptions.value.caseType === 'upper' ? 'UPPERCASE' : cleaningOptions.value.caseType === 'lower' ? 'lowercase' : 'Title Case'
      data = data.map(row => { Object.keys(row).forEach(k => { if (typeof row[k] === 'string') { if (cleaningOptions.value.caseType === 'upper') row[k] = row[k].toUpperCase(); else if (cleaningOptions.value.caseType === 'lower') row[k] = row[k].toLowerCase(); else if (cleaningOptions.value.caseType === 'title') row[k] = row[k].replace(/\b\w/g, l => l.toUpperCase()) } }); return row })
      operations.push(`Changed text to ${caseType}`)
    }
    if (cleaningOptions.value.fillWithCustom && cleaningOptions.value.customFillValue) {
      let filled = 0
      data = data.map(row => { Object.keys(row).forEach(k => { if (row[k] === undefined || row[k] === null || row[k] === '') { row[k] = cleaningOptions.value.customFillValue; filled++ } }); return row })
      if (filled > 0) operations.push(`Filled ${filled} missing values with custom value`)
    }
    if (cleaningOptions.value.removeColumnsAllMissing) {
      const beforeCols = Object.keys(data[0] || {}).length
      const colsToKeep = Object.keys(data[0] || {}).filter(col => data.some(row => row[col] !== null && row[col] !== '' && row[col] !== undefined))
      data = data.map(row => { const newRow = {}; colsToKeep.forEach(c => newRow[c] = row[c]); return newRow })
      const removedCols = beforeCols - colsToKeep.length
      if (removedCols > 0) operations.push(`Removed ${removedCols} columns with all missing values`)
    }
    if (cleaningOptions.value.capOutliers) {
      const numericCols = Object.keys(data[0] || {}).filter(col => data.some(row => typeof row[col] === 'number'))
      let capped = 0
      for (const col of numericCols) {
        const values = data.map(r => r[col]).filter(v => typeof v === 'number')
        const mean = values.reduce((a, b) => a + b, 0) / values.length
        const std = Math.sqrt(values.map(v => Math.pow(v - mean, 2)).reduce((a, b) => a + b, 0) / values.length)
        const upper = mean + 3 * std, lower = mean - 3 * std
        data = data.map(row => { if (row[col] > upper) { row[col] = upper; capped++ } if (row[col] < lower) { row[col] = lower; capped++ } return row })
      }
      if (capped > 0) operations.push(`Capped ${capped} outlier values`)
    }
    if (cleaningOptions.value.removeRowsSpecificColumnEmpty && cleaningOptions.value.specificColumn) {
      const before = data.length
      data = data.filter(row => row[cleaningOptions.value.specificColumn] !== null && row[cleaningOptions.value.specificColumn] !== '')
      const removed = before - data.length
      if (removed > 0) operations.push(`Removed ${removed} rows with empty ${cleaningOptions.value.specificColumn}`)
    }
    if (cleaningOptions.value.standardizeNumericRange) {
      const numericCols = Object.keys(data[0] || {}).filter(col => data.some(row => typeof row[col] === 'number'))
      if (numericCols.length > 0) {
        operations.push(`Standardized numeric range for ${numericCols.length} columns`)
        for (const col of numericCols) {
          const values = data.map(r => r[col]).filter(v => typeof v === 'number')
          const min = Math.min(...values), max = Math.max(...values)
          if (max !== min) data = data.map(row => { if (typeof row[col] === 'number') row[col] = (row[col] - min) / (max - min); return row })
        }
      }
    }
    if (cleaningOptions.value.fillForward) {
      let filled = 0
      for (let i = 1; i < data.length; i++) Object.keys(data[i]).forEach(k => { if (data[i][k] === undefined || data[i][k] === null || data[i][k] === '') { data[i][k] = data[i-1][k]; filled++ } })
      if (filled > 0) operations.push(`Filled ${filled} missing values forward`)
    }
    if (cleaningOptions.value.fillBackward) {
      let filled = 0
      for (let i = data.length - 2; i >= 0; i--) Object.keys(data[i]).forEach(k => { if (data[i][k] === undefined || data[i][k] === null || data[i][k] === '') { data[i][k] = data[i+1][k]; filled++ } })
      if (filled > 0) operations.push(`Filled ${filled} missing values backward`)
    }

    if (excludedDetectedFields.value.size > 0) {
      const excludedCount = excludedDetectedFields.value.size
      data = data.map(row => {
        const newRow = {}
        Object.keys(row).forEach(key => {
          if (!excludedDetectedFields.value.has(key)) {
            newRow[key] = row[key]
          }
        })
        return newRow
      })
      operations.push(`Removed ${excludedCount} excluded fields from data`)
      console.log('=== Applied excluded fields in cleaning ===')
      console.log('Excluded fields:', Array.from(excludedDetectedFields.value))
      console.log('Remaining fields:', Object.keys(data[0] || {}))
    }

    cleanedData.value = data
    cleaningStats.value = { 
      totalRows: originalLength, 
      validRows: cleanedData.value.length, 
      removedRows: originalLength - cleanedData.value.length, 
      fixedMissing: 0,
      removedEmptyRows: cleaningOptions.value.removeEmptyRows ? (originalLength - data.filter(row => Object.values(row).some(v => v !== null && v !== '' && v !== undefined)).length) : 0,
      removedSpecificColumnEmpty: cleaningOptions.value.removeRowsSpecificColumnEmpty && cleaningOptions.value.specificColumn ? (originalLength - data.filter(row => row[cleaningOptions.value.specificColumn] !== null && row[cleaningOptions.value.specificColumn] !== '').length) : 0,
      standardizedNumeric: cleaningOptions.value.standardizeNumericRange ? Object.keys(data[0] || {}).filter(col => data.some(row => typeof row[col] === 'number')).length : 0,
      filledForward: cleaningOptions.value.fillForward ? 1 : 0,
      filledBackward: cleaningOptions.value.fillBackward ? 1 : 0,
      removedDuplicates: cleaningOptions.value.removeDuplicates ? 1 : 0,
      operationsPerformed: operations
    }
    
    debouncedSave()
    forceUpdate.value++
  } catch (error) {
    console.error('Error during cleaning:', error)
    showSnackbar('Error during cleaning: ' + error.message, 'error')
  }
}

async function continueAfterCleaning() {
  if (!cleanedData.value.length) {
    return
  }
  
  if (sheetType.value === 'single' && excludedDetectedFields.value.size > 0) {
    const filteredData = cleanedData.value.map(row => {
      const filteredRow = {}
      for (const [key, value] of Object.entries(row)) {
        const isExcluded = excludedDetectedFields.value.has(key)
        if (!isExcluded) {
          filteredRow[key] = value
        }
      }
      return filteredRow
    })
    
    cleanedData.value = filteredData
  }
  
  activeTab.value = 'calculations'
  await nextTick()
  forceUpdate.value++
  saveSessionData()
  const sid = activeSession.value?.id || sessionManager.getActiveSessionId()
  if (sid) {
    await markStepCompleted(String(sid), 'cleaning')
  }

  calculateMetrics().catch(err => {
    showSnackbar('Error calculating metrics: ' + err.message, 'error')
  })
}

async function calculateMetrics() {
  if (!cleanedData.value.length) {
    showSnackbar('No data available for calculation. Please clean the data first.', 'error')
    return
  }

  if (isCalculating.value) {
    return
  }

  isCalculating.value = true

  const requiredFields = requiredColumns.value[instrumentType.value] || []
  const missingFields = []
  
  if (sheetType.value === 'single') {
    for (const field of requiredFields) {
      const hasColumn = cleanedData.value.some(row => row.hasOwnProperty(field))
      if (!hasColumn) {
        missingFields.push(field)
      }
    }
  } else {
    for (const field of requiredFields) {
      const mappedColumn = columnMapping.value[field]
      if (!mappedColumn) {
        missingFields.push(field)
        continue
      }
      
      const hasColumn = cleanedData.value.some(row => row.hasOwnProperty(mappedColumn))
      if (!hasColumn) {
        missingFields.push(field)
      }
    }
  }
  
  if (missingFields.length > 0) {
    showSnackbar(`Missing required fields: ${missingFields.join(', ')}. Please complete the mapping before calculating.`, 'error')
    isCalculating.value = false
    return
  }

  let dataForCalculation = JSON.parse(JSON.stringify(cleanedData.value))
  
  try {
    dataForCalculation = dataForCalculation.map(row => {
      const normalizedRow = {}
      for (const [key, value] of Object.entries(row)) {
        try {
          const normalizedKey = normalizeFieldName(key)
          let normalizedValue = value
          if (normalizedKey === 'coupon_frequency') {
            if (typeof value === 'string') {
              const freqLower = value.toLowerCase()
              if (freqLower.includes('semi') || freqLower.includes('half')) {
                normalizedValue = 2
              } else if (freqLower.includes('quarter')) {
                normalizedValue = 4
              } else if (freqLower.includes('month') || freqLower.includes('monthly')) {
                normalizedValue = 12
              } else if (freqLower.includes('annual') || freqLower.includes('year')) {
                normalizedValue = 1
              } else {
                normalizedValue = parseFloat(value) || 2
              }
            }
          }
          if (typeof value === 'string' && (normalizedKey.includes('principal') || normalizedKey.includes('face_value') || normalizedKey.includes('price') || normalizedKey.includes('amount') || normalizedKey.includes('value'))) {
            normalizedValue = parseFloat(value.replace(/[$,]/g, '')) || value
          }
          if (typeof value === 'string' && (normalizedKey.includes('rate') || normalizedKey.includes('yield') || normalizedKey.includes('coupon') || normalizedKey.includes('spread') || normalizedKey.includes('discount'))) {
            normalizedValue = parseFloat(value.replace(/[%]/g, '')) || value
          }
          normalizedRow[normalizedKey] = normalizedValue
        } catch (e) {
          normalizedRow[key] = value
        }
      }
      return normalizedRow
    })
  } catch (e) {
    console.error('Error normalizing data:', e)
    dataForCalculation = JSON.parse(JSON.stringify(cleanedData.value))
  }
  
  if (excludedDetectedFields.value.size > 0) {
    dataForCalculation = dataForCalculation.map(row => {
      const newRow = {}
      Object.keys(row).forEach(key => {
        if (!excludedDetectedFields.value.has(key)) {
          newRow[key] = row[key]
        }
      })
      return newRow
    })
  }

  try {
    let shouldContinueProcessing = true

    const response = await api.calculationsAPI.executeByType(
      instrumentType.value,
      dataForCalculation,
      {
        country: effectiveCountry.value,
        currency: effectiveCurrency.value,
        maturity: effectiveMaturity.value,
        manualInputs: manualInputs.value,
        sheet_name: currentSheetName.value,
        section_id: selectedSectionId.value,
        valuationDate: activeValuationDate.value || new Date().toISOString().split('T')[0]
      },
      null,
      activeSession.value?.id
    )

    if (response?.success) {
      if (response?.is_multi_instrument) {
        if (response?.instrument_summary) {
          const mappedRows = response.instrument_summary.rows?.map(row => {
            const mapped = mapBackendFieldsToDisplayNames(row, instrumentType.value)
            return filterToCalculatedFields(mapped, instrumentType.value)
          }) || []
          
          const currentRowsWithWorkbook = mappedRows.map(row => ({
            ...row,
            'Workbook': currentWorkbookName.value || 'Unknown',
            'Worksheet': row['Worksheet'] || row['worksheet'] || currentSheetName.value || 'Unknown'
          }))
          
          instrumentSummary.value = {
            columns: response.instrument_summary.columns,
            rows: currentRowsWithWorkbook
          }
        }
        
        if (response?.portfolio_summary) {
          portfolioSummary.value = response.portfolio_summary
        }

        const results = response?.results || {}
        const firstInstType = Object.keys(results)[0]
        if (firstInstType && results[firstInstType]) {
          calculations.value = results[firstInstType].data

          if (response?.aggregate) {
            const agg = {
              ...response.aggregate,
              accruedInterest: response.aggregate.accrued_interest ?? null,
              annualCoupon: response.aggregate.annual_coupon ?? null,
              bondEquivalentYield: response.aggregate.bond_equivalent_yield ?? null,
              couponRate: response.aggregate.coupon_rate ?? null,
              currentPrice: response.aggregate.current_price ?? null,
              currentYield: response.aggregate.current_yield ?? null,
              duration: response.aggregate.duration ?? null,
              faceValue: response.aggregate.face_value ?? null,
              frequency: response.aggregate.frequency ?? null,
              modifiedDuration: response.aggregate.modified_duration ?? null,
              yearsToMaturity: response.aggregate.years_to_maturity ?? null,
              yieldToMaturity: response.aggregate.yield_to_maturity ?? null,
              yieldCurveRate: response.aggregate.yield_curve_rate ?? null,
              purchasePrice: response.aggregate.purchase_price ?? null,
              termDays: response.aggregate.term_days ?? null,
              discountAmount: response.aggregate.discount_amount ?? null,
              discountYield: response.aggregate.discount_yield ?? null,
              moneyMarketYield: response.aggregate.money_market_yield ?? null,
              holdingPeriodYield: response.aggregate.holding_period_yield ?? null,
              effectiveAnnualYield: response.aggregate.effective_annual_yield ?? null,
              principal: response.aggregate.principal ?? null,
              interestRate: response.aggregate.interest_rate ?? null,
              interestEarned: response.aggregate.interest_earned ?? null,
              effectiveYield: response.aggregate.effective_yield ?? null
            }
            allCalculations.value = agg
            selectedCalculations.value = agg
          } else if (response?.data?.aggregates) {
            const aggregates = response.data.aggregates
            const agg = {
              ...aggregates,
              accruedInterest: aggregates.accrued_interest ?? null,
              annualCoupon: aggregates.annual_coupon ?? null,
              bondEquivalentYield: aggregates.bond_equivalent_yield ?? null,
              couponRate: aggregates.coupon_rate ?? null,
              currentPrice: aggregates.current_price ?? null,
              currentYield: aggregates.current_yield ?? null,
              duration: aggregates.duration ?? null,
              faceValue: aggregates.face_value ?? null,
              frequency: aggregates.frequency ?? null,
              modifiedDuration: aggregates.modified_duration ?? null,
              yearsToMaturity: aggregates.years_to_maturity ?? null,
              yieldToMaturity: aggregates.yield_to_maturity ?? null,
              yieldCurveRate: aggregates.yield_curve_rate ?? null,
              purchasePrice: aggregates.purchase_price ?? null,
              termDays: aggregates.term_days ?? null,
              discountAmount: aggregates.discount_amount ?? null,
              discountYield: aggregates.discount_yield ?? null,
              moneyMarketYield: aggregates.money_market_yield ?? null,
              holdingPeriodYield: aggregates.holding_period_yield ?? null,
              effectiveAnnualYield: aggregates.effective_annual_yield ?? null,
              principal: aggregates.principal ?? null,
              interestRate: aggregates.interest_rate ?? null,
              interestEarned: aggregates.interest_earned ?? null,
              effectiveYield: aggregates.effective_yield ?? null
            }
            allCalculations.value = agg
            selectedCalculations.value = agg
          } else {
            allCalculations.value = results[firstInstType].data
            selectedCalculations.value = results[firstInstType].data
          }
        } else {
          console.warn('No results found in response')
        }

        isUsingDetectedFields.value = false
      } else if (response?.data) {
        calculations.value = response.data

        if (response.data?.field_detection) {
          fieldDetectionResults.value = response.data.field_detection
        }

        const backendInstrumentNames = response?.instrument_names || []
        const calcArray = response.data.calculations || []

        if (sheetType.value === 'single' && calcArray.length === 1) {
          const singleCalc = calcArray[0]
          calculations.value = singleCalc
          
          const agg = {
            totalValue: singleCalc.total_value ?? singleCalc.calculated_value ?? null,
            instrumentCount: 1,
            avgRate: singleCalc.interest_rate ?? singleCalc.coupon_rate ?? singleCalc.discount_rate ?? null,
            weightedAvgRate: singleCalc.interest_rate ?? singleCalc.coupon_rate ?? singleCalc.discount_rate ?? null,
            totalInterest: singleCalc.interest_earned ?? null,
            interestEarned: singleCalc.interest_earned ?? null,
            annualYield: singleCalc.annual_yield ?? null,
            effectiveAnnualRate: singleCalc.effective_annual_rate ?? null,
            avgDaysToMaturity: singleCalc.days_to_maturity ?? singleCalc.term_days ?? null,
            totalPrincipal: singleCalc.principal ?? singleCalc.face_value ?? null,
            fred: response.data.fred || null,
            accruedInterest: singleCalc.accrued_interest ?? null,
            annualCoupon: singleCalc.annual_coupon ?? null,
            bondEquivalentYield: singleCalc.bond_equivalent_yield ?? null,
            couponRate: singleCalc.coupon_rate ?? null,
            currentPrice: singleCalc.current_price ?? null,
            currentYield: singleCalc.current_yield ?? null,
            duration: singleCalc.duration ?? null,
            faceValue: singleCalc.face_value ?? null,
            frequency: singleCalc.frequency ?? null,
            modifiedDuration: singleCalc.modified_duration ?? null,
            yearsToMaturity: singleCalc.years_to_maturity ?? null,
            yieldToMaturity: singleCalc.yield_to_maturity ?? null,
            yieldCurveRate: singleCalc.yield_curve_rate ?? null,
            discountYield: singleCalc.discount_yield ?? null,
            effectiveYield: singleCalc.effective_yield ?? null,
            termDays: singleCalc.term_days ?? null,
            status: singleCalc.status ?? null
          }
          
          if (singleCalc.status === 'cannot_calculate' || singleCalc.error) {
            const errorMsg = singleCalc.error || 'Calculation failed'
            const missingFields = singleCalc.missing_fields || []
            const invalidFields = singleCalc.invalid_fields || []
            
            let fullErrorMsg = errorMsg
            if (missingFields.length > 0) {
              fullErrorMsg += ` Missing: ${missingFields.join(', ')}`
            }
            if (invalidFields.length > 0) {
              const invalidMsg = invalidFields.map(f => `${f.field} (${f.reason})`).join(', ')
              fullErrorMsg += ` Invalid: ${invalidMsg}`
            }
            
            showSnackbar(`Calculation failed: ${fullErrorMsg}`, 'error')
            allCalculations.value = {
              status: 'error',
              message: fullErrorMsg,
              error: singleCalc.error,
              missing_field: singleCalc.missing_field,
              missing_fields: missingFields,
              invalid_fields: invalidFields,
              ...agg
            }
            selectedCalculations.value = allCalculations.value
            // Don't return - let finally block reset isCalculating
          }
          
          if (singleCalc.status === 'partial' && singleCalc.error) {
            const missingFields = singleCalc.missing_fields || []
            const invalidFields = singleCalc.invalid_fields || []
            
            let warningMsg = singleCalc.error
            if (missingFields.length > 0) {
              warningMsg += ` Missing: ${missingFields.join(', ')}`
            }
            if (invalidFields.length > 0) {
              const invalidMsg = invalidFields.map(f => `${f.field} (${f.reason})`).join(', ')
              warningMsg += ` Invalid: ${invalidMsg}`
            }
            
            showSnackbar(`Partial calculation: ${warningMsg}`, 'warning')
            agg.status = 'partial'
            agg.error = singleCalc.error
            agg.missing_field = singleCalc.missing_field
            agg.missing_fields = missingFields
            agg.invalid_fields = invalidFields
          }

          allCalculations.value = agg
          selectedCalculations.value = agg

          const row = {
            'Instrument Name': backendInstrumentNames[0] || singleCalc.instrument_name || 'Instrument',
            'Instrument Type': instrumentType.value,
            ...singleCalc,
            'Worksheet': currentSheetName.value || 'Calculated'
          }

          const currentCols = new Set()
          const mappedRow = mapBackendFieldsToDisplayNames(row, instrumentType.value)
          const filteredRow = filterToCalculatedFields(mappedRow, instrumentType.value)
          
          const filteredRowWithWorkbook = {
            ...filteredRow,
            'Workbook': currentWorkbookName.value || 'Unknown',
            'Worksheet': row['Worksheet'] || row['worksheet'] || currentSheetName.value || 'Unknown'
          }
          
          Object.keys(filteredRowWithWorkbook).forEach(k => currentCols.add(k))
          instrumentSummary.value = { columns: Array.from(currentCols), rows: [filteredRowWithWorkbook] }
          shouldContinueProcessing = false
        } else if (calcArray.length > 1) {
          const aggregates = response.data.aggregates || {}
          
          const agg = {
            totalValue: aggregates.totalValue ?? aggregates.total_value ?? null,
            instrumentCount: aggregates.instrument_count ?? aggregates.instrumentCount ?? calcArray.length,
            avgRate: aggregates.avgRate ?? aggregates.avg_rate ?? null,
            weightedAvgRate: aggregates.weightedAvgRate ?? aggregates.weighted_avg_rate ?? null,
            totalInterest: aggregates.totalInterest ?? aggregates.total_interest ?? null,
            interestEarned: aggregates.interestEarned ?? aggregates.interest_earned ?? null,
            annualYield: aggregates.annualYield ?? aggregates.annual_yield ?? null,
            effectiveAnnualRate: aggregates.effectiveAnnualRate ?? aggregates.effective_annual_rate ?? null,
            avgDaysToMaturity: aggregates.avgDaysToMaturity ?? aggregates.avg_days_to_maturity ?? null,
            totalPrincipal: aggregates.totalPrincipal ?? aggregates.total_principal ?? null,
            fred: response.data.fred || null,
            accruedInterest: aggregates.accrued_interest ?? null,
            annualCoupon: aggregates.annual_coupon ?? null,
            bondEquivalentYield: aggregates.bond_equivalent_yield ?? null,
            couponRate: aggregates.coupon_rate ?? null,
            currentPrice: aggregates.current_price ?? null,
            currentYield: aggregates.current_yield ?? null,
            duration: aggregates.duration ?? null,
            faceValue: aggregates.face_value ?? null,
            frequency: aggregates.frequency ?? null,
            modifiedDuration: aggregates.modified_duration ?? null,
            yearsToMaturity: aggregates.years_to_maturity ?? null,
            yieldToMaturity: aggregates.yield_to_maturity ?? null,
            yieldCurveRate: aggregates.yield_curve_rate ?? null,
            purchasePrice: aggregates.purchase_price ?? null,
            termDays: aggregates.term_days ?? null,
            discountAmount: aggregates.discount_amount ?? null,
            discountYield: aggregates.discount_yield ?? null,
            moneyMarketYield: aggregates.money_market_yield ?? null,
            holdingPeriodYield: aggregates.holding_period_yield ?? null,
            effectiveAnnualYield: aggregates.effective_annual_yield ?? null,
            principal: aggregates.principal ?? null,
            interestRate: aggregates.interest_rate ?? null,
            interestEarned: aggregates.interest_earned ?? null,
            discountYield: aggregates.discount_yield ?? null,
            effectiveYield: aggregates.effective_yield ?? null
          }
          
          allCalculations.value = agg
          selectedCalculations.value = agg
          
          const rows = calcArray.map((calc, idx) => {
            const mappedCalc = mapBackendFieldsToDisplayNames(calc, instrumentType.value)
            const filteredCalc = filterToCalculatedFields(mappedCalc, instrumentType.value)
            return {
              'Instrument Name': backendInstrumentNames[idx] || calc.instrument_name || `Instrument ${idx + 1}`,
              'Instrument Type': instrumentType.value,
              ...filteredCalc,
              'Worksheet': currentSheetName.value || 'Calculated'
            }
          })
          
          const currentCols = new Set()
          rows.forEach(r => Object.keys(r).forEach(k => currentCols.add(k)))
          
          const rowsWithWorkbook = rows.map(row => ({
            ...row,
            'Workbook': currentWorkbookName.value || 'Unknown',
            'Worksheet': row['Worksheet'] || row['worksheet'] || currentSheetName.value || 'Unknown'
          }))
          
          instrumentSummary.value = { columns: Array.from(currentCols), rows: rowsWithWorkbook }
          
          if (response.data.portfolio_summary) {
            portfolioSummary.value = response.data.portfolio_summary
          } else {
            const portfolioRow = {
              'Portfolio Name': currentSheetName.value || 'Current Portfolio',
              'Instrument Type': instrumentType.value,
              'Total Value': agg.totalValue || 0,
              'Number of Instruments': agg.instrumentCount || calcArray.length,
              'Average Rate': agg.avgRate || 0,
              'Weighted Average Rate': agg.weightedAvgRate || 0,
              'Total Interest': agg.totalInterest || 0,
              'Interest Earned': agg.interestEarned || 0,
              'Annual Yield': agg.annualYield || 0,
              'Effective Annual Rate': agg.effectiveAnnualRate || 0,
              'Average Days to Maturity': agg.avgDaysToMaturity || 0,
              'Total Principal': agg.totalPrincipal || 0
            }
            
            const portfolioCols = new Set()
            Object.keys(portfolioRow).forEach(k => portfolioCols.add(k))
            portfolioSummary.value = { columns: Array.from(portfolioCols), rows: [portfolioRow] }
            
            const existingPortfolioRows = completedPortfolioSummary.value.rows || []
            const mergedPortfolioRows = [...existingPortfolioRows, portfolioRow]
            
            const allPortfolioCols = new Set()
            mergedPortfolioRows.forEach(r => Object.keys(r).forEach(k => allPortfolioCols.add(k)))
            
            completedPortfolioSummary.value = { columns: Array.from(allPortfolioCols), rows: mergedPortfolioRows }
          }
          
          // Save portfolio summary snapshot for reports
          if (portfolioSummary.value) {
            let existingSnapshot = { instrumentsWithDetails: [] }
            try {
              const existing = await sessionManager.getWorksheetData(activeSession.value?.id, '__portfolio_summary__')
              if (existing && existing.instrumentsWithDetails) {
                existingSnapshot = existing
              }
            } catch (e) {
              console.log('No existing portfolio snapshot, creating new')
            }
            
            const existingInstrumentIndex = existingSnapshot.instrumentsWithDetails.findIndex(i => i.id === instrumentType.value)
            const currentInstrumentData = {
              id: instrumentType.value,
              details: portfolioSummary.value.rows || [],
              detailHeaders: portfolioSummary.value.columns || [],
              aggregate: agg || {},
              timestamp: Date.now()
            }
            
            if (existingInstrumentIndex >= 0) {
              existingSnapshot.instrumentsWithDetails[existingInstrumentIndex] = currentInstrumentData
            } else {
              existingSnapshot.instrumentsWithDetails.push(currentInstrumentData)
            }
            
            await sessionManager.saveWorksheetData(activeSession.value?.id, '__portfolio_summary__', existingSnapshot)
            console.log('Portfolio summary snapshot saved (single instrument) with', existingSnapshot.instrumentsWithDetails.length, 'instruments')
            
            // Also save to backend for authoritative storage
            try {
              await api.portfolioAPI.saveSummary({
                session_id: activeSession.value?.id,
                instrument_type: instrumentType.value,
                instrument_name: currentSheetName.value || instrumentType.value,
                total_value: agg?.totalValue || 0,
                face_value: agg?.faceValue || 0,
                count: agg?.instrumentCount || 0,
                avg_rate: agg?.avgRate || 0,
                details: portfolioSummary.value?.rows || [],
                detail_headers: portfolioSummary.value?.columns || [],
                aggregate: agg || {},
                valuation_date: activeValuationDate.value || new Date().toISOString().split('T')[0]
              })
              console.log('Portfolio summary saved to backend (single instrument) for', instrumentType.value)
            } catch (saveError) {
              console.error('Failed to save portfolio summary to backend (single instrument):', saveError)
            }
          }
        } else if (calcArray.length) {
          const rows = calcArray.map((calc, idx) => {
            const mappedCalc = mapBackendFieldsToDisplayNames(calc, instrumentType.value)
            const filteredCalc = filterToCalculatedFields(mappedCalc, instrumentType.value)
            return {
              'Instrument Name': backendInstrumentNames[idx] || calc.instrument_name || 'Instrument',
              'Instrument Type': instrumentType.value,
              ...filteredCalc,
              'Worksheet': currentSheetName.value || 'Calculated'
            }
          })

          const currentCols = new Set()
          rows.forEach(r => Object.keys(r).forEach(k => currentCols.add(k)))
          
          const rowsWithWorkbook = rows.map(row => ({
            ...row,
            'Workbook': currentWorkbookName.value || 'Unknown',
            'Worksheet': row['Worksheet'] || row['worksheet'] || currentSheetName.value || 'Unknown'
          }))
          
          instrumentSummary.value = { columns: Array.from(currentCols), rows: rowsWithWorkbook }

          const aggregates = response.data.aggregates || response.data || {}
          const agg = {
            totalValue: aggregates.totalValue ?? aggregates.total_value ?? null,
            instrumentCount: aggregates.instrument_count ?? aggregates.instrumentCount ?? null,
            avgRate: aggregates.avgRate ?? aggregates.avg_rate ?? null,
            weightedAvgRate: aggregates.weightedAvgRate ?? aggregates.weighted_avg_rate ?? null,
            totalInterest: aggregates.totalInterest ?? aggregates.total_interest ?? null,
            interestEarned: aggregates.interestEarned ?? aggregates.interest_earned ?? null,
            annualYield: aggregates.annualYield ?? aggregates.annual_yield ?? null,
            effectiveAnnualRate: aggregates.effectiveAnnualRate ?? aggregates.effective_annual_rate ?? null,
            avgDaysToMaturity: aggregates.avgDaysToMaturity ?? aggregates.avg_days_to_maturity ?? null,
            totalPrincipal: aggregates.totalPrincipal ?? aggregates.total_principal ?? null
          }
          
          allCalculations.value = agg
          selectedCalculations.value = agg

          const portfolioRow = {
            'Portfolio Name': currentSheetName.value || 'Current Portfolio',
            'Instrument Type': instrumentType.value,
            'Total Value': agg.totalValue ?? null,
            'Number of Instruments': agg.instrumentCount ?? null,
            'Average Rate': agg.avgRate ?? null,
            'Weighted Average Rate': agg.weightedAvgRate ?? null,
            'Total Interest': agg.totalInterest ?? null,
            'Interest Earned': agg.interestEarned ?? null,
            'Annual Yield': agg.annualYield ?? null,
            'Effective Annual Rate': agg.effectiveAnnualRate ?? null,
            'Average Days to Maturity': agg.avgDaysToMaturity ?? null,
            'Total Principal': agg.totalPrincipal ?? null
          }
          
          if (response.data.fred?.benchmark_rate) {
            portfolioRow['FRED Benchmark'] = response.data.fred.benchmark_rate
            portfolioRow['Spread vs Market'] = response.data.fred.spread_vs_market ?? null
          }
          
          const currentPortfolioCols = new Set()
          Object.keys(portfolioRow).forEach(k => currentPortfolioCols.add(k))
          portfolioSummary.value = { columns: Array.from(currentPortfolioCols), rows: [portfolioRow] }
        } else {
          const backendErrors = response.data?.errors || []
          const missingFields = response.data?.missing_fields || []
          const invalidFields = response.data?.invalid_fields || []
          
          let errorMsg = 'Not calculable — required input not detected.'
          if (backendErrors.length > 0) {
            errorMsg = backendErrors.map(e => e.message || e).join('; ')
          }
          if (missingFields.length > 0) {
            errorMsg += ` Missing: ${missingFields.join(', ')}`
          }
          if (invalidFields.length > 0) {
            const invalidMsg = invalidFields.map(f => `${f.field} (${f.reason})`).join(', ')
            errorMsg += ` Invalid: ${invalidMsg}`
          }
          
          showSnackbar(`Calculation failed: ${errorMsg}`, 'error')
          allCalculations.value = {
            status: 'error',
            message: errorMsg,
            errors: backendErrors,
            missing_fields: missingFields,
            invalid_fields: invalidFields
          }
          selectedCalculations.value = allCalculations.value
        }
        
        // Save portfolio summary to backend for authoritative storage
        if (response?.portfolio_summary || response.data?.portfolio_summary) {
          const portfolioData = response?.portfolio_summary || response.data?.portfolio_summary
          
          try {
            await api.portfolioAPI.saveSummary({
              session_id: activeSession.value?.id,
              instrument_type: instrumentType.value,
              instrument_name: currentSheetName.value || instrumentType.value,
              total_value: agg?.totalValue || 0,
              face_value: agg?.faceValue || 0,
              count: agg?.instrumentCount || 0,
              avg_rate: agg?.avgRate || 0,
              details: portfolioData.rows || [],
              detail_headers: portfolioData.columns || [],
              aggregate: agg || {},
              valuation_date: activeValuationDate.value || new Date().toISOString().split('T')[0]
            })
          } catch (saveError) {
            console.error('Failed to save portfolio summary to backend:', saveError)
            // Don't fail the calculation if portfolio summary save fails
          }
          
          // Also save to worksheets JSON for backward compatibility
          let existingSnapshot = { instrumentsWithDetails: [] }
          try {
            const existing = await sessionManager.getWorksheetData(activeSession.value?.id, '__portfolio_summary__')
            if (existing && existing.instrumentsWithDetails) {
              existingSnapshot = existing
            }
          } catch (e) {
            // No existing snapshot, creating new
          }
          
          const existingInstrumentIndex = existingSnapshot.instrumentsWithDetails.findIndex(i => i.id === instrumentType.value)
          const currentInstrumentData = {
            id: instrumentType.value,
            details: portfolioData.rows || [],
            detailHeaders: portfolioData.columns || [],
            aggregate: portfolioData.aggregate || allCalculations.value || {},
            timestamp: Date.now()
          }
          
          if (existingInstrumentIndex >= 0) {
            existingSnapshot.instrumentsWithDetails[existingInstrumentIndex] = currentInstrumentData
          } else {
            existingSnapshot.instrumentsWithDetails.push(currentInstrumentData)
          }

          await sessionManager.saveWorksheetData(activeSession.value?.id, '__portfolio_summary__', existingSnapshot)
        }
        
        if (activeSession.value?.id) {
          await sessionManager.saveInstrumentWorkflow(activeSession.value.id, instrumentType.value, {
            rawData: rawData.value,
            cleanedData: cleanedData.value,
            calculations: calculations.value,
            allCalculations: allCalculations.value,
            selectedCalculations: selectedCalculations.value,
            columnMapping: columnMapping.value,
            worksheetStatus: worksheetStatus.value,
            workbookSheets: workbookSheets.value,
            instrumentSummary: instrumentSummary.value,
            portfolioSummary: portfolioSummary.value,
            completedInstrumentSummary: completedInstrumentSummary.value,
            completedPortfolioSummary: completedPortfolioSummary.value,
            yieldCurveData: yieldCurveData.value,
            fredFilters: { country: effectiveCountry.value, currency: effectiveCurrency.value, maturity: effectiveMaturity.value },
            uploadedFile: uploadedFile.value?.name || null,
            cleaningStats: cleaningStats.value,
            sessionSavedAt: sessionSavedAt.value || new Date().toISOString(),
            manualInputs: manualInputs.value,
            formulas: formulas.value,
            autoDetectedFields: autoDetectedFields.value,
            autoDetectedFieldsWithMetadata: autoDetectedFieldsWithMetadata.value,
            autoDetectedAdditionalFields: autoDetectedAdditionalFields.value,
            detectedCurrencies: detectedCurrencies.value,
            excludedDetectedFields: Array.from(excludedDetectedFields.value)
          })
        }

        saveSessionData()
      } else {
        const errorMsg = response?.message || response?.error || 'Unknown error'
        showSnackbar('Calculation failed: ' + errorMsg, 'error')
      }

      isUsingDetectedFields.value = false

      try {
        await enrichCalculationsWithFred()
      } catch (fredError) {
        console.error('FRED enrichment failed (non-critical):', fredError)
      }

      debouncedSave()
      forceUpdate.value++
    }
  } catch (err) {
    console.error('Error in calculation:', err)
    showSnackbar('Error calculating metrics: ' + (err.message || 'Unknown error'), 'error')
    isUsingDetectedFields.value = false
  } finally {
    isCalculating.value = false
  }
}

async function continueToVisualizations() {
  if (!hasCleanedData.value) {
    return
  }
  if (!allCalculations.value.totalValue) {
    await calculateMetrics()
  }
  await nextTick()
  activeTab.value = 'visualizations'
  await nextTick()
  forceUpdate.value++
  saveSessionData()
  const sid = activeSession.value?.id || sessionManager.getActiveSessionId()
  if (sid) {
    await markStepCompleted(String(sid), 'calculations')
  }
}

async function continueFromVisualizations() {
  if (!hasCleanedData.value) { return }
  saveSessionData()
  await nextTick()
  activeTab.value = 'summary'
  await nextTick()
  forceUpdate.value++
  const sid = activeSession.value?.id || sessionManager.getActiveSessionId()
  if (sid) {
    await markStepCompleted(String(sid), 'visualizations')
    await sessionManager.saveInstrumentWorkflow(sid, instrumentType.value, {
      rawData: rawData.value,
      cleanedData: cleanedData.value,
      calculations: calculations.value,
      allCalculations: allCalculations.value,
      selectedCalculations: selectedCalculations.value,
      columnMapping: columnMapping.value,
      worksheetStatus: worksheetStatus.value,
      workbookSheets: workbookSheets.value,
      instrumentSummary: instrumentSummary.value,
      portfolioSummary: portfolioSummary.value,
      completedInstrumentSummary: completedInstrumentSummary.value,
      completedPortfolioSummary: completedPortfolioSummary.value,
      yieldCurveData: yieldCurveData.value,
      fredFilters: { country: effectiveCountry.value, currency: effectiveCurrency.value, maturity: effectiveMaturity.value },
      uploadedFile: uploadedFile.value?.name || null,
      cleaningStats: cleaningStats.value,
      sessionSavedAt: sessionSavedAt.value || new Date().toISOString(),
      manualInputs: manualInputs.value,
      formulas: formulas.value
    })
    saveSessionData()
  }
}

const yieldCurveCache = new Map()
const CACHE_TTL = 15 * 60 * 1000

async function fetchYieldCurve() {
  const country = effectiveCountry.value
  const maturity = effectiveMaturity.value
  const currency = effectiveCurrency.value
  const from_date = yieldCurveStartDate.value || null
  const to_date = yieldCurveEndDate.value || null

  const normalizedCountry = country === 'USA' ? 'US' : 
                            country === 'GBR' ? 'GB' :
                            country === 'JPN' ? 'JP' :
                            country === 'CAN' ? 'CA' :
                            country === 'AUS' ? 'AU' :
                            country === 'CHE' ? 'CH' :
                            country === 'NZL' ? 'NZ' :
                            country === 'NOR' ? 'NO' :
                            country === 'SWE' ? 'SE' :
                            country === 'DNK' ? 'DK' :
                            country === 'BRA' ? 'BR' :
                            country === 'MEX' ? 'MX' :
                            country === 'IND' ? 'IN' :
                            country === 'CHN' ? 'CN' :
                            country === 'KOR' ? 'KR' :
                            country === 'SGP' ? 'SG' :
                            country === 'HKG' ? 'HK' :
                            country === 'RUS' ? 'RU' :
                            country === 'TUR' ? 'TR' :
                            country === 'SAU' ? 'SA' :
                            country === 'ARE' ? 'AE' :
                            country === 'ISR' ? 'IL' :
                            country === 'ZAF' ? 'ZA' : country

  const supportedCountries = ['US', 'GB', 'EUR', 'JP', 'CA', 'AU', 'CH', 'NZ', 'NO', 'SE', 'DK', 'BR', 'MX', 'IN', 'CN', 'KR', 'SG', 'HK', 'RU', 'TR', 'SA', 'AE', 'IL', 'ZA']
  if (!supportedCountries.includes(normalizedCountry) && country !== '__custom__') {
    yieldCurveError.value = `Unsupported country: ${country}. Please select a supported country.`
    yieldCurveData.value = []
    await nextTick()
    await renderYieldCurveChart()
    return
  }
  if (maturityMode.value === 'maturity' && !maturity) {
    yieldCurveError.value = 'Please select a maturity.'
    yieldCurveData.value = []
    await nextTick()
    await renderYieldCurveChart()
    return
  }
  if (maturityMode.value === 'dateRange' && (!from_date || !to_date)) {
    yieldCurveError.value = 'Please select both start and end dates.'
    yieldCurveData.value = []
    await nextTick()
    await renderYieldCurveChart()
    return
  }

  const cacheKey = `${instrumentType.value}_${normalizedCountry}_${currency}_${maturityMode.value}_${maturityMode.value === 'maturity' ? maturity : from_date + '_' + to_date}`
  const cached = yieldCurveCache.get(cacheKey)
  if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
    yieldCurveData.value = cached.data
    chartSeriesLabel.value = 'Yield Curve (cached)'
    yieldCurveError.value = ''
    await nextTick()
    await renderYieldCurveChart()
    updateFredBenchmark()
    debouncedSave()
    forceUpdate.value++
    return
  }

  yieldCurveLoading.value = true
  yieldCurveError.value = ''

  try {
    const payload = {
      instrument_type: instrumentType.value,
      country: normalizedCountry,
      currency: currency
    }
    if (maturityMode.value === 'maturity') {
      payload.maturity = maturity
    } else {
      payload.from_date = from_date
      payload.to_date = to_date
    }
    const response = await api.fredAPI.getYieldCurve(payload)

    if (response?.success && response.data) {
      const curveData = response.data
      if (curveData.maturities && curveData.maturities.length) {
        const points = curveData.maturities.map((m, idx) => ({
          maturity: parseFloat(m),
          maturityLabel: curveData.labels?.[idx] || m,
          rate: curveData.rates?.[idx] || 0,
          date: curveData.dates?.[idx] || null
        }))
        yieldCurveCache.set(cacheKey, { data: points, timestamp: Date.now() })
        yieldCurveData.value = points
        chartSeriesLabel.value = `FRED Yield Curve (${curveData.country || normalizedCountry})`
        yieldCurveError.value = ''
        console.log('Successfully loaded FRED yield curve data:', points.length, 'points')
      } else {
        yieldCurveData.value = []
        yieldCurveError.value = curveData.note || 'No yield curve data available for the selected filters.'
        chartSeriesLabel.value = ''
        console.warn('No FRED data available in response:', curveData)
      }
    } else {
      yieldCurveData.value = []
      yieldCurveError.value = response?.data?.note || response?.message || 'Failed to fetch yield curve from FRED'
      chartSeriesLabel.value = ''
      console.error('FRED API request failed:', response)
    }
  } catch (err) {
    console.error('Yield curve fetch error:', err)
    yieldCurveData.value = []
    yieldCurveError.value = err.message || 'Network error – please try again'
    chartSeriesLabel.value = ''
  } finally {
    yieldCurveLoading.value = false
    await nextTick()
    await renderYieldCurveChart()
    updateFredBenchmark()
    debouncedSave()
    forceUpdate.value++
  }
}

function updateFredBenchmark() {
  const benchRate = getRateForMaturity(effectiveMaturity.value)
  if (benchRate != null) {
    allCalculations.value.fred = {
      benchmark_rate: benchRate,
      series_label: effectiveMaturity.value,
      spread_vs_market: +(portfolioAvgRate.value - benchRate).toFixed(2),
      country: effectiveCountry.value,
      currency: effectiveCurrency.value,
      maturity: effectiveMaturity.value
    }
    calculations.value.fred = allCalculations.value.fred
  }
}

async function renderYieldCurveChart() {
  if (chartInstanceRef.current) {
    chartInstanceRef.current.destroy()
    chartInstanceRef.current = null
  }
  
  if (!yieldCurveChart.value || !yieldCurveData.value.length) {
    return
  }
  const rect = yieldCurveChart.value.getBoundingClientRect()
  if (rect.width === 0 || rect.height === 0) {
    setTimeout(() => renderYieldCurveChart(), 200)
    return
  }
  await nextTick()
  if (chartInstanceRef.current) {
    chartInstanceRef.current.destroy()
    chartInstanceRef.current = null
  }

  let transformed = []
  let xAxisType = 'linear'
  let xAxisTitle = 'Maturity'
  let xScaleOptions = {}

  if (maturityMode.value === 'dateRange') {
    xAxisType = 'time'
    xAxisTitle = 'Date'

    const dateFilteredData = yieldCurveData.value
      .filter(d => d.date !== null && d.date !== undefined)
      .sort((a, b) => new Date(a.date) - new Date(b.date))

    transformed = dateFilteredData.map(d => {
      const dateObj = new Date(d.date)
      return {
        x: dateObj.getTime(),
        y: d.rate,
        label: d.date,
        originalDate: d.date
      }
    })

    console.log('Date range mode data:', transformed.map(t => ({ 
      x: new Date(t.x).toISOString().split('T')[0], 
      y: t.y 
    })))

    xScaleOptions = {
      type: 'time',
      time: {
        unit: 'month',
        displayFormats: {
          month: 'MMM yyyy'
        }
      },
      title: { display: true, text: xAxisTitle },
      ticks: {
        maxRotation: 45,
        minRotation: 45
      }
    }
  } else {
    const period = effectiveMaturity.value
    let unitLabel = 'Years'
    let stepSize = 1
    let maxX = 0

    const match = period.match(/^(\d+)([YMW])$/)
    if (match) {
      const num = parseInt(match[1], 10)
      const unit = match[2]
      if (unit === 'Y') {
        unitLabel = 'Years'
        stepSize = num > 5 ? 5 : 1
        maxX = num + 0.5
      } else if (unit === 'M') {
        unitLabel = 'Months'
        stepSize = num > 6 ? 6 : 1
        maxX = num + 0.5
      } else if (unit === 'W') {
        unitLabel = 'Weeks'
        stepSize = num > 4 ? 2 : 1
        maxX = num + 0.5
      }
    } else {
      const num = parseFloat(period) || 10
      unitLabel = 'Years'
      stepSize = num > 5 ? 5 : 1
      maxX = num + 0.5
    }

    const filterYears = parseMaturityToYears(period)
    const filteredData = yieldCurveData.value.filter(d => d.maturity <= filterYears)

    if (!filteredData.length) {
      console.warn('No yield curve data points for selected maturity:', period)
      yieldCurveError.value = `No yield curve data available for maturity ${period}`
      if (chartInstanceRef.current) {
        chartInstanceRef.current.destroy()
        chartInstanceRef.current = null
      }
      return
    }

    transformed = filteredData.map(d => {
      let xVal = d.maturity
      if (unitLabel === 'Months') xVal = d.maturity * 12
      else if (unitLabel === 'Weeks') xVal = d.maturity * 52
      return { x: xVal, y: d.rate, label: d.maturityLabel }
    })

    xAxisTitle = unitLabel
    xScaleOptions = {
      type: 'linear',
      title: { display: true, text: xAxisTitle },
      min: 0,
      max: maxX,
      ticks: {
        callback: function(value) {
          const closest = filteredData.find(p => Math.abs(p.maturity - value) < 0.01)
          if (closest && closest.maturityLabel) {
            return closest.maturityLabel
          }
          if (Number.isInteger(value) && value >= 0) {
            return value.toString()
          }
          return null
        },
        stepSize: stepSize
      }
    }
  }

  const ctx = yieldCurveChart.value.getContext('2d')
  chartInstanceRef.current = new Chart(ctx, {
    type: 'line',
    data: {
      datasets: [{
        label: 'Yield (%)',
        data: transformed,
        borderColor: '#0B2044',
        backgroundColor: 'rgba(11,32,68,0.1)',
        fill: true,
        tension: 0.3,
        pointBackgroundColor: '#1E88E5',
        pointRadius: 5
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            title: (items) => {
              const pt = items[0]?.raw
              return pt?.label || ''
            },
            label: (ctx) => `Yield: ${ctx.parsed.y.toFixed(2)}%`
          }
        }
      },
      scales: {
        x: xScaleOptions,
        y: {
          title: { display: true, text: 'Yield (%)' },
          beginAtZero: false
        }
      }
    }
  })

  setTimeout(() => {
    if (yieldCurveChart.value) {
      try {
        chartImageData.value = yieldCurveChart.value.toDataURL('image/png', 1.0)
        console.log('Chart image captured successfully')
      } catch (e) {
        console.warn('Failed to capture chart image:', e)
      }
    }
  }, 1000)
}

function onCustomCountryInput() {
  selectedCountryOption.value = '__custom__'
  onFredFilterChange()
}

function onCustomCurrencyInput() {
  selectedCurrencyOption.value = '__custom__'
  onFredFilterChange()
}

function onCustomMaturityInput() {
  selectedMaturityOption.value = '__custom__'
  onFredFilterChange()
}

function onCountrySelectChange() {
  if (selectedCountryOption.value !== '__custom__') {
    fredFilters.value.country = selectedCountryOption.value
  } else {
    fredFilters.value.country = customCountryInput.value || ''
  }
  onFredFilterChange()
}

function onCurrencySelectChange() {
  if (selectedCurrencyOption.value !== '__custom__') {
    fredFilters.value.currency = selectedCurrencyOption.value
  } else {
    fredFilters.value.currency = customCurrencyInput.value || ''
  }
  onFredFilterChange()
}

function onMaturitySelectChange() {
  if (selectedMaturityOption.value !== '__custom__') {
    fredFilters.value.maturity = selectedMaturityOption.value
  } else {
    fredFilters.value.maturity = customMaturityInput.value || config.value.defaultMaturity
  }
  onFredFilterChange()
}

let fredFilterTimeout = null
async function onFredFilterChange() {
  if (fredFilterTimeout) clearTimeout(fredFilterTimeout)
  fredFilterTimeout = setTimeout(async () => {
    if (activeTab.value === 'visualizations') await fetchYieldCurve()
    if (Object.keys(allCalculations.value).length) await enrichCalculationsWithFred()
    debouncedSave()
  }, 500)
}

async function enrichCalculationsWithFred() {
  try {
    const bench = await fetchBenchmark(instrumentType.value)
    if (bench?.benchmark_rate != null) {
      const portfolio = parseFloat(portfolioAvgRate.value) || 0
      allCalculations.value.fred = {
        ...bench,
        spread_vs_market: +(portfolio - bench.benchmark_rate).toFixed(2)
      }
      calculations.value.fred = allCalculations.value.fred
    } else {
      if (allCalculations.value.fred) delete allCalculations.value.fred
      if (calculations.value.fred) delete calculations.value.fred
    }
  } catch (e) {
    console.error('FRED benchmark fetch error:', e)
  }
}

async function loadSavedTemplates() {
  try {
    console.log('Loading templates for instrument type:', instrumentType.value)
    const templates = await mappingTemplateManager.getTemplatesByInstrument(instrumentType.value)
    console.log('Loaded templates:', templates)
    savedTemplates.value = templates || []
  } catch (e) {
    console.error('Error loading saved templates:', e)
    savedTemplates.value = []
  }
}

async function saveTemplates() {
}

async function saveCurrentMappingAsTemplate() {
  if (!newTemplateName.value || !newTemplateName.value.trim()) {
    showSnackbar('Please enter a template name')
    return
  }

  try {
    let result
    if (currentMappingTemplateId.value) {
      result = await mappingTemplateManager.updateTemplate(currentMappingTemplateId.value, {
        columnMapping: columnMapping.value,
        fileColumns: fileColumns.value
      })
    } else {
      result = await mappingTemplateManager.saveTemplate(
        newTemplateName.value.trim(),
        instrumentType.value,
        columnMapping.value,
        requiredColumns.value,
        fileColumns.value
      )
    }

    if (result) {
      if (!currentMappingTemplateId.value) {
        currentMappingTemplateId.value = result.id
      }
      await loadSavedTemplates()
      newTemplateName.value = ''
      showSnackbar('Mapping saved successfully', 'success')
    } else {
      showSnackbar('Failed to save mapping')
    }
  } catch (e) {
    console.error('Error saving template:', e)
    showSnackbar('Error saving mapping: ' + e.message)
  }
}

async function applyTemplate(templateId) {
  if (!templateId) return
  try {
    const template = await mappingTemplateManager.getTemplate(templateId)
    if (!template) {
      showSnackbar('Failed to load template')
      return
    }
    columnMapping.value = { ...template.column_mapping }
    if (template.file_columns) {
      fileColumns.value = [...template.file_columns]
    }
    currentMappingTemplateId.value = template.id
    applyCurrentMapping()
    debouncedSave()
    forceUpdate.value++
    showSnackbar('Mapping loaded successfully', 'success')
  } catch (e) {
    console.error('Error loading template:', e)
    showSnackbar('Error loading mapping')
  }
}

async function deleteTemplate(templateId) {
  if (!templateId) return
  const template = savedTemplates.value.find(t => t.id === templateId)
  if (!template) return
  
  if (confirm(`Delete template "${template.name}"?`)) {
    try {
      const success = await mappingTemplateManager.deleteTemplate(templateId)
      if (success) {
        await loadSavedTemplates()
        if (currentMappingTemplateId.value === templateId) {
          currentMappingTemplateId.value = null
        }
        showSnackbar('Mapping deleted successfully', 'success')
      } else {
        showSnackbar('Failed to delete mapping')
      }
    } catch (e) {
      console.error('Error deleting template:', e)
      showSnackbar('Error deleting mapping')
    }
  }
}

async function loadTemplateFromPopup(templateId) {
  await applyTemplate(templateId)
  showSavedMappingsDialog.value = false
}

async function deleteTemplateFromPopup(templateId) {
  await deleteTemplate(templateId)
}

function selectInstrumentFromPopup(index) {
  if (index < 0 || index >= instrumentSummary.value.rows.length) {
    selectedCalculationInstrument.value = -1
    currentlyViewingInstrument.value = null
    return
  }
  selectedCalculationInstrument.value = index
  const selectedRow = instrumentSummary.value.rows[index]
  const instrumentName = selectedRow['Instrument Name'] || `Instrument ${index + 1}`
  currentlyViewingInstrument.value = instrumentName

  const newCalculations = {}
  Object.keys(selectedRow).forEach(key => {
    const val = parseFloat(selectedRow[key])
    if (!isNaN(val)) {
      newCalculations[key] = val
    }
  })

  if (!newCalculations.totalValue) newCalculations.totalValue = parseFloat(selectedRow['Total Value'] || selectedRow['total_value'] || 0)
  if (!newCalculations.instrumentCount) newCalculations.instrumentCount = parseFloat(selectedRow['Instrument Count'] || selectedRow['instrument_count'] || 1)

  selectedCalculations.value = newCalculations
  calculations.value = newCalculations
  console.log('Loaded instrument calculations:', instrumentName, newCalculations)
  closeAllCalculationsPopup()
}

function loadAllInstruments() {
  if (!instrumentSummary.value.rows.length) {
    return
  }
  if (allCalculations.value.totalValue !== undefined) {
    selectedCalculations.value = allCalculations.value
    calculations.value = allCalculations.value
  } else {
    console.error('No backend aggregate data available in allCalculations')
    showSnackbar('No calculation data available. Please recalculate.', 'error')
  }
  currentlyViewingInstrument.value = null
  closeAllCalculationsPopup()
  saveSessionData()
}

function formatTableCell(value, column) {
  if (value === null || value === undefined || value === '') return '—'
  
  const isTimeField = column.toLowerCase().includes('day') || column.toLowerCase().includes('maturity') || column.toLowerCase().includes('duration') || column.toLowerCase().includes('term') || column.toLowerCase().includes('month') || column.toLowerCase().includes('year') || column.toLowerCase().includes('week') || column.toLowerCase().includes('time')
  
  if (isTimeField && typeof value === 'number') {
    return formatNumber(value, true)
  }
  
  if (isPercentageField(column)) {
    return formatNumber(value) + '%'
  }
  if (column.toLowerCase().includes('value') || column.toLowerCase().includes('amount') || column.toLowerCase().includes('price')) {
    return formatNumber(value)
  }
  if (column.toLowerCase().includes('date') && typeof value === 'string') {
    return value
  }
  return typeof value === 'number' ? formatNumber(value) : value
}

function openAllCalculationsPopup() {
  showAllCalculationsPopup.value = true
}

function closeAllCalculationsPopup() {
  showAllCalculationsPopup.value = false
}

function exportAllCalculations() {
  const allData = completedInstrumentSummary.value.rows || instrumentSummary.value.rows
  if (!allData.length) { return }

  const displayCols = getDisplayColumns()
  const data = allData.map(row => {
    const obj = {}
    displayCols.forEach(col => {
      let val = row[col] !== undefined ? row[col] : ''
      if (isPercentageField(col)) {
        val = formatForExcel(val, 'percentage', col)
      } else if (col.toLowerCase().includes('value') || col.toLowerCase().includes('price') || col.toLowerCase().includes('amount') || col.toLowerCase().includes('principal') || col.toLowerCase().includes('interest')) {
        val = formatForExcel(val, 'money', col)
      } else {
        val = formatForExcel(val, 'number', col)
      }
      obj[col] = val
    })
    return obj
  })

  const wb = XLSX.utils.book_new()
  const ws = XLSX.utils.json_to_sheet(data)
  XLSX.utils.book_append_sheet(wb, ws, 'Calculated Instruments')

  const summaryRows = [
    ['Instrument Summary'],
    ['Total Instruments', allData.length],
    ['Total Value', formatForExcel(allCalculations.value.totalValue, 'money', 'Total Value')],
    ['Average Rate', formatForExcel(allCalculations.value.avgRate, 'percentage', 'Average Rate')],
    ['Weighted Average Rate', formatForExcel(allCalculations.value.weightedAvgRate, 'percentage', 'Weighted Average Rate')]
  ]
  const summaryWs = XLSX.utils.aoa_to_sheet(summaryRows)
  XLSX.utils.book_append_sheet(wb, summaryWs, 'Summary')

  XLSX.writeFile(wb, 'all_instruments_calculations.xlsx')
}

function notifySessionUpdated(explicitSave = false, saveOptions = {}) {
  if (!activeSession.value) return
  const sid = activeSession.value.id
  window.dispatchEvent(new CustomEvent('session-updated', { detail: { sessionId: sid, explicitSave, ...saveOptions } }))
}

const isSaving = ref(false)
const skipAutoSave = ref(false)

const previousSnapshot = ref(null)

function generateVersionDescription(newSnapshot, oldSnapshot) {
  const changes = []
  
  if (!oldSnapshot) {
    return `Initial ${instrumentType.value} workflow setup`
  }
  
  if (JSON.stringify(newSnapshot.rawData) !== JSON.stringify(oldSnapshot.rawData)) {
    changes.push('uploaded new data')
  }
  
  if (JSON.stringify(newSnapshot.cleanedData) !== JSON.stringify(oldSnapshot.cleanedData)) {
    changes.push('cleaned data')
  }
  
  if (JSON.stringify(newSnapshot.calculations) !== JSON.stringify(oldSnapshot.calculations)) {
    changes.push('recalculated metrics')
  }
  
  if (JSON.stringify(newSnapshot.columnMapping) !== JSON.stringify(oldSnapshot.columnMapping)) {
    changes.push('updated column mapping')
  }
  
  if (JSON.stringify(newSnapshot.manualInputs) !== JSON.stringify(oldSnapshot.manualInputs)) {
    changes.push('updated manual inputs')
  }
  
  if (JSON.stringify(newSnapshot.formulas) !== JSON.stringify(oldSnapshot.formulas)) {
    changes.push('updated formulas')
  }
  
  if (changes.length === 0) {
    return `Saved ${instrumentType.value} workflow (no changes)`
  }
  
  const changeText = changes.join(', ')
  return `${instrumentType.value} — ${changeText}`
}

async function saveToSession() {
  if (isSavingVersion) {
    console.log('Version save already in progress, ignoring duplicate click')
    return
  }
  
  isSavingVersion = true
  isSaving.value = true
  skipAutoSave.value = true
  
  if (!activeSession.value || !activeSession.value.id) {
    isSavingVersion = false
    isSaving.value = false
    skipAutoSave.value = false
    return
  }

  const sid = activeSession.value.id
  const worksheetName = currentSheetName.value || 'Unknown'

  try {
    console.log('Fetching current version count from database...')
    const currentVersionsRes = await api.versionAPI.getVersions(sid)
    if (currentVersionsRes && currentVersionsRes.success) {
      const actualCount = currentVersionsRes.total || 0
      console.log(`Actual version count from database: ${actualCount}`)
      if (activeSession.value?.id === sid) {
        activeSession.value.version_count = actualCount
      }
    }

    const datasetSnapshot = {
      rawData: rawData.value,
      cleanedData: cleanedData.value,
      calculations: calculations.value,
      allCalculations: allCalculations.value,
      selectedCalculations: selectedCalculations.value,
      columnMapping: columnMapping.value,
      worksheetStatus: worksheetStatus.value,
      workbookSheets: workbookSheets.value,
      instrumentSummary: instrumentSummary.value,
      portfolioSummary: portfolioSummary.value,
      yieldCurveData: yieldCurveData.value,
      fredFilters: { country: effectiveCountry.value, currency: effectiveCurrency.value, maturity: effectiveMaturity.value },
      manualInputs: manualInputs.value,
      formulas: formulas.value,
      uploadedFile: uploadedFile.value?.name || null,
      cleaningStats: cleaningStats.value,
      sessionSavedAt: new Date().toISOString(),
      instrumentType: instrumentType.value,
      sheetType: sheetType.value
    }

    console.log('Saving worksheet data for:', worksheetName)
    const worksheetData = {
      worksheetName,
      workbookName: uploadedFile.value?.name || 'Workbook',
      instrumentType: instrumentType.value,
      sheetType: sheetType.value,
      rawData: rawData.value,
      cleanedData: cleanedData.value,
      calculations: calculations.value,
      allCalculations: allCalculations.value,
      selectedCalculations: selectedCalculations.value,
      columnMapping: columnMapping.value,
      instrumentSummary: instrumentSummary.value,
      extractedValues: extractedValues.value,
      timestamp: Date.now()
    }
    await sessionManager.saveWorksheetData(sid, worksheetName, worksheetData)
    console.log('Worksheet data saved successfully')
    
    markWorksheetAsSaved()

    console.log('Step 1: Saving workflow data...')
    await sessionManager.saveInstrumentWorkflow(sid, instrumentType.value, datasetSnapshot)
    console.log('Step 1 complete: Workflow data saved')
    
    console.log('Step 2: Updating instrument count...')
    const count = sessionManager.countSessionInstruments(sid)
    await sessionManager.updateSession(sid, { instrument_count: Math.min(count, 3) })
    
    if (activeSession.value?.id === sid) {
      activeSession.value.instrument_count = Math.min(count, 3)
    }
    console.log('Step 2 complete: Instrument count updated to:', Math.min(count, 3))
    
    console.log('Step 3: Creating version via API...')
    
    const versionDescription = generateVersionDescription(datasetSnapshot, previousSnapshot.value)
    console.log('Generated version description:', versionDescription)
    
    const versionResponse = await api.versionAPI.create(
      sid,
      instrumentType.value,
      versionDescription,
      datasetSnapshot,
      null, null, null, null, null
    )
    
    console.log('Version API response:', versionResponse)
    
    if (!versionResponse?.success) {
      console.error('❌ Version creation failed:', versionResponse)
      showSnackbar('Failed to create version', 'error')
    } else {
      console.log('✅ Version created successfully, ID:', versionResponse?.version_id || versionResponse?.data?.id)
      
      previousSnapshot.value = JSON.parse(JSON.stringify(datasetSnapshot))
      
      console.log('Step 4: Fetching updated version count from backend...')
      try {
        const versionsRes = await api.versionAPI.getVersions(sid)
        console.log('Get versions response:', versionsRes)
        if (versionsRes && versionsRes.success) {
          const updatedVersionCount = versionsRes.total || 0
          console.log(`✅ Updated version count from backend: ${updatedVersionCount}`)
          
          const session = sessionManager.sessions.find(s => s.id === sid)
          if (session) {
            session.version_count = updatedVersionCount
            if (versionsRes.data && versionsRes.data.length > 0) {
              const sortedData = [...versionsRes.data].sort((a, b) => (b.versionNumber || 0) - (a.versionNumber || 0))
              session.versions = sortedData.map(v => ({
                id: v.id,
                versionNumber: v.versionNumber,
                timestamp: v.timestamp || v.created_at,
                changeSummary: v.changeSummary || v.change_summary || 'No description',
                instrumentType: v.instrumentType || v.instrument_type || 'General',
                changeType: v.changeType || 'Saved',
                changeTypeClass: v.changeTypeClass || 'badge-saved',
                modifiedInstruments: v.modifiedInstruments || [],
                fieldsChanged: v.fieldsChanged || []
              }))
            }
            
            if (activeSession.value?.id === sid) {
              activeSession.value.version_count = updatedVersionCount
              if (versionsRes.data && versionsRes.data.length > 0) {
                activeSession.value.versions = session.versions
              }
            }
          }

        }
      } catch (fetchError) {
        console.warn('Failed to fetch updated versions:', fetchError)
      }
    }
  } catch (err) {
    console.error('❌ Save to session error:', err)
    showSnackbar('Failed to save to session: ' + err.message, 'error')
  } finally {
    isSavingVersion = false
    isSaving.value = false
    setTimeout(() => {
      skipAutoSave.value = false
      console.log('Skip auto-save flag reset')
    }, 3000)
    console.log('isSavingVersion and isSaving flags reset to false')
  }
}

function debouncedSave(explicitSave = false) {
  if (saveTimeout) clearTimeout(saveTimeout)
  const now = Date.now()
  if (!explicitSave && now - lastSaveTime < SAVE_DEBOUNCE_MS) return
  saveTimeout = setTimeout(() => {
    saveSessionData(explicitSave)
    lastSaveTime = Date.now()
  }, explicitSave ? 100 : SAVE_DEBOUNCE_MS)
}

async function refreshSessionVersionCount(sid) {
  try {
    const updated = await sessionManager.getSession(sid, true)
    if (updated && updated.id && activeSession.value?.id === sid) {
      activeSession.value = updated
    } else if (!updated?.id) {
      console.warn('Session refresh returned invalid session (no ID), keeping current session')
    } else {
      console.warn('Session refresh condition failed: updated?', !!updated, 'activeSession.value?.id === sid?', activeSession.value?.id === sid)
    }
  } catch (err) {
    console.warn('Failed to refresh session count:', err)
  }
}

function saveSessionData(explicitSave = false) {
  if (!activeSession.value) return
  const sid = activeSession.value.id
  const datasetSnapshot = {
    rawData: rawData.value,
    cleanedData: cleanedData.value,
    calculations: calculations.value,
    allCalculations: allCalculations.value,
    selectedCalculations: selectedCalculations.value,
    columnMapping: columnMapping.value,
    worksheetStatus: worksheetStatus.value,
    workbookSheets: workbookSheets.value,
    instrumentSummary: instrumentSummary.value,
    portfolioSummary: portfolioSummary.value,
    completedInstrumentSummary: completedInstrumentSummary.value,
    completedPortfolioSummary: completedPortfolioSummary.value,
    yieldCurveData: yieldCurveData.value,
    fredFilters: { country: effectiveCountry.value, currency: effectiveCurrency.value, maturity: effectiveMaturity.value },
    uploadedFile: uploadedFile.value?.name || null,
    cleaningStats: cleaningStats.value,
    sessionSavedAt: sessionSavedAt.value || new Date().toISOString(),
    manualInputs: manualInputs.value,
    formulas: formulas.value,
    isCalculating: isCalculating.value,
    autoDetectedFields: autoDetectedFields.value,
    autoDetectedFieldsWithMetadata: autoDetectedFieldsWithMetadata.value,
    autoDetectedAdditionalFields: autoDetectedAdditionalFields.value,
    detectedCurrencies: detectedCurrencies.value,
    excludedDetectedFields: Array.from(excludedDetectedFields.value)
  }
  
  sessionManager.setActiveSession(activeSession.value)
  
  sessionManager.saveInstrumentWorkflow(sid, instrumentType.value, datasetSnapshot)
    .then(() => {
      if (explicitSave) {
        const count = sessionManager.countSessionInstruments(sid)
        sessionManager.updateSession(sid, { instrument_count: Math.min(count, 3) })
      }
    })
    .catch(err => console.error('Failed to save workflow:', err))
}

async function loadSavedData() {
  if (!activeSession.value) return false
  const sid = activeSession.value.id
  let loaded = false
  try {
    const wf = await sessionManager.getInstrumentWorkflow(sid, instrumentType.value)
    if (wf) {
      rawData.value = wf.rawData || []
      cleanedData.value = wf.cleanedData || []
      calculations.value = wf.calculations || {}
      allCalculations.value = wf.allCalculations || wf.calculations || {}
      selectedCalculations.value = wf.selectedCalculations || wf.calculations || {}
      columnMapping.value = wf.columnMapping || {}
      worksheetStatus.value = wf.worksheetStatus || {}
      workbookSheets.value = wf.workbookSheets || []
      instrumentSummary.value = wf.instrumentSummary || { rows: [], columns: [] }
      portfolioSummary.value = wf.portfolioSummary || { rows: [], columns: [] }
      completedInstrumentSummary.value = wf.completedInstrumentSummary || { rows: [], columns: [] }
      completedPortfolioSummary.value = wf.completedPortfolioSummary || { rows: [], columns: [] }
      yieldCurveData.value = wf.yieldCurveData || []
      manualInputs.value = wf.manualInputs || {}
      formulas.value = wf.formulas || {}
      isCalculating.value = wf.isCalculating || false
      if (wf.fredFilters) {
        selectedCountryOption.value = wf.fredFilters.country || ''
        selectedCurrencyOption.value = wf.fredFilters.currency || ''
        selectedMaturityOption.value = wf.fredFilters.maturity || config.value.defaultMaturity
      }
      if (wf.uploadedFile) {
        uploadedFile.value = { name: wf.uploadedFile, size: 0 }
      }
      if (wf.cleaningStats) cleaningStats.value = wf.cleaningStats
      if (wf.sessionSavedAt) sessionSavedAt.value = wf.sessionSavedAt

      if (wf.autoDetectedFields) {
        autoDetectedFields.value = wf.autoDetectedFields
        console.log('Restored autoDetectedFields from session:', Object.keys(autoDetectedFields.value).length)
      }
      if (wf.autoDetectedFieldsWithMetadata) {
        autoDetectedFieldsWithMetadata.value = wf.autoDetectedFieldsWithMetadata
      }
      if (wf.autoDetectedAdditionalFields) {
        autoDetectedAdditionalFields.value = wf.autoDetectedAdditionalFields
      }
      if (wf.detectedCurrencies) {
        detectedCurrencies.value = wf.detectedCurrencies
      }
      if (wf.excludedDetectedFields && Array.isArray(wf.excludedDetectedFields)) {
        excludedDetectedFields.value = new Set(wf.excludedDetectedFields)
        console.log('Restored excludedDetectedFields from session:', Array.from(excludedDetectedFields.value))
      }

      loaded = true
    }
  } catch (err) {
    console.error('Failed to load saved data:', err)
  }
  return loaded
}

function showFormula(metricKey) {
  const formulaMap = {
    'Total Portfolio Value': 'Σ Principal for all instruments',
    'Average Rate': 'Σ (Interest Rate × Principal) / Σ Principal',
    'Number of Instruments': 'Count of all instrument rows',
    'weightedAvgRate': 'Σ (Interest Rate × Principal) / Σ Principal',
    'totalInterest': 'Σ (Principal × Interest Rate × Days/360)',
    'interestEarned': 'Σ (Principal × Interest Rate × Days/360)',
    'annualYield': '(Interest / Principal) × (365 / Days) × 100',
    'effectiveAnnualRate': '(Interest / Principal) × (365 / Days) × 100',
    'avgDaysToMaturity': 'Σ Days / Number of Instruments',
    'totalPrincipal': 'Σ Principal',
    'weightedAvgDiscount': 'Σ (Discount Rate × Face Value) / Σ Face Value',
    'totalDiscount': 'Σ ((Face Value - Purchase Price) / Face Value × Face Value)',
    'effectiveYield': '((Face Value / Purchase Price)^(365/Days) - 1) × 100',
    'bondEquivalentYield': '((Face Value - Purchase Price) / Purchase Price) × (365 / Days) × 100',
    'pricePer100': 'Purchase Price / Face Value × 100',
    'totalPurchasePrice': 'Σ Purchase Price',
    'avgInvestment': 'Total Purchase Price / Number of Instruments',
    'holdingPeriodYield': '((Face Value - Purchase Price) / Purchase Price) × 100',
    'annualizedYield': '((Face Value - Purchase Price) / Purchase Price) × (365 / Days) × 100',
    'weightedAvgCoupon': 'Σ (Coupon Rate × Face Value) / Σ Face Value',
    'totalAnnualIncome': 'Σ (Coupon Rate × Face Value)',
    'avgYTM': 'Σ Yield to Maturity / Number of Instruments',
    'duration': 'Macaulay Duration = Σ (t × PV(C_t)) / Price',
    'totalValue': 'Σ of all calculated values',
    'interestRate': 'Interest rate as percentage',
    'discountYield': '(Discount Amount / Face Value) × (360 / Days) × 100',
    'moneyMarketYield': '(Discount Amount / Purchase Price) × (360 / Days) × 100',
    'effectiveAnnualYield': '((Face Value / Purchase Price)^(365/Days) - 1) × 100',
    'currentPrice': 'Market price of the bond',
    'couponRate': 'Annual coupon rate as percentage',
    'yieldToMaturity': 'Internal rate of return',
    'currentYield': '(Annual Coupon / Price) × 100',
    'modifiedDuration': 'Macaulay Duration / (1 + YTM/Frequency)',
    'accruedInterest': 'Coupon per Period × (Days Accrued / Days in Period)',
    'presentValue': 'Σ (Cash Flow / (1 + YTM/Frequency)^t)',
    'fairValue': 'Present Value - Purchase Price',
    'termDays': 'Days from valuation to maturity',
    'yieldCurveRate': 'Benchmark rate from FRED API'
  }
  formulaText.value = formulaMap[metricKey] || 'No formula available for this metric.'
  
  const agg = allCalculations.value || {}
  const calc = calculations.value || {}
  const details = []
  
  const getValue = (key) => {
    // Direct key lookup
    let value = calc[key] || agg[key]
    
    // Try snake_case variant
    if (value === undefined || value === null) {
      const snake = toSnakeCase(key)
      value = calc[snake] || agg[snake]
    }
    
    // Try camelCase variant  
    if (value === undefined || value === null) {
      const camel = toCamelCase(key)
      value = calc[camel] || agg[camel]
    }
    
    // For specific aggregates, try common variations
    if (value === undefined || value === null) {
      const variations = {
        'totalPrincipal': ['total_principal', 'totalPrincipal'],
        'totalInterest': ['total_interest', 'totalInterest'],
        'totalValue': ['total_value', 'totalValue'],
        'interestEarned': ['interest_earned', 'interestEarned'],
        'avgRate': ['avg_rate', 'avgRate'],
        'weightedAvgRate': ['weighted_avg_rate', 'weightedAvgRate'],
        'avgDaysToMaturity': ['avg_days_to_maturity', 'avgDaysToMaturity'],
        'totalPrincipal': ['total_principal', 'totalPrincipal'],
        'totalPurchasePrice': ['total_purchase_price', 'totalPurchasePrice'],
        'totalDiscount': ['total_discount', 'totalDiscount'],
        'avgYTM': ['avg_ytm', 'avgYTM'],
        'avgDuration': ['avg_duration', 'avgDuration'],
        'weightedAvgCoupon': ['weighted_avg_coupon', 'weightedAvgCoupon'],
        'totalCouponIncome': ['total_coupon_income', 'totalAnnualIncome'],
        'totalAnnualIncome': ['total_coupon_income', 'totalAnnualIncome'],
        'weightedAvgDiscount': ['weighted_avg_discount', 'weightedAvgDiscount'],
        'avgInvestment': ['avg_investment', 'avgInvestment'],
        'annualizedYield': ['annualized_yield', 'annualizedYield'],
        'effectiveYield': ['effective_yield', 'effectiveYield'],
        'effectiveAnnualRate': ['effective_annual_rate', 'effectiveAnnualRate'],
        'bondEquivalentYield': ['bond_equivalent_yield', 'bondEquivalentYield'],
        'discountYield': ['discount_yield', 'discountYield'],
        'moneyMarketYield': ['money_market_yield', 'moneyMarketYield'],
        'currentYield': ['current_yield', 'currentYield'],
        'modifiedDuration': ['modified_duration', 'modifiedDuration'],
        'yieldToMaturity': ['yield_to_maturity', 'yieldToMaturity', 'ytm'],
        'couponRate': ['coupon_rate', 'couponRate'],
        'faceValue': ['face_value', 'faceValue'],
        'purchasePrice': ['purchase_price', 'purchasePrice'],
        'currentPrice': ['current_price', 'currentPrice', 'price'],
        'presentValue': ['present_value', 'presentValue'],
        'fairValue': ['fair_value', 'fairValue'],
        'maturityValue': ['maturity_value', 'maturityValue'],
        'yieldCurveRate': ['yield_curve_rate', 'yieldCurveRate', 'benchmark_rate'],
        'termDays': ['term_days', 'termDays'],
        'daysToMaturity': ['days_to_maturity', 'daysToMaturity'],
        'pricePer100': ['price_per_100', 'pricePer100'],
        'holdingPeriodYield': ['holding_period_yield', 'holdingPeriodYield'],
        'daysAccrued': ['days_accrued', 'daysAccrued'],
        'couponPerPeriod': ['coupon_per_period', 'couponPerPeriod'],
        'principal': ['principal', 'principal'],
        'interestRate': ['interest_rate', 'interestRate'],
        'dayCount': ['day_count_convention', 'dayCount'],
        'frequency': ['coupon_frequency', 'frequency'],
        'yearsToMaturity': ['years_to_maturity', 'yearsToMaturity']
      }
      
      for (const variant of variations[key] || []) {
        value = calc[variant] || agg[variant]
        if (value !== undefined && value !== null) break
      }
    }
    
    return value !== undefined && value !== null ? value : null
  }
  
  const formatValue = (val) => {
    if (val === null || val === undefined) return 'N/A'
    if (typeof val === 'number') {
      if (val > 10000) return val.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
      return val.toFixed(4)
    }
    return val
  }
  
  const toSnakeCase = (str) => str.replace(/[A-Z]/g, letter => `_${letter.toLowerCase()}`)
  
  const toCamelCase = (str) => str.replace(/_([a-z])/g, (_, letter) => letter.toUpperCase())
  
  if (metricKey === 'interestEarned' || metricKey === 'totalInterest') {
    const principal = getValue('principal') || getValue('totalPrincipal') || getValue('total_principal')
    const rate = getValue('interestRate') || getValue('interest_rate') || getValue('avgRate') || getValue('avg_rate')
    const days = getValue('termDays') || getValue('term_days') || getValue('avgDaysToMaturity') || getValue('avg_days_to_maturity')
    const dayCount = getValue('dayCount') || getValue('day_count_convention') || 'ACT/360'
    const divisor = dayCount.includes('360') ? 360 : 365
    const interest = principal * (rate / 100) * (days / divisor)
    
    details.push({ label: 'Principal', value: formatValue(principal), formula: 'Principal amount invested' })
    details.push({ label: 'Interest Rate', value: formatValue(rate) + '%', formula: 'Annual interest rate' })
    details.push({ label: 'Term Days', value: formatValue(days), formula: 'Days to maturity' })
    details.push({ label: 'Answer (Interest Earned)', value: formatValue(interest), formula: 'Final calculated interest' })
    
    details.breakdown = {
      title: 'Formula Component Breakdown',
      components: [
        { componentName: 'Principal Component', calculation: formatValue(principal), formula: 'Principal amount' },
        { componentName: 'Rate Component', calculation: formatValue(rate) + '% (as decimal: ' + formatValue(rate/100) + ')', formula: 'Interest rate' },
        { componentName: 'Time Component (Days/Divisor)', calculation: formatValue(days) + '/' + divisor + ' = ' + formatValue(days/divisor), formula: 'Time fraction' },
        { componentName: 'Full Calculation (Principal × Rate × Days/Divisor)', calculation: `${formatValue(principal)} × ${formatValue(rate/100)} × ${formatValue(days/divisor)} = ${formatValue(interest)}`, formula: 'Principal × Rate × (Days/Divisor)' }
      ]
    }
  }
  
  else if (metricKey === 'discountYield') {
    const face = getValue('faceValue') || getValue('face_value') || getValue('totalFaceValue') || getValue('total_face_value')
    const purchase = getValue('purchasePrice') || getValue('purchase_price') || getValue('totalPurchasePrice') || getValue('total_purchase_price')
    const days = getValue('termDays') || getValue('term_days') || getValue('avgDaysToMaturity') || getValue('avg_days_to_maturity')
    const discount = face - purchase
    const dayCount = getValue('dayCount') || getValue('day_count_convention') || 'ACT/360'
    const divisor = dayCount.includes('360') ? 360 : 365
    const discountYield = (discount / face) * (divisor / days) * 100
    
    details.push({ label: 'Face Value', value: formatValue(face), formula: 'Maturity value' })
    details.push({ label: 'Purchase Price', value: formatValue(purchase), formula: 'Price paid' })
    details.push({ label: 'Term Days', value: formatValue(days), formula: 'Days to maturity' })
    details.push({ label: 'Answer (Discount Yield)', value: formatValue(discountYield) + '%', formula: 'Final discount yield' })
    
    details.breakdown = {
      title: 'Formula Component Breakdown',
      components: [
        { componentName: 'Face Value Component', calculation: formatValue(face), formula: 'Maturity value' },
        { componentName: 'Purchase Price Component', calculation: formatValue(purchase), formula: 'Price paid' },
        { componentName: 'Discount Amount Component (Face Value - Purchase Price)', calculation: `${formatValue(face)} - ${formatValue(purchase)} = ${formatValue(discount)}`, formula: 'Face Value - Purchase Price' },
        { componentName: 'Discount Yield Calculation ((Discount / Face) × (Divisor / Days) × 100)', calculation: `(${formatValue(discount)} / ${formatValue(face)}) × (${divisor} / ${formatValue(days)}) × 100 = ${formatValue(discountYield)}%`, formula: '(Discount / Face) × (Divisor / Days) × 100' }
      ]
    }
  }
  
  else if (metricKey === 'bondEquivalentYield') {
    const face = getValue('faceValue') || getValue('face_value') || getValue('totalFaceValue') || getValue('total_face_value')
    const purchase = getValue('purchasePrice') || getValue('purchase_price') || getValue('totalPurchasePrice') || getValue('total_purchase_price')
    const days = getValue('termDays') || getValue('term_days') || getValue('avgDaysToMaturity') || getValue('avg_days_to_maturity')
    const discount = face - purchase
    const bey = (discount / purchase) * (365 / days) * 100
    
    details.push({ label: 'Face Value', value: formatValue(face), formula: 'Maturity value' })
    details.push({ label: 'Purchase Price', value: formatValue(purchase), formula: 'Price paid' })
    details.push({ label: 'Term Days', value: formatValue(days), formula: 'Days to maturity' })
    details.push({ label: 'Answer (Bond Equivalent Yield)', value: formatValue(bey) + '%', formula: 'Final BEY' })
    
    details.breakdown = {
      title: 'Formula Component Breakdown',
      components: [
        { componentName: 'Face Value Component', calculation: formatValue(face), formula: 'Maturity value' },
        { componentName: 'Purchase Price Component', calculation: formatValue(purchase), formula: 'Price paid' },
        { componentName: 'Discount Amount Component (Face Value - Purchase Price)', calculation: `${formatValue(face)} - ${formatValue(purchase)} = ${formatValue(discount)}`, formula: 'Face Value - Purchase Price' },
        { componentName: 'BEY Calculation ((Discount / Purchase) × (365 / Days) × 100)', calculation: `(${formatValue(discount)} / ${formatValue(purchase)}) × (365 / ${formatValue(days)}) × 100 = ${formatValue(bey)}%`, formula: '(Discount / Purchase) × (365 / Days) × 100' }
      ]
    }
  }
  
  else if (metricKey === 'currentYield') {
    const price = getValue('currentPrice') || getValue('current_price') || getValue('price')
    const couponRate = getValue('couponRate') || getValue('coupon_rate')
    const face = getValue('faceValue') || getValue('face_value') || 100000
    const annualCoupon = face * (couponRate / 100)
    const currentYield = (annualCoupon / price) * 100
    
    details.push({ label: 'Face Value', value: formatValue(face), formula: 'Par value' })
    details.push({ label: 'Coupon Rate', value: formatValue(couponRate) + '%', formula: 'Annual coupon rate' })
    details.push({ label: 'Current Price', value: formatValue(price), formula: 'Market price' })
    details.push({ label: 'Answer (Current Yield)', value: formatValue(currentYield) + '%', formula: 'Final current yield' })
    
    details.breakdown = {
      title: 'Formula Component Breakdown',
      components: [
        { componentName: 'Face Value Component', calculation: formatValue(face), formula: 'Par value' },
        { componentName: 'Coupon Rate Component', calculation: formatValue(couponRate) + '% (as decimal: ' + formatValue(couponRate/100) + ')', formula: 'Annual coupon rate' },
        { componentName: 'Annual Coupon Component (Face Value × Coupon Rate)', calculation: `${formatValue(face)} × ${formatValue(couponRate/100)} = ${formatValue(annualCoupon)}`, formula: 'Face Value × Coupon Rate' },
        { componentName: 'Current Yield Calculation ((Annual Coupon / Price) × 100)', calculation: `(${formatValue(annualCoupon)} / ${formatValue(price)}) × 100 = ${formatValue(currentYield)}%`, formula: '(Annual Coupon / Price) × 100' }
      ]
    }
  }
  
  else if (metricKey === 'accruedInterest') {
    const couponRate = getValue('couponRate') || getValue('coupon_rate')
    const frequency = getValue('frequency') || getValue('coupon_frequency') || 2
    const face = getValue('faceValue') || getValue('face_value') || 100000
    const dayCount = getValue('dayCount') || getValue('day_count_convention') || 'ACT/365'
    const daysAccrued = getValue('daysAccrued') || getValue('days_accrued') || 45
    const divisor = dayCount.includes('360') ? 360 : 365
    const couponPerPeriod = face * (couponRate / 100) / frequency
    const daysInPeriod = divisor / frequency
    const accrued = couponPerPeriod * (daysAccrued / daysInPeriod)
    
    details.push({ label: 'Face Value', value: formatValue(face), formula: 'Par value' })
    details.push({ label: 'Coupon Rate', value: formatValue(couponRate) + '%', formula: 'Annual coupon rate' })
    details.push({ label: 'Coupon Frequency', value: frequency, formula: 'Payments per year' })
    details.push({ label: 'Answer (Accrued Interest)', value: formatValue(accrued), formula: 'Final accrued interest' })
    
    details.breakdown = {
      title: 'Formula Component Breakdown',
      components: [
        { componentName: 'Face Value Component', calculation: formatValue(face), formula: 'Par value' },
        { componentName: 'Coupon Rate Component', calculation: formatValue(couponRate) + '% (as decimal: ' + formatValue(couponRate/100) + ')', formula: 'Annual coupon rate' },
        { componentName: 'Coupon per Period Component (Annual Coupon / Frequency)', calculation: `${formatValue(face * (couponRate/100))} / ${frequency} = ${formatValue(couponPerPeriod)}`, formula: 'Annual Coupon / Frequency' },
        { componentName: 'Days Accrued Component', calculation: formatValue(daysAccrued), formula: 'Days since last coupon' },
        { componentName: 'Days in Period Component (Divisor / Frequency)', calculation: `${divisor} / ${frequency} = ${formatValue(daysInPeriod)}`, formula: `${divisor} / ${frequency}` },
        { componentName: 'Accrued Interest Calculation (Coupon per Period × (Days Accrued / Days in Period))', calculation: `${formatValue(couponPerPeriod)} × (${formatValue(daysAccrued)} / ${formatValue(daysInPeriod)}) = ${formatValue(accrued)}`, formula: 'Coupon per Period × (Days Accrued / Days in Period)' }
      ]
    }
  }
  
  else if (metricKey === 'Total Portfolio Value' || metricKey === 'totalValue') {
    const rows = instrumentSummary.value.rows || []
    const valueField = 'Total Value' in rows[0] ? 'Total Value' : 'total_value' in rows[0] ? 'total_value' : 'Calculated Value'
    const principalField = 'Principal' in rows[0] ? 'Principal' : 'principal' in rows[0] ? 'principal' : 'Face Value'
    
    let totalValue = 0
    let totalPrincipal = 0
    const valueBreakdown = []
    const principalBreakdown = []
    
    rows.forEach((row, idx) => {
      const val = parseFloat(row[valueField] || row[valueField.toLowerCase()] || 0)
      const princ = parseFloat(row[principalField] || row[principalField.toLowerCase()] || 0)
      if (!isNaN(val)) {
        totalValue += val
        valueBreakdown.push(val)
      }
      if (!isNaN(princ)) {
        totalPrincipal += princ
        principalBreakdown.push(princ)
      }
    })
    
    details.push({ label: 'Total Value', value: formatValue(totalValue), formula: 'Sum of all instrument values' })
    if (principalBreakdown.length > 0) {
      details.push({ label: 'Total Principal', value: formatValue(totalPrincipal), formula: 'Sum of principal amounts' })
    }
    details.push({ label: 'Answer (Total Portfolio Value)', value: formatValue(totalValue), formula: 'Final portfolio value' })
    
    if (valueBreakdown.length > 0) {
      details.breakdown = {
        title: 'Formula Component Breakdown',
        components: [
          { componentName: 'Value Component', calculation: valueBreakdown.map(v => formatValue(v)).join(' + ') + ' = ' + formatValue(totalValue), formula: 'Individual instrument values' }
        ]
      }
      if (principalBreakdown.length > 0) {
        details.breakdown.components.push({
          componentName: 'Principal Component',
          calculation: principalBreakdown.map(v => formatValue(v)).join(' + ') + ' = ' + formatValue(totalPrincipal),
          formula: 'Individual principal amounts'
        })
      }
    }
  }
  
  else if (metricKey === 'Average Rate' || metricKey === 'avgRate' || metricKey === 'weightedAvgRate') {
    const rows = instrumentSummary.value.rows || []
    const rateField = 'Avg Rate' in rows[0] ? 'Avg Rate' : 'avg_rate' in rows[0] ? 'avg_rate' : 'Interest Rate'
    const principalField = 'Principal' in rows[0] ? 'Principal' : 'principal' in rows[0] ? 'principal' : 'Face Value'
    
    let totalWeightedRate = 0
    let totalPrincipal = 0
    const rateBreakdown = []
    const principalBreakdown = []
    const weightedBreakdown = []
    
    rows.forEach((row, idx) => {
      const rate = parseFloat(row[rateField] || row[rateField.toLowerCase()] || 0)
      const princ = parseFloat(row[principalField] || row[principalField.toLowerCase()] || 0)
      if (!isNaN(rate) && !isNaN(princ)) {
        const weighted = rate * princ
        totalWeightedRate += weighted
        totalPrincipal += princ
        rateBreakdown.push(rate)
        principalBreakdown.push(princ)
        weightedBreakdown.push(weighted)
      }
    })
    
    const avgRate = totalPrincipal > 0 ? totalWeightedRate / totalPrincipal : 0
    
    details.push({ label: 'Total Weighted Rate', value: formatValue(totalWeightedRate), formula: 'Σ (Rate × Principal)' })
    details.push({ label: 'Total Principal', value: formatValue(totalPrincipal), formula: 'Σ Principal' })
    details.push({ label: 'Calculation', value: `${formatValue(totalWeightedRate)} / ${formatValue(totalPrincipal)} = ${formatValue(avgRate)}%`, formula: 'Σ (Rate × Principal) / Σ Principal' })
    details.push({ label: 'Answer (Average Rate)', value: formatValue(avgRate) + '%', formula: 'Final weighted average rate' })
    
    details.breakdown = {
      title: 'Formula Component Breakdown',
      components: [
        { componentName: 'Rate Component', calculation: rateBreakdown.map(v => formatValue(v) + '%').join(' + '), formula: 'Individual interest rates' },
        { componentName: 'Principal Component', calculation: principalBreakdown.map(v => formatValue(v)).join(' + ') + ' = ' + formatValue(totalPrincipal), formula: 'Individual principal amounts' },
        { componentName: 'Weighted Rate Component (Rate × Principal)', calculation: weightedBreakdown.map(v => formatValue(v)).join(' + ') + ' = ' + formatValue(totalWeightedRate), formula: 'Rate × Principal for each instrument' }
      ]
    }
  }
  
  else if (metricKey === 'Number of Instruments' || metricKey === 'instrumentCount') {
    const count = getValue('instrumentCount') || getValue('instrument_count') || (instrumentSummary.value.rows?.length || 0)
    const successful = getValue('successful_rows')
    const rows = instrumentSummary.value.rows || []
    
    details.push({ label: 'Total Count', value: formatValue(count), formula: 'Number of rows' })
    if (successful) {
      details.push({ label: 'Successful Calculations', value: formatValue(successful), formula: 'Rows with successful calculations' })
    }
    details.push({ label: 'Answer (Number of Instruments)', value: formatValue(count), formula: 'Final instrument count' })
    
    const instrumentNames = rows.map((row, idx) => {
      const name = row['Instrument Name'] || row['instrument_name'] || row['Issuer'] || row['Name'] || row['instrument'] || `Instrument ${idx + 1}`
      return name
    })
    
    details.breakdown = {
      title: 'Formula Component Breakdown',
      components: [
        { componentName: 'Individual Instruments', calculation: instrumentNames.join(', '), formula: 'List of all instruments in the portfolio' }
      ]
    }
  }
  
  else if (metricKey === 'weightedAvgCoupon' || metricKey === 'totalAnnualIncome') {
    const rows = instrumentSummary.value.rows || []
    const couponField = 'Coupon Rate' in rows[0] ? 'Coupon Rate' : 'coupon_rate' in rows[0] ? 'coupon_rate' : 'Interest Rate'
    const faceField = 'Face Value' in rows[0] ? 'Face Value' : 'face_value' in rows[0] ? 'face_value' : 'Principal'
    
    let totalCouponIncome = 0
    let totalFaceValue = 0
    const couponBreakdown = []
    const faceBreakdown = []
    const incomeBreakdown = []
    
    rows.forEach((row, idx) => {
      const coupon = parseFloat(row[couponField] || row[couponField.toLowerCase()] || 0)
      const face = parseFloat(row[faceField] || row[faceField.toLowerCase()] || 0)
      if (!isNaN(coupon) && !isNaN(face)) {
        const income = face * (coupon / 100)
        totalCouponIncome += income
        totalFaceValue += face
        couponBreakdown.push(coupon)
        faceBreakdown.push(face)
        incomeBreakdown.push(income)
      }
    })
    
    const avgCoupon = totalFaceValue > 0 ? (totalCouponIncome / totalFaceValue) * 100 : 0
    
    details.push({ label: 'Total Annual Income', value: formatValue(totalCouponIncome), formula: 'Σ (Face Value × Coupon Rate)' })
    details.push({ label: 'Total Face Value', value: formatValue(totalFaceValue), formula: 'Σ Face Value' })
    details.push({ label: 'Answer (Total Annual Income)', value: formatValue(totalCouponIncome), formula: 'Final annual coupon income' })
    
    details.breakdown = {
      title: 'Formula Component Breakdown',
      components: [
        { componentName: 'Coupon Rate Component', calculation: couponBreakdown.map(v => formatValue(v) + '%').join(' + '), formula: 'Individual coupon rates' },
        { componentName: 'Face Value Component', calculation: faceBreakdown.map(v => formatValue(v)).join(' + ') + ' = ' + formatValue(totalFaceValue), formula: 'Individual face values' },
        { componentName: 'Annual Income Component (Face Value × Coupon Rate)', calculation: incomeBreakdown.map(v => formatValue(v)).join(' + ') + ' = ' + formatValue(totalCouponIncome), formula: 'Face Value × Coupon Rate for each instrument' }
      ]
    }
  }
  
  else if (metricKey === 'avgYTM') {
    const rows = instrumentSummary.value.rows || []
    const ytmField = 'YTM' in rows[0] ? 'YTM' : 'ytm' in rows[0] ? 'ytm' : 'Yield to Maturity'
    
    let totalYTM = 0
    let count = 0
    const ytmBreakdown = []
    
    rows.forEach((row, idx) => {
      const ytm = parseFloat(row[ytmField] || row[ytmField.toLowerCase()] || 0)
      if (!isNaN(ytm)) {
        totalYTM += ytm
        count++
        ytmBreakdown.push(ytm)
      }
    })
    
    const avgYTM = count > 0 ? totalYTM / count : 0
    
    details.push({ label: 'Sum of YTMs', value: formatValue(totalYTM) + '%', formula: 'Σ YTM' })
    details.push({ label: 'Number of Instruments', value: formatValue(count), formula: 'Count' })
    details.push({ label: 'Calculation', value: `${formatValue(totalYTM)}% / ${count} = ${formatValue(avgYTM)}%`, formula: 'Σ YTM / Count' })
    details.push({ label: 'Answer (Average YTM)', value: formatValue(avgYTM) + '%', formula: 'Final average YTM' })
    
    details.breakdown = {
      title: 'Formula Component Breakdown',
      components: [
        { componentName: 'YTM Component', calculation: ytmBreakdown.map(v => formatValue(v) + '%').join(' + ') + ' = ' + formatValue(totalYTM) + '%', formula: 'Individual YTM values' }
      ]
    }
  }
  
  else if (metricKey === 'duration') {
    const rows = instrumentSummary.value.rows || []
    const durationField = 'Duration' in rows[0] ? 'Duration' : 'duration' in rows[0] ? 'duration' : 'Macaulay Duration'
    
    let totalDuration = 0
    let count = 0
    const durationBreakdown = []
    
    rows.forEach((row, idx) => {
      const dur = parseFloat(row[durationField] || row[durationField.toLowerCase()] || 0)
      if (!isNaN(dur)) {
        totalDuration += dur
        count++
        durationBreakdown.push(dur)
      }
    })
    
    const avgDuration = count > 0 ? totalDuration / count : 0
    
    details.push({ label: 'Sum of Durations', value: formatValue(totalDuration) + ' years', formula: 'Σ Duration' })
    details.push({ label: 'Number of Instruments', value: formatValue(count), formula: 'Count' })
    details.push({ label: 'Calculation', value: `${formatValue(totalDuration)} / ${count} = ${formatValue(avgDuration)} years`, formula: 'Σ Duration / Count' })
    details.push({ label: 'Answer (Duration)', value: formatValue(avgDuration) + ' years', formula: 'Final duration' })
    
    details.breakdown = {
      title: 'Formula Component Breakdown',
      components: [
        { componentName: 'Duration Component', calculation: durationBreakdown.map(v => formatValue(v) + ' years').join(' + ') + ' = ' + formatValue(totalDuration) + ' years', formula: 'Individual duration values' }
      ]
    }
  }
  
  else if (metricKey === 'weightedAvgDiscount' || metricKey === 'totalDiscount') {
    const rows = instrumentSummary.value.rows || []
    const discountField = 'Discount Rate' in rows[0] ? 'Discount Rate' : 'discount_rate' in rows[0] ? 'discount_rate' : 'Discount'
    const faceField = 'Face Value' in rows[0] ? 'Face Value' : 'face_value' in rows[0] ? 'face_value' : 'Principal'
    
    let totalDiscount = 0
    let totalFaceValue = 0
    const discountBreakdown = []
    const faceBreakdown = []
    const discountAmountBreakdown = []
    
    rows.forEach((row, idx) => {
      const discount = parseFloat(row[discountField] || row[discountField.toLowerCase()] || 0)
      const face = parseFloat(row[faceField] || row[faceField.toLowerCase()] || 0)
      if (!isNaN(discount) && !isNaN(face)) {
        const discountAmount = face * (discount / 100)
        totalDiscount += discountAmount
        totalFaceValue += face
        discountBreakdown.push(discount)
        faceBreakdown.push(face)
        discountAmountBreakdown.push(discountAmount)
      }
    })
    
    const avgDiscount = totalFaceValue > 0 ? (totalDiscount / totalFaceValue) * 100 : 0
    
    details.push({ label: 'Total Discount Amount', value: formatValue(totalDiscount), formula: 'Σ (Face Value × Discount Rate)' })
    details.push({ label: 'Total Face Value', value: formatValue(totalFaceValue), formula: 'Σ Face Value' })
    details.push({ label: 'Answer (Total Discount)', value: formatValue(totalDiscount), formula: 'Final total discount' })
    
    details.breakdown = {
      title: 'Formula Component Breakdown',
      components: [
        { componentName: 'Discount Rate Component', calculation: discountBreakdown.map(v => formatValue(v) + '%').join(' + '), formula: 'Individual discount rates' },
        { componentName: 'Face Value Component', calculation: faceBreakdown.map(v => formatValue(v)).join(' + ') + ' = ' + formatValue(totalFaceValue), formula: 'Individual face values' },
        { componentName: 'Discount Amount Component (Face Value × Discount Rate)', calculation: discountAmountBreakdown.map(v => formatValue(v)).join(' + ') + ' = ' + formatValue(totalDiscount), formula: 'Face Value × Discount Rate for each instrument' }
      ]
    }
  }
  
  else if (metricKey === 'interestRate') {
    const value = getValue('interestRate') || getValue('interest_rate') || getValue('avgRate') || getValue('avg_rate')
    details.push({ label: 'Interest Rate', value: formatValue(value) + '%', formula: 'Annual interest rate as percentage' })
    details.push({ label: 'Answer (Interest Rate)', value: formatValue(value) + '%', formula: 'Final interest rate' })
  }

  else if (metricKey === 'effectiveYield' || metricKey === 'effectiveAnnualRate' || metricKey === 'annualYield') {
    const effYield = getValue('effectiveYield') || getValue('effective_yield') || getValue('effectiveAnnualRate') || getValue('effective_annual_rate')
    const principal = getValue('principal') || getValue('totalPrincipal') || getValue('total_principal')
    const interest = getValue('interestEarned') || getValue('totalInterest') || getValue('interest_earned')
    const days = getValue('termDays') || getValue('term_days') || getValue('avgDaysToMaturity') || getValue('avg_days_to_maturity')

    details.push({ label: 'Effective Yield', value: formatValue(effYield) + '%', formula: 'Effective yield from backend' })
    details.push({ label: 'Interest Earned', value: formatValue(interest), formula: 'Interest amount' })
    details.push({ label: 'Principal', value: formatValue(principal), formula: 'Principal amount' })
    details.push({ label: 'Term Days', value: formatValue(days), formula: 'Days to maturity' })
    details.push({ label: 'Answer (Effective Yield)', value: formatValue(effYield) + '%', formula: '(Interest / Principal) × (365 / Days) × 100' })
  }

  else if (metricKey === 'avgDaysToMaturity' || metricKey === 'termDays' || metricKey === 'daysToMaturity') {
    const avgDays = getValue('avgDaysToMaturity') || getValue('avg_days_to_maturity') || getValue('termDays') || getValue('term_days')
    details.push({ label: 'Average Days to Maturity', value: formatValue(avgDays), formula: 'Average days from backend' })
    details.push({ label: 'Answer (Average Days)', value: formatValue(avgDays), formula: 'Final average days to maturity' })
  }

  else if (metricKey === 'maturityValue') {
    const maturityVal = getValue('maturityValue') || getValue('maturity_value') || getValue('totalValue') || getValue('total_value')
    const principal = getValue('principal') || getValue('totalPrincipal') || getValue('total_principal')
    const interest = getValue('interestEarned') || getValue('totalInterest') || getValue('interest_earned')

    details.push({ label: 'Maturity Value', value: formatValue(maturityVal), formula: 'Maturity value from backend' })
    details.push({ label: 'Principal', value: formatValue(principal), formula: 'Principal amount' })
    details.push({ label: 'Interest Earned', value: formatValue(interest), formula: 'Interest amount' })
    details.push({ label: 'Answer (Maturity Value)', value: formatValue(maturityVal), formula: 'Principal + Interest' })
  }

  else if (metricKey === 'presentValue') {
    const presentValue = getValue('presentValue') || getValue('present_value') || getValue('price')
    const couponRate = getValue('couponRate') || getValue('coupon_rate')
    const face = getValue('faceValue') || getValue('face_value')
    const ytm = getValue('yieldToMaturity') || getValue('yield_to_maturity') || getValue('ytm')
    const frequency = getValue('frequency') || getValue('coupon_frequency') || 2

    details.push({ label: 'Present Value', value: formatValue(presentValue), formula: 'Present value from backend' })
    details.push({ label: 'Face Value', value: formatValue(face), formula: 'Par value' })
    details.push({ label: 'Coupon Rate', value: formatValue(couponRate) + '%', formula: 'Annual coupon rate' })
    details.push({ label: 'Yield to Maturity', value: formatValue(ytm) + '%', formula: 'Discount rate' })
    details.push({ label: 'Coupon Frequency', value: frequency, formula: 'Payments per year' })
    details.push({ label: 'Answer (Present Value)', value: formatValue(presentValue), formula: 'DCF calculated present value' })
  }

  else if (metricKey === 'fairValue') {
    const fairVal = getValue('fairValue') || getValue('fair_value')
    const presentValue = getValue('presentValue') || getValue('present_value') || getValue('price')
    const marketPrice = getValue('currentPrice') || getValue('current_price') || getValue('price')

    details.push({ label: 'Fair Value', value: formatValue(fairVal), formula: 'Fair value from backend' })
    details.push({ label: 'Present Value', value: formatValue(presentValue), formula: 'Discounted cash flow value' })
    details.push({ label: 'Market Price', value: formatValue(marketPrice), formula: 'Current market price' })
    details.push({ label: 'Answer (Fair Value)', value: formatValue(fairVal), formula: 'Present Value - Market Price' })
  }

  else if (metricKey === 'yieldCurveRate') {
    const benchmark = getValue('yieldCurveRate') || getValue('yield_curve_rate') || getValue('benchmark_rate') || getValue('risk_free_rate')
    details.push({ label: 'Benchmark Rate', value: formatValue(benchmark) + '%', formula: 'FRED API benchmark rate' })
    details.push({ label: 'Answer (Benchmark)', value: formatValue(benchmark) + '%', formula: 'External benchmark from FRED' })
  }

  else if (metricKey === 'totalPrincipal') {
    const totalPrincipal = getValue('totalPrincipal') || getValue('total_principal')
    details.push({ label: 'Total Principal', value: formatValue(totalPrincipal), formula: 'Σ Principal amounts (calculated by backend)' })
    details.push({ label: 'Answer (Total Principal)', value: formatValue(totalPrincipal), formula: 'Sum of all principal values from individual instruments' })
  }

  else if (metricKey === 'modifiedDuration') {
    const modDur = getValue('modifiedDuration') || getValue('modified_duration')
    const macaulay = getValue('duration') || getValue('macaulay_duration')
    const ytm = getValue('yieldToMaturity') || getValue('yield_to_maturity') || getValue('ytm')
    const frequency = getValue('frequency') || getValue('coupon_frequency') || 2

    details.push({ label: 'Modified Duration', value: formatValue(modDur) + ' years', formula: 'Modified duration from backend' })
    details.push({ label: 'Macaulay Duration', value: formatValue(macaulay) + ' years', formula: 'Weighted average time to cash flows' })
    details.push({ label: 'Yield to Maturity', value: formatValue(ytm) + '%', formula: 'Discount rate' })
    details.push({ label: 'Coupon Frequency', value: frequency, formula: 'Payments per year' })
    details.push({ label: 'Answer (Modified Duration)', value: formatValue(modDur) + ' years', formula: 'Macaulay / (1 + YTM/Frequency)' })
  }

  else if (metricKey === 'yieldToMaturity') {
    const ytm = getValue('yieldToMaturity') || getValue('yield_to_maturity') || getValue('ytm')
    const price = getValue('currentPrice') || getValue('current_price') || getValue('price')
    const couponRate = getValue('couponRate') || getValue('coupon_rate')
    const face = getValue('faceValue') || getValue('face_value')
    const frequency = getValue('frequency') || getValue('coupon_frequency') || 2
    const years = getValue('yearsToMaturity') || getValue('years_to_maturity')

    details.push({ label: 'Yield to Maturity', value: formatValue(ytm) + '%', formula: 'YTM from backend' })
    details.push({ label: 'Current Price', value: formatValue(price), formula: 'Market price' })
    details.push({ label: 'Coupon Rate', value: formatValue(couponRate) + '%', formula: 'Annual coupon rate' })
    details.push({ label: 'Face Value', value: formatValue(face), formula: 'Par value' })
    details.push({ label: 'Years to Maturity', value: formatValue(years), formula: 'Time to maturity' })
    details.push({ label: 'Answer (YTM)', value: formatValue(ytm) + '%', formula: 'Internal rate of return (Newton-Raphson)' })
  }

  else if (metricKey === 'couponRate') {
    const value = getValue('couponRate') || getValue('coupon_rate')
    const face = getValue('faceValue') || getValue('face_value')
    const annualCoupon = face * (value / 100)

    details.push({ label: 'Coupon Rate', value: formatValue(value) + '%', formula: 'Coupon rate from backend' })
    details.push({ label: 'Face Value', value: formatValue(face), formula: 'Par value' })
    details.push({ label: 'Annual Coupon', value: formatValue(annualCoupon), formula: 'Face Value × Coupon Rate' })
    details.push({ label: 'Answer (Coupon Rate)', value: formatValue(value) + '%', formula: 'Final coupon rate' })
  }

  else if (metricKey === 'holdingPeriodYield') {
    const hpy = getValue('holdingPeriodYield') || getValue('holding_period_yield')
    const face = getValue('faceValue') || getValue('face_value')
    const purchase = getValue('purchasePrice') || getValue('purchase_price')

    details.push({ label: 'Holding Period Yield', value: formatValue(hpy) + '%', formula: 'Holding period yield from backend' })
    details.push({ label: 'Face Value', value: formatValue(face), formula: 'Maturity value' })
    details.push({ label: 'Purchase Price', value: formatValue(purchase), formula: 'Price paid' })
    details.push({ label: 'Answer (Holding Period Yield)', value: formatValue(hpy) + '%', formula: '(Face Value - Purchase Price) / Purchase Price × 100' })
  }

  else if (metricKey === 'pricePer100') {
    const pricePer100 = getValue('pricePer100') || getValue('price_per_100')
    const price = getValue('currentPrice') || getValue('current_price') || getValue('price')
    const face = getValue('faceValue') || getValue('face_value')

    details.push({ label: 'Price per 100', value: formatValue(pricePer100), formula: 'Price per 100 from backend' })
    details.push({ label: 'Current Price', value: formatValue(price), formula: 'Market price' })
    details.push({ label: 'Face Value', value: formatValue(face), formula: 'Par value' })
    details.push({ label: 'Answer (Price per 100)', value: formatValue(pricePer100), formula: '(Price / Face Value) × 100' })
  }

  else if (metricKey === 'totalPurchasePrice') {
    const totalPurchase = getValue('totalPurchasePrice') || getValue('total_purchase_price')
    details.push({ label: 'Total Purchase Price', value: formatValue(totalPurchase), formula: 'Σ Purchase prices' })
    details.push({ label: 'Answer (Total Purchase)', value: formatValue(totalPurchase), formula: 'Sum of all purchase prices' })
  }

  else if (metricKey === 'avgInvestment') {
    const avgInvest = getValue('avgInvestment') || getValue('avg_investment')
    const totalPurchase = getValue('totalPurchasePrice') || getValue('total_purchase_price')
    const count = getValue('instrumentCount') || getValue('instrument_count') || (instrumentSummary.value.rows?.length || 0)

    details.push({ label: 'Average Investment', value: formatValue(avgInvest), formula: 'Average investment from backend' })
    details.push({ label: 'Total Purchase Price', value: formatValue(totalPurchase), formula: 'Sum of all purchase prices' })
    details.push({ label: 'Number of Instruments', value: formatValue(count), formula: 'Count' })
    details.push({ label: 'Answer (Average Investment)', value: formatValue(avgInvest), formula: 'Total Purchase / Count' })
  }

  else if (metricKey === 'annualizedYield' || metricKey === 'moneyMarketYield' || metricKey === 'effectiveAnnualYield') {
    const moneyMarketYield = getValue('moneyMarketYield') || getValue('money_market_yield') || getValue('annualizedYield') || getValue('annualized_yield')
    const face = getValue('faceValue') || getValue('face_value')
    const purchase = getValue('purchasePrice') || getValue('purchase_price')
    const days = getValue('termDays') || getValue('term_days')
    const discount = face - purchase

    details.push({ label: 'Money Market Yield', value: formatValue(moneyMarketYield) + '%', formula: 'Money market yield from backend' })
    details.push({ label: 'Face Value', value: formatValue(face), formula: 'Maturity value' })
    details.push({ label: 'Purchase Price', value: formatValue(purchase), formula: 'Price paid' })
    details.push({ label: 'Term Days', value: formatValue(days), formula: 'Days to maturity' })
    details.push({ label: 'Answer (Money Market Yield)', value: formatValue(moneyMarketYield) + '%', formula: '(Discount / Purchase) × (360 / Days) × 100' })
  }

  else {
    const value = getValue(metricKey)
    details.push({ label: metricKey, value: formatValue(value), formula: formulaMap[metricKey] || 'See formula above' })
    details.push({ label: 'Answer', value: formatValue(value), formula: 'Final calculated value' })
  }
  
  formulaCalculationDetails.value = details.length > 0 ? details : null
  showCalculationDetails.value = true
  showIndividualBreakdown.value = false
  formulaDialog.value = true
}

function selectAllInstruments() { selectedInstruments.value = { 'money-market': true, bonds: true, tbills: true } }
function deselectAllInstruments() { selectedInstruments.value = { 'money-market': false, bonds: false, tbills: false } }

function getInstrumentData(instrumentId) {
  if (!activeSession.value) return null
  const sid = activeSession.value.id
  if (instrumentSummary.value.rows.length > 0) {
    const rows = instrumentSummary.value.rows.filter(r => r['Instrument Type'] === instrumentId)
    if (rows.length > 0) {
      let totalValue = 0, totalFaceValue = 0, totalAvgRate = 0
      rows.forEach(row => {
        const value = parseFloat(row['Total Value'] || row['total_value'] || row['Calculated Value'] || row['calculated_value'] || 0)
        const faceValue = parseFloat(row['Face Value'] || row['face_value'] || row['Amount'] || row['amount'] || row['Principal'] || row['principal'] || 0)
        const rate = parseFloat(row['Avg Rate'] || row['avg_rate'] || row['Coupon Rate'] || row['coupon_rate'] || row['Discount Rate'] || row['discount_rate'] || 0)
        if (!isNaN(value)) totalValue += value
        if (!isNaN(faceValue)) totalFaceValue += faceValue
        if (!isNaN(rate)) totalAvgRate += rate
      })
      const avgRate = rows.length > 0 && totalAvgRate > 0 ? totalAvgRate / rows.length : null
      return {
        totalValue,
        instrumentCount: rows.length,
        avgRate,
        avgCouponRate: instrumentId === 'bonds' ? avgRate : null,
        avgDiscountRate: instrumentId === 'tbills' ? avgRate : null,
        totalPrincipal: totalFaceValue
      }
    }
  }
  return null
}

const reportPreviewData = computed(() => {
  const instrumentsData = []
  const instrumentTypes = [
    { key: 'money-market', label: 'Money Market' },
    { key: 'bonds', label: 'Bonds' },
    { key: 'tbills', label: 'T-Bills' }
  ]

  for (const type of instrumentTypes) {
    const key = type.key
    const selected = selectedInstruments.value[key]
    if (!selected) continue

    const data = getInstrumentData(key)
    if (data && (data.totalValue > 0 || data.instrumentCount > 0)) {
      instrumentsData.push({ name: type.label, calculations: data, id: key })
    }
  }

  return {
    session: activeSession.value?.name || 'No session',
    date: new Date().toLocaleString(),
    instruments: instrumentsData,
    chartImage: chartImageData.value,
    fredFilters: { country: effectiveCountry.value, currency: effectiveCurrency.value, maturity: effectiveMaturity.value },
    yieldCurveData: yieldCurveData.value,
    valuationDate: activeValuationDate.value || ''
  }
})

function formatMetricName(key) {
  const names = {
    totalValue: 'Total Value', instrumentCount: 'Count', avgRate: 'Avg Interest Rate',
    weightedAvgRate: 'Weighted Avg Rate', totalInterest: 'Total Interest',
    interestEarned: 'Interest Earned', annualYield: 'Annual Yield',
    effectiveAnnualRate: 'Effective Annual Rate', avgDaysToMaturity: 'Avg Days to Maturity',
    totalPrincipal: 'Total Principal', avgCouponRate: 'Avg Coupon Rate',
    weightedAvgCoupon: 'Weighted Avg Coupon', totalAnnualIncome: 'Total Annual Income',
    avgYTM: 'Avg Yield to Maturity', duration: 'Duration', avgDiscountRate: 'Avg Discount Rate',
    weightedAvgDiscount: 'Weighted Avg Discount', totalDiscount: 'Total Discount',
    effectiveYield: 'Effective Yield', bondEquivalentYield: 'Bond Equivalent Yield',
    discountYield: 'Discount Yield', moneyMarketYield: 'Money Market Yield',
    pricePer100: 'Price per 100', totalPurchasePrice: 'Total Purchase Price',
    avgInvestment: 'Avg Investment', holdingPeriodYield: 'Holding Period Yield',
    annualizedYield: 'Annualized Yield'
  }
  return names[key] || key.replace(/([A-Z])/g, ' $1').replace(/^./, str => str.toUpperCase())
}

function formatMetricValue(key, value) {
  if (typeof value === 'number') {
    const rounded = Math.round(value * 100) / 100
    if (key.includes('Value') || key.includes('Price') || key.includes('Interest') || key.includes('Income') || key.includes('Discount') || key.includes('Principal') || key.includes('Investment'))
      return rounded.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
    if (key.includes('Rate') || key.includes('Yield') || key.includes('Coupon') || key.includes('Discount'))
      return `${rounded.toFixed(2)}%`
    return rounded.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  }
  return value
}

async function captureChartImage() {
  return new Promise((resolve) => {
    setTimeout(() => {
      const canvas = yieldCurveChart.value
      if (canvas && canvas.toDataURL) {
        try {
          resolve(canvas.toDataURL('image/png', 1.0))
          return
        } catch (e) { console.warn('Canvas capture failed', e) }
      }
      const canvasEl = document.querySelector('.chart-container--fred canvas')
      if (canvasEl && canvasEl.toDataURL) {
        try {
          resolve(canvasEl.toDataURL('image/png', 1.0))
          return
        } catch (e) { console.warn('DOM canvas capture failed', e) }
      }
      const anyCanvas = document.querySelector('canvas')
      if (anyCanvas && anyCanvas.toDataURL) {
        try {
          resolve(anyCanvas.toDataURL('image/png', 1.0))
          return
        } catch (e) { console.warn('Any canvas capture failed', e) }
      }
      console.warn('No canvas found for chart capture')
      resolve('')
    }, 1000)
  })
}

function buildMethodologySection(selectedInstrumentNames) {
  let methods = []
  if (selectedInstrumentNames.includes('Money Market')) methods.push(`<div class="methodology-card"><h4>Money Market Instruments</h4><p class="formula">Fair value = <sup>F</sup> &frasl; <sub>1 + r·t/365</sub></p><p>Where: <strong>F</strong> = Face value, <strong>r</strong> = annualized interest rate (%), <strong>t</strong> = days to maturity.</p><p>Simple interest convention (365 days/year). Weighted average rate = Σ (Rate × Amount) / Σ Amount.</p></div>`)
  if (selectedInstrumentNames.includes('Bonds')) methods.push(`<div class="methodology-card"><h4>Bonds</h4><p class="formula">Fair value = Σ<sub>t=1</sub><sup>n</sup> <sup>C</sup> &frasl; <sub>(1+y)<sup>t</sup></sub> + <sup>FV</sup> &frasl; <sub>(1+y)<sup>n</sup></sub></p><p>Where: <strong>C</strong> = annual coupon payment (CouponRate × FaceValue), <strong>y</strong> = yield to maturity (%), <strong>FV</strong> = face value, <strong>n</strong> = years to maturity.</p><p>Duration = Σ (t × PV(C<sub>t</sub>)) / Price. Approximated using Macaulay duration.</p></div>`)
  if (selectedInstrumentNames.includes('T-Bills')) methods.push(`<div class="methodology-card"><h4>Treasury Bills (T‑Bills)</h4><p class="formula">Discount amount = Face value × (Discount rate / 100) × (Days to maturity / 360)</p><p class="formula">Effective yield = (Face value / Price − 1) × (365 / Days to maturity) × 100</p><p>Bank discount basis (360 days/year) for discount rate; bond equivalent yield uses 365 days.</p></div>`)
  return methods.length ? methods.join('') : '<p>No methodology available for the selected instruments.</p>'
}

const backgroundCoverUrl = '/reportbackground.png'

async function generateReportHtml() {
  await loadSavedData()
  
  const session = activeSession.value
  if (session && session.id) {
    try {
      const wf = await sessionManager.getInstrumentWorkflow(session.id, instrumentType.value)
      if (wf && wf.yieldCurveData && wf.yieldCurveData.length > 0) {
        yieldCurveData.value = wf.yieldCurveData
        if (wf.fredFilters) {
          selectedCountryOption.value = wf.fredFilters.country || ''
          selectedCurrencyOption.value = wf.fredFilters.currency || ''
          selectedMaturityOption.value = wf.fredFilters.maturity || ''
        }
      }
    } catch (e) {
      console.warn('Failed to load yield curve data from session workflow:', e)
    }
  }
  
  const report = reportPreviewData.value
  if (report.instruments.length === 0) {
    return null
  }

  let imageData = chartImageData.value
  if (!imageData && yieldCurveData.value.length > 0) {
    try {
      const previousTab = activeTab.value
      activeTab.value = 'visualizations'
      await nextTick()
      await new Promise(resolve => setTimeout(resolve, 1500))
      
      if (yieldCurveChart.value) {
        imageData = yieldCurveChart.value.toDataURL('image/png', 1.0)
        chartImageData.value = imageData
      }
      
      activeTab.value = previousTab
      await nextTick()
    } catch (e) {
      console.warn('Chart capture failed:', e)
    }
  }

  const valuationDate = activeValuationDate.value || ''
  const totalPortfolioValue = report.instruments.reduce((sum, inst) => sum + (parseFloat(inst.calculations.totalValue) || 0), 0)
  const totalInstrumentCount = report.instruments.reduce((sum, inst) => sum + (parseInt(inst.calculations.instrumentCount) || 0), 0)

  const yieldPoints = yieldCurveData.value || []
  
  let appendixRows = ''
  if (yieldPoints.length) {
    appendixRows = yieldPoints.map(point => `
      <tr>
        <td>${point.maturityLabel || ''}</td>
        <td>${point.maturity || 0}</td>
        <td>${point.rate || 0}%</td>
      </tr>
    `).join('')
  }

  const filterCountry = effectiveCountry.value || '—'
  const filterCurrency = effectiveCurrency.value || '—'
  const filterMaturity = effectiveMaturity.value || '—'

  const methodologyHtml = buildMethodologySection(report.instruments.map(i => i.name))
  const chartHtml = imageData ? `
    <div class="chart-container">
      <img src="${imageData}" alt="Yield Curve" style="max-width:100%; height:auto; border-radius:8px; border:1px solid #e0e0e0;" />
      <p class="chart-caption">FRED Yield Curve – ${chartSeriesLabel.value || report.instruments.map(i => i.name).join(', ')} (${filterCountry} / ${filterCurrency})</p>
    </div>
  ` : (yieldPoints.length ? `
    <div class="chart-container">
      <p><strong>Yield Curve Data:</strong> ${chartSeriesLabel.value || 'FRED Yield Curve'}</p>
      <p><strong>Country:</strong> ${filterCountry} | <strong>Currency:</strong> ${filterCurrency} | <strong>Maturity:</strong> ${filterMaturity}</p>
      <p><em>Chart image could not be captured, but yield curve data is included in the appendix.</em></p>
    </div>
  ` : '<p>Yield curve chart not available. Please load a yield curve in the visualizations section.</p>')

  const sessionName = activeSession.value?.name || 'Valuation Report'

  const html = `<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Valuation Assessment Report - ${sessionName}</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: 'Arial', sans-serif; color: #000; background: white; line-height: 1.6; }
    .page { page-break-after: always; padding: 30px 40px; min-height: 100vh; position: relative; width: 210mm; margin: 0 auto; background: white; }
    .cover-page { background-color: white; background-image: url('${backgroundCoverUrl}'); background-size: 45%; background-position: right center; background-repeat: no-repeat; color: black; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; padding: 40px 50px; min-height: 100vh; position: relative; }
    .cover-logo { position: absolute; top: 30px; left: 40px; z-index: 3; }
    .cover-logo img { max-width: 280px; height: auto; background: white; padding: 4px; }
    .close-button { position: fixed; top: 20px; right: 20px; z-index: 9999; background: #0B2044; color: white; border: none; border-radius: 50%; width: 40px; height: 40px; font-size: 20px; cursor: pointer; display: flex; align-items: center; justify-content: center; box-shadow: 0 2px 10px rgba(0,0,0,0.2); }
    .close-button:hover { background: #1a3a6e; }
    .cover-content { max-width: 70%; position: relative; z-index: 2; color: black; }
    .cover-title { font-size: 48px; font-weight: 700; letter-spacing: 2px; margin-bottom: 20px; color: #000; }
    .cover-subtitle { font-size: 28px; font-weight: 300; opacity: 0.85; margin-bottom: 20px; color: #000; }
    .toc-page h1 { font-size: 28px; color: #0B2044; border-bottom: 3px solid #0B2044; padding-bottom: 15px; margin-bottom: 30px; }
    .toc-item { display: flex; justify-content: space-between; padding: 12px 0; border-bottom: 1px dotted #ddd; font-size: 16px; }
    .section-title { font-size: 24px; color: #0B2044; border-bottom: 2px solid #0B2044; padding-bottom: 10px; margin: 30px 0 20px 0; }
    .executive-summary { background: #f8f9ff; padding: 25px; border-radius: 10px; border-left: 4px solid #0B2044; margin-bottom: 25px; }
    .executive-summary .highlight { color: #0B2044; font-weight: 700; }
    .methodology-card { background: #f8f9ff; padding: 20px; border-radius: 8px; margin: 15px 0; }
    .methodology-card .formula { font-family: 'Courier New', monospace; font-size: 16px; background: white; padding: 10px 15px; border-radius: 6px; border: 1px solid #e0e0e0; margin: 10px 0; }
    table { width: 100%; border-collapse: collapse; margin: 20px 0; font-size: 14px; }
    th { background: #0B2044; color: white; padding: 12px 10px; text-align: left; }
    td { padding: 10px; border-bottom: 1px solid #eee; }
    .appendix-table { font-size: 12px; }
    .appendix-table th { background: #1a3a6e; }
    .appendix-table td { padding: 6px 8px; }
    .footer { margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 12px; color: #999; text-align: center; }
    .reference-list { list-style: none; padding: 0; }
    .reference-list li { padding: 8px 0; border-bottom: 1px solid #eee; }
    .chart-container { margin: 20px 0; text-align: center; }
    .chart-container img { max-width: 100%; height: auto; border-radius: 8px; border: 1px solid #e0e0e0; }
    .chart-caption { font-size: 12px; color: #666; margin-top: 5px; }
    @page { margin: 15mm 12mm; @bottom-center { content: "Page " counter(page) " of " counter(pages); font-size: 10pt; color: #666; } }
    @media print { .page { padding: 30px 40px; width: 210mm; } .cover-page { padding: 40px 50px; width: 210mm; } }
  </style>
</head>
<body>
<button class="close-button" onclick="window.close()">×</button>

<div class="page cover-page">
  <div class="cover-logo"><img src="/DuraCapital logo.png" alt="Dura Capital Logo" /></div>
  <div class="cover-content">
    <h1 class="cover-title">Valuation Assessment Report</h1>
    <p class="cover-subtitle">${sessionName}</p>
  </div>
</div>

<div class="page toc-page">
  <h1>Table of Contents</h1>
  <div class="toc-item"><span>Introduction</span><span>1</span></div>
  <div class="toc-item"><span>Executive Summary</span><span>2</span></div>
  <div class="toc-item"><span>Methodology</span><span>3</span></div>
  <div class="toc-item"><span>Market Inputs</span><span>4</span></div>
  <div class="toc-item"><span>Results</span><span>5</span></div>
  <div class="toc-item"><span>Yield Curve</span><span>6</span></div>
  <div class="toc-item"><span>Conclusion</span><span>7</span></div>
  <div class="toc-item"><span>Appendix</span><span>8</span></div>
  <div class="toc-item"><span>Reference</span><span>9</span></div>
</div>

<div class="page">
  <h1 class="section-title">Introduction</h1>
  <p>Dura Capital (Private) Limited ("Dura Capital", "us", "we") was contracted to provide a fair valuation assessment report of the following fixed income instruments as at ${valuationDate}:</p>
  <ul style="margin: 20px 0 20px 30px;">${report.instruments.map(i => `<li>${i.name}</li>`).join('')}</ul>
  <p>The instruments are classified and measured at fair value through profit or loss in terms of International Financial Reporting Standard 9: Financial Instruments ("IFRS 9") and International Financial Reporting Standard 13: Fair Value Measurement ("IFRS 13") and this forms as the basis to our assessment.</p>
</div>

<div class="page">
  <h1 class="section-title">Executive Summary</h1>
  <div class="executive-summary">
    <p><strong>Valuation Assessment Summary</strong></p>
    <p>This report provides a valuation assessment of ${report.instruments.map(i => i.name).join(', ')} in accordance with IFRS 13 fair value measurement principles.</p>
    <br>
    <p><strong>Key Findings:</strong></p>
    <ul style="margin-left: 20px;">
      <li>Total Portfolio Value: <span class="highlight">${totalPortfolioValue.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</span></li>
      <li>Number of Instruments: <span class="highlight">${totalInstrumentCount}</span></li>
      <li>Valuation Date: <span class="highlight">${valuationDate}</span></li>
    </ul>
  </div>
</div>

<div class="page">
  <h1 class="section-title">Methodology</h1>
  <p>The audit team provided us with data for ${report.instruments.map(i => i.name).join(', ')}. This section outlines the methodologies used to provide a fair value of the fixed income assets in terms of IFRS 13.</p>
  <br>
  ${methodologyHtml}
  <br>
  <p><strong>Day Count Convention:</strong> Actual/365-day count convention as provided by the Audit team.</p>
  <p><strong>Discounting:</strong> The sum of all discounted cashflows for each instrument represents the fair value of the instrument in terms of IFRS 13.</p>
</div>

<div class="page">
  <h1 class="section-title">Market Inputs</h1>
  <p>Market data for Zimbabwe is not available and there have not been any Zimbabwe issued instruments trading on international markets. As such, we have used the OIS SOFR rates from Bloomberg as a risk-free yield curve and added a country risk premium sourced from country risk premiums published by Damodaran.</p>
  <br>
  <p>To determine a smooth yield for the determination of rates for all maturities, we use the Nelson-Siegel-Svensson model which is widely used in practice for fitting the term structure of interest rates.</p>
  <br>
  <p><strong>Key Market Inputs:</strong></p>
  <ul style="margin: 10px 0 20px 30px;">
    <li><strong>Risk-Free Rate:</strong> SOFR OIS curve as at ${valuationDate}</li>
    <li><strong>Country Risk Premium:</strong> Damodaran Country Risk Premiums</li>
    <li><strong>Credit Spread:</strong> Applied based on counterparty risk assessment</li>
    <li><strong>Yield Curve Model:</strong> Nelson-Siegel-Svensson (NSS)</li>
  </ul>
</div>

<div class="page">
  <h1 class="section-title">Results</h1>
  <p>Below is a summary of the key findings of the valuation for the selected instruments.</p>
  <br>
  <table>
    <thead><tr><th>Instrument</th><th>Total Value</th><th>Count</th><th>Avg Rate (%)</th><th>Weighted Avg (%)</th></tr></thead>
    <tbody>
      ${report.instruments.map(inst => `
        <tr>
          <td><strong>${inst.name}</strong></td>
          <td>${(inst.calculations.totalValue || 0).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
          <td>${inst.calculations.instrumentCount || 0}</td>
          <td>${inst.calculations.avgRate || inst.calculations.avgCouponRate || inst.calculations.avgDiscountRate || 0}%</td>
          <td>${inst.calculations.weightedAvgRate || inst.calculations.weightedAvgCoupon || inst.calculations.weightedAvgDiscount || 0}%</td>
        </tr>
      `).join('')}
      <tr style="font-weight:700;background:#f0f2f5;">
        <td><strong>Total Portfolio</strong></td>
        <td><strong>${totalPortfolioValue.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</strong></td>
        <td><strong>${totalInstrumentCount}</strong></td>
        <td colspan="2"></td>
      </tr>
    </tbody>
  </table>
</div>

<div class="page">
  <h1 class="section-title">Yield Curve</h1>
  <p>The following yield curve was used as a benchmark for valuation, sourced from FRED.</p>
  ${chartHtml}
</div>

<div class="page">
  <h1 class="section-title">Conclusion</h1>
  <p>The valuation assessment conducted by Dura Capital provides a comprehensive fair value assessment of the ${report.instruments.map(i => i.name).join(', ')} instruments as at ${valuationDate}.</p>
  <br>
  <p><strong>Key Observations:</strong></p>
  <ul style="margin: 10px 0 20px 30px;">
    <li>The valuation methodology applied is in accordance with IFRS 13 fair value measurement principles.</li>
    <li>Market inputs used are appropriate for the valuation date.</li>
    <li>All material assumptions have been disclosed and are reasonable.</li>
    <li>The valuation is based on information provided by the client and market data as at the valuation date.</li>
  </ul>
  <br>
  <p><strong>Recommendation:</strong> The valuation is reasonable and can be used for financial reporting purposes in accordance with IFRS 13.</p>
</div>

<div class="page">
  <h1 class="section-title">Appendix: FRED API Yield Curve Data</h1>
  <p><strong>Valuation Date:</strong> ${valuationDate}</p>
  <p><strong>Country:</strong> ${filterCountry}</p>
  <p><strong>Instrument Type:</strong> ${instrumentType.value}</p>
  <br>
  ${yieldPoints.length ? `
  <table class="appendix-table">
    <thead><tr><th>BB Ticker (Maturity Label)</th><th>Term (Yr)</th><th>Rate (Actual) %</th></tr></thead>
    <tbody>${appendixRows}</tbody>
  </table>
  ` : '<p>No yield curve data available. FRED API may have failed or returned no data.</p>'}
</div>

<div class="page">
  <h1 class="section-title">Reference</h1>
  <ul class="reference-list">
    <li>Bloomberg Financial Services – SOFR OIS Yield Curve as at ${valuationDate}</li>
    <li>Damodaran Country Risk Premiums – Published country risk premiums</li>
    <li>IFRS 13: Fair Value Measurement – International Financial Reporting Standards</li>
    <li>IFRS 9: Financial Instruments – Classification and measurement</li>
    <li>Nelson-Siegel-Svensson model for yield curve fitting</li>
  </ul>
  <br>
  <div class="footer">
    <p>© ${new Date().getFullYear()} Dura Capital (Private) Limited. All rights reserved.</p>
    <p>This report is confidential and prepared solely for the use of the client.</p>
  </div>
</div>

</body>
</html>`
  return html
}

async function previewReport() {
  await loadSavedData()
  const html = await generateReportHtml()
  if (html) {
    const win = window.open('', '_blank')
    win.document.write(html)
    win.document.close()
  }
}

async function downloadFromPreview(format) {
  if (!reportPreviewHtml.value) return
  const filename = `combined_report_${Date.now()}`
  if (format === 'html') {
    downloadBlob(reportPreviewHtml.value, `${filename}.html`, 'text/html')
  } else if (format === 'pdf') {
    const win = window.open('', '_blank')
    win.document.write(reportPreviewHtml.value)
    win.document.close()
    setTimeout(() => win.print(), 500)
  } else if (format === 'word') {
    downloadBlob(reportPreviewHtml.value, `${filename}.doc`, 'application/msword')
  }
}

async function exportToRealExcel() {
  await loadSavedData()
  const report = reportPreviewData.value
  if (report.instruments.length === 0) { return }
  const workbook = XLSX.utils.book_new()
  const valuationDate = activeValuationDate.value || ''

  const summaryData = [
    ['', '', ''],
    ['DuraCapital', '', ''],
    ['Valuation Assessment Report', '', ''],
    [`Session: ${report.session}`, '', ''],
    [`Valuation Date: ${valuationDate}`, '', ''],
    ['', '', ''],
    ['Report Generated', new Date().toLocaleString(), ''],
    ['', '', ''],
    ['Instrument', 'Metric', 'Value']
  ]
  for (const inst of report.instruments) {
    for (const [key, val] of Object.entries(inst.calculations)) {
      if (key === 'completed' || key === 'timestamp' || key === 'fred') continue
      summaryData.push([inst.name, formatMetricName(key), formatMetricValue(key, val)])
    }
  }
  const summarySheet = XLSX.utils.aoa_to_sheet(summaryData)
  XLSX.utils.book_append_sheet(workbook, summarySheet, 'Summary')

  const appendixData = [
    ['APPENDIX – Detailed Instrument Data'],
    ['Valuation Date:', valuationDate],
    ['Session:', report.session],
    [],
    ['Asset Class', 'Instrument Name', 'BB Ticker', 'Face Value', 'Rate (%)', 'Term (Yrs)', 'Valuation Date']
  ]
  for (const inst of report.instruments) {
    const instKey = inst.id || (inst.name === 'Money Market' ? 'money-market' : inst.name === 'Bonds' ? 'bonds' : 'tbills')
    let instrumentData = []
    const wf = await sessionManager.getInstrumentWorkflow(activeSession.value?.id, instKey)
    if (wf && wf.cleanedData && wf.cleanedData.length) instrumentData = wf.cleanedData
    else {
      const sid = activeSession.value?.id
      if (sid) {
        const saved = localStorage.getItem(`${instKey}_session_${sid}_clean`)
        if (saved) instrumentData = JSON.parse(saved)
      }
    }
    if (instrumentData.length) {
      instrumentData.forEach((item, idx) => {
        const name = item.Instrument || item.BondName || item.TBillName || `${inst.name} ${idx + 1}`
        const ticker = item.BBTicker || item.Ticker || item.Security || ''
        const faceValue = formatForExcel(parseFloat(item.FaceValue || item.Amount || item.Principal || 0), 'money', 'FaceValue')
        const rate = formatForExcel(parseFloat(item.Rate || item.InterestRate || item.CouponRate || item.DiscountRate || 0), 'percentage', 'Rate')
        const term = formatForExcel(parseFloat(item.Term || item.YearsToMaturity || 0) || (parseFloat(item.MaturityDate) ? (new Date(item.MaturityDate) - new Date(item.IssueDate || Date.now())) / (365 * 24 * 60 * 60 * 1000) : 0), 'number', 'Term')
        appendixData.push([inst.name, name, ticker, faceValue, rate, term, valuationDate])
      })
    }
  }
  const appendixSheet = XLSX.utils.aoa_to_sheet(appendixData)
  appendixSheet['!cols'] = [{ wch: 18 }, { wch: 25 }, { wch: 15 }, { wch: 18 }, { wch: 12 }, { wch: 12 }, { wch: 18 }]
  XLSX.utils.book_append_sheet(workbook, appendixSheet, 'Appendix')

  for (const inst of report.instruments) {
    const instKey = inst.id || (inst.name === 'Money Market' ? 'money-market' : inst.name === 'Bonds' ? 'bonds' : 'tbills')
    let instrumentData = []
    const wf = await sessionManager.getInstrumentWorkflow(activeSession.value?.id, instKey)
    if (wf && wf.cleanedData && wf.cleanedData.length) instrumentData = wf.cleanedData
    else {
      const sid = activeSession.value?.id
      if (sid) {
        const saved = localStorage.getItem(`${instKey}_session_${sid}_clean`)
        if (saved) instrumentData = JSON.parse(saved)
      }
    }
    if (instrumentData.length) {
      const formattedData = instrumentData.map(row => formatRowForExcel(row))
      const sheet = XLSX.utils.json_to_sheet(formattedData)
      XLSX.utils.book_append_sheet(workbook, sheet, inst.name.substring(0, 31))
    }
  }
  XLSX.writeFile(workbook, `portfolio_report_${Date.now()}.xlsx`)
}

function formatRowForExcel(row) {
  const formatted = {}
  for (const [key, value] of Object.entries(row)) {
    if (isPercentageField(key)) {
      formatted[key] = formatForExcel(value, 'percentage', key)
    } else if (key.toLowerCase().includes('value') || key.toLowerCase().includes('price') || key.toLowerCase().includes('amount') || key.toLowerCase().includes('principal') || key.toLowerCase().includes('interest')) {
      formatted[key] = formatForExcel(value, 'money', key)
    } else {
      formatted[key] = formatForExcel(value, 'number', key)
    }
  }
  return formatted
}

async function downloadCombinedReport(format) {
  if (format === 'excel') { await exportToRealExcel(); return }
  await loadSavedData()
  const html = await generateReportHtml()
  if (!html) return
  const filename = `combined_report_${Date.now()}`
  if (format === 'json') {
    const report = reportPreviewData.value
    downloadBlob(JSON.stringify(report, null, 2), `${filename}.json`, 'application/json')
  } else if (format === 'csv') {
    const report = reportPreviewData.value
    let csvRows = [['Instrument', 'Metric', 'Value']]
    for (const inst of report.instruments) {
      for (const [key, val] of Object.entries(inst.calculations)) {
        if (key === 'completed' || key === 'timestamp') continue
        csvRows.push([inst.name, formatMetricName(key), formatMetricValue(key, val)])
      }
    }
    const csv = csvRows.map(row => row.join(',')).join('\n')
    downloadBlob(csv, `${filename}.csv`, 'text/csv')
  } else if (format === 'html') downloadBlob(html, `${filename}.html`, 'text/html')
  else if (format === 'pdf') { const win = window.open(); win.document.write(html); win.print() }
  else if (format === 'word') {
    try {
      const session = sessionManager.getActiveSession()
      const sessionId = session?.id || sessionManager.getActiveSessionId() || localStorage.getItem('dura_active_session_id')
      
      if (!sessionId) {
        alert('No active session found')
        return
      }
      
      console.log('Downloading Word report for session:', sessionId)
      
      const response = await fetch('http://localhost:5000/api/report/generate-word', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          report_html: html,
          instrument_type: route.params.type || null,
          file_name: `Dura-Capital-Combined-Report-${Date.now()}.docx`
        })
      })
      
      const result = await response.json()
      
      if (!result.success) {
        alert('Failed to generate Word report: ' + (result.message || 'Unknown error'))
        return
      }
      
      const downloadPath = `http://localhost:5000/api/report/download-word/${sessionId}`
      const downloadResponse = await fetch(downloadPath)
      if (!downloadResponse.ok) {
        alert('Failed to download the generated report')
        return
      }
      
      const blob = await downloadResponse.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = result.data?.file_name || `Dura-Capital-Combined-Report-${Date.now()}.docx`
      a.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      console.error('Error downloading Word report:', err)
      alert('Error downloading Word report: ' + err.message)
    }
  }
}

function downloadBlob(content, filename, mimeType) {
  const blob = new Blob([content], { type: mimeType })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

const autoSaveEnabled = ref(false)
let isSavingVersion = false

watch([rawData, cleanedData], () => {
  if (!autoSaveEnabled.value || skipAutoSave.value || isSaving.value || isSavingVersion) {
    return
  }
  debouncedSave()
}, { deep: true })



watch(() => activeTab.value, async (newTab) => {
  if (newTab === 'calculations' && hasCleanedData.value) {
    await calculateMetrics()
  }
  if (newTab === 'visualizations' && hasCleanedData.value && !yieldCurveData.value.length && !yieldCurveLoading.value) {
    if (!effectiveCountry.value) { selectedCountryOption.value = 'USA'; fredFilters.value.country = 'USA' }
    if (!effectiveMaturity.value) { const def = config.value.defaultMaturity; selectedMaturityOption.value = def; fredFilters.value.maturity = def }
    await fetchYieldCurve()
  }
}, { deep: true })

watch(() => instrumentType.value, async () => {
  await loadSavedTemplates()
})

watch(yieldCurveData, async () => {
  if (activeTab.value === 'visualizations' && yieldCurveData.value.length) {
    await nextTick()
    await renderYieldCurveChart()
  }
}, { deep: true })

let checkTimeout = null

async function checkAndReset() {
  if (checkTimeout) clearTimeout(checkTimeout)
  checkTimeout = setTimeout(async () => {
    const currentSessionId = sessionManager.getActiveSessionId() || route.query.session || null
    const currentInstrument = instrumentType.value
    if (currentInstrument !== lastInstrument || currentSessionId !== lastSessionId) {
      lastInstrument = currentInstrument
      lastSessionId = currentSessionId
      if (currentSessionId) {
        const s = await sessionManager.getSession(String(currentSessionId))
        activeSession.value = s || null
        if (s) {
          sessionManager.setActiveSession(s)
        }
      } else {
        activeSession.value = null
      }
      const loaded = await loadSavedData()
      if (!loaded) {
        if (!route.query.tab) activeTab.value = 'upload'
      } else {
        if (!route.query.tab) {
          const savedTab = (await sessionManager.getInstrumentWorkflow(activeSession.value?.id, instrumentType.value))?.last_tab
          if (savedTab && steps.value.some(s => s.tab === savedTab)) {
            activeTab.value = savedTab
          } else {
            activeTab.value = 'upload'
          }
        }
        if (cleanedData.value.length) await calculateMetrics()
        if (activeTab.value === 'visualizations' && !yieldCurveData.value.length) {
          if (!effectiveCountry.value) { selectedCountryOption.value = 'USA'; fredFilters.value.country = 'USA' }
          if (!effectiveMaturity.value) { const def = config.value.defaultMaturity; selectedMaturityOption.value = def; fredFilters.value.maturity = def }
          await fetchYieldCurve()
        }
      }
      debouncedSave()
    }
  }, 300)
}

onMounted(async () => {
  const qSid = route.query.session
  if (qSid) {
    const s = await sessionManager.getSession(String(qSid), true)
    if (s) {
      try {
        const versionsRes = await api.versionAPI.getVersions(s.id)
        if (versionsRes && versionsRes.success) {
          s.version_count = versionsRes.total || 0
          console.log(`Loaded session ${s.id} with actual version count: ${s.version_count}`)
        }
      } catch (e) {
        console.warn('Failed to fetch version count on mount:', e)
      }
      activeSession.value = s
      sessionManager.setActiveSession(s)
    }
  }
  if (!activeSession.value) {
    const current = sessionManager.getActiveSession()
    if (current) {
      const refreshed = await sessionManager.getSession(current.id, true)
      if (refreshed) {
        try {
          const versionsRes = await api.versionAPI.getVersions(refreshed.id)
          if (versionsRes && versionsRes.success) {
            refreshed.version_count = versionsRes.total || 0
          }
        } catch (e) {
          console.warn('Failed to fetch version count on mount:', e)
        }
        activeSession.value = refreshed
        sessionManager.setActiveSession(refreshed)
      } else {
        activeSession.value = current
        sessionManager.setActiveSession(current)
      }
    } else {
      const allSessions = await sessionManager.getAllSessions()
      if (allSessions.length > 0) {
        const mostRecent = allSessions[0]
        const s = await sessionManager.getSession(mostRecent.id, true)
        if (s) {
          try {
            const versionsRes = await api.versionAPI.getVersions(s.id)
            if (versionsRes && versionsRes.success) {
              s.version_count = versionsRes.total || 0
            }
          } catch (e) {
            console.warn('Failed to fetch version count on mount:', e)
          }
          activeSession.value = s
          sessionManager.setActiveSession(s)
          console.log('Most recent session loaded and set as active:', s.id)
        }
      }
    }
  }
  if (!activeSession.value) {
    const storedSession = localStorage.getItem('activeSession')
    if (storedSession) {
      try {
        const parsed = JSON.parse(storedSession)
        activeSession.value = parsed
        sessionManager.setActiveSession(parsed)
      } catch (e) {
        console.error('Failed to parse stored session:', e)
      }
    }
  }
  await checkAndReset()
  loadUploadHistory()
  await loadSavedTemplates()
  window.addEventListener('storage', () => checkAndReset())
  await loadFilterOptions()
  if (!effectiveMaturity.value) {
    const def = config.value.defaultMaturity
    selectedMaturityOption.value = def
    fredFilters.value.maturity = def
  }
  if (Object.keys(allCalculations.value).length) enrichCalculationsWithFred()
  if (!allCalculations.value.totalValue && activeSession.value) await loadSavedData()
  debouncedSave()
})

const handleSessionRestored = async (event) => {
  const { sessionId } = event.detail || {}
  if (sessionId && activeSession.value?.id === sessionId) {
    await loadSavedData()
    await refreshSessionVersionCount(sessionId)
    forceUpdate.value++
  }
}

onBeforeUnmount(() => {
  window.removeEventListener('storage', () => checkAndReset())
  window.removeEventListener('session-restored', handleSessionRestored)
  if (saveTimeout) clearTimeout(saveTimeout)
  saveSessionData()
})
</script>

<style scoped>
.instrument-page { padding: 20px; max-width: 1400px; margin: 0 auto; }
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 25px; padding: 16px 20px; background: white; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); flex-wrap: wrap; gap: 12px; }
.header-left { flex: 1; min-width: 200px; }
.header-left h1 { color: #0B2044; font-size: 26px; font-weight: 700; margin: 0 0 6px 0; }
.header-left .session-badge { display: inline-flex; align-items: center; gap: 6px; background: #e8ecf1; padding: 4px 12px; border-radius: 20px; font-size: 13px; color: #0B2044; }
.header-left .session-badge.warning { background: #fff3e0; color: #e65100; }
.header-left .version-badge { background: #1e88e5; color: white; padding: 0 8px; border-radius: 10px; font-size: 11px; margin-left: 6px; }
.header-right { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; margin-top: 4px; }
.btn-save-session { background: linear-gradient(135deg, #0B2044, #1E88E5); color: white; border: none; padding: 10px 20px; border-radius: 10px; font-size: 14px; font-weight: 600; cursor: pointer; display: inline-flex; align-items: center; gap: 8px; transition: all 0.3s; white-space: nowrap; }
.btn-save-session:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(11,32,68,0.3); }
.step-indicator { background: #f5f5f5; padding: 8px 16px; border-radius: 20px; font-size: 14px; font-weight: 600; color: #0B2044; white-space: nowrap; }
.progress-bar-container { margin-bottom: 30px; padding: 0 10px; }
.progress-steps { display: flex; justify-content: space-between; align-items: center; background: white; padding: 20px; border-radius: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); position: relative; }
.progress-step { flex: 1; text-align: center; cursor: pointer; position: relative; }
.progress-step.disabled { cursor: not-allowed; opacity: 0.5; }
.step-circle { width: 36px; height: 36px; background: #e0e0e0; color: #999; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; font-weight: 700; transition: all 0.3s; z-index: 2; position: relative; }
.progress-step.active .step-circle { background: #0B2044; color: white; box-shadow: 0 0 0 4px rgba(11,32,68,0.2); }
.progress-step.completed .step-circle { background: #4CAF50; color: white; }
.step-label { font-size: 11px; color: #999; margin-top: 8px; }
.progress-step.active .step-label { color: #0B2044; font-weight: 600; }
.tab-content-wrapper { overflow: auto; height: 100%; padding: 4px 0; }
.content-card { margin-bottom: 20px; }
.valuation-date-section { margin-bottom: 20px; padding: 12px; background: #f8f9ff; border-radius: 8px; border-left: 4px solid #0B2044; }
.valuation-date-section .filter-label { display: block; font-size: 13px; font-weight: 600; color: #0B2044; margin-bottom: 8px; }
.valuation-date-section .date-input { padding: 8px 12px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px; color: #333; width: 200px; }
.valuation-date-section .date-input:focus { outline: none; border-color: #0B2044; box-shadow: 0 0 0 3px rgba(11,32,68,0.1); }
.maturity-toggle { display: flex; gap: 4px; margin-bottom: 8px; }
.toggle-btn { flex: 1; padding: 6px 12px; border: 1px solid #ddd; border-radius: 4px; background: white; cursor: pointer; font-size: 12px; font-weight: 500; color: #666; transition: all 0.2s; }
.toggle-btn:hover { background: #f5f5f5; }
.toggle-btn.active { background: #0B2044; color: white; border-color: #0B2044; }
.date-range-inputs { display: flex; gap: 8px; }
.date-input-small { flex: 1; padding: 8px 12px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px; color: #333; }
.date-input-small:focus { outline: none; border-color: #0B2044; box-shadow: 0 0 0 3px rgba(11,32,68,0.1); }
.upload-area { border: 2px dashed #ccc; border-radius: 12px; padding: 50px; text-align: center; cursor: pointer; transition: all 0.3s; }
.upload-area:hover { border-color: #0B2044; background: #f8f9ff; }
.browse-link { color: #0B2044; cursor: pointer; font-weight: 600; }
.file-info { margin-top: 20px; padding: 12px; background: #f5f5f5; border-radius: 8px; display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.file-size { font-size: 11px; color: #999; margin-left: auto; }
.remove-btn { margin-left: auto; background: none; border: none; font-size: 20px; cursor: pointer; color: #f44336; }
.btn-preview, .btn-review-excel, .btn-mapping, .btn-view-workbook { display: inline-flex; align-items: center; gap: 6px; padding: 6px 12px; border-radius: 6px; font-size: 12px; cursor: pointer; border: none; margin-left: 10px; transition: all 0.2s; }
.btn-preview { background: #2196F3; color: white; }
.btn-preview:hover:not(:disabled) { background: #0b7dda; transform: translateY(-1px); }
.btn-preview:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-review-excel { background: #4CAF50; color: white; }
.btn-review-excel:hover:not(:disabled) { background: #45a049; transform: translateY(-1px); }
.btn-review-excel:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-mapping { background: #FF9800; color: white; }
.btn-mapping:hover:not(:disabled) { background: #F57C00; transform: translateY(-1px); }
.btn-mapping:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-view-workbook { background: #9C27B0; color: white; }
.btn-view-workbook:hover:not(:disabled) { background: #7B1FA2; transform: translateY(-1px); }
.btn-view-workbook:disabled { opacity: 0.5; cursor: not-allowed; }
.cleaning-operations-summary { margin-top: 20px; padding: 16px; background: #f8f9ff; border-radius: 8px; border-left: 4px solid #4CAF50; }
.operations-title { font-size: 14px; font-weight: 600; color: #0B2044; margin: 0 0 12px 0; }
.operations-list { list-style: none; padding: 0; margin: 0; }
.operation-item { display: flex; align-items: center; gap: 8px; padding: 6px 0; font-size: 13px; color: #333; }
.operation-item .v-icon { flex-shrink: 0; }
.btn-review-excel-small { background: #2196F3; color: white; border: none; padding: 4px 10px; border-radius: 6px; cursor: pointer; display: inline-flex; align-items: center; gap: 4px; font-size: 11px; transition: all 0.2s; }
.btn-review-excel-small:hover { background: #0b7dda; }
.mapping-dialog-title { background: #0B2044; color: white; padding: 16px 24px; }
.mapping-dialog-title .mapping-count { font-size: 14px; font-weight: 400; opacity: 0.8; }
.mapping-dialog-body { padding: 20px 24px 16px; }
.mapping-grid { display: flex; flex-direction: column; gap: 12px; margin: 16px 0; }
.mapping-row { display: flex; align-items: center; gap: 12px; }
.required-label { width: 140px; font-weight: 600; color: #0B2044; font-size: 14px; }
.dropdown-wrapper { flex: 1; display: flex; align-items: center; gap: 8px; }
.custom-currency-section { margin-top: 12px; padding: 12px; background: #f8f9ff; border-radius: 8px; border-left: 4px solid #9C27B0; }
.custom-currency-label { font-size: 13px; font-weight: 600; color: #0B2044; margin-bottom: 8px; display: block; }
.custom-currency-input-wrapper { position: relative; margin-top: 8px; }
.custom-currency-field { width: 100%; padding: 10px 12px; padding-right: 50px; border: 2px solid #e8ecf1; border-radius: 8px; font-size: 14px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; transition: all 0.3s; }
.custom-currency-field:focus { outline: none; border-color: #0B2044; box-shadow: 0 0 0 3px rgba(11,32,68,0.1); }
.custom-currency-field::placeholder { text-transform: none; letter-spacing: normal; font-weight: 400; }
.currency-code-badge { position: absolute; right: 12px; top: 50%; transform: translateY(-50%); font-size: 11px; color: #999; font-weight: 500; background: #f5f5f5; padding: 2px 6px; border-radius: 4px; }
.custom-currency-hint { font-size: 11px; color: #666; margin-top: 6px; }
.detected-values-section { margin-top: 24px; padding: 20px; background: #f8f9ff; border-radius: 12px; border-left: 4px solid #4CAF50; }
.detected-values-section h3 { font-size: 16px; font-weight: 600; color: #0B2044; margin: 0 0 8px 0; }
.detected-values-section .section-hint { font-size: 13px; color: #666; margin: 0 0 16px 0; }
.no-detection-message-cleaning { padding: 20px; background: #fff3cd; border-radius: 8px; border: 1px solid #ffc107; text-align: center; }
.no-detection-message-cleaning p { margin: 0; color: #856404; font-size: 14px; }
.detected-values-table { background: white; border-radius: 8px; overflow: hidden; border: 1px solid #e0e0e0; }
.detected-values-table .table-header { display: flex; background: #0B2044; color: white; font-weight: 600; font-size: 13px; }
.detected-values-table .table-header span { padding: 12px 16px; }
.detected-values-table .header-field { flex: 0 0 180px; }
.detected-values-table .header-value { flex: 1; }
.detected-values-table .header-status { flex: 0 0 100px; text-align: center; }
.detected-values-table .header-action { flex: 0 0 100px; text-align: center; }
.detected-values-table .table-row { display: flex; border-bottom: 1px solid #e0e0e0; transition: background 0.2s; }
.detected-values-table .table-row:last-child { border-bottom: none; }
.detected-values-table .table-row:hover { background: #f5f5f5; }
.detected-values-table .table-row.row-excluded { background: #ffebee; opacity: 0.7; }
.detected-values-table .table-row span { padding: 12px 16px; font-size: 13px; }
.detected-values-table .row-field { flex: 0 0 180px; font-weight: 600; color: #0B2044; }
.detected-values-table .row-value { flex: 1; display: flex; align-items: center; }
.detected-values-table .value-display { color: #333; }
.detected-values-table .row-status { flex: 0 0 100px; text-align: center; font-weight: 600; font-size: 12px; }
.detected-values-table .status-included { color: #4CAF50; }
.detected-values-table .status-excluded { color: #f44336; }
.detected-values-table .row-action { flex: 0 0 100px; text-align: center; display: flex; justify-content: center; align-items: center; }
.detected-values-table .btn-toggle-exclude { padding: 6px 12px; border-radius: 4px; font-size: 12px; font-weight: 600; cursor: pointer; border: none; transition: all 0.2s; }
.detected-values-table .btn-toggle-exclude.btn-exclude { background: #f44336; color: white; }
.detected-values-table .btn-toggle-exclude.btn-exclude:hover { background: #d32f2f; }
.detected-values-table .btn-toggle-exclude.btn-include { background: #4CAF50; color: white; }
.detected-values-table .btn-toggle-exclude.btn-include:hover { background: #45a049; }
.detected-values-summary { margin-top: 12px; padding: 8px 12px; background: #e8f5e9; border-radius: 6px; }
.detected-values-summary .summary-text { font-size: 13px; color: #2E7D32; font-weight: 500; }
.mapping-select { flex: 1; padding: 8px 36px 8px 12px; border: 1px solid #ccc; border-radius: 6px; font-size: 14px; background: white; cursor: pointer; appearance: none; -webkit-appearance: none; background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 8'%3E%3Cpath d='M1 1l5 5 5-5' stroke='%23999' stroke-width='1.5' fill='none'/%3E%3C/svg%3E"); background-repeat: no-repeat; background-position: right 12px center; padding-right: 36px; }
.mapping-select:focus { outline: none; border-color: #0B2044; box-shadow: 0 0 0 2px rgba(11,32,68,0.2); }
.saved-mappings-popup-title { background: linear-gradient(135deg, #0B2044, #1E88E5); color: white; padding: 20px 24px; font-size: 18px; font-weight: 700; }
.saved-mappings-popup-body { padding: 24px; background: #f8f9ff; }
.save-section { margin-bottom: 24px; padding: 16px; background: white; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
.save-row { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
.save-row .template-input { flex: 1; padding: 12px 16px; border: 2px solid #e8ecf1; border-radius: 8px; font-size: 14px; min-width: 200px; transition: all 0.3s; }
.save-row .template-input:focus { outline: none; border-color: #0B2044; box-shadow: 0 0 0 3px rgba(11,32,68,0.1); }
.save-row .template-input::placeholder { color: #999; }
.saved-mappings-list { max-height: 400px; overflow-y: auto; display: flex; flex-direction: column; gap: 12px; }
.saved-mappings-list::-webkit-scrollbar { width: 6px; }
.saved-mappings-list::-webkit-scrollbar-track { background: #f1f1f1; border-radius: 3px; }
.saved-mappings-list::-webkit-scrollbar-thumb { background: #c1c1c1; border-radius: 3px; }
.saved-mappings-list::-webkit-scrollbar-thumb:hover { background: #a1a1a1; }
.saved-mapping-item { background: white; border-radius: 12px; padding: 16px 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); transition: all 0.3s; border-left: 4px solid #0B2044; }
.saved-mapping-item:hover { transform: translateY(-2px); box-shadow: 0 4px 16px rgba(0,0,0,0.1); }
.mapping-name { font-size: 16px; font-weight: 700; color: #0B2044; margin-bottom: 4px; }
.mapping-meta { font-size: 13px; color: #666; margin-bottom: 12px; }
.mapping-actions { display: flex; gap: 10px; align-items: center; }
.btn-secondary.small { background: linear-gradient(135deg, #e0e0e0, #c0c0c0); color: #333; padding: 8px 16px; border-radius: 8px; font-size: 13px; font-weight: 600; border: none; cursor: pointer; transition: all 0.3s; }
.btn-secondary.small:hover { background: linear-gradient(135deg, #c0c0c0, #a0a0a0); transform: translateY(-1px); box-shadow: 0 4px 12px rgba(0,0,0,0.15); }
.btn-secondary.small.danger { background: linear-gradient(135deg, #f44336, #d32f2f); color: white; }
.btn-secondary.small.danger:hover { background: linear-gradient(135deg, #d32f2f, #c62828); }
.empty-state { text-align: center; padding: 40px 20px; color: #999; }
.empty-state p { font-size: 15px; margin: 0; }
.excel-dialog-title-no-logo { background: #f5f5f5; color: #0B2044; padding: 12px 24px; display: flex; align-items: center; border-bottom: 2px solid #d0d0d0; }
.excel-dialog-title-no-logo span { font-weight: 600; font-size: 18px; }
.btn-work-on-sheet { background: #0B2044; color: white; border: none; padding: 8px 20px; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; transition: all 0.2s; margin-right: 12px; }
.btn-work-on-sheet:hover { background: #1a3a6e; transform: translateY(-1px); box-shadow: 0 4px 12px rgba(11,32,68,0.2); }
.btn-auto-detect { background: #4CAF50; color: white; border: none; padding: 8px 20px; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; transition: all 0.2s; margin-right: 12px; }
.btn-auto-detect:hover:not(:disabled) { background: #45a049; transform: translateY(-1px); box-shadow: 0 4px 12px rgba(76,175,80,0.3); }
.btn-auto-detect:disabled { opacity: 0.6; cursor: not-allowed; }
.btn-auto-detect-green { background: #4CAF50; color: white; border: none; padding: 8px 20px; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; transition: all 0.2s; margin-right: 8px; }
.btn-auto-detect-green:hover:not(:disabled) { background: #45a049; transform: translateY(-1px); box-shadow: 0 4px 12px rgba(76,175,80,0.3); }
.btn-auto-detect-green:disabled { opacity: 0.6; cursor: not-allowed; }
.spin-animation { animation: spin 1s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
.detection-success-title { background: #4CAF50; color: white; padding: 16px 24px; display: flex; align-items: center; }
.detection-success-body { padding: 20px 24px; }
.currency-selection-section { margin-bottom: 20px; padding: 16px; background: #f8f9ff; border-radius: 8px; border: 1px solid #e8ecf1; }
.currency-label { display: block; font-weight: 600; color: #0B2044; margin-bottom: 12px; font-size: 14px; }
.currency-select-vuetify { margin-bottom: 12px; }
.custom-currency-input-wrapper { margin-top: 12px; }
.custom-currency-field-vuetify { margin-bottom: 8px; }
.currency-code-badge { font-size: 12px; color: #666; font-weight: 500; }
.detected-currencies-info { margin-top: 12px; padding: 8px 12px; background: #e8f5e9; border-radius: 6px; font-size: 13px; color: #2E7D32; }
.selected-currency-info { margin-top: 8px; padding: 8px 12px; background: #e3f2fd; border-radius: 6px; font-size: 13px; color: #1976D2; }
.detected-fields-list { display: flex; flex-direction: column; gap: 12px; margin-bottom: 16px; }
.detected-field-item { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; padding: 12px 16px; background: #f8f9ff; border-radius: 8px; border-left: 4px solid #4CAF50; }
.detected-field-label { font-weight: 600; color: #0B2044; font-size: 14px; margin-right: 8px; }
.detected-field-value { font-weight: 700; color: #2E7D32; font-size: 15px; margin-right: 8px; }
.detected-field-location { font-size: 11px; color: #999; font-style: italic; margin-left: 8px; }
.currency-variant-selector { margin-top: 8px; margin-left: auto; }
.currency-select { padding: 6px 12px; border: 1px solid #2196F3; border-radius: 6px; background: white; font-size: 13px; color: #0B2044; cursor: pointer; min-width: 150px; }
.currency-select:hover { border-color: #1976D2; background: #f0f8ff; }
.no-detection-message { padding: 16px; background: #FFF3E0; border-radius: 8px; border-left: 4px solid #FF9800; text-align: center; }
.no-detection-message p { margin: 4px 0; color: #E65100; }
.missing-fields-warning { padding: 12px 16px; background: #FFF3E0; border-radius: 8px; border-left: 4px solid #FF9800; }
.additional-fields-section { margin-top: 20px; padding: 16px; background: #f0f8ff; border-radius: 8px; border-left: 4px solid #2196F3; }
.additional-fields-section h4 { margin: 0 0 8px 0; font-size: 14px; color: #1976D2; }
.additional-fields-section .section-hint { margin: 0 0 12px 0; font-size: 12px; color: #666; }
.additional-field-item { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; padding: 8px 12px; background: white; border-radius: 6px; border-left: 3px solid #2196F3; margin-bottom: 6px; }
.additional-field-label { font-weight: 600; color: #0B2044; font-size: 13px; margin-right: 8px; }
.additional-field-value { font-weight: 600; color: #1976D2; font-size: 13px; margin-right: 8px; }
.additional-field-location { font-size: 10px; color: #999; font-style: italic; margin-left: 8px; }
.missing-fields-warning p { margin: 0 0 8px 0; font-weight: 600; color: #E65100; font-size: 14px; }
.missing-fields-warning ul { margin: 0; padding-left: 20px; }
.missing-fields-warning li { color: #E65100; font-size: 13px; margin-bottom: 4px; }
.multi-table-summary { padding: 12px 16px; background: #e8f5e9; border-radius: 8px; border-left: 4px solid #4CAF50; margin-bottom: 16px; font-size: 14px; color: #2E7D32; }
.multi-instruments-list { display: flex; flex-direction: column; gap: 16px; max-height: 400px; overflow-y: auto; }
.multi-instrument-item { padding: 16px; background: #f8f9ff; border-radius: 8px; border: 1px solid #e8ecf1; }
.multi-instrument-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid #e0e0e0; }
.table-name-badge { background: #0B2044; color: white; padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: 500; }
.field-count-badge { background: #4CAF50; color: white; padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: 500; }
.multi-instrument-fields { display: flex; flex-direction: column; gap: 8px; margin-bottom: 12px; }
.multi-detected-field-item { display: flex; justify-content: space-between; align-items: center; padding: 8px 12px; background: white; border-radius: 6px; border-left: 3px solid #4CAF50; }
.multi-detected-field-label { font-weight: 600; color: #0B2044; font-size: 13px; }
.multi-detected-field-value { font-weight: 700; color: #2E7D32; font-size: 14px; }
.multi-detected-field-location { font-size: 10px; color: #999; font-style: italic; margin-left: 8px; }
.multi-missing-fields { padding: 8px 12px; background: #FFF3E0; border-radius: 6px; border-left: 3px solid #FF9800; font-size: 12px; }
.multi-missing-fields .missing-label { font-weight: 600; color: #E65100; margin-right: 6px; }
.saved-mappings-popup-title { background: #0B2044; color: white; padding: 16px 24px; }
.saved-mappings-popup-body { padding: 20px 24px; }
.saved-mappings-list { display: flex; flex-direction: column; gap: 12px; max-height: 400px; overflow-y: auto; }
.saved-mapping-item { padding: 16px; background: #f8f9ff; border-radius: 8px; border: 1px solid #e8ecf1; }
.mapping-name { font-weight: 600; color: #0B2044; font-size: 14px; margin-bottom: 4px; }
.mapping-meta { font-size: 12px; color: #999; margin-bottom: 8px; }
.mapping-actions { display: flex; gap: 8px; }
.btn-secondary.small.danger { background: #f44336; color: white; }
.btn-secondary.small.danger:hover { background: #d32f2f; }
.excel-dialog-title-white { background: white; color: #0B2044; padding: 16px 24px; display: flex; align-items: center; border-bottom: 2px solid #e0e0e0; }
.excel-dialog-title-white .logo { height: 40px; width: auto; object-fit: contain; }
.excel-dialog-title-white .header-left { display: flex; align-items: center; gap: 16px; }
.excel-dialog-title-white .header-title h4 { margin: 0; font-size: 18px; font-weight: 600; color: #0B2044; }
.excel-dialog-title-white .header-meta { margin: 2px 0 0 0; font-size: 13px; color: #666; }
.excel-dialog-title-white .btn-close-dialog { background: transparent; border: none; color: #666; cursor: pointer; padding: 8px; border-radius: 50%; font-size: 20px; }
.excel-dialog-title-white .btn-close-dialog:hover { background: #f0f0f0; color: #0B2044; }
.btn-close-dialog { background: transparent; border: none; color: #666; cursor: pointer; padding: 8px; border-radius: 50%; }
.btn-close-dialog:hover { background: #f0f0f0; color: #0B2044; }
.excel-dialog-content { padding: 0; height: calc(100vh - 140px); }
.required-columns { margin: 20px 0; }
.value-input { width: 100%; padding: 6px 10px; border: 1px solid #e0e0e0; border-radius: 4px; font-size: 13px; font-family: inherit; background: white; transition: border-color 0.2s; }
.value-input:focus { outline: none; border-color: #0B2044; box-shadow: 0 0 0 2px rgba(11, 32, 68, 0.1); }
.add-field-section { margin-top: 20px; padding: 16px; background: #f0f8ff; border-radius: 8px; border-left: 4px solid #2196F3; }
.add-field-section h4 { margin: 0 0 8px 0; font-size: 14px; color: #1976D2; }
.add-field-section .section-hint { margin: 0 0 12px 0; font-size: 12px; color: #666; }
.add-field-form { display: flex; gap: 8px; align-items: center; }
.add-field-input { flex: 1; padding: 8px 12px; border: 1px solid #e0e0e0; border-radius: 6px; font-size: 13px; font-family: inherit; }
.add-field-input:focus { outline: none; border-color: #2196F3; box-shadow: 0 0 0 2px rgba(33, 150, 243, 0.1); }
.btn-add-field { padding: 8px 16px; background: #2196F3; color: white; border: none; border-radius: 6px; font-size: 13px; font-weight: 500; cursor: pointer; transition: background 0.2s; }
.btn-add-field:hover { background: #1976D2; }
.calculating-animation { display: flex; align-items: center; justify-content: center; gap: 8px; padding: 20px; color: #666; font-size: 14px; }
.spin-animation { animation: spin 1s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
.value-input.placeholder { color: #999; font-style: italic; }
.btn-clear-value { position: absolute; right: 8px; top: 50%; transform: translateY(-50%); background: #f44336; color: white; border: none; border-radius: 50%; width: 20px; height: 20px; font-size: 14px; cursor: pointer; display: flex; align-items: center; justify-content: center; line-height: 1; opacity: 0.7; transition: opacity 0.2s; }
.btn-clear-value:hover { opacity: 1; }
.row-value { position: relative; display: flex; align-items: center; flex: 1; }
.required-columns h4 { color: #0B2044; font-size: 16px; font-weight: 600; margin-bottom: 16px; display: flex; align-items: center; gap: 8px; }
.required-columns h4::before { content: '📋'; font-size: 18px; }
.columns-list { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 10px; }
.column-badge { background: linear-gradient(135deg, #e8ecf1, #f5f7fa); padding: 8px 16px; border-radius: 24px; font-size: 13px; font-weight: 500; display: inline-flex; align-items: center; gap: 8px; border: 1px solid #e0e0e0; transition: all 0.2s; }
.column-badge:hover { transform: translateY(-2px); box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
.column-badge .badge-icon { font-weight: 700; font-size: 14px; }
.column-badge.missing-column { background: linear-gradient(135deg, #FFEBEE, #FFCDD2); color: #c62828; border-color: #ef9a9a; }
.column-badge.mapped-column { background: linear-gradient(135deg, #E8F5E9, #C8E6C9); color: #2E7D32; border-color: #a5d6a7; }
.extracted-values-table { background: white; border-radius: 12px; border: 1px solid #e0e0e0; overflow: hidden; margin-top: 16px; }
.table-header { display: grid; grid-template-columns: 1fr 1fr 120px; gap: 0; background: linear-gradient(135deg, #0B2044, #1E88E5); color: white; padding: 12px 16px; font-weight: 600; font-size: 13px; }
.header-field, .header-value, .header-status { padding: 4px 8px; }
.table-row { display: grid; grid-template-columns: 1fr 1fr 120px; gap: 0; padding: 12px 16px; border-bottom: 1px solid #f0f0f0; transition: background 0.2s; align-items: center; }
.table-row:hover { background: #f8f9ff; }
.table-row:last-child { border-bottom: none; }
.table-row.row-missing { background: #FFF3E0; }
.table-row.row-missing:hover { background: #FFE0B2; }
.row-field { font-weight: 600; color: #0B2044; font-size: 13px; padding: 4px 8px; }
.row-value { padding: 4px 8px; }
.value-text { color: #333; font-size: 14px; font-weight: 500; }
.value-placeholder { color: #999; font-style: italic; font-size: 13px; }
.row-status { font-size: 12px; font-weight: 600; padding: 4px 8px; text-align: center; }
.row-status:not(.status-missing) { color: #2E7D32; background: #E8F5E9; padding: 4px 8px; border-radius: 12px; }
.row-status.status-missing { color: #c62828; background: #FFEBEE; padding: 4px 8px; border-radius: 12px; }
.values-summary { margin-top: 16px; padding: 12px 16px; background: linear-gradient(135deg, #f8f9ff, #eef2ff); border-radius: 12px; border-left: 4px solid #0B2044; }
.summary-text { font-size: 13px; font-weight: 500; color: #0B2044; }
.success-message { margin-top: 10px; padding: 10px 16px; background: linear-gradient(135deg, #E8F5E9, #C8E6C9); border-radius: 10px; display: flex; align-items: center; gap: 10px; font-size: 13px; font-weight: 500; color: #2E7D32; border: 1px solid #a5d6a7; }
.success-icon { font-size: 16px; }
.warning-message { margin-top: 10px; padding: 10px 16px; background: linear-gradient(135deg, #FFF3E0, #FFE0B2); border-radius: 10px; display: flex; align-items: center; gap: 10px; font-size: 13px; font-weight: 500; color: #E65100; border: 1px solid #FFB74D; }
.warning-icon { font-size: 16px; }
.cleaning-options-panel { background: #f8f9ff; padding: 20px; border-radius: 12px; margin-bottom: 20px; }
.filter-scroll-container { max-height: 200px; overflow-y: auto; border: 1px solid #e0e0e0; border-radius: 8px; background: #fafafa; margin: 12px 0; padding: 8px 4px; }
.options-list { display: flex; flex-direction: column; gap: 8px; }
.option-checkbox { display: flex; align-items: center; gap: 8px; font-size: 14px; padding: 4px 8px; border-radius: 4px; transition: background 0.1s; flex-wrap: wrap; }
.option-checkbox:hover { background: #f0f0f0; }
.option-checkbox select, .option-checkbox input[type="text"] { margin-left: 4px; padding: 2px 6px; font-size: 13px; border: 1px solid #ccc; border-radius: 4px; }
.date-format-dropdown { margin-left: 24px; margin-top: 8px; margin-bottom: 8px; display: block; }
.date-format-select { padding: 6px 12px; border: 1px solid #ccc; border-radius: 6px; font-size: 13px; background: white; cursor: pointer; min-width: 200px; display: block; }
.date-format-select-inline { margin-left: 8px; padding: 4px 8px; border: 1px solid #ccc; border-radius: 4px; font-size: 12px; background: white; cursor: pointer; min-width: 120px; }
.date-format-select-inline:disabled { background: #f5f5f5; cursor: not-allowed; opacity: 0.6; }
.date-format-select:disabled { background: #f5f5f5; cursor: not-allowed; opacity: 0.6; }
.date-format-select:focus, .date-format-select-inline:focus { outline: none; border-color: #0B2044; box-shadow: 0 0 0 2px rgba(11,32,68,0.1); }
.cleaning-buttons { display: flex; gap: 12px; margin-top: 15px; flex-wrap: wrap; }
.summary-cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 20px; margin-bottom: 30px; }
.summary-card { background: linear-gradient(135deg, #1B5E20, #4CAF50); padding: 20px; border-radius: 16px; color: white; text-align: center; display: flex; flex-direction: column; align-items: center; justify-content: center; cursor: pointer; transition: transform 0.2s; }
.summary-card.total { background: linear-gradient(135deg, #1B5E20, #4CAF50); }
.summary-card.rate { background: linear-gradient(135deg, #0D47A1, #2196F3); }
.summary-card.count { background: linear-gradient(135deg, #E65100, #FF9800); }
.summary-card:hover { transform: translateY(-3px); box-shadow: 0 6px 12px rgba(0,0,0,0.15); }
.card-label { font-size: 14px; opacity: 0.9; margin-bottom: 8px; }
.card-value { font-size: 28px; font-weight: 700; }
.calculations-section { margin-top: 10px; }
.calculations-section h3 { color: #0B2044; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 2px solid #0B2044; }
.calculations-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 30px; }
.calculation-card { padding: 16px; background: #f8f9ff; border-radius: 12px; border: 1px solid #e8ecf1; text-align: center; transition: transform 0.2s; cursor: pointer; min-height: 100px; display: flex; flex-direction: column; justify-content: center; }
.calculation-card:hover { transform: translateY(-3px); box-shadow: 0 6px 16px rgba(0,0,0,0.08); }
.calc-name { font-size: 13px; color: #666; margin-bottom: 8px; }
.calc-value { font-size: 22px; font-weight: 700; color: #0B2044; }
.comparison-card { background: linear-gradient(135deg, #f8f9ff, #eef2ff); border-radius: 12px; padding: 16px; margin-bottom: 20px; display: flex; justify-content: space-around; align-items: center; flex-wrap: wrap; gap: 15px; }
.comparison-item { text-align: center; }
.comparison-label { font-size: 13px; color: #666; display: block; }
.comparison-value { font-size: 24px; font-weight: 700; }
.comparison-value.portfolio { color: #0B2044; }
.comparison-value.market { color: #1E88E5; }
.comparison-difference { font-size: 16px; font-weight: 600; padding: 4px 12px; border-radius: 20px; }
.comparison-difference.positive { background: #e8f5e9; color: #2e7d32; }
.comparison-difference.negative { background: #ffebee; color: #c62828; }
.btn-calculated-instruments { background: #0B2044; color: white; border: none; padding: 8px 16px; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; transition: all 0.2s; }
.btn-calculated-instruments:hover { background: #1a3a6e; transform: translateY(-1px); box-shadow: 0 4px 12px rgba(11,32,68,0.2); }
.viewing-badge { background: #e8f5e9; color: #2e7d32; padding: 4px 12px; border-radius: 20px; font-size: 13px; display: inline-flex; align-items: center; gap: 4px; margin-left: 12px; }
.popup-header-white { display: flex; justify-content: space-between; align-items: center; padding: 16px 24px; background: white; border-bottom: 2px solid #e0e0e0; flex-shrink: 0; }
.popup-header-white .header-left { display: flex; align-items: center; gap: 16px; }
.popup-header-white .logo { height: 40px; width: auto; object-fit: contain; }
.popup-header-white .header-title h4 { margin: 0; font-size: 18px; font-weight: 600; color: #0B2044; }
.popup-header-white .header-meta { margin: 2px 0 0 0; font-size: 13px; color: #666; }
.popup-header-white .close-btn { background: transparent; border: none; color: #666; cursor: pointer; font-size: 24px; padding: 4px 8px; border-radius: 50%; }
.popup-header-white .close-btn:hover { background: #f0f0f0; color: #0B2044; }
.popup-body { flex: 1; overflow-y: auto; padding: 20px; }
.popup-instruction { color: #666; margin-bottom: 16px; font-size: 14px; }
.search-bar-container { position: relative; margin-bottom: 16px; display: flex; align-items: center; }
.search-input { width: 100%; padding: 10px 16px 10px 40px; border: 1px solid #e0e0e0; border-radius: 8px; font-size: 14px; background: white; transition: all 0.3s; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
.search-input:focus { outline: none; border-color: #0B2044; box-shadow: 0 0 0 3px rgba(11,32,68,0.1); }
.search-input::placeholder { color: #999; }
.search-icon { position: absolute; left: 12px; color: #999; font-size: 18px; }
.popup-footer { display: flex; justify-content: flex-end; align-items: center; gap: 12px; padding: 12px 24px; background: #f9fafc; border-top: 1px solid #e0e0e0; flex-shrink: 0; flex-wrap: wrap; }
.valuation-date-footer { color: #666; font-size: 13px; }
.viewing-indicator { display: inline-flex; align-items: center; gap: 4px; color: #2e7d32; font-size: 14px; }
.navigation-buttons { display: flex; gap: 15px; justify-content: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e0e0e0; flex-wrap: wrap; }
.btn-primary { background: linear-gradient(135deg, #0B2044, #1E88E5); color: white; border: none; padding: 12px 28px; border-radius: 10px; font-size: 14px; font-weight: 600; cursor: pointer; transition: all 0.3s; }
.btn-primary:hover:not(:disabled) { transform: translateY(-2px); box-shadow: 0 6px 15px rgba(11,32,68,0.3); }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-secondary { background: white; color: #0B2044; border: 2px solid #0B2044; padding: 12px 28px; border-radius: 10px; font-size: 14px; font-weight: 600; cursor: pointer; transition: all 0.3s; }
.btn-secondary:hover { background: #0B2044; color: white; transform: translateY(-2px); }
.excel-table-wrapper { overflow: auto; border: 1px solid #d4d4d4; border-radius: 4px; background: white; max-height: 500px; margin: 16px 0; }
.pagination-controls { display: flex; justify-content: center; align-items: center; gap: 10px; padding: 16px; background: #f8f9fa; border-radius: 8px; margin-top: 16px; }
.pagination-controls button { padding: 8px 16px; border: 1px solid #0B2044; background: white; color: #0B2044; border-radius: 6px; cursor: pointer; font-size: 13px; font-weight: 600; transition: all 0.2s; }
.pagination-controls button:hover:not(:disabled) { background: #0B2044; color: white; }
.pagination-controls button:disabled { opacity: 0.5; cursor: not-allowed; }
.pagination-controls span { font-size: 13px; font-weight: 600; color: #0B2044; min-width: 100px; text-align: center; }
.excel-table { width: 100%; border-collapse: collapse; font-size: 13px; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #000; border: 1px solid #d0d0d0; }
.excel-table thead { position: sticky; top: 0; z-index: 10; }
.excel-table th { background: #0B2044; color: white; border: 1px solid #1a3a6e; padding: 10px 14px; text-align: left; font-weight: 600; font-size: 12px; white-space: nowrap; letter-spacing: 0.3px; }
.excel-table td { border: 1px solid #d4d4d4; padding: 8px 14px; text-align: left; font-size: 13px; font-variant-numeric: tabular-nums; }
.excel-table tbody tr:nth-child(even) { background: #f9fafc; }
.excel-table tbody tr:hover { background: #e8f0fe; }
.excel-table tbody tr.selected-row { background: #bbdefb; font-weight: bold; }
.excel-table tfoot tr.total-row { background: #0B2044 !important; color: white; font-weight: 700; }
.excel-table tfoot td { border: 1px solid #1a3a6e; padding: 10px 14px; font-weight: 700; font-size: 14px; }
.excel-table tfoot td:first-child { text-align: right; padding-right: 20px; }
.sortable-header { cursor: pointer; transition: background 0.2s; }
.sortable-header:hover { background: #1a3a6e; }
.sort-indicator { margin-left: 6px; font-size: 10px; color: #fff; }
.excel-popup-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.6); z-index: 999999 !important; display: flex; align-items: center; justify-content: center; padding: 20px; }
.excel-popup-content { background: white; border-radius: 12px; max-width: 95%; max-height: 90vh; width: 1400px; display: flex; flex-direction: column; box-shadow: 0 25px 60px rgba(0,0,0,0.3); overflow: hidden; }
.filters-row { display: flex; gap: 20px; align-items: flex-end; margin-bottom: 20px; flex-wrap: wrap; }
.filter-group label { display: block; font-size: 12px; font-weight: 600; color: #0B2044; margin-bottom: 4px; }
.filter-group { position: relative; display: flex; align-items: center; flex-wrap: wrap; flex: 1; min-width: 150px; }
.filter-select { width: 100%; padding: 10px 32px 10px 12px; border: 1px solid #ccc; border-radius: 8px; background: linear-gradient(to bottom, #ffffff 0%, #f5f7fa 100%); color: #0B2044; font-size: 14px; cursor: pointer; transition: border 0.2s, box-shadow 0.2s; box-shadow: 0 2px 4px rgba(0,0,0,0.08), inset 0 1px 2px rgba(255,255,255,0.8); appearance: none; -webkit-appearance: none; }
.filter-select:focus { outline: none; border-color: #0B2044; box-shadow: 0 0 0 3px rgba(11,32,68,0.15), 0 4px 8px rgba(0,0,0,0.1); }
.filter-group .filter-arrow { position: absolute; right: 12px; top: 50%; transform: translateY(-50%); pointer-events: none; font-size: 14px; color: #0B2044; font-weight: bold; }
.filter-custom-input { width: 100%; padding: 8px 12px; margin-top: 4px; border: 1px solid #ccc; border-radius: 6px; font-size: 13px; background: white; transition: border 0.2s; }
.filter-custom-input:focus { outline: none; border-color: #0B2044; box-shadow: 0 0 0 2px rgba(11,32,68,0.1); }
.chart-container--fred { position: relative; height: 400px; width: 100%; background: white; border-radius: 8px; padding: 10px; }
.chart-container--fred canvas { width: 100% !important; height: 100% !important; }
.loading-container, .error-container { text-align: center; padding: 40px; }
.spin { animation: spin 1s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
.visualization-placeholder { text-align: center; padding: 60px; background: #f8f9ff; border-radius: 12px; }
.visualization-placeholder h3 { color: #0B2044; margin: 20px 0 10px; }
.visualization-placeholder p { color: #666; margin-bottom: 20px; }
.workflow-options { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 16px; }
.workflow-option-btn { background: #f8f9ff; border: 2px solid #e8ecf1; border-radius: 8px; padding: 16px; cursor: pointer; transition: all 0.2s; display: flex; flex-direction: column; align-items: center; gap: 8px; font-weight: 600; color: #0B2044; }
.workflow-option-btn:hover { border-color: #0B2044; background: white; transform: translateY(-2px); }
.report-options { padding: 20px; }
.instrument-selection { background: #f8f9ff; padding: 20px; border-radius: 12px; margin-bottom: 20px; }
.selection-cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin: 20px 0; }
.selection-card { display: flex; flex-direction: column; align-items: center; gap: 12px; padding: 20px 16px; background: white; border-radius: 12px; cursor: pointer; transition: all 0.2s; border: 2px solid #e0e0e0; position: relative; text-align: center; }
.selection-card:hover { transform: translateY(-2px); box-shadow: 0 4px 8px rgba(0,0,0,0.1); border-color: #0B2044; }
.selection-card.active { border-color: #0B2044; background: #f8f9ff; }
.check-indicator { position: absolute; top: 12px; right: 12px; }
.selection-actions { display: flex; gap: 10px; justify-content: center; margin-top: 10px; flex-wrap: wrap; }
.report-actions { display: flex; flex-wrap: wrap; gap: 10px; justify-content: center; margin-bottom: 10px; }
.btn-preview { background: #673AB7; color: white; padding: 8px 16px; border-radius: 6px; border: none; cursor: pointer; display: inline-flex; align-items: center; gap: 5px; }
.kpi-card { background: white; border-radius: 20px; padding: 18px; display: flex; align-items: center; gap: 12px; position: relative; overflow: hidden; cursor: pointer; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05); transition: all 0.3s ease; }
.kpi-card.simple-kpi { padding: 20px; justify-content: center; text-align: center; }
.kpi-card.simple-kpi .kpi-info { text-align: center; }
.kpi-card.simple-kpi .kpi-value { font-size: 20px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 100%; }
.kpi-top-bar { position: absolute; top: 0; left: 0; right: 0; height: 4px; background: linear-gradient(90deg, #0B2044, #1E88E5, #4CAF50); transform: scaleX(1); }
.kpi-card:hover { transform: translateY(-5px); box-shadow: 0 12px 28px rgba(0, 0, 0, 0.15); }
.kpi-icon { width: 52px; height: 52px; border-radius: 14px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; transition: transform 0.3s ease; }
.kpi-card:hover .kpi-icon { transform: scale(1.05); }
.kpi-content { display: flex; align-items: center; gap: 12px; height: 100%; }
.kpi-info { flex: 1; }
.kpi-value { font-size: 20px; font-weight: 800; color: #0B2044; }
.kpi-title { font-size: 10px; color: #888; }
.cleaning-summary-cards { margin-bottom: 24px; }
.btn-json { background: #607d8b; color: white; padding: 8px 16px; border-radius: 6px; border: none; cursor: pointer; display: inline-flex; align-items: center; gap: 5px; }
.btn-csv { background: #4caf50; color: white; padding: 8px 16px; border-radius: 6px; border: none; cursor: pointer; display: inline-flex; align-items: center; gap: 5px; }
.btn-html { background: #ff9800; color: white; padding: 8px 16px; border-radius: 6px; border: none; cursor: pointer; display: inline-flex; align-items: center; gap: 5px; }
.btn-pdf { background: #f44336; color: white; padding: 8px 16px; border-radius: 6px; border: none; cursor: pointer; display: inline-flex; align-items: center; gap: 5px; }
.btn-word { background: #2196f3; color: white; padding: 8px 16px; border-radius: 6px; border: none; cursor: pointer; display: inline-flex; align-items: center; gap: 5px; }
.btn-excel { background: #8bc34a; color: white; padding: 8px 16px; border-radius: 6px; border: none; cursor: pointer; display: inline-flex; align-items: center; gap: 5px; }
.empty-state { text-align: center; padding: 60px; color: #999; }
.empty-state p { margin: 20px 0; }
.upload-history { margin-top: 20px; padding: 15px; background: #f8f9ff; border-radius: 12px; }
.history-list { max-height: 200px; overflow-y: auto; }
.history-item { display: flex; align-items: center; gap: 12px; padding: 8px 12px; border-bottom: 1px solid #eee; cursor: pointer; transition: background 0.2s; flex-wrap: wrap; }
.history-item:hover { background: #e8ecf1; }
.history-item small { font-size: 11px; color: #666; margin-left: auto; }
.btn-delete-history { background: none; border: none; cursor: pointer; color: #f44336; font-size: 16px; }
.excel-viewer-button { margin-bottom: 20px; text-align: right; }
.formula-dialog-title { background: #0B2044; color: white; }
.formula-content { padding: 20px; }
.formula-section { margin-bottom: 20px; }
.formula-section h4 { color: #0B2044; margin-bottom: 8px; font-size: 14px; }
.formula-text { font-size: 16px; padding: 16px; background: #f8f9ff; border-radius: 8px; margin-top: 8px; font-family: 'Courier New', monospace; }
.calculation-details { margin-top: 20px; }
.calculation-details h4 { color: #0B2044; margin-bottom: 12px; font-size: 14px; }
.calculation-steps { display: flex; flex-direction: column; gap: 12px; }
.calculation-step { background: #f8f9ff; padding: 12px; border-radius: 8px; border-left: 4px solid #0B2044; }
.step-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
.step-label { font-weight: 600; color: #0B2044; font-size: 13px; }
.step-value { font-weight: 700; color: #1E88E5; font-size: 14px; font-family: 'Courier New', monospace; }
.step-formula { font-size: 12px; color: #666; font-style: italic; margin-top: 4px; }
.breakdown-section { margin-top: 16px; }
.breakdown-section button { width: 100%; margin-top: 8px; }
.breakdown-components { margin-top: 12px; }
.breakdown-components h5 { color: #0B2044; margin-bottom: 12px; font-size: 13px; }
.component-breakdown { background: #e8ecf1; padding: 12px; border-radius: 8px; margin-bottom: 12px; border-left: 4px solid #1E88E5; }
.component-header { margin-bottom: 8px; }
.component-name { font-weight: 700; color: #0B2044; font-size: 14px; }
.component-calculation { margin-bottom: 4px; }
.component-data { font-weight: 700; color: #1E88E5; font-size: 13px; font-family: 'Courier New', monospace; }
.component-formula { font-size: 11px; color: #666; font-style: italic; margin-top: 4px; }
.preview-info { font-size: 12px; color: #666; margin-bottom: 8px; }
.excel-preview-section { margin-top: 20px; padding: 16px; background: #fafafa; border-radius: 12px; }
.preview-section { margin-top: 20px; padding: 16px; background: #fafafa; border-radius: 12px; }
.excel-scroll-wrapper { overflow-x: auto; }
.highlight-box { background: #e8f5e9; padding: 12px; border-radius: 8px; margin-bottom: 20px; }
.fred-meta { display: block; margin-top: 8px; color: #666; font-size: 12px; }
.chart-footer { margin-top: 10px; text-align: center; color: #666; font-size: 12px; }
.summary-report { padding: 10px 0; }
.summary-section { margin-bottom: 30px; }
.summary-section h3 { font-size: 18px; color: #0B2044; border-bottom: 2px solid #0B2044; padding-bottom: 8px; margin-bottom: 16px; }
.summary-grid { display: grid; gap: 12px; }
.summary-grid.two-col { grid-template-columns: repeat(2, 1fr); }
.summary-grid.three-col { grid-template-columns: repeat(3, 1fr); }
.summary-item { background: #f8f9ff; padding: 12px 16px; border-radius: 6px; display: flex; justify-content: space-between; align-items: center; border: 1px solid #e8ecf1; }
.summary-item .label { font-weight: 600; color: #0B2044; }
.summary-item .value { font-weight: 500; color: #333; }
.summary-worksheet-selector { margin-bottom: 20px; display: flex; align-items: center; gap: 12px; }
.summary-worksheet-selector label { font-weight: 600; color: #0B2044; }
.summary-worksheet-selector select { padding: 8px 12px; border-radius: 6px; border: 1px solid #ccc; background: white; font-size: 14px; min-width: 200px; }
.field-detection-card { margin-top: 20px; padding: 16px; background: #f8f9ff; border-radius: 12px; border: 1px solid #e8ecf1; }
.field-detection-header { display: flex; align-items: center; gap: 8px; font-weight: 600; color: #0B2044; margin-bottom: 12px; }
.btn-toggle-detection { margin-left: auto; background: #0B2044; color: white; border: none; padding: 4px 12px; border-radius: 6px; font-size: 12px; cursor: pointer; }
.detection-summary { display: flex; flex-wrap: wrap; gap: 16px; margin-bottom: 12px; }
.detection-stat { font-size: 13px; color: #333; }
.detection-stat strong { color: #0B2044; }
.detection-stat.input strong { color: #4CAF50; }
.detection-stat.existing strong { color: #2196F3; }
.detection-stat.derived strong { color: #FF9800; }
.detection-stat.missing strong { color: #f44336; }
.detection-details { margin-top: 12px; padding-top: 12px; border-top: 1px solid #e8ecf1; }
.detection-field-item { display: grid; grid-template-columns: 2fr 1.5fr 1fr 1.5fr 0.8fr; gap: 8px; padding: 8px 0; border-bottom: 1px solid #eee; font-size: 12px; align-items: center; }
.detection-field-item:last-child { border-bottom: none; }
.field-name { font-weight: 600; color: #0B2044; }
.field-value { color: #333; }
.field-type { padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; text-transform: uppercase; }
.field-type.input { background: #e8f5e9; color: #4CAF50; }
.field-type.existing { background: #e3f2fd; color: #2196F3; }
.field-type.derived { background: #fff3e0; color: #FF9800; }
.field-type.missing { background: #ffebee; color: #f44336; }
.field-source { color: #666; font-size: 11px; }
.field-confidence { font-weight: 600; color: #0B2044; text-align: right; }
.summary-tabs { display: flex; gap: 8px; margin-bottom: 24px; border-bottom: 2px solid #e8ecf1; padding-bottom: 16px; }
.summary-tab { display: flex; align-items: center; gap: 8px; padding: 10px 20px; border: none; background: #f5f5f5; border-radius: 8px; font-size: 14px; font-weight: 600; cursor: pointer; transition: all 0.2s; color: #666; }
.summary-tab:hover:not(:disabled) { background: #e8ecf1; color: #0B2044; }
.summary-tab.active { background: #0B2044; color: white; }
.summary-tab:disabled { opacity: 0.4; cursor: not-allowed; }
.tab-count { background: rgba(255,255,255,0.2); padding: 2px 8px; border-radius: 12px; font-size: 12px; }
.summary-tab.active .tab-count { background: rgba(255,255,255,0.3); }
.summary-section { margin-bottom: 32px; padding: 20px; background: #f8f9ff; border-radius: 12px; border: 1px solid #e8ecf1; }
.section-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; padding-bottom: 12px; border-bottom: 2px solid #e8ecf1; }
.section-header h3 { display: flex; align-items: center; gap: 10px; margin: 0; color: #0B2044; font-size: 18px; font-weight: 600; }
.worksheet-badge { background: #4CAF50; color: white; padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 600; margin-left: 12px; }
.btn-sm { padding: 6px 12px; font-size: 13px; }
.previous-summaries-list { display: flex; flex-direction: column; gap: 12px; }
.summary-item-card { background: white; padding: 16px; border-radius: 8px; border: 1px solid #e8ecf1; transition: all 0.2s; }
.summary-item-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.08); border-color: #0B2044; }
.summary-item-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.summary-item-name { font-weight: 600; color: #0B2044; font-size: 15px; }
.summary-item-worksheet { background: #e3f2fd; color: #1976D2; padding: 4px 10px; border-radius: 6px; font-size: 12px; font-weight: 600; }
.summary-item-details { display: flex; gap: 20px; flex-wrap: wrap; }
.summary-detail { display: flex; align-items: center; gap: 6px; }
.detail-label { font-size: 13px; color: #666; font-weight: 500; }
.detail-value { font-size: 14px; color: #0B2044; font-weight: 600; }
.show-more-indicator { text-align: center; padding: 12px; color: #666; font-style: italic; font-size: 13px; }
.analytics-pills { display: flex; flex-wrap: wrap; gap: 16px; justify-content: space-between; margin: 12px 0; }
.analytics-pill { flex: 1; min-width: 160px; background: #f8faff; padding: 14px 20px; border-radius: 12px; border: 1px solid #edf0f6; text-align: center; transition: transform 0.2s, box-shadow 0.2s; }
.analytics-pill:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06); }
.analytics-pill .pill-label { display: block; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; color: #7a879b; margin-bottom: 4px; }
.analytics-pill .pill-value { display: block; font-size: 22px; font-weight: 700; color: #0b1e3c; }
.analytics-cards { display: grid; grid-template-columns: repeat(5, 1fr); gap: 24px; margin-bottom: 28px; }
.quality-cards { display: grid; grid-template-columns: repeat(5, 1fr); gap: 24px; margin-bottom: 28px; }
@media (max-width: 768px) {
  .analytics-cards { grid-template-columns: repeat(2, 1fr); }
  .quality-cards { grid-template-columns: repeat(2, 1fr); }
  .analytics-pills { flex-direction: column; }
  .analytics-pill { min-width: auto; }
  .page-header { flex-direction: column; align-items: flex-start; gap: 10px; }
  .summary-cards, .selection-cards, .summary-grid.two-col, .summary-grid.three-col { grid-template-columns: 1fr; }
  .mapping-row { flex-direction: column; align-items: stretch; }
  .required-label { width: 100%; }
  .progress-steps { flex-wrap: wrap; gap: 8px; }
  .progress-step { flex: 1 0 30%; }
  .filters-row { flex-direction: column; align-items: stretch; }
  .filter-group { min-width: 100%; }
  .workflow-options { grid-template-columns: 1fr; }
  .header-right { width: 100%; justify-content: flex-start; }
  .btn-save-session { width: 100%; justify-content: center; }
}
</style>