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
    """Decision-first regional brief; full diagnostics stay in report.html."""
    catches = data["catch_records"]
    by_landing, by_region = {}, {}
    for catch in catches:
        landing = catch.get("location_text") or catch.get("reporter") or "Unspecified"
        by_landing.setdefault(landing, []).append(catch)
        by_region.setdefault(catch["region"], []).append(catch)

    def fmt_wind(speed, gust):
        if speed is None: return "not supplied"
        return f"{speed} kt" + (f", gusting {gust} kt" if gust is not None else "")

    def color_words(chl):
        if not chl: return "Satellite water-color reading unavailable or cloud obscured"
        value = chl["value"]
        if value < .15: meaning = "very clear blue water with little plankton signal"
        elif value <= .35: meaning = "a clean blue-green band often useful for locating offshore edges"
        elif value <= 1.0: meaning = "productive green water that may hold forage near its cleaner boundary"
        else: meaning = "strong green/plankton-rich water; the cleaner outer edge is usually more relevant than its center"
        return f"Water color: {meaning} ({value:.2f} mg/m³; {chl['observed_at'][:10]})"

    cards = []
    for region, config in REGIONS.items():
        records = by_region.get(region, [])
        local = [r for r in data.get("field_reports", []) if r["region"] == region]
        oc = data.get("ocean_color", {}).get(region, {})
        sst, chl = oc.get("sst"), oc.get("chlorophyll")
        readings = data.get("buoys", {}).get(region, [])
        buoy_temps = [b["water_temp_c"] * 9 / 5 + 32 for b in readings if b.get("water_temp_c") is not None]
        periods = [b["dominant_period_s"] for b in readings if b.get("dominant_period_s") is not None]
        waves = [b["wave_height_m"] * 3.28084 for b in readings if b.get("wave_height_m") is not None]
        if sst:
            water = f"Satellite SST {sst['value']:.1f}°F; sampled range {sst['minimum']:.1f}-{sst['maximum']:.1f}°F ({sst['observed_at'][:10]})"
        elif buoy_temps:
            water = f"Buoy SST {min(buoy_temps):.1f}-{max(buoy_temps):.1f}°F (satellite SST unavailable/cloud obscured)"
        else:
            water = "SST unavailable from both satellite samples and reporting buoys"
        observed = "Observed swell unavailable"
        if waves:
            observed = f"Current buoy seas {sum(waves)/len(waves):.1f} ft"
            observed += f" with {sum(periods)/len(periods):.0f}-second dominant period" if periods else "; buoy period unavailable"

        landing_lines = []
        for landing, grouped in sorted(by_landing.items()):
            if grouped[0]["region"] != region: continue
            first = grouped[0]
            place = ", ".join(v for v in (first.get("city"), first.get("state")) if v)
            totals = []
            for species in sorted({r["species"] for r in grouped}):
                matching = [r for r in grouped if r["species"] == species]
                counts = [r["count"] for r in matching if r.get("count") is not None]
                rates = [r["catch_per_angler"] for r in matching if r.get("catch_per_angler") is not None]
                value = f"{sum(counts):g}" if counts else f"{max(rates):g}/angler" if rates else "reported"
                totals.append(f"{value} {species.title()}")
            landing_lines.append(f"<li><strong>{escape(landing)} ({escape(place)}):</strong> {escape(', '.join(totals))}</li>")
        if not landing_lines: landing_lines = ["<li>No current verified catch report retrieved.</li>"]

        species = sorted({r["species"].title() for r in records} | {s.title() for r in local for s in r.get("species", [])})
        if records and oc.get("front_detected"):
            why = f"The reported {', '.join(species[:4])} coincide with a measurable change in temperature or water color. That boundary can gather bait and is the leading regional explanation."
        elif (records or local) and (sst or buoy_temps):
            why = f"The reported {', '.join(species[:4])} occurred in the water-temperature band shown above, but no strong regional color/temperature edge was verified. Bait or local structure is the more cautious explanation."
        elif records or local:
            why = "Catches are verified, but environmental coverage is insufficient to explain them confidently."
        else:
            why = "No current catch evidence is available for a catch-location conclusion."

        daily = []
        for row in data.get("daily_weather", {}).get(region, []):
            sea = "NWS seas not supplied" if row["wave_ft"] is None else f"{row['wave_ft']} ft"
            sea += f" at {row['period_s']} sec" if row.get("period_s") is not None else "; forecast swell period not supplied"
            direction = f" from {row['wave_direction_deg']}°" if row.get("wave_direction_deg") is not None else ""
            flag = "AVOID - safety screen" if row["safety_block"] else f"Prefer {row['best_window']}"
            daily.append(f"<tr><td>{escape(row['date'][5:])}</td><td>{escape(fmt_wind(row['wind_am_kt'], row['gust_am_kt']))}</td><td>{escape(fmt_wind(row['wind_pm_kt'], row['gust_pm_kt']))}</td><td>{escape(sea + direction)}</td><td>{escape(flag)}<br><small>{row['confidence']} confidence</small></td></tr>")

        region_predictions, prediction_seen = [], set()
        for prediction in data["predictions"]:
            key = (prediction["species"], prediction["zone"])
            if prediction["region"] != region or key in prediction_seen: continue
            prediction_seen.add(key)
            region_predictions.append(prediction)
            if len(region_predictions) == 3: break
        fish_line = "; ".join(f"{p['species'].title()} - {p['zone']} ({p['probability_score']}/100, {p['confidence']})" for p in region_predictions) or "No evidence-supported species prediction"
        quantitative_sources = len({r.get("reporter") for r in records if r.get("reporter")})
        coverage_parts = [f"{quantitative_sources} quantitative source(s)", f"{len(local)} local/private report(s)"]
        coverage_parts.append("satellite ocean color" if sst or chl else "buoy-only ocean temperature")
        coverage_level = "strong" if quantitative_sources and local and (sst or chl) else "partial" if quantitative_sources or local else "weak"
        local_lines = []
        for item in local:
            freshness = "current" if item["age_days"] <= 2 else "recent" if item["age_days"] <= 7 else "stale context"
            places = ", ".join(item.get("places", [])) or "general area not specified"
            methods = ", ".join(item.get("methods", [])) or "method not stated"
            confirmed = ", ".join(s.title() for s in item.get("species", [])) or "no catch confirmed"
            negative = ", ".join(s.title() for s, status in item.get("species_status", {}).items() if "little or no" in status)
            negative_text = f"; searched with little/no action: {negative}" if negative else ""
            local_lines.append(f"<li><strong>{escape(item['name'])} ({freshness}, {item['published_date']}):</strong> "
                               f"catch/activity: {escape(confirmed)}{escape(negative_text)}; "
                               f"areas: {escape(places)}; methods/bait: {escape(methods)}. "
                               f"<a href=\"{escape(item['url'])}\">Source</a></li>")
        if not local_lines: local_lines = ["<li>No permitted current local/private-boat narrative source was retrieved.</li>"]

        cards.append(f"""<section style="border:1px solid #ccd6dd;border-radius:7px;margin:18px 0;padding:14px">
<h2 style="margin:0 0 8px;color:#154360">{escape(config['label'])}</h2>
<p style="margin:0 0 8px;color:#566573"><strong>Coverage: {coverage_level.title()}</strong> - {escape('; '.join(coverage_parts))}</p>
<p><strong>Fish outlook:</strong> {escape(fish_line)}</p>
<p><strong>Ocean now:</strong> {escape(water)}.<br>{escape(color_words(chl))}.<br>{escape(observed)}.</p>
<p><strong>Why here:</strong> {escape(why)} <em>This is a regional environmental comparison, not an undisclosed catch coordinate.</em></p>
<p><strong>Recent verified catches:</strong></p><ul>{''.join(landing_lines)}</ul>
<p><strong>Local and private-boat intelligence:</strong></p><ul>{''.join(local_lines)}</ul>
<table style="border-collapse:collapse;width:100%;font-size:13px" border="1" cellpadding="5"><tr style="background:#eef3f5"><th>Date</th><th>Morning wind</th><th>Afternoon wind</th><th>Combined seas / period</th><th>Decision</th></tr>{''.join(daily)}</table>
</section>""")

    opportunities = []
    active_regions = set(by_region) | {r["region"] for r in data.get("field_reports", [])}
    for region in active_regions:
        records = by_region.get(region, [])
        fish = sorted({r["species"].title() for r in records} | {s.title() for r in data.get("field_reports", []) if r["region"] == region for s in r.get("species", [])})
        candidates = [r for r in data.get("daily_weather", {}).get(region, []) if not r["safety_block"]]
        if not candidates: continue
        def burden(row):
            wind = max(v for v in (row["wind_am_kt"], row["wind_pm_kt"], row["gust_am_kt"], row["gust_pm_kt"]) if v is not None)
            return wind + (row["wave_ft"] or 20) * 2
        best = min(candidates, key=burden)
        opportunities.append((burden(best), f"<li><strong>{escape(REGIONS[region]['label'])} - {escape(best['date'][5:])} {best['best_window']}:</strong> {escape(', '.join(fish[:4]))}; forecast {best['wave_ft'] or 'unavailable'} ft seas and lighter-window wind. Confirm the current forecast before departure.</li>"))
    opportunities.sort(key=lambda item: item[0])
    opportunity_html = "".join(item[1] for item in opportunities[:3]) or "<li>No region has both a verified recent catch and a usable marine forecast.</li>"

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
<strong>Decision brief:</strong> {len(catches)} catch facts from {len(by_landing)} landing/port sources. Each regional card connects catches, ocean water, fish potential, and changing daily weather. {failed} failed source checks are excluded.
</div>
<h2>Best supported opportunities</h2><ul>{opportunity_html}</ul>
{''.join(cards)}
<h2>Coverage and delayed datasets</h2>
<p><strong>Private boats:</strong> Current local reports appear inside each regional card. Official private/rental-boat estimates from <a href="https://www.recfin.org/">RecFIN</a> and state creel programs are sampled and delayed; they will be used as trend context, not daily counts.</p>
<p><strong>Commercial:</strong> <a href="https://pacfin.psmfc.org/">PacFIN</a> and PFMC fish-ticket/HMS information is delayed. No same-day commercial landing feed was retrieved, so no commercial catch claim is made today.</p>
<p><strong>Coverage rule:</strong> “No report retrieved” means the connected sources supplied no usable current record. It does not mean no fish were caught.</p>
<p><strong>Moon:</strong> {escape(moon_text)}</p>
<p><a href="{full_url}">View detailed source data, all tides, forecasts and diagnostics</a></p>
<p style="font-size:12px;color:#626567">Reported catches and model inferences are kept separate. Safety conditions override fishing potential. Verify current NWS, Coast Guard, bar and harbor information before departure.</p>
</body></html>"""


def _catch_detail_rows(records: list[dict], field_reports: list[dict] | None = None) -> str:
    """Preserve boat and trip detail instead of collapsing everything by landing."""
    groups: dict[tuple, list[dict]] = {}
    for record in records:
        key = (record.get("reporter"), record.get("vessel"), record.get("source_excerpt"))
        groups.setdefault(key, []).append(record)
    rows = []
    for (reporter, vessel, excerpt), grouped in groups.items():
        first = grouped[0]
        catches = []
        for item in grouped:
            amount = f"{item['count']:g}" if item.get("count") is not None else (
                f"{item['catch_per_angler']:g}/angler" if item.get("catch_per_angler") is not None else "reported"
            )
            catches.append(f"{amount} {item['species'].title()}")
        boat = vessel or "Boat not identified"
        port = first.get("location_text") or reporter or "Port not identified"
        basis = "Port only - offshore catch position not reported"
        matching_reports = []
        record_species = {item["species"] for item in grouped}
        for report in field_reports or []:
            if record_species.intersection(report.get("species", [])) and report.get("places"):
                matching_reports.append(report)
        if matching_reports:
            places = []
            for report in matching_reports:
                places.extend(place for place in report["places"] if place not in places)
            newest = max(matching_reports, key=lambda item: item.get("published_date", ""))
            confidence = "medium" if newest.get("age_days", 99) <= 2 else "low"
            basis = f"Triangulated estimate: {', '.join(places[:5])} ({confidence} confidence; matching {newest['name']} report)"
        context = escape(excerpt[:360]) if excerpt else "Official port-level catch estimate; charter and private modes may be combined."
        url = first.get("source_url", "")
        rows.append(f"""<tr>
