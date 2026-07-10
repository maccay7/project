<template>
  <FixedLayout>
    <div class="instrument-page">
      <!-- Page Header – Simplified -->
      <div class="page-header">
        <div class="header-left">
          <h1>{{ instrumentName }}</h1>
          <div v-if="activeSession" class="session-badge">
            <strong>{{ activeSession.name }}</strong>
          </div>
          <div v-else class="session-badge warning">
            No active session – please select a session from Dashboard
          </div>
        </div>
        <div class="header-right">
          <button v-if="activeSession" class="btn-save-session" @click="saveToSession" title="Save a version to session history">
            Save to Session
          </button>
          <div class="step-indicator">
            Step {{ currentStepIndex + 1 }} of {{ totalSteps }}
          </div>
        </div>
      </div>

      <!-- Progress Bar -->
      <div class="progress-bar-container">
        <div class="progress-steps">
          <div
            v-for="(step, index) in steps"
            :key="step.tab"
            class="progress-step"
            :class="{
              active: activeTab === step.tab,
              completed: isStepComplete(step.tab),
              disabled: index > farthestAllowedIndex
            }"
            @click="switchTab(step.tab)"
          >
            <div class="step-circle">{{ index + 1 }}</div>
            <div class="step-label">{{ step.name }}</div>
          </div>
        </div>
      </div>

      <!-- Tab content -->
      <div class="tab-content">
        <!-- ===== UPLOAD ===== -->
        <div v-if="activeTab === 'upload'" class="content-card">
          <v-card>
            <v-card-title>Upload {{ instrumentName }} Dataset</v-card-title>
            <v-card-text>
              <div class="upload-area" @dragover.prevent @drop.prevent="handleDrop">
                <input
                  type="file"
                  ref="fileInput"
                  @change="handleFileUpload"
                  accept=".csv,.xlsx,.xls,.xlsm,.xlsb,.xltx,.xltm,.xlam,.ods,.xml,.html,.prn,.dif,.slk,.dbf"
                  style="display: none"
                >
                <p>Drag & drop or <span class="browse-link" @click="$refs.fileInput.click()">browse</span></p>
                <small>Supported: CSV, Excel (including .xlsm, .xlsb, .ods), and many other spreadsheet formats</small>
              </div>

              <!-- Upload History -->
              <div v-if="uploadHistory.length" class="upload-history">
                <h4>Upload History ({{ uploadHistory.length }} files)</h4>
                <div class="history-list">
                  <div v-for="(item, idx) in uploadHistory" :key="idx" class="history-item" @click="loadHistoryFile(item)">
                    <span>{{ item.name }}</span>
                    <small>{{ new Date(item.date).toLocaleString() }}</small>
                    <button class="btn-delete-history" @click.stop="deleteHistoryItem(idx)">
                      ×
                    </button>
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
                <button class="btn-mapping" @click="openMappingDialog" :disabled="!worksheetSelected">Map Columns</button>
              </div>

              <!-- Worksheet Selector -->
              <div v-if="worksheetWorkflow.workbookSheets.length > 0" class="worksheet-selector-section">
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

              <!-- Preview – always shows mapping dropdowns after mapping is applied -->
              <div v-if="rawData.length && showPreview" class="excel-preview-section">
                <h4>File Preview (first {{ Math.min(rawData.length, 500) }} rows)</h4>
                <p class="preview-info">{{ rawData.length }} total rows — edit cells below like Excel</p>
                <ExcelViewer
                  :data="rawData.slice(0, 500)"
                  :headers="uploadPreviewHeaders"
                  :original-data="originalRawData.slice(0, 500)"
                  :original-headers="originalFileColumns"
                  :show-mapping-controls="true"
                  :column-mapping="columnMapping"
                  :available-file-columns="fileColumns"
                  :required-columns="requiredColumns"
                  @data-update="onRawExcelUpdate"
                  @mapping-update="updateColumnMapping"
                />
                <div class="preview-actions">
                  <button class="btn-primary" @click="saveFinalMapping">Save Mapping</button>
                  <button class="btn-review-excel-small" @click="openExcelReview(rawData, 'Uploaded Data')">Full Screen</button>
                </div>
              </div>

              <!-- ===== MAPPING DIALOG ===== -->
              <v-dialog v-model="showMappingDialog" max-width="650px">
                <v-card>
                  <v-card-title class="mapping-dialog-title">
                    Map Columns – {{ instrumentName }}
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
                    <button class="btn-close-dialog" @click="showSavedMappingsDialog = false">
                      ×
                    </button>
                  </v-card-title>
                  <v-card-text>
                    <div class="save-section">
                      <h4>Save current mapping as template</h4>
                      <div class="save-row">
                        <input type="text" v-model="newTemplateName" placeholder="Template name" class="template-input" />
                        <button class="btn-primary" @click="saveCurrentMappingAsTemplate" :disabled="!newTemplateName">Save</button>
                      </div>
                    </div>
                    <div v-if="Object.keys(savedTemplates).length" class="saved-list">
                      <div v-for="(tmpl, name) in savedTemplates" :key="name" class="saved-item">
                        <div class="template-info">
                          <span class="template-name">{{ name }}</span>
                          <span class="template-timestamp">Saved: {{ tmpl.timestamp ? new Date(tmpl.timestamp).toLocaleString() : '' }}</span>
                        </div>
                        <div class="template-actions">
                          <button class="btn-secondary small" @click="loadTemplateFromPopup(name)">Load</button>
                          <button class="btn-danger small" @click="deleteTemplateFromPopup(name)">Delete</button>
                        </div>
                      </div>
                    </div>
                    <div v-else class="empty-saved">
                      <p>No saved mappings yet.</p>
                    </div>
                  </v-card-text>
                  <v-card-actions>
                    <button class="btn-secondary" @click="showSavedMappingsDialog = false">Close</button>
                  </v-card-actions>
                </v-card>
              </v-dialog>

              <!-- Workbook Viewer Dialog - NO LOGO + WORK ON SHEET BUTTON -->
              <v-dialog v-model="showWorkbookViewer" max-width="95%" fullscreen hide-overlay>
                <v-card>
                  <v-card-title class="excel-dialog-title-no-logo">
                    <span>Excel Workbook – {{ currentSheetName || 'Select a sheet' }}</span>
                    <v-spacer></v-spacer>
                    <button class="btn-work-on-sheet" @click="workOnSelectedSheet" v-if="currentSheetName && workbookSheets.length">
                      Work on This Sheet
                    </button>
                    <button class="btn-close-dialog" @click="showWorkbookViewer = false">
                      ×
                    </button>
                  </v-card-title>
                  <v-card-text class="pa-0" style="height: calc(100vh - 120px);">
                    <ExcelViewer
                      :data="workbookSheets.find(s => s.name === currentSheetName)?.data || []"
                      :headers="workbookSheets.find(s => s.name === currentSheetName)?.headers || []"
                      :workbook-sheets="workbookSheets"
                      @sheet-selected="handleSheetSelected"
                      @process-sheet="handleProcessSheet"
                    />
                  </v-card-text>
                  <div class="popup-footer" style="padding:12px 24px; border-top:1px solid #e0e0e0; background:#f9fafc;">
                    <span class="valuation-date-footer">Valuation Date: {{ new Date().toISOString().split('T')[0] }}</span>
                    <v-spacer></v-spacer>
                    <button class="btn-secondary" @click="showWorkbookViewer = false">Close</button>
                  </div>
                </v-card>
              </v-dialog>

              <div class="required-columns">
                <h4>Required Columns:</h4>
                <div class="columns-list">
                  <span v-for="col in requiredColumns" :key="col" class="column-badge" :class="{ 'missing-column': !hasRequiredColumn(col), 'mapped-column': hasRequiredColumn(col) }">
                    {{ col }}
                  </span>
                </div>
                <div v-if="rawData.length && missingColumns.length" class="warning-message">
                  <span>Missing required columns. Use the dropdowns on the column headers or click "Map Columns" to assign them.</span>
                </div>
                <div v-if="rawData.length && missingColumns.length === 0 && mappingApplied" class="success-message">
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

        <!-- ===== CLEANING ===== -->
        <div v-if="activeTab === 'cleaning'" class="content-card">
          <v-card>
            <v-card-title>Clean {{ instrumentName }} Data</v-card-title>
            <v-card-text>
              <div v-if="!hasData" class="empty-state">
                <p>No data uploaded yet.</p>
                <button class="btn-primary" @click="switchTab('upload')">Go to Upload</button>
              </div>
              <div v-else>
                <div class="cleaning-options-panel">
                  <h3>Cleaning Filters (select any combination)</h3>
                  <div class="filter-scroll-container">
                    <div class="options-list">
                      <label class="option-checkbox"><input type="checkbox" v-model="cleaningOptions.removeDuplicates"> Remove duplicate rows</label>
                      <label class="option-checkbox"><input type="checkbox" v-model="cleaningOptions.fillMissingText"> Fill missing text with "N/A"</label>
                      <label class="option-checkbox"><input type="checkbox" v-model="cleaningOptions.dropRowsWithMissing"> Drop rows with ANY missing value</label>
                      <label class="option-checkbox"><input type="checkbox" v-model="cleaningOptions.trimWhitespace"> Trim whitespace from all text cells</label>
                      <label class="option-checkbox"><input type="checkbox" v-model="cleaningOptions.convertToNumbers"> Convert text numbers to numeric</label>
                      <label class="option-checkbox"><input type="checkbox" v-model="cleaningOptions.removeOutliers"> Remove outliers (3σ) from numeric columns</label>
                      <label class="option-checkbox"><input type="checkbox" v-model="cleaningOptions.standardizeDates"> Standardize date formats to YYYY-MM-DD</label>
                      <label class="option-checkbox"><input type="checkbox" v-model="cleaningOptions.removeSpecialChars"> Remove special characters from text columns (keep alphanumeric and spaces)</label>
                      <label class="option-checkbox"><input type="checkbox" v-model="cleaningOptions.changeCase"> Change text case:
                        <select v-model="cleaningOptions.caseType"><option value="none">None</option><option value="upper">UPPER CASE</option><option value="lower">lower case</option><option value="title">Title Case</option></select>
                      </label>
                      <label class="option-checkbox"><input type="checkbox" v-model="cleaningOptions.fillWithCustom"> Fill missing values with custom value:
                        <input type="text" v-model="cleaningOptions.customFillValue" placeholder="Custom value" style="width:100px">
                      </label>
                      <label class="option-checkbox"><input type="checkbox" v-model="cleaningOptions.removeColumnsAllMissing"> Remove columns where ALL values are missing</label>
                      <label class="option-checkbox"><input type="checkbox" v-model="cleaningOptions.capOutliers"> Cap outliers at 3 standard deviations (winsorize)</label>
                      <label class="option-checkbox"><input type="checkbox" v-model="cleaningOptions.removeRowsSpecificColumnEmpty"> Remove rows where a specific column is empty:
                        <select v-model="cleaningOptions.specificColumn"><option value="">-- Select column --</option><option v-for="col in Object.keys(rawData[0]||{})" :key="col" :value="col">{{ col }}</option></select>
                      </label>
                      <label class="option-checkbox"><input type="checkbox" v-model="cleaningOptions.standardizeNumericRange"> Standardize numeric columns to range [0,1] (min-max scaling)</label>
                      <label class="option-checkbox"><input type="checkbox" v-model="cleaningOptions.removeEmptyRows"> Remove rows that are completely empty</label>
                      <label class="option-checkbox"><input type="checkbox" v-model="cleaningOptions.fillForward"> Forward fill missing values (carry last valid observation forward)</label>
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
                <div v-if="cleanedData.length" class="highlight-box">
                  <p>✓ Removed {{ cleaningStats.removedRows }} invalid rows</p>
                  <p>✓ Fixed {{ cleaningStats.fixedMissing }} missing values</p>
                  <p class="success-text">✓ Data is now clean and ready for calculations</p>
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
              <div class="calc-header-left">
                <div class="calc-title">{{ instrumentName }} Calculations</div>
                <div v-if="currentlyViewingInstrument" class="viewing-badge-large">
                  <span class="viewing-label">Currently Viewing:</span>
                  <span class="viewing-name">{{ currentlyViewingInstrument }}</span>
                </div>
              </div>
              <v-spacer></v-spacer>
              <!-- CALCULATED INSTRUMENTS BUTTON - visible when 2+ instruments exist and multi-instrument sheet -->
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
                <!-- ===== RESULTS ===== -->
                <div class="summary-cards">
                  <div class="summary-card total" @click="showFormula('Total Portfolio Value')">
                    <div class="card-label">Total Portfolio Value</div>
                    <div class="card-value">${{ calculations.totalValue?.toLocaleString() || 0 }}</div>
                  </div>
                  <div class="summary-card rate" @click="showFormula('Average Rate')">
                    <div class="card-label">{{ instrumentType === 'money-market' ? 'Avg Interest Rate' : instrumentType === 'bonds' ? 'Avg Coupon Rate' : 'Avg Discount Rate' }}</div>
                    <div class="card-value">{{ instrumentType === 'money-market' ? (calculations.avgRate || 0) : instrumentType === 'bonds' ? (calculations.avgCouponRate || 0) : (calculations.avgDiscountRate || 0) }}%</div>
                  </div>
                  <div class="summary-card count" @click="showFormula('Number of Instruments')">
                    <div class="card-label">Number of Instruments</div>
                    <div class="card-value">{{ calculations.instrumentCount || 0 }}</div>
                  </div>
                </div>
                <div v-if="calculations.fred?.benchmark_rate" class="comparison-card fred-calc-card">
                  <div class="comparison-item">
                    <span class="comparison-label">FRED market benchmark ({{ calculations.fred.series_label }}):</span>
                    <span class="comparison-value market">{{ calculations.fred.benchmark_rate }}%</span>
                  </div>
                  <div class="comparison-item">
                    <span class="comparison-label">Spread vs your portfolio:</span>
                    <span class="comparison-value" :class="(calculations.fred.spread_vs_market || 0) >= 0 ? 'negative' : 'positive'">{{ calculations.fred.spread_vs_market }}%</span>
                  </div>
                  <small class="fred-meta">{{ calculations.fred.country_name || calculations.fred.country }} · {{ calculations.fred.currency }} · {{ calculations.fred.maturity }} · FRED</small>
                  <small v-if="calculations.fred.note" class="fred-meta">{{ calculations.fred.note }}</small>
                </div>

                <!-- ===== DETAILED CALCULATIONS ===== -->
                <div class="calculations-section">
                  <h3>{{ instrumentName }} Calculations</h3>
                  <div class="calculations-grid">
                    <template v-if="instrumentType === 'money-market'">
                      <div class="calculation-card" @click="showFormula('weightedAvgRate')">
                        <div class="calc-name">Weighted Average Rate</div>
                        <div class="calc-value">{{ calculations.weightedAvgRate || 0 }}%</div>
                      </div>
                      <div class="calculation-card" @click="showFormula('totalInterest')">
                        <div class="calc-name">Total Interest (Annualized)</div>
                        <div class="calc-value">${{ calculations.totalInterest?.toLocaleString() || 0 }}</div>
                      </div>
                      <div class="calculation-card" @click="showFormula('interestEarned')">
                        <div class="calc-name">Interest Earned</div>
                        <div class="calc-value">${{ calculations.interestEarned?.toLocaleString() || 0 }}</div>
                      </div>
                      <div class="calculation-card" @click="showFormula('annualYield')">
                        <div class="calc-name">Annual Yield</div>
                        <div class="calc-value">{{ calculations.annualYield || 0 }}%</div>
                      </div>
                      <div class="calculation-card" @click="showFormula('effectiveAnnualRate')">
                        <div class="calc-name">Effective Annual Rate</div>
                        <div class="calc-value">{{ calculations.effectiveAnnualRate || 0 }}%</div>
                      </div>
                      <div class="calculation-card" @click="showFormula('avgDaysToMaturity')">
                        <div class="calc-name">Average Days to Maturity</div>
                        <div class="calc-value">{{ calculations.avgDaysToMaturity || 0 }} days</div>
                      </div>
                      <div class="calculation-card" @click="showFormula('totalPrincipal')">
                        <div class="calc-name">Total Principal</div>
                        <div class="calc-value">${{ calculations.totalPrincipal?.toLocaleString() || 0 }}</div>
                      </div>
                    </template>
                    <template v-else-if="instrumentType === 'bonds'">
                      <div class="calculation-card" @click="showFormula('weightedAvgCoupon')">
                        <div class="calc-name">Weighted Average Coupon</div>
                        <div class="calc-value">{{ calculations.weightedAvgCoupon || 0 }}%</div>
                      </div>
                      <div class="calculation-card" @click="showFormula('totalAnnualIncome')">
                        <div class="calc-name">Total Annual Income</div>
                        <div class="calc-value">${{ calculations.totalAnnualIncome?.toLocaleString() || 0 }}</div>
                      </div>
                      <div class="calculation-card" @click="showFormula('avgYTM')">
                        <div class="calc-name">Average Yield to Maturity</div>
                        <div class="calc-value">{{ calculations.avgYTM || 0 }}%</div>
                      </div>
                      <div class="calculation-card" @click="showFormula('duration')">
                        <div class="calc-name">Duration (years)</div>
                        <div class="calc-value">{{ calculations.duration || 0 }}</div>
                      </div>
                    </template>
                    <template v-else>
                      <div class="calculation-card" @click="showFormula('weightedAvgDiscount')">
                        <div class="calc-name">Weighted Average Discount</div>
                        <div class="calc-value">{{ calculations.weightedAvgDiscount || 0 }}%</div>
                      </div>
                      <div class="calculation-card" @click="showFormula('totalDiscount')">
                        <div class="calc-name">Total Discount</div>
                        <div class="calc-value">${{ calculations.totalDiscount?.toLocaleString() || 0 }}</div>
                      </div>
                      <div class="calculation-card" @click="showFormula('effectiveYield')">
                        <div class="calc-name">Effective Yield</div>
                        <div class="calc-value">{{ calculations.effectiveYield || 0 }}%</div>
                      </div>
                      <div class="calculation-card" @click="showFormula('bondEquivalentYield')">
                        <div class="calc-name">Bond Equivalent Yield</div>
                        <div class="calc-value">{{ calculations.bondEquivalentYield || 0 }}%</div>
                      </div>
                      <div class="calculation-card" @click="showFormula('pricePer100')">
                        <div class="calc-name">Price per $100</div>
                        <div class="calc-value">${{ calculations.pricePer100 || 0 }}</div>
                      </div>
                      <div class="calculation-card" @click="showFormula('totalPurchasePrice')">
                        <div class="calc-name">Total Purchase Price</div>
                        <div class="calc-value">${{ calculations.totalPurchasePrice?.toLocaleString() || 0 }}</div>
                      </div>
                      <div class="calculation-card" @click="showFormula('avgInvestment')">
                        <div class="calc-name">Average Investment</div>
                        <div class="calc-value">${{ calculations.avgInvestment?.toLocaleString() || 0 }}</div>
                      </div>
                      <div class="calculation-card" @click="showFormula('holdingPeriodYield')">
                        <div class="calc-name">Holding Period Yield</div>
                        <div class="calc-value">{{ calculations.holdingPeriodYield || 0 }}%</div>
                      </div>
                      <div class="calculation-card" @click="showFormula('annualizedYield')">
                        <div class="calc-name">Annualized Yield</div>
                        <div class="calc-value">{{ calculations.annualizedYield || 0 }}%</div>
                      </div>
                    </template>
                  </div>
                </div>

                <!-- ===== MULTIPLE INSTRUMENTS POPUP (Calculated Instruments) ===== -->
                <div v-if="showAllCalculationsPopup" class="excel-popup-overlay" @click="closeAllCalculationsPopup">
                  <div class="excel-popup-content excel-table-popup" @click.stop>
                    <div class="popup-header-white">
                      <div class="header-left">
                        <img src="/DuraCapital logo.png" alt="DuraCapital" class="logo" />
                        <div class="header-title">
                          <h4>Calculated Instruments</h4>
                          <p class="header-meta"><strong>{{ activeSession?.name || '' }}</strong></p>
                        </div>
                      </div>
                      <button class="close-btn" @click="closeAllCalculationsPopup">×</button>
                    </div>
                    <div class="popup-body">
                      <div v-if="instrumentSummary.rows.length === 0" class="empty-state">
                        <p>No instruments detected. Please process a worksheet first.</p>
                      </div>
                      <div v-else class="excel-table-container">
                        <p class="popup-instruction">Click any row to load its calculations into the main view.</p>
                        <table class="calculated-instruments-table">
                          <thead>
                            <tr>
                              <th v-for="col in instrumentSummary.columns" :key="col">{{ col }}</th>
                            </tr>
                          </thead>
                          <tbody>
                            <tr 
                              v-for="(row, idx) in instrumentSummary.rows" 
                              :key="idx"
                              :class="{ 'selected-row': currentlyViewingInstrument === (row['Instrument Name'] || `Instrument ${idx + 1}`) }"
                              @click="selectInstrumentFromPopup(idx)"
                            >
                              <td v-for="col in instrumentSummary.columns" :key="col">
                                {{ formatTableCell(row[col], col) }}
                              </td>
                            </tr>
                          </tbody>
                        </table>
                      </div>
                    </div>
                    <div class="popup-footer">
                      <span v-if="currentlyViewingInstrument" class="viewing-indicator">
                        <v-icon small>mdi-eye</v-icon> Currently viewing: <strong>{{ currentlyViewingInstrument }}</strong>
                      </span>
                      <v-spacer></v-spacer>
                      <button class="btn-secondary" @click="closeAllCalculationsPopup">Close</button>
                      <button class="btn-primary" @click="exportAllCalculations">📥 Download Excel</button>
                    </div>
                  </div>
                </div>

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
            <v-card-title><v-icon>mdi-chart-line</v-icon> {{ instrumentName }} – Yield Curve</v-card-title>
            <v-card-text>
              <div v-if="hasCleanedData && yieldCurveData.length" class="comparison-card">
                <div class="comparison-item">
                  <span class="comparison-label">Portfolio Average Rate:</span>
                  <span class="comparison-value portfolio">{{ portfolioAvgRate }}%</span>
                </div>
                <div class="comparison-item">
                  <span class="comparison-label">Benchmark Yield ({{ selectedMaturityOptionLabel }}):</span>
                  <span class="comparison-value market">{{ benchmarkYield !== null ? benchmarkYield + '%' : '—' }}</span>
                </div>
                <div class="comparison-difference" :class="{ 'positive': benchmarkYield - portfolioAvgRate > 0, 'negative': benchmarkYield - portfolioAvgRate < 0 }">
                  Difference: {{ benchmarkYield !== null ? (benchmarkYield - portfolioAvgRate).toFixed(2) : '—' }}%
                </div>
              </div>

              <!-- FILTERS WITH 5 EXAMPLES + CUSTOM INPUT -->
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
                    <option v-for="opt in displayMaturityOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
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
              <div v-else-if="yieldCurveError" class="error-container">
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
            <v-card-title><v-icon>mdi-file-document-outline</v-icon> {{ instrumentName }} – Executive Summary</v-card-title>
            <v-card-text>
              <div class="summary-hero">
                <div class="hero-stat">
                  <span class="hero-value">${{ (calculations.totalValue || 0).toLocaleString() }}</span>
                  <span class="hero-label">Portfolio value</span>
                </div>
                <div class="hero-stat">
                  <span class="hero-value">{{ calculations.instrumentCount || 0 }}</span>
                  <span class="hero-label">Instruments</span>
                </div>
                <div class="hero-stat" v-if="calculations.fred?.benchmark_rate">
                  <span class="hero-value">{{ calculations.fred.benchmark_rate }}%</span>
                  <span class="hero-label">FRED benchmark</span>
                </div>
              </div>
              <div class="summary-grid">
                <div class="summary-section card-panel">
                  <h3><v-icon size="20">mdi-database-outline</v-icon> Data quality</h3>
                  <p><strong>Records processed:</strong> {{ cleanedData.length }}</p>
                  <p><strong>Rows removed:</strong> {{ cleaningStats.removedRows }}</p>
                  <p><strong>Missing values fixed:</strong> {{ cleaningStats.fixedMissing }}</p>
                </div>
                <div class="summary-section card-panel">
                  <h3><v-icon size="20">mdi-finance</v-icon> Valuation metrics</h3>
                  <p><strong>Average rate:</strong> {{ instrumentType === 'money-market' ? (calculations.avgRate || 0) : instrumentType === 'bonds' ? (calculations.avgCouponRate || 0) : (calculations.avgDiscountRate || 0) }}%</p>
                  <p><strong>Weighted average:</strong> {{ instrumentType === 'money-market' ? (calculations.weightedAvgRate || 0) : instrumentType === 'bonds' ? (calculations.weightedAvgCoupon || 0) : (calculations.weightedAvgDiscount || 0) }}%</p>
                  <p v-if="calculations.fred?.spread_vs_market != null"><strong>Spread vs FRED:</strong> {{ calculations.fred.spread_vs_market }}%</p>
                </div>
              </div>
              <div class="excel-viewer-button" style="margin-bottom: 20px; text-align: right;">
                <button class="btn-secondary" @click="openInstrumentDataExcel">📊 View Instrument Data as Excel</button>
              </div>

              <!-- Instrument Summary -->
              <div v-if="instrumentSummary.rows.length > 0" class="instrument-summary-section">
                <h3>📊 Instrument Summary ({{ selectedInstrumentType }})</h3>
                
                <!-- Instrument Breakdown -->
                <div class="instrument-breakdown">
                  <h4>📋 Instrument Breakdown</h4>
                  <div class="breakdown-grid">
                    <div v-for="(row, idx) in instrumentSummary.rows" :key="idx" class="breakdown-card">
                      <div class="card-header">
                        <strong>{{ row['Instrument Name'] || `Instrument ${idx + 1}` }}</strong>
                        <span class="instrument-type">{{ row['Instrument Type'] || selectedInstrumentType }}</span>
                      </div>
                      <div class="card-body">
                        <div class="metric">
                          <span class="label">Counterparty:</span>
                          <span class="value">{{ row['Counterparty'] || '' }}</span>
                        </div>
                        <div class="metric" v-if="row['Face Value'] !== undefined">
                          <span class="label">Face Value:</span>
                          <span class="value">{{ formatCellValue(row['Face Value']) }}</span>
                        </div>
                        <div class="metric" v-if="row['Yield'] !== undefined">
                          <span class="label">Yield:</span>
                          <span class="value">{{ formatCellValue(row['Yield']) }}</span>
                        </div>
                        <div class="metric" v-if="row['Price'] !== undefined">
                          <span class="label">Price:</span>
                          <span class="value">{{ formatCellValue(row['Price']) }}</span>
                        </div>
                        <div class="metric">
                          <span class="label">Status:</span>
                          <span class="value status-active">Active</span>
                        </div>
                      </div>
                      <div class="card-footer">
                        <button class="workflow-btn" @click="openWorkflowPopup(row, idx)">🔄 Open Workflow</button>
                      </div>
                    </div>
                  </div>
                </div>
                
                <div class="summary-table-wrapper">
                  <table class="summary-table">
                    <thead>
                      <tr>
                        <th v-for="col in instrumentSummary.columns" :key="col">
                          {{ col }}
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="(row, idx) in instrumentSummary.rows" :key="idx">
                        <td v-for="col in instrumentSummary.columns" :key="col">
                          <input 
                            v-if="col === 'Instrument Name' || col === 'Counterparty'"
                            v-model="row[col]"
                            @blur="editInstrumentRow(idx, col, row[col])"
                            class="editable-cell"
                          />
                          <span v-else>{{ formatCellValue(row[col], col) }}</span>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <div class="export-buttons">
                  <button class="btn-primary" @click="viewInstrumentSummaryExcel">📊 View as Excel</button>
                </div>
              </div>

              <!-- Instrument Summary Excel Popup -->
              <div v-if="showInstrumentExcelPopup" class="excel-popup-overlay" @click="closeInstrumentExcelPopup">
                <div class="excel-popup-content" @click.stop>
                  <div class="popup-header-white">
                    <div class="header-left">
                      <img src="/DuraCapital logo.png" alt="DuraCapital" class="logo" />
                      <div class="header-title">
                        <h4>Instrument Summary – {{ selectedInstrumentType }}</h4>
                        <p class="header-meta"><strong>{{ activeSession?.name || 'N/A' }}</strong></p>
                      </div>
                    </div>
                    <button class="close-btn" @click="closeInstrumentExcelPopup">×</button>
                  </div>
                  <div class="popup-body">
                    <div class="excel-table-wrapper">
                      <table class="excel-table">
                        <thead>
                          <tr>
                            <th v-for="col in instrumentSummaryColumnsForDisplay" :key="col" @click="sortByColumn(col)" class="sortable-header">
                              <span>{{ col }}</span>
                              <span class="sort-indicator" v-if="sortColumn === col">
                                {{ sortOrder === 'asc' ? '▲' : '▼' }}
                              </span>
                            </th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr v-for="(row, idx) in sortedInstrumentSummaryRows" :key="idx">
                            <td v-for="col in instrumentSummaryColumnsForDisplay" :key="col">
                              {{ formatCellValue(row[col], col) }}
                            </td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                  </div>
                  <div class="popup-footer">
                    <button class="btn-secondary" @click="closeInstrumentExcelPopup">Close</button>
                    <button class="btn-primary" @click="exportInstrumentSummaryExcel">📥 Download Excel</button>
                    <span class="valuation-date-footer">Valuation Date: {{ new Date().toISOString().split('T')[0] }}</span>
                  </div>
                </div>
              </div>

              <!-- Portfolio Summary -->
              <div v-if="portfolioSummary.rows.length > 0" class="portfolio-summary-section">
                <h3>📊 Portfolio Summary ({{ selectedInstrumentType }}) – {{ portfolioSummary.rows.length }} instruments</h3>
                
                <!-- Instrument Breakdown -->
                <div class="instrument-breakdown">
                  <h4>📋 Instrument Breakdown</h4>
                  <div class="breakdown-grid">
                    <div v-for="(row, idx) in portfolioSummary.rows" :key="idx" class="breakdown-card">
                      <div class="card-header">
                        <strong>{{ row['Instrument Name'] || `Instrument ${idx + 1}` }}</strong>
                        <span class="instrument-type">{{ row['Instrument Type'] || selectedInstrumentType }}</span>
                      </div>
                      <div class="card-body">
                        <div class="metric">
                          <span class="label">Counterparty:</span>
                          <span class="value">{{ row['Counterparty'] || '' }}</span>
                        </div>
                        <div class="metric" v-if="row['Face Value'] !== undefined">
                          <span class="label">Face Value:</span>
                          <span class="value">{{ formatCellValue(row['Face Value']) }}</span>
                        </div>
                        <div class="metric" v-if="row['Yield'] !== undefined">
                          <span class="label">Yield:</span>
                          <span class="value">{{ formatCellValue(row['Yield']) }}</span>
                        </div>
                        <div class="metric" v-if="row['Price'] !== undefined">
                          <span class="label">Price:</span>
                          <span class="value">{{ formatCellValue(row['Price']) }}</span>
                        </div>
                        <div class="metric">
                          <span class="label">Status:</span>
                          <span class="value status-active">Active</span>
                        </div>
                      </div>
                      <div class="card-footer">
                        <button class="workflow-btn" @click="openWorkflowPopup(row, idx)">🔄 Open Workflow</button>
                      </div>
                    </div>
                  </div>
                </div>
                
                <div class="summary-table-wrapper">
                  <table class="summary-table">
                    <thead>
                      <tr>
                        <th v-for="col in portfolioSummary.columns" :key="col">
                          {{ col }}
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="(row, idx) in portfolioSummary.rows" :key="idx">
                        <td v-for="col in portfolioSummary.columns" :key="col">
                          <input 
                            v-if="col === 'Instrument Name' || col === 'Counterparty'"
                            v-model="row[col]"
                            @blur="editPortfolioRow(idx, col, row[col])"
                            class="editable-cell"
                          />
                          <span v-else>{{ formatCellValue(row[col], col) }}</span>
                        </td>
                      </tr>
                    </tbody>
                    <tfoot v-if="hasNumericColumns">
                      <tr class="total-row">
                        <td v-for="col in portfolioSummary.columns" :key="col">
                          <strong v-if="isNumericField(col)">{{ calculateTotal(col) }}</strong>
                          <span v-else></span>
                        </td>
                      </tr>
                    </tfoot>
                  </table>
                </div>
                <div class="export-buttons">
                  <button class="btn-secondary" @click="goToPreviousStep">← Previous Step</button>
                  <button class="btn-primary" @click="viewPortfolioSummaryExcel">📊 View as Excel</button>
                  <button class="btn-secondary" @click="exportSummary">📥 Export Summary</button>
                </div>
              </div>

              <!-- Portfolio Summary Excel Popup -->
              <div v-if="showPortfolioExcelPopup" class="excel-popup-overlay" @click="closePortfolioExcelPopup">
                <div class="excel-popup-content" @click.stop>
                  <div class="popup-header-white">
                    <div class="header-left">
                      <img src="/DuraCapital logo.png" alt="DuraCapital" class="logo" />
                      <div class="header-title">
                        <h4>Portfolio Summary – {{ selectedInstrumentType }}</h4>
                        <p class="header-meta"><strong>{{ activeSession?.name || 'N/A' }}</strong></p>
                      </div>
                    </div>
                    <button class="close-btn" @click="closePortfolioExcelPopup">×</button>
                  </div>
                  <div class="popup-body">
                    <div class="excel-table-wrapper">
                      <table class="excel-table">
                        <thead>
                          <tr>
                            <th v-for="col in portfolioSummaryColumnsForDisplay" :key="col" @click="sortByColumn(col)" class="sortable-header">
                              <span>{{ col }}</span>
                              <span class="sort-indicator" v-if="sortColumn === col">
                                {{ sortOrder === 'asc' ? '▲' : '▼' }}
                              </span>
                            </th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr v-for="(row, idx) in sortedPortfolioSummaryRows" :key="idx">
                            <td v-for="col in portfolioSummaryColumnsForDisplay" :key="col">
                              {{ formatCellValue(row[col], col) }}
                            </td>
                          </tr>
                        </tbody>
                        <tfoot v-if="hasNumericColumns">
                          <tr class="total-row">
                            <td v-for="col in portfolioSummaryColumnsForDisplay" :key="col">
                              <strong v-if="isNumericField(col)">{{ calculateTotal(col) }}</strong>
                              <span v-else></span>
                            </td>
                          </tr>
                        </tfoot>
                      </table>
                    </div>
                  </div>
                  <div class="popup-footer">
                    <button class="btn-secondary" @click="closePortfolioExcelPopup">Close</button>
                    <button class="btn-primary" @click="exportPortfolioSummaryExcel">📥 Download Excel</button>
                    <span class="valuation-date-footer">Valuation Date: {{ new Date().toISOString().split('T')[0] }}</span>
                  </div>
                </div>
              </div>

              <!-- Workflow Popup -->
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
                      <button class="workflow-option-btn" @click="navigateToUpload">
                        <v-icon>mdi-upload</v-icon>
                        <span>Upload New Data</span>
                      </button>
                      <button class="workflow-option-btn" @click="navigateToCleaning">
                        <v-icon>mdi-broom</v-icon>
                        <span>Cleaning</span>
                      </button>
                      <button class="workflow-option-btn" @click="navigateToCalculations">
                        <v-icon>mdi-calculator</v-icon>
                        <span>Calculations</span>
                      </button>
                      <button class="workflow-option-btn" @click="navigateToVisualizations">
                        <v-icon>mdi-chart-line</v-icon>
                        <span>Visualizations</span>
                      </button>
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
                <button class="btn-primary" @click="goToPortfolioSummary">Portfolio Summary →</button>
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
                  <button class="btn-json" @click="downloadCombinedReport('json')">JSON</button>
                  <button class="btn-csv" @click="downloadCombinedReport('csv')">CSV</button>
                  <button class="btn-html" @click="downloadCombinedReport('html')">HTML</button>
                  <button class="btn-pdf" @click="downloadCombinedReport('pdf')">PDF</button>
                  <button class="btn-word" @click="downloadCombinedReport('word')">Word</button>
                  <button class="btn-excel" @click="downloadCombinedReport('excel')">Excel (XLSX)</button>
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
            <div class="header-title">
              <h4>{{ excelDialogTitle }}</h4>
              <p class="header-meta"><strong>{{ activeSession?.name || 'N/A' }}</strong></p>
            </div>
          </div>
          <v-spacer></v-spacer>
          <button class="btn-close-dialog" @click="closeExcelDialog">
            <v-icon>mdi-close</v-icon>
          </button>
        </v-card-title>
        <v-card-text class="excel-dialog-content pa-0">
          <ExcelViewer :data="excelData" :headers="excelColumns" @data-update="onExcelDataUpdate" />
        </v-card-text>
        <div class="popup-footer" style="padding:12px 24px; border-top:1px solid #e0e0e0; background:#f9fafc;">
          <span class="valuation-date-footer">Valuation Date: {{ new Date().toISOString().split('T')[0] }}</span>
          <v-spacer></v-spacer>
          <button class="btn-secondary" @click="closeExcelDialog">Close</button>
        </div>
      </v-card>
    </v-dialog>

    <!-- Formula Dialog -->
    <v-dialog v-model="formulaDialog" max-width="500px">
      <v-card>
        <v-card-title class="formula-dialog-title">
          <v-icon>mdi-ruler</v-icon> Formula Used
        </v-card-title>
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
            <div class="header-title">
              <h4>Report Preview</h4>
              <p class="header-meta"><strong>{{ activeSession?.name || 'N/A' }}</strong></p>
            </div>
          </div>
          <v-spacer></v-spacer>
          <button class="btn-close-dialog" @click="reportPreviewDialog = false">
            <v-icon>mdi-close</v-icon>
          </button>
        </v-card-title>
        <v-card-text class="report-preview-content" style="padding:0;">
          <iframe :srcdoc="reportPreviewHtml" frameborder="0" style="width:100%; height:80vh;"></iframe>
        </v-card-text>
        <div class="popup-footer" style="padding:12px 24px; border-top:1px solid #e0e0e0; background:#f9fafc;">
          <span class="valuation-date-footer">Valuation Date: {{ new Date().toISOString().split('T')[0] }}</span>
          <v-spacer></v-spacer>
          <button class="btn-primary" @click="downloadFromPreview('html')">Download HTML</button>
          <button class="btn-pdf" @click="downloadFromPreview('pdf')">Download PDF</button>
          <button class="btn-word" @click="downloadFromPreview('word')">Download Word</button>
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
  </FixedLayout>
