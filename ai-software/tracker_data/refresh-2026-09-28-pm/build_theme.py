"""Rebuild AI Software candidate from observed, frozen 2026-09-28 market evidence.

Run only after refresh.py finishes. This edits AI Software files in the current
worktree; publication still requires independent review of the exact candidate.
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
THEME = ROOT / "ai-software"
DATA = THEME / "tracker_data"
OUT = Path(__file__).resolve().parent
assert ROOT.name == "thematic-tracker-automation" and THEME.name == "ai-software"
BASE_REV = "ed7562de0cb18f9b2f26def9c396ff7e85b0bf8a"  # pre-refresh published source
source = subprocess.run(["git", "show", f"{BASE_REV}:ai-software/theme.md"], cwd=ROOT,
                        check=True, capture_output=True, text=True, encoding="utf-8").stdout.replace("\r\n", "\n")
assert re.search(r"^updated: 2026-09-23$", source, re.M)
e = json.loads((OUT / "refresh_evidence.json").read_text(encoding="utf-8"))
c = json.loads((OUT / "chartdata.json").read_text(encoding="utf-8"))
assert c["dates"][-1] == "2026-09-28"
assert e["validity"]["first"] == c["dates"][-42]
assert len(e["since_prior_exclusive"]) == 3
m = e["metrics"]
percent = lambda value, digits=2: f"{value:+.{digits}f}%"
pp = lambda value: f"{value:+.2f}pp"
points = lambda value: f"{value:+.2f} normalized points"
main, bench = m["IGV"], m["QQQ"]
excess = main["window_return"] - bench["window_return"]
validity = e["validity"]["normalized_point_excess"]
assert validity > 1
start_price = main["latest_close"] / (1 + main["window_return"] / 100)
assert c["dates"][0] == "2025-09-29", c["dates"][0]
assert abs(float(c["zeb_norm"][-1]) - 100 * (1 + main["window_return"] / 100)) < .01

source = source.replace("updated: 2026-09-23", "updated: 2026-09-28", 1)
proxy_lines = [
    "| role | ticker | name | ret12m | note |",
    "|---|---|---|---|---|",
    f"| MAIN | IGV | iShares Expanded Tech-Software | {percent(main['window_return'])} | 美股软件板块 ETF |",
    f"| SUPPORT | CRM | Salesforce | {percent(m['CRM']['window_return'])} | 企业 SaaS 龙头 |",
    f"| SUPPORT | NOW | ServiceNow | {percent(m['NOW']['window_return'])} | 工作流自动化龙头 |",
    f"| SUPPORT | WDAY | Workday | {percent(m['WDAY']['window_return'])} | HR/财务 SaaS |",
    f"| BENCH | QQQ | Invesco QQQ Trust | {percent(bench['window_return'])} | 纳指100基准 |",
    f"| EXCESS | IGV - QQQ | — | {pp(excess)} | 主题 vs 大盘科技超额 |",
]
stats_lines = [
    "| metric | tone | value | sub |",
    "|---|---|---|---|",
    f"| WINDOW RETURN | {'up' if main['window_return'] >= 0 else 'dn'} | {percent(main['window_return'])} | {start_price:.2f} → {main['latest_close']:.2f} |",
    f"| LATEST CLOSE | {'up' if main['daily_return'] >= 0 else 'dn'} | ${main['latest_close']:.2f} | 2026-09-28; daily {percent(main['daily_return'])} |",
    f"| VS QQQ | {'up' if excess >= 0 else 'dn'} | {pp(excess)} | QQQ {percent(bench['window_return'])} |",
    f"| FROM TROUGH | up | {percent(main['from_trough'],1)} | {main['trough_date']} intraday low {main['trough']:.2f} |",
    f"| OFF HIGH | dn | {percent(main['distance_high'],1)} | adjusted 52wk high {main['high_52wk']:.2f} |",
    f"| YTD 2026 | {'up' if main['ytd'] >= 0 else 'dn'} | {percent(main['ytd'],1)} | vs Dec 31 2025 ({main['ytd_baseline']:.2f}) |",
    f"| LAGGARD WATCH | warn | ADBE {percent(m['ADBE']['distance_high'],0)} | INTU {percent(m['INTU']['distance_high'],0)} |",
]
summary = [
    "MARKET: 9月21日美债收益率回落，IGV +2.66%、QQQ +2.88%；大盘风险偏好回升，不是软件独有催化剂。",
    "THEME: 8月27日 Salesforce 披露 AI 产品 ARR，IGV +7.74%、QQQ +1.37%；软件板块走强，但不可外推所有公司。",
    f"WATCH: 9月25日软件逆市跌、28日大盘与软件同跌，催化剂未核实；近42交易日相对 QQQ {points(validity)}，继续盯 AI ARR/NRR。",
]
assert len(summary) == 3 and all(len(line) < 210 for line in summary)
source = re.sub(r"(?<=^## PROXIES\n)[\s\S]*?(?=^## STATS)", "\n".join(proxy_lines) + "\n\n", source, count=1, flags=re.M)
source = re.sub(r"(?<=^## STATS\n)[\s\S]*?(?=^## VERDICT)", "\n".join(stats_lines) + "\n\n", source, count=1, flags=re.M)
source = re.sub(r"(?<=^## VERDICT\n)[\s\S]*?(?=^## EVENTS)", "\n".join(summary) + "\n\n", source, count=1, flags=re.M)

section = re.search(r"(?<=^## EVENTS\n)[\s\S]*?(?=^## VALIDITY)", source, flags=re.M).group()
blocks = re.findall(r"^### #\d+\s*\|[^\n]*\n[\s\S]*?(?=^### #|\Z)", section.strip(), flags=re.M)
assert len(blocks) == 15, len(blocks)
classes = {
    "2025-11-28":"UNVERIFIED", "2026-01-30":"UNVERIFIED", "2026-02-27":"THEME",
    "2026-04-09":"UNVERIFIED", "2026-04-10":"UNVERIFIED",
    "2026-08-19":"UNVERIFIED", "2026-08-27":"THEME",
    "2026-09-03":"UNVERIFIED", "2026-09-08":"UNVERIFIED",
    "2026-09-14":"THEME", "2026-09-18":"MARKET",
    "2026-09-21":"MARKET", "2026-09-22":"UNVERIFIED", "2026-09-23":"UNVERIFIED",
    "2026-09-25":"UNVERIFIED",
}
blocks = [b for b in blocks if "2025-12-31" not in b]  # remove bland December to stay <=15
nov = next(i for i,b in enumerate(blocks) if "2025-11-28" in b.splitlines()[0])
blocks[nov] = (
    "### #01 | 2025-11-28 | IGV -9.89% | Earnings\n"
    "**November software weakness; Workday raised its FY26 subscription guide only modestly**\n"
    "Workday's Nov 25 FY26 Q3 release raised full-year subscription revenue guidance to $8.828B from the $8.815B given in August — not a cut. Its Q4 adjusted operating-margin floor was 28.5%; CNBC reported a 28.7% StreetAccount estimate. For the full month IGV -9.89% versus QQQ -1.56%; a company report and a software-relative drawdown coexist, but the monthly gap alone cannot establish that Workday or AI displacement caused it.\n"
    "MOVES: IGV=-9.89% | QQQ=-1.56%\n"
    "SRC: Workday Investor Relations, Aug 21 and Nov 25 2025, https://investor.workday.com/news-and-events/press-releases/news-details/2025/Workday-Announces-Fiscal-2026-Second-Quarter-Financial-Results-08-21-2025/default.aspx ; https://investor.workday.com/news-and-events/press-releases/news-details/2025/Workday-Announces-Fiscal-2026-Third-Quarter-Financial-Results-11-25-2025/default.aspx ; CNBC publisher report, Nov 25 2025, https://www.linkedin.com/posts/cnbc_workday-stock-slips-on-light-quarterly-margin-activity-7399211582867718144-Fa6-\n"
)
jan = next(i for i,b in enumerate(blocks) if "2026-01-30" in b.splitlines()[0])
blocks[jan] = (
    "### #02 | 2026-01-30 | IGV -14.55% | AI Disruption\n"
    "**January software drawdown coincides with renewed AI-disruption concern**\n"
    "Reuters reported a software selloff after SAP and ServiceNow results on Jan 29, including worries about AI competition. IGV ended January -14.55% while QQQ rose +1.23%. That relative gap shows software weakness; one dated story does not establish the cause of the whole month's decline or rule out other market influences.\n"
    "MOVES: IGV=-14.55% | QQQ=+1.23%\n"
    "SRC: Reuters, Jan 29 2026 (syndicated full wire), https://www.investing.com/news/stock-market-news/us-software-stocks-slide-after-sap-servicenow-results-fuel-ai-disruption-fears-4473752\n"
)
aug = next(i for i,b in enumerate(blocks) if "2026-08-27" in b.splitlines()[0])
blocks[aug] = re.sub(
    r"(?<=\n)FY27 Q2 \(reported Aug 26 AMC\):[^\n]*",
    "FY27 Q2 (reported Aug 26 AMC): cRPO grew 14% year-on-year in constant currency and full-year revenue guidance rose. Agentforce and Data 360 ARR reached nearly $3.9B, up over 210% year-on-year; Agentforce ARR exceeded $1.5B. Salesforce notes the Agentforce definition expanded in FY27 Q2. CRM +22.58%, IGV +7.74% versus QQQ +1.37%. These are disclosed product metrics, not proof that all software vendors reverse per-seat erosion.",
    blocks[aug], count=1,
)
assert "nearly $3.9B" in blocks[aug] and "$1.2B" not in blocks[aug]
blocks[aug] = re.sub(r"\*\*Salesforce proves AI monetization: CRM \+22\.58% in a day\*\*",
    "**Salesforce discloses AI ARR; CRM +22.58% in a day**", blocks[aug], count=1)
blocks[aug] = re.sub(r"^SRC:.*$",
    "SRC: Salesforce Investor Relations, Aug 26, 2026, https://investor.salesforce.com/news/news-details/2026/Salesforce-Delivers-Record-Second-Quarter-Fiscal-2027-Results/default.aspx ; Yahoo Finance adjusted daily history for Aug 27, https://finance.yahoo.com/quote/CRM/history/ ; https://finance.yahoo.com/quote/IGV/history/", blocks[aug], count=1, flags=re.M)
for i, block in enumerate(blocks):
    if "2026-04-09" in block.splitlines()[0]:
        blocks[i] = block.replace("**The cleanest proof this drawdown was about AI disruption, not macro.**",
            "The price divergence is consistent with software-specific pressure; no contemporaneous catalyst was verified, so an AI-agent explanation remains a hypothesis.")
    if "2026-04-10" in block.splitlines()[0]:
        blocks[i] = block.replace("**In hindsight, the entry for the current ~45% recovery leg** — nothing about fundamentals changed that week, only positioning and fear.",
            f"From that intraday low to the current close, IGV recovered {percent(main['from_trough'],1)}; this does not verify a same-day fundamental catalyst.")
        blocks[i] = blocks[i].replace("and the tracked recovery cohort ranged from roughly 39% to 61% below prior highs.",
            "while other tracked names also traded well below prior highs.")
    if "2026-02-27" in block.splitlines()[0]:
        blocks[i] = block.replace("(Forbes, Feb 6)", "(Forbes, Feb 4; updated Feb 5)")
        blocks[i] = blocks[i].replace("SRC: Reuters, Feb 5, 2026",
            "SRC: Reuters, Feb 5 2026; Forbes, Feb 4 (updated Feb 5), https://www.forbes.com/sites/donmuir/2026/02/04/300-billion-evaporated-the-saaspocalypse-has-begun/")
    if "2026-09-03" in block.splitlines()[0]:
        blocks[i] = block.replace("extending the template set by the names that have already reclaimed prior highs.",
            "a rebound in the tracked software cohort, not proof that multiple names have reclaimed prior highs.")
    if "2026-09-18" in block.splitlines()[0]:
        blocks[i] = blocks[i].replace("In the first full week after the Fed's hike,", "On the second trading day after the Fed's Sep 16 hike,")
        blocks[i] = blocks[i].replace("as the same morning's AIforce unveiling drew a guarded first read (UBS: usage potential but \"price point too high\")",
            "as UBS's Sep 18 assessment of Salesforce's Sep 15 AIforce unveiling noted usage potential but questioned the price point")
        blocks[i] = blocks[i].replace("SRC: MT Newswires (via Yahoo Finance), Sep 18, 2026,",
            "SRC: Salesforce, AIforce global unveiling Sep 15, 2026, https://www.salesforce.com/news/stories/aiforce-announcement/ ; MT Newswires (via Yahoo Finance), Sep 18, 2026,")
new = (
    "### #00 | 2026-09-25 | IGV -1.06% | Valuation & Sentiment\n"
    "**Software slips while QQQ rises; cause remains unverified**\n"
    "IGV -1.06% versus QQQ +0.46%, a 1.52pp opposite-direction gap on 0.77x IGV volume. CRM -1.76% and NOW -1.57% fell too; price establishes sector-relative weakness but no verified company release or macro catalyst establishes causality. Attribution is unexplained.\n"
    "MOVES: IGV=-1.06% | QQQ=+0.46% | VOL=0.77x\n"
    "SRC: Yahoo Finance adjusted daily history, Sep 25 close retrieved Sep 28 2026, https://finance.yahoo.com/quote/IGV/history/ ; https://finance.yahoo.com/quote/QQQ/history/ ; https://finance.yahoo.com/quote/CRM/history/ ; https://finance.yahoo.com/quote/NOW/history/\n"
)
blocks.append(new)
assert len(blocks) == 15
renumbered = []
for index, block in enumerate(blocks, 1):
    first, rest = block.split("\n", 1)
    date = re.search(r"\|\s*(\d{4}-\d{2}-\d{2})\s*\|", first).group(1)
    assert date in classes, date
    first = re.sub(r"^### #\d+", f"### #{index:02d}", first)
    title, body = rest.split("\n", 1)
    assert title.startswith("**")
    period = "PERIOD: MONTH\n" if date in {"2025-11-28", "2026-01-30", "2026-02-27"} else ""
    renumbered.append(f"{first}\n{title}\nDRIVER: {classes[date]}\n{period}{body.strip()}\n")
source = re.sub(r"(?<=^## EVENTS\n)[\s\S]*?(?=^## VALIDITY)", "\n" + "\n".join(renumbered) + "\n", source, count=1, flags=re.M)
first = e["validity"]["first"]
start_idx = c["dates"].index(first)
main_points = c["zeb_norm"][-1] - c["zeb_norm"][start_idx]
bench_points = c["tsx_norm"][-1] - c["tsx_norm"][start_idx]
validity_text = (
    f"CALL: green | 42-session normalized-point spread {points(validity)} vs QQQ — relative price signal only; no newly verified AI ARR or NRR catalyst\n\n"
    "- window: 42 trading sessions; subtract changes in IGV and QQQ series each anchored at 100 on 2025-09-29 (normalized points, not trailing-period percentage returns)\n"
    "- green: normalized-point spread > +1; red: < -1 or documented thesis break\n"
    f"- current: {first} → 2026-09-28, IGV {main_points:+.2f} normalized points vs QQQ {bench_points:+.2f} normalized points\n\n"
)
source = re.sub(r"(?<=^## VALIDITY\n)[\s\S]*?(?=^## CATALYSTS)", "\n" + validity_text, source, count=1, flags=re.M)
source = re.sub(r"^### Nov–Dec 2026 \(est\.\) \| hot \| Q3 earnings: CRM / NOW / WDAY must repeat the trick\n[^\n]*\n",
    "### Late Oct 2026 (est.; confirm with IR) | hot | ServiceNow calendar Q3: cRPO / AI workflow\n"
    "NOW reported calendar Q3 2025 on Oct 29 and Q2 2026 on Jul 22; its Q3 2026 announcement date is NOT confirmed here. This earlier checkpoint tests cRPO and subscription guidance against the raised bar. Official prior releases: https://investor.servicenow.com/news/news-details/2025/ServiceNow-Reports-Third-Quarter-2025-Financial-Results-Board-of-Directors-Authorizes-Five-for-One-Stock-Split/default.aspx ; https://investor.servicenow.com/news/news-details/2026/ServiceNow-Reports-Second-Quarter-2026-Financial-Results/default.aspx\n\n"
    "### Late Nov–early Dec 2026 (est.; confirm with IR) | Earnings | CRM / WDAY fiscal Q3 results\n"
    "Salesforce and Workday follow on their fiscal Q3 calendars; dates are estimates pending issuer announcements. After Salesforce's August AI ARR disclosure, watch CRM cRPO and paid AI adoption, plus WDAY's margin and seat-pricing guidance. A guide-cut could reopen the per-seat erosion thesis.\n",
    source, count=1, flags=re.M)
assert "ServiceNow calendar Q3" in source and "Q3 earnings: CRM / NOW / WDAY" not in source
source = source.replace("### Resolved 2026-09-16 | Macro Risk | Fed hiked 25bp, signals one more in 2026",
    "### Resolved 2026-09-16 | Macro Risk | Fed +25bp; participant projections imply another 2026 hike")
source = source.replace("with selling concentrated in speculative small caps rather than the enterprise cohort.",
    "while all five tracked enterprise names also fell (CRM -2.00%, NOW -1.47%, WDAY -1.53%, ADBE -2.82%, INTU -3.38%); weakness was not confined to speculative small caps.")
source = source.replace("### Late Oct 2026 | AI Capex | Hyperscaler earnings + MSFT Copilot commentary",
    "### Late Oct 2026 (est.; confirm with IR) | AI Capex | Hyperscaler earnings + MSFT Copilot commentary")
source = source.replace("MSFT/GOOGL/AMZN/META report late October. Copilot seat/ARPU disclosures are the key datapoint for per-seat pricing power; a second consecutive capex raise extends the infrastructure-over-application regime.",
    "MSFT/GOOGL/AMZN/META are expected around late October, but dates are estimates pending each issuer's announcement. If disclosed, Copilot seat/ARPU figures can test per-seat pricing; another capex raise would support infrastructure demand, not prove software monetization.")
assert "selling concentrated in speculative small caps" not in source and "MSFT/GOOGL/AMZN/META report late October" not in source
source = source.replace("this week's Dreamforce/investor-day reception", "September's Dreamforce/investor-day reception")
risk = (
    "If AI lowers enterprise seat counts without offsetting usage or new paid AI products, per-seat pricing and renewal metrics could weaken; this remains a thesis risk, not an observed NRR break in the tracked cohort. "
    "Salesforce's Agentforce product disclosures are one possible offset, but future CRM/NOW/WDAY earnings and seat/NRR guidance must test it. "
    "Salesforce unveiled AIforce on Sep 15 (https://www.salesforce.com/news/stories/aiforce-announcement/); UBS's Sep 18 assessment questioned its price point (MT Newswires, 2026-09-18). "
    "IBM's separate Jul 14 letter described a shift toward servers, storage and memory, not measured SaaS seat erosion (https://newsroom.ibm.com/2026-07-14-Arvind-Krishnas-Letter-to-IBM-Investors)."
)
source, risk_count = re.subn(r"(?<=^### Standing Risk \| Repricing \| Per-seat erosion without user expansion\n)[^\n]*", risk, source, flags=re.M)
assert risk_count == 1 and "IBM's Sep 15" not in source and "Friday's AIforce unveiling" not in source
source = re.sub(r"(?<=^## CHARTDATA\n)[\s\S]*\Z", "\n```json\n" + json.dumps(c, separators=(",", ":")) + "\n```\n", source, count=1, flags=re.M)
assert source.count("DRIVER: ") == 15
assert source.count("## VERDICT") == 1 and source.count("## CHARTDATA") == 1
assert "updated: 2026-09-28" in source
(THEME / "theme.md").write_bytes(source.encode("utf-8"))
(THEME / "theme.txt").write_bytes(source.encode("utf-8"))
for ticker in ["IGV", "QQQ", "CRM", "NOW", "WDAY", "ADBE", "INTU"]:
    for extension in ("csv", "derived.csv"):
        shutil.copy2(OUT / f"{ticker}.{extension}", DATA / f"{ticker}.{extension}")
for name in ("chartdata.json", "refresh_evidence.json"):
    shutil.copy2(OUT / name, DATA / name)
print("candidate 2026-09-28",len(blocks),"events",points(validity),"42-session normalized spread")
