from datetime import date

from wcfr.collectors.local_reports import parse_latest


def test_parses_latest_local_private_report():
    text = """Sept. 2
The halibut and rock fishing was best near Davenport. Anglers caught lingcod on squid. The wind increased.
Sept. 1
Older report about bluefin.
"""
    source = {"name": "Test", "city": "Santa Cruz", "state": "CA", "region": "central_california",
              "url": "https://example.test", "mode": "local/private-boat intelligence"}
    result = parse_latest(text, source, date(2026, 9, 3))
    assert result["published_date"] == "2026-09-02"
    assert result["age_days"] == 1
    assert {"halibut", "rockfish", "lingcod"}.issubset(result["species"])
    assert result["places"] == ["Davenport"]
    assert "squid" in result["methods"]


def test_does_not_treat_open_season_as_catch():
    text = """Sept. 2
The salmon season is open. Boats looking for tuna did not find much action. A bluefin was caught near the 601.
Sept. 1
Old report.
"""
    source = {"name": "Test", "city": "Santa Cruz", "state": "CA", "region": "central_california",
              "url": "https://example.test", "mode": "local/private-boat intelligence"}
    result = parse_latest(text, source, date(2026, 9, 3))
    assert "salmon (unspecified)" not in result["species"]
    assert "bluefin tuna" in result["species"]
    assert result["species_status"]["tuna (unspecified)"] == "searched; little or no action"
