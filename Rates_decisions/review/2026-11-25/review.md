# PM review — 2026-11-25 (candidate c79e1bdbc86b…)

Verdict: **APPROVED** — independent-pm / rates-decisions-writer, reviewed 09:34 ET.

## Checks

| check | verdict | basis |
|---|---|---|
| official_policy | pass | Fed held 3-3/4–4% on 28 Oct, 10-2, Cook + Hammack for +1/4; next meeting 8-9 Dec with SEP (14:00 ET). BoC +25bp to 2.50%, Bank Rate 2.75, deposit 2.45; next announcement 9 Dec 09:45 ET. |
| pricing | pass | Kalshi five-leg mids re-fetched 09:27 ET: Fed 0.035/0.925/0.025/0.005/0.005, sum 0.995 → 95.5% any hike; BoC 0.255/0.745/0.005/0.005/0.005, sum 1.015 → 73.9% any hike. Both reproduce the frozen numbers. Polymarket 96.6% Fed (96% frozen, $58.4M) and 75.3% BoC (76% frozen, $381.5k). |
| drivers | pass | Primary domains match claims; today's two BEA drivers replay on the release pages; weight_breakdown sums exact; mean \|weight\| 2.42 Fed / 2.11 BoC. |
| market_validation | pass | Spot-checked historical quotes against Kalshi candles: fed-h16 0.645→0.785 (+14pp) on 6 Nov and boc-d8 0.57→0.51 (−6pp) on 20 Nov both reproduce. No weight ≥5 without numbers. |
| freshness | pass | as_of 09:14:04 ET vs review 09:34 ET = 20 min, well inside 90. |
| decision_usefulness | pass | Summaries ≤16 words, no duplicated title numbers; title cap exceeded (see findings). |

## Findings (all minor, next cycle)

1. `drivers.fed.hawkish[14].data.actual` — fed-h29 calls 2.7% the "GDP price index"; BEA says *gross domestic purchases* price index. Number right, label wrong.
2. `drivers[*].title` — 10 of 28 titles over the 12-word cap (worst fed-h27, 19 words). Carried from 20/23 Nov.
3. `drivers.fed` — 19 Fed drivers vs the 3-6 / ~8 guideline; 21 → 24 → 28 over three rounds.
4. `meetings.fed.pricing.source` — app.js still renders the pooled any-size pool under a "Hike 25bp" label (95.5% vs 92.0% exact). Data now names the basis everywhere it can; app.js sits inside the frozen frontend contract, so this needs a separate frontend PR.
5. `notes` — BlueGamma read 84% at the 09:10 capture and prints 83% now (same date-only stamp); the disclosed gap is currently 7.7-9.1pp.

## Closed from the 08:41 round

Both BEA actuals embedded (calendar + fed-h29/h30); both ladders re-cut at 09:14; Beige Book row added (25 Nov 14:00); unsupported 85-96% range removed from boc-h7; unsourced surprise points zeroed on fed-h9, boc-h7, boc-d4. The renderer label is the only residual and is out of this lane.

No structural flags. Published bytes identical to the reviewed candidate.
