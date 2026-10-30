#!/usr/bin/env python3
"""Prune drivers that predate the last policy decision, then re-score.

    python3 scripts/prune_drivers.py            # rewrite data/current.json
    python3 scripts/prune_drivers.py --dry-run  # list what would go

A driver whose published_at (Toronto day) is before
meetings.<bank>.last_meeting.date is dropped unless its weight is
>= CARRY_OVER_MIN_WEIGHT (i.e. significance > 5). total_score base/effective/
band are recomputed against the snapshot as_of, using the same rules as
publish.py --check.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

from publish import _age_days, _band_of, _decay, driver_day, is_stale_driver

ROOT = Path(__file__).resolve().parents[1]


def prune(doc: dict) -> list[str]:
    removed: list[str] = []
    as_of = dt.datetime.fromisoformat(str(doc["as_of"]))
    for bank in ("fed", "boc"):
        last_meeting_date = doc["meetings"][bank]["last_meeting"].get("date")
        drivers = doc["drivers"][bank]
        for side in ("hawkish", "dovish"):
            kept = []
            for driver in drivers.get(side) or []:
                if is_stale_driver(driver, last_meeting_date):
                    removed.append(f"{bank}/{driver.get('id')} ({side}, {driver_day(driver)}, "
                                   f"w{driver.get('weight')}) < {last_meeting_date}")
                else:
                    kept.append(driver)
            drivers[side] = kept
        everything = drivers["hawkish"] + drivers["dovish"]
        base = max(-10, min(10, sum(d["direction"] * d["weight"] for d in everything)))
        eff = sum(d["direction"] * d["weight"] * _decay(_age_days(d.get("observed_at"), as_of))
                  for d in everything)
        score = doc["total_score"][bank]
        score["base_total"] = base
        score["effective_total"] = round(eff, 2)
        score["band"] = _band_of(base)
    return removed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="report only, do not write")
    args = parser.parse_args(argv)
    path = ROOT / "data" / "current.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    removed = prune(doc)
    for line in removed:
        print(f"- {line}")
    print(f"{len(removed)} driver(s) {'would be ' if args.dry_run else ''}pruned")
    if not args.dry_run:
        path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
