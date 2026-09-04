from datetime import date

from wcfr.collectors.local_reports import _parse_wdfw, _report_date, parse_latest


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


def test_date_parser_does_not_turn_wind_or_fishing_line_into_date():
    assert _report_date("The wind was blowing 10-14 knots near the 125 line.", 2026) is None
    assert _report_date("Fishing got good. 8/23/2026", 2026) == date(2026, 8, 23)
    assert _report_date("Updated: September 2, 2026", 2026) == date(2026, 9, 2)


def test_wdfw_extracts_latest_area_catches():
    text = """Ocean sport salmon quota report Updated: September 2, 2026
Columbia River Coho quota: 100 A total of 272 anglers participated, landing 0 Chinook and 424 coho.
Westport Coho quota: 100 A total of 1,184 anglers participated, landing 11 Chinook and 1,417 coho.
La Push Coho quota: 100 Through Sunday, 14 Chinook and 50 coho have been landed.
Neah Bay Coho quota: 100 Through Sunday, 8,609 Chinook and 10,226 coho have been landed.
"""
    source = {"name": "WDFW", "city": "Washington Coast", "state": "WA", "region": "washington",
              "url": "https://example.test", "mode": "official creel"}
    result = _parse_wdfw(text, source, date(2026, 9, 4))
    assert result["published_date"] == "2026-09-02"
    assert {"chinook salmon", "coho salmon"}.issubset(result["species"])
    assert "Westport" in result["places"]
