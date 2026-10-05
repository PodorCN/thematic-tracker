# AGENT.md — General Theme Tracker (PM-facing theme site) Product Instructions

> This product uses the repo-wide shared gate (`scripts/review/`: frozen bytes, SHA binding, verdict coherence),
> **blocking**: no publish without an APPROVED `pm-review.json`.
> Shared doctrine: [`scripts/review/REVIEWER_AGENT.md`](../scripts/review/REVIEWER_AGENT.md).
> This file keeps only Theme-specific structure checks, scoring rules, and source rules.

## 1. Role & Scope

A theme-first site: what are the most important market themes right now? How are they performing? What tracks them?
Why did they form? What catalyst do they depend on? What changed yesterday vs today? Theme or noise?
Read a theme in 5 minutes (body < ~500 English words, explainer folded).

## 2. File Layout & Contracts

```text
general-theme-tracker/
  backend/server.js            read-only API (Node, no framework; never touched in routine work)
  backend/validate.js          YAML schema checks (npm run validate; CI)
  index.html                   static renderer for GitHub Pages (frozen; reads ./data/latest.json)
  data/
    themes/<YYYY-Www>/theme_*.yaml   the agent's only writable area (3–7 themes a week)
    market/snapshot_<YYYY-Www>.yaml  Regime + Benchmark strip
    commentary/<YYYY-Www>.yaml       Weekly Commentary source library
    archive/<YYYY-MM-DD>.json        published frozen snapshots (written by publish, never by hand)
    latest.json                      latest published bundle (static renderer reads this; written by publish)
    schema/theme.schema.yaml         schema_v1 (a development change, never rides a data PR)
  review/
    REVIEWER_AGENT.md       product review annex (six checks + Theme scoring/source rules)
    TEMPLATE.md             product command cheat-sheet
    <YYYY-MM-DD>/           frozen bundle of the day (all four required, else publish refuses):
      candidate.json          weekly bundle JSON (built by build_candidate.mjs, then frozen)
      candidate.sha256        SHA-256 of the candidate bytes
      structural-flags.json   machine flags (reviewer must disposition every one)
      pm-review.json          independent review verdict (SHA-bound, all six checks pass for APPROVED)
      review.md               human-readable version (optional, must match the json verdict)
  scripts/
    build_candidate.mjs     weekly YAML bundle -> candidate JSON (single entry point)
    freeze.py               freeze wrapper (shared freeze + this product's flags plugin)
    publish.py              structure checks + reviewer gate + archiving (shared layer)
    check_review.py         review pre-check wrapper
```

## 3. Maintenance SOP (blocking)

```bash
# 1. Edit data: only data/themes/<week>/*.yaml + market/snapshot_<week>.yaml + commentary/<week>.yaml
#    snapshot_date is injected automatically by freeze as the Toronto date of the day
#    (never hand-write snapshot_date inside YAML).

# 2. Machine data checks (structure errors block; structural flags warn and need reviewer disposition)
npm run validate                       # YAML schema_v1 (backend/validate.js)
python3 scripts/publish.py --check     # whole-week bundle structure + flag preview

# 3. Freeze the candidate (any later edit to data/ voids the review)
npm run freeze
# -> review/<today>/candidate.json + candidate.sha256 + structural-flags.json

# 4. Independent PM review (reviewer must be a different person/model from operator; self-review banned)
#    The reviewer writes review/<today>/pm-review.json against structural-flags.json:
#    candidate_sha256 binding, six checks, findings (critical/major block), full flags_dispositioned coverage
npm run review:check

# 5. Publish & archive (publish re-verifies: rebuilt bundle bytes == frozen bytes + review verdict + full flag coverage + clean frontend)
npm run publish
# Mechanics:
#   - canonical(rebuilt week bundle) sha == candidate.json sha == pm-review.json candidate_sha256
#   - verdict must be APPROVED with zero critical/major findings and all six checks passing
#   - every structural flag of the current bundle must appear in flags_dispositioned
#   - dirty frontend/src, backend, scripts, or index.html in the worktree refuses publish (frontend ships in a separate PR)
#   - published bytes == reviewed candidate bytes -> data/archive/<today>.json + data/latest.json
```

## 4. Core Rules & Red Lines (Theme-specific, enforced by machine + reviewer)

- **Never touch the frontend**: `frontend/src`, `backend/`, `scripts/`, `index.html` are off-limits in routine updates.
  Publish checks the git worktree and refuses on dirt.
- **Six checks (passed to the validator as `--checks`; all must pass for APPROVED)**:
  `excess_math` `timing_source` `freshness` `readability` `theme_noise` `proxy_tradability`.
- **excess_math**: `excess = proxy - benchmark`, mismatch > 0.2pp sent back; no intraday prices passed off as closes;
  Total Return / Price Return mixing must be labeled.
- **timing_source**: every event needs `event_time_UTC + source + https url`;
  no time or no source = unpublishable; performance needs `as_of_UTC + source + benchmark_rationale`.
- **freshness**: `as_of_UTC` more than 7d older than snapshot_date is a hard machine error in publish;
  reviewers hold the PRD 48h ideal (anything older earns a major at minimum).
- **readability**: bodies over ~500 English words are blocked (>5min); unexplained jargon sent back.
- **theme_noise**: `score == count of true flags`, `score >= 3` for a Theme;
  `score < 3` filed as New/Continuing on Home is blocked (demote to Noise/Draft; Fading/Dead excepted).
- **proxy_tradability**: 1–3 proxies per theme; ETFs must state fees;
  `liquidity_note + why_represents + tracking_gap` required; illiquid proxies sent back.
- **English-only**: every string in data, UI, prompts, and docs is English. Non-English text in a data file is a
  publish-blocking structure error; non-English UI/docs get sent back in review.
- **Frozen means frozen**: `review/<date>/candidate.json` bytes are immutable after freezing;
  touching `data/` afterwards means re-freeze (old review auto-voided).
- **Role separation**: operator and reviewer must be different names (`self/me` banned); reviewer never edits the candidate;
  an approval binds exactly one sha.
- **No APPROVED, no publish**: publish requires the complete four-file frozen bundle + matching sha on all three sides +
  zero critical/major + all six checks passing + full structural-flag coverage.
