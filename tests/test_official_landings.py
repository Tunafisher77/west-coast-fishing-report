from wcfr.collectors.official_landings import parse_landing_text


def test_parses_all_species_vessel_and_anglers():
    text = "The Pegasus returned with 32 Bluefin Tuna, 30 Yellowtail, 10 Dorado and 9 Yellowfin Tuna for 9 anglers."
    rows = parse_landing_text(text, "Fisherman's Landing", "https://example.test", "southern_california")
    assert {r["species"] for r in rows} == {
        "bluefin tuna", "california yellowtail", "dorado", "yellowfin tuna"
    }
    assert all(r["vessel"] == "Pegasus" for r in rows)
    assert all(r["anglers"] == 9 for r in rows)
