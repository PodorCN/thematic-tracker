"""Verify the 2026-09-21 AI Software publication against frozen Yahoo data."""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pandas as pd

OUT = Path(__file__).resolve().parent
DATA = OUT.parent
THEME = DATA.parent
ROOT = THEME.parent
TEXT = (THEME / "theme.md").read_text(encoding="utf-8")
EVIDENCE = json.loads((OUT / "refresh_evidence.json").read_text(encoding="utf-8"))

failures: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    print(("PASS " if condition else "FAIL ") + name + (f" | {detail}" if detail else ""))
    if not condition:
        failures.append(name)


def frame(name: str) -> pd.DataFrame:
    result = pd.read_csv(DATA / name, parse_dates=["Date"]).set_index("Date")
    result.index = pd.to_datetime(result.index)
    return result


def daily_return(data: pd.DataFrame, market_date: str) -> float:
    position = data.index.get_loc(pd.Timestamp(market_date))
    return float((data["Close"].iloc[position] / data["Close"].iloc[position - 1] - 1) * 100)


def monthly_return(data: pd.DataFrame, market_date: str) -> float:
    endpoint = pd.Timestamp(market_date)
    month_rows = data.loc[endpoint.strftime("%Y-%m")]
    assert month_rows.index[-1] == endpoint
    before = data.loc[data.index < month_rows.index[0], "Close"].iloc[-1]
    return float((month_rows["Close"].iloc[-1] / before - 1) * 100)


files = ["IGV.csv", "QQQ.csv", "CRM.csv", "NOW.csv", "WDAY.csv", "ADBE.csv", "INTU.csv", "chartdata.json", "refresh_evidence.json"]
for name in files:
    check(
        f"canonical {name} equals frozen refresh",
        (DATA / name).read_bytes() == (OUT / name).read_bytes(),
    )

check("theme.md mirrors theme.txt", (THEME / "theme.md").read_bytes() == (THEME / "theme.txt").read_bytes())
check("frontmatter updated", "updated: 2026-09-21" in TEXT)

chart_match = re.search(r"## CHARTDATA\s*```json\s*(\{.*?\})\s*```", TEXT, re.DOTALL)
check("embedded CHARTDATA exists", chart_match is not None)
embedded = json.loads(chart_match.group(1)) if chart_match else {}
frozen_chart = json.loads((OUT / "chartdata.json").read_text(encoding="utf-8"))
check("embedded CHARTDATA equals frozen chart", embedded == frozen_chart)

data = {ticker: frame(f"{ticker}.csv") for ticker in ["IGV", "QQQ", "CRM", "NOW", "WDAY", "ADBE", "INTU"]}
check("all tracked series settle on 2026-09-21", all(value.index[-1] == pd.Timestamp("2026-09-21") for value in data.values()))
check("only one session since prior update", [row["date"] for row in EVIDENCE["since_prior_exclusive"]] == ["2026-09-21"])

window_returns = {
    ticker: float((value.loc["2026-09-21", "Close"] / value.loc["2025-09-02", "Close"] - 1) * 100)
    for ticker, value in data.items()
}
expected = {"IGV": -0.1118, "QQQ": 31.7211, "CRM": -5.5444, "NOW": -24.4695, "WDAY": -16.1519}
tokens = {"IGV": "-0.11%", "QQQ": "+31.72%", "CRM": "-5.54%", "NOW": "-24.47%", "WDAY": "-16.15%"}
for ticker in expected:
    check(f"{ticker} fixed-window return", abs(window_returns[ticker] - expected[ticker]) < 0.01 and tokens[ticker] in TEXT, f"{window_returns[ticker]:.4f}%")
window_excess = window_returns["IGV"] - window_returns["QQQ"]
check("fixed-window excess -31.83pp", abs(window_excess + 31.8329) < 0.01 and "-31.83pp" in TEXT, f"{window_excess:.4f}pp")

