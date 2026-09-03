from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from urllib.parse import quote

from wcfr.http import get_bytes

BASE = "https://coastwatch.pfeg.noaa.gov/erddap/griddap"
PRODUCTS = {
    "sst": ("erdATastdhday", "sst", "NOAA CoastWatch AVHRR daily SST"),
    "chlorophyll": ("erdMH1chla8day_R2022NRT", "chlorophyll", "NOAA CoastWatch MODIS Aqua 8-day chlorophyll"),
}


def _point(product: str, latitude: float, longitude: float) -> dict:
    dataset, variable, label = PRODUCTS[product]
    query = quote(f"{variable}[(last)][({latitude})][({longitude})]", safe="[](),")
    url = f"{BASE}/{dataset}.csvp?{query}"
    rows = list(csv.DictReader(io.StringIO(get_bytes(url).decode("utf-8"))))
    if not rows:
        raise RuntimeError(f"no {product} value returned")
    row = rows[-1]
    keys = list(row)
    value_key = next((k for k in keys if k.casefold().startswith(variable)), keys[-1])
    time_key = next((k for k in keys if k.casefold().startswith("time")), keys[0])
    value = float(row[value_key])
    if product == "sst" and value < 45:  # ERDDAP product is normally degrees C.
        value = value * 9 / 5 + 32
    return {"value": value, "observed_at": row[time_key], "product": label, "source_url": url}


def fetch_region(latitude: float, longitude: float) -> dict:
    result = {"checked_at": datetime.now(timezone.utc).isoformat()}
    errors = []
    for product in PRODUCTS:
        try:
            result[product] = _point(product, latitude, longitude)
        except Exception as exc:
            result[product] = None
            errors.append(f"{product}: {exc}")
    result["errors"] = errors
    if len(errors) == len(PRODUCTS):
        raise RuntimeError("; ".join(errors))
    return result
