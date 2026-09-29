# Round-2 remediation evidence (operator-produced, 2026-09-29 ~17:00-17:10 Toronto)

Addresses review-artifacts/code-2026-09-29-frontend-tenor/pm-review.json (round 1, verdict revise).

## Finding 1 (major): missing payload key-convention test + insensitive render gate

Added tests/test_render_truthfulness.py:
- test_candidate_payload_uses_tenor_specific_average_rate_keys
- test_odds_cards_render_the_payloads_tenor_level_and_label (card-region scoped via _card_region: fed region = DOM between 'odds-card fed' and 'odds-card boc'; boc region = 'odds-card boc' to 'formula-fold')

RED proof A — key-convention test pinned to the OLD (iteration-02, quarterly-key) candidate:
  FED_BOC_RENDER_CANDIDATE=...iteration-02/candidate.json pytest ...test_candidate_payload_uses_tenor_specific_average_rate_keys
  -> FAILED: "the Fed October 30-day futures average is monthly tenor; it must not be stored under a quarterly-named key"

RED proof B — card-region test against the PRE-CHANGE renderer (the exact hunk from frontend-tenor.patch temporarily reverse-applied to a working-tree index.html, restored byte-exact afterwards, sha256 before/after 8b1242a0558d541c1c801a663e1124a328cbc9cfea0daaedda8192837ef106ca):
  FED_BOC_RENDER_CANDIDATE=...iteration-03/candidate.json pytest ...test_odds_cards_render_the_payloads_tenor_level_and_label
  -> FAILED: "the Fed card does not show the payload's monthly-average level 3.895%" (card text showed 'observable proxy level available' — exactly the degradation round 1 demonstrated)

GREEN — frozen renderer + pinned approved candidate:
  FED_BOC_RENDER_CANDIDATE=...iteration-03/candidate.json pytest tests/test_render_truthfulness.py -q -> 9 passed
  full suite (unpinned): 84 passed, 3 skipped (documented skips: published payload predates the contract)

## Finding 2 (minor): bad pin skipped green

Added test_missing_pinned_candidate_fails_closed; _headless_dump now raises AssertionError when FED_BOC_RENDER_CANDIDATE is set but unreadable.
RED: "Failed: DID NOT RAISE AssertionError" (pre-fix). GREEN: included in the 9 passed above.

## Finding 3 (minor): manifest created_at forward-dated

Round-2 freeze-manifest.json created_at is written from the real clock at freeze time.

## Housekeeping: BACKEND_DATA_SPEC.md

Section 3 (~line 121) now requires a tenor-specific key name (implied_monthly_average_rate for ZQ-style monthly contracts; implied_quarterly_average_rate for CRA-style quarterly contracts) plus rate_label; explicitly forbids storing a monthly-tenor value under the quarterly key.
