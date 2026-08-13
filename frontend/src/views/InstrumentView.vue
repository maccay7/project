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

              <!-- Worksheet Selector - hidden after a sheet is processed -->
              <div v-if="worksheetWorkflow.workbookSheets.length > 0 && !worksheetSelected" class="worksheet-selector-section">
                <WorksheetSelector
                  :workbook-sheets="worksheetWorkflow.workbookSheets"
                  :worksheet-status="worksheetWorkflow.worksheetStatus"
                  :selected-worksheet="worksheetWorkflow.selectedWorksheet"
                  :loading="fileLoading"
                  :error="uploadError"
                  @select-sheet="handleWorksheetSelect"
                  @work-on-sheet="handleWorkOnSheet"
                  @view-results="handleViewResults"
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
                    <div v-if="!Object.keys(savedTemplates).length" class="empty-state">
                      <p>No saved mappings yet.</p>
                    </div>
                    <div v-else class="saved-mappings-list">
                      <div v-for="(template, name) in savedTemplates" :key="name" class="saved-mapping-item">
                        <div class="mapping-name">{{ name }}</div>
                        <div class="mapping-meta">Saved: {{ new Date(template.savedAt).toLocaleDateString() }}</div>
                        <div class="mapping-actions">
                          <button class="btn-secondary small" @click="loadMapping(template)">Load</button>
                          <button class="btn-secondary small danger" @click="deleteMapping(name)">Delete</button>
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
                    <div class="multi-table-summary">
                      <strong>{{ multiTableDetectionResults.length }} table(s) selected</strong>
                      <p style="margin: 8px 0 0 0; font-size: 13px; color: #666;">All detected fields from selected tables will be combined into a single instrument for calculations.</p>
                    </div>
                    
                    <div class="multi-instruments-list">
                      <div v-for="(instrument, index) in multiTableDetectionResults" :key="index" class="multi-instrument-item">
                        <div class="multi-instrument-header">
                          <strong>Table {{ index + 1 }}: {{ instrument.tableName }}</strong>
                        </div>
                        <div class="multi-instrument-fields">
                          <div v-for="(value, field) in instrument.fields" :key="field" class="multi-detected-field-item">
                            <span class="multi-detected-field-label">{{ field }}:</span>
                            <span class="multi-detected-field-value">{{ formatDetectedValue(field, value) }}</span>
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
                    
                    <!-- Currency Selection if multiple currencies detected -->
                    <div v-if="detectedCurrencies.length > 1" class="currency-selection-section">
                      <label class="currency-label">Select Currency:</label>
                      <select v-model="selectedCurrency" class="currency-select">
                        <option value="">-- Select Currency --</option>
                        <option v-for="currency in detectedCurrencies" :key="currency" :value="currency">{{ currency }}</option>
                      </select>
                    </div>
                    
                    <div class="detected-fields-list">
                      <div v-for="(value, field) in autoDetectedFields" :key="field" class="detected-field-item">
                        <span class="detected-field-label">{{ field }}:</span>
                        <span class="detected-field-value">{{ formatDetectedValue(field, value) }}</span>
                        <span v-if="autoDetectedFieldsWithMetadata[field]" class="detected-field-location">
                          @ {{ autoDetectedFieldsWithMetadata[field].location }}
                          ({{ (autoDetectedFieldsWithMetadata[field].confidence * 100).toFixed(0) }}%)
                        </span>
                      </div>
                    </div>
                    
                    <!-- Show missing fields if any -->
                    <div v-if="Object.keys(autoDetectedFields).length < requiredColumns.length" class="missing-fields-warning">
                      <p><strong>Missing Required Fields:</strong></p>
                      <ul>
                        <li v-for="col in requiredColumns.filter(c => !autoDetectedFields[c])" :key="col">{{ col }}</li>
                      </ul>
                    </div>
                  </v-card-text>
                  <v-card-actions>
                    <button class="btn-secondary" @click="showDetectionSuccess = false">Close</button>
                    <button class="btn-primary" @click="useDetectedFields">Work on This Worksheet</button>
                  </v-card-actions>
                </v-card>
              </v-dialog>

              <!-- Workbook Viewer Dialog -->
              <v-dialog v-model="showWorkbookViewer" max-width="95%" fullscreen hide-overlay>
                <v-card>
                  <v-card-title class="excel-dialog-title-no-logo">
                    <span>Excel Workbook – {{ currentSheetName || 'Select a sheet' }}</span>
                    <v-spacer></v-spacer>
                    <button class="btn-auto-detect" @click="autoDetectSingleInstrument" v-if="currentSheetName && workbookSheets.length">
                      Auto Detect
                    </button>
                    <button class="btn-work-on-sheet" @click="workOnSelectedSheet" v-if="currentSheetName && workbookSheets.length">
                      Work on This Sheet
                    </button>
                    <button class="btn-close-dialog" @click="showWorkbookViewer = false">×</button>
                  </v-card-title>
                  <v-card-text class="pa-0" style="height: calc(100vh - 120px);">
                    <ExcelWorkbookViewer
                      :workbook-data="{ sheets: workbookSheets, fileBuffer: originalFileBuffer }"
                      :file-name="uploadedFile?.name || 'Workbook'"
                      :instrument-type="instrumentType"
                      :worksheet-statuses="worksheetStatuses"
                      @close="showWorkbookViewer = false"
                      @sheet-selected="handleSheetSelectedFromViewer"
                      @single-instrument-extracted="handleSingleInstrumentExtracted"
                      @table-isolated="handleTableIsolated"
                      @multi-table-detect="handleMultiTableDetect"
                    />
                  </v-card-text>
                  <div class="popup-footer">
                    <span class="valuation-date-footer">Valuation Date: {{ new Date().toISOString().split('T')[0] }}</span>
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
                      <label class="option-checkbox"><input type="checkbox" v-model="cleaningOptions.standardizeDates"> Standardize dates to YYYY-MM-DD</label>
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
                  <button class="btn-primary" @click="continueAfterCleaning" :disabled="!cleanedData.length">Continue</button>
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
                    <div class="card-value">${{ formatNumber(allCalculations.totalValue || 0) }}</div>
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

                <div class="calculations-section">
                  <h3>{{ instrumentLabel }} Calculations</h3>
                  <div class="calculations-grid">
                    <div
                      v-for="calc in calculationFields"
                      :key="calc.key"
                      class="calculation-card"
                      @click="showFormula(calc.key)"
                    >
                      <div class="calc-name">{{ calc.label }}</div>
                      <div class="calc-value">{{ formatCalcValue(calc.key, selectedCalculations[calc.key] ?? allCalculations[calc.key]) }}</div>
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
                  <label>Maturity</label>
                  <select v-model="selectedMaturityOption" @change="onMaturitySelectChange" class="filter-select">
                    <option v-for="opt in maturityOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
                    <option value="__custom__">✏️ Custom...</option>
                  </select>
                  <input
                    v-if="selectedMaturityOption === '__custom__'"
                    v-model="customMaturityInput"
                    @input="onCustomMaturityInput"
                    placeholder="e.g. 3Y, 6M, 13W"
                    class="filter-custom-input"
                  />
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
              <div v-if="!instrumentSummary.rows.length" class="empty-state">
                <p>No summary data available. Please run calculations first.</p>
              </div>
              <div v-else>
                <div class="analytics-section" style="margin-bottom: 24px;">
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
                        <div class="kpi-value">${{ descriptiveAnalytics['Total Face Value'] || '0.00' }}</div>
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

                <div class="quality-control-section" style="margin-bottom: 24px;">
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

                <div class="summary-report">
                  <div class="excel-viewer-button" style="text-align: center; margin-top: 20px;">
                    <button class="btn-primary" @click="viewInstrumentSummaryExcel" style="font-size: 18px; padding: 16px 40px;">
                      📊 View Instrument Summary Excel
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
                      <p class="popup-instruction">Complete instrument summary with all calculated values.</p>
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
                            <tr v-for="(row, idx) in sortedInstrumentSummaryRows" :key="idx">
                              <td v-for="col in instrumentSummaryColumnsForDisplay" :key="col">{{ formatCellValue(row[col], col) }}</td>
                            </tr>
                          </tbody>
                        </table>
                      </div>
                    </div>
                    <div class="popup-footer">
                      <span class="valuation-date-footer">Valuation Date: {{ new Date().toISOString().split('T')[0] }}</span>
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
                    <div class="selection-card" :class="{ active: selectedInstruments.moneyMarket }" @click="selectedInstruments.moneyMarket = !selectedInstruments.moneyMarket">
                      <v-icon size="28" color="#1E88E5">mdi-chart-line</v-icon>
                      <span>Money Market</span>
                      <div class="check-indicator" v-if="selectedInstruments.moneyMarket"><v-icon size="16" color="#4CAF50">mdi-check-circle-outline</v-icon></div>
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
          <span class="valuation-date-footer">Valuation Date: {{ new Date().toISOString().split('T')[0] }}</span>
          <v-spacer></v-spacer>
          <button class="btn-secondary" @click="closeExcelDialog">Close</button>
        </div>
      </v-card>
    </v-dialog>

    <!-- Formula Dialog -->
    <v-dialog v-model="formulaDialog" max-width="500px">
      <v-card>
        <v-card-title class="formula-dialog-title"><v-icon>mdi-ruler</v-icon> Formula Used</v-card-title>
        <v-card-text class="formula-text">{{ formulaText }}</v-card-text>
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
          <span class="valuation-date-footer">Valuation Date: {{ new Date().toISOString().split('T')[0] }}</span>
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
// ================================================================
// FULL SCRIPT – all functions included (with all fixes applied)
// ================================================================

import { ref, computed, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import FixedLayout from '@/components/FixedLayout.vue'
import * as XLSX from 'xlsx'
import api from '@/services/api.js'
import sessionManager from '@/services/sessionManager.js'
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
import { getInstrumentColumns } from '@/config/instrumentColumns.js'
import { useInstrumentConfig } from '@/composables/useInstrumentConfig'

// ========================
// autoDetectTable – used in cleaning
// ========================
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

// ================================================================
// All refs, computed, and functions
// ================================================================
const router = useRouter()
const route = useRoute()

const instrumentType = ref('money-market')

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
      { key: 'weightedAvgRate', label: 'Weighted Average Rate', suffix: '%' },
      { key: 'totalInterest', label: 'Total Interest (Annualized)', prefix: '$' },
      { key: 'interestEarned', label: 'Interest Earned', prefix: '$' },
      { key: 'annualYield', label: 'Annual Yield', suffix: '%' },
      { key: 'effectiveAnnualRate', label: 'Effective Annual Rate', suffix: '%' },
      { key: 'avgDaysToMaturity', label: 'Average Days to Maturity', suffix: ' days' },
      { key: 'totalPrincipal', label: 'Total Principal', prefix: '$' }
    ],
    summaryMetrics: [
      { key: 'totalValue', label: 'Total Portfolio Value', prefix: '$' },
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
      { key: 'weightedAvgCoupon', label: 'Weighted Average Coupon', suffix: '%' },
      { key: 'totalAnnualIncome', label: 'Total Annual Income', prefix: '$' },
      { key: 'avgYTM', label: 'Average Yield to Maturity', suffix: '%' },
      { key: 'duration', label: 'Duration (years)' }
    ],
    summaryMetrics: [
      { key: 'totalValue', label: 'Total Portfolio Value', prefix: '$' },
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
      { key: 'weightedAvgDiscount', label: 'Weighted Average Discount', suffix: '%' },
      { key: 'totalDiscount', label: 'Total Discount', prefix: '$' },
      { key: 'effectiveYield', label: 'Effective Yield', suffix: '%' },
      { key: 'bondEquivalentYield', label: 'Bond Equivalent Yield', suffix: '%' },
      { key: 'pricePer100', label: 'Price per $100', prefix: '$' },
      { key: 'totalPurchasePrice', label: 'Total Purchase Price', prefix: '$' },
      { key: 'avgInvestment', label: 'Average Investment', prefix: '$' },
      { key: 'holdingPeriodYield', label: 'Holding Period Yield', suffix: '%' },
      { key: 'annualizedYield', label: 'Annualized Yield', suffix: '%' }
    ],
    summaryMetrics: [
      { key: 'totalValue', label: 'Total Portfolio Value', prefix: '$' },
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
  const type = newType || route.path.split('/').pop() || 'money-market'
  console.log('=== ROUTE CHANGE DETECTED ===')
  console.log('New type from route:', newType)
  console.log('Type from path:', route.path.split('/').pop())
  console.log('Final type:', type)
  console.log('Current instrumentType.value:', instrumentType.value)
  if (instrumentType.value !== type) {
    instrumentType.value = type
    console.log('Updated instrumentType.value to:', instrumentType.value)
    loadConfig(type).then(() => {
      console.log('Config loaded for type:', type)
      console.log('Required columns after load:', requiredColumns.value)
    }).catch((e) => {
      console.error('Failed to load config:', e)
    })
    if (worksheetWorkflow.reset) worksheetWorkflow.reset()
  }
}, { immediate: true })

