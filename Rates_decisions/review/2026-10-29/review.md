# Rates Decisions — 2026-10-29 review (independent PM)

This review covers candidate `b6045fa6006e067b…` (snapshot 18:12 ET), operator `rates-decisions-writer`. Verdict: **REVISE**. Four checks pass; `drivers` and `market_validation` fail.

## Integrity

- The sha256 of the candidate bytes is `b6045fa6006e067b4e5fe37037ec001d20685764c49a4ff2b4965e82f11aa8e6`. The candidate bytes match the shared canonical form, and `canonical(data/current.json)` gives the same hash.
- `npm run check`: structure valid, 0 structural flags. `flags_dispositioned` is therefore empty.
- Frontends and scripts are clean in the working tree. Only `data/current.json` and this review directory differ.

## New driver-window rule

The 2026-10-28 candidate held exactly 21 drivers, published 16 Sep – 19 Oct with weights 2–4. None reaches weight 6, so pruning all of them is correct. All 9 remaining drivers are dated 28–29 Oct, so the rendered "since 2026-10-28" header is now true.

## Verified against primaries

- **FOMC statement** (federalreserve.gov/newsevents/pressreleases/monetary20261028a.htm):
  - 10–2 vote; Cook and Hammack preferred +1/4.
  - "Economic activity is expanding at a strong pace" and "Inflation remains elevated" both match.
- **Press conference PDF** (FOMCpresconf20261028.pdf):
  - "real activity is clearly pointing in the right direction … But inflation is too high"
  - H1 GDP revised 1.8% → 2.4%; Q3 "likely running above 3 percent"; business investment "about a double-digit pace"
  - "conditions are quite positive"
  - "I don't believe in forward guidance absent exigent circumstances … I also don't believe in prejudging meetings"
- **Sep SEP:** 16 of 18 end-2026 dots sit above 3.875 (12 at 4.125, 4 at 4.375).
- **BEA PI&O Sep:**
  - PCE prices +0.5% m/m and 3.6% y/y; core +0.3% m/m and 3.1% y/y.
  - Real PCE rose less than 0.1%; real DPI fell 0.3%; saving rate 3.8%.
  - August figures (3.4% / 3.0%) are confirmed from the 30 Sep release.
- **BEA Q3 GDP advance:** 3.4% (Q2 2.2%); final sales to private domestic purchasers 4.9%.
- **BoC press release and opening statement:**
  - Policy rate 2.5%, Bank Rate 2.75%, deposit rate 2.45%.
  - CPI about 3½% by year-end, averaging 3% in 2027 (a point above July), 2% by mid-2028.
  - "There could be a need to raise the policy rate further, but given the uncertainties, we will proceed carefully."
  - CPI excluding gasoline 2.2%; core close to 2%; Q4 tariff drag.
- **Kalshi, live at 18:15 ET** (the candidate matches exactly):

  | | 25bp hike | 50bp hike | Hold | Cuts (each) | Normalised hike / hold / cut |
  |---|---|---|---|---|---|
  | Fed | 0.73/0.74 | 0.02/0.03 | 0.23/0.24 | 0/0.01 | 75.6 / 23.4 / 1.0 |
  | BoC | 0.36/0.38 | 0/0.01 | 0.62/0.64 | 0/0.01 | 36.9 / 62.1 / 1.0 |

  The as_of values are real last trades: 22:01:30Z @0.74 and 19:07:35Z @0.37. The "~24k contracts" figure equals the BoC H25 lifetime volume (24,303).
- **Polymarket legs** recompute to 74.7 / 24.6 / 0.7 (Fed) and 35.7 / 63.9 / 0.4 (BoC), with volumes of $8.20M and $86k. At 18:17 ET the Fed hike had drifted to about 73.6%.
- **Arithmetic:**
  - Fed: 3+2+3+2−2−2 = +6, lean hike.
  - BoC: 4+2−3 = +3, hold.
  - Every driver is 7 days old or less, so decay is ×1.0.
  - All breakdowns sum to their weights, and same-URL pairs carry distinct facets.
  - Implied rates: 4.07% and 2.59%.
