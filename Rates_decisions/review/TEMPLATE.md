# Review flow — TEMPLATE (new SHA-bound gate)

> Legacy `review/<YYYY-MM-DD>.md` (free-text + `Verdict: APPROVED` string match) is
> **retired**: it had no SHA binding and allowed self-review. `publish.mjs` rejects it.
> Old files under `review/*.md` are kept for history only.

## Roles

| Role | Who | Does |
|---|---|---|
| Operator | <operator name> | edits `data/current.json`, runs `freeze.mjs`, never approves own work |
| Reviewer | <reviewer name, DIFFERENT from operator> | writes `pm-review.json` per `REVIEWER_AGENT.md`, never edits candidate |

## SOP

```bash
# 1. operator edits data only
#    snapshot_date MUST equal today (Toronto). Only touch data/current.json.

# 2. freeze (candidate becomes immutable, flags generated)
node scripts/freeze.mjs
# -> review/<today>/candidate.json
# -> review/<today>/candidate.sha256
# -> review/<today>/structural-flags.json   # every flag MUST be dispositioned

# 3. reviewer (independent!) writes the verdict — machine-checked JSON
cp review/pm-review.schema.json /tmp/  # reference only; write real file below
# review/<today>/pm-review.json must contain:
# {
#   "schema_version": "1.0",
#   "reviewer": "<real name/model, != operator>",
#   "operator": "<who froze>",
#   "reviewed_at": "2026-10-04T12:00:00-04:00",
#   "snapshot_date": "<today>",
#   "candidate_sha256": "<copy from candidate.sha256>",
#   "verdict": "APPROVED | REVISE",
#   "executive_summary": ">=20 chars: what you checked, what binds to this sha",
#   "checks": {"official_policy":"pass","pricing":"pass","drivers":"pass",
#              "market_validation":"pass","freshness":"pass","decision_usefulness":"pass"},
#   "findings": [
#     {"severity":"major","field":"drivers.boc.dovish[0].source_url",
#      "issue":"claims StatCan but links nesto.ca",
#      "evidence":"candidate boc-d1 source_url=https://www.nesto.ca/... vs StatCan Daily https://www150.statcan.gc.ca/...",
#      "disposition":"must_fix"}
#   ],
#   "flags_dispositioned": [
#     {"code":"primary_source_mismatch","field":"drivers.boc.dovish[0].source_url",
#      "disposition":"must_fix: swap to StatCan Daily link or restate source"}
#   ]
# }

# 4. validate before publish (optional but recommended)
node scripts/validate_pm_review.mjs \
  --candidate review/<today>/candidate.json \
  --review review/<today>/pm-review.json \
  --flags review/<today>/structural-flags.json \
  --require-approved

# 5. publish (fails closed on: structure errors, sha mismatch, self-review,
#    uncovered flags, critical/major findings with APPROVED, frontend dirtied)
npm run publish

# 6. browser验收
npm run dev  # http://127.0.0.1:7100 — confirm bars/score/calendar render, no NaN
```

## Rules

- `APPROVED` requires: zero `critical`/`major` findings, all 6 checks `pass`,
  every structural flag dispositioned, `candidate_sha256` matches frozen bytes.
- `REVISE` requires at least one `critical`/`major` finding or one failed check.
- Findings about UI taste / overlay style / column layout are OUT OF SCOPE —
  file a separate frontend PR instead.
- Any edit to `data/current.json` after freeze voids the review: re-freeze (`--force`) + re-review.
