from __future__ import annotations

from wcfr.http import get_bytes

BASE = "https://www.ndbc.noaa.gov/data/realtime2"


def _number(value: str) -> float | None:
    if value in {"MM", "999", "9999", "99.0"}:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def fetch_latest(station: str) -> dict:
    text = get_bytes(f"{BASE}/{station}.txt").decode("utf-8", errors="replace")
    lines = [line.split() for line in text.splitlines() if line.strip()]
    if len(lines) < 3:
        raise RuntimeError(f"No observations returned for NDBC {station}")
    headers = [value.lstrip("#") for value in lines[0]]
    row = dict(zip(headers, lines[2]))
    return {
        "station": station,
        "timestamp_utc": "-".join(row.get(k, "") for k in ("YY", "MM", "DD", "hh", "mm")),
        "wind_direction_deg": _number(row.get("WDIR", "MM")),
        "wind_speed_m_s": _number(row.get("WSPD", "MM")),
        "gust_m_s": _number(row.get("GST", "MM")),
        "wave_height_m": _number(row.get("WVHT", "MM")),
        "dominant_period_s": _number(row.get("DPD", "MM")),
        "mean_wave_direction_deg": _number(row.get("MWD", "MM")),
        "water_temp_c": _number(row.get("WTMP", "MM")),
    }
