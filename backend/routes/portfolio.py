import json
from flask import request, jsonify
from utils.db import get_db
from pages.calculations_details import calculate_data


def create_portfolio_table():
    conn = get_db()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS portfolios (
                id INT AUTO_INCREMENT PRIMARY KEY,
                session_id VARCHAR(64) NOT NULL,
                instrument_type VARCHAR(50),
                total_value DECIMAL(20, 2),
                instrument_count INT,
                avg_rate DECIMAL(10, 4),
                weighted_avg_rate DECIMAL(10, 4),
                total_interest DECIMAL(20, 2),
                total_principal DECIMAL(20, 2),
                avg_days_to_maturity DECIMAL(10, 2),
                portfolio_data JSON,
                calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_session_id (session_id)
            )
        """)
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error creating portfolios table: {e}")
        conn.close()
        return False


def aggregate_portfolio(data, instrument_type):
    if not data or not isinstance(data, list):
        return {
            'total_value': 0,
            'instrument_count': 0,
            'avg_rate': 0,
            'weighted_avg_rate': 0,
            'total_interest': 0,
            'total_principal': 0,
            'avg_days_to_maturity': 0
        }
    
    calculation_result = calculate_data(data, instrument_type)
    
    return {
        'total_value': calculation_result.get('totalValue', 0),
        'instrument_count': calculation_result.get('instrumentCount', 0),
        'avg_rate': calculation_result.get('avgRate', 0),
        'weighted_avg_rate': calculation_result.get('weightedAvgRate', 0),
        'total_interest': calculation_result.get('totalInterest', 0),
        'total_principal': calculation_result.get('totalPrincipal', 0),
        'avg_days_to_maturity': calculation_result.get('avgDaysToMaturity', 0),
        'calculations': calculation_result.get('calculations', [])
    }


def save_portfolio(session_id, instrument_type, portfolio_data):
    conn = get_db()
    if not conn:
        return None
    try:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO portfolios 
               (session_id, instrument_type, total_value, instrument_count, avg_rate, weighted_avg_rate, 
                total_interest, total_principal, avg_days_to_maturity, portfolio_data) 
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
               ON DUPLICATE KEY UPDATE
               total_value = VALUES(total_value),
               instrument_count = VALUES(instrument_count),
               avg_rate = VALUES(avg_rate),
               weighted_avg_rate = VALUES(weighted_avg_rate),
               total_interest = VALUES(total_interest),
               total_principal = VALUES(total_principal),
               avg_days_to_maturity = VALUES(avg_days_to_maturity),
               portfolio_data = VALUES(portfolio_data),
               calculated_at = CURRENT_TIMESTAMP""",
            (session_id, instrument_type, portfolio_data['total_value'], portfolio_data['instrument_count'],
             portfolio_data['avg_rate'], portfolio_data['weighted_avg_rate'], portfolio_data['total_interest'],
             portfolio_data['total_principal'], portfolio_data['avg_days_to_maturity'], json.dumps(portfolio_data))
        )
        conn.commit()
        portfolio_id = cursor.lastrowid
        cursor.close()
        conn.close()
        return portfolio_id
    except Exception as e:
        print(f"Error saving portfolio: {e}")
        conn.close()
        return None


def portfolio_routes(app):
    create_portfolio_table()
    
    @app.route('/api/portfolio/aggregate', methods=['POST', 'OPTIONS'])
    def aggregate_portfolio_endpoint():
        if request.method == 'OPTIONS':
            return '', 200
        
        payload = request.get_json() or {}
        data = payload.get('data', [])
        instrument_type = payload.get('instrument_type', 'tbills')
        
        portfolio_summary = aggregate_portfolio(data, instrument_type)
        
        return jsonify({
            'success': True,
            'data': portfolio_summary
        })
    
    @app.route('/api/portfolio/session/<session_id>', methods=['GET', 'OPTIONS'])
    def get_session_portfolio(session_id):
        if request.method == 'OPTIONS':
            return '', 200
        
        conn = get_db()
        if not conn:
            return jsonify({'success': False, 'message': 'Database error'}), 500
        
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM portfolios WHERE session_id = %s", (session_id,))
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            
            portfolios = []
            for row in rows:
                portfolios.append({
                    'id': row['id'],
                    'session_id': row['session_id'],
                    'instrument_type': row['instrument_type'],
                    'total_value': float(row['total_value']),
                    'instrument_count': row['instrument_count'],
                    'avg_rate': float(row['avg_rate']),
                    'weighted_avg_rate': float(row['weighted_avg_rate']),
                    'total_interest': float(row['total_interest']),
                    'total_principal': float(row['total_principal']),
                    'avg_days_to_maturity': float(row['avg_days_to_maturity']),
                    'portfolio_data': json.loads(row['portfolio_data']) if row['portfolio_data'] else None,
                    'calculated_at': row['calculated_at'].isoformat() if row['calculated_at'] else None
                })
            
            return jsonify({
                'success': True,
                'data': portfolios
            })
            
        except Exception as e:
            conn.close()
            return jsonify({'success': False, 'message': str(e)}), 500
    
    @app.route('/api/portfolio/save', methods=['POST', 'OPTIONS'])
    def save_portfolio_endpoint():
        if request.method == 'OPTIONS':
            return '', 200
        
        payload = request.get_json() or {}
        session_id = payload.get('session_id')
        instrument_type = payload.get('instrument_type')
        data = payload.get('data', [])
        
        if not session_id or not instrument_type:
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400
        
        portfolio_summary = aggregate_portfolio(data, instrument_type)
        portfolio_id = save_portfolio(session_id, instrument_type, portfolio_summary)
        
        if portfolio_id:
            return jsonify({
                'success': True,
                'data': {
                    'portfolio_id': portfolio_id,
                    'summary': portfolio_summary
                }
            })
        else:
            return jsonify({'success': False, 'message': 'Failed to save portfolio'}), 500
    
    @app.route('/api/portfolio/export', methods=['POST', 'OPTIONS'])
    def export_summary():
        if request.method == 'OPTIONS':
            return '', 200
        
        import pandas as pd
        
        data = request.get_json()
        
        if not data or 'summary' not in data:
            return jsonify({'error': 'No summary data provided'}), 400
        
        df = pd.DataFrame(data['summary'])
        file_path = 'portfolio_summary.xlsx'
        df.to_excel(file_path, index=False)
        
        return jsonify({
            'message': 'Export successful',
            'file': file_path,
            'rows': len(df)
        })