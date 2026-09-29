from __future__ import annotations

import json
import os
import shutil
import subprocess
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

import econ.render_calendar as render_calendar
from econ.fetch_calendar import _resolve_window
from econ.render_calendar import _chart_category, build_context


def _event(name: str, event_id: str, datetime_utc: str, **values) -> dict:
    return {
        "id": f"release-{event_id}",
        "eventId": event_id,
        "datetime_utc": datetime_utc,
        "date": datetime_utc[:10],
        "time": datetime_utc[11:16],
        "country": "US",
        "currency": "USD",
        "event": name,
        "impact": "HIGH",
        "unit": "%",
        "actual": values.get("actual"),
        "forecast": values.get("forecast"),
        "previous": values.get("previous"),
    }


def test_context_uses_toronto_time_and_merges_mom_yoy_rows():
    data = {
        "events": [
            _event("Consumer Price Index (MoM)", "mom", "2026-01-15T01:30:00", forecast="0.2", previous="0.1"),
            _event("Consumer Price Index (YoY)", "yoy", "2026-01-15T01:30:00", forecast="2.8", previous="2.7"),
        ]
    }

    context = build_context(data)

    assert context["start"] == "2026-01-14"
    assert context["end"] == "2026-01-14"
    assert list(context["grouped"]) == ["2026-01-14"]
    release = context["grouped"]["2026-01-14"][0]
    assert release["display_time"] == "8:30 PM"
    assert release["event"] == "Consumer Price Index"
    assert [row["period"] for row in release["period_rows"]] == ["MoM", "YoY"]
    assert [row["forecast"] for row in release["period_rows"]] == [0.2, 2.8]


def test_context_groups_clear_chart_data_and_formats_frequency_labels():
    event = _event(
        "Core Personal Consumption Expenditures - Price Index (YoY)",
        "core-pce",
        "2026-08-26T12:30:00",
        forecast="3.3",
        previous="3.2",
    )
    data = {
        "events": [event],
        "history": {
            "core-pce": [
                {"periodDateUtc": "2026-04-30T00:00:00Z", "actual": 3.0, "consensus": 2.9},
                {"periodDateUtc": "2026-05-31T00:00:00Z", "actual": 3.1, "consensus": 3.0},
                {"periodDateUtc": "2026-06-30T00:00:00Z", "actual": 3.2, "consensus": 3.1},
            ]
        },
        "history_meta": {
            "core-pce": {
                "event": "Core Personal Consumption Expenditures - Price Index (YoY)",
                "currency": "USD",
                "unit": "%",
            }
        },
    }

    context = build_context(data)

    assert [group["name"] for group in context["chart_groups"]] == ["Inflation"]
    chart = context["chart_groups"][0]["charts"][0]
    assert chart["event"] == "Core PCE Price Index"
    assert chart["period_label"] == "Annual change"
    assert chart["upcoming_label"] == "Aug 26 at 8:30 AM"
    assert chart["labels"] == ["Apr '26", "May '26", "Jun '26"]
    assert "consensuses" not in context["chart_data"][0]


def test_timeline_keeps_previous_day_and_splits_us_from_other_regions():
    us_event = _event("US release", "us", "2026-08-24T12:30:00Z")
    ca_event = _event("Canada release", "ca", "2026-08-24T12:30:00Z")
    ca_event.update({"country": "CA", "currency": "CAD"})

    context = build_context({"events": [us_event, ca_event]}, snapshot_date="2026-08-25")

    assert context["start"] == "2026-08-25"
    previous = context["timeline_days"][0]
    assert previous["date"] == "2026-08-24"
    assert previous["is_previous_day"] is True
    assert [event["country"] for event in previous["us_events"]] == ["US"]
    assert [event["country"] for event in previous["other_events"]] == ["CA"]


def test_default_fetch_window_adds_previous_day_without_shortening_forecast():
    assert _resolve_window("2026-08-25", None, None, 7) == ("2026-08-24", "2026-08-31")


def test_housing_price_is_grouped_as_housing_not_inflation():
    assert _chart_category("Housing Price Index (MoM)") == "Housing"