<td><strong>{escape(boat)}</strong><br><small>{escape(str(reporter or 'Unknown reporter'))}</small></td>
<td><strong>{escape(port)}</strong><br><small>{basis}</small></td>
<td>{escape(', '.join(catches))}</td>
<td>{context}<br><a href="{escape(url)}">Source</a></td>
</tr>""")
    return "".join(rows) or '<tr><td colspan="4">No current quantitative catch report retrieved.</td></tr>'


def _field_report_cards(reports: list[dict]) -> str:
    blocks = []
    for item in sorted(reports, key=lambda x: x.get("published_date", ""), reverse=True):
        places = item.get("places", [])
        location = ", ".join(places) or f"general waters near {item.get('city', 'the reporting port')}"
        basis = "Reported catch area" if places else "Regional report; exact position not supplied"
        fish = ", ".join(s.title() for s in item.get("species", [])) or "No positive catch confirmed"
        methods = ", ".join(item.get("methods", [])) or "not stated"
        conditions = ", ".join(item.get("conditions", [])) or "not stated"
        boats = ", ".join(item.get("boats", [])) or "not identified"
        age = item.get("age_days", "?")
        confidence = "high" if places and age != "?" and age <= 2 else "medium" if age != "?" and age <= 7 else "low"
        blocks.append(f"""<div style="border-left:4px solid #2874a6;background:#f7fafc;padding:9px 11px;margin:8px 0">
