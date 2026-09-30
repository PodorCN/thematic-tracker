# Fed/BOC Portfolio Manager Review Gate

The Fed/BOC watcher is not publishable immediately after collection. A separate
review agent must assess the frozen candidate as a portfolio manager whose own
portfolio and P&L depend on the page being correct.

## Role separation

- **Operator agent:** collects and assembles the candidate payload. It may not
  approve its own work.
- **PM reviewer agent:** receives a frozen candidate and evidence, challenges
  every material claim, and writes only the structured review artifact.
- **Publisher:** may archive, commit, sync, or push only after the review gate
  validates an `approved` verdict bound to the exact candidate bytes.

The PM reviewer is independent and time-constrained. It must be skeptical,
direct, and specific. It does not reward effort. It asks whether it would risk
real capital based on this snapshot.

## Frozen artifacts

For Toronto date `YYYY-MM-DD` and iteration `NN`:

```text
fed-boc-watcher/review/YYYY-MM-DD/iteration-NN/
  candidate.json
  candidate.sha256
  pm-review.json
```

`candidate.json` is an exact copy of the proposed
`fed-boc-watcher/data/dashboard.json`. Once sent for review it is immutable.
`candidate.sha256` contains its SHA-256 digest. `pm-review.json` must cite that
same digest. These review folders are durable audit evidence and are committed
with an approved publication.

## PM review mandate

The reviewer must independently check, not merely summarize:

1. Fed and BoC meeting dates, last decisions, target rates, vote/dissent text,
   and next-decision labels against official sources.
2. Every probability sums to approximately 1, is internally consistent with
   rates/futures, and is labelled as direct pricing versus a proxy. A
   multi-meeting quarterly contract must not be presented as a clean
   single-meeting probability.
3. Every driver belongs on the correct dovish/hawkish side, has a current,
   traceable source, separates Actual/Forecast/Previous, and has a weight
   proportional to evidence and market relevance.
4. Dates, timezone offsets, release chronology, units, signs, basis points,
   percentages, and cross-field statements agree.
5. Market-validation moves match the claimed transmission mechanism. Correlation
   is not presented as causation.
6. Stale, duplicated, superseded, contradictory, or low-signal items are removed
   or clearly qualified.
7. The top-level `as_of`, nested observation times, version, snapshot date, and
   freshness claim are mutually consistent.
8. The output is decision-useful: what changed, why it matters, what is priced,
   what could falsify the view, and the largest P&L risks are clear without
   wasting the PM's time.

The reviewer must use tools to inspect official/current sources where needed.
It must never approve based solely on the operator's verification note.

## Verdict contract

The reviewer writes `pm-review.json` matching
`fed-boc-watcher/review/pm-review.schema.json`.

- `approved`: no unresolved `critical` or `major` finding; the candidate is safe
  to publish as a decision-support snapshot. Findings may contain only minor
  presentation observations.
- `revise`: one or more material problems exist. Every finding must identify the
  field, evidence, why it affects a trading decision/P&L, and an executable
  instruction to the operator.

Approval must not be conditional. “Approved if fixed” is `revise`.

## Revision loop

1. Operator freezes iteration 01 and launches a separate PM reviewer.
2. Run `scripts/econ/validate_pm_review.py --candidate ... --review ...`.
   Then run the pinned render acceptance before any archive:
   `FED_BOC_RENDER_CANDIDATE=$PWD/fed-boc-watcher/review/YYYY-MM-DD/iteration-NN/candidate.json
   uv run --isolated --python 3.11 --with-requirements requirements.txt python -m pytest
   tests/test_render_truthfulness.py -q` — unpinned runs skip the candidate
   assertions by design, so an unpinned green run is not acceptance.
3. If verdict is `revise`, publication is forbidden. Immediately run
   `scripts/econ/record_pm_feedback.py --candidate ... --review ...`; this atomically
   updates `fed-boc-watcher/review/feedback/latest.json` and appends an immutable
   history record. The operator then follows every instruction, re-triggers
   collection for every affected source/claim, rebuilds the whole internally
   consistent candidate, and freezes iteration 02.
4. A fresh PM reviewer reviews iteration 02 from scratch. The operator may not
   edit or reinterpret the prior verdict into approval.
5. At the beginning of every later cron run, read
   `fed-boc-watcher/review/feedback/latest.json` before any collection. If its status is
   `open`, every required recollection and operator instruction is mandatory;
   a normal incremental refresh is not sufficient. Include the feedback and a
   remediation/evidence mapping in the next PM handoff so the reviewer can
   detect repeat failures.
