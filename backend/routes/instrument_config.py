import json
from flask import request, jsonify
from utils.db import get_db

# Default configs seeded into DB on first access
DEFAULT_CONFIGS = {
    'money-market': {
        'required_columns': [
            'Date', 'Instrument', 'Rate', 'Amount', 'MaturityDate', 'DaysToMaturity',
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
        'required_columns': [
            'Date', 'BondName', 'CouponRate', 'FaceValue', 'Yield', 'MaturityDate',
            'IssueDate', 'Frequency', 'Price', 'AccruedInterest', 'DaysToMaturity', 'RedemptionValue'
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
        'required_columns': [
            'Date', 'TBillName', 'DiscountRate', 'FaceValue', 'MaturityDate',
            'DaysToMaturity', 'IssueDate', 'Price', 'Yield'
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
