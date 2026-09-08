# agent.md — Thematic Tracker 每日更新协议（给 LLM 的操作手册）

> **你是谁**：一个负责维护 thematic tracker 的 agent。
> **你的任务**：每个交易日盘后，收集行情与新闻，**重写 `theme.md`**，然后保存网站新版本。
> **核心原则**：`theme.md` 是网页的唯一内容源。网页（index.html）是纯渲染器——**永远不要为了改内容去动 index.html**，所有更新都通过重写 theme.md 完成。

---

## 0. 架构（先理解，再动手）

```
agent.md        ← 本文件，你的操作协议
theme.md        ← 唯一内容源：meta / proxies / stats / verdict / events / catalysts / chartdata
index.html      ← 渲染器：加载时 fetch("theme.md")，解析后渲染 Plotly 图 + 时间线 + 卡片
tracker_data/   ← 原始行情 CSV 缓存（ZEB.TO.csv / BANK.TO.csv / HFIN.TO.csv / GSPTSE.csv / GSPC.csv）
```

theme.md 与 index.html 必须放在同一目录（`/mnt/agents/output/app/`），fetch 才能生效。

---

## 1. 每日 SOP（盘后执行，全程约 10–15 分钟）

### Step 1 — 拉行情（yahoo_finance plugin）

对以下 5 个 ticker 全部重新拉取（不要增量追加，整窗重拉保证幂等）：

```
API: get_historical_stock_prices
params: period=3mo, interval=1d, file_path=/mnt/agents/output/tracker_data/<name>.csv
tickers: ZEB.TO → ZEB.TO.csv | BANK.TO → BANK.TO.csv | HFIN.TO → HFIN.TO.csv
         ^GSPTSE → GSPTSE.csv | ^GSPC → GSPC.csv
```

计算（pandas）：
- 各 ticker 窗口期收益率（首末收盘价）→ 更新 PROXIES 表
- 归一化序列 base=100（首日=100），日期对齐用 inner join；S&P 500 交易日与加股不同，**单独保留 spx_dates / spx_norm**
- ZEB 日收益序列 `zeb_ret`、成交量 `volume`、20 日均量倍数
- 最新收盘、距 52 周高点、YTD → 更新 STATS 表

### Step 2 — 异动筛查

对最近一个交易日（及上次更新以来漏掉的每个交易日）：
- `|ZEB 日收益| < 1.5%` → 不需要新事件，仅更新价格与统计
- `|ZEB 日收益| ≥ 1.5%` 或 `|ZEB − TSX| ≥ 1pp 且方向背离` → **必须新增/更新事件**，进入 Step 3
- 同时检查催化剂日历是否命中当天（BoC 决议日、财报日、CPI 日，见 §4）

### Step 3 — 新闻归因（web search）

按优先级搜索并归因：
1. `Canadian bank stocks today` / 当日大盘复盘（BNN Bloomberg、Financial Post、Yahoo Finance Canada）
2. 财报季（约 2月底/5月底/8月底/12月初）：逐行搜索六大行（RY TD BNS BMO CM NA）财报关键词：EPS、PCL、NIM、CET1、股息、回购
3. 央行：`Bank of Canada rate decision`、FOMC 利率决议/纪要（美债收益率传导至加银行）
4. 宏观：加拿大 CPI、就业、GDP；关税/贸易战：`Canada US tariff banks`
5. 监管/个股：OSFI 资本规则、并购、罚金、评级调整

**归因四要素**（全部写进事件块）：
- 标题：一句话说清发生了什么
- 正文：传导链条（为什么影响银行股，2–4 句）
- MOVES：ZEB 当日 %、TSX 当日 %、放量倍数（>1.5× 才写）
- SRC：来源名 + 日期（禁止编造）

**分化解读规则：**
- ZEB 跌而 TSX 平/涨 → 银行特有事件（财报、估值、监管）
- ZEB 与 TSX 同向大跌 → 宏观/地缘事件
- BANK.TO（1.25x 杠杆）涨跌幅 ≈1.2–1.4× ZEB → 趋势健康；杠杆失效 → 警惕反转
- HFIN.TO（泛金融）与 ZEB 背离 → 判别"银行特有"还是"金融系统性"

### Step 4 — 重写 theme.md

按 §2 的 schema **整个重写** theme.md（不要局部 patch，保证幂等）：
1. meta：`updated` 改为最新交易日
2. PROXIES / STATS：填入 Step 1 的新数字
3. VERDICT：如有新证据，更新结论段（thesis 被强化还是削弱）
4. EVENTS：新事件插入正确日期位置（**按日期升序**），编号重排（#01…#NN）；超过 ~15 个事件时，把最老且不重要的事件合并成一句过渡叙述，保持时间线可读
5. CATALYSTS：已过期的删除，新出现的按重要性排序；最大转折点标 `hot`
6. CHARTDATA：用 Step 1 的结果整体替换 JSON

### Step 5 — 校验 + 发布

