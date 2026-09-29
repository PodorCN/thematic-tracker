"""Render tests: what the page ACTUALLY shows, not what the payload says.

The 2026-09-28 fabrication bug lived entirely in index.html: `.bbar` set
`display:flex`, which overrode the `hidden` attribute, so static default odds
(Cut 0% / Hold 38% / Hike 62%) rendered beside an honestly-null pricing block.
No Python check in the repo could see it -- the payload was correct, the hashes
matched, the arithmetic was right. Only a browser can.

These tests are skipped when a browser is unavailable, so the suite still runs in
CI without one. When a browser IS present they are the only thing standing
between a stale default and a reader sizing a position on it.
"""
from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import time
from functools import lru_cache
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PAGE_ROOT = REPO_ROOT / "fed-boc-watcher"
def _newest_frozen_candidate() -> Path | None:
    """The newest frozen candidate (by date, then iteration number).

    Pinning a fixed path made this file silently test a historical build; the
    render assertions must exercise the candidate currently under review.
    """
    import re as _re
    out = []
    for sidecar in PAGE_ROOT.glob("review/*/iteration-*/candidate.sha256"):
        m = _re.match(r"(\d{4}-\d{2}-\d{2})$", sidecar.parent.parent.name)
        n = _re.match(r"iteration-(\d+)$", sidecar.parent.name)
        candidate = sidecar.with_name("candidate.json")
        if m and n and candidate.exists():
            out.append(((m.group(1), int(n.group(1))), candidate))
    out.sort(key=lambda item: item[0])
    return out[-1][1] if out else None


CANDIDATE = _newest_frozen_candidate()

CHROME_CANDIDATES = [
    shutil.which("chrome"), shutil.which("google-chrome"), shutil.which("chromium"),
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
]


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@lru_cache(maxsize=1)
def _chrome() -> str | None:
    for path in CHROME_CANDIDATES:
        if path and (shutil.which(path) or Path(path).exists()):
            return path
    return None


@lru_cache(maxsize=1)
def _headless_dump() -> str | None:
    """Render the page headlessly and return document.body.innerText.

    Uses --dump-dom, which runs the page's JS and serialises the live DOM. That
    is enough to catch innerText-level fabrication; it cannot compute computed
    styles, so the CSS-specific assertions are guarded separately.
    """
    if CANDIDATE is None or not CANDIDATE.exists():
        return None
    port = _free_port()
    server = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1"],
        cwd=PAGE_ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        url = f"http://127.0.0.1:{port}/index.html"
        for _ in range(40):
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                    break
            except OSError:
                time.sleep(0.1)
        # Stage the candidate so the page renders THIS build, not the published one.
        latest = PAGE_ROOT / "data" / "latest.json"
        backup = None
        try:
            if latest.exists():
                backup = latest.read_bytes()
            shutil.copyfile(CANDIDATE, latest)
            result = subprocess.run(
                [_chrome(), "--headless=new", "--disable-gpu", "--no-sandbox",
                 "--virtual-time-budget=8000", "--run-all-compositor-stages-before-draw",
                 "--dump-dom", url],
                capture_output=True, text=True, timeout=120)
        finally:
            if backup is not None:
                latest.write_bytes(backup)
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()
    except (OSError, subprocess.TimeoutExpired):
        return None
    dom = result.stdout or ""
    return dom if "decision frame" in dom.lower() or "fed" in dom.lower() else dom or None


def _dump_text() -> str | None:
    dom = _headless_dump()
    if dom is None:
        return None
    import re
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", dom))


pytestmark = pytest.mark.skipif(_chrome() is None, reason="no chrome available to render the page")


def test_no_static_default_odds_reach_the_page():
    """Regression: Hike 62% / Hold 38% / Hike 60% must never appear.

    These were the hard-coded placeholders in index.html that the [hidden]
    attribute failed to suppress.
    """
    text = _dump_text()
    if text is None:
        pytest.skip("headless render produced no DOM")
    for fabricated in ("Hike 62%", "Hold 38%", "Hike 60%", "Hold 40%", "3.63%", "2.25% → 2.40%"):
        assert fabricated not in text, (
            f"the page shows the static default {fabricated!r} while this snapshot's meeting "
            "pricing is honestly null: a reader could size on a number no source supports"
        )


def test_hidden_attribute_wins_over_display_flex():
    """The CSS rule that fixes it must be present, or [hidden] is ignored."""
    html = (PAGE_ROOT / "index.html").read_text(encoding="utf-8")
    assert ".bbar[hidden]" in html and ".bbar-legend[hidden]" in html, (
        ".bbar sets display:flex, so [hidden] needs an explicit display:none rule; "
        "without it the hidden odds bar renders anyway"
    )


def test_the_rendered_page_shows_this_candidate_not_the_old_one():
    text = _dump_text()
    if text is None:
        pytest.skip("headless render produced no DOM")
    candidate = json.loads(CANDIDATE.read_text(encoding="utf-8"))
    as_of_date = candidate["decision_brief"]["as_of_toronto"][:10]
    assert as_of_date in text or as_of_date in text.replace("/", "-"), (
        "the page did not render the candidate under test (its as-of date is missing from the page)")
    assert candidate["decision_brief"]["trade_status"] in text


def test_quarterly_proxy_language_survives_to_the_page():
    """The caveat that keeps a PM from reading a quarterly average as meeting odds."""
    text = _dump_text()
    if text is None:
        pytest.skip("headless render produced no DOM")
    assert "quarterly average" in text.lower(), (
        "the 'quarterly average, not a meeting probability' language is load-bearing and must render"
    )


def test_proxy_labels_from_the_candidate_render_to_the_page():
    """2026-09-29 round-1 finding: the Fed card must not be labeled quarterly.

    The observable-proxy line renders the payload's `rate_label`; whatever the
    frozen candidate declares must reach the page.
    """
    text = _dump_text()
    if text is None:
        pytest.skip("headless render produced no DOM")
    candidate = json.loads(CANDIDATE.read_text(encoding="utf-8"))
    meetings = candidate.get("meetings", {})
    labels = []
    for bank in ("fed", "boc"):
        proxy = ((meetings.get(bank) or {}).get("pricing") or {}).get("observable_proxy") or {}
        label = proxy.get("rate_label")
        if label:
            labels.append((bank, label))
    assert labels, "no observable_proxy rate_label in the frozen candidate: the label contract is unexercised"
    for bank, label in labels:
        assert label in text, (
            f"the {bank} proxy label {label!r} does not reach the rendered page")
