import json
from flask import request, jsonify
from utils.db import get_db

DEFAULT_CONFIGS = {
    'money-market': {
        'label': 'Money Market',
        'description': 'Short-term debt instruments including treasury bills, commercial paper',
        'defaultMaturity': '1Y',
        'maturityOptions': [
            { 'value': '1M', 'label': '1 Month' },
            { 'value': '3M', 'label': '3 Months' },
            { 'value': '6M', 'label': '6 Months' },
            { 'value': '1Y', 'label': '1 Year' }
        ],
        'rateLabel': 'Avg Interest Rate',
        'primaryRateKey': 'avgRate',
        'weightedRateKey': 'weightedAvgRate',
        'fredDefault': '1Y',
        'calculationFields': [
            { 'key': 'weightedAvgRate', 'label': 'Weighted Average Rate', 'suffix': '%' },
            { 'key': 'totalInterest', 'label': 'Total Interest (Annualized)', 'prefix': '$' },
            { 'key': 'interestEarned', 'label': 'Interest Earned', 'prefix': '$' },
            { 'key': 'annualYield', 'label': 'Annual Yield', 'suffix': '%' },
            { 'key': 'effectiveAnnualRate', 'label': 'Effective Annual Rate', 'suffix': '%' },
            { 'key': 'avgDaysToMaturity', 'label': 'Average Days to Maturity', 'suffix': ' days' },
            { 'key': 'totalPrincipal', 'label': 'Total Principal', 'prefix': '$' }
        ],
        'summaryMetrics': [
            { 'key': 'totalValue', 'label': 'Total Portfolio Value', 'prefix': '$' },
            { 'key': 'instrumentCount', 'label': 'Number of Instruments' },
            { 'key': 'avgRate', 'label': 'Average Interest Rate', 'suffix': '%' },
            { 'key': 'weightedAvgRate', 'label': 'Weighted Average Rate', 'suffix': '%' }
        ],
        'required_columns': [
            'Date', 'Instrument', 'Rate', 'Amount', 'MaturityDate',
            'Principal', 'InterestRate', 'DiscountRate', 'Price', 'FaceValue'
        ],
        'column_variations': {
            'Date': ['Date', 'date', 'DATE', 'Transaction Date', 'Trade Date', 'Settlement Date', 'Value Date', 'Start Date', 'Issue Date'],
            'Instrument': ['Instrument', 'instrument', 'INSTRUMENT', 'Security', 'Security Name', 'Name', 'Description', 'Asset'],
            'Rate': ['Rate', 'rate', 'RATE', 'Interest Rate', 'Coupon Rate', 'Discount Rate', 'Yield', 'Return', 'APR'],
            'Amount': ['Amount', 'amount', 'AMOUNT', 'Face Value', 'FaceValue', 'Value', 'Price', 'Notional', 'Principal', 'Investment'],
            'MaturityDate': ['MaturityDate', 'Maturity Date', 'Maturity', 'Matures', 'End Date', 'Due Date', 'Expiry Date'],
            'DaysToMaturity': ['DaysToMaturity', 'Days to Maturity', 'Tenor', 'Days', 'Term', 'Duration Days'],
            'Principal': ['Principal', 'Amount', 'Face Value', 'Notional', 'Investment Amount'],
            'InterestRate': ['InterestRate', 'Interest Rate', 'Rate', 'Coupon', 'Yield'],
            'DiscountRate': ['DiscountRate', 'Discount Rate', 'discount', 'Rate'],
            'Price': ['Price', 'price', 'PRICE', 'Market Price', 'Current Price', 'Purchase Price', 'Bid Price', 'Ask Price'],
            'FaceValue': ['FaceValue', 'Face Value', 'Face', 'Value', 'Amount', 'Principal', 'Par Value', 'Nominal']
        },
        'workflow_steps': [
            {'tab': 'upload', 'name': 'Upload', 'order': 1},
            {'tab': 'cleaning', 'name': 'Clean', 'order': 2},
            {'tab': 'calculations', 'name': 'Calculate', 'order': 3},
            {'tab': 'visualizations', 'name': 'Visualize', 'order': 4},
            {'tab': 'summary', 'name': 'Summary', 'order': 5},
            {'tab': 'reports', 'name': 'Report', 'order': 6}
        ]
    },
    'bonds': {
        'label': 'Bonds',
        'description': 'Fixed income securities including government and corporate bonds',
        'defaultMaturity': '10Y',
        'maturityOptions': [
            { 'value': '2Y', 'label': '2 Years' },
            { 'value': '5Y', 'label': '5 Years' },
            { 'value': '10Y', 'label': '10 Years' },
            { 'value': '30Y', 'label': '30 Years' }
        ],
        'rateLabel': 'Avg Coupon Rate',
        'primaryRateKey': 'avgCouponRate',
        'weightedRateKey': 'weightedAvgCoupon',
        'fredDefault': '10Y',
        'calculationFields': [
            { 'key': 'weightedAvgCoupon', 'label': 'Weighted Average Coupon', 'suffix': '%' },
            { 'key': 'totalAnnualIncome', 'label': 'Total Annual Income', 'prefix': '$' },
            { 'key': 'avgYTM', 'label': 'Average Yield to Maturity', 'suffix': '%' },
            { 'key': 'duration', 'label': 'Duration (years)' }
        ],
        'summaryMetrics': [
            { 'key': 'totalValue', 'label': 'Total Portfolio Value', 'prefix': '$' },
            { 'key': 'instrumentCount', 'label': 'Number of Instruments' },
            { 'key': 'avgCouponRate', 'label': 'Average Coupon Rate', 'suffix': '%' },
            { 'key': 'weightedAvgCoupon', 'label': 'Weighted Average Coupon', 'suffix': '%' },
            { 'key': 'avgYTM', 'label': 'Average YTM', 'suffix': '%' },
            { 'key': 'duration', 'label': 'Duration (years)' }
        ],
        'required_columns': [
            'Date', 'BondName', 'CouponRate', 'FaceValue', 'Yield', 'MaturityDate',
            'IssueDate', 'Frequency', 'Price', 'AccruedInterest', 'RedemptionValue'
        ],
        'column_variations': {
            'Date': ['Date', 'date', 'DATE', 'Transaction Date', 'Trade Date', 'Settlement Date', 'Value Date'],
            'BondName': ['BondName', 'Bond Name', 'bond', 'BOND', 'Security', 'Issuer', 'Description', 'Name'],
            'CouponRate': ['CouponRate', 'Coupon Rate', 'coupon', 'Rate', 'Interest Rate', 'Annual Coupon'],
            'FaceValue': ['FaceValue', 'Face Value', 'Face', 'Value', 'Amount', 'Principal', 'Par Value', 'Nominal'],
            'Yield': ['Yield', 'yield', 'YIELD', 'Yield to Maturity', 'YTM', 'Return', 'Effective Yield'],
            'MaturityDate': ['MaturityDate', 'Maturity Date', 'Maturity', 'Matures', 'End Date', 'Due Date'],
            'IssueDate': ['IssueDate', 'Issue Date', 'Issued', 'Issuance Date', 'Start Date'],
            'Frequency': ['Frequency', 'Payment Frequency', 'Coupon Frequency', 'Period', 'SemiAnnual', 'Quarterly', 'Annual'],
            'Price': ['Price', 'price', 'PRICE', 'Market Price', 'Current Price', 'Purchase Price'],
            'AccruedInterest': ['AccruedInterest', 'Accrued Interest', 'Accrued', 'Interest Accrued'],
            'DaysToMaturity': ['DaysToMaturity', 'Days to Maturity', 'Tenor', 'Days', 'Term'],
            'RedemptionValue': ['RedemptionValue', 'Redemption Value', 'Call Value', 'Maturity Value']
        },
        'workflow_steps': [
            {'tab': 'upload', 'name': 'Upload', 'order': 1},
            {'tab': 'cleaning', 'name': 'Clean', 'order': 2},
            {'tab': 'calculations', 'name': 'Calculate', 'order': 3},
            {'tab': 'visualizations', 'name': 'Visualize', 'order': 4},
            {'tab': 'summary', 'name': 'Summary', 'order': 5},
            {'tab': 'reports', 'name': 'Report', 'order': 6}
        ]
    },
    'tbills': {
        'label': 'T-Bills',
        'description': 'Treasury bills - short-term government securities',
        'defaultMaturity': '13W',
        'maturityOptions': [
            { 'value': '4W', 'label': '4 Weeks' },
            { 'value': '13W', 'label': '13 Weeks' },
            { 'value': '26W', 'label': '26 Weeks' },
            { 'value': '52W', 'label': '52 Weeks' }
        ],
        'rateLabel': 'Avg Discount Rate',
        'primaryRateKey': 'avgDiscountRate',
        'weightedRateKey': 'weightedAvgDiscount',
        'fredDefault': '13W',
        'calculationFields': [
            { 'key': 'weightedAvgDiscount', 'label': 'Weighted Average Discount', 'suffix': '%' },
            { 'key': 'totalDiscount', 'label': 'Total Discount', 'prefix': '$' },
            { 'key': 'effectiveYield', 'label': 'Effective Yield', 'suffix': '%' },
            { 'key': 'bondEquivalentYield', 'label': 'Bond Equivalent Yield', 'suffix': '%' },
            { 'key': 'totalPurchasePrice', 'label': 'Total Purchase Price', 'prefix': '$' },
            { 'key': 'avgInvestment', 'label': 'Average Investment', 'prefix': '$' },
            { 'key': 'holdingPeriodYield', 'label': 'Holding Period Yield', 'suffix': '%' },
            { 'key': 'annualizedYield', 'label': 'Annualized Yield', 'suffix': '%' },
            { 'key': 'pricePer100', 'label': 'Price per 100', 'prefix': '$' }
        ],
        'summaryMetrics': [
            { 'key': 'totalValue', 'label': 'Total Portfolio Value', 'prefix': '$' },
            { 'key': 'instrumentCount', 'label': 'Number of Instruments' },
            { 'key': 'avgDiscountRate', 'label': 'Average Discount Rate', 'suffix': '%' },
            { 'key': 'weightedAvgDiscount', 'label': 'Weighted Average Discount', 'suffix': '%' },
            { 'key': 'effectiveYield', 'label': 'Effective Yield', 'suffix': '%' },
            { 'key': 'bondEquivalentYield', 'label': 'Bond Equivalent Yield', 'suffix': '%' }
        ],
        'required_columns': [
            'Date', 'TBillName', 'DiscountRate', 'FaceValue', 'MaturityDate',
            'IssueDate', 'Price', 'Yield'
        ],
        'column_variations': {
            'Date': ['Date', 'date', 'DATE', 'Transaction Date', 'Trade Date', 'Settlement Date'],
            'TBillName': ['TBillName', 'T-Bill Name', 'TBill', 'T Bill', 'Security', 'Instrument', 'Treasury Bill'],
            'DiscountRate': ['DiscountRate', 'Discount Rate', 'discount', 'Rate'],
            'FaceValue': ['FaceValue', 'Face Value', 'Face', 'Value', 'Amount', 'Principal', 'Par Value'],
            'MaturityDate': ['MaturityDate', 'Maturity Date', 'Maturity', 'Matures', 'End Date', 'Due Date'],
            'DaysToMaturity': ['DaysToMaturity', 'Days to Maturity', 'Tenor', 'Days', 'Term'],
            'IssueDate': ['IssueDate', 'Issue Date', 'Issued', 'Issuance Date', 'Start Date'],
            'Price': ['Price', 'price', 'PRICE', 'Market Price', 'Current Price', 'Purchase Price'],
            'Yield': ['Yield', 'yield', 'YIELD', 'Yield to Maturity', 'YTM', 'Return']
        },
        'workflow_steps': [
            {'tab': 'upload', 'name': 'Upload', 'order': 1},
            {'tab': 'cleaning', 'name': 'Clean', 'order': 2},
            {'tab': 'calculations', 'name': 'Calculate', 'order': 3},
            {'tab': 'visualizations', 'name': 'Visualize', 'order': 4},
            {'tab': 'summary', 'name': 'Summary', 'order': 5},
            {'tab': 'reports', 'name': 'Report', 'order': 6}
        ]
    }
}


