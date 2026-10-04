#!/usr/bin/env python3
"""Rates_decisions structural gate + reviewer gate + publisher.

    python3 scripts/publish.py --check   # structural check only (errors fail, flags warn)
    python3 scripts/publish.py           # full gate, then publish snapshot

Flow (SHA-bound, no self-review):
  1. edit data/current.json (snapshot_date = today Toronto)
  2. python3 scripts/freeze.py         # -> review/<today>/{candidate.json, candidate.sha256, structural-flags.json}
  3. reviewer writes review/<today>/pm-review.json (see scripts/review/REVIEWER_AGENT.md)
  4. python3 scripts/publish.py       # validates structure + review + sha binding, then archives

Shared reviewer mechanics (freeze bytes, SHA binding, verdict coherence) live
in scripts/review/ and are identical for all trackers. Only validate() below
(structure math) and RATES_CHECKS are product-specific.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import re
import subprocess
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from review.core import canonical, sha_hex, toronto_today  # noqa: E402
from review.flags_rates_decisions import structural_flags  # noqa: E402
from review.validate_pm_review import validate as validate_review  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"

RATES_CHECKS = [
    "official_policy", "pricing", "drivers",
    "market_validation", "freshness", "decision_usefulness",
]

TORONTO = ZoneInfo("America/Toronto")
_NAN_INF = re.compile(r"\bNaN\b|Infinity")
_HTTPS = re.compile(r"^https://")
_DATE_ONLY = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _toronto_day(value: object) -> str | None:
    if isinstance(value, str) and _DATE_ONLY.match(value.strip()):
        return value.strip()  # date-only = Toronto date as written
    try:
        moment = value if isinstance(value, dt.datetime) else dt.datetime.fromisoformat(str(value))
    except ValueError:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=TORONTO)
    return moment.astimezone(TORONTO).strftime("%Y-%m-%d")


def _age_days(observed: object, as_of: dt.datetime) -> int:
    # Calendar-day difference in Toronto (not millisecond math).
    a, b = _toronto_day(observed), _toronto_day(as_of.isoformat())
    if not a or not b:
        return 0
    return (dt.date.fromisoformat(b) - dt.date.fromisoformat(a)).days


def _decay(days: int) -> float:
    return 1 if days <= 7 else 0.75 if days <= 14 else 0.5 if days <= 30 else 0.25


def _band_of(total: int) -> str:
    if total >= 7:
        return "strong hike lean"
    if total > 3:
        return "lean hike"
    if total >= -3:
        return "hold"
    if total >= -7:
        return "lean cut"
    return "strong cut lean"


def validate(doc: dict) -> list[str]:
    errors: list[str] = []

    def fail(message: str) -> None:
        errors.append(message)

    try:
        as_of = dt.datetime.fromisoformat(str(doc.get("as_of", "")))
    except ValueError:
        fail("as_of must be ISO8601 with offset")
        as_of = None

    for bank in ("fed", "boc"):
        pricing = (doc.get("meetings", {}).get(bank, {}).get("pricing"))
        if not pricing:
            fail(f"meetings.{bank}.pricing missing")
            continue
        probs = pricing.get("probabilities")
        if probs is not None:
            vals = list((probs or {}).values())
            if len(vals) != 3:
                fail(f"{bank}: probabilities must have exactly 3 keys (hike/hold/cut)")
            total = sum(vals)
            if any(not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0 or v > 1
                   for v in vals):
                fail(f"{bank}: probability out of [0,1]")
            if total < 0.99 or total > 1.01:
                fail(f"{bank}: probabilities sum {total:.3f}, must be 0.99-1.01")
        elif pricing.get("probability_status") != "unavailable":
            fail(f'{bank}: null probabilities require probability_status "unavailable"')
        if not _HTTPS.match(str(pricing.get("source_url") or "")):
            fail(f"meetings.{bank}.pricing.source_url must be https://")

        for entry in (doc.get("betting", {}).get(bank) or []):
            if entry.get("status") == "available" and entry.get("probabilities"):
                subtotal = sum(entry["probabilities"].values())
                if subtotal < 0.99 or subtotal > 1.01:
                    fail(f"betting.{bank}.{entry.get('platform')}: "
                         f"probabilities sum {subtotal:.3f}")

        drivers = doc.get("drivers", {}).get(bank)
        if not drivers:
            fail(f"drivers.{bank} missing")
            continue
        ordered: list[dict] = []
        for side, want in (("hawkish", 1), ("dovish", -1)):
            for driver in drivers.get(side) or []:
                ordered.append(driver)
                if driver.get("direction") != want:
                    sign = "+1" if want > 0 else "-1"
                    fail(f"{bank}/{driver.get('id')}: in \"{side}\" array but "
                         f"direction={driver.get('direction')} (must be {sign})")
        seen: set[str] = set()
        signed = w_sum = eff_signed = 0
        for driver in ordered:
            did = driver.get("id")
            if not did or did in seen:
                fail(f'{bank}: duplicate or missing driver id "{did}"')
            seen.add(did)
            weight = driver.get("weight")
            if not isinstance(weight, int) or weight < 1 or weight > 10:
                fail(f"{bank}/{did}: weight must be integer 1-10")
                continue
            wb = driver.get("weight_breakdown") or {}
            parts = [wb.get("deviation"), wb.get("importance"), wb.get("surprise")]
            try:
                numbers = [float(p) for p in parts]
            except (TypeError, ValueError):
                numbers = []
            if len(numbers) != 3 or any(not math.isfinite(n) for n in numbers):
                fail(f"{bank}/{did}: weight_breakdown needs deviation+importance+surprise numbers")
            elif abs(sum(numbers) - weight) > 1e-9 or wb.get("total") != weight:
                plus = "+".join(str(wb.get(k)) for k in ("deviation", "importance", "surprise"))
                fail(f"{bank}/{did}: breakdown ({plus}) must sum to weight {weight} "
                     f"(and total={weight})")
            if not _HTTPS.match(str(driver.get("source_url") or "")):
                fail(f"{bank}/{did}: source_url must be https://")
            if weight >= 7 and driver.get("market_validation") in (None, "unverified"):
                fail(f"{bank}/{did}: weight ≥7 requires market validation evidence")
            try:
                dt.datetime.fromisoformat(str(driver.get("observed_at", "")))
            except ValueError:
                fail(f"{bank}/{did}: observed_at must be ISO8601")
            direction = driver.get("direction") if driver.get("direction") in (1, -1) else 0
            signed += direction * weight
            w_sum += abs(weight)
            if as_of is not None:
                eff_signed += direction * weight * _decay(_age_days(driver.get("observed_at"), as_of))
        if ordered and w_sum / len(ordered) > 5:
            fail(f"{bank}: mean |weight| {w_sum / len(ordered):.1f} > 5 → score inflation")
        declared = (doc.get("total_score", {}).get(bank, {}).get("base_total"))
        recomputed = max(-10, min(10, signed))
        if declared != recomputed:
            fail(f"{bank}: total_score.base_total={declared} but drivers sum to {recomputed}")
        declared_eff = (doc.get("total_score", {}).get(bank, {}).get("effective_total"))
        if (not isinstance(declared_eff, (int, float))
                or abs(declared_eff - round(eff_signed, 2)) > 0.06):
            fail(f"{bank}: total_score.effective_total={declared_eff} but age-decayed "
                 f"recompute is {round(eff_signed, 2):.2f} "
                 "(decay ≤7d×1 / 8–14d×0.75 / 15–30d×0.5 / >30d×0.25 vs as_of)")
        declared_band = str((doc.get("total_score", {}).get(bank, {}).get("band") or ""))
        expected_first = _band_of(recomputed).split(" ")[0].lower()
        hold_ok = recomputed >= -3 and recomputed <= 3 and declared_band.lower() == "hold"
        if expected_first not in declared_band.lower() and not hold_ok:
            fail(f'{bank}: band "{declared_band}" does not match base_total {recomputed} '
                 f'(expected ~"{_band_of(recomputed)}")')

    all_ids = [
        d.get("id")
        for bank in ("fed", "boc")
        for side in ("hawkish", "dovish")
        for d in (doc.get("drivers", {}).get(bank, {}).get(side) or [])
    ]
    if len(set(all_ids)) != len(all_ids):
        fail("duplicate driver id across fed/boc")

    for event in doc.get("calendar") or []:
        if not event.get("date_toronto"):
            fail(f"calendar \"{event.get('event')}\": date_toronto required")
        if event.get("date_only"):
            if event.get("datetime_toronto") or event.get("datetime_utc"):
                fail(f"calendar \"{event.get('event')}\": date_only events must set datetimes to null")
        elif not event.get("datetime_toronto") or not event.get("datetime_utc"):
            fail(f"calendar \"{event.get('event')}\": timed releases require "
                 "datetime_toronto + datetime_utc")
        if not _HTTPS.match(str(event.get("source_url") or "")):
            fail(f"calendar \"{event.get('event')}\": source_url must be https://")
    return errors


def _frontend_dirty() -> list[str] | None:
    watched = ["Rates_decisions/index.html", "Rates_decisions/app.js",
               "Rates_decisions/styles.css", "Rates_decisions/dev-server.js",
               "Rates_decisions/scripts/"]
    try:
        out = subprocess.run(
            ["git", "diff", "--name-only"], cwd=ROOT.parent,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
        ).stdout + subprocess.run(
            ["git", "diff", "--cached", "--name-only"], cwd=ROOT.parent,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    files = [line.strip() for line in out.splitlines() if line.strip()]
    return [f for f in files if any(f == w or f.startswith(w) for w in watched)]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="structural check only (errors fail, flags warn)")
    args = parser.parse_args(argv)

    current_path = DATA_DIR / "current.json"
    try:
        raw = current_path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"✗ current.json unreadable: {exc}")
        return 1
    if _NAN_INF.search(raw):
        print("✗ structural validation failed:\n  - JSON contains NaN/Infinity")
        return 1
    try:
        doc = json.loads(raw)
    except ValueError as exc:
        print(f"✗ current.json is not valid JSON: {exc}")
        return 1

    errors = validate(doc)
    flags = structural_flags(doc) if isinstance(doc, dict) else []
    if errors:
        print("✗ structural validation failed:")
        for error in errors:
            print(f"  - {error}")
        return 1
    print("✓ structure valid")
    if flags:
        print(f"! {len(flags)} structural flag(s) need reviewer disposition:")
        for flag in flags:
            print(f"  ! [{flag['code']}] {flag['field']}: {flag['message']}")
    else:
        print("✓ no structural flags")
    if args.check:
        return 0

    today = toronto_today()
    if doc.get("snapshot_date") != today:
        print(f"✗ snapshot_date is {doc.get('snapshot_date') or '(missing)'} "
              f"but today (Toronto) is {today}.")
        print("  Set it, re-run freeze (which voids prior review), then publish.")
        return 1

    review_dir = ROOT / "review" / today
    cand_path = review_dir / "candidate.json"
    sha_path = review_dir / "candidate.sha256"
    pm_path = review_dir / "pm-review.json"
    flags_path = review_dir / "structural-flags.json"
    missing = [p for p in (cand_path, sha_path, pm_path, flags_path) if not p.exists()]
    if missing:
        print("✗ reviewer gate: frozen review bundle incomplete.")
        for path in missing:
            print(f"  - missing {path.relative(ROOT)}")
        if (ROOT / "review" / f"{today}.md").exists():
            print(f"  NOTE: legacy review/{today}.md exists but is NO LONGER accepted "
                  "(no SHA binding, self-review). Run: python3 scripts/freeze.py")
        print("  Flow: python3 scripts/freeze.py -> reviewer writes pm-review.json "
              "(see scripts/review/REVIEWER_AGENT.md) -> python3 scripts/publish.py")
        return 1

    cand_bytes = cand_path.read_bytes()
    filed_sha = sha_path.read_text(encoding="utf-8").strip()
    if sha_hex(cand_bytes) != filed_sha:
        print("✗ candidate.sha256 does not match candidate.json bytes — candidate was "
              "edited after freezing. Re-freeze.")
        return 1
    if sha_hex(canonical(doc)) != filed_sha:
        print("✗ data/current.json differs from frozen candidate (canonical sha mismatch).")
        print("  Any edit after freeze voids the review — re-run freeze with --force and re-review.")
        return 1

    problems = validate_review(cand_path, pm_path, flags_path, RATES_CHECKS, True)
    if problems:
        print("✗ reviewer gate: pm-review validation failed:")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print("✓ pm-review valid (APPROVED, sha "
          f"{json.loads(pm_path.read_text(encoding='utf-8')).get('candidate_sha256', '')[:12]}…)")
    disp = json.loads(pm_path.read_text(encoding="utf-8")).get("flags_dispositioned") or []
    uncovered = [fl for fl in flags
                 if not any(d.get("code") == fl["code"] and d.get("field") == fl["field"] for d in disp)]
    if uncovered:
        print("✗ reviewer gate: current data has flags the review does not disposition:")
        for flag in uncovered:
            print(f"  - [{flag['code']}] {flag['field']}")
        return 1

    dirty = _frontend_dirty()
    if dirty is None:
        print("  ! git check skipped (not a git repo?) — ensure no frontend changes ride along")
    elif dirty:
        print("✗ data/frontend separation: frontend or scripts changed in working tree:")
        for path in dirty:
            print(f"  - {path}")
        print("  Ship frontend in an independent PR; data publish must be data-only.")
        return 1

    archive_path = DATA_DIR / "archive" / f"{today}.json"
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    archive_path.write_bytes(cand_bytes)
    (DATA_DIR / "latest.json").write_bytes(cand_bytes)
    dates_path = DATA_DIR / "dates.json"
    dates = {"latest": today, "dates": []}
    if dates_path.exists():
        dates = json.loads(dates_path.read_text(encoding="utf-8"))
    dates["latest"] = today
    dates["dates"] = sorted(set([today, *(dates.get("dates") or [])]), reverse=True)
    for day in dates["dates"]:
        if not (DATA_DIR / "archive" / f"{day}.json").exists():
            print(f"  ! dates.json lists {day} but archive/{day}.json is missing")
    dates_path.write_text(json.dumps(dates, indent=2) + "\n", encoding="utf-8")
    print(f"✓ published snapshot {today} (bytes == reviewed candidate {filed_sha[:12]}…)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
