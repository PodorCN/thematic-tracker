# AGENT.md — Rates Decisions (Fed & BOC) Operator Manual

> **Target Maintainer**: Automated Data Operator (e.g., DeepSeek). Read every section carefully before editing.
> **Gate Mode**: **Blocking** via repo-wide shared review layer ([`scripts/review/REVIEWER_AGENT.md`](../scripts/review/REVIEWER_AGENT.md) + [`review/REVIEWER_AGENT.md`](./review/REVIEWER_AGENT.md)).
> This product does **NOT** follow `general-theme-tracker` (`theme.md` / proxies / VALIDITY lights). It is a single-JSON dashboard (`data/current.json`).

---

## 1. Product Mission & Reading Budget

The dashboard answers one question fast: **What will the NEXT Fed (FOMC) and Bank of Canada (BOC) meetings do — hike, hold, or cut — and why?**

The frontend enforces a strict **3-layer progressive reading budget**:
1. **30-Second Brief (Section I, always visible)**: Next/last meeting context, Market implied vs Polymarket probability bars, implied rate path, and age-decayed Driver Net Score gauge (+ divergence flag).
2. **2–3 Minute Key Drivers (Section II, always visible)**: Crisp `title` + `weight` + 1-sentence `summary` + minimal `source · published_at` line.
3. **< 10 Minute Deep Dive (collapsed inside `[Audit ▸]` / `[Method ▸]` drawers)**: `data` tuple (`actual/forecast/previous/delta_label`), multi-sentence `reason`, `market_validation`, age-decay math, `weight_breakdown`, and any long venue pricing notes.

Because `title` and `summary` are the **only narrative text visible by default**, verbose or repetitive summaries directly ruin the dashboard's readability. Follow §4 strictly.

---

## 2. File Boundaries (Hard Rules)

```text
Rates_decisions/
  data/
    current.json            <-- ONLY data file you edit in routine updates
    betting-candidate.json  <-- Written by `npm run fetch:odds` (--candidate); merge betting fields manually into current.json then remove/archive
    latest.json             <-- Written ONLY by `npm run publish` (NEVER edit by hand)
    dates.json              <-- Written ONLY by `npm run publish` (NEVER edit by hand)
    archive/<date>.json     <-- Immutable snapshots written ONLY by `npm run publish`
  index.html                <-- FROZEN SHA-256 (OFF-LIMITS)
  app.js                    <-- FROZEN SHA-256 (OFF-LIMITS)
  styles.css                <-- FROZEN SHA-256 (OFF-LIMITS)
  dev-server.js             <-- OFF-LIMITS
  scripts/                  <-- OFF-LIMITS during data updates (publish.py, freeze.py, prune_drivers.py, fetch_betting.mjs, check_review.py)
  review/
    REVIEWER_AGENT.md       <-- Annex rules for the independent reviewer
    TEMPLATE.md             <-- Command cheat-sheet
    <YYYY-MM-DD>/
      candidate.json        <-- Written by `npm run freeze`
      candidate.sha256      <-- Written by `npm run freeze`
      structural-flags.json <-- Written by `npm run freeze`
      pm-review.json        <-- Written ONLY by an INDEPENDENT reviewer (NEVER by operator)
```

### DO / DON'T Summary Table

