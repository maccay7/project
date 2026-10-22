"""Integration coverage for the saved session → portfolio summary contract."""

import uuid

from app import app
from routes import calculations as calculation_routes


def test_session_calculations_feed_saved_portfolio_and_report_selection(monkeypatch):
    """Each instrument type is saved once and remains isolated to its session."""
    # This test verifies persistence/data flow, not the external FRED service.
    monkeypatch.setattr(calculation_routes, '_fetch_benchmark', lambda *args: None)
    monkeypatch.setattr(calculation_routes, '_attach_fred', lambda *args: None)
    session_id = f"portfolio-flow-{uuid.uuid4()}"
    client = app.test_client()

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
        response = client.post('/api/sessions/save', json={
            'session_id': session_id,
            'name': 'Portfolio flow integration test',
            'instrument_workflows': {},
        })
        assert response.status_code == 200
        assert response.get_json()['success'] is True

        for instrument_type, row in payloads.items():
            calculation = client.post(f'/api/calculate/{instrument_type}', json={
                'session_id': session_id,
                'currency': 'USD',
                'valuationDate': '2026-01-01',
                'data': [row],
            })
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
    finally:
        # The endpoint removes calculation, summary and report records belonging
        # only to this randomly generated integration-test session.
        client.post('/api/sessions/delete', json={'session_id': session_id})
