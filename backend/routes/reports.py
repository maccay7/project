import json
import os
import re
from contextlib import contextmanager
from datetime import datetime
from flask import request, jsonify, send_file
from utils.db import get_db
from utils.fred_config import (
    FRED_API_KEY, FRED_BASE_URL, get_yield_curve,
)
import requests
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


def _to_snake_case(name):
    s = str(name).strip()
    s = re.sub(r'[\s\-]+', '_', s)
    s = re.sub(r'(?<=[a-z0-9])([A-Z])', r'_\1', s)
    return s.lower()


def _dedupe_columns(columns):
    seen = set()
    kept = []
    for col in columns:
        key = _to_snake_case(col)
        if key in seen:
            continue
        seen.add(key)
        kept.append(col)
    return kept


def _escape_html(text):
    if text is None:
        return ''
    return (str(text).replace('&', '&amp;').replace('<', '&lt;')
            .replace('>', '&gt;').replace('"', '&quot;'))


def _safe_num(v):
    try:
        f = float(v)
        if f != f:
            return None
        return f
    except (TypeError, ValueError):
        return None


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


def _load_visualisation_config(session_id, explicit_config=None):
    if explicit_config:
        return explicit_config
    if not session_id:
        return None
    with _db() as (conn, cursor):
        if not conn:
            return None
        try:
            cursor.execute(
                "SELECT visualisation_config FROM report_configurations "
                "WHERE session_id = %s LIMIT 1", (session_id,))
            row = cursor.fetchone()
        except Exception:
            return None
    if not row:
        return None
    raw = row.get('visualisation_config') if isinstance(row, dict) else (row[0] if row else None)
    if not raw:
        return None
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except Exception:
            return None
    return raw if isinstance(raw, dict) else None


def _fetch_curve_observations(config):
    curves = []
    errors = []

    if not FRED_API_KEY:
        return {'curves': [], 'errors': ['FRED_API_KEY not configured on server']}

    series_ids = config.get('series_ids') or []
    if isinstance(series_ids, str):
        series_ids = [series_ids]

    from_date = config.get('from_date')
    to_date = config.get('to_date')

    for sid in series_ids:
        try:
            params = {
                'series_id': sid,
                'api_key': FRED_API_KEY,
                'file_type': 'json',
                'sort_order': 'asc',
                'limit': 5000,
            }
            if from_date:
                params['observation_start'] = from_date
            if to_date:
                params['observation_end'] = to_date
            resp = requests.get(f'{FRED_BASE_URL}/series/observations',
                                params=params, timeout=20)
            if resp.status_code != 200:
                errors.append(f'FRED {sid}: HTTP {resp.status_code}')
                continue
            obs = resp.json().get('observations', []) or []
            pts = []
            for o in obs:
                val = _safe_num(o.get('value'))
                if val is None:
                    continue
                pts.append({'date': o.get('date'), 'value': val})
            if pts:
                curves.append({
                    'label': sid,
                    'series_id': sid,
                    'x_axis': 'date',
                    'points': pts,
                })
            else:
                errors.append(f'FRED {sid}: no observations returned')
        except Exception as e:
            errors.append(f'FRED {sid}: {e}')

    if not series_ids:
        country = config.get('country') or 'US'
        maturities = config.get('maturities') or [
            '1M', '3M', '6M', '1Y', '2Y', '5Y', '10Y', '30Y'
        ]
        inst_types = config.get('instrument_types') or ['money-market']
        inst = inst_types[0] if isinstance(inst_types, list) and inst_types else 'money-market'
        try:
            if from_date and to_date:
                for mat in maturities:
                    pts = get_yield_curve(country, from_date=from_date,
                                          to_date=to_date,
                                          instrument_type=inst,
                                          maturity=mat)
                    if pts:
                        curves.append({
                            'label': f'{country} {mat} time series',
                            'series_id': None,
                            'x_axis': 'date',
                            'points': [{'date': p['date'], 'value': p['rate']}
                                       for p in pts],
                        })
                    else:
                        errors.append(
                            f'No FRED {mat} data for {country} between '
                            f'{from_date} and {to_date}'
                        )
            else:
                pts = get_yield_curve(country, maturities=maturities,
                                      instrument_type=inst)
                if pts:
                    curves.append({
                        'label': f'{country} yield curve',
                        'series_id': None,
                        'x_axis': 'maturity',
                        'points': [{
                            'maturity': p['maturity'],
                            'maturity_label': p['maturityLabel'],
                            'value': p['rate'],
                        } for p in pts],
                    })
                else:
                    errors.append(f'No FRED curve data for {country}')
        except Exception as e:
            errors.append(f'Yield curve fetch failed: {e}')

    return {'curves': curves, 'errors': errors}


