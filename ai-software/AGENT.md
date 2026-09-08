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
params: period=8mo, interval=1d（全量重拉，幂等；窗口必须覆盖 2026-02（SaaSpocalypse），不许缩窗口！）
```
美股统一交易日历，直接对齐即可。

## 异动阈值与解读

- `|IGV 日收益| < 1.5%` → 只更新价格统计，不新增事件
- `|IGV| ≥ 1.5%` 或 `|IGV − QQQ| ≥ 1pp 且方向背离` → 必须新增/更新事件
- MOVES 行标签：`IGV=` / `QQQ=` / `VOL=x.x`
- Tag 集合：AI Disruption / AI Monetization / Earnings / Valuation & Sentiment / Macro Data（已在 index.html TAGCLS 配色）
- 分化规则：IGV 跌而 QQQ 平/涨 → 软件特有（财报/估值/监管）；同向大跌 → 宏观；SNOW/DDOG 新高而 IGV 滞涨 → 反弹扩散未完成

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
