"""Integration coverage for the saved session → portfolio summary contract."""

import uuid
import os
from contextlib import contextmanager
from io import BytesIO
from time import perf_counter

import pytest
from openpyxl import Workbook
from app import app
from routes import calculations as calculation_routes, dataset as dataset_routes
from routes import reports as report_routes
from routes import sessions as session_routes, version_history as version_routes


@pytest.fixture(autouse=True)
def authenticate_integration_test_user(monkeypatch):
    authenticated_user = lambda: (1, None)
    monkeypatch.setattr(session_routes, 'resolve_current_user', authenticated_user)
    monkeypatch.setattr(calculation_routes, 'resolve_current_user', authenticated_user)
    monkeypatch.setattr(dataset_routes, '_authenticated_user', lambda: (1, None))
    monkeypatch.setattr(report_routes, 'resolve_current_user', authenticated_user)
    monkeypatch.setattr(version_routes, 'resolve_current_user', authenticated_user)


def test_session_calculations_feed_saved_portfolio_and_report_selection(monkeypatch):
    """Each instrument type is saved once and remains isolated to its session."""
    # Core valuations must not call FRED synchronously; benchmarks are optional
    # and fetched independently after calculation results are available.
    def reject_synchronous_benchmark(*_args):
        raise AssertionError('Core calculation endpoint attempted FRED I/O')

    monkeypatch.setattr(calculation_routes, '_fetch_benchmark', reject_synchronous_benchmark)
    monkeypatch.setattr(calculation_routes, '_attach_fred', reject_synchronous_benchmark)
    session_id = f"portfolio-flow-{uuid.uuid4()}"
    client = app.test_client()
    report_path = None
    session_deleted = False
    uploaded_dataset_id = None

    payloads = {
        'money-market': {
            'principal': 100_000,
            'interest_rate': 5,
            'term_days': 90,
        },
        'tbills': {
            'face_value': 100_000,
            'discount_rate': 5,
            'term_days': 90,
        },
        'bonds': {
            'face_value': 100_000,
            'coupon_rate': 6,
            'years_to_maturity': 5,
            'coupon_frequency': 2,
            'price': 100_000,
        },
    }

    try:
        saved_workflows = {
            'money-market': {
                'cleanedData': [{'Principal': 125000, 'Interest Rate': 4.25}],
                'includedFields': ['Principal', 'Interest Rate'],
                'excludedFields': ['Unused Column'],
            }
        }
        response = client.post('/api/sessions/save', json={
            'session_id': session_id,
            'name': 'Portfolio flow integration test',
            'instrument_workflows': saved_workflows,
            'worksheets': {'MM Worksheet': {'sheetName': 'MM Worksheet'}},
            'workbookName': 'portfolio.xlsx',
        })
        assert response.status_code == 200
        assert response.get_json()['success'] is True

        restored = client.post('/api/sessions/get', json={'session_id': session_id})
        assert restored.status_code == 200
        restored_data = restored.get_json()['data']
        assert restored_data['instrument_workflows'] == saved_workflows
        assert restored_data['worksheets'] == {
            'MM Worksheet': {'sheetName': 'MM Worksheet'}
        }
        assert restored_data['workbookName'] == 'portfolio.xlsx'

        restore_snapshot = {
            'money-market': {
                'cleanedData': [{'Principal': 150000, 'Interest Rate': 4.5}],
                'includedFields': ['Principal', 'Interest Rate'],
                'excludedFields': [],
            }
        }
        version = client.post('/api/version', json={
            'session_id': session_id,
            'instrument_type': 'money-market',
            'dataset_snapshot': restore_snapshot,
        })
        assert version.status_code == 200
        version_id = version.get_json()['version_id']
        restored_version = client.post(f'/api/version/{version_id}/restore')
        assert restored_version.status_code == 200
        restored_after_version = client.post(
            '/api/sessions/get', json={'session_id': session_id}
        )
        assert restored_after_version.get_json()['data']['instrument_workflows'] == (
            restore_snapshot
        )

        dataset_name = f"persistence-{uuid.uuid4()}.xlsx"
        saved_dataset = client.post('/api/save-dataset', json={
            'name': dataset_name,
            'data': [{'Principal': 125000, 'Interest Rate': 4.25}],
            'headers': ['Principal', 'Interest Rate'],
            'sheet_names': ['MM Worksheet'],
            'instrument_type': 'money-market',
        })
        assert saved_dataset.status_code == 200
        dataset_id = saved_dataset.get_json()['data']['id']
        loaded_dataset = client.post('/api/load-dataset', json={
            'dataset_id': dataset_id,
        })
        assert loaded_dataset.status_code == 200
        assert loaded_dataset.get_json()['data']['data'] == [
            {'Principal': 125000, 'Interest Rate': 4.25}
        ]
        deleted_dataset = client.post('/api/delete-dataset', json={
            'dataset_id': dataset_id,
        })
        assert deleted_dataset.status_code == 200

        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = 'MM Worksheet'
        worksheet.append(['Principal', 'Interest Rate'])
        worksheet.append([125000, 4.25])
        workbook_buffer = BytesIO()
        workbook.save(workbook_buffer)
        workbook_buffer.seek(0)
        uploaded = client.post(
            '/api/dataset/upload',
            data={
                'file': (workbook_buffer, f'{session_id}.xlsx'),
                'instrument_type': 'money-market',
                'session_id': session_id,
            },
            content_type='multipart/form-data',
        )
        assert uploaded.status_code == 200
        uploaded_data = uploaded.get_json()['data']
        uploaded_dataset_id = uploaded_data['dataset_id']
        assert uploaded_data['metadata']['sheet_names'] == ['MM Worksheet']

        parsed_workbook = client.get(
            f'/api/dataset/{uploaded_dataset_id}/parse'
        )
        assert parsed_workbook.status_code == 200
        parsed_sheet = parsed_workbook.get_json()['data']['sheets'][0]
        assert parsed_sheet['headers'] == ['Principal', 'Interest Rate']
        assert parsed_sheet['data'] == [
            {'Principal': 125000, 'Interest Rate': 4.25}
        ]
        deleted_upload = client.delete(
            f'/api/dataset/{uploaded_dataset_id}'
        )
        assert deleted_upload.status_code == 200
        uploaded_dataset_id = None

        for instrument_type, row in payloads.items():
            started = perf_counter()
            calculation = client.post(f'/api/calculate/{instrument_type}', json={
                'session_id': session_id,
                'currency': 'USD',
                'valuationDate': '2026-01-01',
                'data': [row],
            })
            assert perf_counter() - started < 5
            assert calculation.status_code == 200
            calculation_data = calculation.get_json()
            assert calculation_data['success'] is True

            result = calculation_data['data']
            calculation_rows = result.get('calculations', [])
            assert calculation_rows
            assert calculation_rows[0]['status'] == 'success'

            aggregate = {
                **(result.get('aggregates') or {}),
                'currency': 'USD',
                'valuationDate': '2026-01-01',
                'calculationStatus': 'success',
                'successfulCount': 1,
                'failedCount': 0,
            }
            details = [{
                'Instrument Name': calculation_rows[0].get('instrument_name') or instrument_type,
                'Instrument Type': instrument_type,
                'Currency': 'USD',
                'Valuation Date': '2026-01-01',
                'Calculation Status': calculation_rows[0]['status'],
                **calculation_rows[0],
            }]
            save_summary = client.post('/api/portfolio/summary', json={
                'session_id': session_id,
                'instrument_type': instrument_type,
                'instrument_name': instrument_type,
                'total_value': aggregate.get('total_value', 0),
                'face_value': aggregate.get('total_principal', aggregate.get('face_value', 0)),
                'count': 1,
                'avg_rate': aggregate.get('avg_rate', 0),
                'details': details,
                'detail_headers': list(details[0]),
                'aggregate': aggregate,
                'valuation_date': '2026-01-01',
            })
            assert save_summary.status_code == 200
            assert save_summary.get_json()['success'] is True

        saved = client.get(f'/api/portfolio/summary/{session_id}')
        assert saved.status_code == 200
        summaries = saved.get_json()['data']
        assert {summary['id'] for summary in summaries} == set(payloads)
        assert all(summary['details'][0]['Calculation Status'] == 'success' for summary in summaries)
        assert all(summary['aggregate']['currency'] == 'USD' for summary in summaries)

        os.makedirs(report_routes.REPORTS_FOLDER, exist_ok=True)
        report_path = os.path.join(
            report_routes.REPORTS_FOLDER, f'{session_id}.xlsx'
        )
        with open(report_path, 'wb') as report_file:
            report_file.write(b'persistence test report')
        report_id = report_routes.save_report(
            1, session_id, 'integration-test', {'instrument_count': 3}, report_path
        )
        assert report_id
        listed_reports = client.get(f'/api/report/session/{session_id}')
        assert listed_reports.status_code == 200
        assert any(report['id'] == report_id for report in listed_reports.get_json()['data'])
        downloaded_report = client.get(f'/api/report/{report_id}/download')
        assert downloaded_report.status_code == 200
        assert downloaded_report.data == b'persistence test report'
        downloaded_report.close()

        configuration = {'money-market': True, 'bonds': False, 'tbills': True}
        save_report = client.post('/api/report/configuration', json={
            'session_id': session_id,
            'selected_instruments': configuration,
            'report_type': 'session',
        })
        assert save_report.status_code == 200
        assert save_report.get_json()['success'] is True

        loaded_report = client.get(f'/api/report/configuration/{session_id}')
        assert loaded_report.status_code == 200
        assert loaded_report.get_json()['data']['selectedInstruments'] == configuration

        delete_response = client.post(
            '/api/sessions/delete', json={'session_id': session_id}
        )
        assert delete_response.status_code == 200
        assert delete_response.get_json()['warning'] is None
        session_deleted = True
        assert not os.path.exists(report_path)
    finally:
        # The endpoint removes calculation, summary and report records belonging
        # only to this randomly generated integration-test session.
        if uploaded_dataset_id is not None:
            client.delete(f'/api/dataset/{uploaded_dataset_id}')
        if not session_deleted:
            client.post('/api/sessions/delete', json={'session_id': session_id})
        if report_path and os.path.exists(report_path):
            os.remove(report_path)


