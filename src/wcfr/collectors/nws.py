from __future__ import annotations

from wcfr.http import get_json


def _values(prop: dict) -> list[dict]:
    return prop.get("values", []) if isinstance(prop, dict) else []


def fetch_marine_grid(latitude: float, longitude: float) -> dict:
    point = get_json(f"https://api.weather.gov/points/{latitude},{longitude}")
    grid_url = point["properties"]["forecastGridData"]
    data = get_json(grid_url)
    props = data.get("properties", {})
    return {
        "updated": props.get("updateTime"),
        "valid_times": props.get("validTimes"),
        "wind_speed": _values(props.get("windSpeed", {})),
        "wind_gust": _values(props.get("windGust", {})),
        "wave_height": _values(props.get("waveHeight", {})),
        "wave_period": _values(props.get("wavePeriod", {})),
        "wave_direction": _values(props.get("waveDirection", {})),
        "weather": _values(props.get("weather", {})),
        "hazards": _values(props.get("hazards", {})),
        "source_url": grid_url,
    }
