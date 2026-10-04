# Review flow — Rates Decisions (shared gate)

> Shared template: [`scripts/review/TEMPLATE.md`](../../scripts/review/TEMPLATE.md).
> Concrete commands for this product:

```bash
# 1. operator edits data only (snapshot_date = today Toronto)
#    Only touch Rates_decisions/data/current.json.

# 2. freeze (candidate immutable, flags generated)
npm run freeze
# -> review/<today>/candidate.json + candidate.sha256 + structural-flags.json

# 3. reviewer (independent!) writes review/<today>/pm-review.json
#    See review/REVIEWER_AGENT.md (this folder) for the six checks + rubric.
#    Bind candidate_sha256 from candidate.sha256; disposition every flag.

# 4. validate
npm run review:check

# 5. publish (fails closed; publishes exactly the reviewed bytes)
npm run publish

# 6. browser验收
npm run dev  # http://127.0.0.1:7100
```

Rules: `APPROVED` needs zero critical/major + all six checks pass + flags
covered + sha match. Any post-freeze edit voids review: `npm run freeze --force` + re-review.
Legacy `review/<YYYY-MM-DD>.md` free-text approvals are retired (kept for history only).