metrics = EVIDENCE["metrics"]
key_checks = [
    ("latest close $107.13", abs(metrics["IGV"]["latest_close"] - 107.13) < 0.005 and "$107.13" in TEXT),
    ("daily IGV +2.66%", abs(metrics["IGV"]["daily_return"] - 2.6641) < 0.01 and "+2.66%" in TEXT),
    ("IGV volume 0.84x", abs(metrics["IGV"]["volume_ratio"] - 0.83943) < 0.001 and "0.84x" in TEXT),
    ("IGV from trough +44.9%", abs(metrics["IGV"]["from_trough"] - 44.9345) < 0.01 and "+44.9%" in TEXT),
    ("IGV high distance -9.2%", abs(metrics["IGV"]["distance_high"] + 9.1871) < 0.01 and "-9.2%" in TEXT),
    ("IGV YTD +1.4%", abs(metrics["IGV"]["ytd"] - 1.3815) < 0.01 and "+1.4%" in TEXT),
    ("ADBE high distance -32%", abs(metrics["ADBE"]["distance_high"] + 32.3299) < 0.01 and "ADBE -32%" in TEXT),
    ("INTU high distance -56%", abs(metrics["INTU"]["distance_high"] + 56.3134) < 0.01 and "INTU -56%" in TEXT),
]
for name, condition in key_checks:
    check(name, condition)

for ticker, expected_move, token in [
    ("QQQ", 2.7750, "QQQ +2.77%"),
    ("CRM", -0.6305, "CRM -0.63%"),
    ("NOW", 1.6314, "NOW +1.63%"),
    ("WDAY", -1.0058, "WDAY -1.01%"),
    ("ADBE", 0.2410, "ADBE +0.24%"),
    ("INTU", 0.3067, "INTU +0.31%"),
]:
    value = daily_return(data[ticker], "2026-09-21")
    check(f"2026-09-21 {ticker} move", abs(value - expected_move) < 0.01 and token in TEXT, f"{value:.4f}%")

for ticker, rounded in [("CRM", 12), ("NOW", 29), ("WDAY", 23)]:
    distance = abs(metrics[ticker]["distance_high"])
    check(f"{ticker} rounded distance from high", round(distance) == rounded and f"{rounded}%" in TEXT, f"{distance:.4f}%")

igv_leg = embedded["zeb_norm"][-1] - embedded["zeb_norm"][-42]
qqq_leg = embedded["tsx_norm"][-1] - embedded["tsx_norm"][-42]
validity = igv_leg - qqq_leg
check("42-session dates", embedded["dates"][-42] == "2026-07-23" and embedded["dates"][-1] == "2026-09-21")
check("42-session IGV leg +18.68", abs(igv_leg - 18.6760) < 0.01 and "IGV +18.68 vs QQQ +8.80" in TEXT, f"{igv_leg:.4f}")
check("42-session QQQ leg +8.80", abs(qqq_leg - 8.7954) < 0.01, f"{qqq_leg:.4f}")
check("VALIDITY green +9.88pp", abs(validity - 9.8806) < 0.01 and "CALL: green | 2M excess +9.88pp" in TEXT, f"{validity:.4f}pp")

# Check all event heading moves: monthly returns for Sep 2025-Feb 2026, daily thereafter.
blocks = re.findall(r"^### #(\d+) \| (\d{4}-\d{2}-\d{2}) \| IGV ([+-]\d+\.\d+)% \|", TEXT, re.MULTILINE)
check("15 numbered events", len(blocks) == 15 and [int(row[0]) for row in blocks] == list(range(1, 16)))
for number, market_date, claimed_text in blocks:
    claimed = float(claimed_text)
    actual = monthly_return(data["IGV"], market_date) if market_date <= "2026-02-27" else daily_return(data["IGV"], market_date)
    check(f"event #{number} IGV move", abs(actual - claimed) <= 0.055, f"claimed={claimed:.2f}% actual={actual:.4f}%")

event_bodies = re.findall(r"(^### #\d+ \|.*?)(?=^### #|^## VALIDITY)", TEXT, re.MULTILINE | re.DOTALL)
igv_volume_ratio = data["IGV"]["Volume"] / data["IGV"]["Volume"].rolling(20).mean()
for body in event_bodies:
    header = re.search(r"^### #(\d+) \| (\d{4}-\d{2}-\d{2})", body)
    moves = re.search(r"MOVES: IGV=([+-]\d+\.\d+)% \| QQQ=([+-]\d+\.\d+)%", body)
    assert header and moves
    number, market_date = header.groups()
    qqq_actual = monthly_return(data["QQQ"], market_date) if market_date <= "2026-02-27" else daily_return(data["QQQ"], market_date)
    check(
        f"event #{number} QQQ move",
        abs(qqq_actual - float(moves.group(2))) <= 0.055,
        f"claimed={moves.group(2)}% actual={qqq_actual:.4f}%",
    )
    volume = re.search(r"VOL=(\d+(?:\.\d+)?)x(?! peak)", body)
    if volume:
        actual_volume = float(igv_volume_ratio.loc[pd.Timestamp(market_date)])
        check(
            f"event #{number} volume ratio",
            abs(actual_volume - float(volume.group(1))) <= 0.06,
            f"claimed={volume.group(1)}x actual={actual_volume:.4f}x",
        )