</template>

<script setup>
// ===== IMPORTS =====
import { ref, computed, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import FixedLayout from '@/components/FixedLayout.vue'
import * as XLSX from 'xlsx'
import api from '@/services/api.js'
import sessionManager from '@/services/sessionManager.js'
import { useFredMarket } from '@/composables/useFredMarket'
import { useWorksheetWorkflow } from '@/composables/useWorksheetWorkflow.js'
import ExcelViewer from '@/components/ExcelViewer.vue'
import ExcelWorkbookViewer from '@/components/ExcelWorkbookViewer.vue'
import ExcelModalViewer from '@/components/ExcelModalViewer.vue'
import WorksheetSelector from '@/components/WorksheetSelector.vue'
import { loadFredSeriesChart, loadFredSeriesForReport } from '@/utils/fredChartHelper'
import { markStepCompleted, isStepPersistedCompleted } from '@/utils/workflowProgress.js'
import { buildWorkflowSnapshot, applyWorkflowToPage } from '@/utils/instrumentSession.js'
import { useInstrumentConfig } from '@/composables/useInstrumentConfig'
import { autoMatchColumns, applyMappingToRows, isColumnMapped, getMissingColumns } from '@/utils/instrumentMapping'
import { parseExcel } from '@/utils/intelligentParser'
import { detectSheetType, extractSingleInstrumentValues, getRequiredFieldMappings } from '@/utils/sheetTypeDetector'
import Chart from 'chart.js/auto'
import { API_BASE_URL } from '@/config.js'
import { getInstrumentColumns, getTotalFields } from '@/config/instrumentColumns.js'

// ===== COMPOSABLES =====
const router = useRouter()
const route = useRoute()

const instrumentType = computed(() => route.params.type || route.path.split('/').pop())

const { requiredColumns, columnVariations, workflowSteps, loadConfig } = useInstrumentConfig(route.params.type)
const { fredFilters, filterOptions, loadFilterOptions, fetchBenchmark } = useFredMarket('1Y')
const worksheetWorkflow = useWorksheetWorkflow(instrumentType)

// ===== REFS =====
const activeSession = ref(null)
const yieldCurveLoading = ref(false)
const yieldCurveError = ref('')
const yieldCurveChart = ref(null)
const chartInstanceRef = { current: null }
const yieldCurveData = ref([])
const chartSeriesLabel = ref('')
const currentMarketRate = ref(null)

const selectedMaturityOption = ref('')
const selectedCountryOption = ref('USA')
const selectedCurrencyOption = ref('USD')

// Custom filter inputs
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
const cleaningStats = ref({ totalRows: 0, validRows: 0, removedRows: 0, fixedMissing: 0 })
const fileLoading = ref(false)
const uploadError = ref('')
const uploadProgress = ref(0)

const showInstrumentExcelPopup = ref(false)
const showPortfolioExcelPopup = ref(false)
const showWorkflowPopup = ref(false)
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
const sessionSavedAt = ref(null)
const showPreview = ref(false)
const worksheetSelected = ref(false)
const forceUpdate = ref(0)

const savedTemplates = ref({})
const selectedTemplate = ref('')
const newTemplateName = ref('')

const cleaningOptions = ref({
  removeDuplicates: true, fillMissingText: true, dropRowsWithMissing: false, trimWhitespace: true,
  convertToNumbers: true, removeOutliers: false, standardizeDates: false, removeSpecialChars: false,
  changeCase: false, caseType: 'none', fillWithCustom: false, customFillValue: '',
  removeColumnsAllMissing: false, capOutliers: false, removeRowsSpecificColumnEmpty: false,
  specificColumn: '', standardizeNumericRange: false, removeEmptyRows: false, fillForward: false, fillBackward: false
})

const selectedInstrumentType = ref('Bonds')
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
const workbookData = ref(null)
const workbookSheets = ref([])
const currentSheetName = ref('')

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

// ===== FILTER DISPLAY OPTIONS =====
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

const displayMaturityOptions = computed(() => {
  let base = []
  if (instrumentType.value === 'money-market') {
    base = [
      { value: '1M', label: '1 Month' },
      { value: '3M', label: '3 Months' },
      { value: '6M', label: '6 Months' },
      { value: '1Y', label: '1 Year' }
    ]
  } else if (instrumentType.value === 'bonds') {
    base = [
      { value: '2Y', label: '2 Years' },
      { value: '5Y', label: '5 Years' },
      { value: '10Y', label: '10 Years' },
      { value: '30Y', label: '30 Years' }
    ]
  } else if (instrumentType.value === 'tbills') {
    base = [
      { value: '4W', label: '4 Weeks' },
      { value: '13W', label: '13 Weeks' },
      { value: '26W', label: '26 Weeks' },
      { value: '52W', label: '52 Weeks' }
    ]
  } else {
    base = [
      { value: '3M', label: '3 Months' },
      { value: '1Y', label: '1 Year' },
      { value: '5Y', label: '5 Years' },
      { value: '10Y', label: '10 Years' }
    ]
  }
  return base
})

// ===== COMPUTED =====
const instrumentName = computed(() => ({ 'money-market': 'Money Market', bonds: 'Bonds', tbills: 'T-Bills' })[instrumentType.value] || 'Instrument')

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

const portfolioAvgRate = computed(() => 
  instrumentType.value === 'money-market' ? calculations.value.avgRate || 0 : 
  instrumentType.value === 'bonds' ? calculations.value.avgCouponRate || 0 : 
  calculations.value.avgDiscountRate || 0
)

const effectiveMaturity = computed(() => {
  if (selectedMaturityOption.value === '__custom__') return customMaturityInput.value || '1Y'
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
  const opt = displayMaturityOptions.value.find(o => o.value === selectedMaturityOption.value)
  return opt ? opt.label : selectedMaturityOption.value
})

const benchmarkYield = computed(() => {
  if (!effectiveMaturity.value || !yieldCurveData.value.length) return null
  return getRateForMaturity(effectiveMaturity.value)
})

const instrumentSummaryColumnsForDisplay = computed(() => {
  return instrumentSummary.value.columns.filter(c => 
    !['_raw', '_source', 'index', '__v'].includes(c)
  )
})

const portfolioSummaryColumnsForDisplay = computed(() => {
  return portfolioSummary.value.columns.filter(c => 
    !['_raw', '_source', 'index', '__v'].includes(c)
  )
})

const sortedInstrumentSummaryRows = computed(() => {
  if (!sortColumn.value) return instrumentSummary.value.rows
  return [...instrumentSummary.value.rows].sort((a, b) => {
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

const sortedPortfolioSummaryRows = computed(() => {
  if (!sortColumn.value) return portfolioSummary.value.rows
  return [...portfolioSummary.value.rows].sort((a, b) => {
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

// ===== FUNCTIONS =====
function isStepComplete(tab) {
  return isStepPersistedCompleted(activeSession.value?.id, tab)
}

function switchTab(tab) {
  const idx = steps.value.findIndex(s => s.tab === tab)
  if (idx > farthestAllowedIndex.value) {
    alert('You cannot skip ahead. Complete the current step first.')
    return
  }
  saveSessionData()
  activeTab.value = tab
  forceUpdate.value++
}

function goToDashboard() { saveSessionData(); router.push('/dashboard') }
function goToPortfolioSummary() { saveSessionData(); router.push('/summary') }

function goToCalculations() {
  if (hasCleanedData.value) {
    saveSessionData()
    activeTab.value = 'calculations'
    forceUpdate.value++
  } else {
    alert('Please clean your data first.')
  }
}

function goToVisualizations() {
  if (hasCleanedData.value) {
    saveSessionData()
    activeTab.value = 'visualizations'
    forceUpdate.value++
  } else {
    alert('Please clean your data first.')
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
    saveSessionData()
  }
  forceUpdate.value++
}

function defaultMaturityForInstrument() {
  const inst = instrumentType.value
  if (inst === 'bonds') return '10Y'
  if (inst === 'money-market') return '1Y'
  if (inst === 'tbills') return '13W'
  return '3M'
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
  if (closest && minDiff < 0.5) {
    return closest.rate
  }
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

function formatLabel(key) {
  return key.replace(/([A-Z])/g, ' $1').replace(/^./, str => str.toUpperCase())
}

function formatNumber(num) {
  if (num === undefined || num === null) return '0.00'
  return num.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

// ===== UPLOAD FUNCTIONS =====
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
  uploadHistory.value.unshift({
    name: filename,
    date: Date.now(),
    data: JSON.stringify(data),
    fileData: uploadedFileBase64.value
  })
  if (uploadHistory.value.length > 10) uploadHistory.value.pop()
  saveUploadHistory()
}

async function loadHistoryFile(item) {
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
    showPreview.value = false
    saveSessionData()
    forceUpdate.value++
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
    readFileData(fileCopy)
  }
}

function handleDrop(e) {
  e.preventDefault()
  const file = e.dataTransfer.files[0]
  if (file) {
    const fileCopy = new File([file], file.name, { type: file.type })
    uploadedFile.value = fileCopy
    readFileData(fileCopy)
  }
}

async function readFileData(file) {
  console.log('readFileData called with file:', file.name, 'size:', file.size)
  fileLoading.value = true
  uploadError.value = ''
  
  try {
    const result = await worksheetWorkflow.handleFileUpload(file)
    
    if (result.success) {
      workbookSheets.value = worksheetWorkflow.workbookSheets.value
      worksheetStatus.value = worksheetWorkflow.worksheetStatus.value
      originalFileBuffer.value = worksheetWorkflow.originalFileBuffer.value
      
      console.log('✅ Workbook loaded via worksheet workflow:', result.sheets.length, 'sheets')
      
      // Don't auto-select the first sheet - user must explicitly select it
      // This ensures Preview/Review Excel/Map Columns buttons remain disabled until worksheet is selected
      worksheetSelected.value = false
      currentSheetName.value = ''
      
      addToHistory(file.name, result.sheets[0]?.data || [])
      debouncedSave()
      forceUpdate.value++
    } else {
      throw new Error(result.error || 'Failed to upload workbook')
    }
  } catch (err) {
    console.error('Upload error:', err)
    uploadError.value = err.message
    alert(`Failed to parse file: ${err.message}`)
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
  fixedValuesTracker.value.clear()
  mappingApplied.value = false
  columnMapping.value = {}
  fileColumns.value = []
  showPreview.value = false
  worksheetSelected.value = false
  uploadError.value = ''
  worksheetWorkflow.reset()
  debouncedSave()
  forceUpdate.value++
  if (fileInput.value) fileInput.value.value = ''
}

function handleWorksheetSelect(sheetName) {
  worksheetWorkflow.selectWorksheet(sheetName)
  currentSheetName.value = sheetName
  worksheetSelected.value = true
}

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
      rawData.value = result.tabularData || []
      sheetType.value = result.sheetType || 'multi'
      extractedValues.value = result.extractedValues || {}
      
      worksheetStatus.value[sheetName] = {
        ...worksheetStatus.value[sheetName],
        processed: true,
        sheetType: result.sheetType
      }
      
      // Enable worksheet selection and buttons
      worksheetSelected.value = true
      currentSheetName.value = sheetName
      
      // Ensure preview shows the mapped data
      if (result.sheetType === 'multi') {
        // Auto-map columns using actual uploaded dataset column names
        const headers = Object.keys(rawData.value[0] || {})
        fileColumns.value = headers
        columnMapping.value = autoMatchColumns(headers, requiredColumns.value, columnVariations.value)
        applyCurrentMapping()
        showPreview.value = true
      }
      
      if (result.sheetType === 'single') {
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
    if (status.sheetType === 'single') {
      activeTab.value = 'summary'
    } else {
      activeTab.value = 'calculations'
    }
  }
}

function applyCurrentMapping() {
  if (!originalRawData.value.length) return
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
      newRow[col] = srcCol ? row[srcCol] : ''
    })
    return newRow
  })
  rawData.value = mappedData
  const allMapped = requiredColumns.value.every(col => columnMapping.value[col])
  mappingApplied.value = allMapped
  // Ensure preview shows mapping controls
  showPreview.value = true
}

function updateColumnMapping(newMapping) {
  columnMapping.value = { ...newMapping }
  applyCurrentMapping()
  debouncedSave()
}

function saveFinalMapping() {
  // Save the current mapping to localStorage for future use
  const mappingKey = `mapping_${instrumentType.value}_${uploadedFile.value?.name || 'default'}`
  localStorage.setItem(mappingKey, JSON.stringify(columnMapping.value))
  
  // Also save to saved templates
  const templateName = `${instrumentType.value} - ${uploadedFile.value?.name || 'Custom'}`
  savedTemplates.value[templateName] = {
    columnMapping: columnMapping.value,
    requiredColumns: requiredColumns.value,
    fileColumns: fileColumns.value,
    savedAt: new Date().toISOString()
  }
  localStorage.setItem('savedTemplates', JSON.stringify(savedTemplates.value))
  
  alert('✅ Mapping saved successfully')
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
  const newMapping = autoMatchColumns(fileColumns.value, requiredColumns.value, columnVariations.value)
  columnMapping.value = { ...columnMapping.value, ...newMapping }
  applyCurrentMapping()
  forceUpdate.value++
}

function openMappingDialog() {
  if (!fileColumns.value.length) refreshFileColumns()
  if (!fileColumns.value.length && rawData.value.length) {
    fileColumns.value = Object.keys(rawData.value[0] || {})
  }
  if (!fileColumns.value.length && originalRawData.value.length) {
    fileColumns.value = Object.keys(originalRawData.value[0] || {})
  }
  if (fileColumns.value.length && !originalFileColumns.value.length) {
    originalFileColumns.value = [...fileColumns.value]
  }
  
  if (uploadedFile.value) {
    const mappingKey = `mapping_${uploadedFile.value.name}_${uploadedFile.value.size}`
    const savedMapping = localStorage.getItem(mappingKey)
    if (savedMapping) {
      try {
        columnMapping.value = JSON.parse(savedMapping)
        console.log('✅ Loaded saved mapping for file:', uploadedFile.value.name)
      } catch (e) {
        console.warn('⚠️ Failed to load saved mapping:', e)
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
    console.log('✅ Mapping saved for file:', uploadedFile.value.name)
  }
  
  showMappingDialog.value = false
  // Ensure preview stays visible with mapping controls
  showPreview.value = true
  forceUpdate.value++
  refreshFileColumns()
}

function resetMapping() {
  const empty = {}
  requiredColumns.value.forEach(col => empty[col] = null)
  columnMapping.value = empty
  applyCurrentMapping()
  forceUpdate.value++
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

async function detectInstruments(sheetData) {
  if (!sheetData || sheetData.length === 0) return [sheetData]
  
  const hasSectionHeaders = checkForRepeatedHeaders(sheetData)
  const hasBlankSeparators = checkForBlankRows(sheetData)
  const hasInstrumentLabels = checkForLabels(sheetData, ['Instrument', 'Bond', 'T-Bill', 'Money Market', 'Treasury Bill'])
  
  if (hasSectionHeaders || hasBlankSeparators || hasInstrumentLabels) {
    console.log('🔍 Multiple instruments detected in sheet')
    return splitIntoInstruments(sheetData)
  }
  
  return [sheetData]
}

function checkForRepeatedHeaders(data) {
  if (data.length < 2) return false
  const firstRowKeys = Object.keys(data[0]).map(k => k.toLowerCase())
  let repeatCount = 0
  
  for (let i = 1; i < data.length; i++) {
    const currentKeys = Object.keys(data[i]).map(k => k.toLowerCase())
    const matchCount = firstRowKeys.filter(key => currentKeys.includes(key)).length
    if (matchCount > firstRowKeys.length * 0.7) {
      repeatCount++
    }
  }
  
  return repeatCount >= 2
}

function checkForBlankRows(data) {
  let blankCount = 0
  data.forEach(row => {
    const values = Object.values(row)
    const isEmpty = values.every(val => val === '' || val === null || val === undefined)
    if (isEmpty) blankCount++
  })
  return blankCount >= 2
}

function checkForLabels(data, labels) {
  const lowerLabels = labels.map(l => l.toLowerCase())
  let labelCount = 0
  
  data.forEach(row => {
    const values = Object.values(row)
    values.forEach(val => {
      if (val && typeof val === 'string') {
        const lowerVal = val.toLowerCase()
        if (lowerLabels.some(label => lowerVal.includes(label))) {
          labelCount++
        }
      }
    })
  })
  
  return labelCount >= 2
}

function splitIntoInstruments(data) {
  const instruments = []
  let currentInstrument = []
  let inInstrument = false
  const instrumentLabels = ['Instrument:', 'Bond:', 'T-Bill:', 'Money Market:', 'Treasury Bill:']
  
  data.forEach(row => {
    const rowValues = Object.values(row)
    
    const hasInstrumentStart = rowValues.some(val => 
      val && typeof val === 'string' && instrumentLabels.some(label => val.includes(label))
    )
    
    const isEmpty = rowValues.every(val => val === '' || val === null || val === undefined)
    
    if (hasInstrumentStart) {
      if (currentInstrument.length > 0) {
        instruments.push(currentInstrument)
      }
      currentInstrument = [row]
      inInstrument = true
    } else if (isEmpty && inInstrument) {
      if (currentInstrument.length > 0) {
        instruments.push(currentInstrument)
        currentInstrument = []
        inInstrument = false
      }
    } else if (inInstrument) {
      currentInstrument.push(row)
    }
  })
  
  if (currentInstrument.length > 0) {
    instruments.push(currentInstrument)
  }
  
  console.log(`📊 Split into ${instruments.length} instruments`)
  return instruments
}

function autoDetectTable(data) {
  if (!data || data.length === 0) return { type: 'empty', data: [] }
  
  const firstRow = Object.values(data[0] || {})
  const hasHeaders = firstRow.some(v => typeof v === 'string' && v.length > 0 && isNaN(v))
  
  if (!hasHeaders) {
    console.log('🔍 No headers detected - treating as raw table')
    const columnCount = Math.max(...data.map(row => Object.keys(row).length))
    const headers = Array.from({ length: columnCount }, (_, i) => `Column ${i + 1}`)
    
    return {
      type: 'table',
      headers: headers,
      data: data.map(row => Object.values(row))
    }
  }
  
  return { type: 'columns', data: data }
}

function extractValueByLabel(data, label) {
  if (!data || data.length === 0) return null
  
  for (let row of data) {
    const rowValues = Object.values(row)
    for (let value of rowValues) {
      if (typeof value === 'string' && value.toLowerCase().includes(label.toLowerCase())) {
        const index = rowValues.indexOf(value)
        return rowValues[index + 1] || null
      }
    }
  }
  
  return null
}

function togglePreview() {
  if (!rawData.value.length) return
  showPreview.value = !showPreview.value
}

// ----- WORKBOOK VIEWER FUNCTIONS -----
function openWorkbookViewer() {
  console.log('=== Opening Workbook Viewer ===')
  
  if (workbookSheets.value && workbookSheets.value.length > 0) {
    showWorkbookViewer.value = true
    if (!currentSheetName.value && workbookSheets.value.length) {
      currentSheetName.value = workbookSheets.value[0].name
    }
    return
  }
  
  if (rawData.value && rawData.value.length > 0) {
    console.log('⚠️ No workbook sheets, creating from current data')
    const headers = Object.keys(rawData.value[0] || {})
    workbookSheets.value = [{
      name: currentSheetName.value || 'Sheet1',
      data: rawData.value,
      headers: headers,
      row_count: rawData.value.length,
      column_count: headers.length
    }]
    showWorkbookViewer.value = true
    return
  }
  
  alert('No workbook data available. Please upload a file first.')
}

function closeWorkbookViewer() {
  showWorkbookViewer.value = false
}

function workOnSelectedSheet() {
  if (!currentSheetName.value) {
    alert('Please select a sheet first.')
    return
  }
  const sheet = workbookSheets.value.find(s => s.name === currentSheetName.value)
  if (!sheet || !sheet.data || !sheet.data.length) {
    alert('No data found in the selected sheet.')
    return
  }
  handleWorkOnSheet(currentSheetName.value)
  showWorkbookViewer.value = false
  activeTab.value = 'upload'
  forceUpdate.value++
}

function handleProcessSheetFromModal(payload) {
  console.log('📊 Processing from modal viewer:', payload.sheetName)
  console.log('📈 Rows:', payload.data.length)
  console.log('📋 Headers:', payload.headers)
  
  worksheetStatus.value[payload.sheetName] = 'in_progress'
  
  rawData.value = payload.data
  originalRawData.value = JSON.parse(JSON.stringify(payload.data))
  originalFileColumns.value = payload.headers || []
  fileColumns.value = [...originalFileColumns.value]
  currentSheetName.value = payload.sheetName
  
  const sheetDetection = detectSheetType(payload.data, instrumentType.value)
  console.log('🔍 Sheet type detection:', sheetDetection)
  
  sheetType.value = sheetDetection.type
  
  if (sheetDetection.type === 'single') {
    console.log('📋 Single-instrument sheet detected - extracting values')
    handleSingleInstrumentSheet(payload.data, payload.sheetName)
  } else {
    console.log('📊 Multi-instrument sheet detected - proceeding with mapping workflow')
    handleMultiInstrumentSheet(payload.data, payload.headers)
  }
}

function handleMultiInstrumentSheet(data, headers) {
  columnMapping.value = autoMatchColumns(headers, requiredColumns.value, columnVariations.value)
  applyCurrentMapping()
  showMappingDialog.value = true
  console.log('✅ Multi-instrument sheet processed, mapping dialog shown')
}

function handleSingleInstrumentSheet(data, sheetName) {
  const fieldMappings = getRequiredFieldMappings(instrumentType.value)
  const extractedValues = extractSingleInstrumentValues(data, fieldMappings)
  
  console.log('📋 Extracted values:', extractedValues)
  
  const tabularData = convertExtractedToTabular(extractedValues)
  
  rawData.value = tabularData
  originalRawData.value = JSON.parse(JSON.stringify(tabularData))
  fileColumns.value = Object.keys(tabularData[0] || {})
  originalFileColumns.value = [...fileColumns.value]
  
  columnMapping.value = {}
  fileColumns.value.forEach(col => {
    const requiredCol = findMatchingRequiredColumn(col, requiredColumns.value)
    if (requiredCol) {
      columnMapping.value[requiredCol] = col
    }
  })
  
  applyCurrentMapping()
  activeTab.value = 'preview'
  
  console.log('✅ Single-instrument sheet processed, skipping to preview')
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
  console.log(`🔍 Auto-detection: ${matchCount}/${systemColumns.length} matches (${(matchRatio * 100).toFixed(1)}%)`)
  
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

// ---- Process instrument data and update summaries ----
function processInstrumentData(sheetName, data, instrumentType) {
  console.log(`🎯 Processing ${instrumentType} data from sheet: ${sheetName}`)
  
  const instruments = detectInstruments(data)
  
  if (instruments.length > 1) {
    console.log(`📊 Multiple instruments detected (${instruments.length}), processing each separately`)
    return calculateAllInstruments(instruments, sheetName, instrumentType)
  }
  
  const results = runInstrumentCalculations(data, instrumentType)
  
  const instrumentResult = {
    Source: sheetName,
    instrumentName: sheetName,
    instrumentType: instrumentType,
    ...results
  }
  
  const newColumns = buildDynamicColumns([...instrumentSummary.value.rows, instrumentResult])
  instrumentSummary.value.rows.push(instrumentResult)
  instrumentSummary.value.columns = newColumns
  
  const sid = activeSession.value?.id || sessionManager.getActiveSessionId()
  if (sid) {
    const summaryKey = `${instrumentType.value}_session_${sid}_summary`
    localStorage.setItem(summaryKey, JSON.stringify(instrumentSummary.value))
  }
  
  worksheetStatus.value[sheetName] = 'completed'
  console.log('✅ Worksheet marked as completed:', sheetName)
  
  // Sync portfolioSummary with instrumentSummary to ensure they match
  portfolioSummary.value.rows = [...instrumentSummary.value.rows]
  portfolioSummary.value.columns = [...instrumentSummary.value.columns]
  
  console.log('✅ Instrument processed and saved to summaries')
  console.log('📊 Dynamic columns:', newColumns)
  
  if (instruments.length > 1 && !showAllCalculationsPopup.value) {
    setTimeout(() => {
      showAllCalculationsPopup.value = true
    }, 500)
  }
}

function calculateAllInstruments(instruments, sheetName, instrumentType) {
  const results = []
  
  instruments.forEach((data, index) => {
    const result = runInstrumentCalculations(data, instrumentType)
    const instrumentResult = {
      Source: sheetName,
      instrumentName: `${sheetName} - Instrument ${index + 1}`,
      instrumentType: instrumentType,
      ...result
    }
    results.push(instrumentResult)
  })
  
  const newColumns = buildDynamicColumns([...instrumentSummary.value.rows, ...results])
  instrumentSummary.value.rows.push(...results)
  instrumentSummary.value.columns = newColumns
  
  const sid = activeSession.value?.id || sessionManager.getActiveSessionId()
  if (sid) {
    const summaryKey = `${instrumentType.value}_session_${sid}_summary`
    localStorage.setItem(summaryKey, JSON.stringify(instrumentSummary.value))
  }
  
  worksheetStatus.value[sheetName] = 'completed'
  console.log('✅ Worksheet marked as completed:', sheetName)
  
  // Sync portfolioSummary with instrumentSummary to ensure they match
  portfolioSummary.value.rows = [...instrumentSummary.value.rows]
  portfolioSummary.value.columns = [...instrumentSummary.value.columns]
  
  console.log(`✅ Processed ${results.length} instruments from sheet`)
  console.log('📊 Dynamic columns:', newColumns)
  
  if (results.length > 1 && !showAllCalculationsPopup.value) {
    setTimeout(() => {
      showAllCalculationsPopup.value = true
    }, 500)
  }
  
  return results
}

function runInstrumentCalculations(data, instrumentType) {
  const results = {}
  
  if (data.length === 0) return results
  
  const getNumber = (val) => {
    const num = parseFloat(val)
    return isNaN(num) ? 0 : num
  }
  
  const findColumn = (patterns) => {
    const availableCols = Object.keys(data[0] || {})
    for (const pattern of patterns) {
      const found = availableCols.find(col => 
        col.toLowerCase().includes(pattern.toLowerCase()) || 
        pattern.toLowerCase().includes(col.toLowerCase())
      )
      if (found) return found
    }
    return null
  }
  
  const amountCol = findColumn(['Amount', 'FaceValue', 'Face Value', 'Principal', 'Value', 'Notional', 'Nominal', 'Par Value', 'Investment'])
  const rateCol = findColumn(['Rate', 'InterestRate', 'Interest Rate', 'CouponRate', 'Coupon Rate', 'DiscountRate', 'Discount Rate', 'Yield', 'YTM'])
  const instrumentCol = findColumn(['Instrument', 'Instrument Name', 'Name', 'Security', 'Description'])
  
  const totalValue = data.reduce((s, r) => s + getNumber(r[amountCol] || 0), 0)
  const totalRate = data.reduce((s, r) => s + getNumber(r[rateCol] || 0), 0)
  const weightedSum = data.reduce((s, r) => s + (getNumber(r[rateCol] || 0) * getNumber(r[amountCol] || 0)), 0)
  const avgRateVal = totalRate / (data.length || 1)
  
  if (instrumentType === 'money-market') {
    results['Total Value'] = totalValue
    results['Instrument Count'] = data.length
    results['Avg Rate'] = avgRateVal.toFixed(2)
    results['Weighted Avg Rate'] = (totalValue > 0 ? (weightedSum / totalValue).toFixed(2) : '0.00')
    results['Total Interest'] = (totalValue * avgRateVal / 100).toFixed(2)
    results['Interest Earned'] = (totalValue * avgRateVal / 100 * 90 / 365).toFixed(2)
    results['Annual Yield'] = ((Math.pow(1 + avgRateVal / 100, 365 / 90) - 1) * 100).toFixed(2)
    results['Effective Annual Rate'] = ((Math.pow(1 + avgRateVal / 100, 1) - 1) * 100).toFixed(2)
    results['Avg Days to Maturity'] = 90
    results['Total Principal'] = totalValue
  } else if (instrumentType === 'bonds') {
    const yieldCol = findColumn(['Yield', 'YTM', 'YieldToMaturity']) || rateCol
    const totalYield = data.reduce((s, r) => s + getNumber(r[yieldCol] || 0), 0)
    const avgCoupon = totalRate / (data.length || 1)
    const avgYieldVal = totalYield / (data.length || 1)
    
    results['Total Value'] = totalValue
    results['Instrument Count'] = data.length
    results['Avg Coupon Rate'] = avgCoupon.toFixed(2)
    results['Weighted Avg Coupon'] = (totalValue > 0 ? (weightedSum / totalValue).toFixed(2) : '0.00')
    results['Total Annual Income'] = (totalValue * avgCoupon / 100).toFixed(2)
    results['Avg YTM'] = avgYieldVal.toFixed(2)
    results['Duration'] = (10 * 0.7).toFixed(2)
  } else {
    const avgDiscount = totalRate / (data.length || 1)
    const discountAmount = totalValue * (avgDiscount / 100) * 91 / 360
    const price = totalValue - discountAmount
    
    results['Total Value'] = totalValue
    results['Instrument Count'] = data.length
    results['Avg Discount Rate'] = avgDiscount.toFixed(2)
    results['Weighted Avg Discount'] = (totalValue > 0 ? (weightedSum / totalValue).toFixed(2) : '0.00')
    results['Total Discount'] = discountAmount.toFixed(2)
    results['Effective Yield'] = (price > 0 ? ((Math.pow(1 + discountAmount / price, 365 / 91) - 1) * 100).toFixed(2) : '0.00')
    results['Bond Equivalent Yield'] = (price > 0 ? ((discountAmount / price) * (365 / 91) * 100).toFixed(2) : '0.00')
    results['Discount Yield'] = (totalValue > 0 ? ((discountAmount / totalValue) * (360 / 91) * 100).toFixed(2) : '0.00')
    results['Price per 100'] = (100 * (1 - (avgDiscount / 100) * (91 / 360))).toFixed(2)
    results['Total Purchase Price'] = price.toFixed(2)
    results['Avg Investment'] = (data.length > 0 ? (price / data.length).toFixed(2) : '0.00')
    results['Avg Days to Maturity'] = 91
  }
  
  return results
}

function editInstrumentRow(index, field, value) {
  instrumentSummary.value.rows[index][field] = value
  console.log(`✅ Edited instrument row ${index}, field ${field}: ${value}`)
}

function editPortfolioRow(index, field, value) {
  portfolioSummary.value.rows[index][field] = value
  console.log(`✅ Edited portfolio row ${index}, field ${field}: ${value}`)
}

function formatCellValue(value, col) {
  if (value === null || value === undefined || value === '') return '-'
  
  if (typeof value === 'number' && !isNaN(value)) {
    if (isPercentageField(col)) {
      return (value * 100).toFixed(2) + '%'
    }
    return value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
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
  return total.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function exportSummary() {
  const summaryData = {
    instrumentType: selectedInstrumentType.value,
    summary: portfolioSummary.value.rows,
    columns: portfolioSummary.value.columns
  }
  
  console.log('📥 Exporting summary:', summaryData)
  
  const blob = new Blob([JSON.stringify(summaryData, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${selectedInstrumentType.value.replace(' ', '_')}_Portfolio_Summary.json`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
  
  alert('Summary exported successfully!')
}

function viewInstrumentSummaryExcel() {
  showInstrumentExcelPopup.value = true
  sortColumn.value = ''
  sortOrder.value = 'asc'
  console.log('📊 Opening Instrument Summary Excel popup')
}

function closeInstrumentExcelPopup() {
  showInstrumentExcelPopup.value = false
}

function sortByColumn(col) {
  if (sortColumn.value === col) {
    sortOrder.value = sortOrder.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortColumn.value = col
    sortOrder.value = 'asc'
  }
}

function exportInstrumentSummaryExcel() {
  const summaryData = {
    instrumentType: selectedInstrumentType.value,
    summary: instrumentSummary.value.rows,
    columns: instrumentSummary.value.columns
  }
  
  console.log('📥 Exporting Instrument Summary as Excel:', summaryData)
  
  const blob = new Blob([JSON.stringify(summaryData, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${selectedInstrumentType.value.replace(' ', '_')}_Instrument_Summary.json`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
  
  alert('Instrument Summary exported successfully!')
}

function viewPortfolioSummaryExcel() {
  showPortfolioExcelPopup.value = true
  console.log('📊 Opening Portfolio Summary Excel popup')
}

function closePortfolioExcelPopup() {
  showPortfolioExcelPopup.value = false
}

function exportPortfolioSummaryExcel() {
  // Use the same data as displayed in the portfolio summary
  const data = portfolioSummary.value.rows
  const columns = portfolioSummaryColumnsForDisplay.value
  
  // Filter data to only include displayed columns
  const filteredData = data.map(row => {
    const filteredRow = {}
    columns.forEach(col => {
      filteredRow[col] = row[col]
    })
    return filteredRow
  })
  
  console.log('📥 Exporting Portfolio Summary as Excel:', filteredData)
  
  // Create worksheet from filtered data
  const worksheet = XLSX.utils.json_to_sheet(filteredData)
  const workbook = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(workbook, worksheet, 'Portfolio Summary')
  
  // Generate Excel file
  XLSX.writeFile(workbook, `${selectedInstrumentType.value.replace(' ', '_')}_Portfolio_Summary.xlsx`)
  
  alert('Portfolio Summary exported successfully as Excel!')
}

function openWorkflowPopup(row, idx) {
  selectedWorkflowInstrument.value = row
  selectedWorkflowIndex.value = idx
  showWorkflowPopup.value = true
  console.log('🔄 Opening workflow popup for instrument:', row['Instrument Name'] || `Instrument ${idx + 1}`)
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
    else { alert('No data'); return }
  }
  excelData.value = data
  excelColumns.value = Object.keys(data[0] || {})
  excelDialogTitle.value = title || 'Data Review'
  showExcelDialog.value = true
}

function openInstrumentDataExcel() {
  // Create filtered data showing only calculations and yield curve values
  const instrumentData = []
  
  // Add calculation values
  const calcRow = {
    'Metric': 'Calculations',
    'Total Value': calculations.value.totalValue || 0,
    'Average Rate': calculations.value.avgRate || 0,
    'Weighted Average Rate': calculations.value.weightedAvgRate || 0,
    'Total Interest': calculations.value.totalInterest || 0,
    'Annual Yield': calculations.value.annualYield || 0,
    'Effective Annual Rate': calculations.value.effectiveAnnualRate || 0
  }
  
  // Add instrument-specific calculations
  if (instrumentType.value === 'bonds') {
    calcRow['Average Coupon Rate'] = calculations.value.avgCouponRate || 0
    calcRow['Weighted Average Coupon'] = calculations.value.weightedAvgCoupon || 0
    calcRow['Average YTM'] = calculations.value.avgYTM || 0
    calcRow['Duration'] = calculations.value.duration || 0
  } else if (instrumentType.value === 'tbills') {
    calcRow['Average Discount Rate'] = calculations.value.avgDiscountRate || 0
    calcRow['Weighted Average Discount'] = calculations.value.weightedAvgDiscount || 0
    calcRow['Effective Yield'] = calculations.value.effectiveYield || 0
  }
  
  instrumentData.push(calcRow)
  
  // Add FRED benchmark data if available
  if (calculations.value.fred) {
    const fredRow = {
      'Metric': 'FRED Benchmark',
      'Series ID': calculations.value.fred.series_id || '',
      'Series Label': calculations.value.fred.series_label || '',
      'Benchmark Rate': calculations.value.fred.benchmark_rate || 0,
      'Spread vs Market': calculations.value.fred.spread_vs_market || 0,
      'Country': calculations.value.fred.country || '',
      'Currency': calculations.value.fred.currency || '',
      'Maturity': calculations.value.fred.maturity || ''
    }
    instrumentData.push(fredRow)
  }
  
  excelData.value = instrumentData
  excelColumns.value = Object.keys(instrumentData[0] || {})
  excelDialogTitle.value = `${instrumentName} - Calculations & Yield Curve`
  showExcelDialog.value = true
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
  if (!uploadedFile.value) { alert('Please upload a file first.'); return }
  if (!rawData.value.length) { alert('No data loaded. Please upload a valid file.'); return }
  saveSessionData()
  await nextTick()
  activeTab.value = 'cleaning'
  await nextTick()
  debouncedSave()
  forceUpdate.value++
  const sid = activeSession.value?.id || sessionManager.getActiveSessionId()
  if (sid) {
    await markStepCompleted(String(sid), 'upload')
    saveSessionData()
  }
}

// ===== CLEANING =====
function applyCleaning() {
  if (!rawData.value.length) return
  
  const tableDetection = autoDetectTable(rawData.value)
  let data = JSON.parse(JSON.stringify(rawData.value))
  
  if (tableDetection.type === 'table') {
    console.log('🧹 Cleaning raw table data')
    data = tableDetection.data.map((row, idx) => {
      const obj = {}
      tableDetection.headers.forEach((header, i) => {
        obj[header] = row[i] !== undefined ? row[i] : ''
      })
      return obj
    })
  }
  
  if (cleaningOptions.value.removeDuplicates) {
    const seen = new Set()
    data = data.filter(row => { const key = JSON.stringify(row); if (seen.has(key)) return false; seen.add(key); return true })
  }
  if (cleaningOptions.value.removeEmptyRows) data = data.filter(row => Object.values(row).some(v => v !== null && v !== '' && v !== undefined))
  if (cleaningOptions.value.trimWhitespace) data = data.map(row => { const newRow = {}; Object.keys(row).forEach(k => { newRow[k] = typeof row[k] === 'string' ? row[k].trim() : row[k] }); return newRow })
  if (cleaningOptions.value.convertToNumbers) data = data.map(row => { const newRow = { ...row }; Object.keys(newRow).forEach(k => { if (typeof newRow[k] === 'string' && !isNaN(newRow[k]) && newRow[k].trim() !== '') newRow[k] = parseFloat(newRow[k]) }); return newRow })
  if (cleaningOptions.value.fillMissingText) data = data.map(row => { Object.keys(row).forEach(k => { if (row[k] === undefined || row[k] === null || row[k] === '') row[k] = 'N/A' }); return row })
  if (cleaningOptions.value.dropRowsWithMissing) data = data.filter(row => Object.values(row).every(v => v !== null && v !== '' && v !== undefined && (typeof v !== 'number' || !isNaN(v))))
  if (cleaningOptions.value.removeOutliers) {
    const numericCols = Object.keys(data[0] || {}).filter(col => data.some(row => typeof row[col] === 'number'))
    for (const col of numericCols) {
      const values = data.map(r => r[col]).filter(v => typeof v === 'number')
      const mean = values.reduce((a, b) => a + b, 0) / values.length
      const std = Math.sqrt(values.map(v => Math.pow(v - mean, 2)).reduce((a, b) => a + b, 0) / values.length)
      const threshold = 3 * std
      data = data.filter(row => Math.abs(row[col] - mean) <= threshold)
    }
  }
  if (cleaningOptions.value.standardizeDates) data = data.map(row => { Object.keys(row).forEach(k => { if (k.toLowerCase().includes('date') && row[k]) { const d = new Date(row[k]); if (!isNaN(d)) row[k] = d.toISOString().split('T')[0] } }); return row })
  if (cleaningOptions.value.removeSpecialChars) data = data.map(row => { Object.keys(row).forEach(k => { if (typeof row[k] === 'string') row[k] = row[k].replace(/[^a-zA-Z0-9\s]/g, '') }); return row })
  if (cleaningOptions.value.changeCase && cleaningOptions.value.caseType !== 'none') data = data.map(row => { Object.keys(row).forEach(k => { if (typeof row[k] === 'string') { if (cleaningOptions.value.caseType === 'upper') row[k] = row[k].toUpperCase(); else if (cleaningOptions.value.caseType === 'lower') row[k] = row[k].toLowerCase(); else if (cleaningOptions.value.caseType === 'title') row[k] = row[k].replace(/\b\w/g, l => l.toUpperCase()) } }); return row })
  if (cleaningOptions.value.fillWithCustom && cleaningOptions.value.customFillValue) data = data.map(row => { Object.keys(row).forEach(k => { if (row[k] === undefined || row[k] === null || row[k] === '') row[k] = cleaningOptions.value.customFillValue }); return row })
  if (cleaningOptions.value.removeColumnsAllMissing) {
    const colsToKeep = Object.keys(data[0] || {}).filter(col => data.some(row => row[col] !== null && row[col] !== '' && row[col] !== undefined))
    data = data.map(row => { const newRow = {}; colsToKeep.forEach(c => newRow[c] = row[c]); return newRow })
  }
  if (cleaningOptions.value.capOutliers) {
    const numericCols = Object.keys(data[0] || {}).filter(col => data.some(row => typeof row[col] === 'number'))
    for (const col of numericCols) {
      const values = data.map(r => r[col]).filter(v => typeof v === 'number')
      const mean = values.reduce((a, b) => a + b, 0) / values.length
      const std = Math.sqrt(values.map(v => Math.pow(v - mean, 2)).reduce((a, b) => a + b, 0) / values.length)
      const upper = mean + 3 * std, lower = mean - 3 * std
      data = data.map(row => { if (row[col] > upper) row[col] = upper; if (row[col] < lower) row[col] = lower; return row })
    }
  }
  if (cleaningOptions.value.removeRowsSpecificColumnEmpty && cleaningOptions.value.specificColumn) data = data.filter(row => row[cleaningOptions.value.specificColumn] !== null && row[cleaningOptions.value.specificColumn] !== '')
  if (cleaningOptions.value.standardizeNumericRange) {
    const numericCols = Object.keys(data[0] || {}).filter(col => data.some(row => typeof row[col] === 'number'))
    for (const col of numericCols) {
      const values = data.map(r => r[col]).filter(v => typeof v === 'number')
      const min = Math.min(...values), max = Math.max(...values)
      if (max !== min) data = data.map(row => { if (typeof row[col] === 'number') row[col] = (row[col] - min) / (max - min); return row })
    }
  }
  if (cleaningOptions.value.fillForward) { for (let i = 1; i < data.length; i++) Object.keys(data[i]).forEach(k => { if (data[i][k] === undefined || data[i][k] === null || data[i][k] === '') data[i][k] = data[i-1][k] }) }
  if (cleaningOptions.value.fillBackward) { for (let i = data.length - 2; i >= 0; i--) Object.keys(data[i]).forEach(k => { if (data[i][k] === undefined || data[i][k] === null || data[i][k] === '') data[i][k] = data[i+1][k] }) }
  cleanedData.value = data
  cleaningStats.value = { totalRows: rawData.value.length, validRows: cleanedData.value.length, removedRows: rawData.value.length - cleanedData.value.length, fixedMissing: 0 }
  debouncedSave()
  forceUpdate.value++
}

async function continueAfterCleaning() {
  if (!cleanedData.value.length) {
    alert('Please clean your data first.')
    return
  }
  // Save cleaned data before proceeding
  saveSessionData()
  try {
    await calculateMetrics()
  } catch (err) {
    console.error('Error calculating metrics:', err)
    alert('There was an error calculating metrics, but you can proceed to calculations.')
  }
  goToCalculations()
  forceUpdate.value++
  const sid = activeSession.value?.id || sessionManager.getActiveSessionId()
  if (sid) {
    await markStepCompleted(String(sid), 'cleaning')
    saveSessionData()
  }
}

// ===== CALCULATIONS (BACKEND + SYNC TO SUMMARIES) =====
async function calculateMetrics() {
  if (!cleanedData.value.length) {
    console.warn('No cleaned data to calculate')
    return
  }

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
    if (response?.success && response?.data) {
      calculations.value = response.data
      formulas.value = response.data.formulas || {}
      
      // ---- USE BACKEND FOR INSTRUMENT SUMMARY ----
      if (activeSession.value?.id) {
        try {
          const summaryResponse = await api.calculationsAPI.getInstrumentSummary(
            activeSession.value.id,
            instrumentType.value
          )
          if (summaryResponse?.success && summaryResponse?.data) {
            instrumentSummary.value = summaryResponse.data
          }
        } catch (err) {
          console.error('Failed to fetch instrument summary from backend:', err)
          // Fallback to frontend calculation if backend fails
          const summaryRow = {
            'Instrument Name': instrumentName.value,
            'Instrument Type': instrumentType.value,
            'Total Value': calculations.value.totalValue || 0,
            'Instrument Count': calculations.value.instrumentCount || 0,
            'Avg Rate': calculations.value.avgRate || 0,
            'Weighted Avg Rate': calculations.value.weightedAvgRate || 0,
            'Total Interest': calculations.value.totalInterest || 0,
            'Interest Earned': calculations.value.interestEarned || 0,
            'Annual Yield': calculations.value.annualYield || 0,
            'Effective Annual Rate': calculations.value.effectiveAnnualRate || 0,
            'Avg Days to Maturity': calculations.value.avgDaysToMaturity || 0,
            'Total Principal': calculations.value.totalPrincipal || 0,
            'Weighted Avg Coupon': calculations.value.weightedAvgCoupon || 0,
            'Total Annual Income': calculations.value.totalAnnualIncome || 0,
            'Avg YTM': calculations.value.avgYTM || 0,
            'Duration': calculations.value.duration || 0,
            'Weighted Avg Discount': calculations.value.weightedAvgDiscount || 0,
            'Total Discount': calculations.value.totalDiscount || 0,
            'Effective Yield': calculations.value.effectiveYield || 0,
            'Bond Equivalent Yield': calculations.value.bondEquivalentYield || 0,
            'Price per 100': calculations.value.pricePer100 || 0,
            'Total Purchase Price': calculations.value.totalPurchasePrice || 0,
            'Avg Investment': calculations.value.avgInvestment || 0,
            'Holding Period Yield': calculations.value.holdingPeriodYield || 0,
            'Annualized Yield': calculations.value.annualizedYield || 0,
            'FRED Benchmark': calculations.value.fred?.benchmark_rate || null
          }
          
          // Use unique identifier (Instrument Name) to avoid duplicates
          const uniqueId = summaryRow['Instrument Name'] || 'Instrument'
          const existingIndex = instrumentSummary.value.rows.findIndex(r => 
            (r['Instrument Name'] || 'Instrument') === uniqueId
          )
          if (existingIndex !== -1) {
            // Update existing instrument instead of duplicating
            instrumentSummary.value.rows[existingIndex] = { ...summaryRow, 'Worksheet': currentSheetName.value }
          } else {
            // Add new instrument with worksheet identifier
            instrumentSummary.value.rows.push({ ...summaryRow, 'Worksheet': currentSheetName.value })
          }
          const allFields = new Set()
          instrumentSummary.value.rows.forEach(r => {
            Object.keys(r).forEach(k => allFields.add(k))
          })
          instrumentSummary.value.columns = Array.from(allFields)
        }
      }
      
      // Also update portfolioSummary using backend
      if (activeSession.value?.id) {
        try {
          const portfolioResponse = await api.calculationsAPI.getPortfolioSummary(activeSession.value.id)
          if (portfolioResponse?.success && portfolioResponse?.data) {
            portfolioSummary.value = portfolioResponse.data
          }
        } catch (err) {
          console.error('Failed to fetch portfolio summary from backend:', err)
          // Fallback to frontend calculation
          const portExisting = portfolioSummary.value.rows.findIndex(r => r['Instrument Type'] === instrumentType.value)
          if (portExisting !== -1) {
            portfolioSummary.value.rows.splice(portExisting, 1)
          }
          portfolioSummary.value.rows.push(summaryRow)
          const portFields = new Set()
          portfolioSummary.value.rows.forEach(r => {
            Object.keys(r).forEach(k => portFields.add(k))
          })
          portfolioSummary.value.columns = Array.from(portFields)
        }
      }
      
      // Save to localStorage
      const sid = activeSession.value?.id || sessionManager.getActiveSessionId()
      if (sid) {
        const summaryKey = `${instrumentType.value}_session_${sid}_summary`
        localStorage.setItem(summaryKey, JSON.stringify(instrumentSummary.value))
        const portfolioKey = `${instrumentType.value}_session_${sid}_portfolio`
        localStorage.setItem(portfolioKey, JSON.stringify(portfolioSummary.value))
      }
      
      console.log('✅ Calculations synced to instrumentSummary and portfolioSummary')
      
      // If multiple instruments, show the popup
      if (instrumentSummary.value.rows.length >= 2 && !showAllCalculationsPopup.value) {
        setTimeout(() => {
          showAllCalculationsPopup.value = true
        }, 500)
      }
      
      saveSessionData()
    } else {
      console.error('Backend calculation failed:', response?.message)
    }
  } catch (err) {
    console.error('Error calling backend calculation:', err)
  }
  await enrichCalculationsWithFred()
  debouncedSave()
  forceUpdate.value++
}

function updateInput(key, value) {
  manualInputs.value[key] = parseFloat(value) || 0
}

async function recalculateWithInputs() {
  await calculateMetrics()
}

async function continueToVisualizations() {
  if (!hasCleanedData.value) { alert('Please clean your data first.'); return }
  goToVisualizations()
  forceUpdate.value++
  saveSessionData()
  const sid = activeSession.value?.id || sessionManager.getActiveSessionId()
  if (sid) {
    await markStepCompleted(String(sid), 'calculations')
    saveSessionData()
  }
}

async function continueFromVisualizations() {
  if (!hasCleanedData.value) { alert('Please clean your data first.'); return }
  saveSessionData()
  activeTab.value = 'summary'
  forceUpdate.value++
  const sid = activeSession.value?.id || sessionManager.getActiveSessionId()
  if (sid) {
    await markStepCompleted(String(sid), 'visualizations')
    saveSessionData()
  }
}

// ===== FRED / VISUALIZATIONS =====
const yieldCurveCache = new Map()
const CACHE_TTL = 5 * 60 * 1000

async function fetchYieldCurve() {
  const country = effectiveCountry.value
  const maturity = effectiveMaturity.value
  const currency = effectiveCurrency.value || 'USD'

  const supportedCountries = ['USA', 'GBR', 'EUR', 'JPN', 'CAN', 'AUS', 'CHE', 'NZL', 'NOR', 'SWE', 'DNK', 'BRA', 'MEX', 'IND', 'CHN', 'KOR', 'SGP', 'HKG', 'RUS', 'TUR', 'SAU', 'ARE', 'ISR', 'ZAF']
  if (!country || !supportedCountries.includes(country) && country !== '__custom__') {
    yieldCurveError.value = `Country "${country || 'none'}" is not supported. Please select one from the list or use Custom.`
    yieldCurveData.value = []
    return
  }
  if (!maturity) {
    yieldCurveError.value = 'Please select a maturity.'
    return
  }

  const cacheKey = `${instrumentType.value}_${country}_${currency}_${maturity}`
  const cached = yieldCurveCache.get(cacheKey)
  if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
    yieldCurveData.value = cached.data
    chartSeriesLabel.value = 'Yield Curve (cached)'
    await nextTick()
    await renderYieldCurveChart()
    updateFredBenchmark()
    debouncedSave()
    forceUpdate.value++
    return
  }

  yieldCurveLoading.value = true
  yieldCurveError.value = ''

  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), 10000)

  try {
    const payload = { instrument_type: instrumentType.value, country, currency, maturity }
    const response = await api.visualizationAPI.getYieldCurve(payload, { signal: controller.signal })
    if (response.success && response.data && response.data.maturities && response.data.maturities.length) {
      const data = response.data
      const points = data.maturities.map((m, idx) => ({
        maturity: parseFloat(m),
        maturityLabel: data.labels?.[idx] || m,
        rate: data.rates[idx]
      }))
      yieldCurveCache.set(cacheKey, { data: points, timestamp: Date.now() })
      yieldCurveData.value = points
      chartSeriesLabel.value = 'Yield Curve'
      await nextTick()
      await renderYieldCurveChart()
      updateFredBenchmark()
      debouncedSave()
      forceUpdate.value++
    } else {
      yieldCurveError.value = response.error || 'No data returned from FRED for the selected parameters.'
      yieldCurveData.value = []
    }
  } catch (err) {
    if (err.name === 'AbortError') {
      yieldCurveError.value = 'Request timed out. Please try again.'
    } else {
      console.error('Yield curve fetch error:', err)
      yieldCurveError.value = err.message || 'Failed to load yield curve.'
    }
    yieldCurveData.value = []
  } finally {
    clearTimeout(timeoutId)
    yieldCurveLoading.value = false
  }
}

function updateFredBenchmark() {
  const benchRate = getRateForMaturity(effectiveMaturity.value)
  if (benchRate != null) {
    calculations.value.fred = {
      benchmark_rate: benchRate,
      series_label: effectiveMaturity.value,
      spread_vs_market: +(portfolioAvgRate.value - benchRate).toFixed(2),
      country: effectiveCountry.value,
      currency: effectiveCurrency.value,
      maturity: effectiveMaturity.value
    }
  }
}

async function renderYieldCurveChart() {
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

  const period = effectiveMaturity.value
  let multiplier = 1
  let totalUnits = 0
  let unitLabel = ''
  let stepSize = 1
  
  const match = period.match(/^(\d+)([YMW])$/)
  if (match) {
    const num = parseInt(match[1], 10)
    const unit = match[2]
    
    if (unit === 'Y') {
      multiplier = 1
      totalUnits = num
      unitLabel = 'Years'
      stepSize = num > 5 ? 5 : 1
    } else if (unit === 'M') {
      multiplier = 1
      totalUnits = num
      unitLabel = 'Months'
      stepSize = num > 6 ? 6 : 1
    } else if (unit === 'W') {
      multiplier = 1
      totalUnits = num
      unitLabel = 'Weeks'
      stepSize = num > 4 ? 2 : 1
    }
  } else {
    multiplier = 1
    const num = parseFloat(period) || 10
    totalUnits = num
    unitLabel = 'Years'
    stepSize = num > 5 ? 5 : 1
  }

  const maxMat = parseFloat(period) || 10
  const filtered = yieldCurveData.value.filter(d => d.maturity <= maxMat)
  if (!filtered.length) {
    yieldCurveError.value = 'No data available for the selected maturity.'
    return
  }

  const transformed = filtered.map(d => {
    let xValue = d.maturity
    if (unitLabel === 'Months' && d.maturity < 1) {
      xValue = d.maturity * 12
    } else if (unitLabel === 'Weeks' && d.maturity < 1) {
      xValue = d.maturity * 52
    }
    return { x: xValue, y: d.rate, label: d.maturityLabel }
  })
  
  const maxX = Math.max(totalUnits, Math.max(...transformed.map(p => p.x))) + 0.5

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
            stepSize: stepSize,
            autoSkip: false,
            callback: function(value) {
              if (Number.isInteger(value) && value >= 0) return value.toString()
              return null
            }
          }
        },
        y: {
          title: { display: true, text: 'Yield (%)' },
          beginAtZero: false
        }
      }
    }
  })
}

// ---- Custom filter handlers ----
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
    fredFilters.value.maturity = customMaturityInput.value || '1Y'
  }
  onFredFilterChange()
}

let fredFilterTimeout = null
async function onFredFilterChange() {
  if (fredFilterTimeout) clearTimeout(fredFilterTimeout)
  fredFilterTimeout = setTimeout(async () => {
    if (activeTab.value === 'visualizations') await fetchYieldCurve()
    if (Object.keys(calculations.value).length) await enrichCalculationsWithFred()
    debouncedSave()
  }, 500)
}

async function enrichCalculationsWithFred() {
  try {
    const bench = await fetchBenchmark(instrumentType.value)
    if (bench?.benchmark_rate != null) {
      const portfolio = parseFloat(portfolioAvgRate.value) || 0
      calculations.value.fred = {
        ...bench,
        spread_vs_market: +(portfolio - bench.benchmark_rate).toFixed(2)
      }
    } else {
      if (calculations.value.fred) delete calculations.value.fred
    }
  } catch (e) {
    console.error('FRED benchmark fetch error:', e)
  }
}

// ===== SAVED MAPPINGS TEMPLATES =====
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
    alert('Please enter a template name.')
    return
  }
  const hasAnyMapping = requiredColumns.value.some(col => columnMapping.value[col])
  if (!hasAnyMapping) {
    alert('Cannot save template: no columns are mapped.')
    return
  }
  savedTemplates.value[newTemplateName.value] = {
    mapping: { ...columnMapping.value },
    timestamp: Date.now()
  }
  saveTemplates()
  alert(`Template "${newTemplateName.value}" saved.`)
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

