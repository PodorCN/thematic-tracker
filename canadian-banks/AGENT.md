# AGENT.md — Canadian Banks（加拿大六大行）专属指令

> 通用流程见根目录 `agent.md`。这里只写本 theme 特有的东西。

## Proxy 体系（勿改角色）

| 角色 | Ticker | 说明 |
|---|---|---|
| Main | ZEB.TO | BMO 六大行等权 ETF，所有归因基准，CAD |
| Supportive | BANK.TO | 1.25x 杠杆放大器（Evolve），涨跌幅 ≈1.2–1.4× ZEB 为健康 |
| Supportive | HFIN.TO | 泛金融判别器（Hamilton），与 ZEB 背离时判别银行特有 vs 金融系统性 |
| Benchmark | ^GSPTSE / ^GSPC | S&P/TSX 综合指数 / S&P 500（跨币种对比不做汇率换算） |

## 拉行情

```
tickers: ZEB.TO, BANK.TO, HFIN.TO, ^GSPTSE, ^GSPC → canadian-banks/tracker_data/<name>.csv
params: period=3mo, interval=1d（全量重拉，幂等）
```
所有 Canadian Banks 行情、派生 JSON 和 refresh evidence 都只能写入 `canadian-banks/tracker_data/`；根目录不再保存该 theme 的数据。

注意：TSX 和美股节假日不同，归一化日期对齐用 inner join；S&P 500 单独保留 spx_dates/spx_norm。

## 异动阈值与解读

- `|ZEB 日收益| < 1.5%` → 只更新价格统计，不新增事件
- `|ZEB| ≥ 1.5%` 或 `|ZEB − TSX| ≥ 1pp 且方向背离` → 必须新增/更新事件
- MOVES 行标签：`ZEB=` / `TSX=` / `VOL=x.x`
- Tag 集合：Earnings / Monetary Policy / Geopolitics / Macro Data / Valuation & Sentiment / Trade War（驱动颜色，新增 tag 先在 index.html 的 TAGCLS 里加映射）

## 灯规则（## VALIDITY，决定绿/黄/红）

2M 超额 = 近 42 个交易日（约两个月）ZEB（zeb 槽）相对 TSX（tsx 槽）的归一化点差。

- green（成立）: 超额 > +1pp，且无 thesis-break
- yellow（一般）: 超额在 ±1pp 内，thesis 完好
- red（不成立）: 超额 < -1pp，或 thesis-break
- thesis-break 定义：单季 PCL 大幅超预期、削减股息/回购、BoC 意外转向（降息重启或鹰派加息）、CET1 跌破监管舒适区
- CALL 行必须写清超额数字（如 `CALL: red | 1M excess -1.17pp vs TSX — …`），校验器会用 chartdata 复算（允差 ±0.3pp）

## 三因子归因框架

银行股只看三件事：**NIM（净息差，利率路径）/ PCL（信贷拨备，信用质量）/ 非息收入（资本市场+财富管理）**。新闻先归到某一因子再写传导链。

## 催化剂日历（滚动维护，过期删除）

| 日期 | 事件 |
|---|---|
| 2026-10-28 / 12-09 | BoC 利率决议 + MPR |
| 2026-12-02 ~ 12-04（预估） | 六大行 Q4/FY2026 财报（首个含 50% 关税影响的季度，盯 PCL） |
| 每月中旬 | 加拿大 CPI / 就业 |
| 2026 年底 / 2027 Q1 | NA 收购 Laurentian 交割；RBC/BMO 出售 Moneris 交割（~C$475M 一次性收益） |
| 持续 | 美加关税、CUSMA 审查 |

## 图表槽位映射（渲染器 key 名不许改）

`zeb_norm`=ZEB · `tsx_norm`=TSX · `bank_norm`=BANK · `hfin_norm`=HFIN · `spx_norm`+`spx_dates`=S&P 500 · `volume`/`zeb_ret`=ZEB。
