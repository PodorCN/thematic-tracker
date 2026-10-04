# Review flow — shared TEMPLATE (SHA-bound gate)

> Free-text approvals ("Verdict: APPROVED" string match, self-review) are
> retired everywhere. The publisher only accepts a `pm-review.json` that the
> shared validator approves. Product command blocks live in each product's
> `AGENT.md`; the shape below is identical for all trackers.

## Roles

| Role | Who | Does |
|---|---|---|
| Operator | `<operator name>` | edits the product input file, runs freeze, never approves own work |
| Reviewer | `<reviewer name, DIFFERENT from operator>` | writes `pm-review.json` per `REVIEWER_AGENT.md`, never edits candidate |

## SOP

```bash
# 1. operator edits the product input only
#    snapshot_date MUST equal today (Toronto).

# 2. freeze (candidate becomes immutable, flags generated)
#    -> <review-dir>/candidate.json
#    -> <review-dir>/candidate.sha256
#    -> <review-dir>/structural-flags.json   # every flag MUST be dispositioned

# 3. reviewer (independent!) writes the verdict — machine-checked JSON
# {
#   "schema_version": "1.0",
#   "reviewer": "<real name/model, != operator>",
#   "operator": "<who froze>",
#   "reviewed_at": "2026-10-04T12:00:00-04:00",
#   "snapshot_date": "<today>",
#   "candidate_sha256": "<copy from candidate.sha256>",
#   "verdict": "APPROVED | REVISE",
#   "executive_summary": ">=20 chars: what you checked, what binds to this sha",
#   "checks": {"<product check 1>":"pass", ...},
#   "findings": [
#     {"severity":"major","field":"<field path>",
#      "issue":"<what is wrong>",
#      "evidence":"<URL / quote / number proving it>",
#      "disposition":"must_fix"}
#   ],
#   "flags_dispositioned": [
#     {"code":"<flag code>","field":"<flag field>",
#      "disposition":"<how it was resolved>"}
#   ]
# }

# 4. validate before publish
#    python scripts/review/validate_pm_review.py \
#      --candidate <review-dir>/candidate.json \
#      --review <review-dir>/pm-review.json \
#      --flags <review-dir>/structural-flags.json \
#      --checks <product checks, comma-separated> --require-approved

# 5. publish (fails closed on: structure errors, sha mismatch, self-review,
#    uncovered flags, critical/major findings with APPROVED, frontend dirtied)
```

## Rules

- `APPROVED` requires: zero `critical`/`major` findings, all checks `pass`,
  every structural flag dispositioned, `candidate_sha256` matches frozen bytes.
- `REVISE` requires at least one `critical`/`major` finding or one failed check.
- Findings about UI taste are OUT OF SCOPE — file a separate frontend PR.
- Any edit to the input after freeze voids the review: re-freeze (`--force`) + re-review.
