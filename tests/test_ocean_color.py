from wcfr.collectors import ocean_color


def test_mur_sst_is_converted_and_labeled(monkeypatch):
    payload = b"time (UTC),latitude (degrees_north),longitude (degrees_east),analysed_sst (degree_C)\n2026-09-02T09:00:00Z,36.7,-122.05,16.0\n"
    monkeypatch.setattr(ocean_color, "get_bytes", lambda *args, **kwargs: payload)
    sample = ocean_color._point("jplMURSST41", "analysed_sst", "MUR SST", "celsius", 36.7, -122.05)
    assert sample["value"] == 60.8
    assert sample["dataset"] == "jplMURSST41"


def test_product_falls_back_when_primary_has_no_value(monkeypatch):
    def fake_point(dataset, variable, label, units, latitude, longitude):
        if dataset == "jplMURSST41":
            raise RuntimeError("primary unavailable")
        return {"value": 61.0, "observed_at": "2026-09-03T00:00:00Z", "product": label}
    monkeypatch.setattr(ocean_color, "_point", fake_point)
    samples, errors = ocean_color._sample_product("sst", 36.7, -122.05)
    assert len(samples) == 7
    assert any("jplMURSST41" in error for error in errors)