@pytest.mark.parametrize(
    ('instrument_type', 'row'),
    [
        ('money-market', {
            'principal': 100_000, 'interest_rate': 5, 'term_days': 90,
        }),
        ('tbills', {
            'face_value': 100_000, 'purchase_price': 98_750, 'term_days': 90,
        }),
        ('bonds', {
            'face_value': 100_000, 'coupon_rate': 6,
            'years_to_maturity': 5, 'coupon_frequency': 2, 'price': 100_000,
        }),
    ],
)
def test_calculation_uses_frontend_yield_curve_benchmark(instrument_type, row, monkeypatch):
    def reject_fallback_fetch(*_args):
        raise AssertionError('Explicit yield-curve rate should avoid a fallback fetch')

    monkeypatch.setattr(calculation_routes, '_fetch_benchmark', reject_fallback_fetch)
    response = app.test_client().post(
        f'/api/calculate/{instrument_type}',
        json={
            'data': [row],
            'benchmark_yield': 4.375,
            'valuationDate': '2026-01-01',
        },
    )

    assert response.status_code == 200
    result = response.get_json()['data']['calculations'][0]
    assert result['yield_curve_rate'] == pytest.approx(4.375)


@pytest.mark.parametrize(
    ('instrument_type', 'rows', 'value_field'),
    [
        (
            'money-market',
            [
                {'Instrument Name': 'MM-1', 'Principal': 100_000,
                 'Interest Rate': 5, 'Term Days': 90},
                {'Instrument Name': 'MM-2', 'Principal': 200_000,
                 'Interest Rate': 4, 'Term Days': 180},
            ],
            'total_value',
        ),
        (
            'tbills',
            [
                {'Instrument Name': 'TB-1', 'Face Value': 100_000,
                 'Discount Rate': 5, 'Term Days': 90},
                {'Instrument Name': 'TB-2', 'Face Value': 200_000,
                 'Discount Rate': 4, 'Term Days': 180},
            ],
            'purchase_price',
        ),
        (
            'bonds',
            [
                {'Instrument Name': 'B-1', 'Face Value': 100_000,
                 'Coupon Rate': 6, 'Years to Maturity': 5,
                 'Coupon Frequency': 2, 'Price': 100_000},
                {'Instrument Name': 'B-2', 'Face Value': 200_000,
                 'Coupon Rate': 5, 'Years to Maturity': 3,
                 'Coupon Frequency': 2, 'Price': 198_000},
            ],
            'current_price',
        ),
    ],
)
def test_multi_instrument_valuation_returns_within_five_seconds(
    monkeypatch, instrument_type, rows, value_field
):
    def reject_synchronous_benchmark(*_args):
        raise AssertionError('Core calculation endpoint attempted FRED I/O')

    monkeypatch.setattr(calculation_routes, '_fetch_benchmark', reject_synchronous_benchmark)
    monkeypatch.setattr(calculation_routes, '_attach_fred', reject_synchronous_benchmark)
    workbook_rows = [
        {**row, 'Instrument Name': f"{row['Instrument Name']}-{batch}"}
        for batch in range(50)
        for row in rows
    ]
    started = perf_counter()
    response = app.test_client().post(
        f'/api/calculate/{instrument_type}',
        json={
            'valuationDate': '2026-01-01',
            'currency': 'USD',
            'data': workbook_rows,
        },
    )
    elapsed = perf_counter() - started

    assert response.status_code == 200
    result = response.get_json()['data']
    assert result['instrument_count'] == 100
    assert len(result['calculations']) == 100
    assert all(row[value_field] is not None for row in result['calculations'])
    assert result['aggregates']['total_value'] == pytest.approx(
        sum(row['total_value'] for row in result['calculations'])
    )
    assert elapsed < 5


