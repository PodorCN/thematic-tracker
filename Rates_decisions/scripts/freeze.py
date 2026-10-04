#!/usr/bin/env python3
"""Freeze Rates_decisions/data/current.json. Thin wrapper over the shared gate.

Produces review/<today Toronto>/{candidate.json, candidate.sha256,
structural-flags.json} via scripts/review/freeze.py, with flags computed by
the Rates product plugin (scripts/review/flags_rates_decisions.py).
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from review.core import toronto_today  # noqa: E402
from review.flags_rates_decisions import structural_flags  # noqa: E402
from review.freeze import freeze as shared_freeze  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true",
                        help="re-freeze (voids any prior review of this date)")
    args = parser.parse_args(argv)
    today = toronto_today()
    doc = json.loads((ROOT / "data" / "current.json").read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as tmp:
        flags_path = Path(tmp) / "flags.json"
        flags_path.write_text(
            json.dumps(structural_flags(doc), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8")
        message, code = shared_freeze(ROOT / "data" / "current.json",
                                      ROOT / "review" / today, flags_path, today, args.force)
    print(("✓ " if code == 0 else "✗ ") + message)
    if code == 0:
        print("  next: reviewer writes "
              f"review/{today}/pm-review.json covering every flag, then publish")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
