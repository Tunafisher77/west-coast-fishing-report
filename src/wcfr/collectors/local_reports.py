from __future__ import annotations

import re
from datetime import date, datetime, timezone

from wcfr.collectors.official_landings import TextLines
from wcfr.http import get_bytes

SOURCES = [
    {
        "name": "Bayside Marine Monterey Bay Report", "city": "Santa Cruz", "state": "CA",
        "region": "central_california", "url": "https://www.baysidemarinesc.com/",
        "mode": "local/private-boat intelligence",
    },
]

MONTHS = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
          "jul": 7, "aug": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12}
SPECIES = {
    "bluefin": "bluefin tuna", "tuna": "tuna (unspecified)", "salmon": "salmon (unspecified)",
    "halibut": "halibut", "lingcod": "lingcod", "rock fish": "rockfish", "rockfish": "rockfish", "rock fishing": "rockfish",
    "sea bass": "white seabass", "seabass": "white seabass", "striped bass": "striped bass",
    "bonito": "bonito", "albacore": "albacore tuna", "yellowtail": "california yellowtail",
    "marlin": "marlin (unspecified)", "swordfish": "swordfish",
}
PLACES = ["4 Mile", "5 Mile", "Wilder Ranch", "Davenport", "Capitola", "Pajaro", "Rio Del Mar",
          "Moss Landing", "Natural Bridges", "Davenport Fingers", "601", "Monterey Bay", "Santa Cruz"]


def _report_date(label: str, year: int) -> date | None:
    match = re.match(r"([A-Za-z]+)\.?\s+(\d{1,2})", label)
    if not match or match.group(1).casefold() not in MONTHS:
        return None
    return date(year, MONTHS[match.group(1).casefold()], int(match.group(2)))


def parse_latest(text: str, source: dict, run_day: date) -> dict:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    start = next((i for i, line in enumerate(lines) if _report_date(line, run_day.year)), None)
    if start is None:
        raise RuntimeError("no dated local report found")
    published = _report_date(lines[start], run_day.year)
    body = []
    for line in lines[start + 1:]:
        if _report_date(line, run_day.year): break
        body.append(line)
    narrative = " ".join(body)
    if not narrative:
        raise RuntimeError("latest dated report has no narrative")
    lowered = narrative.casefold()
    activity: dict[str, str] = {}
    for sentence in re.split(r"(?<=[.!?])\s+", narrative):
        lowered_sentence = sentence.casefold()
        for phrase, normalized in SPECIES.items():
            if not re.search(rf"\b{re.escape(phrase)}\b", lowered_sentence): continue
            if any(term in lowered_sentence for term in ("season is open", "season opens", "retention is open")):
                status = "regulation/target mention"
            elif any(term in lowered_sentence for term in ("did not find", "no action", "not much action", "no fish", "slow")):
                status = "searched; little or no action"
            elif any(term in lowered_sentence for term in ("caught", "catching", "finding", "on the bite", "has been great", "best bet", "was best", "landed")):
                status = "catch/activity reported"
            else:
                status = "mentioned; catch not confirmed"
            if status == "catch/activity reported" or normalized not in activity:
                activity[normalized] = status
    species = [name for name, status in activity.items() if status == "catch/activity reported"]
    if any(item.endswith("tuna") and item != "tuna (unspecified)" for item in species):
        species = [item for item in species if item != "tuna (unspecified)"]
    places = [place for place in PLACES if place.casefold() in lowered]
    if re.search(r"\bH\.?M\.?B\.?\b", narrative, re.I):
        places.append("Half Moon Bay")
    conditions = [term for term in ("wind", "swell", "calm", "red tide", "warm water", "cold water", "bait") if term in lowered]
    methods = [term for term in ("trolling", "squid", "mackerel", "anchovies", "Mad Macks", "jigging") if term.casefold() in lowered]
    return {**source, "published_date": published.isoformat(), "age_days": (run_day - published).days,
            "species": species, "species_status": activity, "places": places, "conditions": conditions, "methods": methods,
            "summary": narrative[:1200], "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "evidence": "local reported observation", "quantitative": False}


def fetch_all(run_day: date) -> tuple[list[dict], list[dict]]:
    reports, health = [], []
    for source in SOURCES:
        try:
            parser = TextLines()
            parser.feed(get_bytes(source["url"]).decode("utf-8", errors="replace"))
            report = parse_latest("\n".join(parser.lines), source, run_day)
            reports.append(report)
            health.append({"source": source["name"], "ok": True,
                           "detail": f"latest local report {report['published_date']} ({report['age_days']} days old)"})
        except Exception as exc:
            health.append({"source": source["name"], "ok": False, "detail": str(exc)})
    return reports, health
