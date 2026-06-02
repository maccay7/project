<template>
  <FixedLayout>
    <div class="instrument-page">
      <!-- Page Header with Session Name -->
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
            :class="{ active: activeTab === step.tab, completed: getTabStatus(step.tab) }"
            @click="switchTab(step.tab)"
          >
            <div class="step-circle">{{ index + 1 }}</div>
            <div class="step-label">{{ step.name }}</div>
          </div>
        </div>
      </div>

      <!-- Content based on active tab -->
      <div class="tab-content">
        <!-- ==================== UPLOAD TAB ==================== -->
        <div v-if="activeTab === 'upload'" class="content-card">
          <v-card>
            <v-card-title><v-icon>mdi-upload</v-icon> Upload {{ instrumentName }} Dataset</v-card-title>
            <v-card-text>
              <div class="upload-area" @dragover.prevent @drop.prevent="handleDrop">
                <input type="file" ref="fileInput" @change="handleFileUpload" accept=".csv,.xlsx,.xls" style="display: none">
                <v-icon size="48" color="#0B2044">mdi-cloud-upload</v-icon>
                <p>Drag & drop or <span class="browse-link" @click="$refs.fileInput.click()">browse</span></p>
                <small>Supported: CSV, Excel files</small>
              </div>

              <div v-if="uploadedFile" class="file-info">
                <v-icon>mdi-file-excel</v-icon>
                <span>{{ uploadedFile.name }}</span>
                <span class="file-size">{{ fileSize }}</span>
                <button class="remove-btn" @click="removeFile">×</button>
                <button class="btn-review-excel" @click="openExcelReview(rawData, 'Uploaded Data')" :disabled="!rawData.length">Review Excel</button>
                <button class="btn-mapping" @click="autoMatchColumns" :disabled="!rawData.length">Map Columns</button>
              </div>

              <div v-if="rawData.length" class="excel-preview-section">
                <h4>File Preview:</h4>
                <div class="preview-toolbar">
                  <span class="preview-info">{{ rawData.length }} rows × {{ Object.keys(rawData[0] || {}).length }} columns</span>
                  <div class="preview-controls">
                    <button @click="previewStartRow = Math.max(0, previewStartRow - 10)" :disabled="previewStartRow === 0" class="preview-btn">← Previous</button>
                    <span>Rows {{ previewStartRow + 1 }} - {{ Math.min(previewEndRow, rawData.length) }}</span>
                    <button @click="previewStartRow = Math.min(rawData.length - previewRows, previewStartRow + 10)" :disabled="previewEndRow >= rawData.length" class="preview-btn">Next →</button>
                    <button class="btn-review-excel-small" @click="openExcelReview(rawData, 'Uploaded Data')">Full Screen</button>
                  </div>
                </div>
                <div class="table-wrapper">
                  <table class="data-table">
                    <thead>
                      <tr>
                        <th>#</th>
                        <th v-for="col in previewColumnsList" :key="col">{{ col }}</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="(row, idx) in paginatedPreviewData" :key="idx">
                        <td class="row-number">{{ previewStartRow + idx + 1 }}</td>
                        <td v-for="col in previewColumnsList" :key="col">{{ formatCellValue(row[col]) }}</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>

              <!-- Column Mapping Dialog -->
              <v-dialog v-model="showMappingDialog" max-width="700px">
                <v-card>
                  <v-card-title>Map Columns</v-card-title>
                  <v-card-text>
                    <div class="mapping-grid">
                      <div v-for="reqCol in requiredColumns" :key="reqCol" class="mapping-row">
                        <label class="required-label">{{ reqCol }}:</label>
                        <select v-model="columnMapping[reqCol]" class="mapping-select">
                          <option :value="null">-- Select column --</option>
                          <option v-for="fileCol in fileColumns" :key="fileCol" :value="fileCol">{{ fileCol }}</option>
                        </select>
                      </div>
                    </div>
                    <div class="mapping-hint"><v-icon size="16">mdi-information</v-icon><small>Column names are matched automatically.</small></div>
                  </v-card-text>
                  <v-card-actions>
                    <button class="btn-secondary" @click="showMappingDialog = false">Cancel</button>
                    <button class="btn-primary" @click="applyColumnMapping">Apply Mapping</button>
                  </v-card-actions>
                </v-card>
              </v-dialog>

              <div class="required-columns">
                <h4>Required Columns:</h4>
                <div class="columns-list">
                  <span v-for="col in requiredColumns" :key="col" class="column-badge" :class="{ 'missing-column': rawData.length && !hasRequiredColumn(col) }">
                    <v-icon size="12">{{ rawData.length && hasRequiredColumn(col) ? 'mdi-check' : 'mdi-close' }}</v-icon>
                    {{ col }}
                  </span>
                </div>
                <div v-if="rawData.length && missingColumns.length" class="warning-message">
                  <v-icon color="warning">mdi-alert</v-icon><span>Missing required columns. Click "Map Columns".</span>
                </div>
              </div>

              <div class="navigation-buttons">
                <button v-if="rawData.length && missingColumns.length" class="btn-warning" @click="autoMatchColumns">Map Columns</button>
                <button class="btn-primary" @click="uploadData" :disabled="!uploadedFile || (rawData.length && missingColumns.length)">Upload & Continue</button>
                <button class="btn-secondary" @click="goToDashboard">Cancel</button>
              </div>
            </v-card-text>
          </v-card>
        </div>

        <!-- ==================== CLEANING TAB ==================== -->
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
                      <!-- full list of cleaning options (same as original) -->
                      <label class="option-checkbox"><input type="checkbox" v-model="cleaningOptions.removeDuplicates"> Remove duplicate rows</label>
                      <label class="option-checkbox"><input type="checkbox" v-model="cleaningOptions.fillMissingNumeric"> Fill missing numeric with:
                        <select v-model="cleaningOptions.fillMethod"><option value="zero">Zero</option><option value="mean">Mean</option><option value="median">Median</option></select>
                      </label>
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
                    <button class="btn-primary" @click="previewCleanedData">Preview Cleaned Data</button>
                    <button class="btn-primary" @click="applyCleaningOnly">Apply Cleaning</button>
                  </div>
                </div>

                <div v-if="previewData.length" class="preview-section">
                  <h4>Preview of Cleaned Data ({{ previewData.length }} rows)</h4>
                  <div class="table-wrapper">
                    <table class="data-table">
                      <thead>
                        <tr>
                          <th>#</th>
                          <th v-for="col in previewColumnsListClean" :key="col">{{ col }}</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr v-for="(row, idx) in previewData.slice(0,10)" :key="idx">
                          <td class="row-number">{{ idx+1 }}</td>
                          <td v-for="col in previewColumnsListClean" :key="col">{{ formatCellValue(row[col]) }}</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                  <p v-if="previewData.length > 10" class="preview-note">Showing first 10 rows</p>
                </div>

                <div v-if="cleanedData.length" class="highlight-box">
                  <p>✓ Removed {{ cleaningStats.removedRows }} invalid rows</p>
                  <p>✓ Fixed {{ cleaningStats.fixedMissing }} missing values</p>
                  <p class="success-text">✓ Data is now clean and ready for calculations</p>
                </div>

                <div v-if="rawData.length && !cleanedData.length && !previewData.length" class="preview-section">
                  <h4>Raw Data with Issues Highlighted:</h4>
                  <div class="legend"><span class="legend-badge invalid-row-badge">⚠ Invalid Row</span><span class="legend-badge invalid-cell-badge">❌ Missing/Invalid Value</span></div>
                  <div class="preview-toolbar">
                    <span class="preview-info">{{ rawData.length }} rows</span>
                    <div class="preview-controls">
                      <button @click="rawPreviewStartRow = Math.max(0, rawPreviewStartRow - 10)" :disabled="rawPreviewStartRow === 0">← Previous</button>
                      <span>Rows {{ rawPreviewStartRow + 1 }} - {{ Math.min(rawPreviewEndRow, rawData.length) }}</span>
                      <button @click="rawPreviewStartRow = Math.min(rawData.length - rawPreviewRows, rawPreviewStartRow + 10)" :disabled="rawPreviewEndRow >= rawData.length">Next →</button>
                    </div>
                  </div>
                  <div class="table-wrapper">
                    <table class="data-table">
                      <thead>
                        <tr>
                          <th>#</th>
                          <th v-for="col in rawPreviewColumnsList" :key="col">{{ col }}</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr v-for="(row, idx) in paginatedRawPreview" :key="idx" :class="{ 'invalid-row': hasInvalidData(row) }">
                          <td class="row-number">{{ rawPreviewStartRow + idx + 1 }}</td>
                          <td v-for="col in rawPreviewColumnsList" :key="col" :class="{ 'invalid-cell': isInvalidValue(row[col]) }">{{ formatCellValue(row[col]) }}</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>

                <div class="navigation-buttons">
                  <button class="btn-secondary" @click="switchTab('upload')">Previous</button>
                  <button class="btn-primary" @click="goToCalculations" :disabled="!hasCleanedData">Next: Calculations</button>
                  <button class="btn-secondary" @click="goToDashboard">Dashboard</button>
                </div>
              </div>
            </v-card-text>
          </v-card>
        </div>

        <!-- ==================== CALCULATIONS TAB ==================== -->
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
                  <div class="summary-card total">
                    <div class="card-label">Total Portfolio Value</div>
                    <div class="card-value">${{ calculations.totalValue?.toLocaleString() || 0 }}</div>
                  </div>
                  <div class="summary-card rate">
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
                  <div class="summary-card count">
                    <div class="card-label">Number of Instruments</div>
                    <div class="card-value">{{ calculations.instrumentCount || 0 }}</div>
                  </div>
                </div>

                <div class="calculations-section">
                  <h3>{{ instrumentName }} Calculations</h3>
                  <div class="calculations-grid">
                    <template v-if="instrumentType === 'money-market'">
                      <div class="calculation-card"><div class="calc-name">Weighted Average Rate</div><div class="calc-value">{{ calculations.weightedAvgRate || 0 }}%</div></div>
                      <div class="calculation-card"><div class="calc-name">Total Interest (Annualized)</div><div class="calc-value">${{ calculations.totalInterest?.toLocaleString() || 0 }}</div></div>
                      <div class="calculation-card"><div class="calc-name">Interest Earned</div><div class="calc-value">${{ calculations.interestEarned?.toLocaleString() || 0 }}</div></div>
                      <div class="calculation-card"><div class="calc-name">Annual Yield</div><div class="calc-value">{{ calculations.annualYield || 0 }}%</div></div>
                      <div class="calculation-card"><div class="calc-name">Effective Annual Rate</div><div class="calc-value">{{ calculations.effectiveAnnualRate || 0 }}%</div></div>
                      <div class="calculation-card"><div class="calc-name">Average Days to Maturity</div><div class="calc-value">{{ calculations.avgDaysToMaturity || 0 }} days</div></div>
                      <div class="calculation-card"><div class="calc-name">Total Principal</div><div class="calc-value">${{ calculations.totalPrincipal?.toLocaleString() || 0 }}</div></div>
                    </template>
                    <template v-else-if="instrumentType === 'bonds'">
                      <div class="calculation-card"><div class="calc-name">Weighted Average Coupon</div><div class="calc-value">{{ calculations.weightedAvgCoupon || 0 }}%</div></div>
                      <div class="calculation-card"><div class="calc-name">Total Annual Income</div><div class="calc-value">${{ calculations.totalAnnualIncome?.toLocaleString() || 0 }}</div></div>
                      <div class="calculation-card"><div class="calc-name">Average Yield to Maturity</div><div class="calc-value">{{ calculations.avgYTM || 0 }}%</div></div>
                      <div class="calculation-card"><div class="calc-name">Duration (years)</div><div class="calc-value">{{ calculations.duration || 0 }}</div></div>
                    </template>
                    <template v-else>
                      <div class="calculation-card"><div class="calc-name">Weighted Average Discount</div><div class="calc-value">{{ calculations.weightedAvgDiscount || 0 }}%</div></div>
                      <div class="calculation-card"><div class="calc-name">Total Discount</div><div class="calc-value">${{ calculations.totalDiscount?.toLocaleString() || 0 }}</div></div>
                      <div class="calculation-card"><div class="calc-name">Effective Yield</div><div class="calc-value">{{ calculations.effectiveYield || 0 }}%</div></div>
                      <div class="calculation-card"><div class="calc-name">Bond Equivalent Yield</div><div class="calc-value">{{ calculations.bondEquivalentYield || 0 }}%</div></div>
                      <div class="calculation-card"><div class="calc-name">Price per $100</div><div class="calc-value">${{ calculations.pricePer100 || 0 }}</div></div>
                      <div class="calculation-card"><div class="calc-name">Total Purchase Price</div><div class="calc-value">${{ calculations.totalPurchasePrice?.toLocaleString() || 0 }}</div></div>
                      <div class="calculation-card"><div class="calc-name">Average Investment</div><div class="calc-value">${{ calculations.avgInvestment?.toLocaleString() || 0 }}</div></div>
                      <div class="calculation-card"><div class="calc-name">Holding Period Yield</div><div class="calc-value">{{ calculations.holdingPeriodYield || 0 }}%</div></div>
                      <div class="calculation-card"><div class="calc-name">Annualized Yield</div><div class="calc-value">{{ calculations.annualizedYield || 0 }}%</div></div>
                    </template>
                  </div>
                </div>

                <div class="navigation-buttons">
                  <button class="btn-secondary" @click="switchTab('cleaning')">Previous</button>
                  <button class="btn-primary" @click="goToVisualizations">Next: Visualizations</button>
                  <button class="btn-secondary" @click="goToDashboard">Dashboard</button>
                </div>
              </div>
            </v-card-text>
          </v-card>
        </div>

        <!-- ==================== VISUALIZATIONS TAB ==================== -->
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

              <div class="chart-controls">
                <select v-model="selectedSeries" @change="fetchFredData" class="series-select">
                  <option v-for="(label, id) in availableSeries" :key="id" :value="id">{{ label }}</option>
                </select>
                <button class="btn-secondary" @click="fetchFredData" :disabled="fredLoading">Refresh</button>
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
              <div v-else-if="chartData.datasets.length" class="chart-container">
                <canvas ref="yieldCurveChart"></canvas>
                <div class="chart-footer">
                  <small>Source: Federal Reserve Economic Data (FRED) – {{ selectedSeriesLabel }}</small>
                </div>
              </div>
              <div v-else class="visualization-placeholder">
                <v-icon size="64" color="#0B2044">mdi-chart-line</v-icon>
                <h3>No Market Data Yet</h3>
                <p>Select a series above and click Refresh to load the latest yield curve.</p>
              </div>

              <div class="navigation-buttons">
                <button class="btn-secondary" @click="switchTab('calculations')">Previous</button>
                <button class="btn-primary" @click="switchTab('summary')">Next: Summary</button>
                <button class="btn-secondary" @click="goToDashboard">Dashboard</button>
              </div>
            </v-card-text>
          </v-card>
        </div>

        <!-- ==================== SUMMARY TAB ==================== -->
        <div v-if="activeTab === 'summary'" class="content-card">
          <v-card>
            <v-card-title><v-icon>mdi-file-document</v-icon> {{ instrumentName }} Summary</v-card-title>
            <v-card-text>
              <div class="summary-grid">
                <div class="summary-section">
                  <h3>Portfolio Overview</h3>
                  <p><strong>Total Value:</strong> ${{ calculations.totalValue?.toLocaleString() || 0 }}</p>
                  <p><strong>Number of Instruments:</strong> {{ calculations.instrumentCount || 0 }}</p>
                  <p><strong>Data Processed:</strong> {{ cleanedData.length }} records</p>
                  <p><strong>Rows Removed:</strong> {{ cleaningStats.removedRows }}</p>
                  <p><strong>Missing Values Fixed:</strong> {{ cleaningStats.fixedMissing }}</p>
                </div>
                <div class="summary-section">
                  <h3>Key Metrics</h3>
                  <p><strong>Average Rate:</strong> {{ instrumentType === 'money-market' ? (calculations.avgRate || 0) : instrumentType === 'bonds' ? (calculations.avgCouponRate || 0) : (calculations.avgDiscountRate || 0) }}%</p>
                  <p><strong>Weighted Average:</strong> {{ instrumentType === 'money-market' ? (calculations.weightedAvgRate || 0) : instrumentType === 'bonds' ? (calculations.weightedAvgCoupon || 0) : (calculations.weightedAvgDiscount || 0) }}%</p>
                  <p><strong>Total Interest/Discount:</strong> ${{ instrumentType === 'money-market' ? (calculations.totalInterest?.toLocaleString() || 0) : instrumentType === 'bonds' ? (calculations.totalAnnualIncome?.toLocaleString() || 0) : (calculations.totalDiscount?.toLocaleString() || 0) }}</p>
                </div>
              </div>
              <div class="summary-progress"><div class="progress-bar"><div class="progress-fill" style="width:100%"></div></div><p class="progress-text">✓ Upload ✓ Clean ✓ Calculate — Ready for Report</p></div>
              <div class="navigation-buttons">
                <button class="btn-secondary" @click="switchTab('visualizations')">Previous</button>
                <button class="btn-primary" @click="switchTab('reports')">Move to Report →</button>
                <button class="btn-secondary" @click="goToDashboard">Dashboard</button>
              </div>
            </v-card-text>
          </v-card>
        </div>

        <!-- ==================== REPORTS TAB (with Preview Report button) ==================== -->
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

                <div class="report-preview-full">
                  <h3>Report Preview</h3>
                  <div class="preview-content" v-if="reportPreviewData.instruments.length">
                    <div class="preview-header">
                      <p><strong>Session:</strong> {{ reportPreviewData.session }}</p>
                      <p><strong>Date Generated:</strong> {{ reportPreviewData.date }}</p>
                    </div>
                    <div class="preview-instruments">
                      <div v-for="inst in reportPreviewData.instruments" :key="inst.name" class="preview-instrument-card">
                        <h4>{{ inst.name }}</h4>
                        <div class="report-table-wrapper">
                          <table class="report-table">
                            <thead><tr><th>Metric</th><th>Value</th></tr></thead>
                            <tbody>
                              <tr v-for="(value, key) in inst.calculations" :key="key">
                                <td>{{ formatMetricName(key) }}</td>
                                <td class="report-value">{{ formatMetricValue(key, value) }}</td>
                              </tr>
                            </tbody>
                          </table>
                        </div>
                      </div>
                    </div>
                  </div>
                  <div v-else class="preview-empty"><p>No data available for the selected instruments. Please complete data processing for the instruments you wish to include.</p></div>
                </div>

                <div class="report-actions">
                  <!-- New Preview Report button -->
                  <button class="btn-preview" @click="previewReport">Preview Report</button>
                  <button class="btn-json" @click="downloadCombinedReport('json')">JSON</button>
                  <button class="btn-csv" @click="downloadCombinedReport('csv')">CSV</button>
                  <button class="btn-html" @click="downloadCombinedReport('html')">HTML</button>
                  <button class="btn-pdf" @click="downloadCombinedReport('pdf')">PDF</button>
                  <button class="btn-word" @click="downloadCombinedReport('word')">Word</button>
                  <button class="btn-excel" @click="downloadCombinedReport('excel')">Excel</button>
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
        <v-card-title class="excel-dialog-title">{{ excelDialogTitle }} - Excel Viewer <v-spacer></v-spacer><button class="btn-close-dialog" @click="closeExcelDialog">✕</button></v-card-title>
        <v-card-text class="excel-dialog-content">
          <div class="excel-full-view">
            <div class="excel-toolbar-full"><span>{{ excelData.length }} rows × {{ excelColumns.length }} columns</span><div><button class="btn-excel-export" @click="exportToCSV">Export CSV</button><button class="btn-excel-export" @click="exportToJSON">Export JSON</button></div></div>
            <div class="excel-full-table-wrapper">
              <table class="excel-full-table">
                <thead>
                  <tr>
                    <th class="sticky-col">#</th>
                    <th v-for="col in excelColumns" :key="col" class="sticky-header">{{ col }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(row, idx) in excelData" :key="idx">
                    <td class="sticky-col">{{ idx+1 }}</td>
                    <td v-for="col in excelColumns" :key="col">{{ formatCellValue(row[col]) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </v-card-text>
        <v-card-actions><v-spacer></v-spacer><button class="btn-secondary" @click="closeExcelDialog">Close</button></v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Report Preview Dialog (Fullscreen) -->
    <v-dialog v-model="reportPreviewDialog" max-width="90%" fullscreen hide-overlay>
      <v-card>
        <v-card-title class="excel-dialog-title">Report Preview <v-spacer></v-spacer><button class="btn-close-dialog" @click="reportPreviewDialog = false">✕</button></v-card-title>
        <v-card-text class="report-preview-content" style="padding:0;">
          <iframe :srcdoc="reportPreviewHtml" frameborder="0" style="width:100%; height:80vh;"></iframe>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <button class="btn-secondary" @click="reportPreviewDialog = false">Close</button>
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
import * as XLSX from 'xlsx'
import Chart from 'chart.js/auto'
import axios from 'axios'
import html2canvas from 'html2canvas'

const router = useRouter()
const route = useRoute()
const activeSession = ref(null)

// ========== PERSISTENCE (same as original) ==========
function refreshPage() {
  rawData.value = []
  cleanedData.value = []
  uploadedFile.value = null
  previewData.value = []
  calculations.value = {}
  cleaningStats.value = { totalRows: 0, validRows: 0, removedRows: 0, fixedMissing: 0 }
  fixedValuesTracker.value.clear()
  columnMapping.value = {}
  fileColumns.value = []
  showMappingDialog.value = false
  activeTab.value = 'upload'
  if (activeSession.value) {
    const key = `${instrumentType.value}_session_${activeSession.value.id}`
    localStorage.removeItem(`${key}_raw`)
    localStorage.removeItem(`${key}_clean`)
    localStorage.removeItem(`${key}_calc`)
    localStorage.removeItem(`${instrumentType.value}_uploaded_file_name`)
  }
}

function loadSavedData() {
  if (!activeSession.value) return false
  const uploadCompleted = getTabStatus('upload')
  if (!uploadCompleted) {
    const key = `${instrumentType.value}_session_${activeSession.value.id}`
    localStorage.removeItem(`${key}_raw`)
    localStorage.removeItem(`${key}_clean`)
    localStorage.removeItem(`${key}_calc`)
    localStorage.removeItem(`${instrumentType.value}_uploaded_file_name`)
    return false
  }
  const key = `${instrumentType.value}_session_${activeSession.value.id}`
  const savedRaw = localStorage.getItem(`${key}_raw`)
  const savedClean = localStorage.getItem(`${key}_clean`)
  const savedCalc = localStorage.getItem(`${key}_calc`)
  const savedFileName = localStorage.getItem(`${instrumentType.value}_uploaded_file_name`)
  const hasSaved = savedRaw || savedClean || savedCalc
  if (!hasSaved) return false
  if (savedRaw) rawData.value = JSON.parse(savedRaw)
  if (savedClean) cleanedData.value = JSON.parse(savedClean)
  if (savedCalc) calculations.value = JSON.parse(savedCalc)
  if (savedFileName) uploadedFile.value = { name: savedFileName, size: 0 }
  if (cleanedData.value.length && rawData.value.length) {
    cleaningStats.value = {
      totalRows: rawData.value.length,
      validRows: cleanedData.value.length,
      removedRows: rawData.value.length - cleanedData.value.length,
      fixedMissing: 0
    }
  }
  return true
}

function saveSessionData() {
  if (!activeSession.value) return
  const key = `${instrumentType.value}_session_${activeSession.value.id}`
  if (rawData.value.length) localStorage.setItem(`${key}_raw`, JSON.stringify(rawData.value))
  if (cleanedData.value.length) localStorage.setItem(`${key}_clean`, JSON.stringify(cleanedData.value))
  if (Object.keys(calculations.value).length) localStorage.setItem(`${key}_calc`, JSON.stringify(calculations.value))
  if (uploadedFile.value?.name) localStorage.setItem(`${instrumentType.value}_uploaded_file_name`, uploadedFile.value.name)
  localStorage.setItem(`instrument_${instrumentType.value}_last_tab`, activeTab.value)
}

function updateSessionCompletion() {
  if (!activeSession.value) return
  if (!activeSession.value.instrumentData) activeSession.value.instrumentData = {}
  activeSession.value.instrumentData[instrumentType.value] = {
    totalValue: calculations.value.totalValue || 0,
    count: calculations.value.instrumentCount || 0,
    completed: true,
    timestamp: new Date().toISOString()
  }
  let total = 0, count = 0
  for (const data of Object.values(activeSession.value.instrumentData)) {
    if (data.completed) { total += data.totalValue || 0; count++ }
  }
  activeSession.value.totalValue = total
  activeSession.value.instrumentCount = count
  if (count === 3) activeSession.value.status = 'completed'
  localStorage.setItem('active_session', JSON.stringify(activeSession.value))
  const sessionsList = JSON.parse(localStorage.getItem('sessions_list') || '[]')
  const idx = sessionsList.findIndex(s => s.id === activeSession.value.id)
  if (idx !== -1) sessionsList[idx] = activeSession.value
  localStorage.setItem('sessions_list', JSON.stringify(sessionsList))
}

// ========== Instrument info ==========
const instrumentType = computed(() => route.params.type || route.path.split('/').pop())
const instrumentName = computed(() => {
  const names = { 'money-market': 'Money Market', bonds: 'Bonds', tbills: 'T-Bills' }
  return names[instrumentType.value] || 'Instrument'
})
const instrumentDescription = computed(() => ({
  'money-market': 'Short-term debt instruments including treasury bills, commercial paper',
  bonds: 'Fixed income securities including government and corporate bonds',
  tbills: 'Treasury bills - short-term government securities'
}[instrumentType.value] || 'Financial instrument management'))

const steps = [
  { tab: 'upload', name: 'Upload' },
  { tab: 'cleaning', name: 'Clean' },
  { tab: 'calculations', name: 'Calculate' },
  { tab: 'visualizations', name: 'Visualize' },
  { tab: 'summary', name: 'Summary' },
  { tab: 'reports', name: 'Report' }
]

const activeTab = computed({
  get: () => route.query.tab || 'upload',
  set: (val) => router.push({ query: { tab: val } })
})
const currentStepIndex = computed(() => steps.findIndex(s => s.tab === activeTab.value))
const totalSteps = steps.length

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

const cleaningOptions = ref({
  removeDuplicates: true,
  fillMissingNumeric: true,
  fillMethod: 'mean',
  fillMissingText: true,
  dropRowsWithMissing: false,
  trimWhitespace: true,
  convertToNumbers: true,
  removeOutliers: false,
  standardizeDates: false,
  removeSpecialChars: false,
  changeCase: false,
  caseType: 'none',
  fillWithCustom: false,
  customFillValue: '',
  removeColumnsAllMissing: false,
  capOutliers: false,
  removeRowsSpecificColumnEmpty: false,
  specificColumn: '',
  standardizeNumericRange: false,
  removeEmptyRows: false,
  fillForward: false,
  fillBackward: false
})

const requiredColumns = computed(() => {
  if (instrumentType.value === 'money-market') {
    return ['Date', 'Instrument', 'Rate', 'Amount', 'MaturityDate', 'DaysToMaturity', 'Principal', 'InterestRate', 'DiscountRate', 'Price', 'FaceValue']
  } else if (instrumentType.value === 'bonds') {
    return ['Date', 'BondName', 'CouponRate', 'FaceValue', 'Yield', 'MaturityDate', 'IssueDate', 'Frequency', 'Price', 'AccruedInterest', 'DaysToMaturity', 'RedemptionValue']
  } else {
    return ['Date', 'TBillName', 'DiscountRate', 'FaceValue', 'MaturityDate', 'DaysToMaturity', 'IssueDate', 'Price', 'Yield']
  }
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

// Preview helpers
const previewRows = ref(10)
const previewStartRow = ref(0)
const previewEndRow = computed(() => Math.min(previewStartRow.value + previewRows.value, rawData.value.length))
const previewColumnsList = computed(() => rawData.value[0] ? Object.keys(rawData.value[0]).slice(0,8) : [])
const paginatedPreviewData = computed(() => rawData.value.slice(previewStartRow.value, previewEndRow.value))

const rawPreviewRows = ref(10)
const rawPreviewStartRow = ref(0)
const rawPreviewEndRow = computed(() => Math.min(rawPreviewStartRow.value + rawPreviewRows.value, rawData.value.length))
const rawPreviewColumnsList = computed(() => rawData.value[0] ? Object.keys(rawData.value[0]).slice(0,8) : [])
const paginatedRawPreview = computed(() => rawData.value.slice(rawPreviewStartRow.value, rawPreviewEndRow.value))

const previewColumnsListClean = computed(() => previewData.value[0] ? Object.keys(previewData.value[0]).slice(0,8) : [])

const fileSize = computed(() => {
  if (!uploadedFile.value) return ''
  const bytes = uploadedFile.value.size
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024*1024) return (bytes/1024).toFixed(2) + ' KB'
  return (bytes/(1024*1024)).toFixed(2) + ' MB'
})

const hasRequiredColumn = (col) => rawData.value.length && Object.keys(rawData.value[0]).includes(col)
const missingColumns = computed(() => requiredColumns.value.filter(col => !hasRequiredColumn(col)))
const hasData = computed(() => rawData.value.length > 0)
const hasCleanedData = computed(() => cleanedData.value.length > 0)

function formatCellValue(value) {
  if (value === undefined || value === null) return '-'
  if (typeof value === 'number') return value.toFixed(2)
  if (typeof value === 'string' && value.length > 30) return value.substring(0,27)+'...'
  return value
}

function hasInvalidData(row) {
  if (!row) return false
  return requiredColumns.value.some(col => !row[col] || row[col] === '' || row[col] === null)
}
function isInvalidValue(value) { return !value || value === '' || value === null }

// Navigation
function goToDashboard() { router.push('/dashboard') }
function switchTab(tab) { activeTab.value = tab; saveSessionData() }
function goToCalculations() {
  if (hasCleanedData.value) {
    activeTab.value = 'calculations'
    updateStatus('calculations', true)
    saveSessionData()
  } else alert('Please clean your data first (click Apply Cleaning).')
}
function goToVisualizations() {
  if (hasCleanedData.value) {
    activeTab.value = 'visualizations'
    updateStatus('visualizations', true)
    saveSessionData()
  } else alert('Please clean your data first.')
}
function updateStatus(tab, completed) {
  const statuses = JSON.parse(localStorage.getItem(`instrument_${instrumentType.value}_status`) || '{}')
  statuses[tab] = completed
  localStorage.setItem(`instrument_${instrumentType.value}_status`, JSON.stringify(statuses))
}
function getTabStatus(tab) {
  const statuses = JSON.parse(localStorage.getItem(`instrument_${instrumentType.value}_status`) || '{}')
  return statuses[tab] || false
}

// File upload & column mapping
const fileInput = ref(null)
function handleFileUpload(e) { const file = e.target.files[0]; if (file) { uploadedFile.value = file; readFileData(file) } }
function handleDrop(e) { const file = e.dataTransfer.files[0]; if (file) { uploadedFile.value = file; readFileData(file) } }
async function readFileData(file) {
  const ext = file.name.split('.').pop().toLowerCase()
  let data = []
  try {
    if (ext === 'csv') {
      const text = await file.text()
      const lines = text.split('\n')
      const headers = lines[0].split(',').map(h => h.trim())
      data = lines.slice(1).filter(l=>l.trim()).map(line => {
        const vals = line.split(',')
        const row = {}
        headers.forEach((h,i) => { row[h] = vals[i] ? vals[i].trim() : '' })
        return row
      })
    } else {
      const buffer = await file.arrayBuffer()
      const workbook = XLSX.read(buffer)
      const sheet = workbook.Sheets[workbook.SheetNames[0]]
      data = XLSX.utils.sheet_to_json(sheet)
    }
    rawData.value = data
    saveSessionData()
    if (missingColumns.value.length) autoMatchColumns()
  } catch(err) { console.error(err); alert('Error reading file') }
}
function removeFile() {
  uploadedFile.value = null
  rawData.value = []
  cleanedData.value = []
  previewData.value = []
  calculations.value = {}
  fixedValuesTracker.value.clear()
  saveSessionData()
  if (fileInput.value) fileInput.value.value = ''
}
function autoMatchColumns() {
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
  showMappingDialog.value = true
}
function applyColumnMapping() {
  if (!rawData.value.length) return
  const mapped = rawData.value.map(row => {
    const newRow = {}
    requiredColumns.value.forEach(reqCol => {
      const src = columnMapping.value[reqCol]
      newRow[reqCol] = (src && row[src] !== undefined) ? row[src] : null
    })
    return newRow
  })
  rawData.value = mapped
  saveSessionData()
  showMappingDialog.value = false
  alert('Columns mapped successfully!')
}
async function uploadData() {
  if (!uploadedFile.value) return
  if (rawData.value.length && missingColumns.value.length === 0) {
    activeTab.value = 'cleaning'
    updateStatus('upload', true)
    saveSessionData()
  } else alert('Please map missing columns first')
}

// ========== CLEANING FUNCTIONS ==========
function previewCleanedData() {
  if (!rawData.value.length) return
  let data = JSON.parse(JSON.stringify(rawData.value))
  // Apply all cleaning steps (same as original)
  if (cleaningOptions.value.removeDuplicates) {
    const seen = new Set()
    data = data.filter(row => {
      const key = JSON.stringify(row)
      if (seen.has(key)) return false
      seen.add(key)
      return true
    })
  }
  if (cleaningOptions.value.removeEmptyRows) {
    data = data.filter(row => Object.values(row).some(v => v !== null && v !== '' && v !== undefined))
  }
  if (cleaningOptions.value.trimWhitespace) {
    data = data.map(row => {
      const newRow = {}
      Object.keys(row).forEach(k => {
        newRow[k] = typeof row[k] === 'string' ? row[k].trim() : row[k]
      })
      return newRow
    })
  }
  if (cleaningOptions.value.convertToNumbers) {
    data = data.map(row => {
      const newRow = { ...row }
      Object.keys(newRow).forEach(k => {
        if (typeof newRow[k] === 'string' && !isNaN(newRow[k]) && newRow[k].trim() !== '') {
          newRow[k] = parseFloat(newRow[k])
        }
      })
      return newRow
    })
  }
  if (cleaningOptions.value.fillMissingNumeric) {
    const numericCols = Object.keys(data[0] || {}).filter(col => data.some(row => typeof row[col] === 'number'))
    for (const col of numericCols) {
      let fillVal = 0
      if (cleaningOptions.value.fillMethod === 'mean') {
        const vals = data.map(r => r[col]).filter(v => typeof v === 'number' && !isNaN(v))
        fillVal = vals.reduce((a,b) => a+b,0) / (vals.length || 1)
      } else if (cleaningOptions.value.fillMethod === 'median') {
        const vals = data.map(r => r[col]).filter(v => typeof v === 'number' && !isNaN(v)).sort((a,b)=>a-b)
        fillVal = vals[Math.floor(vals.length/2)] || 0
      }
      data = data.map(row => {
        if (row[col] === undefined || row[col] === null || (typeof row[col] !== 'number')) row[col] = fillVal
        return row
      })
    }
  }
  if (cleaningOptions.value.fillMissingText) {
    data = data.map(row => {
      Object.keys(row).forEach(k => {
        if (row[k] === undefined || row[k] === null || row[k] === '') row[k] = 'N/A'
      })
      return row
    })
  }
  if (cleaningOptions.value.dropRowsWithMissing) {
    data = data.filter(row => Object.values(row).every(v => v !== null && v !== '' && v !== undefined && (typeof v !== 'number' || !isNaN(v))))
  }
  if (cleaningOptions.value.removeOutliers) {
    const numericCols = Object.keys(data[0] || {}).filter(col => data.some(row => typeof row[col] === 'number'))
    for (const col of numericCols) {
      const values = data.map(r => r[col]).filter(v => typeof v === 'number')
      const mean = values.reduce((a,b)=>a+b,0)/values.length
      const std = Math.sqrt(values.map(v => Math.pow(v-mean,2)).reduce((a,b)=>a+b,0)/values.length)
      const threshold = 3 * std
      data = data.filter(row => Math.abs(row[col] - mean) <= threshold)
    }
  }
  if (cleaningOptions.value.standardizeDates) {
    data = data.map(row => {
      Object.keys(row).forEach(k => {
        if (k.toLowerCase().includes('date') && row[k]) {
          const d = new Date(row[k])
          if (!isNaN(d)) row[k] = d.toISOString().split('T')[0]
        }
      })
      return row
    })
  }
  if (cleaningOptions.value.removeSpecialChars) {
    data = data.map(row => {
      Object.keys(row).forEach(k => {
        if (typeof row[k] === 'string') row[k] = row[k].replace(/[^a-zA-Z0-9\s]/g, '')
      })
      return row
    })
  }
  if (cleaningOptions.value.changeCase && cleaningOptions.value.caseType !== 'none') {
    data = data.map(row => {
      Object.keys(row).forEach(k => {
        if (typeof row[k] === 'string') {
          if (cleaningOptions.value.caseType === 'upper') row[k] = row[k].toUpperCase()
          else if (cleaningOptions.value.caseType === 'lower') row[k] = row[k].toLowerCase()
          else if (cleaningOptions.value.caseType === 'title') row[k] = row[k].replace(/\b\w/g, l => l.toUpperCase())
        }
      })
      return row
    })
  }
  if (cleaningOptions.value.fillWithCustom && cleaningOptions.value.customFillValue) {
    data = data.map(row => {
      Object.keys(row).forEach(k => {
        if (row[k] === undefined || row[k] === null || row[k] === '') row[k] = cleaningOptions.value.customFillValue
      })
      return row
    })
  }
  if (cleaningOptions.value.removeColumnsAllMissing) {
    const colsToKeep = Object.keys(data[0] || {}).filter(col => data.some(row => row[col] !== null && row[col] !== '' && row[col] !== undefined))
    data = data.map(row => {
      const newRow = {}
      colsToKeep.forEach(c => newRow[c] = row[c])
      return newRow
    })
  }
  if (cleaningOptions.value.capOutliers) {
    const numericCols = Object.keys(data[0] || {}).filter(col => data.some(row => typeof row[col] === 'number'))
    for (const col of numericCols) {
      const values = data.map(r => r[col]).filter(v => typeof v === 'number')
      const mean = values.reduce((a,b)=>a+b,0)/values.length
      const std = Math.sqrt(values.map(v => Math.pow(v-mean,2)).reduce((a,b)=>a+b,0)/values.length)
      const upper = mean + 3*std
      const lower = mean - 3*std
      data = data.map(row => {
        if (row[col] > upper) row[col] = upper
        if (row[col] < lower) row[col] = lower
        return row
      })
    }
  }
  if (cleaningOptions.value.removeRowsSpecificColumnEmpty && cleaningOptions.value.specificColumn) {
    data = data.filter(row => row[cleaningOptions.value.specificColumn] !== null && row[cleaningOptions.value.specificColumn] !== '')
  }
  if (cleaningOptions.value.standardizeNumericRange) {
    const numericCols = Object.keys(data[0] || {}).filter(col => data.some(row => typeof row[col] === 'number'))
    for (const col of numericCols) {
      const values = data.map(r => r[col]).filter(v => typeof v === 'number')
      const min = Math.min(...values)
      const max = Math.max(...values)
      if (max !== min) {
        data = data.map(row => {
          if (typeof row[col] === 'number') row[col] = (row[col] - min) / (max - min)
          return row
        })
      }
    }
  }
  if (cleaningOptions.value.fillForward) {
    for (let i = 1; i < data.length; i++) {
      Object.keys(data[i]).forEach(k => {
        if (data[i][k] === undefined || data[i][k] === null || data[i][k] === '') {
          data[i][k] = data[i-1][k]
        }
      })
    }
  }
  if (cleaningOptions.value.fillBackward) {
    for (let i = data.length-2; i >= 0; i--) {
      Object.keys(data[i]).forEach(k => {
        if (data[i][k] === undefined || data[i][k] === null || data[i][k] === '') {
          data[i][k] = data[i+1][k]
        }
      })
    }
  }
  previewData.value = data
}

async function applyCleaningOnly() {
  if (!previewData.value.length) {
    alert('Please click "Preview Cleaned Data" first.')
    return
  }
  cleanedData.value = previewData.value
  cleaningStats.value = {
    totalRows: rawData.value.length,
    validRows: cleanedData.value.length,
    removedRows: rawData.value.length - cleanedData.value.length,
    fixedMissing: 0
  }
  calculateMetrics()
  saveSessionData()
  updateStatus('cleaning', true)
  alert(`Cleaning applied! ${cleanedData.value.length} rows remaining.`)
  await nextTick()
}

// ========== CALCULATIONS ==========
function calculateMetrics() {
  if (!cleanedData.value.length) return
  if (instrumentType.value === 'money-market') {
    const totalValue = cleanedData.value.reduce((s,row) => s + (parseFloat(row.Amount)||0), 0)
    const totalRate = cleanedData.value.reduce((s,row) => s + (parseFloat(row.Rate)||0), 0)
    const weightedSum = cleanedData.value.reduce((s,row) => s + ((parseFloat(row.Rate)||0) * (parseFloat(row.Amount)||0)), 0)
    const avgRateVal = totalRate / cleanedData.value.length
    calculations.value = {
      totalValue, instrumentCount: cleanedData.value.length,
      avgRate: avgRateVal.toFixed(2),
      weightedAvgRate: totalValue > 0 ? (weightedSum / totalValue).toFixed(2) : 0,
      totalInterest: (totalValue * avgRateVal / 100).toFixed(2),
      interestEarned: (totalValue * avgRateVal / 100 * 90 / 365).toFixed(2),
      annualYield: ((Math.pow(1 + avgRateVal/100, 365/90) - 1) * 100).toFixed(2),
      effectiveAnnualRate: ((Math.pow(1 + avgRateVal/100, 1) - 1) * 100).toFixed(2),
      avgDaysToMaturity: 90,
      totalPrincipal: totalValue
    }
  } else if (instrumentType.value === 'bonds') {
    const totalValue = cleanedData.value.reduce((s,row) => s + (parseFloat(row.FaceValue)||0), 0)
    const totalRate = cleanedData.value.reduce((s,row) => s + (parseFloat(row.CouponRate)||0), 0)
    const weightedSum = cleanedData.value.reduce((s,row) => s + ((parseFloat(row.CouponRate)||0) * (parseFloat(row.FaceValue)||0)), 0)
    const totalYield = cleanedData.value.reduce((s,row) => s + (parseFloat(row.Yield)||0), 0)
    const avgCoupon = totalRate / cleanedData.value.length
    const avgYieldVal = totalYield / cleanedData.value.length
    calculations.value = {
      totalValue, instrumentCount: cleanedData.value.length,
      avgCouponRate: avgCoupon.toFixed(2),
      weightedAvgCoupon: totalValue > 0 ? (weightedSum / totalValue).toFixed(2) : 0,
      totalAnnualIncome: (totalValue * avgCoupon / 100).toFixed(2),
      avgYTM: avgYieldVal.toFixed(2),
      duration: (10 * 0.7).toFixed(2)
    }
  } else {
    const totalValue = cleanedData.value.reduce((s,row) => s + (parseFloat(row.FaceValue)||0), 0)
    const totalRate = cleanedData.value.reduce((s,row) => s + (parseFloat(row.DiscountRate)||0), 0)
    const weightedSum = cleanedData.value.reduce((s,row) => s + ((parseFloat(row.DiscountRate)||0) * (parseFloat(row.FaceValue)||0)), 0)
    const avgDiscount = totalRate / cleanedData.value.length
    const discountAmount = totalValue * (avgDiscount/100) * 91/360
    const price = totalValue - discountAmount
    calculations.value = {
      totalValue, instrumentCount: cleanedData.value.length,
      avgDiscountRate: avgDiscount.toFixed(2),
      weightedAvgDiscount: totalValue > 0 ? (weightedSum / totalValue).toFixed(2) : 0,
      totalDiscount: discountAmount.toFixed(2),
      effectiveYield: ((Math.pow(1 + discountAmount/price, 365/91) - 1) * 100).toFixed(2),
      bondEquivalentYield: ((discountAmount/price) * (365/91) * 100).toFixed(2),
      discountYield: ((discountAmount/totalValue) * (360/91) * 100).toFixed(2),
      moneyMarketYield: ((discountAmount/price) * (360/91) * 100).toFixed(2),
      pricePer100: (100 * (1 - (avgDiscount/100)*(91/360))).toFixed(2),
      totalPurchasePrice: price.toFixed(2),
      avgInvestment: (price / cleanedData.value.length).toFixed(2),
      holdingPeriodYield: ((discountAmount/price)*100).toFixed(2),
      annualizedYield: ((discountAmount/price)*(365/91)*100).toFixed(2),
      avgDaysToMaturity: 91
    }
  }
  saveSessionData()
  updateSessionCompletion()
}

// ========== REPORT LOGIC (ENHANCED with cover page, A4, background, logo, footer, and preview) ==========
const selectedInstruments = ref({ moneyMarket: true, bonds: true, tbills: true })
function selectAllInstruments() { selectedInstruments.value = { moneyMarket: true, bonds: true, tbills: true } }
function deselectAllInstruments() { selectedInstruments.value = { moneyMarket: false, bonds: false, tbills: false } }

function getInstrumentData(instrumentId) {
  if (!activeSession.value) return null
  if (activeSession.value.instrumentData && activeSession.value.instrumentData[instrumentId]) {
    return activeSession.value.instrumentData[instrumentId]
  }
  const key = `${instrumentId}_session_${activeSession.value.id}`
  const savedCalc = localStorage.getItem(`${key}_calc`)
  if (savedCalc) {
    const data = JSON.parse(savedCalc)
    if (!activeSession.value.instrumentData) activeSession.value.instrumentData = {}
    activeSession.value.instrumentData[instrumentId] = data
    return data
  }
  return null
}

const reportPreviewData = computed(() => {
  const instrumentsData = []
  if (selectedInstruments.value.moneyMarket) {
    const data = getInstrumentData('money-market')
    if (data) instrumentsData.push({ name: 'Money Market', calculations: data })
  }
  if (selectedInstruments.value.bonds) {
    const data = getInstrumentData('bonds')
    if (data) instrumentsData.push({ name: 'Bonds', calculations: data })
  }
  if (selectedInstruments.value.tbills) {
    const data = getInstrumentData('tbills')
    if (data) instrumentsData.push({ name: 'T-Bills', calculations: data })
  }
  return {
    session: activeSession.value?.name || 'No session',
    date: new Date().toLocaleString(),
    instruments: instrumentsData
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
    if (key.includes('Value') || key.includes('Price') || key.includes('Interest') || key.includes('Income') || key.includes('Discount') || key.includes('Principal') || key.includes('Investment'))
      return `$${value.toLocaleString()}`
    if (key.includes('Rate') || key.includes('Yield') || key.includes('Coupon') || key.includes('Discount'))
      return `${value}%`
    return value.toLocaleString()
  }
  return value
}

// Report preview dialog state
const reportPreviewDialog = ref(false)
const reportPreviewHtml = ref('')

// Function to generate the full HTML report (used for both preview and download)
async function generateReportHtml() {
  const report = reportPreviewData.value
  if (report.instruments.length === 0) {
    alert('No data available for the selected instruments.')
    return null
  }
  let chartImageBase64 = ''
  if (yieldCurveChart.value && chartData.value.datasets.length) {
    try {
      chartImageBase64 = yieldCurveChart.value.toDataURL('image/png')
    } catch (err) { console.warn(err) }
  }
  const backgroundImageUrl = '/background%20report%201.webp'   // your background image in public folder
  const logoHtml = `<img src="/DuraCapital%20logo.png" alt="DuraCapital Logo" style="height:70px;">` // adjust logo filename as needed

  let totalPortfolioValue = 0, totalInstrumentCount = 0
  for (const inst of report.instruments) {
    totalPortfolioValue += parseFloat(inst.calculations.totalValue) || 0
    totalInstrumentCount += parseInt(inst.calculations.instrumentCount) || 0
  }

  let html = `<!DOCTYPE html>
  <html>
  <head>
    <meta charset="UTF-8">
    <title>Portfolio Report - ${report.session}</title>
    <style>
      @page {
        size: A4;
        margin: 1.5cm;
      }
      @media print {
        body {
          margin: 0;
          padding: 0;
        }
        .cover-page {
          page-break-after: always;
          height: 100vh;
        }
        .no-break {
          page-break-inside: avoid;
        }
      }
      body {
        font-family: 'Arial', sans-serif;
        margin: 0;
        padding: 0;
        line-height: 1.5;
        color: #333;
        background: white;
      }
      .cover-page {
        position: relative;
        height: 100vh;
        width: 100%;
        background: url('${backgroundImageUrl}') no-repeat center center;
        background-size: cover;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        text-align: center;
        color: white;
      }
      .cover-overlay {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0,0,0,0.5);
        z-index: 1;
      }
      .cover-content {
        position: relative;
        z-index: 2;
        padding: 20px;
      }
      .session-name {
        font-size: 56px;
        font-weight: 700;
        letter-spacing: 2px;
        text-shadow: 2px 2px 8px rgba(0,0,0,0.7);
        margin: 30px 0;
        font-family: 'Georgia', serif;
      }
      .logo-cover {
        margin-bottom: 30px;
      }
      .report-content {
        padding: 20px 30px;
        max-width: 1000px;
        margin: 0 auto;
      }
      h1 {
        color: #0B2044;
        font-size: 28px;
        border-bottom: 2px solid #0B2044;
        padding-bottom: 10px;
      }
      h2 {
        color: #1E88E5;
        margin-top: 30px;
        font-size: 22px;
      }
      h3 {
        color: #0B2044;
        margin-top: 20px;
        font-size: 18px;
      }
      table {
        border-collapse: collapse;
        width: 100%;
        margin-bottom: 20px;
      }
      th, td {
        border: 1px solid #ddd;
        padding: 8px;
        text-align: left;
      }
      th {
        background: #0B2044;
        color: white;
      }
      .summary-text {
        background: #f8f9ff;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 20px;
      }
      .metric-highlight {
        font-weight: bold;
        color: #0B2044;
      }
      .formula {
        font-family: monospace;
        background: #f0f0f0;
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 1.1em;
      }
      .footer {
        margin-top: 40px;
        font-size: 12px;
        color: #666;
        text-align: center;
        border-top: 1px solid #eee;
        padding-top: 20px;
      }
    </style>
  </head>
  <body>
    <div class="cover-page">
      <div class="cover-overlay"></div>
      <div class="cover-content">
        <div class="logo-cover">${logoHtml}</div>
        <div class="session-name">${report.session}</div>
      </div>
    </div>
    <div class="report-content">
      <div class="summary-text">
        <h3>Executive Summary</h3>
        <p>This report provides a comprehensive valuation and performance summary of the selected fixed income instruments as of the report date. The analysis includes money market instruments, corporate bonds, and treasury bills held within the portfolio. The valuations are performed in accordance with IFRS 13 fair value measurement principles.</p>
      </div>
      <div class="summary-text">
        <h3>Portfolio Summary</h3>
        <p>The portfolio comprises <strong>${report.instruments.length}</strong> asset class(es) with a total of <strong>${totalInstrumentCount}</strong> individual instruments. The combined fair value of the portfolio is <strong>$${totalPortfolioValue.toLocaleString()}</strong>.</p>
        <p>Key observations:</p>
        <ul>
          <li>Money market instruments provide short-term liquidity with competitive yields.</li>
          <li>Corporate bonds offer higher coupon rates but carry moderate credit risk.</li>
          <li>Treasury bills are low-risk government securities with shorter maturities.</li>
        </ul>
      </div>`

  if (chartImageBase64) {
    html += `<div class="summary-text">
      <h3>Yield Curve Analysis (FRED)</h3>
      <img src="${chartImageBase64}" alt="Yield Curve Chart" style="max-width:100%; border:1px solid #ccc;" />
      <p>Figure 1: Latest yield curve from Federal Reserve Economic Data (FRED). This curve is used as a benchmark for discounting future cash flows.</p>
    </div>`
  }

  for (const inst of report.instruments) {
    const instData = inst.calculations
    html += `<h2>${inst.name}</h2><div class="summary-text">`
    if (inst.name === 'Money Market') {
      html += `<p><strong>Total Value:</strong> $${(instData.totalValue || 0).toLocaleString()}</p>
              <p><strong>Number of Instruments:</strong> ${instData.instrumentCount || 0}</p>
              <p><strong>Average Interest Rate:</strong> ${instData.avgRate || 0}%</p>
              <p><strong>Weighted Average Rate:</strong> ${instData.weightedAvgRate || 0}%</p>
              <p><strong>Total Interest Earned (Annualized):</strong> $${(instData.totalInterest || 0).toLocaleString()}</p>
              <p><strong>Average Days to Maturity:</strong> ${instData.avgDaysToMaturity || 0} days</p>`
    } else if (inst.name === 'Bonds') {
      html += `<p><strong>Total Value:</strong> $${(instData.totalValue || 0).toLocaleString()}</p>
              <p><strong>Number of Instruments:</strong> ${instData.instrumentCount || 0}</p>
              <p><strong>Average Coupon Rate:</strong> ${instData.avgCouponRate || 0}%</p>
              <p><strong>Weighted Average Coupon:</strong> ${instData.weightedAvgCoupon || 0}%</p>
              <p><strong>Total Annual Income:</strong> $${(instData.totalAnnualIncome || 0).toLocaleString()}</p>
              <p><strong>Average Yield to Maturity:</strong> ${instData.avgYTM || 0}%</p>
              <p><strong>Duration (years):</strong> ${instData.duration || 0}</p>`
    } else {
      html += `<p><strong>Total Value:</strong> $${(instData.totalValue || 0).toLocaleString()}</p>
              <p><strong>Number of Instruments:</strong> ${instData.instrumentCount || 0}</p>
              <p><strong>Average Discount Rate:</strong> ${instData.avgDiscountRate || 0}%</p>
              <p><strong>Weighted Average Discount:</strong> ${instData.weightedAvgDiscount || 0}%</p>
              <p><strong>Total Discount:</strong> $${(instData.totalDiscount || 0).toLocaleString()}</p>
              <p><strong>Effective Yield:</strong> ${instData.effectiveYield || 0}%</p>
              <p><strong>Bond Equivalent Yield:</strong> ${instData.bondEquivalentYield || 0}%</p>
              <p><strong>Average Days to Maturity:</strong> ${instData.avgDaysToMaturity || 0} days</p>`
    }
    html += `</div><h3>Detailed Metrics</h3></table><thead><tr><th>Metric</th><th>Value</th></tr></thead><tbody>`
    for (const [key, val] of Object.entries(instData)) {
      if (key === 'completed' || key === 'timestamp') continue
      html += `<tr><td>${formatMetricName(key)}</td><td class="metric-highlight">${formatMetricValue(key, val)}</td></tr>`
    }
    html += `</tbody></table>`
  }

  html += `<div class="summary-text">
    <h3>Methodology</h3>
    <p>The valuation of fixed income instruments is based on the discounted cash flow (DCF) method using the yield curve derived from FRED data.</p>
    <p class="formula">For money market instruments: Fair value = <sup>F</sup>&frasl;<sub>1 + r·t/365</sub></p>
    <p class="formula">For bonds: Fair value = Σ<sub>t=1</sub><sup>n</sup> <sup>C</sup>&frasl;<sub>(1+y)<sup>t</sup></sub> + <sup>FV</sup>&frasl;<sub>(1+y)<sup>n</sup></sub></p>
    <p>All calculations assume a 365‑day count convention and simple interest for money market instruments.</p>
    <p><strong>Sources:</strong> Federal Reserve Economic Data (FRED), Damodaran Country Risk Premiums, Bloomberg OIS SOFR rates.</p>
  </div>
  <div class="footer">
    <p>Date Generated: ${report.date}</p>
    <p>Generated by: DuraCapital Platform</p>
  </div>
  </div></body></html>`
  return html
}

// Preview report: generate HTML and show in dialog
async function previewReport() {
  const html = await generateReportHtml()
  if (html) {
    reportPreviewHtml.value = html
    reportPreviewDialog.value = true
  }
}

// Download from preview dialog
async function downloadFromPreview(format) {
  if (!reportPreviewHtml.value) return
  const filename = `combined_report_${Date.now()}`
  if (format === 'html') downloadBlob(reportPreviewHtml.value, `${filename}.html`, 'text/html')
  else if (format === 'pdf') { const win = window.open(); win.document.write(reportPreviewHtml.value); win.print() }
  else if (format === 'word') downloadBlob(reportPreviewHtml.value, `${filename}.doc`, 'application/msword')
}

async function downloadCombinedReport(format) {
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
  } else if (format === 'html') {
    downloadBlob(html, `${filename}.html`, 'text/html')
  } else if (format === 'pdf') {
    const win = window.open()
    win.document.write(html)
    win.print()
  } else if (format === 'word') {
    downloadBlob(html, `${filename}.doc`, 'application/msword')
  } else if (format === 'excel') {
    const report = reportPreviewData.value
    let csvRows = [['Instrument', 'Metric', 'Value']]
    for (const inst of report.instruments) {
      for (const [key, val] of Object.entries(inst.calculations)) {
        if (key === 'completed' || key === 'timestamp') continue
        csvRows.push([inst.name, formatMetricName(key), formatMetricValue(key, val)])
      }
    }
    const csv = csvRows.map(row => row.join(',')).join('\n')
    downloadBlob(csv, `${filename}.xls`, 'application/vnd.ms-excel')
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

// Excel viewer functions
const showExcelDialog = ref(false)
const excelData = ref([])
const excelColumns = ref([])
const excelDialogTitle = ref('')
function openExcelReview(data, title) {
  if (!data || !data.length) { if (cleanedData.value.length) data = cleanedData.value; else if (rawData.value.length) data = rawData.value; else { alert('No data'); return } }
  excelData.value = data; excelColumns.value = Object.keys(data[0] || {}); excelDialogTitle.value = title || 'Data Review'; showExcelDialog.value = true
}
function closeExcelDialog() { showExcelDialog.value = false; excelData.value = [] }
function exportToCSV() {
  if (!excelData.value.length) return
  const headers = excelColumns.value
  const rows = excelData.value.map(row => headers.map(h => `"${String(row[h] || '').replace(/"/g, '""')}"`).join(','))
  const csv = [headers.join(','), ...rows].join('\n')
  downloadBlob(csv, `${excelDialogTitle.value.replace(/ /g, '_')}_${Date.now()}.csv`, 'text/csv')
}
function exportToJSON() {
  downloadBlob(JSON.stringify(excelData.value, null, 2), `${excelDialogTitle.value.replace(/ /g, '_')}_${Date.now()}.json`, 'application/json')
}
function saveToSession() { saveSessionData(); alert('Data saved to session!') }

// ========== FRED API INTEGRATION ==========
const fredLoading = ref(false)
const fredError = ref('')
const selectedSeries = ref('')
const yieldCurveChart = ref(null)
let chartInstance = null
const chartData = ref({ labels: [], datasets: [] })
const currentMarketRate = ref(null)

const seriesByInstrument = {
  'money-market': {
    'DTB3': '3-Month Treasury Bill',
    'DTB6': '6-Month Treasury Bill',
    'DGS1': '1-Year Treasury Rate',
    'DGS2': '2-Year Treasury Rate'
  },
  'bonds': {
    'DGS2': '2-Year Treasury Rate',
    'DGS5': '5-Year Treasury Rate',
    'DGS10': '10-Year Treasury Rate',
    'DGS30': '30-Year Treasury Rate',
    'T10Y2Y': '10Y-2Y Spread'
  },
  'tbills': {
    'DTB3': '3-Month Treasury Bill',
    'DTB6': '6-Month Treasury Bill',
    'DGS1': '1-Year Treasury Rate'
  }
}

const availableSeries = computed(() => {
  return seriesByInstrument[instrumentType.value] || seriesByInstrument['tbills']
})
const selectedSeriesLabel = computed(() => availableSeries.value[selectedSeries.value] || selectedSeries.value)
const portfolioAvgRate = computed(() => {
  if (instrumentType.value === 'money-market') return calculations.value.avgRate || 0
  if (instrumentType.value === 'bonds') return calculations.value.avgCouponRate || 0
  return calculations.value.avgDiscountRate || 0
})

async function fetchFredData() {
  if (!selectedSeries.value) {
    const firstSeries = Object.keys(availableSeries.value)[0]
    if (firstSeries) selectedSeries.value = firstSeries
    else return
  }
  fredLoading.value = true
  fredError.value = ''
  const BACKEND_URL = 'http://localhost:5000'
  try {
    const response = await axios.get(`${BACKEND_URL}/api/fred/series/${selectedSeries.value}`, {
      params: { limit: 365, sort_order: 'desc' }
    })
    if (!response.data.success) throw new Error(response.data.error || 'Failed to fetch FRED data')
    const observations = response.data.data || []
    if (observations.length === 0) throw new Error('No data returned for this series')
    const reversed = [...observations].reverse()
    const labels = reversed.map(obs => obs.date)
    const values = reversed.map(obs => obs.value)
    if (observations.length > 0) currentMarketRate.value = observations[0].value
    chartData.value = { labels, datasets: [{ label: selectedSeriesLabel.value, data: values, borderColor: '#0B2044', backgroundColor: 'rgba(11,32,68,0.1)', tension: 0.1, fill: true }] }
    await nextTick()
    renderChart()
  } catch (err) {
    console.error(err)
    fredError.value = err.message || 'Failed to load market data. Check your network or try again later.'
  } finally {
    fredLoading.value = false
  }
}

function renderChart() {
  if (!yieldCurveChart.value) return
  if (chartInstance) chartInstance.destroy()
  const ctx = yieldCurveChart.value.getContext('2d')
  chartInstance = new Chart(ctx, {
    type: 'line',
    data: chartData.value,
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: { tooltip: { callbacks: { label: (ctx) => `${ctx.dataset.label}: ${ctx.raw}%` } }, legend: { position: 'top' } },
      scales: { y: { title: { display: true, text: 'Percent (%)' }, ticks: { callback: (val) => val + '%' } }, x: { title: { display: true, text: 'Date' }, ticks: { maxRotation: 45, autoSkip: true } } }
    }
  })
}

watch(() => instrumentType.value, () => {
  const firstSeries = Object.keys(availableSeries.value)[0]
  if (firstSeries) {
    selectedSeries.value = firstSeries
    if (activeTab.value === 'visualizations') fetchFredData()
  }
}, { immediate: true })
watch(() => activeTab.value, (newTab) => {
  if (newTab === 'visualizations' && hasCleanedData.value) fetchFredData()
})
watch(() => chartData.value.datasets.length, async (newLen) => {
  if (newLen > 0 && activeTab.value === 'visualizations') { await nextTick(); renderChart() }
})

// ========== Force refresh on instrument or session change ==========
let lastInstrument = ''
let lastSessionId = ''
function checkAndReset() {
  const savedSession = localStorage.getItem('active_session')
  const currentSessionId = savedSession ? JSON.parse(savedSession).id : null
  const currentInstrument = instrumentType.value
  if (currentInstrument !== lastInstrument || currentSessionId !== lastSessionId) {
    lastInstrument = currentInstrument
    lastSessionId = currentSessionId
    if (savedSession) activeSession.value = JSON.parse(savedSession)
    else activeSession.value = null
    const loaded = loadSavedData()
    if (!loaded) {
      refreshPage()
      activeTab.value = 'upload'
    } else {
      const savedTab = localStorage.getItem(`instrument_${instrumentType.value}_last_tab`)
      if (savedTab && steps.some(s => s.tab === savedTab)) activeTab.value = savedTab
      else activeTab.value = 'upload'
    }
  }
}
onMounted(() => { checkAndReset(); window.addEventListener('storage', () => checkAndReset()) })
onBeforeUnmount(() => { window.removeEventListener('storage', () => checkAndReset()) })
watch(() => route.params.type, () => checkAndReset(), { immediate: true })
</script>

<style scoped>
/* ========== All original styles (unchanged) ========== */
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
.btn-review-excel { background: #4CAF50; color: white; border: none; padding: 6px 12px; border-radius: 6px; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; font-size: 12px; margin-left: 10px; transition: all 0.2s; }
.btn-review-excel:hover:not(:disabled) { background: #45a049; transform: translateY(-1px); }
.btn-review-excel:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-mapping { background: #FF9800; color: white; border: none; padding: 6px 12px; border-radius: 6px; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; font-size: 12px; margin-left: 10px; transition: all 0.2s; }
.btn-mapping:hover:not(:disabled) { background: #F57C00; transform: translateY(-1px); }
.btn-mapping:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-review-excel-small { background: #2196F3; color: white; border: none; padding: 4px 10px; border-radius: 6px; cursor: pointer; display: inline-flex; align-items: center; gap: 4px; font-size: 11px; transition: all 0.2s; }
.btn-review-excel-small:hover { background: #0b7dda; }
.excel-dialog-title { background: #0B2044; color: white; padding: 16px 24px; }
.dialog-title-content { display: flex; align-items: center; gap: 12px; }
.btn-close-dialog { background: transparent; border: none; color: white; cursor: pointer; padding: 8px; border-radius: 50%; transition: all 0.2s; }
.btn-close-dialog:hover { background: rgba(255,255,255,0.1); }
.excel-dialog-content { padding: 0; height: calc(100vh - 140px); }
.excel-full-view { height: 100%; display: flex; flex-direction: column; }
.excel-toolbar-full { display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; background: #f5f5f5; border-bottom: 1px solid #e0e0e0; flex-wrap: wrap; gap: 10px; }
.excel-info { font-size: 13px; color: #666; }
.excel-export-buttons { display: flex; gap: 10px; }
.btn-excel-export { background: white; border: 1px solid #ddd; padding: 6px 12px; border-radius: 6px; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; font-size: 12px; transition: all 0.2s; }
.btn-excel-export:hover { background: #0B2044; color: white; border-color: #0B2044; }
.excel-full-table-wrapper { flex: 1; overflow: auto; }
.excel-full-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.excel-full-table th, .excel-full-table td { padding: 8px 12px; border: 1px solid #e0e0e0; text-align: left; }
.excel-full-table th { background: #f5f5f5; font-weight: 600; position: sticky; top: 0; z-index: 10; }
.sticky-col { position: sticky; left: 0; background: #f5f5f5; font-weight: 600; }
.sticky-header { position: sticky; top: 0; background: #f5f5f5; z-index: 10; }
.excel-preview-section, .preview-toolbar { margin-top: 20px; }
.preview-toolbar { display: flex; justify-content: space-between; align-items: center; padding: 10px 15px; background: #f5f5f5; border-radius: 8px; flex-wrap: wrap; gap: 10px; }
.preview-info { font-size: 12px; color: #666; }
.preview-controls { display: flex; align-items: center; gap: 10px; }
.preview-btn { background: white; border: 1px solid #ddd; padding: 4px 12px; border-radius: 6px; cursor: pointer; font-size: 12px; }
.preview-btn:hover:not(:disabled) { background: #0B2044; color: white; }
.preview-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.row-number { background: #f8f9ff; font-weight: 500; color: #0B2044; width: 50px; text-align: center; }
.mapping-grid { display: flex; flex-direction: column; gap: 15px; margin: 20px 0; }
.mapping-row { display: flex; align-items: center; gap: 15px; }
.required-label { width: 140px; font-weight: 600; color: #0B2044; }
.mapping-select { flex: 1; padding: 10px; border: 1px solid #ddd; border-radius: 8px; font-size: 14px; }
.mapping-hint { margin-top: 15px; padding: 10px; background: #f8f9ff; border-radius: 8px; display: flex; align-items: center; gap: 8px; color: #666; }
.required-columns { margin: 20px 0; }
.columns-list { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 10px; }
.column-badge { background: #e8ecf1; padding: 6px 12px; border-radius: 20px; font-size: 12px; display: inline-flex; align-items: center; gap: 6px; }
.missing-column { background: #FFEBEE; color: #c62828; }
.warning-message { margin-top: 10px; padding: 8px 12px; background: #FFF3E0; border-radius: 8px; display: flex; align-items: center; gap: 8px; font-size: 12px; color: #E65100; }
.btn-warning { background: #FF9800; color: white; border: none; padding: 12px 20px; border-radius: 8px; font-size: 14px; font-weight: 600; cursor: pointer; }
.cleaning-options-panel { background: #f8f9ff; padding: 20px; border-radius: 12px; margin-bottom: 20px; }
.filter-scroll-container { max-height: 200px; overflow-y: auto; border: 1px solid #e0e0e0; border-radius: 8px; background: #fafafa; margin: 12px 0; padding: 8px 4px; scrollbar-width: thin; }
.options-list { display: flex; flex-direction: column; gap: 8px; }
.option-checkbox { display: flex; align-items: center; gap: 8px; font-size: 14px; padding: 4px 8px; border-radius: 4px; transition: background 0.1s; }
.option-checkbox:hover { background: #f0f0f0; }
.option-checkbox select, .option-checkbox input[type="text"] { margin-left: 4px; padding: 2px 6px; font-size: 13px; border: 1px solid #ccc; border-radius: 4px; }
.filter-scroll-container { background: linear-gradient(white 30%, rgba(255,255,255,0)), linear-gradient(rgba(255,255,255,0), white 70%) 0 100%, radial-gradient(farthest-side at 50% 0, rgba(0,0,0,0.1), rgba(0,0,0,0)), radial-gradient(farthest-side at 50% 100%, rgba(0,0,0,0.1), rgba(0,0,0,0)) 0 100%; background-repeat: no-repeat; background-size: 100% 20px, 100% 20px, 100% 8px, 100% 8px; background-attachment: local, local, scroll, scroll; }
.cleaning-buttons { display: flex; gap: 12px; margin-top: 15px; }
.summary-cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 30px; }
.summary-card { background: linear-gradient(135deg, #1B5E20, #4CAF50); padding: 20px; border-radius: 16px; color: white; text-align: center; display: flex; flex-direction: column; align-items: center; justify-content: center; }
.summary-card.total { background: linear-gradient(135deg, #1B5E20, #4CAF50); }
.summary-card.rate { background: linear-gradient(135deg, #0D47A1, #2196F3); }
.summary-card.count { background: linear-gradient(135deg, #E65100, #FF9800); }
.card-label { font-size: 14px; opacity: 0.9; margin-bottom: 8px; }
.card-value { font-size: 28px; font-weight: 700; }
.calculations-section { margin-top: 10px; }
.calculations-section h3 { color: #0B2044; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 2px solid #0B2044; }
.calculations-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; margin-bottom: 30px; }
.calculation-card { padding: 20px; background: linear-gradient(135deg, #f8f9ff, #fff); border-radius: 12px; text-align: center; border: 1px solid rgba(11,32,68,0.1); transition: transform 0.2s; }
.calculation-card:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
.calc-name { font-size: 14px; color: #666; margin-bottom: 10px; }
.calc-value { font-size: 24px; font-weight: 700; color: #0B2044; margin-bottom: 5px; }
.calc-unit { font-size: 12px; color: #999; }
.visualization-placeholder { text-align: center; padding: 60px; background: #f8f9ff; border-radius: 12px; }
.visualization-placeholder h3 { color: #0B2044; margin: 20px 0 10px; }
.visualization-placeholder p { color: #666; margin-bottom: 20px; }
.placeholder-note { display: inline-flex; align-items: center; gap: 8px; padding: 8px 16px; background: #e3f2fd; border-radius: 20px; font-size: 12px; color: #0B2044; }
.summary-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; margin-bottom: 30px; }
.summary-section { padding: 20px; background: #f8f9ff; border-radius: 12px; }
.summary-section h3 { color: #0B2044; margin-bottom: 15px; }
.summary-section p { margin: 8px 0; color: #555; }
.summary-progress { margin: 20px 0; padding: 15px; background: #f8f9ff; border-radius: 12px; }
.progress-bar { height: 8px; background: #e0e0e0; border-radius: 4px; overflow: hidden; margin-bottom: 10px; }
.progress-fill { height: 100%; background: linear-gradient(90deg, #4CAF50, #2E7D32); border-radius: 4px; }
.progress-text { font-size: 12px; color: #4CAF50; font-weight: 500; margin: 0; }
.report-options { padding: 20px; }
.instrument-selection { background: #f8f9ff; padding: 20px; border-radius: 12px; margin-bottom: 20px; }
.selection-cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin: 20px 0; }
.selection-card { display: flex; flex-direction: column; align-items: center; gap: 12px; padding: 20px 16px; background: white; border-radius: 12px; cursor: pointer; transition: all 0.2s; border: 2px solid #e0e0e0; position: relative; text-align: center; }
.selection-card:hover { transform: translateY(-2px); box-shadow: 0 4px 8px rgba(0,0,0,0.1); border-color: #0B2044; }
.selection-card.active { border-color: #0B2044; background: #f8f9ff; }
.check-indicator { position: absolute; top: 12px; right: 12px; }
.selection-actions { display: flex; gap: 10px; justify-content: center; margin-top: 10px; }
.report-preview-full { background: #f8f9ff; padding: 20px; border-radius: 12px; margin-bottom: 20px; max-height: 500px; overflow-y: auto; }
.preview-content { margin-top: 15px; }
.preview-header { padding: 10px; background: white; border-radius: 8px; margin-bottom: 15px; }
.preview-instrument-card { background: white; border-radius: 10px; padding: 15px; margin-bottom: 15px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
.preview-instrument-card h4 { color: #0B2044; margin-bottom: 10px; }
.report-table-wrapper { overflow-x: auto; }
.report-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.report-table th, .report-table td { border: 1px solid #ddd; padding: 8px; text-align: left; }
.report-table th { background: #f5f5f5; font-weight: 600; }
.report-value { font-weight: 500; }
.preview-empty { text-align: center; padding: 40px; color: #999; }
.report-actions { display: flex; flex-wrap: wrap; gap: 10px; justify-content: center; margin-bottom: 20px; }
.btn-preview { background: #673AB7; color: white; padding: 8px 16px; border-radius: 6px; border: none; cursor: pointer; display: inline-flex; align-items: center; gap: 5px; }
.btn-json, .btn-csv, .btn-html, .btn-pdf, .btn-word, .btn-excel, .btn-save { padding: 8px 16px; border-radius: 6px; border: none; cursor: pointer; display: inline-flex; align-items: center; gap: 5px; color: white; }
.btn-json { background: #607d8b; }
.btn-csv { background: #4caf50; }
.btn-html { background: #ff9800; }
.btn-pdf { background: #f44336; }
.btn-word { background: #2196f3; }
.btn-excel { background: #8bc34a; }
.btn-save { background: #9c27b0; }
.table-wrapper { overflow-x: auto; margin: 15px 0; }
.data-table { width: 100%; border-collapse: collapse; }
.data-table th, .data-table td { padding: 10px; text-align: left; border-bottom: 1px solid #e0e0e0; }
.data-table th { background: #f5f5f5; font-weight: 600; color: #0B2044; }
.empty-state { text-align: center; padding: 60px; color: #999; }
.empty-state p { margin: 20px 0; }
.navigation-buttons { display: flex; gap: 15px; justify-content: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e0e0e0; }
.btn-primary { background: linear-gradient(135deg, #0B2044, #1E88E5); color: white; border: none; padding: 12px 28px; border-radius: 10px; font-size: 14px; font-weight: 600; cursor: pointer; transition: all 0.3s; }
.btn-primary:hover:not(:disabled) { transform: translateY(-2px); box-shadow: 0 6px 15px rgba(11,32,68,0.3); }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-secondary { background: white; color: #0B2044; border: 2px solid #0B2044; padding: 12px 28px; border-radius: 10px; font-size: 14px; font-weight: 600; cursor: pointer; transition: all 0.3s; }
.btn-secondary:hover { background: #0B2044; color: white; transform: translateY(-2px); }
.btn-success { background: linear-gradient(135deg, #4CAF50, #2E7D32); color: white; border: none; padding: 12px 28px; border-radius: 10px; font-size: 14px; font-weight: 600; cursor: pointer; transition: all 0.3s; }
.btn-success:hover { transform: translateY(-2px); box-shadow: 0 6px 15px rgba(76, 175, 80, 0.3); }
.invalid-row { background-color: #ffebee !important; }
.invalid-cell { background-color: #ffcdd2 !important; color: #c62828 !important; font-weight: 500; }
.fixed-value { background-color: #c8e6c9 !important; position: relative; }
.fixed-badge { display: inline-block; margin-left: 5px; color: #4caf50; font-weight: bold; cursor: help; }
.legend { margin-bottom: 15px; padding: 10px; background: #f5f5f5; border-radius: 8px; display: flex; gap: 20px; }
.legend-badge { padding: 4px 12px; border-radius: 4px; font-size: 12px; }
.invalid-row-badge { background-color: #ffebee; color: #c62828; border: 1px solid #ef9a9a; }
.invalid-cell-badge { background-color: #ffcdd2; color: #c62828; border: 1px solid #ef9a9a; }
.success-text { color: #4CAF50; font-weight: 600; }
.preview-note { font-size: 12px; color: #666; margin-top: 10px; text-align: center; }
.highlight-box { background: #e8f5e9; padding: 12px; border-radius: 8px; margin-bottom: 20px; }

/* FRED chart comparison card & chart controls */
.comparison-card {
  background: linear-gradient(135deg, #f8f9ff, #eef2ff);
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 20px;
  display: flex;
  justify-content: space-around;
  align-items: center;
  flex-wrap: wrap;
  gap: 15px;
}
.comparison-item {
  text-align: center;
}
.comparison-label {
  font-size: 13px;
  color: #666;
  display: block;
}
.comparison-value {
  font-size: 24px;
  font-weight: 700;
}
.comparison-value.portfolio {
  color: #0B2044;
}
.comparison-value.market {
  color: #1E88E5;
}
.comparison-difference {
  font-size: 16px;
  font-weight: 600;
  padding: 4px 12px;
  border-radius: 20px;
}
.comparison-difference.positive {
  background: #e8f5e9;
  color: #2e7d32;
}
.comparison-difference.negative {
  background: #ffebee;
  color: #c62828;
}
.chart-controls {
  display: flex;
  gap: 15px;
  margin-bottom: 20px;
  align-items: center;
}
.series-select {
  padding: 8px 12px;
  border-radius: 8px;
  border: 1px solid #ccc;
  font-size: 14px;
  min-width: 180px;
}
.loading-container, .error-container {
  text-align: center;
  padding: 40px;
}
.spin {
  animation: spin 1s linear infinite;
}
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
.chart-container {
  margin-top: 20px;
}
.chart-footer {
  margin-top: 10px;
  text-align: center;
  color: #666;
  font-size: 12px;
}
.report-preview-content {
  padding: 0;
}
.report-preview-content iframe {
  width: 100%;
  height: 80vh;
  border: none;
}
</style>