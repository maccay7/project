from flask import Flask
from threading import Barrier

from routes import fred as fred_routes
from utils import fred_config


def test_yield_curve_route_passes_selected_maturity(monkeypatch):
    captured = {}
    monkeypatch.setattr(fred_routes, 'FRED_API_KEY', 'test-key')

    def fake_get_yield_curve(country, **kwargs):
        captured.update(kwargs)
        return [{
            'maturity': 1.0,
            'maturityLabel': '1Y',
            'rate': 4.0,
            'date': '2026-10-30',
        }]

    monkeypatch.setattr(fred_routes, 'get_yield_curve', fake_get_yield_curve)
    app = Flask(__name__)
    fred_routes.fred_routes(app)

    response = app.test_client().post(
        '/api/fred/yield-curve',
        json={'country': 'US', 'currency': 'USD', 'maturity': '1Y'},
    )

    assert response.status_code == 200
    assert captured['maturity'] == '1Y'


def test_yield_curve_limits_requested_tenors_to_selected_maturity(monkeypatch):
    requested_series = []

    def fetch_observation(series_id):
        requested_series.append(series_id)
        return 4.0, '2026-10-30'

    monkeypatch.setattr(fred_config, 'fetch_fred_observation', fetch_observation)

    points = fred_config.get_yield_curve(
        'US',
        maturity='1Y',
        instrument_type='money-market',
    )

    assert set(requested_series) == {'DGS1MO', 'DGS3MO', 'DGS6MO', 'DGS1'}
    assert len(points) == 4


def test_tbill_curve_includes_selected_four_week_series(monkeypatch):
    requested_series = []

    def fetch_observation(series_id):
        requested_series.append(series_id)
        return 4.0, '2026-10-30'

    monkeypatch.setattr(fred_config, 'fetch_fred_observation', fetch_observation)

    points = fred_config.get_yield_curve(
        'US',
        maturity='4W',
        instrument_type='tbills',
    )

    assert requested_series == ['DTB4WK']
    assert [point['maturityLabel'] for point in points] == ['4W']


def test_yield_curve_fetches_maturities_concurrently_and_sorts_points(monkeypatch):
    rendezvous = Barrier(3)

    def fetch_observation(series_id):
        rendezvous.wait(timeout=2)
        return {
            'DGS1MO': (4.1, '2026-10-30'),
            'DGS3MO': (4.2, '2026-10-30'),
            'DGS1': (4.3, '2026-10-30'),
        }[series_id]

    monkeypatch.setattr(fred_config, 'fetch_fred_observation', fetch_observation)

    points = fred_config.get_yield_curve(
        'US',
        maturities=['1Y', '1M', '3M'],
        instrument_type='money-market',
    )

    assert [point['maturityLabel'] for point in points] == ['1M', '3M', '1Y']
    assert [point['rate'] for point in points] == [4.1, 4.2, 4.3]
