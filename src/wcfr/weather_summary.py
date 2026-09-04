from __future__ import annotations

import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

PACIFIC = ZoneInfo("America/Los_Angeles")


def _start(valid: str) -> datetime:
    return datetime.fromisoformat(valid.split("/")[0].replace("Z", "+00:00")).astimezone(PACIFIC)


def _duration(valid: str) -> timedelta:
    duration = valid.split("/", 1)[1] if "/" in valid else "PT1H"
    match = re.fullmatch(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?", duration)
    return timedelta(days=int(match.group(1) or 0), hours=int(match.group(2) or 0), minutes=int(match.group(3) or 0)) if match else timedelta(hours=1)


def _nearest(entries: list[dict], when: datetime):
    for entry in entries:
        start = _start(entry["validTime"])
        if start <= when < start + _duration(entry["validTime"]) and entry.get("value") is not None:
            return entry["value"]
    usable = [(abs((_start(e["validTime"]) - when).total_seconds()), e.get("value")) for e in entries if e.get("value") is not None]
    return min(usable, default=(0, None))[1]


def summarize_week(forecast: dict, start_day) -> list[dict]:
    rows = []
    for offset in range(7):
        day = start_day + timedelta(days=offset)
        am = datetime(day.year, day.month, day.day, 8, tzinfo=PACIFIC)
        pm = datetime(day.year, day.month, day.day, 15, tzinfo=PACIFIC)
        wind_am = _nearest(forecast.get("wind_speed", []), am)
        wind_pm = _nearest(forecast.get("wind_speed", []), pm)
        gust_am = _nearest(forecast.get("wind_gust", []), am)
        gust_pm = _nearest(forecast.get("wind_gust", []), pm)
        wave = _nearest(forecast.get("wave_height", []), am)
        period = _nearest(forecast.get("wave_period", []), am)
        direction = _nearest(forecast.get("wave_direction", []), am)
        # NWS grid wind is km/h and wave height is metres.
        kt = lambda value: round(value * 0.539957) if value is not None else None
        ft = round(wave * 3.28084, 1) if wave is not None else None
        max_wind = max([v for v in (kt(wind_am), kt(wind_pm), kt(gust_am), kt(gust_pm)) if v is not None], default=None)
        blocked = max_wind is not None and max_wind >= 25
        best = "AM" if wind_am is not None and (wind_pm is None or wind_am <= wind_pm) else "PM"
        rows.append({"date": day.isoformat(), "wind_am_kt": kt(wind_am), "gust_am_kt": kt(gust_am),
                     "wind_pm_kt": kt(wind_pm), "gust_pm_kt": kt(gust_pm), "wave_ft": ft,
                     "period_s": round(period) if period is not None else None, "best_window": best,
                     "wave_direction_deg": round(direction) if direction is not None else None,
                     "safety_block": blocked, "confidence": "high" if offset <= 2 else "medium" if offset <= 4 else "low"})
    return rows


def week_synopsis(rows: list[dict]) -> dict:
    """Turn seven forecast rows into a decision-oriented weekly narrative."""
    usable = [row for row in rows if not row["safety_block"]]
    blocked = [row for row in rows if row["safety_block"]]

    def burden(row: dict) -> float:
        winds = [v for v in (row["wind_am_kt"], row["wind_pm_kt"], row["gust_am_kt"], row["gust_pm_kt"]) if v is not None]
        return max(winds, default=30) + (row["wave_ft"] if row["wave_ft"] is not None else 10) * 2

    ranked = sorted(usable, key=burden)
    best = ranked[:3]
    wind_values = [v for row in rows for v in (row["wind_am_kt"], row["wind_pm_kt"]) if v is not None]
    wave_values = [row["wave_ft"] for row in rows if row["wave_ft"] is not None]
    period_values = [row["period_s"] for row in rows if row.get("period_s") is not None]
    windows = [f"{row['date'][5:]} {row['best_window']}" for row in best]
    if rows and wind_values:
        early = burden(rows[0])
        late = burden(rows[-1])
        trend = "improving" if late + 2 < early else "deteriorating" if late > early + 2 else "fairly steady"
    else:
        trend = "uncertain"
    parts = [f"The marine pattern is {trend} through the seven-day period."]
    if wind_values:
        parts.append(f"Typical sustained wind runs {min(wind_values)}-{max(wind_values)} kt; morning is favored on {sum(r['best_window'] == 'AM' for r in rows)} of 7 days.")
    if wave_values:
        sea = f"Combined seas range {min(wave_values):.1f}-{max(wave_values):.1f} ft"
        sea += f" with {min(period_values)}-{max(period_values)} sec periods" if period_values else "; forecast periods are incomplete"
        parts.append(sea + ".")
    if windows:
        parts.append("Best current windows: " + ", ".join(windows) + ".")
    if blocked:
        parts.append("Safety screen blocks: " + ", ".join(row["date"][5:] for row in blocked) + ".")
    parts.append("Confidence decreases after day five; recheck the latest marine forecast before departure.")
    return {"text": " ".join(parts), "best_windows": windows, "blocked_dates": [r["date"] for r in blocked]}
