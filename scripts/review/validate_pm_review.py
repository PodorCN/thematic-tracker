#!/usr/bin/env python3
"""Machine-checks an independent PM review. Shared by all trackers.

Checks (structure + hashes + severity math only, no prose matching):
  - review parses; has exactly the schema top keys; checks has exactly the
    product-declared keys passed via --checks (comma-separated)
  - candidate_sha256 == sha256(candidate file BYTES)
  - candidate.snapshot_date == review.snapshot_date
  - reviewer != operator, neither banned/placeholder
  - verdict/severity/checks coherence:
      APPROVED => zero critical/major findings AND all checks pass
      REVISE   => at least one critical/major finding OR one failed check
  - every finding has field + issue + evidence with a verifiable pointer
  - if --flags given: every machine flag (code+field) is dispositioned
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from review.core import (
    BANNED_IDENTITIES, DISPOSITIONS, SCHEMA_VERSION, SEVERITIES, TOP_KEYS,
    VERDICTS, norm_identity, sha_hex,
)

_EVIDENCE_POINTER = re.compile(
    r"https?://|candidate\.|drivers\.|meetings\.|calendar|pm-review|"
    r"[\"'][^\"']{3,}[\"']|\d{4}-\d{2}-\d{2}|\d+\.\d+%?"
)


def validate(candidate_path: Path, review_path: Path,
             flags_path: Path | None, expected_checks: list[str],
             require_approved: bool) -> list[str]:
    problems: list[str] = []
    try:
        candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        return [f"candidate is not valid JSON: {e}"]
    try:
        review = json.loads(review_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        return [f"review is not valid JSON: {e}"]
    if not isinstance(review, dict):
        return ["review must be a JSON object"]

    for key in TOP_KEYS:
        if key not in review:
            problems.append(f'review missing top key "{key}"')
    for key in review:
        if key not in TOP_KEYS:
            problems.append(f'review has unknown top key "{key}"')
    if review.get("schema_version") != SCHEMA_VERSION:
        problems.append('schema_version must be "1.0"')
    summary = review.get("executive_summary")
    if not isinstance(summary, str) or len(summary) < 20:
        problems.append("executive_summary must be >= 20 chars")

    checks = review.get("checks")
    if not isinstance(checks, dict):
        problems.append("checks must be an object")
        checks = {}
    else:
        for key in expected_checks:
            if key not in checks:
                problems.append(f'checks missing "{key}"')
        for key, value in checks.items():
            if key not in expected_checks:
                problems.append(f'checks has unknown key "{key}"')
            elif value not in ("pass", "fail"):
                problems.append(f"checks.{key} must be pass|fail")

    try:
        actual_sha = sha_hex(candidate_path.read_bytes())
    except OSError as e:
        return [f"cannot read candidate bytes: {e}"]
    if review.get("candidate_sha256") != actual_sha:
        claimed = str(review.get("candidate_sha256") or "")[:12]
        problems.append(
            f"candidate_sha256 mismatch: review says {claimed}… but candidate "
            f"bytes hash to {actual_sha[:12]}… (re-freeze after any edit)"
        )
    cand_snap = candidate.get("snapshot_date") if isinstance(candidate, dict) else None
    if cand_snap and review.get("snapshot_date") and cand_snap != review["snapshot_date"]:
        problems.append(
            f"snapshot_date mismatch: candidate {cand_snap} vs review {review['snapshot_date']}"
        )

    reviewer, operator = review.get("reviewer"), review.get("operator")
    if not isinstance(reviewer, str) or len(reviewer.strip()) < 3:
        problems.append("reviewer must be a named identity (>=3 chars)")
    if not isinstance(operator, str) or len(operator.strip()) < 3:
        problems.append("operator must be a named identity (>=3 chars)")
    if norm_identity(reviewer) == norm_identity(operator):
        problems.append("reviewer and operator must be different people/models (self-review is rejected)")
    if norm_identity(reviewer) in BANNED_IDENTITIES:
        problems.append(f'reviewer "{reviewer}" is a banned placeholder — sign with a real name/model')
    if norm_identity(operator) in BANNED_IDENTITIES:
        problems.append(f'operator "{operator}" is a banned placeholder')

    findings = review.get("findings")
    if not isinstance(findings, list):
        problems.append("findings must be an array")
        findings = []
    else:
        for i, finding in enumerate(findings):
            pre = f"findings[{i}]"
            if not isinstance(finding, dict):
                problems.append(f"{pre} must be an object")
                continue
            for key in ("severity", "field", "issue", "evidence", "disposition"):
                if key not in finding:
                    problems.append(f'{pre} missing "{key}"')
            if finding.get("severity") not in SEVERITIES:
                problems.append(f"{pre}.severity must be critical|major|minor")
            if finding.get("disposition") not in DISPOSITIONS:
                problems.append(f"{pre}.disposition must be fixed|must_fix|accepted|next_cycle")
            for key, minimum in (("field", 3), ("issue", 10), ("evidence", 10)):
                value = finding.get(key)
                if not isinstance(value, str) or len(value.strip()) < minimum:
                    problems.append(
                        f"{pre}.{key} too short — give a grep-able pointer (field path / URL / quote)"
                    )
            evidence = finding.get("evidence")
            if (isinstance(evidence, str) and len(evidence.strip()) >= 10
                    and not _EVIDENCE_POINTER.search(evidence)):
                problems.append(
                    f"{pre}.evidence has no verifiable pointer (need URL, field path, number, or quote)"
                )

    crit_maj = [f for f in findings
                if isinstance(f, dict) and f.get("severity") in ("critical", "major")]
    any_fail = "fail" in checks.values()
    verdict = review.get("verdict")
    if verdict == "APPROVED":
        if crit_maj:
            problems.append(
                f"verdict APPROVED but {len(crit_maj)} critical/major finding(s) open — must be REVISE"
            )
        if any_fail:
            problems.append("verdict APPROVED but at least one check is fail — must be REVISE")
        if "operator_instructions" in review:
            problems.append("APPROVED review must not carry operator_instructions")
    elif verdict == "REVISE":
        if not crit_maj and not any_fail and not findings:
            problems.append("verdict REVISE but no findings and all checks pass — give a reason")
    else:
        problems.append("verdict must be APPROVED|REVISE")
    if require_approved and verdict != "APPROVED":
        problems.append(f"gate requires APPROVED but verdict is {verdict}")

    if flags_path is not None:
        try:
            flags = json.loads(flags_path.read_text(encoding="utf-8"))
            if not isinstance(flags, list):
                raise ValueError("flags file must be a JSON array")
        except (OSError, ValueError) as e:
            problems.append(f"cannot read flags file: {e}")
            flags = None
        if flags is not None:
            disp = review.get("flags_dispositioned")
            if not isinstance(disp, list):
                problems.append("flags_dispositioned must be an array")
            else:
                for flag in flags:
                    hit = next(
                        (d for d in disp
                         if isinstance(d, dict) and d.get("code") == flag.get("code")
                         and d.get("field") == flag.get("field")),
                        None,
                    )
                    if hit is None:
                        problems.append(
                            f"machine flag uncovered: [{flag.get('code')}] {flag.get('field')} — "
                            "reviewer must disposition it in flags_dispositioned"
                        )
                    elif not isinstance(hit.get("disposition"), str) or len(hit["disposition"].strip()) < 5:
                        problems.append(
                            f"flags_dispositioned [{flag.get('code')}] {flag.get('field')} "
                            "needs a real disposition (>=5 chars)"
                        )
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--flags", type=Path, default=None)
    parser.add_argument("--checks", default="",
                        help="comma-separated exact check keys for this product")
    parser.add_argument("--require-approved", action="store_true")
    args = parser.parse_args(argv)
    expected = [c.strip() for c in args.checks.split(",") if c.strip()]
    problems = validate(args.candidate, args.review, args.flags, expected,
                        args.require_approved)
    if problems:
        print("✗ pm-review INVALID:")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    try:
        verdict = json.loads(args.review.read_text(encoding="utf-8"))["verdict"]
        count = len(json.loads(args.review.read_text(encoding="utf-8")).get("findings", []))
    except (OSError, ValueError, KeyError):
        verdict, count = "?", 0
    print(f"✓ pm-review valid ({verdict}, {count} findings)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
