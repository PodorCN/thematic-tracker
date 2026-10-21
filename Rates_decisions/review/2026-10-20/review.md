# Rates_decisions PM review: 2026-10-20 (round 2)

- Reviewer: independent-pm. Operator: rates-decisions-writer.
- Candidate sha256: `02409a5a89b5d4855897e627e2950f20d019dd0d0fc08a4333943d40a03ee486` (re-freeze 7c977c0). This replaces round 1 (REVISE on 8b709e133a88, commit 57e3c5f).
- **Verdict: APPROVED.** This approval binds sha 02409a5a89b5 only. The machine-checked record is `pm-review.json`, and this file mirrors it.

## Checks
All six pass: official_policy, pricing, drivers, market_validation, freshness, decision_usefulness. No structural flags (committed and regenerated).

## Math (recomputed, as_of 2026-10-20)
- Fed: hawkish 22 / eff 15.5, dovish 16 / eff 12.0 -> base +6, effective +3.5, "lean hike".
- BoC: hawkish 17 / eff 12.5, dovish 8 / eff 6.0 -> base +9, effective +6.5, "strong hike lean".
- Implied rates: Fed 3.92, BoC 2.45. Mean |weight| 2.71 / 2.78. No weight >=5.

## Round-1 findings: status
- boc-h6 "first time this cycle" (was MAJOR): **fixed**. Now "back above ... after three months (Reuters)".
- fed-d3 Williams re-count: **fixed**. Now Jefferson timing only, w2, labelled as a retelling.
- fed-h4 validation: **fixed** ("unverified").
- boc-h7 balance/87%: **fixed**. Offsets added, range ~80-87%.
- boc-d4 surprise point: **fixed** (w2).
- boc-d4 Standard Chartered: **withdrawn**. My round-1 finding was partly wrong: StanChart's Oct 20 note does call ~100bp excessive and keeps the hold through 2027. The new wording is accurate.
- boc-d3 "six-month": **fixed** ("multi-month").

## Open minors (next cycle)
- fed-d3: the source label still says "via Williams, Jefferson", and its ~70% -> ~25% move overlaps fed-d1's ~70% -> ~50% leg.
- boc-d4: market_validation still says "87%", while boc-h7 uses ~80-87%.
- boc-h7: the RBC 3.7%/3.1% read is not corroborated. It is labelled as RBC's, so accepted.

## Not verifiable (network policy)
The exact 82.8/17.2 FedWatch print, the 87% top of the range, CPI m/m NSA/SA and the m/m consensus, the RBC firm read, Polymarket volume, and the Oct 23 retail-sales time and ex-autos consensus. None of these moves a band.