- **Calendar:**
  - BLS: Employment Situation 6 Nov and 4 Dec; CPI 10 Nov.
  - StatCan daily calendar: GDP by industry 30 Oct; LFS 6 Nov.
  - StatCan 2026 PDF: CPI (Oct) 16 Nov.
  - BLS September CPI 3.7% / core 2.6%; payrolls +29k; unemployment 4.2%.
  - StatCan July GDP "essentially unchanged".

## Blocking (major, must fix)

1. **`drivers.boc.hawkish[0].market_validation`: the window is cherry-picked.**
   - Before the 09:45 release, the Kalshi Dec 25bp-hike leg was 0.48/0.49 with no trades.
   - After the release it traded 09:45:29 @0.46 → 09:47 @0.42 → 09:48 @0.35 → 09:57 @0.33.
   - The quoted "0.33 → 0.42 (10:00 → 13:00 closes)" is a partial rebound from a 13c fall caused by the release that boc-h7 itself cites.
   - Over the full window December hike odds fell about 11c, to 0.37. That is dovish, the opposite sign to the driver's +4.
   - The "Bloomberg swaps ~60% (Globe and Mail)" figure is second-hand, unlinked and not labelled `via` in this field. I could not locate it.
2. **`drivers.boc.hawkish[0].data.forecast`: wrong number and wrong source.**
   - The field says "pre-meeting Kalshi/Polymarket ~96%".
   - Kalshi Oct H25 was actually 0.83/0.84 at 09:00 ET (H0 0.14/0.15), and Polymarket was 85.3% at 09:08 ET.
   - The 96% was the BlueGamma CORRA OIS figure. This feeds the driver's surprise = 1.

## Next cycle (minor)

3. `fed-h12` leaves out the GDP release's price block: Q3 PCE prices slowed to 2.1% SAAR from 5.0%, and core to 2.5% from 3.3%. `fed-h11`'s "both re-accelerate" is true on year-on-year terms only.
4. `fed-h11` credits the 08–09 ET Kalshi uptick to PCE alone, while `fed-h12` says the same move can't be split between PCE and GDP. Over the full window the data day was dovish on the market: 0.78 → 0.80 → 0.75 → 0.74.
5. `fed-d7` quotes "going the right way", but the transcript says "going in the right way" and "gone the right way". Its claim to be "the main reason" December sits near 75% is contradicted by its own validation, which shows the hike leg rising to 0.81 during the press conference.
6. `boc-h8` links the press release, but "slack absorbed" and "less downward pressure on prices…" appear only in the opening statement.
7. Carried from the 2026-10-28 review: Kalshi and Polymarket are the same instrument class, so their agreement is weak cross-validation.

## Previous round (2026-10-28) follow-up

| # | Finding | Status |
|---|---|---|
| 1 | Header window contradicted the cards | Fixed by pruning |
| 2 | Scores still described the October decision | Fixed: drivers are all post-decision |
| 3 | Fed ladder reprice | Superseded |
| 4 | fed-d4 CNBC citation gap | Fixed: driver removed |
| 5 | boc-h3 resolved catalyst still paying +3 | Fixed: driver removed |
| 6 | Same instrument class | Still open (item 7 above) |
| 7 | Audit trail | Resolved: the 2026-10-28 review is on disk |

## Operator instructions

1. Restate `drivers.boc.hawkish[0].market_validation` over the full window: pre-release ~0.48 → 0.33 trough → 0.42 at 13:00 → 0.37 on 29 Oct. Then either link the swaps figure or mark it "via Globe and Mail, unverified".
2. Correct `drivers.boc.hawkish[0].data.forecast` to the venue figures: Kalshi ~84%, Polymarket 85%. If you keep 96%, label it as CORRA OIS.
3. Re-justify `weight_breakdown.surprise` given that the same release moved December hike odds down. If the weight changes, recompute `total_score.boc`.
4. Re-freeze and resubmit. The minors are optional this round.

**Verdict: REVISE.** Publishing is withheld, and no archive may be written against `b6045fa6006e`.
