# Thematic Tracker — PRD

> 版本：v1.0 · 状态：Scaffold 已落地 · 原始 Plan 见 [thematic-tracker-plan.md](./thematic-tracker-plan.md)

## 1. 产品一句话

一个给 PM 看的 **Theme 第一视角站**：现在市场最重要的 Theme 是什么？表现如何？用什么 track？为什么形成？依赖什么 catalyst？昨天 vs 今天有何变化？是 Theme 还是 Noise？

5 分钟内读懂一个 Theme，不读解释也能决策，想深挖有解释。

## 2. 目标用户与痛点

Portfolio Manager，每天开盘前 / 周会前想回答：

1. **What matters now?** Top 5 Theme、新 Theme、昨天的 Theme 死了还是延续。
2. **How is it performing?** 1W / 1M / YTD 表现，vs Benchmark（SPX / NDX / TSX Composite）超额多少。
3. **How to track it?** 可交易、可跟踪、有流动性的 Proxy。
4. **Why now?** 什么 Re-price？什么 News / Event 触发？Timing + Source 必须有。
5. **What does it depend on?** 下一个验证点、证伪条件。
6. **Theme or Noise?** 从 Weekly Commentary 提炼，不是搬运。

## 3. 产品原则

1. **Decision-first, not news-first**：每个 Theme 必须回答 So What + What Next。
2. **5-min rule**：单个 Theme 正文 < 5min（~700–900 中文字 / ~500 英词），解释默认折叠不计入。
3. **Timing is everything**：任何 News/Event 必须带 `UTC 时间 + Source + Link`，无时间无源 = 不可发布。
4. **前后端隔离**：Agent 只更新 `data/`，绝不碰前端代码。靠 API contract + schema version 隔离。
5. **Dual-agent 制**：发布前必须有第二个 Agent 扮演 PM Reviewer，专挑 data error 和前后矛盾。

## 4. 信息架构

- **首页 / Today**
  - Market Regime 一句话（Risk-on/off + 3 个关键词）
  - Active Themes（3–7 个），状态 = New / Continuing / Fading / Dead
  - Yesterday's Themes 追踪：延续？加强？证伪？
  - Benchmark 条：SPX, NDX, TSX, 10Y, USD/CAD, Oil, Gold
- **Theme 详情页**（固定模板，Agent 不许自创结构）
  1. Title + Status + Conviction（High/Med/Low）+ Horizon（Tactical 2–8w / Cyclical 3–12m）
  2. Performance vs Benchmark（chart + table）
  3. Proxy to Track（1–3 个）
  4. Why Now / Thesis（Re-price 逻辑）
  5. Key Events / News Timeline
  6. Depends On / What to Watch（Next Catalyst + Bear case）
  7. Theme vs Noise 判定
  8. 解释（可展开）：术语、计算方法、数据口径
- **Archive / Weekly Commentary Digests**：原始来源库，可溯源。

## 5. 技术架构

> 落地调整：前端栈从 Plan 的 Next.js 调整为 **Vite + React + TypeScript + Tailwind + shadcn/ui**（本地环境规范）；API contract 不变，前端仍只读 `/api/*`。

```
general theme tracker/
├── PRD.md
├── thematic-tracker-plan.md      # 原始 Plan
├── prompts/                      # Agent prompts 版本管理
│   ├── theme_writer.md
│   ├── pm_reviewer.md
│   └── frontend_builder.md
├── data/                         # Agent 唯一可写区
│   ├── schema/theme.schema.yaml  # schema_v1
│   ├── themes/2026-W40/*.yaml    # 每周主题内容
│   ├── market/snapshot_*.yaml    # Regime + Benchmark 条
│   ├── commentary/2026-W40.yaml  # Weekly Commentary 来源库
│   └── reviews/*.yaml            # Reviewer 报告存档
├── backend/                      # 只读 API（Node，无框架）
│   ├── server.js
│   └── validate.js               # schema 校验（CI 用）
└── frontend/                     # Vite React，Agent 不许动
```

### API Contract（前端锁定）

