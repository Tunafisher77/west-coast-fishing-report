from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timezone
from pathlib import Path

from wcfr.collectors.ndbc import fetch_latest
from wcfr.collectors.noaa_tides import fetch_high_low
from wcfr.config import REGIONS, TIDE_STATIONS
from wcfr.report import render_html


def build(day: date, output: Path) -> None:
    checked = datetime.now(timezone.utc).isoformat()
    health: list[dict] = []
    tides: dict[str, list] = {port: [] for port in TIDE_STATIONS}
    buoys: dict[str, list] = {region: [] for region in REGIONS}

    jobs = {}
    with ThreadPoolExecutor(max_workers=12) as pool:
        for port, station in TIDE_STATIONS.items():
            jobs[pool.submit(fetch_high_low, station, day.isoformat())] = ("tide", port, station)
        for region, config in REGIONS.items():
            for station in config["buoys"]:
                jobs[pool.submit(fetch_latest, station)] = ("buoy", region, station)

        for future in as_completed(jobs):
            kind, label, station = jobs[future]
            try:
                result = future.result()
                if kind == "tide":
                    tides[label] = result
                    detail = f"{len(result)} predictions"
                    source = f"NOAA CO-OPS {label}"
                else:
                    buoys[label].append(result)
                    detail = "latest observation retrieved"
                    source = f"NDBC {station}"
                health.append({"source": source, "ok": True, "detail": detail})
            except Exception as exc:
                source = f"NOAA CO-OPS {label}" if kind == "tide" else f"NDBC {station}"
                health.append({"source": source, "ok": False, "detail": str(exc)})

    for readings in buoys.values():
        readings.sort(key=lambda item: item["station"])
    health.sort(key=lambda item: item["source"])

    output.mkdir(parents=True, exist_ok=True)
    snapshot = {"date": day.isoformat(), "checked_at": checked, "tides": tides, "buoys": buoys, "source_health": health}
    (output / "snapshot.json").write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    (output / "report.html").write_text(render_html(day, tides, buoys, health), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--output", default="output")
    args = parser.parse_args()
    build(date.fromisoformat(args.date), Path(args.output))


if __name__ == "__main__":
    main()
