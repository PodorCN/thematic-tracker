"""Tests for the structural gate.

Every check here is arithmetic or hash comparison.  None of them parse English:
the previous gate's prose checks were evaded by synonym edits across two
independent PM reviews, so they were removed rather than patched.
"""
from __future__ import annotations

import hashlib
import json

import pytest

from econ.structural_gate import (
    check_as_of_coherence,
    check_derived_numbers,
    check_driver_side_signs,
    check_market_close_semantics,
    check_pricing_honesty,
    check_provenance_traceability,
    check_required_containment,
    run_all,
)


def _payload(**overrides):
    payload = {
        "as_of": "2026-09-28T18:05:00-04:00",
        "version": "2026-09-28-002",
        "market": {
            "as_of_toronto": "2026-09-28T05:28:48-04:00",
            "as_of_close": "2026-09-25T16:00:00-04:00",
            "tickers": [{
                "symbol": "SPY", "price": 771.35,
                "chg_1d": 0.005435, "base_1d_price": 767.18,
                "chg_1w": 0.012682, "base_1w_price": 761.69,
                "session_date": "2026-09-25",
                "observed_at_toronto": "2026-09-25T16:00:00-04:00",
            }],
        },
        "meetings": {
            "fed": {"pricing": {"probability_status": "unavailable", "cut_25bp": None,
                                "hold": None, "hike_25bp": None}},
            "boc": {"pricing": {"probability_status": "unavailable", "cut_25bp": None,
                                "hold": None, "hike_25bp": None}},
        },
        "drivers": {
            "fed": {"dovish": [], "hawkish": []},
            "boc": {"dovish": [], "hawkish": []},
        },
        "calendar": [],
        "decision_brief": {"as_of_toronto": "2026-09-28T18:05:00-04:00"},
    }
    payload.update(overrides)
    return payload


# --------------------------------------------------------------------------- #
# containment: absence fails closed (closes the 2026-09-28 deletion bypass)
# --------------------------------------------------------------------------- #
def test_stripped_payload_is_rejected():
    problems = check_required_containment(
        {"as_of": "2026-09-28T18:05:00-04:00", "market": {"return_basis_note": "x"},
         "meetings": {"fed": {}, "boc": {}}, "drivers": {}}
    )
    assert any("decision_brief" in p for p in problems)
    assert any("provenance" in p for p in problems)
    assert any("evidence_manifest" in p for p in problems)


def test_empty_stub_is_rejected():
    problems = check_required_containment({"as_of": "2026-09-28T18:05:00-04:00"})
    assert problems


