from __future__ import annotations

import hashlib
import json

import pytest

from econ.archive_fed_boc import archive_dashboard


def _approved_review(candidate, tmp_path):
    review = tmp_path / "pm-review.json"
    review.write_text(json.dumps({
        "schema_version": "1.0",
        "reviewer_role": "independent_portfolio_manager",
        "reviewed_at": "2026-08-24T12:00:00-04:00",
        "candidate_sha256": hashlib.sha256(candidate.read_bytes()).hexdigest(),
        "verdict": "approved",
        "executive_summary": "All material policy, pricing, driver, and freshness checks passed.",
        "checks": {
            "official_policy": "pass", "pricing": "pass", "drivers": "pass",
            "market_validation": "pass", "freshness": "pass",
            "decision_usefulness": "pass",
        },
        "findings": [],
        "pnl_risks": ["Unexpected inflation can rapidly reprice the front end of the curve."],
        "operator_instructions": [],
    }), encoding="utf-8")
    return review


def _publishable_payload(tmp_path, as_of="2026-08-24T08:00:00-04:00"):
    """A minimal payload that satisfies the pre-flight containment gate.

    The archive gate is no longer content-optional: the 2026-09-28 PM review
    showed a payload stripped of decision_brief, provenance and market dates
    archiving and publishing a stale claim.  Fixtures must therefore carry the
    same evidence containers a real snapshot has.
    """
    evidence = tmp_path / "yahoo_spy_daily.json"
    evidence.write_text('{"chart": {}}', encoding="utf-8")
    manifest = tmp_path / "candidate-source-manifest.json"
    manifest.write_text(json.dumps({
        "schema_version": "1.0",
        "field_evidence_map": [
            {"keys": ["yahoo_SPY_daily"], "evidence": ["yahoo_spy_daily.json"]}
        ],
    }), encoding="utf-8")
    return {
        "as_of": as_of,
        "version": "2026-08-24-001",
        "evidence_manifest": {"path": str(manifest), "sha256": "0" * 64},
        "market": {
            "as_of_toronto": as_of,
            "as_of_close": "2026-08-21T16:00:00-04:00",
            "tickers": [{
                "symbol": "SPY",
                "price": 500.0,
                "session_date": "2026-08-21",
                "observed_at_toronto": "2026-08-21T16:00:00-04:00",
                "source_provenance": {
                    "daily_close": {
                        "key": "yahoo_SPY_daily",
                        "source_url": "https://example.invalid/spy",
                        "evidence_path": str(evidence),
                        "sha256": hashlib.sha256(evidence.read_bytes()).hexdigest(),
                        "http_status": 200,
                        "retrieved_at_toronto": as_of,
                    }
                },
            }],
        },
        "meetings": {
            "fed": {"pricing": {"probability_status": "unavailable", "cut_25bp": None,
                                "hold": None, "hike_25bp": None,
                                "observable_proxy": {"instrument": "TEST"}}},
            "boc": {"pricing": {"probability_status": "unavailable", "cut_25bp": None,
                                "hold": None, "hike_25bp": None,
                                "observable_proxy": {"instrument": "TEST"}}},
        },
        "drivers": {
            "fed": {
                "dovish": [{
                    "id": "fed_dove_test_20260801",
                    "source_url": "https://example.invalid/fed",
                    "source_observed_at_toronto": "2026-08-01T10:00:00-04:00",
                    "published_at_toronto": "2026-08-01T10:00:00-04:00",
                }],
                "hawkish": [],
            },
            "boc": {"dovish": [], "hawkish": []},
        },
        "decision_brief": {
            "as_of_toronto": as_of,
            "trade_status": "NO TRADE / NO EDGE",
            "headline": "No directional edge; snapshot published for the record.",
            "summary": "The snapshot states no position and no probability.",
            "changes_since_previous": ["First archived snapshot for this date."],
            "largest_pnl_risks": ["An unsourced release can move the front end."],
            "source_references": ["https://example.invalid/fed"],
        },
    }


