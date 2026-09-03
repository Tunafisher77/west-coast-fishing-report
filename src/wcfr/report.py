from __future__ import annotations

from datetime import date
from html import escape

from wcfr.config import PRIORITY_SPECIES, REGIONS


def render_html(day: date, tides: dict, buoys: dict, health: list[dict]) -> str:
    tide_rows = []
    for port, values in tides.items():
        summary = ", ".join(f"{v.get('type')} {v.get('t')} ({v.get('v')} ft)" for v in values) or "Unavailable"
        tide_rows.append(f"<tr><td>{escape(port)}</td><td>{escape(summary)}</td></tr>")

    buoy_rows = []
    for region, readings in buoys.items():
        if not readings:
            buoy_rows.append(f"<tr><td>{escape(REGIONS[region]['label'])}</td><td>Unavailable</td></tr>")
            continue
        pieces = []
        for b in readings:
            pieces.append(
                f"{b['station']}: wind {b.get('wind_speed_m_s')} m/s, "
                f"wave {b.get('wave_height_m')} m at {b.get('dominant_period_s')} s, "
                f"water {b.get('water_temp_c')}°C"
            )
        buoy_rows.append(f"<tr><td>{escape(REGIONS[region]['label'])}</td><td>{escape('; '.join(pieces))}</td></tr>")

    health_rows = "".join(
        f"<tr><td>{escape(item['source'])}</td><td>{'OK' if item['ok'] else 'FAILED'}</td><td>{escape(item['detail'])}</td></tr>"
        for item in health
    )
    priority = ", ".join(sorted(PRIORITY_SPECIES))
    return f"""<!doctype html>
<html><body style="font-family:Arial,sans-serif;color:#17202a;max-width:960px;margin:auto">
<h1>West Coast Fishing Intelligence — {day.isoformat()}</h1>
<p><strong>Coverage:</strong> California, Oregon, and Washington. All reported marine species are included; priority watch: {escape(priority)}.</p>
<p><strong>Evidence rule:</strong> “Who/where/what” must come from a cited report. “Why there” is labeled as inference and requires matched environmental evidence.</p>
<h2>Observed buoy conditions</h2>
<table border="1" cellpadding="6" cellspacing="0"><tr><th>Region</th><th>Latest observations</th></tr>{''.join(buoy_rows)}</table>
<h2>Tides</h2>
<table border="1" cellpadding="6" cellspacing="0"><tr><th>Reference port</th><th>High/low predictions (local time, MLLW)</th></tr>{''.join(tide_rows)}</table>
<h2>Catch intelligence</h2>
<p>No catch claim is emitted until an authorized collector supplies a source-attributed record. State fishery collectors are the next implementation stage.</p>
<h2>Source health</h2>
<table border="1" cellpadding="6" cellspacing="0"><tr><th>Source</th><th>Status</th><th>Detail</th></tr>{health_rows}</table>
<p><em>Planning aid only. Verify current NWS, Coast Guard, bar, harbor, and local conditions before departure.</em></p>
</body></html>"""
