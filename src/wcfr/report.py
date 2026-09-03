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


def render_email_summary(day: date, data: dict) -> str:
    """Short decision brief; full diagnostics stay in report.html."""
    catches = data["catch_records"]
    by_landing = {}
    for catch in catches:
        landing = catch.get("location_text") or catch.get("reporter") or "Unspecified"
        by_landing.setdefault(landing, []).append(catch)

    landing_items = []
    for landing, records in sorted(by_landing.items()):
        species_totals = {}
        vessels = set()
        for record in records:
            species = record["species"].title()
            count = record.get("count")
            if count is not None:
                species_totals[species] = species_totals.get(species, 0) + count
            else:
                rate = record.get("catch_per_angler")
                species_totals[species] = f"{rate:g}/angler" if rate is not None else "reported"
            if record.get("vessel"):
                vessels.add(record["vessel"])
        catch_text = ", ".join(
            f"{value:g} {species}" if isinstance(value, (int, float)) else f"{species} {value}"
            for species, value in sorted(species_totals.items())
        )
        vessel_text = f" - {', '.join(sorted(vessels)[:5])}" if vessels else ""
        landing_items.append(f"<li><strong>{escape(landing)}</strong>{escape(vessel_text)}: {escape(catch_text)}</li>")
    if not landing_items:
        landing_items = ["<li>No current source-attributed landing reports were retrieved.</li>"]

    outlook_items = []
    seen = set()
    for prediction in data["predictions"]:
        key = (prediction["species"], prediction["zone"])
        if key in seen:
            continue
        seen.add(key)
        safety = "Do not recommend - safety screen failed" if not prediction["safe_to_recommend"] else "Fishable"
        why = prediction["reasons"][0] if prediction["reasons"] else "limited supporting evidence"
        outlook_items.append(
            f"<li><strong>{escape(prediction['species'].title())} - {escape(prediction['zone'])}</strong> "
            f"({prediction['confidence']} confidence, {prediction['probability_score']}/100): "
            f"{escape(why)}. <em>{escape(safety)}</em></li>"
        )
        if len(outlook_items) == 5:
            break
    if not outlook_items:
        outlook_items = ["<li>No location forecast met the minimum evidence requirement.</li>"]

    condition_items = []
    for region, readings in data["buoys"].items():
        winds = [b["wind_speed_m_s"] * 1.94384 for b in readings if b.get("wind_speed_m_s") is not None]
        waves = [b["wave_height_m"] * 3.28084 for b in readings if b.get("wave_height_m") is not None]
        temps = [b["water_temp_c"] * 9 / 5 + 32 for b in readings if b.get("water_temp_c") is not None]
        parts = []
        if winds: parts.append(f"wind {sum(winds)/len(winds):.0f} kt")
        if waves: parts.append(f"seas {sum(waves)/len(waves):.1f} ft")
        if temps: parts.append(f"water {sum(temps)/len(temps):.1f}°F")
        condition_items.append(f"<li><strong>{escape(REGIONS[region]['label'])}:</strong> {escape(', '.join(parts) or 'data unavailable')}</li>")

    moon = data["lunar"].get("San Diego", {})
    moon_text = (
        f"{moon.get('phase', 'unavailable').title()}, "
        f"{moon.get('illumination_percent', '?')}% illuminated. Tide details are included only when relevant to a highlighted bite."
    )
    failed = sum(not item["ok"] for item in data["source_health"])
    full_url = f"https://github.com/Tunafisher77/west-coast-fishing-report/tree/main/archive/{day.isoformat()}"
    return f"""<!doctype html><html><body style="font-family:Arial,sans-serif;color:#17202a;max-width:760px;margin:auto;line-height:1.4">
<h1 style="margin-bottom:4px">West Coast Fishing Brief</h1>
<p style="margin-top:0;color:#566573">{day.isoformat()} - California, Oregon, Washington</p>
<div style="background:#eef6fc;padding:12px 16px;border-left:5px solid #2471a3">
<strong>At a glance:</strong> {len(catches)} catch facts from {len(by_landing)} landing/port sources. {failed} source checks failed and were excluded.
</div>
<h2>What is being caught</h2><ul>{''.join(landing_items)}</ul>
<h2>Where fish are most likely this week</h2><ul>{''.join(outlook_items)}</ul>
<h2>Marine snapshot</h2><ul>{''.join(condition_items)}</ul>
<p><strong>Moon:</strong> {escape(moon_text)}</p>
<p><a href="{full_url}">View detailed source data, all tides, forecasts and diagnostics</a></p>
<p style="font-size:12px;color:#626567">Reported catches and model inferences are kept separate. Safety conditions override fishing potential. Verify current NWS, Coast Guard, bar and harbor information before departure.</p>
</body></html>"""
