import json
import os
import re
from contextlib import contextmanager
from datetime import datetime
from flask import request, jsonify, send_file
from utils.db import get_db
import openpyxl
from openpyxl.styles import Font, Alignment, Border, Side

try:
    from docx import Document
    from docx.shared import Pt, Cm
    _DOCX_AVAILABLE = True
except Exception:
    _DOCX_AVAILABLE = False

try:
    from playwright.sync_api import sync_playwright
    _PLAYWRIGHT_AVAILABLE = True
except Exception:
    _PLAYWRIGHT_AVAILABLE = False

frontend_base = os.getenv('FRONTEND_URL', 'http://localhost:3000')

A4_WIDTH_PX = 794
A4_HEIGHT_PX = 1123
SCREENSHOT_SCALE = 2

_SUMMARY_EXPORT_EXCLUDED = {
    "Bond-Equivalent Yield", "Currency", "Effective Annual Rate",
    "Maturity Value", "Total Interest",
    "bond_equivalent_yield", "currency", "effective_annual_rate",
    "maturity_value", "total_interest",
}


@contextmanager
def _db():
    conn = get_db()
    cursor = None
    if conn:
        try:
            cursor = conn.cursor()
        except Exception:
            try:
                conn.close()
            except Exception:
                pass
            conn = None
    try:
        yield conn, cursor
    finally:
        if cursor:
            try:
                cursor.close()
            except Exception:
                pass
        if conn:
            try:
                conn.close()
            except Exception:
                pass


def _safe_session_id(session_id):
    if session_id is None:
        return 'unknown'
    s = str(session_id).strip()
    s = re.sub(r'[^A-Za-z0-9_\-\.]', '_', s)
    s = s.replace('..', '_')
    return s or 'unknown'


def _safe_filename(requested_name, fallback):
    if not requested_name:
        return fallback
    base = os.path.basename(str(requested_name).strip())
    base = re.sub(r'[^A-Za-z0-9_\-\. ]', '_', base)
    base = base.replace('..', '_')
    if not base.lower().endswith('.docx'):
        base = base + '.docx'
    return base or fallback


