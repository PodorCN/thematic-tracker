# agent.md — Thematic Tracker 总协议（分发器）

> 你是 thematic tracker 的维护 agent。本仓库现在要维护**四样东西**：两个 theme + 两个宏观页，
> 它们的更新方式**不一样**，先看 §0.1 的清单确认你要动的是哪一类，再往下读。
>
> 本文件只讲通用流程；每样东西自己的 proxy、阈值、日历、闸门，去读它文件夹下的 `AGENT.md`。

## 0. 仓库结构

```
agent.md                 ← 本文件：通用协议
home/                    ← 落地页（新增 theme 时加一张卡片）
<theme>/                  ← 每个 theme 独立文件夹，自包含：
  index.html               渲染器（只读内容，不为改内容而动它）
  theme.md                 唯一内容源（你每天改的就是它）
  tracker_data/            原始行情 CSV 缓存
  AGENT.md                 本 theme 的专属指令（proxy/阈值/日历/ quirks）
economic-calendar/       ← 宏观页 1：全球经济日历（自动发布，无 theme.md）
fed-boc-watcher/         ← 宏观页 2：Fed×BOC 拔河看板（过 PM 闸门才发，无 theme.md）
scripts/validate-theme.mjs ← 校验脚本，theme 通用
scripts/econ/              ← 宏观页的 Python 流水线（抓取/渲染/归档），与 theme SOP 无关
tests/                     ← scripts/econ/ 的单元测试（pytest，无网络）
docs/                      ← 宏观页的发布契约与运维手册
```

## 0.1 要维护的四样东西

本仓库现在有 **4 个要更新的对象**，分成两类。**动手之前先确认你在哪一类**：

| # | 对象 | 类型 | 内容源 | 更新方式 | 专属指令 |
|---|---|---|---|---|---|
| 1 | `canadian-banks/` | theme | `theme.md`（手写） | 人/agent 每交易日盘后跑 §1 SOP | `canadian-banks/AGENT.md` |
| 2 | `ai-software/` | theme | `theme.md`（手写） | 人/agent 每交易日盘后跑 §1 SOP | `ai-software/AGENT.md` |
| 3 | `economic-calendar/` | 宏观页 | FxStreet API（Python 渲染） | **GitHub Actions 全自动**，每天 13:10 UTC | `economic-calendar/AGENT.md` |
| 4 | `fed-boc-watcher/` | 宏观页 | 研究 + 官方源（Python 渲染） | **半自动：必须过独立 PM 审阅闸门**，永不自动发布 | `fed-boc-watcher/AGENT.md` |

两类的区别，别搞混：

|  | theme（1–2） | 宏观页（3–4） |
|---|---|---|
| 内容源 | `theme.md`，你每天手写重写 | JSON 数据，Python 渲染 |
| 有 VALIDITY 灯吗 | 有（green/yellow/red） | 没有 |
| 有 proxy / 基准吗 | 有 | 没有 |
| 校验 | `node scripts/validate-theme.mjs` | `pytest tests/` |
| 适用 SOP | 下面的 §1 | 各自 `AGENT.md`，**§1 不适用** |

`economic-calendar/` 和 `fed-boc-watcher/` 是 2026-09 从 `thematic-market-watcher` 仓库迁入的，
它们没有 `theme.md`、没有 proxy、没有 VALIDITY 灯，**不要**试着用 §1 的流程去更新它们。

日常节奏：第 3 项自己会跑，你不用管（除非 Action 红了）；第 4 项只在你被明确指派时动，且必须走闸门；
第 1、2 项才是每个交易日的例行工作。

## 1. 每日 SOP —— **只适用于 theme（第 1、2 项）**

（每个交易日盘后，对每个 theme 跑一遍，全程约 10–15 分钟/theme。宏观页不走这一节。）

