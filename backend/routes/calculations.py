import json
from flask import request, jsonify
from pages.calculations_details import calculate_data
from utils.db import get_db
from utils.fred_config import attach_fred_to_calculation, get_market_benchmark
from datetime import datetime


def normalize_instrument_type(instrument_type):
    if not instrument_type:
        return 'tbills'
    normalized = instrument_type.lower().replace('_', '-').strip()
    mapping = {
        'treasury-bills': 'tbills',
        'treasury_bills': 'tbills',
        'treasury bills': 'tbills',
        'tbills': 'tbills',
        't-bills': 'tbills',
        'bonds': 'bonds',
        'money-market': 'money-market',
        'money_market': 'money-market',
        'money market': 'money-market'
    }
    return mapping.get(normalized, normalized)


def save_calculation(instrument_type, input_data, result_data, dataset_id=None, session_id=None):
    """Save calculation results to database and update session instrument_count."""
    conn = get_db()
    if not conn:
        print("⚠️ Database connection failed – calculation not saved")
        return
    try:
        cursor = conn.cursor()
        # Ensure calculations table exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS calculations (
                id INT AUTO_INCREMENT PRIMARY KEY,
                instrument_type VARCHAR(64) NOT NULL,
                dataset_id VARCHAR(64),
                session_id VARCHAR(64),
                input_data JSON,
                result_data JSON,
                calculation_status ENUM('pending', 'processing', 'completed', 'failed') DEFAULT 'completed',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP NULL,
                INDEX (instrument_type),
                INDEX (dataset_id),
                INDEX (session_id),
                INDEX (calculation_status),
                INDEX (created_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        
        # Also ensure a versions table for version tracking
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS version_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                session_id VARCHAR(64) NOT NULL,
                version_number INT NOT NULL,
                instrument_type VARCHAR(64) NOT NULL,
                change_summary TEXT,
                dataset_snapshot JSON,
                mapping_snapshot JSON,
                calculation_snapshot JSON,
                portfolio_snapshot JSON,
                report_snapshot JSON,
                user_id INT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX (session_id),
                INDEX (version_number),
                INDEX (instrument_type)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

        cursor.execute(
            """INSERT INTO calculations 
               (instrument_type, dataset_id, session_id, input_data, result_data, calculation_status, completed_at) 
               VALUES (%s, %s, %s, %s, %s, %s, NOW())""",
            (instrument_type, dataset_id, session_id, json.dumps(input_data), json.dumps(result_data), 'completed')
        )
        conn.commit()
        calculation_id = cursor.lastrowid
        print(f"✅ Calculation saved with ID: {calculation_id}")
        
        # ===== FIX: Update session instrument_count =====
        if session_id:
            try:
                # Get current session from ui_sessions
                cursor.execute(
                    "SELECT instrument_workflows, version_count FROM ui_sessions WHERE session_id = %s",
                    (session_id,)
                )
                session_row = cursor.fetchone()
                if session_row:
                    instrument_workflows = session_row.get('instrument_workflows')
                    try:
                        instrument_workflows = json.loads(instrument_workflows) if isinstance(instrument_workflows, str) else instrument_workflows or {}
                    except:
                        instrument_workflows = {}
                    
                    # Update the instrument_workflows with calculation data
                    if instrument_type not in instrument_workflows:
                        instrument_workflows[instrument_type] = {}
                    instrument_workflows[instrument_type]['calculations'] = result_data
                    instrument_workflows[instrument_type]['calculated_at'] = datetime.now().isoformat()
                    
                    # Count distinct instruments with data
                    instrument_count = 0
                    for key in ['money-market', 'bonds', 'tbills']:
                        if key in instrument_workflows and instrument_workflows[key]:
                            wf = instrument_workflows[key]
                            if (wf.get('cleanedData') and len(wf.get('cleanedData')) > 0) or \
                               (wf.get('data') and len(wf.get('data')) > 0) or \
                               (wf.get('calculations') and wf.get('calculations', {}).get('totalValue', 0) > 0):
                                instrument_count += 1
                    
                    # Update session with new instrument_count and increment version_count
                    cursor.execute(
                        """UPDATE ui_sessions 
                           SET instrument_workflows = %s, instrument_count = %s, version_count = version_count + 1 
                           WHERE session_id = %s""",
                        (json.dumps(instrument_workflows), instrument_count, session_id)
                    )
                    conn.commit()
                    print(f"✅ Session {session_id} updated: instrument_count={instrument_count}")
            except Exception as e:
                print(f"⚠️ Failed to update session: {e}")
        
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"❌ Save calculation error: {e}")
        if conn:
            conn.close()


