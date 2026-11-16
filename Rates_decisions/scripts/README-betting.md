# Prediction market fetcher

Run `node scripts/fetch_betting.mjs` from `Rates_decisions` for a read-only
fetch. The Polymarket event slugs and official next-meeting instants come from
the existing `data/current.json`; October slugs are no longer hardcoded.
Meeting dates in that file still need current official-source verification by
the operator and independent PM reviewer.

The fetcher requires one open matching event, five unique supported rate legs,
an unambiguous Yes/No outcome mapping, bounded finite prices, and explicit venue
timestamps. Each binary pair must sum to one within 2 percentage points; the
five mutually exclusive Yes prices must sum to one within 10 percentage points
before normalization. These are conservative refusal thresholds, not a claim
that price discrepancies are economically immaterial. The oldest event/leg
timestamp becomes `as_of`; timestamps older than 90 minutes or over 5 minutes
in the future fail. The operator's stricter refresh window still applies.

Gamma settlement metadata can use end-of-day Toronto or a UTC date boundary.
It is checked against the configured meeting date in either representation;
it is never used as the policy announcement clock. The verified official
meeting instant determines when the market is no longer the upcoming meeting.

## Candidate-only output

`npm run fetch:odds` now uses `--candidate`. Both bank fetches must succeed
before a separate `data/betting-candidate.json` can be emitted. Other venues
and unrelated fields are preserved from the document read before fetching.
The candidate is flushed and read back before an atomic, non-overwriting hard
link publishes it. Filesystems without the required hard-link support fail
closed. `data/current.json`, frozen reviews and published snapshots are never
written by this helper. Direct `--write` is intentionally rejected before any
fetch; scripts expecting its old destructive behavior must use candidate-only
output and the established operator workflow.

If a candidate already exists, the command refuses to overwrite it. Inspect
the existing candidate and its source timestamps first. Preserve a verified
backup before an operator archives/removes an obsolete candidate. Do not
automatically delete, replace, promote or repeatedly fetch on a failure.

The candidate contains an earlier full-document snapshot. Before manually
merging its betting fields, re-read current data and reconcile concurrent
changes; never overwrite the entire current document from the candidate.
Then run the usual structural check, freeze the final current bytes, obtain a
new independent SHA-bound PM review, and use the established publication gate.
Candidate creation, unit-test success and this code review are not approval
to publish market data or to push/merge this development change.

The browser's separate `app.js` live-odds path is outside this patch. It still
needs its own review and frontend verification; this helper does not establish
end-to-end display correctness.

Offline tests: `node --test scripts/test_fetch_betting.mjs`. They block
unmocked fetching and use isolated temporary directories for file tests.