// ===== CALCULATION INSTRUMENT SELECTOR =====
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
  
  // Populate calculation fields with the selected instrument's data
  calculations.value = {
    totalValue: parseFloat(selectedRow['Total Value'] || selectedRow['Calculated Value'] || 0),
    instrumentCount: 1,
    avgRate: parseFloat(selectedRow['Avg Rate'] || 0),
    avgCouponRate: parseFloat(selectedRow['Avg Coupon Rate'] || 0),
    avgDiscountRate: parseFloat(selectedRow['Avg Discount Rate'] || 0),
    weightedAvgRate: parseFloat(selectedRow['Weighted Avg Rate'] || 0),
    weightedAvgCoupon: parseFloat(selectedRow['Weighted Avg Coupon'] || 0),
    weightedAvgDiscount: parseFloat(selectedRow['Weighted Avg Discount'] || 0),
    totalInterest: parseFloat(selectedRow['Total Interest'] || 0),
    interestEarned: parseFloat(selectedRow['Interest Earned'] || 0),
    annualYield: parseFloat(selectedRow['Annual Yield'] || 0),
    effectiveAnnualRate: parseFloat(selectedRow['Effective Annual Rate'] || 0),
    avgDaysToMaturity: parseFloat(selectedRow['Avg Days to Maturity'] || 0),
    // Add all other calculation fields from the row
    ...Object.keys(selectedRow).reduce((acc, key) => {
      if (key !== 'Instrument Name' && key !== 'Instrument Type' && typeof selectedRow[key] === 'number') {
        acc[key] = selectedRow[key]
      }
      return acc
    }, {})
  }
  
  console.log('✅ Loaded instrument calculations:', instrumentName)
  closeAllCalculationsPopup()
}

