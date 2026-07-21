import * as XLSX from 'xlsx';
import api from '@/services/api';

/**
 * Enhanced intelligent parser – tries backend first, then client‑side fallback.
 */
export async function parseExcel(file, instrumentType) {
    try {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('instrument_type', instrumentType);
        formData.append('return_full_workbook', 'true');
        const response = await api.dataAPI.parseExcel(formData);
        if (response.success) {
            return {
                data: response.data,
                warnings: response.data.warnings || [],
                metadata: response.data.metadata || { source: 'backend' },
                sheets: response.data.sheets || []
            };
        }
    } catch (e) {
        console.warn('Backend parser failed, falling back to client parser:', e);
    }
    return clientParser(file, instrumentType);
}

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
                'CouponFrequency': ['coupon frequency', 'frequency', 'payment frequency'],
                'FaceValue': ['face value', 'face', 'par value', 'par', 'amount', 'principal', 'notional'],
                'Yield': ['yield', 'ytm', 'yield to maturity', 'return'],
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
                'PurchasePrice': ['purchase price', 'purchase', 'price', 'buy price'],
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

    function findKeyword(cellValue, field) {
        if (!cellValue || typeof cellValue !== 'string') return false;
        const lower = cellValue.toLowerCase().trim();
        const kw = keywords[field] || [];
        return kw.some(k => lower.includes(k));
    }

    // Enhanced: extract key-value pairs from entire sheet
    function extractKeyValuePairs(sheet) {
        const range = XLSX.utils.decode_range(sheet['!ref'] || 'A1');
        const pairs = [];
        const merged = sheet['!merges'] || [];

        function getMergedValue(row, col) {
            for (const merge of merged) {
                const s = merge.s, e = merge.e;
                if (row >= s.r && row <= e.r && col >= s.c && col <= e.c) {
                    const addr = XLSX.utils.encode_cell({ r: s.r, c: s.c });
                    return sheet[addr] ? sheet[addr].v : null;
                }
            }
            return null;
        }

        function getCellValue(row, col) {
            const addr = XLSX.utils.encode_cell({ r: row, c: col });
            const cell = sheet[addr];
            if (!cell) return null;
            const mergedVal = getMergedValue(row, col);
            return mergedVal !== null ? mergedVal : cell.v;
        }

        // Scan all cells
        for (let R = range.s.r; R <= range.e.r; R++) {
            for (let C = range.s.c; C <= range.e.c; C++) {
                const value = getCellValue(R, C);
                if (value === undefined || value === null || value === '') continue;
                const label = String(value).trim();
                if (!label) continue;
                // Check if it's a label (contains text, not just number)
                if (!isNaN(parseFloat(label)) && label !== '') continue;

                // Match against field keywords
                let matchedField = null;
                for (const field of allFields) {
                    if (findKeyword(label, field)) {
                        matchedField = field;
                        break;
                    }
                }
                if (!matchedField) continue;

                // Extract value from adjacent cells (right, below, left, above)
                let extractedValue = null;
                const offsets = [[0,1,'right'], [1,0,'below'], [0,-1,'left'], [-1,0,'above']];
                for (const [dr, dc] of offsets) {
                    const val = getCellValue(R + dr, C + dc);
                    if (val !== undefined && val !== null && val !== '') {
                        extractedValue = val;
                        break;
                    }
                }
                if (extractedValue !== null) {
                    pairs.push({ field: matchedField, value: extractedValue });
                }
            }
        }
        return pairs;
    }

    // Detect table (existing function)
    function detectTableData(sheet) {
        const range = XLSX.utils.decode_range(sheet['!ref'] || 'A1');
        const data = XLSX.utils.sheet_to_json(sheet, { header: 1, defval: '' });
        if (data.length === 0) return null;
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
        if (maxCount < 2) return null;
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
        return { headers: headerRow, rows: tableRows };
    }

    // Process each sheet
    const allRows = [];
    for (const sheetName of workbook.SheetNames) {
        const sheet = workbook.Sheets[sheetName];
        // First try table
        const tableResult = detectTableData(sheet);
        if (tableResult && tableResult.rows.length > 0) {
            const headers = tableResult.headers;
            const columnMap = {};
            for (const field of allFields) {
                for (const header of headers) {
                    if (findKeyword(header, field)) {
                        columnMap[field] = header;
                        break;
                    }
                }
            }
            if (Object.keys(columnMap).length > 0) {
                const mappedRows = tableResult.rows.map((row, idx) => {
                    const newRow = {};
                    for (const field of allFields) {
                        const col = columnMap[field];
                        newRow[field] = col ? row[col] : '';
                    }
                    return newRow;
                });
                allRows.push(...mappedRows);
                metadata.primarySheet = sheetName;
                metadata.parseMethod = 'table';
                continue;
            }
        }

        // No table: extract key-value pairs
        const pairs = extractKeyValuePairs(sheet);
        if (pairs.length > 0) {
            const row = {};
            for (const p of pairs) {
                row[p.field] = p.value;
            }
            // Fill missing fields
            const fullRow = {};
            for (const f of allFields) {
                fullRow[f] = row[f] !== undefined ? row[f] : '';
            }
            allRows.push(fullRow);
            if (!metadata.primarySheet) {
                metadata.primarySheet = sheetName;
                metadata.parseMethod = 'key-value';
            }
        }
    }

    // Fallback to simple JSON
    if (allRows.length === 0) {
        warnings.push('No structured data found, falling back to simple JSON extraction');
        const firstSheet = workbook.Sheets[workbook.SheetNames[0]];
        const json = XLSX.utils.sheet_to_json(firstSheet, { defval: '' });
        if (json.length > 0) {
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
            const mappedRows = json.map(row => {
                const newRow = {};
                for (const field of allFields) {
                    const col = columnMap[field];
                    newRow[field] = col ? row[col] : '';
                }
                return newRow;
            });
            allRows.push(...mappedRows);
            metadata.parseMethod = 'fallback-json';
        }
    }

    metadata.rowsExtracted = allRows.length;
    return { data: allRows, warnings, metadata };
}