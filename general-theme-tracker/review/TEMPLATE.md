# Review flow — General Theme Tracker (shared gate, blocking)

> Shared template: [`scripts/review/TEMPLATE.md`](../../scripts/review/TEMPLATE.md).
> Concrete commands for this product:

```bash
# 1. operator edits data only (week bundle YAMLs)
#    Only touch general-theme-tracker/data/themes/<week>/*.yaml
#    + data/market/snapshot_<week>.yaml + data/commentary/<week>.yaml.

# 2. structure check (JS schema + Python bundle gate)
npm run validate                  # YAML schema_v1
python3 scripts/publish.py --check

# 3. freeze (candidate immutable, flags generated)
npm run freeze
# -> review/<today>/candidate.json + candidate.sha256 + structural-flags.json

# 4. reviewer (independent!) writes review/<today>/pm-review.json
#    See review/REVIEWER_AGENT.md (this folder) for the six checks + rubric.
#    Bind candidate_sha256 from candidate.sha256; disposition every flag.

# 5. validate
npm run review:check

# 6. publish (fails closed; publishes exactly the reviewed bytes)
npm run publish
# -> data/archive/<today>.json (bytes == reviewed candidate)
```

Rules: `APPROVED` needs zero critical/major + all six checks pass + flags
covered + sha match. Any post-freeze edit voids review: `npm run freeze -- --force` + re-review.
Legacy `data/reviews/*.reviews.yaml` free-text reports are history only (publish does not read them).