const activeSession = ref(null)
const yieldCurveLoading = ref(false)
const yieldCurveError = ref('')
const yieldCurveChart = ref(null)
const chartInstanceRef = { current: null }
const yieldCurveData = ref([])
const chartSeriesLabel = ref('')
const chartImageData = ref('')

// NEW: Track worksheet processing status
const worksheetStatuses = ref({})

const selectedMaturityOption = ref('')
const selectedCountryOption = ref('USA')
const selectedCurrencyOption = ref('USD')
const customCountryInput = ref('')
const customCurrencyInput = ref('')
const customMaturityInput = ref('')

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
const multiTableDetectionResults = ref([])
const selectedWorkflowInstrument = ref(null)
const selectedWorkflowIndex = ref(0)
const sortColumn = ref('')
const sortOrder = ref('asc')
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

// Snackbar notification system
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

const savedTemplates = ref({})
const selectedTemplate = ref('')
const newTemplateName = ref('')

const cleaningOptions = ref({
  removeDuplicates: true, fillMissingText: false, dropRowsWithMissing: false, trimWhitespace: true,
  convertToNumbers: true, removeOutliers: false, standardizeDates: false, removeSpecialChars: false,
  changeCase: false, caseType: 'none', fillWithCustom: false, customFillValue: '',
  removeColumnsAllMissing: false, capOutliers: false, removeRowsSpecificColumnEmpty: false,
  specificColumn: '', standardizeNumericRange: false, removeEmptyRows: false, fillForward: true, fillBackward: false
})

const selectedInstrumentType = computed(() => instrumentLabel.value)
const instrumentSummary = ref({ columns: [], rows: [] })
const portfolioSummary = ref({ columns: [], rows: [] })
const selectedCalculationInstrument = ref(-1)
const currentlyViewingInstrument = ref(null)
const showAllCalculationsPopup = ref(false)
const sheetType = ref('multi')
const extractedValues = ref({})
const worksheetStatus = ref({})
const uploadHistory = ref([])

const selectedInstruments = ref({ moneyMarket: true, bonds: true, tbills: true })
const reportPreviewDialog = ref(false)
const reportPreviewHtml = ref('')

const showExcelDialog = ref(false)
const excelData = ref([])
const excelColumns = ref([])
const excelDialogTitle = ref('')

const showWorkbookViewer = ref(false)
const workbookSheets = ref([])
const currentSheetName = ref('')
const singleInstrumentExtractedValues = ref({})
const isolatedTableData = ref(null)
const autoDetectedFields = ref({})
const autoDetectedFieldsWithMetadata = ref({})
const detectedCurrencies = ref([])
const detectedInstrumentType = ref('') // Store instrument type at detection time
const selectedCurrency = ref('')

const showModalViewer = ref(false)
const viewerFileData = ref(null)

const formulaDialog = ref(false)
const formulaText = ref('')
const formulas = ref({})
const manualInputs = ref({})

let saveTimeout = null
let lastInstrument = ''
let lastSessionId = ''
let lastSaveTime = 0
const SAVE_DEBOUNCE_MS = 2000

const selectedSummaryWorksheet = ref('')
const availableSummaryWorksheets = computed(() => [])

// Track which sheets have already had mapping dialog shown
const mappingShownForSheet = ref({})

const currentSummaryRows = computed(() => {
  return instrumentSummary.value.rows
})

