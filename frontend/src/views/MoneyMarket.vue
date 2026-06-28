<template>
  <FixedLayout>
    <div class="instrument-page">
      <!-- Page Header -->
      <div class="page-header">
        <div class="header-left">
          <h1>{{ instrumentName }}</h1>
          <p>{{ instrumentDescription }}</p>
          <div v-if="activeSession" class="session-badge">
            <v-icon small>mdi-folder</v-icon>
            Session: <strong>{{ activeSession.name }}</strong>
          </div>
          <div v-else class="session-badge warning">
            <v-icon small>mdi-alert</v-icon>
            No active session – please select a session from Dashboard
          </div>
        </div>
        <div class="header-right">
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
            <v-card-title><v-icon>mdi-upload</v-icon> Upload {{ instrumentName }} Dataset</v-card-title>
            <v-card-text>
              <div class="upload-area" @dragover.prevent @drop.prevent="handleDrop">
                <input
                  type="file"
                  ref="fileInput"
                  @change="handleFileUpload"
                  accept=".csv,.xlsx,.xls,.xlsm,.xlsb,.xltx,.xltm,.xlam,.ods,.xml,.html,.prn,.dif,.slk,.dbf"
                  style="display: none"
                >
                <v-icon size="48" color="#0B2044">mdi-cloud-upload</v-icon>
                <p>Drag & drop or <span class="browse-link" @click="$refs.fileInput.click()">browse</span></p>
                <small>Supported: CSV, Excel (including .xlsm, .xlsb, .ods), and many other spreadsheet formats</small>
              </div>

              <!-- Upload History -->
              <div v-if="uploadHistory.length" class="upload-history">
                <h4>📁 Upload History ({{ uploadHistory.length }} files)</h4>
                <div class="history-list">
                  <div v-for="(item, idx) in uploadHistory" :key="idx" class="history-item" @click="loadHistoryFile(item)">
                    <v-icon small>mdi-file-excel</v-icon>
                    <span>{{ item.name }}</span>
                    <small>{{ new Date(item.date).toLocaleString() }}</small>
                    <button class="btn-delete-history" @click.stop="deleteHistoryItem(idx)">🗑️</button>
                  </div>
                </div>
              </div>

              <div v-if="fileLoading" class="loading-container">
                <v-icon size="48" class="spin">mdi-loading</v-icon>
                <p>Parsing file... Please wait.</p>
              </div>

              <div v-if="uploadedFile" class="file-info">
                <v-icon>mdi-file-excel</v-icon>
                <span>{{ uploadedFile.name }}</span>
                <span v-if="fileSize" class="file-size">{{ fileSize }}</span>
                <button class="remove-btn" @click="removeFile">×</button>
                <button class="btn-preview" @click="togglePreview" :disabled="!rawData.length">Preview</button>
                <button class="btn-review-excel" @click="openExcelReview(rawData, 'Uploaded Data')" :disabled="!rawData.length">Review Excel</button>
                <button class="btn-mapping" @click="openMappingDialog" :disabled="!rawData.length">Map Columns</button>
              </div>

              <!-- Preview with header dropdowns – controlled by showPreview -->
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
                <button class="btn-review-excel-small" @click="openExcelReview(rawData, 'Uploaded Data')">Full Screen</button>
              </div>

              <!-- Manual Mapping Dialog (with Saved Mappings) -->
              <v-dialog v-model="showMappingDialog" max-width="800px">
                <v-card>
                  <v-card-title>Map Columns</v-card-title>
                  <v-card-text>
                    <div class="mapping-instructions">
                      <p><v-icon small>mdi-hand-pointing-right</v-icon> Manually match each required system column to a column from your uploaded Excel file. The system suggests likely matches – you can override any selection.</p>
                    </div>
                    <div class="mapping-grid">
                      <div v-for="reqCol in requiredColumns" :key="reqCol" class="mapping-row">
                        <label class="required-label">{{ reqCol }}:</label>
                        <select v-model="columnMapping[reqCol]" class="mapping-select">
                          <option :value="null">-- Select column --</option>
                          <option v-for="fileCol in fileColumns" :key="fileCol" :value="fileCol">{{ fileCol }}</option>
                        </select>
                      </div>
                    </div>

                    <!-- ===== SAVED MAPPINGS SECTION ===== -->
                    <div class="saved-mappings-section">
                      <h4 class="saved-mappings-title">💾 Saved Mappings</h4>
                      <div class="saved-mappings-row">
                        <select v-model="selectedTemplate" class="template-select" style="flex:1; margin-right:8px;">
                          <option value="">-- Load template --</option>
                          <option v-for="(tmpl, name) in savedTemplates" :key="name" :value="name">{{ name }}</option>
                        </select>
                        <button class="btn-secondary" @click="loadSelectedTemplate" :disabled="!selectedTemplate">Load</button>
                        <button class="btn-secondary" @click="deleteSelectedTemplate" :disabled="!selectedTemplate">Delete</button>
                      </div>
                      <div class="saved-mappings-row" style="margin-top:8px;">
                        <input type="text" v-model="newTemplateName" placeholder="Template name" class="template-input" style="flex:1; margin-right:8px;" />
                        <button class="btn-primary" @click="saveCurrentMappingAsTemplate" :disabled="!newTemplateName">Save</button>
                        <button class="btn-secondary" @click="overwriteSelectedTemplate" :disabled="!selectedTemplate || !newTemplateName">Overwrite</button>
                      </div>
                      <div class="mapping-hint" style="margin-top:8px;">
                        <v-icon size="16">mdi-information</v-icon>
                        <small>Load a template to apply its mapping. Click "Apply Mapping" to preview.</small>
                      </div>
                    </div>

                    <div class="mapping-hint" style="margin-top:16px;">
                      <v-icon size="16">mdi-information</v-icon>
                      <small>Changes are applied only when you click "Apply Mapping". The Preview Excel will update instantly.</small>
                    </div>
                  </v-card-text>
                  <v-card-actions>
                    <button class="btn-secondary" @click="closeMappingDialog">Cancel</button>
                    <button class="btn-primary" @click="applyColumnMappingAndClose">Apply Mapping</button>
                  </v-card-actions>
                </v-card>
              </v-dialog>

              <div class="required-columns">
                <h4>Required Columns:</h4>
                <div class="columns-list">
                  <span v-for="col in requiredColumns" :key="col" class="column-badge" :class="{ 'missing-column': !hasRequiredColumn(col), 'mapped-column': hasRequiredColumn(col) }">
                    <v-icon size="12">
                      {{ hasRequiredColumn(col) ? 'mdi-check' : 'mdi-close' }}
                    </v-icon>
                    {{ col }}
                  </span>
                </div>
                <div v-if="rawData.length && missingColumns.length" class="warning-message">
                  <v-icon color="warning">mdi-alert</v-icon>
                  <span>Missing required columns. Use the dropdowns on the column headers or click "Map Columns" to assign them.</span>
                </div>
                <div v-if="rawData.length && missingColumns.length === 0 && mappingApplied" class="success-message">
                  <v-icon color="success">mdi-check-circle</v-icon>
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
            <v-card-title><v-icon>mdi-broom</v-icon> Clean {{ instrumentName }} Data</v-card-title>
            <v-card-text>
              <div v-if="!hasData" class="empty-state">
                <v-icon size="48" color="#ccc">mdi-database</v-icon>
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
            <v-card-title><v-icon>mdi-calculator</v-icon> {{ instrumentName }} Calculations</v-card-title>
            <v-card-text>
              <div v-if="!hasCleanedData" class="empty-state">
                <v-icon size="48" color="#ccc">mdi-calculator</v-icon>
                <p>No cleaned data. Please clean first.</p>
                <button class="btn-primary" @click="switchTab('cleaning')">Go to Cleaning</button>
              </div>
              <div v-else>
                <div class="summary-cards">
                  <div class="summary-card total" @click="showFormula('Total Portfolio Value')">
                    <div class="card-label">Total Portfolio Value</div>
                    <div class="card-value">${{ calculations.totalValue?.toLocaleString() || 0 }}</div>
                  </div>
                  <div class="summary-card rate" @click="showFormula('Average Rate')">
                    <div class="card-label">
                      {{ instrumentType === 'money-market' ? 'Avg Interest Rate' : instrumentType === 'bonds' ? 'Avg Coupon Rate' : 'Avg Discount Rate' }}
                    </div>
                    <div class="card-value">
                      {{
                        instrumentType === 'money-market' ? (calculations.avgRate || 0) :
                        instrumentType === 'bonds' ? (calculations.avgCouponRate || 0) :
                        (calculations.avgDiscountRate || 0)
                      }}%
                    </div>
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
                    <span class="comparison-value" :class="(calculations.fred.spread_vs_market || 0) >= 0 ? 'negative' : 'positive'">
                      {{ calculations.fred.spread_vs_market }}%
                    </span>
                  </div>
                  <small class="fred-meta">{{ calculations.fred.country_name || calculations.fred.country }} · {{ calculations.fred.currency }} · {{ calculations.fred.maturity }} · FRED</small>
                  <small v-if="calculations.fred.note" class="fred-meta">{{ calculations.fred.note }}</small>
                </div>

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
            <v-card-title><v-icon>mdi-chart-line</v-icon> {{ instrumentName }} – Market Yield Curves</v-card-title>
            <v-card-text>
              <div v-if="hasCleanedData && currentMarketRate" class="comparison-card">
                <div class="comparison-item">
                  <span class="comparison-label">Portfolio Average Rate:</span>
                  <span class="comparison-value portfolio">{{ portfolioAvgRate }}%</span>
                </div>
                <div class="comparison-item">
                  <span class="comparison-label">Current {{ selectedSeriesLabel }}:</span>
                  <span class="comparison-value market">{{ currentMarketRate }}%</span>
                </div>
                <div class="comparison-difference" :class="{ 'positive': (currentMarketRate - portfolioAvgRate) > 0, 'negative': (currentMarketRate - portfolioAvgRate) < 0 }">
                  Difference: {{ (currentMarketRate - portfolioAvgRate).toFixed(2) }}%
                </div>
              </div>

              <div class="filters-row">
                <div class="filter-group">
                  <label>Country / Region</label>
                  <select v-model="selectedCountryOption" @change="onCountrySelectChange" class="filter-select">
                    <option v-for="opt in countryOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
                    <option value="__custom__">Custom...</option>
                  </select>
                  <input
                    v-if="selectedCountryOption === '__custom__'"
                    v-model="customCountry"
                    @change="onCustomCountryChange"
                    type="text"
                    class="filter-select custom-maturity-input"
                    placeholder="e.g., DEU, FRA, CHN, AUS"
                  />
                </div>
                <div class="filter-group">
                  <label>Currency</label>
                  <select v-model="selectedCurrencyOption" @change="onCurrencySelectChange" class="filter-select">
                    <option v-for="opt in currencyOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
                    <option value="__custom__">Custom...</option>
                  </select>
                  <input
                    v-if="selectedCurrencyOption === '__custom__'"
                    v-model="customCurrency"
                    @change="onCustomCurrencyChange"
                    type="text"
                    class="filter-select custom-maturity-input"
                    placeholder="e.g., CHF, SEK, NZD"
                  />
                </div>
                <div class="filter-group">
                  <label>Maturity</label>
                  <select v-model="selectedMaturityOption" @change="onMaturitySelectChange" class="filter-select">
                    <option v-for="opt in maturityOptions" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
                    <option value="__custom__">Custom...</option>
                  </select>
                  <input
                    v-if="selectedMaturityOption === '__custom__'"
                    v-model="customMaturity"
                    @change="onCustomMaturityChange"
                    type="text"
                    class="filter-select custom-maturity-input"
                    placeholder="e.g., 18M, 2Y, 3M"
                  />
                </div>
                <button class="btn-secondary refresh-btn" @click="fetchFredData" :disabled="fredLoading">Refresh chart</button>
              </div>

              <div v-if="fredLoading" class="loading-container">
                <v-icon size="48" class="spin">mdi-loading</v-icon>
                <p>Fetching market data from FRED...</p>
              </div>
              <div v-else-if="fredError" class="error-container">
                <v-icon color="error" size="48">mdi-alert-circle</v-icon>
                <p>{{ fredError }}</p>
                <button class="btn-primary" @click="fetchFredData">Retry</button>
              </div>
              <div v-else-if="chartData.datasets && chartData.datasets.length" class="chart-container chart-container--fred">
                <canvas ref="yieldCurveChart" width="800" height="400" style="background: white; border-radius: 8px;"></canvas>
                <div class="chart-footer">
                  <small>Source: FRED – {{ chartSeriesLabel }} ({{ getCountryLabel(effectiveCountry) }} / {{ getCurrencyLabel(effectiveCurrency) }})</small>
                </div>
              </div>
              <div v-else class="visualization-placeholder">
                <v-icon size="64" color="#0B2044">mdi-chart-line</v-icon>
                <h3>No Market Data Loaded</h3>
                <p>Click the <strong>Refresh chart</strong> button above to fetch the latest yield curve.</p>
                <button class="btn-primary" @click="fetchFredData" style="margin-top: 16px;">Load Market Data</button>
              </div>

              <div class="navigation-buttons">
                <button class="btn-secondary" @click="switchTab('calculations')">Previous</button>
                <button class="btn-primary" @click="switchTab('summary')">Continue</button>
                <button class="btn-secondary" @click="goToDashboard">Dashboard</button>
              </div>
            </v-card-text>
          </v-card>
        </div>

        <!-- ===== SUMMARY ===== -->
        <div v-if="activeTab === 'summary'" class="content-card">
          <v-card class="summary-pro-card">
            <v-card-title><v-icon>mdi-file-document</v-icon> {{ instrumentName }} – Executive Summary</v-card-title>
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
                  <h3><v-icon size="20">mdi-database</v-icon> Data quality</h3>
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
                <button class="btn-secondary" @click="openExcelReview(cleanedData, `${instrumentName} - Cleaned Data`)">
                  📊 View Instrument Data as Excel
                </button>
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
            <v-card-title><v-icon>mdi-file-pdf</v-icon> Generate Combined Report</v-card-title>
            <v-card-text>
              <div class="report-options">
                <div class="instrument-selection">
                  <h3>Select Instruments to Include</h3>
                  <div class="selection-cards">
                    <div class="selection-card" :class="{ active: selectedInstruments.moneyMarket }" @click="selectedInstruments.moneyMarket = !selectedInstruments.moneyMarket">
                      <v-icon size="28" color="#1E88E5">mdi-chart-line</v-icon>
                      <span>Money Market</span>
                      <div class="check-indicator" v-if="selectedInstruments.moneyMarket"><v-icon size="16" color="#4CAF50">mdi-check-circle</v-icon></div>
                    </div>
                    <div class="selection-card" :class="{ active: selectedInstruments.bonds }" @click="selectedInstruments.bonds = !selectedInstruments.bonds">
                      <v-icon size="28" color="#4CAF50">mdi-chart-timeline</v-icon>
                      <span>Bonds</span>
                      <div class="check-indicator" v-if="selectedInstruments.bonds"><v-icon size="16" color="#4CAF50">mdi-check-circle</v-icon></div>
                    </div>
                    <div class="selection-card" :class="{ active: selectedInstruments.tbills }" @click="selectedInstruments.tbills = !selectedInstruments.tbills">
                      <v-icon size="28" color="#FF9800">mdi-finance</v-icon>
                      <span>T-Bills</span>
                      <div class="check-indicator" v-if="selectedInstruments.tbills"><v-icon size="16" color="#4CAF50">mdi-check-circle</v-icon></div>
                    </div>
                  </div>
                  <div class="selection-actions">
                    <button class="btn-secondary" @click="selectAllInstruments">Select All</button>
                    <button class="btn-secondary" @click="deselectAllInstruments">Deselect All</button>
                  </div>
                </div>

                <p class="report-hint">Click <strong>Preview Report</strong> to see the full professional report with cover, TOC, methodology, appendix, and live FRED charts. Downloads match the preview.</p>
                <div class="report-actions">
                  <button class="btn-preview" @click="previewReport">Preview Report</button>
                  <button class="btn-json" @click="downloadCombinedReport('json')">JSON</button>
                  <button class="btn-csv" @click="downloadCombinedReport('csv')">CSV</button>
                  <button class="btn-html" @click="downloadCombinedReport('html')">HTML</button>
                  <button class="btn-pdf" @click="downloadCombinedReport('pdf')">PDF</button>
                  <button class="btn-word" @click="downloadCombinedReport('word')">Word</button>
                  <button class="btn-excel" @click="downloadCombinedReport('excel')">Excel (XLSX)</button>
                  <button class="btn-save" @click="saveToSession">Save to Session</button>
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
        <v-card-title class="excel-dialog-title">
          {{ excelDialogTitle }} - Excel Viewer
          <v-spacer></v-spacer>
          <button class="btn-close-dialog" @click="closeExcelDialog">✕</button>
        </v-card-title>
        <v-card-text class="excel-dialog-content pa-0">
          <ExcelViewer :data="excelData" :headers="excelColumns" @data-update="onExcelDataUpdate" />
        </v-card-text>
      </v-card>
    </v-dialog>

    <!-- Formula Dialog -->
    <v-dialog v-model="formulaDialog" max-width="500px">
      <v-card>
        <v-card-title class="formula-dialog-title">📐 Formula Used</v-card-title>
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
        <v-card-title class="excel-dialog-title">
          Report Preview
          <v-spacer></v-spacer>
          <button class="btn-close-dialog" @click="reportPreviewDialog = false">✕</button>
        </v-card-title>
        <v-card-text class="report-preview-content" style="padding:0;">
          <iframe :srcdoc="reportPreviewHtml" frameborder="0" style="width:100%; height:80vh;"></iframe>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <button class="btn-primary" @click="downloadFromPreview('html')">Download HTML</button>
          <button class="btn-pdf" @click="downloadFromPreview('pdf')">Download PDF</button>
          <button class="btn-word" @click="downloadFromPreview('word')">Download Word</button>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </FixedLayout>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import FixedLayout from '@/components/FixedLayout.vue'
