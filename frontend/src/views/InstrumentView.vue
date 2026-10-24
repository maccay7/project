<template>
  <FixedLayout>
    <div class="instrument-page">
      <div class="page-header">
        <div class="header-left">
          <h1>{{ pageTitle }}</h1>
          <p>{{ pageSubtitle }}</p>
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

      <div class="tab-content-wrapper">
        <div v-if="activeTab === 'upload'" class="content-card">
          <v-card>
            <v-card-title>Upload {{ instrumentLabel }} Dataset</v-card-title>
            <v-card-text>
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
                <button class="btn-view-workbook" @click="openWorkbookViewer">View Excel Workbook</button>
                <button class="btn-preview" @click="togglePreview" :disabled="!worksheetSelected">Preview</button>
                <button class="btn-review-excel" @click="openExcelReview(rawData, 'Uploaded Data')" :disabled="!worksheetSelected">Review Excel</button>
                <button v-if="sheetType === 'multi'" class="btn-mapping" @click="openMappingDialog" :disabled="!worksheetSelected">Map Columns</button>
              </div>

              <div v-if="worksheetWorkflow.workbookSheets.length > 0" class="worksheet-selector-section" style="margin-top: 20px;">
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

              <div v-if="rawData.length && showPreview" class="excel-preview-section">
                <h4>File Preview – {{ currentSheetName || 'Selected Sheet' }}</h4>
                <p class="preview-info">{{ rawData.length }} total rows — edit cells below like Excel</p>
                
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
                
                <div v-if="sheetType === 'multi'" class="preview-actions">
                  <button class="btn-primary" @click="saveFinalMapping">Save Mapping</button>
                </div>
              </div>

              <!-- ============================================================
                   DIALOGS — deduplicated (was 8x mapping / 2x saved / 7 orphans)
                   ============================================================ -->

              <!-- SINGLE: Map Columns dialog -->
              <v-dialog v-model="showMappingDialog" max-width="650px">
                <v-card>
                  <v-card-title class="mapping-dialog-title">
                    Map Columns – {{ instrumentLabel }}
                    <v-spacer></v-spacer>
                    <span class="mapping-count">{{ requiredColumns.length }} required fields</span>
                  </v-card-title>
                  <v-card-text class="mapping-dialog-body">
                    <div v-if="isolatedTableData && isolatedTableData.rawTableData"
                         class="header-selection-section"
                         style="margin-bottom: 24px; padding: 16px; background: #f8f9ff; border-radius: 8px; border-left: 4px solid #0B2044;">
                      <label style="font-weight: 600; color: #0B2044; margin-bottom: 8px; display: flex; align-items: center; gap: 6px; font-size: 14px;">
                        <v-icon size="16" color="#0B2044">mdi-format-line-spacing</v-icon>
                        Select Header Row for Mapping
                      </label>
                      <select v-model="selectedHeaderRowIndex" @change="updateIsolatedTableData" class="mapping-select" style="width: 100%;">
                        <option v-for="(row, idx) in isolatedTableData.rawTableData" :key="idx" :value="idx">
                          Row {{ idx + 1 }}: {{ getRowPreview(row) }}
                        </option>
                      </select>
                      <p style="font-size: 12px; color: #666; margin-top: 8px;">
                        If the detected column headers below are incorrect, choose the correct row above.
                      </p>
                    </div>

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

              <!-- SINGLE: Saved Mappings dialog -->
              <v-dialog v-model="showSavedMappingsDialog" max-width="700px">
                <v-card>
                  <v-card-title class="saved-mappings-popup-title">
                    Saved Mappings
                    <v-spacer></v-spacer>
                    <button class="btn-close-dialog" @click="showSavedMappingsDialog = false">×</button>
                  </v-card-title>
                  <v-card-text class="saved-mappings-popup-body">
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

              <!-- MULTI-TABLE DETECTION — required vs additional, selectable -->
              <v-dialog v-model="showMultiTableDetectionSuccess" max-width="800px">
                <v-card>
                  <v-card-title class="detection-success-title">
                    Multi-Table Detection Successful
                    <v-spacer></v-spacer>
                    <span class="detection-count">{{ multiTableDetectionResults.length }} table(s)</span>
                    <button class="btn-close-dialog" @click="showMultiTableDetectionSuccess = false">×</button>
                  </v-card-title>

                  <v-card-text class="detection-success-body">
                    <div class="instrument-type-display">
                      <strong>Instrument:</strong> {{ formatInstrumentTypeLabel(instrumentType) }}
                      <span class="required-summary">
                        {{ multiRequiredCount }} required · {{ multiAdditionalCount }} additional
                      </span>
                    </div>

                    <div class="currency-selection-section">
                      <label class="currency-label">Currency to include in auto-detected values:</label>
                      <v-select
                        v-model="selectedCurrency"
                        @update:modelValue="handleCurrencyChange"
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
                          @update:modelValue="handleCustomCurrencyInput"
                        ></v-text-field>
                      </div>
                      <div v-if="detectedCurrencies.length > 0" class="detected-currencies-info">
                        <strong>Detected currencies:</strong> {{ detectedCurrencies.join(', ') }}
                      </div>
                    </div>

                    <div class="multi-instruments-list">
                      <div
                        v-for="(instrument, index) in multiTableDetectionResults"
                        :key="index"
                        class="multi-instrument-item"
                      >
                        <div class="multi-instrument-header">
                          <strong>Table {{ index + 1 }}: {{ instrument.tableName }}</strong>
                          <span class="field-count-badge">{{ Object.keys(instrument.fields).length }} fields</span>
                        </div>

                        <!-- REQUIRED fields -->
                        <div class="field-group">
                          <div class="field-group-title">
                            <v-icon size="14" color="#2e7d32">mdi-check-circle</v-icon>
                            Required for {{ instrumentLabel }} calculation
                          </div>
                          <div class="field-grid">
                            <div
                              v-for="(value, field) in instrument.fields"
                              :key="'req-' + field"
                              v-show="isRequiredField(field)"
                              class="field-row field-row--required"
                            >
                              <span class="field-name">{{ autoDetectedFieldsWithMetadata[field]?.originalLabel || field }}</span>
                              <span class="field-value">{{ formatDetectedValue(field, typeof value === 'object' && value !== null ? value.value : value) }}</span>
                              <span v-if="instrument.fieldsWithMetadata?.[field]?.location" class="field-loc">
                                @ {{ instrument.fieldsWithMetadata[field].location }}
                              </span>
                              <div
                                v-if="typeof value === 'object' && value?.currencyVariants && Object.keys(value.currencyVariants).length > 1"
                                class="currency-variant-selector"
                              >
                                <select
                                  :value="value.selectedCurrency"
                                  @change="updateMultiTableCurrency(instrument, field, $event.target.value)"
                                  class="currency-select"
                                >
                                  <option v-for="(variantValue, currency) in value.currencyVariants" :key="currency" :value="currency">
                                    {{ currency }}: {{ formatDetectedValue(field, variantValue) }}
                                  </option>
                                </select>
                              </div>
                            </div>
                          </div>
                        </div>

                        <!-- ADDITIONAL fields (toggleable) -->
                        <div v-if="hasAdditionalFields(instrument)" class="field-group">
                          <div class="field-group-title">
                            <v-icon size="14" color="#1565c0">mdi-plus-circle</v-icon>
                            Additional detected fields
                            <span class="field-group-hint">(used only if checked)</span>
                          </div>
                          <div class="field-grid">
                            <label
                              v-for="(value, field) in instrument.fields"
                              :key="'add-' + field"
                              v-show="!isRequiredField(field)"
                              class="field-row field-row--additional"
                              :class="{ 'field-row--excluded': excludedDetectedFields.has(field) }"
                            >
                              <input
                                type="checkbox"
                                :checked="!excludedDetectedFields.has(field)"
                                @change="toggleExcludeField(field)"
                                class="field-checkbox"
                              />
                              <span class="field-name">{{ field }}</span>
                              <span class="field-value">{{ formatDetectedValue(field, typeof value === 'object' && value !== null ? value.value : value) }}</span>
                              <span v-if="instrument.fieldsWithMetadata?.[field]?.location" class="field-loc">
                                @ {{ instrument.fieldsWithMetadata[field].location }}
                              </span>
                            </label>
                          </div>
                        </div>

                        <div v-if="instrument.missingFields.length > 0" class="multi-missing-fields">
                          <span class="missing-label">Missing required:</span>
                          {{ instrument.missingFields.join(', ') }}
                        </div>
                      </div>
                    </div>
                  </v-card-text>

                  <v-card-actions class="detection-footer">
                    <span class="footer-selection-summary">
                      {{ selectedAdditionalCount }} additional field(s) will be included
                    </span>
                    <v-spacer></v-spacer>
                    <button class="btn-secondary" @click="showMultiTableDetectionSuccess = false">Cancel</button>
                    <button class="btn-primary" @click="useMultiTableDetectedFields" :disabled="isDetecting">
                      <v-icon v-if="isDetecting" size="16" class="spin-animation">mdi-loading</v-icon>
                      Use Combined Fields
                    </button>
                  </v-card-actions>
                </v-card>
              </v-dialog>

              <!-- SINGLE-INSTRUMENT DETECTION — required vs additional, selectable -->
              <v-dialog v-model="showDetectionSuccess" max-width="700px">
                <v-card>
                  <v-card-title class="detection-success-title">
                    Auto Detection Successful
                    <v-spacer></v-spacer>
                    <span class="detection-count">
                      {{ Object.keys(autoDetectedFields).length }} required ·
                      {{ Object.keys(autoDetectedAdditionalFields).length }} additional
                    </span>
                    <button class="btn-close-dialog" @click="showDetectionSuccess = false">×</button>
                  </v-card-title>

                  <v-card-text class="detection-success-body">
                    <div class="instrument-type-display">
                      <strong>Instrument:</strong> {{ formatInstrumentTypeLabel(detectedInstrumentType) }}
                    </div>

                    <div v-if="Object.keys(autoDetectedFields).length > 0" class="field-group">
                      <div class="field-group-title">
                        <v-icon size="14" color="#2e7d32">mdi-check-circle</v-icon>
                        Required fields detected
                      </div>
                      <div class="field-grid">
                        <div
                          v-for="(value, field) in autoDetectedFields"
                          :key="field"
                          class="field-row field-row--required"
                        >
                          <span class="field-name">{{ autoDetectedFieldsWithMetadata[field]?.originalLabel || field }}</span>
                          <span class="field-value">{{ formatDetectedValue(field, typeof value === 'object' && value !== null ? value.value : value) }}</span>
                          <span v-if="autoDetectedFieldsWithMetadata[field]?.location" class="field-loc">
                            @ {{ autoDetectedFieldsWithMetadata[field].location }}
                          </span>
                          <div
                            v-if="typeof value === 'object' && value?.currencyVariants && Object.keys(value.currencyVariants).length > 1"
                            class="currency-variant-selector"
                          >
                            <select
                              v-model="value.selectedCurrency"
                              @change="updateSelectedCurrency(field, value.selectedCurrency)"
                              class="currency-select"
                            >
                              <option v-for="(variantValue, currency) in value.currencyVariants" :key="currency" :value="currency">
                                {{ currency }}: {{ formatDetectedValue(field, variantValue) }}
                              </option>
                            </select>
                          </div>
                        </div>
                      </div>
                    </div>

                    <div v-if="Object.keys(autoDetectedAdditionalFields).length > 0" class="field-group">
                      <div class="field-group-title">
                        <v-icon size="14" color="#1565c0">mdi-plus-circle</v-icon>
                        Additional detected fields
                        <span class="field-group-hint">(used only if checked)</span>
                      </div>
                      <div class="field-grid">
                        <label
                          v-for="(value, field) in autoDetectedAdditionalFields"
                          :key="'add-' + field"
                          class="field-row field-row--additional"
                          :class="{ 'field-row--excluded': excludedDetectedFields.has(field) }"
                        >
                          <input
                            type="checkbox"
                            :checked="!excludedDetectedFields.has(field)"
                            @change="toggleExcludeField(field)"
                            class="field-checkbox"
                          />
                          <span class="field-name">{{ autoDetectedFieldsWithMetadata[field]?.originalLabel || field }}</span>
                          <span class="field-value">{{ formatDetectedValue(field, typeof value === 'object' && value !== null ? value.value : value) }}</span>
                          <span v-if="autoDetectedFieldsWithMetadata[field]?.location" class="field-loc">
                            @ {{ autoDetectedFieldsWithMetadata[field].location }}
                          </span>
                        </label>
                      </div>
                    </div>

                    <div
                      v-if="Object.keys(autoDetectedFields).length === 0 && Object.keys(autoDetectedAdditionalFields).length === 0"
                      class="no-detection-message"
                    >
                      <p>No fields were detected in this worksheet.</p>
                      <p>Try selecting a different sheet, section, or check the field names.</p>
                    </div>

                    <div v-if="Object.keys(autoDetectedFields).length < requiredColumns.length" class="missing-fields-warning">
                      <p><strong>Missing required fields:</strong></p>
                      <ul>
                        <li v-for="col in requiredColumns.filter(c => !autoDetectedFields[c])" :key="col">{{ col }}</li>
                      </ul>
                    </div>
                  </v-card-text>

                  <v-card-actions class="detection-footer">
                    <span class="footer-selection-summary">
                      {{ Object.keys(autoDetectedAdditionalFields).length - excludedDetectedFields.size }} additional field(s) will be included
                    </span>
                    <v-spacer></v-spacer>
                    <button class="btn-secondary" @click="showDetectionSuccess = false">Cancel</button>
                    <button class="btn-primary" @click="useDetectedFields">
                      Work on This Worksheet
                    </button>
                  </v-card-actions>
                </v-card>
              </v-dialog>

              <!-- SINGLE: Workbook viewer -->
              <v-dialog v-model="showWorkbookViewer" max-width="95%" persistent>
                <v-card style="height: 90vh;">
                  <v-card-title class="excel-dialog-title-no-logo">
                    <span>Excel Workbook – {{ currentSheetName || 'Select a sheet' }}</span>
                    <v-spacer></v-spacer>
                    
                    <button class="btn-auto-detect-green" @click="() => autoDetectSingleInstrument()" v-if="workbookSheets.length > 0" :disabled="isDetecting">
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
                      :detecting-from-parent="isDetecting"
                      :dataset-id="originalDatasetId"
                      @close="showWorkbookViewer = false"
                      @sheet-selected="handleSheetSelectedFromViewer"
                      @single-instrument-extracted="handleSingleInstrumentExtracted"
                      @table-isolated="handleTableIsolated"
                      @multi-table-detect="handleMultiTableDetect"
                      @workbook-loaded="handleWorkbookLoaded"
                    />
                  </v-card-text>
                  <div class="popup-footer">
                    <span v-if="activeValuationDate" class="valuation-date-footer">Valuation Date: {{ activeValuationDate }}</span>
                    <v-spacer></v-spacer>
                    <button class="btn-secondary" @click="showWorkbookViewer = false">Close</button>
                  </div>
                </v-card>
              </v-dialog>

              <!-- ============================================================
                   END dialogs
                   ============================================================ -->

              <div class="required-columns" v-if="sheetType === 'multi'">
                <h4>Required Columns</h4>
                
                <div class="columns-list">
                  <span v-for="col in requiredColumns" :key="col" class="column-badge" :class="{ 'missing-column': !hasRequiredColumn(col), 'mapped-column': hasRequiredColumn(col) }">
                    <span class="badge-icon">{{ hasRequiredColumn(col) ? '✓' : '○' }}</span>
                    {{ col }}
                  </span>
                </div>
                
                <div v-if="rawData.length && missingColumns.length" class="warning-message">
                  <span class="warning-icon">⚠</span>
                  <span>Missing required columns. Use the dropdowns on the column headers or click "Map Columns" to assign them.</span>
                </div>
                <div v-if="rawData.length && missingColumns.length === 0 && mappingApplied" class="success-message">
                  <span class="success-icon">✓</span>
                  <span>All columns mapped. Ready to continue.</span>
                </div>
              </div>

              <div class="navigation-buttons">
                <button class="btn-primary" @click="continueAfterUpload" :disabled="!uploadedFile || !rawData.length">Continue</button>
                <button class="btn-secondary" @click="goToDashboard">Cancel</button>
              </div>
            </v-card-text>
          </v-card>
        </div>

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
                    <button class="btn-secondary" @click="toggleAllAdditionalFields" v-if="sheetType === 'single'">
                      <v-icon size="14">{{ excludedDetectedFields.size > 0 ? 'mdi-check-all' : 'mdi-close-circle-outline' }}</v-icon>
                      {{ excludedDetectedFields.size > 0 ? 'Include all fields' : 'Exclude all additional' }}
                    </button>
                  </div>
                </div>

                <!-- COMPACT FIELD SELECTOR — single instrument -->
                <div v-if="sheetType === 'single' && displayedSelectionFields.length > 0" class="detected-values-section">
                  <h3>Field Selection — Final Inputs for Valuation</h3>
                  <p class="section-hint">
                    Checked fields flow to the valuation engine. Unchecked fields are removed from the preview below and excluded from all calculations.
                    Any edits made in the Excel preview will reflect here instantly.
                  </p>

                  <div class="compact-fields-table">
                    <div
                      v-for="key in displayedSelectionFields"
                      :key="key"
                      class="compact-field-row"
                      :class="{ 'compact-field-row--excluded': excludedDetectedFields.has(key) }"
                    >
                      <label class="compact-checkbox">
                        <input
                          type="checkbox"
                          :checked="!excludedDetectedFields.has(key)"
                          @change="toggleExcludeField(key)"
                        />
                      </label>
                      <span class="compact-field-name">{{ autoDetectedFieldsWithMetadata[key]?.originalLabel || key }}</span>
                      <span class="compact-field-value">
                        {{ getFieldSelectionValue(key, autoDetectedFields[key]) }}
                      </span>
                      <div v-if="autoDetectedFields[key] && typeof autoDetectedFields[key] === 'object' && autoDetectedFields[key]?.currencyVariants && Object.keys(autoDetectedFields[key].currencyVariants).length > 1 && !excludedDetectedFields.has(key)" class="currency-variant-selector" style="flex: 0 0 auto;">
                        <select v-model="autoDetectedFields[key].selectedCurrency" @change="updateSelectedCurrency(key, autoDetectedFields[key].selectedCurrency)" class="currency-select" style="min-width: 80px; padding: 2px 6px; font-size: 11px;">
                          <option v-for="(variantValue, currency) in autoDetectedFields[key].currencyVariants" :key="currency" :value="currency">
                            {{ currency }}
                          </option>
                        </select>
                      </div>
                    </div>
                  </div>

                  <div class="compact-summary">
                    {{ Object.keys(autoDetectedFields).length - excludedDetectedFields.size }} of {{ Object.keys(autoDetectedFields).length }} fields included
                  </div>

                  <div class="add-field-section">
                    <h4>Add Field</h4>
                    <div class="add-field-form">
                      <input v-model="newFieldName" type="text" placeholder="Field name" class="add-field-input" />
                      <input v-model="newFieldValue" type="text" placeholder="Value" class="add-field-input" />
                      <button class="btn-add-field" @click="addCustomField">Add</button>
                    </div>
                  </div>
                </div>

                <!-- EXCEL PREVIEW — single source of truth -->
                <div v-if="cleanedData.length" class="preview-section" style="margin-top: 20px;">
                  <h4>
                    <v-icon size="16" style="color: #0B2044; margin-right: 6px;">mdi-microsoft-excel</v-icon>
                    Cleaned Data Preview — {{ cleanedData.length }} row(s) · {{ Object.keys(cleanedData[0] || {}).length }} columns
                  </h4>
                  <p class="section-hint">
                    This preview is the single source of truth. Any cell edited here flows directly to Calculations.
                    Excluded fields have already been removed.
                  </p>
                  <div class="excel-scroll-wrapper">
                    <ExcelViewer
                      :data="cleanedData"
                      :headers="cleanPreviewHeaders"
                      @data-update="onCleanedExcelUpdate"
                    />
                  </div>
                </div>

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

                  <div v-if="cleaningOperationsSummary.length" class="cleaning-operations-summary">
                    <h4 class="operations-title">Operations Performed:</h4>
                    <ul class="operations-list">
                      <li v-for="(operation, index) in cleaningOperationsSummary" :key="index" class="operation-item">
                        <v-icon size="16" color="#4CAF50">mdi-check-circle</v-icon>
                        {{ operation }}
                      </li>
                    </ul>
                  </div>

                  <p class="success-text text-center">Data is clean and ready for calculations</p>
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
                    <div class="card-value">{{ formatNumber(allCalculations.totalValue) }}</div>
                  </div>
                  <div class="summary-card rate" @click="showFormula(config.primaryRateKey)">
                    <div class="card-label">{{ rateLabel }}</div>
                    <div class="card-value">{{ allCalculations.avgRate != null ? formatNumber(allCalculations.avgRate) + '%' : '—' }}</div>
                  </div>
                  <div class="summary-card count" @click="showFormula('Number of Instruments')">
                    <div class="card-label">Number of Instruments</div>
                    <div class="card-value">{{ allCalculations.instrumentCount != null ? allCalculations.instrumentCount : '—' }}</div>
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

                <div v-if="allCalculations.status === 'error'" class="warning-message" style="margin-bottom: 20px;">
                  <span class="warning-icon">⚠</span>
                  <span><strong>Calculation Error:</strong> {{ allCalculations.message }}</span>
                </div>

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

                  <div v-if="isCalculating" class="calculating-animation">
                    <v-icon size="16" class="spin-animation">mdi-loading</v-icon>
                    <span>Calculating...</span>
                  </div>
                  <div v-else-if="allCalculations.status === 'error' && allCalculations.message" class="calc-error-banner">
                    {{ allCalculations.message }}
                  </div>
                  <div v-else-if="!calculationFields.length" class="no-calcs-message">
                    <v-icon size="48" color="#999">mdi-calculator-variant-outline</v-icon>
                    <p>No calculated values available. Ensure the required inputs are present in the cleaned data.</p>
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
                              <th v-for="col in instrumentSummaryColumnsForDisplay" :key="col">{{ formatColumnHeader(col) }}</th>
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
                </div>

                <div class="summary-report">
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
                                <span>{{ formatColumnHeader(col) }}</span>
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

    <ExcelModalViewer
      :visible="showModalViewer"
      :fileData="viewerFileData"
      @close="showModalViewer = false"
      @update:visible="(val) => showModalViewer = val"
      @process-sheet="handleProcessSheetFromModal"
    />

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
import { API_BASE_URL } from '@/config.js'
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
import {
  buildAggregatesFromBackend,
  hasDisplayableCalculation,
  formatCalculationFailureMessage
} from '@/utils/calculationDisplay.js'

// ─────────────────────────────────────────────────────────────
// FIX 1 — dedupeColumns helper.
// Backend emits face_value AND faceValue, valuation_date AND
// valuationDate. Collapse to ONE column using snake_case as the key.
// ─────────────────────────────────────────────────────────────
function dedupeColumns(cols) {
  const seen = new Set()
  const out = []
  const norm = (c) => String(c)
    .trim()
    .replace(/[\s\-]+/g, '_')
    .replace(/(?<=[a-z0-9])([A-Z])/g, '_$1')
    .toLowerCase()
  for (const c of cols || []) {
    if (c === null || c === undefined || c === '') continue
    const k = norm(c)
    if (seen.has(k)) continue
    seen.add(k)
    out.push(c)
  }
  return out
}

function formatInstrumentTypeLabel(type) {
  if (type === 'money-market') return 'Money Market (money-market)'
  if (type === 'tbills') return 'Treasury Bills (tbills)'
  if (type === 'bonds') return 'Bonds (bonds)'
  return type || 'Unknown'
}

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

