"""Tests for the 2026-09-28 gates.

Each of these corresponds to a real defect that shipped far enough to be caught
by a portfolio manager. The comment on each names the incident; that is the
point -- a test without an incident behind it tends to get deleted the next time
the file is "cleaned up".
"""
from __future__ import annotations

import hashlib
import json

import pytest

from econ.structural_gate import (
    CHECKS,
    RUNNERS,
    check_evidence_contains_claim,
    check_price_threshold_arithmetic,
    check_published_path_provenance,
    run_all,
)


def _driver(**overrides):
    base = {
        "id": "fed_dovish_test_20260925",
        "source_url": "https://example.invalid/src",
        "published_at_toronto": "2026-09-25T10:00:00-04:00",
        "data": {"actual": "48.1", "forecast": "47.6", "previous": "51.7"},
    }
    base.update(overrides)
    return base


def _payload(drivers):
    return {
        "as_of": "2026-09-28T19:05:00-04:00",
        "drivers": {"fed": {"dovish": drivers, "hawkish": []},
                    "boc": {"dovish": [], "hawkish": []}},
        "decision_brief": {"as_of_toronto": "2026-09-28T19:05:00-04:00"},
    }


# --------------------------------------------------------------------------- #
# incident: Michigan showed 48.1 while the bound capture held only the
# preliminary 47.8. The number was right and had no evidence at all.
# --------------------------------------------------------------------------- #
def test_displayed_value_must_appear_in_its_own_capture(tmp_path):
    capture = tmp_path / "umich.html"
    capture.write_text("<html>September preliminary 47.8, August 51.7</html>", encoding="utf-8")
    payload = _payload([_driver(source_provenance={
        "actual_evidence": str(capture),
        "actual_sha256": hashlib.sha256(capture.read_bytes()).hexdigest(),
    })])
    problems = check_evidence_contains_claim(payload)
    assert any("48.1" in p and "no evidence" in p for p in problems), (
        "48.1 is displayed but absent from the bound capture; that must fail"
    )


def test_value_present_in_its_capture_passes(tmp_path):
    capture = tmp_path / "umich.html"
    capture.write_text("<html>final 48.1, consensus 47.6, prior 51.7</html>", encoding="utf-8")
    payload = _payload([_driver(source_provenance={
        "actual_evidence": str(capture),
        "actual_sha256": hashlib.sha256(capture.read_bytes()).hexdigest(),
    })])
    assert check_evidence_contains_claim(payload) == []


def test_consensus_and_previous_may_live_in_separate_captures(tmp_path):
    """The real fix: three sources, each carrying one of the three numbers."""
    a = tmp_path / "a.html"; a.write_text("final 48.1", encoding="utf-8")
    b = tmp_path / "b.html"; b.write_text("forecast 47.6", encoding="utf-8")
    c = tmp_path / "c.html"; c.write_text("prior 51.7", encoding="utf-8")
    payload = _payload([_driver(source_provenance={
        "actual_evidence": str(a), "consensus_evidence": str(b), "previous_evidence": str(c),
    })])
    assert check_evidence_contains_claim(payload) == []


def test_missing_capture_is_not_this_checks_business(tmp_path):
    """A driver with no readable evidence is provenance's problem, not a false positive here."""
    payload = _payload([_driver(source_provenance={"actual_evidence": "does/not/exist.html"})])
    assert check_evidence_contains_claim(payload) == []


# --------------------------------------------------------------------------- #
# incident: the brief claimed ZQV26 95.65-96.57 meant 'above 4.00% / below
# 3.75%'. 100-95.65 = 4.35% and 100-96.57 = 3.43%: ~35bp too wide each side.
# --------------------------------------------------------------------------- #
def test_price_threshold_must_satisfy_100_minus_price():
    payload = {"decision_brief": {
        "as_of_toronto": "2026-09-28T19:05:00-04:00",
        "price_thresholds": [{"instrument": "ZQV26", "basis": "100 - price",
                              "low_price": 96.00, "low_implied_rate": 4.00,
                              "high_price": 96.25, "high_implied_rate": 3.75}],
        "falsifiers": ["ZQV26 outside 96.00-96.25 breaks the premise"],
        "banks": {},
    }}
    assert check_price_threshold_arithmetic(payload) == []


