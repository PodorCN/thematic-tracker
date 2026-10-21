# Rates Decisions — independent PM review, 2026-10-21

- verdict: **REVISE**
- candidate sha256: `82c8a075cc9b140536565196bc5a038a67064ffdfb1ef288cd8b1a5427b9f92a`
- reviewer: independent-pm · operator: rates-decisions-writer
- bundle: candidate.json hash matches candidate.sha256 (raw and canonical agree); structural-flags.json = `[]`, so nothing to disposition.

## Verdict in one line

Fed leg verified end to end; BoC pricing does not reproduce from its own cited BlueGamma page (95% / +24bp claimed, 93% / +23bp printed at 21 Oct 08:09:32 ET, 89% / +22bp at 07:00 ET for 20 Oct).

## What was checked against primaries

| Claim | Source | Result |
|---|---|---|
| Sep 16 FOMC hike to 3.75–4.00%, 12–0 | federalreserve.gov/newsevents/pressreleases/monetary20260916a.htm | match |
| Next FOMC Oct 27–28, 2pm ET | federalreserve.gov/monetarypolicy/fomccalendars.htm | match |
| Sep SEP 16 of 18 see ≥1 more 2026 hike | federalreserve.gov/monetarypolicy/fomcprojtabl20260916.htm (+wire count 12/4/2) | match |
| Oct 7 minutes: "most ... another increase ... by year end" | fomcminutes20260916.htm | match |
| Sep CPI 3.7% / core 2.6% YoY, +0.6% m/m | bls.gov/news.release/archives/cpi_10142026.htm | match |
| Sep PPI +1.3% m/m, largest since Mar 2022 | bls.gov/news.release/archives/ppi_10152026.htm | match |
| Sep payrolls +29k, U3 4.2% | bls.gov/news.release/archives/empsit_10022026.htm | match |
| Aug PCE 3.4% / core 3.0% | bea.gov/news/2026/personal-income-and-outlays-august-2026 | match |
| Jefferson, Waller, Williams, Hammack, Warsh, Daly, Bowman quotes | federalreserve.gov / newyorkfed.org / clevelandfed.org / cnbc.com / reuters syndications | match |
| FedWatch 86.2% hold / 13.8% hike, Oct 21 | investing.com fed rate monitor (CME 30-day FF), updated 08:25 ET | match |
| BoC Sep 2 hold 2.25%, 7th consecutive | bankofcanada.ca/core-functions/monetary-policy/key-interest-rate/ | match |
| BoC Oct 28 + MPR, 09:45 ET | bankofcanada.ca/2026/10/interest-rate-announcement-and-monetary-policy-report-october-28-2026/ | match |
| Sep CPI 3.1%, CPI-trim 1.8 / CPI-median 1.9 | statcan dq261019a + bankofcanada.ca/rates/price-indexes/cpi/ | match |
| Sep LFS -68k, second straight decline | statcan dq261009a | match |
| Q3 BOS: inflation expectations up with tariffs/energy | bankofcanada.ca/2026/10/business-outlook-survey-third-quarter-of-2026/ | match |
| Sep 2 deliberations: energy spillover could require a response | bankofcanada.ca/2026/09/summary-of-governing-council-deliberations... | match |
| G7 100M bbl release (Oct 2) | financialpost.com | match |
| UBS/Manulife/Oxford/Scotia all moved to Oct; UBS 3.3% CPI call | mpamag.com 592150 (Oct 2) | match |
| Polymarket Fed 88/12, BoC 73/27 + volumes | gamma-api.polymarket.com | match |
| PCE + Q3 GDP advance Oct 29 08:30 ET | bea.gov/news/schedule | match |

Structural math re-run locally: weight_breakdown sums = weight for all 22 drivers, direction signs match the arrays, base totals recompute to 5 (Fed) and 6 (BoC), effective totals 3.0 / 5.0 reproduce under the 1.0/0.75/0.5/0.25 decay, mean |weight| 2.79 / 2.75 sits inside 2–4, no weight ≥5 so no numeric-validation gate fires, no shared URL across hawkish/dovish so no facet requirement.

## Blocking

1. **BoC pricing (major).** 95% / 5% / +24bp cannot be reproduced. BlueGamma prints 93% / 7% / +23bp with an in-page `<time dateTime="2026-10-21T12:09:32">` (08:09:32 ET, 34s after the freeze), and a 07:00 ET copy of the same URL prints 89% / +22bp "as of 20 Oct 2026". The same pair is copied into `calendar[0].forecast` and `drivers.boc.hawkish[0].market_validation`, so one edit fixes all three. Either attach the capture that shows 95% / +24bp, or restate as 93% / 7% / +23bp and re-freeze.

## Non-blocking (next cycle)

2. boc-d1 title "wipes out 2026 gains" — StatCan has +181k Apr–Jul and +95k YoY; the two declines are -110k.
3. boc-h5 title "as oil holds ~$100" — Brent ~US$110, WTI US$101; $100 is Macklem's hypothetical.
4. fed-h1 consensus 3.7% / 3.3% has no link; the BEA release carries actuals only.
5. Fed driver +3.0 ("lean hike") vs 86.2% hold is unreconciled in `notes`, unlike the BoC OIS-vs-Polymarket gap.

No candidate bytes were touched; nothing was published for this date.
