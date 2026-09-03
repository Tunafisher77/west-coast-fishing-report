from wcfr.analysis import explain_presence, safety_gate
from wcfr.models import ConditionRecord, SourceRef


SOURCE = SourceRef("test", "https://example.test", "2026-09-03T00:00:00Z")


def test_safety_gate_blocks_high_wind():
    condition = ConditionRecord("oregon", "2026-09-03T12:00:00Z", SOURCE, wind_knots=24)
    safe, reasons = safety_gate(condition)
    assert not safe
    assert "sustained wind" in reasons[0]


def test_safety_gate_allows_mild_complete_conditions():
    condition = ConditionRecord(
        "oregon", "2026-09-03T12:00:00Z", SOURCE,
        wind_knots=8, gust_knots=12, wave_height_ft=4, wave_period_sec=12,
    )
    assert safety_gate(condition) == (True, [])


def test_albacore_explanation_uses_sst_evidence():
    condition = ConditionRecord(
        "oregon", "2026-09-03T12:00:00Z", SOURCE,
        water_temp_f=60, chlorophyll_mg_m3=0.25,
    )
    result = explain_presence("albacore tuna", "oregon", condition)
    assert result.confidence == "medium"
    assert len(result.evidence) == 2
