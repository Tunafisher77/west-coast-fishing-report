from wcfr.forecast import predict_location
from wcfr.models import ConditionRecord, SourceRef

SOURCE = SourceRef("test", "https://example.test", "2026-09-03T00:00:00Z")


def test_prediction_rewards_matching_evidence():
    condition = ConditionRecord(
        "oregon", "2026-09-04T12:00:00Z", SOURCE,
        wind_knots=8, gust_knots=12, wave_height_ft=4,
        wave_period_sec=12, water_temp_f=60,
    )
    result = predict_location(
        "albacore tuna", "oregon", "off Newport",
        condition, recent_catch_score=0.8, front_detected=True, bait_reported=True,
    )
    assert result.probability_score >= 90
    assert result.confidence == "high"
    assert result.safe_to_recommend


def test_unsafe_prediction_is_never_recommended():
    condition = ConditionRecord(
        "washington", "2026-09-04T12:00:00Z", SOURCE,
        wind_knots=25, wave_height_ft=11, wave_period_sec=8, water_temp_f=60,
    )
    result = predict_location("albacore tuna", "washington", "off Westport", condition, recent_catch_score=1)
    assert not result.safe_to_recommend
    assert result.confidence == "low"
