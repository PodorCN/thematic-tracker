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
    """Only a caller-pinned candidate may replace published data in a render test."""
    raw = os.environ.get("FED_BOC_RENDER_CANDIDATE")
    return Path(raw).resolve() if raw else None


CANDIDATE = _newest_frozen_candidate() or PAGE_ROOT / "data" / "latest.json"

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
        if os.environ.get("FED_BOC_RENDER_CANDIDATE"):
            raise AssertionError(
                "FED_BOC_RENDER_CANDIDATE is set but the file is missing or unreadable: "
                f"{os.environ['FED_BOC_RENDER_CANDIDATE']!r} - a mistyped pin must fail, not skip")
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
            if CANDIDATE != latest:
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
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise AssertionError(f"headless render failed: {exc}") from exc
    dom = result.stdout or ""
    assert result.returncode == 0 and dom, "headless render did not produce a page"
    return dom


def _dump_text() -> str | None:
    dom = _headless_dump()
    if dom is None:
        return None
    import re
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", dom))


pytestmark = pytest.mark.skipif(_chrome() is None, reason="no chrome available to render the page")


def test_candidate_selection_requires_explicit_path(monkeypatch, tmp_path):
    monkeypatch.delenv("FED_BOC_RENDER_CANDIDATE", raising=False)
    assert _newest_frozen_candidate() is None
    candidate = tmp_path / "candidate.json"
    candidate.write_text('{"as_of":"2026-09-29T09:00:00-04:00"}', encoding="utf-8")
    monkeypatch.setenv("FED_BOC_RENDER_CANDIDATE", str(candidate))
    assert _newest_frozen_candidate() == candidate


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
    if not labels:
        pytest.skip("published payload has no rate_label; pin FED_BOC_RENDER_CANDIDATE to exercise that field")
    for bank, label in labels:
        assert label in text, (
            f"the {bank} proxy label {label!r} does not reach the rendered page")


def _card_region(dom: str, bank: str) -> str:
    """The text of exactly one odds card, so a label found in brief prose cannot
    satisfy a card assertion (2026-09-29 code-review round-1 finding)."""
    start = dom.find(f"odds-card {bank}")
    assert start != -1, f"no odds-card {bank} in the rendered DOM"
    end_marker = "odds-card boc" if bank == "fed" else "formula-fold"
    end = dom.find(end_marker, start + 1)
    assert end != -1, f"no end marker {end_marker!r} after odds-card {bank}"
    import re
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", dom[start:end]))


def test_candidate_payload_uses_tenor_specific_average_rate_keys():
    """Round-2 PM finding: the Fed monthly-average value must not sit under a
    quarterly-named key; the BoC quarterly CORRA value keeps its quarterly key.

    Enforced only on pinned candidates: the published payload may legitimately
    predate this contract, and an unpinned run must stay a regression check
    against what is live, not a blocker for data already approved under the old
    schema. Pinning a candidate is what asks "may THIS ship?"."""
    if not os.environ.get("FED_BOC_RENDER_CANDIDATE"):
        pytest.skip("tenor-key convention is a candidate-acceptance gate; pin FED_BOC_RENDER_CANDIDATE")
    candidate = json.loads(CANDIDATE.read_text(encoding="utf-8"))
    fed = candidate["meetings"]["fed"]["pricing"].get("observable_proxy") or {}
    boc = candidate["meetings"]["boc"]["pricing"].get("observable_proxy") or {}
    if "implied_monthly_average_rate" not in fed and "implied_quarterly_average_rate" not in fed:
        pytest.skip("published payload predates the tenor-key contract; pin FED_BOC_RENDER_CANDIDATE")
    assert "implied_monthly_average_rate" in fed, (
        "the Fed October 30-day futures average is monthly tenor; it must not be stored "
        "under a quarterly-named key")
    assert "implied_quarterly_average_rate" not in fed, (
        "a quarterly-named key on the Fed card re-creates the round-2 defect")
    assert "implied_quarterly_average_rate" in boc, (
        "the BoC CORRA contract is genuinely quarterly; its key must say so")


def test_odds_cards_render_the_payloads_tenor_level_and_label():
    """The card itself must show the payload's value and label. Page-wide
    substring checks pass while the card degrades to 'observable proxy level
    available', because the same label text also appears in brief prose."""
    dom = _headless_dump()
    if dom is None:
        pytest.skip("headless render produced no DOM")
    candidate = json.loads(CANDIDATE.read_text(encoding="utf-8"))
    fed = candidate["meetings"]["fed"]["pricing"].get("observable_proxy") or {}
    boc = candidate["meetings"]["boc"]["pricing"].get("observable_proxy") or {}
    fed_level = fed.get("implied_monthly_average_rate")
    boc_level = boc.get("implied_quarterly_average_rate")
    if fed_level is None or boc_level is None:
        pytest.skip("published payload predates the tenor-key contract; pin FED_BOC_RENDER_CANDIDATE")
    fed_region = _card_region(dom, "fed")
    boc_region = _card_region(dom, "boc")
    assert f"{fed_level:.3f}%" in fed_region, (
        f"the Fed card does not show the payload's monthly-average level {fed_level:.3f}%")
    assert fed.get("rate_label") and fed["rate_label"] in fed_region, (
        f"the Fed card does not show the payload's rate_label {fed.get('rate_label')!r}")
    assert f"{boc_level:.3f}%" in boc_region, (
        f"the BoC card does not show the payload's quarterly-average level {boc_level:.3f}%")
    assert boc.get("rate_label") and boc["rate_label"] in boc_region, (
        f"the BoC card does not show the payload's rate_label {boc.get('rate_label')!r}")


def test_missing_pinned_candidate_fails_closed(monkeypatch, tmp_path):
    """A mistyped FED_BOC_RENDER_CANDIDATE must error, not skip 4 tests green."""
    import sys
    self_module = sys.modules[__name__]
    missing = tmp_path / "nope.json"
    monkeypatch.setenv("FED_BOC_RENDER_CANDIDATE", str(missing))
    monkeypatch.setattr(self_module, "CANDIDATE", missing)
    _headless_dump.cache_clear()
    try:
        with pytest.raises(AssertionError, match="FED_BOC_RENDER_CANDIDATE"):
            _headless_dump()
    finally:
        _headless_dump.cache_clear()