def _build_svg_line_chart(curve, width=760, height=320):
    points = [p for p in (curve.get('points') or [])
              if _safe_num(p.get('value')) is not None]
    if not points:
        return ''

    x_axis = curve.get('x_axis', 'date')
    width = int(width)
    height = int(height)
    ml, mr, mt, mb = 70, 20, 40, 60
    pw = width - ml - mr
    ph = height - mt - mb

    values = [_safe_num(p['value']) for p in points]
    vmin = min(values)
    vmax = max(values)
    if vmax - vmin < 1e-9:
        vmax = vmin + 1.0

    n = len(points)

    def x_at(i):
        return ml + (i / max(1, n - 1)) * pw

    def y_at(v):
        return mt + ph - ((v - vmin) / (vmax - vmin)) * ph

    x_labels = []
    if x_axis == 'date':
        idxs = sorted(set([0, n // 4, n // 2, (3 * n) // 4, n - 1]))
        for i in idxs:
            lbl = points[i].get('date') or ''
            x_labels.append((x_at(i), str(lbl)))
    else:
        step = max(1, n // 8)
        for i in range(0, n, step):
            lbl = points[i].get('maturity_label') or str(points[i].get('maturity', ''))
            x_labels.append((x_at(i), str(lbl)))

    y_ticks = []
    for k in range(5):
        v = vmin + (vmax - vmin) * (k / 4.0)
        y_ticks.append((y_at(v), f'{v:.2f}%'))

    path_parts = []
    for i, p in enumerate(points):
        cmd = 'M' if i == 0 else 'L'
        path_parts.append(f'{cmd} {x_at(i):.1f} {y_at(_safe_num(p["value"])):.1f}')
    path_d = ' '.join(path_parts)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" '
        f'style="background:#fff;font-family:Arial,Helvetica,sans-serif;">',
        f'<text x="{width/2:.0f}" y="22" text-anchor="middle" font-size="14" '
        f'font-weight="bold" fill="#0B2044">{_escape_html(curve.get("label") or "Yield Curve")}</text>',
    ]
    for y, lbl in y_ticks:
        parts.append(f'<line x1="{ml}" y1="{y:.1f}" x2="{ml+pw}" y2="{y:.1f}" '
                     f'stroke="#e5e7eb" stroke-width="1"/>')
        parts.append(f'<text x="{ml-6}" y="{y+3:.1f}" text-anchor="end" '
                     f'font-size="10" fill="#444">{lbl}</text>')
    parts.append(f'<line x1="{ml}" y1="{mt+ph}" x2="{ml+pw}" y2="{mt+ph}" '
                 f'stroke="#666" stroke-width="1"/>')
    parts.append(f'<line x1="{ml}" y1="{mt}" x2="{ml}" y2="{mt+ph}" '
                 f'stroke="#666" stroke-width="1"/>')
    parts.append(f'<path d="{path_d}" fill="none" stroke="#0B2044" stroke-width="2"/>')
    for i, p in enumerate(points):
        parts.append(f'<circle cx="{x_at(i):.1f}" cy="{y_at(_safe_num(p["value"])):.1f}" '
                     f'r="2" fill="#0B2044"/>')
    for x, lbl in x_labels:
        parts.append(f'<text x="{x:.1f}" y="{mt+ph+18}" text-anchor="middle" '
                     f'font-size="10" fill="#444">{_escape_html(lbl)}</text>')
    parts.append(f'<text x="{ml+pw/2:.0f}" y="{height-10}" text-anchor="middle" '
                 f'font-size="10" fill="#666">'
                 f'{"Date" if x_axis == "date" else "Maturity"}</text>')
    parts.append('</svg>')
    return ''.join(parts)


def _build_curves_html(config):
    result = _fetch_curve_observations(config)
    curves = result.get('curves') or []
    errors = result.get('errors') or []
    if not curves and not errors:
        return ''

    blocks = ['<div style="page-break-before: always; padding: 20px;">',
              '<h2 style="font-family:Arial;font-size:18px;color:#0B2044;'
              'border-bottom:2px solid #0B2044;padding-bottom:8px;">'
              'Live FRED Yield Curves</h2>']

    if curves:
        for curve in curves:
            svg = _build_svg_line_chart(curve)
            if svg:
                blocks.append(f'<div style="margin-bottom:24px;">{svg}</div>')
    else:
        blocks.append('<div style="font-family:Arial;font-size:12px;color:#666;'
                      'padding:10px;">No live FRED curves were returned for the '
                      'selected filters.</div>')

    if errors:
        blocks.append('<div style="font-family:Arial;font-size:11px;color:#b91c1c;'
                      'background:#fef2f2;padding:10px;border-radius:4px;">')
        blocks.append('<strong>FRED data warnings:</strong>'
                      '<ul style="margin:6px 0 0 16px;">')
        for e in errors:
            blocks.append(f'<li>{_escape_html(e)}</li>')
        blocks.append('</ul></div>')

    blocks.append('</div>')
    return ''.join(blocks)


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


def generate_report_excel(session_id, report_data, instrument_type,
                          visualisation_config=None):
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
        headers = _dedupe_columns(headers)

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

    if visualisation_config:
        try:
            curve_result = _fetch_curve_observations(visualisation_config)
            curves = curve_result.get('curves') or []
            errors = curve_result.get('errors') or []
            if curves or errors:
                ws_curves = wb.create_sheet('Yield Curves')
                ws_curves['A1'] = 'LIVE FRED YIELD CURVES'
                ws_curves['A1'].font = title_font
                row = 3
                for curve in curves:
                    ws_curves.cell(row=row, column=1,
                                   value=curve.get('label') or 'Curve').font = header_font
                    row += 1
                    x_axis = curve.get('x_axis', 'date')
                    x_header = 'Date' if x_axis == 'date' else 'Maturity'
                    ws_curves.cell(row=row, column=1, value=x_header).font = header_font
                    ws_curves.cell(row=row, column=2, value='Rate (%)').font = header_font
                    row += 1
                    for p in curve.get('points', []):
                        x_val = (p.get('date') if x_axis == 'date'
                                 else p.get('maturity_label', p.get('maturity')))
                        ws_curves.cell(row=row, column=1, value=x_val).font = normal_font
                        ws_curves.cell(row=row, column=2,
                                       value=p.get('value')).font = normal_font
                        row += 1
                    row += 2
                if errors:
                    row += 1
                    ws_curves.cell(row=row, column=1,
                                   value='FRED warnings:').font = header_font
                    row += 1
                    for e in errors:
                        ws_curves.cell(row=row, column=1, value=e).font = normal_font
                        row += 1
                ws_curves.column_dimensions['A'].width = 30
                ws_curves.column_dimensions['B'].width = 20
        except Exception as e:
            print(f'[reports] Failed to add live FRED curves to Excel: {e}')

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


def _inject_curves_into_html(html, visualisation_config):
    if not visualisation_config:
        return html
    curves_html = _build_curves_html(visualisation_config)
    if not curves_html:
        return html
    if '</body>' in html:
        return html.replace('</body>', curves_html + '</body>', 1)
    return html + curves_html


def generate_word_from_html(session_id, report_html, requested_name=None,
                            visualisation_config=None, allow_backend_fallback=True):
    """
    If ``allow_backend_fallback`` is True and no explicit ``visualisation_config``
    was passed, the saved session config is used to inject live FRED curves.

    If ``allow_backend_fallback`` is False, no curve is ever injected — the
    caller is responsible for including the real curves in ``report_html``.
    This is the mode the InstrumentView frontend uses (it builds real SVGs
    client-side), so we never end up with TWO curve sets (one client-rendered
    from the user's selection, one injected from stale session config).
    """
    if not _DOCX_AVAILABLE:
        raise RuntimeError("python-docx not installed. Run: pip install python-docx")
    if not _PLAYWRIGHT_AVAILABLE:
        raise RuntimeError(
            "Playwright not installed. Install with: pip install playwright && playwright install chromium"
        )

    if visualisation_config is None and allow_backend_fallback:
        visualisation_config = _load_visualisation_config(session_id)

    if visualisation_config:
        report_html = _inject_curves_into_html(report_html, visualisation_config)

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
        explicit_config = payload.get('visualisation_config')
        if not session_id:
            return jsonify({'success': False, 'message': 'Session ID is required'}), 400

        visualisation_config = explicit_config or _load_visualisation_config(session_id)

        file_path = generate_report_excel(session_id, report_data, instrument_type,
                                         visualisation_config=visualisation_config)
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

    @app.route('/api/report/curve-data', methods=['POST', 'OPTIONS'])
    def report_curve_data():
        if request.method == 'OPTIONS':
            return '', 200
        payload = request.get_json() or {}
        session_id = payload.get('session_id')
        explicit_config = payload.get('visualisation_config')
        visualisation_config = explicit_config or _load_visualisation_config(session_id)
        if not visualisation_config:
            return jsonify({'success': False,
                            'error': 'No visualisation_config supplied and no '
                                     'saved config found for this session'}), 400

        data = _fetch_curve_observations(visualisation_config)
        svg_blocks = []
        for curve in data.get('curves', []):
            svg = _build_svg_line_chart(curve)
            if svg:
                svg_blocks.append({'label': curve.get('label'), 'svg': svg})
        return jsonify({
            'success': True,
            'data': {
                'curves': data.get('curves', []),
                'errors': data.get('errors', []),
                'svg_charts': svg_blocks,
                'config': visualisation_config,
            }
        })

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
        explicit_config = payload.get('visualisation_config')
        include_live_curves = bool(payload.get('include_live_curves', False))

        if not session_id:
            return jsonify({'success': False, 'message': 'Session ID is required'}), 400
        if not report_html:
            return jsonify({'success': False, 'message': 'report_html is required'}), 400

        # Only inject backend FRED curves when the caller explicitly asks.
        # The frontend already embeds real SVGs built from the exact data the
        # user is viewing on the Visualizations page — so the default is to
        # render the client HTML as-is and avoid duplicate / stale injection.
        if include_live_curves:
            visualisation_config = explicit_config or _load_visualisation_config(session_id)
            if not visualisation_config:
                return jsonify({
                    'success': False,
                    'message': ('include_live_curves was requested but no '
                                'visualisation_config was supplied and no saved '
                                'config exists for this session.')
                }), 400
            allow_backend_fallback = True
        else:
            visualisation_config = None
            allow_backend_fallback = False

        try:
            file_path, display_name = generate_word_from_html(
                session_id, report_html, requested_name,
                visualisation_config=visualisation_config,
                allow_backend_fallback=allow_backend_fallback,
            )
            if file_path and os.path.exists(file_path):
                return jsonify({
                    'success': True,
                    'data': {'file_path': file_path, 'file_name': display_name,
                             'stored_file_name': os.path.basename(file_path),
                             'live_curves_included': include_live_curves}
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