def test_archive_dashboard_writes_snapshot_and_sorted_manifest(tmp_path):
    source = tmp_path / "dashboard.json"
    page_root = tmp_path / "fed-boc-watcher"
    payload = _publishable_payload(tmp_path)
    source.write_text(json.dumps(payload), encoding="utf-8")
    review = _approved_review(source, tmp_path)

    snapshot, dates_path = archive_dashboard(
        source,
        page_root,
        source,
        review,
        snapshot_date="2026-08-24",
        archived_at="2026-08-24T13:10:00Z",
    )

    assert snapshot == page_root / "data" / "archive" / "2026-08-24.json"
    archived = json.loads(snapshot.read_text(encoding="utf-8"))
    assert {key: archived[key] for key in payload} == payload
    assert archived["snapshot_date"] == "2026-08-24"
    assert archived["archived_at"] == "2026-08-24T13:10:00Z"
    assert archived["stale"] is False
    assert json.loads((page_root / "data" / "latest.json").read_text(encoding="utf-8")) == archived
    manifest = json.loads(dates_path.read_text(encoding="utf-8"))
    assert manifest["latest"] == "2026-08-24"
    assert manifest["dates"] == ["2026-08-24"]

    stale_snapshot, dates_path = archive_dashboard(
        source,
        page_root,
        source,
        review,
        snapshot_date="2026-08-25",
        archived_at="2026-08-25T13:10:00Z",
    )
    assert json.loads(stale_snapshot.read_text(encoding="utf-8"))["stale"] is True
    manifest = json.loads(dates_path.read_text(encoding="utf-8"))
    assert manifest["latest"] == "2026-08-25"
    assert manifest["dates"] == ["2026-08-25", "2026-08-24"]


def _payload(driver: dict) -> dict:
    return {
        "as_of": "2026-09-09T12:40:00-04:00",
        "meetings": {"fed": {}, "boc": {}},
        "drivers": {"fed": {"dovish": [driver], "hawkish": []}, "boc": {}},
    }


def test_observation_stamp_may_follow_publication(tmp_path):
    """A driver refreshed with a newer reading is the normal case, not a defect."""
    from econ.driver_quality import check_payload

    assert check_payload(_payload({
        "id": "fed_dove_oil",
        "published_at_toronto": "2026-08-27T16:00:00-04:00",
        "observed_at_toronto": "2026-09-09T12:31:00-04:00",
    })) == []


def test_reading_cannot_predate_or_outrun_the_snapshot():
    from econ.driver_quality import check_payload

    backwards = check_payload(_payload({
        "id": "fed_dove_oil",
        "published_at_toronto": "2026-09-09T12:00:00-04:00",
        "observed_at_toronto": "2026-08-27T16:00:00-04:00",
    }))
    assert len(backwards) == 1 and "precedes published_at_toronto" in backwards[0]

    future = check_payload(_payload({
        "id": "fed_dove_oil",
        "published_at_toronto": "2026-08-27T16:00:00-04:00",
        "observed_at_toronto": "2026-09-10T09:00:00-04:00",
    }))
    assert len(future) == 1 and "after the payload as_of" in future[0]


def test_naive_timestamp_is_rejected():
    from econ.driver_quality import check_payload

    problems = check_payload(_payload({
        "id": "fed_dove_oil",
        "published_at_toronto": "2026-08-27T16:00:00",
    }))
    assert len(problems) == 1 and "UTC offset" in problems[0]


def test_archive_refuses_an_incoherent_payload(tmp_path):
    """A bad driver must not overwrite the last good latest.json."""
    import pytest

    source = tmp_path / "dashboard.json"
    page_root = tmp_path / "fed-boc-watcher"
    source.write_text(json.dumps(_payload({
        "id": "fed_dove_oil",
        "published_at_toronto": "2026-09-09T12:00:00-04:00",
        "observed_at_toronto": "2026-08-27T16:00:00-04:00",
    })), encoding="utf-8")

    review = _approved_review(source, tmp_path)

    with pytest.raises(ValueError, match="refusing to archive"):
        archive_dashboard(source, page_root, source, review, snapshot_date="2026-09-09")
    assert not (page_root / "data" / "latest.json").exists()


def test_unavailable_pricing_requires_nulls_and_observable_proxy():
    from econ.archive_fed_boc import _validate_pricing

    payload = {"meetings": {
        "fed": {"pricing": {"cut_25bp": 0.0, "hold": 0.4, "hike_25bp": 0.6}},
        "boc": {"pricing": {
            "probability_status": "unavailable",
            "cut_25bp": None, "hold": None, "hike_25bp": None,
            "implied_rate_after": None,
            "observable_proxy": {"instrument": "CRAU26", "observed_price": 97.65},
        }},
    }}
    _validate_pricing(payload)


