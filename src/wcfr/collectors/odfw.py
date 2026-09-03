from __future__ import annotations

import re
from datetime import datetime, timezone
from html.parser import HTMLParser

from wcfr.http import get_bytes

URL = "https://myodfw.com/recreation-report/fishing-report/marine-zone"


class _Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        value = " ".join(data.split())
        if value:
            self.parts.append(value)


def fetch_report_text() -> str:
    parser = _Text()
    parser.feed(get_bytes(URL).decode("utf-8", errors="replace"))
    return "\n".join(parser.parts)


def parse_port_catch_rates(text: str) -> list[dict]:
    records: list[dict] = []
    species_blocks = {
        "albacore tuna": r"(?:Albacore)(.*?)(?:Bottomfish)",
        "rockfish": r"(?:Bottomfish)(.*?)(?:Ocean salmon|Pacific halibut)",
        "pacific halibut": r"(?:Pacific halibut)(.*?)(?:Shore and estuary|$)",
    }
    ports = "Garibaldi|Pacific City|Depoe Bay|Newport|Winchester Bay|Charleston|Brookings"
    retrieved = datetime.now(timezone.utc).isoformat()
    for species, pattern in species_blocks.items():
        match = re.search(pattern, text, re.I | re.S)
        if not match:
            continue
        block = match.group(1)
        rate_pattern = rf"({ports})\s*:?\s*(?:.*?)(\d+(?:\.\d+)?)\s+(?:{re.escape(species.split()[0])}\s+)?(?:fish\s+)?per angler"
        for found in re.finditer(rate_pattern, block, re.I):
            records.append({
                "species": species,
                "region": "oregon",
                "location_text": found.group(1),
                "city": found.group(1), "state": "OR",
                "catch_per_angler": float(found.group(2)),
                "reporter": "Oregon Department of Fish and Wildlife",
                "source_url": URL,
                "retrieved_at": retrieved,
                "evidence": "reported",
            })
    return records
