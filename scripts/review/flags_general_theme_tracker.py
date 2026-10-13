#!/usr/bin/env python3
"""Structural flags for general-theme-tracker. Product plugin for the shared gate.

Mirrors general-theme-tracker/backend/validate.js + data/schema/theme.schema.yaml,
but operates on the frozen weekly candidate JSON (built by
general-theme-tracker/scripts/build_candidate.mjs from data/themes/<week>/*.yaml).

Candidate shape:
  {snapshot_date, week, themes[], market_snapshot?, commentary?}

Emits [{code, field, message}] — items a human reviewer must disposition in
pm-review.json's flags_dispositioned. Machine reports; PM judges.

Usage: flags_general_theme_tracker.py --input <candidate.json> [--out PATH]
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
_WEEK = re.compile(r"^\d{4}-W\d{2}$")
_CJK = re.compile(r"[\u4e00-\u9fff]")
_HTTPS = re.compile(r"^https://")


def _cjk_len(s: str) -> int:
    return len(_CJK.findall(s or ""))


def _en_words(s: str) -> int:
    stripped = _CJK.sub(" ", s or "")
    return len(re.findall(r"\S+", stripped))


def _parse_moment(value: object) -> dt.datetime | None:
    try:
        m = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if m.tzinfo is None:
        m = m.replace(tzinfo=TORONTO)
    return m


def structural_flags(doc: dict) -> list[dict]:
    flags: list[dict] = []

    def push(code: str, field: str, message: str) -> None:
        flags.append({"code": code, "field": field, "message": message})

    week = doc.get("week")
    if not isinstance(week, str) or not _WEEK.match(week):
        push("bad_week", "week", f"week must match YYYY-Www (got {week!r})")
        week = None

    try:
        snap = dt.date.fromisoformat(str(doc.get("snapshot_date", "")))
    except ValueError:
        snap = None
    if snap is None:
        push("bad_snapshot_date", "snapshot_date",
             "snapshot_date must be YYYY-MM-DD (Toronto) — set it before freezing")

    themes = doc.get("themes")
    if not isinstance(themes, list) or not themes:
        push("no_themes", "themes", "candidate carries zero themes — nothing to review")
        themes = []
    if len(themes) > 7:
        push("too_many_themes", "themes",
             f"{len(themes)} themes in one week (homepage shows 3-7) — demote extras to Noise/Draft")

    for i, t in enumerate(themes):
        base = f"themes[{i}]"
        tid = t.get("id", f"index-{i}") if isinstance(t, dict) else f"index-{i}"
        if not isinstance(t, dict):
            push("theme_not_object", base, f"theme {tid} must be an object")
            continue
        loc = f"{base}.{tid}"
        if week and t.get("week") != week:
            push("week_mismatch", f"{loc}.week",
                 f"theme week {t.get('week')!r} != candidate week {week!r}")
        # --- performance / excess math (reviewer rule: >0.2pp mismatch) ---
        p = t.get("performance") or {}
        for suffix in ("1w", "1m", "ytd"):
            ret, bret, exc = p.get(f"ret_{suffix}"), p.get(f"benchmark_ret_{suffix}"), p.get(f"excess_{suffix}")
            if isinstance(ret, (int, float)) and isinstance(bret, (int, float)) \
                    and isinstance(exc, (int, float)):
                if abs(exc - (ret - bret)) > 0.2:
                    push("excess_mismatch", f"{loc}.performance.excess_{suffix}",
                         f"excess_{suffix}={exc} vs ret-benchmark={(ret - bret):.2f} (>0.2pp) — recheck numbers")
        for k in ("proxy_price", "ret_1w", "ret_1m", "ret_ytd",
                  "benchmark_ret_1w", "benchmark_ret_1m", "benchmark_ret_ytd",
                  "excess_1w", "excess_1m", "excess_ytd"):
            if not isinstance(p.get(k), (int, float)):
                push("missing_performance_field", f"{loc}.performance.{k}",
                     f"performance.{k} must be a number (got {p.get(k)!r})")
        if not p.get("as_of_utc") or not p.get("source") or not p.get("benchmark_rationale"):
            push("missing_performance_source", f"{loc}.performance",
                 "performance needs as_of_utc + source + benchmark_rationale (unpublishable without)")
        as_of = _parse_moment(p.get("as_of_utc")) if p.get("as_of_utc") else None
        if p.get("as_of_utc") and as_of is None:
            push("bad_as_of", f"{loc}.performance.as_of_utc",
                 f"as_of_utc {p.get('as_of_utc')!r} is not ISO8601")
        elif as_of is not None and snap is not None:
            age_days = (snap - as_of.astimezone(TORONTO).date()).days
            if age_days > 7:
                push("stale_performance", f"{loc}.performance.as_of_utc",
                     f"as_of {p.get('as_of_utc')} is {age_days}d older than snapshot_date "
                     f"{snap} — re-pull or mark unavailable")
        # --- chain: formation arc (3-5 steps, label <=12w + plain-English detail <=30w) ---
        chain = t.get("chain")
        if not isinstance(chain, list) or not chain:
            push("missing_chain", f"{loc}.chain",
                 "chain missing — every theme needs 3-5 formation steps for Home cards")
        else:
            if not 3 <= len(chain) <= 5:
                push("chain_count", f"{loc}.chain",
                     f"chain count {len(chain)} not in 3-5")
            for j, s in enumerate(chain):
                lab = s.get("label") if isinstance(s, dict) else None
                if not lab:
                    push("chain_gap", f"{loc}.chain[{j}].label", "chain step label missing")
                elif _en_words(str(lab)) > 12:
                    push("chain_label_long", f"{loc}.chain[{j}].label",
                         f"chain label {_en_words(str(lab))} words > 12 — keep steps scannable")
                when = s.get("when") if isinstance(s, dict) else None
                if not when:
                    push("chain_when_gap", f"{loc}.chain[{j}].when",
                         "chain step date missing — each step needs a short 'when' label")
                elif len(str(when)) > 20:
                    push("chain_when_long", f"{loc}.chain[{j}].when",
                         f"chain when {len(str(when))} chars > 20 — keep it a short date label")
                det = s.get("detail") if isinstance(s, dict) else None
                if not det:
                    push("chain_detail_gap", f"{loc}.chain[{j}].detail",
                         "chain step detail missing — each step needs a plain-English sentence")
                elif _en_words(str(det)) > 30:
                    push("chain_detail_long", f"{loc}.chain[{j}].detail",
                         f"chain detail {_en_words(str(det))} words > 30 — one or two short sentences")
        # --- summary: pre-click overview (<=100w, carries proxy vs benchmark) ---
        summ = t.get("summary") or ""
        if not summ:
            push("missing_summary", f"{loc}.summary",
                 "summary missing — every theme needs a <=100-word pre-click overview")
        else:
            if _en_words(str(summ)) > 100:
                push("summary_too_long", f"{loc}.summary",
                     f"summary EN words {_en_words(str(summ))} > 100 — cut to the overview budget")
        # --- body 2-min core + up to 5min folded (legacy caliber 500w = 5min) ---
        body = t.get("body_text") or ""
        expl = t.get("explainer") or ""
        if _cjk_len(body) > 360:
            push("body_too_long", f"{loc}.body_text",
                 f"body CJK chars {_cjk_len(body)} > 360 (>2min core) — cut or split")
        if _en_words(body) > 200:
            push("body_too_long", f"{loc}.body_text",
                 f"body EN words {_en_words(body)} > 200 (>2min core) — cut or split")
        total_words = _en_words(body) + _en_words(str(expl) if isinstance(expl, str) else "")
        if total_words > 500:
            push("body_too_long", f"{loc}.body_text",
                 f"body+explainer EN words {total_words} > 500 (>5min total) — cut or split")
        # --- series ---
        series = t.get("series")
        if not isinstance(series, list) or len(series) < 2:
            push("series_too_short", f"{loc}.series", "series needs >= 2 rebased points")
        # --- proxies 1-3 / ETF expense / liquidity ---
        proxies = t.get("proxies")
        if not isinstance(proxies, list) or not 1 <= len(proxies) <= 3:
            n = len(proxies) if isinstance(proxies, list) else 0
            push("proxy_count", f"{loc}.proxies",
                 f"proxies count {n} not in 1-3 — pick liquid ETF > Index > Basket")
        else:
            for j, px in enumerate(proxies):
                for k in ("ticker", "name", "type", "region",
                          "liquidity_note", "why_represents", "tracking_gap"):
                    if not (isinstance(px, dict) and px.get(k)):
                        push("proxy_gap", f"{loc}.proxies[{j}].{k}",
                             f"proxies[{j}].{k} missing — state tradability + tracking defect")
                if isinstance(px, dict) and px.get("type") == "ETF" and not px.get("expense"):
                    push("proxy_gap", f"{loc}.proxies[{j}].expense",
                         "ETF proxy needs expense (fee) — required")
        # --- events: no time+source = unpublishable ---
        events = t.get("events")
        if not isinstance(events, list) or not events:
            push("no_events", f"{loc}.events", "events empty — no time+source, unpublishable")
        else:
            for j, ev in enumerate(events):
                ef = f"{loc}.events[{j}]"
                if not (isinstance(ev, dict) and ev.get("event_time_utc")):
                    push("missing_event_time_source", ef,
                         "event missing event_time_utc — UNPUBLISHABLE")
                elif _parse_moment(ev.get("event_time_utc")) is None:
                    push("missing_event_time_source", ef + ".event_time_utc",
                         f"event_time_utc {ev.get('event_time_utc')!r} is not ISO8601")
                if not (isinstance(ev, dict) and ev.get("source")):
                    push("missing_event_time_source", ef,
                         "event missing source — UNPUBLISHABLE")
                url = ev.get("url") if isinstance(ev, dict) else None
                if not (isinstance(url, str) and _HTTPS.match(url)):
                    push("missing_event_time_source", ef + ".url",
                         f"event url must be https:// (got {url!r})")
                # Key Events must carry benchmarked returns going forward.
                if isinstance(ev, dict) and (
                    ev.get("proxy_ret") is None or ev.get("benchmark_ret") is None
                    or not ev.get("return_window")
                ):
                    push("missing_event_return", ef,
                         "event missing proxy_ret/benchmark_ret/return_window — "
                         "each Key Event must show proxy return vs benchmark return")
        # --- depends_on: no catalyst -> Noise ---
        depends = t.get("depends_on")
        if not isinstance(depends, list) or not depends:
            push("no_next_catalyst", f"{loc}.depends_on",
                 "no next catalyst — demote to Noise per PRD")
        else:
            for j, d in enumerate(depends):
                for k in ("event_name", "due_date", "why_matters", "if_bull", "if_bear"):
                    if not (isinstance(d, dict) and d.get(k)):
                        push("missing_catalyst_field", f"{loc}.depends_on[{j}].{k}",
                             f"depends_on[{j}].{k} missing (need bull + bear/falsifiable case)")
        # --- theme vs noise score ---
        vn = t.get("theme_vs_noise") or {}
        keys = ("persistence", "breadth", "volume_confirm",
                "falsifiable_catalyst", "repricing_logic")
        count = sum(1 for k in keys if vn.get(k) is True)
        if vn.get("score") != count:
            push("theme_score_mismatch", f"{loc}.theme_vs_noise.score",
                 f"score={vn.get('score')} but true-count={count} — fix the count")
        if isinstance(vn.get("score"), int) and vn["score"] < 3 \
                and t.get("status") in ("New", "Continuing"):
            push("noise_on_homepage", f"{loc}.status",
                 f"score {vn['score']} < 3 but status {t.get('status')} — demote to Noise/Draft, "
                 "keep off homepage")

    ms = doc.get("market_snapshot")
    if isinstance(ms, dict) and week and ms.get("week") != week:
        push("snapshot_week_mismatch", "market_snapshot.week",
             f"market snapshot week {ms.get('week')!r} != candidate week {week!r}")
    cm = doc.get("commentary")
    if isinstance(cm, dict) and week and cm.get("week") != week:
        push("snapshot_week_mismatch", "commentary.week",
             f"commentary week {cm.get('week')!r} != candidate week {week!r}")
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
