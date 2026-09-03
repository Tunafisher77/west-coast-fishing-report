from __future__ import annotations

from urllib.parse import urlencode

from wcfr.http import get_json

BASE = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"


def fetch_high_low(station: str, day: str) -> list[dict]:
    params = {
        "product": "predictions",
        "application": "west_coast_fishing_report",
        "begin_date": day.replace("-", ""),
        "end_date": day.replace("-", ""),
        "datum": "MLLW",
        "station": station,
        "time_zone": "lst_ldt",
        "units": "english",
        "interval": "hilo",
        "format": "json",
    }
    payload = get_json(f"{BASE}?{urlencode(params)}")
    if "error" in payload:
        raise RuntimeError(payload["error"].get("message", "NOAA tide error"))
    return payload.get("predictions", [])
