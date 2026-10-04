"""The shared reviewer gate (scripts/review/) behaves identically for all trackers.

Pins: canonical bytes, committed-bundle acceptance, and every fail-closed
branch (self-review, sha mismatch, APPROVED+major, uncovered flags).
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from review.core import canonical, sha_hex, toronto_today
from review.flags_rates_decisions import structural_flags
from review.freeze import freeze as shared_freeze
from review.validate_pm_review import validate as validate_review

REPO = Path(__file__).resolve().parents[1]
RATES = REPO / "Rates_decisions"
REVIEW_DIR = RATES / "review" / "2026-10-04"
RATES_CHECKS = [
    "official_policy", "pricing", "drivers",
    "market_validation", "freshness", "decision_usefulness",
]


def _spec_load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_canonical_bytes_pinned_to_committed_candidate():
    raw = (REVIEW_DIR / "candidate.json").read_bytes()
    assert canonical(json.loads(raw.decode("utf-8"))) == raw
    assert sha_hex(raw) == (REVIEW_DIR / "candidate.sha256").read_text().strip()


def test_validator_accepts_committed_approved_bundle():
    assert validate_review(
        REVIEW_DIR / "candidate.json",
        REVIEW_DIR / "pm-review.json",
        REVIEW_DIR / "structural-flags.json",
        RATES_CHECKS, True,
    ) == []


def _mutated_review(tmp_path: Path, **overrides):
    review = json.loads((REVIEW_DIR / "pm-review.json").read_text(encoding="utf-8"))
    review.update(overrides)
    path = tmp_path / "pm-review.json"
    path.write_text(json.dumps(review), encoding="utf-8")
    return path


def test_validator_rejects_self_review(tmp_path):
    path = _mutated_review(tmp_path, reviewer="self", operator="self")
    problems = validate_review(REVIEW_DIR / "candidate.json", path, None, RATES_CHECKS, False)
    assert any("different people" in p for p in problems)


def test_validator_rejects_sha_mismatch(tmp_path):
    path = _mutated_review(tmp_path, candidate_sha256="0" * 64)
    problems = validate_review(REVIEW_DIR / "candidate.json", path, None, RATES_CHECKS, False)
    assert any("mismatch" in p for p in problems)


def test_validator_rejects_approved_with_major_open(tmp_path):
    review = json.loads((REVIEW_DIR / "pm-review.json").read_text(encoding="utf-8"))
    review["findings"] = [{
        "severity": "major", "field": "drivers.fed.fed-d1.source_url",
        "issue": "secondary source used as primary evidence",
        "evidence": "candidate fed-d1 url https://example.com/x vs primary",
        "disposition": "must_fix",
    }]
    path = tmp_path / "pm-review.json"
    path.write_text(json.dumps(review), encoding="utf-8")
    problems = validate_review(
        REVIEW_DIR / "candidate.json", path,
        REVIEW_DIR / "structural-flags.json", RATES_CHECKS, True)
    assert any("must be REVISE" in p for p in problems)


def test_validator_requires_flags_coverage(tmp_path):
    review = json.loads((REVIEW_DIR / "pm-review.json").read_text(encoding="utf-8"))
    review["flags_dispositioned"] = []
    path = tmp_path / "pm-review.json"
    path.write_text(json.dumps(review), encoding="utf-8")
    flags = [{"code": "stale_pricing", "field": "meetings.fed.pricing.as_of", "message": "old"}]
    flags_path = tmp_path / "flags.json"
    flags_path.write_text(json.dumps(flags), encoding="utf-8")
    problems = validate_review(
        REVIEW_DIR / "candidate.json", path, flags_path, RATES_CHECKS, False)
    assert any("uncovered" in p for p in problems)


def test_freeze_roundtrip_in_tmp_dir(tmp_path):
    doc = {"snapshot_date": toronto_today(), "meetings": {}, "v": 1}
    src = tmp_path / "input.json"
    src.write_text(json.dumps(doc), encoding="utf-8")
    flags = tmp_path / "flags.json"
    flags.write_text("[]", encoding="utf-8")
    message, code = shared_freeze(src, tmp_path / "review", flags, toronto_today(), False)
    assert code == 0, message
    cand = tmp_path / "review" / "candidate.json"
    assert cand.read_bytes() == canonical(doc)
    assert (tmp_path / "review" / "candidate.sha256").read_text().strip() == sha_hex(cand.read_bytes())
    # Re-freeze without --force refuses (candidate immutable).
    _, code = shared_freeze(src, tmp_path / "review", flags, toronto_today(), False)
    assert code == 1


def test_rates_flags_empty_on_published_snapshot():
    snapshot = json.loads((RATES / "data" / "archive" / "2026-10-04.json").read_text(encoding="utf-8"))
    assert structural_flags(snapshot) == []


def test_rates_structure_valid_on_published_snapshot():
    publish = _spec_load("rates_publish", RATES / "scripts" / "publish.py")
    snapshot = json.loads((RATES / "data" / "archive" / "2026-10-04.json").read_text(encoding="utf-8"))
    assert publish.validate(snapshot) == []
