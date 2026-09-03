# Forecast methodology

The report has two separate forecasts:

1. **Boatability and safety** — official warnings, wind, gusts, wave height, period, direction, crossing seas, and bar conditions.
2. **Fish-location probability** — where suitable habitat is most likely to overlap recent verified catch activity.

A fish-location forecast is a region or oceanographic zone, not a fabricated catch coordinate.

## Evidence hierarchy

1. Source-attributed recent catch with a usable date and location/zone.
2. Observed SST, chlorophyll, currents, buoy conditions, and reported bait.
3. Forecast movement of water masses and marine conditions.
4. Species habitat ranges and seasonal behavior.
5. Tide and lunar context as secondary features.

Each prediction reports:

- species;
- region and likely zone;
- probability score and confidence;
- likely habitat feature;
- evidence supporting the prediction;
- conditions that would invalidate it;
- whether it passes the safety screen.

## Initial score

- Baseline: 20
- Recent comparable catch: 0–30
- SST inside configured range: +20; outside: -15
- Detectable SST/chlorophyll front: +15
- Source-attributed bait activity: +15

Scores are provisional and will not be described as calibrated probabilities. After sufficient history accumulates, weights will be evaluated separately by species, season, and region using out-of-sample results.

## Guardrails

- A safety failure suppresses the recommendation regardless of fish score.
- Exact coordinates require authorized evidence or a reproducible oceanographic feature.
- Landing totals alone cannot establish the catch location.
- “Why there” is always labelled as inference unless the reporting captain/source explicitly stated it.
- Missing or stale SST, catch, or forecast data lowers confidence.
