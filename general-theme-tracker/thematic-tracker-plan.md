# Thematic Tracker: 产品 Plan + 可直接执行的 Prompt

> 角色：Senior PM + Portfolio Manager 双视角，为你写的 Build Plan。

## 1. 产品一句话

一个给 PM 看的 **Theme 第一视角站**：现在市场最重要的 Theme 是什么？表现如何？用什么 track？为什么形成？依赖什么 catalyst？昨天 vs 今天有何变化？是 Theme 还是 Noise？

5分钟内读懂一个 Theme，不读解释也能决策，想深挖有解释。

---

## 2. 用户故事 / PM 痛点

作为 Portfolio Manager，我每天开盘前 / 周会前想回答：

1. **What matters now?** 现在 Top 5 Theme 是什么？新的 Theme 是什么？昨天的 Theme 死了还是延续？
2. **How is it performing?** Theme 近 1W / 1M / YTD 表现如何？vs Benchmark (SPX / QQQ / TSX Composite) 超额多少？
3. **How to track it?** 有什么 Proxy？比如加拿大金融业：`XFN.TO, ZEB.TO, S&P/TSX Capped Financials Index`。要可交易、可跟踪、有流动性。
4. **Why now?** 是什么 Re-price？什么 News / Event 触发？Timing + Source 必须有。
5. **What does it depend on?** 下一个验证点是什么？下个Q财报？央行会议？大选？数据发布？如果证伪会怎样？
6. **Theme or Noise?** 帮我过滤。大量的 Weekly Commentary 是最好的 Theme 来源，但要提炼，不是搬运。

---

## 3. 产品原则

1. **Decision-first, not news-first：** 每个 Theme 必须回答 So What + What Next，不只是发生了什么。
2. **5-min rule：** 单个 Theme 正文阅读 <5min (~700-900中文字 / ~500英词)。解释不计入，但默认折叠。
3. **Timing is everything：** 任何 News/Event 必须带 `UTC时间 + Source + Link`，无时间无源 = 不可发布。
4. **前后端隔离：** Agent 每周只更新 `content / data`，绝不碰 `UI code`。靠 API contract + schema version 隔离。
5. **Dual-agent制：** 发布前必须有第二个 Agent扮演 Portfolio Manager Reviewer，专挑 data error 和前后矛盾。

---

## 4. 信息架构 (IA)

**首页 / Today：**
* Market Regime 一句话 (Risk-on/off, 关键词3个)
* Active Themes (3-7个)：状态 = New / Continuing / Fading / Dead
* Yesterday's Themes 追踪：延续？加强？证伪？
* Benchmark 条：SPX, NDX, TSX, 10Y, USD/CAD, Oil/Gold

**Theme 详情页结构 (固定模板，不许 Agent 自创)：**
1. Title + Status + Conviction (High/Med/Low) + Horizon (Tactical 2-8w / Cyclical 3-12m)
2. Performance vs Benchmark (chart + table)
3. Proxy to Track (1-3个)
4. Why Now / Thesis (Re-price逻辑)
5. Key Events / News Timeline
6. Depends On / What to Watch (Next Catalyst + Bear case)
7. Theme vs Noise 判定
8. 解释 (Smaller, 可展开) : 术语、计算方法、数据口径

**Archive / Weekly Commentary Digests：** 原始来源库，可溯源。

---

## 5. 后端设计：让每周更新不乱

**核心原则：Frontend 只读 API，Agent 只写 Content DB。**

DB Tables:

```text
themes(id, title, status, conviction, horizon, thesis_summary, created_at, updated_at, schema_v=1)
theme_perf(theme_id, date, ret_1w, ret_1m, ret_ytd, benchmark_ticker, excess_1w, data_as_of_utc)
proxies(id, theme_id, ticker, name, type[ETF/Index/Basket], region, expense, liquidity_note)
events(id, theme_id, event_time_utc, title, source, url, type[macro/earnings/policy/geopolitics])
catalysts(id, theme_id, due_date, event_name, why_matters, if_bull, if_bear)
commentary_sources(id, week, firm, url, key_takeaway)
reviews(theme_id, reviewer_version, pass_fail, issues[])
```