| Endpoint | 说明 |
|---|---|
| `GET /api/themes/active?date=YYYY-MM-DD` | 当期 Active Themes（不含 Dead） |
| `GET /api/themes/:id` | 单个 Theme 完整详情 |
| `GET /api/themes/history?theme_id=` | Theme 跨周快照历史 |
| `GET /api/market/snapshot` | Regime + Benchmark 条（v1.1 增补） |
| `GET /api/commentary?week=2026-W40` | Commentary 来源库（Archive 页用） |

### Agent 更新流程

只允许新增 `content_version` + PR 到 `data/` 目录（yaml），跑 `node backend/validate.js` 做 schema 校验，通过 + Reviewer PASS 才能 merge，前端自动重新渲染，无需改代码。

## 6. 字体与阅读规范（严格三档）

| 档位 | 规格 | 用途 |
|---|---|---|
| Title | 20–22px / 700 | 一行主题 + 状态标签 |
| Body | 15–16px / 400 / 1.6 行高 | 所有决策信息，超 900 字打回 |
| Explainer | 13px / `#6B7280` / 默认折叠 `<details>` | 口径、术语、计算细节 |

News 时间用 Monospace 13px 内嵌时间轴，不算新档次。发布前计算 `word_count / 200wpm`，正文 > 5min 自动 FAIL。

## 7. Performance vs Benchmark 规范

- 基准选择：US Theme → SPX，Tech → NDX，Canada → S&P/TSX Composite，必须说明为什么。
- 区间：1W / 1M / YTD + Since inception。
- 字段：`proxy_price, as_of_UTC, source, excess_return`。
- 图：Proxy vs Benchmark 归一化（Rebased to 100）。
- 禁止：盘中价冒充收盘价；混用 Total Return / Price Return 不注明。

## 8. Proxy 选择规范

每个 Theme 1–3 个 Proxy，优先级：流动性 ETF > Index > Basket（3–5 只龙头注明权重）。必须含：Ticker、费用、AUM/日均量、代表性理由、tracking 缺陷。

## 9. Why Now + Depends On 规范

**Why Now 必答 Re-price 三问**：以前 price-in 了什么？触发器是哪个 Event？市场共识 vs 边际变化？

**Depends On 表格**：下一验证点 / 日期(UTC) / 为什么重要 / Bull 信号 / Bear 证伪信号。没有 Next Catalyst 的 Theme 降级为 Noise。

## 10. Theme vs Noise 判别（≥3 条才算 Theme）

1. 持续性 > 2 周或跨 2+ 独立 Commentary 提及
2. 广度：≥3 只股票 / ≥2 子行业同向
3. 量价确认：Proxy 超额 + 成交量放大
4. 有可证伪 Catalyst
5. 有 Re-price 逻辑，非单一 headline 脉冲

状态机：`Emerging -> New -> Continuing -> Fading -> Dead`，每天更新状态变化原因一句话。

## 11. Dual-Agent 工作流

- **Agent A — Theme Writer**：每周/每日跑，读 Commentary + 行情，输出 `data/themes/*.yaml` 符合 schema_v1。Prompt 见 `prompts/theme_writer.md`。
- **Agent B — PM Reviewer (Gatekeeper)**：发布前必跑，刻薄多疑的 PM 人设，只信数字和逻辑。Checklist：数据准确性 / 前后一致 / Timing+Source 完整 / 5min 可读 / Theme-Noise 判别 / Proxy 可交易。输出 `PASS / FAIL + issue list`，FAIL 打回最多 2 轮，仍 FAIL 降级 Draft。Prompt 见 `prompts/pm_reviewer.md`，报告存档 `data/reviews/`。

## 12. 验收标准（Definition of Done）

- 首页 5min 看完所有 Active Themes 标题 + 结论
- 单 Theme 正文 < 5min，解释折叠但完整
- 每个 Event 可点击溯源 + UTC 时间正确
- 前端改动与数据更新完全解耦：Agent PR 只碰 `/data/`
- Reviewer 报告存档可查，FAIL 率、修改记录可见
- 每日有 Yesterday vs Today diff：新增 / 延续 / 消退一目了然

## 13. 本地运行

```bash
npm install            # 安装 backend 依赖（frontend 依赖在 frontend/ 内单独装）
npm run dev            # 同时起 backend (:8787) + frontend (Vite)
npm run validate       # 校验 data/ 下所有主题 YAML 是否符合 schema_v1
```
