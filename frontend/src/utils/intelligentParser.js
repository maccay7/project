import * as XLSX from 'xlsx';
import api from '@/services/api';

/**
 * Enhanced intelligent parser – tries backend first, then client‑side fallback.
 * @param {File} file - The Excel file to parse.
 * @param {string} instrumentType - 'money-market', 'bonds', or 'tbills'.
 * @returns {Promise<Object>} { data: Array, warnings: Array, metadata: Object }
 */
export async function parseExcel(file, instrumentType) {
    // First, try the backend parser
    try {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('instrument_type', instrumentType);
        const response = await api.dataAPI.parseExcel(formData);
        if (response.success) {
            return { data: response.data, warnings: [], metadata: { source: 'backend' } };
        }
    } catch (e) {
        console.warn('Backend parser failed, falling back to client parser:', e);
    }

    // Fallback: original client‑side parser (your full code)
    return clientParser(file, instrumentType);
}

// ----- Your original client‑side parser (unchanged, included below) -----
// (I've kept it exactly as you wrote it – nothing cut)
export async function clientParser(file, instrumentType) {
    const buffer = await file.arrayBuffer();
    const workbook = XLSX.read(buffer, { type: 'array', cellDates: false, cellNF: false, cellText: false, defval: '' });

    const warnings = [];
    const metadata = {
        sheets: workbook.SheetNames.length,
        sheetNames: workbook.SheetNames,
        instrumentType,
        parseDate: new Date().toISOString()
    };

    // Define required fields per instrument with validation rules
    const fieldMap = {
        'money-market': {
            required: ['Principal', 'InterestRate', 'DaysToMaturity'],
            optional: ['InvestmentAmount', 'IssueDate', 'MaturityDate'],
            keywords: {
                'Principal': ['principal', 'principal amount', 'investment', 'amount', 'notional'],
                'InterestRate': ['interest rate', 'rate', 'interest', 'coupon', 'annual rate'],
                'InvestmentAmount': ['investment amount', 'investment', 'amount', 'principal'],
                'DaysToMaturity': ['days to maturity', 'maturity days', 'term', 'tenor', 'duration'],
                'IssueDate': ['issue date', 'effective date', 'start date', 'trade date'],
                'MaturityDate': ['maturity date', 'maturity', 'due date', 'end date']
            }
        },
        'bonds': {
            required: ['CouponRate', 'FaceValue', 'MaturityDate'],
            optional: ['CouponFrequency', 'Yield', 'SettlementDate', 'IssueDate', 'Price'],
            keywords: {
                'CouponRate': ['coupon rate', 'coupon', 'rate', 'interest rate'],
                'CouponFrequency': ['coupon frequency', 'frequency', 'payment frequency', 'pmt freq'],
                'FaceValue': ['face value', 'face', 'par value', 'par', 'amount', 'principal', 'notional'],
                'Yield': ['yield', 'ytm', 'yield to maturity', 'return', 'irr'],
                'SettlementDate': ['settlement date', 'settlement', 'trade date'],
                'MaturityDate': ['maturity date', 'maturity', 'due date', 'end date'],
                'IssueDate': ['issue date', 'effective date', 'start date'],
                'Price': ['price', 'clean price', 'dirty price', 'market price']
            }
        },
        'tbills': {
            required: ['FaceValue', 'DiscountRate', 'DaysToMaturity'],
            optional: ['PurchasePrice', 'RedemptionValue', 'IssueDate', 'MaturityDate'],
            keywords: {
                'FaceValue': ['face value', 'face', 'par value', 'par', 'amount', 'principal', 'notional'],
                'DiscountRate': ['discount rate', 'discount', 'rate', 'bank discount'],
                'PurchasePrice': ['purchase price', 'purchase', 'price', 'buy price', 'bid price'],
                'RedemptionValue': ['redemption value', 'redemption', 'maturity value'],
                'DaysToMaturity': ['days to maturity', 'maturity days', 'term', 'tenor', 'duration'],
                'IssueDate': ['issue date', 'effective date', 'start date', 'trade date'],
                'MaturityDate': ['maturity date', 'maturity', 'due date', 'end date']
            }
        }
    };

    const fieldConfig = fieldMap[instrumentType] || fieldMap['money-market'];
    const requiredFields = fieldConfig.required;
    const optionalFields = fieldConfig.optional;
    const allFields = [...requiredFields, ...optionalFields];
    const keywords = fieldConfig.keywords;

    // Helper to find a keyword in a string
    function findKeyword(cellValue, field) {
        if (!cellValue || typeof cellValue !== 'string') return false;
        const lower = cellValue.toLowerCase().trim();
        const kw = keywords[field] || [];
        return kw.some(k => lower.includes(k));
    }

    // Extract all key-value pairs from a sheet with enhanced positioning
    function extractKeyValuePairs(sheet) {
        const range = XLSX.utils.decode_range(sheet['!ref'] || 'A1');
        const pairs = [];
        const merged = sheet['!merges'] || [];

        // Helper to get merged cell value
        function getMergedValue(row, col) {
            for (const merge of merged) {
                const s = merge.s, e = merge.e;
                if (row >= s.r && row <= e.r && col >= s.c && col <= e.c) {
                    const addr = XLSX.utils.encode_cell({ r: s.r, c: s.c });
                    return sheet[addr] ? sheet[addr].v : '';
                }
            }
            return null;
        }

        // Helper to get cell value with merge support
        function getCellValue(row, col) {
            const addr = XLSX.utils.encode_cell({ r: row, c: col });
            const cell = sheet[addr];
            if (!cell) return null;
            const mergedVal = getMergedValue(row, col);
            return mergedVal !== null ? mergedVal : cell.v;
        }

        // Iterate all cells
        for (let R = range.s.r; R <= range.e.r; R++) {
            for (let C = range.s.c; C <= range.e.c; C++) {
                const value = getCellValue(R, C);
                if (value === undefined || value === null || value === '') continue;

                // Try to match this cell as a label
                let label = String(value).trim();
                // If label is a number, skip as label
                if (!isNaN(parseFloat(label)) && label !== '') continue;

                // Find which field this label corresponds to
                let matchedField = null;
                for (const field of allFields) {
                    if (findKeyword(label, field)) {
                        matchedField = field;
                        break;
                    }
                }
                if (!matchedField) continue;

                // Extract value from adjacent cells (right, below, or within merged area)
                let extractedValue = null;
                let extractionSource = '';

                // Check right cell
                const rightVal = getCellValue(R, C + 1);
                if (rightVal !== undefined && rightVal !== null && rightVal !== '') {
                    extractedValue = rightVal;
                    extractionSource = 'right';
                }
                // Check below cell
                if (extractedValue === null) {
                    const belowVal = getCellValue(R + 1, C);
                    if (belowVal !== undefined && belowVal !== null && belowVal !== '') {
                        extractedValue = belowVal;
                        extractionSource = 'below';
                    }
                }
                // Check left cell (for value:label format)
                if (extractedValue === null) {
                    const leftVal = getCellValue(R, C - 1);
                    if (leftVal !== undefined && leftVal !== null && leftVal !== '') {
                        extractedValue = leftVal;
                        extractionSource = 'left';
                    }
                }
                // Check above cell
                if (extractedValue === null) {
                    const aboveVal = getCellValue(R - 1, C);
                    if (aboveVal !== undefined && aboveVal !== null && aboveVal !== '') {
                        extractedValue = aboveVal;
                        extractionSource = 'above';
                    }
                }

                if (extractedValue !== null) {
                    pairs.push({ field: matchedField, value: extractedValue, row: R, col: C, source: extractionSource });
                }
            }
        }
        return pairs;
    }

    // Try to detect tabular data: look for rows that have many non-empty cells
    function detectTableData(sheet) {
        const range = XLSX.utils.decode_range(sheet['!ref'] || 'A1');
        const data = XLSX.utils.sheet_to_json(sheet, { header: 1, defval: '' });
        if (data.length === 0) return null;

        // Find row with most non-empty cells (potential header or data row)
        let maxCount = 0;
        let headerRowIndex = -1;
        for (let i = 0; i < data.length; i++) {
            const row = data[i];
            const count = row.filter(cell => cell !== '' && cell !== null && cell !== undefined).length;
            if (count > maxCount) {
                maxCount = count;
                headerRowIndex = i;
            }
        }
        if (maxCount < 2) return null; // no table

        // Assume header row is the one with most non-empty cells
        const headerRow = data[headerRowIndex];
        const tableRows = [];
        for (let i = headerRowIndex + 1; i < data.length; i++) {
            const row = data[i];
            if (row.some(cell => cell !== '' && cell !== null && cell !== undefined)) {
                const obj = {};
                for (let j = 0; j < headerRow.length; j++) {
                    const header = headerRow[j] || `col${j}`;
                    obj[String(header).trim()] = row[j] !== undefined ? row[j] : '';
                }
                tableRows.push(obj);
            }
        }
        return { headers: headerRow, rows: tableRows, headerRowIndex };
    }

    // Validate a row against required fields
    function validateRow(row, rowIndex) {
        const missing = [];
        const invalid = [];

        for (const field of requiredFields) {
            const value = row[field];
            if (value === undefined || value === null || value === '' || value === 0) {
                missing.push(field);
            }
        }

        // Type validation
        if (row.Principal && isNaN(parseFloat(row.Principal))) {
            invalid.push({ field: 'Principal', error: 'Must be a number' });
        }
        if (row.FaceValue && isNaN(parseFloat(row.FaceValue))) {
            invalid.push({ field: 'FaceValue', error: 'Must be a number' });
        }
        if (row.InterestRate && isNaN(parseFloat(row.InterestRate))) {
            invalid.push({ field: 'InterestRate', error: 'Must be a number' });
        }
        if (row.CouponRate && isNaN(parseFloat(row.CouponRate))) {
            invalid.push({ field: 'CouponRate', error: 'Must be a number' });
        }
        if (row.DiscountRate && isNaN(parseFloat(row.DiscountRate))) {
            invalid.push({ field: 'DiscountRate', error: 'Must be a number' });
        }
        if (row.DaysToMaturity && isNaN(parseFloat(row.DaysToMaturity))) {
            invalid.push({ field: 'DaysToMaturity', error: 'Must be a number' });
        }

        return { valid: missing.length === 0 && invalid.length === 0, missing, invalid };
    }

    // Process each sheet
    const allRows = [];
    for (const sheetName of workbook.SheetNames) {
        const sheet = workbook.Sheets[sheetName];
        // First try to detect a table
        const tableResult = detectTableData(sheet);
        if (tableResult && tableResult.rows.length > 0) {
            // We have tabular data; map columns to required fields based on headers
            const headers = tableResult.headers;
            const columnMap = {};
            for (const field of allFields) {
                // Find column whose header matches keywords
                for (const header of headers) {
                    if (findKeyword(header, field)) {
                        columnMap[field] = header;
                        break;
                    }
                }
            }
            // If we have at least one mapped column, use this table
            if (Object.keys(columnMap).length > 0) {
                const mappedRows = tableResult.rows.map((row, idx) => {
                    const newRow = {};
                    for (const field of allFields) {
                        const col = columnMap[field];
                        if (col) {
                            newRow[field] = row[col] !== undefined ? row[col] : '';
                        } else {
                            newRow[field] = '';
                        }
                    }
                    // Validate row
                    const validation = validateRow(newRow, idx);
                    if (!validation.valid) {
                        warnings.push(`Sheet "${sheetName}", Row ${idx + 1}: Missing fields: ${validation.missing.join(', ')}`);
                    }
                    return newRow;
                });
                allRows.push(...mappedRows);
                metadata.primarySheet = sheetName;
                metadata.parseMethod = 'table';
                continue; // processed this sheet
            }
        }

        // If no table, use key-value extraction and try to group into rows
        const pairs = extractKeyValuePairs(sheet);
        if (pairs.length === 0) continue;

        // Try to group pairs into rows by proximity (same row or same block)
        const rowGroups = {};
        for (const p of pairs) {
            const rowKey = p.row;
            if (!rowGroups[rowKey]) rowGroups[rowKey] = {};
            rowGroups[rowKey][p.field] = p.value;
        }
        // Convert to array of rows
        for (const rowKey in rowGroups) {
            const row = rowGroups[rowKey];
            // Fill missing fields with empty string
            const fullRow = {};
            for (const f of allFields) {
                fullRow[f] = row[f] !== undefined ? row[f] : '';
            }
            // Validate row
            const validation = validateRow(fullRow, parseInt(rowKey));
            if (!validation.valid) {
                warnings.push(`Sheet "${sheetName}", Row ${parseInt(rowKey) + 1}: Missing fields: ${validation.missing.join(', ')}`);
            }
            allRows.push(fullRow);
        }
        if (allRows.length > 0 && !metadata.primarySheet) {
            metadata.primarySheet = sheetName;
            metadata.parseMethod = 'key-value';
        }
    }

    // If still no rows, fallback to simple sheet_to_json
    if (allRows.length === 0) {
        warnings.push('No structured data found, falling back to simple JSON extraction');
        const firstSheet = workbook.Sheets[workbook.SheetNames[0]];
        const json = XLSX.utils.sheet_to_json(firstSheet, { defval: '' });
        if (json.length > 0) {
            // Map columns based on headers
            const headers = Object.keys(json[0]);
            const columnMap = {};
            for (const field of allFields) {
                for (const header of headers) {
                    if (findKeyword(header, field)) {
                        columnMap[field] = header;
                        break;
                    }
                }
            }
            const mappedRows = json.map((row, idx) => {
                const newRow = {};
                for (const field of allFields) {
                    const col = columnMap[field];
                    newRow[field] = col ? row[col] : '';
                }
                const validation = validateRow(newRow, idx);
                if (!validation.valid) {
                    warnings.push(`Row ${idx + 1}: Missing fields: ${validation.missing.join(', ')}`);
                }
                return newRow;
            });
            allRows.push(...mappedRows);
            metadata.parseMethod = 'fallback-json';
        }
    }

    metadata.rowsExtracted = allRows.length;
    metadata.warningsCount = warnings.length;

    return { data: allRows, warnings, metadata };
}