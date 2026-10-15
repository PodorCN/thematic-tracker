# General Theme Tracker: autonomous research playbook

## Mission and completion states

Maintain a small, evidence-backed account of what is being repriced, why it
matters, how to track it, and what would invalidate it. Discover new themes as
well as maintaining existing ones. A theme is a persistent, testable change in
market expectations; a headline or a rising ticker alone is insufficient.

This procedure governs `general-theme-tracker/`, not the legacy bank/software
trackers, economic calendar, or Rates Decisions product. Read `AGENT.md`, the
schema, and the shared review doctrine first. Existing content is a starting
hypothesis, never evidence. Use the tools available in your environment to
research, calculate, write and verify without asking the user for routine choices.

Finish in exactly one truthful state:

| State | Required evidence |
| --- | --- |
| Ready for independent review | Current source YAML, successful schema/bundle checks, frozen candidate and hash, structural flags, accessible research evidence and handoff |
| Published | All of the above, independent APPROVED review, successful publisher, byte-identical archive/latest, and verified deployed date/hash when deployment is authorized |
| Incomplete; not published | Specific missing data/tool/source, attempts made, affected fields, preserved last approved snapshot, and the next executable action |

Do not call a run complete because the prose sounds persuasive or a validator
exits successfully. Never claim publication from a local file write.

## 1. Establish the run before collecting

1. Inspect the branch and working tree. Preserve unrelated edits. Use a clean
   checkout for a data release; layout, instructions and research updates ship
   separately. Record the starting commit and hash of `data/latest.json`.
2. Read the most recent published bundle, its week and snapshot date, every
   existing theme, previous review findings and the commentary library.
3. Determine today's **Toronto** date and ISO week, and the latest completed
   session separately for each relevant exchange. Use an exchange calendar;
   include holidays, half-days and daylight saving. A current snapshot date does
   not make old market observations fresh. Never include a still-open daily bar.
4. Pin the intended week explicitly in commands. If creating a new week, carry
   forward stable theme IDs and `created_at`, update every `week`, create matching
   market/commentary YAMLs and reassess every copied fact. Never silently use the
   lexicographically newest old directory as today's research.
5. Create an evidence workspace outside the release checkout (or an ignored local
   directory). Store raw responses, retrieval metadata, calculations, the coverage
   log and final handoff there. Share its exact path with the reviewer. The data
   release allow-list does not accept arbitrary evidence/report files; do not
   weaken the gate to bundle them. Never store credentials in evidence.

Set `RUN_DATE`, `WEEK`, `AS_OF` and `EVIDENCE_DIR` in your run notes. Use the real
current date, not a date copied from an example or historical candidate.

## 2. Discover candidates and revisit the entire watchlist

On every run scan changes since the **last published observation**, not just
the last 24 hours. Daily: official releases, material company news, price/breadth
changes and due catalysts. Weekly: repeat the broader commentary/discovery sweep.

| Coverage | Starting sources and questions |
| --- | --- |
| US growth, inflation and policy | Fed, BLS, BEA, Treasury; what changed versus expectations? |
| Canada | BoC, Statistics Canada, bank IR and TSX; policy, credit and earnings transmission? |
| Cross-asset | Equities, rates, FX, energy and gold; common driver or unrelated movements? |
| Industry/company fundamentals | Issuer IR, filings, guidance, product/industry releases; does the evidence change cash-flow expectations? |
| Institutional disagreement | Goldman Sachs, BofA, Morgan Stanley, JPMorgan, Deutsche Bank, BMO, RBC and TD public commentary; where do views conflict? |
| Independent reporting | Original reporting from reputable newsrooms; what corroborates or contradicts the primary record? |

Search for the dated release or full article, open it, and record what it
actually supports. Search snippets, AI answers and old theme files are discovery
aids only. Do not invent access to a paywalled bank note. Log inaccessible sources,
the attempt and any public substitute; label secondary quotations as secondary.
Two syndications of one Reuters story count as one source, not two opinions.

Build a candidate ledger with: proposed ID, repricing claim, first/last evidence
dates, liquid proxy, benchmark, confirming evidence, counterevidence, catalyst,
five scoring flags, and include/reject/watch reason. Test at least one plausible
alternative explanation for each retained theme (broad beta, rates, FX, commodity
exposure, concentration or positioning). Keep rejected ideas in the evidence
workspace so the next agent understands why they were excluded.

