from __future__ import annotations

import re
from datetime import date, datetime, timezone
from html.parser import HTMLParser

from wcfr.collectors.official_landings import TextLines
from wcfr.http import get_bytes

SOURCES = [
    {
        "name": "Bayside Marine Monterey Bay Report", "city": "Santa Cruz", "state": "CA",
        "region": "central_california", "url": "https://www.baysidemarinesc.com/",
        "mode": "local/private-boat intelligence",
    },
    {
        "name": "Fishing the North Coast", "city": "Eureka", "state": "CA",
        "region": "northern_california", "url": "https://fishingthenorthcoast.com/category/current-fishing-reports/feed/",
        "mode": "multi-port local/private-boat intelligence",
    },
    {
        "name": "Dockside Depoe Bay Daily Report", "city": "Depoe Bay", "state": "OR",
        "region": "oregon", "url": "https://www.docksidedepoebay.com/fishing-report.php",
        "mode": "daily fleet and local conditions", "known_boats": ["Surfrider"],
    },
    {
        "name": "Shake N' Bake Ilwaco Report", "city": "Ilwaco", "state": "WA",
        "region": "washington", "url": "https://www.shakenbakesportfishing.com/fishing-reports",
        "mode": "fleet/private/commercial tuna intelligence",
        "known_boats": ["Shake N' Bake", "SNB", "Legendz", "Salty Dog", "Gold Rush", "Hot Pursuit", "Fury"],
    },
    {
        "name": "WDFW Ocean Salmon Quota Report", "city": "Washington Coast", "state": "WA",
        "region": "washington", "url": "https://wdfw.wa.gov/fishing/reports/creel/ocean",
        "mode": "official recreational creel and quota data",
    },
    {
        "name": "WDFW Marine Creel Reports", "city": "Washington Marine Areas", "state": "WA",
        "region": "washington", "url": "https://wdfw.wa.gov/fishing/reports/creel",
        "mode": "official marine creel directory", "reference_only": True,
    },
    {
        "name": "CDFW Ocean Salmon Tracker", "city": "California Coast", "state": "CA",
        "region": "central_california", "url": "https://wildlife.ca.gov/Fishing/Ocean/Regulations/Salmon",
        "mode": "official recreational/commercial harvest tracker", "reference_only": True,
    },
    {
        "name": "ODFW Ocean Salmon Updates", "city": "Oregon Coast", "state": "OR",
        "region": "oregon", "url": "https://www.dfw.state.or.us/mrp/salmon/updatesnew.asp",
        "mode": "official commercial troll catch and management updates",
    },
    {
        "name": "Oregon Albacore Dock Network", "city": "Oregon Coast", "state": "OR",
        "region": "oregon", "url": "https://www.oregonalbacore.org/on-the-docks",
        "mode": "commercial vessel and dock availability directory", "reference_only": True,
    },
]