// ─────────────────────────────────────────────────────────────
// FIX 2 — FIELD_MAPPINGS now maps snake_case AND camelCase
// aliases for every field, including dates and identifiers.
// ─────────────────────────────────────────────────────────────
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
    'days_to_maturity': 'Days to Maturity',
    'daysToMaturity': 'Days to Maturity',
    'total_value': 'Total Value',
    'totalValue': 'Total Value',
    'yield_curve_rate': 'Yield Curve Rate',
    'yieldCurveRate': 'Yield Curve Rate',
    'valuation_date': 'Valuation Date',
    'valuationDate': 'Valuation Date',
    'maturity_date': 'Maturity Date',
    'maturityDate': 'Maturity Date',
    'issue_date': 'Issue Date',
    'issueDate': 'Issue Date',
    'settlement_date': 'Settlement Date',
    'settlementDate': 'Settlement Date',
    'instrument_name': 'Instrument Name',
    'instrumentName': 'Instrument Name',
    'instrument_type': 'Instrument Type',
    'instrumentType': 'Instrument Type',
    'status': 'Status'
  },
  'bonds': {
    'clean_price': 'Clean Price',
    'dirty_price': 'Dirty Price',
    'current_price': 'Current Price',
    'currentPrice': 'Current Price',
    'price': 'Price',
    'coupon_rate': 'Coupon Rate',
    'couponRate': 'Coupon Rate',
    'annual_coupon': 'Annual Coupon',
    'annualCoupon': 'Annual Coupon',
    'coupon_per_period': 'Coupon per Period',
    'couponPerPeriod': 'Coupon per Period',
    'yield_to_maturity': 'Yield to Maturity',
    'yieldToMaturity': 'Yield to Maturity',
    'current_yield': 'Current Yield',
    'currentYield': 'Current Yield',
    'duration': 'Duration',
    'macaulay_duration': 'Macaulay Duration',
    'macaulayDuration': 'Macaulay Duration',
    'modified_duration': 'Modified Duration',
    'modifiedDuration': 'Modified Duration',
    'convexity': 'Convexity',
    'accrued_interest': 'Accrued Interest',
    'accruedInterest': 'Accrued Interest',
    'face_value': 'Face Value',
    'faceValue': 'Face Value',
    'years_to_maturity': 'Years to Maturity',
    'yearsToMaturity': 'Years to Maturity',
    'price_per_100': 'Price per 100',
    'pricePer100': 'Price per 100',
    'valuation_date': 'Valuation Date',
    'valuationDate': 'Valuation Date',
    'maturity_date': 'Maturity Date',
    'maturityDate': 'Maturity Date',
    'issue_date': 'Issue Date',
    'issueDate': 'Issue Date',
    'settlement_date': 'Settlement Date',
    'settlementDate': 'Settlement Date',
    'last_coupon_date': 'Last Coupon Date',
    'lastCouponDate': 'Last Coupon Date',
    'days_accrued': 'Days Accrued',
    'daysAccrued': 'Days Accrued',
    'coupon_frequency': 'Coupon Frequency',
    'couponFrequency': 'Coupon Frequency',
    'frequency': 'Frequency',
    'total_value': 'Total Value',
    'totalValue': 'Total Value',
    'yield_curve_rate': 'Yield Curve Rate',
    'yieldCurveRate': 'Yield Curve Rate',
    'instrument_name': 'Instrument Name',
    'instrumentName': 'Instrument Name',
    'instrument_type': 'Instrument Type',
    'instrumentType': 'Instrument Type',
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
    'effective_annual_yield': 'Effective Annual Yield',
    'effectiveAnnualYield': 'Effective Annual Yield',
    'money_market_yield': 'Money Market Yield',
    'moneyMarketYield': 'Money Market Yield',
    'holding_period_yield': 'Holding Period Yield',
    'holdingPeriodYield': 'Holding Period Yield',
    'face_value': 'Face Value',
    'faceValue': 'Face Value',
    'purchase_price': 'Purchase Price',
    'purchasePrice': 'Purchase Price',
    'discount_amount': 'Discount Amount',
    'discountAmount': 'Discount Amount',
    'total_value': 'Total Value',
    'totalValue': 'Total Value',
    'days_to_maturity': 'Days to Maturity',
    'daysToMaturity': 'Days to Maturity',
    'term_days': 'Days to Maturity',
    'termDays': 'Days to Maturity',
    'valuation_date': 'Valuation Date',
    'valuationDate': 'Valuation Date',
    'maturity_date': 'Maturity Date',
    'maturityDate': 'Maturity Date',
    'issue_date': 'Issue Date',
    'issueDate': 'Issue Date',
    'settlement_date': 'Settlement Date',
    'settlementDate': 'Settlement Date',
    'yield_curve_rate': 'Yield Curve Rate',
    'yieldCurveRate': 'Yield Curve Rate',
    'instrument_name': 'Instrument Name',
    'instrumentName': 'Instrument Name',
    'instrument_type': 'Instrument Type',
    'instrumentType': 'Instrument Type',
    'status': 'Status'
  }
}

const INPUT_FIELDS = {
  'money-market': [
    'Principal', 'Interest Rate', 'Discount Rate', 'Purchase Price',
    'Issue Date', 'Maturity Date', 'Settlement Date', 'Valuation Date',
    'Days to Maturity', 'Compounding Frequency', 'Day Count Convention',
    'Status', 'Error', 'Instrument Name', 'Instrument Type'
  ],
  'bonds': [
    'Face Value', 'Par Value', 'Coupon Rate', 'Coupon Frequency', 'Frequency',
    'Yield to Maturity', 'Issue Date', 'Maturity Date', 'Settlement Date',
    'Valuation Date', 'Last Coupon Date', 'Years to Maturity',
    'Day Count Convention', 'Status', 'Error', 'Instrument Name', 'Instrument Type'
  ],
  'tbills': [
    'Face Value', 'Discount Rate', 'Purchase Price',
    'Issue Date', 'Maturity Date', 'Settlement Date', 'Valuation Date',
    'Days to Maturity', 'Day Count Convention',
    'Status', 'Error', 'Instrument Name', 'Instrument Type'
  ]
}

function mapBackendFieldsToDisplayNames(row, instrumentType) {
  const mapping = FIELD_MAPPINGS[instrumentType] || {}
  const mappedRow = {}
  for (const [key, value] of Object.entries(row)) {
    const displayKey = mapping[key] || key
    if (displayKey in mappedRow && mappedRow[displayKey] !== value) {
      if (mappedRow[displayKey] === null || mappedRow[displayKey] === undefined || mappedRow[displayKey] === '') {
        mappedRow[displayKey] = value
      }
      continue
    }
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
    if (!isInput) filteredRow[key] = value
  }
  return filteredRow
}

const VALID_FREQUENCIES = /^(annual(ly)?|semi[- ]?annual(ly)?|quarter(ly)?|month(ly)?|weekly|daily|at maturity|zero|bullet|1|2|4|12|52|365)$/i

