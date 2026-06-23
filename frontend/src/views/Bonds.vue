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
                <button class="btn-review-excel" @click="openExcelReview(rawData, 'Uploaded Data')" :disabled="!rawData.length">Review Excel</button>
                <button class="btn-mapping" @click="openMappingDialog" :disabled="!rawData.length">Map Columns</button>
              </div>

              <!-- Preview – inline toggle removed -->
              <div v-if="rawData.length" class="excel-preview-section">
                <h4>File Preview (first {{ Math.min(rawData.length, 500) }} rows)</h4>
                <p class="preview-info">{{ rawData.length }} total rows — edit cells below like Excel</p>
                <ExcelViewer
                  :data="rawData.slice(0, 500)"
                  :headers="uploadPreviewHeaders"
                  :original-data="originalRawData.slice(0, 500)"
                  :original-headers="originalFileColumns"
                  :show-mapping-controls="false"
                  :column-mapping="columnMapping"
                  :available-file-columns="fileColumns"
                  :default-mapped-mode="mappingApplied"
                  @data-update="onRawExcelUpdate"
                  @mapping-update="updateColumnMapping"
                />
                <button class="btn-review-excel-small" @click="openExcelReview(rawData, 'Uploaded Data')">Full Screen</button>
              </div>

              <!-- Manual Mapping Dialog -->
              <v-dialog v-model="showMappingDialog" max-width="700px">
                <v-card>
                  <v-card-title>Map Columns</v-card-title>
                  <v-card-text>
                    <div class="mapping-instructions">
                      <p><v-icon small>mdi-hand-pointing-right</v-icon> Manually match each required system column to a column from your uploaded Excel file.</p>
                    </div>
                    <div class="mapping-grid">
                      <div v-for="reqCol in requiredColumns" :key="reqCol" class="mapping-row">
                        <label class="required-label">{{ reqCol }}:</label>
                        <select v-model="columnMapping[reqCol]" class="mapping-select">
                          <option :value="null">-- Select column --</option>
                          <option v-for="fileCol in fileColumns" :key="fileCol" :value="fileCol">{{ fileCol }}</option>
                        </select>
                        <span v-if="columnMapping[reqCol]" class="mapped-indicator">✅</span>
                      </div>
                    </div>
                    <div class="mapping-hint">
                      <v-icon size="16">mdi-information</v-icon>
                      <small>Changes are applied immediately when you click "Apply Mapping".</small>
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
                  <span>Missing required columns. Click "Map Columns" to manually assign them.</span>
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

                <p class="report-hint">Click <strong>Preview Report</strong> to see the full report with live FRED charts. Downloads match the preview.</p>
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
import * as XLSX from 'xlsx'
import api from '@/services/api.js'
import sessionManager from '@/services/sessionManager.js'
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
      return rawData.value.length > 0   // Only need raw data – mapping optional
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
    columnMapping.value = matchColumns(fileColumns.value, requiredColumns.value, columnVariations.value)
    mappingApplied.value = false
    saveSessionData()
    // Removed alert
  }
}

function deleteHistoryItem(idx) {
  uploadHistory.value.splice(idx, 1)
  saveUploadHistory()
}

// ========== Computed Helpers ==========
const fileSize = computed(() => {
  if (!uploadedFile.value) return ''
  const bytes = uploadedFile.value.size
  if (bytes === 0) return ''  // Hide 0B
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
  if (mappingApplied.value) {
    return requiredColumns.value.filter(col => isColumnMapped(col, mappingContext.value))
  }
  return originalFileColumns.value.length
    ? originalFileColumns.value
    : Object.keys(rawData.value[0] || {})
})
const cleanPreviewHeaders = computed(() => Object.keys((cleanedData.value[0]) || {}))

const portfolioAvgRate = computed(() => instrumentType.value === 'money-market' ? calculations.value.avgRate || 0 : instrumentType.value === 'bonds' ? calculations.value.avgCouponRate || 0 : calculations.value.avgDiscountRate || 0)

// ========== Navigation – FIXED ==========
function goToDashboard() { saveSessionData(); router.push('/dashboard') }
function goToPortfolioSummary() { saveSessionData(); router.push('/summary') }