先跑自动校验（一条命令覆盖下面大部分清单）：
```
node scripts/validate-theme.mjs app/theme.md
```
必须 PASS（warning 可以留，error 必须清零），再人工过一遍清单：
- [ ] JSON 代码块可被解析（校验器已查）
- [ ] 每个事件都有 MOVES 行和 SRC 行（校验器已查）
- [ ] 事件日期必须是 ZEB 交易日（在 chartdata.dates 里存在），否则图上挂不上标记（校验器已查）
- [ ] 事件编号连续（#01…#NN），ret 带正负号与 %（编号校验器已查，正负号人工看一眼）
- [ ] PROXIES 表的 ret3m 与 chartdata 末端值一致（允许 ±0.06pp 取整误差，校验器已查）

发布（git + GitHub Pages）：
1. `git add app/theme.md tracker_data/` 后提交，一天一个 commit：`git commit -m "data: update theme.md <updated>"`（提交粒度细，坏了用 `git revert` 一条命令回滚）
2. 推到 dev/功能分支 → GitHub Action 自动跑校验 → 绿了再合 main（合 main 即自动上线，约 1 分钟）
3. 上线后打开 https://podor.org/thematic-tracker/ 确认数字与事件已更新
4. 紧急回滚：`git revert <出问题的commit>`，重新走第 2 步

不需要改 index.html。

### Step 6 — 每周五盘后加做

- 复核 VERDICT 与 CATALYSTS 排序
- 检查 supportive proxy 是否连续 3 日以上背离 main proxy（写进 VERDICT）
- 在 VERDICT 末尾追加一行本周一句话总结（可选）

---

## 2. theme.md Schema（严格遵守，渲染器靠这些格式解析）

### meta（文件开头，frontmatter）
```
---
theme_cn: Canadian Banks
theme_en: BIG-SIX BANKS · CA
updated: YYYY-MM-DD
window: 3M
currency: CAD
---
```

All content in theme.md must be written in **English**. Do not add a `subtitle` field — the hero renders the title only.

### ## PROXIES / ## STATS — Markdown 表格
```
| role | ticker | name | ret3m | extra |
| MAIN PROXY | ZEB.TO | ... | +7.84% | 3M RETURN |

| label | value | sub | tone |        ← tone ∈ up / dn / warn / flat
```

### ## VERDICT — 一个段落
支持 `**加粗**`。

### ## EVENTS — event blocks (ascending by date in the file; the page renders newest-first automatically)
```
### #NN | YYYY-MM-DD | ZEB +x.xx% | Tag
**One-line title**
Body paragraph (transmission logic, **bold** supported)
MOVES: ZEB=+x.xx% | TSX=+x.xx% | VOL=1.8x
SRC: Source name, date
```
- Tag ∈ Earnings / Monetary Policy / Geopolitics / Macro Data / Valuation & Sentiment (drives color)
- Sign of the daily move drives the node color (negative = red, positive = green)

### ## CATALYSTS — 催化剂块
```
### 日期或时间窗 | hot 或普通标签 | 标题
段落
```

### ## CHARTDATA — 图表数据
````
```json
{"dates":[...],"zeb_norm":[...],"tsx_norm":[...],"bank_norm":[...],"hfin_norm":[...],
 "spx_dates":[...],"spx_norm":[...],"volume":[...],"zeb_ret":[null,...]}
```
````
所有 norm 序列 base=100（各自窗口首日），zeb_ret 首元素为 null。

---

## 3. Proxy 体系（事实表，勿改）

| 角色 | Ticker | 说明 |
|---|---|---|
| Main proxy | ZEB.TO | BMO 六大行等权 ETF，所有归因基准 |
| Supportive | BANK.TO | 1.25x 杠杆放大器（Evolve） |
| Supportive | HFIN.TO | 泛金融结构判别器（Hamilton） |
| Benchmark | ^GSPTSE / ^GSPC | S&P/TSX、S&P 500 |

## 4. 催化剂日历（随时间滚动维护）

| 日期 | 事件 |
|---|---|
| 2026-10-28 / 12-09 | BoC 利率决议 |
| 2026-12-02 ~ 12-04（预估） | 六大行 Q4/FY2026 财报（首个含 50% 关税影响的季度，盯 PCL） |
| 每月中旬 | 加拿大 CPI / 就业 |
| 2026 年底 / 2027 Q1 | NA 收购 Laurentian 组合交割；RBC/BMO 出售 Moneris 交割 |
| 持续 | 美加关税、CUSMA 审查 |

## 5. 红线

- **禁止编造**：价格必须来自行情接口，事件必须带来源。搜不到原因就在正文里写 `归因不明（unexplained）`。
- **接口失败**：当日跳过并记录，下一交易日重拉（period=3mo 幂等覆盖）。
- **非交易日**：只维护 CATALYSTS，不改价格。
- **不要改 index.html**：内容问题一律在 theme.md 里解决；只有用户明确要求改版式时才动渲染器。
