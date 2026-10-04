#!/usr/bin/env python3
"""Freeze a product data file into an immutable review candidate. Shared.

Writes <review-dir>/candidate.json (canonical bytes), candidate.sha256, and
copies the product's precomputed machine flags to structural-flags.json.

Rule: after freezing, ANY edit to the input file invalidates the review
(publish compares canonical sha). Re-freeze with --force instead of editing
the candidate; the prior review is then void.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from review.core import canonical, sha_hex, toronto_today


def freeze(input_path: Path, review_dir: Path, flags_path: Path | None,
           today: str, force: bool) -> tuple[str, int]:
    try:
        doc = json.loads(input_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        return f"input is not valid JSON: {e}", 1
    if not isinstance(doc, dict):
        return "input must be a JSON object", 1
    if doc.get("snapshot_date") != today:
        return (
            f"snapshot_date is {doc.get('snapshot_date')!r} but today (Toronto) "
            f"is {today}. Set it before freezing so the hash covers the publish date."
        ), 1
    review_dir.mkdir(parents=True, exist_ok=True)
    cand_path = review_dir / "candidate.json"
    payload = canonical(doc)
    if cand_path.exists() and not force:
        return (
            f"{cand_path} already exists. Candidate is immutable — edit the input, "
            "then re-run with --force (old review is void)."
        ), 1
    cand_path.write_bytes(payload)
    digest = sha_hex(payload)
    (review_dir / "candidate.sha256").write_text(digest + "\n", encoding="utf-8")
    flags: object = []
    if flags_path is not None:
        try:
            flags = json.loads(flags_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            return f"cannot read flags file: {e}", 1
        if not isinstance(flags, list):
            return "flags file must be a JSON array", 1
    (review_dir / "structural-flags.json").write_text(
        json.dumps(flags, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    count = len(flags) if isinstance(flags, list) else 0
    return (f"froze {cand_path} (sha {digest[:12]}…, {count} structural flag(s))\n"
            "next: reviewer writes pm-review.json covering every flag, then publish"), 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--review-dir", type=Path, required=True)
    parser.add_argument("--flags", type=Path, default=None)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--today", default=None,
                        help="override Toronto date (tests only)")
    args = parser.parse_args(argv)
    message, code = freeze(args.input, args.review_dir, args.flags,
                           args.today or toronto_today(), args.force)
    print(("✓ " if code == 0 else "✗ ") + message)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
