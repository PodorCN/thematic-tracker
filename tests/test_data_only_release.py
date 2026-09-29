"""The unattended publishers may change data, never page templates or code."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

from econ.verify_data_only_changes import (
    classify_changes, validate_paths, verify_template_binding, verify_fed_publication,
)

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "econ" / "verify_data_only_changes.py"


def _git(repo: Path, *args: str):
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def test_cli_rejects_a_staged_template_change_in_real_git_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "config", "user.email", "test@example.org")
    (repo / "fed-boc-watcher" / "data").mkdir(parents=True)
    page = repo / "fed-boc-watcher" / "index.html"
    snapshot = repo / "fed-boc-watcher" / "data" / "latest.json"
    page.write_text("before", encoding="utf-8")
    snapshot.write_text("{}", encoding="utf-8")
    manifest = repo / "scripts" / "econ" / "frontend_contract.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps({"fed-boc-watcher": hashlib.sha256(b"before").hexdigest()}), encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "baseline")
    page.write_text("changed", encoding="utf-8")
    snapshot.write_text('{"new":true}', encoding="utf-8")
    _git(repo, "add", ".")
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--repo", str(repo), "--product", "fed-boc-watcher", "--staged"],
        capture_output=True, text=True,
    )
    assert result.returncode != 0
    assert "fed-boc-watcher/index.html" in result.stdout + result.stderr




def test_change_classification_rejects_mixed_code_data_and_unreviewed_frontend_push():
    assert classify_changes(["economic-calendar/data/latest.json", "economic-calendar/index.html"], "pull_request")
    assert classify_changes(["canadian-banks/index.html"], "pull_request")
    assert classify_changes(["ai-software/theme.md", "canadian-banks/theme.md"], "pull_request")
    assert classify_changes(["fed-boc-watcher/index.html", "scripts/econ/frontend_contract.json", "tests/test_render_truthfulness.py"], "pull_request") == []
    assert classify_changes(["economic-calendar/data/latest.json", "economic-calendar/data/archive/2026-09-29.json"], "push") == []


def test_push_lane_accepts_contract_bound_frontend_and_rejects_unbound_or_mixed():
    """2026-09-29 overhaul review: a merged frontend PR pushes frontend files to
    main; rejecting that push reddens main after every legitimate merge forever
    (a crying-wolf gate). The push lane accepts frontend bytes iff the same
    range carries the updated frontend_contract.json that binds them; the
    binding itself is enforced by verify_template_binding against the head
    bytes. Unbound HTML, and HTML bundled with data, stay rejected."""
    assert classify_changes(
        ["fed-boc-watcher/index.html", "scripts/econ/frontend_contract.json"], "push") == []
    assert classify_changes(
        ["fed-boc-watcher/index.html", "scripts/econ/frontend_contract.json",
         "tests/test_render_truthfulness.py"], "push") == []
    assert classify_changes(["fed-boc-watcher/index.html"], "push")
    assert classify_changes(
        ["fed-boc-watcher/index.html", "scripts/econ/frontend_contract.json",
         "fed-boc-watcher/data/latest.json"], "push")
    assert classify_changes(
        ["economic-calendar/index.html", "economic-calendar/data/latest.json",
         "scripts/econ/frontend_contract.json"], "push")


def test_fed_data_release_rejects_a_changed_page_even_with_valid_json():
    violations = validate_paths(
        ["fed-boc-watcher/index.html", "fed-boc-watcher/data/latest.json"],
        product="fed-boc-watcher",
    )
    assert "fed-boc-watcher/index.html" in violations


def test_all_four_products_allow_only_daily_data_files():
    allowed = {
        "fed-boc-watcher": [
            "fed-boc-watcher/data/dashboard.json",
            "fed-boc-watcher/data/latest.json",
            "fed-boc-watcher/data/dates.json",
            "fed-boc-watcher/data/archive/2026-09-29.json",
            "fed-boc-watcher/review/2026-09-29/iteration-01/candidate.json",
            "fed-boc-watcher/review/2026-09-29/iteration-01/candidate.sha256",
            "fed-boc-watcher/review/2026-09-29/iteration-01/pm-review.json",
            "fed-boc-watcher/review/2026-09-29/iteration-01/evidence/capture.html",
            "fed-boc-watcher/review/feedback/history/2026-09-29-a.json",
        ],
        "economic-calendar": [
            "economic-calendar/raw/2026-09-29/economic_calendar.json",
            "economic-calendar/data/latest.json",
            "economic-calendar/data/dates.json",
            "economic-calendar/data/archive/2026-09-29.json",
        ],
        "canadian-banks": [
            "canadian-banks/theme.md",
            "canadian-banks/theme.txt",
            "canadian-banks/tracker_data/ZEB.csv",
        ],
        "ai-software": [
            "ai-software/theme.md",
            "ai-software/theme.txt",
            "ai-software/tracker_data/IGV.csv",
        ],
    }
    for product, paths in allowed.items():
        assert validate_paths(paths, product) == [], product


def test_daily_data_rejects_html_templates_generated_pages_and_code():
    rejected = {
        "fed-boc-watcher": ["fed-boc-watcher/index.html", "scripts/econ/archive_fed_boc.py"],
        "economic-calendar": [
            "economic-calendar/index.html",
            "economic-calendar/archive/2026-09-29.html",
            "scripts/econ/render_calendar.py",
        ],
        "canadian-banks": ["canadian-banks/index.html", "canadian-banks/AGENT.md"],
        "ai-software": ["ai-software/index.html", "ai-software/tracker_data/../../index.html"],
    }
    for product, paths in rejected.items():
        assert validate_paths(paths, product) == paths, product


def test_a_job_cannot_masquerade_other_products_data_as_its_own():
    assert validate_paths(["economic-calendar/data/latest.json"], "fed-boc-watcher") == [
        "economic-calendar/data/latest.json"
    ]


def test_template_digest_is_frozen_for_daily_data_publication(tmp_path):
    template = tmp_path / "fed-boc-watcher" / "index.html"
    template.parent.mkdir()
    template.write_bytes(b"<html>original</html>\r\n")
    contract = tmp_path / "scripts" / "econ" / "frontend_contract.json"
    contract.parent.mkdir(parents=True)
    digest = hashlib.sha256(b"<html>original</html>\n").hexdigest()
    contract.write_text(json.dumps({"fed-boc-watcher": digest}), encoding="utf-8")
    assert verify_template_binding(tmp_path, "fed-boc-watcher") == []
    template.write_text("<html>changed</html>\n", encoding="utf-8")
    assert verify_template_binding(tmp_path, "fed-boc-watcher") == ["fed-boc-watcher/index.html"]


def test_missing_template_or_contract_fails_closed(tmp_path):
    assert verify_template_binding(tmp_path, "economic-calendar") == [
        "economic-calendar/index.html"
    ]


def test_missing_fed_review_cannot_authorize_latest_publication(tmp_path):
    root = tmp_path / "fed-boc-watcher"
    (root / "data" / "archive").mkdir(parents=True)
    candidate = {"as_of": "2026-09-29T09:00:00-04:00", "meetings": {}, "drivers": {}}
    published = {**candidate, "snapshot_date": "2026-09-29", "archived_at": "2026-09-29T14:00:00Z", "stale": False}
    (root / "data" / "latest.json").write_text(json.dumps(published), encoding="utf-8")
    (root / "data" / "archive" / "2026-09-29.json").write_text(json.dumps(published), encoding="utf-8")
    (root / "data" / "dates.json").write_text(json.dumps({"latest": "2026-09-29", "dates": ["2026-09-29"]}), encoding="utf-8")
    assert "approved review" in " ".join(verify_fed_publication(tmp_path)).lower()


def test_fed_latest_must_equal_the_approved_candidate_not_a_newer_cron_draft(tmp_path):
    root = tmp_path / "fed-boc-watcher"
    (root / "data" / "archive").mkdir(parents=True)
    review_dir = root / "review" / "2026-09-29" / "iteration-01"
    review_dir.mkdir(parents=True)
    candidate = {"as_of": "2026-09-29T09:00:00-04:00", "meetings": {}, "drivers": {}}
    published = {**candidate, "snapshot_date": "2026-09-29", "archived_at": "2026-09-29T14:00:00Z", "stale": False}
    candidate_path = review_dir / "candidate.json"
    candidate_path.write_text(json.dumps(candidate), encoding="utf-8")
    digest = hashlib.sha256(candidate_path.read_bytes()).hexdigest()
    (review_dir / "candidate.sha256").write_text(f"{digest}  candidate.json\n", encoding="utf-8")
    review = {
        "schema_version": "1.0", "reviewer_role": "independent_portfolio_manager",
        "reviewed_at": "2026-09-29T10:00:00-04:00", "candidate_sha256": digest,
        "verdict": "approved", "executive_summary": "Approved candidate with independently checked risk details.",
        "checks": {key: "pass" for key in (
            "official_policy", "pricing", "drivers", "market_validation", "freshness", "decision_usefulness")},
        "findings": [], "pnl_risks": ["A policy surprise can reprice the entire front-end curve."],
        "operator_instructions": [],
    }
    (review_dir / "pm-review.json").write_text(json.dumps(review), encoding="utf-8")
    latest_path = root / "data" / "latest.json"
    archive_path = root / "data" / "archive" / "2026-09-29.json"
    latest_path.write_text(json.dumps(published), encoding="utf-8")
    archive_path.write_text(json.dumps(published), encoding="utf-8")
    (root / "data" / "dates.json").write_text(json.dumps({"latest": "2026-09-29", "dates": ["2026-09-29"]}), encoding="utf-8")
    assert verify_fed_publication(tmp_path) == []
    published["as_of"] = "2026-09-29T11:00:00-04:00"
    latest_path.write_text(json.dumps(published), encoding="utf-8")
    assert verify_fed_publication(tmp_path)


def test_auto_mode_push_lane_accepts_only_contract_bound_frontend(tmp_path):
    """2026-09-29 overhaul review: rejecting every push that contains frontend
    bytes reddens main after every legitimate PR merge forever. The push lane
    accepts iff the range carries a frontend_contract.json whose digest binds
    the head bytes; unbound, wrongly-bound, or data-bundled HTML is rejected."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "config", "user.email", "test@example.org")
    page = repo / "canadian-banks" / "index.html"
    page.parent.mkdir()
    page.write_text("old", encoding="utf-8")
    contract = repo / "scripts" / "econ" / "frontend_contract.json"
    contract.parent.mkdir(parents=True)
    contract.write_text(json.dumps({"canadian-banks": hashlib.sha256(b"old").hexdigest()}), encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "baseline")
    command = [sys.executable, str(SCRIPT), "--repo", str(repo), "--auto", "--range", "HEAD^..HEAD"]

    # A. contract-bound frontend push (e.g. a reviewed PR merge): accepted.
    page.write_text("new", encoding="utf-8")
    contract.write_text(json.dumps({"canadian-banks": hashlib.sha256(b"new").hexdigest()}), encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "reviewed page change")
    allowed = subprocess.run(command + ["--event", "push"], capture_output=True, text=True)
    assert allowed.returncode == 0, allowed.stdout + allowed.stderr

    # B. frontend push without the contract in range: rejected.
    page.write_text("newer", encoding="utf-8")
    contract.write_text(json.dumps({"canadian-banks": hashlib.sha256(b"newer").hexdigest()}), encoding="utf-8")
    _git(repo, "add", "canadian-banks/index.html")
    _git(repo, "commit", "-qm", "unbound page change")
    denied = subprocess.run(command + ["--event", "push"], capture_output=True, text=True)
    assert denied.returncode != 0

    # C. contract in range but digest does not bind the head bytes: rejected.
    _git(repo, "reset", "-q", "--hard", "HEAD^")
    page.write_text("newer", encoding="utf-8")
    contract.write_text(json.dumps({"canadian-banks": hashlib.sha256(b"wrong").hexdigest()}), encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "wrongly bound page change")
    denied = subprocess.run(command + ["--event", "push"], capture_output=True, text=True)
    assert denied.returncode != 0
    assert "canadian-banks/index.html" in denied.stdout + denied.stderr

    # D. frontend bundled with data: rejected even with a correct contract.
    _git(repo, "reset", "-q", "--hard", "HEAD^")
    page.write_text("newest", encoding="utf-8")
    contract.write_text(json.dumps({"canadian-banks": hashlib.sha256(b"newest").hexdigest()}), encoding="utf-8")
    data = repo / "canadian-banks" / "tracker_data"
    data.mkdir()
    (data / "2026-09-29.csv").write_text("date,x\n2026-09-29,1\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "bundled page and data")
    denied = subprocess.run(command + ["--event", "push"], capture_output=True, text=True)
    assert denied.returncode != 0


def test_cli_checks_template_hash_even_when_only_data_is_staged(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "config", "user.email", "test@example.org")
    page = repo / "economic-calendar" / "index.html"
    page.parent.mkdir()
    page.write_text("immutable", encoding="utf-8")
    data = repo / "economic-calendar" / "data" / "latest.json"
    data.parent.mkdir()
    data.write_text("{}", encoding="utf-8")
    contract = repo / "scripts" / "econ" / "frontend_contract.json"
    contract.parent.mkdir(parents=True)
    contract.write_text(json.dumps({"economic-calendar": hashlib.sha256(b"immutable").hexdigest()}), encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "baseline")
    data.write_text('{"new":true}', encoding="utf-8")
    _git(repo, "add", "economic-calendar/data/latest.json")
    command = [sys.executable, str(SCRIPT), "--repo", str(repo), "--product", "economic-calendar", "--staged"]
    accepted = subprocess.run(command, capture_output=True, text=True)
    assert accepted.returncode == 0, accepted.stdout + accepted.stderr
    page.write_text("mutated", encoding="utf-8")
    rejected = subprocess.run(command, capture_output=True, text=True)
    assert rejected.returncode != 0
    assert "economic-calendar/index.html" in rejected.stdout + rejected.stderr