import api from '@/services/api.js'
import sessionManager from '@/services/sessionManager.js'
import mappingTemplateManager from '@/services/mappingTemplateManager.js'
import { useFredMarket } from '@/composables/useFredMarket'
import ExcelViewer from '@/components/ExcelViewer.vue'
import { loadFredSeriesChart, loadFredSeriesForReport } from '@/utils/fredChartHelper'
import { renderFredLineChart } from '@/utils/renderFredChart'
import { buildWorkflowSnapshot, applyWorkflowToPage } from '@/utils/instrumentSession.js'
import { useInstrumentConfig } from '@/composables/useInstrumentConfig.js'
import { autoMatchColumns as matchColumns, applyMappingToRows, isColumnMapped, getMissingColumns } from '@/utils/instrumentMapping.js'

// ========== Router & Route ==========
const router = useRouter()
const route = useRoute()
const activeSession = ref(null)

// ========== Instrument Info ==========
const instrumentType = computed(() => route.params.type || route.path.split('/').pop())
const instrumentName = computed(() => ({ 'money-market': 'Money Market', bonds: 'Bonds', tbills: 'T-Bills' }[instrumentType.value] || 'Instrument'))
const instrumentDescription = computed(() => ({
  'money-market': 'Short-term debt instruments including treasury bills, commercial paper',
  bonds: 'Fixed income securities including government and corporate bonds',
  tbills: 'Treasury bills - short-term government securities'
}[instrumentType.value] || 'Financial instrument management'))

const activeTab = computed({
  get: () => route.query.tab || 'upload',
  set: (val) => router.push({ query: { ...route.query, tab: val } })
})

// ========== Configuration ==========
const { requiredColumns, columnVariations, workflowSteps, loadConfig } = useInstrumentConfig()

// ========== FRED ==========
const { fredFilters, filterOptions, loadFilterOptions, seriesIdForMaturity, fetchBenchmark } = useFredMarket('1Y')
const fredLoading = ref(false), fredError = ref(''), selectedSeries = ref('')
const yieldCurveChart = ref(null), chartInstanceRef = { current: null }
const chartData = ref({ labels: [], datasets: [] }), chartSeriesLabel = ref(''), currentMarketRate = ref(null)

// ========== FRED Options & Computed ==========
const selectedMaturityOption = ref(''), customMaturity = ref('')
const selectedCountryOption = ref(''), customCountry = ref('')
const selectedCurrencyOption = ref(''), customCurrency = ref('')

const effectiveMaturity = computed(() => selectedMaturityOption.value === '__custom__' ? customMaturity.value : selectedMaturityOption.value)
const effectiveCountry = computed(() => selectedCountryOption.value === '__custom__' ? customCountry.value : selectedCountryOption.value)
const effectiveCurrency = computed(() => selectedCurrencyOption.value === '__custom__' ? customCurrency.value : selectedCurrencyOption.value)

const countryOptions = computed(() => [
  { value: 'USA', label: 'United States' },
  { value: 'GBR', label: 'United Kingdom' },
  { value: 'EUR', label: 'Eurozone' },
  { value: 'JPN', label: 'Japan' },
  { value: 'CAN', label: 'Canada' }
])
const currencyOptions = computed(() => [
  { value: 'USD', label: 'USD' },
  { value: 'EUR', label: 'EUR' },
  { value: 'GBP', label: 'GBP' },
  { value: 'JPY', label: 'JPY' },
  { value: 'CAD', label: 'CAD' }
])
const maturityOptions = computed(() => {
  let baseOptions = []
  if (filterOptions.value.maturities?.length) baseOptions = filterOptions.value.maturities
  else baseOptions = [
    { value: '1M', label: '1 Month' }, { value: '3M', label: '3 Months' },
    { value: '6M', label: '6 Months' }, { value: '1Y', label: '1 Year' },
    { value: '2Y', label: '2 Years' }, { value: '5Y', label: '5 Years' },
    { value: '10Y', label: '10 Years' }, { value: '30Y', label: '30 Years' },
    { value: '4W', label: '4 Weeks' }, { value: '8W', label: '8 Weeks' },
    { value: '13W', label: '13 Weeks' }, { value: '26W', label: '26 Weeks' },
    { value: '52W', label: '52 Weeks' }
  ]
  if (instrumentType.value === 'money-market') return baseOptions.filter(opt => ['1M','3M','6M','1Y'].includes(opt.value))
  if (instrumentType.value === 'bonds') return baseOptions.filter(opt => ['2Y','5Y','10Y','30Y'].includes(opt.value))
  if (instrumentType.value === 'tbills') return baseOptions.filter(opt => ['4W','8W','13W','26W','52W'].includes(opt.value))
  return baseOptions
})