# Explicit checks for daily extremes and cohort observations embedded in narratives.
check("Feb 5 IGV -4.97%", abs(daily_return(data["IGV"], "2026-02-05") + 4.9738) < 0.01)
check("Feb 5 IGV volume 3.3x", abs(float(igv_volume_ratio.loc[pd.Timestamp("2026-02-05")]) - 3.3218) < 0.01)
check("Feb 5 NOW -7.60%", abs(daily_return(data["NOW"], "2026-02-05") + 7.5988) < 0.01)
check("Feb 5 WDAY -6.69%", abs(daily_return(data["WDAY"], "2026-02-05") + 6.6941) < 0.01)
check("Feb 23 IGV -4.75%", abs(daily_return(data["IGV"], "2026-02-23") + 4.7536) < 0.01)
check("Apr 10 IGV low 73.92", abs(float(data["IGV"].loc["2026-04-10", "Low"]) - 73.9161) < 0.01 and "73.92" in TEXT)
check("Apr 10 IGV close 36.7% below Sep high", abs((data["IGV"].loc["2026-04-10", "Close"] / data["IGV"].loc["2025-09-23", "High"] - 1) * 100 + 36.7150) < 0.01 and "36.7%" in TEXT)
for ticker, market_date, expected_move in [
    ("NOW", "2026-04-09", -7.8588), ("WDAY", "2026-04-09", -5.1271),
    ("ADBE", "2026-04-09", -3.9154), ("CRM", "2026-04-09", -2.8875),
    ("NOW", "2026-04-10", -7.5827), ("CRM", "2026-08-19", 5.0729),
    ("NOW", "2026-08-19", 6.4524), ("WDAY", "2026-08-19", 4.0810),
    ("ADBE", "2026-08-19", 3.5456), ("CRM", "2026-08-27", 22.5805),
    ("NOW", "2026-08-27", 10.0397), ("NOW", "2026-09-03", 6.4877),
    ("CRM", "2026-09-03", 2.9191), ("WDAY", "2026-09-03", 3.0119),
    ("NOW", "2026-09-08", -4.9908), ("WDAY", "2026-09-08", -4.8572),
    ("CRM", "2026-09-08", -3.9000), ("NOW", "2026-09-14", 7.4096),
    ("INTU", "2026-09-14", 5.4669), ("ADBE", "2026-09-14", 5.3007),
    ("CRM", "2026-09-14", 4.7271), ("WDAY", "2026-09-14", 4.5827),
    ("WDAY", "2026-09-18", -2.7148), ("INTU", "2026-09-18", -3.1744),
    ("NOW", "2026-09-18", -2.1665), ("CRM", "2026-09-18", -2.0301),
    ("ADBE", "2026-09-18", -1.4841),
]:
    check(f"narrative {ticker} {market_date}", abs(daily_return(data[ticker], market_date) - expected_move) < 0.01)

week_igv = float((data["IGV"].loc["2026-09-18", "Close"] / data["IGV"].loc["2026-09-11", "Close"] - 1) * 100)
week_qqq = float((data["QQQ"].loc["2026-09-18", "Close"] / data["QQQ"].loc["2026-09-11", "Close"] - 1) * 100)
check("Sep 18 weekly IGV +2.79%", abs(week_igv - 2.7876) < 0.01 and "IGV +2.79% versus QQQ +0.92%" in TEXT)
check("Sep 18 weekly QQQ +0.92%", abs(week_qqq - 0.9190) < 0.01)

check("new event absolute trigger", EVIDENCE["since_prior_exclusive"][0]["absolute_trigger"] is True)
check("new event divergence flag false", EVIDENCE["since_prior_exclusive"][0]["divergence_trigger"] is False)
check("Reuters current source URL", "wall-st-futures-rise-ai-115836672.html" in TEXT)
check("Yahoo current source URL", "stock-market-today-monday-september-21" in TEXT)

validator = subprocess.run(
    ["node", "scripts/validate-theme.mjs", "ai-software/theme.md"],
    cwd=ROOT,
    text=True,
    capture_output=True,
)
print(validator.stdout, end="")
print(validator.stderr, end="")
check("node validator", validator.returncode == 0)

if failures:
    print(f"VERIFY FAIL: {len(failures)} failure(s): {failures}")
    sys.exit(1)
print("VERIFY PASS ai-software 2026-09-21")