@pytest.mark.parametrize(
    ('instrument_type', 'row'),
    [
        ('money-market', {
            'principal': 100_000, 'interest_rate': 5,
            'valuation_date': '2024-01-01',
            'maturity_date': '2024-04-01', 'term_days': 30,
        }),
        ('tbills', {
            'face_value': 100_000, 'discount_rate': 5,
            'valuation_date': '2024-01-01',
            'maturity_date': '2024-04-01', 'term_days': 30,
        }),
        ('bonds', {
            'face_value': 100_000, 'coupon_rate': 6,
            'coupon_frequency': 2, 'price': 100_000,
            'valuation_date': '2024-01-01',
            'maturity_date': '2029-01-01',
        }),
    ],
)
def test_multiple_calculations_preserve_cleaned_valuation_dates(
    monkeypatch, instrument_type, row
):
    monkeypatch.setattr(calculation_routes, '_fetch_benchmark', lambda *_args: None)
    monkeypatch.setattr(calculation_routes, '_attach_fred', lambda *_args: None)
    response = app.test_client().post(
        '/api/calculations/multiple',
        json={
            'instrument_type': instrument_type,
            'valuationDate': '2025-01-01',
            'data': [row],
        },
    )

    assert response.status_code == 200
    result = response.get_json()['results'][0]['calculation']
    assert result['valuation_date'] == '2024-01-01'
    if instrument_type != 'bonds':
        assert result['term_days'] == 91