| Rule | DO | DON'T |
|---|---|---|
| **Writable Files** | Edit **only** `Rates_decisions/data/current.json` (plus `freeze`/`publish`/`prune` outputs via npm scripts). | **NEVER** edit `index.html`, `app.js`, `styles.css`, `dev-server.js`, `scripts/*`, `data/latest.json`, `data/dates.json`, `data/archive/*`, or `scripts/econ/frontend_contract.json`. Dirty frontend/scripts causes `publish` and CI to fail closed. |
| **Polymarket Fetcher** | Run `npm run fetch:odds` (`--candidate`), which writes `data/betting-candidate.json` without touching `current.json`; reconcile timestamps & merge only `betting`. | **NEVER** pass `--write` (removed) and **NEVER** blindly overwrite `current.json` with `betting-candidate.json`. Also clean up stale `data/betting-candidate.json` before staging commits so `verify_data_only_changes.py` passes. |
| **Driver Window** | Run `npm run prune` whenever `meetings.<bank>.last_meeting.date` advances to drop old drivers with `weight <= 5`. | **NEVER** keep drivers with `published_at < last_meeting.date` and `weight <= 5` (`npm run check` blocks them; only `weight >= 6` carries across a meeting). |
| **Speech Eligibility** | Include speeches **ONLY** from key principals: Fed Chair, Vice Chair, NY Fed President (or an official FOMC dissenter), and BoC Governor / Senior Deputy Governor. | **NEVER** include routine speeches by regional Fed presidents, junior Governors, or Deputy Governors unless casting a formal dissent — ignore minor/repetitive speakers. |
| **Driver Consolidation & Cap** | Follow the selection and count guidance in §3.4, merge overlapping signals, and keep the raw and effective net scores in `[-10, +10]`. | **NEVER** create separate cards for repeated speeches by the same official (or keep an older decayed stance card after they update guidance) or duplicate macro themes causing `sum(direction * weight)` or `effective_total` to exceed `±10` (`score_overflow_overlap` flag). |
| **Role Separation** | Hand off frozen `review/<today>/` bundle to a separate reviewer identity/model. | **NEVER** write `pm-review.json` yourself, NEVER set `reviewer == operator`, and NEVER use `"self"`, `"me"`, `"ai"`, `"agent"`, `"operator"`, or `"reviewer"` as identity strings. |
| **Post-Freeze Immutability** | If any edit to `current.json` is needed after freezing, run `npm run freeze --force` and obtain a fresh review for the new SHA. | **NEVER** modify `data/current.json` after `pm-review.json` is written without re-freezing; `publish` checks canonical SHA equality across `current.json`, `candidate.json`, and `pm-review.json`. |
| **Language** | Write all fields in `data/current.json` in clean, idiomatic **English**. | **NEVER** write Chinese characters or HTML/Markdown formatting inside JSON strings. |
| **Data Honesty** | Use `"unverified"` / `"unavailable"` (with `probabilities: null` + `observable_proxy`) if live data is missing. | **NEVER** fabricate probabilities, consensus forecasts, release times, or market repricing numbers. |
| **Copy Conciseness** | Keep `title` <= 12 words, `summary` <= 22 words (1 sentence, policy takeaway only), and `pricing.source` <= 60 chars. | **NEVER** repeat headline numbers in `summary`, paste `reason` into `summary`, or dump 400-char calculation walls into `pricing.source` (put long methodology in `notes`). |
| **Primary Sources** | Link primary official domains when naming Fed/NY Fed/BLS/BEA/BoC/StatCan/CME. | **NEVER** cite an official agency in `source` while linking a blog, aggregator, or news mirror without labeling `Outlet (via Agency)`. |

---

## 3. Exact Schema & Calculation Rules (`data/current.json`)

Do not rename keys, drop required fields, or emit `NaN` / `Infinity`.

### 3.1 Top-level Fields
- `as_of`: ISO8601 timestamp with Toronto offset (e.g. `"2026-11-25T00:05:00-05:00"` EST or `"-04:00"` EDT).
- `snapshot_date`: `"YYYY-MM-DD"` in `America/Toronto`. **Must equal today's Toronto date when running `npm run publish`.**
- `version`: `1`
- `timezone`: `"America/Toronto"`
- `notes`: Concise methodology/cross-check summary.

### 3.2 `meetings.{fed|boc}`
- `label`: `"Fed (FOMC)"` / `"BOC"`
- `next_meeting`: `{ "date_label": "Dec 9 + SEP", "datetime_toronto": "...", "datetime_utc": "...Z" }`
- `last_meeting`: `{ "date": "YYYY-MM-DD", "decision": "..." }`
- `pricing`:
  - `probabilities`: `{ "hike": float, "hold": float, "cut": float }` — all values in `[0, 1]`, sum MUST be `0.99..1.01`.
  - If single-meeting implied probabilities cannot be cleanly observed, set `probabilities: null`, `probability_status: "unavailable"`, and populate `observable_proxy: { "instrument": "...", "price": "...", "tenor": "..." }`. Otherwise `probability_status: "available"` and `observable_proxy: null`.
  - `implied_rate_before` / `implied_rate_after`: numeric percentages (e.g. `3.88`, `4.12`).
  - `source`: Short venue label (`<= 60` chars, e.g. `"Kalshi Dec ladder (bid/ask mid)"`, `"CORRA OIS via BlueGamma (+21bp)"`). Put multi-sentence leg normalization notes in `notes`, NOT here.
  - `source_url`: must start with `https://`.
  - `as_of`: `"YYYY-MM-DD"` or ISO8601 timestamp. **Warning**: if `> 4` calendar days older than `as_of`, triggers `stale_pricing` structural flag.

