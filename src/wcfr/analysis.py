from __future__ import annotations

from wcfr.config import SPECIES_HABITAT
from wcfr.models import ConditionRecord, Inference


def explain_presence(species: str, region: str, condition: ConditionRecord | None) -> Inference:
    key = species.casefold()
    habitat = SPECIES_HABITAT.get(key)
    if not habitat:
        return Inference(species, region, "No species-specific environmental explanation is available yet.", "low", [])

    evidence: list[str] = []
    matches: list[str] = []
    if condition and condition.water_temp_f is not None and "temp_f" in habitat:
        low, high = habitat["temp_f"]
        evidence.append(f"SST {condition.water_temp_f:.1f}°F; reference range {low}–{high}°F")
        if low <= condition.water_temp_f <= high:
            matches.append("water temperature was within the configured habitat range")

    if condition and condition.chlorophyll_mg_m3 is not None and "chlorophyll" in habitat:
        low, high = habitat["chlorophyll"]
        evidence.append(f"chlorophyll {condition.chlorophyll_mg_m3:.2f} mg/m³")
        if low <= condition.chlorophyll_mg_m3 <= high:
            matches.append("chlorophyll was within the configured productive edge range")

    features = ", ".join(habitat.get("features", []))
    if matches:
        return Inference(species, region, "; ".join(matches) + f". Relevant features: {features}.", "medium", evidence)
    return Inference(
        species, region,
        f"Reported presence may relate to {features}, but current environmental evidence is incomplete.",
        "low", evidence,
    )


def safety_gate(condition: ConditionRecord) -> tuple[bool, list[str]]:
    reasons = list(condition.marine_hazards)
    if condition.wind_knots is not None and condition.wind_knots >= 21:
        reasons.append("sustained wind at or above 21 kt")
    if condition.gust_knots is not None and condition.gust_knots >= 25:
        reasons.append("gusts at or above 25 kt")
    if condition.wave_height_ft is not None and condition.wave_height_ft >= 10:
        reasons.append("significant waves at or above 10 ft")
    if (
        condition.wave_height_ft is not None
        and condition.wave_period_sec
        and condition.wave_period_sec > 0
        and condition.wave_height_ft / condition.wave_period_sec >= 0.5
    ):
        reasons.append("steep wave-height/period relationship")
    return not reasons, reasons