function formatTableCell(value, column) {
  if (value === null || value === undefined || value === '') return '—'
  
  // Format currency columns
  if (column.toLowerCase().includes('value') || column.toLowerCase().includes('amount') || column.toLowerCase().includes('price')) {
    return '$' + formatNumber(value)
  }
  
  // Format percentage columns
  if (column.toLowerCase().includes('rate') || column.toLowerCase().includes('yield') || column.toLowerCase().includes('coupon') || column.toLowerCase().includes('discount')) {
    return formatNumber(value) + '%'
  }
  
  // Format dates
  if (column.toLowerCase().includes('date') && typeof value === 'string') {
    return value
  }
  
  // Default formatting
  return typeof value === 'number' ? formatNumber(value) : value
}

function openAllCalculationsPopup() {
  showAllCalculationsPopup.value = true
  console.log('📊 Opening all calculations popup')
}

function closeAllCalculationsPopup() {
  showAllCalculationsPopup.value = false
}

function exportAllCalculations() {
  const allData = instrumentSummary.value.rows
  const columns = instrumentSummary.value.columns
  
  const worksheet = XLSX.utils.json_to_sheet(allData)
  const workbook = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(workbook, worksheet, 'All Calculations')
  XLSX.writeFile(workbook, 'all_instruments_calculations.xlsx')
  
  alert('All calculations exported successfully!')
}

