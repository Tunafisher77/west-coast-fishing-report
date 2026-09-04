from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

from wcfr.http import get_bytes

BASE = "https://coastwatch.pfeg.noaa.gov/erddap/griddap"
BOUNDS = (32.0, 49.0, -130.0, -117.0)
MAPS = {
    "sst": {
        "dataset": "jplMURSST41",
        "variable": "analysed_sst",
        "stride": 4,
        "title": "West Coast Sea Surface Temperature (Fisherman's Overview)",
        "colorbar": "Rainbow|C|Linear|8|25|1",
    },
    "chlorophyll": {
        "dataset": "productivity_viirs_snpp_daily",
        "variable": "chlor_a",
        "stride": 1,
        "title": "West Coast Chlorophyll-a (Clean/Green Edges)",
        "colorbar": "Rainbow|C|Log|0.03|5|",
    },
}


def map_url(kind: str) -> str:
    spec = MAPS[kind]
    south, north, west, east = BOUNDS
    variable = spec["variable"]
    subset = f"{variable}[(last)][({south}):{spec['stride']}:({north})][({west}):{spec['stride']}:({east})]"
    options = [
        ".draw=surface",
        f".vars=longitude|latitude|{variable}",
        f".colorBar={spec['colorbar']}",
        ".land=over",
        f".title={spec['title']}",
    ]
    query = "&".join([quote(subset, safe="[]():,.-"), *[quote(x, safe="=|().,:-'") for x in options]])
    return f"{BASE}/{spec['dataset']}.png?{query}"


def download_maps(output: Path) -> dict:
    """Download durable daily maps; a failed map never aborts the report."""
    results = {}
    for kind in MAPS:
        try:
            payload = get_bytes(map_url(kind), attempts=3, timeout=90)
            if not payload.startswith(b"\x89PNG"):
                raise RuntimeError("NOAA response was not a PNG image")
            filename = f"{kind}.png"
            (output / filename).write_bytes(payload)
            results[kind] = {"ok": True, "filename": filename, "source_url": map_url(kind)}
        except Exception as exc:
            results[kind] = {"ok": False, "error": str(exc), "source_url": map_url(kind)}
    return results
