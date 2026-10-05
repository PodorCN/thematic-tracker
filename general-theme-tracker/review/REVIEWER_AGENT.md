# REVIEWER_AGENT.md — General Theme Tracker annex (thin)

> Shared doctrine: [`scripts/review/REVIEWER_AGENT.md`](../../scripts/review/REVIEWER_AGENT.md)
> (roles, evidence, severity — identical for all trackers). This file only
> declares what is Theme-specific. On conflict, the shared file wins for
> mechanics; this annex wins for Theme judgment.

## Theme checks (passed to the validator as `--checks`)

`excess_math` `timing_source` `freshness` `readability` `theme_noise`
`proxy_tradability` — all must be `pass` for `APPROVED`.

## Theme scoring rubric (binding)

See `general-theme-tracker/AGENT.md` §4 + `data/schema/theme.schema.yaml`:
excess recompute tolerance 0.2pp; body 900 CJK / 500 EN words; series ≥2 points;
proxies 1–3 with ETF expense + liquidity note + tracking gap; every event needs
UTC + source + https URL; `depends_on` non-empty (else Noise);
`theme_vs_noise.score == true-count`, `score >= 3` for homepage
(`New`/`Continuing` with `score < 3` is blocked; `Fading`/`Dead` excepted).

## Theme source rule (binding)

Claiming a primary (earnings release, StatCan/BLS/Fed/BoC, exchange close)
requires linking that primary domain; `via X` retellings must be labeled and
down-weighted. `as_of_UTC` >7d vs `snapshot_date` is a structural error;
>48h is a reviewer major. Machine flags every mismatch; the reviewer decides
the severity.
