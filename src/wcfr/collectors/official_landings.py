from __future__ import annotations

import re
from datetime import datetime, timezone
from html.parser import HTMLParser

from wcfr.http import get_bytes

SOURCES = [
    ("Fisherman's Landing", "San Diego", "CA", "https://www.fishermanslanding.com/fishcounts.php", "southern_california"),
    ("Seaforth Landing", "San Diego", "CA", "https://www.seaforthlanding.com/fishcounts.php", "southern_california"),
    ("Redondo Beach Sportfishing", "Redondo Beach", "CA", "https://www.redondosportfishing.com/fish-counts.php", "southern_california"),
    ("Virg's Landing", "Morro Bay", "CA", "https://www.virgslanding.com/fish-counts.php", "central_california"),
]

SPECIES = [
    "bluefin tuna", "yellowfin tuna", "albacore tuna", "bigeye tuna", "skipjack tuna",
    "california yellowtail", "yellowtail", "white seabass", "chinook salmon", "king salmon",
    "coho salmon", "striped marlin", "blue marlin", "swordfish", "dorado", "mahi mahi",
    "calico bass", "sand bass", "kelp bass", "spotted bay bass", "bonito", "barracuda",
    "rockfish", "rock cod", "rockcod", "lingcod", "halibut", "whitefish", "sheephead",
    "sculpin", "cabezon", "bocaccio", "red rockfish", "vermilion rockfish", "copper rockfish",
    "blue perch", "sargo", "rock sole",
]
SPECIES_PATTERN = "|".join(re.escape(s) for s in sorted(SPECIES, key=len, reverse=True))


class TextLines(HTMLParser):
    def __init__(self):
        super().__init__()
        self.lines: list[str] = []
        self.current: list[str] = []

    def handle_data(self, data: str) -> None:
        value = " ".join(data.split())
        if value:
            self.current.append(value)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"p", "li", "tr", "div", "br"} and self.current:
            self.lines.append(" ".join(self.current))
            self.current = []


def parse_landing_text(text: str, landing: str, url: str, region: str, city: str = "", state: str = "") -> list[dict]:
    retrieved = datetime.now(timezone.utc).isoformat()
    records = []
    seen = set()
    for line in text.splitlines():
        catches = [
            (int(m.group(1)), m.group(2).casefold())
            for m in re.finditer(rf"\b(\d+)\s+({SPECIES_PATTERN})s?\b", line, re.I)
        ]
        if not catches:
            continue
        anglers_match = re.search(r"\b(?:for|with)\s+(\d+)\s+anglers?\b", line, re.I)
        anglers = int(anglers_match.group(1)) if anglers_match else None
        vessel_match = re.search(
            r"\b(?:The\s+)?([A-Z][A-Za-z0-9' -]{1,35}?)(?:\s+(?:returned|called|finished|caught|on a|with a))\b",
            line,
        )
        vessel = vessel_match.group(1).strip() if vessel_match else None
        for count, species in catches:
            species = {"yellowtail": "california yellowtail", "king salmon": "chinook salmon",
                       "mahi mahi": "dorado", "rock cod": "rockfish", "rockcod": "rockfish"}.get(species, species)
            key = (landing, vessel, species, count, anglers)
            if key in seen:
                continue
            seen.add(key)
            records.append({
                "species": species, "count": count, "anglers": anglers,
                "catch_per_angler": round(count / anglers, 3) if anglers else None,
                "region": region, "location_text": landing, "reporter": landing,
                "city": city, "state": state,
                "vessel": vessel, "source_url": url, "retrieved_at": retrieved,
                "evidence": "reported", "source_excerpt": line[:500],
            })
    return records


def fetch_landing(name: str, city: str, state: str, url: str, region: str) -> list[dict]:
    parser = TextLines()
    parser.feed(get_bytes(url).decode("utf-8", errors="replace"))
    if parser.current:
        parser.lines.append(" ".join(parser.current))
    text = "\n".join(parser.lines)
    # Redondo's page contains a long archive. Keep only the current report block.
    if name == "Redondo Beach Sportfishing":
        dated = re.search(r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},\s+\d{4}", text)
        if dated:
            text = text[:dated.start()]
    if name == "Virg's Landing":
        dates = list(re.finditer(r"\b(\d{1,2})-(\d{1,2})-(\d{4})\b", text))
        if not dates:
            return []
        month, day, year = map(int, dates[0].groups())
        report_day = datetime(year, month, day, tzinfo=timezone.utc)
        if (datetime.now(timezone.utc) - report_day).days > 14:
            return []
        end = dates[1].start() if len(dates) > 1 else len(text)
        text = text[dates[0].start():end]
    return parse_landing_text(text, name, url, region, city, state)


def fetch_all() -> tuple[list[dict], list[dict]]:
    records, health = [], []
    for name, city, state, url, region in SOURCES:
        try:
            found = fetch_landing(name, city, state, url, region)
            records.extend(found)
            health.append({"source": name, "ok": True, "detail": f"{len(found)} catch facts"})
        except Exception as exc:
            health.append({"source": name, "ok": False, "detail": str(exc)})
    return records, health
