from __future__ import annotations

from datetime import date
from html import escape

from wcfr.config import PRIORITY_SPECIES, REGIONS


def _table(headers, rows):
    head = "".join(f"<th>{escape(h)}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{escape(str(v))}</td>" for v in row) + "</tr>" for row in rows)
    return f'<table border="1" cellpadding="6" cellspacing="0"><tr>{head}</tr>{body}</table>'


def render_html(day: date, data: dict) -> str:
    catches = data["catch_records"]
    catch_rows = [
        (c["species"], c["location_text"], c["reporter"], c["catch_per_angler"], "Reported", c["source_url"])
        for c in catches
    ] or [("No structured catch records retrieved", "", "", "", "", "")]

    prediction_rows = []
    for p in data["predictions"][:15]:
        status = "PASS" if p["safe_to_recommend"] else "SAFETY BLOCK"
        prediction_rows.append((
            p["species"], p["zone"], p["probability_score"], p["confidence"], status,
            p["likely_feature"], "; ".join(p["reasons"]) or "Evidence incomplete",
            "; ".join(p["invalidators"]),
        ))
    if not prediction_rows:
        prediction_rows = [("No evidence-supported prediction", "", "", "", "", "", "", "")]

    tide_rows = []
    for port, values in data["tides"].items():
        summary = ", ".join(f"{v.get('type')} {v.get('t')} ({v.get('v')} ft)" for v in values) or "Unavailable"
        moon = data["lunar"].get(port, {})
        lunar = (
            f"{moon.get('phase', 'unavailable')}; {moon.get('illumination_percent', '?')}% illuminated; "
            f"overhead {moon.get('overhead_utc', 'unavailable')}"
        )
        tide_rows.append((port, summary, lunar))

    buoy_rows = []
    for region, readings in data["buoys"].items():
        summary = "; ".join(
            f"{b['station']}: wind {b.get('wind_speed_m_s')} m/s, "
            f"wave {b.get('wave_height_m')} m/{b.get('dominant_period_s')} s, "
            f"water {b.get('water_temp_c')}°C" for b in readings
        ) or "Unavailable"
        forecast = data["marine_forecasts"].get(region, {})
        buoy_rows.append((REGIONS[region]["label"], summary, forecast.get("updated", "Unavailable")))

    health_rows = [
        (h["source"], "OK" if h["ok"] else "FAILED", h["detail"]) for h in data["source_health"]
    ]
    priority = ", ".join(sorted(PRIORITY_SPECIES))
    return f"""<!doctype html>
<html><body style="font-family:Arial,sans-serif;color:#17202a;max-width:1100px;margin:auto">
<h1>West Coast Fishing Intelligence — {day.isoformat()}</h1>
<p><strong>Coverage:</strong> California, Oregon, and Washington; all reported marine species. Priority watch: {escape(priority)}.</p>
<p><strong>Evidence rule:</strong> Who/what/where are reported facts with sources. Why there and week-ahead locations are model inferences, not reported catch positions.</p>
<h2>What was caught, where, and who reported it</h2>
{_table(["Species","Location/port","Reporter","Catch/angler","Evidence","Source"], catch_rows)}
<h2>Week-ahead fish-location outlook</h2>
<p>Scores are provisional habitat scores—not calibrated catch probabilities. A safety block overrides the fish score.</p>
{_table(["Species","Likely zone","Score","Confidence","Safety","Why there","Supporting evidence","Invalidated if"], prediction_rows)}
<h2>Observed and forecast marine conditions</h2>
{_table(["Region","Latest buoy observations","NWS grid updated"], buoy_rows)}
<h2>Tides and lunar cycle</h2>
{_table(["Reference port","High/low tides (local, MLLW)","Lunar context"], tide_rows)}
<h2>Source health</h2>
{_table(["Source","Status","Detail"], health_rows)}
<p><em>Planning aid only. Verify current NWS, Coast Guard, bar, harbor, and local conditions before departure.</em></p>
</body></html>"""