<strong>{escape(item['name'])}</strong> <span style="color:#566573">- {escape(item.get('published_date','date unavailable'))}</span><br>
<strong>Where:</strong> {escape(location)} <small>({basis}; {confidence} confidence)</small><br>
<strong>Catch/activity:</strong> {escape(fish)}<br>
<strong>Boats named:</strong> {escape(boats)}<br>
<strong>Conditions:</strong> {escape(conditions)} &nbsp; <strong>Method/bait:</strong> {escape(methods)}<br>
<span style="color:#4d5656">{escape(item.get('summary','')[:650])}</span> <a href="{escape(item['url'])}">Source</a>
</div>""")
    return "".join(blocks) or '<p style="color:#707b7c">No current permitted local/private-boat narrative was retrieved.</p>'


def render_email_summary_v2(day: date, data: dict) -> str:
    catches = data.get("catch_records", [])
    field_reports = data.get("field_reports", [])
    by_region: dict[str, list[dict]] = {}
    for catch in catches:
        by_region.setdefault(catch["region"], []).append(catch)
    fields_by_region: dict[str, list[dict]] = {}
    for report in field_reports:
        fields_by_region.setdefault(report["region"], []).append(report)

    regional_cards = []
    for region, config in REGIONS.items():
        records = by_region.get(region, [])
        reports = fields_by_region.get(region, [])
        readings = data.get("buoys", {}).get(region, [])
        temps = [b["water_temp_c"] * 9 / 5 + 32 for b in readings if b.get("water_temp_c") is not None]
        waves = [b["wave_height_m"] * 3.28084 for b in readings if b.get("wave_height_m") is not None]
        periods = [b["dominant_period_s"] for b in readings if b.get("dominant_period_s") is not None]
        oc = data.get("ocean_color", {}).get(region, {})
        sst, chl = oc.get("sst"), oc.get("chlorophyll")
        water_bits = []
        if sst: water_bits.append(f"Satellite SST {sst['value']:.1f} F ({sst['minimum']:.1f}-{sst['maximum']:.1f} F sampled)")
        elif temps: water_bits.append(f"Buoy water {min(temps):.1f}-{max(temps):.1f} F; satellite SST unavailable")
        else: water_bits.append("Water temperature unavailable")
        if chl: water_bits.append(f"chlorophyll {chl['value']:.2f} mg/m3")
        else: water_bits.append("satellite color unavailable")
        if waves:
            sea = f"observed seas {sum(waves)/len(waves):.1f} ft"
            sea += f" at {sum(periods)/len(periods):.0f} sec" if periods else "; period unavailable"
            water_bits.append(sea)
        species = sorted({r["species"].title() for r in records} | {s.title() for x in reports for s in x.get("species", [])})
        weather = data.get("weekly_weather", {}).get(region, {}).get("text", "Seven-day synopsis unavailable.")
        if records or reports:
            where_summary = "Named areas below are source-reported. Port-only catches remain port-level; broader offshore zones require corroborating water and narrative evidence."
        else:
            where_summary = "No current catch evidence supports a fishing-zone estimate."
        coverage = f"{len(records)} quantitative catch facts; {len(reports)} local/private/commercial narratives"
        regional_cards.append(f"""<section style="border:1px solid #ccd6dd;border-radius:8px;margin:18px 0;padding:15px">
