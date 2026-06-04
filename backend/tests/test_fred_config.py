"""Unit tests for FRED helpers (pytest)."""
from utils.fred_config import (
    normalize_type,
    series_for_country,
    attach_fred_to_calculation,
    build_filter_options,
    get_country,
)


def test_normalize_type():
    assert normalize_type('money-market') == 'money_market'
    assert normalize_type('treasury_bills') == 'treasury_bills'


def test_multi_country_series():
    sid, label, used, _, curr, _ = series_for_country('ZA', '10Y')
    assert sid == 'IRLTLT01ZAM156N'
    assert curr == 'ZAR'


def test_us_has_many_maturities():
    c = get_country('US')
    assert len(c['series']) >= 5


def test_filter_options_countries():
    opts = build_filter_options()
    codes = [c['code'] for c in opts['countries']]
    assert 'US' in codes
    assert 'ZA' in codes


def test_attach_fred_adds_spread(monkeypatch):
    def fake_benchmark(inst, maturity=None, country='US', currency='USD'):
        return {
            'benchmark_rate': 4.0,
            'series_label': 'Test',
            'country': country,
            'currency': currency,
            'maturity': '10Y',
        }

    monkeypatch.setattr('utils.fred_config.FRED_KEY', 'test-key')
    monkeypatch.setattr('utils.fred_config.get_market_benchmark', fake_benchmark)

    result = {'avgRate': 5.0, 'instrumentCount': 1}
    attach_fred_to_calculation(result, 'money-market', '10Y', 'US', 'USD')
    assert result['fred']['spread_vs_market'] == 1.0
