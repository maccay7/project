import json
import os
import re
import tempfile
from flask import request, jsonify, send_file
from utils.db import get_db
from datetime import datetime
import openpyxl
from openpyxl.styles import Font, Alignment, Border, Side
import io
from docx import Document
from docx.shared import Pt, Inches, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from playwright.sync_api import sync_playwright

# ---- Frontend URL for Playwright ----
frontend_base = os.getenv('FRONTEND_URL', 'http://localhost:3000')

# ---- A4 geometry (96 DPI) ----
A4_WIDTH_PX = 794
A4_HEIGHT_PX = 1123
SCREENSHOT_SCALE = 2  # device pixel ratio for sharpness


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
                session_id VARCHAR(64) NOT NULL,
                report_type VARCHAR(50),
                report_data JSON,
                file_path VARCHAR(512),
                generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_session_id (session_id)
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
    """Generate appendix data for reports."""
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
    """Generate Excel report with cover, summary, data, and appendix sheets.
    Uses the exact data provided without modification or recalculation."""
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
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )

    valuation_date = report_data.get('valuationDate', datetime.now().strftime('%Y-%m-%d'))

    # Sheet 1: Cover Page
    ws_cover = wb.active
    ws_cover.title = 'Cover'

    ws_cover['A1'] = 'DURA CAPITAL (PRIVATE) LIMITED'
    ws_cover['A1'].font = Font(name='Arial', size=20, bold=True, color='0B2044')
    ws_cover['A1'].alignment = center_align

    ws_cover['A3'] = 'PORTFOLIO VALUATION REPORT'
    ws_cover['A3'].font = Font(name='Arial', size=18, bold=True, color='1E88E5')
    ws_cover['A3'].alignment = center_align

    ws_cover['A5'] = f'Instrument Type: {instrument_type.replace("-", " ").upper()}'
    ws_cover['A5'].font = header_font
    ws_cover['A5'].alignment = left_align

    ws_cover['A6'] = f'Session: {report_data.get("session", "Current Session")}'
    ws_cover['A6'].font = normal_font
    ws_cover['A6'].alignment = left_align

    ws_cover['A7'] = f'Valuation Date: {valuation_date}'
    ws_cover['A7'].font = normal_font
    ws_cover['A7'].alignment = left_align

    ws_cover['A8'] = f'Report Generated: {datetime.now().strftime("%B %d, %Y at %H:%M")}'
    ws_cover['A8'].font = normal_font
    ws_cover['A8'].alignment = left_align

    ws_cover['A10'] = 'CONFIDENTIAL'
    ws_cover['A10'].font = Font(name='Arial', size=14, bold=True, color='c62828')
    ws_cover['A10'].alignment = center_align

    ws_cover.column_dimensions['A'].width = 50

    # Sheet 2: Summary
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

    ws_summary[f'A{len(metrics)+4}'] = 'Generated at'
    ws_summary[f'B{len(metrics)+4}'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    ws_summary[f'A{len(metrics)+4}'].font = normal_font
    ws_summary[f'B{len(metrics)+4}'].font = normal_font

    ws_summary.column_dimensions['A'].width = 30
    ws_summary.column_dimensions['B'].width = 20

    # Sheet 3: Data
    ws_data = wb.create_sheet('Data')
    data = report_data.get('data', [])
    if data and len(data) > 0:
        headers = list(data[0].keys())
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
            max_length = 0
            column = col[0].column_letter
            for cell in col:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except Exception:
                    pass
            adjusted_width = min(max_length + 2, 50)
            ws_data.column_dimensions[column].width = adjusted_width

    # Sheet 4: Appendix
    ws_appendix = wb.create_sheet('Appendix')
    appendix = generate_appendix_data(data, instrument_type)

    ws_appendix['A1'] = 'APPENDIX: DETAILED INSTRUMENT DATA'
    ws_appendix['A1'].font = title_font
    ws_appendix['A1'].alignment = center_align
    ws_appendix.merge_cells('A1:J1')

    appendix_headers = ['Instrument Name', 'Face Value', 'Rate (%)', 'Term', 'Issue Date', 'Maturity Date', 'Currency', 'Calculated Value', 'Difference', 'Yield (%)']
    ws_appendix.append([''])
    ws_appendix.append(appendix_headers)

    for col_idx, header in enumerate(appendix_headers, start=1):
        cell = ws_appendix.cell(row=3, column=col_idx)
        cell.font = header_font
        cell.alignment = center_align
        cell.border = thin_border

    for row_idx, detail in enumerate(appendix['instrument_details'], start=4):
        values = [
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
        ]
        for col_idx, value in enumerate(values, start=1):
            cell = ws_appendix.cell(row=row_idx, column=col_idx)
            cell.value = value
            cell.font = normal_font
            cell.alignment = left_align
            cell.border = thin_border

    ws_appendix.column_dimensions['A'].width = 25
    ws_appendix.column_dimensions['B'].width = 15
    ws_appendix.column_dimensions['C'].width = 12
    ws_appendix.column_dimensions['D'].width = 12
    ws_appendix.column_dimensions['E'].width = 15
    ws_appendix.column_dimensions['F'].width = 15
    ws_appendix.column_dimensions['G'].width = 12
    ws_appendix.column_dimensions['H'].width = 18
    ws_appendix.column_dimensions['I'].width = 15
    ws_appendix.column_dimensions['J'].width = 12

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


def _render_html_to_page_images(html: str, tmpdir: str):
    """Render HTML in headless Chromium and return paths of A4-sized PNGs,
    one image per A4 page. This is what guarantees the exported Word
    matches the Report Preview visually, page for page."""

    # Replace relative image URLs with HTTP URLs to the backend's reports directory
    output_dir = 'reports'
    
    # Replace /DuraCapital%20logo.png with backend URL
    html = html.replace('/DuraCapital%20logo.png', 'http://localhost:5000/reports/DuraCapital logo.png')
    html = html.replace('/DuraCapital logo.png', 'http://localhost:5000/reports/DuraCapital logo.png')
    
    # Replace /reportbackground.png with backend URL
    html = html.replace('/reportbackground.png', 'http://localhost:5000/reports/reportbackground.png')
    
    print(f"[reports] Replaced image URLs with backend HTTP URLs")

    # Debug: Log image URLs in HTML
    img_urls = re.findall(r'<img[^>]*src=["\']([^"\']+)["\']', html, re.IGNORECASE)
    if img_urls:
        print(f"[reports] Found {len(img_urls)} img tags with URLs: {img_urls[:3]}")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-web-security", "--disable-features=VizDisplayCompositor"]
        )
        context = browser.new_context(
            viewport={"width": A4_WIDTH_PX, "height": A4_HEIGHT_PX},
            device_scale_factor=SCREENSHOT_SCALE,
            ignore_https_errors=True,
            java_script_enabled=True,
        )
        page = context.new_page()

        # set_content uses about:blank as the document URL, so we must give
        # the page a real URL for the <base href> to work reliably.
        try:
            page.goto(f"{frontend_base}/", wait_until="domcontentloaded", timeout=15000)
        except Exception as e:
            print(f"[reports] Could not open frontend base URL ({frontend_base}): {e}")

        page.set_content(html, wait_until="networkidle")

        # Wait for the page to be fully loaded
        page.wait_for_load_state("networkidle", timeout=15000)

        # Wait for all images to load and be fully rendered
        try:
            page.wait_for_function(
                """() => {
                    const images = document.querySelectorAll('img');
                    if (images.length === 0) return true;
                    return Array.from(images).every(img => img.complete && img.naturalWidth > 0);
                }""",
                timeout=20000,
            )
            print("[reports] All images loaded successfully")
        except Exception as e:
            print(f"[reports] Warning: Image loading wait failed: {e}")

        # Let chart libraries (Chart.js, D3, etc.) finish drawing on canvas
        page.wait_for_timeout(3000)

        # Log all images and their status before screenshot
        try:
            image_status = page.evaluate(
                """() => Array.from(document.images).map(img => ({
                    src: img.src,
                    complete: img.complete,
                    naturalWidth: img.naturalWidth,
                    naturalHeight: img.naturalHeight
                }))"""
            )
            print(f"[reports] Image status before screenshot: {image_status}")
        except Exception as e:
            print(f"[reports] Could not log image status: {e}")
        try:
            page.wait_for_function(
                """() => {
                    const canvases = document.querySelectorAll('canvas');
                    if (canvases.length === 0) return true;
                    return Array.from(canvases).every(c => c.width > 0 && c.height > 0);
                }""",
                timeout=10000,
            )
        except Exception:
            pass

        # Let images finish loading (key step for background / logo)
        try:
            page.wait_for_function(
                """() => {
                    const images = Array.from(document.images);
                    if (images.length === 0) return true;
                    return images.every(img => img.complete && img.naturalWidth > 0);
                }""",
                timeout=15000,
            )
        except Exception as e:
            print(f"[reports] Warning: Image loading check failed: {e}")

        # Log loaded images for debugging
        try:
            loaded = page.evaluate(
                """() => Array.from(document.images)
                    .map(img => ({ src: img.src, complete: img.complete, naturalWidth: img.naturalWidth }))"""
            )
            print(f"[reports] Images loaded: {loaded}")
        except Exception as e:
            print(f"[reports] Warning: Could not log loaded images: {e}")

        # Let web fonts settle
        try:
            page.evaluate("() => document.fonts && document.fonts.ready")
        except Exception:
            pass

        # Wait for all images to be fully loaded and rendered
        page.wait_for_timeout(3000)

        # Force a repaint to ensure images are rendered
        try:
            page.evaluate("() => document.body.offsetHeight")
        except Exception:
            pass

        # Log any images that still failed to load (helps debugging)
        try:
            failed = page.evaluate(
                """() => Array.from(document.images)
                    .filter(img => !img.complete || img.naturalWidth === 0)
                    .map(img => img.src)"""
            )
            if failed:
                print(f"[reports] Images that failed to load: {failed}")
        except Exception:
            pass

        # Get the actual content height
        content_height = page.evaluate("document.documentElement.scrollHeight")
        
        # Calculate number of pages based on actual content
        # Only count a page if it has meaningful content (at least 20% of A4 height)
        raw_num_pages = (content_height + A4_HEIGHT_PX - 1) // A4_HEIGHT_PX
        last_page_height = content_height % A4_HEIGHT_PX if content_height % A4_HEIGHT_PX != 0 else A4_HEIGHT_PX
        
        # If the last page is less than 20% of A4 height, skip it
        if last_page_height < (A4_HEIGHT_PX * 0.2) and raw_num_pages > 1:
            num_pages = raw_num_pages - 1
        else:
            num_pages = raw_num_pages
        
        print(f"[reports] Content height: {content_height}px, Calculated pages: {num_pages}")

        page_paths = []
        for i in range(num_pages):
            y = i * A4_HEIGHT_PX
            img_path = os.path.join(tmpdir, f"page_{i}.png")
            page.screenshot(
                path=img_path,
                clip={"x": 0, "y": y, "width": A4_WIDTH_PX, "height": A4_HEIGHT_PX},
                full_page=True,
            )
            page_paths.append(img_path)

        browser.close()
        return page_paths


