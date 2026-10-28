# Rates Decisions — 2026-10-28 post-decision refresh (independent PM)

Candidate `a88d6f6c10be2065…` (frozen 15:12:55 ET) — **APPROVED**, all six checks pass.

## What was verified against primaries

- **FOMC 28 Oct** (federalreserve.gov/newsevents/pressreleases/monetary20261028a.htm): target range maintained at 3-3/4 to 4 percent, 10-2 vote, Lisa D. Cook and Beth M. Hammack dissenting for a quarter-point increase. "Activity is expanding at a strong pace", "inflation remains elevated" and the "accumulation of more information" sentence all reproduce.
- **BoC 28 Oct** (bankofcanada.ca/2026/10/fad-press-release-2026-10-28/): overnight target +25bp to 2.5%, Bank Rate 2.75%, deposit rate 2.45%; "there could be a need to increase the policy rate further … proceed carefully"; CPI about 3½% by year-end, 3% average in 2027, 2% by mid-2028; next decision 9 Dec, next MPR 27 Jan. "First increase since July 2023" checks against Valet series V39079 (last raised 13 Jul 2023).
- **Pricing**: as_of values are real Kalshi trade stamps, not pull clocks — KXFEDDECISION-26DEC-H25 traded 19:11:32.492Z @0.80, KXCBDECISIONCANADA-26DEC-H25 traded 18:58:55.068Z @0.39. Re-pull at 15:47 ET: Fed 81.95/17.07/0.98 vs frozen 81.6/17.4/1.0; BoC 38.73/60.29/0.98 vs 38.4/60.6/1.0. Polymarket BoC reproduces exactly (39.7/59.6/0.7); Fed hike leg 2.1pp firmer after the stamp.
- **Venue switch justified**: BlueGamma SOFR/CORRA pages still print "Next meeting: 28 Oct 2026" and 3.88% / 2.25% current rates at 15:49 ET (stamps 19:46:53Z, 19:12:33Z).
- **Arithmetic**: Fed base +2 / effective 0.0, BoC +6 / +4.25; every breakdown sums to its weight; every decay factor matches the as_of age. StatCan Sep CPI 3.1%, employment −68,000; BEA 29 Oct 08:30 PCE Sep + Q3 GDP advance; FOMC 8-9 Dec with SEP.

## Minor findings (next cycle, non-blocking)

1. `drivers` carried over unchanged, so the rendered header reads "since 2026-10-28" above cards dated 16-19 Oct (notes explain it but are not rendered).
2. Carried scores still describe the October decision (Fed 0.0 hold vs 81.6% Dec hike; BoC +4.25 vs 60.6% hold); only the frontend divergence badge discloses it.
3. Fed ladder re-priced 0.35pp after the stamp (legs one cent firmer).
4. `fed-d4` CNBC link still lacks the "broadly conformed" quote (third cycle).
5. `boc-h3` is a resolved October catalyst still paying +3.
6. Primary and overlay are now both event-contract ladders — weaker cross-validation than OIS vs binary.
7. Re-freeze deleted the 09:33 review from the review directory (audit trail).

Verdict: **APPROVED** — publish candidate `a88d6f6c10be`.