def test_complete_payload_passes_containment(tmp_path):
    evidence = tmp_path / "spy.json"
    evidence.write_text("{}", encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    manifest.write_text("{}", encoding="utf-8")
    payload = _payload(evidence_manifest={"path": str(manifest)})
    payload["market"]["tickers"][0]["source_provenance"] = {
        "daily_close": {
            "source_url": "https://example.invalid/spy",
            "evidence_path": str(evidence),
            "sha256": hashlib.sha256(evidence.read_bytes()).hexdigest(),
        }
    }
    assert check_required_containment(payload) == []


# --------------------------------------------------------------------------- #
# the BoC retail sign error the PM found
# --------------------------------------------------------------------------- #
def test_contraction_on_the_hawkish_side_is_flagged():
    payload = _payload()
    payload["drivers"]["boc"]["hawkish"] = [{
        "id": "boc_hawk_retail_20260924",
        "source_url": "https://example.invalid/statcan",
        "data": {"actual": "-0.7", "delta_type": "beat"},
    }]
    problems = check_driver_side_signs(payload)
    assert problems
    assert any("growth-negative" in p for p in problems)


def test_contraction_on_the_dovish_side_is_fine():
    payload = _payload()
    payload["drivers"]["boc"]["dovish"] = [{
        "id": "boc_dove_retail_20260924",
        "source_url": "https://example.invalid/statcan",
        "data": {"actual": "-0.7", "delta_type": "contraction"},
    }]
    assert check_driver_side_signs(payload) == []


def test_positive_beat_on_the_hawkish_side_is_fine():
    payload = _payload()
    payload["drivers"]["fed"]["hawkish"] = [{
        "id": "fed_hawk_cpi_20260812",
        "source_url": "https://example.invalid/bls",
        "data": {"actual": "0.4", "delta_type": "beat"},
    }]
    assert check_driver_side_signs(payload) == []


def test_numeric_actual_as_number_is_handled():
    payload = _payload()
    payload["drivers"]["fed"]["hawkish"] = [{
        "id": "fed_hawk_cpi_20260812",
        "source_url": "https://example.invalid/bls",
        "data": {"actual": -0.7, "delta_type": "beat"},
    }]
    assert check_driver_side_signs(payload)


# --------------------------------------------------------------------------- #
# arithmetic and hashes
# --------------------------------------------------------------------------- #
def test_chg_must_recompute_from_its_bases():
    payload = _payload()
    payload["market"]["tickers"][0]["chg_1w"] = 0.137698
    problems = check_derived_numbers(payload)
    assert problems
    assert any("chg_1w" in p for p in problems)


def test_close_must_be_observed_at_or_after_1600():
    payload = _payload()
    payload["market"]["tickers"][0]["observed_at_toronto"] = "2026-09-25T09:30:00-04:00"
    assert any("16:00" in p for p in check_market_close_semantics(payload))


def test_stale_evidence_hash_is_flagged(tmp_path):
    evidence = tmp_path / "spy.json"
    evidence.write_text('{"a": 1}', encoding="utf-8")
    payload = _payload()
    payload["market"]["tickers"][0]["source_provenance"] = {
        "daily_close": {
            "source_url": "https://example.invalid/spy",
            "evidence_path": str(evidence),
            "sha256": "b" * 64,
        }
    }
    problems = check_provenance_traceability(payload)
    assert any("stale" in p for p in problems)


def test_provenance_without_evidence_path_is_flagged():
    payload = _payload()
    payload["market"]["tickers"][0]["source_provenance"] = {
        "daily_close": {"source_url": "https://example.invalid/spy", "sha256": "c" * 64}
    }
    assert check_provenance_traceability(payload)


# --------------------------------------------------------------------------- #
# pricing honesty
# --------------------------------------------------------------------------- #
def test_unavailable_pricing_must_be_null():
    payload = _payload()
    payload["meetings"]["fed"]["pricing"] = {
        "probability_status": "unavailable", "cut_25bp": 0.4, "hold": 0.5, "hike_25bp": 0.1,
    }
    assert any("unavailable but carries probabilities" in p for p in check_pricing_honesty(payload))


def test_available_pricing_must_sum_to_one():
    payload = _payload()
    payload["meetings"]["fed"]["pricing"] = {
        "probability_status": "available", "cut_25bp": 0.4, "hold": 0.4, "hike_25bp": 0.1,
    }
    assert any("not 1" in p for p in check_pricing_honesty(payload))


def test_rate_level_is_not_a_probability():
    payload = _payload()
    payload["meetings"]["boc"]["pricing"]["implied_rate_before"] = 2.25
    assert check_pricing_honesty(payload) == []


# --------------------------------------------------------------------------- #
def test_source_observation_after_as_of_is_flagged():
    """The gate caught this on the real rebuild: brief cited 17:50 under an 05:37 as_of."""
    payload = _payload(as_of="2026-09-28T05:37:17-04:00")
    payload["decision_brief"] = {
        "as_of_toronto": "2026-09-28T05:37:17-04:00",
        "source_references": [{"url": "https://example.invalid", "label": "x",
                               "observed_at_toronto": "2026-09-28T17:50:00-04:00"}],
    }
    assert check_as_of_coherence(payload)


def test_run_all_covers_every_check():
    from econ.structural_gate import CHECKS, RUNNERS
    payload = _payload(
        evidence_manifest={"path": "nope.json"},
        decision_brief={"as_of_toronto": "2026-09-28T18:05:00-04:00"},
    )
    results = run_all(payload)
    # Assert against the registry, not a magic number: adding a check must
    # break this test loudly instead of silently going uncovered.
    assert set(results) == set(CHECKS) == set(RUNNERS)
    assert len(results) >= 10
    assert any(name in results for name in ("required_containment", "driver_side_signs",
                                            "renderer_contract"))


# --------------------------------------------------------------------------- #
# renderer contract: the 2026-09-28 findings
# --------------------------------------------------------------------------- #
def test_brief_field_the_renderer_ignores_is_flagged():
    """The 2026-09-28 bug class: a field in the payload, nowhere in index.html.

    what_is_priced/falsifiers/attention_budget were exactly this until the
    renderer was taught to read them, so the check must still catch a *new*
    unwired field rather than only the historical three.
    """
    from econ.structural_gate import check_renderer_contract
    problems = check_renderer_contract(_payload(
        decision_brief={"as_of_toronto": "2026-09-28T18:05:00-04:00",
                        "attention_budget": "90 seconds",
                        "zzz_promised_but_never_rendered": "x"}))
    assert any("zzz_promised_but_never_rendered" in p and "never reads it" in p
               for p in problems)
    # and the historical three now pass, because the sub-agent wired them
    ok = check_renderer_contract(_payload(
        decision_brief={"as_of_toronto": "2026-09-28T18:05:00-04:00",
                        "what_is_priced": {"fed": "..."}, "falsifiers": ["x"],
                        "attention_budget": "90 seconds"}))
    assert not any("never reads it" in p for p in ok)


def test_unknown_delta_type_is_flagged():
    from econ.structural_gate import check_renderer_contract
    payload = _payload()
    payload["drivers"]["boc"]["dovish"] = [{
        "id": "boc_dovish_retail", "data": {"delta_type": "contraction"},
    }]
    problems = check_renderer_contract(payload)
    # 'contraction' IS in the live index.html badge map now, so this must pass;
    # a type absent from both map and payload is the real failure.
    assert not any("badge map" in p for p in problems)
    payload["drivers"]["boc"]["dovish"][0]["data"]["delta_type"] = "zzz-unknown"
    assert any("badge map" in p for p in check_renderer_contract(payload))


def test_trade_status_must_match_the_renderer_token():
    from econ.structural_gate import check_renderer_contract
    ok = check_renderer_contract(_payload(
        decision_brief={"as_of_toronto": "2026-09-28T18:05:00-04:00",
                        "trade_status": "NO TRADE / NO EDGE"}))
    assert not any("exact token" in p for p in ok)
    bad = check_renderer_contract(_payload(
        decision_brief={"as_of_toronto": "2026-09-28T18:05:00-04:00",
                        "trade_status": "NO TRADE - but for a stated reason"}))
    assert any("compares against" in p for p in bad)