const descriptiveAnalytics = computed(() => {
  const rows = currentSummaryRows.value
  if (!rows.length) return {}

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
      // Check if this is a time field (days, months, years, maturity, duration, term, week, time)
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
  if (selectedCountryOption.value === '__custom__') return customCountryInput.value || 'USA'
  return selectedCountryOption.value
})
const effectiveCurrency = computed(() => {
  if (selectedCurrencyOption.value === '__custom__') return customCurrencyInput.value || 'USD'
  return selectedCurrencyOption.value
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
  const exclude = ['_raw', '_source', 'index', '__v', 'instrument_name', 'instrument_type', 'Worksheet', 'worksheet']
  const cols = instrumentSummary.value.columns.filter(c => !exclude.includes(c))
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

const instrumentSearchQuery = ref('')

const sortedInstrumentSummaryRows = computed(() => {
  let rows = instrumentSummary.value.rows
  
  // Apply search filter
  if (instrumentSearchQuery.value) {
    const query = instrumentSearchQuery.value.toLowerCase()
    rows = rows.filter(row => {
      return Object.values(row).some(val => 
        String(val).toLowerCase().includes(query)
      )
    })
  }
  
  // Apply sorting
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

const calculationFields = computed(() => {
  const fields = config.value.calculationFields || []
  return fields.map(field => ({
    ...field,
    value: selectedCalculations.value[field.key] !== undefined ? selectedCalculations.value[field.key] : allCalculations.value[field.key] !== undefined ? allCalculations.value[field.key] : null
  }))
})

function formatCalcValue(key, value) {
  if (value === null || value === undefined) return '—'
  const field = config.value.calculationFields.find(f => f.key === key)
  if (!field) return value
  
  // Round numeric values to 2 decimal places, but round time values to whole numbers
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

// ===== switchTab =====
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
function goToPortfolioSummary() { saveSessionData(); router.push('/summary') }

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
    saveSessionData()
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
  if (num === undefined || num === null) return '0.00'
  if (isTimeField) {
    const rounded = Math.round(num)
    return rounded.toLocaleString()
  }
  const rounded = Math.round(num * 100) / 100
  return rounded.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function formatTimeValue(num) {
  if (num === undefined || num === null) return '0'
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
    totalInterest: 0,
    interestEarned: 0,
    annualYield: 0,
    effectiveAnnualRate: 0,
    avgDaysToMaturity: 0,
    totalPrincipal: 0,
    avgCouponRate: 0,
    weightedAvgCoupon: 0,
    totalAnnualIncome: 0,
    avgYTM: 0,
    duration: 0,
    avgDiscountRate: 0,
    weightedAvgDiscount: 0,
    totalDiscount: 0,
    effectiveYield: 0,
    bondEquivalentYield: 0,
    totalPurchasePrice: 0,
    avgInvestment: 0,
    holdingPeriodYield: 0,
    annualizedYield: 0,
    pricePer100: 0
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

  agg.totalValue = total
  agg.instrumentCount = count
  agg.avgRate = avgRate
  agg.weightedAvgRate = weightedAvg
  agg.totalInterest = total * (avgRate / 100) * 90 / 360
  agg.interestEarned = agg.totalInterest
  agg.annualYield = avgRate
  agg.effectiveAnnualRate = avgRate
  agg.avgDaysToMaturity = 90
  agg.totalPrincipal = total

  const couponSum = rows.reduce((sum, row) => sum + getNumber(row, 'Avg Coupon Rate', 'avg_coupon_rate', 'Coupon Rate', 'coupon_rate'), 0)
  agg.avgCouponRate = count > 0 ? couponSum / count : 0
  agg.weightedAvgCoupon = weightedAvg
  agg.totalAnnualIncome = total * (agg.avgCouponRate / 100)
  agg.avgYTM = avgRate
  agg.duration = 10

  const discountSum = rows.reduce((sum, row) => sum + getNumber(row, 'Avg Discount Rate', 'avg_discount_rate', 'Discount Rate', 'discount_rate'), 0)
  agg.avgDiscountRate = count > 0 ? discountSum / count : 0
  agg.weightedAvgDiscount = weightedAvg
  agg.totalDiscount = total * (agg.avgDiscountRate / 100) * 90 / 360
  agg.effectiveYield = avgRate
  agg.bondEquivalentYield = avgRate
  agg.totalPurchasePrice = total - agg.totalDiscount
  agg.avgInvestment = count > 0 ? agg.totalPurchasePrice / count : 0
  agg.holdingPeriodYield = avgRate
  agg.annualizedYield = avgRate
  agg.pricePer100 = 100 * (1 - (agg.avgDiscountRate / 100) * 90 / 360)

  return agg
}

function runInstrumentCalculations(row, instrumentType) {
  const results = {}
  const getNumber = (val) => { const num = parseFloat(val); return isNaN(num) ? 0 : num }

  const nameCol = columnMapping.value['Instrument Name'] || 'Instrument'
  const instrumentName = row[nameCol] || row['Instrument'] || row['Name'] || 'Instrument'

  const amount = getNumber(row['Amount'] || row['FaceValue'] || row['Principal'] || row['Value'] || 0)
  const rate = getNumber(row['Rate'] || row['InterestRate'] || row['CouponRate'] || row['DiscountRate'] || row['Yield'] || 0)
  const days = getNumber(row['DaysToMaturity'] || row['Term'] || row['Maturity'] || 90)

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
    results['Duration'] = 10
    results['duration'] = 10
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

function addToHistory(filename, data) {
  const existing = uploadHistory.value.find(h => h.name === filename && (Date.now() - h.date) < 5000)
  if (existing) return
  // Don't store fileData in history to avoid localStorage quota issues
  uploadHistory.value.unshift({
    name: filename,
    date: Date.now(),
    data: JSON.stringify(data)
  })
  if (uploadHistory.value.length > 5) uploadHistory.value.pop() // Reduce from 10 to 5
  saveUploadHistory()
}

async function loadHistoryFile(item) {
  console.log('Loading history file:', item.name)
  console.log('item.fileData exists:', !!item.fileData)
  
  // Clear old history items without fileData since they can't support workbook viewer
  if (!item.fileData) {
    // Remove this item from history since it's outdated
    const idx = uploadHistory.value.findIndex(h => h.name === item.name && h.date === item.date)
    if (idx !== -1) {
      uploadHistory.value.splice(idx, 1)
      saveUploadHistory()
    }
    return
  }
  
  if (confirm(`Load ${item.name}? Current unsaved data will be lost.`)) {
    const data = JSON.parse(item.data)
    rawData.value = data
    originalRawData.value = JSON.parse(JSON.stringify(data))
    originalFileColumns.value = Object.keys(data[0] || {})
    fileColumns.value = [...originalFileColumns.value]

    if (item.fileData) {
      uploadedFileBase64.value = item.fileData
      try {
        const response = await fetch(item.fileData)
        const blob = await response.blob()
        uploadedFile.value = new File([blob], item.name, { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
        
        // Re-parse the workbook to get workbookSheets for viewer
        console.log('Re-parsing workbook from history file...')
        console.log('Uploaded file:', uploadedFile.value)
        const result = await worksheetWorkflow.handleFileUpload(uploadedFile.value)
        console.log('Workbook parse result:', result)
        console.log('worksheetWorkflow.workbookSheets.value after parse:', worksheetWorkflow.workbookSheets.value)
        if (result.success) {
          workbookSheets.value = worksheetWorkflow.workbookSheets.value
          worksheetStatus.value = worksheetWorkflow.worksheetStatus.value
          originalFileBuffer.value = worksheetWorkflow.originalFileBuffer.value
          console.log('Workbook re-parsed from history:', workbookSheets.value.length, 'sheets')
          console.log('workbookSheets.value:', workbookSheets.value)
          console.log('workbookSheets.value[0]:', workbookSheets.value[0])
        } else {
          console.error('Workbook parse failed:', result.error)
        }
      } catch (err) {
        console.error('Failed to restore file from base64:', err)
        uploadedFile.value = { name: item.name, size: 0 }
      }
    } else {
      uploadedFile.value = { name: item.name, size: 0 }
      uploadedFileBase64.value = null
    }

    columnMapping.value = autoMatchColumns(fileColumns.value, requiredColumns.value, columnVariations.value)
    applyCurrentMapping()
    worksheetSelected.value = false  // Don't auto-select, let user choose from workbook viewer
    showPreview.value = false  // Show workbook viewer instead of preview
    saveSessionData()
    forceUpdate.value++
    console.log('History file loaded, workbookSheets length:', workbookSheets.value.length)
  }
}

function deleteHistoryItem(idx) {
  uploadHistory.value.splice(idx, 1)
  saveUploadHistory()
}

function handleFileUpload(e) {
  console.log('handleFileUpload called, event:', e)
  console.log('Files selected:', e.target.files)
  console.log('Number of files:', e.target.files.length)
  
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
    // Reset worksheet statuses when new file is uploaded
    worksheetStatuses.value = {}
    console.log('Calling readFileData with file:', fileCopy.name)
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
    // Reset worksheet statuses when new file is uploaded
    worksheetStatuses.value = {}
    readFileData(fileCopy)
  }
}

async function readFileData(file) {
  console.log('readFileData called with file:', file.name, 'size:', file.size)
  console.log('uploadedFile.value before:', uploadedFile.value?.name)
  fileLoading.value = true
  uploadError.value = ''

  try {
    // Convert file to base64 for history storage
    const base64Promise = new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = (e) => {
        uploadedFileBase64.value = e.target.result
        console.log('File converted to base64, length:', uploadedFileBase64.value?.length)
        resolve(e.target.result)
      }
      reader.onerror = reject
      reader.readAsDataURL(file)
    })
    await base64Promise

    console.log('Calling worksheetWorkflow.handleFileUpload...')
    const result = await worksheetWorkflow.handleFileUpload(file)

    console.log('File upload result:', result)
    console.log('Result success:', result.success)
    console.log('Result sheets:', result.sheets?.length)
    console.log('Result error:', result.error)

    if (result.success) {
      workbookSheets.value = worksheetWorkflow.workbookSheets.value
      worksheetStatus.value = worksheetWorkflow.worksheetStatus.value
      originalFileBuffer.value = worksheetWorkflow.originalFileBuffer.value

      console.log('Workbook loaded (preview):', result.sheets.length, 'sheets')
      console.log('workbookSheets.value:', workbookSheets.value)
      console.log('worksheetStatus.value:', worksheetStatus.value)
      console.log('worksheetWorkflow.workbookSheets.value:', worksheetWorkflow.workbookSheets.value)
      console.log('worksheetWorkflow.workbookSheets.length:', worksheetWorkflow.workbookSheets.value.length)
      console.log('worksheetSelected.value:', worksheetSelected.value)
      console.log('UI condition check:', worksheetWorkflow.workbookSheets.value.length > 0 && !worksheetSelected.value)
      console.log('originalFileBuffer.value set:', !!originalFileBuffer.value)
      console.log('originalFileBuffer.value byteLength:', originalFileBuffer.value?.byteLength || 0)

      worksheetSelected.value = false
      currentSheetName.value = ''
      showPreview.value = false
      sheetType.value = 'multi'

      addToHistory(file.name, result.sheets[0]?.data || [])
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
  const result = worksheetWorkflow.selectWorksheet(sheetName)
  if (result.success) {
    currentSheetName.value = sheetName
    worksheetSelected.value = true
    const sheet = workbookSheets.value.find(s => s.name === sheetName)
    if (sheet) {
      // Load preview data (100 rows) instead of full data
      const previewResult = worksheetWorkflow.parseSheetPreview(sheetName, 100)
      if (previewResult) {
        rawData.value = previewResult.jsonData || []
        originalRawData.value = JSON.parse(JSON.stringify(previewResult.jsonData || []))
        fileColumns.value = previewResult.headers || []
        originalFileColumns.value = [...fileColumns.value]
        sheetTotalRows.value = previewResult.totalRows || 0
      }
      sheetType.value = 'multi' // Will be updated after processing
    }
  }
}

// ================================================================
// handleSheetSelectedFromViewer
// ================================================================
function handleSheetSelectedFromViewer(sheetName) {
  console.log('Sheet selected from viewer:', sheetName)
  currentSheetName.value = sheetName
  worksheetSelected.value = true
}

// ================================================================
// Handle single instrument extracted from workbook viewer
// ================================================================
function handleSingleInstrumentExtracted({ sheetName, extractedValues }) {
  console.log('Single instrument extracted from sheet:', sheetName, extractedValues)
  currentSheetName.value = sheetName
  singleInstrumentExtractedValues.value = extractedValues
}

// ================================================================
// FIXED: handleTableIsolated – sets worksheetSelected = true
// ================================================================
function handleTableIsolated({ sheetName, tableName, data, headers, tableRange }) {
  console.log('Table isolated for mapping:', sheetName, tableName, tableRange)
  
  isolatedTableData.value = {
    sheetName,
    tableName,
    data,
    headers,
    tableRange
  }
  
  currentSheetName.value = sheetName
  showWorkbookViewer.value = false
  rawData.value = data
  originalRawData.value = JSON.parse(JSON.stringify(data))
  fileColumns.value = headers
  originalFileColumns.value = [...headers]
  showMappingDialog.value = true
  mappingApplied.value = false
  columnMapping.value = autoMatchColumns(headers, requiredColumns.value, columnVariations.value)
  applyCurrentMapping()
  worksheetSelected.value = true  // Enable preview, review, map buttons
  showPreview.value = true
  console.log('Isolated table data loaded for mapping:', data.length, 'rows')
}

// ================================================================
// handleWorkOnSheet
// ================================================================
async function handleWorkOnSheet(sheetName) {
  fileLoading.value = true
  uploadError.value = ''

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
        const headers = Object.keys(sheetData[0] || {})
        if (headers.length) {
          columnMapping.value = autoMatchColumns(headers, requiredColumns.value, columnVariations.value)
          const mappingKey = `mapping_${instrumentType.value}_${uploadedFile.value?.name || 'default'}`
          const savedMapping = localStorage.getItem(mappingKey)
          if (savedMapping) {
            try {
              const parsed = JSON.parse(savedMapping)
              columnMapping.value = { ...columnMapping.value, ...parsed }
            } catch (e) {}
          }
        }
        applyCurrentMapping()
        if (result.type === 'multi' && !mappingShownForSheet.value[sheetName]) {
          mappingShownForSheet.value[sheetName] = true
          showMappingDialog.value = true
        }
        showPreview.value = true
      } else {
        // Single instrument – show extracted values in preview
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
    // Both single and multi instruments should show calculations tab
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
  const hasAnyMapping = requiredColumns.value.some(col => columnMapping.value[col])
  if (!hasAnyMapping) {
    rawData.value = originalRawData.value
    mappingApplied.value = false
    return
  }
  const mappedData = originalRawData.value.map(row => {
    const newRow = {}
    requiredColumns.value.forEach(col => {
      const srcCol = columnMapping.value[col]
      newRow[col] = srcCol ? getCellValue(row[srcCol]) : ''
    })
    return newRow
  })
  rawData.value = mappedData
  const allMapped = requiredColumns.value.every(col => columnMapping.value[col])
  mappingApplied.value = allMapped
  showPreview.value = true
}

function updateColumnMapping(newMapping) {
  columnMapping.value = { ...newMapping }
  applyCurrentMapping()
  debouncedSave()
}

function saveFinalMapping() {
  const mappingKey = `mapping_${instrumentType.value}_${uploadedFile.value?.name || 'default'}`
  localStorage.setItem(mappingKey, JSON.stringify(columnMapping.value))

  const templateName = `${instrumentType.value} - ${uploadedFile.value?.name || 'Custom'}`
  savedTemplates.value[newTemplateName.value] = {
    columnMapping: columnMapping.value,
    requiredColumns: requiredColumns.value,
    fileColumns: fileColumns.value,
    savedAt: new Date().toISOString()
  }
  saveTemplates()
  newTemplateName.value = ''
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
    const newMapping = autoMatchColumns(fileColumns.value, requiredColumns.value, columnVariations.value)
    columnMapping.value = { ...columnMapping.value, ...newMapping }
  }
  applyCurrentMapping()
  forceUpdate.value++
}

// Helper function to extract actual cell value from Excel cell objects
function getCellValue(cell) {
  if (cell == null) return ""
  
  // SheetJS cell object with formatted value (w) or raw value (v)
  if (typeof cell === 'object' && cell !== null) {
    // Try formatted value first (w), then raw value (v), then formula (f)
    if (cell.w !== undefined && cell.w !== null) return cell.w
    if (cell.v !== undefined && cell.v !== null) return cell.v
    if (cell.f !== undefined && cell.f !== null) return cell.f
    // Handle array objects
    if (Array.isArray(cell)) return cell.join(', ')
    // Fallback to string representation for any other object
    try {
      return JSON.stringify(cell)
    } catch {
      return String(cell)
    }
  }
  
  // Return as-is if it's already a primitive value
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

  if (uploadedFile.value) {
    const mappingKey = `mapping_${uploadedFile.value.name}_${uploadedFile.value.size}`
    const savedMapping = localStorage.getItem(mappingKey)
    if (savedMapping) {
      try {
        columnMapping.value = JSON.parse(savedMapping)
        console.log('Loaded saved mapping for file:', uploadedFile.value.name)
      } catch (e) {
        console.warn('Failed to load saved mapping:', e)
      }
    }
  }

  showMappingDialog.value = true
}

function closeMappingDialog() {
  showMappingDialog.value = false
}

function applyColumnMappingAndClose() {
  applyCurrentMapping()

  if (uploadedFile.value && columnMapping.value) {
    const mappingKey = `mapping_${uploadedFile.value.name}_${uploadedFile.value.size}`
    localStorage.setItem(mappingKey, JSON.stringify(columnMapping.value))
    console.log('Mapping saved for file:', uploadedFile.value.name)
  }

  showMappingDialog.value = false
  showPreview.value = true
  forceUpdate.value++
  refreshFileColumns()
}

function resetMapping() {
  const empty = {}
  requiredColumns.value.forEach(col => empty[col] = null)
  columnMapping.value = empty
  applyCurrentMapping()
}

function openWorkbookViewer() {
  console.log('Opening workbook viewer...')
  console.log('workbookSheets.value:', workbookSheets.value)
  console.log('workbookSheets.length:', workbookSheets.value.length)
  console.log('originalFileBuffer.value present?', !!originalFileBuffer.value)
  console.log('originalFileBuffer.value length:', originalFileBuffer.value?.byteLength || 0)
  console.log('uploadedFile.name:', uploadedFile.value?.name)
  
  if (workbookSheets.value.length > 0) {
    console.log('First sheet:', workbookSheets.value[0])
    console.log('First sheet has fullData?', !!workbookSheets.value[0]?.fullData)
    console.log('First sheet fullData length:', workbookSheets.value[0]?.fullData?.length || 0)
  }
  
  if (!uploadedFile.value) {
    alert('Please upload a file first')
    return
  }
  if (!workbookSheets.value.length) {
    alert('No workbook sheets available')
    return
  }
  if (!originalFileBuffer.value) {
    alert('File buffer not available. Please try re-uploading the file.')
    return
  }
  if (originalFileBuffer.value.byteLength === 0) {
    alert('File buffer is empty. Please try re-uploading the file.')
    return
  }
  if (!currentSheetName.value && workbookSheets.value.length) {
    currentSheetName.value = workbookSheets.value[0].name
  }
  
  // Load worksheet statuses from session
  if (activeSession.value?.id) {
    loadWorksheetStatuses()
  }
  
  showWorkbookViewer.value = true
}

// ================================================================
// workOnSelectedSheet
// ================================================================
function workOnSelectedSheet() {
  console.log('=== workOnSelectedSheet called ===')
  console.log('currentSheetName.value:', currentSheetName.value)
  console.log('workbookSheets.value.length:', workbookSheets.value.length)
  
  if (!currentSheetName.value) {
    console.log('ERROR: No sheet selected')
    alert('Please select a sheet first')
    return
  }
  
  if (!originalFileBuffer.value) {
    console.log('ERROR: No file buffer available')
    alert('File buffer not available')
    return
  }
  
  console.log('Calling handleWorkOnSheet with:', currentSheetName.value)
  handleWorkOnSheet(currentSheetName.value)
  showWorkbookViewer.value = false
}

// ================================================================
// autoDetectSingleInstrument
// ================================================================
async function autoDetectSingleInstrument() {
  if (!currentSheetName.value || !originalFileBuffer.value) {
    alert('Please select a sheet first')
    return
  }

  console.log('=== Auto Detect Started ===')
  console.log('Current Sheet:', currentSheetName.value)
  console.log('Instrument Type from page:', instrumentType.value)
  console.log('Route path:', window.location.pathname)
  console.log('Required Columns:', requiredColumns.value)
  console.log('File Buffer Length:', originalFileBuffer.value.byteLength)

  try {
    const detectionResult = await autoDetectInstrumentFields(
      originalFileBuffer.value,
      currentSheetName.value,
      requiredColumns.value,
      instrumentType.value
    )

    console.log('=== Detection Result ===')
    console.log('Detected Fields:', detectionResult.fields)
    console.log('Detected Fields with Metadata:', detectionResult.fieldsWithMetadata)
    console.log('Detected Currencies:', detectionResult.currencies)
    console.log('Missing Fields:', detectionResult.missingFields)

    if (detectionResult && detectionResult.fields && Object.keys(detectionResult.fields).length > 0) {
      autoDetectedFields.value = detectionResult.fields
      autoDetectedFieldsWithMetadata.value = detectionResult.fieldsWithMetadata
      detectedCurrencies.value = detectionResult.currencies || []
      detectedInstrumentType.value = instrumentType.value // Store instrument type at detection time
      
      // Auto-select first currency if only one detected
      if (detectedCurrencies.value.length === 1) {
        selectedCurrency.value = detectedCurrencies.value[0]
      } else if (detectedCurrencies.value.length > 1) {
        selectedCurrency.value = ''
      }
      
      showDetectionSuccess.value = true
  console.log('=== POPUP OPENING ===')
  console.log('instrumentType.value at popup:', instrumentType.value)
  console.log('detectedInstrumentType.value:', detectedInstrumentType.value)
  console.log('instrumentType object:', instrumentType)
    } else {
      alert('Auto Detect could not identify required fields. Please try manual entry.')
    }
  } catch (error) {
    console.error('Auto Detect error:', error)
    alert('Auto Detect failed: ' + error.message)
  }
}

// ================================================================
// handleMultiTableDetect
// ================================================================
async function handleMultiTableDetect(event) {
  console.log('=== Multi-Table Detect Started ===')
  console.log('Sheet Name:', event.sheetName)
  console.log('Number of tables:', event.tables.length)
  console.log('Instrument Type:', event.instrumentType)

  const detectedInstruments = []
  
  for (const table of event.tables) {
    console.log(`Processing table: ${table.tableName}`)
    console.log(`Table range: Row ${table.range.startRow + 1} - ${table.range.endRow + 1}, Col ${table.range.startCol} - ${table.range.endCol}`)
    console.log(`Table data length:`, table.data?.length)
    console.log(`Table data sample:`, table.data?.slice(0, 3))
    
    try {
      // Extract only this table's data from the full sheet
      const tableData = table.data
      
      // Create a minimal worksheet structure for this table only
      const tableWorksheet = {
        name: table.tableName,
        data: tableData,
        range: table.range
      }
      
      // Run auto-detection directly on the table data (not the full file buffer)
      const detectionResult = await autoDetectInstrumentFields(
        originalFileBuffer.value,
        event.sheetName,
        requiredColumns.value,
        event.instrumentType,
        table.range,
        tableData // Pass the table-specific data
      )

      console.log(`Detection result for ${table.tableName}:`, detectionResult)

      if (detectionResult && detectionResult.fields && Object.keys(detectionResult.fields).length > 0) {
        detectedInstruments.push({
          tableName: table.tableName,
          instrumentName: detectionResult.fields.Instrument || table.tableName,
          fields: detectionResult.fields,
          fieldsWithMetadata: detectionResult.fieldsWithMetadata,
          currencies: detectionResult.currencies || [],
          missingFields: detectionResult.missingFields || [],
          range: table.range
        })
      }
    } catch (error) {
      console.error(`Error detecting table ${table.tableName}:`, error)
    }
  }

  if (detectedInstruments.length > 0) {
    console.log('=== Multi-Table Detection Complete ===')
    console.log('Detected instruments:', detectedInstruments.length)
    
    // Store multi-table detection results
    multiTableDetectionResults.value = detectedInstruments
    
    // Show multi-table detection success popup
    showMultiTableDetectionSuccess.value = true
    
    // Close workbook viewer
    showWorkbookViewer.value = false
  } else {
    alert('Auto Detect could not identify required fields in any selected table. Please try manual entry.')
  }
}

// ================================================================
// useMultiTableDetectedFields
// ================================================================
function useMultiTableDetectedFields() {
  showMultiTableDetectionSuccess.value = false
  showWorkbookViewer.value = false

  console.log('=== Using Multi-Table Detected Fields ===')
  console.log('Number of tables:', multiTableDetectionResults.value.length)

  // Combine all detected fields from all tables into a single dataset
  const combinedFields = {}
  for (const instrument of multiTableDetectionResults.value) {
    console.log('Merging fields from table:', instrument.tableName, instrument.fields)
    // Merge all fields from this table into the combined object
    for (const [key, fieldObj] of Object.entries(instrument.fields)) {
      // Extract the actual value from the field object (which has { value, location, confidence })
      const actualValue = fieldObj?.value || fieldObj
      // If field already exists, keep the first one (or could merge differently based on requirements)
      if (!combinedFields[key]) {
        combinedFields[key] = actualValue
      }
    }
  }

  // Add instrument name from the first table or use worksheet name
  if (!combinedFields.Instrument && multiTableDetectionResults.value.length > 0) {
    combinedFields.Instrument = multiTableDetectionResults.value[0].instrumentName || 'Combined Instrument'
  }

  console.log('Combined fields from all tables:', combinedFields)
  console.log('Number of combined fields:', Object.keys(combinedFields).length)

  // Create single-row tabular data
  const tabularData = [combinedFields]

  // Set up for single-instrument workflow (since we're combining into one)
  rawData.value = tabularData
  originalRawData.value = JSON.parse(JSON.stringify(tabularData))
  cleanedData.value = JSON.parse(JSON.stringify(tabularData)) // Also set cleanedData to avoid fallback issues
  
  const headers = Object.keys(combinedFields)
  fileColumns.value = headers
  originalFileColumns.value = [...headers]
  
  worksheetSelected.value = true
  showPreview.value = true
  sheetType.value = 'single'
  mappingApplied.value = true
  
  // Set extracted values for single-instrument display
  extractedValues.value = combinedFields
  
  console.log('Combined table data applied to preview:', tabularData)
  console.log('Number of rows in tabularData:', tabularData.length)
  console.log('Headers:', headers)
}

// ================================================================
// formatDetectedValue
// ================================================================
function formatDetectedValue(field, value) {
  if (value === null || value === undefined) return '—'
  
  // Format dates
  if (field.toLowerCase().includes('date') || field.toLowerCase().includes('maturity')) {
    try {
      const date = new Date(value)
      if (!isNaN(date.getTime())) {
        return date.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
      }
    } catch {
      // Not a valid date, return as-is
    }
  }
  
  // Format percentages
  if (field.toLowerCase().includes('rate') || field.toLowerCase().includes('yield') || field.toLowerCase().includes('coupon') || field.toLowerCase().includes('discount')) {
    const num = parseFloat(value)
    if (!isNaN(num)) {
      return num.toFixed(2) + '%'
    }
  }
  
  // Format currency values
  if (field.toLowerCase().includes('value') || field.toLowerCase().includes('amount') || field.toLowerCase().includes('price') || field.toLowerCase().includes('principal')) {
    const num = parseFloat(value)
    if (!isNaN(num)) {
      return num.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
    }
  }
  
  return String(value)
}

// ================================================================
// useDetectedFields
// ================================================================
function useDetectedFields() {
  showDetectionSuccess.value = false
  showWorkbookViewer.value = false
  
  // Convert detected fields to the format expected by the preview
  extractedValues.value = autoDetectedFields.value
  
  // Add selected currency to extracted values if detected
  if (selectedCurrency.value) {
    extractedValues.value['Currency'] = selectedCurrency.value
  }
  
  // Create a single-row dataset for the preview
  const previewRow = {}
  for (const [key, value] of Object.entries(autoDetectedFields.value)) {
    previewRow[key] = value
  }
  
  // Add currency if selected
  if (selectedCurrency.value) {
    previewRow['Currency'] = selectedCurrency.value
  }
  
  rawData.value = [previewRow]
  originalRawData.value = JSON.parse(JSON.stringify([previewRow]))
  fileColumns.value = Object.keys(previewRow)
  originalFileColumns.value = [...fileColumns.value]
  
  worksheetSelected.value = true
  showPreview.value = true
  sheetType.value = 'single'
  mappingApplied.value = true
  
  console.log('Auto-detected fields applied to preview:', autoDetectedFields.value)
  console.log('Selected currency:', selectedCurrency.value)
}

function handleProcessSheetFromViewer(sheetName, sheetData, sheetHeaders) {
  console.log('Processing sheet from viewer:', sheetName)
  console.log('sheetData type:', typeof sheetData)
  console.log('sheetData length:', sheetData?.length)
  console.log('sheetData sample:', sheetData?.[0])
  console.log('Checking if sheetData contains objects:', sheetData?.[0] && typeof sheetData[0] === 'object')
  
  // Keep raw data as-is (may contain Excel cell objects)
  originalRawData.value = sheetData || []
  // Normalize for display - extract real cell values
  rawData.value = sheetData.map(row => {
    const normalized = {}
    for (const [key, value] of Object.entries(row)) {
      const extracted = getCellValue(value)
      normalized[key] = extracted
      // Debug: log if we still get an object
      if (typeof extracted === 'object' && extracted !== null) {
        console.log(`Warning: getCellValue returned object for ${key}:`, extracted)
      }
    }
    return normalized
  })
  
  fileColumns.value = sheetHeaders || []
  originalFileColumns.value = [...fileColumns.value]
  currentSheetName.value = sheetName
  worksheetSelected.value = true
  showPreview.value = true
  const detection = detectSheetType(sheetData, instrumentType.value)
  sheetType.value = detection.type
  if (detection.type === 'multi') {
    columnMapping.value = autoMatchColumns(fileColumns.value, requiredColumns.value, columnVariations.value)
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
  console.log(`Updated ${key}:`, value)
}

function clearExtractedValue(key) {
  extractedValues.value[key] = 'N/A'
  console.log(`Cleared ${key}`)
}

// NEW: Load worksheet statuses from session
async function loadWorksheetStatuses() {
  if (!activeSession.value?.id) return
  
  try {
    const worksheets = await sessionManager.getAllWorksheets(activeSession.value.id)
    worksheetStatuses.value = {}
    for (const [name, data] of Object.entries(worksheets)) {
      worksheetStatuses.value[name] = data.status || 'saved'
    }
    console.log('Loaded worksheet statuses:', worksheetStatuses.value)
  } catch (err) {
    console.error('Failed to load worksheet statuses:', err)
  }
}

// NEW: Mark current worksheet as saved
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

  const systemColumns = getInstrumentColumns(instrumentType)
  const firstRow = data[0]
  let matchCount = 0

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
  const allData = instrumentSummary.value.rows
  if (!allData.length) { return }

  const displayCols = getDisplayColumns()
  const data = allData.map(row => {
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

  const ws = XLSX.utils.json_to_sheet(data)
  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, ws, 'Instrument Summary')
  XLSX.writeFile(wb, `instrument_summary_${new Date().toISOString().split('T')[0]}.xlsx`)
}

function viewInstrumentSummaryExcel() {
  showInstrumentExcelPopup.value = true
  sortColumn.value = ''
  sortOrder.value = 'asc'
  console.log('Opening Instrument Summary Excel popup')
}

function closeInstrumentExcelPopup() {
  showInstrumentExcelPopup.value = false
}

function continueWorkingOnCurrent() {
  // Navigate to upload page to access workbook
  console.log('Navigating to upload page to continue on current sheet:', currentSheetName.value)
  switchTab('upload')
}

function chooseAnotherSheet() {
  // Navigate to upload page to access workbook
  console.log('Navigating to upload page to choose another sheet')
  switchTab('upload')
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
  
  // Round time fields to whole numbers
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

    // NEW: Aggregate all worksheets from session
    let allRows = [...rows]
    
    // Add rows from all saved worksheets in the session
    if (activeSession.value?.id) {
      sessionManager.getAllWorksheets(activeSession.value.id).then(worksheets => {
        console.log('Aggregating data from worksheets:', Object.keys(worksheets))
        
        for (const [worksheetName, worksheetData] of Object.entries(worksheets)) {
          if (worksheetData.instrumentSummary && worksheetData.instrumentSummary.rows) {
            // Add worksheet name to each row if not present
            const worksheetRows = worksheetData.instrumentSummary.rows.map(row => ({
              ...row,
              Worksheet: worksheetName
            }))
            allRows = [...allRows, ...worksheetRows]
          }
        }
        
        console.log('Total rows after aggregation:', allRows.length)
        
        // Create Excel with aggregated data
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
        // Fallback to current rows only
        exportCurrentRowsOnly(wb, displayCols, rows)
      })
    } else {
      // No session, export current rows only
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
    addToHistory(`${uploadedFile.value.name} - ${sheetData.sheetName}`, sheetData.data)
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
        // Apply same rounding logic as formatForExcel - time fields to whole numbers, others to 2 decimal places
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
  if (!instrumentSummary.value.rows.length) {
    return
  }

  const workbook = XLSX.utils.book_new()
  const columns = instrumentSummaryColumnsForDisplay.value
  const rows = sortedInstrumentSummaryRows.value

  // Create header row
  const data = [columns]

  // Add data rows with formatted values
  rows.forEach(row => {
    const dataRow = columns.map(col => {
      const value = row[col]
      return formatTableCell(value, col)
    })
    data.push(dataRow)
  })

  const worksheet = XLSX.utils.aoa_to_sheet(data)
  
  // Set column widths based on content type
  const columnWidths = columns.map(col => {
    const isNumeric = columns.some(c => c.toLowerCase().includes('value') || c.toLowerCase().includes('amount') || c.toLowerCase().includes('rate') || c.toLowerCase().includes('yield') || c.toLowerCase().includes('price'))
    const isDate = col.toLowerCase().includes('date')
    const isName = col.toLowerCase().includes('name') || col.toLowerCase().includes('instrument') || col.toLowerCase().includes('ticker')
    
    if (isNumeric) return { wch: 18 }
    if (isDate) return { wch: 14 }
    if (isName) return { wch: 25 }
    return { wch: 20 }
  })
  worksheet['!cols'] = columnWidths

  // Style the header row (first row)
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

  // Style data rows for alignment
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

  const fileName = `Calculated_Instruments_${activeSession.value?.name || 'Session'}_${new Date().toISOString().split('T')[0]}.xlsx`
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

// ===== FIXED: continueAfterUpload =====
async function continueAfterUpload() {
  if (!uploadedFile.value) { return }
  if (!rawData.value.length) { return }
  
  // No mandatory mapping check – user can proceed even if columns are not mapped.
  // They can always map later via the Map Columns button.
  
  saveSessionData()
  await nextTick()
  activeTab.value = 'cleaning'
  await nextTick()
  forceUpdate.value++
  debouncedSave()
  const sid = activeSession.value?.id || sessionManager.getActiveSessionId()
  if (sid) {
    await markStepCompleted(String(sid), 'upload')
    saveSessionData()
  }
}

// ===== FIXED: cleaning summary KPI stats =====
const cleaningResultStats = computed(() => {
  if (!cleaningStats.value || !cleanedData.value.length) return []
  return [
    { title: 'Original Rows', value: cleaningStats.value.totalRows || 0, icon: 'mdi-table-row', gradient: 'linear-gradient(135deg, #0B2044, #1a3a6e)' },
    { title: 'Cleaned Rows', value: cleanedData.value.length, icon: 'mdi-check-circle', gradient: 'linear-gradient(135deg, #4CAF50, #2E7D32)' },
    { title: 'Duplicates Removed', value: cleaningStats.value.removedRows || 0, icon: 'mdi-delete', gradient: 'linear-gradient(135deg, #F44336, #d32f2f)' },
    { title: 'Missing Values Fixed', value: cleaningStats.value.fixedMissing || 0, icon: 'mdi-pencil', gradient: 'linear-gradient(135deg, #FF9800, #F57C00)' }
  ]
})

// ===== NEW: cleaning operations performed summary =====
const cleaningOperationsSummary = computed(() => {
  if (!cleaningStats.value || !cleaningStats.value.operationsPerformed) return []
  return cleaningStats.value.operationsPerformed
})

function applyCleaning() {
  console.log('applyCleaning called')
  console.log('rawData.value.length:', rawData.value.length)
  console.log('cleanedData.value.length:', cleanedData.value.length)
  console.log('worksheetSelected.value:', worksheetSelected.value)
  console.log('currentSheetName.value:', currentSheetName.value)
  
  if (!rawData.value.length) {
    console.log('No raw data to clean')
    return
  }

  try {
    const tableDetection = autoDetectTable(rawData.value)
    let data = JSON.parse(JSON.stringify(rawData.value))
    const operations = []
    const originalLength = data.length

    console.log('Starting cleaning process with', originalLength, 'rows')
    console.log('Cleaning options:', cleaningOptions.value)

    if (tableDetection.type === 'table') {
      console.log('Cleaning raw table data')
      data = tableDetection.data
      operations.push('Auto-detected and extracted table data')
    }

    // Apply cleaning options...
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
      data = data.map(row => { Object.keys(row).forEach(k => { if (k.toLowerCase().includes('date') && row[k]) { const d = new Date(row[k]); if (!isNaN(d)) { row[k] = d.toISOString().split('T')[0]; standardized++ } } }); return row })
      if (standardized > 0) operations.push(`Standardized ${standardized} date values`)
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
    
    console.log('Cleaning completed. Cleaned rows:', cleanedData.value.length)
    console.log('Cleaning operations:', operations)
    
    debouncedSave()
    forceUpdate.value++
  } catch (error) {
    console.error('Error during cleaning:', error)
    showSnackbar('Error during cleaning: ' + error.message, 'error')
  }
}

// ===== FIXED: continueAfterCleaning =====
async function continueAfterCleaning() {
  if (!cleanedData.value.length) {
    return
  }
  
  // Navigate immediately, calculate metrics in background
  activeTab.value = 'calculations'
  await nextTick()
  forceUpdate.value++
  saveSessionData()
  const sid = activeSession.value?.id || sessionManager.getActiveSessionId()
  if (sid) {
    await markStepCompleted(String(sid), 'cleaning')
    saveSessionData()
  }
  
  // Calculate metrics in background without blocking UI
  calculateMetrics().catch(err => {
    console.error('Error calculating metrics:', err)
  })
}

// ===== FIXED: calculateMetrics with better error handling =====
async function calculateMetrics() {
  if (!cleanedData.value.length) {
    console.warn('No cleaned data to calculate')
    // Try to use rawData as fallback
    if (rawData.value.length) {
      console.log('Using rawData as fallback for calculations')
      cleanedData.value = JSON.parse(JSON.stringify(rawData.value))
    } else {
      return
    }
  }

  // Log the data being sent for debugging
  console.log('🔍 Sending data to backend:', {
    instrumentType: instrumentType.value,
    rowCount: cleanedData.value.length,
    sheetType: sheetType.value,
    sampleRow: cleanedData.value[0],
    columns: Object.keys(cleanedData.value[0] || {}),
    sessionId: activeSession.value?.id
  })

  try {
    const response = await api.calculationsAPI.executeByType(
      instrumentType.value,
      cleanedData.value,
      {
        country: effectiveCountry.value,
        currency: effectiveCurrency.value,
        maturity: effectiveMaturity.value,
        manualInputs: manualInputs.value
      },
      null,
      activeSession.value?.id
    )
    
      console.log('🔍 Backend response:', response)
      console.log('🔍 Response success:', response?.success)
      console.log('🔍 Response data:', response?.data)
      console.log('🔍 Response message:', response?.message)
      
      if (response?.success && response?.data) {
        calculations.value = response.data
        console.log('✅ Set calculations.value:', calculations.value)

        // Extract calculations array
        const calcArray = response.data.calculations || []
        console.log('🔍 Calculations array length:', calcArray.length)
        console.log('🔍 Calculations array:', calcArray)
        
        if (calcArray.length) {
          // Multiple instruments
          console.log('🔍 Processing multiple instruments')
          const rows = calcArray.map(calc => ({
            'Instrument Name': calc.instrument_name || 'Instrument',
            'Instrument Type': instrumentType.value,
            ...calc,
            'Worksheet': currentSheetName.value || 'Calculated'
          }))

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
          console.log('🔍 Updated instrumentSummary:', instrumentSummary.value)

          const agg = computeAggregate(mergedRows)
          const uniqueNames = new Set(mergedRows.map(r => r['Instrument Name']))
          // For single-instrument mode (multi-table combined), force count to 1
          agg.instrumentCount = sheetType.value === 'single' ? 1 : uniqueNames.size
          console.log('🔍 Computed aggregate:', agg)
          console.log('🔍 Instrument count set to:', agg.instrumentCount, '(sheetType:', sheetType.value + ')')

          allCalculations.value = agg
          selectedCalculations.value = agg
          console.log('🔍 Set allCalculations.value:', allCalculations.value)
          console.log('🔍 Set selectedCalculations.value:', selectedCalculations.value)
        } else {
          // Single instrument case - use aggregated values directly
          console.log('🔍 Processing single instrument case')
          const instrumentName = columnMapping.value['Instrument Name']
            ? (cleanedData.value[0]?.[columnMapping.value['Instrument Name']] || instrumentLabel.value)
            : instrumentLabel.value

          const summaryRow = {
            'Instrument Name': instrumentName,
            'Instrument Type': instrumentType.value,
            'Total Value': response.data.totalValue || 0,
            'total_value': response.data.totalValue || 0,
            'Instrument Count': response.data.instrumentCount || 0,
            'instrument_count': response.data.instrumentCount || 0,
            'Avg Rate': response.data.avgRate || 0,
            'avg_rate': response.data.avgRate || 0,
            'Weighted Avg Rate': response.data.weightedAvgRate || 0,
            'weighted_avg_rate': response.data.weightedAvgRate || 0,
            'Total Interest': response.data.totalInterest || 0,
            'total_interest': response.data.totalInterest || 0,
            'Interest Earned': response.data.interestEarned || 0,
            'interest_earned': response.data.interestEarned || 0,
            'Annual Yield': response.data.annualYield || 0,
            'annual_yield': response.data.annualYield || 0,
            'Effective Annual Rate': response.data.effectiveAnnualRate || 0,
            'effective_annual_rate': response.data.effectiveAnnualRate || 0,
            'Avg Days to Maturity': response.data.avgDaysToMaturity || 0,
            'avg_days_to_maturity': response.data.avgDaysToMaturity || 0,
            'Total Principal': response.data.totalPrincipal || 0,
            'total_principal': response.data.totalPrincipal || 0,
            'FRED Benchmark': response.data.fred?.benchmark_rate || null,
            'fred_benchmark': response.data.fred?.benchmark_rate || null,
            'Worksheet': currentSheetName.value || 'Calculated'
          }
          console.log('🔍 Created summaryRow:', summaryRow)

          const existingRows = instrumentSummary.value.rows || []
          const id = summaryRow['Instrument Name'] + '_' + (summaryRow['Worksheet'] || '')
          const exists = existingRows.some(r => (r['Instrument Name'] || '') + '_' + (r['Worksheet'] || '') === id)
          if (!exists) {
            instrumentSummary.value.rows.push(summaryRow)
            const allCols = new Set()
            instrumentSummary.value.rows.forEach(r => Object.keys(r).forEach(k => allCols.add(k)))
            instrumentSummary.value.columns = Array.from(allCols)
          }
          console.log('🔍 Updated instrumentSummary:', instrumentSummary.value)

          const agg = computeAggregate(instrumentSummary.value.rows)
          const uniqueNames = new Set(instrumentSummary.value.rows.map(r => r['Instrument Name']))
          // For single-instrument mode, force count to 1
          agg.instrumentCount = sheetType.value === 'single' ? 1 : uniqueNames.size
          console.log('🔍 Computed aggregate:', agg)
          console.log('🔍 Instrument count set to:', agg.instrumentCount, '(sheetType:', sheetType.value + ')')

          allCalculations.value = agg
          selectedCalculations.value = agg
          console.log('🔍 Set allCalculations.value:', allCalculations.value)
          console.log('🔍 Set selectedCalculations.value:', selectedCalculations.value)
        }

        console.log('🔍 Final state:', {
          allCalculations: allCalculations.value,
          selectedCalculations: selectedCalculations.value,
          instrumentSummary: instrumentSummary.value,
          calculationFields: calculationFields.value
        })
        saveSessionData()
      } else {
        // Show the actual error from the backend
        const errorMsg = response?.message || response?.error || 'Unknown error'
        console.error('❌ Backend calculation failed:', errorMsg)
        console.error('❌ Full response:', response)
        showSnackbar('Calculation failed: ' + errorMsg, 'error')
      }
    } catch (err) {
      console.error('❌ Error calling backend calculation:', err)
      console.error('❌ Error details:', err.message)
      console.error('❌ Error stack:', err.stack)
      showSnackbar('Error calculating metrics: ' + (err.message || 'Unknown error'), 'error')
    }
  await enrichCalculationsWithFred()
  debouncedSave()
  forceUpdate.value++
}

// ===== continueToVisualizations =====
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
    saveSessionData()
  }
}

// ===== continueFromVisualizations =====
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
    saveSessionData()
  }
}

const yieldCurveCache = new Map()
const CACHE_TTL = 15 * 60 * 1000

// ================================================================
// fetchYieldCurve – uses real FRED data only
// ================================================================
async function fetchYieldCurve() {
  const country = effectiveCountry.value
  const maturity = effectiveMaturity.value
  const currency = effectiveCurrency.value || 'USD'

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
  if (!maturity) {
    yieldCurveError.value = 'Please select a maturity.'
    yieldCurveData.value = []
    await nextTick()
    await renderYieldCurveChart()
    return
  }

  const cacheKey = `${instrumentType.value}_${normalizedCountry}_${currency}_${maturity}`
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
    console.log('Fetching yield curve from FRED endpoint:', { instrument_type: instrumentType.value, country: normalizedCountry, currency, maturity })
    const response = await api.fredAPI.getYieldCurve({
      instrument_type: instrumentType.value,
      country: normalizedCountry,
      currency: currency,
      maturity: maturity
    })
    console.log('FRED yield curve response:', response)

    if (response?.success && response.data) {
      const curveData = response.data
      if (curveData.maturities && curveData.maturities.length) {
        const points = curveData.maturities.map((m, idx) => ({
          maturity: parseFloat(m),
          maturityLabel: curveData.labels?.[idx] || m,
          rate: curveData.rates?.[idx] || 0
        }))
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

// ===== renderYieldCurveChart with dynamic x-axis labels =====
async function renderYieldCurveChart() {
  if (!yieldCurveChart.value || !yieldCurveData.value.length) {
    if (chartInstanceRef.current) {
      chartInstanceRef.current.destroy()
      chartInstanceRef.current = null
    }
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

  const transformed = filteredData.map(d => {
    let xVal = d.maturity
    if (unitLabel === 'Months') xVal = d.maturity * 12
    else if (unitLabel === 'Weeks') xVal = d.maturity * 52
    return { x: xVal, y: d.rate, label: d.maturityLabel }
  })

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
        x: {
          type: 'linear',
          title: { display: true, text: unitLabel },
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
        },
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
    fredFilters.value.country = customCountryInput.value || 'USA'
  }
  onFredFilterChange()
}

function onCurrencySelectChange() {
  if (selectedCurrencyOption.value !== '__custom__') {
    fredFilters.value.currency = selectedCurrencyOption.value
  } else {
    fredFilters.value.currency = customCurrencyInput.value || 'USD'
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

function loadSavedTemplates() {
  const key = `${instrumentType.value}_mapping_templates`
  const saved = localStorage.getItem(key)
  savedTemplates.value = saved ? JSON.parse(saved) : {}
}

function saveTemplates() {
  const key = `${instrumentType.value}_mapping_templates`
  localStorage.setItem(key, JSON.stringify(savedTemplates.value))
}

function saveCurrentMappingAsTemplate() {
  if (!newTemplateName.value) {
    return
  }
  const hasAnyMapping = requiredColumns.value.some(col => columnMapping.value[col])
  if (!hasAnyMapping) {
    return
  }
  savedTemplates.value[newTemplateName.value] = {
    columnMapping: columnMapping.value,
    requiredColumns: requiredColumns.value,
    fileColumns: fileColumns.value,
    savedAt: new Date().toISOString()
  }
  saveTemplates()
  newTemplateName.value = ''
}

function applyTemplate() {
  if (!selectedTemplate.value) return
  const template = savedTemplates.value[selectedTemplate.value]
  if (!template) return
  columnMapping.value = { ...template.mapping }
  applyCurrentMapping()
  debouncedSave()
  forceUpdate.value++
}

function deleteTemplate() {
  if (!selectedTemplate.value) return
  if (confirm(`Delete template "${selectedTemplate.value}"?`)) {
    delete savedTemplates.value[selectedTemplate.value]
    saveTemplates()
    selectedTemplate.value = ''
  }
}

function loadTemplateFromPopup(name) {
  selectedTemplate.value = name
  applyTemplate()
  showSavedMappingsDialog.value = false
}

function deleteTemplateFromPopup(name) {
  if (confirm(`Delete template "${name}"?`)) {
    delete savedTemplates.value[name]
    saveTemplates()
    if (selectedTemplate.value === name) selectedTemplate.value = ''
  }
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
  const agg = computeAggregate(instrumentSummary.value.rows)
  allCalculations.value = agg
  selectedCalculations.value = agg
  calculations.value = agg
  currentlyViewingInstrument.value = null
  closeAllCalculationsPopup()
  saveSessionData()
}

function formatTableCell(value, column) {
  if (value === null || value === undefined || value === '') return '—'
  
  // Check if this is a time field (days, months, years, maturity, duration, term, week, time)
  const isTimeField = column.toLowerCase().includes('day') || column.toLowerCase().includes('maturity') || column.toLowerCase().includes('duration') || column.toLowerCase().includes('term') || column.toLowerCase().includes('month') || column.toLowerCase().includes('year') || column.toLowerCase().includes('week') || column.toLowerCase().includes('time')
  
  if (isTimeField && typeof value === 'number') {
    return formatNumber(value, true)
  }
  
  if (isPercentageField(column)) {
    return formatNumber(value) + '%'
  }
  if (column.toLowerCase().includes('value') || column.toLowerCase().includes('amount') || column.toLowerCase().includes('price')) {
    return '$' + formatNumber(value)
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
  const allData = instrumentSummary.value.rows
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

// ================================================================
// saveToSession – with version creation and refresh
// ================================================================
const isSaving = ref(false)
const skipAutoSave = ref(false)

// Track previous state for change detection
const previousSnapshot = ref(null)

// Generate dynamic version description based on changes
function generateVersionDescription(newSnapshot, oldSnapshot) {
  const changes = []
  
  if (!oldSnapshot) {
    return `Initial ${instrumentType.value} workflow setup`
  }
  
  // Check for data changes
  if (JSON.stringify(newSnapshot.rawData) !== JSON.stringify(oldSnapshot.rawData)) {
    changes.push('uploaded new data')
  }
  
  // Check for cleaning changes
  if (JSON.stringify(newSnapshot.cleanedData) !== JSON.stringify(oldSnapshot.cleanedData)) {
    changes.push('cleaned data')
  }
  
  // Check for calculation changes
  if (JSON.stringify(newSnapshot.calculations) !== JSON.stringify(oldSnapshot.calculations)) {
    changes.push('recalculated metrics')
  }
  
  // Check for mapping changes
  if (JSON.stringify(newSnapshot.columnMapping) !== JSON.stringify(oldSnapshot.columnMapping)) {
    changes.push('updated column mapping')
  }
  
  // Check for manual input changes
  if (JSON.stringify(newSnapshot.manualInputs) !== JSON.stringify(oldSnapshot.manualInputs)) {
    changes.push('updated manual inputs')
  }
  
  // Check for formula changes
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
  // Strict version creation guard - prevent duplicate execution
  if (isSavingVersion) {
    console.log('Version save already in progress, ignoring duplicate click')
    return
  }
  
  isSavingVersion = true
  isSaving.value = true
  skipAutoSave.value = true
  console.log('=== saveToSession START ===')
  console.log('Session ID:', activeSession.value?.id)
  console.log('Current version count BEFORE save:', activeSession.value?.version_count)
  console.log('Current worksheet:', currentSheetName.value)
  
  if (!activeSession.value || !activeSession.value.id) {
    isSavingVersion = false
    isSaving.value = false
    skipAutoSave.value = false
    return
  }

  const sid = activeSession.value.id
  const worksheetName = currentSheetName.value || 'Unknown'

  try {
    // First, fetch the ACTUAL current version count from database
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

    // NEW: Save worksheet data to session (for multi-worksheet support)
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
    
    // Mark current worksheet as saved
    markWorksheetAsSaved()

    // Step 1: Save workflow data (NO version creation)
    console.log('Step 1: Saving workflow data...')
    await sessionManager.saveInstrumentWorkflow(sid, instrumentType.value, datasetSnapshot)
    console.log('Step 1 complete: Workflow data saved')
    
    // Step 2: Update instrument count (NO version creation)
    console.log('Step 2: Updating instrument count...')
    const count = sessionManager.countSessionInstruments(sid)
    await sessionManager.updateSession(sid, { instrument_count: Math.min(count, 3) })
    
    if (activeSession.value?.id === sid) {
      activeSession.value.instrument_count = Math.min(count, 3)
    }
    console.log('Step 2 complete: Instrument count updated to:', Math.min(count, 3))
    
    // Step 3: Create EXACTLY ONE version via API
    console.log('Step 3: Creating version via API...')
    
    // Generate dynamic description based on actual changes
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
      
      // Update previous snapshot for next save comparison
      previousSnapshot.value = JSON.parse(JSON.stringify(datasetSnapshot))
      
      // Step 4: Fetch updated version count from backend (READ ONLY)
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
          
          console.log('=== saveToSession COMPLETE ===')
          console.log('Final version count:', updatedVersionCount)
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
    // Re-enable skip flag after delay
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
  console.log('refreshSessionVersionCount called with sid:', sid)
  try {
    const updated = await sessionManager.getSession(sid, true)
    console.log('Session refresh returned:', updated)
    console.log('Session has ID?', updated?.id)
    // Only update if the returned session has a valid ID
    if (updated && updated.id && activeSession.value?.id === sid) {
      activeSession.value = updated
      console.log('Session refreshed, version_count =', updated.version_count)
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
  // Do NOT create versions here - only saveToSession should create versions
  // This function is for auto-saving workflow data only
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
    yieldCurveData: yieldCurveData.value,
    fredFilters: { country: effectiveCountry.value, currency: effectiveCurrency.value, maturity: effectiveMaturity.value },
    uploadedFile: uploadedFile.value?.name || null,
    cleaningStats: cleaningStats.value,
    sessionSavedAt: sessionSavedAt.value || new Date().toISOString(),
    manualInputs: manualInputs.value,
    formulas: formulas.value
  }
  
  // Save workflow data only - NO version creation
  sessionManager.saveInstrumentWorkflow(sid, instrumentType.value, datasetSnapshot)
    .then(() => {
      // Only update instrument count on explicit save, but NO version creation
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
      yieldCurveData.value = wf.yieldCurveData || []
      manualInputs.value = wf.manualInputs || {}
      formulas.value = wf.formulas || {}
      if (wf.fredFilters) {
        selectedCountryOption.value = wf.fredFilters.country || 'USA'
        selectedCurrencyOption.value = wf.fredFilters.currency || 'USD'
        selectedMaturityOption.value = wf.fredFilters.maturity || config.value.defaultMaturity
      }
      if (wf.uploadedFile) {
        uploadedFile.value = { name: wf.uploadedFile, size: 0 }
      }
      if (wf.cleaningStats) cleaningStats.value = wf.cleaningStats
      if (wf.sessionSavedAt) sessionSavedAt.value = wf.sessionSavedAt
      loaded = true

      if (instrumentSummary.value.rows.length && !allCalculations.value.totalValue) {
        allCalculations.value = computeAggregate(instrumentSummary.value.rows)
        selectedCalculations.value = allCalculations.value
        calculations.value = allCalculations.value
      }
    }
  } catch (err) {
    console.error('Failed to load saved data:', err)
  }
  return loaded
}

function showFormula(metricKey) {
  const formulaMap = {
    // Money Market Formulas
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
    
    // T-Bills Formulas
    'weightedAvgDiscount': 'Σ (Discount Rate × Face Value) / Σ Face Value',
    'totalDiscount': 'Σ ((Face Value - Purchase Price) / Face Value × Face Value)',
    'effectiveYield': '((Face Value / Purchase Price)^(365/Days) - 1) × 100',
    'bondEquivalentYield': '((Face Value - Purchase Price) / Purchase Price) × (365 / Days) × 100',
    'pricePer100': 'Purchase Price / Face Value × 100',
    'totalPurchasePrice': 'Σ Purchase Price',
    'avgInvestment': 'Total Purchase Price / Number of Instruments',
    'holdingPeriodYield': '((Face Value - Purchase Price) / Purchase Price) × 100',
    'annualizedYield': '((Face Value - Purchase Price) / Purchase Price) × (365 / Days) × 100',
    
    // Bonds Formulas
    'weightedAvgCoupon': 'Σ (Coupon Rate × Face Value) / Σ Face Value',
    'totalAnnualIncome': 'Σ (Coupon Rate × Face Value)',
    'avgYTM': 'Σ Yield to Maturity / Number of Instruments',
    'duration': 'Macaulay Duration = Σ (t × PV(C_t)) / Price'
  }
  formulaText.value = formulaMap[metricKey] || 'No formula available for this metric.'
  formulaDialog.value = true
}

function selectAllInstruments() { selectedInstruments.value = { moneyMarket: true, bonds: true, tbills: true } }
function deselectAllInstruments() { selectedInstruments.value = { moneyMarket: false, bonds: false, tbills: false } }

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
  
  // NEW: Aggregate data from all worksheets in session
  let allSummaryRows = [...(instrumentSummary.value.rows || [])]
  
  // Add rows from all saved worksheets in the session
  if (activeSession.value?.id) {
    sessionManager.getAllWorksheets(activeSession.value.id).then(worksheets => {
      console.log('Aggregating report data from worksheets:', Object.keys(worksheets))
      
      for (const [worksheetName, worksheetData] of Object.entries(worksheets)) {
        if (worksheetData.instrumentSummary && worksheetData.instrumentSummary.rows) {
          // Add worksheet name to each row if not present
          const worksheetRows = worksheetData.instrumentSummary.rows.map(row => ({
            ...row,
            Worksheet: worksheetName
          }))
          allSummaryRows = [...allSummaryRows, ...worksheetRows]
        }
      }
      
      console.log('Total rows after aggregation for report:', allSummaryRows.length)
    }).catch(err => {
      console.error('Failed to aggregate worksheets for report:', err)
    })
  }
  
  for (const type of instrumentTypes) {
    const key = type.key
    const selected = selectedInstruments.value[key]
    if (selected) {
      const data = getInstrumentData(key)
      if (data && data.totalValue > 0) {
        instrumentsData.push({ name: type.label, calculations: data, id: key })
      }
    }
  }
  
  // Use aggregated summary rows if no instrument data found
  if (instrumentsData.length === 0 && allSummaryRows.length > 0) {
    const summaryRows = allSummaryRows
    const grouped = {}
    summaryRows.forEach(row => {
      const type = row['Instrument Type'] || 'unknown'
      if (!grouped[type]) grouped[type] = []
      grouped[type].push(row)
    })
    for (const [type, rows] of Object.entries(grouped)) {
      let totalValue = 0, instrumentCount = rows.length, totalAvgRate = 0
      rows.forEach(row => {
        const value = parseFloat(row['Total Value'] || row['total_value'] || row['Calculated Value'] || row['calculated_value'] || 0)
        const rate = parseFloat(row['Avg Rate'] || row['avg_rate'] || row['Coupon Rate'] || row['coupon_rate'] || row['Discount Rate'] || row['discount_rate'] || 0)
        if (!isNaN(value)) totalValue += value
        if (!isNaN(rate)) totalAvgRate += rate
      })
      const avgRate = instrumentCount > 0 ? totalAvgRate / instrumentCount : null
      const nameMap = { 'money-market': 'Money Market', 'bonds': 'Bonds', 'tbills': 'T-Bills' }
      instrumentsData.push({
        name: nameMap[type] || type,
        calculations: {
          totalValue,
          instrumentCount,
          avgRate,
          avgCouponRate: type === 'bonds' ? avgRate : null,
          avgDiscountRate: type === 'tbills' ? avgRate : null
        }
      })
    }
  }
  return { 
    session: activeSession.value?.name || 'No session', 
    date: new Date().toLocaleString(), 
    instruments: instrumentsData,
    chartImage: chartImageData.value,
    fredFilters: { country: effectiveCountry.value, currency: effectiveCurrency.value, maturity: effectiveMaturity.value },
    yieldCurveData: yieldCurveData.value
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
    pricePer100: 'Price per $100', totalPurchasePrice: 'Total Purchase Price',
    avgInvestment: 'Avg Investment', holdingPeriodYield: 'Holding Period Yield',
    annualizedYield: 'Annualized Yield'
  }
  return names[key] || key.replace(/([A-Z])/g, ' $1').replace(/^./, str => str.toUpperCase())
}

function formatMetricValue(key, value) {
  if (typeof value === 'number') {
    const rounded = Math.round(value * 100) / 100
    if (key.includes('Value') || key.includes('Price') || key.includes('Interest') || key.includes('Income') || key.includes('Discount') || key.includes('Principal') || key.includes('Investment'))
      return `$${rounded.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
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
  
  // Load yield curve data from session workflow if not already loaded
  const session = activeSession.value
  console.log('Loading yield curve data for report. Session:', session, 'Instrument type:', instrumentType.value)
  if (session && session.id) {
    try {
      const wf = await sessionManager.getInstrumentWorkflow(session.id, instrumentType.value)
      console.log('Workflow data from session:', wf)
      if (wf && wf.yieldCurveData && wf.yieldCurveData.length > 0) {
        console.log('Loading yield curve data from session workflow:', wf.yieldCurveData.length, 'points')
        yieldCurveData.value = wf.yieldCurveData
        if (wf.fredFilters) {
          effectiveCountry.value = wf.fredFilters.country
          effectiveCurrency.value = wf.fredFilters.currency
          effectiveMaturity.value = wf.fredFilters.maturity
          console.log('Loaded FRED filters:', wf.fredFilters)
        }
      } else {
        console.log('No yield curve data found in session workflow')
      }
    } catch (e) {
      console.warn('Failed to load yield curve data from session workflow:', e)
    }
  } else {
    console.log('No session available to load yield curve data')
  }
  
  const report = reportPreviewData.value
  if (report.instruments.length === 0) {
    return null
  }

  console.log('Generating report with yield curve data:', yieldCurveData.value.length, 'points')
  console.log('Chart series label:', chartSeriesLabel.value)
  console.log('Current chart image data:', chartImageData.value ? 'exists' : 'empty')

  // If no chart image exists and we have yield curve data, try to render and capture
  let imageData = chartImageData.value
  if (!imageData && yieldCurveData.value.length > 0) {
    console.log('No chart image found, attempting to render and capture...')
    try {
      // Switch to visualizations tab temporarily to render chart
      const previousTab = activeTab.value
      activeTab.value = 'visualizations'
      await nextTick()
      
      // Wait for chart to render
      await new Promise(resolve => setTimeout(resolve, 1500))
      
      // Try to capture the chart
      if (yieldCurveChart.value) {
        imageData = yieldCurveChart.value.toDataURL('image/png', 1.0)
        chartImageData.value = imageData
        console.log('Chart captured after rendering:', imageData ? 'success' : 'failed')
      }
      
      // Switch back to previous tab
      activeTab.value = previousTab
      await nextTick()
    } catch (e) {
      console.warn('Chart capture failed:', e)
    }
  }

  const valuationDate = new Date().toISOString().split('T')[0]
  const totalPortfolioValue = report.instruments.reduce((sum, inst) => sum + (parseFloat(inst.calculations.totalValue) || 0), 0)
  const totalInstrumentCount = report.instruments.reduce((sum, inst) => sum + (parseInt(inst.calculations.instrumentCount) || 0), 0)

  const yieldPoints = yieldCurveData.value || []
  console.log('Yield points for report:', yieldPoints.length)
  
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

  const methodologyHtml = buildMethodologySection(report.instruments.map(i => i.name))
  const chartHtml = imageData ? `
    <div class="chart-container">
      <img src="${imageData}" alt="Yield Curve" style="max-width:100%; height:auto; border-radius:8px; border:1px solid #e0e0e0;" />
      <p class="chart-caption">FRED Yield Curve – ${chartSeriesLabel.value || report.instruments.map(i => i.name).join(', ')} (${effectiveCountry.value || 'USA'} / ${effectiveCurrency.value || 'USD'})</p>
    </div>
  ` : (yieldPoints.length ? `
    <div class="chart-container">
      <p><strong>Yield Curve Data:</strong> ${chartSeriesLabel.value || 'FRED Yield Curve'}</p>
      <p><strong>Country:</strong> ${effectiveCountry.value || 'USA'} | <strong>Currency:</strong> ${effectiveCurrency.value || 'USD'} | <strong>Maturity:</strong> ${effectiveMaturity.value || 'N/A'}</p>
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
    .cover-logo img { max-width: 140px; height: auto; background: white; padding: 4px; }
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
      <li>Total Portfolio Value: <span class="highlight">$${totalPortfolioValue.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</span></li>
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
          <td>$${(inst.calculations.totalValue || 0).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
          <td>${inst.calculations.instrumentCount || 0}</td>
          <td>${inst.calculations.avgRate || inst.calculations.avgCouponRate || inst.calculations.avgDiscountRate || 0}%</td>
          <td>${inst.calculations.weightedAvgRate || inst.calculations.weightedAvgCoupon || inst.calculations.weightedAvgDiscount || 0}%</td>
        </tr>
      `).join('')}
      <tr style="font-weight:700;background:#f0f2f5;">
        <td><strong>Total Portfolio</strong></td>
        <td><strong>$${totalPortfolioValue.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</strong></td>
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
  <p><strong>Country:</strong> ${effectiveCountry.value || 'USA'}</p>
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
    // Open in new window to avoid navbar
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
  const valuationDate = new Date().toISOString().split('T')[0]

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
    ['Asset Class', 'Instrument Name', 'BB Ticker', 'Face Value ($)', 'Rate (%)', 'Term (Yrs)', 'Valuation Date']
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
  else if (format === 'word') downloadBlob(html, `${filename}.doc`, 'application/msword')
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
    console.log('Skipping auto-save - disabled or save in progress')
    return
  }
  debouncedSave()
}, { deep: true })
watch(cleanedData, async (newVal) => { if (newVal.length) await calculateMetrics() }, { deep: true })

watch(() => activeTab.value, async (newTab) => {
  if (newTab === 'calculations' && hasCleanedData.value) {
    await calculateMetrics()
  }
  if (newTab === 'visualizations' && hasCleanedData.value && !yieldCurveData.value.length && !yieldCurveLoading.value) {
    if (!effectiveCountry.value) { selectedCountryOption.value = 'USA'; fredFilters.value.country = 'USA' }
    if (!effectiveMaturity.value) { const def = config.value.defaultMaturity; selectedMaturityOption.value = def; fredFilters.value.maturity = def }
    await fetchYieldCurve()
  }
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
    const s = await sessionManager.getSession(String(qSid), true) // Force refresh from backend
    if (s) {
      // Fetch actual version count from database
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
      // Force refresh and fetch actual version count
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
      } else {
        activeSession.value = current
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
  loadSavedTemplates()
  window.addEventListener('storage', () => checkAndReset())
  await loadFilterOptions()
  if (!effectiveMaturity.value) {
    const def = config.value.defaultMaturity
    selectedMaturityOption.value = def
    fredFilters.value.maturity = def
  }
  if (Object.keys(allCalculations.value).length) enrichCalculationsWithFred()
  if (!allCalculations.value.totalValue && activeSession.value) await loadSavedData()
  if (cleanedData.value.length) await calculateMetrics()
  debouncedSave()

  if (instrumentSummary.value.rows.length && !allCalculations.value.totalValue) {
    allCalculations.value = computeAggregate(instrumentSummary.value.rows)
    selectedCalculations.value = allCalculations.value
    calculations.value = allCalculations.value
  }
})

// Listen for session-restored events from Dashboard (defined outside onMounted for cleanup)
const handleSessionRestored = async (event) => {
  const { sessionId } = event.detail || {}
  if (sessionId && activeSession.value?.id === sessionId) {
    console.log('Session restored, reloading data...')
    await loadSavedData()
    await refreshSessionVersionCount(sessionId)
    forceUpdate.value++
  }
}

onMounted(async () => {
  const qSid = route.query.session
  if (qSid) {
    const s = await sessionManager.getSession(String(qSid))
    if (s) {
      activeSession.value = s
      sessionManager.setActiveSession(s)
    }
  }
  if (!activeSession.value) {
    const current = sessionManager.getActiveSession()
    if (current) activeSession.value = current
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
  loadSavedTemplates()
  window.addEventListener('storage', () => checkAndReset())
  await loadFilterOptions()
  if (!effectiveMaturity.value) {
    const def = config.value.defaultMaturity
    selectedMaturityOption.value = def
    fredFilters.value.maturity = def
  }
  if (Object.keys(allCalculations.value).length) enrichCalculationsWithFred()
  if (!allCalculations.value.totalValue && activeSession.value) await loadSavedData()
  if (cleanedData.value.length) await calculateMetrics()
  debouncedSave()

  window.addEventListener('session-restored', handleSessionRestored)

  if (instrumentSummary.value.rows.length && !allCalculations.value.totalValue) {
    allCalculations.value = computeAggregate(instrumentSummary.value.rows)
    selectedCalculations.value = allCalculations.value
    calculations.value = allCalculations.value
  }
})

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
.mapping-select { flex: 1; padding: 8px 36px 8px 12px; border: 1px solid #ccc; border-radius: 6px; font-size: 14px; background: white; cursor: pointer; appearance: none; -webkit-appearance: none; background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 8'%3E%3Cpath d='M1 1l5 5 5-5' stroke='%23999' stroke-width='1.5' fill='none'/%3E%3C/svg%3E"); background-repeat: no-repeat; background-position: right 12px center; padding-right: 36px; }
.mapping-select:focus { outline: none; border-color: #0B2044; box-shadow: 0 0 0 2px rgba(11,32,68,0.2); }
.saved-mappings-popup-title { background: #0B2044; color: white; padding: 16px 24px; }
.save-section { margin-bottom: 20px; }
.save-row { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
.save-row .template-input { flex: 1; padding: 8px 12px; border: 1px solid #ccc; border-radius: 6px; font-size: 14px; min-width: 150px; }
.saved-list { max-height: 300px; overflow-y: auto; border-top: 1px solid #e8ecf1; padding-top: 12px; }
.saved-item { display: flex; justify-content: space-between; align-items: center; padding: 10px 12px; border-bottom: 1px solid #eee; flex-wrap: wrap; gap: 8px; }
.template-info { display: flex; flex-direction: column; gap: 2px; }
.template-name { font-weight: 600; color: #0B2044; }
.template-timestamp { font-size: 12px; color: #999; }
.template-actions { display: flex; gap: 8px; flex-wrap: wrap; }
.btn-secondary.small, .btn-danger.small { padding: 4px 10px; font-size: 12px; border-radius: 4px; border: none; cursor: pointer; }
.btn-secondary.small { background: #e0e0e0; color: #333; }
.btn-secondary.small:hover { background: #c0c0c0; }
.btn-danger.small { background: #f44336; color: white; }
.btn-danger.small:hover { background: #d32f2f; }
.empty-saved { text-align: center; color: #999; padding: 20px 0; }
.excel-dialog-title-no-logo { background: #f5f5f5; color: #0B2044; padding: 12px 24px; display: flex; align-items: center; border-bottom: 2px solid #d0d0d0; }
.excel-dialog-title-no-logo span { font-weight: 600; font-size: 18px; }
.btn-work-on-sheet { background: #0B2044; color: white; border: none; padding: 8px 20px; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; transition: all 0.2s; margin-right: 12px; }
.btn-work-on-sheet:hover { background: #1a3a6e; transform: translateY(-1px); box-shadow: 0 4px 12px rgba(11,32,68,0.2); }
.btn-auto-detect { background: #4CAF50; color: white; border: none; padding: 8px 20px; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; transition: all 0.2s; margin-right: 12px; }
.btn-auto-detect:hover { background: #45a049; transform: translateY(-1px); box-shadow: 0 4px 12px rgba(76,175,80,0.3); }
.detection-success-title { background: #4CAF50; color: white; padding: 16px 24px; display: flex; align-items: center; }
.detection-success-body { padding: 20px 24px; }
.currency-selection-section { margin-bottom: 20px; padding: 16px; background: #f8f9ff; border-radius: 8px; border: 1px solid #e8ecf1; }
.currency-label { display: block; font-weight: 600; color: #0B2044; margin-bottom: 8px; font-size: 14px; }
.currency-select { width: 100%; padding: 10px 12px; border: 1px solid #ccc; border-radius: 6px; font-size: 14px; background: white; cursor: pointer; }
.currency-select:focus { outline: none; border-color: #4CAF50; box-shadow: 0 0 0 2px rgba(76,175,80,0.2); }
.detected-fields-list { display: flex; flex-direction: column; gap: 12px; margin-bottom: 16px; }
.detected-field-item { display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; background: #f8f9ff; border-radius: 8px; border-left: 4px solid #4CAF50; }
.detected-field-label { font-weight: 600; color: #0B2044; font-size: 14px; }
.detected-field-value { font-weight: 700; color: #2E7D32; font-size: 15px; }
.detected-field-location { font-size: 11px; color: #999; font-style: italic; margin-left: 8px; }
.missing-fields-warning { padding: 12px 16px; background: #FFF3E0; border-radius: 8px; border-left: 4px solid #FF9800; }
.missing-fields-warning p { margin: 0 0 8px 0; font-weight: 600; color: #E65100; font-size: 14px; }
.missing-fields-warning ul { margin: 0; padding-left: 20px; }
.missing-fields-warning li { color: #E65100; font-size: 13px; margin-bottom: 4px; }

.multi-table-summary { padding: 12px 16px; background: #e8f5e9; border-radius: 8px; border-left: 4px solid #4CAF50; margin-bottom: 16px; font-size: 14px; color: #2E7D32; }

.multi-instruments-list { display: flex; flex-direction: column; gap: 16px; max-height: 400px; overflow-y: auto; }

.multi-instrument-item { padding: 16px; background: #f8f9ff; border-radius: 8px; border: 1px solid #e8ecf1; }

.multi-instrument-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid #e0e0e0; }

.table-name-badge { background: #0B2044; color: white; padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: 500; }

.multi-instrument-fields { display: flex; flex-direction: column; gap: 8px; margin-bottom: 12px; }

.multi-detected-field-item { display: flex; justify-content: space-between; align-items: center; padding: 8px 12px; background: white; border-radius: 6px; border-left: 3px solid #4CAF50; }

.multi-detected-field-label { font-weight: 600; color: #0B2044; font-size: 13px; }

.multi-detected-field-value { font-weight: 700; color: #2E7D32; font-size: 14px; }

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

.value-input {
  width: 100%;
  padding: 6px 10px;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  font-size: 13px;
  font-family: inherit;
  background: white;
  transition: border-color 0.2s;
}

.value-input:focus {
  outline: none;
  border-color: #0B2044;
  box-shadow: 0 0 0 2px rgba(11, 32, 68, 0.1);
}

.value-input.placeholder {
  color: #999;
  font-style: italic;
}

.btn-clear-value {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  background: #f44336;
  color: white;
  border: none;
  border-radius: 50%;
  width: 20px;
  height: 20px;
  font-size: 14px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
  opacity: 0.7;
  transition: opacity 0.2s;
}

.btn-clear-value:hover {
  opacity: 1;
}

.row-value {
  position: relative;
  display: flex;
  align-items: center;
  flex: 1;
}
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
.formula-text { font-size: 16px; padding: 16px; background: #f8f9ff; border-radius: 8px; margin-top: 8px; }
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