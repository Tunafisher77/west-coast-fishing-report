from __future__ import annotations

import csv
import io
import math
from concurrent.futures import ThreadPoolExecutor, as_completed
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
    rows = list(csv.DictReader(io.StringIO(get_bytes(url, attempts=1, timeout=20).decode("utf-8"))))
    if not rows:
        raise RuntimeError(f"no {product} value returned")
    row = rows[-1]
    keys = list(row)
    value_key = next((k for k in keys if k.casefold().startswith(variable)), keys[-1])
    time_key = next((k for k in keys if k.casefold().startswith("time")), keys[0])
    value = float(row[value_key])
    if not math.isfinite(value):
        raise RuntimeError(f"{product} sample is missing/cloud-obscured")
    if product == "sst" and value < 45:  # ERDDAP product is normally degrees C.
        value = value * 9 / 5 + 32
    return {"value": value, "observed_at": row[time_key], "product": label, "source_url": url}


def fetch_region(latitude: float, longitude: float) -> dict:
    result = {"checked_at": datetime.now(timezone.utc).isoformat()}
    errors = []
    offsets = [(0, 0), (0.35, 0), (-0.35, 0), (0, 0.45), (0, -0.45)]
    for product in PRODUCTS:
        samples = []
        with ThreadPoolExecutor(max_workers=5) as pool:
            futures = [pool.submit(_point, product, latitude + dy, longitude + dx) for dy, dx in offsets]
            for future in as_completed(futures):
                try:
                    samples.append(future.result())
                except Exception as exc:
                    errors.append(f"{product} sample: {exc}")
        if samples:
            values = sorted(sample["value"] for sample in samples)
            middle = samples[0]
            middle.update({"value": values[len(values) // 2], "minimum": values[0], "maximum": values[-1],
                           "spread": values[-1] - values[0], "sample_count": len(values)})
            result[product] = middle
        else:
            result[product] = None
    result["errors"] = errors
    if not result.get("sst") and not result.get("chlorophyll"):
        raise RuntimeError("; ".join(errors))
    sst_spread = result.get("sst", {}).get("spread", 0) if result.get("sst") else 0
    chl = result.get("chlorophyll")
    chl_ratio = (chl["maximum"] / max(chl["minimum"], .01)) if chl else 1
    result["front_detected"] = sst_spread >= 1.0 or chl_ratio >= 2.0
    return result
