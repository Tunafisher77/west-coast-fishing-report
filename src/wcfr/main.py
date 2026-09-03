from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timezone
from pathlib import Path

from wcfr.collectors.ndbc import fetch_latest
from wcfr.collectors.noaa_tides import fetch_high_low
from wcfr.config import REGIONS, TIDE_STATIONS
from wcfr.report import render_html


def build(day: date, output: Path) -> None:
    checked = datetime.now(timezone.utc).isoformat()
    health: list[dict] = []
    tides: dict[str, list] = {}
    buoys: dict[str, list] = {}

    for port, station in TIDE_STATIONS.items():
        try:
            tides[port] = fetch_high_low(station, day.isoformat())
            health.append({"source": f"NOAA CO-OPS {port}", "ok": True, "detail": f"{len(tides[port])} predictions"})
        except Exception as exc:
            tides[port] = []
            health.append({"source": f"NOAA CO-OPS {port}", "ok": False, "detail": str(exc)})

    for region, config in REGIONS.items():
        buoys[region] = []
        for station in config["buoys"]:
            try:
                buoys[region].append(fetch_latest(station))
                health.append({"source": f"NDBC {station}", "ok": True, "detail": "latest observation retrieved"})
            except Exception as exc:
                health.append({"source": f"NDBC {station}", "ok": False, "detail": str(exc)})

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
