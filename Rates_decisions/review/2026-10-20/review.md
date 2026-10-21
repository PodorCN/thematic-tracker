# Rates_decisions PM review: 2026-10-20

- Reviewer: independent-pm. Operator: rates-decisions-writer.
- Candidate sha256: `8b709e133a88d26dbfdd695b3dc0ff28572ea00905a0d6c3e37cc3f6fac0522b` (the same hash for candidate.sha256, the candidate.json bytes and canonical data/current.json)
- **Verdict: REVISE**. The machine-checked record is `pm-review.json`, and this file mirrors it.

## Checks
| check | result |
|---|---|
| official_policy | pass |
| pricing | pass |
| drivers | **fail** |
| market_validation | pass |
| freshness | pass |
| decision_usefulness | pass |

Structural flags: none, both in the committed file and when regenerated. Scoring reproduces: Fed base +5, effective +3.0, "lean hike". BoC base +8, effective +5.5, "strong hike lean".

## Blocking (major, must_fix)
- **boc-h6 reason**: "pushed the headline out of the 1-3% control range for the first time this cycle" is false. May 2026 CPI was 3.2% y/y, and Reuters says September is above the upper limit "once again after three months". Rewrite it (e.g., "back above the range for the first time since May"), then re-run check and freeze.

## Minor (next cycle unless noted)
- fed-d3: Williams overlap with fed-d1, and a Reuters retelling is scored at full weight. Second carry; escalates to major next time.
- fed-h4: the Oct 12 18% level is not a move caused by the minutes, and the same reading also validates the dovish fed-d3.
- boc-h7: the data block is one-sided (BOS sentiment improved). The 87% and RBC 3.7/3.1 figures are not corroborated; indexed coverage shows about 80-85%.
- boc-d4: surprise=1 with forecast "unverified".
- boc-d4: Standard Chartered (Aug, ~65bp) and BBH (Oct 20, ~100bp) are conflated.
- boc-d3: "six-month" vs "five-month" high (accepted).
- Fixed since 2026-10-19: fed-h1 previous, fed-h2 source_url, the Fed implied rate, boc-h5 attribution, and the BOS calendar row (moot).

## Not verifiable (network policy)
The exact 82.8/17.2 FedWatch print, Polymarket volume and the BoC Polymarket line (labelled stale), CPI m/m NSA/SA and the m/m consensus, the 87% intraday print, and the Oct 23 retail-sales timestamp and ex-autos consensus. None of these changes a band or the call.
