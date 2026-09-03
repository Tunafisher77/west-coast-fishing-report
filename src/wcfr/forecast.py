from __future__ import annotations

from dataclasses import dataclass

from wcfr.analysis import safety_gate
from wcfr.config import SPECIES_HABITAT
from wcfr.models import ConditionRecord


@dataclass
class FishLocationPrediction:
    species: str
    region: str
    zone: str
    probability_score: int
    confidence: str
    likely_feature: str
    reasons: list[str]
    invalidators: list[str]
    safe_to_recommend: bool


def predict_location(
    species: str,
    region: str,
    zone: str,
    condition: ConditionRecord,
    recent_catch_score: float | None = None,
    front_detected: bool = False,
    bait_reported: bool = False,
) -> FishLocationPrediction:
    """Create an evidence-labelled habitat forecast, never an invented catch point."""
    safe, safety_reasons = safety_gate(condition)
    habitat = SPECIES_HABITAT.get(species.casefold(), {})
    score = 20
    reasons: list[str] = []
    invalidators: list[str] = []

    if recent_catch_score is not None:
        catch_component = max(0, min(30, round(recent_catch_score * 30)))
        score += catch_component
        reasons.append(f"recent comparable catch signal contributed {catch_component}/30")

    temp_range = habitat.get("temp_f")
    if condition.water_temp_f is not None and temp_range:
        low, high = temp_range
        if low <= condition.water_temp_f <= high:
            score += 20
            reasons.append(f"SST {condition.water_temp_f:.1f}°F is within the {low}–{high}°F habitat band")
        else:
            score -= 15
            invalidators.append(f"SST remains outside {low}–{high}°F")
    else:
        invalidators.append("no current SST match is available")

    if front_detected:
        score += 15
        reasons.append("a current SST/chlorophyll front is detected")
    else:
        invalidators.append("the expected front dissipates or shifts")

    if bait_reported:
        score += 15
        reasons.append("recent source-attributed bait activity is present")
    else:
        invalidators.append("no bait concentration is confirmed")

    score = max(0, min(100, score))
    if not safe:
        reasons.extend(f"safety block: {reason}" for reason in safety_reasons)
    confidence = "high" if score >= 75 and safe else "medium" if score >= 50 and safe else "low"
    feature = ", ".join(habitat.get("features", ["structure or forage concentration"]))
    return FishLocationPrediction(
        species=species,
        region=region,
        zone=zone,
        probability_score=score,
        confidence=confidence,
        likely_feature=feature,
        reasons=reasons,
        invalidators=invalidators,
        safe_to_recommend=safe,
    )
