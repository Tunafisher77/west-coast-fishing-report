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
    "sst": [
        ("jplMURSST41", "analysed_sst", "NASA/NOAA MUR daily 1-km SST", "celsius"),
        ("erdATastdhday", "sst", "NOAA CoastWatch AVHRR daily SST", "celsius"),
    ],
    "chlorophyll": [
        ("productivity_viirs_snpp_daily", "chlor_a", "NOAA CoastWatch VIIRS chlorophyll", "native"),
        ("erdMH1chla8day_R2022NRT", "chlorophyll", "NASA MODIS Aqua 8-day chlorophyll", "native"),
    ],
}


def _point(dataset: str, variable: str, label: str, units: str, latitude: float, longitude: float) -> dict:
    query = quote(f"{variable}[(last)][({latitude})][({longitude})]", safe="[](),")
    url = f"{BASE}/{dataset}.csvp?{query}"
    rows = list(csv.DictReader(io.StringIO(get_bytes(url, attempts=2, timeout=25).decode("utf-8"))))
    if not rows:
        raise RuntimeError(f"no value returned by {dataset}")
    row = rows[-1]
    keys = list(row)
    value_key = next((k for k in keys if k.casefold().startswith(variable.casefold())), None)
    time_key = next((k for k in keys if k.casefold().startswith("time")), None)
    if not value_key or not time_key:
        raise RuntimeError(f"unexpected columns from {dataset}")
    value = float(row[value_key])
    if not math.isfinite(value) or value in (-999, 9999, -99999):
        raise RuntimeError(f"missing/cloud-obscured value from {dataset}")
    if units == "celsius":
        value = value * 9 / 5 + 32
    return {"value": value, "observed_at": row[time_key], "product": label,
            "dataset": dataset, "source_url": url}


def _sample_product(product: str, latitude: float, longitude: float) -> tuple[list[dict], list[str]]:
    errors = []
    offsets = [(0, 0), (.25, 0), (-.25, 0), (0, .35), (0, -.35), (.2, .25), (-.2, -.25)]
    for dataset, variable, label, units in PRODUCTS[product]:
        samples = []
        with ThreadPoolExecutor(max_workers=7) as pool:
            futures = [pool.submit(_point, dataset, variable, label, units, latitude + dy, longitude + dx)
                       for dy, dx in offsets]
            for future in as_completed(futures):
                try:
                    samples.append(future.result())
                except Exception as exc:
                    errors.append(f"{dataset}: {exc}")
        if samples:
            return samples, errors
    return [], errors


def fetch_region(latitude: float, longitude: float) -> dict:
    result = {"checked_at": datetime.now(timezone.utc).isoformat()}
    errors = []
    for product in PRODUCTS:
        samples, product_errors = _sample_product(product, latitude, longitude)
        errors.extend(product_errors)
        if samples:
            values = sorted(sample["value"] for sample in samples)
            middle = samples[0]
            middle.update({"value": values[len(values) // 2], "minimum": values[0], "maximum": values[-1],
                           "spread": values[-1] - values[0], "sample_count": len(values),
                           "quality": "multi-point regional sample" if len(values) >= 3 else "limited sample"})
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
    result["front_basis"] = "regional SST/color contrast" if result["front_detected"] else "no strong regional contrast sampled"
    return result
