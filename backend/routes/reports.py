import json
import os
from flask import request, jsonify, send_file
from utils.db import get_db
from datetime import datetime
import openpyxl
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
import io


def create_reports_table():
    """Create the reports table if it doesn't exist."""
    conn = get_db()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id INT AUTO_INCREMENT PRIMARY KEY,
                session_id INT NOT NULL,
                report_type VARCHAR(50),
                report_data JSON,
                file_path VARCHAR(512),
                generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            )
        """)
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Error creating reports table: {e}")
        conn.close()
        return False


def generate_appendix_data(data, instrument_type):
    """
    Generate appendix data for reports.
    Returns: appendix data structure
    """
    appendix = {
        'instrument_details': [],
        'metadata': {
            'instrument_type': instrument_type,
            'generated_at': datetime.now().isoformat(),
            'total_instruments': len(data) if data else 0
        }
    }
    
    if not data or not isinstance(data, list):
        return appendix
    
    for idx, item in enumerate(data):
        instrument_detail = {
            'index': idx + 1,
            'name': item.get('Instrument') or item.get('BondName') or item.get('TBillName') or f'Instrument {idx + 1}',
            'face_value': item.get('FaceValue') or item.get('Amount') or item.get('Principal') or 0,
            'rate': item.get('Rate') or item.get('InterestRate') or item.get('CouponRate') or item.get('DiscountRate') or 0,
            'term': item.get('Term') or item.get('YearsToMaturity') or item.get('DaysToMaturity') or 0,
            'issue_date': item.get('IssueDate') or item.get('Issue Date') or 'N/A',
            'maturity_date': item.get('MaturityDate') or item.get('Maturity') or 'N/A',
            'currency': item.get('Currency') or 'USD',
            'calculated_value': item.get('CalculatedValue') or 0,
            'difference': item.get('Difference') or 0,
            'yield': item.get('Yield') or 0
        }
        appendix['instrument_details'].append(instrument_detail)
    
    return appendix


def generate_report_excel(session_id, report_data, instrument_type):
    """
    Generate Excel report with multiple sheets including appendix.
    Returns: file path
    """
    # Create output directory if it doesn't exist
    output_dir = 'reports'
    os.makedirs(output_dir, exist_ok=True)
    
    # Create workbook
    wb = openpyxl.Workbook()
    
    # Sheet 1: Summary
    ws_summary = wb.active
    ws_summary.title = 'Summary'
    
    summary_data = report_data.get('summary', {})
    ws_summary.append(['Portfolio Summary'])
    ws_summary.append([''])
    ws_summary.append(['Total Portfolio Value', summary_data.get('total_value', 0)])
    ws_summary.append(['Number of Instruments', summary_data.get('instrument_count', 0)])
    ws_summary.append(['Average Rate (%)', summary_data.get('avg_rate', 0)])
    ws_summary.append(['Total Interest Earned', summary_data.get('total_interest', 0)])
    ws_summary.append([''])
    ws_summary.append(['Generated at', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
    
    # Sheet 2: Data
    ws_data = wb.create_sheet('Data')
    data = report_data.get('data', [])
    if data and len(data) > 0:
        headers = list(data[0].keys())
        ws_data.append(headers)
        for row in data:
            ws_data.append([row.get(h, '') for h in headers])
    
    # Sheet 3: Appendix
    ws_appendix = wb.create_sheet('Appendix')
    appendix = generate_appendix_data(data, instrument_type)
    
    ws_appendix.append(['APPENDIX: DETAILED INSTRUMENT DATA'])
    ws_appendix.append([''])
    ws_appendix.append(['Instrument Name', 'Face Value', 'Rate (%)', 'Term', 'Issue Date', 'Maturity Date', 'Currency', 'Calculated Value', 'Difference', 'Yield (%)'])
    
    for detail in appendix['instrument_details']:
        ws_appendix.append([
            detail['name'],
            detail['face_value'],
            detail['rate'],
            detail['term'],
            detail['issue_date'],
            detail['maturity_date'],
            detail['currency'],
            detail['calculated_value'],
            detail['difference'],
            detail['yield']
        ])
    
    # Save file
    file_name = f"report_{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    file_path = os.path.join(output_dir, file_name)
    wb.save(file_path)
    
    return file_path


def save_report(session_id, report_type, report_data, file_path):
    """Save report metadata to database."""
    conn = get_db()
    if not conn:
        return None
    try:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO reports (session_id, report_type, report_data, file_path) 
               VALUES (%s, %s, %s, %s)""",
            (session_id, report_type, json.dumps(report_data), file_path)
        )
        conn.commit()
        report_id = cursor.lastrowid
        cursor.close()
        conn.close()
        return report_id
    except Exception as e:
        print(f"Error saving report: {e}")
        conn.close()
        return None