def test_the_actual_2026_09_28_mistake_is_now_caught():
    payload = {"decision_brief": {
        "as_of_toronto": "2026-09-28T19:05:00-04:00",
        "price_thresholds": [{"instrument": "ZQV26", "basis": "100 - price",
                              "low_price": 95.65, "low_implied_rate": 4.00,
                              "high_price": 96.57, "high_implied_rate": 3.75}],
        "falsifiers": ["ZQV26 outside 95.65-96.57"],
        "banks": {},
    }}
    problems = check_price_threshold_arithmetic(payload)
    assert any("100 - 95.65 = 4.35" in p for p in problems)


def test_threshold_the_reader_never_sees_is_flagged():
    """A structured number that no rendered string quotes is not a threshold a PM can act on."""
    payload = {"decision_brief": {
        "as_of_toronto": "2026-09-28T19:05:00-04:00",
        "price_thresholds": [{"instrument": "ZQV26", "basis": "100 - price",
                              "low_price": 96.00, "low_implied_rate": 4.00,
                              "high_price": 96.25, "high_implied_rate": 3.75}],
        "falsifiers": ["something qualitative with no numbers at all"],
        "banks": {},
    }}
    assert any("appears in no falsifier" in p for p in check_price_threshold_arithmetic(payload))


def test_no_thresholds_is_not_a_failure():
    payload = {"decision_brief": {"as_of_toronto": "2026-09-28T19:05:00-04:00",
                                  "falsifiers": ["x"], "banks": {}}}
    assert check_price_threshold_arithmetic(payload) == []


# --------------------------------------------------------------------------- #
# incident: a frozen candidate was copied over data/latest.json for a render
# check, and the restore was a no-op because the backup was taken afterwards.
# --------------------------------------------------------------------------- #
def test_unapproved_candidate_in_the_published_path_is_caught(tmp_path, monkeypatch):
    """A frozen candidate copied over data/latest.json must be distinguishable
    from a publication. The real incident: the restore was a no-op because the
    backup had been taken after the overwrite, and only `git status` noticed."""
    import econ.structural_gate as gate

    root = tmp_path / "repo"
    (root / "fed-boc-watcher" / "data").mkdir(parents=True)
    (root / "fed-boc-watcher" / "review" / "2026-09-27" / "iteration-01").mkdir(parents=True)
    arts = root / "review-artifacts"
    arts.mkdir()

    # an approved, older candidate
    old = root / "fed-boc-watcher" / "review" / "2026-09-27" / "iteration-01" / "candidate.json"
    old.write_text(json.dumps({"as_of": "2026-09-27T05:00:00-04:00"}), encoding="utf-8")
    old_sha = hashlib.sha256(old.read_bytes()).hexdigest()
    (arts / "pm-review-old.json").write_text(
        json.dumps({"verdict": "approved", "candidate_sha256": old_sha}), encoding="utf-8")

    # a REJECTED newer candidate, which must not be able to masquerade as published
    (root / "fed-boc-watcher" / "review" / "2026-09-27" / "iteration-02").mkdir(parents=True)
    new = root / "fed-boc-watcher" / "review" / "2026-09-27" / "iteration-02" / "candidate.json"
    new.write_text(json.dumps({"as_of": "2026-09-28T19:05:00-04:00"}), encoding="utf-8")

    latest = root / "fed-boc-watcher" / "data" / "latest.json"
    latest.write_text(json.dumps({"as_of": "2026-09-28T19:05:00-04:00"}), encoding="utf-8")

    monkeypatch.setattr(gate, "REPO_ROOT", root)
    problems = check_published_path_provenance()
    assert any("newer than the newest approved candidate" in p for p in problems), (
        f"a rejected candidate staged in data/latest.json must be caught: {problems}"
    )


def test_legitimately_published_approved_candidate_passes(tmp_path, monkeypatch):
    import econ.structural_gate as gate

    root = tmp_path / "repo"
    (root / "fed-boc-watcher" / "data").mkdir(parents=True)
    (root / "fed-boc-watcher" / "review" / "2026-09-27" / "iteration-01").mkdir(parents=True)
    arts = root / "review-artifacts"
    arts.mkdir()
    cand = root / "fed-boc-watcher" / "review" / "2026-09-27" / "iteration-01" / "candidate.json"
    cand.write_text(json.dumps({"as_of": "2026-09-28T19:05:00-04:00"}), encoding="utf-8")
    (arts / "pm-review.json").write_text(json.dumps(
        {"verdict": "approved",
         "candidate_sha256": hashlib.sha256(cand.read_bytes()).hexdigest()}), encoding="utf-8")
    (root / "fed-boc-watcher" / "data" / "latest.json").write_text(
        json.dumps({"as_of": "2026-09-28T19:05:00-04:00"}), encoding="utf-8")

    monkeypatch.setattr(gate, "REPO_ROOT", root)
    assert check_published_path_provenance() == []