function isPlausibleValue(canonicalKey, value) {
  if (value === null || value === undefined || value === '') return false
  const lc = String(canonicalKey).toLowerCase()
  if (lc.includes('frequency') || (lc.includes('interest') && lc.includes('payment') && lc.includes('frequency')) || (lc.includes('payment') && lc.includes('frequency'))) {
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
  if (lc.includes('date') || lc.includes('maturity') || lc.includes('auction') || lc.includes('settlement') || lc.includes('issue') || (lc.includes('coupon') && lc.includes('date'))) {
    if (value instanceof Date) return !isNaN(value.getTime())
    const d = new Date(value)
    return !isNaN(d.getTime())
  }
  if (lc.includes('days') || lc.includes('term') || lc.includes('tenor') || (lc.includes('maturity') && !lc.includes('date'))) {
    const n = typeof value === 'number' ? value : parseFloat(String(value))
    if (isNaN(n)) return false
    return n >= 0 && Number.isInteger(n)
  }
  return true
}

const SEMANTIC_FIELD_GROUPS = {
  name: ['InstrumentName', 'BondName', 'TBillName', 'Instrument Name', 'Bond Name', 'T-Bill Name', 'Counterparty', 'Issuer', 'Name', 'Security', 'Security Name', 'Counter Party', 'Counterparty Name', 'Issuer Name', 'Instrument'],
  faceValue: ['FaceValue', 'Principal', 'Notional', 'Par', 'ParValue', 'Nominal', 'NominalValue', 'Amount', 'Face Value', 'Par Value', 'Principal Amount', 'Investment Amount', 'Issue Amount', 'Redemption Value', 'Maturity Value', 'Nominal Amount', 'Face Amount', 'Par Amount', 'Notional Amount', 'Purchase Price', 'Future Value'],
  rate: ['CouponRate', 'InterestRate', 'DiscountRate', 'Yield', 'YieldToMaturity', 'Rate', 'Interest Rate', 'Coupon Rate', 'Discount Rate', 'Current Yield', 'Yield Rate', 'YTM', 'Discount', 'Coupon', 'Investment Yield', 'Effective Annual Yield', 'Benchmark Rate', 'Reference Rate', 'Spread', 'Margin'],
  date: ['IssueDate', 'MaturityDate', 'SettlementDate', 'ValuationDate', 'AuctionDate', 'NextCouponDate', 'Issue Date', 'Maturity Date', 'Settlement Date', 'Valuation Date', 'Auction Date', 'Next Coupon Date', 'Redemption Date', 'Due Date', 'Expiry Date', 'Value Date', 'Pricing Date', 'Trade Date', 'Effective Date', 'Start Date', 'End Date', 'Call Date', 'Put Date', 'Coupon Date', 'Last Coupon Date'],
  frequency: ['CouponFrequency', 'InterestPaymentFrequency', 'PaymentFrequency', 'Frequency', 'Coupon Frequency', 'Interest Payment Frequency', 'Payment Freq', 'Pmt Frequency', 'Coupon Freq', 'Interest Pmt Frequency', 'Compounding Frequency'],
  term: ['DaysToMaturity', 'Term', 'Tenor', 'Days to Maturity', 'Term (Days)', 'Tenor (Days)', 'Duration', 'Years to Maturity', 'Term in Days', 'Term in Months', 'Term in Years', 'Tenor Days', 'Tenor Months', 'Tenor Years', 'Accrued Days', 'Days in Coupon Period', 'Term to Maturity'],
  currency: ['Currency', 'CurrencyCode', 'Currency Code', 'CCY', 'Denomination', 'Base Currency', 'Local Currency', 'Reporting Currency', 'Exchange Rate', 'FX Rate'],
  status: ['Status', 'State', 'Type', 'Category', 'Classification'],
  price: ['Price', 'Purchase Price', 'Clean Price', 'Dirty Price', 'Market Price', 'Current Price', 'Price per 100', 'Call Price', 'Put Price'],
  interest: ['Accrued Interest', 'Interest Accrued', 'Coupon', 'Coupon Amount', 'Coupon Payment', 'Annual Coupon', 'Interest Earned', 'Interest Income', 'Discount Amount'],
  duration: ['Macaulay Duration', 'Modified Duration', 'Convexity', 'DV01'],
  return: ['Capital Gain Loss', 'Total Return', 'Profit Return', 'Market Value', 'Present Value', 'Carrying Value', 'Book Value', 'Fair Value', 'Maturity Value', 'Current Value', 'Purchase Cost']
}

function normalizeKeyForMatch(key) {
  return String(key).toLowerCase().replace(/[\s_\-()]+/g, '')
}

function findSemanticType(key) {
  const lower = normalizeKeyForMatch(key)
  for (const [type, list] of Object.entries(SEMANTIC_FIELD_GROUPS)) {
    if (list.some(f => {
      const fLower = normalizeKeyForMatch(f)
      return lower.includes(fLower) || fLower.includes(lower)
    })) {
      return type
    }
  }
  return null
}

function isSemanticMatch(detectedKey, targetField, semanticType) {
  const detectedLower = normalizeKeyForMatch(detectedKey)
  const targetLower = normalizeKeyForMatch(targetField)
  if (detectedLower === targetLower) return true
  if (detectedLower.includes(targetLower) || targetLower.includes(detectedLower)) return true
  const fields = SEMANTIC_FIELD_GROUPS[semanticType] || []
  const detectedInList = fields.some(f => normalizeKeyForMatch(f) === detectedLower)
  const targetInList = fields.some(f => normalizeKeyForMatch(f) === targetLower)
  return detectedInList && targetInList
}

function normalizeDetectedFields(fields, fieldsWithMetadata, instrumentType, requiredColsOverride = null) {
  const normalised = {}
  const normalisedMeta = {}
  const usedCanonical = new Set()
  const targetColumns = requiredColsOverride || requiredColumns.value || []
  const detectedSemantics = {}
  for (const rawKey of Object.keys(fields || {})) {
    detectedSemantics[rawKey] = findSemanticType(rawKey) || 'generic'
  }
  const rawEntries = Object.entries(fields || {}).sort(
    (a, b) => String(b[0]).length - String(a[0]).length
  )
  for (const [rawKey, rawValue] of rawEntries) {
    const semantic = detectedSemantics[rawKey]
    let matchedCanonical = null
    for (const targetCol of targetColumns) {
      if (usedCanonical.has(targetCol)) continue
      const targetLower = normalizeKeyForMatch(targetCol)
      const rawKeyLower = normalizeKeyForMatch(rawKey)
      if (rawKeyLower === targetLower) {
        matchedCanonical = targetCol
        break
      }
      if (semantic && semantic !== 'generic' && isSemanticMatch(rawKey, targetCol, semantic)) {
        matchedCanonical = targetCol
        break
      }
      if (rawKeyLower.includes(targetLower) || targetLower.includes(rawKeyLower)) {
        matchedCanonical = targetCol
        break
      }
    }
    if (!matchedCanonical) matchedCanonical = rawKey
    if (usedCanonical.has(matchedCanonical)) continue
    // [FIX-MULTICURRENCY] Preserve currencyVariants for multi-currency fields.
    const isObjectValue = rawValue && typeof rawValue === 'object' && 'value' in rawValue
    const scalarValue = isObjectValue ? rawValue.value : rawValue
    const hasMultiCurrency =
      isObjectValue &&
      rawValue.currencyVariants &&
      Object.keys(rawValue.currencyVariants).length > 1
    const storedValue = hasMultiCurrency ? { ...rawValue } : scalarValue
    if (semantic !== 'generic' && !isPlausibleValue(matchedCanonical, scalarValue)) {
      continue
    }
    normalised[matchedCanonical] = storedValue
    usedCanonical.add(matchedCanonical)
    const meta = fieldsWithMetadata ? fieldsWithMetadata[rawKey] : null
    const metaCopy = meta && typeof meta === 'object' ? { ...meta } : {}
    metaCopy.originalLabel = rawKey
    normalisedMeta[matchedCanonical] = metaCopy
  }
  return { fields: normalised, fieldsWithMetadata: normalisedMeta }
}

function deriveDaysToMaturity(fields, metadata) {
  const normalizedKeys = Object.keys(fields).map(k => normalizeKeyForMatch(k))
  const alreadyHasDays = normalizedKeys.some(k =>
    k === 'daystomaturity' || k === 'termdays' || k === 'term' || k === 'tenor'
  )
  if (alreadyHasDays) return
  const normalized = {}
  for (const [k, v] of Object.entries(fields)) {
    normalized[normalizeKeyForMatch(k)] = v
  }
  // [FIX-MULTICURRENCY] unwrap object values before using them as dates
  const _unwrap = (v) => (v && typeof v === 'object' && 'value' in v) ? v.value : v
  const startDate = _unwrap(normalized['valuationdate']) || _unwrap(normalized['settlementdate']) || _unwrap(normalized['issuedate'])
  const maturityDate = _unwrap(normalized['maturitydate'])
  if (!startDate || !maturityDate) return
  const start = new Date(startDate)
  const maturity = new Date(maturityDate)
  if (isNaN(start.getTime()) || isNaN(maturity.getTime())) return
  const days = Math.ceil((maturity.getTime() - start.getTime()) / (1000 * 60 * 60 * 24))
  if (days <= 0) return
  const daysKey = (requiredColumns.value || []).find(c => {
    const n = normalizeKeyForMatch(c)
    return n === 'daystomaturity' || n === 'termdays'
  }) || 'days_to_maturity'
  fields[daysKey] = days
  metadata[daysKey] = {
    value: days,
    location: `auto-calculated: ${startDate} → ${maturityDate}`,
    source: 'auto-calculation',
    confidence: 1.0
  }
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
      { key: 'totalValue',          label: 'Total Value (Maturity)' },
      { key: 'totalPrincipal',      label: 'Total Principal' },
      { key: 'totalInterest',       label: 'Total Interest' },
      { key: 'avgRate',             label: 'Average Rate', suffix: '%' },
      { key: 'weightedAvgRate',     label: 'Weighted Average Rate', suffix: '%' },
      { key: 'effectiveAnnualRate', label: 'Effective Annual Rate', suffix: '%' },
      { key: 'discountYield',       label: 'Discount Yield', suffix: '%' },
      { key: 'avgDaysToMaturity',   label: 'Average Days to Maturity', suffix: ' days' },
      { key: 'yieldCurveRate',      label: 'Benchmark Rate', suffix: '%' }
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
      { key: 'totalValue',        label: 'Total Market Value' },
      { key: 'totalFaceValue',    label: 'Total Face Value' },
      { key: 'pricePer100',       label: 'Price per 100' },
      { key: 'avgCouponRate',     label: 'Average Coupon Rate', suffix: '%' },
      { key: 'weightedAvgCoupon', label: 'Weighted Average Coupon', suffix: '%' },
      { key: 'totalAnnualIncome', label: 'Total Annual Coupon Income' },
      { key: 'couponPerPeriod',   label: 'Coupon per Period' },
      { key: 'avgYTM',            label: 'Average YTM', suffix: '%' },
      { key: 'currentYield',      label: 'Current Yield', suffix: '%' },
      { key: 'duration',          label: 'Macaulay Duration (years)' },
      { key: 'modifiedDuration',  label: 'Modified Duration (years)' },
      { key: 'convexity',         label: 'Convexity' },
      { key: 'dv01',              label: 'DV01' },
      { key: 'accruedInterest',   label: 'Accrued Interest' },
      { key: 'yearsToMaturity',   label: 'Years to Maturity' },
      { key: 'yieldCurveRate',    label: 'Benchmark Rate', suffix: '%' }
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
      { key: 'totalFaceValue',        label: 'Total Face Value' },
      { key: 'totalPurchasePrice',    label: 'Total Purchase Price' },
      { key: 'totalDiscount',         label: 'Total Discount Amount' },
      { key: 'avgDiscountRate',       label: 'Average Discount Rate', suffix: '%' },
      { key: 'weightedAvgDiscount',   label: 'Weighted Average Discount', suffix: '%' },
      { key: 'moneyMarketYield',      label: 'Money Market Yield', suffix: '%' },
      { key: 'bondEquivalentYield',   label: 'Bond Equivalent Yield', suffix: '%' },
      { key: 'holdingPeriodYield',    label: 'Holding Period Yield', suffix: '%' },
      { key: 'effectiveAnnualYield',  label: 'Effective Annual Yield', suffix: '%' },
      { key: 'avgDaysToMaturity',     label: 'Average Days to Maturity', suffix: ' days' },
      { key: 'yieldCurveRate',        label: 'Benchmark Rate', suffix: '%' }
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

const pageTitle = computed(() => {
  if (activeTab.value === 'reports') return 'Generate Report'
  if (activeTab.value === 'summary') return `${instrumentLabel.value} – Executive Summary`
  if (activeTab.value === 'visualizations') return `${instrumentLabel.value} – Yield Curve`
  return instrumentLabel.value
})

const pageSubtitle = computed(() => {
  if (activeTab.value === 'reports') return 'Select the instruments to include and generate the combined valuation report.'
  if (activeTab.value === 'summary') return 'Executive summary of the current portfolio valuations.'
  if (activeTab.value === 'visualizations') return `Market yield curve for ${instrumentLabel.value}.`
  return instrumentDescription.value
})

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

watch(instrumentType, (val) => {
  if (val) {
    try { localStorage.setItem('dura_last_instrument', val) } catch (e) { /* ignore */ }
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
const originalDatasetId = ref(null)
const sheetTotalRows = ref(0)
const sessionSavedAt = ref(null)
const showPreview = ref(false)
const worksheetSelected = ref(false)
const forceUpdate = ref(0)

const isSaving = ref(false)
const skipAutoSave = ref(false)
let isSavingVersion = false
let lastInstrument = ''
let lastSessionId = ''
let lastSaveTime = 0
const SAVE_DEBOUNCE_MS = 2000

const snackbar = ref({ show: false, message: '', color: 'error', timeout: 4000 })

function showSnackbar(message, color = 'error', timeout = 4000) {
  snackbar.value = { show: true, message, color, timeout }
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
const selectedHeaderRowIndex = ref(0)
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

const selectedSummaryWorksheet = ref('')
const availableSummaryWorksheets = computed(() => [])

const mappingShownForSheet = ref({})

const currentSummaryRows = computed(() => instrumentSummary.value.rows)

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
        const isTimeField = /day|maturity|duration|term|month|year|week|time/.test(k.toLowerCase())
        if (isTimeField) {
          stats[k] = Math.round(v).toLocaleString()
        } else {
          stats[k] = v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
        }
      }
    }
    return stats
  }
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
      const isTimeField = /day|maturity|duration|term|month|year|week|time/.test(k.toLowerCase())
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
  // FIX: For multi-instrument sheets, always show required columns as headers
  // so the mapping dropdowns are always visible in the preview.
  if (sheetType.value === 'multi') {
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

const EXCLUDED_COLUMNS = new Set([
  '_raw', '_source', 'index', '__v',
  '_row_index', 'valuationtype',
  'workbook', 'worksheet',                       // ids, not results
  'currency', 'currencycode', 'ccy', 'currency_code',   // metadata
  'calculationerrors', 'calculation_errors',     // step-level error array
  'missingprerequisites', 'missing_prerequisites',       // error array
  'ytminput', 'ytm_input',                       // helper fields
  'ytmsource', 'ytm_source',
  'instrument_name', 'instrumentname',           // ids
  'instrument_type', 'instrumenttype',
  'valuation_date', 'valuationdate',
  'maturity_date', 'maturitydate',
  'issue_date', 'issuedate',
  'settlement_date', 'settlementdate',
  'last_coupon_date', 'lastcoupondate'
].map(s => s.toLowerCase().replace(/[_\s\-]+/g, '')))

function isExcludedColumn(col) {
  if (!col) return false
  const normalized = String(col).toLowerCase().replace(/[_\s\-]+/g, '')
  if (EXCLUDED_COLUMNS.has(normalized)) return true
  if (normalized.startsWith('derivation')) return true
  return false
}

function formatColumnHeader(col) {
  if (!col) return col
  return String(col)
    .replace(/_/g, ' ')
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/\b\w/g, c => c.toUpperCase())
}

// ─────────────────────────────────────────────────────────────
// FIX 3 — getDisplayColumns() dedupes via snake_case.
// ─────────────────────────────────────────────────────────────
function getDisplayColumns() {
  const INTERNAL_ONLY = new Set([
    '_raw', '_source', 'index', '__v', '_row_index', 'valuationtype'
  ].map(s => s.toLowerCase().replace(/[_\s\-]+/g, '')))

  const seen = new Set()
  const seenLabels = new Set()
  const result = []

  const consider = (rawKey) => {
    if (!rawKey) return
    const norm = String(rawKey).toLowerCase().replace(/[_\s\-]+/g, '')
    if (INTERNAL_ONLY.has(norm)) return
    if (norm.startsWith('derivation')) return
    if (seen.has(norm)) return
    const label = formatColumnHeader(rawKey).toLowerCase().replace(/[\s_\-]+/g, '')
    if (seenLabels.has(label)) return
    seen.add(norm)
    seenLabels.add(label)
    result.push(String(rawKey))
  }

  for (const r of (instrumentSummary.value.rows || [])) {
    for (const k of Object.keys(r)) consider(k)
  }
  for (const r of (completedInstrumentSummary.value.rows || [])) {
    for (const k of Object.keys(r)) consider(k)
  }

  if (result.length === 0) {
    const typeMapping = FIELD_MAPPINGS[instrumentType.value] || {}
    const rawCols = [
      ...(instrumentSummary.value.columns || []),
      ...(completedInstrumentSummary.value.columns || [])
    ]
    for (const c of rawCols) {
      if (!c) continue
      const base = String(c).replace(/_\d+$/, '').trim()
      consider(typeMapping[base] || base)
    }
  }

  return dedupeColumns(result)
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
    rows = instrumentSummary.value.rows.map(row => ({ ...row, 'Valuation Type': 'Current' }))
  } else if (excelPopupMode.value === 'previous') {
    const allPrevious = completedInstrumentSummary.value.rows || []
    if (allPrevious.length > 0) {
      const lastSummary = allPrevious[allPrevious.length - 1]
      rows = [lastSummary].map(row => ({ ...row, 'Valuation Type': 'Previous' }))
    }
  } else if (excelPopupMode.value === 'all') {
    const currentRows = instrumentSummary.value.rows.map(row => ({ ...row, 'Valuation Type': 'Current' }))
    const previousRows = (completedInstrumentSummary.value.rows || []).map(row => ({ ...row, 'Valuation Type': 'Previous' }))
    rows = [...currentRows, ...previousRows]
  }
  if (instrumentSearchQuery.value) {
    const query = instrumentSearchQuery.value.toLowerCase()
    rows = rows.filter(row => Object.values(row).some(val => String(val).toLowerCase().includes(query)))
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

const totalPages = computed(() => Math.ceil(sortedInstrumentSummaryRows.value.length / rowsPerPage.value))

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
  
  const result = fields.map(field => {
    let value = selectedCalc[field.key] !== undefined ? selectedCalc[field.key] :
                allCalc[field.key] !== undefined ? allCalc[field.key] :
                selectedCalc[toSnakeCase(field.key)] !== undefined ? selectedCalc[toSnakeCase(field.key)] :
                allCalc[toSnakeCase(field.key)] !== undefined ? allCalc[toSnakeCase(field.key)] : null
    if (value === null || value === undefined) {
      const agg = allCalc.agg || selectedCalc.agg || {}
      value = agg[field.key] !== undefined ? agg[field.key] :
              agg[toSnakeCase(field.key)] !== undefined ? agg[toSnakeCase(field.key)] : null
    }
    return { ...field, value }
  })
  
  // Add any dynamically calculated fields that aren't in the hardcoded config
  const knownKeys = new Set(result.map(f => f.key))
  const knownSnakeKeys = new Set(result.map(f => toSnakeCase(f.key)))
  
  // Fields that must NEVER be added dynamically as KPI cards, even if they
  // are present in the backend aggregate. Either they duplicate a static
  // card (maturityValue/fairValue/presentValue ≡ totalValue/principal), or
  // they are metadata (currency, error arrays, dates, ids) that belong in
  // the audit trail — not in the KPI grid.
  const DYNAMIC_BLOCK = new Set([
    'agg', 'derivations', 'fred',
    'instrumentCount', 'instrument_count',
    'totalValue', 'total_value',
    'avgRate', 'avg_rate',
    'status', 'error', 'message',
    'missing_fields', 'invalid_fields',
    // duplicates of totalValue / principal
    'maturityValue', 'maturity_value',
    'fairValue', 'fair_value',
    'presentValue', 'present_value',
    // metadata / non-KPI
    'currency', 'currencyCode', 'ccy', 'currency_code',
    'calculationErrors', 'calculation_errors',
    'missingPrerequisites', 'missing_prerequisites',
    'warning',
    'ytmInput', 'ytm_input',
    'ytmSource', 'ytm_source',
    'instrument_name', 'instrumentName',
    'instrument_type', 'instrumentType',
    'valuation_date', 'valuationDate',
    'maturity_date', 'maturityDate',
    'issue_date', 'issueDate',
    'settlement_date', 'settlementDate',
    'last_coupon_date', 'lastCouponDate',
    'worksheet', 'workbook',
    // inputs already shown by static cards
    'principal', 'faceValue', 'face_value',
    'couponRate', 'coupon_rate',
    'interestRate', 'interest_rate',
    'discountRate', 'discount_rate'
  ])

  for (const key of Object.keys(allCalc)) {
    if (knownKeys.has(key) || knownSnakeKeys.has(toSnakeCase(key))) continue
    if (DYNAMIC_BLOCK.has(key)) continue

    let label = formatColumnHeader(key)
    if (label === 'Dv01') label = 'DV01'
    if (label === 'Ytm') label = 'YTM'
    if (label === 'Ytm Input') label = 'YTM Input'

    result.push({
      key: key,
      label: label,
      value: allCalc[key]
    })
  }
  
  // Filter out boxes that have no genuine value (null, undefined, empty, NaN, Infinity)
  return result.filter(field => {
    if (field.value === null || field.value === undefined || field.value === '') return false
    if (typeof field.value === 'number' && (isNaN(field.value) || !isFinite(field.value))) return false
    if (typeof field.value === 'string' && ['nan', 'infinity', '-infinity'].includes(field.value.toLowerCase())) return false
    return true
  })
})

function toSnakeCase(str) {
  if (!str || typeof str !== 'string') return str
  try {
    return str
      .replace(/([a-z])([A-Z])/g, '$1_$2')
      .replace(/[\s\-]+/g, '_')
      .toLowerCase()
  } catch (e) { return str }
}

function normalizeFieldName(fieldName) {
  if (!fieldName || typeof fieldName !== 'string') return fieldName
  const snake = fieldName
    .replace(/([a-z])([A-Z])/g, '$1_$2')
    .replace(/[\s\-]+/g, '_')
    .toLowerCase()
  const fieldMap = {
    coupon_rate: 'coupon_rate',
    coupon_frequency: 'coupon_frequency',
    maturity_date: 'maturity_date',
    bond_name: 'instrument_name',
    t_bill_name: 'instrument_name',
    tbills_name: 'instrument_name',
    tb_bill_name: 'instrument_name',
    instrument_name: 'instrument_name',
    settlement_date: 'issue_date',
    next_coupon_date: 'next_coupon_date',
    valuation_date: 'valuation_date',
    present_value: 'present_value',
    accrued_interest: 'accrued_interest',
    carrying_value: 'carrying_value',
    discount_rate: 'discount_rate',
    price: 'price',
    interest_rate: 'interest_rate',
    yield_to_maturity: 'yield_to_maturity',
    spread: 'spread',
    principal: 'principal',
    face_value: 'face_value',
    par_value: 'face_value',
    notional: 'face_value',
    fair_value: 'fair_value',
    tenor: 'tenor',
    country_risk_premium: 'country_risk_premium',
    days_to_maturity: 'days_to_maturity',
    term_days: 'days_to_maturity',
    term: 'days_to_maturity',
    purchase_price: 'purchase_price',
    issue_date: 'issue_date',
    coupon_payment: 'coupon_payment',
    instrument: 'instrument_name'
  }
  return fieldMap[snake] || snake
}

function formatCalcValue(key, value) {
  if (value === null || value === undefined || value === '') return '—'
  if (typeof value === 'number' && (isNaN(value) || !isFinite(value))) return '—'
  if (typeof value === 'string' && ['nan', 'infinity', '-infinity'].includes(value.toLowerCase())) return '—'

  const field = config.value.calculationFields.find(f => f.key === key) || {}
  const lc = key.toLowerCase()

  if (typeof value === 'number') {
    // Only exact whole-day keys round to integers. Value keys (maturityValue,
    // presentValue, fairValue) and duration/years keys that need decimal
    // precision are NOT in this list, so `maturityValue: 59,855,497.04` keeps
    // its decimals and `yearsToMaturity: 4.50` stays decimal.
    const isDayCountKey =
      lc === 'termdays' || lc === 'term_days' ||
      lc === 'daystomaturity' || lc === 'days_to_maturity' ||
      lc === 'avgdaystomaturity' || lc === 'avg_days_to_maturity' ||
      lc === 'daysaccrued' || lc === 'days_accrued' ||
      lc === 'dayssinceissue' || lc === 'days_since_issue'
    if (isDayCountKey) {
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
  if (idx > farthestAllowedIndex.value) return
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
async function goToPortfolioSummary() {
  try { await saveSessionData(true) } catch (e) { console.warn('Save before portfolio summary failed:', e) }
  const sessionId = activeSession.value?.id || sessionManager.getActiveSessionId() || localStorage.getItem('dura_active_session_id')
  if (sessionId) {
    sessionManager.setActiveSession({ id: sessionId })
    localStorage.setItem('dura_active_session_id', sessionId)
    router.push({ path: '/summary', query: { session: sessionId } })
  } else {
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
    totalValue: 0, instrumentCount: 0, avgRate: 0, weightedAvgRate: 0,
    totalInterest: null, interestEarned: null, annualYield: null,
    effectiveAnnualRate: null, avgDaysToMaturity: null, totalPrincipal: 0,
    avgCouponRate: 0, weightedAvgCoupon: 0, totalAnnualIncome: null, avgYTM: null, duration: null,
    avgDiscountRate: 0, weightedAvgDiscount: 0, totalDiscount: null, effectiveYield: null,
    bondEquivalentYield: null, totalPurchasePrice: null, avgInvestment: null,
    holdingPeriodYield: null, annualizedYield: null, pricePer100: null
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
  agg.avgDaysToMaturity = avgDays
  agg.totalPrincipal = total
  const couponSum = rows.reduce((sum, row) => sum + getNumber(row, 'Avg Coupon Rate', 'avg_coupon_rate', 'Coupon Rate', 'coupon_rate'), 0)
  agg.avgCouponRate = count > 0 ? couponSum / count : 0
  agg.weightedAvgCoupon = weightedAvg
  agg.avgYTM = avgRate || null
  const discountSum = rows.reduce((sum, row) => sum + getNumber(row, 'Avg Discount Rate', 'avg_discount_rate', 'Discount Rate', 'discount_rate'), 0)
  agg.avgDiscountRate = count > 0 ? discountSum / count : 0
  agg.weightedAvgDiscount = weightedAvg
  agg.avgInvestment = count > 0 ? total / count : null
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

// ─────────────────────────────────────────────────────────────
// FIX 4 — processInstrumentData dedupes columns.
// ─────────────────────────────────────────────────────────────
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
  instrumentSummary.value = { columns: dedupeColumns(Array.from(allCols)), rows: mergedRows }
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
      const sid = activeSession.value?.id || sessionManager.getActiveSessionId() || null
      const result = await worksheetWorkflow.handleFileUpload(new File([arrayBuffer], item.name), sid)
      if (result.success) {
        workbookSheets.value = worksheetWorkflow.workbookSheets.value
        worksheetStatus.value = worksheetWorkflow.worksheetStatus.value
        originalFileBuffer.value = worksheetWorkflow.originalFileBuffer.value
        if (result.datasetId) {
          originalDatasetId.value = result.datasetId
          if (sid) {
            try {
              const wf = await sessionManager.getInstrumentWorkflow(sid, instrumentType.value) || {}
              await sessionManager.saveInstrumentWorkflow(sid, instrumentType.value, {
                ...wf,
                originalDatasetId: result.datasetId,
                originalFileName: item.name
              })
            } catch (e) { console.warn('Failed to persist originalDatasetId (history):', e) }
          }
        }
        showSnackbar(`Loaded ${item.name} from history`, 'success')
        clearActiveCache(true)
        showWorkbookViewer.value = true
        activeTab.value = 'upload'
        forceUpdate.value++
      } else {
        showSnackbar('Failed to parse workbook', 'error')
      }
    } catch (err) {
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
    const fileCopy = new File([file], file.name, { type: file.type })
    uploadedFile.value = fileCopy
    worksheetStatuses.value = {}
    readFileData(fileCopy)
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
    const sid = activeSession.value?.id || sessionManager.getActiveSessionId() || null
    const result = await worksheetWorkflow.handleFileUpload(file, sid)
    if (result.success) {
      workbookSheets.value = worksheetWorkflow.workbookSheets.value
      worksheetStatus.value = worksheetWorkflow.worksheetStatus.value
      originalFileBuffer.value = worksheetWorkflow.originalFileBuffer.value
      worksheetStatuses.value = {}
      if (result.datasetId) {
        originalDatasetId.value = result.datasetId
        if (sid) {
          try {
            const wf = await sessionManager.getInstrumentWorkflow(sid, instrumentType.value) || {}
            await sessionManager.saveInstrumentWorkflow(sid, instrumentType.value, {
              ...wf,
              originalDatasetId: result.datasetId,
              originalFileName: file.name
            })
          } catch (e) { console.warn('Failed to persist originalDatasetId:', e) }
        }
      }
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
  originalDatasetId.value = null
  worksheetWorkflow.reset()
  debouncedSave()
  forceUpdate.value++
  if (fileInput.value) fileInput.value.value = ''
}

function togglePreview() { showPreview.value = !showPreview.value }

function handleWorksheetSelect(sheetName) {
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
          applyCurrentMapping() // FIX: Apply mapping immediately so preview shows transformed data
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
  if (preservePreviousValuations) {
    if (instrumentSummary.value.rows.length > 0) {
      completedInstrumentSummary.value = JSON.parse(JSON.stringify(instrumentSummary.value))
    }
    if (portfolioSummary.value.rows.length > 0) {
      completedPortfolioSummary.value = JSON.parse(JSON.stringify(portfolioSummary.value))
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
  cleaningStats.value = { totalRows: 0, cleanedRows: 0, modifiedRows: 0, duplicateRows: 0, missingValueRows: 0 }
  formulas.value = {}
  manualInputs.value = {}
}

function handleSheetSelectedFromViewer(sheetName) { currentSheetName.value = sheetName }
function handleSingleInstrumentExtracted({ sheetName, extractedValues }) {
  currentSheetName.value = sheetName
  singleInstrumentExtractedValues.value = extractedValues
}

// ─────────────────────────────────────────────────────────────
// NEW HELPERS (row preview + required/additional classification)
// ─────────────────────────────────────────────────────────────

// Truncated, non-crowded row preview for the header-row dropdown.
// Shows only non-empty cells, max 4, each capped at 18 chars.
function getRowPreview(row) {
  if (!row || !row.length) return '(empty row)'
  const cells = []
  let nonEmpty = 0
  for (const c of row) {
    if (c === null || c === undefined || String(c).trim() === '') continue
    nonEmpty++
    if (cells.length >= 4) continue
    let s = String(c).trim().replace(/\s+/g, ' ')
    if (s.length > 18) s = s.slice(0, 18) + '…'
    cells.push(s)
  }
  if (!cells.length) return '(empty row)'
  return cells.join(' · ') + (nonEmpty > 4 ? ' …' : '')
}

// ─────────────────────────────────────────────────────────────
// REQUIRED vs ADDITIONAL field detection (used by the two popups)
// ─────────────────────────────────────────────────────────────
function normalizeFieldKey(key) {
  return String(key || '').toLowerCase().replace(/[-_\s]+/g, '')
}

function isRequiredField(fieldKey) {
  const norm = normalizeFieldKey(fieldKey)
  return (requiredColumns.value || []).some(col => normalizeFieldKey(col) === norm)
}

function hasAdditionalFields(instrument) {
  if (!instrument?.fields) return false
  return Object.keys(instrument.fields).some(k => !isRequiredField(k))
}

const displayedSelectionFields = computed(() => {
  const keys = new Set()
  // Add all fields present in the cleaned preview (the source of truth)
  if (cleanedData.value.length > 0) {
    Object.keys(cleanedData.value[0]).forEach(k => keys.add(k))
  }
  // Add excluded fields so they remain visible in the list to be re-included
  Object.keys(autoDetectedFields.value).forEach(k => {
    if (excludedDetectedFields.value.has(k)) keys.add(k)
  })
  return Array.from(keys)
})

// Counts for the multi-table popup summary
const multiRequiredCount = computed(() => {
  let n = 0
  for (const inst of multiTableDetectionResults.value) {
    for (const k of Object.keys(inst.fields || {})) {
      if (isRequiredField(k)) n++
    }
  }
  return n
})

const multiAdditionalCount = computed(() => {
  let n = 0
  for (const inst of multiTableDetectionResults.value) {
    for (const k of Object.keys(inst.fields || {})) {
      if (!isRequiredField(k)) n++
    }
  }
  return n
})

const selectedAdditionalCount = computed(() => {
  let n = 0
  for (const inst of multiTableDetectionResults.value) {
    for (const k of Object.keys(inst.fields || {})) {
      if (!isRequiredField(k) && !excludedDetectedFields.value.has(k)) n++
    }
  }
  return n
})

// Bulk-toggle: include or exclude every additional field at once.
function toggleAllAdditionalFields() {
  const allAdditional = new Set()
  for (const k of Object.keys(autoDetectedFields.value || {})) {
    if (!isRequiredField(k)) allAdditional.add(k)
  }
  for (const k of Object.keys(autoDetectedAdditionalFields.value || {})) {
    if (!isRequiredField(k)) allAdditional.add(k)
  }
  if (excludedDetectedFields.value.size > 0) {
    excludedDetectedFields.value = new Set()
  } else {
    excludedDetectedFields.value = new Set(allAdditional)
  }
  try {
    sessionStorage.setItem('excluded_fields', JSON.stringify([...excludedDetectedFields.value]))
  } catch (e) { /* ignore */ }
  if (cleanedData.value.length > 0) {
    applyCleaning()
  }
  debouncedSave()
}

// Helper to sync the Field Selection list with the Excel preview
function getFieldSelectionValue(key, rawValue) {
  // If the field is included and exists in the preview, use the preview's value
  if (!excludedDetectedFields.value.has(key) && cleanedData.value.length > 0 && cleanedData.value[0][key] !== undefined) {
    return formatDetectedValue(key, cleanedData.value[0][key])
  }
  // Otherwise, fall back to the originally detected value
  return formatDetectedValue(key, typeof rawValue === 'object' && rawValue !== null ? rawValue.value : rawValue)
}

// [NEW] Handle header row selection & re-mapping
function handleTableIsolated({ sheetName, tableName, rawTableData, headerRowIndex, tableRange }) {
  currentSheetName.value = sheetName
  clearActiveCache(true)
  
  // Store the raw 2D data so the user can switch header rows
  isolatedTableData.value = { sheetName, tableName, rawTableData, tableRange }
  selectedHeaderRowIndex.value = headerRowIndex !== undefined ? headerRowIndex : 0
  
  showWorkbookViewer.value = false
  currentMappingTemplateId.value = null
  showMappingDialog.value = true
  mappingApplied.value = false
  
  // Generate headers and map fields based on the default header row
  updateIsolatedTableData()
  
  worksheetSelected.value = true
  showPreview.value = true
}

// [NEW] Recalculate mapping when the user changes the header row
function updateIsolatedTableData() {
  if (!isolatedTableData.value || !isolatedTableData.value.rawTableData) return
  
  const raw = isolatedTableData.value.rawTableData
  const hIdx = selectedHeaderRowIndex.value
  if (hIdx < 0 || hIdx >= raw.length) return
  
  // Extract headers from the chosen row
  const headers = raw[hIdx].map((h, i) => 
    h !== null && h !== undefined && String(h).trim() !== '' ? String(h).trim() : `Column ${i + 1}`
  )
  
  // Handle duplicate headers to prevent mapping overwrites
  const seen = new Set()
  const uniqueHeaders = headers.map(h => {
    let base = h
    let n = 2
    while (seen.has(h)) { h = `${base} (${n++})` }
    seen.add(h)
    return h
  })
  
  // Extract data rows (everything below the selected header row)
  const dataRows = []
  for (let r = hIdx + 1; r < raw.length; r++) {
    const obj = {}
    for (let c = 0; c < uniqueHeaders.length; c++) {
      obj[uniqueHeaders[c]] = raw[r][c] !== undefined ? raw[r][c] : ''
    }
    dataRows.push(obj)
  }
  
  // Update the live state
  rawData.value = dataRows
  originalRawData.value = JSON.parse(JSON.stringify(dataRows))
  fileColumns.value = uniqueHeaders
  originalFileColumns.value = [...uniqueHeaders]
  
  // Instantly re-run auto-matching so the UI updates
  columnMapping.value = autoMatchColumns(uniqueHeaders, requiredColumns.value, columnVariations.value)
  applyCurrentMapping()
}

async function handleAutoDetectSheet(sheetName) {
  if (!originalFileBuffer.value) { alert('File buffer not available'); return }
  currentSheetName.value = sheetName
  await autoDetectSingleInstrument()
}

async function handleWorkOnSheet(sheetName) {
  fileLoading.value = true
  uploadError.value = ''
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
      worksheetStatus.value[sheetName] = { ...worksheetStatus.value[sheetName], processed: true, sheetType: result.type }
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
    uploadError.value = err.message
  } finally {
    fileLoading.value = false
  }
}

function handleViewResults(sheetName) {
  const status = worksheetStatus.value[sheetName]
  if (status?.processed) activeTab.value = 'calculations'
}

function applyCurrentMapping() {
  if (!originalRawData.value.length) return
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
      out[reqCol] = (srcCol && srcCol !== '__na__' && row[srcCol] !== undefined) ? row[srcCol] : ''
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
      const result = await mappingTemplateManager.updateTemplate(currentMappingTemplateId.value, {
        columnMapping: columnMapping.value,
        fileColumns: fileColumns.value
      })
      if (result) {
        await loadSavedTemplates()
        showSnackbar('Mapping saved successfully', 'success')
      } else {
        showSnackbar('Failed to update mapping: No response from server', 'error')
      }
    } catch (e) {
      showSnackbar('Failed to update mapping: ' + (e.message || e), 'error')
    }
  } else {
    const templateName = `${instrumentType.value} - ${uploadedFile.value?.name || 'Custom'} - ${new Date().toLocaleDateString()}`
    try {
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
    try { return JSON.stringify(cell) } catch { return String(cell) }
  }
  return cell
}

function openMappingDialog() {
  if (sheetType.value === 'single') return
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

function closeMappingDialog() { showMappingDialog.value = false }

async function applyColumnMappingAndClose() {
  applyCurrentMapping()
  if (currentMappingTemplateId.value) {
    try {
      await mappingTemplateManager.updateTemplate(currentMappingTemplateId.value, {
        columnMapping: columnMapping.value,
        fileColumns: fileColumns.value
      })
    } catch (e) { /* non-fatal */ }
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
  let buffer = originalFileBuffer.value
  if ((!buffer || buffer.byteLength === 0) && originalDatasetId.value) {
    try {
      const res = await fetch(`${API_BASE_URL}/api/dataset/${originalDatasetId.value}/file`)
      if (!res.ok) {
        showSnackbar(
          res.status === 404
            ? 'The original workbook is no longer stored on the server. Please re-upload the file.'
            : `Could not load the original workbook (HTTP ${res.status}).`,
          'error'
        )
        return
      }
      buffer = await res.arrayBuffer()
      originalFileBuffer.value = buffer
    } catch (e) {
      showSnackbar('Network error loading workbook: ' + (e.message || e), 'error')
      return
    }
  }
  if (!buffer || buffer.byteLength === 0) {
    showSnackbar('No original workbook is available for this session. Please re-upload the file.', 'error')
    return
  }
  if (worksheetWorkflow.workbookSheets.value?.length > 0) {
    workbookSheets.value = [...worksheetWorkflow.workbookSheets.value]
  } else {
    workbookSheets.value = []
  }
  if (activeSession.value?.id) {
    loadWorksheetStatuses()
  }
  try {
    showWorkbookViewer.value = true
    await nextTick()
  } catch (error) {
    showSnackbar('Failed to open workbook viewer: ' + (error.message || error), 'error')
  }
}

async function downloadOriginalWorkbook() {
  if (!originalDatasetId.value) {
    showSnackbar('No original workbook is stored for this session.', 'error')
    return
  }
  try {
    const res = await fetch(`${API_BASE_URL}/api/dataset/${originalDatasetId.value}/download`)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const blob = await res.blob()
    let filename = `workbook_${originalDatasetId.value}.xlsx`
    const cd = res.headers.get('Content-Disposition') || ''
    const match = /filename\*?=(?:UTF-8'')?"?([^";]+)"?/i.exec(cd)
    if (match) filename = decodeURIComponent(match[1])
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    showSnackbar('Original workbook downloaded.', 'success')
  } catch (e) {
    showSnackbar('Download failed: ' + (e.message || e), 'error')
  }
}

function workOnSelectedSheet() {
  if (!currentSheetName.value) { alert('Please select a sheet first'); return }
  if (!originalFileBuffer.value) { alert('File buffer not available'); return }
  handleWorkOnSheet(currentSheetName.value)
  showWorkbookViewer.value = false
}

async function autoDetectSingleInstrument() {
  const sheetName = currentSheetName.value || workbookSheets.value?.[0]?.name
  if (!sheetName || !originalFileBuffer.value) { alert('Please select a sheet first'); return }
  currentSheetName.value = sheetName
  if (isDetecting.value) return
  isDetecting.value = true
  detectionStatus.value = 'scanning'
  autoDetectedFields.value = {}
  autoDetectedFieldsWithMetadata.value = {}
  autoDetectedAdditionalFields.value = {}
  detectedCurrencies.value = []
  detectedInstrumentType.value = ''
  excludedDetectedFields.value.clear()
  showDetectionSuccess.value = false
  try {
    if (!requiredColumns.value || requiredColumns.value.length === 0) {
      await loadConfig()
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
    detectionStatus.value = 'detecting'
    const detectionPromise = autoDetectInstrumentFields(
      originalFileBuffer.value,
      currentSheetName.value,
      requiredColumns.value,
      instrumentType.value,
      null, null, currencyFilter,
      (status) => { detectionStatus.value = status }
    )
    const timeoutPromise = new Promise((_, reject) =>
      setTimeout(() => reject(new Error('Detection timeout - scan took too long')), 30000)
    )
    const detectionResult = await Promise.race([detectionPromise, timeoutPromise])
    detectionStatus.value = 'validating'
    const normalized = normalizeDetectedFields(
      detectionResult?.fields,
      detectionResult?.fieldsWithMetadata,
      instrumentType.value,
      requiredColumns.value
    )
    detectionStatus.value = 'complete'
    const deriveUnion = { ...normalized.fields, ...(detectionResult?.additionalFields || {}) }
    const deriveUnionMeta = { ...normalized.fieldsWithMetadata }
    for (const [key, value] of Object.entries(detectionResult?.additionalFields || {})) {
      if (!(key in deriveUnionMeta)) {
        deriveUnionMeta[key] = {
          ...(value && typeof value === 'object' ? value : {}),
          originalLabel: key,
        }
      }
    }
    deriveDaysToMaturity(deriveUnion, deriveUnionMeta)
    const primaryAfterDerive = { ...normalized.fields }
    const metaAfterDerive = { ...normalized.fieldsWithMetadata }
    for (const [key, value] of Object.entries(deriveUnion)) {
      if (!(key in primaryAfterDerive) && deriveUnionMeta[key]?.source === 'auto-calculation') {
        primaryAfterDerive[key] = value
        metaAfterDerive[key] = deriveUnionMeta[key]
      }
    }
    autoDetectedFields.value = primaryAfterDerive
    autoDetectedFieldsWithMetadata.value = metaAfterDerive
    autoDetectedAdditionalFields.value = detectionResult?.additionalFields || {}
    detectedCurrencies.value = detectionResult?.currencies || []
    detectedInstrumentType.value = instrumentType.value
    await nextTick()
    if (!selectedCurrency.value) {
      if (detectedCurrencies.value.length === 1) {
        selectedCurrency.value = detectedCurrencies.value[0]
      } else if (detectedCurrencies.value.length > 1) {
        selectedCurrency.value = ''
      }
    }
    showDetectionSuccess.value = true
  } catch (error) {
    if (Object.keys(autoDetectedFields.value).length > 0) {
      showDetectionSuccess.value = true
    } else {
      alert('Auto Detect failed: ' + error.message)
    }
  } finally {
    isDetecting.value = false
  }
}

async function handleMultiTableDetect(event) {
  if (!event?.tables?.length) return
  if (!originalFileBuffer.value) { alert('File buffer not available — please re-upload the workbook.'); return }
  isDetecting.value = true
  detectionStatus.value = 'scanning'
  autoDetectedFields.value = {}
  autoDetectedFieldsWithMetadata.value = {}
  autoDetectedAdditionalFields.value = {}
  detectedCurrencies.value = []
  detectedInstrumentType.value = ''
  selectedCurrency.value = ''
  excludedDetectedFields.value.clear()
  showDetectionSuccess.value = false
  showMultiTableDetectionSuccess.value = false
  multiTableDetectionResults.value = []
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
    const totalTables = event.tables.length
    let processedTables = 0
    for (const table of event.tables) {
      processedTables++
      detectionStatus.value = `analyzing (table ${processedTables} of ${totalTables})`
      try {
        const tableData = table.data
        const TABLE_TIMEOUT_MS = 20000
        const timeoutPromise = new Promise((_, reject) =>
          setTimeout(
            () => reject(new Error(`Table "${table.tableName}" detection timed out after ${TABLE_TIMEOUT_MS / 1000}s`)),
            TABLE_TIMEOUT_MS
          )
        )
        const detectionPromise = autoDetectInstrumentFields(
          originalFileBuffer.value,
          event.sheetName,
          requiredColumns.value,
          event.instrumentType,
          table.range,
          tableData,
          currencyFilter,
          (status) => { detectionStatus.value = status }
        )
        const detectionResult = await Promise.race([detectionPromise, timeoutPromise])
        const normalized = normalizeDetectedFields(
          detectionResult?.fields,
          detectionResult?.fieldsWithMetadata,
          event.instrumentType,
          requiredColumns.value
        )
        const mergedFields = { ...normalized.fields }
        const mergedFieldsWithMetadata = { ...normalized.fieldsWithMetadata }
        const deriveUnion = { ...mergedFields, ...(detectionResult?.additionalFields || {}) }
        const deriveUnionMeta = { ...mergedFieldsWithMetadata }
        for (const [key, value] of Object.entries(detectionResult?.additionalFields || {})) {
          if (!(key in deriveUnionMeta)) {
            deriveUnionMeta[key] = {
              ...(value && typeof value === 'object' ? value : {}),
              originalLabel: key,
            }
          }
        }
        deriveDaysToMaturity(deriveUnion, deriveUnionMeta)
        for (const [key, value] of Object.entries(deriveUnion)) {
          if (!(key in mergedFields) && deriveUnionMeta[key]?.source === 'auto-calculation') {
            mergedFields[key] = value
            mergedFieldsWithMetadata[key] = deriveUnionMeta[key]
          }
        }
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
    detectionStatus.value = 'complete'
    multiTableDetectionResults.value = detectedInstruments
    showMultiTableDetectionSuccess.value = true
    showWorkbookViewer.value = false
  } catch (err) {
    console.error('Multi-table detection failed:', err)
    alert('Multi-table detection failed: ' + (err.message || 'Unknown error'))
  } finally {
    isDetecting.value = false
    detectionStatus.value = 'idle'
  }
}

// [FIX-MULTICURRENCY + EXCLUSION] Preserve multi-currency fields (with
// currencyVariants) in autoDetectedFields, but skip fields the user
// explicitly excluded in the multi-table popup.
function useMultiTableDetectedFields() {
  showMultiTableDetectionSuccess.value = false
  showWorkbookViewer.value = false

  const fullFields = {}
  const displayFields = {}

  for (const instrument of multiTableDetectionResults.value) {
    for (const [key, fieldObj] of Object.entries(instrument.fields)) {
      if (key in fullFields) continue
      if (excludedDetectedFields.value.has(key)) continue

      const isMulti =
        typeof fieldObj === 'object' && fieldObj !== null &&
        fieldObj.currencyVariants &&
        Object.keys(fieldObj.currencyVariants).length > 1
      if (isMulti) {
        fullFields[key] = { ...fieldObj }
        const cur = fieldObj.selectedCurrency || Object.keys(fieldObj.currencyVariants)[0]
        displayFields[key] = fieldObj.currencyVariants[cur]
      } else {
        const scalar = typeof fieldObj === 'object' && fieldObj !== null ? fieldObj.value : fieldObj
        fullFields[key] = scalar
        displayFields[key] = scalar
      }
    }
  }

  if (!displayFields.InstrumentName && multiTableDetectionResults.value.length > 0) {
    const fallback = multiTableDetectionResults.value[0].instrumentName || ''
    displayFields.InstrumentName = fallback
    fullFields.InstrumentName = fullFields.InstrumentName || fallback
  }

  const tabularData = [displayFields]
  rawData.value = tabularData
  originalRawData.value = JSON.parse(JSON.stringify(tabularData))
  cleanedData.value = JSON.parse(JSON.stringify(tabularData))
  const headers = Object.keys(displayFields)
  fileColumns.value = headers
  originalFileColumns.value = [...headers]
  worksheetSelected.value = true
  showPreview.value = true
  sheetType.value = 'single'
  mappingApplied.value = true
  extractedValues.value = { ...displayFields }
  autoDetectedFields.value = fullFields
  activeTab.value = 'cleaning'
}

function formatDetectedValue(field, value) {
  if (value === null || value === undefined) return '—'
  const lc = String(field).toLowerCase()
  if (lc.includes('frequency') || (lc.includes('coupon') && lc.includes('frequency'))) return String(value)
  if (lc.includes('interest') && lc.includes('payment') && lc.includes('frequency')) return String(value)
  if (lc.includes('payment') && lc.includes('frequency')) return String(value)
  if (lc.includes('date') || lc.includes('maturity')) {
    try {
      const date = new Date(value)
      if (!isNaN(date.getTime())) {
        return date.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' })
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

// [FIX-MULTICURRENCY] Full propagation. Mirrors the selected currency value
// into Cleaning / Calculations / Summary, then saves and re-runs calculations.
function updateSelectedCurrency(fieldName, currency, isAdditional = false) {
  const targetRef = isAdditional ? autoDetectedAdditionalFields : autoDetectedFields
  const targetFields = targetRef.value || {}
  const fieldData = targetFields[fieldName]
  if (!fieldData || !fieldData.currencyVariants || fieldData.currencyVariants[currency] === undefined) return

  const newValue = fieldData.currencyVariants[currency]

  // 1. update the field object itself
  fieldData.selectedCurrency = currency
  fieldData.value = newValue
  fieldData.currency = currency

  // 2. mirror into the other bucket if the same field name exists there
  const otherRef = isAdditional ? autoDetectedFields : autoDetectedAdditionalFields
  const otherFields = otherRef.value || {}
  if (otherFields[fieldName] && otherFields[fieldName] !== fieldData) {
    otherFields[fieldName].selectedCurrency = currency
    otherFields[fieldName].value = newValue
    otherFields[fieldName].currency = currency
  }

  // 3. metadata
  if (autoDetectedFieldsWithMetadata.value[fieldName]) {
    autoDetectedFieldsWithMetadata.value[fieldName].selectedCurrency = currency
    autoDetectedFieldsWithMetadata.value[fieldName].value = newValue
  }

  // 4. live data stores (single-row instruments)
  if (extractedValues.value) extractedValues.value[fieldName] = newValue
  if (rawData.value.length > 0 && fieldName in rawData.value[0]) rawData.value[0][fieldName] = newValue
  if (originalRawData.value.length > 0 && fieldName in originalRawData.value[0]) originalRawData.value[0][fieldName] = newValue
  if (cleanedData.value.length > 0 && fieldName in cleanedData.value[0]) cleanedData.value[0][fieldName] = newValue

  // 5. persist + recalc so Calculations / Summary / Portfolio Summary reflect it
  debouncedSave()
  if (cleanedData.value.length > 0) {
    calculateMetrics().catch(() => { /* non-fatal */ })
  }
  forceUpdate.value++
}

// [FIX-MULTICURRENCY] Per-field currency change inside the multi-table popup.
function updateMultiTableCurrency(instrument, fieldName, currency) {
  const fieldData = instrument.fields[fieldName]
  if (!fieldData || !fieldData.currencyVariants || fieldData.currencyVariants[currency] === undefined) return
  fieldData.selectedCurrency = currency
  fieldData.value = fieldData.currencyVariants[currency]
  fieldData.currency = currency
  multiTableDetectionResults.value = [...multiTableDetectionResults.value]
}

async function handleCustomCurrencyInput() {
  if (customCurrency.value) customCurrency.value = customCurrency.value.toUpperCase()
  if (customCurrency.value && customCurrency.value.length === 3) {
    try {
      const detectionResult = await autoDetectInstrumentFields(
        originalFileBuffer.value,
        currentSheetName.value,
        requiredColumns.value,
        instrumentType.value,
        null, null,
        customCurrency.value,
        (status) => { detectionStatus.value = status }
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
    } catch (error) { /* non-fatal */ }
  }
}

async function handleCurrencyChange() {
  if (!currentSheetName.value || !originalFileBuffer.value) return
  if (isDetecting.value) return
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
    const detectionResult = await autoDetectInstrumentFields(
      originalFileBuffer.value,
      currentSheetName.value,
      requiredColumns.value,
      instrumentType.value,
      null, null, currencyFilter,
      (status) => { detectionStatus.value = status }
    )
    const normalized = normalizeDetectedFields(
      detectionResult?.fields,
      detectionResult?.fieldsWithMetadata,
      instrumentType.value,
      requiredColumns.value
    )
    const mergedFields = { ...normalized.fields }
    const mergedFieldsWithMetadata = { ...normalized.fieldsWithMetadata }
    if (Object.keys(mergedFields).length > 0) {
      const deriveUnion = { ...mergedFields, ...(detectionResult?.additionalFields || {}) }
      const deriveUnionMeta = { ...mergedFieldsWithMetadata }
      for (const [key, value] of Object.entries(detectionResult?.additionalFields || {})) {
        if (!(key in deriveUnionMeta)) {
          deriveUnionMeta[key] = {
            ...(value && typeof value === 'object' ? value : {}),
            originalLabel: key,
          }
        }
      }
      deriveDaysToMaturity(deriveUnion, deriveUnionMeta)
      for (const [key, value] of Object.entries(deriveUnion)) {
        if (!(key in mergedFields) && deriveUnionMeta[key]?.source === 'auto-calculation') {
          mergedFields[key] = value
          mergedFieldsWithMetadata[key] = deriveUnionMeta[key]
        }
      }
      autoDetectedFields.value = mergedFields
      autoDetectedFieldsWithMetadata.value = mergedFieldsWithMetadata
      autoDetectedAdditionalFields.value = detectionResult?.additionalFields || {}
      detectedCurrencies.value = detectionResult?.currencies || []
      detectedInstrumentType.value = instrumentType.value
    }
    showDetectionSuccess.value = true
  } catch (error) { /* non-fatal */ } finally {
    isDetecting.value = false
  }
}

async function useDetectedFields() {
  const preservedDetectedFields = JSON.parse(JSON.stringify(autoDetectedFields.value))
  const preservedDetectedFieldsWithMetadata = JSON.parse(JSON.stringify(autoDetectedFieldsWithMetadata.value))
  const preservedDetectedAdditionalFields = JSON.parse(JSON.stringify(autoDetectedAdditionalFields.value))
  const preservedDetectedCurrencies = JSON.parse(JSON.stringify(detectedCurrencies.value))
  const mergedDetectedFields = { ...preservedDetectedFields }
  for (const [key, value] of Object.entries(preservedDetectedAdditionalFields)) {
    if (!(key in mergedDetectedFields)) mergedDetectedFields[key] = value
  }
  autoDetectedFields.value = mergedDetectedFields
  autoDetectedFieldsWithMetadata.value = preservedDetectedFieldsWithMetadata
  autoDetectedAdditionalFields.value = preservedDetectedAdditionalFields
  detectedCurrencies.value = preservedDetectedCurrencies
  isUsingDetectedFields.value = true
  showDetectionSuccess.value = false
  showWorkbookViewer.value = false

  const values = {}
  const applyIfIncluded = (key, value) => {
    // FIX: honour the excludedDetectedFields toggle set from the popup.
    if (excludedDetectedFields.value.has(key)) return
    if (typeof value === 'object' && value !== null) {
      if (value.currencyVariants && value.selectedCurrency && value.currencyVariants[value.selectedCurrency]) {
        values[key] = value.currencyVariants[value.selectedCurrency]
      } else {
        values[key] = value.value
      }
    } else {
      values[key] = value
    }
  }
  for (const [key, value] of Object.entries(autoDetectedFields.value)) applyIfIncluded(key, value)
  for (const [key, value] of Object.entries(autoDetectedAdditionalFields.value)) {
    if (!(key in values)) applyIfIncluded(key, value)
  }

  if (selectedCurrency.value && selectedCurrency.value !== 'custom') {
    values['Currency'] = selectedCurrency.value
  } else if (selectedCurrency.value === 'custom' && customCurrency.value) {
    values['Currency'] = customCurrency.value.toUpperCase()
  }
  if (currentSheetName.value && String(currentSheetName.value).trim()) {
    const sheetName = String(currentSheetName.value).trim()
    if (!values['TBillName']) values['TBillName'] = sheetName
    if (!values['BondName']) values['BondName'] = sheetName
    if (!values['InstrumentName']) values['InstrumentName'] = sheetName
    if (!values['Instrument Name']) values['Instrument Name'] = sheetName
    if (!values['instrument_name']) values['instrument_name'] = sheetName
  }
  const instType = String(instrumentType.value || '').trim()
  if (instType) {
    if (!values['instrument_type']) values['instrument_type'] = instType
    if (!values['Instrument Type']) values['Instrument Type'] = instType
  }
  extractedValues.value = values
  rawData.value = [{ ...values }]
  originalRawData.value = [{ ...values }]
  cleanedData.value = [{ ...values }]
  fileColumns.value = Object.keys(values)
  originalFileColumns.value = [...fileColumns.value]
  worksheetSelected.value = true
  showPreview.value = true
  sheetType.value = 'single'
  mappingApplied.value = true
  showWorkbookViewer.value = false
  await nextTick()
  activeTab.value = 'cleaning'
  await nextTick()
}

function handleProcessSheetFromViewer(sheetName, sheetData, sheetHeaders) {
  currentSheetName.value = sheetName
  clearActiveCache(true)
  originalRawData.value = sheetData || []
  rawData.value = sheetData.map(row => {
    const normalized = {}
    for (const [key, value] of Object.entries(row)) {
      normalized[key] = getCellValue(value)
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
  currentSheetName.value = sheetName
  rawData.value = sheetData
}

function handleProcessSheet(sheetName, sheetData, sheetHeaders) {
  showWorkbookViewer.value = false
  rawData.value = sheetData
  applyCurrentMapping()
}

function handleProcessSheetFromModal(payload) {
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

function updateExtractedValue(key, value) { extractedValues.value[key] = value }
function clearExtractedValue(key) { extractedValues.value[key] = 'N/A' }

function toggleExcludeField(fieldKey) {
  if (excludedDetectedFields.value.has(fieldKey)) {
    excludedDetectedFields.value.delete(fieldKey)
  } else {
    excludedDetectedFields.value.add(fieldKey)
  }
  excludedDetectedFields.value = new Set(excludedDetectedFields.value)

  // Persist across page reloads
  try {
    sessionStorage.setItem('excluded_fields', JSON.stringify([...excludedDetectedFields.value]))
  } catch (e) { /* ignore */ }

  // FIX: rebuild cleanedData from rawData so the Excel preview
  // and the valuation engine reflect the current exclusion set.
  // The preview is now the single source of truth.
  if (cleanedData.value.length > 0 && rawData.value.length > 0) {
    applyCleaning()
  }

  debouncedSave()
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
  autoDetectedFieldsWithMetadata.value[fieldName] = {
    location: 'custom',
    source: 'manual',
    originalLabel: fieldName
  }
  extractedValues.value[fieldName] = fieldValue
  if (cleanedData.value.length > 0) cleanedData.value[0][fieldName] = fieldValue
  if (rawData.value.length > 0) rawData.value[0][fieldName] = fieldValue
  if (!fileColumns.value.includes(fieldName)) fileColumns.value.push(fieldName)
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
  } catch (err) { /* non-fatal */ }
}

function markWorksheetAsSaved() {
  const worksheetName = currentSheetName.value
  if (worksheetName) worksheetStatuses.value[worksheetName] = 'saved'
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
  return dedupeColumns([...allFields])
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
    if (isPercentageField(col)) return rounded.toFixed(2) + '%'
    return rounded.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  }
  if (isDateField(value)) {
    const d = new Date(value)
    return d.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      timeZone: 'UTC'
    })
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

const hasNumericColumns = computed(() => portfolioSummary.value.columns.some(col => isNumericField(col)))

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
  if (!currentData.length && !completedData.length) return
  const allColumns = new Set()
  currentData.forEach(row => Object.keys(row).forEach(k => allColumns.add(k)))
  completedData.forEach(row => Object.keys(row).forEach(k => allColumns.add(k)))
  const displayCols = dedupeColumns(Array.from(allColumns))
  const wb = XLSX.utils.book_new()
  if (currentData.length) {
    const filteredCols = displayCols.filter(c => !isExcludedColumn(c))
    const headerRow = filteredCols.map(formatColumnHeader)
    const currentBody = currentData.map(row => filteredCols.map(col => {
      const value = row[col]
      if (typeof value === 'number' && !isNaN(value)) {
        const rounded = Math.round(value * 100) / 100
        return rounded.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
      }
      return value !== undefined ? value : ''
    }))
    const wsCurrent = XLSX.utils.aoa_to_sheet([headerRow, ...currentBody])
    XLSX.utils.book_append_sheet(wb, wsCurrent, 'Current Selection')
  }
  if (completedData.length) {
    const filteredCols = displayCols.filter(c => !isExcludedColumn(c))
    const headerRow = filteredCols.map(formatColumnHeader)
    const completedBody = completedData.map(row => filteredCols.map(col => {
      const value = row[col]
      if (typeof value === 'number' && !isNaN(value)) {
        const rounded = Math.round(value * 100) / 100
        return rounded.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
      }
      return value !== undefined ? value : ''
    }))
    const wsCompleted = XLSX.utils.aoa_to_sheet([headerRow, ...completedBody])
    XLSX.utils.book_append_sheet(wb, wsCompleted, 'All Completed History')
  }
  const summaryInfo = [
    ['Instrument Summary Export'],
    ['Export Date', new Date().toLocaleString()],
    ['Current Sheet', currentSheetName.value || 'N/A'],
    [''],
    ['Current Selection Records', currentData.length],
    ['Total Completed Records', completedData.length],
    ['Total Columns', displayCols.length]
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
}

function viewPreviousSummary() {
  excelPopupMode.value = 'previous'
  showInstrumentExcelPopup.value = true
  sortColumn.value = ''
  sortOrder.value = 'asc'
  currentPage.value = 1
}

function viewAllSummaries() {
  excelPopupMode.value = 'all'
  showInstrumentExcelPopup.value = true
  sortColumn.value = ''
  sortOrder.value = 'asc'
  currentPage.value = 1
}

function viewInstrumentSummaryExcel() {
  excelPopupMode.value = 'current'
  showInstrumentExcelPopup.value = true
  sortColumn.value = ''
  sortOrder.value = 'asc'
  currentPage.value = 1
}

function viewPreviousSummariesExcel() {
  excelPopupMode.value = 'previous'
  showInstrumentExcelPopup.value = true
  sortColumn.value = ''
  sortOrder.value = 'asc'
  currentPage.value = 1
}

function handleWorkbookLoaded(fileName) {
  currentWorkbookName.value = fileName || 'Unknown'
}

function closeInstrumentExcelPopup() { showInstrumentExcelPopup.value = false }

function continueWorkingOnCurrent() {
  clearActiveCache(true)
  showWorkbookViewer.value = true
  activeTab.value = 'upload'
  forceUpdate.value++
}

function chooseAnotherSheet() {
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
  if (isTimeField) return Math.round(num)
  if (type === 'percentage') return Math.round(num * 100) / 100
  if (type === 'money') return Math.round(num * 100) / 100
  return num
}

// ─────────────────────────────────────────────────────────────
// FIX 5 — downloadCalculatedInstrumentsExcel dedupes columns.
// ─────────────────────────────────────────────────────────────
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
  const columns = dedupeColumns(Array.from(allColumns).filter(c => !isExcludedColumn(c)))
  const data = [columns.map(formatColumnHeader)]
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
  
  // Sync edits from the Excel preview back to the Field Selection list
  if (data.length > 0) {
    Object.entries(data[0]).forEach(([key, val]) => {
      if (autoDetectedFields.value[key] !== undefined) {
         if (typeof autoDetectedFields.value[key] === 'object' && autoDetectedFields.value[key] !== null) {
            autoDetectedFields.value[key].value = val
            if (autoDetectedFields.value[key].currencyVariants && autoDetectedFields.value[key].selectedCurrency) {
               autoDetectedFields.value[key].currencyVariants[autoDetectedFields.value[key].selectedCurrency] = val
            }
         } else {
            autoDetectedFields.value[key] = val
         }
      }
      if (extractedValues.value) {
        extractedValues.value[key] = val
      }
    })
  }
  
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
  if (!uploadedFile.value) return
  if (!rawData.value.length) return
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
  if (!rawData.value.length) return
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
            const d = new Date(row[k])
            if (!isNaN(d)) {
              const utcDay = String(d.getUTCDate()).padStart(2, '0')
              const utcMonth = String(d.getUTCMonth() + 1).padStart(2, '0')
              const utcYear = d.getUTCFullYear()
              const utcShortYear = utcYear.toString().slice(-2)
              let formattedDate = ''
              if (format === 'YYYY-MM-DD') formattedDate = `${utcYear}-${utcMonth}-${utcDay}`
              else if (format === 'DD-MM-YYYY') formattedDate = `${utcDay}-${utcMonth}-${utcYear}`
              else if (format === 'MM-DD-YYYY') formattedDate = `${utcMonth}-${utcDay}-${utcYear}`
              else if (format === 'DD/MM/YYYY') formattedDate = `${utcDay}/${utcMonth}/${utcYear}`
              else if (format === 'MM/DD/YYYY') formattedDate = `${utcMonth}/${utcDay}/${utcYear}`
              else if (format === 'YYYY/MM/DD') formattedDate = `${utcYear}/${utcMonth}/${utcDay}`
              else if (format === 'DD-MM-YY') formattedDate = `${utcDay}-${utcMonth}-${utcShortYear}`
              else if (format === 'MM-DD-YY') formattedDate = `${utcMonth}-${utcDay}-${utcShortYear}`
              else formattedDate = `${utcYear}-${utcMonth}-${utcDay}`
              row[k] = formattedDate
              standardized++
            }
          }
        })
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
          if (!excludedDetectedFields.value.has(key)) newRow[key] = row[key]
        })
        return newRow
      })
      operations.push(`Removed ${excludedCount} excluded fields from data`)
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
    showSnackbar('Error during cleaning: ' + error.message, 'error')
  }
}

async function continueAfterCleaning() {
  if (!cleanedData.value.length) return
  if (sheetType.value === 'single' && excludedDetectedFields.value.size > 0) {
    const filteredData = cleanedData.value.map(row => {
      const filteredRow = {}
      for (const [key, value] of Object.entries(row)) {
        const isExcluded = excludedDetectedFields.value.has(key)
        if (!isExcluded) filteredRow[key] = value
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
  if (isCalculating.value) return
  isCalculating.value = true
  try {
    const stored = sessionStorage.getItem('excluded_fields')
    if (stored) {
      const arr = JSON.parse(stored)
      if (Array.isArray(arr)) arr.forEach(k => excludedDetectedFields.value.add(k))
    }
  } catch (e) { /* ignore */ }
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
              if (freqLower.includes('semi') || freqLower.includes('half')) normalizedValue = 2
              else if (freqLower.includes('quarter')) normalizedValue = 4
              else if (freqLower.includes('month') || freqLower.includes('monthly')) normalizedValue = 12
              else if (freqLower.includes('annual') || freqLower.includes('year')) normalizedValue = 1
              else normalizedValue = parseFloat(value) || 2
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
    dataForCalculation = JSON.parse(JSON.stringify(cleanedData.value))
  }
  if (excludedDetectedFields.value.size > 0) {
    dataForCalculation = dataForCalculation.map(row => {
      const newRow = {}
      Object.keys(row).forEach(key => {
        if (!excludedDetectedFields.value.has(key)) newRow[key] = row[key]
      })
      return newRow
    })
  }
  try {
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
            columns: dedupeColumns(response.instrument_summary.columns || []),
            rows: currentRowsWithWorkbook
          }
        }
        if (response?.portfolio_summary) portfolioSummary.value = response.portfolio_summary
        if (activeSession.value?.id && instrumentSummary.value?.rows?.length) {
          try {
            const firstAgg = response?.aggregate || {}
            await api.portfolioAPI.saveSummary({
              session_id: activeSession.value.id,
              instrument_type: instrumentType.value,
              instrument_name: currentSheetName.value || instrumentType.value,
              total_value: firstAgg.total_value ?? firstAgg.totalValue ?? 0,
              face_value: firstAgg.total_face_value ?? firstAgg.face_value ?? 0,
              count: firstAgg.instrument_count ?? firstAgg.instrumentCount ?? instrumentSummary.value.rows.length,
              avg_rate: firstAgg.avg_rate ?? firstAgg.avgRate ?? 0,
              details: instrumentSummary.value.rows,
              detail_headers: instrumentSummary.value.columns || [],
              aggregate: firstAgg,
              valuation_date: activeValuationDate.value || new Date().toISOString().split('T')[0]
            })
          } catch (saveError) { console.warn('Multi-instrument saveSummary failed:', saveError) }
        }
        const results = response?.results || {}
        const firstInstType = Object.keys(results)[0]
        if (firstInstType && results[firstInstType]) {
          calculations.value = results[firstInstType].data
          if (response?.aggregate) {
            const agg = { ...response.aggregate }
            allCalculations.value = agg
            selectedCalculations.value = agg
          } else if (response?.data?.aggregates) {
            const agg = { ...response.data.aggregates }
            allCalculations.value = agg
            selectedCalculations.value = agg
          } else {
            allCalculations.value = results[firstInstType].data
            selectedCalculations.value = results[firstInstType].data
          }
        }
        isUsingDetectedFields.value = false
      } else if (response?.data) {
        calculations.value = response.data
        if (response.data?.field_detection) fieldDetectionResults.value = response.data.field_detection
        const backendInstrumentNames = response?.instrument_names || []
        const calcArray = response.data.calculations || []
        const backendAggregates = response.data.aggregates || {}
        if (calcArray.length === 1) {
          const singleCalc = calcArray[0]
          calculations.value = singleCalc
          const agg = buildAggregatesFromBackend(backendAggregates, singleCalc, instrumentType.value)
          agg.instrumentCount = agg.instrumentCount ?? 1
          if (response.data.fred) agg.fred = response.data.fred
          const displayable = hasDisplayableCalculation(agg)
          const failedStatuses = ['cannot_calculate', 'error']
          const isFailed = failedStatuses.includes(singleCalc.status) || (!displayable && singleCalc.status !== 'success')
          if (singleCalc.status === 'partial' && (singleCalc.error || singleCalc.warning || singleCalc.missing_fields?.length)) {
            const warningMsg = singleCalc.warning || formatCalculationFailureMessage(singleCalc, 'Partial calculation')
            showSnackbar(`Partial calculation: ${warningMsg}`, 'warning', 6000)
            agg.status = 'partial'
          } else if (isFailed && !displayable) {
            const fullErrorMsg = formatCalculationFailureMessage(singleCalc)
            showSnackbar(`Calculation failed: ${fullErrorMsg}`, 'error')
            allCalculations.value = {
              status: 'error',
              message: fullErrorMsg,
              error: singleCalc.error,
              missing_fields: singleCalc.missing_fields || [],
              invalid_fields: singleCalc.invalid_fields || [],
              ...agg
            }
            selectedCalculations.value = allCalculations.value
          } else {
            allCalculations.value = agg
            selectedCalculations.value = agg
          }
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
          instrumentSummary.value = { columns: dedupeColumns(Array.from(currentCols)), rows: [filteredRowWithWorkbook] }
        } else if (calcArray.length === 0 && cleanedData.value.length > 0) {
          console.warn('Backend returned empty calculations — running local fallback')
          const rows = cleanedData.value.map((row, idx) => {
            const enriched = { ...row, 'Instrument Name': row.InstrumentName || row['Instrument Name'] || currentSheetName.value || `Instrument ${idx + 1}` }
            const result = runInstrumentCalculations(enriched, instrumentType.value)
            return {
              'Instrument Name': enriched['Instrument Name'],
              'Instrument Type': instrumentType.value,
              ...result,
              'Worksheet': currentSheetName.value || 'Calculated',
              'Workbook': currentWorkbookName.value || 'Unknown'
            }
          })
          const cols = new Set()
          rows.forEach(r => Object.keys(r).forEach(k => cols.add(k)))
          instrumentSummary.value = { columns: dedupeColumns(Array.from(cols)), rows }
          const agg = computeAggregate(rows)
          agg.instrumentCount = rows.length
          allCalculations.value = agg
          selectedCalculations.value = agg
          calculations.value = agg
          showSnackbar('Calculated locally — backend returned empty result. Verify the /calculations/execute-by-type endpoint.', 'warning', 6000)
        } else if (calcArray.length > 1) {
          const agg = buildAggregatesFromBackend(backendAggregates, null, instrumentType.value)
          agg.instrumentCount = agg.instrumentCount ?? calcArray.length
          if (response.data.fred) agg.fred = response.data.fred
          if (!hasDisplayableCalculation(agg) && response.data.status === 'cannot_calculate') {
            const firstFail = calcArray.find(c => c.status !== 'success') || calcArray[0]
            const fullErrorMsg = formatCalculationFailureMessage(firstFail)
            showSnackbar(`Calculation failed: ${fullErrorMsg}`, 'error')
            allCalculations.value = { status: 'error', message: fullErrorMsg, ...agg }
            selectedCalculations.value = allCalculations.value
          } else {
            allCalculations.value = agg
            selectedCalculations.value = agg
          }
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
          instrumentSummary.value = { columns: dedupeColumns(Array.from(currentCols)), rows: rowsWithWorkbook }
          if (response.data.portfolio_summary) {
            portfolioSummary.value = response.data.portfolio_summary
          } else {
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
            const portfolioCols = new Set()
            Object.keys(portfolioRow).forEach(k => portfolioCols.add(k))
            portfolioSummary.value = { columns: dedupeColumns(Array.from(portfolioCols)), rows: [portfolioRow] }
            const existingPortfolioRows = completedPortfolioSummary.value.rows || []
            const mergedPortfolioRows = [...existingPortfolioRows, portfolioRow]
            const allPortfolioCols = new Set()
            mergedPortfolioRows.forEach(r => Object.keys(r).forEach(k => allPortfolioCols.add(k)))
            completedPortfolioSummary.value = { columns: dedupeColumns(Array.from(allPortfolioCols)), rows: mergedPortfolioRows }
          }
          if (portfolioSummary.value) {
            let existingSnapshot = { instrumentsWithDetails: [] }
            try {
              const existing = await sessionManager.getWorksheetData(activeSession.value?.id, '__portfolio_summary__')
              if (existing && existing.instrumentsWithDetails) existingSnapshot = existing
            } catch (e) { /* no existing */ }
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
            try {
              await api.portfolioAPI.saveSummary({
                session_id: activeSession.value?.id,
                instrument_type: instrumentType.value,
                instrument_name: currentSheetName.value || instrumentType.value,
                total_value: agg?.totalValue ?? 0,
                face_value: agg?.faceValue ?? 0,
                count: agg?.instrumentCount ?? 0,
                avg_rate: agg?.avgRate ?? 0,
                details: portfolioSummary.value?.rows || [],
                detail_headers: portfolioSummary.value?.columns || [],
                aggregate: agg || {},
                valuation_date: activeValuationDate.value || new Date().toISOString().split('T')[0]
              })
            } catch (saveError) { /* non-fatal */ }
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
          instrumentSummary.value = { columns: dedupeColumns(Array.from(currentCols)), rows: rowsWithWorkbook }
          const agg = buildAggregatesFromBackend(backendAggregates, calcArray[0] || null, instrumentType.value)
          if (response.data.fred) agg.fred = response.data.fred
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
          portfolioSummary.value = { columns: dedupeColumns(Array.from(currentPortfolioCols)), rows: [portfolioRow] }
        } else {
          const backendErrors = response.data?.errors || []
          const missingFields = response.data?.missing_fields || []
          const invalidFields = response.data?.invalid_fields || []
          let errorMsg = 'Not calculable — required input not detected.'
          if (backendErrors.length > 0) errorMsg = backendErrors.map(e => e.message || e).join('; ')
          if (missingFields.length > 0) errorMsg += ` Missing: ${missingFields.join(', ')}`
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
        if (response?.portfolio_summary || response.data?.portfolio_summary) {
          const portfolioData = response?.portfolio_summary || response.data?.portfolio_summary
          try {
            await api.portfolioAPI.saveSummary({
              session_id: activeSession.value?.id,
              instrument_type: instrumentType.value,
              instrument_name: currentSheetName.value || instrumentType.value,
              total_value: allCalculations.value?.totalValue ?? 0,
              face_value: allCalculations.value?.faceValue ?? 0,
              count: allCalculations.value?.instrumentCount ?? 0,
              avg_rate: allCalculations.value?.avgRate ?? 0,
              details: portfolioData.rows || [],
              detail_headers: portfolioData.columns || [],
              aggregate: allCalculations.value || {},
              valuation_date: activeValuationDate.value || new Date().toISOString().split('T')[0]
            })
          } catch (saveError) { /* non-fatal */ }
          let existingSnapshot = { instrumentsWithDetails: [] }
          try {
            const existing = await sessionManager.getWorksheetData(activeSession.value?.id, '__portfolio_summary__')
            if (existing && existing.instrumentsWithDetails) existingSnapshot = existing
          } catch (e) { /* no existing */ }
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
            fredFilters: {
              country: effectiveCountry.value,
              currency: effectiveCurrency.value,
              maturity: effectiveMaturity.value,
              maturityMode: maturityMode.value === 'dateRange' ? 'date' : 'tenor',
              fromDate: yieldCurveStartDate.value,
              toDate: yieldCurveEndDate.value
            },
            uploadedFile: uploadedFile.value?.name || null,
            originalDatasetId: originalDatasetId.value,
            originalFileName: uploadedFile.value?.name || null,
            cleaningStats: cleaningStats.value,
            sessionSavedAt: sessionSavedAt.value || new Date().toISOString(),
            manualInputs: manualInputs.value,
            formulas: formulas.value,
            autoDetectedFields: autoDetectedFields.value,
            autoDetectedFieldsWithMetadata: autoDetectedFieldsWithMetadata.value,
            autoDetectedAdditionalFields: autoDetectedAdditionalFields.value,
            detectedCurrencies: detectedCurrencies.value,
            excludedDetectedFields: Array.from(excludedDetectedFields.value),
            sheetType: sheetType.value,
            currentSheetName: currentSheetName.value,
            extractedValues: extractedValues.value,
            selectedCurrency: selectedCurrency.value,
            customCurrency: customCurrency.value
          })
        }
        saveSessionData()
      } else {
        const errorMsg = response?.message || response?.error || 'Unknown error'
        showSnackbar('Calculation failed: ' + errorMsg, 'error')
      }
      isUsingDetectedFields.value = false
      try { await enrichCalculationsWithFred() } catch (fredError) { /* non-fatal */ }
      try { await saveSessionData(true) } catch (e) { console.warn('Post-calc save failed:', e) }
      forceUpdate.value++
    }
  } catch (err) {
    showSnackbar('Error calculating metrics: ' + (err.message || 'Unknown error'), 'error')
    isUsingDetectedFields.value = false
  } finally {
    isCalculating.value = false
  }
}

async function continueToVisualizations() {
  if (!hasCleanedData.value) return
  if (!allCalculations.value.totalValue) await calculateMetrics()
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
  if (!hasCleanedData.value) return
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
      fredFilters: {
        country: effectiveCountry.value,
        currency: effectiveCurrency.value,
        maturity: effectiveMaturity.value,
        maturityMode: maturityMode.value === 'dateRange' ? 'date' : 'tenor',
        fromDate: yieldCurveStartDate.value,
        toDate: yieldCurveEndDate.value
      },
      uploadedFile: uploadedFile.value?.name || null,
      originalDatasetId: originalDatasetId.value,
      originalFileName: uploadedFile.value?.name || null,
      cleaningStats: cleaningStats.value,
      sessionSavedAt: sessionSavedAt.value || new Date().toISOString(),
      manualInputs: manualInputs.value,
      formulas: formulas.value,
      sheetType: sheetType.value,
      currentSheetName: currentSheetName.value,
      extractedValues: extractedValues.value,
      selectedCurrency: selectedCurrency.value,
      customCurrency: customCurrency.value
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
    if (maturityMode.value === 'maturity') payload.maturity = maturity
    else {
      payload.from_date = from_date
      payload.to_date = to_date
    }
    const response = await api.fredAPI.getYieldCurve(payload)
    if (response?.success && response.data) {
      const curveData = response.data
      if (curveData.maturities && curveData.maturities.length) {
        const isDateMode = maturityMode.value === 'dateRange'
        const points = curveData.maturities.map((m, idx) => {
          const dateStr = curveData.dates?.[idx] || null
          const labelStr = curveData.labels?.[idx] || m
          
          if (isDateMode && dateStr) {
            return {
              x: new Date(dateStr).getTime(),
              y: curveData.rates?.[idx] || 0,
              maturity: null,
              maturityLabel: dateStr,
              rate: curveData.rates?.[idx] || 0,
              date: dateStr,
              isDate: true
            }
          }
          const matNum = parseFloat(m) || 1.0
          return {
            x: matNum,
            y: curveData.rates?.[idx] || 0,
            maturity: matNum,
            maturityLabel: labelStr,
            rate: curveData.rates?.[idx] || 0,
            date: dateStr,
            isDate: false
          }
        })
        yieldCurveCache.set(cacheKey, { data: points, timestamp: Date.now() })
        yieldCurveData.value = points
        chartSeriesLabel.value = `FRED Yield Curve (${curveData.country || normalizedCountry})`
        yieldCurveError.value = ''
      } else {
        yieldCurveData.value = []
        yieldCurveError.value = curveData.note || 'No yield curve data available for the selected filters.'
        chartSeriesLabel.value = ''
      }
    } else {
      yieldCurveData.value = []
      yieldCurveError.value = response?.data?.note || response?.message || 'Failed to fetch yield curve from FRED'
      chartSeriesLabel.value = ''
    }
  } catch (err) {
    yieldCurveData.value = []
    yieldCurveError.value = err.message || 'Network error – please try again'
    chartSeriesLabel.value = ''
  } finally {
    yieldCurveLoading.value = false
    await nextTick()
    await renderYieldCurveChart()
    updateFredBenchmark()
    try { await saveSessionData(true) } catch (e) { console.warn('Post-FRED save failed:', e) }
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
  if (!yieldCurveChart.value || !yieldCurveData.value.length) return
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
      return { x: dateObj.getTime(), y: d.rate, label: d.date, originalDate: d.date }
    })
    xScaleOptions = {
      type: 'time',
      time: { unit: 'month', displayFormats: { month: 'MMM yyyy' } },
      title: { display: true, text: xAxisTitle },
      ticks: { maxRotation: 45, minRotation: 45 }
    }
  } else {
    const period = effectiveMaturity.value
    let unitLabel = 'Years'
    let maxX = 0
    const match = period.match(/^(\d+)([YMW])$/)
    if (match) {
      const num = parseInt(match[1], 10)
      const unit = match[2]
      if (unit === 'Y') { unitLabel = 'Years'; maxX = num + 0.5 }
      else if (unit === 'M') { unitLabel = 'Months'; maxX = num + 0.5 }
      else if (unit === 'W') { unitLabel = 'Weeks'; maxX = num + 0.5 }
    } else {
      const num = parseFloat(period) || 10
      unitLabel = 'Years'
      maxX = num + 0.5
    }
    const filterYears = parseMaturityToYears(period)
    const filteredData = yieldCurveData.value.filter(d => d.maturity <= filterYears)
    if (!filteredData.length) {
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
        autoSkip: false,
        stepSize: 1,
        maxRotation: 0,
        minRotation: 0,
        callback: function (value) {
          if (!Number.isInteger(value) || value < 0) return null
          if (value > maxX) return null
          const closest = filteredData.find(p => Math.abs(p.maturity - value) < 0.01)
          if (closest && closest.maturityLabel) return closest.maturityLabel
          return value.toString()
        }
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
            title: (items) => items[0]?.raw?.label || '',
            label: (ctx) => `Yield: ${ctx.parsed.y.toFixed(2)}%`
          }
        }
      },
      scales: {
        x: xScaleOptions,
        y: { title: { display: true, text: 'Yield (%)' }, beginAtZero: false }
      }
    }
  })
  setTimeout(() => {
    if (yieldCurveChart.value) {
      try { chartImageData.value = yieldCurveChart.value.toDataURL('image/png', 1.0) } catch (e) { /* non-fatal */ }
    }
  }, 1000)
}

