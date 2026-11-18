# Rates Decisions — PM review 2026-11-18

**Verdict: REVISE** · reviewer `independent-pm` · operator `rates-decisions-writer`
· candidate `f504020268cdd9edbd307998cd8eed3d961e4d4103e9f1bf1f060b2231b2b966`
· frozen 09:16 ET, reviewed 09:39 ET (23 min) · 0 machine flags.

## What passed

- **official_policy** — Fed held 3-3/4 to 4 percent on 28 Oct by 10-2, Cook and
  Hammack preferring +1/4 (`monetary20261028a.htm`); September was a 12-0 +1/4
  to the same range (`monetary20260916a.htm`). BoC raised to 2.50% with Bank
  Rate 2.75%, deposit 2.45%, growth 1% / 2% / 2%, CPI "about 3½% by the end of
  the year" (`fad-press-release-2026-10-28`). Both next meetings 9 Dec (Fed
  14:00 ET with SEP, BoC 09:45 ET).
- **pricing** — Kalshi `KXFEDDECISION-26DEC` at the 09:05:38 ET read is
  0.065 / 0.925 / 0.035 / 0.005 / 0.005, raw sum 1.035, normalised
  95.65 / 3.38 / 0.97 — the block's 95.6 / 3.4 / 1.0. `KXCBDECISIONCANADA-26DEC`
  is 0.005 / 0.495 / 0.500 / 0.005 / 0.005, sum 1.010, giving 49.01 / 49.50 /
  0.99 against the printed 49.5 / 49.5. Polymarket gives 96.4 / 3.0 / 0.5
  (Fed, $38.47M) and 48.4 / 51.4 / 0.2 (BoC, $265.9k) on a re-read.
- **drivers** — 14 Fed and 5 BoC rows all trace to primaries: BLS 165k / 4.1% /
  AHE +0.4% / +3.1%, Aug +186k, Sep +60k, participation 61.9%; BLS CPI +0.4%
  with core +0.3% a third month and no 12-month (lapse in appropriations);
  Census +0.2% / control +0.6% / ex-autos +0.6% / Sep unrevised +0.8%; StatCan
  LFS −4,700 / 6.7% / wages 2.2%; GDP 0.0% with a −0.1% September advance;
  CPI 3.1% with ex-energy 2.0%. Waller, Jefferson, Bowman, Warsh and Hammack
  quotes are verbatim. `via Reuters` copy is labelled and down-weighted.
- **market_validation** — the historical Kalshi prints reproduce on the venue's
  own candles: 5 Nov 23:00 0.64/0.65 → 6 Nov 09:00 0.78/0.79 on 68,547
  contracts (fed-h16); 5 Nov 09:00 0.79/0.80 → 17:00 0.64/0.65 (fed-h19);
  10 Nov 04:00 0.80/0.81 → 05:00 0.88/0.89 on 28,077 with H26 0.01/0.02 →
  0.02/0.03 on 748,703 (fed-h17). Weight sums, breakdowns, decay and bands
  recompute (Fed 10 / 18.75, BoC −3 / −2.5).
- **freshness** — 23 minutes, inside 90.

## What blocks

1. **`calendar.2026-12-09.fed.forecast` (major).** Still "Hike 94.6% … (Kalshi
   ladder, 16 Nov 09:17 ET)" against a 95.6% pricing card in the same bytes;
   `renderCalendar()` prints it in the Forecast column.
2. **`calendar.2026-12-09.boc.forecast` (major).** Still "Hold 2.50% 52.5% /
   +25bp 46.5%" — a hold lead — against a 49.5 / 49.5 level ladder. The leader
   reverses between two places on one page.
3. **`notes` (major).** The BoC hike leg's "17 November close" is given as
   0.41/0.43 and the morning move as 7pp. The venue's 17 Nov 23:00 candle is
   0.44/0.46; 0.41/0.43 is the 13:00 ET candle. Close-to-08:00 is 5pp.

## Next cycle (does not block)

- BoC repriced after the freeze: Kalshi 0.495 → 0.485, Polymarket 51 → 49.5
  with hold 52.5. Re-grab at the latest `as_of`.
- `implied_rate_after` 4.13 for the Fed vs 3.88 + 0.956 × 25bp = 4.12; the BoC
  block uses the weighted form, the Fed block does not.
- BlueGamma re-read prints 65/35, +16bp (candidate: 67/33, +17bp) under the same
  date-only stamp.
- The Senior Loan Officer Survey row omits the published 10:30 ET slot.

No escalation: no field has carried a critical/major through the two prior
rounds (2026-11-16 APPROVED, 2026-11-09 two majors on different fields).
