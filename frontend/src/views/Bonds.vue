<template>
  <FixedLayout>
    <div class="instrument-page">
      <!-- Page Header -->
      <div class="page-header">
        <div class="header-left">
          <h1>{{ instrumentName }}</h1>
          <p>{{ instrumentDescription }}</p>
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
              completed: getTabStatus(step.tab)
            }"
            @click="switchTab(step.tab)"
          >
            <div class="step-circle">{{ index + 1 }}</div>
            <div class="step-label">{{ step.name }}</div>
          </div>
        </div>
      </div>

      <!-- Content based on active tab -->
      <div class="tab-content">
        <!-- UPLOAD TAB -->
        <div v-if="activeTab === 'upload'" class="content-card">
          <v-card>
            <v-card-title>
              <v-icon>mdi-upload</v-icon>
              Upload {{ instrumentName }} Dataset
            </v-card-title>
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
                <button class="btn-review-excel" @click="openExcelReview(rawData, 'Uploaded Data')" :disabled="!rawData || rawData.length === 0">
                  <v-icon>mdi-eye</v-icon> Review Excel
                </button>
                <button class="btn-mapping" @click="autoMatchColumns" :disabled="!rawData || rawData.length === 0">
                  <v-icon>mdi-map</v-icon> Map Columns
                </button>
              </div>

              <div v-if="rawData && rawData.length > 0" class="excel-preview-section">
                <h4>File Preview:</h4>
                <div class="preview-toolbar">
                  <span class="preview-info">Showing {{ rawData.length }} rows × {{ Object.keys(rawData[0] || {}).length }} columns</span>
                  <div class="preview-controls">
                    <button @click="previewStartRow = Math.max(0, previewStartRow - 10)" :disabled="previewStartRow === 0" class="preview-btn">← Previous</button>
                    <span>Rows {{ previewStartRow + 1 }} - {{ Math.min(previewEndRow, rawData.length) }}</span>
                    <button @click="previewStartRow = Math.min(rawData.length - previewRows, previewStartRow + 10)" :disabled="previewEndRow >= rawData.length" class="preview-btn">Next →</button>
                    <button class="btn-review-excel-small" @click="openExcelReview(rawData, 'Uploaded Data')">
                      <v-icon size="16">mdi-eye</v-icon> Full Screen
                    </button>
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
              <v-dialog v-model="showMappingDialog" max-width="600px">
                <v-card>
                  <v-card-title>
                    <v-icon>mdi-map</v-icon>
                    Map Columns
                  </v-card-title>
                  <v-card-text>
                    <p>Please map the required columns to columns in your file:</p>
                    <div class="mapping-grid">
                      <div v-for="reqCol in requiredColumns" :key="reqCol" class="mapping-row">
                        <label class="required-label">{{ reqCol }}:</label>
                        <select v-model="columnMapping[reqCol]" class="mapping-select">
                          <option :value="null">-- Select column --</option>
                          <option v-for="fileCol in fileColumns" :key="fileCol" :value="fileCol">
                            {{ fileCol }}
                          </option>
                        </select>
                      </div>
                    </div>
                    <div class="mapping-hint">
                      <v-icon size="16">mdi-information</v-icon>
                      <small>Column names are matched automatically. You can adjust the mapping above.</small>
                    </div>
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
                  <span v-for="col in requiredColumns" :key="col" class="column-badge" :class="{ 'missing-column': rawData.length > 0 && !hasRequiredColumn(col) }">
                    <v-icon size="12">{{ rawData.length > 0 && hasRequiredColumn(col) ? 'mdi-check' : 'mdi-close' }}</v-icon>
                    {{ col }}
                  </span>
                </div>
                <div v-if="rawData.length > 0 && missingColumns.length > 0" class="warning-message">
                  <v-icon color="warning">mdi-alert</v-icon>
                  <span>Missing required columns. Click "Map Columns" to fix.</span>
                </div>
              </div>

              <div class="navigation-buttons">
                <button v-if="rawData.length > 0 && missingColumns.length > 0" class="btn-warning" @click="autoMatchColumns">
                  Map Columns
                </button>
                <button class="btn-primary" @click="uploadData" :disabled="!uploadedFile || (rawData.length > 0 && missingColumns.length > 0)">
                  Upload & Continue
                </button>
                <button class="btn-secondary" @click="goToDashboard">Cancel</button>
              </div>
            </v-card-text>
          </v-card>
        </div>

        <!-- CLEANING TAB -->
        <div v-if="activeTab === 'cleaning'" class="content-card">
          <v-card>
            <v-card-title>
              <v-icon>mdi-broom</v-icon>
              Clean {{ instrumentName }} Data
            </v-card-title>
            <v-card-text>
              <div v-if="!hasData" class="empty-state">
                <v-icon size="48" color="#ccc">mdi-database</v-icon>
                <p>No data uploaded yet. Please upload a dataset first.</p>
                <button class="btn-primary" @click="switchTab('upload')">Go to Upload</button>
              </div>
              
              <div v-else>
                <div class="cleaning-stats">
                  <div class="stat-card">
                    <div class="stat-value">{{ cleaningStats.totalRows }}</div>
                    <div class="stat-label">Total Rows</div>
                  </div>
                  <div class="stat-card">
                    <div class="stat-value">{{ cleaningStats.validRows }}</div>
                    <div class="stat-label">Valid Rows</div>
                  </div>
                  <div class="stat-card">
                    <div class="stat-value">{{ cleaningStats.removedRows }}</div>
                    <div class="stat-label">Removed Rows</div>
                  </div>
                  <div class="stat-card">
                    <div class="stat-value">{{ cleaningStats.fixedMissing }}</div>
                    <div class="stat-label">Missing Fixed</div>
                  </div>
                </div>

                <div class="cleaning-actions">
                  <button class="btn-primary" @click="cleanData" :disabled="cleanedData.length > 0">
                    <v-icon>mdi-broom</v-icon> Auto-Clean Data
                  </button>
                  <button class="btn-review-excel" @click="openExcelReview(rawData, 'Raw Data (Before Cleaning)')" :disabled="!rawData || rawData.length === 0">
                    <v-icon>mdi-eye</v-icon> Review Raw Data
                  </button>
                </div>

                <!-- Raw Data Preview with Issue Highlighting -->
                <div v-if="rawData.length > 0 && !cleanedData.length" class="preview-section">
                  <h4>Raw Data with Issues Highlighted:</h4>
                  <div class="legend">
                    <span class="legend-badge invalid-row-badge">⚠ Invalid Row</span>
                    <span class="legend-badge invalid-cell-badge">❌ Missing/Invalid Value</span>
                  </div>
                  <div class="preview-toolbar">
                    <span class="preview-info">Raw Data: {{ rawData.length }} rows</span>
                    <div class="preview-controls">
                      <button @click="rawPreviewStartRow = Math.max(0, rawPreviewStartRow - 10)" :disabled="rawPreviewStartRow === 0" class="preview-btn">← Previous</button>
                      <span>Rows {{ rawPreviewStartRow + 1 }} - {{ Math.min(rawPreviewEndRow, rawData.length) }}</span>
                      <button @click="rawPreviewStartRow = Math.min(rawData.length - rawPreviewRows, rawPreviewStartRow + 10)" :disabled="rawPreviewEndRow >= rawData.length" class="preview-btn">Next →</button>
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
                          <td v-for="col in rawPreviewColumnsList" :key="col" :class="{ 'invalid-cell': isInvalidValue(row[col]) }">
                            {{ formatCellValue(row[col]) }}
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>

                <div v-if="cleanedData.length > 0" class="preview-section">
                  <h4>Cleaned Data Preview:</h4>
                  <div class="highlight-box">
                    <p>✓ Removed {{ cleaningStats.removedRows }} invalid rows</p>
                    <p>✓ Fixed {{ cleaningStats.fixedMissing }} missing values</p>
                    <p class="success-text">✓ Data is now clean and ready for calculations</p>
                  </div>
                  
                  <div class="preview-toolbar">
                    <span class="preview-info">Clean Data: {{ cleanedData.length }} rows</span>
                    <div class="preview-controls">
                      <button @click="cleanPreviewStartRow = Math.max(0, cleanPreviewStartRow - 10)" :disabled="cleanPreviewStartRow === 0" class="preview-btn">← Previous</button>
                      <span>Rows {{ cleanPreviewStartRow + 1 }} - {{ Math.min(cleanPreviewEndRow, cleanedData.length) }}</span>
                      <button @click="cleanPreviewStartRow = Math.min(cleanedData.length - cleanPreviewRows, cleanPreviewStartRow + 10)" :disabled="cleanPreviewEndRow >= cleanedData.length" class="preview-btn">Next →</button>
                      <button class="btn-review-excel-small" @click="openExcelReview(cleanedData, 'Cleaned Data')">
                        <v-icon size="16">mdi-eye</v-icon> Full Screen
                      </button>
                    </div>
                  </div>
                  <div class="table-wrapper">
                    <table class="data-table">
                      <thead>
                        <tr>
                          <th>#</th>
                          <th v-for="col in cleanPreviewColumnsList" :key="col">{{ col }}</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr v-for="(row, idx) in paginatedCleanPreview" :key="idx">
                          <td class="row-number">{{ cleanPreviewStartRow + idx + 1 }}</td>
                          <td v-for="col in cleanPreviewColumnsList" :key="col" :class="{ 'fixed-value': wasFixed(row, col) }">
                            {{ formatCellValue(row[col]) }}
                            <span v-if="wasFixed(row, col)" class="fixed-badge" title="This value was fixed during cleaning">✓</span>
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>

                <div class="navigation-buttons">
                  <button class="btn-secondary" @click="switchTab('upload')">Previous</button>
                  <button class="btn-primary" @click="switchTab('calculations')" :disabled="!hasCleanedData">Next: Calculations</button>
                  <button class="btn-secondary" @click="goToDashboard">Dashboard</button>
                </div>
              </div>
            </v-card-text>
          </v-card>
        </div>

        <!-- CALCULATIONS TAB -->
        <div v-if="activeTab === 'calculations'" class="content-card">
          <v-card>
            <v-card-title>
              <v-icon>mdi-calculator</v-icon>
              {{ instrumentName }} Calculations
            </v-card-title>
            <v-card-text>
              <div v-if="!hasCleanedData" class="empty-state">
                <v-icon size="48" color="#ccc">mdi-calculator</v-icon>
                <p>No cleaned data available. Please clean your data first.</p>
                <button class="btn-primary" @click="switchTab('cleaning')">Go to Cleaning</button>
              </div>
              
              <div v-else>
                <div class="calculations-grid">
                  <div v-for="calc in calculationsList" :key="calc.name" class="calculation-card">
                    <div class="calc-name">{{ calc.name }}</div>
                    <div class="calc-value">{{ calc.value }}</div>
                    <div class="calc-unit">{{ calc.unit }}</div>
                  </div>
                </div>

                <!-- Money Market Calculations -->
                <div class="detailed-calculations" v-if="instrumentType.value === 'money-market'">
                  <h4>Money Market Calculations</h4>
                  <div class="detail-item">
                    <span class="detail-label">Weighted Average Rate:</span>
                    <span class="detail-value">{{ calculations.weightedAvgRate || calculations.avgRate }}%</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-label">Total Interest (Annualized):</span>
                    <span class="detail-value">${{ calculations.totalInterest?.toLocaleString() || 0 }}</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-label">Interest Earned:</span>
                    <span class="detail-value">${{ calculations.interestEarned?.toLocaleString() || 0 }}</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-label">Annual Yield:</span>
                    <span class="detail-value">{{ calculations.annualYield || 0 }}%</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-label">Maturity Value:</span>
                    <span class="detail-value">${{ calculations.maturityValue?.toLocaleString() || 0 }}</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-label">Average Yield:</span>
                    <span class="detail-value">{{ calculations.avgYield || 0 }}%</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-label">Effective Annual Rate:</span>
                    <span class="detail-value">{{ calculations.effectiveAnnualRate || 0 }}%</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-label">Average Days to Maturity:</span>
                    <span class="detail-value">{{ calculations.avgDaysToMaturity || 0 }} days</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-label">Total Interest Income:</span>
                    <span class="detail-value">${{ calculations.totalInterestIncome?.toLocaleString() || 0 }}</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-label">Portfolio Yield:</span>
                    <span class="detail-value">{{ calculations.portfolioYield || 0 }}%</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-label">Total Principal:</span>
                    <span class="detail-value">${{ calculations.totalPrincipal?.toLocaleString() || calculations.totalValue?.toLocaleString() || 0 }}</span>
                  </div>
                </div>

                <!-- Bonds Calculations -->
                <div class="detailed-calculations" v-if="instrumentType.value === 'bonds'">
                  <h4>Bond Calculations</h4>
                  <div class="detail-item">
                    <span class="detail-label">Weighted Average Coupon:</span>
                    <span class="detail-value">{{ calculations.weightedAvgCoupon || calculations.avgCouponRate }}%</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-label">Total Annual Income:</span>
                    <span class="detail-value">${{ calculations.totalAnnualIncome?.toLocaleString() || 0 }}</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-label">Average Yield to Maturity:</span>
                    <span class="detail-value">{{ calculations.avgYTM || 0 }}%</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-label">Annual Coupon Payment:</span>
                    <span class="detail-value">${{ calculations.annualCouponPayment?.toLocaleString() || 0 }}</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-label">Current Yield:</span>
                    <span class="detail-value">{{ calculations.currentYield || 0 }}%</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-label">Yield to Maturity:</span>
                    <span class="detail-value">{{ calculations.yieldToMaturity || 0 }}%</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-label">Yield Curve Rate:</span>
                    <span class="detail-value">{{ calculations.yieldCurveRate || 0 }}%</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-label">Yield Spread:</span>
                    <span class="detail-value">{{ calculations.yieldSpread || 0 }} bps</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-label">Duration:</span>
                    <span class="detail-value">{{ calculations.duration || 0 }} years</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-label">Modified Duration:</span>
                    <span class="detail-value">{{ calculations.modifiedDuration || 0 }} years</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-label">Convexity:</span>
                    <span class="detail-value">{{ calculations.convexity || 0 }}</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-label">Macaulay Duration:</span>
                    <span class="detail-value">{{ calculations.macaulayDuration || 0 }} years</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-label">Price Volatility:</span>
                    <span class="detail-value">{{ calculations.priceVolatility || 0 }}%</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-label">Credit Spread:</span>
                    <span class="detail-value">{{ calculations.creditSpread || 0 }} bps</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-label">Real Yield:</span>
                    <span class="detail-value">{{ calculations.realYield || 0 }}%</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-label">Nominal Yield:</span>
                    <span class="detail-value">{{ calculations.nominalYield || 0 }}%</span>
                  </div>
                </div>

                <!-- T-Bills Calculations -->
                <div class="detailed-calculations" v-if="instrumentType.value === 'tbills'">
                  <h4>T-Bill Calculations</h4>
                  <div class="detail-item">
                    <span class="detail-label">Weighted Average Discount:</span>
                    <span class="detail-value">{{ calculations.weightedAvgDiscount || calculations.avgDiscountRate }}%</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-label">Total Discount Earned:</span>
                    <span class="detail-value">${{ calculations.totalDiscount?.toLocaleString() || 0 }}</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-label">Effective Yield:</span>
                    <span class="detail-value">{{ calculations.effectiveYield || 0 }}%</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-label">Discount Yield:</span>
                    <span class="detail-value">{{ calculations.discountYield || 0 }}%</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-label">Bond Equivalent Yield:</span>
                    <span class="detail-value">{{ calculations.bondEquivalentYield || 0 }}%</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-label">Money Market Yield:</span>
                    <span class="detail-value">{{ calculations.moneyMarketYield || 0 }}%</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-label">Price per $100 Face Value:</span>
                    <span class="detail-value">${{ calculations.pricePer100 || 0 }}</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-label">Total Purchase Price:</span>
                    <span class="detail-value">${{ calculations.totalPurchasePrice?.toLocaleString() || 0 }}</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-label">Average Investment:</span>
                    <span class="detail-value">${{ calculations.avgInvestment?.toLocaleString() || 0 }}</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-label">Holding Period Yield:</span>
                    <span class="detail-value">{{ calculations.holdingPeriodYield || 0 }}%</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-label">Annualized Yield:</span>
                    <span class="detail-value">{{ calculations.annualizedYield || 0 }}%</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-label">Average Days to Maturity:</span>
                    <span class="detail-value">{{ calculations.avgDaysToMaturity || 0 }} days</span>
                  </div>
                </div>

                <div class="navigation-buttons">
                  <button class="btn-secondary" @click="switchTab('cleaning')">Previous</button>
                  <button class="btn-primary" @click="switchTab('visualizations')">Next: Visualizations</button>
                  <button class="btn-secondary" @click="goToDashboard">Dashboard</button>
                </div>
              </div>
            </v-card-text>
          </v-card>
        </div>

        <!-- VISUALIZATIONS TAB -->
        <div v-if="activeTab === 'visualizations'" class="content-card">
          <v-card>
            <v-card-title>
              <v-icon>mdi-chart-line</v-icon>
              {{ instrumentName }} Visualizations
            </v-card-title>
            <v-card-text>
              <div class="visualization-placeholder">
                <v-icon size="64" color="#0B2044">mdi-chart-line</v-icon>
                <h3>Visualizations Coming Soon</h3>
                <p>Yield curve and other visualizations will be displayed here once the backend API is integrated.</p>
                <div class="placeholder-note">
                  <v-icon>mdi-information</v-icon>
                  <span>Backend API integration in progress</span>
                </div>
              </div>

              <div class="navigation-buttons">
                <button class="btn-secondary" @click="switchTab('calculations')">Previous</button>
                <button class="btn-primary" @click="switchTab('summary')">Next: Summary</button>
                <button class="btn-secondary" @click="goToDashboard">Dashboard</button>
              </div>
            </v-card-text>
          </v-card>
        </div>

        <!-- SUMMARY TAB -->
        <div v-if="activeTab === 'summary'" class="content-card">
          <v-card>
            <v-card-title>
              <v-icon>mdi-file-document</v-icon>
              {{ instrumentName }} Summary
            </v-card-title>
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
                  <div v-for="calc in calculationsList" :key="calc.name">
                    <p><strong>{{ calc.name }}:</strong> {{ calc.value }} {{ calc.unit }}</p>
                  </div>
                </div>
              </div>

              <div class="summary-progress">
                <div class="progress-bar">
                  <div class="progress-fill" style="width: 100%"></div>
                </div>
                <p class="progress-text">✓ Upload ✓ Clean ✓ Calculate — Ready for Report</p>
              </div>

              <div class="navigation-buttons">
                <button class="btn-secondary" @click="switchTab('visualizations')">Previous</button>
                <button class="btn-primary" @click="switchTab('reports')">Move to Report →</button>
                <button class="btn-secondary" @click="goToDashboard">Dashboard</button>
              </div>
            </v-card-text>
          </v-card>
        </div>

        <!-- REPORTS TAB -->
        <div v-if="activeTab === 'reports'" class="content-card">
          <v-card>
            <v-card-title>
              <v-icon>mdi-file-pdf</v-icon>
              Generate {{ instrumentName }} Report
            </v-card-title>
            <v-card-text>
              <div class="report-options">
                <div class="report-preview">
                  <h3>Report Preview</h3>
                  <div class="report-content">
                    <p><strong>Instrument:</strong> {{ instrumentName }}</p>
                    <p><strong>Date Generated:</strong> {{ new Date().toLocaleString() }}</p>
                    <p><strong>Total Value:</strong> ${{ calculations.totalValue?.toLocaleString() || 0 }}</p>
                    <p><strong>Records Processed:</strong> {{ cleanedData.length }}</p>
                  </div>
                  
                  <div class="report-data-preview">
                    <div class="preview-toolbar">
                      <h5>Data Preview</h5>
                      <button class="btn-review-excel-small" @click="openExcelReview(cleanedData, 'Report Data')" :disabled="!cleanedData || cleanedData.length === 0">
                        <v-icon size="16">mdi-eye</v-icon> Review Full Data
                      </button>
                    </div>
                    <div class="table-wrapper">
                      <table class="data-table">
                        <thead>
                          <tr>
                            <th>#</th>
                            <th v-for="col in reportPreviewColumns" :key="col">{{ col }}</th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr v-for="(row, idx) in reportDataPreview" :key="idx">
                            <td>{{ idx + 1 }}</td>
                            <td v-for="col in reportPreviewColumns" :key="col">{{ formatCellValue(row[col]) }}</td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
                <div class="report-actions">
                  <button class="btn-primary" @click="downloadReport">
                    <v-icon>mdi-download</v-icon> Download JSON Report
                  </button>
                  <button class="btn-success" @click="saveToSummary">
                    <v-icon>mdi-content-save</v-icon> Save to Summary
                  </button>
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
          <div class="dialog-title-content">
            <v-icon large>mdi-file-excel</v-icon>
            <span>{{ excelDialogTitle }} - Excel Viewer</span>
          </div>
          <v-spacer></v-spacer>
          <button class="btn-close-dialog" @click="closeExcelDialog">
            <v-icon>mdi-close</v-icon>
          </button>
        </v-card-title>
        <v-card-text class="excel-dialog-content">
          <div class="excel-full-view">
            <div class="excel-toolbar-full">
              <div class="excel-info">
                <span>{{ excelData.length }} rows × {{ excelColumns.length }} columns</span>
              </div>
              <div class="excel-export-buttons">
                <button class="btn-excel-export" @click="exportToCSV">
                  <v-icon size="16">mdi-file-delimited</v-icon> Export CSV
                </button>
                <button class="btn-excel-export" @click="exportToJSON">
                  <v-icon size="16">mdi-code-json</v-icon> Export JSON
                </button>
              </div>
            </div>
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
                    <td class="sticky-col">{{ idx + 1 }}</td>
                    <td v-for="col in excelColumns" :key="col">{{ formatCellValue(row[col]) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <button class="btn-secondary" @click="closeExcelDialog">Close</button>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </FixedLayout>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import FixedLayout from '@/components/FixedLayout.vue'
import * as XLSX from 'xlsx'

const router = useRouter()
const route = useRoute()

// Excel Dialog State
const showExcelDialog = ref(false)
const excelData = ref([])
const excelColumns = ref([])
const excelDialogTitle = ref('')

// Instrument type from route
const instrumentType = computed(() => route.params.type || route.path.split('/').pop())
const instrumentName = computed(() => {
  const names = { 'money-market': 'Money Market', bonds: 'Bonds', tbills: 'T-Bills' }
  return names[instrumentType.value] || 'Instrument'
})

const instrumentDescription = computed(() => {
  const descriptions = {
    'money-market': 'Short-term debt instruments including treasury bills, commercial paper',
    'bonds': 'Fixed income securities including government and corporate bonds',
    'tbills': 'Treasury bills - short-term government securities'
  }
  return descriptions[instrumentType.value] || 'Financial instrument management'
})

// Steps
const steps = [
  { tab: 'upload', name: 'Upload' },
  { tab: 'cleaning', name: 'Clean' },
  { tab: 'calculations', name: 'Calculate' },
  { tab: 'visualizations', name: 'Visualize' },
  { tab: 'summary', name: 'Summary' },
  { tab: 'reports', name: 'Report' }
]

const currentStepIndex = computed(() => steps.findIndex(s => s.tab === activeTab.value))
const totalSteps = steps.length

const activeTab = computed({
  get: () => route.query.tab || 'upload',
  set: (val) => router.push({ query: { tab: val } })
})

// Data - with persistence
const uploadedFile = ref(null)
const rawData = ref([])
const cleanedData = ref([])
const columnMapping = ref({})
const showMappingDialog = ref(false)
const fileColumns = ref([])
const fixedValuesTracker = ref(new Map())

// Raw Data Preview for Cleaning
const rawPreviewRows = ref(10)
const rawPreviewStartRow = ref(0)
const rawPreviewEndRow = computed(() => Math.min(rawPreviewStartRow.value + rawPreviewRows.value, rawData.value.length))
const rawPreviewColumnsList = computed(() => {
  if (!rawData.value || rawData.value.length === 0) return []
  return Object.keys(rawData.value[0]).slice(0, 8)
})
const paginatedRawPreview = computed(() => rawData.value.slice(rawPreviewStartRow.value, rawPreviewEndRow.value))

// Required columns
const requiredColumns = computed(() => {
  const columns = {
    'money-market': ['Date', 'Instrument', 'Rate', 'Amount'],
    'bonds': ['Date', 'BondName', 'CouponRate', 'FaceValue', 'Yield'],
    'tbills': ['Date', 'TBillName', 'DiscountRate', 'FaceValue']
  }
  return columns[instrumentType.value] || ['Date', 'Amount']
})

// Column name variations for auto-matching
const columnVariations = {
  'Date': ['Date', 'date', 'DATE', 'Transaction Date', 'Trade Date', 'Settlement Date', 'Value Date'],
  'Instrument': ['Instrument', 'instrument', 'INSTRUMENT', 'Security', 'Security Name', 'Name', 'Description'],
  'Rate': ['Rate', 'rate', 'RATE', 'Interest Rate', 'Coupon Rate', 'Discount Rate', 'Yield'],
  'Amount': ['Amount', 'amount', 'AMOUNT', 'Face Value', 'FaceValue', 'Value', 'Price', 'Notional', 'Principal'],
  'BondName': ['BondName', 'Bond Name', 'bond', 'BOND', 'Security', 'Issuer'],
  'CouponRate': ['CouponRate', 'Coupon Rate', 'coupon', 'Rate', 'Interest Rate'],
  'FaceValue': ['FaceValue', 'Face Value', 'Face', 'Value', 'Amount', 'Principal', 'Par Value'],
  'Yield': ['Yield', 'yield', 'YIELD', 'Yield to Maturity', 'YTM', 'Return'],
  'TBillName': ['TBillName', 'T-Bill Name', 'TBill', 'T Bill', 'Security', 'Instrument'],
  'DiscountRate': ['DiscountRate', 'Discount Rate', 'discount', 'Rate']
}

// Preview
const previewRows = ref(10)
const previewStartRow = ref(0)
const previewEndRow = computed(() => Math.min(previewStartRow.value + previewRows.value, rawData.value.length))
const previewColumnsList = computed(() => {
  if (!rawData.value || rawData.value.length === 0) return []
  return Object.keys(rawData.value[0]).slice(0, 8)
})
const paginatedPreviewData = computed(() => rawData.value.slice(previewStartRow.value, previewEndRow.value))

// Clean Preview
const cleanPreviewRows = ref(10)
const cleanPreviewStartRow = ref(0)
const cleanPreviewEndRow = computed(() => Math.min(cleanPreviewStartRow.value + cleanPreviewRows.value, cleanedData.value.length))
const cleanPreviewColumnsList = computed(() => {
  if (!cleanedData.value || cleanedData.value.length === 0) return []
  return Object.keys(cleanedData.value[0]).slice(0, 8)
})
const paginatedCleanPreview = computed(() => cleanedData.value.slice(cleanPreviewStartRow.value, cleanPreviewEndRow.value))

// Report Preview
const reportPreviewColumns = computed(() => {
  if (!cleanedData.value || cleanedData.value.length === 0) return []
  return Object.keys(cleanedData.value[0]).slice(0, 6)
})
const reportDataPreview = computed(() => cleanedData.value.slice(0, 5))

// File size
const fileSize = computed(() => {
  if (!uploadedFile.value) return ''
  const bytes = uploadedFile.value.size
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(2) + ' MB'
})

// Column validation
const hasRequiredColumn = (col) => {
  if (!rawData.value || rawData.value.length === 0) return false
  return Object.keys(rawData.value[0]).includes(col)
}

const missingColumns = computed(() => {
  if (!rawData.value || rawData.value.length === 0) return []
  return requiredColumns.value.filter(col => !hasRequiredColumn(col))
})

// Cleaning stats
const cleaningStats = ref({ totalRows: 0, validRows: 0, removedRows: 0, fixedMissing: 0 })

// Expanded calculations with all backend fields
const calculations = ref({ 
  totalValue: 0, 
  instrumentCount: 0, 
  avgRate: 0, 
  avgCouponRate: 0, 
  avgDiscountRate: 0,
  weightedAvgRate: 0,
  totalInterest: 0,
  weightedAvgCoupon: 0,
  totalAnnualIncome: 0,
  avgYTM: 0,
  weightedAvgDiscount: 0,
  totalDiscount: 0,
  effectiveYield: 0,
  // Money Market
  interestEarned: 0,
  annualYield: 0,
  maturityValue: 0,
  avgYield: 0,
  effectiveAnnualRate: 0,
  avgDaysToMaturity: 0,
  totalInterestIncome: 0,
  portfolioYield: 0,
  totalPrincipal: 0,
  // T-Bills
  discountYield: 0,
  bondEquivalentYield: 0,
  moneyMarketYield: 0,
  pricePer100: 0,
  totalPurchasePrice: 0,
  avgInvestment: 0,
  holdingPeriodYield: 0,
  annualizedYield: 0,
  // Bonds
  annualCouponPayment: 0,
  currentYield: 0,
  yieldToMaturity: 0,
  yieldCurveRate: 0,
  yieldSpread: 0,
  duration: 0,
  modifiedDuration: 0,
  convexity: 0,
  macaulayDuration: 0,
  priceVolatility: 0,
  creditSpread: 0,
  realYield: 0,
  nominalYield: 0
})

const calculationsList = computed(() => {
  const list = []
  if (instrumentType.value === 'money-market') {
    list.push({ name: 'Total Portfolio Value', value: `$${calculations.value.totalValue?.toLocaleString() || 0}`, unit: 'USD' })
    list.push({ name: 'Average Interest Rate', value: calculations.value.avgRate || 0, unit: '%' })
    list.push({ name: 'Number of Instruments', value: calculations.value.instrumentCount || 0, unit: 'items' })
  } 
  else if (instrumentType.value === 'bonds') {
    list.push({ name: 'Total Portfolio Value', value: `$${calculations.value.totalValue?.toLocaleString() || 0}`, unit: 'USD' })
    list.push({ name: 'Average Coupon Rate', value: calculations.value.avgCouponRate || 0, unit: '%' })
    list.push({ name: 'Number of Bonds', value: calculations.value.instrumentCount || 0, unit: 'issues' })
  }
  else if (instrumentType.value === 'tbills') {
    list.push({ name: 'Total Portfolio Value', value: `$${calculations.value.totalValue?.toLocaleString() || 0}`, unit: 'USD' })
    list.push({ name: 'Average Discount Rate', value: calculations.value.avgDiscountRate || 0, unit: '%' })
    list.push({ name: 'Number of T-Bills', value: calculations.value.instrumentCount || 0, unit: 'securities' })
  }
  return list
})

const hasData = computed(() => rawData.value && rawData.value.length > 0)
const hasCleanedData = computed(() => cleanedData.value && cleanedData.value.length > 0)

// Helper functions for highlighting
function hasInvalidData(row) {
  if (!row) return false
  return requiredColumns.value.some(col => !row[col] || row[col] === '' || row[col] === null)
}

function isInvalidValue(value) {
  return !value || value === '' || value === null
}

function wasFixed(row, col) {
  const key = `${row[Object.keys(row)[0]] || row.Date || row.Instrument}_${col}`
  return fixedValuesTracker.value.has(key)
}

// Navigation
function goToDashboard() { 
  router.push('/dashboard') 
}

function switchTab(tab) { 
  activeTab.value = tab 
}

// File handling functions with persistence
function handleFileUpload(event) {
  const file = event.target.files[0]
  if (file) {
    uploadedFile.value = file
    readFileData(file)
  }
}

function handleDrop(event) {
  const file = event.dataTransfer.files[0]
  if (file) {
    uploadedFile.value = file
    readFileData(file)
  }
}

async function readFileData(file) {
  const extension = file.name.split('.').pop().toLowerCase()
  let data = []
  
  try {
    if (extension === 'csv') {
      const text = await file.text()
      const lines = text.split('\n')
      const headers = lines[0].split(',').map(h => h.trim())
      data = lines.slice(1)
        .filter(line => line.trim())
        .map(line => {
          const values = line.split(',')
          const row = {}
          headers.forEach((h, i) => {
            row[h] = values[i] ? values[i].trim() : ''
          })
          return row
        })
    } else {
      const buffer = await file.arrayBuffer()
      const workbook = XLSX.read(buffer)
      const worksheet = workbook.Sheets[workbook.SheetNames[0]]
      data = XLSX.utils.sheet_to_json(worksheet)
    }
    
    rawData.value = data
    
    // Save to localStorage for persistence
    localStorage.setItem(`${instrumentType.value}_raw_data`, JSON.stringify(data))
    localStorage.setItem(`${instrumentType.value}_uploaded_file_name`, file.name)
    
    // Auto-check if mapping is needed
    await nextTick()
    if (missingColumns.value.length > 0) {
      autoMatchColumns()
    }
  } catch (error) {
    console.error('Error reading file:', error)
    alert('Error reading file. Please check the file format.')
  }
}

function removeFile() { 
  uploadedFile.value = null
  rawData.value = []
  cleanedData.value = []
  fixedValuesTracker.value.clear()
  // Clear from localStorage
  localStorage.removeItem(`${instrumentType.value}_raw_data`)
  localStorage.removeItem(`${instrumentType.value}_cleaned_data`)
  localStorage.removeItem(`${instrumentType.value}_uploaded_file_name`)
  if (fileInput.value) {
    fileInput.value.value = ''
  }
}

function formatCellValue(value) {
  if (value === undefined || value === null) return '-'
  if (typeof value === 'number') return value.toFixed(2)
  if (typeof value === 'string' && value.length > 30) return value.substring(0, 27) + '...'
  return value
}

// Excel Review Functions
function openExcelReview(data, title) {
  console.log('openExcelReview called with:', data, title)
  
  if (!data || data.length === 0) {
    if (cleanedData.value && cleanedData.value.length > 0) {
      data = cleanedData.value
      title = title || 'Cleaned Data'
    } else if (rawData.value && rawData.value.length > 0) {
      data = rawData.value
      title = title || 'Uploaded Data'
    } else {
      alert('No data to review. Please upload a file first.')
      return
    }
  }
  
  if (!data || data.length === 0) {
    alert('No data to review. Please upload a file first.')
    return
  }
  
  excelData.value = data
  excelColumns.value = Object.keys(data[0] || {})
  excelDialogTitle.value = title || 'Data Review'
  showExcelDialog.value = true
}

function closeExcelDialog() {
  showExcelDialog.value = false
  excelData.value = []
  excelColumns.value = []
}

function exportToCSV() {
  if (!excelData.value || excelData.value.length === 0) return
  
  const headers = excelColumns.value
  const rows = excelData.value.map(row => 
    headers.map(h => `"${String(row[h] || '').replace(/"/g, '""')}"`).join(',')
  )
  const csvContent = [headers.join(','), ...rows].join('\n')
  
  const blob = new Blob([csvContent], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${excelDialogTitle.value.toLowerCase().replace(/ /g, '_')}_${Date.now()}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

function exportToJSON() {
  if (!excelData.value || excelData.value.length === 0) return
  
  const jsonContent = JSON.stringify(excelData.value, null, 2)
  const blob = new Blob([jsonContent], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${excelDialogTitle.value.toLowerCase().replace(/ /g, '_')}_${Date.now()}.json`
  a.click()
  URL.revokeObjectURL(url)
}

// Column matching functions
function autoMatchColumns() {
  if (!rawData.value || rawData.value.length === 0) return
  fileColumns.value = Object.keys(rawData.value[0])
  const newMapping = {}
  
  requiredColumns.value.forEach(reqCol => {
    const variations = columnVariations[reqCol] || [reqCol]
    let matchedColumn = null
    
    matchedColumn = fileColumns.value.find(col => col === reqCol)
    if (!matchedColumn) {
      matchedColumn = fileColumns.value.find(col => col.toLowerCase() === reqCol.toLowerCase())
    }
    if (!matchedColumn) {
      matchedColumn = fileColumns.value.find(col => {
        return variations.some(variation => 
          col.toLowerCase().includes(variation.toLowerCase()) ||
          variation.toLowerCase().includes(col.toLowerCase())
        )
      })
    }
    newMapping[reqCol] = matchedColumn || null
  })
  
  columnMapping.value = newMapping
  showMappingDialog.value = true
}

function applyColumnMapping() {
  if (!rawData.value || rawData.value.length === 0) return
  
  const mappedData = rawData.value.map(row => {
    const newRow = {}
    requiredColumns.value.forEach(reqCol => {
      const sourceCol = columnMapping.value[reqCol]
      if (sourceCol && row[sourceCol] !== undefined) {
        newRow[reqCol] = row[sourceCol]
      } else {
        newRow[reqCol] = null
      }
    })
    return newRow
  })
  
  rawData.value = mappedData
  // Save mapped data to localStorage
  localStorage.setItem(`${instrumentType.value}_raw_data`, JSON.stringify(mappedData))
  showMappingDialog.value = false
  alert('Columns mapped successfully!')
}

async function uploadData() {
  if (!uploadedFile.value) return
  
  if (rawData.value.length > 0 && missingColumns.value.length === 0) {
    activeTab.value = 'cleaning'
    updateStatus('upload', true)
  } else if (rawData.value.length > 0 && missingColumns.value.length > 0) {
    alert('Please map the missing columns first using the "Map Columns" button.')
  }
}

function cleanData() {
  if (!rawData.value || rawData.value.length === 0) return
  
  fixedValuesTracker.value.clear()
  const required = requiredColumns.value
  let cleaned = rawData.value.filter(row => required.every(col => row[col] !== undefined && row[col] !== null && row[col] !== ''))

  let missingCount = 0
  cleaned = cleaned.map((row, rowIndex) => {
    required.forEach(col => {
      if (!row[col] || row[col] === '') {
        missingCount++
        const key = `${row[Object.keys(row)[0]] || row.Date || row.Instrument || rowIndex}_${col}`
        if (col.includes('Rate') || col.includes('Yield')) {
          row[col] = 0
          fixedValuesTracker.value.set(key, true)
        }
        else if (col.includes('Amount') || col.includes('Value')) {
          row[col] = 0
          fixedValuesTracker.value.set(key, true)
        }
        else {
          row[col] = 'N/A'
          fixedValuesTracker.value.set(key, true)
        }
      }
    })
    
    if (row.Rate) row.Rate = parseFloat(row.Rate) || 0
    if (row.Amount) row.Amount = parseFloat(row.Amount) || 0
    if (row.CouponRate) row.CouponRate = parseFloat(row.CouponRate) || 0
    if (row.FaceValue) row.FaceValue = parseFloat(row.FaceValue) || 0
    if (row.Yield) row.Yield = parseFloat(row.Yield) || 0
    if (row.DiscountRate) row.DiscountRate = parseFloat(row.DiscountRate) || 0
    return row
  })

  cleanedData.value = cleaned
  cleaningStats.value = {
    totalRows: rawData.value.length,
    validRows: cleaned.length,
    removedRows: rawData.value.length - cleaned.length,
    fixedMissing: missingCount
  }

  calculateMetrics()
  updateStatus('cleaning', true)
}

function calculateMetrics() {
  if (!cleanedData.value || cleanedData.value.length === 0) return
  
  let totalValue = 0, totalRate = 0, weightedSum = 0
  
  if (instrumentType.value === 'money-market') {
    totalValue = cleanedData.value.reduce((sum, row) => sum + (row.Amount || 0), 0)
    totalRate = cleanedData.value.reduce((sum, row) => sum + (row.Rate || 0), 0)
    weightedSum = cleanedData.value.reduce((sum, row) => sum + ((row.Rate || 0) * (row.Amount || 0)), 0)
    const avgRateVal = totalRate / cleanedData.value.length
    
    calculations.value = {
      totalValue, 
      instrumentCount: cleanedData.value.length,
      avgRate: avgRateVal.toFixed(2),
      avgCouponRate: 0,
      avgDiscountRate: 0,
      weightedAvgRate: totalValue > 0 ? (weightedSum / totalValue).toFixed(2) : 0,
      totalInterest: (totalValue * avgRateVal / 100).toFixed(2),
      weightedAvgCoupon: 0,
      totalAnnualIncome: 0,
      avgYTM: 0,
      weightedAvgDiscount: 0,
      totalDiscount: 0,
      effectiveYield: 0,
      interestEarned: (totalValue * avgRateVal / 100 * 90 / 365).toFixed(2),
      annualYield: ((Math.pow(1 + avgRateVal / 100, 365 / 90) - 1) * 100).toFixed(2),
      maturityValue: (totalValue + totalValue * avgRateVal / 100 * 90 / 365).toFixed(2),
      avgYield: avgRateVal.toFixed(2),
      effectiveAnnualRate: ((Math.pow(1 + avgRateVal / 100, 1) - 1) * 100).toFixed(2),
      avgDaysToMaturity: 90,
      totalInterestIncome: (totalValue * avgRateVal / 100).toFixed(2),
      portfolioYield: avgRateVal.toFixed(2),
      totalPrincipal: totalValue,
      discountYield: 0,
      bondEquivalentYield: 0,
      moneyMarketYield: 0,
      pricePer100: 0,
      totalPurchasePrice: 0,
      avgInvestment: 0,
      holdingPeriodYield: 0,
      annualizedYield: 0,
      annualCouponPayment: 0,
      currentYield: 0,
      yieldToMaturity: 0,
      yieldCurveRate: 0,
      yieldSpread: 0,
      duration: 0,
      modifiedDuration: 0,
      convexity: 0,
      macaulayDuration: 0,
      priceVolatility: 0,
      creditSpread: 0,
      realYield: 0,
      nominalYield: 0
    }
  } 
  else if (instrumentType.value === 'bonds') {
    totalValue = cleanedData.value.reduce((sum, row) => sum + (row.FaceValue || 0), 0)
    totalRate = cleanedData.value.reduce((sum, row) => sum + (row.CouponRate || 0), 0)
    weightedSum = cleanedData.value.reduce((sum, row) => sum + ((row.CouponRate || 0) * (row.FaceValue || 0)), 0)
    const totalYield = cleanedData.value.reduce((sum, row) => sum + (row.Yield || 0), 0)
    const avgCouponVal = totalRate / cleanedData.value.length
    const avgYieldVal = totalYield / cleanedData.value.length
    
    calculations.value = {
      totalValue, 
      instrumentCount: cleanedData.value.length,
      avgRate: 0,
      avgCouponRate: avgCouponVal.toFixed(2),
      avgDiscountRate: 0,
      weightedAvgRate: 0,
      totalInterest: 0,
      weightedAvgCoupon: totalValue > 0 ? (weightedSum / totalValue).toFixed(2) : 0,
      totalAnnualIncome: (totalValue * avgCouponVal / 100).toFixed(2),
      avgYTM: avgYieldVal.toFixed(2),
      weightedAvgDiscount: 0,
      totalDiscount: 0,
      effectiveYield: 0,
      interestEarned: 0,
      annualYield: 0,
      maturityValue: 0,
      avgYield: 0,
      effectiveAnnualRate: 0,
      avgDaysToMaturity: 0,
      totalInterestIncome: 0,
      portfolioYield: 0,
      totalPrincipal: 0,
      discountYield: 0,
      bondEquivalentYield: 0,
      moneyMarketYield: 0,
      pricePer100: 0,
      totalPurchasePrice: 0,
      avgInvestment: 0,
      holdingPeriodYield: 0,
      annualizedYield: 0,
      annualCouponPayment: (totalValue * avgCouponVal / 100).toFixed(2),
      currentYield: avgCouponVal.toFixed(2),
      yieldToMaturity: avgYieldVal.toFixed(2),
      yieldCurveRate: (avgYieldVal + 0.5).toFixed(2),
      yieldSpread: (avgYieldVal - 3.5).toFixed(2),
      duration: (10 * 0.7).toFixed(2),
      modifiedDuration: ((10 * 0.7) / (1 + avgYieldVal / 100)).toFixed(2),
      convexity: ((10 * 0.7) * (10 * 0.7 + 1) / Math.pow(1 + avgYieldVal / 100, 2)).toFixed(2),
      macaulayDuration: (10 * 0.7).toFixed(2),
      priceVolatility: ((10 * 0.7) / (1 + avgYieldVal / 100)).toFixed(2),
      creditSpread: (avgYieldVal - 4.5).toFixed(2),
      realYield: (avgYieldVal - 2.5).toFixed(2),
      nominalYield: avgYieldVal.toFixed(2)
    }
  }
  else if (instrumentType.value === 'tbills') {
    totalValue = cleanedData.value.reduce((sum, row) => sum + (row.FaceValue || 0), 0)
    totalRate = cleanedData.value.reduce((sum, row) => sum + (row.DiscountRate || 0), 0)
    weightedSum = cleanedData.value.reduce((sum, row) => sum + ((row.DiscountRate || 0) * (row.FaceValue || 0)), 0)
    const avgDiscountVal = totalRate / cleanedData.value.length
    const discountAmount = totalValue * (avgDiscountVal / 100) * 91 / 360
    const price = totalValue - discountAmount
    
    calculations.value = {
      totalValue, 
      instrumentCount: cleanedData.value.length,
      avgRate: 0,
      avgCouponRate: 0,
      avgDiscountRate: avgDiscountVal.toFixed(2),
      weightedAvgRate: 0,
      totalInterest: 0,
      weightedAvgCoupon: 0,
      totalAnnualIncome: 0,
      avgYTM: 0,
      weightedAvgDiscount: totalValue > 0 ? (weightedSum / totalValue).toFixed(2) : 0,
      totalDiscount: discountAmount.toFixed(2),
      effectiveYield: ((Math.pow(1 + discountAmount / price, 365 / 91) - 1) * 100).toFixed(2),
      interestEarned: 0,
      annualYield: 0,
      maturityValue: 0,
      avgYield: 0,
      effectiveAnnualRate: 0,
      avgDaysToMaturity: 91,
      totalInterestIncome: 0,
      portfolioYield: 0,
      totalPrincipal: 0,
      discountYield: ((discountAmount / totalValue) * (360 / 91) * 100).toFixed(2),
      bondEquivalentYield: ((discountAmount / price) * (365 / 91) * 100).toFixed(2),
      moneyMarketYield: ((discountAmount / price) * (360 / 91) * 100).toFixed(2),
      pricePer100: (100 * (1 - (avgDiscountVal / 100) * (91 / 360))).toFixed(2),
      totalPurchasePrice: price.toFixed(2),
      avgInvestment: (price / cleanedData.value.length).toFixed(2),
      holdingPeriodYield: ((discountAmount / price) * 100).toFixed(2),
      annualizedYield: ((discountAmount / price) * (365 / 91) * 100).toFixed(2),
      annualCouponPayment: 0,
      currentYield: 0,
      yieldToMaturity: 0,
      yieldCurveRate: 0,
      yieldSpread: 0,
      duration: 0,
      modifiedDuration: 0,
      convexity: 0,
      macaulayDuration: 0,
      priceVolatility: 0,
      creditSpread: 0,
      realYield: 0,
      nominalYield: 0
    }
  }
  
  // Save cleaned data to localStorage for persistence
  localStorage.setItem(`${instrumentType.value}_cleaned_data`, JSON.stringify(cleanedData.value))
}

function downloadReport() {
  if (!cleanedData.value || cleanedData.value.length === 0) return
  
  const report = {
    instrument: instrumentName.value,
    date: new Date().toLocaleString(),
    calculations: calculations.value,
    cleaningStats: cleaningStats.value,
    totalRecords: cleanedData.value.length,
    data: cleanedData.value.slice(0, 100)
  }
  const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${instrumentType.value}_report_${Date.now()}.json`
  a.click()
  URL.revokeObjectURL(url)
  updateStatus('reports', true)
}

function saveToSummary() {
  const session = JSON.parse(localStorage.getItem('active_session') || '{}')
  const summary = JSON.parse(localStorage.getItem('summary_totals') || '{}')
  summary[instrumentType.value] = calculations.value.totalValue
  localStorage.setItem('summary_totals', JSON.stringify(summary))
  
  if (session.id) {
    if (!session.instrumentData) session.instrumentData = {}
    session.instrumentData[instrumentType.value] = {
      totalValue: calculations.value.totalValue,
      count: calculations.value.instrumentCount,
      completed: true
    }
    session.completedInstruments = session.completedInstruments || {}
    session.completedInstruments[instrumentType.value] = true
    localStorage.setItem('active_session', JSON.stringify(session))
    
    const sessions = JSON.parse(localStorage.getItem('sessions_list') || '[]')
    const index = sessions.findIndex(s => s.id === session.id)
    if (index !== -1) sessions[index] = session
    localStorage.setItem('sessions_list', JSON.stringify(sessions))
  }
  
  updateStatus('summary', true)
  alert('Saved to Summary!')
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

// Load persisted data on mount
onMounted(() => {
  // Load raw data if exists
  const savedRawData = localStorage.getItem(`${instrumentType.value}_raw_data`)
  if (savedRawData) {
    rawData.value = JSON.parse(savedRawData)
    const savedFileName = localStorage.getItem(`${instrumentType.value}_uploaded_file_name`)
    if (savedFileName) {
      uploadedFile.value = { name: savedFileName, size: 0 }
    }
    fileColumns.value = Object.keys(rawData.value[0] || {})
  }
  
  // Load cleaned data if exists
  const savedCleanedData = localStorage.getItem(`${instrumentType.value}_cleaned_data`)
  if (savedCleanedData) {
    cleanedData.value = JSON.parse(savedCleanedData)
    calculateMetrics()
  }
})

// File input ref
const fileInput = ref(null)
</script>

<style scoped>
/* All styles remain exactly the same as your original */
.instrument-page {
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 25px;
  padding: 0 10px;
}

.header-left h1 {
  color: #0B2044;
  font-size: 28px;
  font-weight: 700;
  margin-bottom: 5px;
}

.header-left p {
  color: #666;
  font-size: 14px;
}

.step-indicator {
  background: white;
  padding: 8px 16px;
  border-radius: 20px;
  font-size: 13px;
  color: #0B2044;
  font-weight: 600;
}

.progress-bar-container {
  margin-bottom: 30px;
  padding: 0 10px;
}

.progress-steps {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: white;
  padding: 20px;
  border-radius: 16px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.05);
}

.progress-step {
  flex: 1;
  text-align: center;
  cursor: pointer;
}

.step-circle {
  width: 36px;
  height: 36px;
  background: #e0e0e0;
  color: #999;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  transition: all 0.3s;
}

.progress-step.active .step-circle {
  background: #0B2044;
  color: white;
  box-shadow: 0 0 0 4px rgba(11,32,68,0.2);
}

.progress-step.completed .step-circle {
  background: #4CAF50;
  color: white;
}

.step-label {
  font-size: 11px;
  color: #999;
  margin-top: 8px;
}

.progress-step.active .step-label {
  color: #0B2044;
  font-weight: 600;
}

.content-card {
  margin-bottom: 20px;
}

.upload-area {
  border: 2px dashed #ccc;
  border-radius: 12px;
  padding: 50px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s;
}

.upload-area:hover {
  border-color: #0B2044;
  background: #f8f9ff;
}

.browse-link {
  color: #0B2044;
  cursor: pointer;
  font-weight: 600;
}

.file-info {
  margin-top: 20px;
  padding: 12px;
  background: #f5f5f5;
  border-radius: 8px;
  display: flex;
  align-items: center;
  gap: 10px;
}

.file-size {
  font-size: 11px;
  color: #999;
  margin-left: auto;
}

.remove-btn {
  margin-left: auto;
  background: none;
  border: none;
  font-size: 20px;
  cursor: pointer;
  color: #f44336;
}

/* Excel Review Button Styles */
.btn-review-excel {
  background: #4CAF50;
  color: white;
  border: none;
  padding: 6px 12px;
  border-radius: 6px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  margin-left: 10px;
  transition: all 0.2s;
}

.btn-review-excel:hover:not(:disabled) {
  background: #45a049;
  transform: translateY(-1px);
}

.btn-review-excel:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Map Columns Button Styles */
.btn-mapping {
  background: #FF9800;
  color: white;
  border: none;
  padding: 6px 12px;
  border-radius: 6px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  margin-left: 10px;
  transition: all 0.2s;
}

.btn-mapping:hover:not(:disabled) {
  background: #F57C00;
  transform: translateY(-1px);
}

.btn-mapping:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-review-excel-small {
  background: #2196F3;
  color: white;
  border: none;
  padding: 4px 10px;
  border-radius: 6px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  transition: all 0.2s;
}

.btn-review-excel-small:hover {
  background: #0b7dda;
}

/* Excel Dialog Styles */
.excel-dialog-title {
  background: #0B2044;
  color: white;
  padding: 16px 24px;
}

.dialog-title-content {
  display: flex;
  align-items: center;
  gap: 12px;
}

.btn-close-dialog {
  background: transparent;
  border: none;
  color: white;
  cursor: pointer;
  padding: 8px;
  border-radius: 50%;
  transition: all 0.2s;
}

.btn-close-dialog:hover {
  background: rgba(255,255,255,0.1);
}

.excel-dialog-content {
  padding: 0;
  height: calc(100vh - 140px);
}

.excel-full-view {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.excel-toolbar-full {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #f5f5f5;
  border-bottom: 1px solid #e0e0e0;
  flex-wrap: wrap;
  gap: 10px;
}

.excel-info {
  font-size: 13px;
  color: #666;
}

.excel-export-buttons {
  display: flex;
  gap: 10px;
}

.btn-excel-export {
  background: white;
  border: 1px solid #ddd;
  padding: 6px 12px;
  border-radius: 6px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  transition: all 0.2s;
}

.btn-excel-export:hover {
  background: #0B2044;
  color: white;
  border-color: #0B2044;
}

.excel-full-table-wrapper {
  flex: 1;
  overflow: auto;
}

.excel-full-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

.excel-full-table th,
.excel-full-table td {
  padding: 8px 12px;
  border: 1px solid #e0e0e0;
  text-align: left;
}

.excel-full-table th {
  background: #f5f5f5;
  font-weight: 600;
  position: sticky;
  top: 0;
  z-index: 10;
}

.sticky-col {
  position: sticky;
  left: 0;
  background: #f5f5f5;
  font-weight: 600;
}

.sticky-header {
  position: sticky;
  top: 0;
  background: #f5f5f5;
  z-index: 10;
}

.excel-preview-section, .preview-toolbar {
  margin-top: 20px;
}

.preview-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 15px;
  background: #f5f5f5;
  border-radius: 8px;
  flex-wrap: wrap;
  gap: 10px;
}

.preview-info {
  font-size: 12px;
  color: #666;
}

.preview-controls {
  display: flex;
  align-items: center;
  gap: 10px;
}

.preview-btn {
  background: white;
  border: 1px solid #ddd;
  padding: 4px 12px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 12px;
}

.preview-btn:hover:not(:disabled) {
  background: #0B2044;
  color: white;
}

.preview-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.row-number {
  background: #f8f9ff;
  font-weight: 500;
  color: #0B2044;
  width: 50px;
  text-align: center;
}

.mapping-grid {
  display: flex;
  flex-direction: column;
  gap: 15px;
  margin: 20px 0;
}

.mapping-row {
  display: flex;
  align-items: center;
  gap: 15px;
}

.required-label {
  width: 120px;
  font-weight: 600;
  color: #0B2044;
}

.mapping-select {
  flex: 1;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 14px;
}

.mapping-hint {
  margin-top: 15px;
  padding: 10px;
  background: #f8f9ff;
  border-radius: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
  color: #666;
}

.required-columns {
  margin: 20px 0;
}

.columns-list {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 10px;
}

.column-badge {
  background: #e8ecf1;
  padding: 6px 12px;
  border-radius: 20px;
  font-size: 12px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.missing-column {
  background: #FFEBEE;
  color: #c62828;
}

.warning-message {
  margin-top: 10px;
  padding: 8px 12px;
  background: #FFF3E0;
  border-radius: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #E65100;
}

.btn-warning {
  background: #FF9800;
  color: white;
  border: none;
  padding: 12px 20px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}

.cleaning-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  margin-bottom: 30px;
}

.stat-card {
  text-align: center;
  padding: 20px;
  background: linear-gradient(135deg, #f8f9ff, #fff);
  border-radius: 12px;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #0B2044;
}

.stat-label {
  font-size: 12px;
  color: #666;
  margin-top: 8px;
}

.cleaning-actions {
  text-align: center;
  margin: 20px 0;
}

.highlight-box {
  background: #e8f5e9;
  padding: 12px;
  border-radius: 8px;
  margin-bottom: 20px;
}

.calculations-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
  margin-bottom: 30px;
}

.calculation-card {
  padding: 25px;
  background: linear-gradient(135deg, #f8f9ff, #fff);
  border-radius: 12px;
  text-align: center;
  border: 1px solid rgba(11,32,68,0.1);
}

.calc-name {
  font-size: 14px;
  color: #666;
  margin-bottom: 10px;
}

.calc-value {
  font-size: 28px;
  font-weight: 700;
  color: #0B2044;
  margin-bottom: 5px;
}

.calc-unit {
  font-size: 12px;
  color: #999;
}

.visualization-placeholder {
  text-align: center;
  padding: 60px;
  background: #f8f9ff;
  border-radius: 12px;
}

.visualization-placeholder h3 {
  color: #0B2044;
  margin: 20px 0 10px;
}

.visualization-placeholder p {
  color: #666;
  margin-bottom: 20px;
}

.placeholder-note {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: #e3f2fd;
  border-radius: 20px;
  font-size: 12px;
  color: #0B2044;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
  margin-bottom: 30px;
}

.summary-section {
  padding: 20px;
  background: #f8f9ff;
  border-radius: 12px;
}

.summary-section h3 {
  color: #0B2044;
  margin-bottom: 15px;
}

.summary-section p {
  margin: 8px 0;
  color: #555;
}

.summary-progress {
  margin: 20px 0;
  padding: 15px;
  background: #f8f9ff;
  border-radius: 12px;
}

.progress-bar {
  height: 8px;
  background: #e0e0e0;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 10px;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #4CAF50, #2E7D32);
  border-radius: 4px;
}

.progress-text {
  font-size: 12px;
  color: #4CAF50;
  font-weight: 500;
  margin: 0;
}

.report-options {
  padding: 20px;
}

.report-preview {
  background: #f8f9ff;
  padding: 20px;
  border-radius: 12px;
  margin-bottom: 20px;
}

.report-content {
  margin-top: 15px;
  padding: 15px;
  background: white;
  border-radius: 8px;
}

.report-data-preview {
  margin-top: 20px;
}

.report-data-preview h5 {
  color: #0B2044;
  margin-bottom: 10px;
}

.report-actions {
  display: flex;
  gap: 15px;
  justify-content: center;
  margin-bottom: 20px;
}

.table-wrapper {
  overflow-x: auto;
  margin: 15px 0;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th, .data-table td {
  padding: 10px;
  text-align: left;
  border-bottom: 1px solid #e0e0e0;
}

.data-table th {
  background: #f5f5f5;
  font-weight: 600;
  color: #0B2044;
}

.empty-state {
  text-align: center;
  padding: 60px;
  color: #999;
}

.empty-state p {
  margin: 20px 0;
}

.navigation-buttons {
  display: flex;
  gap: 15px;
  justify-content: center;
  margin-top: 30px;
  padding-top: 20px;
  border-top: 1px solid #e0e0e0;
}

.btn-primary {
  background: linear-gradient(135deg, #0B2044, #1E88E5);
  color: white;
  border: none;
  padding: 12px 28px;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 15px rgba(11,32,68,0.3);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  background: white;
  color: #0B2044;
  border: 2px solid #0B2044;
  padding: 12px 28px;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
}

.btn-secondary:hover {
  background: #0B2044;
  color: white;
  transform: translateY(-2px);
}

.btn-success {
  background: linear-gradient(135deg, #4CAF50, #2E7D32);
  color: white;
  border: none;
  padding: 12px 28px;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
}

.btn-success:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 15px rgba(76, 175, 80, 0.3);
}

/* New styles for highlighting */
.invalid-row {
  background-color: #ffebee !important;
}

.invalid-cell {
  background-color: #ffcdd2 !important;
  color: #c62828 !important;
  font-weight: 500;
}

.fixed-value {
  background-color: #c8e6c9 !important;
  position: relative;
}

.fixed-badge {
  display: inline-block;
  margin-left: 5px;
  color: #4caf50;
  font-weight: bold;
  cursor: help;
}

.legend {
  margin-bottom: 15px;
  padding: 10px;
  background: #f5f5f5;
  border-radius: 8px;
  display: flex;
  gap: 20px;
}

.legend-badge {
  padding: 4px 12px;
  border-radius: 4px;
  font-size: 12px;
}

.invalid-row-badge {
  background-color: #ffebee;
  color: #c62828;
  border: 1px solid #ef9a9a;
}

.invalid-cell-badge {
  background-color: #ffcdd2;
  color: #c62828;
  border: 1px solid #ef9a9a;
}

.detailed-calculations {
  margin-top: 20px;
  padding: 15px;
  background: #f8f9ff;
  border-radius: 12px;
}

.detailed-calculations h4 {
  color: #0B2044;
  margin-bottom: 15px;
  padding-bottom: 8px;
  border-bottom: 2px solid #0B2044;
}

.detail-item {
  display: flex;
  justify-content: space-between;
  padding: 8px 12px;
  margin: 8px 0;
  background: white;
  border-radius: 8px;
}

.detail-label {
  font-weight: 600;
  color: #555;
}

.detail-value {
  font-weight: 700;
  color: #0B2044;
}

.success-text {
  color: #4CAF50;
  font-weight: 600;
}
</style>