function onCustomCountryInput() { selectedCountryOption.value = '__custom__'; onFredFilterChange() }
function onCustomCurrencyInput() { selectedCurrencyOption.value = '__custom__'; onFredFilterChange() }
function onCustomMaturityInput() { selectedMaturityOption.value = '__custom__'; onFredFilterChange() }
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
      allCalculations.value.fred = { ...bench, spread_vs_market: +(portfolio - bench.benchmark_rate).toFixed(2) }
      calculations.value.fred = allCalculations.value.fred
    } else {
      if (allCalculations.value.fred) delete allCalculations.value.fred
      if (calculations.value.fred) delete calculations.value.fred
    }
  } catch (e) { /* non-fatal */ }
}

async function loadSavedTemplates() {
  try {
    const templates = await mappingTemplateManager.getTemplatesByInstrument(instrumentType.value)
    savedTemplates.value = templates || []
  } catch (e) {
    savedTemplates.value = []
  }
}

async function saveTemplates() {}

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
      if (!currentMappingTemplateId.value) currentMappingTemplateId.value = result.id
      await loadSavedTemplates()
      newTemplateName.value = ''
      showSnackbar('Mapping saved successfully', 'success')
    } else {
      showSnackbar('Failed to save mapping')
    }
  } catch (e) {
    showSnackbar('Error saving mapping: ' + e.message)
  }
}

