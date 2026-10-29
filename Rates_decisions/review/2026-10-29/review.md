# Rates Decisions — 2026-10-29 review, round 2 (independent PM)

This review covers candidate `e1a179d37974bc90…`, operator `rates-decisions-writer`. It is the re-freeze after the round-1 REVISE of `b6045fa6006e` (commit 1d191f9). **Verdict: APPROVED.** All six checks pass, and there are zero open critical or major findings.

## Integrity

- The sha256 of the candidate bytes is `e1a179d37974bc90502faed99b6ee95c02bc863cf4283e6461bb415255329264`, which matches `candidate.sha256`.
- The candidate bytes match the shared canonical form, and `canonical(data/current.json)` gives the same hash.
- `npm run check`: structure valid, 0 structural flags. `flags_dispositioned` is empty.
- The working tree has no frontend or script changes.
- The diff from 73e7246 touches only boc-h7, boc-h8, boc-d4, fed-h11, fed-h12, fed-d7, `total_score.boc` and `notes`. Pricing, calendar, betting and the other drivers are byte-identical to round 1. Round 1 verified them against federalreserve.gov, BEA, bankofcanada.ca, BLS, StatCan and the live Kalshi and Polymarket books.

## Round-1 majors: both fixed

These two fixes are recorded here and in `executive_summary` rather than as findings. The validator counts every major finding as open, even one marked `fixed`.

1. **boc-h7 `market_validation`.** The field now covers the whole window: 0.46 at 09:45, then 0.33–0.35 within 12 minutes, then 0.39–0.40, then 0.37 on 29 Oct. It is labelled "Mixed".
   - The Kalshi trade tape confirms it: 09:45:29 @0.46, 09:48:45 @0.35, 09:57:11 @0.33, 10:31–10:59 @0.39–0.42, last trade 19:07:35Z @0.37.
   - The Bloomberg swaps figure is now labelled secondary and linked. The Globe and Mail article (HTTP 200) says "a roughly 60-per-cent chance of another hike at the bank's next meeting in December", according to Bloomberg data.
2. **boc-h7 `data.forecast`.** The field now reads "CORRA OIS ~96% (BlueGamma), Polymarket 85.3% (09:08 ET)", which matches the morning candidate (git `2516384^`).
   - Surprise is now 0, so the weight is 2+1+0 = 3.
   - BoC rescores to 3+2−3 = **+2, hold**, against Kalshi 62.1% hold.
   - Fed is unchanged at +6, lean hike, against 75.6% hike.

## Round-1 minors

| Round-1 minor | Status |
|---|---|
| fed-h12 price block | Fixed: now shows PCE 2.1% / core 2.5% SAAR against Q2's 5.0% / 3.3% |
| fed-h11 / fed-h12 attribution | Fixed: one combined 08:30 window, 0.78 → 0.74, net −4c (matches the hourly candles) |
| fed-d7 "main reason" claim | Fixed: removed |
| fed-d7 quote | Still open: see item 1 below |
| boc-h8 wording | Partly fixed: summary and reason now quote the press release; the title does not (item 2 below) |
| Same instrument class | Mitigated for BoC by the verified swaps figure; still open for Fed (item 4 below) |

## Next cycle (minor, non-blocking)

1. **fed-d7 quote.** The summary still has "going the right way". Warsh said "going in the right way" and "gone the right way"; the exact phrase appears only in a reporter's question.
2. **boc-h8 title.** It still says "slack absorbed by 2028", which is opening-statement wording. The linked press release says "some excess supply".
3. **boc-h7 stamps.**
   - "BlueGamma, 09:13 ET" is the morning freeze time; the OIS page was stamped 08:27:48 ET.
   - "−9c net" is measured from the first post-release trade. The pre-release book was 0.48/0.49, so the move is about −11c.
4. **Fed cross-check.** Fed pricing is still checked only Kalshi against Polymarket, which are the same instrument class.

**Verdict: APPROVED.** This approval binds to `e1a179d37974` only.
