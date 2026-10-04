# Public Macro Pages: Backend and Daily Archive Contract

This document is the canonical backend contract for these public pages:

| Page | Public HTML | Latest data |
|---|---|---|
| Global Economic Calendar | `economic-calendar/index.html` | `economic-calendar/data/latest.json` |
| Rates Decisions | `Rates_decisions/index.html` | `Rates_decisions/data/latest.json` |

The economic calendar frontend (`economic-calendar/index.html`) is a versioned static page with digest recorded in `scripts/econ/frontend_contract.json`. Daily jobs publish only the content assets they fetch; changing a frontend requires a separate, reviewed code PR and an updated SHA in `scripts/econ/frontend_contract.json`. Macro and rate decision pages publish dated JSON and a date manifest, never regenerated HTML. All public times are rendered in `America/Toronto`.

## 1. Required Publication Layout

```text
economic-calendar/index.html                 # static renderer
economic-calendar/raw/YYYY-MM-DD/economic_calendar.json
economic-calendar/data/{latest,dates}.json
economic-calendar/data/archive/YYYY-MM-DD.json

Rates_decisions/index.html                   # static renderer
Rates_decisions/data/current.json            # edit source
Rates_decisions/data/{latest,dates}.json
Rates_decisions/data/archive/YYYY-MM-DD.json
Rates_decisions/review/<today>.md            # approved review
```

Rules:
1. `archive/YYYY-MM-DD.json` is immutable after a successful publication, except to repair invalid data.
2. `latest.json` is an atomic copy of the newest successful archive.
3. `dates.json` lists only snapshots that exist and passed validation.
4. A failed collection must not replace `latest.json`. Continue serving the last successful snapshot.

## 2. Daily Publication Sequence (Economic Calendar)

1. Resolve the publication date in `America/Toronto`.
2. Fetch calendar data via `scripts/econ/fetch_calendar.py`.
3. Validate and publish via `scripts/econ/render_calendar.py`.
4. Run `python scripts/econ/verify_data_only_changes.py --product economic-calendar --staged`.

## 3. Rates Decisions Publication Sequence

1. Update `Rates_decisions/data/current.json`.
2. Validate via `npm --prefix Rates_decisions run check`.
3. Fill `Rates_decisions/review/<today>.md` with `Verdict: APPROVED`.
4. Publish via `npm --prefix Rates_decisions run publish`.
