from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Literal

EvidenceKind = Literal["reported", "observed", "forecast", "inferred"]


@dataclass(frozen=True)
class SourceRef:
    name: str
    url: str
    retrieved_at: str
    published_at: str | None = None


@dataclass
class CatchRecord:
    species: str
    count: float | None
    anglers: int | None
    region: str
    location_text: str | None
    reporter: str | None
    vessel: str | None
    landing: str | None
    trip_type: str | None
    catch_date: str
    source: SourceRef
    evidence: EvidenceKind = "reported"
    notes: list[str] = field(default_factory=list)

    @property
    def catch_per_angler(self) -> float | None:
        if self.count is None or not self.anglers:
            return None
        return self.count / self.anglers

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["catch_per_angler"] = self.catch_per_angler
        return value


@dataclass
class ConditionRecord:
    region: str
    valid_at: str
    source: SourceRef
    wind_knots: float | None = None
    gust_knots: float | None = None
    wave_height_ft: float | None = None
    wave_period_sec: float | None = None
    swell_direction: str | None = None
    water_temp_f: float | None = None
    chlorophyll_mg_m3: float | None = None
    marine_hazards: list[str] = field(default_factory=list)


@dataclass
class Inference:
    species: str
    region: str
    explanation: str
    confidence: Literal["low", "medium", "high"]
    evidence: list[str]


@dataclass
class SourceHealth:
    source: str
    ok: bool
    checked_at: str
    detail: str