// ========== Watches ==========
watch([countryOptions, currencyOptions, maturityOptions], () => {
  if (!effectiveCountry.value && countryOptions.value.length) {
    const def = countryOptions.value[0].value
    selectedCountryOption.value = def
    fredFilters.value.country = def
  }
  if (!effectiveCurrency.value && currencyOptions.value.length) {
    const def = 'USD'
    selectedCurrencyOption.value = def
    fredFilters.value.currency = def
  }
  if (!effectiveMaturity.value && maturityOptions.value.length) {
    const def = maturityOptions.value[0]?.value
    selectedMaturityOption.value = def
    fredFilters.value.maturity = def
  }
}, { immediate: true })

watch(() => instrumentType.value, () => {
  if (activeTab.value === 'visualizations') fetchFredData()
  if (!effectiveMaturity.value) {
    const def = defaultMaturityForInstrument()
    selectedMaturityOption.value = def
    fredFilters.value.maturity = def
  }
}, { immediate: true })

// ========== Steps ==========
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

// ---- Custom step completion ----
function isStepComplete(tab) {
  switch (tab) {
    case 'upload':
      return rawData.value.length > 0
    case 'cleaning':
      return cleanedData.value.length > 0
    case 'calculations':
      return !!calculations.value.totalValue && calculations.value.totalValue > 0
    case 'visualizations':
      return chartData.value.datasets && chartData.value.datasets.length > 0
    case 'summary':
      return cleanedData.value.length > 0 && !!calculations.value.totalValue
    case 'reports':
      return cleanedData.value.length > 0 && !!calculations.value.totalValue
    default:
      return false
  }
}

const farthestAllowedIndex = computed(() => {
  for (let i = 0; i < steps.value.length; i++) {
    if (!isStepComplete(steps.value[i].tab)) {
      return i
    }
  }
  return steps.value.length - 1
})

const currentStepIndex = computed(() => steps.value.findIndex(s => s.tab === activeTab.value))
const totalSteps = computed(() => steps.value.length)

// ========== Data refs ==========
const uploadedFile = ref(null)
const rawData = ref([])
const cleanedData = ref([])
const previewData = ref([])
const columnMapping = ref({})
const showMappingDialog = ref(false)
const fileColumns = ref([])
const fixedValuesTracker = ref(new Map())
const calculations = ref({})
const cleaningStats = ref({ totalRows: 0, validRows: 0, removedRows: 0, fixedMissing: 0 })
const fileLoading = ref(false)
const mappingApplied = ref(false)
const originalRawData = ref([])
const originalFileColumns = ref([])
const sessionSavedAt = ref(null)

// Control inline preview visibility
const showPreview = ref(false)

// ---- Force progress update ----
const forceUpdate = ref(0)

// ---- Mapping Templates ----
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

// ========== Upload History ==========
const uploadHistory = ref([])

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
    data: JSON.stringify(data)
  })
  if (uploadHistory.value.length > 10) uploadHistory.value.pop()
  saveUploadHistory()
}

function loadHistoryFile(item) {
  if (confirm(`Load ${item.name}? Current unsaved data will be lost.`)) {
    const data = JSON.parse(item.data)
    rawData.value = data
    originalRawData.value = JSON.parse(JSON.stringify(data))
    originalFileColumns.value = Object.keys(data[0] || {})
    fileColumns.value = [...originalFileColumns.value]
    uploadedFile.value = { name: item.name, size: 0 }
    // Auto-match columns (intelligent suggestions)
    columnMapping.value = matchColumns(fileColumns.value, requiredColumns.value, columnVariations.value)
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

// ========== Mapping Templates ==========
async function loadSavedTemplates() {
  const templates = await mappingTemplateManager.getTemplatesByInstrument(instrumentType.value)
  savedTemplates.value = {}
  templates.forEach(t => {
    savedTemplates.value[t.name] = t.column_mapping
  })
}

function saveTemplates() {
  // Templates are now managed by mappingTemplateManager via backend API
  // This function is kept for compatibility but delegates to the manager
}

async function saveCurrentMappingAsTemplate() {
  if (!newTemplateName.value) {
    alert('Please enter a template name.')
    return
  }
  // Check if at least one mapping exists
  const hasAnyMapping = requiredColumns.value.some(col => columnMapping.value[col])
  if (!hasAnyMapping) {
    alert('Cannot save template: no columns are mapped.')
    return
  }
  
  const template = await mappingTemplateManager.saveTemplate(
    newTemplateName.value,
    instrumentType.value,
    columnMapping.value,
    requiredColumns.value,
    fileColumns.value
  )
  
  if (template) {
    savedTemplates.value[template.name] = template.column_mapping
    alert(`Template "${newTemplateName.value}" saved.`)
    newTemplateName.value = ''
    await loadSavedTemplates()
  } else {
    alert('Failed to save template.')
  }
}

async function applyTemplate() {
  if (!selectedTemplate.value) return
  const templates = await mappingTemplateManager.getTemplatesByInstrument(instrumentType.value)
  const template = templates.find(t => t.name === selectedTemplate.value)
  if (!template) return
  columnMapping.value = { ...template.column_mapping }
  applyCurrentMapping()
  if (showPreview.value) {
    // The data is already updated via applyCurrentMapping; the ExcelViewer will re-render
  }
  debouncedSave()
  forceUpdate.value++
}

async function deleteTemplate() {
  if (!selectedTemplate.value) return
  const templates = await mappingTemplateManager.getTemplatesByInstrument(instrumentType.value)
  const template = templates.find(t => t.name === selectedTemplate.value)
  if (!template) return
  
  if (confirm(`Delete template "${selectedTemplate.value}"?`)) {
    const success = await mappingTemplateManager.deleteTemplate(template.id)
    if (success) {
      delete savedTemplates.value[selectedTemplate.value]
      selectedTemplate.value = ''
      await loadSavedTemplates()
    } else {
      alert('Failed to delete template.')
    }
  }
}

// ---- Dialog-specific template actions ----
async function loadSelectedTemplate() {
  await applyTemplate()
}

async function deleteSelectedTemplate() {
  await deleteTemplate()
}

async function overwriteSelectedTemplate() {
  if (!selectedTemplate.value) {
    alert('No template selected to overwrite.')
    return
  }
  const templates = await mappingTemplateManager.getTemplatesByInstrument(instrumentType.value)
  const template = templates.find(t => t.name === selectedTemplate.value)
  if (!template) return
  
  const updated = await mappingTemplateManager.updateTemplate(template.id, {
    columnMapping: columnMapping.value,
    fileColumns: fileColumns.value
  })
  
  if (updated) {
    savedTemplates.value[selectedTemplate.value] = { ...columnMapping.value }
    alert(`Template "${selectedTemplate.value}" overwritten.`)
  } else {
    alert('Failed to overwrite template.')
  }
}

// ========== Computed Helpers ==========
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
  return originalFileColumns.value.length
    ? originalFileColumns.value
    : Object.keys(rawData.value[0] || {})
})
const cleanPreviewHeaders = computed(() => Object.keys((cleanedData.value[0]) || {}))

const portfolioAvgRate = computed(() => instrumentType.value === 'money-market' ? calculations.value.avgRate || 0 : instrumentType.value === 'bonds' ? calculations.value.avgCouponRate || 0 : calculations.value.avgDiscountRate || 0)

// ========== Navigation ==========
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

function goToReportTab() {
  saveSessionData()
  activeTab.value = 'reports'
  forceUpdate.value++
}

function switchTab(tab) {
  saveSessionData()
  activeTab.value = tab
  forceUpdate.value++
}

// ========== File Upload ==========
const fileInput = ref(null)
function handleFileUpload(e) { const file = e.target.files[0]; if (file) { uploadedFile.value = file; readFileData(file) } }
function handleDrop(e) { const file = e.dataTransfer.files[0]; if (file) { uploadedFile.value = file; readFileData(file) } }

async function readFileData(file) {
  fileLoading.value = true
  try {
    if (file.size > 20 * 1024 * 1024 && !confirm(`File is ${(file.size / (1024 * 1024)).toFixed(2)} MB. Continue?`)) {
      fileLoading.value = false; uploadedFile.value = null; return
    }

    // Use backend API for file parsing
    const formData = new FormData()
    formData.append('file', file)
    const response = await fetch('http://localhost:5000/api/upload', {
      method: 'POST',
      body: formData
    })
    const result = await response.json()

    if (!result.success || !result.data.success) {
      throw new Error(result.data?.error || 'Failed to parse file')
    }

    const data = result.data.data || []
    rawData.value = data
    originalRawData.value = JSON.parse(JSON.stringify(data))
    originalFileColumns.value = result.data.headers || Object.keys(data[0] || {})
    fileColumns.value = [...originalFileColumns.value]

    // Intelligent auto-match
    columnMapping.value = matchColumns(fileColumns.value, requiredColumns.value, columnVariations.value)
    applyCurrentMapping()
    showPreview.value = false

    addToHistory(file.name, data)
    debouncedSave()
    forceUpdate.value++
  } catch (err) {
    console.error(err)
    alert(`Failed to parse file: ${err.message}`)
    uploadedFile.value = null
    rawData.value = []
  } finally {
    fileLoading.value = false
  }
}

function removeFile() {
  uploadedFile.value = null
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
  debouncedSave()
  forceUpdate.value++
  if (fileInput.value) fileInput.value.value = ''
}

// ========== Mapping ==========
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
      if (srcCol) {
        newRow[col] = row[srcCol] !== undefined ? row[srcCol] : ''
      } else {
        newRow[col] = ''
      }
    })
    return newRow
  })
  rawData.value = mappedData
  const allMapped = requiredColumns.value.every(col => columnMapping.value[col])
  mappingApplied.value = allMapped
}

function updateColumnMapping(newMapping) {
  columnMapping.value = { ...newMapping }
  applyCurrentMapping()
  debouncedSave()
}

function openMappingDialog() {
  if (!fileColumns.value.length) {
    fileColumns.value = originalFileColumns.value.length ? [...originalFileColumns.value] : Object.keys(rawData.value[0] || {})
  }
  showMappingDialog.value = true
}

function closeMappingDialog() {
  showMappingDialog.value = false
}

function applyColumnMappingAndClose() {
  applyCurrentMapping()
  // Show preview if not already visible
  if (rawData.value.length) {
    showPreview.value = true
  }
  showMappingDialog.value = false
  forceUpdate.value++
}

async function continueAfterUpload() {
  if (!uploadedFile.value) { alert('Please upload a file first.'); return }
  if (!rawData.value.length) { alert('No data loaded. Please upload a valid file.'); return }
  activeTab.value = 'cleaning'
  debouncedSave()
  forceUpdate.value++
}

// ========== Cleaning ==========
async function applyCleaning() {
  if (!rawData.value.length) return
  
  try {
    // Use backend API for data cleaning
    const response = await fetch('http://localhost:5000/api/clean', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        data: rawData.value,
        options: cleaningOptions.value
      })
    })
    const result = await response.json()

    if (!result.success) {
      throw new Error(result.message || 'Failed to clean data')
    }

    cleanedData.value = result.data || []
    cleaningStats.value = result.stats || { totalRows: rawData.value.length, validRows: 0, removedRows: 0, fixedMissing: 0 }
    debouncedSave()
    forceUpdate.value++
  } catch (err) {
    console.error('Cleaning error:', err)
    alert(`Failed to clean data: ${err.message}`)
  }
}

