# Rates_decisions — Next Fed & BOC Rate Decision Dashboard

A static, JSON-driven dashboard that answers in under 2 minutes: what will the **next** Fed and BOC meetings do — hike, hold, or cut?

## Run

```bash
npm run dev          # serves at http://127.0.0.1:7100 (fetch() needs HTTP, not file://)
```

GitHub Pages compatible: push the folder and it works as-is.

## Workflow

1. **Edit** `data/current.json` only (set `snapshot_date` = today Toronto). Never edit `index.html` to change content.
2. **Validate:** `npm run check` (structure errors block; structural flags warn and must be dispositioned by reviewer).
3. **Freeze:** `npm run freeze` → `review/<today>/{candidate.json, candidate.sha256, structural-flags.json}`. Candidate is immutable after this.
4. **Review (independent, different person/model from operator):** write `review/<today>/pm-review.json` per `review/REVIEWER_AGENT.md` (SHA-bound, 6 checks, findings with evidence, every structural flag dispositioned). See `review/TEMPLATE.md`.
5. **Publish:** `npm run publish` — publishes the reviewed bytes verbatim to `data/archive/<today Toronto>.json` + `data/latest.json`, updates `dates.json`. Fails closed on: structure errors, SHA mismatch (any post-freeze edit voids review), self-review, uncovered flags, critical/major with APPROVED, or dirty frontend/scripts. Older archives are immutable.

## Reading rules

- **L text** (24–32px): title, total score, verdict — the 2-minute layer.
- **M text** (16–18px): probabilities, driver title + summary + weight, calendar rows.
- **S text** (12–13px gray): reasons, breakdowns, links — audit only, skip it.
- Score gauge: −10 guaranteed cut … 0 balanced … +10 guaranteed hike. Effective weights are age-decayed (≤7d ×1.0, 8–14d ×0.75, 15–30d ×0.5, >30d ×0.25); base weights kept for audit.
- ⚠ divergence badge = driver total disagrees with market pricing leader — investigate, don't average.
- `unverified` / `unavailable` are valid values. Never invent a probability or a release time.
