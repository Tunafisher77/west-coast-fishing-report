from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from datetime import date, datetime, timezone
from pathlib import Path

from wcfr.collectors.ndbc import fetch_latest
from wcfr.collectors.local_reports import fetch_all as fetch_local_reports
from wcfr.collectors.noaa_tides import fetch_high_low
from wcfr.collectors.nws import fetch_marine_grid
from wcfr.collectors.odfw import fetch_report_text, parse_port_catch_rates
from wcfr.collectors.official_landings import fetch_all as fetch_official_landings
from wcfr.collectors.ocean_color import fetch_region as fetch_ocean_color
from wcfr.config import PORTS, REGIONS, TIDE_STATIONS
from wcfr.forecast import predict_location
from wcfr.lunar import lunar_for_day
from wcfr.models import ConditionRecord, SourceRef
from wcfr.report import render_email_summary, render_html
from wcfr.weather_summary import summarize_week


def _observed_condition(region: str, readings: list[dict], checked: str) -> ConditionRecord:
    def avg(key):
        values = [r[key] for r in readings if r.get(key) is not None]
        return sum(values) / len(values) if values else None
    source = SourceRef("NOAA NDBC", "https://www.ndbc.noaa.gov/", checked)
    temp_c = avg("water_temp_c")
    return ConditionRecord(
        region=region, valid_at=checked, source=source,
        wind_knots=(avg("wind_speed_m_s") * 1.94384) if avg("wind_speed_m_s") is not None else None,
        gust_knots=(avg("gust_m_s") * 1.94384) if avg("gust_m_s") is not None else None,
        wave_height_ft=(avg("wave_height_m") * 3.28084) if avg("wave_height_m") is not None else None,
        wave_period_sec=avg("dominant_period_s"),
        water_temp_f=(temp_c * 9 / 5 + 32) if temp_c is not None else None,
    )