### 3.3 `betting.{fed|boc}[]`
- Array of prediction market objects (typically 1 Polymarket entry).
- `platform`: `"Polymarket"`
- `event_slug` & `event_url`: `https://polymarket.com/event/<slug>` (must match the upcoming meeting month in `next_meeting`, not an expired contract!).
- `probabilities`: `{ "cut": float, "hold": float, "hike": float }`, sum `0.99..1.01` when `status === "available"`.
- `status`: `"available"` (or `"stale"` / `"unavailable"`).
- `volume`, `liquidity`, `as_of`, `note`.
- `npm run fetch:odds` (`node scripts/fetch_betting.mjs --candidate`) reads `event_slug` + `next_meeting` directly from `data/current.json`, validates all 5 rate legs and timestamps (`<= 90` min old), and writes `data/betting-candidate.json` atomically without touching `current.json`.

### 3.4 `drivers.{fed|boc}.{hawkish|dovish}[]`

**Selection and deduplication**

- Aim for **4–6 Fed drivers**, counted across both directions. Use fewer when evidence is sparse. Give a seventh or eighth Fed card a specific justification for review that explains the distinct decision it informs. Apply the same selection test to the BoC's **4–8** target.
- Give a signal its own card when it materially changes the next meeting's hike, hold, or cut outlook, the likely move size, the threshold for action, or which upcoming release could change the call. State the incremental implication in `summary` and support it in `reason`. Fed coverage will often include inflation, labour, demand, and the Committee's policy stance.
- **Key Principals Only (Speeches)**: Only speeches by top leadership qualify — **Fed**: Chair, Vice Chair, NY Fed President (FOMC Vice Chair), or an FOMC voting dissenter; **BOC**: Governor or Senior Deputy Governor. All other regional presidents, junior governors, and routine conference panels are excluded.
- Give Warsh or another eligible policymaker a separate card when their remarks add a meeting-specific preference, move size, decision threshold, or material shift in how the committee weighs risks. Explain what changed from the prior stance and update any prior card for that principal. Market repricing can corroborate the change. Use the normal evidence and weight rules below when repricing is flat or unverified.
- Use one card and one weight per policy signal. Combine CPI and PCE when they tell the same inflation story. Merge a policy statement and its minutes once both are available. Use the existing Audit fields for corroborating remarks, dated sources, and caveats. A refusal to prejudge a meeting provides context about uncertainty. Assign directional weight only when the remarks support a directional policy implication. When an observation has two independently material policy effects, follow the `facet` rule below.
- Before each freeze, review carried-over and new cards together. Merge overlapping evidence across both sides, remove superseded cards, and recompute the scores from the surviving set. Preserve the actual observation date for evidence you carry forward.
- Keep **raw unclamped `sum(direction * weight)`** AND **`effective_total`** strictly within **`[-10, +10]`** (if it exceeds `±10`, you have overlapping drivers — merge them; triggers `score_overflow_overlap` flag).
- **Window rule enforced by `publish.py`**: every driver MUST have `published_at >= meetings.<bank>.last_meeting.date`, UNLESS `weight >= 6` (`CARRY_OVER_MIN_WEIGHT = 6`). Lighter pre-meeting drivers fail `npm run check` (`npm run prune` strips them automatically).