// ===== SESSION MANAGEMENT =====
function notifySessionUpdated(explicitSave = false, saveOptions = {}) {
  if (!activeSession.value) return
  const sid = activeSession.value.id
  const instrumentCount = sessionManager.countSessionInstruments(sid)
  sessionManager.updateSession(sid, { instrumentCount })
  const detail = {
    sessionId: sid,
    explicitSave,
    ...saveOptions
  }
  if (!explicitSave) detail.skipCapture = true
  window.dispatchEvent(new CustomEvent('session-updated', { detail }))
}

async function saveToSession() {
  if (!activeSession.value) {
    alert('Please select or create a session on the Dashboard first.')
    return
  }
  
  const datasetSnapshot = {
    rawData: rawData.value,
    cleanedData: cleanedData.value,
    calculations: calculations.value,
    columnMapping: columnMapping.value,
    worksheetStatus: worksheetStatus.value,
    workbookSheets: workbookSheets.value,
    instrumentSummary: instrumentSummary.value,
    portfolioSummary: portfolioSummary.value,
    yieldCurveData: yieldCurveData.value,
    fredFilters: { country: effectiveCountry.value, currency: effectiveCurrency.value, maturity: effectiveMaturity.value },
    manualInputs: manualInputs.value,
    formulas: formulas.value
  }

  try {
    console.log('📝 Creating version for session:', activeSession.value.id, 'instrument:', instrumentType.value)
    const response = await api.versionAPI.create(
      activeSession.value.id,
      instrumentType.value,
      `Saved ${instrumentName.value} from ${activeTab.value}`,
      datasetSnapshot,
      null,
      null,
      null,
      null,
      null
    )
    console.log('✅ Version created:', response)

    await sessionManager.saveInstrumentWorkflow(activeSession.value.id, instrumentType.value, {
      ...datasetSnapshot,
      uploadedFile: uploadedFile.value?.name || null,
      cleaningStats: cleaningStats.value,
      sessionSavedAt: new Date().toISOString()
    })

    // Trigger dashboard refresh to get updated counts from backend
    window.dispatchEvent(new CustomEvent('session-updated', { detail: { sessionId: activeSession.value.id } }))

    alert('✅ Saved to session. A new version has been recorded in Version History.')
  } catch (err) {
    console.error('Failed to save version:', err)
    alert('❌ Failed to save to session: ' + err.message)
  }
}