API Contract (Frontend 锁定)：
* `GET /api/themes/active?date=YYYY-MM-DD`
* `GET /api/themes/:id`
* `GET /api/themes/history?theme_id=`

> Agent 更新流程：只允许新增 `content_version` + PR 到 `data/` 目录 (yaml/json)，触发 CI schema validation，通过 + Reviewer PASS 才能 merge，前端自动重新渲染，无需改代码。

文件隔离：
```
/frontend/  # Next.js / React, 不许 Agent 动
/backend/   # API + DB
/data/themes/2026-W40/theme_xxx.yaml  # Agent 唯一可写区
/prompts/   # Agent prompts 版本管理
```

---

## 6. 字体与阅读规范 (严格三档)

只允许三类：

* **Title：** 20-22px, 700, 一行主题 + 状态标签。例：`加拿大银行盈利重估 [Continuing | High Conviction]`
* **正文 Body：** 15-16px, 400, 1.6行高。承载所有决策信息。超过900字打回。
* **解释 Explainer：** 13px, 灰色 `#6B7280`, 默认折叠 `<details>`。解释口径、术语、计算细节。你可以不读，但想读必须能读懂。

正文禁止引入第四种 size/颜色加粗滥用。News 时间用 `Monospace 13px` 内嵌于正文时间轴，但不算新档次。

阅读时长检测：发布前计算 `word_count / 200wpm`，正文 >5min 自动 FAIL。

---

## 7. Performance vs Benchmark 规范

每个 Theme 必须有：

* 基准选择逻辑：US Theme -> SPX, Tech -> NDX, Canada -> S&P/TSX Composite，必须说明为什么选它。
* 区间：1W / 1M / YTD + Since Theme inception
* 数据字段：`Proxy price, as_of_UTC, source (Yahoo/CapitalIQ/Bloomberg), excess return`
* 图：Proxy vs Benchmark 归一化 (Rebased to 100)
* 禁止事项：禁止用盘中价冒充收盘价，禁止混用 Total Return / Price Return 不注明。

示例：`ZEB.TO +8.2% 1M vs TSX +2.1%, 超额 +6.1pp, as of 2026-10-03 close, Source: TMX`

---

## 8. Proxy 选择规范

每个 Theme 1-3个 Proxy，按优先级：
1. 流动性 ETF (例：加拿大金融 `ZEB.TO, XFN.TO`)
2. Index (例：`S&P/TSX Capped Financials`)
3. Basket (3-5只龙头，注明权重)

必须含：Ticker, 费用, AUM/日均量, 为什么能代表此 Theme, 有什么 tracking 缺陷。

---

## 9. Why Now + Depends On 规范

**Why Now 必须回答 Re-price 三问：**
* 以前 Price-in 了什么？现在为什么不对了？
* 触发器是哪个 Event (Earnings / Macro / Policy)？
* 市场共识 vs 你的边际变化？

**Depends On / What to Watch 表格：**

| 下一验证点 | 日期 (UTC) | 为什么重要 | Bull会看到什么 | Bear/证伪信号 |
|---|---|---|---|---|
| 例：RY/BMO Q3财报 | 2026-XX-XX | NIM/信贷损失 | ... | ... |

没有 Next Catalyst 的 Theme 降级为 Noise。

---

## 10. Theme vs Noise 判别 (Reviewer 重点查)

Theme 需满足 ≥3条，否则标 Noise 不上首页：

1. 持续性 >2周或跨 2+ 独立 Commentary 提及
2. 广度：≥3只股票 / ≥2子行业同向
3. 量价确认：Proxy 超额 +成交量放大
4. 有可证伪 Catalyst
5. 有 Re-price 逻辑，非单一 headline 脉冲

状态机：`Emerging -> New -> Continuing -> Fading -> Dead`，每天更新状态变化原因一句话。

