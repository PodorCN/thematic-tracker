# Macro Pages Data Operations and LLM Handoff

This runbook covers the two public macro pages:

| Page | Staging or raw input | Published data |
|---|---|---|
| Global Economic Calendar | `economic-calendar/raw/<date>/economic_calendar.json` | `economic-calendar/data/` |
| Fed/BOC Watcher | `fed-boc-watcher/data/dashboard.json` | `fed-boc-watcher/data/` |

The canonical publication contract is
[`docs/PUBLIC_PAGES_BACKEND_SPEC.md`](PUBLIC_PAGES_BACKEND_SPEC.md).
The detailed schemas are
[`docs/ECON_CALENDAR_API_SPEC.md`](ECON_CALENDAR_API_SPEC.md) and
[`fed-boc-watcher/BACKEND_DATA_SPEC.md`](../fed-boc-watcher/BACKEND_DATA_SPEC.md).

## Current Automation Boundary

- `scripts/econ/fetch_calendar.py` collects the Economic Calendar from FxStreet,
  with ForexFactory as its fallback.
- `scripts/econ/render_calendar.py` validates fetched JSON and publishes only `economic-calendar/data/archive/<date>.json`, `data/latest.json`, and `data/dates.json`. The fixed `index.html` reads these in the browser; the job must not generate dated HTML.
- `scripts/econ/archive_fed_boc.py` validates and publishes an existing Fed/BOC
  staging payload.
- There is currently no Fed/BOC collector. An operator or web-enabled LLM
  must research and update `fed-boc-watcher/data/dashboard.json` before it is
  archived.
- `.github/workflows/macro-pages-daily.yml` runs daily at `13:10 UTC` and
  publishes only the deterministic economic calendar. It deliberately cannot
  publish Fed/BOC because that output requires the independent PM review gate.
- What that workflow commits to `main` is what goes live: GitHub Pages serves
  this repository directly, with no sync step and no mirrored copy.

## Independent PM Review Gate

After updating `fed-boc-watcher/data/dashboard.json`, but before running
`scripts/econ/archive_fed_boc.py`, follow
[`fed-boc-watcher/PM_REVIEW_GATE.md`](../fed-boc-watcher/PM_REVIEW_GATE.md):

1. Before collecting anything, read `fed-boc-watcher/review/feedback/latest.json` if
   it exists. An `open` feedback record is a mandatory collection plan, not an
   optional note: re-trigger every affected source and address every finding.
2. Freeze the proposed payload under
   `fed-boc-watcher/review/<TODAY>/iteration-<NN>/candidate.json` and record its
   SHA-256 in `candidate.sha256`.
3. Launch a **separate agent session** as the independent portfolio manager.
   The collecting/operator agent may not review or approve its own candidate.
4. The PM writes `pm-review.json` matching
   `fed-boc-watcher/review/pm-review.schema.json` and bound to the candidate digest.
5. Run `scripts/econ/validate_pm_review.py` against the candidate and review with
   `--require-approved`.
6. A `revise` verdict, failed check, material finding, missing review, or hash
   mismatch forbids archive, commit, sync, and push. First run
   `scripts/econ/record_pm_feedback.py` to persist the rejection as latest + immutable
   history. Then re-trigger affected collection, follow every PM instruction,
   rebuild the whole candidate, freeze a new iteration, and request a fresh
   independent review.
7. Allow at most three iterations per run. If none is approved, fail closed,
   leave the previous public `latest.json` untouched, and carry the open
   feedback into the next cron run.
8. Only the exact candidate with a passing `approved` review may proceed to
   archive/publication. Commit its approved review folder and feedback history
   as audit evidence.

The PM review is a hard publication gate, not editorial commentary. Never turn
“approved if fixed” into approval, and never edit the PM's review artifact.

## Manual Daily Run

Run from the repository root. On Windows, use the repository virtual
environment explicitly:

