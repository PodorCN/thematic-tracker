# PM review — 2026-11-23 (REVISE)

Candidate `7c3a163dd420889e5c8cd0f624436bc847890a35598387cfdd3b081c293b9a3d` (frozen 09:11:15 ET),
operator `rates-decisions-writer`, reviewer `independent-pm`. Hash matches `candidate.sha256`,
`canonical(data/current.json)` has the same digest, `structural-flags.json` is `[]`, `publish.py --check`
passes, worktree clean.

## Verdict: REVISE — the BoC book repriced after the freeze

| block | frozen (09:11 ET) | live (09:24–09:34 ET) |
|---|---|---|
| BoC hike (Kalshi, normalised) | 47.5% (25bp 47.1 / >25 0.5) | 58.0% |
| BoC hold (Kalshi) | 51.5% | 41.0% |
| BoC 25bp increase (Polymarket) | 0.460 | 0.580–0.585 |
| Fed hike (Kalshi, normalised) | 95.5% | ~95 |
| Fed >25bp leg | 0.025 | 0.035 |

The frozen legs reproduce exactly at the stated minute (Kalshi candlesticks 14:11Z: 0.02/0.03,
0.92/0.93, 0.03/0.04, 0.00/0.01 for Fed; 0.00/0.01, 0.47/0.49, 0.50/0.55 for BoC; Polymarket CLOB
history 0.460 at 14:05Z), so this is post-snapshot repricing, not a misread — but at 14:17Z a
1,000-contract BoC trade lifted the 25bp leg to 0.48/0.55 and by 14:24Z the book was 0.55/0.60 with
hold at 0.36/0.45. The leader has flipped hold → hike on both venues the candidate cites.

Consequence: the `hold` band and the notes' "BoC book has given back about 10 points since Friday" no
longer describe the market; BlueGamma's 60% (20 Nov forward table) now agrees with Kalshi and
Polymarket rather than diverging.

## Six checks

- `official_policy` pass — Fed statement (10-2, Cook/Hammack for +25, "inflation remains elevated"),
  28 Oct minutes ("almost all" + "a couple" >25bp), BoC 28 Oct (+25 to 2.5%, Bank Rate 2.75%, deposit
  2.45%, CPI ~3.5% by year-end, 3% average 2027), 10 Nov deliberations, Q3 SLOS (-6.48 / -26.27, price
  -52.55, non-price 0.00). All reproduce on primaries.
- `pricing` **fail** — BoC 47.5 → 58.0 on Kalshi and 0.46 → 0.58 on Polymarket after the freeze.
- `drivers` pass — 24 drivers, parts sum to weight, mean |weight| 2.3, no pre-meeting leftovers, no
  weight ≥5 without numeric validation; two minor blemishes noted.
- `market_validation` pass — spot checks reproduce (Waller 10 Nov 0.805 → 0.885; BoC 6 Nov 0.305 mid
  at 14:13Z).
- `freshness` pass — as_of 09:11:15, reviewed 09:36 ET (25 min).
- `decision_usefulness` pass — structure and evidence chain intact; the call itself is what the pricing
  finding blocks.

## To fix in the re-freeze

1. Re-pull both BoC ladders and the Fed ladder after 09:20 ET, re-freeze, and rewrite the BoC narrative
   (and the "ledger versus market" paragraph) to the new leader.
2. Regenerate `calendar[6]` (BoC 9 Dec) from the same stamps.
3. Reconcile fed-h24's August control-group revision (1.6/1.4 vs 1.5/1.3).
4. Either link the Reuters original for the Williams entry or label the investing.com republication.