function saveSessionData() {
  if (!activeSession.value) return
  const sid = activeSession.value.id
  const datasetSnapshot = {
    rawData: rawData.value,
    cleanedData: cleanedData.value,
    calculations: calculations.value,
    columnMapping: columnMapping.value,
    fileColumns: fileColumns.value,
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
  sessionManager.saveInstrumentWorkflow(sid, instrumentType.value, datasetSnapshot)
    .then(() => {
      const count = sessionManager.countSessionInstruments(sid)
      sessionManager.updateSession(sid, { instrument_count: Math.min(count, 3) })
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
      columnMapping.value = wf.columnMapping || {}
      fileColumns.value = wf.fileColumns || []
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
        selectedMaturityOption.value = wf.fredFilters.maturity || defaultMaturityForInstrument()
      }
      if (wf.uploadedFile) {
        uploadedFile.value = { name: wf.uploadedFile, size: 0 }
      }
      if (wf.cleaningStats) cleaningStats.value = wf.cleaningStats
      if (wf.sessionSavedAt) sessionSavedAt.value = wf.sessionSavedAt
      loaded = true
    }
  } catch (err) {
    console.error('Failed to load saved data:', err)
  }
  return loaded
}

function debouncedSave(explicitSave = false) {
  if (saveTimeout) clearTimeout(saveTimeout)
  const now = Date.now()
  if (!explicitSave && now - lastSaveTime < SAVE_DEBOUNCE_MS) return
  saveTimeout = setTimeout(() => {
    saveSessionData()
    lastSaveTime = Date.now()
  }, explicitSave ? 100 : SAVE_DEBOUNCE_MS)
}

