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


def _rates_manifest(*, app=b"js", css=b"css", html=b"<html>rates</html>\n"):
    def digest(content: bytes) -> str:
        return hashlib.sha256(content.replace(b"\r\n", b"\n")).hexdigest()

    return {
        "economic-calendar": "0" * 64,
        "Rates_decisions": {
            "index.html": digest(html),
            "app.js": digest(app),
            "styles.css": digest(css),
        },
    }


def test_rates_data_release_allows_snapshot_and_review_bundle():
    allowed = [
        "Rates_decisions/data/current.json",
        "Rates_decisions/data/latest.json",
        "Rates_decisions/data/dates.json",
        "Rates_decisions/data/archive/2026-10-04.json",
        "Rates_decisions/review/2026-10-04/candidate.json",
        "Rates_decisions/review/2026-10-04/candidate.sha256",
        "Rates_decisions/review/2026-10-04/structural-flags.json",
        "Rates_decisions/review/2026-10-04/pm-review.json",
        "Rates_decisions/review/2026-10-04/review.md",
    ]
    assert validate_paths(allowed, "Rates_decisions") == []
    assert classify_changes(allowed, "push") == []


def test_rates_data_lane_rejects_renderers_mechanism_and_retired_reviews():
    rejected = [
        "Rates_decisions/index.html",
        "Rates_decisions/app.js",
        "Rates_decisions/styles.css",
        "Rates_decisions/data/evil.json",
        "Rates_decisions/review/2026-10-04.md",
        "Rates_decisions/review/TEMPLATE.md",
        "Rates_decisions/review/REVIEWER_AGENT.md",
        "Rates_decisions/scripts/publish.mjs",
    ]
    assert validate_paths(rejected, "Rates_decisions") == rejected


def test_rates_classification_blocks_unbound_frontend_and_mixed_bundles():
    contract = "scripts/econ/frontend_contract.json"
    assert classify_changes(["Rates_decisions/app.js"], "push")
    assert classify_changes(["Rates_decisions/styles.css"], "pull_request")
    assert classify_changes(
        ["Rates_decisions/index.html", "Rates_decisions/data/latest.json", contract], "push")
    assert classify_changes(
        ["Rates_decisions/index.html", "Rates_decisions/app.js",
         "Rates_decisions/styles.css", contract], "push") == []
    assert classify_changes(["Rates_decisions/app.js", contract], "push") == []


def test_rates_template_binding_covers_all_three_renderer_files(tmp_path):
    root = tmp_path
    (root / "Rates_decisions").mkdir()
    (root / "Rates_decisions" / "index.html").write_bytes(b"<html>rates</html>\n")
    (root / "Rates_decisions" / "app.js").write_bytes(b"js")
    (root / "Rates_decisions" / "styles.css").write_bytes(b"css")
    contract = root / "scripts" / "econ" / "frontend_contract.json"
    contract.parent.mkdir(parents=True)
    contract.write_text(json.dumps(_rates_manifest()), encoding="utf-8")
    assert verify_template_binding(root, "Rates_decisions") == []
    (root / "Rates_decisions" / "app.js").write_text("changed", encoding="utf-8")
    assert verify_template_binding(root, "Rates_decisions") == ["Rates_decisions/app.js"]
    (root / "Rates_decisions" / "styles.css").unlink()
    assert "Rates_decisions/styles.css" in verify_template_binding(root, "Rates_decisions")


def test_cli_rejects_staged_rates_app_change_bundled_with_data(tmp_path):
    repo = tmp_path / "repo"
    (repo / "Rates_decisions" / "data").mkdir(parents=True)
    (repo / "Rates_decisions" / "index.html").write_text("<html>r</html>\n", encoding="utf-8")
    (repo / "Rates_decisions" / "app.js").write_text("js", encoding="utf-8")
    (repo / "Rates_decisions" / "styles.css").write_text("css", encoding="utf-8")
    (repo / "Rates_decisions" / "data" / "latest.json").write_text("{}", encoding="utf-8")
    manifest = repo / "scripts" / "econ" / "frontend_contract.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps(_rates_manifest(
        html=b"<html>r</html>\n")), encoding="utf-8")
    _git(repo, "init", "-q")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "config", "user.email", "test@example.org")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "baseline")
    (repo / "Rates_decisions" / "app.js").write_text("changed", encoding="utf-8")
    (repo / "Rates_decisions" / "data" / "latest.json").write_text('{"new":true}', encoding="utf-8")
    _git(repo, "add", ".")
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--repo", str(repo), "--product", "Rates_decisions", "--staged"],
        capture_output=True, text=True,
    )
    assert result.returncode != 0
    assert "Rates_decisions/app.js" in result.stdout + result.stderr