// ========== CONTINUE AFTER CLEANING ==========
async function continueAfterCleaning() {
  if (!cleanedData.value.length) {
    alert('Please clean your data first.')
    return
  }
  try {
    await calculateMetrics()
  } catch (err) {
    console.error('Error calculating metrics:', err)
    alert('There was an error calculating metrics, but you can proceed to calculations.')
  }
  goToCalculations()
  forceUpdate.value++
}

// ========== Calculations ==========
async function calculateMetrics() {
  if (!cleanedData.value.length) return

  try {
    // Use backend API for calculations
    const response = await fetch(`http://localhost:5000/api/calculate/${instrumentType.value}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        data: cleanedData.value,
        country: effectiveCountry.value || 'USA',
        currency: effectiveCurrency.value || 'USD',
        maturity: effectiveMaturity.value || '1Y'
      })
    })
    const result = await response.json()

    if (!result.success) {
      throw new Error(result.message || 'Failed to calculate metrics')
    }

    calculations.value = result.data || {}
    await enrichCalculationsWithFred()
    debouncedSave()
    forceUpdate.value++
  } catch (err) {
    console.error('Calculation error:', err)
    alert(`Failed to calculate metrics: ${err.message}`)
  }
}

function continueToVisualizations() {
  if (!hasCleanedData.value) { alert('Please clean your data first.'); return }
  goToVisualizations()
  forceUpdate.value++
}

// ========== Report Logic ==========
const selectedInstruments = ref({ moneyMarket: true, bonds: true, tbills: true })
function selectAllInstruments() { selectedInstruments.value = { moneyMarket: true, bonds: true, tbills: true } }
function deselectAllInstruments() { selectedInstruments.value = { moneyMarket: false, bonds: false, tbills: false } }

const reportPreviewDialog = ref(false)
const reportPreviewHtml = ref('')

function getInstrumentData(instrumentId) {
  if (!activeSession.value) return null
  const sid = activeSession.value.id
  let wf = sessionManager.getInstrumentWorkflow(sid, instrumentId)
  if (!wf) {
    const stored = activeSession.value.instrumentData?.[instrumentId]
    if (stored) return stored
    const savedCalc = localStorage.getItem(`${instrumentId}_session_${sid}_calc`)
    if (savedCalc) try { return JSON.parse(savedCalc) } catch { }
    return null
  }
  return wf.calculations || null
}

const reportPreviewData = computed(() => {
  const instrumentsData = []
  if (selectedInstruments.value.moneyMarket) {
    const data = getInstrumentData('money-market')
    if (data && Object.keys(data).length && data.totalValue > 0) instrumentsData.push({ name: 'Money Market', calculations: data })
  }
  if (selectedInstruments.value.bonds) {
    const data = getInstrumentData('bonds')
    if (data && Object.keys(data).length && data.totalValue > 0) instrumentsData.push({ name: 'Bonds', calculations: data })
  }
  if (selectedInstruments.value.tbills) {
    const data = getInstrumentData('tbills')
    if (data && Object.keys(data).length && data.totalValue > 0) instrumentsData.push({ name: 'T-Bills', calculations: data })
  }
  return { session: activeSession.value?.name || 'No session', date: new Date().toLocaleString(), instruments: instrumentsData }
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
    if (key.includes('Value') || key.includes('Price') || key.includes('Interest') || key.includes('Income') || key.includes('Discount') || key.includes('Principal') || key.includes('Investment'))
      return `$${value.toLocaleString()}`
    if (key.includes('Rate') || key.includes('Yield') || key.includes('Coupon') || key.includes('Discount'))
      return `${value}%`
    return value.toLocaleString()
  }
  return value
}

function buildMethodologySection(selectedInstrumentNames) {
  let methods = []
  if (selectedInstrumentNames.includes('Money Market')) methods.push(`<div class="methodology-card"><h4>Money Market Instruments</h4><p class="formula">Fair value = <sup>F</sup> &frasl; <sub>1 + r·t/365</sub></p><p>Where: <strong>F</strong> = Face value, <strong>r</strong> = annualized interest rate (%), <strong>t</strong> = days to maturity.</p><p>Simple interest convention (365 days/year). Weighted average rate = Σ (Rate × Amount) / Σ Amount.</p></div>`)
  if (selectedInstrumentNames.includes('Bonds')) methods.push(`<div class="methodology-card"><h4>Bonds</h4><p class="formula">Fair value = Σ<sub>t=1</sub><sup>n</sup> <sup>C</sup> &frasl; <sub>(1+y)<sup>t</sup></sub> + <sup>FV</sup> &frasl; <sub>(1+y)<sup>n</sup></sub></p><p>Where: <strong>C</strong> = annual coupon payment (CouponRate × FaceValue), <strong>y</strong> = yield to maturity (%), <strong>FV</strong> = face value, <strong>n</strong> = years to maturity.</p><p>Duration = Σ (t × PV(C<sub>t</sub>)) / Price. Approximated using Macaulay duration.</p></div>`)
  if (selectedInstrumentNames.includes('T-Bills')) methods.push(`<div class="methodology-card"><h4>Treasury Bills (T‑Bills)</h4><p class="formula">Discount amount = Face value × (Discount rate / 100) × (Days to maturity / 360)</p><p class="formula">Effective yield = (Face value / Price − 1) × (365 / Days to maturity) × 100</p><p>Bank discount basis (360 days/year) for discount rate; bond equivalent yield uses 365 days.</p></div>`)
  return methods.length ? methods.join('') : '<p>No methodology available for the selected instruments.</p>'
}

async function generateReportHtml() {
  await loadSavedData()
  const report = reportPreviewData.value
  if (report.instruments.length === 0) {
    alert('No data available for the selected instruments.')
    return null
  }

  const chartDataMap = {}
  for (const inst of report.instruments) {
    const instKey = inst.name === 'Money Market' ? 'money-market' : inst.name === 'Bonds' ? 'bonds' : 'tbills'
    const instSessionData = activeSession.value?.instrumentData?.[instKey]
    if (instSessionData?.chartData && instSessionData.chartData.datasets?.length) chartDataMap[inst.name] = instSessionData.chartData
    else {
      try {
        const sid = await seriesIdForMaturity()
        const loaded = await loadFredSeriesForReport(sid)
        if (loaded) {
          chartDataMap[inst.name] = loaded
          if (activeSession.value?.instrumentData) {
            if (!activeSession.value.instrumentData[instKey]) activeSession.value.instrumentData[instKey] = {}
            activeSession.value.instrumentData[instKey].chartData = loaded
          }
        }
      } catch (err) { console.error('FRED chart for report', inst.name, err) }
    }
  }

  // Build professional report HTML (with all sections)
  const origin = window.location.origin
  const logoHtml = `<div style="font-size:32px;font-weight:700;color:#0B2044;letter-spacing:1px;">Dura<span style="color:#1E88E5;">Capital</span></div><div style="font-size:12px;color:#666;margin-top:-4px;">Valuation</div>`
  const valuationDate = new Date().toISOString().split('T')[0]
  const totalPortfolioValue = report.instruments.reduce((sum, inst) => sum + (parseFloat(inst.calculations.totalValue) || 0), 0)
  const totalInstrumentCount = report.instruments.reduce((sum, inst) => sum + (parseInt(inst.calculations.instrumentCount) || 0), 0)

  // Build instrument details table for appendix
  let appendixRows = ''
  let allDataRows = []
  for (const inst of report.instruments) {
    const instKey = inst.name === 'Money Market' ? 'money-market' : inst.name === 'Bonds' ? 'bonds' : 'tbills'
    let cleanData = []
    const wf = sessionManager.getInstrumentWorkflow(activeSession.value?.id, instKey)
    if (wf && wf.cleanedData && wf.cleanedData.length) cleanData = wf.cleanedData
    else {
      const saved = localStorage.getItem(`${instKey}_session_${activeSession.value?.id}_clean`)
      if (saved) cleanData = JSON.parse(saved)
    }
    if (cleanData && cleanData.length) {
      cleanData.forEach((item, idx) => {
        const name = item.Instrument || item.BondName || item.TBillName || `${inst.name} ${idx + 1}`
        const ticker = item.BBTicker || item.Ticker || item.Security || 'N/A'
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

  const html = `<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Valuation Assessment Report - ${report.session}</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: 'Arial', sans-serif; color: #333; background: white; line-height: 1.6; }
    .page { page-break-after: always; padding: 60px 80px; min-height: 100vh; }
    .page:last-child { page-break-after: auto; }
    .cover-page { display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; background: linear-gradient(135deg, #0B2044 0%, #1a3a6e 100%); color: white; }
    .cover-content { max-width: 800px; }
    .logo { margin-bottom: 40px; }
    .cover-title { font-size: 48px; font-weight: 700; letter-spacing: 2px; margin-bottom: 20px; }
    .cover-subtitle { font-size: 24px; font-weight: 300; opacity: 0.9; margin-bottom: 40px; }
    .cover-meta { font-size: 14px; opacity: 0.8; line-height: 1.8; }
    .cover-meta strong { opacity: 1; }
    .toc-page h1 { font-size: 28px; color: #0B2044; border-bottom: 3px solid #0B2044; padding-bottom: 15px; margin-bottom: 30px; }
    .toc-item { display: flex; justify-content: space-between; padding: 12px 0; border-bottom: 1px dotted #ddd; font-size: 16px; }
    .toc-item:hover { background: #f5f5f5; }
    .section-title { font-size: 24px; color: #0B2044; border-bottom: 2px solid #0B2044; padding-bottom: 10px; margin: 30px 0 20px 0; }
    .section-title.centered { text-align: center; border-bottom: none; }
    .executive-summary { background: #f8f9ff; padding: 25px; border-radius: 10px; border-left: 4px solid #0B2044; margin-bottom: 25px; }
    .executive-summary .highlight { color: #0B2044; font-weight: 700; }
    .methodology-card { background: #f8f9ff; padding: 20px; border-radius: 8px; margin: 15px 0; }
    .methodology-card .formula { font-family: 'Courier New', monospace; font-size: 16px; background: white; padding: 10px 15px; border-radius: 6px; border: 1px solid #e0e0e0; margin: 10px 0; }
    table { width: 100%; border-collapse: collapse; margin: 20px 0; font-size: 14px; }
    th { background: #0B2044; color: white; padding: 12px 10px; text-align: left; }
    td { padding: 10px; border-bottom: 1px solid #eee; }
    tr:hover { background: #f5f8ff; }
    .appendix-table { font-size: 12px; }
    .appendix-table th { background: #1a3a6e; }
    .appendix-table td { padding: 6px 8px; }
    .footer { margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 12px; color: #999; text-align: center; }
    .reference-list { list-style: none; padding: 0; }
    .reference-list li { padding: 8px 0; border-bottom: 1px solid #eee; }
    .chart-container { margin: 20px 0; text-align: center; max-height: 360px; overflow: hidden; }
    .chart-container canvas { max-width: 100%; height: auto; max-height: 300px; background: #f8f9ff; border-radius: 8px; padding: 10px; }
    .chart-caption { font-size: 12px; color: #666; margin-top: 5px; }
    @media print {
      .page { padding: 40px 60px; }
      .cover-page { background: #0B2044 !important; -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
      .executive-summary { background: #f8f9ff !important; -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
    }
  </style>
</head>
<body>

<!-- COVER PAGE -->
<div class="page cover-page">
  <div class="cover-content">
    <div class="logo">${logoHtml}</div>
    <h1 class="cover-title">Valuation Assessment Report</h1>
    <p class="cover-subtitle">${report.instruments.map(i => i.name).join(' & ')}</p>
    <div class="cover-meta">
      <p><strong>Prepared for:</strong> ${report.session}</p>
      <p><strong>Valuation Date:</strong> ${valuationDate}</p>
      <p><strong>Report Date:</strong> ${report.date}</p>
      <p><strong>Prepared by:</strong> Dura Capital (Private) Limited</p>
    </div>
  </div>
</div>

<!-- TABLE OF CONTENTS -->
<div class="page toc-page">
  <h1>Table of Contents</h1>
  <div class="toc-item"><span>Introduction</span><span>1</span></div>
  <div class="toc-item"><span>Executive Summary</span><span>2</span></div>
  <div class="toc-item"><span>Methodology</span><span>3</span></div>
  <div class="toc-item"><span>Market Inputs</span><span>4</span></div>
  <div class="toc-item"><span>Results</span><span>5</span></div>
  <div class="toc-item"><span>Conclusion</span><span>6</span></div>
  <div class="toc-item"><span>Appendix</span><span>7</span></div>
  <div class="toc-item"><span>Reference</span><span>8</span></div>
</div>

<!-- INTRODUCTION -->
<div class="page">
  <h1 class="section-title">Introduction</h1>
  <p>Dura Capital (Private) Limited ("Dura Capital", "us", "we") was contracted to provide a fair valuation assessment report of the following fixed income instruments as at ${valuationDate}:</p>
  <ul style="margin: 20px 0 20px 30px;">
    ${report.instruments.map(i => `<li>${i.name}</li>`).join('')}
  </ul>
  <p>The instruments are classified and measured at fair value through profit or loss in terms of International Financial Reporting Standard 9: Financial Instruments ("IFRS 9") and International Financial Reporting Standard 13: Fair Value Measurement ("IFRS 13") and this forms as the basis to our assessment.</p>
  <br>
  <p><strong>This report is structured in five parts:</strong></p>
  <ul style="margin: 10px 0 20px 30px;">
    <li><strong>Methodology:</strong> Outlines the methods used to value the financial instruments and the discounting factors.</li>
    <li><strong>Market Inputs:</strong> Assesses the reasonability of market data that is used in the valuation models.</li>
    <li><strong>Results:</strong> Compares the client's valuation to our independent assessment.</li>
    <li><strong>Conclusion:</strong> Gives our independent opinion as well as other considerations.</li>
    <li><strong>Appendix:</strong> Detailed instrument-level data and calculations.</li>
  </ul>
</div>

<!-- EXECUTIVE SUMMARY -->
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
    <br>
    <p><strong>Valuation Approach:</strong></p>
    <p>${methodologyHtml.replace(/<[^>]*>/g, '').substring(0, 300)}...</p>
  </div>
</div>

<!-- METHODOLOGY -->
<div class="page">
  <h1 class="section-title">Methodology</h1>
  <p>The audit team provided us with data for ${report.instruments.map(i => i.name).join(', ')}. This section outlines the methodologies used to provide a fair value of the fixed income assets in terms of IFRS 13.</p>
  <br>
  ${methodologyHtml}
  <br>
  <p><strong>Day Count Convention:</strong> Actual/365-day count convention as provided by the Audit team.</p>
  <p><strong>Discounting:</strong> The sum of all discounted cashflows for each instrument represents the fair value of the instrument in terms of IFRS 13.</p>
</div>

<!-- MARKET INPUTS -->
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

<!-- RESULTS -->
<div class="page">
  <h1 class="section-title">Results</h1>
  <p>Below is a summary of the key findings of the valuation for the selected instruments.</p>
  <br>
  <table>
    <thead>
      <tr>
        <th>Instrument</th>
        <th>Total Value</th>
        <th>Count</th>
        <th>Avg Rate (%)</th>
        <th>Weighted Avg (%)</th>
      </tr>
    </thead>
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

<!-- CONCLUSION -->
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
  <br>
  <p style="font-style: italic; color: #666;">This report is confidential and prepared solely for the use of the client.</p>
</div>

<!-- APPENDIX -->
<div class="page">
  <h1 class="section-title">Appendix: Detailed Instrument Data</h1>
  <p><strong>Valuation Date:</strong> ${valuationDate}</p>
  <p><strong>Total Instruments:</strong> ${allDataRows.length}</p>
  <br>
  ${allDataRows.length ? `
  <table class="appendix-table">
    <thead>
      <tr>
        <th>Asset Class</th>
        <th>Instrument Name</th>
        <th>BB Ticker</th>
        <th>Face Value ($)</th>
        <th>Rate (%)</th>
        <th>Term (Yrs)</th>
        <th>Valuation Date</th>
      </tr>
    </thead>
    <tbody>
      ${appendixRows}
    </tbody>
  </table>
  <p style="font-size: 12px; color: #999; margin-top: 10px;"><em>Note: BB Ticker refers to Bloomberg ticker where available. Term is calculated as years to maturity.</em></p>
  ` : '<p>No detailed instrument data available.</p>'}
</div>

<!-- REFERENCE -->
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
  }
}

async function downloadFromPreview(format) {
  if (!reportPreviewHtml.value) return
  const filename = `combined_report_${Date.now()}`
  if (format === 'html') downloadBlob(reportPreviewHtml.value, `${filename}.html`, 'text/html')
  else if (format === 'pdf') { const win = window.open(); win.document.write(reportPreviewHtml.value); win.print() }
  else if (format === 'word') downloadBlob(reportPreviewHtml.value, `${filename}.doc`, 'application/msword')
}

async function exportToRealExcel() {
  await loadSavedData()
  const report = reportPreviewData.value
  if (report.instruments.length === 0) { alert('No data available for the selected instruments.'); return }
  const workbook = XLSX.utils.book_new()
  const summaryData = [['Report Generated', new Date().toLocaleString()], ['Session', report.session], [], ['Instrument', 'Metric', 'Value']]
  for (const inst of report.instruments) {
    for (const [key, val] of Object.entries(inst.calculations)) {
      if (key === 'completed' || key === 'timestamp' || key === 'fred') continue
      summaryData.push([inst.name, formatMetricName(key), formatMetricValue(key, val)])
    }
  }
  const summarySheet = XLSX.utils.aoa_to_sheet(summaryData)
  XLSX.utils.book_append_sheet(workbook, summarySheet, 'Summary')

  // Appendix sheet
  const appendixData = [
    ['APPENDIX – Detailed Instrument Data'],
    ['Valuation Date:', new Date().toISOString().split('T')[0]],
    ['Session:', report.session],
    [],
    ['Asset Class', 'Instrument Name', 'BB Ticker', 'Face Value ($)', 'Rate (%)', 'Term (Yrs)', 'Valuation Date']
  ]

  for (const inst of report.instruments) {
    const instKey = inst.name === 'Money Market' ? 'money-market' : inst.name === 'Bonds' ? 'bonds' : 'tbills'
    let instrumentData = []
    const wf = sessionManager.getInstrumentWorkflow(activeSession.value?.id, instKey)
    if (wf && wf.cleanedData && wf.cleanedData.length) instrumentData = wf.cleanedData
    else {
      const sid = activeSession.value?.id
      if (sid) { const saved = localStorage.getItem(`${instKey}_session_${sid}_clean`); if (saved) instrumentData = JSON.parse(saved) }
    }
    if (instrumentData.length) {
      instrumentData.forEach((item, idx) => {
        const name = item.Instrument || item.BondName || item.TBillName || `${inst.name} ${idx + 1}`
        const ticker = item.BBTicker || item.Ticker || item.Security || 'N/A'
        const faceValue = parseFloat(item.FaceValue || item.Amount || item.Principal || 0)
        const rate = parseFloat(item.Rate || item.InterestRate || item.CouponRate || item.DiscountRate || 0)
        const term = parseFloat(item.Term || item.YearsToMaturity || 0) || (parseFloat(item.MaturityDate) ? (new Date(item.MaturityDate) - new Date(item.IssueDate || Date.now())) / (365 * 24 * 60 * 60 * 1000) : 0)
        appendixData.push([inst.name, name, ticker, faceValue, rate, term, new Date().toISOString().split('T')[0]])
      })
    }
  }

  const appendixSheet = XLSX.utils.aoa_to_sheet(appendixData)
  appendixSheet['!cols'] = [{ wch: 18 }, { wch: 25 }, { wch: 15 }, { wch: 18 }, { wch: 12 }, { wch: 12 }, { wch: 18 }]
  XLSX.utils.book_append_sheet(workbook, appendixSheet, 'Appendix')

  // Detail sheets for each instrument
  for (const inst of report.instruments) {
    const instKey = inst.name === 'Money Market' ? 'money-market' : inst.name === 'Bonds' ? 'bonds' : 'tbills'
    let instrumentData = []
    const wf = sessionManager.getInstrumentWorkflow(activeSession.value?.id, instKey)
    if (wf && wf.cleanedData && wf.cleanedData.length) instrumentData = wf.cleanedData
    else {
      const sid = activeSession.value?.id
      if (sid) { const saved = localStorage.getItem(`${instKey}_session_${sid}_clean`); if (saved) instrumentData = JSON.parse(saved) }
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

// ========== Excel Viewer Dialogs ==========
const showExcelDialog = ref(false)
const excelData = ref([])
const excelColumns = ref([])
const excelDialogTitle = ref('')
function openExcelReview(data, title) {
  if (!data?.length) { if (cleanedData.value.length) data = cleanedData.value; else if (rawData.value.length) data = rawData.value; else { alert('No data'); return } }
  excelData.value = data; excelColumns.value = Object.keys(data[0] || {}); excelDialogTitle.value = title || 'Data Review'; showExcelDialog.value = true
}
function closeExcelDialog() { showExcelDialog.value = false; excelData.value = [] }

function togglePreview() {
  if (!rawData.value.length) return
  showPreview.value = !showPreview.value
}

// ========== Formula Popup ==========
const formulaDialog = ref(false)
const formulaText = ref('')
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

// ========== Save to Session ==========
function saveToSession() {
  saveSessionData()
  if (!activeSession.value) {
    alert('No active session selected.')
    return
  }
  const sid = activeSession.value.id
  updateSessionCompletion()
  const wf = sessionManager.getInstrumentWorkflow(sid, instrumentType.value)
  const versionData = {
    instrument: instrumentName.value,
    changeType: 'Saved',
    changeTypeClass: 'badge-saved',
    shortDescription: `💾 Saved ${instrumentName.value} to session`,
    description: `Saved changes for ${instrumentName.value}`,
    fieldsChanged: ['data', 'calculations', 'mapping'],
    modifiedInstruments: [instrumentName.value],
    workflows: { [instrumentType.value]: wf }
  }
  sessionManager.addVersion(sid, versionData)
  window.dispatchEvent(new CustomEvent('session-updated', {
    detail: { sessionId: sid, skipCapture: true }
  }))
  sessionSavedAt.value = new Date().toISOString()
  forceUpdate.value++
}

// ========== Session Persistence ==========
function refreshPage() {
  rawData.value = []
  originalRawData.value = []
  originalFileColumns.value = []
  cleanedData.value = []
  uploadedFile.value = null
  previewData.value = []
  calculations.value = {}
  cleaningStats.value = { totalRows: 0, validRows: 0, removedRows: 0, fixedMissing: 0 }
  fixedValuesTracker.value.clear()
  columnMapping.value = {}
  fileColumns.value = []
  showMappingDialog.value = false
  mappingApplied.value = false
  sessionSavedAt.value = null
  showPreview.value = false
}

async function loadSavedData() {
  const datasetId = route.query.dataset_id
  if (datasetId) {
    try {
      const res = await api.datasetAPI.load(datasetId)
      if (res && res.success && res.data) {
        const last = res.data
        rawData.value = last.data || []
        originalRawData.value = JSON.parse(JSON.stringify(rawData.value))
        originalFileColumns.value = Object.keys(rawData.value[0] || {})
        fileColumns.value = [...originalFileColumns.value]
        cleanedData.value = last.data || []
        calculations.value = {}
        uploadedFile.value = { name: last.name || '', size: 0 }
        cleaningStats.value = {
          totalRows: rawData.value.length,
          validRows: cleanedData.value.length,
          removedRows: rawData.value.length - cleanedData.value.length,
          fixedMissing: 0
        }
        columnMapping.value = matchColumns(fileColumns.value, requiredColumns.value, columnVariations.value)
        applyCurrentMapping()
        showPreview.value = false
        forceUpdate.value++
        return true
      }
    } catch (err) { console.error(err) }
  }

  if (!activeSession.value) return false
  const sid = activeSession.value.id
  let loaded = false
  let wf = sessionManager.getInstrumentWorkflow(sid, instrumentType.value)
  if (!wf) {
    await sessionManager.loadSessionFromDb(sid)
    wf = sessionManager.getInstrumentWorkflow(sid, instrumentType.value)
  }
  if (wf) {
    loaded = applyWorkflowToPage(wf, {
      rawData, cleanedData, calculations, uploadedFile, cleaningStats,
      columnMapping, mappingApplied, originalRawData, originalFileColumns
    })
    if (wf.sessionSavedAt) sessionSavedAt.value = wf.sessionSavedAt
    if (originalFileColumns.value.length) fileColumns.value = [...originalFileColumns.value]
    else if (originalRawData.value.length) fileColumns.value = Object.keys(originalRawData.value[0] || {})
    if (wf.chartData) chartData.value = wf.chartData
    if (wf.fredFilters) {
      fredFilters.value = { ...fredFilters.value, ...wf.fredFilters }
      if (wf.fredFilters.maturity) {
        const matVal = wf.fredFilters.maturity
        const isCustom = !maturityOptions.value.some(opt => opt.value === matVal)
        if (isCustom) {
          selectedMaturityOption.value = '__custom__'
          customMaturity.value = matVal
        } else {
          selectedMaturityOption.value = matVal
          customMaturity.value = ''
        }
      }
      if (wf.fredFilters.country) {
        const countryVal = wf.fredFilters.country
        const isCustom = !countryOptions.value.some(opt => opt.value === countryVal)
        if (isCustom) {
          selectedCountryOption.value = '__custom__'
          customCountry.value = countryVal
        } else {
          selectedCountryOption.value = countryVal
          customCountry.value = ''
        }
      }
      if (wf.fredFilters.currency) {
        const currencyVal = wf.fredFilters.currency
        const isCustom = !currencyOptions.value.some(opt => opt.value === currencyVal)
        if (isCustom) {
          selectedCurrencyOption.value = '__custom__'
          customCurrency.value = currencyVal
        } else {
          selectedCurrencyOption.value = currencyVal
          customCurrency.value = ''
        }
      }
    }
    if (wf.last_tab && !route.query.tab) activeTab.value = wf.last_tab
    applyCurrentMapping()
    showPreview.value = false
    forceUpdate.value++
  }

  const s = sessionManager.getSession(sid)
  if (!loaded && s) {
    if (s.data?.length) {
      rawData.value = s.data
      originalRawData.value = JSON.parse(JSON.stringify(s.data))
      originalFileColumns.value = Object.keys(s.data[0] || {})
      fileColumns.value = [...originalFileColumns.value]
      loaded = true
    }
    if (s.cleanedData?.length) { cleanedData.value = s.cleanedData; loaded = true }
    if (s.calculations) { calculations.value = s.calculations; loaded = true }
    if (s.uploaded_file_name) { uploadedFile.value = { name: s.uploaded_file_name, size: 0 }; loaded = true }
    if (fileColumns.value.length) {
      columnMapping.value = matchColumns(fileColumns.value, requiredColumns.value, columnVariations.value)
      applyCurrentMapping()
    }
    showPreview.value = false
    forceUpdate.value++
  }

  if (!loaded) {
    const key = `${instrumentType.value}_session_${sid}`
    const savedRaw = localStorage.getItem(`${key}_raw`)
    const savedClean = localStorage.getItem(`${key}_clean`)
    const savedCalc = localStorage.getItem(`${key}_calc`)
    const savedFileName = localStorage.getItem(`${instrumentType.value}_uploaded_file_name`)
    const savedChartData = localStorage.getItem(`${key}_chartData`)
    const savedFredFilters = localStorage.getItem(`${key}_fredFilters`)
    const savedMapping = localStorage.getItem(`${key}_mapping`)
    if (savedRaw) {
      rawData.value = JSON.parse(savedRaw)
      originalRawData.value = JSON.parse(JSON.stringify(rawData.value))
      originalFileColumns.value = Object.keys(rawData.value[0] || {})
      fileColumns.value = [...originalFileColumns.value]
      loaded = true
    }
    if (savedClean) { cleanedData.value = JSON.parse(savedClean); loaded = true }
    if (savedCalc) { calculations.value = JSON.parse(savedCalc); loaded = true }
    if (savedFileName) { uploadedFile.value = { name: savedFileName, size: 0 }; loaded = true }
    if (savedChartData) { chartData.value = JSON.parse(savedChartData); loaded = true }
    if (savedFredFilters) {
      fredFilters.value = { ...fredFilters.value, ...JSON.parse(savedFredFilters) }
      loaded = true
    }
    if (savedMapping) {
      columnMapping.value = JSON.parse(savedMapping)
      applyCurrentMapping()
    } else if (fileColumns.value.length) {
      columnMapping.value = matchColumns(fileColumns.value, requiredColumns.value, columnVariations.value)
      applyCurrentMapping()
    }
    showPreview.value = false
    forceUpdate.value++
  }

  if (cleanedData.value.length && rawData.value.length) {
    cleaningStats.value = {
      totalRows: rawData.value.length,
      validRows: cleanedData.value.length,
      removedRows: rawData.value.length - cleanedData.value.length,
      fixedMissing: 0
    }
  }
  return loaded
}

function saveSessionData() {
  const datasetId = route.query.dataset_id
  if (datasetId) {
    const payload = {
      name: uploadedFile.value?.name || `${instrumentType.value}_${Date.now()}`,
      file_base64: '',
      sheet_names: [],
      upload_id: datasetId,
      data: cleanedData.value.length ? cleanedData.value : rawData.value,
      headers: Object.keys((cleanedData.value[0] || rawData.value[0]) || {})
    }
    api.datasetAPI.save(payload.name, payload.file_base64, payload.sheet_names, payload.upload_id, payload.data, payload.headers, instrumentType.value)
    if (activeSession.value) sessionManager.updateSession(activeSession.value.id, { last_tab: activeTab.value })
    else localStorage.setItem(`instrument_${instrumentType.value}_last_tab`, activeTab.value)
    return
  }

  if (!activeSession.value) return
  const sid = activeSession.value.id
  const wf = buildWorkflowSnapshot({
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
    sessionSavedAt: sessionSavedAt.value,
    showPreview: showPreview.value
  })
  sessionManager.saveInstrumentWorkflow(sid, instrumentType.value, wf)
  sessionManager.updateSession(sid, { last_tab: activeTab.value })

  const key = `${instrumentType.value}_session_${sid}`
  localStorage.setItem(`${key}_raw`, JSON.stringify(rawData.value))
  localStorage.setItem(`${key}_original`, JSON.stringify(originalRawData.value))
  localStorage.setItem(`${key}_clean`, JSON.stringify(cleanedData.value))
  localStorage.setItem(`${key}_calc`, JSON.stringify(calculations.value))
  localStorage.setItem(`${key}_chartData`, JSON.stringify(chartData.value))
  localStorage.setItem(`${key}_mapping`, JSON.stringify(columnMapping.value))
  localStorage.setItem(`${key}_fredFilters`, JSON.stringify({ country: effectiveCountry.value, currency: effectiveCurrency.value, maturity: effectiveMaturity.value }))
  localStorage.setItem(`${key}_showPreview`, JSON.stringify(showPreview.value))
  if (uploadedFile.value) localStorage.setItem(`${instrumentType.value}_uploaded_file_name`, uploadedFile.value.name)
}

function updateSessionCompletion() {
  if (!activeSession.value) return
  if (!activeSession.value.instrumentData) activeSession.value.instrumentData = {}
  activeSession.value.instrumentData[instrumentType.value] = {
    ...calculations.value,
    completed: !!calculations.value.totalValue,
    timestamp: new Date().toISOString(),
    chartData: chartData.value
  }

  let totalValue = 0
  let completedCount = 0
  for (const [instId, data] of Object.entries(activeSession.value.instrumentData)) {
    if (data.completed) {
      totalValue += parseFloat(data.totalValue) || 0
      completedCount++
    }
  }
  activeSession.value.totalValue = totalValue
  activeSession.value.instrumentCount = completedCount
  activeSession.value.status = completedCount === 3 ? 'completed' : 'in-progress'

  sessionManager.updateSession(activeSession.value.id, {
    totalValue: activeSession.value.totalValue,
    instrumentCount: activeSession.value.instrumentCount,
    status: activeSession.value.status,
    instrumentData: activeSession.value.instrumentData
  })
}

// ========== Data Update Handlers ==========
function onRawExcelUpdate(data, sourceData) {
  if (sourceData?.length) originalRawData.value = sourceData
  rawData.value = data
  debouncedSave()
}
function onCleanedExcelUpdate(data) { cleanedData.value = data; debouncedSave(); calculateMetrics() }
function onExcelDataUpdate(data) { excelData.value = data; if (activeTab.value === 'upload') rawData.value = data; if (cleanedData.value.length) cleanedData.value = data; debouncedSave() }

let saveTimeout = null
function debouncedSave() { if (saveTimeout) clearTimeout(saveTimeout); saveTimeout = setTimeout(() => { saveSessionData() }, 500) }

watch([rawData, cleanedData], () => debouncedSave(), { deep: true })
watch(cleanedData, async (newVal) => { if (newVal.length) await calculateMetrics() }, { deep: true })
watch(chartData, async () => {
  if (activeTab.value === 'visualizations' && yieldCurveChart.value && chartData.value.datasets?.length) {
    await nextTick()
    if (chartInstanceRef.current) chartInstanceRef.current.destroy()
    await renderFredLineChart(yieldCurveChart, chartData.value, chartInstanceRef)
  }
}, { deep: true })
watch(() => activeTab.value, async (newTab) => {
  if (newTab === 'visualizations' && hasCleanedData.value && !chartData.value.datasets.length && !fredLoading.value) {
    await fetchFredData()
  }
})

watch([rawData, cleanedData, calculations, chartData], () => {
  forceUpdate.value++
}, { deep: true })

// ========== FRED Functions ==========
const fredCategories = ref({})
const availableSeries = computed(() => fredCategories.value.interest_rates || {})
const selectedSeriesLabel = computed(() => availableSeries.value[selectedSeries.value] || selectedSeries.value)

function getCountryLabel(code) { const found = countryOptions.value.find(c => c.value === code); return found ? found.label : code }
function getCurrencyLabel(code) { const found = currencyOptions.value.find(c => c.value === code); return found ? found.label : code }

function onCountrySelectChange() {
  if (selectedCountryOption.value !== '__custom__') {
    fredFilters.value.country = selectedCountryOption.value
    onFredFilterChange()
  } else {
    fredFilters.value.country = customCountry.value
    if (customCountry.value) onFredFilterChange()
  }
}
function onCustomCountryChange() {
  if (selectedCountryOption.value === '__custom__') {
    fredFilters.value.country = customCountry.value
    onFredFilterChange()
  }
}
function onCurrencySelectChange() {
  if (selectedCurrencyOption.value !== '__custom__') {
    fredFilters.value.currency = selectedCurrencyOption.value
    onFredFilterChange()
  } else {
    fredFilters.value.currency = customCurrency.value
    if (customCurrency.value) onFredFilterChange()
  }
}
function onCustomCurrencyChange() {
  if (selectedCurrencyOption.value === '__custom__') {
    fredFilters.value.currency = customCurrency.value
    onFredFilterChange()
  }
}
function onMaturitySelectChange() {
  if (selectedMaturityOption.value !== '__custom__') {
    fredFilters.value.maturity = selectedMaturityOption.value
    onFredFilterChange()
  } else {
    fredFilters.value.maturity = customMaturity.value
    if (customMaturity.value) onFredFilterChange()
  }
}
function onCustomMaturityChange() {
  if (selectedMaturityOption.value === '__custom__') {
    fredFilters.value.maturity = customMaturity.value
    onFredFilterChange()
  }
}

const CACHE_KEY = 'fred_chart_cache'
const CACHE_DURATION = 5 * 60 * 1000

async function fetchFredData() {
  fredLoading.value = true
  fredError.value = ''
  try {
    const cacheKey = `${CACHE_KEY}_${instrumentType.value}_${effectiveCountry.value}_${effectiveCurrency.value}_${effectiveMaturity.value}`
    const cached = localStorage.getItem(cacheKey)
    if (cached) {
      const parsed = JSON.parse(cached)
      if (Date.now() - parsed.timestamp < CACHE_DURATION) {
        chartData.value = parsed.data
        currentMarketRate.value = parsed.data.latest
        chartSeriesLabel.value = parsed.seriesLabel || 'FRED'
        fredLoading.value = false
        forceUpdate.value++
        return
      }
    }

    const sid = await seriesIdForMaturity()
    if (!sid) throw new Error('Could not resolve FRED series')
    selectedSeries.value = sid
    chartSeriesLabel.value = availableSeries.value[sid] || sid
    const loaded = await loadFredSeriesChart(sid)
    if (!loaded) throw new Error('No FRED data')
    chartData.value = loaded
    currentMarketRate.value = loaded.latest

    localStorage.setItem(cacheKey, JSON.stringify({
      timestamp: Date.now(),
      data: loaded,
      seriesLabel: chartSeriesLabel.value
    }))

    if (activeSession.value) {
      if (!activeSession.value.instrumentData) activeSession.value.instrumentData = {}
      if (!activeSession.value.instrumentData[instrumentType.value]) activeSession.value.instrumentData[instrumentType.value] = {}
      activeSession.value.instrumentData[instrumentType.value].chartData = loaded
      sessionManager.updateSession(activeSession.value.id, { instrumentData: activeSession.value.instrumentData })
    }
    await nextTick()
    if (yieldCurveChart.value) {
      if (chartInstanceRef.current) chartInstanceRef.current.destroy()
      await renderFredLineChart(yieldCurveChart, chartData.value, chartInstanceRef)
    }
    forceUpdate.value++
  } catch (err) {
    console.error(err)
    fredError.value = err.message || 'Failed to load market data.'
    chartData.value = { labels: [], datasets: [] }
  } finally {
    fredLoading.value = false
  }
}

function defaultMaturityForInstrument() {
  return instrumentType.value === 'bonds' ? '10Y' : instrumentType.value === 'money-market' ? '1Y' : instrumentType.value === 'tbills' ? '13W' : '3M'
}

async function enrichCalculationsWithFred() {
  try {
    const bench = await fetchBenchmark(instrumentType.value)
    if (bench?.benchmark_rate != null) {
      const portfolio = parseFloat(portfolioAvgRate.value) || 0
      calculations.value.fred = { ...bench, spread_vs_market: +(portfolio - bench.benchmark_rate).toFixed(2) }
    }
  } catch (e) { console.error(e) }
}

async function onFredFilterChange() {
  if (activeTab.value === 'visualizations') await fetchFredData()
  if (Object.keys(calculations.value).length) enrichCalculationsWithFred()
  debouncedSave()
}

// ========== Lifecycle ==========
let lastInstrument = '', lastSessionId = ''
async function checkAndReset() {
  const currentSessionId = sessionManager.getActiveSessionId() || route.query.session || null
  const currentInstrument = instrumentType.value
  if (currentInstrument !== lastInstrument || currentSessionId !== lastSessionId) {
    lastInstrument = currentInstrument
    lastSessionId = currentSessionId
    if (currentSessionId) {
      const s = sessionManager.getSession(String(currentSessionId))
      activeSession.value = s || null
    } else {
      activeSession.value = null
    }
    const loaded = await loadSavedData()
    if (!loaded) {
      refreshPage()
      if (!route.query.tab) activeTab.value = 'upload'
    } else {
      if (!route.query.tab) {
        const savedTab = sessionManager.getInstrumentWorkflow(activeSession.value?.id, instrumentType.value)?.last_tab
        if (savedTab && steps.value.some(s => s.tab === savedTab)) {
          activeTab.value = savedTab
        } else {
          activeTab.value = 'upload'
        }
      }
      if (cleanedData.value.length) await calculateMetrics()
      if (activeTab.value === 'visualizations' && !chartData.value.datasets.length) await fetchFredData()
    }
    debouncedSave()
  }
}

onMounted(async () => {
  await loadConfig(instrumentType.value)
  const qSid = route.query.session
  if (qSid) {
    await sessionManager.loadSessionFromDb(String(qSid))
    const s = sessionManager.getSession(String(qSid))
    if (s) {
      activeSession.value = s
      sessionManager.setActiveSession(s)
    }
  }
  await checkAndReset()
  loadUploadHistory()
  await loadSavedTemplates()
  window.addEventListener('storage', () => checkAndReset())
  await loadFilterOptions()
  if (!effectiveMaturity.value) {
    const def = defaultMaturityForInstrument()
    selectedMaturityOption.value = def
    fredFilters.value.maturity = def
  }
  try {
    const res = await api.fredAPI.getCategories()
    if (res?.success && res.categories) {
      fredCategories.value = res.categories
      selectedSeries.value = (await seriesIdForMaturity()) || Object.keys(fredCategories.value.interest_rates || {})[0]
    }
  } catch (err) { console.error(err) }
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
/* ===== ALL ORIGINAL STYLES – UNCHANGED ===== */
.instrument-page { padding: 20px; max-width: 1400px; margin: 0 auto; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px; padding: 0 10px; }
.header-left h1 { color: #0B2044; font-size: 28px; font-weight: 700; margin-bottom: 5px; }
.header-left p { color: #666; font-size: 14px; }
.session-badge { background: #e8ecf1; padding: 4px 8px; border-radius: 12px; font-size: 12px; display: inline-flex; align-items: center; gap: 4px; margin-top: 8px; }
.session-badge.warning { background: #fff3e0; color: #e65100; }
.step-indicator { background: white; padding: 8px 16px; border-radius: 20px; font-size: 13px; color: #0B2044; font-weight: 600; }

.progress-bar-container { margin-bottom: 30px; padding: 0 10px; }
.progress-steps { display: flex; justify-content: space-between; align-items: center; background: white; padding: 20px; border-radius: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }
.progress-step { flex: 1; text-align: center; cursor: pointer; }
.progress-step.disabled { cursor: not-allowed; opacity: 0.5; }
.step-circle { width: 36px; height: 36px; background: #e0e0e0; color: #999; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; font-weight: 700; transition: all 0.3s; }
.progress-step.active .step-circle { background: #0B2044; color: white; box-shadow: 0 0 0 4px rgba(11,32,68,0.2); }
.progress-step.completed .step-circle { background: #4CAF50; color: white; }
.step-label { font-size: 11px; color: #999; margin-top: 8px; }
.progress-step.active .step-label { color: #0B2044; font-weight: 600; }

.content-card { margin-bottom: 20px; }
.upload-area { border: 2px dashed #ccc; border-radius: 12px; padding: 50px; text-align: center; cursor: pointer; transition: all 0.3s; }
.upload-area:hover { border-color: #0B2044; background: #f8f9ff; }
.browse-link { color: #0B2044; cursor: pointer; font-weight: 600; }
.file-info { margin-top: 20px; padding: 12px; background: #f5f5f5; border-radius: 8px; display: flex; align-items: center; gap: 10px; }
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
.btn-review-excel-small { background: #2196F3; color: white; border: none; padding: 4px 10px; border-radius: 6px; cursor: pointer; display: inline-flex; align-items: center; gap: 4px; font-size: 11px; transition: all 0.2s; }
.btn-review-excel-small:hover { background: #0b7dda; }
.excel-dialog-title { background: #0B2044; color: white; padding: 16px 24px; }
.btn-close-dialog { background: transparent; border: none; color: white; cursor: pointer; padding: 8px; border-radius: 50%; }
.btn-close-dialog:hover { background: rgba(255,255,255,0.1); }
.excel-dialog-content { padding: 0; height: calc(100vh - 140px); }
.mapping-instructions { background: #e3f2fd; padding: 12px 16px; border-radius: 8px; margin-bottom: 16px; font-size: 14px; color: #0B2044; }
.mapping-instructions p { margin: 0; display: flex; align-items: center; gap: 8px; }
.mapping-grid { display: flex; flex-direction: column; gap: 15px; margin: 20px 0; }
.mapping-row { display: flex; align-items: center; gap: 15px; }
.required-label { width: 140px; font-weight: 600; color: #0B2044; }
.mapping-select { flex: 1; padding: 10px; border: 1px solid #ddd; border-radius: 8px; font-size: 14px; }
.mapping-hint { margin-top: 15px; padding: 10px; background: #f8f9ff; border-radius: 8px; display: flex; align-items: center; gap: 8px; color: #666; }

/* ===== SAVED MAPPINGS STYLES ===== */
.saved-mappings-section {
  margin-top: 20px;
  padding: 16px;
  background: #f8f9ff;
  border-radius: 8px;
  border: 1px solid #e8ecf1;
}
.saved-mappings-title {
  color: #0B2044;
  font-size: 15px;
  font-weight: 600;
  margin: 0 0 12px 0;
}
.saved-mappings-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.saved-mappings-row .template-select,
.saved-mappings-row .template-input {
  padding: 6px 10px;
  border: 1px solid #ccc;
  border-radius: 6px;
  font-size: 13px;
  background: white;
}
.saved-mappings-row .template-select:focus,
.saved-mappings-row .template-input:focus {
  outline: none;
  border-color: #0B2044;
}
.saved-mappings-row .btn-primary,
.saved-mappings-row .btn-secondary {
  padding: 6px 14px;
  font-size: 12px;
  border-radius: 6px;
  border: none;
  cursor: pointer;
  white-space: nowrap;
}
.saved-mappings-row .btn-primary {
  background: #0B2044;
  color: white;
}
.saved-mappings-row .btn-primary:hover {
  background: #1a3a6e;
}
.saved-mappings-row .btn-secondary {
  background: #e0e0e0;
  color: #333;
}
.saved-mappings-row .btn-secondary:hover {
  background: #c0c0c0;
}

/* ===== REST OF ORIGINAL STYLES – UNCHANGED ===== */
.required-columns { margin: 20px 0; }
.columns-list { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 10px; }
.column-badge { background: #e8ecf1; padding: 6px 12px; border-radius: 20px; font-size: 12px; display: inline-flex; align-items: center; gap: 6px; }
.column-badge.missing-column { background: #FFEBEE; color: #c62828; }
.column-badge.mapped-column { background: #E8F5E9; color: #2E7D32; }
.success-message { margin-top: 10px; padding: 8px 12px; background: #E8F5E9; border-radius: 8px; display: flex; align-items: center; gap: 8px; font-size: 12px; color: #2E7D32; }
.warning-message { margin-top: 10px; padding: 8px 12px; background: #FFF3E0; border-radius: 8px; display: flex; align-items: center; gap: 8px; font-size: 12px; color: #E65100; }
.cleaning-options-panel { background: #f8f9ff; padding: 20px; border-radius: 12px; margin-bottom: 20px; }
.filter-scroll-container { max-height: 200px; overflow-y: auto; border: 1px solid #e0e0e0; border-radius: 8px; background: #fafafa; margin: 12px 0; padding: 8px 4px; scrollbar-width: thin; }
.options-list { display: flex; flex-direction: column; gap: 8px; }
.option-checkbox { display: flex; align-items: center; gap: 8px; font-size: 14px; padding: 4px 8px; border-radius: 4px; transition: background 0.1s; }
.option-checkbox:hover { background: #f0f0f0; }
.option-checkbox select, .option-checkbox input[type="text"] { margin-left: 4px; padding: 2px 6px; font-size: 13px; border: 1px solid #ccc; border-radius: 4px; }
.cleaning-buttons { display: flex; gap: 12px; margin-top: 15px; }
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
.visualization-placeholder { text-align: center; padding: 60px; background: #f8f9ff; border-radius: 12px; }
.visualization-placeholder h3 { color: #0B2044; margin: 20px 0 10px; }
.visualization-placeholder p { color: #666; margin-bottom: 20px; }
.summary-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; margin-bottom: 30px; }
.summary-section { padding: 20px; background: #f8f9ff; border-radius: 12px; }
.summary-section h3 { color: #0B2044; margin-bottom: 15px; }
.summary-section p { margin: 8px 0; color: #555; }
.report-options { padding: 20px; }
.instrument-selection { background: #f8f9ff; padding: 20px; border-radius: 12px; margin-bottom: 20px; }
.selection-cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin: 20px 0; }
.selection-card { display: flex; flex-direction: column; align-items: center; gap: 12px; padding: 20px 16px; background: white; border-radius: 12px; cursor: pointer; transition: all 0.2s; border: 2px solid #e0e0e0; position: relative; text-align: center; }
.selection-card:hover { transform: translateY(-2px); box-shadow: 0 4px 8px rgba(0,0,0,0.1); border-color: #0B2044; }
.selection-card.active { border-color: #0B2044; background: #f8f9ff; }
.check-indicator { position: absolute; top: 12px; right: 12px; }
.selection-actions { display: flex; gap: 10px; justify-content: center; margin-top: 10px; }
.report-actions { display: flex; flex-wrap: wrap; gap: 10px; justify-content: center; margin-bottom: 20px; }
.btn-preview { background: #673AB7; color: white; padding: 8px 16px; border-radius: 6px; border: none; cursor: pointer; display: inline-flex; align-items: center; gap: 5px; }
.btn-json { background: #607d8b; }
.btn-csv { background: #4caf50; }
.btn-html { background: #ff9800; }
.btn-pdf { background: #f44336; }
.btn-word { background: #2196f3; }
.btn-excel { background: #8bc34a; }
.btn-save { background: #9c27b0; }
.btn-json, .btn-csv, .btn-html, .btn-pdf, .btn-word, .btn-excel, .btn-save { padding: 8px 16px; border-radius: 6px; border: none; cursor: pointer; display: inline-flex; align-items: center; gap: 5px; color: white; }
.empty-state { text-align: center; padding: 60px; color: #999; }
.empty-state p { margin: 20px 0; }
.navigation-buttons { display: flex; gap: 15px; justify-content: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e0e0e0; }
.btn-primary { background: linear-gradient(135deg, #0B2044, #1E88E5); color: white; border: none; padding: 12px 28px; border-radius: 10px; font-size: 14px; font-weight: 600; cursor: pointer; transition: all 0.3s; }
.btn-primary:hover:not(:disabled) { transform: translateY(-2px); box-shadow: 0 6px 15px rgba(11,32,68,0.3); }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-secondary { background: white; color: #0B2044; border: 2px solid #0B2044; padding: 12px 28px; border-radius: 10px; font-size: 14px; font-weight: 600; cursor: pointer; transition: all 0.3s; }
.btn-secondary:hover { background: #0B2044; color: white; transform: translateY(-2px); }
.highlight-box { background: #e8f5e9; padding: 12px; border-radius: 8px; margin-bottom: 20px; }
.comparison-card { background: linear-gradient(135deg, #f8f9ff, #eef2ff); border-radius: 12px; padding: 16px; margin-bottom: 20px; display: flex; justify-content: space-around; align-items: center; flex-wrap: wrap; gap: 15px; }
.comparison-item { text-align: center; }
.comparison-label { font-size: 13px; color: #666; display: block; }
.comparison-value { font-size: 24px; font-weight: 700; }
.comparison-value.portfolio { color: #0B2044; }
.comparison-value.market { color: #1E88E5; }
.comparison-difference { font-size: 16px; font-weight: 600; padding: 4px 12px; border-radius: 20px; }
.comparison-difference.positive { background: #e8f5e9; color: #2e7d32; }
.comparison-difference.negative { background: #ffebee; color: #c62828; }
.loading-container, .error-container { text-align: center; padding: 40px; }
.spin { animation: spin 1s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
.chart-container--fred { position: relative; height: 400px; width: 100%; background: white; border-radius: 8px; padding: 10px; }
.chart-container--fred canvas { width: 100% !important; height: 100% !important; }
.filters-row { display: flex; gap: 20px; align-items: flex-end; margin-bottom: 20px; flex-wrap: wrap; }
.filter-group { flex: 1; min-width: 150px; }
.filter-group label { display: block; font-size: 12px; font-weight: 600; color: #0B2044; margin-bottom: 4px; }
.filter-select { width: 100%; padding: 10px 12px; border: 1px solid #ddd; border-radius: 8px; background: white; color: #0B2044; font-size: 14px; cursor: pointer; transition: border 0.2s; }
.filter-select:focus { outline: none; border-color: #0B2044; }
.filter-select option { color: #0B2044; background: white; }
.custom-maturity-input { margin-top: 8px; }
.refresh-btn { flex-shrink: 0; align-self: flex-end; }
.report-hint { font-size: 14px; color: #555; margin-bottom: 16px; padding: 12px; background: #f0f4f8; border-radius: 8px; }
.summary-hero { display: flex; justify-content: space-around; flex-wrap: wrap; gap: 24px; margin-bottom: 24px; padding: 30px 20px; background: linear-gradient(135deg, #0B2044, #1E88E5); border-radius: 16px; color: white; text-align: center; }
.hero-stat { flex: 1; min-width: 140px; display: flex; flex-direction: column; align-items: center; }
.hero-value { font-size: 32px; font-weight: 700; margin-bottom: 4px; }
.hero-label { font-size: 14px; opacity: 0.9; }
.card-panel { background: #f8f9ff; padding: 16px; border-radius: 10px; border: 1px solid #e8ecf1; }
.fred-calc-card { margin: 16px 0; }
.fred-meta { display: block; margin-top: 8px; color: #666; font-size: 12px; }
.chart-footer { margin-top: 10px; text-align: center; color: #666; font-size: 12px; }
.report-preview-content { padding: 0; }
.report-preview-content iframe { width: 100%; height: 80vh; border: none; }
.upload-history { margin-top: 20px; padding: 15px; background: #f8f9ff; border-radius: 12px; }
.history-list { max-height: 200px; overflow-y: auto; }
.history-item { display: flex; align-items: center; gap: 12px; padding: 8px 12px; border-bottom: 1px solid #eee; cursor: pointer; transition: background 0.2s; }
.history-item:hover { background: #e8ecf1; }
.history-item small { font-size: 11px; color: #666; margin-left: auto; }
.btn-delete-history { background: none; border: none; cursor: pointer; color: #f44336; font-size: 16px; }
.excel-viewer-button { margin-bottom: 20px; text-align: right; }
.formula-dialog-title { background: #0B2044; color: white; }
.formula-text { font-size: 16px; padding: 16px; background: #f8f9ff; border-radius: 8px; margin-top: 8px; }

/* Resizable Excel columns and rows */
.excel-edit-table th { resize: horizontal; overflow: auto; }
.excel-edit-table td { resize: vertical; overflow: auto; }
</style>

<style>
/* ===== GLOBAL OVERRIDES – UNCHANGED ===== */
html, body, #app, .v-application, .v-application--wrap, .fixed-layout, .v-main, .v-content { max-width: 100vw !important; overflow-x: hidden !important; }
.instrument-page { max-width: 100% !important; overflow-x: hidden !important; }
.instrument-page .excel-table-wrapper, .instrument-page .excel-preview-section, .instrument-page .preview-section, .instrument-page .excel-scroll-wrapper, .instrument-page .excel-dialog-content { overflow-x: auto !important; max-width: 100% !important; }
.instrument-page .excel-viewer { max-width: 100% !important; overflow-x: hidden !important; }
.instrument-page .excel-edit-table { max-width: 100% !important; table-layout: fixed !important; width: 100% !important; }
.instrument-page .excel-edit-table th, .instrument-page .excel-edit-table td { white-space: nowrap !important; overflow: hidden !important; text-overflow: ellipsis !important; max-width: 200px !important; }
.instrument-page .filters-row select, .instrument-page .filters-row .filter-select, .instrument-page .filters-row select:focus, .instrument-page .filters-row .filter-select:focus { color: #000000 !important; background-color: #ffffff !important; }
</style>