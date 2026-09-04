from datetime import date

from wcfr.weather_summary import summarize_week, week_synopsis


def test_day_by_day_weather_converts_units_and_degrades_confidence():
    forecast = {
        "wind_speed": [{"validTime": "2026-09-03T15:00:00+00:00/PT168H", "value": 18.52}],
        "wind_gust": [{"validTime": "2026-09-03T15:00:00+00:00/PT168H", "value": 27.78}],
        "wave_height": [{"validTime": "2026-09-03T15:00:00+00:00/PT168H", "value": 1.5}],
        "wave_period": [{"validTime": "2026-09-03T15:00:00+00:00/PT168H", "value": 12}],
    }
    rows = summarize_week(forecast, date(2026, 9, 3))
    assert len(rows) == 7
    assert rows[0]["wind_am_kt"] == 10
    assert rows[0]["wave_ft"] == 4.9
    assert rows[0]["confidence"] == "high"
    assert rows[-1]["confidence"] == "low"


def test_week_synopsis_replaces_day_by_day_dump():
    forecast = {
        "wind_speed": [{"validTime": "2026-09-03T15:00:00+00:00/PT168H", "value": 18.52}],
        "wind_gust": [{"validTime": "2026-09-03T15:00:00+00:00/PT168H", "value": 27.78}],
        "wave_height": [{"validTime": "2026-09-03T15:00:00+00:00/PT168H", "value": 1.5}],
        "wave_period": [{"validTime": "2026-09-03T15:00:00+00:00/PT168H", "value": 12}],
    }
    summary = week_synopsis(summarize_week(forecast, date(2026, 9, 3)))
    assert "seven-day period" in summary["text"]
    assert "Combined seas range" in summary["text"]
    assert len(summary["best_windows"]) == 3
