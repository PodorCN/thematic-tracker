#!/usr/bin/env python3
"""General-theme-tracker structural gate + reviewer gate + publisher.

    python3 scripts/publish.py --check          # structural check only (errors fail, flags warn)
    python3 scripts/publish.py                  # full gate, then archive snapshot
    python3 scripts/publish.py --week 2026-W40  # pin week (default: frozen candidate's week)

Flow (SHA-bound, no self-review):
  1. edit data/themes/<week>/*.yaml (+ market snapshot + commentary)
  2. python3 scripts/freeze.py [--week <week>]  # builds candidate JSON, freezes to review/<today>/
  3. reviewer writes review/<today>/pm-review.json (see review/REVIEWER_AGENT.md)
  4. python3 scripts/publish.py                  # validates structure + review + sha binding, then archives

Shared reviewer mechanics (freeze bytes, SHA binding, verdict coherence) live
in scripts/review/ and are identical for all trackers. Only validate() below
(structure math, mirrored from backend/validate.js) and THEME_CHECKS are
product-specific.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from review.core import canonical, sha_hex, toronto_today  # noqa: E402
from review.flags_general_theme_tracker import structural_flags  # noqa: E402
from review.validate_pm_review import validate as validate_review  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"

THEME_CHECKS = [
    "excess_math", "timing_source", "freshness",
    "readability", "theme_noise", "proxy_tradability",
]

TORONTO = ZoneInfo("America/Toronto")
_WEEK = re.compile(r"^\d{4}-W\d{2}$")
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_HTTPS = re.compile(r"^https://")
_CJK = re.compile(r"[\u4e00-\u9fff]")
_ID = re.compile(r"^[a-z0-9-]+$")
STATUS = {"Emerging", "New", "Continuing", "Fading", "Dead"}
CONVICTION = {"High", "Med", "Low"}
HORIZON = {"Tactical 2-8w", "Cyclical 3-12m"}


def _moment(value: object) -> dt.datetime | None:
    try:
        m = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if m.tzinfo is None:
        m = m.replace(tzinfo=TORONTO)
    return m


def validate(doc: dict) -> list[str]:
    errors: list[str] = []

    def fail(message: str) -> None:
        errors.append(message)

    if not isinstance(doc, dict):
        return ["candidate must be a JSON object"]
    week = doc.get("week")
    if not isinstance(week, str) or not _WEEK.match(week):
        fail(f"week must match YYYY-Www (got {week!r})")
    snap_raw = doc.get("snapshot_date")
    try:
        snap = dt.date.fromisoformat(str(snap_raw))
    except ValueError:
        fail(f"snapshot_date must be YYYY-MM-DD (got {snap_raw!r})")
        snap = None
    themes = doc.get("themes")
    if not isinstance(themes, list) or not themes:
        fail("themes is empty — nothing to publish")
        themes = []
    if len(themes) > 7:
        fail(f"{len(themes)} themes in one week (homepage shows 3-7) — demote extras")
    for i, t in enumerate(themes):
        loc = f"themes[{i}].{t.get('id', '?')}" if isinstance(t, dict) else f"themes[{i}]"
        if not isinstance(t, dict):
            fail(f"{loc} must be an object")
            continue
        for k in ("schema_v", "id", "week", "title", "status", "status_note",
                  "conviction", "horizon", "created_at", "updated_at",
                  "body_text", "performance", "series", "proxies",
                  "events", "depends_on", "theme_vs_noise"):
            if t.get(k) is None:
                fail(f"{loc} missing required field: {k}")
        if t.get("schema_v") != 1:
            fail(f"{loc}.schema_v must be 1")
        if t.get("id") and not _ID.match(str(t["id"])):
            fail(f"{loc}.id must be slug")
        if t.get("status") and t["status"] not in STATUS:
            fail(f"{loc}.status bad: {t['status']}")
        if t.get("conviction") and t["conviction"] not in CONVICTION:
            fail(f"{loc}.conviction bad: {t['conviction']}")
        if t.get("horizon") and t["horizon"] not in HORIZON:
            fail(f"{loc}.horizon bad: {t['horizon']}")
        body = t.get("body_text") or ""
        if len(_CJK.findall(body)) > 900:
            fail(f"{loc}.body_text CJK > 900 (>5min)")
        if len(re.findall(r"\S+", _CJK.sub(" ", body))) > 500:
            fail(f"{loc}.body_text EN words > 500 (>5min)")
        p = t.get("performance") or {}
        for k in ("ret_1w", "ret_1m", "ret_ytd", "benchmark_ret_1w",
                  "benchmark_ret_1m", "benchmark_ret_ytd",
                  "excess_1w", "excess_1m", "excess_ytd", "proxy_price"):
            if not isinstance(p.get(k), (int, float)):
                fail(f"{loc}.performance.{k} must be number")
        for suffix in ("1w", "1m", "ytd"):
            ret, bret, exc = p.get(f"ret_{suffix}"), p.get(f"benchmark_ret_{suffix}"), p.get(f"excess_{suffix}")
            if isinstance(ret, (int, float)) and isinstance(bret, (int, float)) \
                    and isinstance(exc, (int, float)) and abs(exc - (ret - bret)) > 0.2:
                fail(f"{loc}.performance.excess_{suffix} mismatch "
                     f"({exc} vs {(ret - bret):.2f}, >0.2pp)")
        if not p.get("as_of_utc") or not p.get("source") or not p.get("benchmark_rationale"):
            fail(f"{loc}.performance needs as_of_utc + source + benchmark_rationale")
        as_of = _moment(p.get("as_of_utc")) if p.get("as_of_utc") else None
        if p.get("as_of_utc") and as_of is None:
            fail(f"{loc}.performance.as_of_utc not ISO8601")
        elif as_of is not None and snap is not None:
            if (snap - as_of.astimezone(TORONTO).date()).days > 7:
                fail(f"{loc}.performance.as_of_utc stale (>7d vs snapshot_date)")
        if not isinstance(t.get("series"), list) or len(t["series"]) < 2:
            fail(f"{loc}.series needs >= 2 points")
        proxies = t.get("proxies")
        if not isinstance(proxies, list) or not 1 <= len(proxies) <= 3:
            fail(f"{loc}.proxies count must be 1-3")
        else:
            for j, px in enumerate(proxies):
                for k in ("ticker", "name", "type", "region",
                          "liquidity_note", "why_represents", "tracking_gap"):
                    if not (isinstance(px, dict) and px.get(k)):
                        fail(f"{loc}.proxies[{j}].{k} missing")
                if isinstance(px, dict) and px.get("type") == "ETF" and not px.get("expense"):
                    fail(f"{loc}.proxies[{j}].expense required for ETF")
        events = t.get("events")
        if not isinstance(events, list) or not events:
            fail(f"{loc}.events empty — UNPUBLISHABLE")
        else:
            for j, ev in enumerate(events):
                ef = f"{loc}.events[{j}]"
                if not (isinstance(ev, dict) and ev.get("event_time_utc")):
                    fail(f"{ef} missing event_time_utc — UNPUBLISHABLE")
                elif _moment(ev.get("event_time_utc")) is None:
                    fail(f"{ef}.event_time_utc not ISO8601")
                if not (isinstance(ev, dict) and ev.get("source")):
                    fail(f"{ef} missing source — UNPUBLISHABLE")
                url = ev.get("url") if isinstance(ev, dict) else None
                if not (isinstance(url, str) and _HTTPS.match(url)):
                    fail(f"{ef}.url must be https://")
        depends = t.get("depends_on")
        if not isinstance(depends, list) or not depends:
            fail(f"{loc}.depends_on empty — no next catalyst, demote to Noise")
        else:
            for j, d in enumerate(depends):
                for k in ("event_name", "due_date", "why_matters", "if_bull", "if_bear"):
                    if not (isinstance(d, dict) and d.get(k)):
                        fail(f"{loc}.depends_on[{j}].{k} missing")
        vn = t.get("theme_vs_noise") or {}
        keys = ("persistence", "breadth", "volume_confirm",
                "falsifiable_catalyst", "repricing_logic")
        count = sum(1 for k in keys if vn.get(k) is True)
        if vn.get("score") != count:
            fail(f"{loc}.theme_vs_noise.score={vn.get('score')} but true-count={count}")
    ms = doc.get("market_snapshot")
    if isinstance(ms, dict) and ms.get("week") != week:
        fail(f"market_snapshot.week {ms.get('week')!r} != candidate week {week!r}")
    cm = doc.get("commentary")
    if isinstance(cm, dict) and cm.get("week") != week:
        fail(f"commentary.week {cm.get('week')!r} != candidate week {week!r}")
    return errors


def _build(week: str | None, snapshot_date: str) -> dict:
    cmd = ["node", str(ROOT / "scripts" / "build_candidate.mjs"),
           "--snapshot-date", snapshot_date]
    if week:
        cmd += ["--week", week]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(res.stdout + res.stderr)
        raise SystemExit(res.returncode or 1)
    return json.loads(res.stdout)


def _frontend_dirty() -> list[str] | None:
    watched = ["general-theme-tracker/frontend/src/", "general-theme-tracker/backend/",
               "general-theme-tracker/scripts/", "general-theme-tracker/frontend/vite.config.ts",
               "general-theme-tracker/frontend/tailwind.config.js"]
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
    parser.add_argument("--week", default=None, help="YYYY-Www (default: latest)")
    args = parser.parse_args(argv)
    today = toronto_today()

    if args.check:
        doc = _build(args.week, today)
        errors = validate(doc)
        flags = structural_flags(doc)
        if errors:
            print("✗ structural validation failed:")
            for error in errors:
                print(f"  - {error}")
            return 1
        print(f"✓ structure valid (week={doc.get('week')} themes={len(doc.get('themes') or [])})")
        if flags:
            print(f"! {len(flags)} structural flag(s) need reviewer disposition:")
            for flag in flags:
                print(f"  ! [{flag['code']}] {flag['field']}: {flag['message']}")
        else:
            print("✓ no structural flags")
        return 0

    review_dir = ROOT / "review" / today
    cand_path = review_dir / "candidate.json"
    sha_path = review_dir / "candidate.sha256"
    pm_path = review_dir / "pm-review.json"
    flags_path = review_dir / "structural-flags.json"
    missing = [p for p in (cand_path, sha_path, pm_path, flags_path) if not p.exists()]
    if missing:
        print("✗ reviewer gate: frozen review bundle incomplete.")
        for path in missing:
            print(f"  - missing review/{today}/{path.name}")
        print("  Flow: python3 scripts/freeze.py -> reviewer writes pm-review.json "
              "(see review/REVIEWER_AGENT.md) -> python3 scripts/publish.py")
        return 1
    try:
        frozen = json.loads(cand_path.read_text(encoding="utf-8"))
    except ValueError as exc:
        print(f"✗ frozen candidate is not valid JSON: {exc}")
        return 1
    if frozen.get("snapshot_date") != today:
        print(f"✗ frozen candidate snapshot_date is {frozen.get('snapshot_date') or '(missing)'} "
              f"but today (Toronto) is {today}.")
        print("  Re-run freeze (which voids prior review), then publish.")
        return 1

    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "rebuilt.json"
        res = subprocess.run(
            ["node", str(ROOT / "scripts" / "build_candidate.mjs"),
             "--week", str(frozen.get("week")),
             "--snapshot-date", str(frozen.get("snapshot_date")),
             "--out", str(src)], capture_output=True, text=True)
        if res.returncode != 0:
            print(res.stdout + res.stderr)
            return 1
        try:
            current = json.loads(src.read_text(encoding="utf-8"))
        except ValueError as exc:
            print(f"✗ rebuilt candidate is not valid JSON: {exc}")
            return 1

    errors = validate(current)
    flags = structural_flags(current)
    if errors:
        print("✗ structural validation failed:")
        for error in errors:
            print(f"  - {error}")
        return 1
    print(f"✓ structure valid (week={current.get('week')} themes={len(current.get('themes') or [])})")

    cand_bytes = cand_path.read_bytes()
    filed_sha = sha_path.read_text(encoding="utf-8").strip()
    if sha_hex(cand_bytes) != filed_sha:
        print("✗ candidate.sha256 does not match candidate.json bytes — candidate was "
              "edited after freezing. Re-freeze.")
        return 1
    if sha_hex(canonical(current)) != filed_sha:
        print("✗ data/themes bundle differs from frozen candidate (canonical sha mismatch).")
        print("  Any edit after freeze voids the review — re-run freeze with --force and re-review.")
        return 1

    problems = validate_review(cand_path, pm_path, flags_path, THEME_CHECKS, True)
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
    print(f"✓ published snapshot {today} (week={current.get('week')}, "
          f"bytes == reviewed candidate {filed_sha[:12]}…)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
