"""Verify the 2026-09-21 Canadian Banks publication against frozen Yahoo data."""
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


files = ["ZEB.TO.csv", "BANK.TO.csv", "HFIN.TO.csv", "GSPTSE.csv", "GSPC.csv", "chartdata.json", "refresh_evidence.json"]
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

zeb = frame("ZEB.TO.csv")
bank = frame("BANK.TO.csv")
hfin = frame("HFIN.TO.csv")
tsx = frame("GSPTSE.csv")
spx = frame("GSPC.csv")
check("all tracked series settle on 2026-09-21", all(data.index[-1] == pd.Timestamp("2026-09-21") for data in [zeb, bank, hfin, tsx, spx]))
check("only one session since prior update", [row["date"] for row in EVIDENCE["since_prior_exclusive"]] == ["2026-09-21"])

returns = {
    "ZEB": (zeb["Close"].iloc[-1] / zeb["Close"].iloc[0] - 1) * 100,
    "BANK": (bank["Close"].iloc[-1] / bank["Close"].iloc[0] - 1) * 100,
    "HFIN": (hfin["Close"].iloc[-1] / hfin["Close"].iloc[0] - 1) * 100,
    "TSX": (tsx["Close"].iloc[-1] / tsx["Close"].iloc[0] - 1) * 100,
    "SPX": (spx["Close"].iloc[-1] / spx["Close"].iloc[0] - 1) * 100,
}
expected_tokens = {
    "ZEB": "+2.54%",
    "BANK": "+4.72%",
    "HFIN": "+1.47%",
    "TSX": "+2.88%",
    "SPX": "+3.91%",
}
expected_values = {"ZEB": 2.5404, "BANK": 4.7234, "HFIN": 1.4702, "TSX": 2.8775, "SPX": 3.9063}
for name, value in returns.items():
    check(f"{name} window return", abs(value - expected_values[name]) < 0.01 and expected_tokens[name] in TEXT, f"{value:.4f}%")
excess = returns["ZEB"] - returns["TSX"]
check("3M excess -0.34pp", abs(excess + 0.3371) < 0.01 and "-0.34pp" in TEXT, f"{excess:.4f}pp")

latest = EVIDENCE["metrics"]["ZEB.TO"]
checks = [
    ("latest close C$76.46", abs(latest["latest_close"] - 76.46) < 0.005 and "C$76.46" in TEXT),
    ("daily return +1.57%", abs(latest["daily_return"] - 1.5675) < 0.01 and "+1.57%" in TEXT),
    ("YTD +33.48%", abs(latest["ytd"] - 33.4798) < 0.01 and "+33.48%" in TEXT),
    ("52-week high distance -2.73%", abs(latest["distance_high"] + 2.7268) < 0.01 and "-2.73%" in TEXT),
    ("volume 656,813", latest["volume"] == 656813 and "656,813" in TEXT),
    ("volume ratio 0.52x", abs(latest["volume_ratio"] - 0.51645) < 0.001 and "0.52x" in TEXT),
]
for name, condition in checks:
    check(name, condition)

for symbol, data, expected, token in [
    ("BANK.TO", bank, 1.3841, "BANK.TO +1.38%"),
    ("HFIN.TO", hfin, 1.2280, "HFIN.TO +1.23%"),
    ("TSX", tsx, 0.5661, "TSX's +0.57%"),
]:
    value = daily_return(data, "2026-09-21")
    check(f"2026-09-21 {symbol} move", abs(value - expected) < 0.01 and token in TEXT, f"{value:.4f}%")

zeb_leg = embedded["zeb_norm"][-1] - embedded["zeb_norm"][-42]
tsx_leg = embedded["tsx_norm"][-1] - embedded["tsx_norm"][-42]
validity = zeb_leg - tsx_leg
check("42-session dates", embedded["dates"][-42] == "2026-07-22" and embedded["dates"][-1] == "2026-09-21")
check("42-session ZEB leg +0.07", abs(zeb_leg - 0.0719) < 0.01 and "ZEB +0.07 vs TSX +1.50" in TEXT, f"{zeb_leg:.4f}")
check("42-session TSX leg +1.50", abs(tsx_leg - 1.4979) < 0.01, f"{tsx_leg:.4f}")
check("VALIDITY red -1.43pp", abs(validity + 1.4260) < 0.01 and "CALL: red | 2M excess -1.43pp" in TEXT, f"{validity:.4f}pp")

# Every event heading and MOVES pair is checked against the canonical daily bars.
blocks = re.findall(r"^### #(\d+) \| (\d{4}-\d{2}-\d{2}) \| ZEB ([+-]\d+\.\d+)% \|.*?(?=^### #|^## VALIDITY)", TEXT, re.MULTILINE | re.DOTALL)
check("15 numbered events", len(blocks) == 15 and [int(row[0]) for row in blocks] == list(range(1, 16)))
for number, market_date, claimed_text in blocks:
    actual = daily_return(zeb, market_date)
    check(f"event #{number} ZEB move", abs(actual - float(claimed_text)) <= 0.055, f"claimed={claimed_text}% actual={actual:.4f}%")

event_bodies = re.findall(r"(^### #\d+ \|.*?)(?=^### #|^## VALIDITY)", TEXT, re.MULTILINE | re.DOTALL)
reference = pd.read_csv(OUT / "ZEB.TO.reference.csv", parse_dates=["Date"]).set_index("Date")
reference.index = pd.to_datetime(reference.index)
reference_volume_ratio = reference["Volume"] / reference["Volume"].rolling(20).mean()
for body in event_bodies:
    header = re.search(r"^### #(\d+) \| (\d{4}-\d{2}-\d{2})", body)
    moves = re.search(r"MOVES: ZEB=([+-]\d+\.\d+)% \| TSX=([+-]\d+\.\d+)%", body)
    assert header and moves
    number, market_date = header.groups()
    benchmark_actual = daily_return(tsx, market_date)
    check(
        f"event #{number} TSX move",
        abs(benchmark_actual - float(moves.group(2))) <= 0.055,
        f"claimed={moves.group(2)}% actual={benchmark_actual:.4f}%",
    )
    volume = re.search(r"VOL=(\d+(?:\.\d+)?)x", body)
    if volume:
        actual_volume = float(reference_volume_ratio.loc[pd.Timestamp(market_date)])
        check(
            f"event #{number} volume ratio",
            abs(actual_volume - float(volume.group(1))) <= 0.06,
            f"claimed={volume.group(1)}x actual={actual_volume:.4f}x",
        )

for market_date, expected in [("2026-07-06", 1.2223), ("2026-07-08", -2.1013), ("2026-07-10", 1.5277)]:
    check(f"consolidated July claim {market_date}", abs(daily_return(zeb, market_date) - expected) < 0.01)

check("new event source URL", "tsx-closer-index-closes-higher-202426685.html" in TEXT)
check("event threshold is absolute", EVIDENCE["since_prior_exclusive"][0]["absolute_trigger"] is True)
check("same-direction divergence flag is false", EVIDENCE["since_prior_exclusive"][0]["divergence_trigger"] is False)

validator = subprocess.run(
    ["node", "scripts/validate-theme.mjs", "canadian-banks/theme.md"],
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
print("VERIFY PASS canadian-banks 2026-09-21")
