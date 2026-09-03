from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

PACIFIC = ZoneInfo("America/Los_Angeles")


def _start(valid: str) -> datetime:
    return datetime.fromisoformat(valid.split("/")[0].replace("Z", "+00:00")).astimezone(PACIFIC)


def _nearest(entries: list[dict], when: datetime):
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
        # NWS grid wind is km/h and wave height is metres.
        kt = lambda value: round(value * 0.539957) if value is not None else None
        ft = round(wave * 3.28084, 1) if wave is not None else None
        max_wind = max([v for v in (kt(wind_am), kt(wind_pm), kt(gust_am), kt(gust_pm)) if v is not None], default=None)
        blocked = max_wind is not None and max_wind >= 25
        best = "AM" if wind_am is not None and (wind_pm is None or wind_am <= wind_pm) else "PM"
        rows.append({"date": day.isoformat(), "wind_am_kt": kt(wind_am), "gust_am_kt": kt(gust_am),
                     "wind_pm_kt": kt(wind_pm), "gust_pm_kt": kt(gust_pm), "wave_ft": ft,
                     "period_s": round(period) if period is not None else None, "best_window": best,
                     "safety_block": blocked, "confidence": "high" if offset <= 2 else "medium" if offset <= 4 else "low"})
    return rows
