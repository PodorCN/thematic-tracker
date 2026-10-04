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
    current.json          唯一人工/Agent 编辑的数据源（snapshot_date 必须=当日多伦多）
    latest.json           已发布的最新快照（publish 原子写入 reviewed bytes，勿手改）
    dates.json            已归档日期清单（降序排列）
    archive/<date>.json   每日不可变历史快照（字节 == 当日 reviewed candidate）
  review/
    REVIEWER_AGENT.md       独立审阅者指令（必读：角色分离/证据/严重度/打分审计）
    pm-review.schema.json   pm-review.json 的机器 schema
    TEMPLATE.md             新流程模板（冻结→审阅→发布）
    <YYYY-MM-DD>/           当日冻结包（缺一不可，否则拒发）：
      candidate.json          冻结候选（freeze 写入后不可变）
      candidate.sha256        候选字节 SHA-256
      structural-flags.json   机器旗标（reviewer 必须逐条 disposition）
      pm-review.json          独立审阅结论（reviewer 亲手写，SHA 绑定）
      review.md               人类可读版（可选，需与 json verdict 一致）
    *.md                    旧版自由文本审阅（已退役，仅留档，publish 不认）
  scripts/
    freeze.mjs              冻结候选 + 生成 SHA + 结构旗标（npm run freeze）
    validate_pm_review.mjs  审阅结论校验（schema/SHA/角色/严重度，npm run review:check）
    publish.mjs           数据校验与归档发布脚本（npm run check / npm run publish）
    fetch_betting.mjs     Polymarket 预测市场赔率抓取脚本
```

## 3. 维护流程（SOP）

日常更新数据时，严格执行以下 6 步：

```bash
# 1. （可选）抓取最新 Polymarket 预测市场赔率
node scripts/fetch_betting.mjs

# 2. 编辑数据：只修改 data/current.json，并把 snapshot_date 设为当日多伦多日期
#    - 更新会议定价 probabilities / status
#    - 维护 hawkish / dovish 驱动因子、权重与依据
#    - 维护后续关键日历 releases

# 3. 机器数据校验（结构错误直接拦；结构旗标 warn，需 reviewer 逐条 disposition）
npm run check
# 检查项：概率和 0.99~1.01、betting 概率和、权重 1-10 整数、breakdown 三项和==weight、
# direction 与 hawkish(+1)/dovish(-1) 数组一致、base_total 与 effective_total 重算、
# band 标签一致、source_url https、日历 datetimes、snapshot_date 口径

# 4. 冻结候选（冻结后 data/current.json 任何改动都会让审阅作废）
node scripts/freeze.mjs
# -> review/<today>/candidate.json + candidate.sha256 + structural-flags.json

# 5. 独立 PM 审阅（reviewer 必须与 operator 不同人/模型，禁 self；详见 REVIEWER_AGENT.md）
#    reviewer 按 structural-flags.json 逐条写 review/<today>/pm-review.json：
#    candidate_sha256 绑定、六个 checks、findings（critical/major 拦）、flags_dispositioned 全覆盖
node scripts/validate_pm_review.mjs \
  --candidate review/<today>/candidate.json \
  --review review/<today>/pm-review.json \
  --flags review/<today>/structural-flags.json --require-approved

# 6. 发布归档（publish 会重验：结构 + SHA 三方一致 + review 结论 + 旗标全覆盖 + 前端干净）
npm run publish
# 机制：
#   - canonical(data/current.json) sha == candidate.json sha == pm-review.json candidate_sha256
#   - verdict 必须 APPROVED，且零 critical/major、六个 checks 全 pass
#   - 当前数据的每条结构旗标都必须在 flags_dispositioned 里出现
#   - 工作区里 index.html/app.js/styles.css/scripts 有改动则拒发（前端走独立 PR）
#   - 发布字节 == reviewed candidate 字节 -> archive/<today>.json + latest.json + dates.json

# 7. 本地真浏览器验收
npm run dev
# 打开 http://127.0.0.1:7100 确认页面渲染正常、无 NAN/错误徽标
```

## 4. 核心规范与红线

- **严禁修改前端**：`index.html`、`styles.css`、`app.js` 在日常更新中绝对禁止修改。publish 会检查 git 工作区，前端/scripts 脏了就拒发。
- **事实必须有源**：所有驱动因子必须附带真实有效的 `source_url`（https）。声称 StatCan/BLS/BEA/Fed/BoC 就必须链到对应主域（`statcan.gc.ca / bls.gov / bea.gov / federalreserve.gov / bankofcanada.ca`），否则机器打旗、reviewer 打回。二手转述必须写 `via X` 并降权，不得拿转述当独立 `market_validation`。
- **breakdown 必须对上**：`weight_breakdown{deviation, importance, surprise}` 三项和 == `weight`（且 `total`==`weight`）；`direction` 必须与所在数组一致（hawkish=+1/dovish=-1）；`effective_total` 按 `as_of` 年龄衰减重算（≤7d×1 / 8–14d×0.75 / 15–30d×0.5 / >30d×0.25），差 >0.06 拒发。
- **同一 release 拆两边必须有 facet**：同一 URL 同时出现在 hawkish 与 dovish，必须各自有不同 `facet` + 独立传导链，否则按 double-count 打回合并。
- **概率与时间填空规则**：未知或无法验证的数据必须明确标注 `"unverified"` 或 `"unavailable"`（例如 `probabilities: null` 配 `probability_status: "unavailable"`），严禁虚构概率数值。
- **冻结后不可变**：`review/<date>/candidate.json` 冻结后字节不可变；`data/current.json` 再改就 re-freeze（旧 review 自动作废）。
- **角色分离**：operator 与 reviewer 必须不同名（禁 `self/me`），reviewer 不改 candidate；approval 只绑定一个 sha。
- **无 APPROVED 绝不发布**：publish 要求冻结包四件套齐全 + `pm-review.json` 的 `candidate_sha256` 三方一致 + 零 critical/major + 六个 checks 全 pass + 结构旗标全覆盖。旧版 `review/<date>.md` 字符串门禁已废除。