def get_history():
    """Get calculation history for the current user/session."""
    conn = get_db()
    if not conn:
        return []
    try:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT id, instrument_type, dataset_id, session_id, calculation_status, created_at 
               FROM calculations ORDER BY created_at DESC LIMIT 20"""
        )
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return [
            {
                'id': row['id'],
                'instrument_type': row['instrument_type'],
                'dataset_id': row['dataset_id'],
                'session_id': row['session_id'],
                'status': row['calculation_status'],
                'created_at': row['created_at'].isoformat() if row['created_at'] else None
            }
            for row in rows
        ]
    except Exception as e:
        print(f"❌ Get history error: {e}")
        return []


def get_latest_calculation(dataset_id=None, session_id=None):
    """Get the latest calculation for a dataset or session."""
    conn = get_db()
    if not conn:
        return None
    try:
        cursor = conn.cursor()
        if dataset_id:
            cursor.execute(
                "SELECT * FROM calculations WHERE dataset_id = %s ORDER BY created_at DESC LIMIT 1",
                (dataset_id,)
            )
        elif session_id:
            cursor.execute(
                "SELECT * FROM calculations WHERE session_id = %s ORDER BY created_at DESC LIMIT 1",
                (session_id,)
            )
        else:
            cursor.execute("SELECT * FROM calculations ORDER BY created_at DESC LIMIT 1")
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        if not row:
            return None
        result_data = row.get('result_data')
        try:
            result_data = json.loads(result_data) if isinstance(result_data, str) else result_data
        except Exception:
            result_data = None
        return {
            'id': row.get('id'),
            'instrument_type': row.get('instrument_type'),
            'dataset_id': row.get('dataset_id'),
            'session_id': row.get('session_id'),
            'result_data': result_data,
            'status': row.get('calculation_status'),
            'created_at': row.get('created_at').isoformat() if row.get('created_at') else None
        }
    except Exception as e:
        print(f"❌ Get latest calculation error: {e}")
        return None


def get_calculations_by_session(session_id):
    """Get all calculations for a session."""
    conn = get_db()
    if not conn:
        return []
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM calculations WHERE session_id = %s ORDER BY created_at DESC",
            (session_id,)
        )
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        
        calculations = []
        for row in rows:
            result_data = row.get('result_data')
            try:
                result_data = json.loads(result_data) if isinstance(result_data, str) else result_data
            except Exception:
                result_data = None
            calculations.append({
                'id': row.get('id'),
                'instrument_type': row.get('instrument_type'),
                'dataset_id': row.get('dataset_id'),
                'session_id': row.get('session_id'),
                'result_data': result_data,
                'status': row.get('calculation_status'),
                'created_at': row.get('created_at').isoformat() if row.get('created_at') else None
            })
        return calculations
    except Exception as e:
        print(f"❌ Get calculations by session error: {e}")
        return []


def generate_instrument_summary(session_id, instrument_type=None):
    """
    Generate instrument summary from saved calculations.
    Returns: { columns: [], rows: [] }
    """
    conn = get_db()
    if not conn:
        return {'columns': [], 'rows': []}
    
    try:
        cursor = conn.cursor()
        if instrument_type:
            cursor.execute(
                "SELECT * FROM calculations WHERE session_id = %s AND instrument_type = %s ORDER BY created_at DESC",
                (session_id, normalize_instrument_type(instrument_type))
            )
        else:
            cursor.execute(
                "SELECT * FROM calculations WHERE session_id = %s ORDER BY created_at DESC",
                (session_id,)
            )
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        
        summary_rows = []
        for row in rows:
            result_data = row.get('result_data')
            try:
                result_data = json.loads(result_data) if isinstance(result_data, str) else result_data
            except Exception:
                result_data = {}
            
            inst_type = row.get('instrument_type')
            calculations = result_data.get('calculations', [])
            
            if calculations:
                for calc in calculations:
                    summary_row = {
                        'Instrument Type': inst_type,
                        'Calculation ID': row.get('id'),
                        'Created At': row.get('created_at').isoformat() if row.get('created_at') else None,
                        **calc
                    }
                    summary_rows.append(summary_row)
            else:
                summary_row = {
                    'Instrument Type': inst_type,
                    'Calculation ID': row.get('id'),
                    'Created At': row.get('created_at').isoformat() if row.get('created_at') else None,
                    'Total Value': result_data.get('totalValue', 0),
                    'Instrument Count': result_data.get('instrumentCount', 0),
                    'Avg Rate': result_data.get('avgRate', 0),
                    'Weighted Avg Rate': result_data.get('weightedAvgRate', 0),
                    'Total Interest': result_data.get('totalInterest', 0),
                    'Interest Earned': result_data.get('interestEarned', 0),
                    'Annual Yield': result_data.get('annualYield', 0),
                    'Effective Annual Rate': result_data.get('effectiveAnnualRate', 0),
                    'Avg Days to Maturity': result_data.get('avgDaysToMaturity', 0),
                    'Total Principal': result_data.get('totalPrincipal', 0),
                }
                if inst_type == 'bonds':
                    summary_row.update({
                        'Avg Coupon Rate': result_data.get('avgCouponRate', 0),
                        'Weighted Avg Coupon': result_data.get('weightedAvgCoupon', 0),
                        'Total Annual Income': result_data.get('totalAnnualIncome', 0),
                        'Avg YTM': result_data.get('avgYTM', 0),
                        'Duration': result_data.get('duration', 0)
                    })
                elif inst_type == 'tbills':
                    summary_row.update({
                        'Avg Discount Rate': result_data.get('avgDiscountRate', 0),
                        'Weighted Avg Discount': result_data.get('weightedAvgDiscount', 0),
                        'Total Discount': result_data.get('totalDiscount', 0),
                        'Effective Yield': result_data.get('effectiveYield', 0),
                        'Bond Equivalent Yield': result_data.get('bondEquivalentYield', 0),
                        'Price per 100': result_data.get('pricePer100', 0),
                        'Total Purchase Price': result_data.get('totalPurchasePrice', 0),
                        'Avg Investment': result_data.get('avgInvestment', 0),
                        'Holding Period Yield': result_data.get('holdingPeriodYield', 0),
                        'Annualized Yield': result_data.get('annualizedYield', 0)
                    })
                summary_rows.append(summary_row)
        
        columns = []
        if summary_rows:
            columns = list(summary_rows[0].keys())
        
        return {'columns': columns, 'rows': summary_rows}
    except Exception as e:
        print(f"❌ Generate instrument summary error: {e}")
        return {'columns': [], 'rows': []}


def generate_portfolio_summary(session_id):
    """
    Generate portfolio summary from all instrument calculations in a session.
    Returns: { columns: [], rows: [], portfolio_total: 0, instrument_counts: {} }
    """
    conn = get_db()
    if not conn:
        return {'columns': [], 'rows': [], 'portfolio_total': 0, 'instrument_counts': {}}
    
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM calculations WHERE session_id = %s ORDER BY created_at DESC",
            (session_id,)
        )
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        
        portfolio_rows = []
        portfolio_total = 0
        instrument_counts = {}
        
        for row in rows:
            result_data = row.get('result_data')
            try:
                result_data = json.loads(result_data) if isinstance(result_data, str) else result_data
            except Exception:
                result_data = {}
            
            inst_type = row.get('instrument_type')
            total_value = result_data.get('totalValue', 0)
            instrument_count = result_data.get('instrumentCount', 0)
            avg_rate = result_data.get('avgRate', 0)
            
            portfolio_total += total_value
            instrument_counts[inst_type] = instrument_counts.get(inst_type, 0) + instrument_count
            
            calculations = result_data.get('calculations', [])
            if calculations:
                for calc in calculations:
                    portfolio_row = {
                        'Instrument Type': inst_type,
                        'Session ID': session_id,
                        'Calculation ID': row.get('id'),
                        'Created At': row.get('created_at').isoformat() if row.get('created_at') else None,
                        **calc
                    }
                    portfolio_rows.append(portfolio_row)
            else:
                portfolio_row = {
                    'Instrument Type': inst_type,
                    'Session ID': session_id,
                    'Calculation ID': row.get('id'),
                    'Created At': row.get('created_at').isoformat() if row.get('created_at') else None,
                    'Total Value': total_value,
                    'Instrument Count': instrument_count,
                    'Avg Rate': avg_rate,
                    'Weighted Avg Rate': result_data.get('weightedAvgRate', 0),
                    'Total Interest': result_data.get('totalInterest', 0),
                    'Total Principal': result_data.get('totalPrincipal', 0),
                }
                if inst_type == 'bonds':
                    portfolio_row['Avg Coupon Rate'] = result_data.get('avgCouponRate', 0)
                    portfolio_row['Avg YTM'] = result_data.get('avgYTM', 0)
                    portfolio_row['Duration'] = result_data.get('duration', 0)
                elif inst_type == 'tbills':
                    portfolio_row['Avg Discount Rate'] = result_data.get('avgDiscountRate', 0)
                    portfolio_row['Effective Yield'] = result_data.get('effectiveYield', 0)
                    portfolio_row['Bond Equivalent Yield'] = result_data.get('bondEquivalentYield', 0)
                portfolio_rows.append(portfolio_row)
        
        columns = []
        if portfolio_rows:
            columns = list(portfolio_rows[0].keys())
        
        return {
            'columns': columns,
            'rows': portfolio_rows,
            'portfolio_total': portfolio_total,
            'instrument_counts': instrument_counts
        }
    except Exception as e:
        print(f"❌ Generate portfolio summary error: {e}")
        return {'columns': [], 'rows': [], 'portfolio_total': 0, 'instrument_counts': {}}


def get_session_instrument_workflows(session_id):
    """Get instrument workflows from the session for display in dashboard."""
    conn = get_db()
    if not conn:
        return {}
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT instrument_workflows FROM ui_sessions WHERE session_id = %s",
            (session_id,)
        )
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        if row and row.get('instrument_workflows'):
            try:
                return json.loads(row.get('instrument_workflows')) if isinstance(row.get('instrument_workflows'), str) else row.get('instrument_workflows')
            except:
                return {}
        return {}
    except Exception as e:
        print(f"❌ Get session workflows error: {e}")
        return {}


def calculations_routes(app):
    """Register all calculation routes."""

    @app.route('/api/calculate/<instrument_type>', methods=['POST', 'OPTIONS'])
    def calculate_endpoint(instrument_type):
        if request.method == 'OPTIONS':
            return '', 200
        payload = request.get_json() or {}
        data = payload.get('data', [])
        if not isinstance(data, list):
            return jsonify({'success': False, 'message': 'Data must be an array'}), 400
        
        inst_type = normalize_instrument_type(instrument_type)
        dataset_id = payload.get('dataset_id')
        session_id = payload.get('session_id')
        country = payload.get('country', 'US')
        currency = payload.get('currency', 'USD')
        maturity = payload.get('maturity', '1Y')
        manual_inputs = payload.get('manualInputs', {})
        
        try:
            result = calculate_data(data, inst_type)
            attach_fred_to_calculation(result, inst_type, maturity, country, currency)
            
            # Save calculation with session_id for retrieval – this updates instrument_count
            save_calculation(inst_type, data, result, dataset_id, session_id)
            
            # Get updated instrument summary from backend
            summary = generate_instrument_summary(session_id, inst_type) if session_id else {'columns': [], 'rows': []}
            portfolio = generate_portfolio_summary(session_id) if session_id else {'columns': [], 'rows': [], 'portfolio_total': 0}
            
            return jsonify({
                'success': True,
                'data': result,
                'instrument_type': inst_type,
                'dataset_id': dataset_id,
                'session_id': session_id,
                'summary': {
                    'total_instruments': result.get('instrumentCount', 0),
                    'total_value': result.get('totalValue', 0),
                    'avg_rate': result.get('avgRate', 0),
                    'calculations': result.get('calculations', [])
                },
                'instrument_summary': summary,
                'portfolio_summary': portfolio
            })
        except Exception as e:
            print(f"❌ Calculation error: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/calculations/history', methods=['GET', 'OPTIONS'])
    def calculations_history():
        if request.method == 'OPTIONS':
            return '', 200
        return jsonify({'success': True, 'data': get_history()})

    @app.route('/api/calculations/latest', methods=['GET', 'OPTIONS'])
    def calculations_latest():
        if request.method == 'OPTIONS':
            return '', 200
        dataset_id = request.args.get('dataset_id')
        session_id = request.args.get('session_id')
        latest = get_latest_calculation(dataset_id, session_id)
        if not latest:
            return jsonify({'success': False, 'message': 'Calculation not found'}), 404
        return jsonify({'success': True, 'data': latest})

    @app.route('/api/calculations/session/<session_id>', methods=['GET', 'OPTIONS'])
    def calculations_by_session(session_id):
        if request.method == 'OPTIONS':
            return '', 200
        calculations = get_calculations_by_session(session_id)
        return jsonify({'success': True, 'data': calculations})

    @app.route('/api/calculations/instrument-summary', methods=['POST', 'OPTIONS'])
    def generate_instrument_summary_endpoint():
        if request.method == 'OPTIONS':
            return '', 200
        payload = request.get_json() or {}
        session_id = payload.get('session_id')
        instrument_type = payload.get('instrument_type')
        
        if not session_id:
            return jsonify({'success': False, 'message': 'session_id required'}), 400
        
        summary = generate_instrument_summary(session_id, instrument_type)
        return jsonify({'success': True, 'data': summary})

    @app.route('/api/calculations/portfolio-summary', methods=['POST', 'OPTIONS'])
    def generate_portfolio_summary_endpoint():
        if request.method == 'OPTIONS':
            return '', 200
        payload = request.get_json() or {}
        session_id = payload.get('session_id')
        
        if not session_id:
            return jsonify({'success': False, 'message': 'session_id required'}), 400
        
        summary = generate_portfolio_summary(session_id)
        return jsonify({'success': True, 'data': summary})

    @app.route('/api/calculations/session-workflows/<session_id>', methods=['GET', 'OPTIONS'])
    def get_session_workflows(session_id):
        if request.method == 'OPTIONS':
            return '', 200
        workflows = get_session_instrument_workflows(session_id)
        return jsonify({'success': True, 'data': workflows})

    # Legacy endpoint
    @app.route('/api/calculate', methods=['POST', 'OPTIONS'])
    def calculate_legacy():
        if request.method == 'OPTIONS':
            return '', 200
        payload = request.get_json() or {}
        data = payload.get('data', [])
        instrument_type = normalize_instrument_type(payload.get('instrument_type', 'tbills'))
        dataset_id = payload.get('dataset_id')
        session_id = payload.get('session_id')
        country = payload.get('country', 'US')
        currency = payload.get('currency', 'USD')
        maturity = payload.get('maturity', '1Y')
        try:
            result = calculate_data(data, instrument_type)
            attach_fred_to_calculation(result, instrument_type, maturity, country, currency)
            save_calculation(instrument_type, data, result, dataset_id, session_id)
            return jsonify({'success': True, 'data': result})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500