def _parse_json_field(val, default=None):
    if val is None:
        return default if default is not None else {}
    if isinstance(val, (dict, list)):
        return val
    try:
        return json.loads(val)
    except Exception:
        return default if default is not None else {}


def instrument_config_routes(app):
    @app.before_request
    def ensure_instrument_config_table():
        conn = get_db()
        if not conn:
            return
        try:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS instrument_configs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    instrument_type VARCHAR(64) UNIQUE NOT NULL,
                    required_columns JSON NOT NULL,
                    column_variations JSON NOT NULL,
                    workflow_steps JSON NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            ''')
            for inst_type, cfg in DEFAULT_CONFIGS.items():
                cursor.execute(
                    'SELECT id FROM instrument_configs WHERE instrument_type = %s LIMIT 1',
                    (inst_type,)
                )
                if not cursor.fetchone():
                    cursor.execute('''
                        INSERT INTO instrument_configs
                        (instrument_type, required_columns, column_variations, workflow_steps)
                        VALUES (%s, %s, %s, %s)
                    ''', (
                        inst_type,
                        json.dumps(cfg['required_columns']),
                        json.dumps(cfg['column_variations']),
                        json.dumps(cfg['workflow_steps'])
                    ))
                else:
                    cursor.execute('''
                        UPDATE instrument_configs
                        SET required_columns = %s, column_variations = %s, workflow_steps = %s
                        WHERE instrument_type = %s
                    ''', (
                        json.dumps(cfg['required_columns']),
                        json.dumps(cfg['column_variations']),
                        json.dumps(cfg['workflow_steps']),
                        inst_type
                    ))
            conn.commit()
            cursor.close()
        except Exception as e:
            print(f'Instrument config schema error: {e}')
        finally:
            conn.close()

    @app.route('/api/instrument-config', methods=['GET', 'OPTIONS'])
    def list_instrument_configs():
        if request.method == 'OPTIONS':
            return '', 200
        conn = get_db()
        if not conn:
            return jsonify({'success': False, 'message': 'DB error'}), 500
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT instrument_type, required_columns, column_variations, workflow_steps
                FROM instrument_configs ORDER BY instrument_type
            ''')
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            data = []
            for row in rows:
                data.append({
                    'instrument_type': row['instrument_type'],
                    'required_columns': _parse_json_field(row['required_columns'], []),
                    'column_variations': _parse_json_field(row['column_variations'], {}),
                    'workflow_steps': _parse_json_field(row['workflow_steps'], [])
                })
            return jsonify({'success': True, 'data': data})
        except Exception as e:
            print(f'List instrument config error: {e}')
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/instrument-config/<instrument_type>', methods=['GET', 'OPTIONS'])
    def get_instrument_config(instrument_type):
        if request.method == 'OPTIONS':
            return '', 200
        conn = get_db()
        if not conn:
            return jsonify({'success': False, 'message': 'DB error'}), 500
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT instrument_type, required_columns, column_variations, workflow_steps
                FROM instrument_configs WHERE instrument_type = %s LIMIT 1
            ''', (instrument_type,))
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            if not row:
                fallback = DEFAULT_CONFIGS.get(instrument_type)
                if fallback:
                    return jsonify({'success': True, 'data': {
                        'instrument_type': instrument_type,
                        **fallback
                    }})
                return jsonify({'success': False, 'message': 'Config not found'}), 404
            return jsonify({'success': True, 'data': {
                'instrument_type': row['instrument_type'],
                'required_columns': _parse_json_field(row['required_columns'], []),
                'column_variations': _parse_json_field(row['column_variations'], {}),
                'workflow_steps': _parse_json_field(row['workflow_steps'], [])
            }})
        except Exception as e:
            print(f'Get instrument config error: {e}')
            return jsonify({'success': False, 'message': str(e)}), 500