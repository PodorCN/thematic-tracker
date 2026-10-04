"""The unattended publishers may change data, never page templates or code."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

from econ.verify_data_only_changes import (
    classify_changes, validate_paths, verify_template_binding,
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
    (repo / "economic-calendar" / "data").mkdir(parents=True)
    page = repo / "economic-calendar" / "index.html"
    snapshot = repo / "economic-calendar" / "data" / "latest.json"
    page.write_text("before", encoding="utf-8")
    snapshot.write_text("{}", encoding="utf-8")
    manifest = repo / "scripts" / "econ" / "frontend_contract.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps({"economic-calendar": hashlib.sha256(b"before").hexdigest()}), encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "baseline")
    page.write_text("changed", encoding="utf-8")
    snapshot.write_text('{"new":true}', encoding="utf-8")
    _git(repo, "add", ".")
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--repo", str(repo), "--product", "economic-calendar", "--staged"],
        capture_output=True, text=True,
    )
    assert result.returncode != 0
    assert "economic-calendar/index.html" in result.stdout + result.stderr


def test_change_classification_rejects_mixed_code_data_and_unreviewed_frontend_push():
    assert classify_changes(["economic-calendar/data/latest.json", "economic-calendar/index.html"], "pull_request")
    assert classify_changes(["economic-calendar/index.html"], "pull_request")
    assert classify_changes(["economic-calendar/index.html", "scripts/econ/frontend_contract.json"], "pull_request") == []
    assert classify_changes(["economic-calendar/data/latest.json", "economic-calendar/data/archive/2026-09-29.json"], "push") == []


def test_push_lane_accepts_contract_bound_frontend_and_rejects_unbound_or_mixed():
    assert classify_changes(
        ["economic-calendar/index.html", "scripts/econ/frontend_contract.json"], "push") == []
    assert classify_changes(["economic-calendar/index.html"], "push")
    assert classify_changes(
        ["economic-calendar/index.html", "economic-calendar/data/latest.json",
         "scripts/econ/frontend_contract.json"], "push")


def test_data_release_rejects_a_changed_page_even_with_valid_json():
    violations = validate_paths(
        ["economic-calendar/index.html", "economic-calendar/data/latest.json"],
        product="economic-calendar",
    )
    assert "economic-calendar/index.html" in violations


def test_economic_calendar_allows_only_daily_data_files():
    allowed = [
        "economic-calendar/raw/2026-09-29/economic_calendar.json",
        "economic-calendar/data/latest.json",
        "economic-calendar/data/dates.json",
        "economic-calendar/data/archive/2026-09-29.json",
    ]
    assert validate_paths(allowed, "economic-calendar") == []


def test_daily_data_rejects_html_templates_generated_pages_and_code():
    rejected = [
        "economic-calendar/index.html",
        "economic-calendar/archive/2026-09-29.html",
        "scripts/econ/render_calendar.py",
    ]
    assert validate_paths(rejected, "economic-calendar") == rejected


def test_template_digest_is_frozen_for_daily_data_publication(tmp_path):
    template = tmp_path / "economic-calendar" / "index.html"
    template.parent.mkdir()
    template.write_bytes(b"<html>original</html>\r\n")
    contract = tmp_path / "scripts" / "econ" / "frontend_contract.json"
    contract.parent.mkdir(parents=True)
    digest = hashlib.sha256(b"<html>original</html>\n").hexdigest()
    contract.write_text(json.dumps({"economic-calendar": digest}), encoding="utf-8")
    assert verify_template_binding(tmp_path, "economic-calendar") == []
    template.write_text("<html>changed</html>\n", encoding="utf-8")
    assert verify_template_binding(tmp_path, "economic-calendar") == ["economic-calendar/index.html"]


def test_missing_template_or_contract_fails_closed(tmp_path):
    assert verify_template_binding(tmp_path, "economic-calendar") == [
        "economic-calendar/index.html"
    ]
