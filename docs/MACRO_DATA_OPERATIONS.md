# Macro Pages Data Operations

This runbook covers the public macro and rate decision pages in this repository:

| Page | Staging or raw input | Published data | Dedicated instructions |
|---|---|---|---|
| Global Economic Calendar | `economic-calendar/raw/<date>/economic_calendar.json` | `economic-calendar/data/` | [`economic-calendar/AGENT.md`](../economic-calendar/AGENT.md) |
| Rates Decisions | `Rates_decisions/data/current.json` | `Rates_decisions/data/` | [`Rates_decisions/AGENT.md`](../Rates_decisions/AGENT.md) |

The canonical publication contracts and schemas:
- Global Economic Calendar: [`docs/ECON_CALENDAR_API_SPEC.md`](ECON_CALENDAR_API_SPEC.md)
- Rates Decisions: [`Rates_decisions/AGENT.md`](../Rates_decisions/AGENT.md)

---

## 1. Global Economic Calendar (`economic-calendar/`)

### Current Automation Boundary
- `scripts/econ/fetch_calendar.py` collects the Economic Calendar from FxStreet, with ForexFactory as fallback.
- `scripts/econ/render_calendar.py` validates fetched JSON and publishes only `economic-calendar/data/archive/<date>.json`, `data/latest.json`, and `data/dates.json`. The fixed `index.html` reads these in the browser; the job must not generate dated HTML.
- `.github/workflows/macro-pages-daily.yml` runs daily at `13:10 UTC` and publishes the deterministic economic calendar.

### Verification
```bash
python scripts/econ/verify_data_only_changes.py --product economic-calendar --staged
python -m pytest tests/test_econ_render.py -q
```

---

## 2. Rates Decisions Dashboard (`Rates_decisions/`)

A static, JSON-driven dashboard that answers in under 2 minutes: what will the next Fed and BOC meetings do — hike, hold, or cut?

### Workflow
1. Edit `Rates_decisions/data/current.json` only.
2. Validate: `npm --prefix Rates_decisions run check` (schema, probability sums, weight rules, total recomputation).
3. Review: copy `Rates_decisions/review/TEMPLATE.md` → `Rates_decisions/review/<today>.md`, fill audit items, end with `Verdict: APPROVED`.
4. Publish: `npm --prefix Rates_decisions run publish` (archives to `data/archive/<today>.json` + `data/latest.json`, updates `dates.json`).
