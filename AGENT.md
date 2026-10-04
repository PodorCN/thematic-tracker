# AGENT.md — Thematic Tracker 总协议（分发器）

> **给维护 Agent 的指引**：
> 本仓库采用**分层维护架构**：
> 1. **根目录 `AGENT.md`（本文件）**：全局总指挥与协议分发器。告诉你当前仓库维护哪些产品看板、核心运行机制、全局红线与安全门禁。
> 2. **每个具体目录专属的 `AGENT.md`**：每个看板目录下均有其独立的 `AGENT.md`。具体的数据字段定义、抓取脚本、异动规则、审阅要求或发布门禁，**必须去读该目录下的 `AGENT.md`**。

---

## 0. 仓库结构与维护清单

```text
AGENT.md                 ← 【根协议】总分发器：全库对象清单、SOP 分发、通用红线
home/                    ← 落地主页（展示 Rates_decisions 和 economic-calendar）
Rates_decisions/         ← 看板 1：美加央行利率决议看板（JSON 驱动 + Polymarket 预测）
  AGENT.md                 current.json 维护、check 校验、PM 审阅与 publish 流程
economic-calendar/       ← 看板 2：全球经济日历（Actions 每日全自动抓取与发布 JSON）
  AGENT.md                 日历数据抓取、发布契约与本地测试说明
scripts/econ/frontend_contract.json ← 前端渲染器 SHA-256 冻结基线
scripts/econ/verify_data_only_changes.py ← 日常发布路径与数据-only 机器门禁
```

### 0.1 维护对象总览

本仓库当前核心维护 **2 个宏观与利率决策看板（Macro & Rate Decisions Dashboards）**：

| # | 目录/对象 | 核心定位与数据源 | 更新与发布机制 | 专属指令入口 |
|---|---|---|---|---|
| **1** | `Rates_decisions/` | 下次美加利率决议 2 分钟快览看板；`data/current.json` | 本地 `npm run check` 校验 + 独立 PM 审阅签字后 `npm run publish` 归档 | [`Rates_decisions/AGENT.md`](./Rates_decisions/AGENT.md) |
| **2** | `economic-calendar/` | 全球高影响经济日历；FxStreet/ForexFactory JSON | **GitHub Actions 全自动抓取与发布**（每日 13:10 UTC） | [`economic-calendar/AGENT.md`](./economic-calendar/AGENT.md) |

> 💡 **关于投资主题（Theme）**：目前暂无活跃 Theme。如后续需要新增具体的主题跟踪器（如特定行业或策略），请参考 [§2 新增一个 Theme 的标准化流程](#2-未来新增-theme-的标准化流程)。

---

## 0.2 Agent 导航与行动指引

当你以 Agent 身份进入本仓库执行任务时：
1. **确认目标**：先看 §0.1 清单，明确当前任务是针对 `Rates_decisions` 还是 `economic-calendar`。
2. **读专属规则**：立即打开对应目录下的 `AGENT.md`：
   - 维护利率决议看板：进入 [`Rates_decisions/AGENT.md`](./Rates_decisions/AGENT.md)
   - 维护全球经济日历：进入 [`economic-calendar/AGENT.md`](./economic-calendar/AGENT.md)
3. **严格区分数据与前端**：所有日常数据更新**仅限修改数据文件**（如 JSON 数据源），严禁在日常数据更新提交中夹带修改前端 `index.html`。

---

## 1. 核心看板维护流程概览

### 1.1 Rates Decisions 看板维护
详细 SOP 见 [`Rates_decisions/AGENT.md`](./Rates_decisions/AGENT.md)：
1. （可选）抓取最新 Polymarket 赔率：`node scripts/fetch_betting.mjs`
2. 编辑数据源：仅修改 `Rates_decisions/data/current.json`
3. 机器数据校验：`npm --prefix Rates_decisions run check`
4. 独立审阅签字：复制 `review/TEMPLATE.md` 至 `review/<today Toronto>.md`，确认 `Verdict: APPROVED`
5. 归档发布：`npm --prefix Rates_decisions run publish`

### 1.2 Economic Calendar 日历维护
详细规范见 [`economic-calendar/AGENT.md`](./economic-calendar/AGENT.md)：
- 由 `.github/workflows/macro-pages-daily.yml` 每日 13:10 UTC 自动抓取并发布；
- 本地手动更新或测试：
  ```bash
  python scripts/econ/fetch_calendar.py --date <date> --days 7 --countries US,CA,EMU,DE,FR,IT,ES,UK,CH --impacts HIGH,MEDIUM --with-history
  python scripts/econ/render_calendar.py --date <date>
  python scripts/econ/verify_data_only_changes.py --product economic-calendar --staged
  python -m pytest tests/test_econ_render.py -q
  ```

---

## 2. 未来新增 Theme 的标准化流程

如需在未来新增单项投资主题跟踪器（Thematic Tracker）：

1. **创建 Theme 目录**：新建 `<new-theme>/` 文件夹，包含渲染器 `index.html` 与行情缓存 `tracker_data/`。
2. **编写专属 `AGENT.md` 与首版 `theme.md`**：在目录下建立 `<new-theme>/AGENT.md`，定义 Proxy 标的体系、异动阈值、归因框架与 VALIDITY 绿/黄/红灯规则；编写首版 `theme.md` 并镜像为 `theme.txt`。
3. **主页注册**：在 `home/index.html` 中新增对应的 Theme 卡片与入口。
4. **CI 门禁接入**：在 `.github/workflows/` 中添加自动化校验步骤。

---

## 3. 全局红线与安全规范（所有模块通用）

- **严禁虚构造假**：价格必须取自行情真实数据，所有驱动因素必须附带真实来源 URL。未知或无法验证的数据必须明确标为 `"unverified"` 或 `"unavailable"`，严禁臆测。
- **数据与前端严格解耦**：
  - 日常数据发布只允许触碰数据文件（JSON、CSV 或 review 审阅凭证）。
  - 各模块的 `index.html`、CSS、JS、模板以及脚本均属于开发变更，严禁在日常数据更新提交中夹带。
- **修改 HTML 必须走独立开发 PR**：若需改动页面展示，必须单独开分支与 PR，更新 `scripts/econ/frontend_contract.json` 中该页面的 SHA-256 哈希，完成真浏览器测试与代码审查后方可合并。
- **提交前必跑机器门禁**：在暂存数据后、commit 之前，必须执行：
  ```bash
  python scripts/econ/verify_data_only_changes.py --product economic-calendar --staged
  ```
  门禁退出码非 0 时绝对禁止提交或推送。
- **发布需经严格审阅**：带有审阅机制的看板（如 `Rates_decisions`），必须在通过机器检验且具有 APPROVED 审阅凭证后方可执行 publish 归档。