def create_reports_table():
    with _db() as (conn, cursor):
        if not conn:
            return False
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reports (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    session_id VARCHAR(64) NOT NULL,
                    report_type VARCHAR(50),
                    report_data JSON,
                    file_path VARCHAR(512),
                    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_session_id (session_id)
                )
            """)
            conn.commit()
            return True
        except Exception as e:
            print(f"Error creating reports table: {e}")
            return False


def _pick(item, *keys):
    for key in keys:
        v = item.get(key)
        if v not in (None, ""):
            return v
    return None


def generate_appendix_data(data, instrument_type):
    appendix = {
        'instrument_details': [],
        'metadata': {
            'instrument_type': instrument_type,
            'generated_at': datetime.now().isoformat(),
            'total_instruments': len(data) if isinstance(data, list) else 0,
        }
    }

    if not data or not isinstance(data, list):
        return appendix

    for idx, item in enumerate(data):
        appendix['instrument_details'].append({
            'index': idx + 1,
            'name': (_pick(item, 'instrument_name', 'instrumentName', 'Instrument',
                           'BondName', 'TBillName') or f'Instrument {idx + 1}'),
            'face_value': (_pick(item, 'face_value', 'faceValue', 'FaceValue',
                                 'Principal', 'Amount') or 0),
            'rate': (_pick(item, 'coupon_rate', 'couponRate', 'interest_rate',
                           'interestRate', 'discount_rate', 'Rate', 'InterestRate',
                           'CouponRate', 'DiscountRate') or 0),
            'term': (_pick(item, 'years_to_maturity', 'yearsToMaturity', 'term_days',
                           'termDays', 'Term', 'YearsToMaturity', 'DaysToMaturity') or 0),
            'issue_date': (_pick(item, 'issue_date', 'issueDate', 'IssueDate', 'Issue Date') or 'N/A'),
            'maturity_date': (_pick(item, 'maturity_date', 'maturityDate',
                                    'MaturityDate', 'Maturity') or 'N/A'),
            'currency': (_pick(item, 'currency', 'Currency') or ''),
            'calculated_value': (_pick(item, 'total_value', 'totalValue',
                                       'current_price', 'currentPrice',
                                       'CalculatedValue') or 0),
            'difference': (_pick(item, 'difference', 'Difference') or 0),
            'yield': (_pick(item, 'yield_to_maturity', 'yieldToMaturity',
                            'bond_equivalent_yield', 'bondEquivalentYield',
                            'Yield') or 0),
        })

    return appendix


def generate_report_excel(session_id, report_data, instrument_type):
    output_dir = 'reports'
    os.makedirs(output_dir, exist_ok=True)

    wb = openpyxl.Workbook()
    title_font = Font(name='Arial', size=16, bold=True, color='0B2044')
    header_font = Font(name='Arial', size=12, bold=True, color='0B2044')
    normal_font = Font(name='Arial', size=10)
    center_align = Alignment(horizontal='center', vertical='center')
    left_align = Alignment(horizontal='left', vertical='center')
    wrap_align = Alignment(horizontal='left', vertical='top', wrap_text=True)
    thin_border = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin')
    )

    valuation_date = report_data.get('valuationDate',
                                     datetime.now().strftime('%Y-%m-%d'))

    ws_cover = wb.active
    ws_cover.title = 'Cover'
    ws_cover['A1'] = 'DURA CAPITAL (PRIVATE) LIMITED'
    ws_cover['A1'].font = Font(name='Arial', size=20, bold=True, color='0B2044')
    ws_cover['A1'].alignment = center_align
    ws_cover['A3'] = 'PORTFOLIO VALUATION REPORT'
    ws_cover['A3'].font = Font(name='Arial', size=18, bold=True, color='1E88E5')
    ws_cover['A3'].alignment = center_align
    ws_cover['A5'] = f'Instrument Type: {str(instrument_type).replace("-", " ").upper()}'
    ws_cover['A5'].font = header_font
    ws_cover['A6'] = f'Session: {report_data.get("session", "Current Session")}'
    ws_cover['A6'].font = normal_font
    ws_cover['A7'] = f'Valuation Date: {valuation_date}'
    ws_cover['A7'].font = normal_font
    ws_cover['A8'] = f'Report Generated: {datetime.now().strftime("%B %d, %Y at %H:%M")}'
    ws_cover['A8'].font = normal_font
    ws_cover['A10'] = 'CONFIDENTIAL'
    ws_cover['A10'].font = Font(name='Arial', size=14, bold=True, color='c62828')
    ws_cover['A10'].alignment = center_align
    ws_cover.column_dimensions['A'].width = 50

    ws_summary = wb.create_sheet('Summary')
    summary_data = report_data.get('summary', {})
    ws_summary['A1'] = 'PORTFOLIO SUMMARY'
    ws_summary['A1'].font = title_font
    ws_summary['A1'].alignment = center_align
    ws_summary.merge_cells('A1:B1')
    ws_summary['A3'] = 'Metric'
    ws_summary['B3'] = 'Value'
    ws_summary['A3'].font = header_font
    ws_summary['B3'].font = header_font
    ws_summary['A3'].alignment = center_align
    ws_summary['B3'].alignment = center_align

    metrics = [
        ('Total Portfolio Value', summary_data.get('total_value', 0)),
        ('Number of Instruments', summary_data.get('instrument_count', 0)),
        ('Average Rate (%)', summary_data.get('avg_rate', 0)),
        ('Total Interest Earned', summary_data.get('total_interest', 0)),
        ('Total Principal', summary_data.get('total_principal', 0)),
    ]
    for idx, (label, value) in enumerate(metrics, start=4):
        ws_summary[f'A{idx}'] = label
        ws_summary[f'B{idx}'] = value
        ws_summary[f'A{idx}'].font = normal_font
        ws_summary[f'B{idx}'].font = normal_font
        ws_summary[f'A{idx}'].alignment = left_align
        ws_summary[f'B{idx}'].alignment = left_align
    tail = len(metrics) + 4
    ws_summary[f'A{tail}'] = 'Generated at'
    ws_summary[f'B{tail}'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    ws_summary[f'A{tail}'].font = normal_font
    ws_summary[f'B{tail}'].font = normal_font
    ws_summary.column_dimensions['A'].width = 30
    ws_summary.column_dimensions['B'].width = 20

    ws_data = wb.create_sheet('Data')
    data = report_data.get('data', [])
    if data and len(data) > 0:
        raw_headers = list(data[0].keys())
        headers = [h for h in raw_headers if h not in _SUMMARY_EXPORT_EXCLUDED]

        ws_data.append(headers)
        for col_idx, header in enumerate(headers, start=1):
            cell = ws_data.cell(row=1, column=col_idx)
            cell.font = header_font
            cell.alignment = center_align
            cell.border = thin_border

        for row_idx, row in enumerate(data, start=2):
            for col_idx, header in enumerate(headers, start=1):
                cell = ws_data.cell(row=row_idx, column=col_idx)
                cell.value = row.get(header, '')
                cell.font = normal_font
                cell.alignment = wrap_align
                cell.border = thin_border

        for col in ws_data.columns:
            column = col[0].column_letter
            max_length = 0
            for cell in col:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except Exception:
                    pass
            ws_data.column_dimensions[column].width = min(max_length + 2, 50)

    ws_appendix = wb.create_sheet('Appendix')
    appendix = generate_appendix_data(data, instrument_type)
    ws_appendix['A1'] = 'APPENDIX: DETAILED INSTRUMENT DATA'
    ws_appendix['A1'].font = title_font
    ws_appendix['A1'].alignment = center_align
    ws_appendix.merge_cells('A1:J1')

    appendix_headers = ['Instrument Name', 'Face Value', 'Rate (%)', 'Term',
                        'Issue Date', 'Maturity Date', 'Currency',
                        'Calculated Value', 'Difference', 'Yield (%)']
    ws_appendix.append([''])
    ws_appendix.append(appendix_headers)
    for col_idx, header in enumerate(appendix_headers, start=1):
        cell = ws_appendix.cell(row=3, column=col_idx)
        cell.font = header_font
        cell.alignment = center_align
        cell.border = thin_border

    for row_idx, detail in enumerate(appendix['instrument_details'], start=4):
        values = [detail['name'], detail['face_value'], detail['rate'],
                  detail['term'], detail['issue_date'], detail['maturity_date'],
                  detail['currency'], detail['calculated_value'],
                  detail['difference'], detail['yield']]
        for col_idx, value in enumerate(values, start=1):
            cell = ws_appendix.cell(row=row_idx, column=col_idx)
            cell.value = value
            cell.font = normal_font
            cell.alignment = left_align
            cell.border = thin_border

    widths = [25, 15, 12, 12, 15, 15, 12, 18, 15, 12]
    for letter, width in zip('ABCDEFGHIJ', widths):
        ws_appendix.column_dimensions[letter].width = width

    for sheet in wb.worksheets:
        sheet.page_setup.paperSize = sheet.PAPERSIZE_A4
        sheet.page_setup.orientation = sheet.ORIENTATION_PORTRAIT
        sheet.page_setup.fitToPage = True
        sheet.page_setup.fitToHeight = 0
        sheet.page_setup.fitToWidth = 1
        sheet.page_margins.left = 0.5
        sheet.page_margins.right = 0.5
        sheet.page_margins.top = 0.5
        sheet.page_margins.bottom = 0.5

    file_name = f"report_{_safe_session_id(session_id)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    file_path = os.path.join(output_dir, file_name)
    wb.save(file_path)
    return file_path


def save_report(session_id, report_type, report_data, file_path):
    with _db() as (conn, cursor):
        if not conn:
            return None
        try:
            cursor.execute(
                """INSERT INTO reports (session_id, report_type, report_data, file_path)
                   VALUES (%s, %s, %s, %s)""",
                (session_id, report_type, json.dumps(report_data), file_path)
            )
            conn.commit()
            return cursor.lastrowid
        except Exception as e:
            print(f"Error saving report: {e}")
            return None


def _render_html_to_page_images(html, tmpdir):
    if not _PLAYWRIGHT_AVAILABLE:
        raise RuntimeError(
            "Playwright not installed. Install with: pip install playwright && playwright install chromium"
        )

    html = html.replace('/DuraCapital%20logo.png',
                        'http://localhost:5000/reports/DuraCapital logo.png')
    html = html.replace('/DuraCapital logo.png',
                        'http://localhost:5000/reports/DuraCapital logo.png')
    html = html.replace('/reportbackground.png',
                        'http://localhost:5000/reports/reportbackground.png')

    with sync_playwright() as p:
        browser = p.chromium.launch(
            args=["--no-sandbox", "--disable-dev-shm-usage",
                  "--disable-web-security", "--disable-features=VizDisplayCompositor"]
        )
        context = browser.new_context(
            viewport={"width": A4_WIDTH_PX, "height": A4_HEIGHT_PX},
            device_scale_factor=SCREENSHOT_SCALE,
            ignore_https_errors=True,
            java_script_enabled=True,
        )
        page = context.new_page()

        try:
            page.goto(f"{frontend_base}/", wait_until="domcontentloaded", timeout=15000)
        except Exception as e:
            print(f"[reports] Could not open frontend base URL: {e}")

        page.set_content(html, wait_until="networkidle")
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass

        try:
            page.wait_for_function(
                "() => Array.from(document.images).every(i => i.complete && i.naturalWidth > 0)",
                timeout=20000,
            )
        except Exception:
            pass

        page.wait_for_timeout(2000)

        try:
            page.evaluate("() => document.fonts && document.fonts.ready")
        except Exception:
            pass

        content_height = page.evaluate("document.documentElement.scrollHeight")
        raw_pages = (content_height + A4_HEIGHT_PX - 1) // A4_HEIGHT_PX
        last_height = content_height % A4_HEIGHT_PX or A4_HEIGHT_PX
        num_pages = raw_pages - 1 if (last_height < A4_HEIGHT_PX * 0.2 and raw_pages > 1) else raw_pages

        page_paths = []
        for i in range(num_pages):
            img_path = os.path.join(tmpdir, f"page_{i}.png")
            page.screenshot(
                path=img_path,
                clip={"x": 0, "y": i * A4_HEIGHT_PX,
                      "width": A4_WIDTH_PX, "height": A4_HEIGHT_PX},
                full_page=True,
            )
            page_paths.append(img_path)

        browser.close()
        return page_paths


def generate_word_from_html(session_id, report_html, requested_name=None):
    if not _DOCX_AVAILABLE:
        raise RuntimeError("python-docx not installed. Run: pip install python-docx")
    if not _PLAYWRIGHT_AVAILABLE:
        raise RuntimeError(
            "Playwright not installed. Install with: pip install playwright && playwright install chromium"
        )

    output_dir = 'reports'
    os.makedirs(output_dir, exist_ok=True)
    safe_sid = _safe_session_id(session_id)
    tmpdir = os.path.join(output_dir,
                          f'tmp_{safe_sid}_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
    os.makedirs(tmpdir, exist_ok=True)

    page_images = _render_html_to_page_images(report_html, tmpdir)

    doc = Document()
    section = doc.sections[0]
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(0)
    section.bottom_margin = Cm(0)
    section.left_margin = Cm(0)
    section.right_margin = Cm(0)

    normal = doc.styles['Normal']
    normal.font.name = 'Arial'
    normal.font.size = Pt(1)
    normal.paragraph_format.space_before = Pt(0)
    normal.paragraph_format.space_after = Pt(0)
    normal.paragraph_format.line_spacing = 1.0

    for idx, img_path in enumerate(page_images):
        if idx > 0:
            doc.add_page_break()
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.line_spacing = 1.0
        run = p.add_run()
        run.font.size = Pt(1)
        run.add_picture(img_path, width=Cm(21.0), height=Cm(29.7))

    internal_name = f"report_{safe_sid}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
    file_path = os.path.join(output_dir, internal_name)
    doc.save(file_path)

    display_name = _safe_filename(requested_name, internal_name)
    return file_path, display_name


def reports_routes(app):
    create_reports_table()

    @app.route('/reports/<path:filename>')
    def serve_report_image(filename):
        output_dir = os.path.abspath('reports')
        requested = os.path.abspath(os.path.join(output_dir, filename))
        if not requested.startswith(output_dir + os.sep) and requested != output_dir:
            return jsonify({'success': False, 'message': 'Invalid path'}), 400
        if not os.path.isfile(requested):
            return jsonify({'success': False, 'message': 'File not found'}), 404
        return send_file(requested)

    @app.route('/api/report/generate', methods=['POST', 'OPTIONS'])
    def generate_report_endpoint():
        if request.method == 'OPTIONS':
            return '', 200
        payload = request.get_json() or {}
        session_id = payload.get('session_id')
        report_type = payload.get('report_type', 'portfolio')
        instrument_type = payload.get('instrument_type') or 'portfolio'
        report_data = payload.get('report_data', {})
        if not session_id:
            return jsonify({'success': False, 'message': 'Session ID is required'}), 400

        file_path = generate_report_excel(session_id, report_data, instrument_type)
        report_id = save_report(session_id, report_type, report_data, file_path)
        if report_id:
            return jsonify({
                'success': True,
                'data': {'report_id': report_id, 'file_path': file_path,
                         'report_type': report_type}
            })
        return jsonify({'success': False, 'message': 'Failed to save report'}), 500

    @app.route('/api/report/appendix', methods=['POST', 'OPTIONS'])
    def generate_appendix_endpoint():
        if request.method == 'OPTIONS':
            return '', 200
        payload = request.get_json() or {}
        appendix = generate_appendix_data(
            payload.get('data', []),
            payload.get('instrument_type') or 'portfolio',
        )
        return jsonify({'success': True, 'data': appendix})

    @app.route('/api/report/<int:report_id>/download', methods=['GET', 'OPTIONS'])
    def download_report(report_id):
        if request.method == 'OPTIONS':
            return '', 200
        with _db() as (conn, cursor):
            if not conn:
                return jsonify({'success': False, 'message': 'Database error'}), 500
            try:
                cursor.execute("SELECT * FROM reports WHERE id = %s", (report_id,))
                report = cursor.fetchone()
            except Exception as e:
                return jsonify({'success': False, 'message': str(e)}), 500
        if not report:
            return jsonify({'success': False, 'message': 'Report not found'}), 404
        file_path = report['file_path']
        if not os.path.exists(file_path):
            return jsonify({'success': False, 'message': 'Report file not found'}), 404
        return send_file(file_path, as_attachment=True,
                         download_name=os.path.basename(file_path))

    @app.route('/api/report/generate-word', methods=['POST', 'OPTIONS'])
    def generate_word_report_endpoint():
        if request.method == 'OPTIONS':
            return '', 200
        payload = request.get_json() or {}
        session_id = payload.get('session_id')
        report_html = payload.get('report_html')
        requested_name = payload.get('file_name')
        if not session_id:
            return jsonify({'success': False, 'message': 'Session ID is required'}), 400
        if not report_html:
            return jsonify({'success': False, 'message': 'report_html is required'}), 400

        try:
            file_path, display_name = generate_word_from_html(
                session_id, report_html, requested_name
            )
            if file_path and os.path.exists(file_path):
                return jsonify({
                    'success': True,
                    'data': {'file_path': file_path, 'file_name': display_name,
                             'stored_file_name': os.path.basename(file_path)}
                })
            return jsonify({'success': False, 'message': 'Failed to generate Word document'}), 500
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/report/download-word/<session_id>', methods=['GET', 'OPTIONS'])
    def download_word_report(session_id):
        if request.method == 'OPTIONS':
            return '', 200
        output_dir = 'reports'
        if not os.path.exists(output_dir):
            return jsonify({'success': False, 'message': 'Reports directory not found'}), 404

        safe_sid = _safe_session_id(session_id)
        prefix = f'report_{safe_sid}_'
        word_files = [f for f in os.listdir(output_dir)
                      if f.startswith(prefix) and f.endswith('.docx')]
        if not word_files:
            return jsonify({'success': False,
                            'message': 'No Word report found for this session'}), 404

        word_files.sort(reverse=True)
        file_path = os.path.join(output_dir, word_files[0])
        requested = request.args.get('name')
        download_name = (_safe_filename(requested, word_files[0])
                         if requested else word_files[0])
        return send_file(file_path, as_attachment=True, download_name=download_name)

    @app.route('/api/report/session/<session_id>', methods=['GET', 'OPTIONS'])
    def get_session_reports(session_id):
        if request.method == 'OPTIONS':
            return '', 200
        with _db() as (conn, cursor):
            if not conn:
                return jsonify({'success': False, 'message': 'Database error'}), 500
            try:
                cursor.execute(
                    "SELECT * FROM reports WHERE session_id = %s ORDER BY generated_at DESC",
                    (session_id,)
                )
                rows = cursor.fetchall()
            except Exception as e:
                return jsonify({'success': False, 'message': str(e)}), 500
        reports = []
        for row in rows:
            reports.append({
                'id': row['id'],
                'session_id': row['session_id'],
                'report_type': row['report_type'],
                'file_path': row['file_path'],
                'generated_at': row['generated_at'].isoformat() if row['generated_at'] else None,
            })
        return jsonify({'success': True, 'data': reports})