Each item MUST contain:
- `id`: unique across BOTH `fed` and `boc` (e.g. `"fed-h1"`, `"boc-d1"`).
- `title`: **<= 12 words**. Outcome + primary figure.
- `summary`: **1 sentence, <= 22 words**. Policy implication ("so what") only.
- `published_at`: `"YYYY-MM-DD"`.
- `observed_at`: `"YYYY-MM-DD"` or ISO8601 (parsed by `datetime.fromisoformat()` in `publish.py` to compute age decay).
- `source` & `source_url`: must start with `https://`. Primary domain enforcement (`scripts/review/flags_rates_decisions.py`):
  - Claiming `"Statistics Canada"` → URL must contain `statcan.gc.ca`
  - Claiming `"Bank of Canada"` → URL must contain `bankofcanada.ca`
  - Claiming `"BLS"` / `"Bureau of Labor"` → URL must contain `bls.gov`
  - Claiming `"BEA"` / `"Bureau of Economic"` → URL must contain `bea.gov`
  - Claiming `"Federal Reserve"` / `"FOMC"` / `"NY Fed"` → URL must contain `federalreserve.gov` or `newyorkfed.org`
  - Claiming `"CME"` / `"FedWatch"` → URL must contain `cmegroup.com`
  - If using a secondary report, write `source: "Media (via Primary)"` (matching the actual URL domain!) and assign a lower `weight`.
- `facet`: **Mandatory & distinct** whenever the exact same `source_url` appears on BOTH `hawkish` and `dovish` sides (e.g., `"headline-energy-band-breach"` vs `"core-at-target"`), with separate transmission chains in `reason`.
- `data`: `{ "actual": "...", "forecast": "... or n/a or unverified", "previous": "...", "delta_label": "..." }` (rendered inside collapsed `[Audit ▸]`).
- `reason`: **1–3 concise sentences (`<= 60 words`)** explaining the transmission mechanism & caveats (rendered inside collapsed `[Audit ▸]`).
- `market_validation`: Exact numeric repricing quote with timestamps/venue/contracts, or `"unverified"`.
  - **Hard block**: `weight >= 7` with `null` or `"unverified"` **FAILS `npm run check`**!
  - **Structural flag**: `weight >= 5` with missing/`"unverified"` emits `high_weight_no_validation`.
- `direction`: MUST be `1` inside `hawkish[]`, and `-1` inside `dovish[]`.
- `weight`: Integer `1..10`. Note: per-bank `mean(|weight|)` MUST be `<= 5.0` or `npm run check` fails for score inflation.
- `weight_breakdown`: `{ "deviation": num, "importance": num, "surprise": num, "total": int }`.
  - `deviation + importance + surprise` MUST equal `weight`, and `total` MUST equal `weight`.

