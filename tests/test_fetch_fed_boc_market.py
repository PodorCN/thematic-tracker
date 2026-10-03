"""Unit tests for scripts/econ/fetch_fed_boc_market.py."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from econ.fetch_fed_boc_market import (
    DEFAULT_TICKERS,
    ZQ_SYMBOL,
    _atomic_write,
    _completed_bars,
    compute_ticker,
    compute_zq_proxy,
    main,
)


def _make_yahoo_chart_payload(timestamps_and_closes: list[tuple[int, float | None]]) -> dict:
    timestamps = [ts for ts, _ in timestamps_and_closes]
    closes = [close for _, close in timestamps_and_closes]
    return {
        "chart": {
            "result": [
                {
                    "meta": {"currency": "USD", "symbol": "SPY"},
                    "timestamp": timestamps,
                    "indicators": {
                        "quote": [
                            {
                                "close": closes,
                            }
                        ]
                    },
                }
            ],
            "error": None,
        }
    }


def test_completed_bars_normal():
    # 2026-10-01 16:00 EDT is 1790884800 (approx timestamp)
    # Using unix timestamps:
    # 1790800000 -> 2026-10-01 in Toronto
    # 1790886400 -> 2026-10-02 in Toronto
    payload = _make_yahoo_chart_payload([
        (1790800000, 570.1234),
        (1790840000, None),  # in-progress or missing bar
        (1790886400, 572.4567),
    ])
    bars = _completed_bars(payload)
    assert len(bars) == 2
    assert bars[0][1] == pytest.approx(570.1234)
    assert bars[1][1] == pytest.approx(572.4567)


def test_completed_bars_errors():
    with pytest.raises(ValueError, match="no chart.result"):
        _completed_bars({"chart": {"result": None}})

    with pytest.raises(ValueError, match="no completed daily bars"):
        _completed_bars(_make_yahoo_chart_payload([]))


def test_compute_ticker_arithmetic():
    # 7 bars representing 7 daily sessions
    bars = [
        ("2026-09-24", 560.00),  # bar -7
        ("2026-09-25", 562.50),  # bar -6 (1w base: 5 sessions back from -1)
        ("2026-09-28", 564.00),  # bar -5
        ("2026-09-29", 565.00),  # bar -4
        ("2026-09-30", 566.00),  # bar -3
        ("2026-10-01", 568.00),  # bar -2 (1d base)
        ("2026-10-02", 570.00),  # bar -1 (latest)
    ]
    ticker = compute_ticker("SPY", bars, name="S&P 500 ETF", unit="USD")

    assert ticker["symbol"] == "SPY"
    assert ticker["name"] == "S&P 500 ETF"
    assert ticker["unit"] == "USD"
    assert ticker["price"] == 570.00
    assert ticker["price_display"] == "570.00"
    assert ticker["session_date"] == "2026-10-02"
    assert ticker["base_1d_date"] == "2026-10-01"
    assert ticker["base_1d_price"] == 568.00
    assert ticker["base_1w_date"] == "2026-09-25"
    assert ticker["base_1w_price"] == 562.50

    # 1d change: (570.00 - 568.00) / 568.00 = 2.0 / 568.00 = +0.0035211...
    expected_1d = (570.00 - 568.00) / 568.00
    assert ticker["chg_1d"] == pytest.approx(expected_1d)
    assert ticker["type_1d"] == "up"
    assert "+0.35% Fri close vs 10-01" in ticker["label_1d"]

    # 1w change: (570.00 - 562.50) / 562.50 = 7.5 / 562.50 = +0.013333...
    expected_1w = (570.00 - 562.50) / 562.50
    assert ticker["chg_1w"] == pytest.approx(expected_1w)
    assert ticker["type_1w"] == "up"
    assert "+1.33% Fri close vs 09-25" in ticker["label_1w"]


def test_compute_ticker_downward_and_short_history():
    # Only 3 bars
    bars = [
        ("2026-10-01", 100.00),
        ("2026-10-02", 95.00),
        ("2026-10-05", 90.00),
    ]
    ticker = compute_ticker("TLT", bars)
    assert ticker["name"] == "20+ Year Treasury"
    assert ticker["unit"] == "USD"
    assert ticker["price"] == 90.00
    # 1d base is bar -2: 95.00
    assert ticker["base_1d_price"] == 95.00
    # 1w base falls back to bar 0 because len < 6
    assert ticker["base_1w_price"] == 100.00
    assert ticker["type_1d"] == "down"
    assert ticker["type_1w"] == "down"
    assert ticker["chg_1d"] == pytest.approx((90.00 - 95.00) / 95.00)
    assert ticker["chg_1w"] == pytest.approx((90.00 - 100.00) / 100.00)


def test_compute_ticker_meta_defaults():
    bars = [("2026-10-01", 70.0), ("2026-10-02", 71.0)]
    ticker = compute_ticker("ZEB.TO", bars)
    assert ticker["name"] == "Canadian banks"
    assert ticker["unit"] == "CAD"


def test_compute_zq_proxy():
    bars = [
        ("2026-10-01", 95.123),
        ("2026-10-02", 95.186),
    ]
    zq = compute_zq_proxy(bars)
    assert zq["session_date"] == "2026-10-02"
    assert zq["observed_price"] == 95.19
    # 100 - 95.19 = 4.810
    assert zq["implied_monthly_average_rate"] == 4.810
    assert "ZQV26.CBT" in zq["instrument"]


def test_atomic_write(tmp_path):
    target = tmp_path / "sub" / "test.txt"
    content = b"hello world\n"
    size, digest = _atomic_write(target, content)
    assert target.is_file()
    assert target.read_bytes() == content
    assert size == len(content)
    import hashlib
    assert digest == hashlib.sha256(content).hexdigest()


def test_main_collector_execution(tmp_path):
    # Mock fetch_chart to return dummy chart data
    mock_payload = _make_yahoo_chart_payload([
        (1790800000, 100.0),
        (1790810000, 101.0),
        (1790820000, 102.0),
        (1790830000, 103.0),
        (1790840000, 104.0),
        (1790850000, 105.0),
        (1790860000, 106.0),
    ])

    out_dir = tmp_path / "staging"

    with patch("econ.fetch_fed_boc_market.fetch_chart") as mock_fetch:
        mock_fetch.return_value = (mock_payload, "https://mock.yahoo/chart", 200)

        # Call main with explicit CLI args
        with patch("sys.argv", [
            "fetch_fed_boc_market.py",
            "--date", "2026-10-03",
            "--out", str(out_dir),
            "--symbols", "SPY,TLT",
        ]):
            main()

    # Verify staging output files
    assert (out_dir / "market_fragment.json").is_file()
    assert (out_dir / "zq_proxy_fragment.json").is_file()
    assert (out_dir / "retrieval-manifest-entries.json").is_file()
    assert (out_dir / "yahoo_SPY_daily.json").is_file()
    assert (out_dir / "yahoo_TLT_daily.json").is_file()
    assert (out_dir / "yahoo_ZQV26_CBT_daily.json").is_file()

    market = json.loads((out_dir / "market_fragment.json").read_text())
    assert len(market["tickers"]) == 2
    assert market["tickers"][0]["symbol"] == "SPY"
    assert market["tickers"][1]["symbol"] == "TLT"
    assert market["since"] == "2026-10-03"

    zq = json.loads((out_dir / "zq_proxy_fragment.json").read_text())
    assert "observed_price" in zq
    assert "implied_monthly_average_rate" in zq

    manifest = json.loads((out_dir / "retrieval-manifest-entries.json").read_text())
    assert len(manifest) == 3  # SPY, TLT, and ZQV26.CBT
    keys = [m["key"] for m in manifest]
    assert "yahoo_SPY_daily" in keys
    assert "yahoo_TLT_daily" in keys
    assert "yahoo_ZQV26_CBT_daily" in keys
