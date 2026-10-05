"""General-theme-tracker blocking gate: flags plugin + data-only lanes.

Covers the third blocking product (general-theme-tracker/):
- structural flags mirror backend/validate.js on the weekly candidate JSON
- data-only release allows week YAMLs + archive + review bundle, rejects renderers
- publisher declares exactly six checks
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from econ.verify_data_only_changes import (
    classify_changes, validate_paths, verify_template_binding,
)
from review.flags_general_theme_tracker import structural_flags

REPO = Path(__file__).resolve().parents[1]
GTT = REPO / "general-theme-tracker"


def _spec_load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _good_theme(theme_id="t1"):
    return {
        "schema_v": 1, "id": theme_id, "week": "2026-W40", "title": "t",
        "status": "Continuing", "status_note": "n", "conviction": "Med",
        "horizon": "Cyclical 3-12m", "created_at": "2026-10-01",
        "updated_at": "2026-10-04", "body_text": "short body",
        "performance": {
            "proxy_ticker": "QQQ", "proxy_price": 10.0, "currency": "USD",
            "return_type": "price", "ret_1w": 1.0, "ret_1m": 2.0, "ret_ytd": 3.0,
            "benchmark_ticker": "SPX", "benchmark_name": "S&P 500",
            "benchmark_ret_1w": 0.5, "benchmark_ret_1m": 1.0, "benchmark_ret_ytd": 1.5,
            "excess_1w": 0.5, "excess_1m": 1.0, "excess_ytd": 1.5,
            "as_of_utc": "2026-10-04T12:00:00Z", "source": "Yahoo",
            "benchmark_rationale": "US tech vs SPX",
        },
        "series": [
            {"date": "2026-10-01", "proxy": 100.0, "benchmark": 100.0},
            {"date": "2026-10-02", "proxy": 101.0, "benchmark": 100.5},
        ],
        "proxies": [{
            "ticker": "QQQ", "name": "Invesco QQQ", "type": "ETF", "region": "US",
            "expense": "0.20%", "liquidity_note": "deep",
            "why_represents": "tracks NDX", "tracking_gap": "no dividend",
        }],
        "events": [{
            "event_time_utc": "2026-10-02T12:00:00Z", "title": "payrolls",
            "source": "BLS", "url": "https://www.bls.gov/news.htm", "type": "macro",
        }],
        "depends_on": [{
            "event_name": "CPI", "due_date": "2026-10-15", "why_matters": "m",
            "if_bull": "cool", "if_bear": "hot",
        }],
        "theme_vs_noise": {
            "persistence": True, "breadth": True, "volume_confirm": True,
            "falsifiable_catalyst": True, "repricing_logic": False, "score": 4,
        },
    }


def _candidate(**overrides):
    doc = {
        "snapshot_date": "2026-10-04", "week": "2026-W40",
        "themes": [_good_theme()],
        "market_snapshot": {"week": "2026-W40"},
        "commentary": {"week": "2026-W40"},
    }
    doc.update(overrides)
    return doc


def test_flags_empty_on_clean_candidate():
    assert structural_flags(_candidate()) == []


def test_flags_catch_excess_event_score_and_noise():
    bad = _good_theme()
    bad["performance"]["excess_1w"] = 9.9
    bad["events"] = [{"title": "no time/source/url"}]
    bad["theme_vs_noise"] = {
        "persistence": True, "breadth": False, "volume_confirm": False,
        "falsifiable_catalyst": False, "repricing_logic": False, "score": 2,
    }
    bad["status"] = "New"
    codes = {f["code"] for f in structural_flags(_candidate(themes=[bad]))}
    assert {"excess_mismatch", "missing_event_time_source",
            "theme_score_mismatch", "noise_on_homepage"} <= codes


def test_flags_catch_stale_proxy_and_week_drift():
    bad = _good_theme()
    bad["performance"]["as_of_utc"] = "2026-09-01T12:00:00Z"
    bad["proxies"] = [{"ticker": "X", "name": "n", "type": "ETF", "region": "US"}]
    doc = _candidate(themes=[bad],
                     market_snapshot={"week": "2026-W39"})
    codes = {f["code"] for f in structural_flags(doc)}
    assert {"stale_performance", "proxy_gap", "snapshot_week_mismatch"} <= codes


def test_publisher_declares_six_blocking_checks():
    publish = _spec_load("gtt_publish", GTT / "scripts" / "publish.py")
    assert publish.THEME_CHECKS == [
        "excess_math", "timing_source", "freshness",
        "readability", "theme_noise", "proxy_tradability",
    ]
    assert publish.validate(_candidate()) == []
    assert publish.validate(_candidate(themes=[]))


def test_data_release_allows_week_bundle_and_review_bundle():
    allowed = [
        "general-theme-tracker/data/themes/2026-W40/theme_ai_capex_supercycle.yaml",
        "general-theme-tracker/data/market/snapshot_2026-W40.yaml",
        "general-theme-tracker/data/commentary/2026-W40.yaml",
        "general-theme-tracker/data/archive/2026-10-04.json",
        "general-theme-tracker/review/2026-10-04/candidate.json",
        "general-theme-tracker/review/2026-10-04/candidate.sha256",
        "general-theme-tracker/review/2026-10-04/structural-flags.json",
        "general-theme-tracker/review/2026-10-04/pm-review.json",
        "general-theme-tracker/review/2026-10-04/review.md",
    ]
    assert validate_paths(allowed, "general-theme-tracker") == []
    assert classify_changes(allowed, "push") == []


def test_data_lane_rejects_renderers_schema_and_legacy_reviews():
    rejected = [
        "general-theme-tracker/frontend/src/pages/Home.tsx",
        "general-theme-tracker/frontend/src/lib/api.ts",
        "general-theme-tracker/backend/server.js",
        "general-theme-tracker/scripts/publish.py",
        "general-theme-tracker/data/schema/theme.schema.yaml",
        "general-theme-tracker/data/reviews/2026-W40.reviews.yaml",
    ]
    assert validate_paths(rejected, "general-theme-tracker") == rejected


def test_classification_blocks_mixed_data_frontend_bundle():
    contract = "scripts/econ/frontend_contract.json"
    assert classify_changes(
        ["general-theme-tracker/frontend/src/pages/Home.tsx",
         "general-theme-tracker/frontend/src/lib/api.ts",
         "general-theme-tracker/frontend/src/pages/ThemeDetail.tsx",
         "general-theme-tracker/frontend/src/pages/Archive.tsx", contract], "push") == []
    assert classify_changes(
        ["general-theme-tracker/frontend/src/pages/Home.tsx"], "push")
    assert classify_changes(
        ["general-theme-tracker/data/themes/2026-W40/theme_x.yaml",
         "general-theme-tracker/frontend/src/pages/Home.tsx", contract], "push")


def test_template_binding_covers_four_renderer_files(tmp_path):
    root = tmp_path
    for rel in ("frontend/src/pages/Home.tsx", "frontend/src/pages/ThemeDetail.tsx",
                "frontend/src/pages/Archive.tsx", "frontend/src/lib/api.ts"):
        target = root / "general-theme-tracker" / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        src = (REPO / "general-theme-tracker" / rel).read_bytes()
        target.write_bytes(src)
    manifest = json.loads((REPO / "scripts" / "econ" / "frontend_contract.json")
                          .read_text(encoding="utf-8"))
    contract = root / "scripts" / "econ" / "frontend_contract.json"
    contract.parent.mkdir(parents=True)
    contract.write_text(json.dumps({
        "economic-calendar": "0" * 64,
        "Rates_decisions": {"index.html": "0" * 64, "app.js": "0" * 64, "styles.css": "0" * 64},
        "general-theme-tracker": manifest["general-theme-tracker"],
    }), encoding="utf-8")
    assert verify_template_binding(root, "general-theme-tracker") == []
    (root / "general-theme-tracker" / "frontend/src/lib/api.ts").write_text("changed", encoding="utf-8")
    assert verify_template_binding(root, "general-theme-tracker") == [
        "general-theme-tracker/frontend/src/lib/api.ts"]