<h2 style="margin:0;color:#154360">{escape(config['label'])}</h2>
<p style="margin:3px 0 12px;color:#5d6d7e">{escape(coverage)}</p>
<div style="background:#eef6fc;padding:10px 12px"><strong>Current picture:</strong> {escape(', '.join(species[:8]) or 'No evidence-supported active species')}<br>
<strong>Ocean:</strong> {escape('; '.join(water_bits))}</div>
<h3 style="margin-bottom:4px">Where fish were reported or estimated</h3>
<p style="margin-top:0;font-size:13px;color:#566573">{escape(where_summary)}</p>
{_field_report_cards(reports)}
<h3>Boat and landing catch detail</h3>
<table style="border-collapse:collapse;width:100%;font-size:12px" border="1" cellpadding="6">
<tr style="background:#eaf2f8"><th>Boat / reporter</th><th>Location basis</th><th>Catch</th><th>Trip evidence</th></tr>{_catch_detail_rows(records, reports)}</table>
<h3 style="margin-bottom:4px">Seven-day marine synopsis</h3><p style="margin-top:0">{escape(weather)}</p>
</section>""")

    failed = [item for item in data.get("source_health", []) if not item["ok"]]
    unique_sources = {r.get("reporter") for r in catches if r.get("reporter")} | {r.get("name") for r in field_reports}
    full_url = f"https://github.com/Tunafisher77/west-coast-fishing-report/tree/main/archive/{day.isoformat()}"
    return f"""<!doctype html><html><body style="font-family:Arial,sans-serif;color:#17202a;max-width:820px;margin:auto;line-height:1.42">
<h1 style="margin-bottom:3px">West Coast Fishing Intelligence</h1>
<p style="margin-top:0;color:#566573">{day.isoformat()} - California, Oregon and Washington</p>
<div style="background:#154360;color:white;padding:14px 16px;border-radius:7px">
<strong>Today at a glance</strong><br>{len(catches)} quantitative catch facts and {len(field_reports)} local/private/commercial narratives from {len(unique_sources)} named sources. {len(failed)} failed checks are excluded rather than treated as “no fish.”
</div>
<p><strong>How to read locations:</strong> Reported areas come directly from a named source. Triangulated estimates use multiple reports plus ocean conditions and are labeled as estimates. “Port only” means the fish were landed there but the offshore catch position was not published.</p>
{''.join(regional_cards)}
<p><a href="{full_url}">Detailed source data, tides, complete forecasts and diagnostics</a></p>
<p style="font-size:12px;color:#626567">Planning aid only. Reported facts and model inference are kept separate. Verify current NWS, Coast Guard, bar and harbor conditions before departure.</p>
</body></html>"""


# The email uses the information-dense regional layout; report.html retains full diagnostics.
render_email_summary = render_email_summary_v2
