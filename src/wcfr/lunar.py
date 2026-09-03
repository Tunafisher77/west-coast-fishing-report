from __future__ import annotations

from datetime import date, datetime, timezone

import ephem


def lunar_for_day(day: date, latitude: float, longitude: float) -> dict:
    observer = ephem.Observer()
    observer.lat = str(latitude)
    observer.lon = str(longitude)
    observer.date = datetime(day.year, day.month, day.day, 12, tzinfo=timezone.utc)

    moon = ephem.Moon(observer)
    previous_new = ephem.previous_new_moon(observer.date)
    next_new = ephem.next_new_moon(observer.date)
    age = float(observer.date - previous_new)
    cycle = float(next_new - previous_new)
    phase_fraction = age / cycle

    try:
        rise = observer.next_rising(moon).datetime().replace(tzinfo=timezone.utc).isoformat()
    except (ephem.AlwaysUpError, ephem.NeverUpError):
        rise = None
    try:
        setting = observer.next_setting(moon).datetime().replace(tzinfo=timezone.utc).isoformat()
    except (ephem.AlwaysUpError, ephem.NeverUpError):
        setting = None
    try:
        transit = observer.next_transit(moon).datetime().replace(tzinfo=timezone.utc).isoformat()
        underfoot = observer.next_antitransit(moon).datetime().replace(tzinfo=timezone.utc).isoformat()
    except (ephem.AlwaysUpError, ephem.NeverUpError):
        transit = underfoot = None

    if phase_fraction < 0.25:
        name = "waxing crescent"
    elif phase_fraction < 0.5:
        name = "waxing gibbous"
    elif phase_fraction < 0.75:
        name = "waning gibbous"
    else:
        name = "waning crescent"

    return {
        "phase": name,
        "illumination_percent": round(float(moon.phase), 1),
        "age_days": round(age, 1),
        "moonrise_utc": rise,
        "moonset_utc": setting,
        "overhead_utc": transit,
        "underfoot_utc": underfoot,
    }