Target 3-7 useful themes. Do not manufacture a third theme or a fifth score point
to reach a quota. If fewer than three qualify, report the shortfall; unresolved
coverage is preferable to promoting noise. Every existing ID must be accounted
for as continued, changed, faded or dead, with a factual reason. Preserve dead
themes in history; do not delete them to improve the page's appearance.

## 3. Collect market observations and calculate, never estimate

For every retained theme collect the primary proxy, benchmark, sufficient history
for 1W/1M/YTD, rebased series, and volume/breadth evidence needed by the score.
Also refresh all market-strip instruments at a clearly identified observation
time. Do not combine intraday commodity/FX quotes with equity closes under an
unqualified common close timestamp. Keep source times and conventions explicit.

Evidence per request must include provider, full URL/request parameters, ticker,
retrieved-at UTC, observed-at UTC, exchange/timezone, currency, adjustment mode,
raw response/file and any provider delay. Save failed requests too. Use one
documented price provider for calculations; cross-check material discrepancies
against an issuer/exchange or a second independent provider.

Use bounded requests: a timeout, at most three attempts per source with increasing
backoff, respect Retry-After, then a documented alternative source. Do not loop
indefinitely or erase good published data when one provider fails.

### Return convention and exact anchors

Use numeric percentages (`2.5` means 2.5%), and percentage points for excess.
Calculate with full precision; round only for display.

```text
return_pct = 100 * (close_end / close_anchor - 1)
excess_pp = proxy_return_pct - benchmark_return_pct
rebased_t = 100 * close_t / close_first_common_session
```

Use the latest completed **common** session for proxy/benchmark comparisons.
For 1W use the same calendar weekday one week earlier; for 1M use the same calendar
date one month earlier (clamp month-end); if an anchor is not a session, use the
last available common session on or before it. YTD uses the last common session
of the previous calendar year, not a hard-coded December 30. Save the actual
anchor dates and closes for all six returns so another agent can reproduce them.
Do not compare a Monday proxy close to a Friday benchmark close without disclosure.

For `return_type: price`, prefer split-adjusted, dividend-unadjusted prices; for
`total_return`, use a documented reinvestment-adjusted series. Yahoo Adjusted Close
can incorporate distributions: do not silently label it Price Return. If only
mixed conventions are available, disclose precisely and raise the comparability
issue to the reviewer; never hide it behind a generic source label. Explain
currency differences and any FX treatment. These explicit rules supersede old
prompt examples that hard-code Dec 30 or call adjusted closes Price Return.

Before accepting a series check: strictly ascending unique sessions, finite
positive prices, no future dates, consistent adjustment basis, first rebased
points 100, matching date coverage, and last observation matching `as_of_utc`.
Missing sessions require a documented calendar/provider explanation; no invented
interpolation. Retain sufficient daily history even when the displayed chart
uses weekly points. Reconcile excess within 0.2pp (aim for <0.01pp before rounding).

For volume confirmation compare the latest completed session's volume with the
preceding 20 completed sessions, excluding the current one. Record the formula,
window and threshold before scoring. Missing volume cannot count as confirmation.
For breadth name the >=3 stocks or >=2 sub-industries and save their observations.

### Event timing and attribution

Each event needs real `event_time_utc`, source, direct HTTPS URL, `proxy_ret`,
`benchmark_ret`, and the same `return_window`. Store event time, article publication
time and retrieval time separately in evidence. Do not manufacture midnight UTC
when a source gives only a date. Search the primary release; if the actual event
time remains unknown, omit that event from production and report the gap.

An intraday/pre-open release can use event-day close versus prior close. For an
after-close, weekend or holiday event, use the first session **after the event
became public**, label the window explicitly and save its dates. Do not attribute
a close to news published after that close. A benchmarked same-day move is an
observation, not proof of causality. Use "consistent with" for inference; if the
driver cannot be established, say so instead of inventing an explanation.

## 4. Decide what survives and what would falsify it

Use the five boolean fields in `theme_vs_noise`, each with a field-level evidence
reference in the ledger. `score` is exactly the count of true flags.