def test_unavailable_pricing_rejects_numeric_placeholder():
    import pytest
    from econ.archive_fed_boc import _validate_pricing

    payload = {"meetings": {
        "fed": {"pricing": {"cut_25bp": 0.0, "hold": 0.4, "hike_25bp": 0.6}},
        "boc": {"pricing": {
            "probability_status": "unavailable",
            "cut_25bp": 0.0, "hold": 0.4, "hike_25bp": 0.6,
            "observable_proxy": {"instrument": "CRAU26"},
        }},
    }}
    with pytest.raises(ValueError, match="must be null"):
        _validate_pricing(payload)

# --------------------------------------------------------------------------- #
# The archive step must enforce the structural gate itself.
#
# Mutation check: with `if structural:` replaced by `if False:` the suite stayed
# green, i.e. nothing covered publication-time enforcement.  Two independent PM
# reviews flagged this.  These tests go through archive_dashboard -- the only path
# a publisher can take -- and use a payload that satisfies every EARLIER guard, so
# the structural gate is the only thing that can stop it.
# --------------------------------------------------------------------------- #
def _approved_review_for(candidate, tmp_path):
    return _approved_review(candidate, tmp_path)


def _claim_bearing_payload_without_containers():
    """Passes the missing-meetings/drivers and pricing guards; fails only the gate."""
    return {
        "as_of": "2026-09-28T18:05:00-04:00",
        "market": {
            "return_basis_note": "Closes were retrieved Sunday Sep 27.",
            "tickers": [],
        },
        "meetings": {
            "fed": {"pricing": {"probability_status": "unavailable", "cut_25bp": None,
                                "hold": None, "hike_25bp": None,
                                "observable_proxy": {"instrument": "TEST"}}},
            "boc": {"pricing": {"probability_status": "unavailable", "cut_25bp": None,
                                "hold": None, "hike_25bp": None,
                                "observable_proxy": {"instrument": "TEST"}}},
        },
        "drivers": {
            "fed": {"dovish": [], "hawkish": [{
                "id": "fed_hawk_test_20260901",
                "source_url": "https://example.invalid/fed",
                "source_observed_at_toronto": "2026-09-01T10:00:00-04:00",
                "published_at_toronto": "2026-09-01T10:00:00-04:00",
            }]},
            "boc": {"dovish": [], "hawkish": []},
        },
    }


def test_archive_refuses_payload_without_evidence_containers(tmp_path):
    source = tmp_path / "dashboard.json"
    page_root = tmp_path / "fed-boc-watcher"
    source.write_text(json.dumps(_claim_bearing_payload_without_containers()), encoding="utf-8")
    review = _approved_review_for(source, tmp_path)

    with pytest.raises(ValueError) as excinfo:
        archive_dashboard(source, page_root, source, review, snapshot_date="2026-09-28")
    assert "structural gate failed" in str(excinfo.value), (
        f"the structural gate must be what refuses this: {excinfo.value}"
    )
    assert not (page_root / "data" / "latest.json").exists(), "nothing may be published"


def test_archive_refuses_contraction_filed_as_hawkish(tmp_path):
    """The BoC retail sign error must not be archivable."""
    payload = _publishable_payload(tmp_path)
    payload["drivers"]["boc"]["hawkish"] = [{
        "id": "boc_hawk_retail_20260924",
        "source_url": "https://example.invalid/statcan",
        "source_observed_at_toronto": "2026-09-24T08:30:00-04:00",
        "published_at_toronto": "2026-09-24T08:30:00-04:00",
        "data": {"actual": "-0.7", "delta_type": "beat"},
    }]
    source = tmp_path / "dashboard.json"
    page_root = tmp_path / "fed-boc-watcher"
    source.write_text(json.dumps(payload), encoding="utf-8")
    review = _approved_review_for(source, tmp_path)

    with pytest.raises(ValueError) as excinfo:
        archive_dashboard(source, page_root, source, review, snapshot_date="2026-09-24")
    assert "structural gate failed" in str(excinfo.value)
    assert "growth-negative" in str(excinfo.value)
