"""Reproduce Sep 18 pre-open refresh (covers settled Sep 17 close). Run from repo root:
env -u PYTHONPATH uv run --isolated --python 3.11 --with yfinance --with pandas python THEME/tracker_data/refresh-2026-09-18/refresh.py
No publication writes; all outputs stay next to this script.
"""
import json, sys, time, hashlib
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import yfinance as yf
OUT=Path(__file__).resolve().parent
THEME=OUT.parent.parent
BANK=THEME.name=="canadian-banks"
TICKERS=["ZEB.TO","BANK.TO","HFIN.TO","^GSPTSE","^GSPC"] if BANK else ["IGV","QQQ","CRM","NOW","WDAY","ADBE","INTU"]
ASOF="2026-09-18"
PRIOR="2026-09-16"
def dump(name,obj): (OUT/name).write_text(json.dumps(obj,indent=2,allow_nan=False)+"\n",encoding="utf-8")
def clean(df):
    df=df.copy()
    df.index=pd.to_datetime([str(x.date()) for x in df.index])
    df.index.name="Date"
    df=df.loc[df.index<ASOF]
    assert len(df)>42 and not df.index.duplicated().any()
    assert df[["Open","High","Low","Close","Volume"]].notna().all().all()
    assert (df.Close>0).all()
    return df
def fetch(t,**kw):
    for attempt in range(3):
        try:
            d=clean(yf.Ticker(t).history(interval="1d",auto_adjust=True,actions=True,raise_errors=True,**kw))
            print(t,kw,len(d),str(d.index[-1].date()),float(d.Close.iloc[-1]),flush=True)
            return d
        except Exception as e:
            print(t,"attempt",attempt+1,repr(e),flush=True)
            if attempt==2: raise
            time.sleep(2)
frames={}; refs={}; records=[]
try:
    for ticker in TICKERS:
        d=fetch(ticker,period="3mo" if BANK else "14mo")
        name=ticker.replace("^","")
        d.to_csv(OUT/(name+".csv"))
        frames[ticker]=d
        ref=fetch(ticker,start="2025-07-01",end=ASOF) if BANK else d
        if BANK: ref.to_csv(OUT/(name+".reference.csv"))
        refs[ticker]=ref
    main,bench=("ZEB.TO","^GSPTSE") if BANK else ("IGV","QQQ")
    support=["BANK.TO","HFIN.TO"] if BANK else ["CRM","NOW"]
    window={t:(d if BANK else d.loc["2025-09-01":]) for t,d in frames.items()}
    aligned=pd.concat([window[t].Close.rename(t) for t in [main,bench,*support]],axis=1,join="inner").dropna()
    cd={"dates":[str(x.date()) for x in aligned.index]}
    for key,t in zip(["zeb_norm","tsx_norm","bank_norm","hfin_norm"],[main,bench,*support]):
        cd[key]=(aligned[t]/aligned[t].iloc[0]*100).round(4).tolist()
    extra="^GSPC" if BANK else "WDAY"
    e=window[extra]
    cd["spx_dates"]=[str(x.date()) for x in e.index]
    cd["spx_norm"]=(e.Close/e.Close.iloc[0]*100).round(4).tolist()
    cd["volume"]=frames[main].loc[aligned.index,"Volume"].astype(int).tolist()
    cd["zeb_ret"]=[None]+(aligned[main].pct_change().iloc[1:]*100).round(4).tolist()
    dump("chartdata.json",cd)
    metrics={}
    for t,d in frames.items():
        ref=refs[t]; last=d.index[-1]; w=window[t]
        ybase=ref.loc[ref.index<"2026-01-01"].Close.iloc[-1]
        hist=ref.loc[(ref.index>last-pd.Timedelta(weeks=52))&(ref.index<=last)]
        daily=d.Close.pct_change()*100; vr=d.Volume/d.Volume.rolling(20).mean()
        derived=pd.DataFrame({"Close":d.Close,"daily_return_pct":daily,"volume":d.Volume,"volume_current_inclusive_20d":vr})
        derived.to_csv(OUT/(t.replace("^","")+".derived.csv"))
        metrics[t]={"first":str(d.index[0].date()),"latest":str(last.date()),"latest_close":float(d.Close.iloc[-1]),"daily_return":float(daily.iloc[-1]),"window_start":str(w.index[0].date()),"window_return":float((w.Close.iloc[-1]/w.Close.iloc[0]-1)*100),"ytd_baseline_date":str(ref.loc[ref.index<"2026-01-01"].index[-1].date()),"ytd_baseline":float(ybase),"ytd":float((d.Close.iloc[-1]/ybase-1)*100),"high_52wk":float(hist.High.max()),"distance_high":float((d.Close.iloc[-1]/hist.High.max()-1)*100),"trough":float(w.Low.min()),"trough_date":str(w.Low.idxmin().date()),"from_trough":float((d.Close.iloc[-1]/w.Low.min()-1)*100),"volume":int(d.Volume.iloc[-1]),"volume_ratio":float(vr.iloc[-1])}
    daily=pd.concat([frames[t].Close.pct_change().mul(100).rename(t) for t in [main,bench]],axis=1,join="inner").dropna()
    vr=frames[main].Volume/frames[main].Volume.rolling(20).mean()
    for date,row in daily.iterrows():
        a,b=map(float,row)
        records.append({"date":str(date.date()),"main":a,"benchmark":b,"volume_ratio":float(vr.loc[date]) if pd.notna(vr.loc[date]) else None,"absolute_trigger":abs(a)>=1.5,"divergence_trigger":abs(a-b)>=1 and a*b<=0 and a!=b})
    months=[]
    for month in pd.period_range("2025-09","2026-02",freq="M") if not BANK else []:
        dm=daily.loc[str(month)]
        end=dm.index[-1]; before=frames[main].loc[frames[main].index<dm.index[0]].index[-1]
        lo=dm[main].idxmin(); hi=dm[main].idxmax()
        months.append({"month":str(month),"date":str(end.date()),"main":float((frames[main].loc[end,"Close"]/frames[main].loc[before,"Close"]-1)*100),"benchmark":float((frames[bench].loc[end,"Close"]/frames[bench].loc[before,"Close"]-1)*100),"min_date":str(lo.date()),"min":float(dm.loc[lo,main]),"min_volume_ratio":float(vr.loc[lo]),"max_date":str(hi.date()),"max":float(dm.loc[hi,main]),"max_volume_ratio":float(vr.loc[hi])})
    excess=(cd["zeb_norm"][-1]-cd["zeb_norm"][-42])-(cd["tsx_norm"][-1]-cd["tsx_norm"][-42])
    out={"provider":"Yahoo Finance / yfinance; auto_adjust=True","yfinance_version":yf.__version__,"pandas_version":pd.__version__,"retrieved_utc":datetime.now(timezone.utc).isoformat(),"asof_exclusive":ASOF,"prior_updated":PRIOR,"metrics":metrics,"validity":{"first":cd["dates"][-42],"last":cd["dates"][-1],"normalized_point_excess":excess},"since_prior_inclusive":[r for r in records if r["date"]>=PRIOR],"all_threshold_events":[r for r in records if r["absolute_trigger"] or r["divergence_trigger"]],"all_daily_checks":records,"months":months}
    dump("refresh_evidence.json",out)
    print(json.dumps({k:v for k,v in out.items() if k not in ["all_threshold_events","all_daily_checks"]},indent=2),flush=True)
except Exception as e:
    dump("failure.json",{"error":repr(e),"publication_preserved":True})
    raise