| Flag | Pass evidence |
| --- | --- |
| persistence | More than two weeks of dated evidence, or two independent commentaries |
| breadth | Named >=3 stocks or >=2 sub-industries with observed participation |
| volume_confirm | Measured relative price confirmation and expanding volume, with window/threshold disclosed |
| falsifiable_catalyst | A future verified checkpoint with a measurable supporting and invalidating outcome |
| repricing_logic | Prior expectation, new evidence, and the resulting change in expected cash flows/discount rate |

Price confirmation must reflect the **stated direction** of the thesis. A rising
yield thesis may be represented by falling TLT; explain the inverse relation and
trade direction. Keep the displayed TLT returns unchanged. Negative TLT-SPX
excess is not automatically a failed rates thesis, and a high score is not a
probability or investment recommendation.

Use Emerging for a qualifying early idea, New for a newly confirmed theme,
Continuing for intact evidence, Fading for weakening evidence, and Dead for a
specific falsifier or completed thesis. Write the observed transition and why.
Do not force a linear promotion path: new contradictory evidence can immediately
kill a theme. Below three points, do not promote to New/Continuing; retain the
idea in the watch ledger or mark an existing theme Fading/Dead as appropriate.
Schema has no Draft/Noise enum: never invent one in production YAML.

Conviction must follow evidence quality, independence, breadth and counterevidence;
it is separate from the mechanical score. Verify each proxy's current issuer fee,
liquidity and tracking gap. An index is a reference, not directly tradable; explain
the instrument used to express it. A basket needs weights/rebalancing rules.

Revisit every past-due catalyst: record the observed result as a sourced event,
reassess status and remove/replace it in `depends_on`. Future dates require an
official calendar or issuer announcement; identify estimates explicitly. Bull
and bear labels describe asset outcomes; separately explain which outcome
confirms the theme when its direction is bearish. Never present an already
released CPI or completed earnings date as the next checkpoint.

## 5. Write the production YAML, not the webpage

Use the actual snake_case fields in `data/schema/theme.schema.yaml`; do not copy
informal camelCase/uppercase spellings from old prose. All output is English.
Keep IDs stable and use only supported statuses, event types and horizons.

| Field/output | Acceptance |
| --- | --- |
| `status_note` | One line: what changed since the previous snapshot and why; obey schema length |
| `summary` | <=100 words: observed trigger, proxy vs benchmark with period, consequence |
| `chain` | 3-5 chronological steps; `when` <=20 characters; label <=12 words; detail <=30 words; dates/claims already supported in events/body; final step = current state |
| `body_text` | <=200 words: what happened, prior expectation, marginal change, competing explanation, so what, next test |
| Body + explainer | <=500 words combined; define technical terms and return convention in the folded explainer |
| `performance`, `series` | Reproducible observations, dates, source and benchmark rationale; no hand-entered approximations |
| `events` | Every item has source URL/time and two comparable returns; duplicates merged |
| `depends_on` | At least one future checkpoint; verified date, why it matters, measurable support/falsifier |
| Market/commentary | Same week and coherent as-of; real source library plus factual yesterday-to-today diff |

One claim-to-evidence record is required for **every material numeric or causal
claim**, including claims inherited from the previous run:

```text
field: themes[<id>].events[<index>].title
claim: <exact factual assertion>
source_url: <direct source>
source_published_at_utc: <actual publication time, if known>
event_observed_at_utc: <actual event time>
retrieved_at_utc: <retrieval time>
capture_path: <saved response or excerpt>
calculation_path: <script/output and inputs, if derived>
classification: primary fact | secondary report | analyst inference
counterevidence: <link/observation or explicit search result>
```

Do not claim an IR release, Fed, BoC, BLS or StatCan primary while linking only
to a broker/blog retelling. Label secondary reporting and lower confidence.
If you cannot verify an inherited fact, remove or qualify it; do not launder it
through a new `updated_at`. Never update `as_of_utc` without new observations.

## 6. Validate, freeze and hand off

Run from `general-theme-tracker/`. Use the available Python 3 executable (`python`
or `python3`); set `PYTHON` below to that interpreter. Install locked Node
dependencies with `npm ci` if missing. `<WEEK>` is the ISO week chosen in step 1.
On Windows use Python's `-X utf8` option (shown below) to avoid console encoding
errors. Install repository Python dependencies from `../requirements.txt` if
missing. Placeholders below are instructions to substitute, not literal shell
commands; in PowerShell use `&` before a quoted interpreter path.

