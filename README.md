# West Coast Fishing Report

Automated daily fishing-intelligence report for the marine coasts of California, Oregon, and Washington.

## Goals

- Report **all marine species** with credible current activity.
- Highlight tuna, California yellowtail, white seabass, salmon, marlin, and swordfish.
- Capture what was caught, where, who reported/caught it, trip context, and catch per angler when possible.
- Explain likely environmental drivers using contemporaneous SST, chlorophyll, wind, waves, tides, currents, and lunar context.
- Keep reported facts separate from model inference.
- Rank the next seven days by region only after a marine-safety screen.
- Preserve daily raw observations for later backtesting and species-specific models.

## Data policy

Only free public sources whose terms permit automated access are used. SportfishingReport.com data is excluded unless written authorization or a licensed API is obtained. The pipeline never invents exact catch locations from landing totals.

## Status

Initial foundation under construction. GitHub Actions will build and archive reports; delivery configuration will be added after the data and report output pass validation.