async function applyTemplate(templateId) {
  if (!templateId) return
  try {
    const template = await mappingTemplateManager.getTemplate(templateId)
    if (!template) { showSnackbar('Failed to load template'); return }
    columnMapping.value = { ...template.column_mapping }
    if (template.file_columns) fileColumns.value = [...template.file_columns]
    currentMappingTemplateId.value = template.id
    applyCurrentMapping()
    debouncedSave()
    forceUpdate.value++
    showSnackbar('Mapping loaded successfully', 'success')
  } catch (e) {
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
        if (currentMappingTemplateId.value === templateId) currentMappingTemplateId.value = null
        showSnackbar('Mapping deleted successfully', 'success')
      } else {
        showSnackbar('Failed to delete mapping')
      }
    } catch (e) {
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
    if (!isNaN(val)) newCalculations[key] = val
  })
  if (!newCalculations.totalValue) newCalculations.totalValue = parseFloat(selectedRow['Total Value'] || selectedRow['total_value'] || 0)
  if (!newCalculations.instrumentCount) newCalculations.instrumentCount = parseFloat(selectedRow['Instrument Count'] || selectedRow['instrument_count'] || 1)
  selectedCalculations.value = newCalculations
  calculations.value = newCalculations
  closeAllCalculationsPopup()
}

function loadAllInstruments() {
  if (!instrumentSummary.value.rows.length) return
  if (allCalculations.value.totalValue !== undefined) {
    selectedCalculations.value = allCalculations.value
    calculations.value = allCalculations.value
  } else {
    showSnackbar('No calculation data available. Please recalculate.', 'error')
  }
  currentlyViewingInstrument.value = null
  closeAllCalculationsPopup()
  saveSessionData()
}

function formatTableCell(value, column) {
  if (value === null || value === undefined || value === '') return '—'
  const isTimeField = column.toLowerCase().includes('day') || column.toLowerCase().includes('maturity') || column.toLowerCase().includes('duration') || column.toLowerCase().includes('term') || column.toLowerCase().includes('month') || column.toLowerCase().includes('year') || column.toLowerCase().includes('week') || column.toLowerCase().includes('time')
  if (isTimeField && typeof value === 'number') return formatNumber(value, true)
  if (isPercentageField(column)) return formatNumber(value) + '%'
  if (column.toLowerCase().includes('value') || column.toLowerCase().includes('amount') || column.toLowerCase().includes('price')) {
    return formatNumber(value)
  }
  if (column.toLowerCase().includes('date') && typeof value === 'string') return value
  return typeof value === 'number' ? formatNumber(value) : value
}

function openAllCalculationsPopup() { showAllCalculationsPopup.value = true }
function closeAllCalculationsPopup() { showAllCalculationsPopup.value = false }