def reports_routes(app):
    """Register all report routes."""
    
    # Create table on module load
    create_reports_table()
    
    @app.route('/api/report/generate', methods=['POST', 'OPTIONS'])
    def generate_report_endpoint():
        if request.method == 'OPTIONS':
            return '', 200
        
        payload = request.get_json() or {}
        session_id = payload.get('session_id')
        report_type = payload.get('report_type', 'portfolio')
        instrument_type = payload.get('instrument_type', 'money-market')
        report_data = payload.get('report_data', {})
        
        if not session_id:
            return jsonify({'success': False, 'message': 'Session ID is required'}), 400
        
        # Generate Excel file
        file_path = generate_report_excel(session_id, report_data, instrument_type)
        
        # Save to database
        report_id = save_report(session_id, report_type, report_data, file_path)
        
        if report_id:
            return jsonify({
                'success': True,
                'data': {
                    'report_id': report_id,
                    'file_path': file_path,
                    'report_type': report_type
                }
            })
        else:
            return jsonify({'success': False, 'message': 'Failed to save report'}), 500
    
    @app.route('/api/report/appendix', methods=['POST', 'OPTIONS'])
    def generate_appendix_endpoint():
        if request.method == 'OPTIONS':
            return '', 200
        
        payload = request.get_json() or {}
        data = payload.get('data', [])
        instrument_type = payload.get('instrument_type', 'money-market')
        
        appendix = generate_appendix_data(data, instrument_type)
        
        return jsonify({
            'success': True,
            'data': appendix
        })
    
    @app.route('/api/report/<int:report_id>/download', methods=['GET', 'OPTIONS'])
    def download_report(report_id):
        if request.method == 'OPTIONS':
            return '', 200
        
        conn = get_db()
        if not conn:
            return jsonify({'success': False, 'message': 'Database error'}), 500
        
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM reports WHERE id = %s", (report_id,))
            report = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if not report:
                return jsonify({'success': False, 'message': 'Report not found'}), 404
            
            file_path = report['file_path']
            
            if not os.path.exists(file_path):
                return jsonify({'success': False, 'message': 'Report file not found'}), 404
            
            return send_file(file_path, as_attachment=True, download_name=os.path.basename(file_path))
            
        except Exception as e:
            conn.close()
            return jsonify({'success': False, 'message': str(e)}), 500
    
    @app.route('/api/report/session/<int:session_id>', methods=['GET', 'OPTIONS'])
    def get_session_reports(session_id):
        if request.method == 'OPTIONS':
            return '', 200
        
        conn = get_db()
        if not conn:
            return jsonify({'success': False, 'message': 'Database error'}), 500
        
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM reports WHERE session_id = %s ORDER BY generated_at DESC", (session_id,))
            rows = cursor.fetchall()
            cursor.close()
            conn.close()
            
            reports = []
            for row in rows:
                reports.append({
                    'id': row['id'],
                    'session_id': row['session_id'],
                    'report_type': row['report_type'],
                    'file_path': row['file_path'],
                    'generated_at': row['generated_at'].isoformat() if row['generated_at'] else None
                })
            
            return jsonify({'success': True, 'data': reports})
            
        except Exception as e:
            conn.close()
            return jsonify({'success': False, 'message': str(e)}), 500
