"""Cron 2026-09-19 (Sat) full idempotent re-pull; settled bars through Fri 2026-09-18.
Writes canonical CSVs into <theme>/tracker_data/ (overwrite), evidence into refresh-2026-09-19/.
Run from repo root: env -u PYTHONPATH uv run --isolated --python 3.11 --with yfinance --with pandas python tmp_refresh_0919.py
"""
import json, time
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parent
ASOF = "2026-09-19"

def clean(df):
    df = df.copy()
    df.index = pd.to_datetime([str(x.date()) for x in df.index])
    df.index.name = "Date"
    df = df.loc[df.index < ASOF]
    assert len(df) > 42 and not df.index.duplicated().any()
    assert df[["Open","High","Low","Close","Volume"]].notna().all().all()
    assert (df.Close > 0).all()
    return df

def fetch(t, **kw):
    for attempt in range(3):
        try:
            d = clean(yf.Ticker(t).history(interval="1d", auto_adjust=True, actions=True, raise_errors=True, **kw))
            print(t, kw.get("period") or kw.get("start"), len(d), str(d.index[-1].date()), float(d.Close.iloc[-1]), flush=True)
            return d
        except Exception as e:
            print(t, "attempt", attempt+1, repr(e), flush=True)
            if attempt == 2: raise
            time.sleep(2)

def run(theme, tickers, period):
    data_dir = ROOT / theme / "tracker_data"
    out = data_dir / "refresh-2026-09-19"
    out.mkdir(exist_ok=True)
    bank = theme == "canadian-banks"
    frames, refs = {}, {}
    for ticker in tickers:
        d = fetch(ticker, period=period)
        name = ticker.replace("^", "")
        d.to_csv(data_dir / (name + ".csv"))          # canonical overwrite
        d.to_csv(out / (name + ".csv"))
        frames[ticker] = d
        ref = fetch(ticker, start="2025-07-01", end=ASOF) if bank else d
        if bank: ref.to_csv(out / (name + ".reference.csv"))
        refs[ticker] = ref
    main, bench = ("ZEB.TO", "^GSPTSE") if bank else ("IGV", "QQQ")
    support = ["BANK.TO", "HFIN.TO"] if bank else ["CRM", "NOW"]
    window = {t: (d if bank else d.loc["2025-09-01":]) for t, d in frames.items()}
    aligned = pd.concat([window[t].Close.rename(t) for t in [main, bench, *support]], axis=1, join="inner").dropna()
    cd = {"dates": [str(x.date()) for x in aligned.index]}
    for key, t in zip(["zeb_norm","tsx_norm","bank_norm","hfin_norm"], [main, bench, *support]):
        cd[key] = (aligned[t]/aligned[t].iloc[0]*100).round(4).tolist()
    extra = "^GSPC" if bank else "WDAY"
    e = window[extra]
    cd["spx_dates"] = [str(x.date()) for x in e.index]
    cd["spx_norm"] = (e.Close/e.Close.iloc[0]*100).round(4).tolist()
    cd["volume"] = frames[main].loc[aligned.index, "Volume"].astype(int).tolist()
    cd["zeb_ret"] = [None] + (aligned[main].pct_change().iloc[1:]*100).round(4).tolist()
    (out/"chartdata.json").write_text(json.dumps(cd, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    (data_dir/"chartdata.json").write_text(json.dumps(cd, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    metrics = {}
    for t, d in frames.items():
        ref = refs[t]; last = d.index[-1]; w = window[t]
        ybase = ref.loc[ref.index < "2026-01-01"].Close.iloc[-1]
        hist = ref.loc[(ref.index > last - pd.Timedelta(weeks=52)) & (ref.index <= last)]
        daily = d.Close.pct_change()*100; vr = d.Volume/d.Volume.rolling(20).mean()
        metrics[t] = {"first": str(d.index[0].date()), "latest": str(last.date()), "latest_close": float(d.Close.iloc[-1]),
            "daily_return": float(daily.iloc[-1]), "window_start": str(w.index[0].date()),
            "window_return": float((w.Close.iloc[-1]/w.Close.iloc[0]-1)*100),
            "ytd_baseline_date": str(ref.loc[ref.index < "2026-01-01"].index[-1].date()), "ytd_baseline": float(ybase),
            "ytd": float((d.Close.iloc[-1]/ybase-1)*100), "high_52wk": float(hist.High.max()),
            "distance_high": float((d.Close.iloc[-1]/hist.High.max()-1)*100), "trough": float(w.Low.min()),
            "trough_date": str(w.Low.idxmin().date()), "from_trough": float((d.Close.iloc[-1]/w.Low.min()-1)*100),
            "volume": int(d.Volume.iloc[-1]), "volume_ratio": float(vr.iloc[-1])}
    daily = pd.concat([frames[t].Close.pct_change().mul(100).rename(t) for t in [main, bench]], axis=1, join="inner").dropna()
    vr = frames[main].Volume/frames[main].Volume.rolling(20).mean()
    records = []
    for date, row in daily.iterrows():
        a, b = map(float, row)
        records.append({"date": str(date.date()), "main": a, "benchmark": b,
            "volume_ratio": float(vr.loc[date]) if pd.notna(vr.loc[date]) else None,
            "absolute_trigger": abs(a) >= 1.5, "divergence_trigger": abs(a-b) >= 1 and a*b <= 0 and a != b})
    excess = (cd["zeb_norm"][-1]-cd["zeb_norm"][-42]) - (cd["tsx_norm"][-1]-cd["tsx_norm"][-42])
    ev = {"provider": "Yahoo Finance / yfinance; auto_adjust=True", "yfinance_version": yf.__version__,
          "pandas_version": pd.__version__, "retrieved_utc": datetime.now(timezone.utc).isoformat(),
          "asof_exclusive": ASOF, "metrics": metrics,
          "validity": {"first": cd["dates"][-42], "last": cd["dates"][-1], "normalized_point_excess": excess},
          "since_0917_inclusive": [r for r in records if r["date"] >= "2026-09-17"],
          "all_threshold_events": [r for r in records if r["absolute_trigger"] or r["divergence_trigger"]]}
    (out/"refresh_evidence.json").write_text(json.dumps(ev, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    (data_dir/"refresh_evidence.json").write_text(json.dumps(ev, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    print(theme, "VALIDITY", ev["validity"], flush=True)
    print(theme, "SINCE0917", json.dumps(ev["since_0917_inclusive"]), flush=True)

run("canadian-banks", ["ZEB.TO","BANK.TO","HFIN.TO","^GSPTSE","^GSPC"], "3mo")
run("ai-software", ["IGV","QQQ","CRM","NOW","WDAY","ADBE","INTU"], "14mo")
print("DONE")