### 3.5 `total_score.{fed|boc}` (Exact Python Formulas)
`publish.py` recomputes these values and fails if mismatched:
```python
base_total = max(-10, min(10, sum(d["direction"] * d["weight"] for d in drivers)))

# Age decay uses Toronto calendar-day difference: (toronto_day(as_of) - toronto_day(observed_at)).days
decay = 1.0 if days <= 7 else 0.75 if days <= 14 else 0.5 if days <= 30 else 0.25
effective_total = round(sum(d["direction"] * d["weight"] * decay for d in drivers), 2)
# NOTE: effective_total is NOT clamped to [-10, 10] in publish.py, and tolerance is <= 0.06.
```
- `band` (validated in `publish.py` against **`base_total`**; UI displays `effective_total` band alongside `base_total` if they differ, and flags `⚠ opposes N% <leader>` when a `>=60%` market leader contradicts `effective_total`'s sign, or `mild vs N% <leader>` when `>=70%` and `0 < |eff| <= 2`):
  - `>= 7` → `"strong hike lean"`
  - `> 3` → `"lean hike"`
  - `-3 .. +3` → `"hold"`
  - `< -3` (down to `-7` in `publish.py`) → `"lean cut"`
  - `< -7` → `"strong cut lean"`

### 3.6 `calendar[]`
- `date_toronto`: `"YYYY-MM-DD"` (required).
- `date_only`: boolean.
  - If `true`: `datetime_toronto` and `datetime_utc` MUST both be `null`.
  - If `false`: both `datetime_toronto` and `datetime_utc` MUST be valid ISO8601 strings.
- `currency`: `"USD"` or `"CAD"`.
- `event`: concise event name (UI highlights meetings and splits pre-meeting `HIGH` from `MEDIUM`/post-meeting).
- `impact`: `"HIGH"` or `"MEDIUM"`.
- `importance`: integer `1..3`.
- `forecast` / `previous`: string, or `"unverified"`.
- `source` & `source_url`: `https://` URL to specific release/schedule page (do NOT reuse generic `/economic-calendar/` URLs across `>= 5` rows).

---

## 4. Writing Quality Rules (BAD vs GOOD)

Because the UI shows only `title` + `summary` by default and folds `data` + `reason` into `[Audit ▸]`, follow this separation strictly:

- **BAD (redundant bloat — DO NOT write this)**:
  - `title`: `"October CPI +0.4% m/m, core +0.3% a third straight month, above consensus"`
  - `summary`: `"Headline CPI +0.4% m/m after +0.6% in September and core +0.3% for the third consecutive month... Both headline and core came in 0.1pp above Dow Jones consensus (0.3% / 0.2%)..."` *(65 words, duplicates `title` & `data.actual`/`forecast`.)*
- **GOOD (high-signal, 2-min scan)**:
  - `title`: `"Oct CPI +0.4% m/m, core +0.3% (+0.1pp beat)"`
  - `summary`: `"Third straight 0.3% monthly core gain reinforces Fed tightening pressure despite lower headline pace."` *(14 words, zero duplicate numbers, clear policy implication.)*
  - `data`: `{ "actual": "+0.4% m/m, core +0.3% m/m", "forecast": "+0.3% / +0.2% (Dow Jones)", "previous": "+0.6% / +0.3% Sep", "delta_label": "+0.1pp beat" }`
  - `reason`: `"Sequential core persistence keeps 2% return stalled; shelter (+0.3%) and energy (+0.7%) drove the gain."`

---

## 5. Step-by-Step Maintenance SOP

Run all commands inside `Rates_decisions/` unless noted:

```bash
# 1. If last_meeting.date changed, prune stale drivers (published_at < last_meeting.date & weight <= 5)
npm run prune

# 2. (Optional) Fetch validated Polymarket odds into data/betting-candidate.json
#    Verify current.json event_slug matches the NEXT meeting first!
npm run fetch:odds
# Manually merge betting.{fed,boc} into data/current.json after checking timestamps, then delete data/betting-candidate.json.

# 3. Edit ONLY data/current.json
#    - Set snapshot_date = today Toronto (YYYY-MM-DD) & as_of
#    - Update meetings.{fed,boc}.pricing (keep source <= 60 chars) & betting
#    - Apply the selection and deduplication rules in §3.4 to all drivers, then edit for §4
#    - Recompute total_score.{fed,boc} using exact §3.5 Python rules
#    - Update upcoming calendar[]

# 4. Structural & math validation (blocks on errors, warns on structural flags)
npm run check

# 5. Freeze candidate (writes review/<today>/{candidate.json, candidate.sha256, structural-flags.json})
npm run freeze

# 6. Stop here as Operator -> Hand off to Independent Reviewer
#    Reviewer reads review/<today>/candidate.json + structural-flags.json
#    and writes review/<today>/pm-review.json per review/REVIEWER_AGENT.md:
#    6 checks: official_policy, pricing, drivers, market_validation, freshness, decision_usefulness
#    Under drivers, verify next-meeting relevance, distinct signals, and any Fed cards beyond six (§3.4).
#    Every structural flag must be dispositioned. Verdict must be APPROVED.

# 7. Validate review bundle
npm run review:check

# 8. Publish snapshot (writes data/archive/<today>.json, data/latest.json, data/dates.json)
npm run publish

# 9. Verify data-only scope before git commit (run from repo root)
cd ..
python3 scripts/econ/verify_data_only_changes.py --product Rates_decisions --staged
```

### Failure Recovery
- **`npm run check` fails on old driver**: Run `npm run prune` (or promote driver `weight >= 6` if genuinely cycle-defining and backed by validation).
- **`npm run check` fails on math/schema**: Fix the reported field/math mismatch in `data/current.json` and re-run `npm run check`.
- **`npm run review:check` or `pm-review.json` returns `REVISE`**: Fix `data/current.json`, run `npm run check`, then run `npm run freeze --force` (voids old review and generates new SHA-256) and request a new review on the new SHA.
- **`npm run publish` says dirty frontend/scripts**: Run `git status`. Restore any accidental edits outside `Rates_decisions/data/` and `Rates_decisions/review/<today>/`.
- **`stale_pricing` / `high_weight_no_validation` / `primary_source_mismatch` flags**: Fix the underlying URL, date, or weight in `current.json` before freezing so `structural-flags.json` stays clean.
