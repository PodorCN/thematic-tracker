#!/usr/bin/env python3
"""Freeze general-theme-tracker week bundle. Thin wrapper over the shared gate.

Builds the weekly candidate via scripts/build_candidate.mjs
(data/themes/<week>/*.yaml + market snapshot + commentary), then freezes it
with the shared gate into review/<today Toronto>/.

Produces review/<today>/{candidate.json, candidate.sha256,
structural-flags.json} with flags from scripts/review/flags_general_theme_tracker.py.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from review.core import toronto_today  # noqa: E402
from review.flags_general_theme_tracker import structural_flags  # noqa: E402
from review.freeze import freeze as shared_freeze  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def build_candidate(week: str | None, snapshot_date: str, out: Path) -> None:
    cmd = ["node", str(ROOT / "scripts" / "build_candidate.mjs"),
           "--snapshot-date", snapshot_date]
    if week:
        cmd += ["--week", week]
    cmd += ["--out", str(out)]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(res.stdout + res.stderr)
        raise SystemExit(res.returncode or 1)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--week", default=None,
                        help="YYYY-Www (default: latest in data/themes)")
    parser.add_argument("--force", action="store_true",
                        help="re-freeze (voids any prior review of this date)")
    args = parser.parse_args(argv)
    today = toronto_today()
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "candidate_src.json"
        build_candidate(args.week, today, src)
        try:
            doc = json.loads(src.read_text(encoding="utf-8"))
        except ValueError as exc:
            print(f"✗ built candidate is not valid JSON: {exc}")
            return 1
        with tempfile.TemporaryDirectory() as tmp2:
            flags_path = Path(tmp2) / "flags.json"
            flags_path.write_text(
                json.dumps(structural_flags(doc), indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8")
            message, code = shared_freeze(src, ROOT / "review" / today,
                                          flags_path, today, args.force)
        print(("✓ " if code == 0 else "✗ ") + message)
        if code == 0:
            print(f"  week={doc.get('week')} themes={len(doc.get('themes') or [])}")
            print("  next: reviewer writes "
                  f"review/{today}/pm-review.json covering every flag, then publish")
        return code


if __name__ == "__main__":
    raise SystemExit(main())
