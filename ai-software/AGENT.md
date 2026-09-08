# AGENT.md — AI-Beaten Software（AI 错杀软件反弹）专属指令

> 通用流程见根目录 `agent.md`。这里只写本 theme 特有的东西。

## Proxy 体系（勿改角色）

| 角色 | Ticker | 说明 |
|---|---|---|
| Main | IGV | iShares Expanded Tech-Software ETF，所有归因基准，USD |
| Supportive | CRM | Salesforce，Agentforce AI 变现的头号证据 |
| Supportive | NOW | ServiceNow，AI workflow，情绪风向标 |
| Supportive | WDAY | Workday，HCM/Finance， guide 方向决定 AI 蚕食叙事 |
| Benchmark | QQQ | Nasdaq-100（科技 beta 锚） |
| Laggard watch（仅 STATS/正文提，不进图） | ADBE / INTU | 跌最深还没回来的：轮动候选或价值陷阱 |

## 拉行情

```
tickers: IGV, QQQ, CRM, NOW, WDAY, ADBE → tracker_data/<name>.csv
params: period=14mo, interval=1d（全量重拉，幂等；窗口必须覆盖 2025-09（本轮起点），不许缩窗口！）
```
美股统一交易日历，直接对齐即可。

## 时间线跨度规则（12M 窗口）

- **近 6 个月**：逐日事件块（沿用根协议阈值）。
- **6 个月以前**：按自然月合并为月度块——日期取该月最后一个交易日，标题涨跌幅写**当月**回报，正文保留当月关键单日极值（如单日 -4.97% / 3.9x 放量），MOVES 行写月度 IGV/QQQ，SRC 至少 1 个。
- 每日重写时把超 6 个月的逐日块合并成月度块，保持总数 ≤15。

## 异动阈值与解读

- `|IGV 日收益| < 1.5%` → 只更新价格统计，不新增事件
- `|IGV| ≥ 1.5%` 或 `|IGV − QQQ| ≥ 1pp 且方向背离` → 必须新增/更新事件
- MOVES 行标签：`IGV=` / `QQQ=` / `VOL=x.x`
- Tag 集合：AI Disruption / AI Monetization / Earnings / Valuation & Sentiment / Macro Data（已在 index.html TAGCLS 配色）
- 分化规则：IGV 跌而 QQQ 平/涨 → 软件特有（财报/估值/监管）；同向大跌 → 宏观；SNOW/DDOG 新高而 IGV 滞涨 → 反弹扩散未完成

## 灯规则（## VALIDITY，决定绿/黄/红）

1M 超额 = 近 21 个交易日 IGV（zeb 槽）相对 QQQ（tsx 槽）的归一化点差。

- green（成立）: 超额 > +1pp，且 AI ARR 证据链完好
- yellow（一般）: 超额在 ±1pp 内，thesis 完好
- red（不成立）: 超额 < -1pp，或 thesis-break
- thesis-break 定义：龙头下调 AI 指引、NRR 崩塌、hyperscaler 砍 capex、per-seat 加速侵蚀且无用户扩张对冲
- CALL 行必须写清超额数字（如 `CALL: green | 1M excess +2.47pp vs QQQ — …`），校验器会用 chartdata 复算（允差 ±0.3pp）

## 两因子归因框架

软件股只看两件事：**AI 增量收入（AI ARR、Agentforce 付费单、cRPO）/ per-seat 侵蚀（NRR、指引、定价权）**。每季度盯 NRR 和 AI-SKU attach——这两个数就是本 theme。

## 催化剂日历（滚动维护，过期删除）

| 日期 | 事件 |
|---|---|
| 2026-09-10 | Adobe Q3（laggard 验证或证伪） |
| 2026-10 下旬 | hyperscaler 财报 + MSFT Copilot 评论（AI capex 耐久度） |
| 2026-11 ~ 12（预估） | CRM / NOW / WDAY Q3 财报（hot：AI ARR 能否连 beat 第二季） |
| 持续 | per-seat 定价战、AI agent 新品（通用 AI 替代专业软件的 headline 风险） |

## 图表槽位映射（渲染器 key 名不许改）

`zeb_norm`=IGV · `tsx_norm`=QQQ · `bank_norm`=CRM · `hfin_norm`=NOW · `spx_norm`+`spx_dates`=WDAY · `volume`/`zeb_ret`=IGV。