def test_publish_calendar_snapshot_changes_only_data_and_keeps_legacy_html(tmp_path, monkeypatch):
    monkeypatch.setattr(render_calendar, "REPO_ROOT", tmp_path)
    page = tmp_path / "economic-calendar"
    (page / "archive").mkdir(parents=True)
    index = page / "index.html"
    index.write_bytes(b"<html>stable client</html>")
    legacy = page / "archive" / "2026-08-23.html"
    legacy.write_bytes(b"<html>legacy snapshot</html>")
    source_dir = page / "raw" / "2026-08-24"
    source_dir.mkdir(parents=True)
    source_json = source_dir / "economic_calendar.json"
    source_json.write_text('{"count": 1, "events": [{"id": "event-1"}]}', encoding="utf-8")

    latest_json = render_calendar.publish_calendar_snapshot("2026-08-24", source_json)

    assert latest_json.read_bytes() == source_json.read_bytes()
    assert (page / "data" / "archive" / "2026-08-24.json").read_bytes() == source_json.read_bytes()
    assert index.read_bytes() == b"<html>stable client</html>"
    assert legacy.read_bytes() == b"<html>legacy snapshot</html>"
    assert sorted(p.name for p in (page / "archive").glob("*.html")) == ["2026-08-23.html"]
    dates = json.loads((page / "data" / "dates.json").read_text(encoding="utf-8"))
    assert dates == {"latest": "2026-08-24", "dates": ["2026-08-24"]}


def test_daily_cli_does_not_write_any_html(tmp_path, monkeypatch):
    monkeypatch.setattr(render_calendar, "REPO_ROOT", tmp_path)
    page = tmp_path / "economic-calendar"
    (page / "archive").mkdir(parents=True)
    (page / "raw" / "2026-08-25").mkdir(parents=True)
    (page / "raw" / "2026-08-25" / "economic_calendar.json").write_text(
        json.dumps({"start": "2026-08-25", "end": "2026-08-31", "count": 0, "events": [], "history": {}}),
        encoding="utf-8",
    )
    (page / "index.html").write_bytes(b"immutable shell")
    monkeypatch.setattr("sys.argv", ["render_calendar.py", "--date", "2026-08-25"])

    render_calendar.main()

    assert (page / "index.html").read_bytes() == b"immutable shell"
    assert list(page.rglob("*.html")) == [page / "index.html"]
    assert (page / "data" / "latest.json").exists()


def test_daily_cli_rejects_nonfinite_json_without_touching_latest(tmp_path, monkeypatch):
    monkeypatch.setattr(render_calendar, "REPO_ROOT", tmp_path)
    page = tmp_path / "economic-calendar"
    raw = page / "raw" / "2026-08-25" / "economic_calendar.json"
    raw.parent.mkdir(parents=True)
    raw.write_text('{"count": 1, "events": [{"actual": NaN}]}', encoding="utf-8")
    latest = page / "data" / "latest.json"
    latest.parent.mkdir(parents=True)
    latest.write_bytes(b'{"count":0,"events":[]}')
    monkeypatch.setattr("sys.argv", ["render_calendar.py", "--date", "2026-08-25"])

    with pytest.raises((SystemExit, ValueError)):
        render_calendar.main()

    assert latest.read_bytes() == b'{"count":0,"events":[]}'
    assert not (page / "data" / "archive" / "2026-08-25.json").exists()


def test_index_shell_has_no_embedded_release_or_chart_data():
    page = render_calendar.REPO_ROOT / "economic-calendar" / "index.html"
    html = page.read_text(encoding="utf-8")
    assert 'id="trendsContent"' in html
    assert 'id="timelineContent"' in html
    assert 'id="status"' in html
    assert 'data/latest.json' in html
    assert 'data/archive/' in html
    assert 'archive/${date}.html' not in html
    assert 'const chartData = [' not in html
    assert 'data-date="2026-' not in html
    assert 'Next forecast <span class="forecast-pill">' not in html


