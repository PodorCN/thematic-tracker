# Reviewer Report — <YYYY-MM-DD>

**Snapshot reviewed:** `data/current.json` → `data/archive/<YYYY-MM-DD>.json`
**Reviewer:** <name/model>

## 1. Data accuracy (mismatch = CRITICAL)
Re-fetch every `source_url`; confirm actual / forecast / previous / probabilities match.

| Field | Claimed | Source says | Status |
|---|---|---|---|
| | | | |

## 2. Consistency
- [ ] Title / summary / side sign agree for every driver
- [ ] Total math: `base_total == clamp(Σ direction×weight)`, band label correct
- [ ] Score direction vs market pricing leader badge correct (✓ / ⚠)
- [ ] Calendar: past events removed, no invented times (date_only events have null datetimes)

## 3. Scoring audit
- [ ] Every weight 1–10 justified by `weight_breakdown` (deviation + importance + surprise)
- [ ] Any weight ≥ 7 has 2+ independent sources + market validation (else CRITICAL)
- [ ] Mean |weight| within 2–4 (flag if > 5)
- [ ] No double-counting (same release ≠ two drivers on the same facet)
- [ ] No 9–10 without unanimous reviewer + >25bp repricing

## Findings

| # | Severity | Field | Evidence | Suggested fix |
|---|---|---|---|---|
| | critical/major/minor | | | |

## Verdict: APPROVED | REVISE

<one-line justification>