function exportAllCalculations() {
  const allData = completedInstrumentSummary.value.rows || instrumentSummary.value.rows
  if (!allData.length) return
  const displayCols = getDisplayColumns()
  const data = allData.map(row => {
    const obj = {}
    displayCols.forEach(col => {
      let val = row[col] !== undefined ? row[col] : ''
      if (isPercentageField(col)) val = formatForExcel(val, 'percentage', col)
      else if (col.toLowerCase().includes('value') || col.toLowerCase().includes('price') || col.toLowerCase().includes('amount') || col.toLowerCase().includes('principal') || col.toLowerCase().includes('interest')) {
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

const previousSnapshot = ref(null)

function generateVersionDescription(newSnapshot, oldSnapshot) {
  const changes = []
  if (!oldSnapshot) return `Initial ${instrumentType.value} workflow setup`
  if (JSON.stringify(newSnapshot.rawData) !== JSON.stringify(oldSnapshot.rawData)) changes.push('uploaded new data')
  if (JSON.stringify(newSnapshot.cleanedData) !== JSON.stringify(oldSnapshot.cleanedData)) changes.push('cleaned data')
  if (JSON.stringify(newSnapshot.calculations) !== JSON.stringify(oldSnapshot.calculations)) changes.push('recalculated metrics')
  if (JSON.stringify(newSnapshot.columnMapping) !== JSON.stringify(oldSnapshot.columnMapping)) changes.push('updated column mapping')
  if (JSON.stringify(newSnapshot.manualInputs) !== JSON.stringify(oldSnapshot.manualInputs)) changes.push('updated manual inputs')
  if (JSON.stringify(newSnapshot.formulas) !== JSON.stringify(oldSnapshot.formulas)) changes.push('updated formulas')
  if (changes.length === 0) return `Saved ${instrumentType.value} workflow (no changes)`
  return `${instrumentType.value} — ${changes.join(', ')}`
}

async function saveToSession() {
  if (isSavingVersion) return
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
    const currentVersionsRes = await api.versionAPI.getVersions(sid)
    if (currentVersionsRes && currentVersionsRes.success) {
      const actualCount = currentVersionsRes.total || 0
      if (activeSession.value?.id === sid) activeSession.value.version_count = actualCount
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
      fredFilters: {
        country: effectiveCountry.value,
        currency: effectiveCurrency.value,
        maturity: effectiveMaturity.value,
        maturityMode: maturityMode.value === 'dateRange' ? 'date' : 'tenor',
        fromDate: yieldCurveStartDate.value,
        toDate: yieldCurveEndDate.value
      },
      manualInputs: manualInputs.value,
      formulas: formulas.value,
      uploadedFile: uploadedFile.value?.name || null,
      originalDatasetId: originalDatasetId.value,
      originalFileName: uploadedFile.value?.name || null,
      cleaningStats: cleaningStats.value,
      sessionSavedAt: new Date().toISOString(),
      instrumentType: instrumentType.value,
      sheetType: sheetType.value,
      currentSheetName: currentSheetName.value,
      extractedValues: extractedValues.value,
      selectedCurrency: selectedCurrency.value,
      customCurrency: customCurrency.value
    }
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
    markWorksheetAsSaved()
    await sessionManager.saveInstrumentWorkflow(sid, instrumentType.value, datasetSnapshot)
    const count = sessionManager.countSessionInstruments(sid)
    await sessionManager.updateSession(sid, { instrument_count: Math.min(count, 3) })
    if (activeSession.value?.id === sid) activeSession.value.instrument_count = Math.min(count, 3)
    const versionDescription = generateVersionDescription(datasetSnapshot, previousSnapshot.value)
    const versionResponse = await api.versionAPI.create(
      sid,
      instrumentType.value,
      versionDescription,
      datasetSnapshot,
      null, null, null, null, null
    )
    if (!versionResponse?.success) {
      showSnackbar('Failed to create version', 'error')
    } else {
      previousSnapshot.value = JSON.parse(JSON.stringify(datasetSnapshot))
      try {
        const versionsRes = await api.versionAPI.getVersions(sid)
        if (versionsRes && versionsRes.success) {
          const updatedVersionCount = versionsRes.total || 0
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
              if (versionsRes.data && versionsRes.data.length > 0) activeSession.value.versions = session.versions
            }
          }
        }
      } catch (fetchError) { /* non-fatal */ }
    }
  } catch (err) {
    showSnackbar('Failed to save to session: ' + err.message, 'error')
  } finally {
    isSavingVersion = false
    isSaving.value = false
    setTimeout(() => { skipAutoSave.value = false }, 3000)
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
    }
  } catch (err) { /* non-fatal */ }
}

function saveSessionData(explicitSave = false) {
  if (!activeSession.value) return Promise.resolve()
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
    fredFilters: {
      country: effectiveCountry.value,
      currency: effectiveCurrency.value,
      maturity: effectiveMaturity.value,
      maturityMode: maturityMode.value === 'dateRange' ? 'date' : 'tenor',
      fromDate: yieldCurveStartDate.value,
      toDate: yieldCurveEndDate.value
    },
    uploadedFile: uploadedFile.value?.name || null,
    originalDatasetId: originalDatasetId.value,
    originalFileName: uploadedFile.value?.name || null,
    cleaningStats: cleaningStats.value,
    sessionSavedAt: sessionSavedAt.value || new Date().toISOString(),
    manualInputs: manualInputs.value,
    formulas: formulas.value,
    isCalculating: isCalculating.value,
    autoDetectedFields: autoDetectedFields.value,
    autoDetectedFieldsWithMetadata: autoDetectedFieldsWithMetadata.value,
    autoDetectedAdditionalFields: autoDetectedAdditionalFields.value,
    detectedCurrencies: detectedCurrencies.value,
    excludedDetectedFields: Array.from(excludedDetectedFields.value),
    sheetType: sheetType.value,
    currentSheetName: currentSheetName.value,
    extractedValues: extractedValues.value,
    selectedCurrency: selectedCurrency.value,
    customCurrency: customCurrency.value,
    last_tab: activeTab.value
  }
  sessionManager.setActiveSession(activeSession.value)
  return sessionManager.saveInstrumentWorkflow(sid, instrumentType.value, datasetSnapshot)
    .then(() => {
      if (explicitSave) {
        const count = sessionManager.countSessionInstruments(sid)
        sessionManager.updateSession(sid, { instrument_count: Math.min(count, 3) })
      }
    })
    .catch(err => {
      console.error('Failed to save workflow:', err)
      showSnackbar('Warning: session could not be saved — ' + (err?.message || err), 'warning', 6000)
    })
}

let _lastLoadSavedSessionId = null
let _lastLoadSavedAt = 0
const LOAD_SAVED_THROTTLE_MS = 2000

// ─────────────────────────────────────────────────────────────
// FIX 6 — loadSavedData restores the FULL filter set including
// maturityMode, fromDate, toDate. Before, only country/currency/
// maturity survived a reload, so date-range selections silently
// reverted to tenor mode in the report.
// ─────────────────────────────────────────────────────────────
async function loadSavedData(force = false, prefetchedWorkflow = null) {
  if (!activeSession.value) return false
  const sid = activeSession.value.id
  if (!prefetchedWorkflow && !force &&
      sid === _lastLoadSavedSessionId &&
      Date.now() - _lastLoadSavedAt < LOAD_SAVED_THROTTLE_MS) {
    return true
  }
  let loaded = false
  try {
    const wf = prefetchedWorkflow || await sessionManager.getInstrumentWorkflow(sid, instrumentType.value)
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
      if (Array.isArray(wf.yieldCurveData) && wf.yieldCurveData.length) {
        yieldCurveData.value = wf.yieldCurveData.filter(p =>
          p && typeof p === 'object' &&
          p.rate != null && !isNaN(parseFloat(p.rate)) && parseFloat(p.rate) > 0
        )
      } else {
        yieldCurveData.value = []
      }
      manualInputs.value = wf.manualInputs || {}
      formulas.value = wf.formulas || {}
      isCalculating.value = wf.isCalculating || false
      if (wf.sheetType) sheetType.value = wf.sheetType
      if (wf.currentSheetName) currentSheetName.value = wf.currentSheetName
      if (wf.extractedValues && Object.keys(wf.extractedValues).length) extractedValues.value = wf.extractedValues
      if (wf.fredFilters) {
        const f = wf.fredFilters
        selectedCountryOption.value = f.country || ''
        selectedCurrencyOption.value = f.currency || ''
        selectedMaturityOption.value = f.maturity || config.value.defaultMaturity
        maturityMode.value = (f.maturityMode === 'date') ? 'dateRange' : 'maturity'
        yieldCurveStartDate.value = f.fromDate || ''
        yieldCurveEndDate.value = f.toDate || ''
        fredFilters.value.country = f.country || ''
        fredFilters.value.currency = f.currency || ''
        fredFilters.value.maturity = f.maturity || config.value.defaultMaturity
        fredFilters.value.maturityMode = f.maturityMode === 'date' ? 'date' : 'tenor'
        fredFilters.value.fromDate = f.fromDate || ''
        fredFilters.value.toDate = f.toDate || ''
      }
      if (wf.uploadedFile) uploadedFile.value = { name: wf.uploadedFile, size: 0 }
      if (wf.originalDatasetId) originalDatasetId.value = wf.originalDatasetId
      if (wf.cleaningStats) cleaningStats.value = wf.cleaningStats
      if (wf.sessionSavedAt) sessionSavedAt.value = wf.sessionSavedAt
      if (wf.autoDetectedFields) autoDetectedFields.value = wf.autoDetectedFields
      if (wf.autoDetectedFieldsWithMetadata) autoDetectedFieldsWithMetadata.value = wf.autoDetectedFieldsWithMetadata
      if (wf.autoDetectedAdditionalFields) autoDetectedAdditionalFields.value = wf.autoDetectedAdditionalFields
      if (wf.detectedCurrencies) detectedCurrencies.value = wf.detectedCurrencies
      if (wf.excludedDetectedFields && Array.isArray(wf.excludedDetectedFields)) excludedDetectedFields.value = new Set(wf.excludedDetectedFields)
      if (typeof wf.selectedCurrency === 'string') selectedCurrency.value = wf.selectedCurrency
      if (typeof wf.customCurrency === 'string') customCurrency.value = wf.customCurrency
      loaded = true
    }
  } catch (err) {
    console.warn('loadSavedData failed:', err)
  }
  if (loaded) {
    _lastLoadSavedSessionId = sid
    _lastLoadSavedAt = Date.now()
  }
  return loaded
}

// ─────────────────────────────────────────────────────────────
// FIX 7 — loadAllSelectedInstrumentCurves: NO US fallback when
// ANY saved curve exists. Missing instruments show honest "not
// saved" state instead of an invented US default curve.
// ─────────────────────────────────────────────────────────────
async function loadAllSelectedInstrumentCurves(workflowMap = null) {
  const session = activeSession.value
  if (!session?.id) return []
  const meta = [
    { key: 'money-market', label: 'Money Market', color: '#1E88E5', apiType: 'money-market' },
    { key: 'bonds', label: 'Bonds', color: '#4CAF50', apiType: 'bonds' },
    { key: 'tbills', label: 'T-Bills', color: '#FF9800', apiType: 'tbills' }
  ]
  const neededKeys = meta.filter(m => selectedInstruments.value[m.key]).map(m => m.key)
  const missingKeys = neededKeys.filter(k => !workflowMap?.[k])
  const localMap = { ...(workflowMap || {}) }
  if (missingKeys.length) {
    const fetched = await Promise.all(missingKeys.map(async k => {
      try { return [k, await sessionManager.getInstrumentWorkflow(session.id, k)] }
      catch (e) { console.warn(`[report] workflow load failed for ${k}:`, e); return [k, null] }
    }))
    for (const [k, wf] of fetched) if (wf) localMap[k] = wf
  }

  const stage = []
  for (const m of meta) {
    if (!selectedInstruments.value[m.key]) continue
    const wf = localMap[m.key] || null
    const isCurrent = m.key === instrumentType.value
    const sessionPoints = Array.isArray(wf?.yieldCurveData) ? wf.yieldCurveData : []
    const sessionFilters = (wf?.fredFilters && wf.fredFilters.country) ? wf.fredFilters : null
    const localPoints = isCurrent ? yieldCurveData.value : null
    const localFilters = isCurrent ? {
      country: effectiveCountry.value || 'US',
      currency: effectiveCurrency.value || 'USD',
      maturity: effectiveMaturity.value || config.value.defaultMaturity,
      maturityMode: maturityMode.value === 'dateRange' ? 'date' : 'tenor',
      fromDate: yieldCurveStartDate.value,
      toDate: yieldCurveEndDate.value
    } : null
    const savedPoints = sessionPoints.length ? sessionPoints : (localPoints || [])
    const savedFilters = sessionFilters || localFilters || {}
    const filters = {
      country: savedFilters.country || 'US',
      currency: savedFilters.currency || 'USD',
      maturity: savedFilters.maturity || config.value.defaultMaturity,
      maturityMode: savedFilters.maturityMode || 'tenor',
      fromDate: savedFilters.fromDate || null,
      toDate: savedFilters.toDate || null
    }
    let normalised = []
    for (const p of savedPoints) {
      if (!p || typeof p !== 'object') continue
      const rate = parseFloat(p.rate ?? p.y ?? p.value)
      if (isNaN(rate) || rate === 0) continue
      const rawX = p.x ?? p.maturity
      let isDate
      if (typeof p.isDate === 'boolean') {
        isDate = p.isDate
      } else {
        const matNum = parseFloat(rawX)
        const hasValidTenor = !isNaN(matNum) && matNum > 0 && matNum < 1000
        isDate = !hasValidTenor && (
          !!p.date ||
          (typeof rawX === 'number' && rawX > 9999999999) ||
          (typeof rawX === 'string' && /^\d{4}-\d{2}-\d{2}/.test(rawX))
        )
      }
      if (isDate) {
        const dateStr = p.date || (typeof rawX === 'string' ? rawX : new Date(rawX).toISOString().slice(0, 10))
        const ts = new Date(dateStr).getTime()
        if (isNaN(ts)) continue
        normalised.push({ x: ts, y: rate, maturityLabel: dateStr, date: dateStr, isDate: true })
      } else {
        const mat = parseFloat(rawX)
        if (isNaN(mat) || mat <= 0) continue
        normalised.push({
          x: mat,
          y: rate,
          maturityLabel: p.maturityLabel || String(mat),
          date: p.date || null,
          isDate: false
        })
      }
    }

    // Truncate the curve to match the Visualisations page selection
    if (filters.maturityMode !== 'date' && filters.maturity && filters.maturity !== '__custom__') {
      const filterYears = parseMaturityToYears(filters.maturity)
      if (filterYears > 0) {
        normalised = normalised.filter(p => !p.isDate && p.x <= filterYears)
      }
    }

    stage.push({ m, filters, normalised, fromSession: sessionPoints.length > 0, savedAt: wf?.yieldCurveSavedAt })
  }

  const anySavedCurve = stage.some(s => s.fromSession && s.normalised.length >= 2)
  const needsFallback = anySavedCurve
    ? []
    : stage.filter(s => s.normalised.length < 2)

  const fallbackResults = await Promise.all(needsFallback.map(async job => {
    const { m, filters } = job
    try {
      const payload = {
        instrument_type: m.apiType || m.key,
        country: filters.country,
        currency: filters.currency
      }
      if (filters.maturityMode === 'date' && filters.fromDate && filters.toDate) {
        payload.from_date = filters.fromDate
        payload.to_date = filters.toDate
      } else if (filters.maturity) {
        payload.maturity = filters.maturity
      }
      const res = await api.fredAPI.getYieldCurve(payload)
      return { key: m.key, fetched: extractFredPointsForReport(res), error: null }
    } catch (e) {
      return { key: m.key, fetched: [], error: e?.message || String(e) }
    }
  }))
  const fallbackByKey = Object.fromEntries(fallbackResults.map(r => [r.key, r]))

  const result = []
  for (const job of stage) {
    const { m, filters, normalised, fromSession, savedAt } = job
    let validPoints = normalised
    let dataSource = null
    let fetchError = null

    if (fromSession && normalised.length >= 2) {
      dataSource = 'session_visualization'
    } else if (validPoints.length < 2) {
      const fb = fallbackByKey[m.key]
      if (fb && fb.fetched.length >= 2) {
        validPoints = fb.fetched
        dataSource = 'fred_api_live'
      } else if (fb) {
        fetchError = fb.error ||
          `FRED returned ${fb.fetched.length} observation(s); a curve requires at least 2.`
      } else {
        fetchError = 'No yield curve has been selected for this instrument on the Visualisations page.'
      }
    }

    if (validPoints.length < 2) {
      result.push({
        key: m.key,
        label: m.label,
        color: m.color,
        points: [],
        filters,
        svg: '',
        dataSource: null,
        status: 'unavailable',
        message: fetchError ||
          `No yield curve is saved for ${m.label}. Visit Visualisations, select ${m.label} (or "All Instruments"), fetch the curve, then regenerate this report.`
      })
      continue
    }

    const isDateMode = validPoints.some(p => p.isDate)
    result.push({
      key: m.key,
      label: m.label,
      color: m.color,
      points: validPoints,
      filters,
      svg: buildInstrumentCurveSvg(validPoints, m.label, m.color, isDateMode, savedAt),
      dataSource,
      status: 'ok',
      isDateMode
    })
  }

  if (typeof window !== 'undefined' && window.__DURA_REPORT_DEBUG__) {
    console.groupCollapsed('[report] curves used by report')
    for (const c of result) {
      console.log(c.label, {
        status: c.status,
        source: c.dataSource,
        points: c.points.length,
        filters: c.filters,
        firstPoint: c.points[0],
        lastPoint: c.points[c.points.length - 1]
      })
    }
    console.groupEnd()
  }

  return result
}

function extractFredPointsForReport(res) {
  if (!res?.success || !res.data) return []
  const d = res.data
  const out = []
  if (Array.isArray(d.maturities) && Array.isArray(d.rates)) {
    d.maturities.forEach((m, i) => {
      const rate = parseFloat(d.rates[i])
      if (isNaN(rate) || rate === 0) return
      out.push({
        x: parseFloat(m),
        y: rate,
        maturityLabel: d.labels?.[i] || String(m),
        date: d.dates?.[i] || null,
        isDate: false
      })
    })
    return out
  }
  if (d.datasets?.[0]?.data?.length) {
    for (const pt of d.datasets[0].data) {
      const rate = parseFloat(pt.y ?? pt.rate)
      if (isNaN(rate) || rate === 0) continue
      const rawX = pt.x
      const isDate =
        (typeof rawX === 'number' && rawX > 9999999999) ||
        (typeof rawX === 'string' && /^\d{4}-\d{2}-\d{2}/.test(rawX)) ||
        !!pt.date
      if (isDate) {
        const dateStr = pt.date || (typeof rawX === 'string' ? rawX : new Date(rawX).toISOString().slice(0, 10))
        const ts = new Date(dateStr).getTime()
        if (isNaN(ts)) continue
        out.push({ x: ts, y: rate, maturityLabel: dateStr, date: dateStr, isDate: true })
      } else {
        const mat = parseFloat(rawX)
        if (isNaN(mat) || mat <= 0) continue
        out.push({ x: mat, y: rate, maturityLabel: pt.label || String(mat), date: pt.date || null, isDate: false })
      }
    }
  }
  return out
}

function buildInstrumentCurveSvg(validPoints, title, color, isDateMode = false, savedAt = null) {
  // Pixel-match the Visualisations page Chart.js config:
  //   borderColor:          '#0B2044'
  //   backgroundColor:      'rgba(11,32,68,0.1)'
  //   tension: 0.3
  //   fill: true
  //   white canvas background, x.min = 0, x.max = lastMaturity + 0.5 (tenor mode)
  // NOTE: dots are intentionally omitted here (report only). The
  // Visualisations page keeps its blue dots via Chart.js.
  const LINE_COLOR  = '#0B2044'
  const FILL_COLOR  = 'rgba(11,32,68,0.1)'
  const GRID_COLOR  = '#E5E7EB'
  const AXIS_COLOR  = '#9CA3AF'
  const LABEL_COLOR = '#6B7280'

  const width  = 800
  const height = 400
  const pad = { l: 60, r: 30, t: 34, b: 60 }
  const plotW = width - pad.l - pad.r
  const plotH = height - pad.t - pad.b

  const valid = (validPoints || [])
    .filter(p => p && !isNaN(parseFloat(p.x)) && !isNaN(parseFloat(p.y)))
    .map(p => ({
      x: parseFloat(p.x),
      y: parseFloat(p.y),
      label: p.maturityLabel || (isDateMode
        ? new Date(p.x).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
        : String(p.x))
    }))
    .sort((a, b) => a.x - b.x)

  // No injected origin point — start exactly at the first real observation,
  // same as the Visualisations page.
  if (valid.length < 2) {
    return `<div style="padding:24px;text-align:center;color:#999;font-size:13px;">No live data available for this curve.</div>`
  }

  // X-axis extents — same as the Visualisations page
  let axisMinX = Math.min(...valid.map(p => p.x))
  let axisMaxX = Math.max(...valid.map(p => p.x))
  if (!isDateMode) {
    axisMinX = 0
    axisMaxX = axisMaxX + 0.5
  } else {
    const span = (axisMaxX - axisMinX) || 1
    axisMinX -= span * 0.02
    axisMaxX += span * 0.02
  }

  // Y-axis range with ~15 % padding (matches Chart.js auto-padding)
  const dataMinY = Math.min(...valid.map(p => p.y))
  const dataMaxY = Math.max(...valid.map(p => p.y))
  const yPad     = (dataMaxY - dataMinY) * 0.15 || 0.5
  const axisMinY = Math.max(0, dataMinY - yPad)
  const axisMaxY = dataMaxY + yPad

  const rangeX = (axisMaxX - axisMinX) || 1
  const rangeY = (axisMaxY - axisMinY) || 1
  const sx = x => pad.l + ((x - axisMinX) / rangeX) * plotW
  const sy = y => pad.t + plotH - ((y - axisMinY) / rangeY) * plotH

  const points = valid.map(p => ({ x: sx(p.x), y: sy(p.y) }))

  // Smooth cardinal spline (tension = 0.3, same as Chart.js `tension`)
  const tension = 0.3
  let lineD = `M ${points[0].x.toFixed(2)} ${points[0].y.toFixed(2)}`
  for (let i = 0; i < points.length - 1; i++) {
    const p0 = points[i]
    const p1 = points[i + 1]
    const dx   = p1.x - p0.x
    const cp1x = p0.x + dx * tension
    const cp2x = p1.x - dx * tension
    lineD += ` C ${cp1x.toFixed(2)} ${p0.y.toFixed(2)}, ${cp2x.toFixed(2)} ${p1.y.toFixed(2)}, ${p1.x.toFixed(2)} ${p1.y.toFixed(2)}`
  }
  const areaD =
    lineD +
    ` L ${points[points.length - 1].x.toFixed(2)} ${(pad.t + plotH).toFixed(2)}` +
    ` L ${points[0].x.toFixed(2)} ${(pad.t + plotH).toFixed(2)} Z`

  // Y grid + tick labels
  const yTickCount = 5
  let yGridSvg = ''
  for (let i = 0; i <= yTickCount; i++) {
    const v   = axisMinY + (axisMaxY - axisMinY) * (i / yTickCount)
    const yPx = sy(v)
    yGridSvg += `<line x1="${pad.l}" y1="${yPx.toFixed(2)}" x2="${(pad.l + plotW).toFixed(2)}" y2="${yPx.toFixed(2)}" stroke="${GRID_COLOR}" stroke-width="1" stroke-dasharray="3 3"/>`
    yGridSvg += `<text x="${(pad.l - 8).toFixed(2)}" y="${(yPx + 4).toFixed(2)}" text-anchor="end" font-size="11" fill="${LABEL_COLOR}">${v.toFixed(2)}</text>`
  }

  // X labels — thinned to roughly match Chart.js autoSkip
  const labelEvery = Math.max(1, Math.ceil(valid.length / 10))
  const xLabelsSvg = valid.map((p, i) =>
    i % labelEvery === 0
      ? `<text x="${sx(p.x).toFixed(2)}" y="${(pad.t + plotH + 18).toFixed(2)}" text-anchor="middle" font-size="11" fill="${LABEL_COLOR}">${p.label}</text>`
      : ''
  ).join('')

  const xAxisTitle = isDateMode ? 'Date' : 'Years'

  return `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" role="img" aria-label="${title} yield curve" style="background:#ffffff;border-radius:8px;display:block;max-width:100%;height:auto;">
    <rect width="100%" height="100%" fill="#ffffff"/>
    ${yGridSvg}
    <path d="${areaD}" fill="${FILL_COLOR}"/>
    <path d="${lineD}" fill="none" stroke="${LINE_COLOR}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
    <line x1="${pad.l}" y1="${(pad.t + plotH).toFixed(2)}" x2="${(pad.l + plotW).toFixed(2)}" y2="${(pad.t + plotH).toFixed(2)}" stroke="${AXIS_COLOR}" stroke-width="1"/>
    <line x1="${pad.l}" y1="${pad.t.toFixed(2)}" x2="${pad.l}" y2="${(pad.t + plotH).toFixed(2)}" stroke="${AXIS_COLOR}" stroke-width="1"/>
    <text x="${(pad.l - 44).toFixed(2)}" y="${(pad.t + plotH / 2).toFixed(2)}" font-size="12" fill="${LABEL_COLOR}" transform="rotate(-90 ${(pad.l - 44).toFixed(2)} ${(pad.t + plotH / 2).toFixed(2)})" text-anchor="middle">Yield (%)</text>
    <text x="${(pad.l + plotW / 2).toFixed(2)}" y="${(height - 10).toFixed(2)}" text-anchor="middle" font-size="12" fill="${LABEL_COLOR}">${xAxisTitle}</text>
    ${xLabelsSvg}
    <text x="${pad.l}" y="${(pad.t - 12).toFixed(2)}" font-size="13" font-weight="600" fill="${LINE_COLOR}">${title} — Yield Curve (%)</text>
  </svg>`
}