def _headless_chrome():
    candidates = [shutil.which(name) for name in ("google-chrome", "chromium", "chromium-browser", "chrome", "msedge")]
    if os.name == "nt":
        candidates += [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                       r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"]
    return next((path for path in candidates if path and Path(path).is_file()), None)


def _browser_dom(tmp_path, *, select_date=None, measure_gap=False):
    browser = _headless_chrome()
    if not browser:
        pytest.skip("Chromium is not installed; browser DOM smoke must run on a host with Chrome/Edge")
    source = render_calendar.REPO_ROOT / "economic-calendar"
    page = tmp_path / "economic-calendar"
    (page / "data" / "archive").mkdir(parents=True)
    shell = (source / "index.html").read_text(encoding="utf-8")
    if select_date:
        # Drive the real date selector (rather than navigating directly to ?date=).
        switch = ("<script>setTimeout(() => { const select = document.getElementById('snapshotDate');"
                  f" select.value = '{select_date}'; select.dispatchEvent(new Event('change'));"
                  " }, 300); setInterval(() => document.body.dataset.selection = location.search, 100);</script>")
        shell = shell.replace("</body>", switch + "</body>")
    if measure_gap:
        probe = ("<script>setInterval(() => { const groups = document.querySelectorAll('#trendsContent > .chart-group');"
                 " if (groups.length > 1) document.body.dataset.trendGap ="
                 " String(groups[1].getBoundingClientRect().top - groups[0].getBoundingClientRect().bottom);"
                 " }, 100);</script>")
        shell = shell.replace("</body>", probe + "</body>")
    (page / "index.html").write_text(shell, encoding="utf-8")
    for relative in ("data/dates.json", "data/latest.json", f"data/archive/{select_date or '2026-08-24'}.json"):
        shutil.copyfile(source / relative, page / relative)

    class QuietHandler(SimpleHTTPRequestHandler):
        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(tmp_path)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_port}/economic-calendar/"
        command = [str(browser), "--headless=new", "--no-sandbox", "--disable-gpu", "--disable-background-networking",
                   f"--user-data-dir={tmp_path / 'browser-profile'}", "--virtual-time-budget=4000", "--dump-dom", url]
        result = subprocess.run(command, capture_output=True, text=True, errors="replace", timeout=40)
        assert result.returncode == 0, result.stderr
        return BeautifulSoup(result.stdout, "html.parser")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_browser_renders_current_json_instead_of_embedded_snapshot(tmp_path):
    soup = _browser_dom(tmp_path)
    data_root = render_calendar.REPO_ROOT / "economic-calendar" / "data"
    data = json.loads((data_root / "latest.json").read_text(encoding="utf-8"))
    latest_date = json.loads((data_root / "dates.json").read_text(encoding="utf-8"))["latest"]
    context = build_context(data, latest_date)
    expected_rows = sum(len(rows) for rows in context["grouped"].values())
    assert len(soup.select("#timeline tbody tr")) == expected_rows
    assert len(soup.select(".chart-card canvas")) == len(context["charts"])
    assert soup.select_one("#windowCaption").get_text(strip=True).startswith(latest_date)
    assert soup.select_one("#status").get_text(strip=True) == ""
    assert soup.select_one("#timeline .event-name") is not None


def test_browser_trend_groups_retain_visual_spacing(tmp_path):
    soup = _browser_dom(tmp_path, measure_gap=True)
    assert len(soup.select('#trendsContent > .chart-group')) > 1
    assert float(soup.body['data-trend-gap']) >= 40


def test_browser_date_selector_renders_archived_json_without_html_navigation(tmp_path):
    soup = _browser_dom(tmp_path, select_date="2026-08-24")
    data = json.loads((render_calendar.REPO_ROOT / "economic-calendar" / "data" / "archive" / "2026-08-24.json").read_text(encoding="utf-8"))
    context = build_context(data, "2026-08-24")
    assert soup.body.get("data-selection") == "?date=2026-08-24"
    assert len(soup.select("#timeline tbody tr")) == sum(len(rows) for rows in context["grouped"].values())
    assert len(soup.select(".chart-card canvas")) == len(context["charts"])
    assert soup.select_one("#windowCaption").get_text(strip=True).startswith("2026-08-24")
    assert soup.select_one("#status").get_text(strip=True) == ""