MONTHS = {"jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
          "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
          "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9, "oct": 10,
          "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12}
SPECIES = {
    "bluefin": "bluefin tuna", "tuna": "tuna (unspecified)", "salmon": "salmon (unspecified)",
    "halibut": "halibut", "lingcod": "lingcod", "rock fish": "rockfish", "rockfish": "rockfish", "rock fishing": "rockfish",
    "sea bass": "white seabass", "seabass": "white seabass", "striped bass": "striped bass",
    "bonito": "bonito", "albacore": "albacore tuna", "yellowtail": "california yellowtail",
    "marlin": "marlin (unspecified)", "swordfish": "swordfish",
    "chinook": "chinook salmon", "king salmon": "chinook salmon", "coho": "coho salmon",
}
PLACES = ["4 Mile", "5 Mile", "Wilder Ranch", "Davenport", "Capitola", "Pajaro", "Rio Del Mar",
          "Moss Landing", "Natural Bridges", "Davenport Fingers", "601", "Monterey Bay", "Santa Cruz",
          "Fort Bragg", "Bodega Bay", "Trinidad", "Shelter Cove", "the Hat", "Crescent City", "Brookings",
          "Depoe Bay", "Newport", "Garibaldi", "Charleston", "Ilwaco", "Westport", "La Push", "Neah Bay",
          "Columbia River", "125 line"]


def _report_date(label: str, year: int) -> date | None:
    match = re.search(r"(?:^|Updated:\s+)([A-Za-z]+)\.?\s+(\d{1,2})(?:,\s*(\d{4}))?", label, re.I)
    if match and match.group(1).casefold() in MONTHS:
        if not match.group(3) and len(label) > 40:
            return None
        return date(int(match.group(3) or year), MONTHS[match.group(1).casefold()], int(match.group(2)))
    rfc = re.match(r"^(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun),\s+(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", label, re.I)
    if rfc and rfc.group(2).casefold() in MONTHS:
        return date(int(rfc.group(3)), MONTHS[rfc.group(2).casefold()], int(rfc.group(1)))
    # A numeric date may appear after a report title, but require a year so
    # counts/ranges such as "10-14 knots" cannot become false dates.
    numeric = re.search(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b", label)
    if numeric:
        if len(label) > 120:
            return None
        value_year = int(numeric.group(3))
        if value_year < 100: value_year += 2000
        month, day = int(numeric.group(1)), int(numeric.group(2))
        if 1 <= month <= 12 and 1 <= day <= 31:
            try: return date(value_year, month, day)
            except ValueError: return None
    return None


class _ArticleText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "article": self.depth += 1
        elif self.depth: self.depth += 1

    def handle_endtag(self, tag):
        if self.depth: self.depth -= 1

    def handle_data(self, value):
        if self.depth:
            clean = " ".join(value.split())
            if clean: self.parts.append(clean)


def _fetch_north_coast_latest(source: dict, run_day: date) -> dict:
    raw = get_bytes("https://fishingthenorthcoast.com/category/current-fishing-reports/").decode("utf-8", errors="replace")
    candidates = []
    for match in re.finditer(r'href=["\'](https://fishingthenorthcoast\.com/(\d{4})/(\d{2})/(\d{2})/[^"\']+/)["\']', raw):
        published = date(int(match.group(2)), int(match.group(3)), int(match.group(4)))
        if published <= run_day: candidates.append((published, match.group(1)))
    if not candidates: raise RuntimeError("no current North Coast article link found")
    published, url = max(candidates)
    parser = _ArticleText()
    parser.feed(get_bytes(url).decode("utf-8", errors="replace"))
    if not parser.parts: raise RuntimeError("North Coast article returned no readable body")
    item = parse_latest(f"{published.strftime('%B %d, %Y')}\n" + " ".join(parser.parts), {**source, "url": url}, run_day)
    return item


def parse_latest(text: str, source: dict, run_day: date) -> dict:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    start, published, body = None, None, []
    for candidate, line in enumerate(lines):
        candidate_day = _report_date(line, run_day.year)
        if not candidate_day or candidate_day > run_day:
            continue
        candidate_body = []
        for following in lines[candidate + 1:]:
            if _report_date(following, run_day.year): break
            candidate_body.append(following)
        if candidate_body:
            start, published, body = candidate, candidate_day, candidate_body
            break
    if start is None:
        raise RuntimeError("no dated local report found")
    narrative = " ".join(body)
    for bad, good in (("â€“", "-"), ("â€”", "-"), ("â€™", "'"), ("â€œ", '"'), ("â€", '"'), ("Â", "")):
        narrative = narrative.replace(bad, good)
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
            elif any(term in lowered_sentence for term in ("caught", "catching", "finding", "on the bite", "has been great", "best bet", "was best", "landed", "back on top", "did well", "good fishing")):
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
    conditions = [term for term in ("wind", "swell", "calm", "flat", "storm", "red tide", "warm water", "cold water", "blue water", "bait") if term in lowered]
    methods = [term for term in ("trolling", "squid", "mackerel", "anchovies", "Mad Macks", "jigging") if term.casefold() in lowered]
    boats = [boat for boat in source.get("known_boats", []) if boat.casefold() in lowered]
    return {**source, "published_date": published.isoformat(), "age_days": (run_day - published).days,
            "species": species, "species_status": activity, "places": places, "conditions": conditions, "methods": methods, "boats": boats,
            "summary": narrative[:1200], "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "evidence": "local reported observation", "quantitative": False}


def _parse_wdfw(text: str, source: dict, run_day: date) -> dict:
    updated = re.search(r"Updated:\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})", text, re.I)
    if not updated: raise RuntimeError("WDFW update date not found")
    published = datetime.strptime(updated.group(1), "%B %d, %Y").date()
    areas = ["Columbia River", "Westport", "La Push", "Neah Bay"]
    summaries, species, status, places = [], [], {}, []
    for index, area in enumerate(areas):
        start = text.find(area + " Coho quota")
        if start < 0: continue
        next_starts = [text.find(other + " Coho quota", start + 1) for other in areas[index + 1:]]
        end = min((value for value in next_starts if value >= 0), default=len(text))
        section = text[start:end]
        sentence = re.search(r"(?:A total of .*?(?:landing|landed).*?\.|Through .*?landed\.)", section, re.I)
        if sentence:
            summaries.append(f"{area}: {sentence.group(0)}")
            places.append(area)
            for label, normalized in (("Chinook", "chinook salmon"), ("coho", "coho salmon")):
                match = re.search(rf"([\d,]+)\s+{label}", sentence.group(0), re.I)
                if match and int(match.group(1).replace(",", "")) > 0:
                    if normalized not in species: species.append(normalized)
                    status[normalized] = "catch/activity reported"
    if not summaries: raise RuntimeError("WDFW current area summaries not found")
    return {**source, "published_date": published.isoformat(), "age_days": (run_day - published).days,
            "species": species, "species_status": status, "places": places, "conditions": [], "methods": [], "boats": [],
            "summary": " ".join(summaries)[:1200], "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "evidence": "official weekly creel estimate", "quantitative": True}


def fetch_all(run_day: date) -> tuple[list[dict], list[dict]]:
    reports, health = [], []
    for source in SOURCES:
        try:
            if source["name"] == "Fishing the North Coast":
                report = _fetch_north_coast_latest(source, run_day)
                reports.append(report)
                health.append({"source": source["name"], "ok": True,
                               "detail": f"latest multi-port report {report['published_date']} ({report['age_days']} days old)"})
                continue
            parser = TextLines()
            parser.feed(get_bytes(source["url"]).decode("utf-8", errors="replace"))
            if source.get("reference_only"):
                if not parser.lines:
                    raise RuntimeError("reference page returned no readable content")
                health.append({"source": source["name"], "ok": True,
                               "detail": "reference/management source reachable; no same-day catch claim extracted"})
                continue
            text = "\n".join(parser.lines)
            if source["name"] == "Dockside Depoe Bay Daily Report":
                dated = re.search(r"Fishing Report:\s*(\d{1,2}/\d{1,2}/\d{4})", text, re.I)
                if not dated: raise RuntimeError("Dockside report date not found")
                current = text[dated.end():]
                current = re.split(r"Season Info:", current, maxsplit=1, flags=re.I)[0]
                text = dated.group(1) + "\n" + current
            if source["name"] == "WDFW Ocean Salmon Quota Report":
                report = _parse_wdfw(text, source, run_day)
            else:
                report = parse_latest(text, source, run_day)
            reports.append(report)
            health.append({"source": source["name"], "ok": True,
                           "detail": f"latest local report {report['published_date']} ({report['age_days']} days old)"})
        except Exception as exc:
            health.append({"source": source["name"], "ok": False, "detail": str(exc)})
    return reports, health
