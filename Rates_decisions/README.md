# Rates_decisions — Next Fed & BOC Rate Decision Dashboard

A static, JSON-driven dashboard structured for **30s / 2–3m / <10m** reading: what will the **next** Fed and BOC meetings do — hike, hold, or cut?

## Run

```bash
npm run dev          # serves at http://127.0.0.1:7100 (fetch() needs HTTP, not file://)
```

GitHub Pages compatible: push the folder and it works as-is.

## Workflow

1. **Prune & Fetch (optional):** after a policy decision rolls `last_meeting.date`, run `npm run prune` to drop pre-meeting drivers with `weight <= 5`. Run `npm run fetch:odds` (`--candidate`) to write live Polymarket odds into `data/betting-candidate.json` (merge only `betting` into `current.json`).
2. **Edit** `data/current.json` only (set `snapshot_date` = today Toronto). Never edit `index.html`, `app.js`, or `styles.css` in data updates.
3. **Validate:** `npm run check` (structure errors block; structural flags warn and must be dispositioned by reviewer).
4. **Freeze:** `npm run freeze` → `review/<today>/{candidate.json, candidate.sha256, structural-flags.json}`. Candidate is immutable after this.
5. **Review (independent, different person/model from operator):** write `review/<today>/pm-review.json` per `review/REVIEWER_AGENT.md` (SHA-bound, 6 checks, findings with evidence, every structural flag dispositioned). See `review/TEMPLATE.md`.
6. **Publish:** `npm run publish` — publishes the reviewed bytes verbatim to `data/archive/<today Toronto>.json` + `data/latest.json`, updates `dates.json`. Fails closed on: structure errors, SHA mismatch (any post-freeze edit voids review), self-review, uncovered flags, critical/major with APPROVED, or dirty frontend/scripts. Older archives are immutable.

## Reading & Layout Rules

- **Section I — 30-Second Brief**: Side-by-side Fed & BOC cards combining next/last meeting info, Market vs Polymarket probability bars, implied rate path, and age-decayed Driver Net Score gauge (+ divergence flag). Long venue methodology strings fold inside `Method ▸`.
- **Section II — Key Drivers (2–3 min scan)**: Default view shows only `title`, weight badge, 1-sentence `summary`, and `source · date`, sorted by effective weight. Detailed `data`, `reason`, `market_validation`, and `weight_breakdown` stay collapsed inside each card's `Audit ▸` drawer (with a global `Expand all audit` toggle for <10m deep dives).
- **Section III — Upcoming Catalysts**: Pre-meeting `HIGH`-impact releases with direct source links; `MEDIUM`-impact and post-meeting releases fold behind a toggle.
- Score gauge: −10 guaranteed cut … 0 balanced … +10 guaranteed hike. Effective weights are age-decayed (≤7d ×1.0, 8–14d ×0.75, 15–30d ×0.5, >30d ×0.25); base weights kept for audit.
- ⚠ divergence badge = driver total disagrees with market pricing leader — investigate, don't average.
- `unverified` / `unavailable` are valid values. Never invent a probability or a release time.