function showFormula(metricKey) {
  const formulas = {
    'Total Portfolio Value': 'Σ (Face Value or Amount) for all rows',
    'Average Rate': 'Σ (Rate, CouponRate, or DiscountRate) / Number of Instruments',
    'Number of Instruments': 'Count of distinct Instrument/BondName/TBillName (unique securities)',
    'weightedAvgRate': 'Σ (Rate × Amount) / Σ Amount',
    'totalInterest': 'Total Value × Average Rate / 100',
    'interestEarned': 'Total Interest × (90/365)',
    'annualYield': '((1 + AvgRate/100)^(365/90) - 1) × 100',
    'effectiveAnnualRate': '((1 + AvgRate/100) - 1) × 100',
    'avgDaysToMaturity': 'Average of DaysToMaturity column',
    'totalPrincipal': 'Sum of Principal/Amount',
    'weightedAvgCoupon': 'Σ (CouponRate × FaceValue) / Σ FaceValue',
    'totalAnnualIncome': 'Total Face Value × Avg Coupon Rate / 100',
    'avgYTM': 'Average of Yield column',
    'duration': 'Approximated Macaulay duration (10 years × 0.7)',
    'weightedAvgDiscount': 'Σ (DiscountRate × FaceValue) / Σ FaceValue',
    'totalDiscount': 'Total Face Value × Avg Discount Rate / 100 × 91/360',
    'effectiveYield': '((1 + TotalDiscount/Price)^(365/91) - 1) × 100',
    'bondEquivalentYield': '(TotalDiscount/Price) × (365/91) × 100',
    'pricePer100': '100 × (1 - (DiscountRate/100) × (91/360))',
    'totalPurchasePrice': 'Total Face Value - Total Discount',
    'avgInvestment': 'Total Purchase Price / Number of Instruments',
    'holdingPeriodYield': '(TotalDiscount/Price) × 100',
    'annualizedYield': '(TotalDiscount/Price) × (365/91) × 100'
  }
  formulaText.value = formulas[metricKey] || 'No formula available for this metric.'
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
      let totalValue = 0
      let totalFaceValue = 0
      let totalAvgRate = 0
      rows.forEach(row => {
        const value = parseFloat(row['Total Value'] || row['Calculated Value'] || 0)
        const faceValue = parseFloat(row['Face Value'] || row['Amount'] || row['Principal'] || 0)
        const rate = parseFloat(row['Avg Rate'] || row['Coupon Rate'] || row['Discount Rate'] || 0)
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

// ===== REPORT PREVIEW DATA (FIXED - reads from instrumentSummary) =====
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
    if (selected) {
      const data = getInstrumentData(key)
      if (data && data.totalValue > 0) {
        instrumentsData.push({ 
          name: type.label, 
          calculations: data,
          id: key
        })
      }
    }
  }
  
  // If no instruments have data, check if instrumentSummary has any rows
  if (instrumentsData.length === 0 && instrumentSummary.value.rows.length > 0) {
    // Include all instruments from summary
    const summaryRows = instrumentSummary.value.rows
    const grouped = {}
    summaryRows.forEach(row => {
      const type = row['Instrument Type'] || 'unknown'
      if (!grouped[type]) grouped[type] = []
      grouped[type].push(row)
    })
    
    for (const [type, rows] of Object.entries(grouped)) {
      let totalValue = 0
      let instrumentCount = rows.length
      let totalAvgRate = 0
      rows.forEach(row => {
        const value = parseFloat(row['Total Value'] || row['Calculated Value'] || 0)
        const rate = parseFloat(row['Avg Rate'] || row['Coupon Rate'] || row['Discount Rate'] || 0)
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
    instruments: instrumentsData 
  }
})

// ===== REPORT GENERATION =====
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
    if (key.includes('Value') || key.includes('Price') || key.includes('Interest') || key.includes('Income') || key.includes('Discount') || key.includes('Principal') || key.includes('Investment'))
      return `$${value.toLocaleString()}`
    if (key.includes('Rate') || key.includes('Yield') || key.includes('Coupon') || key.includes('Discount'))
      return `${value}%`
    return value.toLocaleString()
  }
  return value
}

async function captureChartImage() {
  return new Promise((resolve) => {
    // Wait a moment for chart to fully render
    setTimeout(() => {
      const canvas = yieldCurveChart.value
      if (canvas && canvas.toDataURL) {
        try {
          const dataUrl = canvas.toDataURL('image/png', 1.0)
          resolve(dataUrl)
          return
        } catch (e) { console.warn('Canvas capture failed', e) }
      }
      const canvasEl = document.querySelector('.chart-container--fred canvas')
      if (canvasEl && canvasEl.toDataURL) {
        try {
          const dataUrl = canvasEl.toDataURL('image/png', 1.0)
          resolve(dataUrl)
          return
        } catch (e) { console.warn('DOM canvas capture failed', e) }
      }
      // Try alternative selectors
      const altCanvas = document.querySelector('canvas')
      if (altCanvas && altCanvas.toDataURL) {
        try {
          const dataUrl = altCanvas.toDataURL('image/png', 1.0)
          resolve(dataUrl)
          return
        } catch (e) { console.warn('Alternative canvas capture failed', e) }
      }
      resolve('')
    }, 500)
  })
}

function buildMethodologySection(selectedInstrumentNames) {
  let methods = []
  if (selectedInstrumentNames.includes('Money Market')) methods.push(`<div class="methodology-card"><h4>Money Market Instruments</h4><p class="formula">Fair value = <sup>F</sup> &frasl; <sub>1 + r·t/365</sub></p><p>Where: <strong>F</strong> = Face value, <strong>r</strong> = annualized interest rate (%), <strong>t</strong> = days to maturity.</p><p>Simple interest convention (365 days/year). Weighted average rate = Σ (Rate × Amount) / Σ Amount.</p></div>`)
  if (selectedInstrumentNames.includes('Bonds')) methods.push(`<div class="methodology-card"><h4>Bonds</h4><p class="formula">Fair value = Σ<sub>t=1</sub><sup>n</sup> <sup>C</sup> &frasl; <sub>(1+y)<sup>t</sup></sub> + <sup>FV</sup> &frasl; <sub>(1+y)<sup>n</sup></sub></p><p>Where: <strong>C</strong> = annual coupon payment (CouponRate × FaceValue), <strong>y</strong> = yield to maturity (%), <strong>FV</strong> = face value, <strong>n</strong> = years to maturity.</p><p>Duration = Σ (t × PV(C<sub>t</sub>)) / Price. Approximated using Macaulay duration.</p></div>`)
  if (selectedInstrumentNames.includes('T-Bills')) methods.push(`<div class="methodology-card"><h4>Treasury Bills (T‑Bills)</h4><p class="formula">Discount amount = Face value × (Discount rate / 100) × (Days to maturity / 360)</p><p class="formula">Effective yield = (Face value / Price − 1) × (365 / Days to maturity) × 100</p><p>Bank discount basis (360 days/year) for discount rate; bond equivalent yield uses 365 days.</p></div>`)
  return methods.length ? methods.join('') : '<p>No methodology available for the selected instruments.</p>'
}

const logoUrl = '/DuraCapital logo.png'
const backgroundCoverUrl = '/reportbackground.png'

async function generateReportHtml() {
  await loadSavedData()
  const report = reportPreviewData.value
  if (report.instruments.length === 0) {
    alert('No data available for the selected instruments. Please ensure you have run calculations and have data in the instrument summary.')
    return null
  }

  let chartImageData = ''
  try {
    chartImageData = await captureChartImage()
  } catch (e) { console.warn('Chart capture failed', e) }

  const valuationDate = new Date().toISOString().split('T')[0]
  const reportDate = new Date().toLocaleString()
  const totalPortfolioValue = report.instruments.reduce((sum, inst) => sum + (parseFloat(inst.calculations.totalValue) || 0), 0)
  const totalInstrumentCount = report.instruments.reduce((sum, inst) => sum + (parseInt(inst.calculations.instrumentCount) || 0), 0)

  let appendixRows = ''
  let allDataRows = []
  for (const inst of report.instruments) {
    const instKey = inst.id || (inst.name === 'Money Market' ? 'money-market' : inst.name === 'Bonds' ? 'bonds' : 'tbills')
    let cleanData = []
    const wf = await sessionManager.getInstrumentWorkflow(activeSession.value?.id, instKey)
    if (wf && wf.cleanedData && wf.cleanedData.length) cleanData = wf.cleanedData
    else {
      const sid = activeSession.value?.id
      if (sid) {
        const saved = localStorage.getItem(`${instKey}_session_${sid}_clean`)
        if (saved) cleanData = JSON.parse(saved)
      }
    }
    if (cleanData && cleanData.length) {
      cleanData.forEach((item, idx) => {
        const name = item.Instrument || item.BondName || item.TBillName || `${inst.name} ${idx + 1}`
        const ticker = item.BBTicker || item.Ticker || item.Security || ''
        const faceValue = parseFloat(item.FaceValue || item.Amount || item.Principal || 0)
        const rate = parseFloat(item.Rate || item.InterestRate || item.CouponRate || item.DiscountRate || 0)
        const term = parseFloat(item.Term || item.YearsToMaturity || 0) || (parseFloat(item.MaturityDate) ? (new Date(item.MaturityDate) - new Date(item.IssueDate || Date.now())) / (365 * 24 * 60 * 60 * 1000) : 0)
        allDataRows.push({ instrument: inst.name, name, ticker, faceValue, rate, term, valuationDate })
      })
    }
  }
  if (allDataRows.length) {
    appendixRows = allDataRows.map(r => `
      <tr>
        <td>${r.instrument}</td>
        <td>${r.name}</td>
        <td>${r.ticker}</td>
        <td>${r.faceValue.toFixed(2)}</td>
        <td>${r.rate.toFixed(4)}%</td>
        <td>${r.term.toFixed(2)}</td>
        <td>${r.valuationDate}</td>
      </tr>
    `).join('')
  }

  const methodologyHtml = buildMethodologySection(report.instruments.map(i => i.name))
  const chartHtml = chartImageData ? `
    <div class="chart-container">
      <img src="${chartImageData}" alt="Yield Curve" style="max-width:100%; height:auto; border-radius:8px; border:1px solid #e0e0e0;" />
      <p class="chart-caption">FRED Yield Curve – ${report.instruments.map(i => i.name).join(', ')}</p>
    </div>
  ` : '<p>Yield curve chart not available.</p>'

  const html = `<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Valuation Assessment Report - ${report.session}</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: 'Arial', sans-serif; color: #000; background: white; line-height: 1.6; margin: 0; padding: 0; }
    .page { page-break-after: always; padding: 30px 40px; min-height: 100vh; position: relative; width: 210mm; margin: 0 auto; background: white; }
    .page:last-child { page-break-after: auto; }
    .cover-page { background-color: white; background-image: url('${backgroundCoverUrl}'); background-size: 45%; background-position: right center; background-repeat: no-repeat; color: black; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; padding: 40px 50px; position: relative; min-height: 100vh; width: 210mm; margin: 0 auto; }
    .cover-content { max-width: 70%; position: relative; z-index: 2; color: black; }
    .cover-logo { position: absolute; top: 30px; left: 40px; z-index: 3; }
    .cover-logo img { max-width: 160px; height: auto; background: white; padding: 4px; }
    .cover-session-name { font-size: 44px; font-weight: 300; letter-spacing: 2px; margin-bottom: 10px; color: #000; }
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
    @media print { .page { padding: 30px 40px; width: 210mm; } .cover-page { padding: 40px 50px; width: 210mm; } .executive-summary { background: #f8f9ff !important; -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; } }
    table, img, .chart-container { max-width: 100%; }
  </style>
</head>
<body>

<div class="page cover-page">
  <div class="cover-content">
    <h1 class="cover-title">Valuation Assessment Report</h1>
    <p class="cover-subtitle">${report.instruments.map(i => i.name).join(' & ')}</p>
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
  <h1 class="section-title">Appendix: Detailed Instrument Data</h1>
  <p><strong>Valuation Date:</strong> ${valuationDate}</p>
  <p><strong>Total Instruments:</strong> ${allDataRows.length}</p>
  <br>
  ${allDataRows.length ? `
  <table class="appendix-table">
    <thead><tr><th>Asset Class</th><th>Instrument Name</th><th>BB Ticker</th><th>Face Value ($)</th><th>Rate (%)</th><th>Term (Yrs)</th><th>Valuation Date</th></tr></thead>
    <tbody>${appendixRows}</tbody>
  </table>
  ` : '<p>No detailed instrument data available.</p>'}
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
    reportPreviewHtml.value = html
    reportPreviewDialog.value = true
  } else {
    alert('No data available to generate the report. Please run calculations first.')
  }
}

async function downloadFromPreview(format) {
  if (!reportPreviewHtml.value) return
  const filename = `combined_report_${Date.now()}`
  
  if (format === 'html') {
    // Ensure HTML includes all styles for proper formatting
    const htmlWithStyles = reportPreviewHtml.value
    downloadBlob(htmlWithStyles, `${filename}.html`, 'text/html')
  } else if (format === 'pdf') {
    // Open in new window with print dialog for better PDF generation
    const win = window.open('', '_blank')
    win.document.write(reportPreviewHtml.value)
    win.document.close()
    setTimeout(() => win.print(), 500)
  } else if (format === 'word') {
    // Use proper MIME type for Word documents
    downloadBlob(reportPreviewHtml.value, `${filename}.doc`, 'application/msword')
  }
}

async function exportToRealExcel() {
  await loadSavedData()
  const report = reportPreviewData.value
  if (report.instruments.length === 0) { alert('No data available for the selected instruments.'); return }
  const workbook = XLSX.utils.book_new()
  const valuationDate = new Date().toISOString().split('T')[0]
  
  const summaryData = []
  summaryData.push(['', '', ''])
  summaryData.push(['DuraCapital', '', ''])
  summaryData.push(['Valuation Assessment Report', '', ''])
  summaryData.push([`Session: ${report.session}`, '', ''])
  summaryData.push([`Valuation Date: ${valuationDate}`, '', ''])
  summaryData.push(['', '', ''])
  summaryData.push(['Report Generated', new Date().toLocaleString(), ''])
  summaryData.push(['', '', ''])
  summaryData.push(['Instrument', 'Metric', 'Value'])
  
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
        const faceValue = parseFloat(item.FaceValue || item.Amount || item.Principal || 0)
        const rate = parseFloat(item.Rate || item.InterestRate || item.CouponRate || item.DiscountRate || 0)
        const term = parseFloat(item.Term || item.YearsToMaturity || 0) || (parseFloat(item.MaturityDate) ? (new Date(item.MaturityDate) - new Date(item.IssueDate || Date.now())) / (365 * 24 * 60 * 60 * 1000) : 0)
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
      const sheet = XLSX.utils.json_to_sheet(instrumentData)
      XLSX.utils.book_append_sheet(workbook, sheet, inst.name.substring(0, 31))
    }
  }
  XLSX.writeFile(workbook, `portfolio_report_${Date.now()}.xlsx`)
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

// ===== WATCHERS & LIFECYCLE =====
watch([rawData, cleanedData], () => debouncedSave(), { deep: true })
watch(cleanedData, async (newVal) => { if (newVal.length) await calculateMetrics() }, { deep: true })
watch(() => activeTab.value, async (newTab) => {
  if (newTab === 'calculations' && hasCleanedData.value) {
    await calculateMetrics()
  }
  if (newTab === 'visualizations' && hasCleanedData.value && !yieldCurveData.value.length && !yieldCurveLoading.value) {
    if (!effectiveCountry.value) { selectedCountryOption.value = 'USA'; fredFilters.value.country = 'USA' }
    if (!effectiveMaturity.value) { const def = defaultMaturityForInstrument(); selectedMaturityOption.value = def; fredFilters.value.maturity = def }
    await fetchYieldCurve()
  }
})
watch([rawData, cleanedData, calculations, yieldCurveData], () => { forceUpdate.value++ }, { deep: true })
watch(yieldCurveData, async () => {
  if (activeTab.value === 'visualizations' && yieldCurveData.value.length) {
    await nextTick()
    await renderYieldCurveChart()
  }
}, { deep: true })

async function checkAndReset() {
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
      if (!rawData.value.length && !cleanedData.value.length) {
        // keep empty
      }
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
        if (!effectiveMaturity.value) { const def = defaultMaturityForInstrument(); selectedMaturityOption.value = def; fredFilters.value.maturity = def }
        await fetchYieldCurve()
      }
    }
    debouncedSave()
  }
}

onMounted(async () => {
  await loadConfig(instrumentType.value)
  const qSid = route.query.session
  if (qSid) {
    await sessionManager.getSession(String(qSid))
    const s = await sessionManager.getSession(String(qSid))
    if (s) { activeSession.value = s; sessionManager.setActiveSession(s) }
  }
  await checkAndReset()
  loadUploadHistory()
  loadSavedTemplates()
  window.addEventListener('storage', () => checkAndReset())
  await loadFilterOptions()
  if (!effectiveMaturity.value) { const def = defaultMaturityForInstrument(); selectedMaturityOption.value = def; fredFilters.value.maturity = def }
  if (Object.keys(calculations.value).length) enrichCalculationsWithFred()
  if (!calculations.value.totalValue && activeSession.value) await loadSavedData()
  if (cleanedData.value.length) await calculateMetrics()
  debouncedSave()
})

onBeforeUnmount(() => {
  window.removeEventListener('storage', () => checkAndReset())
  saveSessionData()
})
watch(() => route.params.type, () => checkAndReset(), { immediate: true })
</script>

<style scoped>
/* ===== INSTRUMENT PAGE STYLES ===== */
.instrument-page { padding: 20px; max-width: 1400px; margin: 0 auto; }

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 25px;
  padding: 16px 20px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
  flex-wrap: wrap;
  gap: 12px;
}

.header-left { flex: 1; min-width: 200px; }
.header-left h1 { color: #0B2044; font-size: 26px; font-weight: 700; margin: 0 0 6px 0; }
.header-left .session-badge { display: inline-flex; align-items: center; gap: 6px; background: #e8ecf1; padding: 4px 12px; border-radius: 20px; font-size: 13px; color: #0B2044; }
.header-left .session-badge.warning { background: #fff3e0; color: #e65100; }
.header-left .session-badge strong { color: #0B2044; }

.header-right { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; margin-top: 4px; }

.btn-save-session {
  background: linear-gradient(135deg, #0B2044, #1E88E5);
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  transition: all 0.3s;
  white-space: nowrap;
}
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

.content-card { margin-bottom: 20px; }

.upload-area { border: 2px dashed #ccc; border-radius: 12px; padding: 50px; text-align: center; cursor: pointer; transition: all 0.3s; }
.upload-area:hover { border-color: #0B2044; background: #f8f9ff; }
.browse-link { color: #0B2044; cursor: pointer; font-weight: 600; }

.file-info { margin-top: 20px; padding: 12px; background: #f5f5f5; border-radius: 8px; display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.file-size { font-size: 11px; color: #999; margin-left: auto; }
.remove-btn { margin-left: auto; background: none; border: none; font-size: 20px; cursor: pointer; color: #f44336; }

.btn-preview { background: #2196F3; color: white; border: none; padding: 6px 12px; border-radius: 6px; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; font-size: 12px; margin-left: 10px; transition: all 0.2s; }
.btn-preview:hover:not(:disabled) { background: #0b7dda; transform: translateY(-1px); }
.btn-preview:disabled { opacity: 0.5; cursor: not-allowed; }

.btn-review-excel { background: #4CAF50; color: white; border: none; padding: 6px 12px; border-radius: 6px; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; font-size: 12px; margin-left: 10px; transition: all 0.2s; }
.btn-review-excel:hover:not(:disabled) { background: #45a049; transform: translateY(-1px); }
.btn-review-excel:disabled { opacity: 0.5; cursor: not-allowed; }

.btn-mapping { background: #FF9800; color: white; border: none; padding: 6px 12px; border-radius: 6px; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; font-size: 12px; margin-left: 10px; transition: all 0.2s; }
.btn-mapping:hover:not(:disabled) { background: #F57C00; transform: translateY(-1px); }
.btn-mapping:disabled { opacity: 0.5; cursor: not-allowed; }

.btn-view-workbook { background: #9C27B0; color: white; border: none; padding: 6px 12px; border-radius: 6px; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; font-size: 12px; margin-left: 10px; transition: all 0.2s; }
.btn-view-workbook:hover:not(:disabled) { background: #7B1FA2; transform: translateY(-1px); }
.btn-view-workbook:disabled { opacity: 0.5; cursor: not-allowed; }

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

/* No-logo header for workbook viewer */
.excel-dialog-title-no-logo {
  background: #f5f5f5;
  color: #0B2044;
  padding: 12px 24px;
  display: flex;
  align-items: center;
  border-bottom: 2px solid #d0d0d0;
}
.excel-dialog-title-no-logo span { font-weight: 600; font-size: 18px; }

.btn-work-on-sheet {
  background: #0B2044;
  color: white;
  border: none;
  padding: 8px 20px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  transition: all 0.2s;
  margin-right: 12px;
}
.btn-work-on-sheet:hover { background: #1a3a6e; transform: translateY(-1px); box-shadow: 0 4px 12px rgba(11,32,68,0.2); }

.excel-dialog-title-white {
  background: white;
  color: #0B2044;
  padding: 16px 24px;
  display: flex;
  align-items: center;
  border-bottom: 2px solid #e0e0e0;
}
.excel-dialog-title-white .logo {
  height: 40px;
  width: auto;
  object-fit: contain;
}
.excel-dialog-title-white .header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}
.excel-dialog-title-white .header-title h4 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #0B2044;
}
.excel-dialog-title-white .header-meta {
  margin: 2px 0 0 0;
  font-size: 13px;
  color: #666;
}
.excel-dialog-title-white .btn-close-dialog {
  background: transparent;
  border: none;
  color: #666;
  cursor: pointer;
  padding: 8px;
  border-radius: 50%;
  font-size: 20px;
}
.excel-dialog-title-white .btn-close-dialog:hover {
  background: #f0f0f0;
  color: #0B2044;
}

.btn-close-dialog { background: transparent; border: none; color: #666; cursor: pointer; padding: 8px; border-radius: 50%; }
.btn-close-dialog:hover { background: #f0f0f0; color: #0B2044; }
.excel-dialog-content { padding: 0; height: calc(100vh - 140px); }

.required-columns { margin: 20px 0; }
.columns-list { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 10px; }
.column-badge { background: #e8ecf1; padding: 6px 12px; border-radius: 20px; font-size: 12px; display: inline-flex; align-items: center; gap: 6px; }
.column-badge.missing-column { background: #FFEBEE; color: #c62828; }
.column-badge.mapped-column { background: #E8F5E9; color: #2E7D32; }
.success-message { margin-top: 10px; padding: 8px 12px; background: #E8F5E9; border-radius: 8px; display: flex; align-items: center; gap: 8px; font-size: 12px; color: #2E7D32; }
.warning-message { margin-top: 10px; padding: 8px 12px; background: #FFF3E0; border-radius: 8px; display: flex; align-items: center; gap: 8px; font-size: 12px; color: #E65100; }

.cleaning-options-panel { background: #f8f9ff; padding: 20px; border-radius: 12px; margin-bottom: 20px; }
.filter-scroll-container { max-height: 200px; overflow-y: auto; border: 1px solid #e0e0e0; border-radius: 8px; background: #fafafa; margin: 12px 0; padding: 8px 4px; }
.options-list { display: flex; flex-direction: column; gap: 8px; }
.option-checkbox { display: flex; align-items: center; gap: 8px; font-size: 14px; padding: 4px 8px; border-radius: 4px; transition: background 0.1s; flex-wrap: wrap; }
.option-checkbox:hover { background: #f0f0f0; }
.option-checkbox select, .option-checkbox input[type="text"] { margin-left: 4px; padding: 2px 6px; font-size: 13px; border: 1px solid #ccc; border-radius: 4px; }
.cleaning-buttons { display: flex; gap: 12px; margin-top: 15px; flex-wrap: wrap; }

.summary-cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 30px; }
.summary-card { background: linear-gradient(135deg, #1B5E20, #4CAF50); padding: 20px; border-radius: 16px; color: white; text-align: center; display: flex; flex-direction: column; align-items: center; justify-content: center; cursor: pointer; transition: transform 0.2s; }
.summary-card.total { background: linear-gradient(135deg, #1B5E20, #4CAF50); }
.summary-card.rate { background: linear-gradient(135deg, #0D47A1, #2196F3); }
.summary-card.count { background: linear-gradient(135deg, #E65100, #FF9800); }
.summary-card:hover { transform: translateY(-3px); box-shadow: 0 6px 12px rgba(0,0,0,0.15); }
.card-label { font-size: 14px; opacity: 0.9; margin-bottom: 8px; }
.card-value { font-size: 28px; font-weight: 700; }

.calculations-section { margin-top: 10px; }
.calculations-section h3 { color: #0B2044; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 2px solid #0B2044; }
.calculations-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; margin-bottom: 30px; }
.calculation-card { padding: 20px; background: linear-gradient(135deg, #f8f9ff, #fff); border-radius: 12px; text-align: center; border: 1px solid rgba(11,32,68,0.1); transition: transform 0.2s; cursor: pointer; }
.calculation-card:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
.calc-name { font-size: 14px; color: #666; margin-bottom: 10px; }
.calc-value { font-size: 24px; font-weight: 700; color: #0B2044; margin-bottom: 5px; }

.comparison-card { background: linear-gradient(135deg, #f8f9ff, #eef2ff); border-radius: 12px; padding: 16px; margin-bottom: 20px; display: flex; justify-content: space-around; align-items: center; flex-wrap: wrap; gap: 15px; }
.comparison-item { text-align: center; }
.comparison-label { font-size: 13px; color: #666; display: block; }
.comparison-value { font-size: 24px; font-weight: 700; }
.comparison-value.portfolio { color: #0B2044; }
.comparison-value.market { color: #1E88E5; }
.comparison-difference { font-size: 16px; font-weight: 600; padding: 4px 12px; border-radius: 20px; }
.comparison-difference.positive { background: #e8f5e9; color: #2e7d32; }
.comparison-difference.negative { background: #ffebee; color: #c62828; }

.btn-calculated-instruments {
  background: #0B2044;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  transition: all 0.2s;
}
.btn-calculated-instruments:hover { background: #1a3a6e; transform: translateY(-1px); box-shadow: 0 4px 12px rgba(11,32,68,0.2); }

.viewing-badge {
  background: #e8f5e9;
  color: #2e7d32;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 13px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-left: 12px;
}

.calc-header-left {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.calc-title {
  font-size: 20px;
  font-weight: 600;
  color: #0B2044;
}

.viewing-badge-large {
  background: linear-gradient(135deg, #0B2044 0%, #1a3a6e 100%);
  color: white;
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 8px;
  box-shadow: 0 2px 8px rgba(11, 32, 68, 0.2);
}

.viewing-label {
  opacity: 0.9;
  font-weight: 500;
}

.viewing-name {
  font-weight: 700;
  font-size: 15px;
}

.instrument-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
  margin-top: 16px;
}
.instrument-card {
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 12px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.2s;
}
.instrument-card:hover { border-color: #0B2044; box-shadow: 0 4px 16px rgba(11,32,68,0.12); transform: translateY(-2px); }
.instrument-card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; padding-bottom: 8px; border-bottom: 1px solid #eee; }
.instrument-card-header strong { color: #0B2044; font-size: 14px; }
.instrument-type-badge { background: #e8ecf1; color: #0B2044; padding: 2px 10px; border-radius: 12px; font-size: 11px; font-weight: 600; }
.instrument-card-body { display: flex; flex-direction: column; gap: 6px; }
.card-metric { display: flex; justify-content: space-between; font-size: 13px; padding: 2px 0; }
.metric-label { color: #666; }
.metric-value { color: #0B2044; font-weight: 600; }
.instrument-card-footer { margin-top: 12px; padding-top: 8px; border-top: 1px solid #eee; }
.btn-select-instrument { background: #0B2044; color: white; border: none; padding: 6px 12px; border-radius: 6px; cursor: pointer; font-size: 12px; font-weight: 600; display: inline-flex; align-items: center; gap: 4px; width: 100%; justify-content: center; transition: all 0.2s; }
.btn-select-instrument:hover { background: #1a3a6e; }

.popup-header-white {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  background: white;
  border-bottom: 2px solid #e0e0e0;
  flex-shrink: 0;
}
.popup-header-white .header-left { display: flex; align-items: center; gap: 16px; }
.popup-header-white .logo { height: 40px; width: auto; object-fit: contain; }
.popup-header-white .header-title h4 { margin: 0; font-size: 18px; font-weight: 600; color: #0B2044; }
.popup-header-white .header-meta { margin: 2px 0 0 0; font-size: 13px; color: #666; }
.popup-header-white .close-btn {
  background: transparent;
  border: none;
  color: #666;
  cursor: pointer;
  font-size: 24px;
  padding: 4px 8px;
  border-radius: 50%;
}
.popup-header-white .close-btn:hover { background: #f0f0f0; color: #0B2044; }

.popup-body { flex: 1; overflow-y: auto; padding: 20px; }
.popup-instruction { color: #666; margin-bottom: 16px; font-size: 14px; }

.popup-footer {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 12px;
  padding: 12px 24px;
  background: #f9fafc;
  border-top: 1px solid #e0e0e0;
  flex-shrink: 0;
  flex-wrap: wrap;
}
.valuation-date-footer { color: #666; font-size: 13px; }

.viewing-indicator { display: inline-flex; align-items: center; gap: 4px; color: #2e7d32; font-size: 14px; }

.navigation-buttons { display: flex; gap: 15px; justify-content: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e0e0e0; flex-wrap: wrap; }
.btn-primary { background: linear-gradient(135deg, #0B2044, #1E88E5); color: white; border: none; padding: 12px 28px; border-radius: 10px; font-size: 14px; font-weight: 600; cursor: pointer; transition: all 0.3s; }
.btn-primary:hover:not(:disabled) { transform: translateY(-2px); box-shadow: 0 6px 15px rgba(11,32,68,0.3); }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-secondary { background: white; color: #0B2044; border: 2px solid #0B2044; padding: 12px 28px; border-radius: 10px; font-size: 14px; font-weight: 600; cursor: pointer; transition: all 0.3s; }
.btn-secondary:hover { background: #0B2044; color: white; transform: translateY(-2px); }

.excel-table-wrapper { overflow: auto; border: 1px solid #d4d4d4; border-radius: 4px; background: white; max-height: 500px; margin: 16px 0; }
.excel-table { width: 100%; border-collapse: collapse; font-size: 13px; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #000; }
.excel-table thead { position: sticky; top: 0; z-index: 10; }
.excel-table th { background: #0B2044; color: white; border: 1px solid #1a3a6e; padding: 10px 14px; text-align: left; font-weight: 600; font-size: 12px; white-space: nowrap; letter-spacing: 0.3px; }
.excel-table td { border: 1px solid #d4d4d4; padding: 8px 14px; text-align: left; font-size: 13px; font-variant-numeric: tabular-nums; }
.excel-table tbody tr:nth-child(even) { background: #f9fafc; }
.excel-table tbody tr:hover { background: #e8f0fe; }
.excel-table tfoot tr.total-row { background: #0B2044 !important; color: white; font-weight: 700; }
.excel-table tfoot td { border: 1px solid #1a3a6e; padding: 10px 14px; font-weight: 700; font-size: 14px; }
.excel-table tfoot td:first-child { text-align: right; padding-right: 20px; }

.sortable-header { cursor: pointer; transition: background 0.2s; }
.sortable-header:hover { background: #1a3a6e; }
.sort-indicator { margin-left: 6px; font-size: 10px; color: #fff; }

.excel-popup-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0,0,0,0.6);
  z-index: 99999;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}
.excel-popup-content {
  background: white;
  border-radius: 12px;
  max-width: 95%;
  max-height: 90vh;
  width: 1400px;
  display: flex;
  flex-direction: column;
  box-shadow: 0 25px 60px rgba(0,0,0,0.3);
  overflow: hidden;
  position: relative;
  z-index: 100000;
}

.filters-row { display: flex; gap: 20px; align-items: flex-end; margin-bottom: 20px; flex-wrap: wrap; }
.filter-group label { display: block; font-size: 12px; font-weight: 600; color: #0B2044; margin-bottom: 4px; }
.filter-group { position: relative; display: flex; align-items: center; flex-wrap: wrap; flex: 1; min-width: 150px; }
.filter-select { width: 100%; padding: 10px 32px 10px 12px; border: 1px solid #ccc; border-radius: 8px; background: linear-gradient(to bottom, #ffffff 0%, #f5f7fa 100%); color: #0B2044; font-size: 14px; cursor: pointer; transition: border 0.2s, box-shadow 0.2s; box-shadow: 0 2px 4px rgba(0,0,0,0.08), inset 0 1px 2px rgba(255,255,255,0.8); appearance: none; -webkit-appearance: none; }
.filter-select:focus { outline: none; border-color: #0B2044; box-shadow: 0 0 0 3px rgba(11,32,68,0.15), 0 4px 8px rgba(0,0,0,0.1); }
.filter-group .filter-arrow { position: absolute; right: 12px; top: 50%; transform: translateY(-50%); pointer-events: none; font-size: 14px; color: #0B2044; font-weight: bold; }
.filter-custom-input {
  width: 100%;
  padding: 8px 12px;
  margin-top: 4px;
  border: 1px solid #ccc;
  border-radius: 6px;
  font-size: 13px;
  background: white;
  transition: border 0.2s;
}
.filter-custom-input:focus {
  outline: none;
  border-color: #0B2044;
  box-shadow: 0 0 0 2px rgba(11,32,68,0.1);
}

.chart-container--fred { position: relative; height: 400px; width: 100%; background: white; border-radius: 8px; padding: 10px; }
.chart-container--fred canvas { width: 100% !important; height: 100% !important; }

.loading-container, .error-container { text-align: center; padding: 40px; }
.spin { animation: spin 1s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

.visualization-placeholder { text-align: center; padding: 60px; background: #f8f9ff; border-radius: 12px; }
.visualization-placeholder h3 { color: #0B2044; margin: 20px 0 10px; }
.visualization-placeholder p { color: #666; margin-bottom: 20px; }

.summary-hero { display: flex; justify-content: space-around; flex-wrap: wrap; gap: 24px; margin-bottom: 24px; padding: 30px 20px; background: linear-gradient(135deg, #0B2044, #1E88E5); border-radius: 16px; color: white; text-align: center; }
.hero-stat { flex: 1; min-width: 140px; display: flex; flex-direction: column; align-items: center; }
.hero-value { font-size: 32px; font-weight: 700; margin-bottom: 4px; }
.hero-label { font-size: 14px; opacity: 0.9; }

.summary-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; margin-bottom: 30px; }
.summary-section { padding: 20px; background: #f8f9ff; border-radius: 12px; }
.summary-section h3 { color: #0B2044; margin-bottom: 15px; }
.summary-section p { margin: 8px 0; color: #555; }
.card-panel { background: #f8f9ff; padding: 16px; border-radius: 10px; border: 1px solid #e8ecf1; }

.instrument-summary-section, .portfolio-summary-section { margin: 30px 0; padding: 20px; background: white; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }
.instrument-summary-section h3, .portfolio-summary-section h3 { color: #0B2044; font-size: 18px; margin-bottom: 15px; display: flex; align-items: center; gap: 8px; }

.instrument-breakdown { margin: 20px 0; padding: 15px; background: #f8f9ff; border-radius: 8px; }
.instrument-breakdown h4 { color: #0B2044; font-size: 16px; margin-bottom: 15px; }
.breakdown-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; }
.breakdown-card { background: white; border: 1px solid #e0e0e0; border-radius: 8px; padding: 16px; cursor: pointer; transition: all 0.2s; }
.breakdown-card:hover { border-color: #0B2044; box-shadow: 0 4px 12px rgba(11,32,68,0.15); transform: translateY(-2px); }
.card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid #eee; }
.card-header strong { color: #0B2044; font-size: 14px; }
.instrument-type { background: #e8ecf1; color: #0B2044; padding: 4px 8px; border-radius: 12px; font-size: 11px; font-weight: 600; }
.card-body { display: flex; flex-direction: column; gap: 8px; }
.metric { display: flex; justify-content: space-between; align-items: center; font-size: 13px; }
.metric .label { color: #666; }
.metric .value { color: #0B2044; font-weight: 600; }
.metric .value.status-active { color: #4CAF50; }
.card-footer { margin-top: 12px; padding-top: 8px; border-top: 1px solid #eee; }
.workflow-btn { background: #0B2044; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-size: 12px; font-weight: 600; transition: all 0.2s; width: 100%; }
.workflow-btn:hover { background: #1a3a6e; transform: translateY(-1px); }

.export-buttons { margin-top: 20px; text-align: right; display: flex; gap: 10px; justify-content: flex-end; flex-wrap: wrap; }
.export-buttons .btn-primary { background: #4CAF50; color: white; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer; font-size: 14px; display: inline-flex; align-items: center; gap: 8px; transition: all 0.2s; }
.export-buttons .btn-primary:hover { background: #45a049; transform: translateY(-1px); }

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
.report-actions { display: flex; flex-wrap: wrap; gap: 10px; justify-content: center; margin-bottom: 20px; }
.btn-preview { background: #673AB7; color: white; padding: 8px 16px; border-radius: 6px; border: none; cursor: pointer; display: inline-flex; align-items: center; gap: 5px; }
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

@media (max-width: 768px) {
  .page-header { flex-direction: column; align-items: flex-start; gap: 10px; }
  .summary-cards, .selection-cards, .summary-grid { grid-template-columns: 1fr; }
  .mapping-row { flex-direction: column; align-items: stretch; }
  .required-label { width: 100%; }
  .progress-steps { flex-wrap: wrap; gap: 8px; }
  .progress-step { flex: 1 0 30%; }
  .filters-row { flex-direction: column; align-items: stretch; }
  .filter-group { min-width: 100%; }
  .breakdown-grid { grid-template-columns: 1fr; }
  .workflow-options { grid-template-columns: 1fr; }
  .header-right { width: 100%; justify-content: flex-start; }
  .btn-save-session { width: 100%; justify-content: center; }
  .instrument-grid { grid-template-columns: 1fr; }
}
</style>