// ─────────────────────────────────────────────────────────────
// FIX 8 — showFormula prefers backend `derivations`.
// ─────────────────────────────────────────────────────────────
function showFormula(metricKey) {
  const formulaMap = {
    'Total Portfolio Value': 'Σ (Total Value of each instrument)',
    'Average Rate': 'Σ (Rate × Principal) / Σ Principal',
    'Number of Instruments': 'Count of all instrument rows',
    'totalValue': 'Σ (Total Value of each instrument)',
    'avgRate': 'Σ (Rate × Principal) / Σ Principal',
    'weightedAvgRate': 'Σ (Rate × Weight) / Σ Weight',
    'totalInterest': 'Σ (Principal × Interest Rate × Days ÷ DayCountBasis)',
    'interestEarned': 'Σ (Principal × Interest Rate × Days ÷ DayCountBasis)',
    'annualYield': '(Interest ÷ Principal) × (365 ÷ Days) × 100',
    'effectiveAnnualRate': '((1 + (Rate ÷ 100) × (Days ÷ Basis))^(Basis ÷ Days) − 1) × 100',
    'effectiveYield': '((Face Value ÷ Purchase Price)^(365 ÷ Days) − 1) × 100',
    'bondEquivalentYield': '((Face Value − Purchase Price) ÷ Purchase Price) × (365 ÷ Days) × 100',
    'discountYield': '((Face Value − Purchase Price) ÷ Face Value) × (360 ÷ Days) × 100',
    'moneyMarketYield': '((Face Value − Purchase Price) ÷ Purchase Price) × (360 ÷ Days) × 100',
    'holdingPeriodYield': '((Face Value − Purchase Price) ÷ Purchase Price) × 100',
    'annualizedYield': '((Face Value − Purchase Price) ÷ Purchase Price) × (365 ÷ Days) × 100',
    'effectiveAnnualYield': '((Face Value ÷ Purchase Price)^(365 ÷ Days) − 1) × 100',
    'avgDaysToMaturity': 'Σ Days to Maturity / Number of Instruments',
    'totalPrincipal': 'Σ Principal',
    'totalFaceValue': 'Σ Face Value',
    'maturityValue': 'Principal × (1 + (Rate ÷ 100) × (Days ÷ Basis))',
    'presentValue': 'Future Value ÷ (1 + Rate × Days ÷ Basis)',
    'fairValue': 'Present Value − Purchase Price',
    'yieldCurveRate': 'FRED benchmark rate matched to maturity',
    'couponRate': 'Annual coupon rate (%)',
    'avgCouponRate': 'Σ Coupon Rate ÷ Number of Instruments',
    'weightedAvgCoupon': 'Σ (Coupon Rate × Face Value) ÷ Σ Face Value',
    'totalAnnualIncome': 'Σ (Coupon Rate × Face Value ÷ 100)',
    'annualCoupon': 'Face Value × Coupon Rate ÷ 100',
    'couponPerPeriod': 'Annual Coupon ÷ Coupon Frequency',
    'yieldToMaturity': 'IRR of bond cash flows',
    'avgYTM': 'Σ Yield to Maturity ÷ Number of Instruments',
    'currentYield': '(Annual Coupon ÷ Current Price) × 100',
    'duration': 'Macaulay Duration = Σ (t × PV(C_t)) ÷ Price',
    'modifiedDuration': 'Macaulay Duration ÷ (1 + (YTM ÷ 100) ÷ Frequency)',
    'accruedInterest': 'Coupon per Period × (Days Accrued ÷ Days in Period)',
    'yearsToMaturity': 'Days to Maturity ÷ 365',
    'termDays': 'Maturity Date − Valuation Date (in days)',
    'daysToMaturity': 'Maturity Date − Valuation Date (in days)',
    'pricePer100': '(Current Price ÷ Face Value) × 100',
    'currentPrice': 'Current market price',
    'totalDiscount': 'Σ (Face Value − Purchase Price)',
    'avgDiscountRate': 'Σ Discount Rate ÷ Number of Instruments',
    'weightedAvgDiscount': 'Σ (Discount Rate × Face Value) ÷ Σ Face Value',
    'totalPurchasePrice': 'Σ Purchase Price',
    'avgInvestment': 'Total Purchase Price ÷ Number of Instruments',
    'discountRate': 'Annual discount rate (%)',
    'totalMarketValue': 'Σ Market Value',
    'frequency': 'Coupon payments per year'
  }
  formulaText.value = formulaMap[metricKey] || 'No formula available for this metric.'

  const agg = allCalculations.value || {}
  const calc = calculations.value || {}
  const rows = instrumentSummary.value.rows || []
  const firstRow = (cleanedData.value && cleanedData.value[0]) || (rawData.value && rawData.value[0]) || {}

  const toSnake = (s) => String(s).replace(/([a-z])([A-Z])/g, '$1_$2').replace(/[\s\-]+/g, '_').toLowerCase()
  const fmtNum = (v, d = 2) => {
    if (v === null || v === undefined || v === '') return 'N/A'
    const n = typeof v === 'number' ? v : parseFloat(v)
    if (isNaN(n)) return String(v)
    return Number.isInteger(n) ? n.toLocaleString() : n.toLocaleString(undefined, { minimumFractionDigits: d, maximumFractionDigits: d })
  }
  const fmtPct = (v, d = 2) => {
    if (v === null || v === undefined || v === '') return 'N/A'
    const n = typeof v === 'number' ? v : parseFloat(v)
    if (isNaN(n)) return String(v)
    return n.toFixed(d) + '%'
  }
  const _variants = (key) => {
    const set = new Set([key])
    try { set.add(toSnake(key)) } catch (e) { /* ignore */ }
    try { set.add(formatColumnHeader(key)) } catch (e) { /* ignore */ }
    set.add(String(key).replace(/_/g, ' '))
    return [...set]
  }
  const _pickFrom = (source, variants) => {
    if (!source || typeof source !== 'object') return null
    for (const v of variants) {
      const val = source[v]
      if (val !== undefined && val !== null && val !== '') return val
    }
    return null
  }
  const getVal = (key) => {
    const v = _variants(key)
    return (
      _pickFrom(selectedCalculations.value, v) ??
      _pickFrom(allCalculations.value, v) ??
      _pickFrom(calculations.value, v) ??
      _pickFrom(instrumentSummary.value?.rows?.[0], v)
    )
  }
  const getRowVal = (key) => {
    const v = _variants(key)
    return _pickFrom(firstRow, v) ?? _pickFrom(instrumentSummary.value?.rows?.[0], v)
  }

  const derivations =
    (calculations.value && calculations.value.derivations) ||
    (selectedCalculations.value && selectedCalculations.value.derivations) ||
    (allCalculations.value && allCalculations.value.derivations) ||
    (calc && calc.derivations) ||
    null

  if (derivations && typeof derivations === 'object') {
    const dk = derivations[metricKey] ||
               derivations[toSnake(metricKey)] ||
               derivations[String(metricKey).replace(/_/g, ' ')] ||
               derivations[formatColumnHeader(metricKey)]
    if (dk && typeof dk === 'object') {
      const details = []
      const ctx = {}
      const name = firstRow['Instrument Name'] || firstRow.instrument_name || null
      if (name) ctx['Instrument Name'] = name
      const instType = firstRow['Instrument Type'] || firstRow.instrument_type || instrumentType.value
      if (instType) ctx['Instrument Type'] = instType
      for (const [label, key] of [
        ['Valuation Date', 'valuation_date'],
        ['Maturity Date', 'maturity_date'],
        ['Issue Date', 'issue_date'],
        ['Settlement Date', 'settlement_date'],
        ['Last Coupon Date', 'last_coupon_date']
      ]) {
        const v = firstRow[label] ?? firstRow[key] ?? firstRow[toSnake(label)] ?? firstRow[formatColumnHeader(key)]
        if (v) ctx[label] = v
      }
      for (const [k, v] of Object.entries(ctx)) details.push({ label: k, value: v, formula: 'Input' })

      if (dk.from || dk.to) details.push({ label: 'Period', value: `${dk.from || '?'} → ${dk.to || '?'}`, formula: 'Derivation window' })
      if (dk.formula) details.push({ label: 'Formula', value: dk.formula, formula: 'Backend' })
      if (dk.inputs && typeof dk.inputs === 'object') {
        for (const [inKey, inVal] of Object.entries(dk.inputs)) {
          details.push({
            label: `Input: ${inKey}`,
            value: typeof inVal === 'number' ? inVal.toLocaleString(undefined, { maximumFractionDigits: 6 }) : String(inVal),
            formula: 'Backend input'
          })
        }
      }
      const resultLabel = `✓ ${formatColumnHeader(metricKey)}`
      const resultValue = (dk.result !== undefined && dk.result !== null)
        ? (dk.unit === 'percent' ? fmtPct(dk.result, 4)
           : dk.unit === 'days' ? `${fmtNum(dk.result, 0)} days`
           : dk.unit === 'years' ? `${fmtNum(dk.result, 4)} years`
           : dk.unit === 'currency' ? fmtNum(dk.result, 2)
           : String(dk.result))
        : '—'
      details.push({ label: resultLabel, value: resultValue, formula: dk.formula || 'Backend result' })
      if (dk.unit) details.push({ label: 'Unit', value: dk.unit, formula: 'Backend' })
      formulaCalculationDetails.value = details
      showCalculationDetails.value = true
      showIndividualBreakdown.value = false
      formulaDialog.value = true
      return
    }
  }

  const details = []
  const pushInput = (label, value) => details.push({ label, value, formula: 'Input' })
  const pushStep = (label, value, formula) => details.push({ label, value, formula })
  const pushAnswer = (label, value, formula) => details.push({ label: '✓ ' + label, value, formula })

  const name = firstRow['Instrument Name'] || firstRow.instrument_name || null
  if (name) pushInput('Instrument Name', name)
  const instTypeVal = firstRow['Instrument Type'] || firstRow.instrument_type || instrumentType.value
  if (instTypeVal) pushInput('Instrument Type', instTypeVal)
  for (const [label, key] of [
    ['Valuation Date', 'valuation_date'],
    ['Maturity Date', 'maturity_date'],
    ['Issue Date', 'issue_date'],
    ['Settlement Date', 'settlement_date'],
    ['Last Coupon Date', 'last_coupon_date']
  ]) {
    const v = firstRow[label] ?? firstRow[key] ?? firstRow[toSnake(label)] ?? firstRow[formatColumnHeader(key)]
    if (v) pushInput(label, v)
  }

  const faceValue = getRowVal('Face Value') || getRowVal('Principal') || getVal('faceValue') || getVal('principal')
  const principal = getRowVal('Principal') || getVal('principal') || faceValue
  const purchasePrice = getRowVal('Purchase Price') || getVal('purchasePrice')
  const currentPrice = getRowVal('Current Price') || getRowVal('Price') || getVal('currentPrice')
  const couponRate = getRowVal('Coupon Rate') || getVal('couponRate')
  const interestRate = getRowVal('Interest Rate') || getVal('interestRate')
  const discountRate = getRowVal('Discount Rate') || getVal('discountRate')
  const ytm = getRowVal('Yield to Maturity') || getVal('yieldToMaturity')
  const frequency = getVal('frequency') || getRowVal('Coupon Frequency') || getRowVal('Frequency') || 2
  const days = getVal('daysToMaturity') || getVal('termDays') || getRowVal('Days to Maturity') || getRowVal('Term')
  const dayBasis = String(getRowVal('Day Count Convention') || 'ACT/360').includes('360') ? 360 : 365
  const maturityDate = getRowVal('Maturity Date')
  const issueDate = getRowVal('Issue Date')
  const valuationDate = getRowVal('Valuation Date') || getRowVal('Settlement Date')

  const daysBetween = (a, b) => {
    if (!a || !b) return null
    const d1 = new Date(a), d2 = new Date(b)
    if (isNaN(d1) || isNaN(d2)) return null
    return Math.ceil((d2 - d1) / 86400000)
  }
  const computedDays = days || daysBetween(valuationDate || issueDate, maturityDate)

  let handled = true
  switch (metricKey) {
    case 'interestEarned':
    case 'totalInterest': {
      const p = parseFloat(principal) || 0
      const r = parseFloat(interestRate || couponRate || discountRate) || 0
      const d = parseFloat(computedDays) || 0
      const interest = p * (r / 100) * (d / dayBasis)
      pushInput('Principal', fmtNum(p))
      pushInput('Rate', fmtPct(r))
      pushInput('Days to Maturity', fmtNum(d, 0))
      pushInput('Day Count Basis', String(dayBasis))
      pushStep('Formula', `${fmtNum(p)} × (${fmtNum(r)} ÷ 100) × (${fmtNum(d, 0)} ÷ ${dayBasis}) = ${fmtNum(interest)}`, 'Principal × Rate ÷ 100 × Days ÷ Basis')
      pushAnswer('Interest Earned', fmtNum(interest), 'Simple interest')
      break
    }
    case 'Total Portfolio Value':
    case 'totalValue':
    case 'totalPrincipal':
    case 'totalFaceValue':
    case 'totalDiscount':
    case 'totalPurchasePrice':
    case 'totalAnnualIncome':
    case 'totalMarketValue': {
      const columnKey =
        metricKey === 'totalPrincipal' ? 'Principal' :
        metricKey === 'totalFaceValue' ? 'Face Value' :
        metricKey === 'totalDiscount' ? 'Discount' :
        metricKey === 'totalPurchasePrice' ? 'Purchase Price' :
        metricKey === 'totalAnnualIncome' ? 'Annual Coupon' :
        metricKey === 'totalMarketValue' ? 'Market Value' :
        'Total Value'
      if (rows.length > 0) {
        let sum = 0
        rows.forEach((row, idx) => {
          const v = parseFloat(row[columnKey] || row[toSnake(columnKey)] || 0) || 0
          pushInput(row['Instrument Name'] || `Row ${idx + 1}`, fmtNum(v))
          sum += v
        })
        pushStep('Sum', `Σ (${columnKey}) = ${fmtNum(sum)}`, `Add up ${columnKey} across all rows`)
        pushAnswer(metricKey === 'Total Portfolio Value' || metricKey === 'totalValue' ? 'Total Portfolio Value' : columnKey, fmtNum(sum), 'Sum of all rows')
      } else {
        const v = parseFloat(getVal(metricKey)) || 0
        pushAnswer('Total', fmtNum(v), 'From calculation engine')
      }
      break
    }
    case 'Average Rate':
    case 'avgRate':
    case 'avgCouponRate':
    case 'avgDiscountRate': {
      const key = metricKey === 'avgCouponRate' ? 'Coupon Rate' : metricKey === 'avgDiscountRate' ? 'Discount Rate' : 'Rate'
      if (rows.length > 0) {
        let sum = 0, count = 0
        rows.forEach((row, idx) => {
          const r = parseFloat(row[key] || row[toSnake(key)] || 0) || 0
          pushInput(row['Instrument Name'] || `Row ${idx + 1}`, fmtPct(r))
          sum += r
          count++
        })
        pushStep('Sum', `Σ ${key} = ${fmtPct(sum)}`, `Add up ${key}`)
        pushStep('Average', `${fmtPct(sum)} ÷ ${count} = ${fmtNum(sum / count)}%`, 'Sum ÷ Count')
        pushAnswer(`Average ${key}`, fmtPct(sum / count), 'Simple average')
      } else {
        const v = parseFloat(getVal(metricKey)) || 0
        pushAnswer(`Average ${key}`, fmtPct(v), 'From calculation engine')
      }
      break
    }
    case 'Number of Instruments':
    case 'instrumentCount': {
      const count = rows.length || parseInt(agg.instrumentCount) || 0
      if (rows.length > 0) {
        rows.forEach((row, idx) => pushInput(row['Instrument Name'] || `Row ${idx + 1}`, 'counted'))
      }
      pushAnswer('Number of Instruments', String(count), 'Count of all rows')
      break
    }
    default:
      handled = false
  }

  if (!handled) {
    const value = getVal(metricKey)
    const label = (config.value.calculationFields.find(f => f.key === metricKey) || {}).label || metricKey
    
    // Check if there's a specific error or missing field diagnostic from the backend
    const backendError = allCalculations.value?.error || allCalculations.value?.message
    const backendMissing = allCalculations.value?.missing_fields || []
    const backendInvalid = allCalculations.value?.invalid_fields || []
    
    if (value !== null && value !== undefined) {
      const numeric = parseFloat(value)
      pushInput('Reported value', !isNaN(numeric) ? fmtNum(numeric) : String(value))
      pushInput('Source', 'Calculation engine (aggregate)')
      pushStep('Note', `No dedicated step-by-step breakdown is implemented for "${label}" — the raw aggregate value returned by the backend is shown above.`, 'Generic fallback')
    } else if (backendError || backendMissing.length > 0 || backendInvalid.length > 0) {
      pushInput('Metric key', metricKey)
      if (backendError) details.push({ label: '⚠ Backend Error', value: backendError, formula: 'Error state' })
      if (backendMissing.length) details.push({ label: '⚠ Missing Inputs', value: backendMissing.join(', '), formula: 'Validation' })
      if (backendInvalid.length) details.push({ label: '⚠ Invalid Inputs', value: backendInvalid.map(f => typeof f === 'object' ? f.field : f).join(', '), formula: 'Validation' })
    } else {
      // Determine why it's missing based on the actual cleaned data
      const availableInputs = Object.keys(firstRow).filter(k => firstRow[k] !== null && firstRow[k] !== undefined && firstRow[k] !== '')
      
      details.push({
        label: '⚠ Not Calculated',
        value: `The backend did not return a value for "${label}". The required inputs for this formula were either not present in the cleaned data, or the calculation resulted in an undefined or infinite value.`,
        formula: 'Diagnostic'
      })
      
      if (availableInputs.length > 0) {
        details.push({
          label: 'Inputs available during calculation',
          value: availableInputs.join(', '),
          formula: 'Diagnostic'
        })
      }
    }
  }

  formulaCalculationDetails.value = details
  showCalculationDetails.value = true
  showIndividualBreakdown.value = false
  formulaDialog.value = true
}

function selectAllInstruments() { selectedInstruments.value = { 'money-market': true, bonds: true, tbills: true } }
function deselectAllInstruments() { selectedInstruments.value = { 'money-market': false, bonds: false, tbills: false } }

function getInstrumentData(instrumentId) {
  if (!activeSession.value) return null
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
    fredFilters: {
      country: effectiveCountry.value,
      currency: effectiveCurrency.value,
      maturity: effectiveMaturity.value,
      maturityMode: maturityMode.value === 'dateRange' ? 'date' : 'tenor',
      fromDate: yieldCurveStartDate.value,
      toDate: yieldCurveEndDate.value
    },
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
        try { resolve(canvas.toDataURL('image/png', 1.0)); return } catch (e) { /* fallthrough */ }
      }
      const canvasEl = document.querySelector('.chart-container--fred canvas')
      if (canvasEl && canvasEl.toDataURL) {
        try { resolve(canvasEl.toDataURL('image/png', 1.0)); return } catch (e) { /* fallthrough */ }
      }
      const anyCanvas = document.querySelector('canvas')
      if (anyCanvas && anyCanvas.toDataURL) {
        try { resolve(anyCanvas.toDataURL('image/png', 1.0)); return } catch (e) { /* fallthrough */ }
      }
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

async function loadAllInstrumentWorkflowsForReport(workflowMap = null) {
  if (!activeSession.value?.id) return
  const sid = activeSession.value.id
  const currentType = instrumentType.value
  const otherTypes = ['money-market', 'bonds', 'tbills'].filter(t => t !== currentType)
  const allRows = [...(instrumentSummary.value.rows || [])]
  for (const r of allRows) {
    if (!r['Instrument Type']) r['Instrument Type'] = currentType
  }
  const localMap = { ...(workflowMap || {}) }
  const missing = otherTypes.filter(t => !localMap[t])
  if (missing.length) {
    const fetched = await Promise.all(missing.map(async t => {
      try { return [t, await sessionManager.getInstrumentWorkflow(sid, t)] }
      catch (e) { console.warn('Report preview: failed to load workflow for', t, e); return [t, null] }
    }))
    for (const [t, wf] of fetched) if (wf) localMap[t] = wf
  }
  for (const t of otherTypes) {
    const rows = localMap[t]?.instrumentSummary?.rows || []
    for (const r of rows) {
      allRows.push({ ...r, 'Instrument Type': r['Instrument Type'] || t })
    }
  }
  const seen = new Set()
  const merged = allRows.filter(r => {
    const key = `${r['Instrument Name'] || ''}|${r['Instrument Type'] || ''}|${r['Worksheet'] || ''}`
    if (seen.has(key)) return false
    seen.add(key)
    return true
  })
  instrumentSummary.value = {
    columns: dedupeColumns(instrumentSummary.value.columns || []),
    rows: merged
  }
}

// ─────────────────────────────────────────────────────────────
// FIX 9 — prefetchPreviewWorkflows checks singular key first.
// ─────────────────────────────────────────────────────────────
async function prefetchPreviewWorkflows(sid) {
  const map = {}
  try {
    const session = await sessionManager.getSession(sid, true)
    const candidates = [
      session?.instrumentWorkflow,
      session?.instrumentWorkflows,
      session?.payload?.instrumentWorkflow,
      session?.payload?.instrumentWorkflows,
      session?.workflows,
      session?.payload?.workflows
    ]
    for (const cand of candidates) {
      if (cand && typeof cand === 'object' &&
          (cand['money-market'] || cand['bonds'] || cand['tbills'])) {
        for (const k of ['money-market', 'bonds', 'tbills']) {
          if (cand[k]) map[k] = cand[k]
        }
        if (Object.keys(map).length === 3) return map
        break
      }
    }
  } catch (e) {
    console.warn('[preview] unified session fetch failed, will fall back to per-workflow fetch:', e)
  }
  const missing = ['money-market', 'bonds', 'tbills'].filter(k => !map[k])
  if (missing.length) {
    const fetched = await Promise.all(missing.map(async k => {
      try { return [k, await sessionManager.getInstrumentWorkflow(sid, k)] }
      catch { return [k, null] }
    }))
    for (const [k, wf] of fetched) if (wf) map[k] = wf
  }
  return map
}

function resolveAggValue(agg, key) {
  if (!agg || typeof agg !== 'object') return null
  if (agg[key] !== undefined && agg[key] !== null && agg[key] !== '') return agg[key]
  const snake = toSnakeCase(key)
  if (agg[snake] !== undefined && agg[snake] !== null && agg[snake] !== '') return agg[snake]
  if (agg.agg && typeof agg.agg === 'object') {
    if (agg.agg[key] !== undefined && agg.agg[key] !== null && agg.agg[key] !== '') return agg.agg[key]
    if (agg.agg[snake] !== undefined && agg.agg[snake] !== null && agg.agg[snake] !== '') return agg.agg[snake]
  }
  return null
}

function formatCalcForType(typeKey, key, value) {
  if (value === null || value === undefined || value === '') return '—'
  const typeConfig = instrumentConfigs.value[typeKey] || {}
  const field = (typeConfig.calculationFields || []).find(f => f.key === key)
  if (typeof value === 'number' && !isNaN(value)) {
    const isTimeField = /day|maturity|duration|term|month|year|week|time/.test(key.toLowerCase())
    if (isTimeField) {
      const rounded = Math.round(value)
      if (field?.prefix) return field.prefix + rounded.toLocaleString()
      if (field?.suffix) return rounded.toLocaleString() + field.suffix
      return rounded.toLocaleString()
    }
    const rounded = Math.round(value * 100) / 100
    if (field?.prefix) return field.prefix + rounded.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
    if (field?.suffix) return rounded.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + field.suffix
    return rounded.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  }
  if (field?.prefix) return field.prefix + value
  if (field?.suffix) return value + field.suffix
  return value
}