```bash
# Run from the repository root; resolve YYYY-MM-DD in America/Toronto.
uv run --isolated --python 3.11 --with-requirements requirements.txt python scripts/econ/fetch_calendar.py --date YYYY-MM-DD --days 7 --countries US,CA,EMU,DE,FR,IT,ES,UK,CH --impacts HIGH,MEDIUM --with-history --history-events 15 --history-limit 12
uv run --isolated --python 3.11 --with-requirements requirements.txt python scripts/econ/render_calendar.py --date YYYY-MM-DD
# Stage only these paths, then run the scope gate before a data commit:
git add economic-calendar/raw/YYYY-MM-DD/economic_calendar.json economic-calendar/data/latest.json economic-calendar/data/dates.json economic-calendar/data/archive/YYYY-MM-DD.json
python scripts/econ/verify_data_only_changes.py --product economic-calendar --staged
```

The published page and legacy HTML archive must remain unchanged; use a clean worktree for a manual replay. With no explicit `--from`, the fetcher includes the Toronto day before the target date and a seven-day window from that date.

Then research and update `fed-boc-watcher/data/dashboard.json`. Do not use the
example payload as current data. Freeze it, obtain a separate approved PM
review as described above, and provide both paths to the hard-gated archiver:

```bash
uv run --isolated --python 3.11 --with-requirements requirements.txt python scripts/econ/archive_fed_boc.py --date YYYY-MM-DD --input fed-boc-watcher/data/dashboard.json --candidate fed-boc-watcher/review/YYYY-MM-DD/iteration-01/candidate.json --pm-review fed-boc-watcher/review/YYYY-MM-DD/iteration-01/pm-review.json
uv run --isolated --python 3.11 --with-requirements requirements.txt python -m pytest tests/test_econ_render.py tests/test_fed_boc_archive.py tests/test_data_only_release.py -q
# Pinned render acceptance is a required publish step, not optional: unpinned
# runs skip the candidate-acceptance assertions by design.
FED_BOC_RENDER_CANDIDATE="$PWD/fed-boc-watcher/review/YYYY-MM-DD/iteration-01/candidate.json" uv run --isolated --python 3.11 --with-requirements requirements.txt python -m pytest tests/test_render_truthfulness.py -q
```

Only after the independent PM review and tests pass: stage the approved Fed/BOC JSON and that iteration's candidate, digest and reviewer-written review; run `python scripts/econ/verify_data_only_changes.py --product fed-boc-watcher --staged`, then verify `--range origin/main..HEAD` immediately before pushing. A review log or operator-transcribed review is not independent approval.

Review only the relevant output paths before publishing:

```text
economic-calendar/raw/<date>/economic_calendar.json
economic-calendar/data/{latest,dates}.json
economic-calendar/data/archive/<date>.json
fed-boc-watcher/data/latest.json
fed-boc-watcher/data/dates.json
fed-boc-watcher/data/archive/<date>.json
fed-boc-watcher/review/<date>/iteration-<NN>/candidate.json + candidate.sha256 + pm-review.json
# index.html and economic-calendar/archive/*.html MUST remain unchanged on every daily run
```

## Publishing

This repository publishes itself. GitHub Pages serves it from `main` at the
root, and because `PodorCN.github.io` carries the `podor.org` custom domain,
this project site is served under that same domain:

| Page | Public URL |
|---|---|
| Global Economic Calendar | `https://podor.org/thematic-tracker/economic-calendar/` |
| dated calendar snapshot | `https://podor.org/thematic-tracker/economic-calendar/?date=<date>` (reads `data/archive/<date>.json`) |
| Fed/BOC Watcher | `https://podor.org/thematic-tracker/fed-boc-watcher/` |

There is **no sync step and no second copy**. Nothing is mirrored into
`PodorCN.github.io`; that site only links here. This matters when you change a
page: what you merge to `main` is what goes live, about a minute later.

To publish: commit the intended snapshots to a branch, merge to `main`, then
confirm the live page directly — request `<page>/data/latest.json`, check
HTTP 200 and its `snapshot_date`, then open the page itself. Roll back with
`git revert`.

> **Never publish these.** They live inside the page folders but must stay off
> the public site's radar as data, not as pages: `fed-boc-watcher/review/`
> (the PM review evidence chain), `fed-boc-watcher/data/dashboard.json` (the
> staging payload, by definition not yet PM-approved), and
> `economic-calendar/raw/` (fetch-stage intermediates). They are committed here
> for provenance and are reachable by URL like any other file in a Pages repo —
> so never link to them, and never treat `dashboard.json` as published data.

## Fed/BOC Collection Rules

