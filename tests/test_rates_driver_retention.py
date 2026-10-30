"""Rates drivers older than the last decision are pruned unless weight > 5."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Rates_decisions" / "scripts"))

from prune_drivers import prune  # noqa: E402
from publish import validate  # noqa: E402


def _driver(did, direction, weight, day):
    third = weight // 3
    return {
        "id": did, "direction": direction, "weight": weight,
        "weight_breakdown": {"deviation": weight - 2 * third, "importance": third,
                             "surprise": third, "total": weight},
        "published_at": day, "observed_at": day,
        "source_url": "https://example.org/x", "market_validation": "FedWatch +12pp",
    }


def _doc():
    pricing = {"probabilities": {"hike": 0.5, "hold": 0.49, "cut": 0.01},
               "source_url": "https://example.org/p"}
    meeting = {"last_meeting": {"date": "2026-10-28"}, "pricing": pricing}
    return {
        "as_of": "2026-10-29T18:00:00-04:00",
        "meetings": {"fed": meeting, "boc": {**meeting}},
        "drivers": {
            "fed": {"hawkish": [_driver("f-old", 1, 4, "2026-10-14"),
                                _driver("f-big", 1, 6, "2026-10-14"),
                                _driver("f-day", 1, 2, "2026-10-28")],
                    "dovish": [_driver("f-new", -1, 3, "2026-10-29")]},
            "boc": {"hawkish": [], "dovish": [_driver("b-old", -1, 5, "2026-10-09")]},
        },
        "total_score": {"fed": {"base_total": 0, "effective_total": 0, "band": "hold"},
                        "boc": {"base_total": 0, "effective_total": 0, "band": "hold"}},
        "calendar": [],
    }


def test_check_rejects_light_drivers_from_before_last_decision():
    errors = validate(_doc())
    stale = [e for e in errors if "before last decision" in e]
    assert any("fed/f-old" in e for e in stale)
    assert any("boc/b-old" in e for e in stale)  # weight 5 is not > 5
    assert not any(tag in e for e in stale for tag in ("f-big", "f-day", "f-new"))


def test_prune_keeps_decision_day_onward_and_significant_carry_over():
    doc = _doc()
    removed = prune(doc)
    assert sorted(r.split(" ")[0] for r in removed) == ["boc/b-old", "fed/f-old"]
    assert [d["id"] for d in doc["drivers"]["fed"]["hawkish"]] == ["f-big", "f-day"]
    assert doc["drivers"]["boc"]["dovish"] == []
    # f-big is 15 days old (x0.5): 6*0.5 + 2 - 3 = 2.0
    assert doc["total_score"]["fed"] == {"base_total": 5, "effective_total": 2.0,
                                         "band": "lean hike"}
    assert doc["total_score"]["boc"] == {"base_total": 0, "effective_total": 0,
                                         "band": "hold"}
    assert validate(doc) == []