def generate_word_from_html(session_id: str, report_html: str) -> str:
    """Build a .docx whose pages are exact images of the given HTML,
    so the exported Word matches the Report Preview visually, page for page."""
    output_dir = 'reports'
    os.makedirs(output_dir, exist_ok=True)

    # Use a persistent directory instead of temp for debugging
    tmpdir = os.path.join(output_dir, f'tmp_{session_id}_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
    os.makedirs(tmpdir, exist_ok=True)

    try:
        page_images = _render_html_to_page_images(report_html, tmpdir)
        print(f"[reports] Generated {len(page_images)} page images in {tmpdir}")

        doc = Document()

        section = doc.sections[0]
        section.page_width = Cm(21.0)
        section.page_height = Cm(29.7)
        section.top_margin = Cm(0)
        section.bottom_margin = Cm(0)
        section.left_margin = Cm(0)
        section.right_margin = Cm(0)

        # Zero the default spacing so the picture paragraph takes no extra room
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
            # Fill the entire A4 page with the rendered image
            run.add_picture(img_path, width=Cm(21.0), height=Cm(29.7))

        file_name = f"report_{session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
        file_path = os.path.join(output_dir, file_name)
        doc.save(file_path)

        # Keep temp directory for debugging - don't delete
        print(f"[reports] Debug: Intermediate PNG files saved in {tmpdir}")

        return file_path

    except Exception as e:
        print(f"[reports] Error generating Word document: {e}")
        raise


def reports_routes(app):
    """Register all report routes."""

    create_reports_table()

    # Serve temporary images from reports directory
    @app.route('/reports/<path:filename>')
    def serve_report_image(filename):
        """Serve temporary images for Playwright rendering."""
        output_dir = 'reports'
        return send_file(os.path.join(output_dir, filename))

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

        file_path = generate_report_excel(session_id, report_data, instrument_type)
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

    @app.route('/api/report/generate-word', methods=['POST', 'OPTIONS'])
    def generate_word_report_endpoint():
        if request.method == 'OPTIONS':
            return '', 200

        payload = request.get_json() or {}
        session_id = payload.get('session_id')
        report_html = payload.get('report_html')

        if not session_id:
            return jsonify({'success': False, 'message': 'Session ID is required'}), 400
        if not report_html:
            return jsonify({'success': False, 'message': 'report_html is required'}), 400

        try:
            file_path = generate_word_from_html(session_id, report_html)

            if file_path and os.path.exists(file_path):
                return jsonify({
                    'success': True,
                    'data': {
                        'file_path': file_path,
                        'file_name': os.path.basename(file_path)
                    }
                })
            else:
                return jsonify({'success': False, 'message': 'Failed to generate Word document'}), 500

        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/report/download-word/<session_id>', methods=['GET', 'OPTIONS'])
    def download_word_report(session_id):
        if request.method == 'OPTIONS':
            return '', 200

        try:
            output_dir = 'reports'
            if not os.path.exists(output_dir):
                return jsonify({'success': False, 'message': 'Reports directory not found'}), 404

            word_files = [f for f in os.listdir(output_dir)
                          if f.startswith(f'report_{session_id}_') and f.endswith('.docx')]

            if not word_files:
                return jsonify({'success': False, 'message': 'No Word report found for this session'}), 404

            word_files.sort(reverse=True)
            latest_file = word_files[0]
            file_path = os.path.join(output_dir, latest_file)

            return send_file(file_path, as_attachment=True, download_name=latest_file)

        except Exception as e:
            print(f"Error downloading Word report: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/report/session/<session_id>', methods=['GET', 'OPTIONS'])
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

            return jsonify({'success': True,  'data': reports})

        except Exception as e:
            conn.close()
            return jsonify({'success': False, 'message': str(e)}), 500