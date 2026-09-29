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

2M 相对信号 = 截至最新收盘的 42 个交易观测值，IGV 与 QQQ 均按窗口首日 100 归一化；比较从第 -42 个观测值到最新观测值各自的标准化点数变化，差值单位为 normalized points（不是这两个月各自百分比收益之差）。

- green（成立）: 标准化点差 > +1 point，且 AI ARR 证据链完好
- yellow（一般）: 标准化点差在 ±1 point 内，thesis 完好
- red（不成立）: 标准化点差 < -1 point，或 thesis-break
- thesis-break 定义：龙头下调 AI 指引、NRR 崩塌、hyperscaler 砍 capex、per-seat 加速侵蚀且无用户扩张对冲
- CALL 行必须写清标准化点差（如 `CALL: green | 42-session normalized-point spread +2.47 normalized points vs QQQ — …`），校验器会用 chartdata 复算（允差 ±0.3 point）。

## 两因子归因框架

软件股只看两件事：**AI 增量收入（AI ARR、Agentforce 付费单、cRPO）/ per-seat 侵蚀（NRR、指引、定价权）**。每季度盯 NRR 和 AI-SKU attach——这两个数就是本 theme。

## 催化剂日历（滚动维护，过期删除）

| 日期 | 事件 |
|---|---|
| 2026-09-10 | Adobe Q3（laggard 验证或证伪） |
| 2026-10 下旬 | hyperscaler 财报 + MSFT Copilot 评论（AI capex 耐久度） |
| 2026-10 下旬（估计；以 IR 正式公告为准） | NOW Q3 日历年财报：cRPO/AI workflow 指引（2025 Q3 于 10/29 发布，2026 Q2 于 7/22 发布） |
| 2026-11 下旬 ~ 12 上旬（估计；以 IR 公告为准） | WDAY FY27 Q3 / CRM FY27 Q3 财报：AI ARR 与续费/席位指标；不得将 NOW 并入此窗口 |
| 持续 | per-seat 定价战、AI agent 新品（通用 AI 替代专业软件的 headline 风险） |

## 图表槽位映射（渲染器 key 名不许改）

`zeb_norm`=IGV · `tsx_norm`=QQQ · `bank_norm`=CRM · `hfin_norm`=NOW · `spx_norm`+`spx_dates`=WDAY · `volume`/`zeb_ret`=IGV。
