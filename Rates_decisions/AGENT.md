# AGENT.md — Rates Decisions（美加央行下一次利率决议看板）专属指令

> ⚠️ 本文件夹**不走**根目录 `AGENT.md` 的每日 theme SOP（没有 `theme.md`、proxy 或 VALIDITY 灯）。
> 它是基于 JSON 数据驱动的利率决议 2 分钟快览看板，配有独立的 PM 审阅机制与归档流水线。

## 1. 角色与定位

本看板回答的核心问题：**下一次 Fed 与 BOC 利率决议会议（Hike / Hold / Cut）大概率会怎么走？**
通过聚合官方利率预期、市场定价（含 Polymarket 预测市场赔率）与加权驱动因子（Hawkish / Dovish），在 2 分钟内提供最清晰的决策依据。

## 2. 文件结构与契约

```text
Rates_decisions/
  index.html              前端渲染器（固定版式；日常数据更新绝不修改）
  styles.css              样式表（只读）
  app.js                  前端逻辑（只读）
  data/
    current.json          唯一人工/Agent 编辑的数据源
    latest.json           已发布的最新快照（由 publish 脚本原子生成，勿直接手动修改）
    dates.json            已归档日期清单（降序排列）
    archive/<date>.json   每日不可变历史快照
  review/
    TEMPLATE.md           审阅报告模板
    <YYYY-MM-DD>.md       每日独立 PM 审阅记录（必须含 Verdict: APPROVED 方可发布）
  scripts/
    publish.mjs           数据校验与归档发布脚本（npm run check / npm run publish）
    fetch_betting.mjs     Polymarket 预测市场赔率抓取脚本
```

## 3. 维护流程（SOP）

日常更新数据时，严格执行以下 6 步：

```bash
# 1. （可选）抓取最新 Polymarket 预测市场赔率
node scripts/fetch_betting.mjs

# 2. 编辑数据：只修改 data/current.json
#    - 更新会议定价 probabilities / status
#    - 维护 hawkish / dovish 驱动因子、权重与依据
#    - 维护后续关键日历 releases

# 3. 机器数据校验
npm run check
# 或 node scripts/publish.mjs --check
# 检查项：JSON 合法性、概率和（0.99~1.01）、权重边界 [1,10]、总分重算一致性

# 4. 独立 PM 审阅
#    复制 review/TEMPLATE.md -> review/<today Toronto>.md
#    核对 source_url 真实数据、驱动方向符号、权重依据
#    在末尾签署：Verdict: APPROVED

# 5. 发布归档
npm run publish
# 机制：
#   - 校验 current.json 合法性
#   - 检查 review/<today Toronto>.md 是否存在且包含 Verdict: APPROVED
#   - 复制 current.json -> data/archive/<today>.json 与 data/latest.json
#   - 更新 data/dates.json

# 6. 本地真浏览器验收
npm run dev
# 打开 http://127.0.0.1:7100 确认页面渲染正常、无 NAN/错误徽标
```

## 4. 核心规范与红线

- **严禁修改前端**：`index.html`、`styles.css`、`app.js` 在日常更新中绝对禁止修改。
- **事实必须有源**：所有驱动因子必须附带真实有效的 `source_url`，严禁编造或臆测。
- **概率与时间填空规则**：未知或无法验证的数据必须明确标注 `"unverified"` 或 `"unavailable"`（例如 `probabilities: null` 配 `probability_status: "unavailable"`），严禁虚构概率数值。
- **无 APPROVED 绝不发布**：`scripts/publish.mjs` 会自动拦截缺失当天的 APPROVED 审阅文件，严禁绕过门禁手工拷贝。
