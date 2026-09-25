"""2026-09-21 post-close AI Software refresh.

Run from the repository root:
  env -u PYTHONPATH uv run --isolated --python 3.11 --with yfinance --with pandas \
    python ai-software/tracker_data/refresh-2026-09-21-pm/refresh.py

All collection evidence remains inside ai-software/tracker_data. Canonical files are
copied from this frozen refresh only after the collection validates.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yfinance as yf

OUT = Path(__file__).resolve().parent
DATA_DIR = OUT.parent
THEME = DATA_DIR.parent
assert THEME.name == "ai-software", THEME

TICKERS = ["IGV", "QQQ", "CRM", "NOW", "WDAY", "ADBE", "INTU"]
ASOF_EXCLUSIVE = "2026-09-22"
PRIOR_UPDATED = "2026-09-18"
WINDOW_START = "2025-09-01"


def dump(name: str, value: object) -> None:
    (OUT / name).write_text(
        json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )


def clean(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    frame.index = pd.to_datetime([str(value.date()) for value in frame.index])
    frame.index.name = "Date"
    frame = frame.loc[frame.index < ASOF_EXCLUSIVE]
    assert len(frame) > 42
    assert not frame.index.duplicated().any()
    assert frame.index.is_monotonic_increasing
    assert frame[["Open", "High", "Low", "Close", "Volume"]].notna().all().all()
    assert (frame["Close"] > 0).all()
    return frame


def fetch(ticker: str) -> pd.DataFrame:
    for attempt in range(1, 4):
        try:
            frame = yf.Ticker(ticker).history(
                period="14mo",
                interval="1d",
                auto_adjust=True,
                actions=True,
                raise_errors=True,
            )
            frame = clean(frame)
            print(
                ticker,
                len(frame),
                str(frame.index[-1].date()),
                float(frame["Close"].iloc[-1]),
                flush=True,
            )
            return frame
        except Exception as exc:
            print(ticker, "attempt", attempt, repr(exc), flush=True)
            if attempt == 3:
                raise
            time.sleep(2)
    raise AssertionError("unreachable")


def main() -> None:
    frames: dict[str, pd.DataFrame] = {}
    for ticker in TICKERS:
        frame = fetch(ticker)
        frame.to_csv(OUT / f"{ticker}.csv")
        frames[ticker] = frame

    main_ticker, benchmark = "IGV", "QQQ"
    support = ["CRM", "NOW"]
    window = {ticker: frame.loc[WINDOW_START:] for ticker, frame in frames.items()}
    assert all(not frame.empty for frame in window.values())
    aligned = pd.concat(
        [window[ticker]["Close"].rename(ticker) for ticker in [main_ticker, benchmark, *support]],
        axis=1,
        join="inner",
    ).dropna()
    assert aligned.index[-1] == frames[main_ticker].index[-1]

    chart = {"dates": [str(value.date()) for value in aligned.index]}
    for key, ticker in zip(
        ["zeb_norm", "tsx_norm", "bank_norm", "hfin_norm"],
        [main_ticker, benchmark, *support],
    ):
        chart[key] = (aligned[ticker] / aligned[ticker].iloc[0] * 100).round(4).tolist()
    wday = window["WDAY"]
    chart["spx_dates"] = [str(value.date()) for value in wday.index]
    chart["spx_norm"] = (wday["Close"] / wday["Close"].iloc[0] * 100).round(4).tolist()
    chart["volume"] = frames[main_ticker].loc[aligned.index, "Volume"].astype(int).tolist()
    chart["zeb_ret"] = [None] + (
        aligned[main_ticker].pct_change().iloc[1:] * 100
    ).round(4).tolist()
    dump("chartdata.json", chart)

    metrics: dict[str, object] = {}
    for ticker, frame in frames.items():
        ticker_window = window[ticker]
        last = frame.index[-1]
        baseline_rows = frame.loc[frame.index < "2026-01-01"]
        assert not baseline_rows.empty
        ytd_baseline = baseline_rows["Close"].iloc[-1]
        history_52wk = frame.loc[
            (frame.index > last - pd.Timedelta(weeks=52)) & (frame.index <= last)
        ]
        daily = frame["Close"].pct_change() * 100
        volume_ratio = frame["Volume"] / frame["Volume"].rolling(20).mean()
        pd.DataFrame(
            {
                "Close": frame["Close"],
                "daily_return_pct": daily,
                "volume": frame["Volume"],
                "volume_current_inclusive_20d": volume_ratio,
            }
        ).to_csv(OUT / f"{ticker}.derived.csv")
        metrics[ticker] = {
            "first": str(frame.index[0].date()),
            "latest": str(last.date()),
            "latest_close": float(frame["Close"].iloc[-1]),
            "daily_return": float(daily.iloc[-1]),
            "window_start": str(ticker_window.index[0].date()),
            "window_return": float(
                (ticker_window["Close"].iloc[-1] / ticker_window["Close"].iloc[0] - 1) * 100
            ),
            "ytd_baseline_date": str(baseline_rows.index[-1].date()),
            "ytd_baseline": float(ytd_baseline),
            "ytd": float((frame["Close"].iloc[-1] / ytd_baseline - 1) * 100),
            "high_52wk": float(history_52wk["High"].max()),
            "high_52wk_date": str(history_52wk["High"].idxmax().date()),
            "distance_high": float(
                (frame["Close"].iloc[-1] / history_52wk["High"].max() - 1) * 100
            ),
            "trough": float(ticker_window["Low"].min()),
            "trough_date": str(ticker_window["Low"].idxmin().date()),
            "from_trough": float(
                (frame["Close"].iloc[-1] / ticker_window["Low"].min() - 1) * 100
            ),
            "volume": int(frame["Volume"].iloc[-1]),
            "volume_ratio": float(volume_ratio.iloc[-1]),
        }

    daily_pair = pd.concat(
        [frames[ticker]["Close"].pct_change().mul(100).rename(ticker) for ticker in [main_ticker, benchmark]],
        axis=1,
        join="inner",
    ).dropna()
    main_volume_ratio = frames[main_ticker]["Volume"] / frames[main_ticker]["Volume"].rolling(20).mean()
    checks = []
    for market_date, row in daily_pair.iterrows():
        main_move, benchmark_move = map(float, row)
        checks.append(
            {
                "date": str(market_date.date()),
                "main": main_move,
                "benchmark": benchmark_move,
                "volume_ratio": float(main_volume_ratio.loc[market_date])
                if pd.notna(main_volume_ratio.loc[market_date])
                else None,
                "absolute_trigger": abs(main_move) >= 1.5,
                "divergence_trigger": abs(main_move - benchmark_move) >= 1
                and main_move * benchmark_move <= 0
                and main_move != benchmark_move,
            }
        )

    monthly = []
    for month in pd.period_range("2025-09", "2026-02", freq="M"):
        month_daily = daily_pair.loc[str(month)]
        end = month_daily.index[-1]
        before = frames[main_ticker].loc[
            frames[main_ticker].index < month_daily.index[0]
        ].index[-1]
        low_date = month_daily[main_ticker].idxmin()
        high_date = month_daily[main_ticker].idxmax()
        monthly.append(
            {
                "month": str(month),
                "date": str(end.date()),
                "main": float(
                    (frames[main_ticker].loc[end, "Close"] / frames[main_ticker].loc[before, "Close"] - 1)
                    * 100
                ),
                "benchmark": float(
                    (frames[benchmark].loc[end, "Close"] / frames[benchmark].loc[before, "Close"] - 1)
                    * 100
                ),
                "min_date": str(low_date.date()),
                "min": float(month_daily.loc[low_date, main_ticker]),
                "min_volume_ratio": float(main_volume_ratio.loc[low_date]),
                "max_date": str(high_date.date()),
                "max": float(month_daily.loc[high_date, main_ticker]),
                "max_volume_ratio": float(main_volume_ratio.loc[high_date]),
            }
        )

    excess = (chart["zeb_norm"][-1] - chart["zeb_norm"][-42]) - (
        chart["tsx_norm"][-1] - chart["tsx_norm"][-42]
    )
    evidence = {
        "provider": "Yahoo Finance / yfinance; auto_adjust=True",
        "yfinance_version": yf.__version__,
        "pandas_version": pd.__version__,
        "retrieved_utc": datetime.now(timezone.utc).isoformat(),
        "asof_exclusive": ASOF_EXCLUSIVE,
        "prior_updated": PRIOR_UPDATED,
        "metrics": metrics,
        "validity": {
            "first": chart["dates"][-42],
            "last": chart["dates"][-1],
            "normalized_point_excess": excess,
        },
        "since_prior_exclusive": [row for row in checks if row["date"] > PRIOR_UPDATED],
        "all_threshold_events": [
            row for row in checks if row["absolute_trigger"] or row["divergence_trigger"]
        ],
        "all_daily_checks": checks,
        "months": monthly,
    }
    dump("refresh_evidence.json", evidence)
    print(
        json.dumps(
            {
                "metrics": metrics,
                "validity": evidence["validity"],
                "since_prior_exclusive": evidence["since_prior_exclusive"],
            },
            indent=2,
        ),
        flush=True,
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        dump("failure.json", {"error": repr(exc), "publication_preserved": True})
        raise