1. Read the current payload before editing it and preserve its schema and
   stable driver IDs where the underlying event has not changed.
2. Use authoritative or direct sources where possible: Federal Reserve and
   Bank of Canada for meetings and decisions; BLS, BEA, and Statistics Canada
   for releases; CME FedWatch and an identified OIS source for market pricing;
   structured market data such as yfinance for the validation strip.
3. Every driver must have a verifiable source and `source_url`, plus a one-line
   plain-English `summary` (for example "Job market is cracking: payrolls went
   negative, far below forecast."). Keep Actual, Forecast, and Previous
   distinct. Do not infer or invent missing values.
4. Reuse the freshly collected `economic-calendar/raw/<date>/economic_calendar.json` for
   upcoming releases when possible instead of transcribing the same events
   from search results.
5. Change `as_of` only after the payload has actually been refreshed and
   verified. A refresh can be current when official policy records/rates plus
   clearly labelled exchange-traded futures proxies and market validation are
   current, even if direct CME FedWatch or single-meeting OIS access is
   unavailable; disclose those probability limitations locally instead of
   marking the entire snapshot stale. Retain the prior timestamp and publish
   `stale: true` only when the snapshot's core observations could not be refreshed.
6. Meeting probabilities must be in `[0, 1]` and total approximately `1` for
   each bank. Driver weights must be in `0.5` increments from `0` to `3`, with
   most values in the `1.0` to `2.0` range. Do not use `2.5+` without unusually
   strong evidence.
7. Do not alter page design, archived dates other than the requested date, or
   unrelated working-tree files. Commit and push only when the assignment
   explicitly includes publication, as the prompt below does.

## Copy-Paste LLM Assignment

Use this prompt with a model that has web access and repository tools:

```text
Work as the daily data operator for the two public macro pages in this
repository. Do not redesign the pages.

Before changing anything, read:
- agent.md（仓库总协议）
- docs/MACRO_DATA_OPERATIONS.md
- docs/PUBLIC_PAGES_BACKEND_SPEC.md
- docs/ECON_CALENDAR_API_SPEC.md
- fed-boc-watcher/BACKEND_DATA_SPEC.md
- the current fed-boc-watcher/data/dashboard.json

Target Toronto snapshot date: YYYY-MM-DD.

Tasks:
1. Run the documented econ/fetch_calendar.py command for the target date and
   then econ/render_calendar.py. Confirm the event count matches events.length,
   timestamps are valid UTC ISO 8601 values, history is chronological, and the
   JSON contains no NaN or Infinity.
2. Research current Fed and Bank of Canada meeting dates, policy pricing,
   macro drivers, market validation prices/returns, and upcoming relevant
   releases using authoritative live sources. Update only
   fed-boc-watcher/data/dashboard.json. Include source URLs, preserve Actual vs
   Forecast vs Previous, and do not fabricate unavailable data.
3. Apply the weight, probability, timezone, and freshness rules in
   fed-boc-watcher/BACKEND_DATA_SPEC.md. Prefer the freshly fetched economic-calendar
   archive for the watcher calendar. Update as_of only when the payload has
   been genuinely refreshed and verified.
4. Freeze the exact candidate, request the independent portfolio manager review and wait for the reviewer-written `pm-review.json`. A `revise` or missing review stops this run; do not archive or push. On approval, archive with `--candidate` and `--pm-review`; then stage only the approved data JSON and audit files, run `verify_data_only_changes.py --product fed-boc-watcher --staged`, and run the tests.
5. Inspect the staged diff. Frontend HTML, scripts and other products' data are forbidden in a data release; frontend fixes are separate PRs with a revised `frontend_contract.json`, browser tests and independent code review.
6. Publish only the approved data commit to `main` under the repository's branch rules, then compare the live `data/latest.json` to the reviewed candidate (allowing the three archiver fields) and inspect the real browser. A successful Git push or HTTP 200 is not a visual or fact check.

Report the changed files, exact source URLs and observation times, validation
results, and any values that could not be independently verified. If a
required source is unavailable, preserve the previous confirmed data and
report the snapshot as stale rather than guessing.
```

Replace `YYYY-MM-DD` before assigning the task. The LLM should return its
sources and unresolved gaps in addition to modifying the files; a successful
script exit alone does not prove the researched values are correct.
