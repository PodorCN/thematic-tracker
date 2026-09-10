# agent.md — Thematic Tracker 总协议（分发器）

> 你是 thematic tracker 的维护 agent。本文件只讲**所有 theme 通用的流程**，每个 theme 自己的 proxy、阈值、日历去读该文件夹下的 `AGENT.md`。

## 0. 仓库结构

```
agent.md                 ← 本文件：通用协议
home/                    ← 落地页（新增 theme 时加一张卡片）
<theme>/                  ← 每个 theme 独立文件夹，自包含：
  index.html               渲染器（只读内容，不为改内容而动它）
  theme.md                 唯一内容源（你每天改的就是它）
  tracker_data/            原始行情 CSV 缓存
  AGENT.md                 本 theme 的专属指令（proxy/阈值/日历/ quirks）
scripts/validate-theme.mjs ← 校验脚本，两个 theme 通用
```

现有 theme：`canadian-banks/`（加拿大六大行），`ai-software/`（AI 错杀软件反弹）。

## 1. 每日 SOP（每个交易日盘后，对每个 theme 跑一遍，全程约 10–15 分钟/theme）

1. **读专属指令**：先读 `<theme>/AGENT.md`（拿 ticker 清单、拉取窗口、异动阈值、MOVES 标签写法）。
2. **拉行情**：按 AGENT.md 的参数全量重拉（不要增量追加，保证幂等），覆盖 `tracker_data/*.csv`；算窗口收益、归一化序列（base=100）、日收益、放量倍数。
3. **异动筛查**：按 AGENT.md 的阈值决定是否需要新事件；同时检查催化剂日历是否命中当天。
4. **新闻归因**：web search，事件四要素——标题（一句话）、正文（传导链 2–4 句）、MOVES（当日 %）、SRC（来源名 + 日期，禁止编造；搜不到原因就写 `归因不明（unexplained）`）。
5. **重写 theme.md**：整个重写（不要局部 patch），格式严格遵守根 agent.md 旧版 §2 schema（frontmatter / PROXIES / STATS / VERDICT / EVENTS 升序编号 / CATALYSTS / CHARTDATA）；事件超 ~15 条时合并最老最不重要的。**同步更新 `## VALIDITY` 灯**：用 chartdata 重算近 42 个交易日（约两个月）主 proxy vs 基准（tsx 槽）的超额，按该 theme AGENT.md 的灯规则定 green/yellow/red 并写清理由数字。
6. **校验**：`node scripts/validate-theme.mjs <theme>/theme.md` 必须 PASS（error 清零；warning 修不了就留着，但要在汇报里说明）。
7. **发布**：`git add <theme>/` → 一天一个 commit（`data(<theme>): update theme.md <updated>`）→ 推 dev/功能分支 → Action 绿 → 合 main（自动上线约 1 分钟）→ 打开线上页确认。回滚用 `git revert`。

## 2. 新增一个 theme（5 步）

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
