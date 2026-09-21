"""2026-09-21 post-close Canadian Banks refresh.

Run from the repository root:
  env -u PYTHONPATH uv run --isolated --python 3.11 --with yfinance --with pandas \
    python canadian-banks/tracker_data/refresh-2026-09-21-pm/refresh.py

All collection evidence remains inside canadian-banks/tracker_data. Canonical files are
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
assert THEME.name == "canadian-banks", THEME

TICKERS = ["ZEB.TO", "BANK.TO", "HFIN.TO", "^GSPTSE", "^GSPC"]
ASOF_EXCLUSIVE = "2026-09-22"
PRIOR_UPDATED = "2026-09-18"


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


def fetch(ticker: str, **kwargs: object) -> pd.DataFrame:
    for attempt in range(1, 4):
        try:
            frame = yf.Ticker(ticker).history(
                interval="1d",
                auto_adjust=True,
                actions=True,
                raise_errors=True,
                **kwargs,
            )
            frame = clean(frame)
            print(
                ticker,
                kwargs,
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
    references: dict[str, pd.DataFrame] = {}

    for ticker in TICKERS:
        name = ticker.replace("^", "")
        frame = fetch(ticker, period="3mo")
        reference = fetch(ticker, start="2025-07-01", end=ASOF_EXCLUSIVE)
        frame.to_csv(OUT / f"{name}.csv")
        reference.to_csv(OUT / f"{name}.reference.csv")
        frames[ticker] = frame
        references[ticker] = reference

    main_ticker, benchmark = "ZEB.TO", "^GSPTSE"
    support = ["BANK.TO", "HFIN.TO"]
    aligned = pd.concat(
        [frames[ticker]["Close"].rename(ticker) for ticker in [main_ticker, benchmark, *support]],
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
    spx = frames["^GSPC"]
    chart["spx_dates"] = [str(value.date()) for value in spx.index]
    chart["spx_norm"] = (spx["Close"] / spx["Close"].iloc[0] * 100).round(4).tolist()
    chart["volume"] = frames[main_ticker].loc[aligned.index, "Volume"].astype(int).tolist()
    chart["zeb_ret"] = [None] + (
        aligned[main_ticker].pct_change().iloc[1:] * 100
    ).round(4).tolist()
    dump("chartdata.json", chart)

    metrics: dict[str, object] = {}
    for ticker, frame in frames.items():
        reference = references[ticker]
        last = frame.index[-1]
        baseline_rows = reference.loc[reference.index < "2026-01-01"]
        assert not baseline_rows.empty
        ytd_baseline = baseline_rows["Close"].iloc[-1]
        history_52wk = reference.loc[
            (reference.index > last - pd.Timedelta(weeks=52)) & (reference.index <= last)
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
        ).to_csv(OUT / f"{ticker.replace('^', '')}.derived.csv")
        metrics[ticker] = {
            "first": str(frame.index[0].date()),
            "latest": str(last.date()),
            "latest_close": float(frame["Close"].iloc[-1]),
            "daily_return": float(daily.iloc[-1]),
            "window_start": str(frame.index[0].date()),
            "window_return": float((frame["Close"].iloc[-1] / frame["Close"].iloc[0] - 1) * 100),
            "ytd_baseline_date": str(baseline_rows.index[-1].date()),
            "ytd_baseline": float(ytd_baseline),
            "ytd": float((frame["Close"].iloc[-1] / ytd_baseline - 1) * 100),
            "high_52wk": float(history_52wk["High"].max()),
            "distance_high": float((frame["Close"].iloc[-1] / history_52wk["High"].max() - 1) * 100),
            "trough": float(frame["Low"].min()),
            "trough_date": str(frame["Low"].idxmin().date()),
            "from_trough": float((frame["Close"].iloc[-1] / frame["Low"].min() - 1) * 100),
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
