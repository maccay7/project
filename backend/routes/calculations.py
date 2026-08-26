import json
from flask import request, jsonify
from pages.calculations_details import calculate_data
from utils.db import get_db
from utils.fred_config import attach_fred_to_calculation, get_market_benchmark
from datetime import datetime
from calculations.tbills import calculate_tbills
from calculations.bonds import calculate_bonds
from calculations.money_market import calculate_money_market
from utils.field_mapping_engine import create_field_mapping_engine, InstrumentType
from utils.calculation_dependencies import create_calculation_dependency_engine
from utils.instrument_detection import create_instrument_detector


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
        'tbo': 'tbills',
        'tbos': 'tbills',
        'bonds': 'bonds',
        'bond': 'bonds',
        'money-market': 'money-market',
        'money_market': 'money-market',
        'money market': 'money-market',
        'mm': 'money-market'
    }
    return mapping.get(normalized, normalized)


def detect_instruments_from_data(data):
    """
    Detect unique instrument types from cleaned data using the Instrument column.
    Returns: {
        'unique_instruments': ['bonds', 'money-market', 'tbills'],
        'instrument_counts': {'bonds': 5, 'money-market': 3, 'tbills': 2},
        'total_rows': 10,
        'is_multi_instrument': True
    }
    """
    if not data or len(data) == 0:
        return {
            'unique_instruments': [],
            'instrument_counts': {},
            'total_rows': 0,
            'is_multi_instrument': False
        }
    
    # Look for Instrument column (case-insensitive)
    instrument_column = None
    possible_names = ['instrument', 'instrument type', 'instrument_type', 'type', 'classification']
    
    first_row = data[0] if data else {}
    for key in first_row.keys():
        if key.lower() in possible_names:
            instrument_column = key
            break
    
    if not instrument_column:
        # No Instrument column found - use auto-detection
        print("⚠️ No Instrument column found, using auto-detection")
        detector = create_instrument_detector()
        detection_result = detector.detect_from_data(data)
        detected_type = detection_result.instrument_type if detection_result.instrument_type else 'tbills'
        return {
            'unique_instruments': [detected_type],
            'instrument_counts': {detected_type: len(data)},
            'total_rows': len(data),
            'is_multi_instrument': False
        }
    
    # Extract unique instrument values from the Instrument column
    instrument_values = []
    for row in data:
        inst_value = row.get(instrument_column)
        if inst_value:
            instrument_values.append(str(inst_value).strip())
    
    if not instrument_values:
        # No instrument values found - use auto-detection
        print("⚠️ No instrument values found in Instrument column, using auto-detection")
        detector = create_instrument_detector()
        detection_result = detector.detect_from_data(data)
        detected_type = detection_result.instrument_type if detection_result.instrument_type else 'tbills'
        return {
            'unique_instruments': [detected_type],
            'instrument_counts': {detected_type: len(data)},
            'total_rows': len(data),
            'is_multi_instrument': False
        }
    
    # Normalize and count unique instruments
    normalized_instruments = [normalize_instrument_type(val) for val in instrument_values]
    unique_instruments = list(set(normalized_instruments))
    
    instrument_counts = {}
    for inst in normalized_instruments:
        instrument_counts[inst] = instrument_counts.get(inst, 0) + 1
    
    is_multi_instrument = len(unique_instruments) > 1
    
    print(f"🔍 Detected instruments from Instrument column: {unique_instruments}")
    print(f"🔍 Instrument counts: {instrument_counts}")
    print(f"🔍 Is multi-instrument: {is_multi_instrument}")
    
    return {
        'unique_instruments': unique_instruments,
        'instrument_counts': instrument_counts,
        'total_rows': len(data),
        'is_multi_instrument': is_multi_instrument,
        'instrument_column': instrument_column
    }


def split_data_by_instrument(data, instrument_column):
    """
    Split data by instrument type using the Instrument column.
    Returns: {
        'bonds': [row1, row2, ...],
        'money-market': [row3, row4, ...],
        'tbills': [row5, row6, ...]
    }
    """
    if not data or not instrument_column:
        return {}
    
    split_data = {}
    
    for row in data:
        inst_value = row.get(instrument_column)
        if inst_value:
            normalized_inst = normalize_instrument_type(str(inst_value).strip())
            if normalized_inst not in split_data:
                split_data[normalized_inst] = []
            split_data[normalized_inst].append(row)
    
    return split_data