def test_no_approved_reviews_means_nothing_to_breach(tmp_path, monkeypatch):
    import econ.structural_gate as gate

    root = tmp_path / "repo"
    (root / "fed-boc-watcher" / "data").mkdir(parents=True)
    (root / "fed-boc-watcher" / "data" / "latest.json").write_text(
        json.dumps({"as_of": "2026-09-28T19:05:00-04:00"}), encoding="utf-8")
    monkeypatch.setattr(gate, "REPO_ROOT", root)
    assert check_published_path_provenance() == []


def test_working_tree_check_can_be_skipped():
    results = run_all({"as_of": "2026-09-28T19:05:00-04:00"}, include_working_tree=False)
    assert "published_path_provenance" not in results
    assert "evidence_contains_claim" in results


def test_enumerated_brief_fields_are_checked_too(tmp_path, monkeypatch):
    """The historical three are in the enumerated list, not the catch-all loop.

    Covering only the catch-all left the enumerated branch unverified: mutating
    `if field not in html:` inside the first loop changed nothing in the suite.
    Point the gate at a stripped index.html so the enumerated branch is the only
    thing that can fire.
    """
    import econ.structural_gate as gate

    root = tmp_path / "repo"
    (root / "fed-boc-watcher").mkdir(parents=True)
    (root / "fed-boc-watcher" / "index.html").write_text(
        "<html><body>no decision frame at all</body></html>", encoding="utf-8")
    monkeypatch.setattr(gate, "REPO_ROOT", root)

    payload = {"decision_brief": {
        "as_of_toronto": "2026-09-28T19:05:00-04:00",
        "what_is_priced": {"fed": "..."}, "falsifiers": ["..."], "attention_budget": "...",
    }}
    problems = gate.check_renderer_contract(payload)
    for field in ("what_is_priced", "falsifiers", "attention_budget"):
        assert any(field in p for p in problems), f"{field} is enumerated but was not flagged"


def test_wired_page_passes_the_enumerated_branch():
    from econ.structural_gate import check_renderer_contract
    ok = check_renderer_contract({"decision_brief": {
        "as_of_toronto": "2026-09-28T19:05:00-04:00",
        "what_is_priced": {"fed": "..."}, "falsifiers": ["..."],
        "attention_budget": "...", "banks": {}, "summary": "s",
        "changes_since_previous": ["c"], "largest_pnl_risks": ["r"],
        "source_references": [{"url": "u", "label": "l", "observed_at_toronto": "t"}],
        "trade_status": "NO TRADE / NO EDGE",
    }})
    assert not any("never reads it" in p for p in ok)


def test_matching_row_is_the_evidence_not_the_whole_file(tmp_path):
    """Round 3: the PM caught the gate's own false positive.

    The card claimed a June headline of +0.6% was unevidenced and the gate agreed.
    But the bound FXStreet capture pins a matching_row whose previous IS 0.6 for
    that exact event, and the same figure also appears in the statcan capture as
    the NOVA SCOTIA provincial row. Restoring +0.6% must pass, on the matching_row.
    """
    fx = tmp_path / "fx.csv"
    fx.write_text(json.dumps([{"name": "Retail Sales (MoM)", "previous": 0.6,
                               "consensus": -0.8, "actual": -0.7, "countryCode": "CA"}]),
                  encoding="utf-8")
    payload = _payload([_driver(source_provenance={
        "forecast_previous_source": {
            "evidence_path": str(fx),
            "matching_row": {"name": "Retail Sales (MoM)", "previous": 0.6,
                             "consensus": -0.8, "actual": -0.7},
        }})])
    payload["drivers"]["boc"]["dovish"] = [{
        "id": "boc_dove_retail_jul2026_20260924",
        "source_url": "https://example.invalid/statcan",
        "data": {"actual": "-0.7%", "forecast": "-0.8%", "previous": "+0.6%"},
        "source_provenance": payload["drivers"]["fed"]["dovish"][0]["source_provenance"],
    }]
    payload["drivers"]["fed"]["dovish"] = []
    assert check_evidence_contains_claim(payload) == [], (
        "a value evidenced by the card's own matching_row must not be flagged"
    )