6. Repeat until approval, with a maximum of 3 iterations per scheduled run.
   Exhaustion fails closed and leaves the prior public/latest output untouched;
   the open feedback remains mandatory on the next run.
7. On approval, run the validator with `--require-approved`, then archive,
   test, commit, sync, push, and verify the live artifact.

A failed or missing reviewer, malformed artifact, digest mismatch, or stale
approval always blocks publication.


---

# Reviewer Playbook (learned 2026-09-28, four rounds)

Everything above is the mandate. This section is what a reviewer actually needs to
avoid wasting a round. Each item below is a real cost the reviewer or the operator
paid in this project.

## Your first obligation: the artifact must exist on disk

- **Write `pm-review.json` yourself, as your first-class deliverable, before you
  return your final message.** Do not rely on the operator transcribing your
  verdict — a review whose file was never written is not a review.
- Verify the file you just wrote parses and that its `candidate_sha256` equals
  `candidate.sha256` byte-for-byte. If you run low on tool budget, drop
  lower-value checks and **keep the write**.
- Never report "approved" in prose while leaving the artifact unwritten. The
  operator is not allowed to transcribe it (see operator AGENT.md §9).

## Use the exact schema — no invented field names

The validator (`scripts/econ/validate_pm_review.py`) enforces a fixed shape. Before
writing, read `fed-boc-watcher/review/pm-review.schema.json`. The rules that bite:

- Top-level keys are exactly: `schema_version`, `reviewer_role`, `reviewed_at`,
  `candidate_sha256`, `verdict`, `executive_summary`, `checks`, `findings`,
  `pnl_risks`, `operator_instructions`.
- `checks` has exactly six keys, spelled exactly:
  `official_policy`, `pricing`, `drivers`, `market_validation`, `freshness`,
  `decision_usefulness`. **Do not rename or substitute these** — a faithful but
  differently-named file wastes the whole round and costs the operator a manual
  rewrite.
- Each finding has exactly six keys: `severity`, `field`, `issue`, `evidence`,
  `pnl_impact`, `instruction`.
- `approved` may **not** carry `operator_instructions` (it must be empty). Put
  anything you need the operator to know in `executive_summary`.
- `revise` findings must be executable: name the field, the evidence, why it
  moves P&L, and the concrete change.

## Distinguish your verdict from the machine's

The operator may have run the structural gate, but its output is not your verdict.
You are the independent check; do not rubber-stamp it. Conversely, **if the
structural gate itself is wrong, say so explicitly** — during this round the
operator's own `evidence_contains_claim` check produced a false positive that led
to a self-contradictory page. A reviewer who spots a broken check is doing the
job correctly; a reviewer who trusts a machine's false positive is not.

## A review that only says "revise" without a location is wasted

Every finding must carry a concrete, greppable location: a JSON path
(`drivers.fed.dovish[0].actual`), an evidence filename, a live URL, or an exact
quoted string. Round 2's blocking finding named the field, quoted the offending
`grep` output, and even supplied a fallback instruction — that is the standard.

## Fresh review each round; carry forward nothing but open items

- Review the frozen bytes of the candidate you were given. Never review a
  description of it, and never assume a prior approval carries forward.
- Read `fed-boc-watcher/review/feedback/latest.json` and confirm every open
  operator instruction is actually resolved in the new candidate. Say so
  explicitly in `executive_summary` (e.g. "the previously flagged X is now bound
  to Y"). A reviewer that doesn't check the feedback is why the same defect
  survives three rounds.

## Severity discipline

- `critical`/`major` = a number that is wrong, a conclusion that is wrong, an
  unsupported claim presented as fact, or a self-contradictory page. Block.
- `minor` = wording, naming, counting nits, unsourced-but-true superlatives,
  tests that should be pinned to a specific candidate. **Do not block on these**;
  say "next natural rebuild" and move on. Over-strict reviewers burn operator
  budget and get their real findings ignored.
- "Approved if fixed" is `revise` — but a *fixable minor* is not. Distinguish
  "this is wrong" from "this could be tidier."

## Scope discipline

State exactly what you approved. An approval binds one candidate's SHA-256; it
never covers a newer candidate that a scheduled run produced afterward. If a newer
candidate exists, say in `executive_summary` that it is not covered.

## Decide with real capital in mind

The question is never "is the writing clear" — it is "would I size a position off
this page, and what would cost me money." Check the actual sources (official
statements, exchange data), verify the displayed numbers against the bound
evidence, and only then judge the narrative.
