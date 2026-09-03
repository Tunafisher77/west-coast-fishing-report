from wcfr.collectors.odfw import parse_port_catch_rates


def test_parse_odfw_albacore_rate():
    text = "Albacore Port by port reports: Newport: 2.88 albacore per angler Bottomfish"
    records = parse_port_catch_rates(text)
    assert records[0]["species"] == "albacore tuna"
    assert records[0]["location_text"] == "Newport"
    assert records[0]["catch_per_angler"] == 2.88