1. **读专属指令**：先读 `<theme>/AGENT.md`（拿 ticker 清单、拉取窗口、异动阈值、MOVES 标签写法）。
2. **拉行情**：按 AGENT.md 的参数全量重拉（不要增量追加，保证幂等），覆盖 `tracker_data/*.csv`；算窗口收益、归一化序列（base=100）、日收益、放量倍数。
3. **异动筛查**：按 AGENT.md 的阈值决定是否需要新事件；同时检查催化剂日历是否命中当天。
4. **新闻归因**：web search，事件四要素——标题（一句话）、正文（传导链 2–4 句）、MOVES（当日 %）、SRC（来源名 + 日期，禁止编造；搜不到原因就写 `归因不明（unexplained）`）。
5. **重写 theme.md**：整个重写（不要局部 patch），格式严格遵守根 agent.md 旧版 §2 schema（frontmatter / PROXIES / STATS / VERDICT / EVENTS 升序编号 / CATALYSTS / CHARTDATA）；事件超 ~15 条时合并最老最不重要的。**同步更新 `## VALIDITY` 灯**：用 chartdata 重算近 42 个交易日（约两个月）主 proxy vs 基准（tsx 槽）的超额，按该 theme AGENT.md 的灯规则定 green/yellow/red 并写清理由数字。
6. **同步发布副本**：将 `<theme>/theme.md` 逐字节复制为 `<theme>/theme.txt`。`theme.md` 是唯一编辑源；`theme.txt` 是 GitHub Pages 可稳定 fetch 的发布资产，两者必须字节一致。
7. **校验**：`node scripts/validate-theme.mjs <theme>/theme.md` 必须 PASS（error 清零；warning 修不了就留着，但要在汇报里说明），并检查 `theme.md` 与 `theme.txt` 字节一致。
8. **发布**：`git add <theme>/` → 一天一个 commit（`data(<theme>): update theme.md <updated>`）→ 推 dev/功能分支 → Action 绿 → 合 main（自动上线约 1 分钟）→ 直接请求线上 `<theme>/theme.txt`，确认 HTTP 200 和 `updated` 日期，再打开线上页确认。回滚用 `git revert`。

## 2. 新增一个 theme（5 步）

> 这一节只讲新增 **theme**。宏观页不是这样加的——它自带 Python 流水线和 workflow，加之前先读 `docs/PUBLIC_PAGES_BACKEND_SPEC.md`。

1. 复制 `canadian-banks/` 文件夹为 `<new-theme>/`（渲染器、分叉即用）。
2. 在新文件夹里：按显示需求替换 `index.html` 的标签文字（图表 key 名 `zeb_norm/tsx_norm/bank_norm/hfin_norm/spx_norm` **不许改**，只换 label——槽位映射写进该 theme 的 AGENT.md）。
3. 写该 theme 的 `AGENT.md` + 首版 `theme.md`（用校验器跑通）。
4. `home/index.html` 加一张卡片。
5. `.github/workflows/validate.yml` 加两行（trigger path + run 命令）。

## 3. 红线（所有 theme 通用）

- **禁止编造**：价格必须来自行情接口，事件必须带来源。
- **接口失败**：当日跳过并记录，下一交易日重拉（全量窗口幂等覆盖）。
- **非交易日**：只维护 CATALYSTS，不改价格。
- **不要改 index.html**：内容问题一律在 theme.md 里解决；只有用户明确要求改版式才动渲染器。
- **CRLF 注意**：theme.md 经常是 CRLF（Windows 编辑），解析/校验必须先归一化换行（校验脚本已处理；自己写脚本别忘）。
- **宏观页的 HTML 不要手改**：`economic-calendar/index.html`、`economic-calendar/archive/*.html` 由
  `scripts/econ/template_calendar.html.j2` 渲染，手改会被下次流水线覆盖；要改版式就改模板。
- **Fed/BOC 永不自动发布**：没有 `approved` 的 PM 审阅（且 sha256 对上 candidate 字节），不许 archive/commit/push。
