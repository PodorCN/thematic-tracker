# REVIEWER_AGENT.md — Rates Decisions annex (thin)

> Shared doctrine: [`scripts/review/REVIEWER_AGENT.md`](../../scripts/review/REVIEWER_AGENT.md)
> (roles, evidence, severity — identical for all trackers). This file only
> declares what is Rates-specific. On conflict, the shared file wins for
> mechanics; this annex wins for Rates judgment.

## Rates checks (passed to the validator as `--checks`)

`official_policy` `pricing` `drivers` `market_validation` `freshness`
`decision_usefulness` — all must be `pass` for `APPROVED`.

## Rates scoring rubric (binding)

See `Rates_decisions/AGENT.md` §4: weight 1–10 integer, `weight_breakdown`
parts sum to weight, hawkish `+1` / dovish `-1`, age decay
`≤7d ×1.0 / 8–14d ×0.75 / 15–30d ×0.5 / >30d ×0.25`, same-URL split needs
distinct `facet`, weight ≥5 needs numeric market validation.

## Rates source rule (binding)

Claiming StatCan / BLS / BEA / Fed / BoC requires linking that primary domain;
`via X` retellings must be labeled and down-weighted. Machine flags every
mismatch; the reviewer decides the severity.
