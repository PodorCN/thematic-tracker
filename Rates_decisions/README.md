# Rates_decisions — Next Fed & BOC Rate Decision Dashboard

A static, JSON-driven dashboard that answers in under 2 minutes: what will the **next** Fed and BOC meetings do — hike, hold, or cut?

## Run

```bash
npm run dev          # serves at http://127.0.0.1:7100 (fetch() needs HTTP, not file://)
```

GitHub Pages compatible: push the folder and it works as-is.

## Workflow

1. **Edit** `data/current.json` only. Never edit `index.html` to change content.
2. **Validate:** `npm run check` (schema, probability sums, weight rules, total recomputation).
3. **Review:** copy `review/TEMPLATE.md` → `review/<today>.md`, fill it, end with `Verdict: APPROVED`.
4. **Publish:** `npm run publish` — copies `current.json` to `data/archive/<today Toronto>.json` + `data/latest.json`, updates `dates.json`. Refuses to publish without an APPROVED review for today. Older archives are immutable; same-day re-runs overwrite only today's file.

## Reading rules

- **L text** (24–32px): title, total score, verdict — the 2-minute layer.
- **M text** (16–18px): probabilities, driver title + summary + weight, calendar rows.
- **S text** (12–13px gray): reasons, breakdowns, links — audit only, skip it.
- Score gauge: −10 guaranteed cut … 0 balanced … +10 guaranteed hike. Effective weights are age-decayed (≤7d ×1.0, 8–14d ×0.75, 15–30d ×0.5, >30d ×0.25); base weights kept for audit.
- ⚠ divergence badge = driver total disagrees with market pricing leader — investigate, don't average.
- `unverified` / `unavailable` are valid values. Never invent a probability or a release time.
