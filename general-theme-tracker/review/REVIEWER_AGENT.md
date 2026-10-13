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
excess recompute tolerance 0.2pp; body ~200 English words max (2min core, must state what happened);
summary ~100 words max (pre-click overview with the proxy-vs-benchmark picture);
chain 3-5 dated steps (`when` <= 20 chars, chronological, traceable to dated events/body), each label ~12 words max + plain-English detail ~30 words max (readable by a non-market reader, jargon explained in-step), traceable to sourced body/events (no new claims);
body + explainer ~500 words combined max (up to 5min folded); series ≥2 points;
proxies 1–3 with ETF fee + liquidity note + tracking gap; every event needs
UTC + source + https URL + proxy_ret/benchmark_ret for the same return_window (benchmarked move); `depends_on` non-empty (else Noise);
`theme_vs_noise.score == true-count`, `score >= 3` for the homepage
(`New`/`Continuing` with `score < 3` is blocked; `Fading`/`Dead` excepted).

## Theme source rule (binding)

Claiming a primary (earnings release, StatCan/BLS/Fed/BoC, exchange close)
requires linking that primary domain; `via X` retellings must be labeled and
down-weighted. `as_of_UTC` >7d vs `snapshot_date` is a structural error;
>48h is a reviewer major. Machine flags every mismatch; the reviewer decides
the severity. Non-English strings anywhere are blocking findings.
