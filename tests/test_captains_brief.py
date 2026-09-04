from datetime import date

from wcfr.report import render_email_summary_v3


def test_captains_brief_ranks_and_embeds_maps():
    region = "central_california"
    data = {
        "catch_records": [],
        "field_reports": [{"region": region, "age_days": 1, "species": ["halibut"],
                           "places": ["Davenport"], "name": "Bayside", "published_date": "2026-09-03"}],
        "ocean_color": {region: {"sst": {"minimum": 59, "maximum": 61, "observed_at": "2026-09-03"},
                                  "chlorophyll": {"value": .3, "minimum": .2, "maximum": .5},
                                  "front_detected": True}},
        "daily_weather": {region: [{"date": "2026-09-04", "best_window": "AM", "wave_ft": 4,
                                     "period_s": 10, "wind_am_kt": 6, "wind_pm_kt": 14,
                                     "gust_am_kt": 8, "gust_pm_kt": 18, "safety_block": False}]},
        "weekly_weather": {}, "lunar": {}, "source_health": [],
        "ocean_maps": {"sst": {"ok": True, "filename": "sst.png"},
                       "chlorophyll": {"ok": True, "filename": "chlorophyll.png"}},
    }
    html = render_email_summary_v3(date(2026, 9, 4), data)
    assert "THE MORNING CALL" in html
    assert "Davenport" in html
    assert "Ranked opportunities" in html
    assert "raw.githubusercontent.com" in html
    assert "Regional watchlist" in html

