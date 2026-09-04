from pathlib import Path

from wcfr import ocean_maps


def test_map_url_uses_west_coast_bounds_and_graph_options():
    url = ocean_maps.map_url("sst")
    assert "jplMURSST41.png" in url
    assert "analysed_sst" in url
    assert ".draw=surface" in url
    assert "32.0" in url and "49.0" in url


def test_download_maps_keeps_report_alive_when_one_map_fails(monkeypatch, tmp_path: Path):
    def fake_get(url, **kwargs):
        if "jplMURSST41" in url:
            return b"\x89PNG\r\n\x1a\nimage"
        raise RuntimeError("cloud product unavailable")
    monkeypatch.setattr(ocean_maps, "get_bytes", fake_get)
    result = ocean_maps.download_maps(tmp_path)
    assert result["sst"]["ok"] is True
    assert (tmp_path / "sst.png").exists()
    assert result["chlorophyll"]["ok"] is False

