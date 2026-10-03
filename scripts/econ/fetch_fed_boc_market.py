"""Fetch Fed/BOC market-validation closes + Fed-funds proxy from Yahoo chart API.

Automates the most mechanical part of the daily Fed/BOC operator run: the six
market-strip closes (SPY, TLT, XLF, XLE, GLD, ZEB.TO) and the ZQV26.CBT October
30-day Fed-funds proxy. Everything else in the candidate (drivers, calendar,
decision_brief) still needs human research + independent PM review.

Outputs a staging dir (NOT a publication):

    <out>/yahoo_<SYM>_daily.json        raw Yahoo chart captures (evidence)
    <out>/market_fragment.json          `market` object ready to paste into dashboard.json
    <out>/zq_proxy_fragment.json        Fed observable_proxy fragment (monthly-average)
    <out>/retrieval-manifest-entries.json  sha256/bytes/URL rows for the candidate manifest

Computation contract (matches the 2026-10-0x operator convention):
  - price = displayed 2dp close of the last completed daily bar
  - chg_1d = (price - base_1d) / base_1d on DISPLAYED 2dp values
  - chg_1w = (price - base_1w) / base_1w, base_1w = 5 sessions back
  - implied_monthly_average_rate = round(100 - displayed ZQ close, 3)

Example:
    python scripts/econ/fetch_fed_boc_market.py --date 2026-10-04
    python scripts/econ/fetch_fed_boc_market.py --date 2026-10-04 --out /tmp/mkt --symbols SPY,TLT
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

TORONTO = ZoneInfo("America/Toronto")
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) thematic-tracker/1.0"}
DEFAULT_TICKERS = ["SPY", "TLT", "XLF", "XLE", "GLD", "ZEB.TO"]
ZQ_SYMBOL = "ZQV26.CBT"
TICKER_META = {
    "SPY": ("S&P 500", "USD"),
    "TLT": ("20+ Year Treasury", "USD"),
    "XLF": ("Financials", "USD"),
    "XLE": ("Energy", "USD"),
    "GLD": ("Gold", "USD"),
    "ZEB.TO": ("Canadian banks", "CAD"),
}
YAHOO_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range=1mo&interval=1d&events=history"
YAHOO_FALLBACK_URL = "https://query2.finance.yahoo.com/v8/finance/chart/{sym}?range=1mo&interval=1d&events=div%2Csplits"


def _now_toronto() -> datetime.datetime:
    return datetime.datetime.now(TORONTO)


def fetch_chart(symbol: str, timeout: int = 30) -> tuple[dict, str, int]:
    """Return (payload, url_used, http_status). Raises on total failure."""
    last_exc = None
    for url in (YAHOO_URL.format(sym=symbol), YAHOO_FALLBACK_URL.format(sym=symbol)):
        try:
            resp = requests.get(url, headers=UA, timeout=timeout)
            if resp.status_code == 200:
                return resp.json(), url, resp.status_code
            last_exc = RuntimeError(f"HTTP {resp.status_code} for {symbol}")
        except Exception as exc:
            last_exc = exc
            continue
    raise RuntimeError(f"Yahoo fetch failed for {symbol}: {last_exc}")


def _completed_bars(payload: dict) -> list[tuple[str, float]]:
    """Extract (toronto_session_date, raw_close) for bars with a close."""
    result = (payload.get("chart") or {}).get("result") or []
    if not result:
        raise ValueError("Yahoo payload has no chart.result")
    result = result[0]
    stamps = result.get("timestamp") or []
    quotes = ((result.get("indicators") or {}).get("quote") or [{}])[0]
    closes = quotes.get("close") or []
    bars = []
    for ts, close in zip(stamps, closes):
        if close is not None:
            try:
                day = datetime.datetime.fromtimestamp(ts, TORONTO).date().isoformat()
            except (OSError, OverflowError, ValueError) as exc:
                raise ValueError(f"bad Yahoo timestamp {ts!r}") from exc
            bars.append((day, float(close)))
    if not bars:
        raise ValueError("Yahoo payload has no completed daily bars")
    return bars


def compute_ticker(
    symbol: str,
    bars: list[tuple[str, float]],
    name: str = "",
    unit: str = "",
) -> dict:
    """Build one market-strip ticker entry from completed bars (oldest->newest)."""
    meta_name, meta_unit = TICKER_META.get(symbol, (symbol, "USD"))
    display_name = name or meta_name
    display_unit = unit or meta_unit

    session_date, raw = bars[-1]
    if len(bars) >= 2:
        base_1d_date, base_1d_raw = bars[-2]
    else:
        base_1d_date, base_1d_raw = session_date, raw

    if len(bars) >= 6:
        base_1w_date, base_1w_raw = bars[-6]
    else:
        base_1w_date, base_1w_raw = bars[0]

    price = round(raw, 2)
    base_1d = round(base_1d_raw, 2)
    base_1w = round(base_1w_raw, 2)

    chg_1d = (price - base_1d) / base_1d if base_1d else 0.0
    chg_1w = (price - base_1w) / base_1w if base_1w else 0.0

    weekday = datetime.date.fromisoformat(session_date).strftime("%a")

    return {
        "symbol": symbol,
        "name": display_name,
        "unit": display_unit,
        "price": price,
        "price_display": f"{price:.2f}",
        "chg_1d": chg_1d,
        "chg_1w": chg_1w,
        "label_1d": f"{chg_1d:+.2%} {weekday} close vs {base_1d_date[5:]}",
        "label_1w": f"{chg_1w:+.2%} {weekday} close vs {base_1w_date[5:]}",
        "type_1d": "up" if chg_1d >= 0 else "down",
        "type_1w": "up" if chg_1w >= 0 else "down",
        "observed_at_toronto": f"{session_date}T16:00:00-04:00",
        "session_date": session_date,
        "base_1d_date": base_1d_date,
        "base_1d_price": base_1d,
        "base_1w_date": base_1w_date,
        "base_1w_price": base_1w,
        "price_type": "completed regular-session daily close (session close 16:00 Toronto); Yahoo's 09:30 daily-bar timestamp is candle start only",
        "comparison_basis": "Changes use displayed two-decimal prices/bases.",
    }


def compute_zq_proxy(bars: list[tuple[str, float]]) -> dict:
    """Build the Fed monthly-average proxy fragment from ZQV26.CBT bars."""
    session_date, raw = bars[-1]
    observed = round(raw, 2)
    return {
        "instrument": "ZQV26.CBT October 30-day Fed funds futures contract (monthly-average proxy; not a FedWatch distribution)",
        "observed_price": observed,
        "session_date": session_date,
        "implied_monthly_average_rate": round(100 - observed, 3),
        "price_type": "last completed daily bar close",
    }


def _atomic_write(path: Path, data: bytes) -> tuple[int, str]:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)
    digest = hashlib.sha256(data).hexdigest()
    return len(data), digest


def main() -> None:
    ap = argparse.ArgumentParser(description="Fetch Fed/BOC market closes + ZQ proxy (staging only)")
    ap.add_argument("--date", default=_now_toronto().date().isoformat(), help="Toronto snapshot date YYYY-MM-DD")
    ap.add_argument("--out", default=None, help="staging dir (default fed-boc-watcher/data/.market-staging/<date>/)")
    ap.add_argument("--symbols", default=",".join(DEFAULT_TICKERS), help="comma-separated Yahoo symbols")
    ap.add_argument("--timeout", type=int, default=30)
    args = ap.parse_args()

    datetime.date.fromisoformat(args.date)
    repo_root = Path(__file__).resolve().parent.parent.parent
    if args.out:
        out = Path(args.out)
    else:
        out = repo_root / "fed-boc-watcher" / "data" / ".market-staging" / args.date
    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()] or list(DEFAULT_TICKERS)

    retrieved_at = _now_toronto().isoformat(timespec="seconds")
    manifest = []
    tickers = []
    for sym in symbols:
        payload, url, status = fetch_chart(sym, timeout=args.timeout)
        raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode() + b"\n"
        fname = f"yahoo_{sym.replace('.', '_')}_daily.json"
        size, digest = _atomic_write(out / fname, raw)
        manifest.append({
            "key": f"yahoo_{sym}_daily",
            "evidence_path": str(out / fname),
            "source_url": url,
            "http_status": status,
            "retrieved_at_toronto": retrieved_at,
            "bytes": size,
            "sha256": digest,
        })
        bars = _completed_bars(payload)
        entry = compute_ticker(sym, bars)
        entry["source_url"] = url
        tickers.append(entry)
        print(f"{sym}: {entry['price_display']} {entry['label_1d']} / {entry['label_1w']}")

    zq_payload, zq_url, zq_status = fetch_chart(ZQ_SYMBOL, timeout=args.timeout)
    zq_raw = json.dumps(zq_payload, ensure_ascii=False, separators=(",", ":")).encode() + b"\n"
    zq_fname = "yahoo_ZQV26_CBT_daily.json"
    size, digest = _atomic_write(out / zq_fname, zq_raw)
    manifest.append({
        "key": "yahoo_ZQV26_CBT_daily",
        "evidence_path": str(out / zq_fname),
        "source_url": zq_url,
        "http_status": zq_status,
        "retrieved_at_toronto": retrieved_at,
        "bytes": size,
        "sha256": digest,
    })
    zq_bars = _completed_bars(zq_payload)
    zq = compute_zq_proxy(zq_bars)
    zq["source_url"] = zq_url
    zq["retrieved_at_toronto"] = retrieved_at
    print(f"ZQV26: {zq['observed_price']:.2f} -> {zq['implied_monthly_average_rate']:.3f}% monthly avg")

    session_dates = {t["session_date"] for t in tickers} | {zq["session_date"]}
    market = {
        "data_session_date": sorted(session_dates)[-1],
        "as_of_close": f"{sorted(session_dates)[-1]}T16:00:00-04:00",
        "as_of_toronto": retrieved_at,
        "since": args.date,
        "tickers": tickers,
        "note": "STAGING ONLY - operator must verify session dates are the last completed close, then paste into dashboard.json; CORRA/TMX and all drivers still manual.",
    }
    frag, _ = _atomic_write(
        out / "market_fragment.json",
        (json.dumps(market, ensure_ascii=False, indent=2) + "\n").encode(),
    )
    _atomic_write(
        out / "zq_proxy_fragment.json",
        (json.dumps(zq, ensure_ascii=False, indent=2) + "\n").encode(),
    )
    _atomic_write(
        out / "retrieval-manifest-entries.json",
        (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode(),
    )
    print(f"wrote {out} ({len(tickers)} tickers + ZQ proxy, {frag} bytes market fragment)")


if __name__ == "__main__":
    main()