async function generateReportHtml() {
  const sid = activeSession.value?.id
  const workflows = sid ? await prefetchPreviewWorkflows(sid) : {}
  await loadSavedData(true, workflows[instrumentType.value] || null)
  if (typeof loadAllInstrumentWorkflowsForReport === 'function') {
    await loadAllInstrumentWorkflowsForReport(workflows)
  }
  const report = reportPreviewData.value
  if (report.instruments.length === 0) return null
  let instrumentCurves = []
  try {
    instrumentCurves = await loadAllSelectedInstrumentCurves(workflows)
  } catch (e) {
    console.error('[report] loadAllSelectedInstrumentCurves failed:', e)
    instrumentCurves = []
  }
  const valuationDate = activeValuationDate.value || ''

  // Build per-instrument rows that mirror the Calculations-page boxes exactly.
  const resultsByInstrument = report.instruments.map(inst => {
    const wf = workflows[inst.id] || null
    const allCalcs = inst.id === instrumentType.value
      ? (allCalculations.value || wf?.allCalculations || wf?.calculations || {})
      : (wf?.allCalculations || wf?.calculations || {})
    const typeConfig = instrumentConfigs.value[inst.id] || {}
    const fields = typeConfig.calculationFields || []
    const calcRows = []
    for (const f of fields) {
      const val = resolveAggValue(allCalcs, f.key)
      if (val === null || val === undefined || val === '') continue
      calcRows.push({ label: f.label, value: formatCalcForType(inst.id, f.key, val) })
    }
    return { ...inst, calcRows, _agg: allCalcs }
  })

  const totalPortfolioValue = resultsByInstrument.reduce((sum, inst) => {
    const tv = resolveAggValue(inst._agg, 'totalValue')
    const tvVal = typeof tv === 'number' ? tv : (parseFloat(tv) || 0)
    return sum + tvVal
  }, 0)
  const totalInstrumentCount = resultsByInstrument.reduce((sum, inst) => {
    const cnt = resolveAggValue(inst._agg, 'instrumentCount')
    const cntVal = typeof cnt === 'number' ? cnt : (parseFloat(cnt) || 0)
    return sum + cntVal
  }, 0)
  const methodologyHtml = buildMethodologySection(report.instruments.map(i => i.name))
  const okCurves = instrumentCurves.filter(c => c.status === 'ok' && c.points.length > 0)
  const curveSignature = (curve) => curve.points
    .map(p => `${Number(p.x).toFixed(4)}:${Number(p.y).toFixed(4)}`)
    .sort()
    .join('|')
  const sigGroups = new Map()
  for (const c of okCurves) {
    const sig = curveSignature(c)
    if (!sigGroups.has(sig)) sigGroups.set(sig, { curves: [], label: '' })
    sigGroups.get(sig).curves.push(c)
  }
  for (const group of sigGroups.values()) {
    group.label = group.curves.map(c => c.label).join(' · ')
    group.dataSource = group.curves[0].dataSource
    group.filters = group.curves[0].filters
    group.svg = group.curves[0].svg
  }
  let chartHtml
  if (instrumentCurves.length > 0) {
    const unavailableCount = instrumentCurves.length - okCurves.length
    let intro
    if (okCurves.length === 0) {
      intro = 'No live yield-curve data is available for the selected instruments. Open the Visualizations page to fetch a FRED benchmark, save it to the session, then regenerate this report.'
    } else if (sigGroups.size === 1 && unavailableCount === 0) {
      const shared = sigGroups.values().next().value
      intro = shared.curves.length > 1
        ? `The following benchmark curve was fetched from FRED and used for all selected instruments (${shared.label}):`
        : 'The following yield curve was fetched from FRED for valuation:'
    } else {
      intro = `Live FRED yield curves for ${okCurves.length} of ${instrumentCurves.length} selected instrument types:`
    }
    const okBlocks = Array.from(sigGroups.values()).map(g => {
      const srcLabel = g.dataSource === 'fred_api_live'
        ? 'Live FRED'
        : (g.dataSource === 'session_visualization' ? 'Saved from Visualizations' : 'FRED')
      const country = g.filters?.country || '—'
      const currency = g.filters?.currency || '—'
      const maturity = g.filters?.maturity || '—'
      return `<div class="chart-container" style="margin-bottom:28px;">
        <h3 style="color:#0B2044;font-size:16px;margin-bottom:6px;">${g.label}</h3>
        <p style="font-size:12px;color:#666;margin-bottom:10px;">${srcLabel} — ${country} / ${currency} / ${maturity}</p>
        ${g.svg}
      </div>`
    }).join('')
    const unavailableBlocks = instrumentCurves
      .filter(c => c.status !== 'ok')
      .map(c => `<div class="chart-container" style="margin-bottom:28px;padding:16px;background:#fff8f0;border-left:4px solid #FF9800;border-radius:8px;">
        <h3 style="color:#0B2044;font-size:16px;margin-bottom:6px;">${c.label}</h3>
        <p style="font-size:13px;color:#666;">${c.message}</p>
      </div>`).join('')
    chartHtml = `<p>${intro}</p>${okBlocks}${unavailableBlocks}`
  } else {
    chartHtml = '<p>No instruments selected for yield curve display.</p>'
  }
  let appendixHtml
  if (okCurves.length > 0) {
    appendixHtml = okCurves.map(c => {
      const rows = c.points.map(p => `
        <tr>
          <td>${p.maturityLabel || p.date || ''}</td>
          <td>${c.isDateMode ? '' : parseFloat(p.x).toFixed(4)}</td>
          <td>${parseFloat(p.y).toFixed(4)}%</td>
        </tr>
      `).join('')
      return `<h3 style="font-size:15px;color:#0B2044;margin-top:20px;">${c.label} — FRED Yield Data</h3>
        <table class="appendix-table">
          <thead><tr><th>Maturity / Date</th><th>Term (Yr)</th><th>Rate (%)</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>`
    }).join('')
  } else {
    appendixHtml = '<p>No yield curve data available for the selected instruments.</p>'
  }
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
    .chart-container svg { max-width: 100%; height: auto; border-radius: 8px; border: 1px solid #e0e0e0; }
    @page { margin: 15mm 12mm; }
    @media print { .page { padding: 30px 40px; width: 210mm; } .cover-page { padding: 40px 50px; width: 210mm; } }
  </style>
</head>
<body>

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
  <div class="toc-item"><span>Yield Curves</span><span>6</span></div>
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
  ${resultsByInstrument.map(inst => `
    <h3 style="color:#0B2044;font-size:16px;margin:20px 0 10px 0;padding-bottom:6px;border-bottom:1px solid #e0e0e0;">${inst.name}</h3>
    ${inst.calcRows.length
      ? `<table>
          <thead><tr><th style="width:65%;">Metric</th><th>Value</th></tr></thead>
          <tbody>
            ${inst.calcRows.map(r => `<tr><td>${r.label}</td><td>${r.value}</td></tr>`).join('')}
          </tbody>
        </table>`
      : '<p style="color:#999;font-size:13px;margin:8px 0;">No calculated values available for this instrument.</p>'}
  `).join('')}
  <h3 style="color:#0B2044;font-size:16px;margin:30px 0 10px 0;padding-bottom:6px;border-bottom:1px solid #e0e0e0;">Portfolio Total</h3>
  <table>
    <thead><tr><th>Instrument</th><th>Total Value</th><th>Count</th></tr></thead>
    <tbody>
      ${resultsByInstrument.map(inst => {
        const tv = resolveAggValue(inst._agg, 'totalValue')
        const tvVal = typeof tv === 'number' ? tv : (parseFloat(tv) || 0)
        const cnt = resolveAggValue(inst._agg, 'instrumentCount')
        const cntVal = typeof cnt === 'number' ? cnt : (parseFloat(cnt) || 0)
        return `<tr>
          <td><strong>${inst.name}</strong></td>
          <td>${tvVal.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
          <td>${cntVal}</td>
        </tr>`
      }).join('')}
      <tr style="font-weight:700;background:#f0f2f5;">
        <td><strong>Total Portfolio</strong></td>
        <td><strong>${totalPortfolioValue.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</strong></td>
        <td><strong>${totalInstrumentCount}</strong></td>
      </tr>
    </tbody>
  </table>
</div>

<div class="page">
  <h1 class="section-title">Yield Curve</h1>
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
  <br>
  ${appendixHtml}
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

let _previewInFlight = null
let _previewHtmlCachedAt = 0
const PREVIEW_HTML_CACHE_MS = 5000

// ─────────────────────────────────────────────────────────────
// FIX 10 — previewReport invalidates the cache on every explicit request.
// ─────────────────────────────────────────────────────────────
async function previewReport() {
  // Force a fresh read of the session BEFORE generating the report
  await loadSavedData(true)
  reportPreviewHtml.value = ''
  _previewHtmlCachedAt = 0

  if (_previewInFlight) {
    try {
      const html = await _previewInFlight
      if (html) {
        reportPreviewHtml.value = html
        reportPreviewDialog.value = true
      }
    } catch (e) { console.error('previewReport (reused) failed:', e) }
    return
  }
  try {
    _previewInFlight = generateReportHtml()
    const html = await _previewInFlight
    if (html) {
      reportPreviewHtml.value = html
      _previewHtmlCachedAt = Date.now()
      reportPreviewDialog.value = true
    } else {
      showSnackbar('Could not generate report — select at least one instrument with completed calculations.', 'warning', 6000)
    }
  } catch (e) {
    console.error('previewReport failed:', e)
    showSnackbar('Failed to build report preview: ' + (e?.message || e), 'error', 6000)
  } finally {
    _previewInFlight = null
  }
}

// ─────────────────────────────────────────────────────────────
// FIX 11 — diagnostic helper. Call from browser console:
//   window.__DURA_REPORT_DEBUG__ = true
//   await window.__diagnoseReportCurves()
// ─────────────────────────────────────────────────────────────
if (typeof window !== 'undefined') {
  window.__diagnoseReportCurves = async () => {
    const sid = activeSession.value?.id
    if (!sid) { console.warn('No active session'); return }
    console.group('[diagnose] Session curves vs Report curves')
    for (const key of ['money-market', 'bonds', 'tbills']) {
      const wf = await sessionManager.getInstrumentWorkflow(sid, key)
      console.log(key, {
        savedPoints: wf?.yieldCurveData?.length || 0,
        filters: wf?.fredFilters,
        firstPoint: wf?.yieldCurveData?.[0],
        lastPoint: wf?.yieldCurveData?.slice(-1)[0],
        savedAt: wf?.yieldCurveSavedAt
      })
    }
    const workflows = await prefetchPreviewWorkflows(sid)
    const curves = await loadAllSelectedInstrumentCurves(workflows)
    console.log('Report will use:', curves.map(c => ({
      label: c.label,
      status: c.status,
      source: c.dataSource,
      points: c.points.length,
      filters: c.filters,
      first: c.points[0],
      last: c.points[c.points.length - 1]
    })))
    console.groupEnd()
    return curves
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

// ─────────────────────────────────────────────────────────────
// FIX 12 — exportToRealExcel dedupes columns per sheet.
// ─────────────────────────────────────────────────────────────
async function exportToRealExcel() {
  await loadSavedData()
  if (typeof loadAllInstrumentWorkflowsForReport === 'function') {
    await loadAllInstrumentWorkflowsForReport()
  }
  const report = reportPreviewData.value
  if (report.instruments.length === 0) return
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
  const instrumentSheets = []
  for (const inst of report.instruments) {
    const instKey = inst.id || (inst.name === 'Money Market' ? 'money-market' : inst.name === 'Bonds' ? 'bonds' : 'tbills')
    const wf = await sessionManager.getInstrumentWorkflow(activeSession.value?.id, instKey)
    const calculatedRows = wf?.instrumentSummary?.rows || []
    const cleanedRows = wf?.cleanedData || []
    const sourceRows = calculatedRows.length ? calculatedRows : cleanedRows
    sourceRows.forEach((item, idx) => {
      const name = item['Instrument Name'] || item.Instrument || item.BondName || item.TBillName || `${inst.name} ${idx + 1}`
      const ticker = item['BB Ticker'] || item.BBTicker || item.Ticker || item.Security || ''
      const faceValue = formatForExcel(parseFloat(item['Face Value'] || item.FaceValue || item.Amount || item.Principal || 0), 'money', 'FaceValue')
      const rate = formatForExcel(parseFloat(item['Avg Rate'] || item.Rate || item['Interest Rate'] || item['Coupon Rate'] || item['Discount Rate'] || 0), 'percentage', 'Rate')
      const term = formatForExcel(parseFloat(item['Days to Maturity'] || item.Term || item['Years to Maturity'] || 0), 'number', 'Term')
      appendixData.push([inst.name, name, ticker, faceValue, rate, term, valuationDate])
    })
    if (calculatedRows.length) instrumentSheets.push({ name: inst.name.substring(0, 31), rows: calculatedRows })
    else if (cleanedRows.length) instrumentSheets.push({ name: inst.name.substring(0, 31), rows: cleanedRows })
  }
  const appendixSheet = XLSX.utils.aoa_to_sheet(appendixData)
  appendixSheet['!cols'] = [{ wch: 18 }, { wch: 25 }, { wch: 15 }, { wch: 18 }, { wch: 12 }, { wch: 12 }, { wch: 18 }]
  XLSX.utils.book_append_sheet(workbook, appendixSheet, 'Appendix')
  for (const sheetData of instrumentSheets) {
    if (!sheetData.rows.length) continue
    const allCols = new Set()
    sheetData.rows.forEach(r => Object.keys(r).forEach(k => allCols.add(k)))
    const cols = dedupeColumns(Array.from(allCols).filter(c => !isExcludedColumn(c)))
    if (!cols.length) continue
    const headerRow = cols.map(formatColumnHeader)
    const bodyRows = sheetData.rows.map(row => cols.map(col => {
      const val = row[col] !== undefined ? row[col] : ''
      if (isPercentageField(col)) return formatForExcel(val, 'percentage', col)
      if (/value|price|amount|principal|interest/i.test(col)) return formatForExcel(val, 'money', col)
      return formatForExcel(val, 'number', col)
    }))
    const sheet = XLSX.utils.aoa_to_sheet([headerRow, ...bodyRows])
    XLSX.utils.book_append_sheet(workbook, sheet, sheetData.name)
  }
  XLSX.writeFile(workbook, `portfolio_report_${Date.now()}.xlsx`)
}

function formatRowForExcel(row) {
  const formatted = {}
  for (const [key, value] of Object.entries(row)) {
    if (isExcludedColumn(key)) continue
    const headerKey = formatColumnHeader(key)
    if (isPercentageField(key)) formatted[headerKey] = formatForExcel(value, 'percentage', key)
    else if (key.toLowerCase().includes('value') || key.toLowerCase().includes('price') || key.toLowerCase().includes('amount') || key.toLowerCase().includes('principal') || key.toLowerCase().includes('interest')) {
      formatted[headerKey] = formatForExcel(value, 'money', key)
    } else {
      formatted[headerKey] = formatForExcel(value, 'number', key)
    }
  }
  return formatted
}

// ─────────────────────────────────────────────────────────────
// FIX 13 — downloadCombinedReport('word') sends
// include_live_curves: false so the backend does NOT append
// a second (potentially stale) curve set to the client HTML.
// ─────────────────────────────────────────────────────────────
async function downloadCombinedReport(format) {
  if (format === 'excel') { await exportToRealExcel(); return }
  
  // Force a fresh read of the session BEFORE generating the report
  await loadSavedData(true)
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
      const response = await fetch(`${API_BASE_URL}/api/report/generate-word`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          report_html: html,
          instrument_type: route.params.type || null,
          file_name: `Dura-Capital-Combined-Report-${Date.now()}.docx`,
          include_live_curves: false
        })
      })
      const result = await response.json()
      if (!result.success) {
        alert('Failed to generate Word report: ' + (result.message || 'Unknown error'))
        return
      }
      const downloadPath = `${API_BASE_URL}/api/report/download-word/${sessionId}`
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

watch([rawData, cleanedData], () => {
  if (!autoSaveEnabled.value || skipAutoSave.value || isSaving.value || isSavingVersion) return
  debouncedSave()
}, { deep: true })

watch(() => activeTab.value, async (newTab) => {
  if (newTab === 'calculations' && hasCleanedData.value && !allCalculations.value?.totalValue && !isCalculating.value) {
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
        if (s) sessionManager.setActiveSession(s)
      } else {
        activeSession.value = null
      }
      const loaded = await loadSavedData(true)
      if (!loaded) {
        if (!route.query.tab) activeTab.value = 'upload'
      } else {
        if (!route.query.tab) {
          const savedTab = (await sessionManager.getInstrumentWorkflow(activeSession.value?.id, instrumentType.value))?.last_tab
          if (savedTab && steps.value.some(s => s.tab === savedTab)) activeTab.value = savedTab
          else activeTab.value = 'upload'
        }
        if (cleanedData.value.length && !allCalculations.value?.totalValue && !isCalculating.value) {
          await calculateMetrics()
        }
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
        if (versionsRes && versionsRes.success) s.version_count = versionsRes.total || 0
      } catch (e) { /* non-fatal */ }
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
          if (versionsRes && versionsRes.success) refreshed.version_count = versionsRes.total || 0
        } catch (e) { /* non-fatal */ }
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
            if (versionsRes && versionsRes.success) s.version_count = versionsRes.total || 0
          } catch (e) { /* non-fatal */ }
          activeSession.value = s
          sessionManager.setActiveSession(s)
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
      } catch (e) { /* non-fatal */ }
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
    await loadSavedData(true)
    await refreshSessionVersionCount(sessionId)
    forceUpdate.value++
  }
}

onBeforeUnmount(() => {
  window.removeEventListener('storage', () => checkAndReset())
  window.removeEventListener('session-restored', handleSessionRestored)
  if (saveTimeout) clearTimeout(saveTimeout)
  try { saveSessionData() } catch (err) { console.error('onBeforeUnmount save failed:', err) }
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
.btn-preview, .btn-review-excel, .btn-mapping, .btn-view-workbook, .btn-download-workbook { display: inline-flex; align-items: center; gap: 6px; padding: 6px 12px; border-radius: 6px; font-size: 12px; cursor: pointer; border: none; margin-left: 10px; transition: all 0.2s; }
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
.btn-download-workbook { background: #607D8B; color: white; }
.btn-download-workbook:hover { background: #455A64; transform: translateY(-1px); }
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
.currency-code-badge { position: absolute; right: 12px; top: 50%; transform: translateY(-50%); font-size: 11px; color: #999; font-weight: 500; background: #f5f5f5; padding: 2px 6px; border-radius: 4px; }
.detected-values-section { margin-top: 24px; padding: 20px; background: #f8f9ff; border-radius: 12px; border-left: 4px solid #4CAF50; }
.detected-values-section h3 { font-size: 16px; font-weight: 600; color: #0B2044; margin: 0 0 8px 0; }
.detected-values-section .section-hint { font-size: 13px; color: #666; margin: 0 0 16px 0; }
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
.custom-currency-field-vuetify { margin-bottom: 8px; }
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
.missing-fields-warning p { margin: 0 0 8px 0; font-weight: 600; color: #E65100; font-size: 14px; }
.missing-fields-warning ul { margin: 0; padding-left: 20px; }
.missing-fields-warning li { color: #E65100; font-size: 13px; margin-bottom: 4px; }
.multi-table-summary { padding: 12px 16px; background: #e8f5e9; border-radius: 8px; border-left: 4px solid #4CAF50; margin-bottom: 16px; font-size: 14px; color: #2E7D32; }
.multi-instruments-list { display: flex; flex-direction: column; gap: 16px; max-height: 400px; overflow-y: auto; }
.multi-instrument-item { padding: 16px; background: #f8f9ff; border-radius: 8px; border: 1px solid #e8ecf1; }
.multi-instrument-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid #e0e0e0; }
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
.date-format-select-inline { margin-left: 8px; padding: 4px 8px; border: 1px solid #ccc; border-radius: 4px; font-size: 12px; background: white; cursor: pointer; min-width: 120px; }
.date-format-select-inline:disabled { background: #f5f5f5; cursor: not-allowed; opacity: 0.6; }
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
.sortable-header { cursor: pointer; transition: background 0.2s; }
.sortable-header:hover { background: #1a3a6e; }
.sort-indicator { margin-left: 6px; font-size: 10px; color: #fff; }
.excel-popup-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.6); z-index: 999999 !important; display: flex; align-items: center; justify-content: center; padding: 20px; }
.excel-popup-content { background: white; border-radius: 12px; max-width: 95%; max-height: 90vh; width: 1400px; display: flex; flex-direction: column; box-shadow: 0 25px 60px rgba(0,0,0,0.3); overflow: hidden; }
.filters-row { display: flex; gap: 20px; align-items: flex-end; margin-bottom: 20px; flex-wrap: wrap; }
.filter-group { position: relative; display: flex; align-items: center; flex-wrap: wrap; flex: 1; min-width: 150px; }
.filter-group label { display: block; font-size: 12px; font-weight: 600; color: #0B2044; margin-bottom: 4px; }
.filter-select { width: 100%; padding: 10px 32px 10px 12px; border: 1px solid #ccc; border-radius: 8px; background: linear-gradient(to bottom, #ffffff 0%, #f5f7fa 100%); color: #0B2044; font-size: 14px; cursor: pointer; transition: border 0.2s, box-shadow 0.2s; box-shadow: 0 2px 4px rgba(0,0,0,0.08), inset 0 1px 2px rgba(255,255,255,0.8); appearance: none; -webkit-appearance: none; }
.filter-select:focus { outline: none; border-color: #0B2044; box-shadow: 0 0 0 3px rgba(11,32,68,0.15), 0 4px 8px rgba(0,0,0,0.1); }
.filter-custom-input { width: 100%; padding: 8px 12px; margin-top: 4px; border: 1px solid #ccc; border-radius: 6px; font-size: 13px; background: white; transition: border 0.2s; }
.filter-custom-input:focus { outline: none; border-color: #0B2044; box-shadow: 0 0 0 2px rgba(11,32,68,0.1); }
.chart-container--fred { position: relative; height: 400px; width: 100%; background: white; border-radius: 8px; padding: 10px; }
.chart-container--fred canvas { width: 100% !important; height: 100% !important; }
.loading-container, .error-container { text-align: center; padding: 40px; }
.spin { animation: spin 1s linear infinite; }
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
.upload-history { margin-top: 20px; padding: 15px; background: #f8f9ff; border-radius: 12px; }
.history-list { max-height: 200px; overflow-y: auto; }
.history-item { display: flex; align-items: center; gap: 12px; padding: 8px 12px; border-bottom: 1px solid #eee; cursor: pointer; transition: background 0.2s; flex-wrap: wrap; }
.history-item:hover { background: #e8ecf1; }
.history-item small { font-size: 11px; color: #666; margin-left: auto; }
.btn-delete-history { background: none; border: none; cursor: pointer; color: #f44336; font-size: 16px; }
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
.fred-meta { display: block; margin-top: 8px; color: #666; font-size: 12px; }
.chart-footer { margin-top: 10px; text-align: center; color: #666; font-size: 12px; }
.summary-report { padding: 10px 0; }
.summary-section { margin-bottom: 32px; padding: 20px; background: #f8f9ff; border-radius: 12px; border: 1px solid #e8ecf1; }
.summary-section h3 { font-size: 18px; color: #0B2044; border-bottom: 2px solid #0B2044; padding-bottom: 8px; margin-bottom: 16px; }
.section-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; padding-bottom: 12px; border-bottom: 2px solid #e8ecf1; }
.section-header h3 { display: flex; align-items: center; gap: 10px; margin: 0; color: #0B2044; font-size: 18px; font-weight: 600; }
.worksheet-badge { background: #4CAF50; color: white; padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 600; margin-left: 12px; }
.btn-sm { padding: 6px 12px; font-size: 13px; }
.summary-tabs { display: flex; gap: 8px; margin-bottom: 24px; border-bottom: 2px solid #e8ecf1; padding-bottom: 16px; }
.summary-tab { display: flex; align-items: center; gap: 8px; padding: 10px 20px; border: none; background: #f5f5f5; border-radius: 8px; font-size: 14px; font-weight: 600; cursor: pointer; transition: all 0.2s; color: #666; }
.summary-tab:hover:not(:disabled) { background: #e8ecf1; color: #0B2044; }
.summary-tab.active { background: #0B2044; color: white; }
.summary-tab:disabled { opacity: 0.4; cursor: not-allowed; }
.tab-count { background: rgba(255,255,255,0.2); padding: 2px 8px; border-radius: 12px; font-size: 12px; }
.summary-tab.active .tab-count { background: rgba(255,255,255,0.3); }
.analytics-cards { display: grid; grid-template-columns: repeat(5, 1fr); gap: 24px; margin-bottom: 28px; }
.quality-cards { display: grid; grid-template-columns: repeat(5, 1fr); gap: 24px; margin-bottom: 28px; }
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
@media (max-width: 768px) {
  .analytics-cards { grid-template-columns: repeat(2, 1fr); }
  .quality-cards { grid-template-columns: repeat(2, 1fr); }
  .page-header { flex-direction: column; align-items: flex-start; gap: 10px; }
  .summary-cards, .selection-cards { grid-template-columns: 1fr; }
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
.no-calcs-message { grid-column: 1 / -1; padding: 40px 20px; text-align: center; color: #999; font-size: 14px; background: #f9fafc; border-radius: 12px; border: 1px dashed #ccc; }
.no-calcs-message p { margin: 12px 0 0 0; }

/* ── Detection popup additions ─────────────────────────── */
.detection-count {
  background: rgba(255, 255, 255, 0.22);
  color: white;
  padding: 3px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
  margin-right: 12px;
}
.instrument-type-display {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  background: #f8f9ff;
  border-radius: 8px;
  border-left: 3px solid #0B2044;
  margin-bottom: 16px;
  font-size: 13px;
}
.required-summary {
  margin-left: auto;
  font-size: 12px;
  color: #2e7d32;
  background: #e8f5e9;
  padding: 3px 10px;
  border-radius: 12px;
  font-weight: 600;
}
.field-group {
  margin-bottom: 18px;
}
.field-group-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: #0B2044;
  margin-bottom: 10px;
}
.field-group-hint {
  font-weight: 400;
  color: #999;
  font-size: 12px;
}
.field-grid {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.field-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  background: #fafafa;
  border-radius: 6px;
  font-size: 13px;
  border-left: 3px solid transparent;
  width: 100%;
  box-sizing: border-box;
}
.field-row--required {
  background: #e8f5e9;
  border-left-color: #2e7d32;
}
.field-row--additional {
  background: #fff;
  border-left-color: #1565c0;
  cursor: pointer;
}
.field-row--additional:hover {
  background: #f0f7ff;
}
.field-row--excluded {
  opacity: 0.55;
  text-decoration: line-through;
}
.field-name {
  font-weight: 600;
  color: #0B2044;
  flex: 1 1 25%;
  min-width: 120px;
  word-break: break-word;
}
.field-value {
  font-family: 'Courier New', monospace;
  color: #2e7d32;
  font-weight: 600;
  flex: 1 1 25%;
}
.field-loc {
  font-size: 11px;
  color: #999;
  font-style: italic;
  flex: 0 0 auto;
  white-space: nowrap;
}
.field-checkbox {
  width: 16px;
  height: 16px;
  cursor: pointer;
  accent-color: #0B2044;
  flex: 0 0 auto;
}
.currency-variant-selector {
  flex: 0 0 auto;
  margin-left: auto;
}
.detection-footer {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 20px;
  background: #f9fafc;
  border-top: 1px solid #e0e0e0;
}
.footer-selection-summary {
  font-size: 13px;
  color: #666;
}

/* ── Compact cleaning field selector ───────────────────── */
.compact-fields-table {
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin-bottom: 8px;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  overflow: hidden;
  background: white;
}
.compact-field-row {
  display: grid;
  grid-template-columns: 26px 1fr 1.4fr;
  gap: 8px;
  align-items: center;
  padding: 6px 12px;
  font-size: 13px;
  border-bottom: 1px solid #f0f0f0;
  transition: background 0.15s;
}
.compact-field-row:last-child { border-bottom: none; }
.compact-field-row:hover { background: #f8f9ff; }
.compact-field-row--excluded {
  background: #fff4f4;
  opacity: 0.65;
}
.compact-field-row--excluded .compact-field-name,
.compact-field-row--excluded .compact-field-value {
  text-decoration: line-through;
  color: #999;
}
.compact-checkbox input {
  width: 15px;
  height: 15px;
  cursor: pointer;
  accent-color: #0B2044;
}
.compact-field-name {
  font-weight: 600;
  color: #0B2044;
  font-size: 12px;
}
.compact-field-value {
  font-family: 'Courier New', monospace;
  color: #2e7d32;
  font-size: 12px;
  font-weight: 600;
  text-align: right;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.compact-summary {
  font-size: 12px;
  color: #666;
  padding: 6px 12px;
  background: #f0f4ff;
  border-radius: 6px;
  margin-bottom: 16px;
}
</style>