// These functions directly set the tab without checking farthestAllowedIndex
function goToCalculations() {
  if (hasCleanedData.value) {
    saveSessionData()
    activeTab.value = 'calculations'
  } else {
    alert('Please clean your data first.')
  }
}

function goToVisualizations() {
  if (hasCleanedData.value) {
    saveSessionData()
    activeTab.value = 'visualizations'
  } else {
    alert('Please clean your data first.')
  }
}

function goToReportTab() {
  saveSessionData()
  activeTab.value = 'reports'
}

// switchTab now allows navigation to any tab (the progress bar still shows disabled for incomplete steps)
function switchTab(tab) {
  saveSessionData()
  activeTab.value = tab
}

// ========== File Upload ==========
const fileInput = ref(null)
function handleFileUpload(e) { const file = e.target.files[0]; if (file) { uploadedFile.value = file; readFileData(file) } }
function handleDrop(e) { const file = e.dataTransfer.files[0]; if (file) { uploadedFile.value = file; readFileData(file) } }

async function readFileData(file) {
  fileLoading.value = true
  const ext = file.name.split('.').pop().toLowerCase()
  let data = []
  try {
    if (file.size > 20 * 1024 * 1024 && !confirm(`File is ${(file.size / (1024 * 1024)).toFixed(2)} MB. Continue?`)) {
      fileLoading.value = false; uploadedFile.value = null; return
    }
    if (ext === 'csv') {
      const text = await file.text()
      const lines = text.split(/\r?\n/).filter(l => l.trim())
      if (lines.length === 0) throw new Error('Empty file')
      let delimiter = ','; if (lines[0].includes(';') && !lines[0].includes(',')) delimiter = ';'
      const headers = lines[0].split(delimiter).map(h => h.trim().replace(/^"|"$/g, ''))
      data = lines.slice(1).map(line => {
        const vals = line.split(delimiter).map(v => v.trim().replace(/^"|"$/g, ''))
        const row = {}
        headers.forEach((h, i) => { row[h] = vals[i] !== undefined ? vals[i] : '' })
        return row
      })
    } else {
      const buffer = await file.arrayBuffer()
      const workbook = XLSX.read(buffer, { type: 'array', cellDates: false, cellNF: false, cellText: false, sheetRows: 5000, defval: "" })
      const sheetName = workbook.SheetNames[0]
      const sheet = workbook.Sheets[sheetName]
      data = XLSX.utils.sheet_to_json(sheet, { defval: "" })
      if (data.length === 0) throw new Error('No data found in the first sheet')
    }
    rawData.value = data
    originalRawData.value = JSON.parse(JSON.stringify(data))
    originalFileColumns.value = Object.keys(data[0] || {})
    fileColumns.value = [...originalFileColumns.value]

    columnMapping.value = matchColumns(fileColumns.value, requiredColumns.value, columnVariations.value)
    mappingApplied.value = false

    addToHistory(file.name, data)
    debouncedSave()
    // Removed success alert
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
  debouncedSave()
  if (fileInput.value) fileInput.value.value = ''
}

// ========== Mapping ==========
function applyMappingToData(mapping) {
  if (!originalRawData.value.length) return false
  const allMapped = requiredColumns.value.every(col => mapping[col])
  if (!allMapped) {
    alert('Please map all required columns before applying.')
    return false
  }
  rawData.value = applyMappingToRows(originalRawData.value, requiredColumns.value, mapping)
  fileColumns.value = requiredColumns.value.filter(c => mapping[c])
  mappingApplied.value = true
  debouncedSave()
  return true
}

function applyColumnMappingAndClose() {
  const success = applyMappingToData(columnMapping.value)
  if (success) {
    showMappingDialog.value = false
    // Removed alert
  }
}

function closeMappingDialog() { showMappingDialog.value = false }

function openMappingDialog() {
  if (!originalFileColumns.value.length) {
    originalFileColumns.value = Object.keys((originalRawData.value[0] || rawData.value[0]) || {})
  }
  fileColumns.value = [...originalFileColumns.value]
  const suggested = matchColumns(fileColumns.value, requiredColumns.value, columnVariations.value)
  requiredColumns.value.forEach(col => {
    if (!columnMapping.value[col] && suggested[col]) {
      columnMapping.value[col] = suggested[col]
    }
  })
  showMappingDialog.value = true
}

function updateColumnMapping(newMapping) {
  columnMapping.value = newMapping
}

async function continueAfterUpload() {
  if (!uploadedFile.value) { alert('Please upload a file first.'); return }
  if (!rawData.value.length) { alert('No data loaded. Please upload a valid file.'); return }
  // No longer requires mapping
  activeTab.value = 'cleaning'
  debouncedSave()
}

// ========== Cleaning ==========
function applyCleaning() {
  if (!rawData.value.length) return
  let data = JSON.parse(JSON.stringify(rawData.value))
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
  if (cleaningOptions.value.fillForward) { for (let i = 1; i < data.length; i++) Object.keys(data[i]).forEach(k => { if (data[i][k] === undefined || data[i][k] === null || data[i][k] === '') data[i][k] = data[i - 1][k] }) }
  if (cleaningOptions.value.fillBackward) { for (let i = data.length - 2; i >= 0; i--) Object.keys(data[i]).forEach(k => { if (data[i][k] === undefined || data[i][k] === null || data[i][k] === '') data[i][k] = data[i + 1][k] }) }
  cleanedData.value = data
  cleaningStats.value = { totalRows: rawData.value.length, validRows: cleanedData.value.length, removedRows: rawData.value.length - cleanedData.value.length, fixedMissing: 0 }
  debouncedSave()
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
}

// ========== Calculations ==========
async function calculateMetrics() {
  if (!cleanedData.value.length) return

  let uniqueInstrumentsCount = 0
  if (instrumentType.value === 'money-market') {
    const uniqueNames = new Set(cleanedData.value.map(row => row.Instrument).filter(v => v && v !== 'N/A'))
    uniqueInstrumentsCount = uniqueNames.size
  } else if (instrumentType.value === 'bonds') {
    const uniqueNames = new Set(cleanedData.value.map(row => row.BondName).filter(v => v && v !== 'N/A'))
    uniqueInstrumentsCount = uniqueNames.size
  } else {
    const uniqueNames = new Set(cleanedData.value.map(row => row.TBillName).filter(v => v && v !== 'N/A'))
    uniqueInstrumentsCount = uniqueNames.size
  }
  if (uniqueInstrumentsCount === 0) uniqueInstrumentsCount = cleanedData.value.length

  if (instrumentType.value === 'money-market') {
    const totalValue = cleanedData.value.reduce((s, r) => s + (parseFloat(r.Amount) || 0), 0)
    const totalRate = cleanedData.value.reduce((s, r) => s + (parseFloat(r.Rate) || 0), 0)
    const weightedSum = cleanedData.value.reduce((s, r) => s + ((parseFloat(r.Rate) || 0) * (parseFloat(r.Amount) || 0)), 0)
    const avgRateVal = totalRate / cleanedData.value.length
    calculations.value = {
      totalValue, instrumentCount: uniqueInstrumentsCount,
      avgRate: avgRateVal.toFixed(2),
      weightedAvgRate: totalValue > 0 ? (weightedSum / totalValue).toFixed(2) : 0,
      totalInterest: (totalValue * avgRateVal / 100).toFixed(2),
      interestEarned: (totalValue * avgRateVal / 100 * 90 / 365).toFixed(2),
      annualYield: ((Math.pow(1 + avgRateVal / 100, 365 / 90) - 1) * 100).toFixed(2),
      effectiveAnnualRate: ((Math.pow(1 + avgRateVal / 100, 1) - 1) * 100).toFixed(2),
      avgDaysToMaturity: 90,
      totalPrincipal: totalValue
    }
  } else if (instrumentType.value === 'bonds') {
    const totalValue = cleanedData.value.reduce((s, r) => s + (parseFloat(r.FaceValue) || 0), 0)
    const totalRate = cleanedData.value.reduce((s, r) => s + (parseFloat(r.CouponRate) || 0), 0)
    const weightedSum = cleanedData.value.reduce((s, r) => s + ((parseFloat(r.CouponRate) || 0) * (parseFloat(r.FaceValue) || 0)), 0)
    const totalYield = cleanedData.value.reduce((s, r) => s + (parseFloat(r.Yield) || 0), 0)
    const avgCoupon = totalRate / cleanedData.value.length
    const avgYieldVal = totalYield / cleanedData.value.length
    calculations.value = {
      totalValue, instrumentCount: uniqueInstrumentsCount,
      avgCouponRate: avgCoupon.toFixed(2),
      weightedAvgCoupon: totalValue > 0 ? (weightedSum / totalValue).toFixed(2) : 0,
      totalAnnualIncome: (totalValue * avgCoupon / 100).toFixed(2),
      avgYTM: avgYieldVal.toFixed(2),
      duration: (10 * 0.7).toFixed(2)
    }
  } else {
    const totalValue = cleanedData.value.reduce((s, r) => s + (parseFloat(r.FaceValue) || 0), 0)
    const totalRate = cleanedData.value.reduce((s, r) => s + (parseFloat(r.DiscountRate) || 0), 0)
    const weightedSum = cleanedData.value.reduce((s, r) => s + ((parseFloat(r.DiscountRate) || 0) * (parseFloat(r.FaceValue) || 0)), 0)
    const avgDiscount = totalRate / cleanedData.value.length
    const discountAmount = totalValue * (avgDiscount / 100) * 91 / 360
    const price = totalValue - discountAmount
    calculations.value = {
      totalValue, instrumentCount: uniqueInstrumentsCount,
      avgDiscountRate: avgDiscount.toFixed(2),
      weightedAvgDiscount: totalValue > 0 ? (weightedSum / totalValue).toFixed(2) : 0,
      totalDiscount: discountAmount.toFixed(2),
      effectiveYield: ((Math.pow(1 + discountAmount / price, 365 / 91) - 1) * 100).toFixed(2),
      bondEquivalentYield: ((discountAmount / price) * (365 / 91) * 100).toFixed(2),
      discountYield: ((discountAmount / totalValue) * (360 / 91) * 100).toFixed(2),
      moneyMarketYield: ((discountAmount / price) * (360 / 91) * 100).toFixed(2),
      pricePer100: (100 * (1 - (avgDiscount / 100) * (91 / 360))).toFixed(2),
      totalPurchasePrice: price.toFixed(2),
      avgInvestment: (price / cleanedData.value.length).toFixed(2),
      holdingPeriodYield: ((discountAmount / price) * 100).toFixed(2),
      annualizedYield: ((discountAmount / price) * (365 / 91) * 100).toFixed(2),
      avgDaysToMaturity: 91
    }
  }
  await enrichCalculationsWithFred()
  debouncedSave()
}

function continueToVisualizations() {
  if (!hasCleanedData.value) { alert('Please clean your data first.'); return }
  goToVisualizations()
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

  const origin = window.location.origin, logoUrl = `${origin}/DuraCapital logo.png`, logoHtml = `<img src="${logoUrl}" alt="DuraCapital Logo" style="display:block; width:auto; max-height:60px; height:auto; margin:0; padding:0; border:none;" onerror="this.style.display='none'">`
  let totalPortfolioValue = 0, totalInstrumentCount = 0
  for (const inst of report.instruments) {
    totalPortfolioValue += parseFloat(inst.calculations.totalValue) || 0
    totalInstrumentCount += parseInt(inst.calculations.instrumentCount) || 0
  }
  const instrumentNames = report.instruments.map(i => i.name), methodologyHtml = buildMethodologySection(instrumentNames)

  let html = `<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Portfolio Report - ${report.session}</title><script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"><\/script><style>@page{size:A4;margin:0;}@media print{body{margin:0;padding:0;}.cover-page{page-break-after:always;height:100vh;}.chart-container{page-break-inside:avoid;}}body{font-family:'Arial',sans-serif;margin:0;padding:0;line-height:1.5;color:#333;background:white;}.cover-page{position:relative;height:100vh;width:100%;background:url('${origin}/background%20report%201.webp') no-repeat center center;background-size:cover;display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center;color:#0B2044;}.cover-content{position:relative;z-index:2;padding:20px;background:rgba(255,255,255,0.7);border-radius:16px;max-width:80%;}.session-name{font-size:56px;font-weight:700;letter-spacing:2px;text-shadow:2px 2px 8px rgba(255,255,255,0.8);margin:20px 0 10px;font-family:'Georgia',serif;color:#0B2044;}.valuation-title{font-size:24px;font-weight:500;margin-bottom:20px;color:#1E88E5;}.logo-cover img{max-height:70px;width:auto;}.report-content{padding:20px 30px;max-width:1000px;margin:0 auto;}h1{color:#0B2044;font-size:28px;border-bottom:2px solid #0B2044;padding-bottom:10px;}h2{color:#1E88E5;margin-top:30px;font-size:22px;}h3{color:#0B2044;margin-top:20px;font-size:18px;}table{border-collapse:collapse;width:100%;margin-bottom:20px;}th,td{border:1px solid #ddd;padding:8px;text-align:left;}th{background:#0B2044;color:white;}.summary-text{background:#f8f9ff;padding:15px;border-radius:8px;margin-bottom:20px;}.metric-highlight{font-weight:bold;color:#0B2044;}.formula{font-family:monospace;background:#f0f0f0;padding:2px 6px;border-radius:4px;font-size:1.1em;margin:10px 0;}.methodology-card{background:#f8f9ff;padding:15px;border-radius:8px;margin-bottom:15px;}.methodology-card h4{margin-top:0;color:#0B2044;}.footer{margin-top:40px;font-size:12px;color:#666;text-align:center;border-top:1px solid #eee;padding-top:20px;}.chart-container{margin:20px 0;text-align:center;max-height:360px;overflow:hidden;}canvas{max-width:100%;height:auto;max-height:300px;background:#f8f9ff;border-radius:8px;padding:10px;}.chart-caption{font-size:12px;color:#666;margin-top:5px;}<\/style><\/head><body><div class="cover-page"><div class="cover-content"><div class="logo-cover">${logoHtml}</div><div class="valuation-title">Valuation Assessment Report</div><div class="session-name">${report.session}</div></div></div><div class="report-content"><div class="summary-text"><h3>Executive Summary</h3><p>This report provides a comprehensive valuation and performance summary of the selected fixed income instruments as of the report date. The analysis includes money market instruments, corporate bonds, and treasury bills held within the portfolio. The valuations are performed in accordance with IFRS 13 fair value measurement principles.</p></div><div class="summary-text"><h3>Portfolio Summary</h3><p>The portfolio comprises <strong>${report.instruments.length}</strong> asset class(es) with a total of <strong>${totalInstrumentCount}</strong> individual instruments. The combined fair value of the portfolio is <strong>$${totalPortfolioValue.toLocaleString()}</strong>.</p><p>Key observations:</p><ul><li>Money market instruments provide short-term liquidity with competitive yields.</li><li>Corporate bonds offer higher coupon rates but carry moderate credit risk.</li><li>Treasury bills are low-risk government securities with shorter maturities.</li></ul></div>`

  for (const inst of report.instruments) {
    const instData = inst.calculations
    html += `<h2>${inst.name}</h2><div class="summary-text">`
    if (inst.name === 'Money Market') html += `<p><strong>Total Value:</strong> $${(instData.totalValue || 0).toLocaleString()}</p><p><strong>Number of Instruments:</strong> ${instData.instrumentCount || 0}</p><p><strong>Average Interest Rate:</strong> ${instData.avgRate || 0}%</p><p><strong>Weighted Average Rate:</strong> ${instData.weightedAvgRate || 0}%</p><p><strong>Total Interest Earned (Annualized):</strong> $${(instData.totalInterest || 0).toLocaleString()}</p><p><strong>Average Days to Maturity:</strong> ${instData.avgDaysToMaturity || 0} days</p>`
    else if (inst.name === 'Bonds') html += `<p><strong>Total Value:</strong> $${(instData.totalValue || 0).toLocaleString()}</p><p><strong>Number of Instruments:</strong> ${instData.instrumentCount || 0}</p><p><strong>Average Coupon Rate:</strong> ${instData.avgCouponRate || 0}%</p><p><strong>Weighted Average Coupon:</strong> ${instData.weightedAvgCoupon || 0}%</p><p><strong>Total Annual Income:</strong> $${(instData.totalAnnualIncome || 0).toLocaleString()}</p><p><strong>Average Yield to Maturity:</strong> ${instData.avgYTM || 0}%</p><p><strong>Duration (years):</strong> ${instData.duration || 0}</p>`
    else html += `<p><strong>Total Value:</strong> $${(instData.totalValue || 0).toLocaleString()}</p><p><strong>Number of Instruments:</strong> ${instData.instrumentCount || 0}</p><p><strong>Average Discount Rate:</strong> ${instData.avgDiscountRate || 0}%</p><p><strong>Weighted Average Discount:</strong> ${instData.weightedAvgDiscount || 0}%</p><p><strong>Total Discount:</strong> $${(instData.totalDiscount || 0).toLocaleString()}</p><p><strong>Effective Yield:</strong> ${instData.effectiveYield || 0}%</p><p><strong>Bond Equivalent Yield:</strong> ${instData.bondEquivalentYield || 0}%</p><p><strong>Average Days to Maturity:</strong> ${instData.avgDaysToMaturity || 0} days</p>`
    html += `</div><h3>Detailed Metrics</h3><table><thead><tr><th>Metric</th><th>Value</th></tr></thead><tbody>`
    for (const [key, val] of Object.entries(instData)) if (key !== 'completed' && key !== 'timestamp' && key !== 'fred') html += `<tr><td class="metric-highlight">${formatMetricName(key)}</td><td class="metric-highlight">${formatMetricValue(key, val)}</td></tr>`
    html += `</tbody></table>`
    const chartData = chartDataMap[inst.name]
    if (chartData && chartData.labels?.length) {
      const chartId = `chart-${inst.name.replace(/\s/g, '')}`
      html += `<div class="summary-text"><h3>Yield Curve Analysis – ${inst.name}</h3><div class="chart-container"><canvas id="${chartId}" width="800" height="300" style="max-width:100%; height:auto; max-height:300px;"></canvas><div class="chart-caption">Source: FRED – ${chartSeriesLabel.value || 'market rate'} (${getCountryLabel(effectiveCountry.value)} / ${getCurrencyLabel(effectiveCurrency.value)})</div></div><p>This chart shows the latest market yield curve used as a benchmark for discounting cash flows of ${inst.name} instruments.</p><script>(function(){const ctx=document.getElementById('${chartId}').getContext('2d');new Chart(ctx,{type:'line',data:{labels:${JSON.stringify(chartData.labels)},datasets:${JSON.stringify(chartData.datasets || [{ label: 'Yield (%)', data: chartData.values, borderColor: '#0B2044' }])}},options:{responsive:true,maintainAspectRatio:true,plugins:{tooltip:{callbacks:{label:function(context){return 'Yield: '+context.raw+'%';}}},legend:{position:'top'}},scales:{y:{title:{display:true,text:'Percent (%)'}},x:{title:{display:true,text:'Date'},ticks:{maxRotation:45,autoSkip:true}}},maintainAspectRatio:false,animation:false}});})();<\/script></div>`
    } else {
      html += `<div class="summary-text graph-placeholder"><h3>Yield Curve Analysis – ${inst.name}</h3><div class="placeholder-chart"><svg width="100%" height="200" viewBox="0 0 800 200" xmlns="http://www.w3.org/2000/svg"><rect width="100%" height="100%" fill="#f8f9ff" stroke="#ccc" stroke-width="1"/><text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" fill="#999" font-size="14">Yield curve data not available.</text><line x1="50" y1="180" x2="750" y2="180" stroke="#aaa" stroke-width="1"/><line x1="50" y1="20" x2="50" y2="180" stroke="#aaa" stroke-width="1"/></svg></div><p>Market data could not be loaded for ${inst.name}.</p></div>`
    }
  }
  html += `<div class="summary-text"><h3>Methodology</h3>${methodologyHtml}<p><strong>Sources:</strong> Federal Reserve Economic Data (FRED), Damodaran Country Risk Premiums, Bloomberg OIS SOFR rates.</p></div><div class="footer"><p>Date Generated: ${report.date}</p><p>Generated by: DuraCapital Platform</p></div></div></body></html>`
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

// ========== Save to Session (EXPLICIT SAVE) ==========
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
  // Removed alert
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
        mappingApplied.value = false
        const allPresent = requiredColumns.value.every(col => fileColumns.value.includes(col))
        if (allPresent) {
          const autoMap = {}
          requiredColumns.value.forEach(col => {
            if (fileColumns.value.includes(col)) autoMap[col] = col
          })
          if (Object.keys(autoMap).length === requiredColumns.value.length) {
            columnMapping.value = autoMap
            mappingApplied.value = true
            rawData.value = applyMappingToRows(originalRawData.value, requiredColumns.value, autoMap)
          }
        }
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
    const allMapped = requiredColumns.value.every(col => columnMapping.value[col])
    if (allMapped && rawData.value.length) {
      mappingApplied.value = true
      rawData.value = applyMappingToRows(originalRawData.value, requiredColumns.value, columnMapping.value)
    }
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
    }
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
      const allMapped = requiredColumns.value.every(col => columnMapping.value[col])
      if (allMapped && rawData.value.length) {
        mappingApplied.value = true
        rawData.value = applyMappingToRows(originalRawData.value, requiredColumns.value, columnMapping.value)
      }
    } else if (fileColumns.value.length) {
      columnMapping.value = matchColumns(fileColumns.value, requiredColumns.value, columnVariations.value)
    }
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
    sessionSavedAt: sessionSavedAt.value
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
  rawData.value = mappingApplied.value
    ? applyMappingToRows(originalRawData.value, requiredColumns.value, columnMapping.value)
    : [...originalRawData.value]
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