def test_saved_portfolio_summary_does_not_invent_or_mix_values(monkeypatch):
    rows = [
        {
            'id': 'usd-calculation',
            'instrument_type': 'money-market',
            'result_data': {
                'currency': 'USD',
                'aggregates': {'total_value': 100, 'currency': 'USD'},
            },
        },
        {
            'id': 'eur-calculation',
            'instrument_type': 'tbills',
            'result_data': {
                'currency': 'EUR',
                'aggregates': {'total_market_value': 200, 'currency': 'EUR'},
            },
        },
        {
            'id': 'unvalued-bond',
            'instrument_type': 'bonds',
            'result_data': {
                'currency': 'USD',
                'aggregates': {
                    'total_face_value': 10_000,
                    'instrument_count': 1,
                },
            },
        },
    ]

    class FakeCursor:
        def execute(self, *_args):
            pass

        def fetchall(self):
            return rows

    @contextmanager
    def fake_database():
        yield object(), FakeCursor()

    monkeypatch.setattr(calculation_routes, '_db', fake_database)
    monkeypatch.setattr(calculation_routes, 'session_is_owned', lambda *_args: True)
    response = app.test_client().post(
        '/api/calculations/portfolio-summary',
        json={'session_id': 'portfolio-summary-test'},
    )

    assert response.status_code == 200
    summary = response.get_json()['data']
    assert summary['portfolio_total'] is None
    assert summary['currency_totals'] == {'USD': 100, 'EUR': 200}
    assert summary['rows'][2]['Total Value'] is None