def save_calculation(instrument_type, input_data, result_data, dataset_id=None, session_id=None, sheet_name=None, section_id=None, instrument_names=None):
    """Save calculation results to database with duplicate prevention and provenance tracking."""
    conn = get_db()
    if not conn:
        print("⚠️ Database connection failed – calculation not saved")
        return None
    
    try:
        cursor = conn.cursor()
        
        # Ensure calculations table exists with enhanced schema
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS calculations (
                id INT AUTO_INCREMENT PRIMARY KEY,
                instrument_type VARCHAR(64) NOT NULL,
                dataset_id VARCHAR(64),
                session_id VARCHAR(64),
                sheet_name VARCHAR(255),
                section_id VARCHAR(64),
                instrument_names JSON,
                input_data JSON,
                result_data JSON,
                calculation_status ENUM('pending', 'processing', 'completed', 'failed') DEFAULT 'completed',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP NULL,
                input_hash VARCHAR(64),
                INDEX (instrument_type),
                INDEX (dataset_id),
                INDEX (session_id),
                INDEX (calculation_status),
                INDEX (created_at),
                INDEX (input_hash),
                INDEX (sheet_name),
                INDEX (section_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        conn.commit()
        
        # Add new columns if they don't exist
        for column in ['sheet_name', 'section_id', 'input_hash', 'instrument_names']:
            try:
                cursor.execute(f"SHOW COLUMNS FROM calculations LIKE '{column}'")
                if not cursor.fetchone():
                    cursor.execute(f"ALTER TABLE calculations ADD COLUMN {column} JSON AFTER session_id")
                    conn.commit()
                    print(f"✅ Added missing {column} column to calculations table")
            except Exception as alter_error:
                print(f"⚠️ Could not add {column} column: {alter_error}")
        
        # Generate input hash for duplicate detection
        import hashlib
        input_str = json.dumps(input_data, sort_keys=True)
        input_hash = hashlib.md5(input_str.encode()).hexdigest()
        
        # Check for duplicate calculation (same session, instrument type, input hash)
        cursor.execute(
            """SELECT id FROM calculations 
               WHERE session_id = %s AND instrument_type = %s AND input_hash = %s 
               AND calculation_status = 'completed' 
               ORDER BY created_at DESC LIMIT 1""",
            (session_id, instrument_type, input_hash)
        )
        duplicate = cursor.fetchone()
        
        if duplicate:
            print(f"⚠️ Duplicate calculation detected (ID: {duplicate['id']}), skipping save")
            return duplicate['id']
        
        # Insert new calculation
        cursor.execute(
            """INSERT INTO calculations 
               (instrument_type, dataset_id, session_id, sheet_name, section_id, instrument_names,
                input_data, result_data, calculation_status, completed_at, input_hash) 
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), %s)""",
            (instrument_type, dataset_id, session_id, sheet_name, section_id, json.dumps(instrument_names) if instrument_names else None,
             json.dumps(input_data), json.dumps(result_data), 'completed', input_hash)
        )
        conn.commit()
        calculation_id = cursor.lastrowid
        print(f"✅ Calculation saved with ID: {calculation_id} (sheet: {sheet_name}, section: {section_id}, instruments: {instrument_names})")

        # Update session with multi-sheet/section support
        if session_id:
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

                # Initialize instrument type if not exists
                if instrument_type not in instrument_workflows:
                    instrument_workflows[instrument_type] = {}
                
                # Track sheets/sections for this instrument type
                if 'sheets' not in instrument_workflows[instrument_type]:
                    instrument_workflows[instrument_type]['sheets'] = {}
                
                if sheet_name:
                    if sheet_name not in instrument_workflows[instrument_type]['sheets']:
                        instrument_workflows[instrument_type]['sheets'][sheet_name] = {}
                    sheet_data = instrument_workflows[instrument_type]['sheets'][sheet_name]
                    
                    if section_id:
                        sheet_data['sections'] = sheet_data.get('sections', {})
                        sheet_data['sections'][section_id] = {
                            'calculation_id': calculation_id,
                            'calculated_at': datetime.now().isoformat(),
                            'input_hash': input_hash
                        }
                    else:
                        sheet_data['calculation_id'] = calculation_id
                        sheet_data['calculated_at'] = datetime.now().isoformat()
                        sheet_data['input_hash'] = input_hash
                
                # Store latest calculation result
                instrument_workflows[instrument_type]['calculations'] = result_data
                instrument_workflows[instrument_type]['calculated_at'] = datetime.now().isoformat()
                instrument_workflows[instrument_type]['latest_calculation_id'] = calculation_id

                # Count distinct instruments with data
                instrument_count = 0
                for key in ['money-market', 'bonds', 'tbills']:
                    if key in instrument_workflows and instrument_workflows[key]:
                        wf = instrument_workflows[key]
                        if (wf.get('cleanedData') and len(wf.get('cleanedData')) > 0) or \
                           (wf.get('data') and len(wf.get('data')) > 0) or \
                           (wf.get('calculations') and wf.get('calculations', {}).get('totalValue', 0) > 0):
                            instrument_count += 1

                # Update session
                cursor.execute(
                    """UPDATE ui_sessions 
                       SET instrument_workflows = %s, instrument_count = %s 
                       WHERE session_id = %s""",
                    (json.dumps(instrument_workflows), instrument_count, session_id)
                )
                conn.commit()
                print(f"✅ Session updated with multi-sheet/section tracking")

        return calculation_id
        
    except Exception as e:
        print(f"❌ Error saving calculation: {e}")
        import traceback
        traceback.print_exc()
        return None


def get_history():
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
    Fixed: Properly handles rows as list of dicts, avoids 'list' object has no attribute 'get' error.
    Enhanced: Includes traceability (sheet_name, section_id) and proper aggregation.
    Uses instrument_names from database for accurate instrument names.
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

        if not rows:
            return {'columns': [], 'rows': []}

        summary_rows = []
        for row in rows:
            result_data = row.get('result_data')
            if isinstance(result_data, str):
                try:
                    result_data = json.loads(result_data)
                except:
                    result_data = {}
            elif not isinstance(result_data, dict):
                result_data = {}

            # Get instrument names from the instrument_names column (source of truth)
            instrument_names_json = row.get('instrument_names')
            instrument_names = []
            if instrument_names_json:
                if isinstance(instrument_names_json, str):
                    try:
                        instrument_names = json.loads(instrument_names_json)
                    except:
                        instrument_names = []
                elif isinstance(instrument_names_json, list):
                    instrument_names = instrument_names_json
            
            # If no instrument_names in database, fall back to input_data
            if not instrument_names:
                input_data = row.get('input_data')
                if isinstance(input_data, str):
                    try:
                        input_data = json.loads(input_data)
                    except:
                        input_data = {}
                instrument_name = input_data.get('instrument_name') or input_data.get('Instrument Name') or 'Instrument'
                instrument_names = [instrument_name]

            calculations_list = result_data.get('calculations', [])
            if calculations_list and isinstance(calculations_list, list):
                for idx, calc in enumerate(calculations_list):
                    if isinstance(calc, dict):
                        # Use the corresponding instrument name from the list
                        inst_name = instrument_names[idx] if idx < len(instrument_names) else (instrument_names[0] if instrument_names else 'Instrument')
                        summary_row = {
                            'Instrument Name': calc.get('instrument_name', inst_name),
                            'Instrument Type': row.get('instrument_type'),
                            'Calculation ID': row.get('id'),
                            'Created At': row.get('created_at').isoformat() if row.get('created_at') else None,
                            'Sheet Name': row.get('sheet_name'),
                            'Section ID': row.get('section_id'),
                        }
                        for key, value in calc.items():
                            if key not in summary_row and key not in ['_raw', '_source', 'index', '__v']:
                                summary_row[key] = value
                        summary_rows.append(summary_row)
            else:
                # For single instrument calculations, use the first instrument name
                inst_name = instrument_names[0] if instrument_names else 'Instrument'
                summary_row = {
                    'Instrument Name': inst_name,
                    'Instrument Type': row.get('instrument_type'),
                    'Calculation ID': row.get('id'),
                    'Created At': row.get('created_at').isoformat() if row.get('created_at') else None,
                    'Sheet Name': row.get('sheet_name'),
                    'Section ID': row.get('section_id'),
                    'Total Value': result_data.get('totalValue', 0),
                    'Instrument Count': result_data.get('instrumentCount', 1),
                    'Avg Rate': result_data.get('avgRate', 0),
                    'Weighted Avg Rate': result_data.get('weightedAvgRate', 0),
                    'Total Interest': result_data.get('totalInterest', 0),
                    'Interest Earned': result_data.get('interestEarned', 0),
                    'Annual Yield': result_data.get('annualYield', 0),
                    'Effective Annual Rate': result_data.get('effectiveAnnualRate', 0),
                    'Avg Days to Maturity': result_data.get('avgDaysToMaturity', 0),
                    'Total Principal': result_data.get('totalPrincipal', 0),
                    'FRED Benchmark': result_data.get('fred', {}).get('benchmark_rate') if result_data.get('fred') else None
                }
                inst_type = row.get('instrument_type')
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
            all_keys = set()
            for row in summary_rows:
                all_keys.update(row.keys())
            columns = sorted(list(all_keys))

        return {'columns': columns, 'rows': summary_rows}

    except Exception as e:
        print(f"❌ Generate instrument summary error: {e}")
        import traceback
        traceback.print_exc()
        return {'columns': [], 'rows': []}


def generate_portfolio_summary(session_id):
    """
    Generate portfolio summary from saved calculations.
    Returns: { columns: [], rows: [], portfolio_total: 0, instrument_counts: {} }
    Enhanced: Aggregates from actual calculation results, includes traceability, prevents double-counting.
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
        processed_calculation_ids = set()  # Prevent double-counting same calculation
        
        for row in rows:
            calculation_id = row.get('id')
            if calculation_id in processed_calculation_ids:
                continue  # Skip already processed calculations
            
            result_data = row.get('result_data')
            input_data = row.get('input_data')
            try:
                result_data = json.loads(result_data) if isinstance(result_data, str) else result_data
                input_data = json.loads(input_data) if isinstance(input_data, str) else input_data
            except Exception:
                result_data = {}
                input_data = {}
            
            inst_type = row.get('instrument_type')
            total_value = result_data.get('totalValue', 0)
            instrument_count = result_data.get('instrumentCount', 0)
            avg_rate = result_data.get('avgRate', 0)
            
            instrument_name = input_data.get('instrument_name') or input_data.get('Instrument Name') or 'Instrument'
            
            portfolio_total += total_value
            instrument_counts[inst_type] = instrument_counts.get(inst_type, 0) + instrument_count
            processed_calculation_ids.add(calculation_id)
            
            calculations = result_data.get('calculations', [])
            if calculations and isinstance(calculations, list):
                for calc in calculations:
                    if isinstance(calc, dict):
                        portfolio_row = {
                            'Instrument Name': calc.get('instrument_name', instrument_name),
                            'Instrument Type': inst_type,
                            'Session ID': session_id,
                            'Calculation ID': calculation_id,
                            'Created At': row.get('created_at').isoformat() if row.get('created_at') else None,
                            'Sheet Name': row.get('sheet_name'),
                            'Section ID': row.get('section_id'),
                        }
                        for key, value in calc.items():
                            if key not in portfolio_row:
                                portfolio_row[key] = value
                        portfolio_rows.append(portfolio_row)
            else:
                portfolio_row = {
                    'Instrument Name': instrument_name,
                    'Instrument Type': inst_type,
                    'Session ID': session_id,
                    'Calculation ID': calculation_id,
                    'Created At': row.get('created_at').isoformat() if row.get('created_at') else None,
                    'Sheet Name': row.get('sheet_name'),
                    'Section ID': row.get('section_id'),
                    'Total Value': total_value,
                    'Instrument Count': instrument_count,
                    'Avg Rate': avg_rate,
                    'Weighted Avg Rate': result_data.get('weightedAvgRate', 0),
                    'Total Interest': result_data.get('totalInterest', 0),
                    'Total Principal': result_data.get('totalPrincipal', 0),
                    'FRED Benchmark': result_data.get('fred', {}).get('benchmark_rate') if result_data.get('fred') else None
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
            all_keys = set()
            for row in portfolio_rows:
                all_keys.update(row.keys())
            columns = sorted(list(all_keys))
        
        return {
            'columns': columns,
            'rows': portfolio_rows,
            'portfolio_total': portfolio_total,
            'instrument_counts': instrument_counts
        }
    except Exception as e:
        print(f"❌ Generate portfolio summary error: {e}")
        import traceback
        traceback.print_exc()
        return {'columns': [], 'rows': [], 'portfolio_total': 0, 'instrument_counts': {}}


def get_session_instrument_workflows(session_id):
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
            print(f"🔍 Starting calculation for {inst_type}")
            print(f"🔍 Session ID: {session_id}, Dataset ID: {dataset_id}")
            
            # If dataset_id is provided, load full dataset from backend file
            if dataset_id:
                from utils.db import get_db
                from utils.excel_parser import parse_full_workbook
                import os
                
                conn = get_db()
                if conn:
                    try:
                        cursor = conn.cursor()
                        cursor.execute("SELECT file_path, instrument_type FROM datasets WHERE id = %s", (dataset_id,))
                        dataset = cursor.fetchone()
                        cursor.close()
                        conn.close()
                        
                        if dataset and dataset.get('file_path') and os.path.exists(dataset['file_path']):
                            print(f"🔍 Loading full dataset from file: {dataset['file_path']}")
                            parsed = parse_full_workbook(dataset['file_path'], dataset.get('instrument_type', inst_type), max_rows=None)
                            sheets = parsed.get('sheets', [])
                            if sheets:
                                # Use the first sheet's full data for calculations
                                full_data = sheets[0].get('data', [])
                                if full_data and len(full_data) > len(data):
                                    print(f"🔍 Using full dataset ({len(full_data)} rows) instead of preview ({len(data)} rows)")
                                    data = full_data
                                else:
                                    print(f"🔍 Using provided data ({len(data)} rows)")
                    except Exception as load_error:
                        print(f"⚠️ Failed to load full dataset from backend: {load_error}")
                        print(f"🔍 Using provided data ({len(data)} rows)")
            
            print(f"🔍 Processing {len(data)} rows for calculation")
            print(f"🔍 Data sample: {data[0] if data else 'No data'}")
            
            result = calculate_data(data, inst_type)
            print(f"✅ Calculation result: {result}")
            
            attach_fred_to_calculation(result, inst_type, maturity, country, currency)
            
            # Save calculation asynchronously - don't block response
            try:
                save_calculation(inst_type, data, result, dataset_id, session_id)
            except Exception as save_error:
                print(f"⚠️ Failed to save calculation to database (non-blocking): {save_error}")
            
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
            return jsonify({'success': False, 'message': f"Calculation failed: {str(e)}"}), 500

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

    @app.route('/api/calculate', methods=['POST', 'OPTIONS'])
    def calculate_legacy():
        if request.method == 'OPTIONS':
            return '', 200
        try:
            payload = request.get_json()
            if isinstance(payload, str):
                import json
                payload = json.loads(payload)
            if not payload:
                payload = {}
        except:
            payload = {}
        
        data = payload.get('data', [])
        instrument_type = normalize_instrument_type(payload.get('instrument_type', 'tbills'))
        dataset_id = payload.get('dataset_id')
        session_id = payload.get('session_id')
        sheet_name = payload.get('sheet_name')
        section_id = payload.get('section_id')
        country = payload.get('country', 'US')
        currency = payload.get('currency', 'USD')
        maturity = payload.get('maturity', '1Y')
        
        try:
            result = calculate_data(data, instrument_type)
            attach_fred_to_calculation(result, instrument_type, maturity, country, currency)
            save_calculation(instrument_type, data, result, dataset_id, session_id, sheet_name, section_id)
            return jsonify({'success': True, 'data': result})
        except Exception as e:
            print(f"❌ Calculation error: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/calculate/tbills', methods=['POST', 'OPTIONS'])
    def calculate_tbills_endpoint():
        if request.method == 'OPTIONS':
            return '', 200
        try:
            payload = request.get_json()
            if isinstance(payload, str):
                import json
                payload = json.loads(payload)
            if not payload:
                payload = {}
        except:
            payload = {}
        
        # Support both 'data' array (new format) and 'inputs' object (old format)
        data = payload.get('data', [])
        inputs = payload.get('inputs', {})
        column_mapping = payload.get('column_mapping', {})
        benchmark_yield = payload.get('benchmark_yield')
        inflation_rate = payload.get('inflation_rate')
        session_id = payload.get('session_id')
        dataset_id = payload.get('dataset_id')
        sheet_name = payload.get('sheet_name')
        section_id = payload.get('section_id')
        country = payload.get('country', 'US')
        currency = payload.get('currency', 'USD')
        maturity = payload.get('maturity', '13W')
        
        # Debug logging to see what data is being received
        print(f"DEBUG T-Bills endpoint: data length = {len(data) if data else 0}")
        if data and len(data) > 0:
            print(f"DEBUG T-Bills endpoint: first row keys = {list(data[0].keys())}")
            print(f"DEBUG T-Bills endpoint: first row sample = {data[0]}")
        
        try:
            # Detect instruments from Instrument column BEFORE normalization (to preserve original names)
            instrument_detection = detect_instruments_from_data(data)
            print(f"DEBUG T-Bills endpoint: instrument_detection = {instrument_detection}")
            
            # Store original data for extracting instrument names before normalization
            original_data = data.copy() if data else []
            
            # Apply column mapping if provided
            if column_mapping and data:
                from routes.mapping import apply_column_mapping
                data = apply_column_mapping(data, column_mapping)
                print(f"Applied column mapping: {column_mapping}")
            
            # Apply semantic normalization to map Excel column names to standardized fields
            if data and len(data) > 0:
                from pages.calculations_details import normalize_row
                normalized_data = [normalize_row(row) for row in data]
                print(f"Applied semantic normalization to {len(normalized_data)} rows")
                data = normalized_data
            
            if instrument_detection['is_multi_instrument']:
                # Multi-instrument data - split and calculate each type separately
                print(f"🔍 Multi-instrument data detected in T-Billed endpoint: {instrument_detection['unique_instruments']}")
                
                instrument_column = instrument_detection.get('instrument_column')
                split_data = split_data_by_instrument(data, instrument_column) if instrument_column else {}
                
                all_results = {}
                calculation_count = 0
                
                for inst_type in instrument_detection['unique_instruments']:
                    inst_data = split_data.get(inst_type, [])
                    if inst_data:
                        print(f"🔍 Calculating {inst_type} with {len(inst_data)} rows")
                        result = calculate_data(inst_data, inst_type)
                        attach_fred_to_calculation(result, inst_type, maturity, country, currency)
                        
                        # Extract actual instrument names from ORIGINAL data (before normalization) for this instrument type
                        instrument_names = []
                        if instrument_column:
                            # Find rows in original data that match this instrument type
                            for row in original_data:
                                inst_value = row.get(instrument_column)
                                if inst_value:
                                    normalized_inst = normalize_instrument_type(str(inst_value).strip())
                                    if normalized_inst == inst_type:
                                        inst_name = str(inst_value).strip()
                                        if inst_name not in instrument_names:
                                            instrument_names.append(inst_name)
                        
                        print(f"🔍 Extracted instrument names for {inst_type}: {instrument_names}")
                        
                        # Save each instrument calculation separately with actual instrument names
                        calc_id = save_calculation(inst_type, inst_data, result, dataset_id, session_id, sheet_name, section_id, instrument_names)
                        
                        # Set instrument_count to the actual number of unique instruments from the column
                        result['instrumentCount'] = len(instrument_names) if instrument_names else 1
                        
                        all_results[inst_type] = {
                            'data': result,
                            'calculation_id': calc_id,
                            'row_count': len(inst_data),
                            'instrument_count': len(instrument_names) if instrument_names else 1,
                            'instrument_names': instrument_names
                        }
                        calculation_count += 1
                
                # Generate summaries
                instrument_summary = generate_instrument_summary(session_id) if session_id else {'columns': [], 'rows': []}
                portfolio_summary = generate_portfolio_summary(session_id) if session_id else {'columns': [], 'rows': [], 'portfolio_total': 0}
                
                return jsonify({
                    'success': True,
                    'is_multi_instrument': True,
                    'instrument_detection': instrument_detection,
                    'results': all_results,
                    'calculation_count': calculation_count,
                    'instrument_summary': instrument_summary,
                    'portfolio_summary': portfolio_summary
                })
            
            # If data array is provided, use the new calculation function
            if data and len(data) > 0:
                result = calculate_data(data, 'tbills')
                attach_fred_to_calculation(result, 'tbills', maturity, country, currency)
                
                # Extract instrument names from ORIGINAL data (before normalization) for single-instrument case
                instrument_names = []
                instrument_column = instrument_detection.get('instrument_column')
                if instrument_column:
                    for row in original_data:
                        inst_name = row.get(instrument_column)
                        if inst_name and str(inst_name).strip() not in instrument_names:
                            instrument_names.append(str(inst_name).strip())
                
                print(f"🔍 Extracted instrument names for single-instrument case: {instrument_names}")
                
                # Set instrument_count to actual unique instrument count
                result['instrumentCount'] = len(instrument_names) if instrument_names else 1
                
                # Save calculation asynchronously - don't block response
                try:
                    save_calculation('tbills', data, result, dataset_id, session_id, sheet_name, section_id, instrument_names)
                except Exception as save_error:
                    print(f"⚠️ Failed to save calculation to database (non-blocking): {save_error}")
                
                # Generate summaries
                instrument_summary = generate_instrument_summary(session_id, 'tbills') if session_id else {'columns': [], 'rows': []}
                portfolio_summary = generate_portfolio_summary(session_id) if session_id else {'columns': [], 'rows': [], 'portfolio_total': 0}
                
                return jsonify({
                    'success': True, 
                    'is_multi_instrument': False,
                    'instrument_type': 'tbills', 
                    'data': result,
                    'instrument_names': instrument_names,
                    'instrument_summary': instrument_summary,
                    'portfolio_summary': portfolio_summary
                })
            else:
                # Fall back to old single-instrument calculation
                results = calculate_tbills(inputs, benchmark_yield, inflation_rate)
                if session_id:
                    save_calculation('tbills', inputs, results, dataset_id, session_id, sheet_name, section_id)
                return jsonify({'success': True, 'instrument_type': 'tbills', 'data': results})
        except Exception as e:
            print(f"❌ T-Bills calculation error: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/calculate/bonds', methods=['POST', 'OPTIONS'])
    def calculate_bonds_endpoint():
        if request.method == 'OPTIONS':
            return '', 200
        try:
            payload = request.get_json()
            if isinstance(payload, str):
                import json
                payload = json.loads(payload)
            if not payload:
                payload = {}
        except:
            payload = {}
        
        # Support both 'data' array (new format) and 'inputs' object (old format)
        data = payload.get('data', [])
        inputs = payload.get('inputs', {})
        column_mapping = payload.get('column_mapping', {})
        benchmark_yield = payload.get('benchmark_yield')
        benchmark_curve = payload.get('benchmark_curve')
        inflation_rate = payload.get('inflation_rate')
        session_id = payload.get('session_id')
        dataset_id = payload.get('dataset_id')
        sheet_name = payload.get('sheet_name')
        section_id = payload.get('section_id')
        country = payload.get('country', 'US')
        currency = payload.get('currency', 'USD')
        maturity = payload.get('maturity', '10Y')
        
        # Debug logging to see what data is being received
        print(f"DEBUG Bonds endpoint: data length = {len(data) if data else 0}")
        if data and len(data) > 0:
            print(f"DEBUG Bonds endpoint: first row keys = {list(data[0].keys())}")
            print(f"DEBUG Bonds endpoint: first row sample = {data[0]}")
        
        try:
            # Detect instruments from Instrument column BEFORE normalization (to preserve original names)
            instrument_detection = detect_instruments_from_data(data)
            print(f"DEBUG Bonds endpoint: instrument_detection = {instrument_detection}")
            
            # Store original data for extracting instrument names before normalization
            original_data = data.copy() if data else []
            
            # Apply column mapping if provided
            if column_mapping and data:
                from routes.mapping import apply_column_mapping
                data = apply_column_mapping(data, column_mapping)
                print(f"Applied column mapping: {column_mapping}")
            
            # Apply semantic normalization to map Excel column names to standardized fields
            if data and len(data) > 0:
                from pages.calculations_details import normalize_row
                normalized_data = [normalize_row(row) for row in data]
                print(f"Applied semantic normalization to {len(normalized_data)} rows")
                data = normalized_data
            
            if instrument_detection['is_multi_instrument']:
                # Multi-instrument data - split and calculate each type separately
                print(f"🔍 Multi-instrument data detected in Bonds endpoint: {instrument_detection['unique_instruments']}")
                
                instrument_column = instrument_detection.get('instrument_column')
                split_data = split_data_by_instrument(data, instrument_column) if instrument_column else {}
                
                all_results = {}
                calculation_count = 0
                
                for inst_type in instrument_detection['unique_instruments']:
                    inst_data = split_data.get(inst_type, [])
                    if inst_data:
                        print(f"🔍 Calculating {inst_type} with {len(inst_data)} rows")
                        result = calculate_data(inst_data, inst_type)
                        attach_fred_to_calculation(result, inst_type, maturity, country, currency)
                        
                        # Extract actual instrument names from ORIGINAL data (before normalization) for this instrument type
                        instrument_names = []
                        if instrument_column:
                            # Find rows in original data that match this instrument type
                            for row in original_data:
                                inst_value = row.get(instrument_column)
                                if inst_value:
                                    normalized_inst = normalize_instrument_type(str(inst_value).strip())
                                    if normalized_inst == inst_type:
                                        inst_name = str(inst_value).strip()
                                        if inst_name not in instrument_names:
                                            instrument_names.append(inst_name)
                        
                        print(f"🔍 Extracted instrument names for {inst_type}: {instrument_names}")
                        
                        # Save each instrument calculation separately with actual instrument names
                        calc_id = save_calculation(inst_type, inst_data, result, dataset_id, session_id, sheet_name, section_id, instrument_names)
                        
                        # Set instrument_count to the actual number of unique instruments from the column
                        result['instrumentCount'] = len(instrument_names) if instrument_names else 1
                        
                        all_results[inst_type] = {
                            'data': result,
                            'calculation_id': calc_id,
                            'row_count': len(inst_data),
                            'instrument_count': len(instrument_names) if instrument_names else 1,
                            'instrument_names': instrument_names
                        }
                        calculation_count += 1
                
                # Generate summaries
                instrument_summary = generate_instrument_summary(session_id) if session_id else {'columns': [], 'rows': []}
                portfolio_summary = generate_portfolio_summary(session_id) if session_id else {'columns': [], 'rows': [], 'portfolio_total': 0}
                
                return jsonify({
                    'success': True,
                    'is_multi_instrument': True,
                    'instrument_detection': instrument_detection,
                    'results': all_results,
                    'calculation_count': calculation_count,
                    'instrument_summary': instrument_summary,
                    'portfolio_summary': portfolio_summary
                })
            
            # If data array is provided, use the new calculation function
            if data and len(data) > 0:
                result = calculate_data(data, 'bonds')
                attach_fred_to_calculation(result, 'bonds', maturity, country, currency)
                
                # Extract instrument names from ORIGINAL data (before normalization) for single-instrument case
                instrument_names = []
                instrument_column = instrument_detection.get('instrument_column')
                if instrument_column:
                    for row in original_data:
                        inst_name = row.get(instrument_column)
                        if inst_name and str(inst_name).strip() not in instrument_names:
                            instrument_names.append(str(inst_name).strip())
                
                print(f"🔍 Extracted instrument names for single-instrument case: {instrument_names}")
                
                # Set instrument_count to actual unique instrument count
                result['instrumentCount'] = len(instrument_names) if instrument_names else 1
                
                # Save calculation asynchronously - don't block response
                try:
                    save_calculation('bonds', data, result, dataset_id, session_id, sheet_name, section_id, instrument_names)
                except Exception as save_error:
                    print(f"⚠️ Failed to save calculation to database (non-blocking): {save_error}")
                
                # Generate summaries
                instrument_summary = generate_instrument_summary(session_id, 'bonds') if session_id else {'columns': [], 'rows': []}
                portfolio_summary = generate_portfolio_summary(session_id) if session_id else {'columns': [], 'rows': [], 'portfolio_total': 0}
                
                return jsonify({
                    'success': True,
                    'is_multi_instrument': False,
                    'instrument_type': 'bonds', 
                    'data': result,
                    'instrument_names': instrument_names,
                    'instrument_summary': instrument_summary,
                    'portfolio_summary': portfolio_summary
                })
            else:
                # Fall back to old single-instrument calculation
                results = calculate_bonds(inputs, benchmark_yield, benchmark_curve, inflation_rate)
                if session_id:
                    save_calculation('bonds', inputs, results, dataset_id, session_id, sheet_name, section_id)
                return jsonify({'success': True, 'instrument_type': 'bonds', 'data': results})
        except Exception as e:
            print(f"❌ Bonds calculation error: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/calculate/money-market', methods=['POST', 'OPTIONS'])
    def calculate_money_market_endpoint():
        if request.method == 'OPTIONS':
            return '', 200
        try:
            payload = request.get_json()
            if isinstance(payload, str):
                import json
                payload = json.loads(payload)
            if not payload:
                payload = {}
        except:
            payload = {}
        
        # Support both 'data' array (new format) and 'inputs' object (old format)
        data = payload.get('data', [])
        inputs = payload.get('inputs', {})
        column_mapping = payload.get('column_mapping', {})
        benchmark_yield = payload.get('benchmark_yield')
        inflation_rate = payload.get('inflation_rate')
        session_id = payload.get('session_id')
        dataset_id = payload.get('dataset_id')
        sheet_name = payload.get('sheet_name')
        section_id = payload.get('section_id')
        country = payload.get('country', 'US')
        currency = payload.get('currency', 'USD')
        maturity = payload.get('maturity', '1Y')
        
        # Debug logging to see what data is being received
        print(f"DEBUG Money Market endpoint: data length = {len(data) if data else 0}")
        if data and len(data) > 0:
            print(f"DEBUG Money Market endpoint: first row keys = {list(data[0].keys())}")
            print(f"DEBUG Money Market endpoint: first row sample = {data[0]}")
        
        try:
            # Detect instruments from Instrument column BEFORE normalization (to preserve original names)
            instrument_detection = detect_instruments_from_data(data)
            print(f"DEBUG Money Market endpoint: instrument_detection = {instrument_detection}")
            
            # Store original data for extracting instrument names before normalization
            original_data = data.copy() if data else []
            
            # Apply column mapping if provided
            if column_mapping and data:
                from routes.mapping import apply_column_mapping
                data = apply_column_mapping(data, column_mapping)
                print(f"Applied column mapping: {column_mapping}")
            
            # Apply semantic normalization to map Excel column names to standardized fields
            if data and len(data) > 0:
                from pages.calculations_details import normalize_row
                normalized_data = [normalize_row(row) for row in data]
                print(f"Applied semantic normalization to {len(normalized_data)} rows")
                data = normalized_data
            
            # If data array is provided, use the new calculation function
            if data and len(data) > 0:
                result = calculate_data(data, 'money-market')
                attach_fred_to_calculation(result, 'money-market', maturity, country, currency)
                
                # Extract instrument names from ORIGINAL data (before normalization) for single-instrument case
                instrument_names = []
                instrument_column = instrument_detection.get('instrument_column')
                if instrument_column:
                    for row in original_data:
                        inst_name = row.get(instrument_column)
                        if inst_name and str(inst_name).strip() not in instrument_names:
                            instrument_names.append(str(inst_name).strip())
                
                print(f"🔍 Extracted instrument names for money-market: {instrument_names}")
                
                # Set instrument_count to actual unique instrument count
                result['instrumentCount'] = len(instrument_names) if instrument_names else 1
                
                # Save calculation asynchronously - don't block response
                try:
                    save_calculation('money-market', data, result, dataset_id, session_id, sheet_name, section_id, instrument_names)
                except Exception as save_error:
                    print(f"⚠️ Failed to save calculation to database (non-blocking): {save_error}")
                
                return jsonify({
                    'success': True, 
                    'instrument_type': 'money-market', 
                    'data': result,
                    'instrument_names': instrument_names
                })
            else:
                # Fall back to old single-instrument calculation
                results = calculate_money_market(inputs, benchmark_yield, inflation_rate)
                if session_id:
                    save_calculation('money-market', inputs, results, dataset_id, session_id, sheet_name, section_id)
                return jsonify({'success': True, 'instrument_type': 'money-market', 'data': results})
        except Exception as e:
            print(f"❌ Money Market calculation error: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/calculate/comprehensive', methods=['POST', 'OPTIONS'])
    def calculate_comprehensive_endpoint():
        if request.method == 'OPTIONS':
            return '', 200
        try:
            payload = request.get_json()
            if isinstance(payload, str):
                import json
                payload = json.loads(payload)
            if not payload:
                payload = {}
        except:
            payload = {}
        
        data = payload.get('data', [])
        column_mapping = payload.get('column_mapping', {})
        session_id = payload.get('session_id')
        dataset_id = payload.get('dataset_id')
        sheet_name = payload.get('sheet_name')
        section_id = payload.get('section_id')
        country = payload.get('country', 'US')
        currency = payload.get('currency', 'USD')
        maturity = payload.get('maturity', '1Y')
        
        if not data or len(data) == 0:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
        
        try:
            # Detect instruments from Instrument column BEFORE normalization (to preserve original names)
            instrument_detection = detect_instruments_from_data(data)
            print(f"DEBUG Comprehensive endpoint: instrument_detection = {instrument_detection}")
            
            # Store original data for extracting instrument names before normalization
            original_data = data.copy() if data else []
            
            # Apply column mapping if provided
            if column_mapping and data:
                from routes.mapping import apply_column_mapping
                data = apply_column_mapping(data, column_mapping)
                print(f"Applied column mapping: {column_mapping}")
            
            # Apply semantic normalization to map Excel column names to standardized fields
            if data and len(data) > 0:
                from pages.calculations_details import normalize_row
                normalized_data = [normalize_row(row) for row in data]
                print(f"Applied semantic normalization to {len(normalized_data)} rows")
                data = normalized_data
            
            if instrument_detection['is_multi_instrument']:
                # Multi-instrument data - split and calculate each type separately
                print(f"🔍 Multi-instrument data detected: {instrument_detection['unique_instruments']}")
                
                instrument_column = instrument_detection.get('instrument_column')
                split_data = split_data_by_instrument(data, instrument_column) if instrument_column else {}
                
                all_results = {}
                calculation_count = 0
                
                for inst_type in instrument_detection['unique_instruments']:
                    inst_data = split_data.get(inst_type, [])
                    if inst_data:
                        print(f"🔍 Calculating {inst_type} with {len(inst_data)} rows")
                        result = calculate_data(inst_data, inst_type)
                        attach_fred_to_calculation(result, inst_type, maturity, country, currency)
                        
                        # Extract actual instrument names from ORIGINAL data (before normalization) for this instrument type
                        instrument_names = []
                        if instrument_column:
                            # Find rows in original data that match this instrument type
                            for row in original_data:
                                inst_value = row.get(instrument_column)
                                if inst_value:
                                    normalized_inst = normalize_instrument_type(str(inst_value).strip())
                                    if normalized_inst == inst_type:
                                        inst_name = str(inst_value).strip()
                                        if inst_name not in instrument_names:
                                            instrument_names.append(inst_name)
                        
                        print(f"🔍 Extracted instrument names for {inst_type}: {instrument_names}")
                        
                        # Save each instrument calculation separately with actual instrument names
                        calc_id = save_calculation(inst_type, inst_data, result, dataset_id, session_id, sheet_name, section_id, instrument_names)
                        
                        # Set instrument_count to the actual number of unique instruments from the column
                        result['instrumentCount'] = len(instrument_names) if instrument_names else 1
                        
                        all_results[inst_type] = {
                            'data': result,
                            'calculation_id': calc_id,
                            'row_count': len(inst_data),
                            'instrument_count': len(instrument_names) if instrument_names else 1,
                            'instrument_names': instrument_names
                        }
                        calculation_count += 1
                
                # Generate summaries
                instrument_summary = generate_instrument_summary(session_id) if session_id else {'columns': [], 'rows': []}
                portfolio_summary = generate_portfolio_summary(session_id) if session_id else {'columns': [], 'rows': [], 'portfolio_total': 0}
                
                return jsonify({
                    'success': True,
                    'is_multi_instrument': True,
                    'instrument_detection': instrument_detection,
                    'results': all_results,
                    'calculation_count': calculation_count,
                    'instrument_summary': instrument_summary,
                    'portfolio_summary': portfolio_summary
                })
            else:
                # Single instrument data - use existing logic
                print(f"🔍 Single instrument data detected: {instrument_detection['unique_instruments']}")
                
                detector = create_instrument_detector()
                detection_result = detector.detect_from_data(data)
                
                instrument_type = detection_result.instrument_type if detection_result.instrument_type else 'tbills'
                
                # Override detection if classification indicates money market
                if data and len(data) > 0 and 'classification' in data[0]:
                    classification = str(data[0]['classification']).lower()
                    if 'mm' in classification or 'money' in classification or 'market' in classification:
                        instrument_type = 'money-market'
                        print(f"Overriding detected instrument type to money-market based on classification: {data[0]['classification']}")
                
                print(f"Final instrument type for calculation: {instrument_type}")
                
                result = calculate_data(data, instrument_type)
                attach_fred_to_calculation(result, instrument_type, maturity, country, currency)
                
                # Extract instrument names from ORIGINAL data (before normalization) for single-instrument case
                instrument_names = []
                instrument_column = instrument_detection.get('instrument_column')
                if instrument_column:
                    for row in original_data:
                        inst_name = row.get(instrument_column)
                        if inst_name and str(inst_name).strip() not in instrument_names:
                            instrument_names.append(str(inst_name).strip())
                
                print(f"🔍 Extracted instrument names for comprehensive single-instrument case: {instrument_names}")
                
                # Set instrument_count to actual unique instrument count
                result['instrumentCount'] = len(instrument_names) if instrument_names else 1
                
                save_calculation(instrument_type, data, result, dataset_id, session_id, sheet_name, section_id, instrument_names)
                
                instrument_summary = generate_instrument_summary(session_id, instrument_type) if session_id else {'columns': [], 'rows': []}
                portfolio_summary = generate_portfolio_summary(session_id) if session_id else {'columns': [], 'rows': [], 'portfolio_total': 0}
                
                detection_dict = {
                    'count_type': detection_result.count_type.value,
                    'instrument_count': detection_result.instrument_count,
                    'instrument_type': detection_result.instrument_type,
                    'confidence': detection_result.confidence,
                    'reasoning': detection_result.reasoning,
                    'recommended_workflow': detection_result.recommended_workflow
                }
                
                return jsonify({
                    'success': True,
                    'is_multi_instrument': False,
                    'instrument_type': instrument_type,
                    'detection': detection_dict,
                    'data': result,
                    'instrument_summary': instrument_summary,
                    'portfolio_summary': portfolio_summary
                })
        except Exception as e:
            print(f"❌ Comprehensive calculation error: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/detect-instrument', methods=['POST', 'OPTIONS'])
    def detect_instrument_endpoint():
        """Detect instrument type and count from data."""
        if request.method == 'OPTIONS':
            return '', 200
        
        try:
            payload = request.get_json()
            if isinstance(payload, str):
                import json
                payload = json.loads(payload)
            if not payload:
                payload = {}
        except:
            payload = {}
        
        data = payload.get('data', [])
        fields = payload.get('fields', [])
        
        detector = create_instrument_detector()
        
        if data:
            detection_result = detector.detect_from_data(data)
        elif fields:
            detection_result = detector.detect_from_fields(fields)
        else:
            return jsonify({
                'success': False,
                'message': 'No data or fields provided for detection'
            }), 400
        
        workflow_requirements = detector.get_workflow_requirements(detection_result)
        
        return jsonify({
            'success': True,
            'data': {
                'count_type': detection_result.count_type.value,
                'instrument_count': detection_result.instrument_count,
                'instrument_type': detection_result.instrument_type,
                'confidence': detection_result.confidence,
                'reasoning': detection_result.reasoning,
                'recommended_workflow': detection_result.recommended_workflow,
                'workflow_requirements': workflow_requirements
            }
        })

    @app.route('/api/suggest-mapping', methods=['POST', 'OPTIONS'])
    def suggest_mapping_endpoint():
        """Suggest field mappings for a given instrument type."""
        if request.method == 'OPTIONS':
            return '', 200
        
        try:
            payload = request.get_json()
            if isinstance(payload, str):
                import json
                payload = json.loads(payload)
            if not payload:
                payload = {}
        except:
            payload = {}
        
        source_fields = payload.get('source_fields', [])
        instrument_type = payload.get('instrument_type', 'money-market')
        
        # Normalize instrument type
        inst_type = normalize_instrument_type(instrument_type)
        
        # Map to InstrumentType enum
        type_mapping = {
            'money-market': InstrumentType.MONEY_MARKET,
            'tbills': InstrumentType.TBILLS,
            'bonds': InstrumentType.BONDS
        }
        
        enum_type = type_mapping.get(inst_type, InstrumentType.MONEY_MARKET)
        
        mapping_engine = create_field_mapping_engine()
        mappings = mapping_engine.suggest_mapping(source_fields, enum_type)
        
        # Convert to serializable format
        serializable_mappings = {}
        for target_field, field_mapping in mappings.items():
            serializable_mappings[target_field] = {
                'target_field': field_mapping.target_field,
                'source_field': field_mapping.source_field,
                'confidence': field_mapping.confidence,
                'aliases': field_mapping.aliases,
                'semantic_category': field_mapping.semantic_category
            }
        
        # Validate the mapping
        available_fields = {field: None for field in source_fields}
        validation = mapping_engine.validate_mapping(mappings, enum_type)
        
        return jsonify({
            'success': True,
            'data': {
                'mappings': serializable_mappings,
                'validation': {
                    'is_valid': validation[0],
                    'missing_fields': validation[1],
                    'warnings': validation[2]
                }
            }
        })

    @app.route('/api/validate-dependencies', methods=['POST', 'OPTIONS'])
    def validate_dependencies_endpoint():
        """Validate calculation dependencies for given fields."""
        if request.method == 'OPTIONS':
            return '', 200
        
        try:
            payload = request.get_json()
            if isinstance(payload, str):
                import json
                payload = json.loads(payload)
            if not payload:
                payload = {}
        except:
            payload = {}
        
        available_fields = payload.get('available_fields', {})
        instrument_type = payload.get('instrument_type', 'money-market')
        calculation_name = payload.get('calculation_name')  # Optional
        
        # Normalize instrument type
        inst_type = normalize_instrument_type(instrument_type)
        
        dependency_engine = create_calculation_dependency_engine()
        
        if calculation_name:
            # Validate specific calculation
            validation = dependency_engine.validate_calculation(
                calculation_name, available_fields, inst_type
            )
            return jsonify({
                'success': True,
                'data': {
                    'calculation_name': validation.calculation_name,
                    'status': validation.status.value,
                    'can_calculate': validation.can_calculate,
                    'missing_fields': validation.missing_fields,
                    'invalid_fields': validation.invalid_fields,
                    'warnings': validation.warnings,
                    'required_fields': validation.required_fields,
                    'optional_fields': validation.optional_fields
                }
            })
        else:
            # Validate all calculations
            validations = dependency_engine.validate_all_calculations(
                available_fields, inst_type
            )
            
            serializable_validations = {}
            for calc_name, validation in validations.items():
                serializable_validations[calc_name] = {
                    'status': validation.status.value,
                    'can_calculate': validation.can_calculate,
                    'missing_fields': validation.missing_fields,
                    'invalid_fields': validation.invalid_fields,
                    'warnings': validation.warnings
                }
            
            available_calcs = dependency_engine.get_available_calculations(
                available_fields, inst_type
            )
            
            return jsonify({
                'success': True,
                'data': {
                    'all_validations': serializable_validations,
                    'available_calculations': available_calcs
                }
            })


def auto_detect_instrument_type(inputs: dict) -> str:
    if inputs.get('discount_rate') and not inputs.get('coupon_rate'):
        return 'tbills'
    if inputs.get('coupon_rate') and inputs.get('years_to_maturity'):
        return 'bonds'
    if inputs.get('interest_rate') and inputs.get('principal'):
        return 'money-market'
    return 'money-market'