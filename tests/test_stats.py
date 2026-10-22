import json
from datetime import date, datetime
from pathlib import Path

import pytz

import application
from application import build_chart_data


def test_build_daily_chart_data_includes_empty_days_and_aggregates_hours():
    records = {
        '2026-08-10': {'english': 3600, 'piano': 1800},
        '2026-08-12': {'english': 5400, 'piano': 0},
    }

    result = build_chart_data(records, 'english', 'day', date(2026, 8, 12))

    assert len(result) == 12
    assert result[-3:] == [
        {'label': '8/10', 'hours': 1.0},
        {'label': '8/11', 'hours': 0},
        {'label': '8/12', 'hours': 1.5},
    ]


def test_build_monthly_and_yearly_chart_data_sums_recorded_seconds():
    records = {
        '2025-12-31': {'english': 3600, 'piano': 7200},
        '2026-01-01': {'english': 1800, 'piano': 0},
    }

    monthly = build_chart_data(records, 'piano', 'month', date(2026, 2, 1))
    yearly = build_chart_data(records, 'english', 'year', date(2026, 2, 1))

    assert monthly[-3:] == [
        {'label': '2025/12', 'hours': 2.0},
        {'label': '2026/1', 'hours': 0},
        {'label': '2026/2', 'hours': 0},
    ]
    assert yearly[-2:] == [
        {'label': '2025年', 'hours': 1.0},
        {'label': '2026年', 'hours': 0.5},
    ]


def test_build_chart_data_includes_at_least_12_periods():
    today = date(2026, 8, 12)

    daily = build_chart_data({}, 'english', 'day', today)
    monthly = build_chart_data({}, 'english', 'month', today)
    yearly = build_chart_data({}, 'english', 'year', today)

    assert len(daily) == 12
    assert len(monthly) == 12
    assert len(yearly) == 12
    assert daily[-1] == {'label': '8/12', 'hours': 0}
    assert monthly[-1] == {'label': '2026/8', 'hours': 0}
    assert yearly[-1] == {'label': '2026年', 'hours': 0}


def test_stats_route_renders_selected_period_and_category(tmp_path, monkeypatch):
    data_file = tmp_path / 'data.json'
    data_file.write_text(json.dumps({
        'records': {'2026-08-12': {'english': 3600, 'piano': 1800}},
        'active_session': None,
    }), encoding='utf-8')
    monkeypatch.setattr(application, 'DATA_FILE', str(data_file))
    monkeypatch.setattr(
        application,
        'get_now_jst',
        lambda: pytz.timezone('Asia/Tokyo').localize(datetime(2026, 8, 12)),
    )

    response = application.app.test_client().get('/stats/english?period=month')
    response_text = response.get_data(as_text=True)

    assert response.status_code == 200
    assert '英語学習の実績' in response_text
    assert '<option value="month" selected>' in response_text
    assert '<output class="chart-total" aria-label="グラフの総計">総計: 1時間</output>' in response_text


def test_stats_route_renders_sample_data_totals_and_recent_daily_bars(monkeypatch):
    monkeypatch.setattr(
        application,
        'DATA_FILE',
        str(Path(__file__).resolve().parents[1] / 'sample_data.json'),
    )
    monkeypatch.setattr(
        application,
        'get_now_jst',
        lambda: pytz.timezone('Asia/Tokyo').localize(datetime(2026, 10, 22)),
    )

    response = application.app.test_client().get('/stats/english?period=day')
    response_text = response.get_data(as_text=True)

    assert response.status_code == 200
    assert '総計: 28.25時間' in response_text
    assert '"hours": 1.25' in response_text
    assert '"label": "10/22"' in response_text


def test_stats_route_rejects_unknown_category_and_period():
    client = application.app.test_client()

    assert client.get('/stats/french').status_code == 404
    assert client.get('/stats/english?period=week').status_code == 404