```text
npm run validate
<PYTHON> -X utf8 scripts/publish.py --check --week <WEEK>
<PYTHON> -X utf8 scripts/freeze.py --week <WEEK>
```

Zero schema/bundle errors is necessary. Read every warning and structural flag;
do not treat warnings as permission. Check the real clock: the ideal freshness
limit is 48h and >7 days is a machine blocker. Weekend/holiday exceptions require
an explicit independent reviewer disposition with exchange-calendar evidence;
do not move observation timestamps to pass. When the rule cannot be met, retain
the last approved snapshot, finish the source work and report the blocker.

Freeze writes today's Toronto review directory. Candidate bytes then stay
unchanged. Give an **independent named reviewer** the following, not merely a
request to "approve":

1. Starting commit, run date/week and exact frozen candidate path/hash.
2. Candidate, `candidate.sha256`, `structural-flags.json` and prior open findings.
3. Evidence directory, coverage/rejection ledger, reproducible return inputs and
   commands, claim-to-source map, and all data-access/freshness limitations.
4. Status-transition table for every previous theme; competing explanation for
   each active theme; catalysts consumed and replaced.
5. The shared `scripts/review/REVIEWER_AGENT.md`, this product's review annex,
   and the six mandatory checks.

The reviewer independently opens material sources, recalculates returns and
scores, dispositions every structural flag, and writes `pm-review.json` plus
`review.md`. Changing identity text is not independence. The operator must never
create its own approval. If no independent reviewer is available, leave a
review-ready handoff and report that publication is pending.

On REVISE fix the source, preserve prior findings/candidate evidence, re-freeze
with `--force` only after archiving the prior review outside the release checkout,
and obtain a new SHA-bound review. After two unsuccessful revision rounds, stop
publication and list unresolved findings; never lower a threshold to get a pass.

Only after independent approval and within the authorized publishing scope:

```text
<PYTHON> -X utf8 scripts/check_review.py
<PYTHON> -X utf8 scripts/publish.py
<PYTHON> -X utf8 ../scripts/econ/verify_data_only_changes.py --product general-theme-tracker --working-tree
```

Publisher requires all six checks `pass`, verdict `APPROVED`, zero critical/major
findings, complete flag coverage and matching rebuilt/frozen/review SHA. It writes
the archive/latest from the exact reviewed bytes. Do not hand-edit those JSONs.
Commit only allowed data/review paths. After a permitted push/deployment, request
the public `data/latest.json` and confirm SHA/date/week against the reviewed
candidate, then inspect the page, its banner, theme board, checkpoints and source
links. A green build without the correct public data is not deployment acceptance.

## 7. Final acceptance checklist and run report

- [ ] Every existing theme accounted for; discovery sweep and rejected ideas logged.
- [ ] Material claims traceable to opened sources; no invented times, figures or access.
- [ ] Proxy/benchmark six returns reproduced from saved closes and anchor dates;
      chart and market strip coherent; no price/total-return ambiguity hidden.
- [ ] All five flags justified separately; score recomputed; counterevidence tested.
- [ ] Every event benchmarked in a valid time window; no after-close causal reversal.
- [ ] Past catalysts resolved; next checkpoints future, sourced and falsifiable.
- [ ] Content English, concise, jargon explained; chain/summary/body mutually consistent.
- [ ] Schema and whole-bundle checks pass; every flag explicitly dispositioned.
- [ ] Independent review approved the exact SHA before publication (or pending reported).
- [ ] Release contains no frontend/instructions changes; published bytes match review.
- [ ] Public verification done if deployed; freshness accurately visible.

End each run with this compact report; use PASS / FAIL / PENDING per item:

```text
Outcome: review-ready | published | incomplete, not published
Run: Toronto date, ISO week, starting commit, observation cutoffs by exchange
Coverage: sources opened / unavailable; candidates considered / rejected
Theme changes: ID, old -> new status, one-sentence evidence, next falsifier
Data: provider, return convention, anchor dates, missing observations
Checks: exact commands, exit results, outstanding flags/findings
Review: reviewer identity, verdict, candidate SHA and evidence/handoff paths
Publication: local archive/latest SHA; deployed URL/date/SHA if verified
Next action: exact task, owner/role and blocking dependency (if any)
```

Do not schedule a recurring job, publish, or message another chat merely because
this document describes those capabilities. Execute the authorized run; preserve
the handoff so a later agent can continue without reconstructing your reasoning.
