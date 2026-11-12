#!/usr/bin/env python3
"""Portfolio validation harness.

Scans a directory of .xlsx workbooks, runs each sheet's rows through the
backend calculation engine, compares results against an adjacent
``expected.md`` file, and writes a CSV diff report.

Usage:
    python scripts/validate_portfolio.py <workbooks_dir> [--out report.csv]

Workbook layout expected:
    <dir>/my_book.xlsx
    <dir>/my_book.expected.md   (optional; absent -> rows marked NO_EXPECTED)

expected.md format (simple key: value lines, one instrument block per
sheet, sections separated by '## <sheet name>'):
    ## Sheet1
    total_value: 12345.67
    instrument_count: 3
    discount_rate: 10.65

Instrument types without a backend strategy are reported as
``SKIPPED - strategy not implemented`` rather than failing.
"""
import argparse
import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'backend'))

SUPPORTED_TYPES = {'money-market', 'money_market', 'tbills', 't-bills',
                   'treasury bill', 'bonds', 'bond'}


def load_expected(md_path: Path):
    """Parse expected.md -> {sheet_name: {field: float|str}}."""
    if not md_path.exists():
        return {}
    expected = {}
    sheet = None
    for line in md_path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        m = re.match(r'^##\s+(.+)$', line)
        if m:
            sheet = m.group(1).strip()
            expected[sheet] = {}
            continue
        m = re.match(r'^([A-Za-z_][\w .\-]*?)\s*:\s*(.+)$', line)
        if m and sheet:
            expected[sheet][m.group(1).strip().lower()] = m.group(2).strip()
    return expected


def sheet_rows(ws):
    """First row = headers; remaining non-empty rows -> dicts."""
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return []
    header = [str(h).strip() if h is not None else '' for h in rows[0]]
    out = []
    for r in rows[1:]:
        row = {header[i]: r[i] for i in range(min(len(header), len(r)))
               if header[i]}
        if any(v not in (None, '') for v in row.values()):
            out.append(row)
    return out


def classify_type(rows, sheet_name):
    blob = ' '.join([sheet_name] + [str(v) for r in rows[:5] for v in r.values() if v]).lower()
    if 'bill' in blob or 't-bill' in blob or 'treasury' in blob:
        return 'tbills'
    if 'bond' in blob or 'note' in blob:
        return 'bonds'
    if 'money' in blob or 'mm' in blob or 'yield' in blob:
        return 'money-market'
    return None


def run_workbook(xlsx_path: Path, expected):
    from openpyxl import load_workbook
    from pages.calculations_details import calculate_data

    wb = load_workbook(xlsx_path, data_only=True)
    findings = []
    for ws in wb.worksheets:
        rows = sheet_rows(ws)
        if not rows:
            continue
        inst_type = classify_type(rows, ws.title)
        if not inst_type:
            findings.append({
                'workbook': xlsx_path.name, 'sheet': ws.title,
                'instrument': '-', 'field': '-',
                'expected': '-', 'actual': 'SKIPPED - strategy not implemented',
                'status': 'SKIPPED'})
            continue
        resp = calculate_data(rows, inst_type)
        calcs = resp.get('calculations') or resp.get('instrument_results') or []
        exp_sheet = expected.get(ws.title, {})
        if not exp_sheet:
            for c in calcs:
                findings.append({
                    'workbook': xlsx_path.name, 'sheet': ws.title,
                    'instrument': c.get('instrument_name', '?'),
                    'field': '*', 'expected': '-',
                    'actual': c.get('status', '?'), 'status': 'NO_EXPECTED'})
            continue
        for c in calcs:
            for field, exp_val in exp_sheet.items():
                actual = c.get(field)
                try:
                    match = abs(float(actual) - float(exp_val)) < 0.01
                except (TypeError, ValueError):
                    match = str(actual).strip().lower() == str(exp_val).strip().lower()
                findings.append({
                    'workbook': xlsx_path.name, 'sheet': ws.title,
                    'instrument': c.get('instrument_name', '?'),
                    'field': field, 'expected': exp_val,
                    'actual': actual,
                    'status': 'MATCH' if match else 'MISMATCH'})
    return findings


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('directory', type=Path)
    ap.add_argument('--out', type=Path, default=None)
    args = ap.parse_args()

    findings = []
    for xlsx in sorted(args.directory.glob('*.xlsx')):
        expected = load_expected(xlsx.with_suffix('').with_suffix('.expected.md'))
        try:
            findings.extend(run_workbook(xlsx, expected))
        except Exception as e:  # keep harness going; report per workbook
            findings.append({
                'workbook': xlsx.name, 'sheet': '-', 'instrument': '-',
                'field': '-', 'expected': '-',
                'actual': f'ERROR: {e}', 'status': 'ERROR'})

    out = args.out or args.directory / 'validation_report.csv'
    with out.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=['workbook', 'sheet', 'instrument',
                                          'field', 'expected', 'actual', 'status'])
        w.writeheader()
        w.writerows(findings)

    counts = {}
    for f_ in findings:
        counts[f_['status']] = counts.get(f_['status'], 0) + 1
    print(f'wrote {out} — {counts}')
    return 1 if counts.get('MISMATCH') or counts.get('ERROR') else 0


if __name__ == '__main__':
    sys.exit(main())
