#!/usr/bin/env python3
"""Validate today's Rates pm-review.json. Thin wrapper over the shared gate."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from publish import RATES_CHECKS  # noqa: E402
from review.core import toronto_today  # noqa: E402
from review.validate_pm_review import validate  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    review_dir = ROOT / "review" / toronto_today()
    problems = validate(
        review_dir / "candidate.json",
        review_dir / "pm-review.json",
        review_dir / "structural-flags.json",
        RATES_CHECKS,
        False,
    )
    if problems:
        print("✗ pm-review INVALID:")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print("✓ pm-review valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