def build(day: date, output: Path) -> None:
    checked = datetime.now(timezone.utc).isoformat()
    health: list[dict] = []
    tides = {port: [] for port in TIDE_STATIONS}
    buoys = {region: [] for region in REGIONS}
    marine_forecasts = {region: {} for region in REGIONS}
    ocean_color = {region: {} for region in REGIONS}
    lunar = {}
    catch_records: list[dict] = []
    field_reports: list[dict] = []

    jobs = {}
    with ThreadPoolExecutor(max_workers=16) as pool:
        for port, station in TIDE_STATIONS.items():
            jobs[pool.submit(fetch_high_low, station, day.isoformat())] = ("tide", port, station)
            _, lat, lon = PORTS[port]
            jobs[pool.submit(lunar_for_day, day, lat, lon)] = ("lunar", port, "")
        for region, config in REGIONS.items():
            for station in config["buoys"]:
                jobs[pool.submit(fetch_latest, station)] = ("buoy", region, station)
            lat, lon = config["point"]
            jobs[pool.submit(fetch_marine_grid, lat, lon)] = ("nws", region, "")
            jobs[pool.submit(fetch_ocean_color, lat, lon)] = ("ocean", region, "")
        jobs[pool.submit(fetch_report_text)] = ("odfw", "Oregon", "")
        jobs[pool.submit(fetch_official_landings)] = ("landings", "Official landings", "")
        jobs[pool.submit(fetch_local_reports, day)] = ("local", "Local/private reports", "")

        for future in as_completed(jobs):
            kind, label, station = jobs[future]
            try:
                result = future.result()
                if kind == "tide":
                    tides[label] = result
                    detail, source = f"{len(result)} predictions", f"NOAA CO-OPS {label}"
                elif kind == "lunar":
                    lunar[label] = result
                    detail, source = "lunar events calculated", f"PyEphem {label}"
                elif kind == "buoy":
                    buoys[label].append(result)
                    detail, source = "latest observation retrieved", f"NDBC {station}"
                elif kind == "nws":
                    marine_forecasts[label] = result
                    detail, source = "marine grid retrieved", f"NWS grid {label}"
                elif kind == "ocean":
                    ocean_color[label] = result
                    detail, source = "SST/chlorophyll retrieved", f"NOAA CoastWatch {label}"
                elif kind == "landings":
                    landing_records, landing_health = result
                    catch_records.extend(landing_records)
                    health.extend(landing_health)
                    detail, source = f"{len(landing_records)} catch facts", "Official landing pages"
                elif kind == "local":
                    local_records, local_health = result
                    field_reports.extend(local_records)
                    health.extend(local_health)
                    detail, source = f"{len(local_records)} narrative reports", "Local/private reports"
                else:
                    catch_records.extend(parse_port_catch_rates(result))
                    detail, source = f"{len(catch_records)} structured catch rates", "ODFW Marine Report"
                health.append({"source": source, "ok": True, "detail": detail})
            except Exception as exc:
                source = {
                    "tide": f"NOAA CO-OPS {label}", "lunar": f"PyEphem {label}",
                    "buoy": f"NDBC {station}", "nws": f"NWS grid {label}",
                    "ocean": f"NOAA CoastWatch {label}",
                    "landings": "Official landing pages",
                    "local": "Local/private reports",
                    "odfw": "ODFW Marine Report",
                }[kind]
                health.append({"source": source, "ok": False, "detail": str(exc)})

    predictions = []
    unique_records = {}
    for catch in catch_records:
        key = (
            catch.get("source_url"), catch.get("vessel"), catch.get("species"),
            catch.get("count"), catch.get("catch_per_angler"), catch.get("location_text"),
        )
        unique_records[key] = catch
    catch_records = list(unique_records.values())
    by_region = {region: _observed_condition(region, readings, checked) for region, readings in buoys.items()}
    for region, condition in by_region.items():
        sst = ocean_color.get(region, {}).get("sst")
        if sst:
            condition.water_temp_f = sst["value"]
    for catch in catch_records:
        region = catch["region"]
        catch_rate = catch.get("catch_per_angler")
        signal = min(1.0, catch_rate / 3) if catch_rate is not None else 0.35
        prediction = predict_location(
            catch["species"], region, f"waters accessible from {catch['location_text']}",
            by_region[region], recent_catch_score=signal,
            front_detected=bool(ocean_color.get(region, {}).get("front_detected")),
        )
        predictions.append(asdict(prediction))
    for report in field_reports:
        region = report["region"]
        zone = ", ".join(report.get("places", [])[:3]) or f"waters near {report['city']}"
        for species in report.get("species", []):
            prediction = predict_location(
                species, region, zone, by_region[region], recent_catch_score=0.25,
                front_detected=bool(ocean_color.get(region, {}).get("front_detected")),
                bait_reported="bait" in report.get("conditions", []),
            )
            predictions.append(asdict(prediction))

    for readings in buoys.values():
        readings.sort(key=lambda item: item["station"])
    health.sort(key=lambda item: item["source"])
    predictions.sort(key=lambda item: item["probability_score"], reverse=True)
    daily_weather = {region: summarize_week(value, day) for region, value in marine_forecasts.items()}

    snapshot = {
        "date": day.isoformat(), "checked_at": checked, "catch_records": catch_records,
        "predictions": predictions, "marine_forecasts": marine_forecasts,
        "daily_weather": daily_weather, "ocean_color": ocean_color,
        "field_reports": field_reports,
        "tides": tides, "lunar": lunar, "buoys": buoys, "source_health": health,
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "snapshot.json").write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    (output / "report.html").write_text(render_html(day, snapshot), encoding="utf-8")
    (output / "email.html").write_text(render_email_summary(day, snapshot), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--output", default="output")
    args = parser.parse_args()
    build(date.fromisoformat(args.date), Path(args.output))


if __name__ == "__main__":
    main()
