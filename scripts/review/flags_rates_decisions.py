#!/usr/bin/env python3
"""Structural flags for Rates_decisions. Product plugin for the shared gate.

Emits [{code, field, message}] — items a human reviewer must disposition in
pm-review.json's flags_dispositioned. Machine reports; PM judges.

Usage: flags_rates_decisions.py --input Rates_decisions/data/current.json [--out PATH]
With --out, writes the JSON array to PATH; otherwise prints it.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

TORONTO = ZoneInfo("America/Toronto")

_PRIMARY = [
    (re.compile(r"statistics canada", re.I), ("statcan.gc.ca",), "Statistics Canada"),
    (re.compile(r"bank of canada", re.I), ("bankofcanada.ca",), "Bank of Canada"),
    (re.compile(r"\bBLS\b|bureau of labor", re.I), ("bls.gov",), "BLS"),
    (re.compile(r"\bBEA\b|bureau of economic", re.I), ("bea.gov",), "BEA"),
    (re.compile(r"federal reserve|fomc|ny fed|new york fed", re.I),
     ("federalreserve.gov", "newyorkfed.org"), "Federal Reserve"),
    (re.compile(r"\bCME\b|fedwatch", re.I), ("cmegroup.com",), "CME"),
]

_VIA = re.compile(r"^(.*?)\s*\(via\b", re.I)


def _claimed_primary(source: str) -> str:
    match = _VIA.match(source or "")
    return (match.group(1) if match else (source or "")).strip()


def structural_flags(doc: dict) -> list[dict]:
    flags: list[dict] = []

    def push(code: str, field: str, message: str) -> None:
        flags.append({"code": code, "field": field, "message": message})

    for bank in ("fed", "boc"):
        drivers = doc.get("drivers", {}).get(bank, {})
        all_drivers = list(drivers.get("hawkish", [])) + list(drivers.get("dovish", []))
        for driver in all_drivers:
            did = driver.get("id", "?")
            claimed = _claimed_primary(str(driver.get("source") or ""))
            url = str(driver.get("source_url") or "")
            for pattern, domains, label in _PRIMARY:
                if pattern.search(claimed):
                    if not any(dom in url for dom in domains):
                        push(
                            "primary_source_mismatch",
                            f"drivers.{bank}.{did}.source_url",
                            f'{did} claims "{claimed}" ({label}) but URL is {url or "(missing)"} '
                            "— swap to primary or restate source as secondary and down-weight",
                        )
                    break
            if not url.startswith("https://"):
                push("bad_source_url", f"drivers.{bank}.{did}.source_url",
                     f'{did} source_url must be https:// (got "{url}")')
            weight = driver.get("weight")
            if isinstance(weight, int) and weight >= 5 and not driver.get("market_validation"):
                push("high_weight_no_validation", f"drivers.{bank}.{did}.weight",
                     f"{did} weight={weight} without market validation")
            elif isinstance(weight, int) and weight >= 5 \
                    and driver.get("market_validation") == "unverified":
                push("high_weight_no_validation", f"drivers.{bank}.{did}.weight",
                     f"{did} weight={weight} without market validation "
                     "— need FedWatch pp / 2Y bp repricing number or lower the weight")
        by_url: dict[str, list[dict]] = {}
        for driver in all_drivers:
            url = str(driver.get("source_url") or "")
            if url:
                by_url.setdefault(url, []).append(driver)
        for url, group in by_url.items():
            sides = {d.get("direction") for d in group}
            if len(group) > 1 and sides == {1, -1}:
                facets = [d.get("facet") for d in group if d.get("facet")]
                if not (len(facets) == len(group) and len(set(facets)) == len(group)):
                    ids = ",".join(d.get("id", "?") for d in group)
                    push(
                        "split_release_no_facet",
                        f"drivers.{bank}.[{ids}]",
                        f"same URL {url} used on BOTH sides "
                        f"({' vs '.join(d.get('id', '?') for d in group)}) without distinct "
                        "facet fields — merge or add facet + separate transmission chains",
                    )
    try:
        as_of = dt.datetime.fromisoformat(str(doc.get("as_of", "")))
    except ValueError:
        as_of = None
    for bank in ("fed", "boc"):
        placed = (doc.get("meetings", {}).get(bank, {}).get("pricing", {}).get("as_of"))
        if placed and as_of is not None:
            try:
                other = dt.datetime.fromisoformat(str(placed))
            except ValueError:
                continue
            # Compare calendar dates, not wall-clock: pricing as_of is often
            # date-only (naive) while snapshot as_of carries an offset.
            a = as_of.replace(tzinfo=None).date()
            b = other.replace(tzinfo=None).date()
            days = (a - b).days
            if days > 4:
                push("stale_pricing", f"meetings.{bank}.pricing.as_of",
                     f"{bank} pricing as_of {placed} is {days}d older than snapshot "
                     "as_of — re-pull or mark unavailable")
    cal_urls: dict[str, list[str]] = {}
    for event in doc.get("calendar", []):
        url = str(event.get("source_url") or "")
        if not url.startswith("https://"):
            push("bad_source_url", f"calendar.{event.get('event')}.source_url",
                 f"calendar \"{event.get('event')}\" needs an https source_url")
        if url:
            cal_urls.setdefault(url, []).append(str(event.get("event")))
    for url, events in cal_urls.items():
        if len(events) >= 5 and re.search(r"economic-calendar/?$", url):
            push("generic_calendar_source", "calendar.source_url",
                 f"{len(events)} rows share generic homepage {url} — link each row to its "
                 "consensus row or mark forecast unverified with a named source")
    return flags


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    doc = json.loads(args.input.read_text(encoding="utf-8"))
    payload = json.dumps(structural_flags(doc), indent=2, ensure_ascii=False) + "\n"
    if args.out is not None:
        args.out.write_text(payload, encoding="utf-8")
    else:
        sys.stdout.write(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