def test_number_absent_from_the_pinned_matching_row_is_flagged(tmp_path):
    """The branch that actually failed in round 3: the card pins a row, and the
    value is not in it. Mutating this branch to a no-op left the suite green."""
    fx = tmp_path / "fx.csv"
    fx.write_text(json.dumps([
        {"name": "Retail Sales (MoM)", "previous": 0.6, "consensus": -0.8, "actual": -0.7},
        {"name": "Other Event", "previous": 1.9, "consensus": 2.0, "actual": 2.1},
    ]), encoding="utf-8")
    payload = {"as_of": "2026-09-28T19:05:00-04:00", "drivers": {
        "fed": {"dovish": [], "hawkish": []},
        "boc": {"dovish": [{
            "id": "boc_retail", "source_url": "https://example.invalid/fx",
            "data": {"actual": "-0.7%", "previous": "+1.9%"},
            "source_provenance": {"forecast_previous_source": {
                "evidence_path": str(fx),
                "matching_row": {"name": "Retail Sales (MoM)", "previous": 0.6,
                                 "consensus": -0.8, "actual": -0.7},
            }},
        }], "hawkish": []}},
        "decision_brief": {"as_of_toronto": "2026-09-28T19:05:00-04:00"}}
    problems = check_evidence_contains_claim(payload)
    assert any("matching_row" in p for p in problems), (
        f"1.9 belongs to another row; the pinned row says 0.6: {problems}"
    )


def test_number_found_only_in_a_provincial_row_is_still_flagged(tmp_path):
    """The flip side: 0.6 as the Nova Scotia row does not evidence Canada."""
    statcan = tmp_path / "statcan.html"
    rows = [
        "Retail sales - Canada $73.7 billion July 2026 -0.7% (monthly change)",
        "Retail sales - N.L. $1.1 billion July 2026 -1.5%",
        "Retail sales - P.E.I. $0.3 billion July 2026 0.2%",
        "Retail sales - N.S. $2.0 billion July 2026 0.6%",
        "Retail sales - N.B. $1.6 billion July 2026 1.6%",
        "Retail sales - Que. $16.2 billion July 2026 -0.0%",
        "Retail sales - Ont. $27.9 billion July 2026 -2.0%",
        "Retail sales - Man. $2.5 billion July 2026 -0.4%",
        "Retail sales - Sask. $2.3 billion July 2026 0.4%",
        "Retail sales - Alta. $9.8 billion July 2026 0.7%",
        "Retail sales - B.C. $14.0 billion July 2026 -0.2%",
    ]
    statcan.write_text("<html><table>" + "".join(f"<tr><td>{r}</td></tr>" for r in rows)
                       + "</table></html>", encoding="utf-8")
    payload = {"as_of": "2026-09-28T19:05:00-04:00", "drivers": {
        "fed": {"dovish": [], "hawkish": []},
        "boc": {"dovish": [{
            "id": "boc_retail", "source_url": "https://example.invalid/statcan",
            "data": {"actual": "-0.7%", "previous": "+0.6%"},
            "source_provenance": {"actual_source": {"evidence_path": str(statcan)}},
        }], "hawkish": []}},
        "decision_brief": {"as_of_toronto": "2026-09-28T19:05:00-04:00"}}
    problems = check_evidence_contains_claim(payload)
    assert any("0.6" in p for p in problems), (
        f"a provincial-only hit must not pass as national evidence: {problems}"
    )


def test_decimal_format_variants_all_match():
    """Every spelling of 0.6 in a payload must match a 0.6 / 0.60 / 0.600 capture."""
    from econ.structural_gate import _numeric_variants
    for value in ("+0.6%", "0.60%", "0.6%", ".6%", "\u22120.6".replace("\u2212", "-") + "0.6%"):
        variants = _numeric_variants(value)
        assert {"0.6", "0.60", "0.600"} & variants, (
            f"{value!r} -> {sorted(variants)} must match a 0.6 / 0.60 / 0.600 capture"
        )


def test_variants_never_leak_the_sign_or_a_digit_fragment():
    """'-6' for '0.6%' and '+0.6' for '+0.6%' are what broke the round-3 match."""
    from econ.structural_gate import _numeric_variants
    for value in ("+0.6%", "0.6%", "48.1", "+162k"):
        variants = _numeric_variants(value)
        assert not any(v.startswith(("+", "-")) for v in variants), (
            f"{value!r} produced a signed fragment: {sorted(variants)}"
        )
        assert "6" not in variants and "0.1" not in variants or value == "48.1", (
            f"{value!r} produced a bare digit fragment: {sorted(variants)}"
        )


def test_registry_stays_in_sync():
    """Adding a check without a runner (or vice versa) is a silent coverage hole."""
    assert set(CHECKS) == set(RUNNERS)
    for name in ("evidence_contains_claim", "published_path_provenance",
                 "price_threshold_arithmetic", "renderer_contract"):
        assert name in CHECKS