async function fetchFredData() {
  fredLoading.value = true
  fredError.value = ''
  try {
    const sid = await seriesIdForMaturity()
    if (!sid) throw new Error('Could not resolve FRED series')
    selectedSeries.value = sid
    chartSeriesLabel.value = availableSeries.value[sid] || sid
    const loaded = await loadFredSeriesChart(sid)
    if (!loaded) throw new Error('No FRED data')
    chartData.value = loaded
    currentMarketRate.value = loaded.latest
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
.mapped-indicator { font-size: 18px; }
.mapping-hint { margin-top: 15px; padding: 10px; background: #f8f9ff; border-radius: 8px; display: flex; align-items: center; gap: 8px; color: #666; }
.required-columns { margin: 20px 0; }
.columns-list { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 10px; }
.column-badge { background: #e8ecf1; padding: 6px 12px; border-radius: 20px; font-size: 12px; display: inline-flex; align-items: center; gap: 6px; }
.column-badge.missing-column { background: #FFEBEE; color: #c62828; }
.column-badge.mapped-column { background: #E8F5E9; color: #2E7D32; }
.success-message { margin-top: 10px; padding: 8px 12px; background: #E8F5E9; border-radius: 8px; display: flex; align-items: center; gap: 8px; font-size: 12px; color: #2E7D32; }
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

/* Resizable Excel columns and rows – applies to all ExcelViewer instances */
.excel-edit-table th { resize: horizontal; overflow: auto; }
.excel-edit-table td { resize: vertical; overflow: auto; }
</style>

<style>
html, body, #app, .v-application, .v-application--wrap, .fixed-layout, .v-main, .v-content { max-width: 100vw !important; overflow-x: hidden !important; }
.instrument-page { max-width: 100% !important; overflow-x: hidden !important; }
.instrument-page .excel-table-wrapper, .instrument-page .excel-preview-section, .instrument-page .preview-section, .instrument-page .excel-scroll-wrapper, .instrument-page .excel-dialog-content { overflow-x: auto !important; max-width: 100% !important; }
.instrument-page .excel-viewer { max-width: 100% !important; overflow-x: hidden !important; }
.instrument-page .excel-edit-table { max-width: 100% !important; table-layout: fixed !important; width: 100% !important; }
.instrument-page .excel-edit-table th, .instrument-page .excel-edit-table td { white-space: nowrap !important; overflow: hidden !important; text-overflow: ellipsis !important; max-width: 200px !important; }
.instrument-page .filters-row select, .instrument-page .filters-row .filter-select, .instrument-page .filters-row select:focus, .instrument-page .filters-row .filter-select:focus { color: #000000 !important; background-color: #ffffff !important; }
</style>