Weekly Commentary 是主要输入：Goldman/BofA/MS/JPM/DB + BMO/RBC/TD 每周必扫，提炼分歧点，不是摘要。

---

## 11. 双 Agent 工作流 (关键：防 Data Error)

### Agent A - Theme Writer (Updater)

> 每周/每日跑，读 Commentary + 行情，输出 `data/themes/*.yaml` 符合 schema。

### Agent B - Portfolio Manager Reviewer (Gatekeeper)

发布前必须跑，不通过不能发布。Reviewer 人设：刻薄、多疑的 PM，只信数字和逻辑。

**Review Checklist (硬性)：**
1. Data error？价格/日期/涨跌幅能否对上 Source？as_of 是否过期？
2. 前后矛盾？Thesis 说利好，Catalyst 却是利空？Conviction High 但 Proxy 很弱？
3. Timing/Source 缺失？每个 Event 有 UTC + Link？
4. 超 5min？字数超？
5. Theme/Noise 误判？
6. Proxy 可交易？流动性太差打回。

输出：`PASS / FAIL + issue list + fix suggestion`。FAIL 必须打回 Writer 修改，最多 2轮，第二轮仍 FAIL 则降级为 Draft 不发布。

---

## 12. 可直接复制的 Prompts

### Prompt 1: Theme Writer

```text
You are a buy-side Thematic Analyst.

Input: weekly commentaries [links], market data as_of_UTC {date}, existing themes status.

Task: Output 3-7 themes in YAML following schema_v1. Each theme MUST include:
- title, status, conviction, horizon
- performance: proxy_ticker, ret_1w/1m/ytd, benchmark, excess, as_of_UTC, source
- proxies[1-3] with liquidity note
- thesis: priced_in_before vs repricing_now (max 150 words)
- events[]: each with event_time_UTC, source, url
- depends_on[]: next catalyst with due_date, bull/bear case
- theme_vs_noise_score (5 criteria)
- body_text <900 Chinese chars, explainer separate

Constraints:
- 3 font classes only. Body <5min read.
- No event without time+source.
- No forward-looking claim without catalyst.
- Language: concise, PM tone.
```

### Prompt 2: PM Reviewer (Gatekeeper)

```text
You are a skeptical Portfolio Manager reviewer. Your job is to BLOCK bad publishing.

Review the theme YAML. Check:
1. Data accuracy: recalc excess = proxy - benchmark. Flag mismatch >0.2pp. Check as_of freshness <48h.
2. Logic consistency: Does thesis match proxies? Does conviction match evidence? Bull/bear symmetric?
3. Completeness: Every event has event_time_UTC + source URL? Next catalyst dated?
4. Readability: body_text reading time <5min? No jargon without explainer?
5. Theme vs Noise: Does it meet >=3 criteria? If not, suggest demote to Noise.

Output JSON: {verdict: PASS/FAIL, issues: [{severity: blocker/major/minor, location, reason, fix}], summary_1line}
If FAIL blocker exists, DO NOT approve. Be harsh.
```

### Prompt 3: Frontend Builder (隔离用)

```text
Build a read-only frontend that ONLY consumes /api/themes/*.
- Stack: Next.js + Tailwind.
- Typography: Title 21px/700, Body 15.5px/1.6, Explainer 13px gray in <details>.
- Theme card shows: status pill, perf table, proxy tickers, timeline with UTC+source link, Depends On table.
- Never fetch raw YAML. Never hardcode theme content.
- Reading progress bar + ~X min label computed from body_text.
```

---

## 13. 验收标准 Definition of Done

* 首页 5min 能看完所有 Active Themes 标题+结论
* 单 Theme 正文 <5min，解释折叠但完整
* 每个 Event 可点击溯源 + UTC 时间正确
* 前端改动与数据更新完全解耦：Agent PR 只碰 `/data/`
* Reviewer 报告存档可查，FAIL 率、修改记录可见
* 每日有 Yesterday vs Today diff：新增/延续/消退一目了然

---

你要我下一步帮你把这个 plan 落成 `PRD.md + prompts/ + data schema yaml` 脚手架吗？